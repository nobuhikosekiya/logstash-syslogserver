#!/bin/bash

# Make script exit on error and enable debug output
set -e
set -x

echo "=========================================="
echo "Starting log sender container with DEBUG enabled"
echo "=========================================="

# Print all environment variables for debugging
echo "ENVIRONMENT VARIABLES:"
env | sort

# Explicitly check LOG_TYPE and set default if not defined
if [ -z "$LOG_TYPE" ]; then
    echo "WARNING: LOG_TYPE is not set, defaulting to 'all'"
    LOG_TYPE="all"
fi

echo "Using LOG_TYPE: $LOG_TYPE"

# Create required directories
mkdir -p /logs
mkdir -p /archive

# Check if we need to download log files
if [ "$DOWNLOAD_LOGS" = "true" ]; then
    echo "Downloading log files for LOG_TYPE: $LOG_TYPE"
    
    # Call download_logs.py with explicit log-type parameter and archive directory
    python /app/download_logs.py --log-type "$LOG_TYPE" --output-dir "/logs" --archive-dir "/archive"
    
    # Verify download results
    echo "Contents of /logs directory after download:"
    ls -la /logs
    echo "Contents of /archive directory:"
    ls -la /archive
else
    echo "Skipping log download (DOWNLOAD_LOGS=$DOWNLOAD_LOGS)"
fi

# Check if we need to loop through the logs
if [ "$LOOP_LOGS" = "true" ]; then
    LOOP_FLAG="--loop"
else
    LOOP_FLAG=""
fi

# The netcat check is no longer needed as Docker Compose will handle service dependencies
echo "Logstash service should be ready. Starting log sender..."

python /app/send_logs.py --host "${LOGSTASH_HOST}" --port "${LOGSTASH_PORT}" \
                        --log-dir "/logs" --interval "${LOG_SEND_INTERVAL}" \
                        --protocol "${PROTOCOL}" ${LOOP_FLAG}

# Keep container running if specified
if [ "$KEEP_RUNNING" = "true" ]; then
    echo "Log sending completed. Keeping container running..."
    tail -f /dev/null
else
    echo "Log sending completed. Container will exit."
fi