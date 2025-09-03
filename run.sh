#!/bin/bash
set -euo pipefail

CONTAINER_NAME="superset-warmer-dev"
IMAGE_NAME="superset-warmer"
BASE_FOLDER=${BASE_FOLDER:-/home/ubuntu/superset-warmer}
LOG_DIR="$BASE_FOLDER/logs"
# Keep logs for N days
LOG_RETENTION_DAYS=${LOG_RETENTION_DAYS:-14}

# Timestamp for this run (local time)
RUN_TS=$(date +%F_%H-%M-%S)
LOG_FILE="$LOG_DIR/output-$RUN_TS.log"
LATEST_LINK="$LOG_DIR/latest.log"

mkdir -p "$LOG_DIR"

# Clean up any old container with same name
if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

# Start a fresh container (detached)
docker run -d --rm --name "$CONTAINER_NAME" -v "$BASE_FOLDER":/app "$IMAGE_NAME" >/dev/null

# Stream logs until container exits
# Use tee to write both the timestamped file and a latest file
# pipefail ensures we get the exit code properly
docker logs -f "$CONTAINER_NAME" | tee "$LOG_FILE" > "$LATEST_LINK"

# Capture exit code (if container already auto-removed, default to 0)
EXIT_CODE=$(docker inspect "$CONTAINER_NAME" --format='{{.State.ExitCode}}' 2>/dev/null || echo 0)

# Optional: compress the finished log (saves space)
if command -v gzip >/dev/null 2>&1; then
  gzip -f "$LOG_FILE"
  LOG_FILE="$LOG_FILE.gz"
fi

# Retention: delete old logs older than N days
find "$LOG_DIR" -type f -name 'output-*.log*' -mtime +$LOG_RETENTION_DAYS -print -delete || true

exit "$EXIT_CODE"
