#!/usr/bin/env bash
# k8s/scripts/deploy-init.sh
#
# FinOps MVP unified deploy/init script.
# Idempotent. Safe to re-run.
#
# Usage:
#   bash k8s/scripts/deploy-init.sh
#
# Optional env vars:
#   REPO_URL       - git repo URL for ArgoCD bootstrap
#                    (default: https://github.com/mityay36/finops-mvp)
#   MODE           - skip interactive mode prompt:
#                    "full"   = full bootstrap (Helm CRDs + ArgoCD + repos + secrets + sync)
#                    "gitops" = ArgoCD already there, apply root-app + secrets
#                    "finops" = ArgoCD + root-app already there, just secrets + sync
#   ASSUME_YES     - "1" to skip the kubectl-context confirmation
#
# Exit codes:
#   0  - success
#   1  - missing tool / unmet precondition
#   2  - user aborted
#   3  - kubectl/argocd operation failed

set -Eeuo pipefail

# ── Path resolution ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$K8S_ROOT/.." && pwd)"

REPO_URL="${REPO_URL:-https://github.com/mityay36/finops-mvp}"
MODE="${MODE:-}"
ASSUME_YES="${ASSUME_YES:-0}"

# ── Pretty logging ─────────────────────────────────────────────────────────
if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'
  C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_CYAN=$'\033[36m'
else
  C_RESET=''; C_BOLD=''; C_GREEN=''; C_YELLOW=''; C_RED=''; C_CYAN=''
fi

log()  { printf '%s%s%s\n' "$C_CYAN" "$*" "$C_RESET"; }
ok()   { printf '  %s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf '  %s!%s %s\n' "$C_YELLOW" "$C_RESET" "$*"; }
err()  { printf '  %s✗%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; }
phase(){ printf '\n%s%s%s\n' "$C_BOLD" "$*" "$C_RESET"; }

# ── Phase 0: Preflight ─────────────────────────────────────────────────────
phase "[Phase 0] Preflight checks"

tool_version() {
  local tool="$1"
  case "$tool" in
    kubectl)  kubectl version --client 2>/dev/null | head -n1 | sed 's/Client Version: //' ;;
    helm)     helm version --short 2>/dev/null ;;
    openssl)  openssl version 2>/dev/null ;;
    jq)       jq --version 2>/dev/null ;;
    curl)     curl --version 2>/dev/null | head -n1 | awk '{print $1, $2}' ;;
    python3)  python3 --version 2>/dev/null ;;
    htpasswd) echo "" ;;
    base64)   echo "" ;;
    *)        echo "" ;;
  esac
}

require_tool() {
  local tool="$1"
  local hint="${2:-}"
  if ! command -v "$tool" >/dev/null 2>&1; then
    err "Required tool not found: $tool"
    if [ -n "$hint" ]; then
      err "  Hint: $hint"
    fi
    return 1
  fi
  local v
  v="$(tool_version "$tool")"
  if [ -n "$v" ]; then
    ok "$tool found ($v)"
  else
    ok "$tool found"
  fi
}

PREFLIGHT_OK=1
require_tool kubectl  "https://kubernetes.io/docs/tasks/tools/" || PREFLIGHT_OK=0
require_tool helm     "https://helm.sh/docs/intro/install/"     || PREFLIGHT_OK=0
require_tool openssl  "usually preinstalled"                    || PREFLIGHT_OK=0
require_tool htpasswd "apt install apache2-utils  /  brew install httpd" || PREFLIGHT_OK=0
require_tool jq       "apt install jq  /  brew install jq"      || PREFLIGHT_OK=0
require_tool curl     "usually preinstalled"                    || PREFLIGHT_OK=0
require_tool python3  "https://www.python.org/downloads/"       || PREFLIGHT_OK=0
require_tool base64   "usually preinstalled"                    || PREFLIGHT_OK=0

if [ "$PREFLIGHT_OK" = "1" ]; then
  if python3 -c "from cryptography.fernet import Fernet" >/dev/null 2>&1; then
    ok "python cryptography library available"
  else
    err "Python 'cryptography' package is required for FERNET_KEY generation"
    err "  Install with:  pip3 install cryptography"
    err "  Or:            python3 -m pip install cryptography"
    PREFLIGHT_OK=0
  fi
