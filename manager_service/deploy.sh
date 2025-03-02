#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Build the Docker image
docker build -t digital_platform-manager_service .

# Tag the image
docker tag digital_platform-manager_service gsiatras13/digital_platform-manager_service:a1.1

# Push the image to Docker Hub
docker push gsiatras13/digital_platform-manager_service:a1.1

# Restart the StatefulSet in Kubernetes
kubectl rollout restart statefulset/manager-service -n platform

echo "Deployment completed successfully!"
