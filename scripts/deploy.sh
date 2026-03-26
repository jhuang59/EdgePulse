#!/bin/bash
set -e

IMAGE="${IMAGE:-ghcr.io/jhuang59/edgepulse:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-edgepulse}"
DATA_DIR="${DATA_DIR:-./data}"
PORT="${PORT:-5000}"

# Pull latest image
docker pull "$IMAGE"

# Stop existing container if running
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Run new container
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p "$PORT:5000" \
  -v "$DATA_DIR:/app/data" \
  "$IMAGE"

echo "Deployed $IMAGE as $CONTAINER_NAME on port $PORT"