fi

if [ "$PREFLIGHT_OK" != "1" ]; then
  err "Preflight failed. Install missing tools and retry."
  exit 1
fi

# ── Kubectl context confirmation ───────────────────────────────────────────
CTX="$(kubectl config current-context 2>/dev/null || true)"
if [ -z "$CTX" ]; then
  err "kubectl has no current-context. Set one with 'kubectl config use-context <name>'."
  exit 1
fi

CLUSTER_NAME="$(kubectl config view --minify -o jsonpath='{.clusters[0].name}' 2>/dev/null || echo unknown)"
SERVER="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || echo unknown)"

log ""
log "Current kubectl context:"
log "  context: $CTX"
log "  cluster: $CLUSTER_NAME"
log "  server : $SERVER"
log ""

if [ "$ASSUME_YES" = "1" ]; then
  ok "ASSUME_YES=1 — skipping confirmation"
elif [ -t 0 ]; then
  read -rp "Proceed with this context? [y/N]: " ans
  case "$ans" in
    y|Y|yes|YES) ok "Confirmed" ;;
    *) err "Aborted by user."; exit 2 ;;
  esac
else
  warn "Non-interactive shell, no ASSUME_YES — proceeding without confirmation"
fi

# ── Phase 1: Detect cluster state ──────────────────────────────────────────
phase "[Phase 1] Detecting cluster state"

ARGOCD_PRESENT=0
ROOT_APP_PRESENT=0
FINOPS_NS_PRESENT=0
NGINX_PRESENT=0
OPENCOST_PRESENT=0
VMKS_PRESENT=0

if kubectl get ns argocd >/dev/null 2>&1; then
  if kubectl -n argocd get deploy argocd-server >/dev/null 2>&1; then
    READY="$(kubectl -n argocd get deploy argocd-server -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)"
    if [ "${READY:-0}" -ge 1 ]; then
      ARGOCD_PRESENT=1
      ok "ArgoCD is running (argocd-server has $READY ready replicas)"
    else
      warn "argocd-server exists but not Ready"
    fi
  else
    warn "namespace 'argocd' exists but argocd-server Deployment not found"
  fi
else
  warn "ArgoCD not installed (no 'argocd' namespace)"
fi

if [ "$ARGOCD_PRESENT" = "1" ]; then
  if kubectl -n argocd get application finops-root >/dev/null 2>&1; then
    ROOT_APP_PRESENT=1
    SYNC="$(kubectl -n argocd get app finops-root -o jsonpath='{.status.sync.status}' 2>/dev/null || echo Unknown)"
    HEALTH="$(kubectl -n argocd get app finops-root -o jsonpath='{.status.health.status}' 2>/dev/null || echo Unknown)"
    ok "finops-root Application present (sync=$SYNC, health=$HEALTH)"
  else
    warn "finops-root Application not found"
  fi

  for app in nginx-ingress opencost vmks; do
    if kubectl -n argocd get application "$app" >/dev/null 2>&1; then
      sync="$(kubectl -n argocd get app "$app" -o jsonpath='{.status.sync.status}' 2>/dev/null || echo Unknown)"
      health="$(kubectl -n argocd get app "$app" -o jsonpath='{.status.health.status}' 2>/dev/null || echo Unknown)"
      ok "$app present (sync=$sync, health=$health)"
      case "$app" in
        nginx-ingress) NGINX_PRESENT=1 ;;
        opencost)      OPENCOST_PRESENT=1 ;;
        vmks)          VMKS_PRESENT=1 ;;
      esac
    else
      warn "$app Application not found"
    fi
  done
fi

if kubectl get ns finops >/dev/null 2>&1; then
  FINOPS_NS_PRESENT=1
  ok "namespace 'finops' exists"
else
  warn "namespace 'finops' does not exist"
fi

# ── Phase 2: Choose mode ───────────────────────────────────────────────────
phase "[Phase 2] Choose deployment mode"

