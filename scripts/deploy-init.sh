#!/bin/bash
# Первичный деплой: создаём namespace + secret + ArgoCD apps
set -e

REGISTRY_ID=${1:-"crppm2p2j5q3tmf17su4"}

echo "=== 1. Replacing REGISTRY_ID in manifests ==="
find k8s/ -name "*.yaml" -exec   sed -i '' "s/REGISTRY_ID/${REGISTRY_ID}/g" {} \;

echo "=== 2. Creating namespace ==="
kubectl apply -f k8s/namespace.yaml

echo "=== 3. Creating secret (YC credentials) ==="
read -p "YC_ACCESS_KEY: " YC_ACCESS_KEY
read -s -p "YC_SECRET_KEY: " YC_SECRET_KEY
echo ""

kubectl create secret generic finops-api-secret   -n finops   --from-literal=YC_ACCESS_KEY="${YC_ACCESS_KEY}"   --from-literal=YC_SECRET_KEY="${YC_SECRET_KEY}"   --dry-run=client -o yaml | kubectl apply -f -

echo "=== 4. Applying K8s manifests ==="
kubectl apply -f k8s/api/
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/ingress.yaml

echo "=== 5. Registering ArgoCD Applications ==="
kubectl apply -f k8s/argocd/

echo "=== 6. Ingress for services ==="
kubectl apply -f k8s/ingress.yaml

echo "=== Done! ==="
echo "ArgoCD will now watch the repo and keep cluster in sync."
echo ""
echo "Check status:"
echo "  kubectl get pods -n finops"
echo "  kubectl get applications -n argocd"
