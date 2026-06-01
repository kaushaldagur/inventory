#!/bin/sh
# Build and push backend image to Docker Hub.
# Usage: sh scripts/publish-docker.sh YOUR_DOCKERHUB_USERNAME [tag]
set -e

USER="${1:?Usage: sh scripts/publish-docker.sh DOCKERHUB_USERNAME [tag]}"
TAG="${2:-latest}"
IMAGE="${USER}/inventory-backend:${TAG}"

echo "Building ${IMAGE}..."
docker build -t "${IMAGE}" ./backend

if [ "${TAG}" = "latest" ]; then
  docker tag "${IMAGE}" "${USER}/inventory-backend:1.0.0"
fi

echo "Logging in to Docker Hub (if needed)..."
docker login

echo "Pushing ${IMAGE}..."
docker push "${IMAGE}"

if [ "${TAG}" = "latest" ]; then
  docker push "${USER}/inventory-backend:1.0.0"
fi

echo ""
echo "Done."
echo "Docker Hub: https://hub.docker.com/r/${USER}/inventory-backend"
echo "Pull: docker pull ${IMAGE}"
