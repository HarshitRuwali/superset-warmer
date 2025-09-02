#!/bin/bash
if [ "$(docker ps -a -q -f name=superset-warmer-dev)" ]; then
    if [ "$(docker ps -q -f name=superset-warmer-dev)" ]; then
        echo "Container superset-warmer-dev is already running."
    else
        echo "Starting existing container superset-warmer-dev."
        docker start superset-warmer-dev
    fi
else
    docker run -it --name superset-warmer-dev -v $(pwd):/app superset-warmer > output.log 2>&1
fi
