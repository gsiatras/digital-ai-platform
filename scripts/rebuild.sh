#!/bin/bash
# Rebuild and deploy a service image to minikube (ARM-safe, linux/amd64 forced)
# Usage: ./scripts/rebuild.sh <service> [<node>...]
#
# Examples:
#   ./scripts/rebuild.sh ui              -> rebuilds ui_service, loads into minikube (node1)
#   ./scripts/rebuild.sh manager         -> rebuilds manager_service, loads into minikube (node1)
#   ./scripts/rebuild.sh worker          -> rebuilds worker_service, loads into all worker nodes
#   ./scripts/rebuild.sh worker m02 m03  -> loads only into specified nodes

set -e

export PATH="$HOME/bin:$PATH"

SERVICE=$1
if [ -z "$SERVICE" ]; then
    echo "Usage: $0 <ui|manager|worker> [node...]"
    exit 1
fi

TAG="gsiatras13/digital_platform-${SERVICE}_service:a1.1"
CONTEXT=""
RESTART_CMD=""

case "$SERVICE" in
  ui)
    CONTEXT="ui_service"
    NODES=("minikube")
    RESTART_CMD="kubectl rollout restart deployment/ui-deployment -n platform"
    ;;
  manager)
    CONTEXT="manager_service"
    NODES=("minikube")
    RESTART_CMD="kubectl rollout restart statefulset/manager-service -n platform && kubectl delete pod manager-service-0 -n platform --force 2>/dev/null || true"
    ;;
  worker)
    CONTEXT="worker_service"
    if [ $# -gt 1 ]; then
        shift
        NODES=("$@")
    else
        NODES=("minikube-m02" "minikube-m03" "minikube-m04")
    fi
    RESTART_CMD="kubectl delete pod worker-a-0 worker-b-0 worker-c-0 -n platform --force 2>/dev/null || true"
    ;;
  *)
    echo "Unknown service: $SERVICE. Use ui, manager, or worker."
    exit 1
    ;;
esac

BUILD_DIR="$(dirname "$0")/../${CONTEXT}"

echo "==> Building $TAG for linux/amd64..."
docker buildx build --platform linux/amd64 --load -t "$TAG" "$BUILD_DIR"

IMAGE_ID=$(docker inspect --format '{{.Id}}' "$TAG")
echo "==> Built image ID: $IMAGE_ID"

for NODE in "${NODES[@]}"; do
    echo "==> Loading into $NODE..."
    LOADED_ID=$(docker save "$IMAGE_ID" | minikube ssh -n "$NODE" --native-ssh=false "docker load" 2>&1 | grep "Loaded image ID" | awk '{print $NF}')
    if [ -n "$LOADED_ID" ]; then
        minikube ssh -n "$NODE" "docker tag $LOADED_ID $TAG"
        ARCH=$(minikube ssh -n "$NODE" "docker inspect $TAG --format '{{.Architecture}}'")
        echo "    $NODE: $ARCH OK"
    else
        echo "    $NODE: already present or tag not needed"
        minikube ssh -n "$NODE" "docker inspect $TAG --format '    arch={{.Architecture}}'" 2>/dev/null || true
    fi
done

echo "==> Restarting pods..."
eval "$RESTART_CMD"
echo "==> Done. Run: kubectl get pods -n platform"