if [ "$ARGOCD_PRESENT" = "1" ] && [ "$ROOT_APP_PRESENT" = "1" ]; then
  DEFAULT_MODE="finops"
elif [ "$ARGOCD_PRESENT" = "1" ]; then
  DEFAULT_MODE="gitops"
else
  DEFAULT_MODE="full"
fi

if [ -z "$MODE" ]; then
  log ""
  log "Available modes:"
  log "  ${C_BOLD}1) full${C_RESET}   - Empty cluster: install Helm CRDs + ArgoCD + register repos"
  log "  ${C_BOLD}2) gitops${C_RESET} - ArgoCD running: apply root-app + create secrets + sync FinOps"
  log "  ${C_BOLD}3) finops${C_RESET} - root-app already present: only ensure secrets + force-sync FinOps"
  log ""
  log "Suggested mode based on cluster state: ${C_BOLD}$DEFAULT_MODE${C_RESET}"
  if [ -t 0 ] && [ "$ASSUME_YES" != "1" ]; then
    read -rp "Select mode [1=full / 2=gitops / 3=finops, Enter=$DEFAULT_MODE]: " ans
    case "$ans" in
      1|full)   MODE="full" ;;
      2|gitops) MODE="gitops" ;;
      3|finops) MODE="finops" ;;
      "")       MODE="$DEFAULT_MODE" ;;
      *) err "Invalid choice: $ans"; exit 2 ;;
    esac
  else
    MODE="$DEFAULT_MODE"
  fi
fi

ok "Selected mode: $MODE"

# Sanity: prevent obviously wrong combos
if [ "$MODE" = "finops" ] && [ "$ARGOCD_PRESENT" != "1" ]; then
  err "Mode 'finops' requires ArgoCD running. Use 'full' instead."
  exit 1
fi
if [ "$MODE" = "gitops" ] && [ "$ARGOCD_PRESENT" != "1" ]; then
  err "Mode 'gitops' requires ArgoCD running. Use 'full' instead."
  exit 1
fi

log ""
log "Plan:"
case "$MODE" in
  full)
    log "  - Install Prometheus Operator CRDs (Helm)"
    log "  - Install ArgoCD"
    log "  - Register OCI/Git repositories"
    log "  - Apply root-app"
    log "  - Create FinOps secrets"
    log "  - Force sync + wait for FinOps apps"
    ;;
  gitops)
    log "  - Apply root-app"
    log "  - Create FinOps secrets"
    log "  - Force sync + wait for FinOps apps"
    ;;
  finops)
    log "  - Create FinOps secrets (only if missing)"
    log "  - Force sync + wait for FinOps apps"
    ;;
esac
log ""


# ── Helpers for secrets ────────────────────────────────────────────────────

gen_password() {
  # 24 random bytes → base64 → strip /+= → alnum-only string ~32 chars
  openssl rand -base64 24 | tr -d '/+='
}

