#!/bin/bash
set -e

REPO_URL="${1:-https://github.com/mityay36/finops-mvp}"
echo "Bootstrap FinOps MVP → $REPO_URL"

# 1. Prometheus Operator CRDs
echo "[1/5] Installing Prometheus Operator CRDs..."
helm upgrade --install prometheus-operator-crds \
  oci://ghcr.io/prometheus-community/charts/prometheus-operator-crds \
  --namespace kube-system --wait --version 27.0.0

# 2. ArgoCD
echo "[2/5] Installing ArgoCD..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=120s deployment/argocd-server -n argocd

# 3. Регистрируем OCI репозитории в ArgoCD
echo "[3/5] Registering OCI repositories..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: vmks-helm-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: helm
  name: victoriametrics
  url: ghcr.io/victoriametrics/helm-charts
  enableOCI: "true"
---
apiVersion: v1
kind: Secret
metadata:
  name: opencost-helm-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: helm
  name: opencost
  url: ghcr.io/opencost/charts
  enableOCI: "true"
EOF

# 4. Регистрируем Git репозиторий
echo "[4/5] Registering Git repository: $REPO_URL"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: finops-mvp-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: git
  url: $REPO_URL
EOF

# 5. Применяем root App-of-Apps
echo "[5/5] Applying root App-of-Apps..."
kubectl apply -f apps/root-app.yaml

echo ""
echo "Bootstrap complete!"
echo "ArgoCD password: $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
echo "Port-forward: kubectl port-forward svc/argocd-server -n argocd 8080:443"
