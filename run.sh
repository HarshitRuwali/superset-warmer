#!/bin/bash
set -e

CONTAINER_NAME="superset-warmer-dev"
IMAGE_NAME="superset-warmer"

# Always remove old container if it exists
if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
    docker rm -f $CONTAINER_NAME > /dev/null 2>&1 || true
fi

# Run new container, mount current dir so it sees code/config
docker run --rm --name $CONTAINER_NAME -v $(pwd):/app $IMAGE_NAME > output.log 2>&1