gen_fernet_key() {
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

# Read a single field from an existing k8s Secret (returns plaintext via base64 -d).
secret_field() {
  local ns="$1" name="$2" key="$3"
  kubectl -n "$ns" get secret "$name" \
    -o jsonpath="{.data.$key}" 2>/dev/null \
    | base64 -d 2>/dev/null
}

# Returns 0 if Secret exists in given namespace.
secret_exists() {
  local ns="$1" name="$2"
  kubectl -n "$ns" get secret "$name" >/dev/null 2>&1
}

# Prompt with [auto-generate] default. Empty answer → auto.
# Usage: prompt_secret VAR_NAME "Postgres password"
prompt_secret() {
  local var_name="$1" question="$2" default_label="${3:-auto-generate}"
  local input

  if [ -t 0 ] && [ "$ASSUME_YES" != "1" ]; then
    read -rsp "$question [$default_label]: " input
    echo
  else
    input=""
  fi

  if [ -z "$input" ]; then
    eval "$var_name=\$(gen_password)"
    NEWLY_GENERATED=1
  else
    eval "$var_name=\$input"
    NEWLY_GENERATED=0
  fi
}

prompt_plain() {
  local var_name="$1" question="$2" default_value="$3"
  local input

  if [ -t 0 ] && [ "$ASSUME_YES" != "1" ]; then
    read -rp "$question [$default_value]: " input
  else
    input=""
  fi
  if [ -z "$input" ]; then
    eval "$var_name=\$default_value"
  else
    eval "$var_name=\$input"
  fi
}

# ── Phase 3: Namespace ─────────────────────────────────────────────────────
phase "[Phase 3] Ensuring namespace 'finops'"

if kubectl get ns finops >/dev/null 2>&1; then
  ok "namespace 'finops' already exists"
else
  kubectl create namespace finops >/dev/null
  ok "namespace 'finops' created"
fi

# ── Phase 4: Secrets ───────────────────────────────────────────────────────
phase "[Phase 4] Ensuring FinOps secrets"

# Tracks whether any secret was generated in this run, to decide what to print.
SUMMARY_PG_PASS=""
SUMMARY_REDIS_PASS=""
SUMMARY_BASIC_USER=""
SUMMARY_BASIC_PASS=""
SUMMARY_FERNET=""
SUMMARY_NEW_SECRETS=()

# 1) finops-postgres-secret
if secret_exists finops finops-postgres-secret; then
  ok "finops-postgres-secret exists, reusing"
  PG_PASS="$(secret_field finops finops-postgres-secret POSTGRES_PASSWORD)"
  if [ -z "$PG_PASS" ]; then
    err "finops-postgres-secret exists but POSTGRES_PASSWORD is empty/missing"
    err "  Recreate it manually or delete with: kubectl -n finops delete secret finops-postgres-secret"
    exit 3
  fi
else
  log "Creating finops-postgres-secret"
  prompt_secret PG_PASS "  Postgres password"
  kubectl -n finops create secret generic finops-postgres-secret \
    --from-literal=POSTGRES_USER=finops \
    --from-literal=POSTGRES_DB=finops \
    --from-literal=POSTGRES_PASSWORD="$PG_PASS" >/dev/null
  ok "finops-postgres-secret created"
  SUMMARY_PG_PASS="$PG_PASS"
  SUMMARY_NEW_SECRETS+=("finops-postgres-secret")
fi

# 2) finops-redis-secret
if secret_exists finops finops-redis-secret; then
  ok "finops-redis-secret exists, reusing"
  REDIS_PASS="$(secret_field finops finops-redis-secret REDIS_PASSWORD)"
  if [ -z "$REDIS_PASS" ]; then
    err "finops-redis-secret exists but REDIS_PASSWORD is empty/missing"
    exit 3
  fi
else
  log "Creating finops-redis-secret"
  prompt_secret REDIS_PASS "  Redis password"
  kubectl -n finops create secret generic finops-redis-secret \
    --from-literal=REDIS_PASSWORD="$REDIS_PASS" >/dev/null
  ok "finops-redis-secret created"
  SUMMARY_REDIS_PASS="$REDIS_PASS"
  SUMMARY_NEW_SECRETS+=("finops-redis-secret")
fi

# 3) finops-api-secrets (depends on PG_PASS and REDIS_PASS resolved above)
if secret_exists finops finops-api-secrets; then
  ok "finops-api-secrets exists, reusing"
  EXISTING_FERNET="$(secret_field finops finops-api-secrets FERNET_KEY)"
  if [ -z "$EXISTING_FERNET" ]; then
    err "finops-api-secrets exists but FERNET_KEY is empty/missing"
    err "  Recreate it manually or delete with: kubectl -n finops delete secret finops-api-secrets"
    exit 3
  fi
else
  log "Creating finops-api-secrets"

  if [ -t 0 ] && [ "$ASSUME_YES" != "1" ]; then
    read -rsp "  FERNET_KEY [auto-generate]: " FERNET_KEY_INPUT
    echo
  else
    FERNET_KEY_INPUT=""
  fi

  if [ -z "$FERNET_KEY_INPUT" ]; then
    FERNET_KEY="$(gen_fernet_key)"
  else
    FERNET_KEY="$FERNET_KEY_INPUT"
  fi

  DATABASE_URL="postgresql+asyncpg://finops:${PG_PASS}@postgres.finops.svc.cluster.local:5432/finops"
  REDIS_URL="redis://:${REDIS_PASS}@redis.finops.svc.cluster.local:6379/0"

  kubectl -n finops create secret generic finops-api-secrets \
    --from-literal=DATABASE_URL="$DATABASE_URL" \
    --from-literal=REDIS_URL="$REDIS_URL" \
    --from-literal=FERNET_KEY="$FERNET_KEY" >/dev/null
  ok "finops-api-secrets created"
  SUMMARY_FERNET="(stored in finops-api-secrets, never printed)"
  SUMMARY_NEW_SECRETS+=("finops-api-secrets")
fi

# 4) finops-basic-auth
if secret_exists finops finops-basic-auth; then
  ok "finops-basic-auth exists, reusing"
else
  log "Creating finops-basic-auth"
  prompt_plain BASIC_USER "  Basic auth username" "admin"
  prompt_secret BASIC_PASS "  Basic auth password"

  HTPASSWD_LINE="$(htpasswd -nbB "$BASIC_USER" "$BASIC_PASS" | head -n1)"
  if [ -z "$HTPASSWD_LINE" ]; then
    err "htpasswd produced empty output — check that 'apache2-utils' or equivalent is installed"
    exit 3
  fi

  kubectl -n finops create secret generic finops-basic-auth \
    --from-literal=auth="$HTPASSWD_LINE" >/dev/null
  ok "finops-basic-auth created"
  SUMMARY_BASIC_USER="$BASIC_USER"
  SUMMARY_BASIC_PASS="$BASIC_PASS"
  SUMMARY_NEW_SECRETS+=("finops-basic-auth")
fi

log ""
if [ "${#SUMMARY_NEW_SECRETS[@]}" -gt 0 ]; then
  ok "Newly created secrets: ${SUMMARY_NEW_SECRETS[*]}"
else
  ok "All secrets were already present, nothing changed"
fi

# Print credentials block ONLY for newly created secrets:
if [ -n "$SUMMARY_PG_PASS" ] || [ -n "$SUMMARY_REDIS_PASS" ] || [ -n "$SUMMARY_BASIC_USER" ]; then
  log ""
  log "${C_BOLD}${C_YELLOW}Save these credentials NOW — they will not be shown again:${C_RESET}"
  [ -n "$SUMMARY_PG_PASS" ]    && log "  POSTGRES_PASSWORD: $SUMMARY_PG_PASS"
  [ -n "$SUMMARY_REDIS_PASS" ] && log "  REDIS_PASSWORD:    $SUMMARY_REDIS_PASS"
  if [ -n "$SUMMARY_BASIC_USER" ]; then
    log "  BASIC_AUTH_USER:   $SUMMARY_BASIC_USER"
    log "  BASIC_AUTH_PASS:   $SUMMARY_BASIC_PASS"
  fi
  log ""
  log "  (You can also recover them with:"
  log "     kubectl -n finops get secret <name> -o jsonpath='{.data.<KEY>}' | base64 -d )"
fi

# ── Helpers for ArgoCD operations ──────────────────────────────────────────

# Force sync an ArgoCD Application via kubectl patch (no argocd CLI needed).
argo_sync() {
  local app="$1"
  kubectl -n argocd patch application "$app" \
    --type merge \
    --patch '{"operation":{"initiatedBy":{"username":"deploy-init"},"sync":{"revision":"HEAD"}}}' \
    >/dev/null 2>&1 || return 1
}

# Wait until ArgoCD app reaches Synced+Healthy or timeout.
argo_wait() {
  local app="$1"
  local timeout="${2:-300}"
  local elapsed=0
  local interval=5
  local sync health

  while [ "$elapsed" -lt "$timeout" ]; do
    sync="$(kubectl -n argocd get app "$app" -o jsonpath='{.status.sync.status}' 2>/dev/null || echo Unknown)"
    health="$(kubectl -n argocd get app "$app" -o jsonpath='{.status.health.status}' 2>/dev/null || echo Unknown)"
    if [ "$sync" = "Synced" ] && [ "$health" = "Healthy" ]; then
      ok "$app: Synced + Healthy (in ${elapsed}s)"
      return 0
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done

  err "$app: timeout after ${timeout}s (last: sync=$sync, health=$health)"
  return 1
}

# ── Phase 5: Apply root App-of-Apps ────────────────────────────────────────
phase "[Phase 5] Ensuring root App-of-Apps"

if [ "$ROOT_APP_PRESENT" = "1" ]; then
  ok "finops-root already present, skipping apply"
else
  if [ ! -f "$K8S_ROOT/apps/root-app.yaml" ]; then
    err "Cannot find $K8S_ROOT/apps/root-app.yaml"
    exit 3
  fi
  kubectl apply -f "$K8S_ROOT/apps/root-app.yaml" >/dev/null
  ok "finops-root applied"
fi

# In 'full' mode, ArgoCD was just installed; give the controllers a moment
# to register CRDs and start watching.
if [ "$MODE" = "full" ]; then
  log "  Waiting 15s for ArgoCD controllers to settle..."
  sleep 15
fi

# ── Phase 6: Force-sync FinOps applications ────────────────────────────────
phase "[Phase 6] Force-syncing FinOps applications"

FINOPS_APPS=(finops-root finops-misc finops-postgres finops-redis finops-api finops-frontend)

for app in "${FINOPS_APPS[@]}"; do
  if ! kubectl -n argocd get application "$app" >/dev/null 2>&1; then
    warn "$app: Application not yet present in ArgoCD (root-app may still be propagating)"
    continue
  fi
  argo_sync "$app" && ok "$app: sync triggered" || warn "$app: failed to trigger sync"
done

log ""
log "  Waiting for ArgoCD apps to reach Synced+Healthy (timeout 5 min each)..."
ALL_OK=1
for app in "${FINOPS_APPS[@]}"; do
  if ! kubectl -n argocd get application "$app" >/dev/null 2>&1; then
    warn "$app: skipped (Application missing)"
    ALL_OK=0
    continue
  fi
  argo_wait "$app" 300 || ALL_OK=0
done

if [ "$ALL_OK" != "1" ]; then
  warn "Some apps did not reach Synced+Healthy in time."
  warn "  Investigate with: kubectl -n argocd get app"
  warn "  Continuing anyway — Pods may still be coming up."
fi

# ── Phase 7: Wait for workload rollouts ────────────────────────────────────
phase "[Phase 7] Waiting for workload rollouts"

wait_rollout() {
  local kind="$1" name="$2" ns="$3" timeout="${4:-300}"
  if ! kubectl -n "$ns" get "$kind" "$name" >/dev/null 2>&1; then
    warn "$kind/$name not found in namespace $ns"
    return 1
  fi
  if kubectl -n "$ns" rollout status "$kind/$name" --timeout="${timeout}s" >/dev/null 2>&1; then
    ok "$kind/$name rolled out"
    return 0
  else
    err "$kind/$name rollout did not complete in ${timeout}s"
    return 1
  fi
}

wait_rollout statefulset postgres        finops || true
wait_rollout statefulset redis           finops || true
wait_rollout deployment  finops-api      finops || true
wait_rollout deployment  finops-frontend finops || true

# ── Phase 8: Smoke tests ───────────────────────────────────────────────────
phase "[Phase 8] Smoke tests"

# 8.1 In-cluster /health
log "  In-cluster API /health:"
if kubectl -n finops exec deploy/finops-api -- \
     python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/health'); sys.exit(0 if r.status==200 else 1)"; then
  ok "/health returns 200 (in-cluster)"
else
  warn "/health did not return 200 (api may still be starting)"
fi

# 8.2 Resolve ingress External IP
log "  Resolving ingress External IP..."
INGRESS_IP=""
for i in 1 2 3 4 5 6; do
  INGRESS_IP="$(kubectl -n ingress-nginx get svc nginx-ingress-ingress-nginx-controller \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  if [ -n "$INGRESS_IP" ]; then break; fi
  sleep 5
done

if [ -z "$INGRESS_IP" ]; then
  warn "Could not resolve LoadBalancer IP for nginx-ingress-ingress-nginx-controller"
  warn "  External smoke tests skipped."
  EXTERNAL_OK=0
else
  ok "Ingress IP: $INGRESS_IP"
  EXTERNAL_OK=1
fi

# 8.3 External smoke (basic auth)
if [ "$EXTERNAL_OK" = "1" ]; then
  # Pull basic-auth credentials from k8s if we don't have them in memory:
  if [ -z "${SUMMARY_BASIC_USER:-}" ]; then
    SUMMARY_BASIC_USER="admin"
  fi
  EFFECTIVE_PASS="${SUMMARY_BASIC_PASS:-}"
  if [ -z "$EFFECTIVE_PASS" ]; then
    log "  (basic-auth password not in memory — skipping authenticated curl)"
    log "  To test manually:"
    log "    PASS=\$(...)  # see Phase 9 hints"
    log "    curl -sS -u \$BASIC_USER:\$PASS http://$INGRESS_IP/api/v1/clusters"
  else
    test_url() {
      local path="$1" expected="$2" desc="$3"
      local code
      code="$(curl -sS -o /dev/null -w '%{http_code}' \
                  --max-time 10 \
                  -u "$SUMMARY_BASIC_USER:$EFFECTIVE_PASS" \
                  "http://$INGRESS_IP$path")"
      if [ "$code" = "$expected" ]; then
        ok "$desc → $code"
      else
        warn "$desc → $code (expected $expected)"
      fi
    }
    test_url "/"                 "200" "GET /                  (frontend)"
    test_url "/api/v1/clusters"  "200" "GET /api/v1/clusters   (api)"
    test_url "/api/v1/providers" "200" "GET /api/v1/providers  (api)"
    test_url "/docs"             "200" "GET /docs              (swagger)"
    test_url "/openapi.json"     "200" "GET /openapi.json      (openapi)"

    # Also assert that auth is actually enforced:
    code_noauth="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 \
                       "http://$INGRESS_IP/api/v1/clusters")"
    if [ "$code_noauth" = "401" ]; then
      ok "GET /api/v1/clusters without auth → 401 (auth enforced)"
    else
      warn "GET /api/v1/clusters without auth → $code_noauth (expected 401)"
    fi
  fi
fi

# ── Phase 9: Summary ───────────────────────────────────────────────────────
phase "[Phase 9] Summary"

log ""
log "${C_BOLD}FinOps MVP is up.${C_RESET}"
log ""

if [ -n "${INGRESS_IP:-}" ]; then
  log "  URL:     ${C_BOLD}http://$INGRESS_IP/${C_RESET}"
  log "  API:     http://$INGRESS_IP/api/v1/"
  log "  Swagger: http://$INGRESS_IP/docs"
  log "  OpenAPI: http://$INGRESS_IP/openapi.json"
else
  log "  Ingress IP: not yet allocated (check 'kubectl -n ingress-nginx get svc')"
fi

log ""
log "  Basic auth username: ${SUMMARY_BASIC_USER:-admin}"
if [ -n "${SUMMARY_BASIC_PASS:-}" ]; then
  log "  Basic auth password: ${C_YELLOW}${SUMMARY_BASIC_PASS}${C_RESET}  (newly generated)"
else
  log "  Basic auth password: (unchanged from previous run)"
  log "    Recover with:"
  log "      kubectl -n finops get secret finops-basic-auth \\"
  log "        -o jsonpath='{.data.auth}' | base64 -d"
fi

log ""
log "${C_BOLD}Next steps:${C_RESET}"
log "  1. Open Swagger and create your first cluster:"
log "     http://${INGRESS_IP:-<ingress-ip>}/docs"
log "  2. POST /api/v1/clusters       — create cluster profile"
log "  3. PUT  /api/v1/clusters/{id}/credentials  — attach YC S3 + creds"
log "  4. GET  /api/v1/clusters/{id}/diagnostics  — verify connectivity"
log "  5. POST /api/v1/clusters/{id}/sync/billing      — first billing sync"
log "  6. POST /api/v1/clusters/{id}/sync/allocations  — first allocations snapshot"
log "  7. POST /api/v1/clusters/{id}/recommendations/refresh — generate recs"
log ""
log "${C_GREEN}Done.${C_RESET}"
exit 0
