#!/bin/bash

# Ensure Docker containers are always stopped at end of test regardless of success or failure
cleanup() {
  echo "Cleaning up..."
  docker-compose down >/dev/null 2>&1 || echo "Warning: docker-compose down failed"
  
  # Restore original .env file if backup exists
  if [ -f .env.backup ]; then
    mv .env.backup .env
    echo "Restored original .env file"
  fi
  
  # Deactivate virtual environment if active
  if [ ! -z "$VIRTUAL_ENV" ]; then
    deactivate
    echo "Virtual environment deactivated."
  fi
  
  echo "Cleanup completed."
}

# Execute cleanup when script exits for any reason
# trap cleanup EXIT

# Colors for better output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Main function
main() {
  echo -e "${YELLOW}Starting test of Logstash Syslog Server to Elasticsearch setup...${NC}"

  # Check if --logsdb flag is provided (simpler approach)
  USE_LOGSDB=false
  for arg in "$@"; do
    if [ "$arg" = "--logsdb" ]; then
      USE_LOGSDB=true
      break
    fi
  done

  # Function to check if a command exists
  command_exists() {
    command -v "$1" >/dev/null 2>&1
  }

  # Check prerequisites
  echo "Checking prerequisites..."
  for cmd in docker docker-compose curl; do
    if ! command_exists $cmd; then
      echo -e "${RED}Error: $cmd is not installed. Please install it and try again.${NC}"
      exit 1
    fi
  done

  # Check if python3 or python is available
  if command_exists python3; then
    PYTHON_CMD="python3"
  elif command_exists python; then
    PYTHON_CMD="python"
  else
    echo -e "${RED}Error: Neither python3 nor python is installed. Please install Python and try again.${NC}"
    exit 1
  fi
  echo -e "${GREEN}Using Python command: $PYTHON_CMD${NC}"

  # Check if .env file exists and has required variables
  echo "Checking environment variables..."
  if [ ! -f .env ]; then
    if [ -f .env.example ]; then
      echo "Creating .env file from .env.example for testing..."
      cp .env.example .env
      echo "You'll need to update the .env file with your actual credentials before the test will pass."
    else
      echo -e "${RED}Error: .env file not found and no .env.example to copy from.${NC}"
      exit 1
    fi
  fi

  # Source environment variables
  source .env
  if [[ -z "$ES_ENDPOINT" || -z "$ELASTIC_LOGSTASH_API_KEY" || -z "$ELASTIC_ADMIN_API_KEY" ]]; then
    echo -e "${RED}Error: Required environment variables not set in .env file.${NC}"
    echo "Please set ES_ENDPOINT, ELASTIC_LOGSTASH_API_KEY, and ELASTIC_ADMIN_API_KEY"
    exit 1
  fi
  
  # Set default port if not specified, based on protocol
  if [[ -z "$ES_PORT" ]]; then
    # Use simple string matching to check for HTTPS
    if [[ "$ES_ENDPOINT" =~ ^https:// ]]; then
      echo "ES_PORT not set, defaulting to 443 for HTTPS"
      ES_PORT=443
    else
      echo "ES_PORT not set, defaulting to 9200 for HTTP"
      ES_PORT=9200
    fi
  fi
  
  # Construct full Elasticsearch URL with port
  ES_URL="${ES_ENDPOINT}:${ES_PORT}"
  
  echo -e "${GREEN}Environment variables are set.${NC}"

  # Set namespace based on logsdb mode
  if [ "$USE_LOGSDB" = true ]; then
    NAMESPACE="logsdb"
    LOGSDB_ARG="--logsdb"
    echo -e "${GREEN}Using LogsDB mode with namespace '$NAMESPACE'${NC}"
  else
    NAMESPACE="default" 
    LOGSDB_ARG=""
    echo -e "${GREEN}Using standard mode with namespace '$NAMESPACE'${NC}"
  fi
  
  # Create a temporary .env file with the correct namespace
  if [ -f .env ]; then
    # Create a backup of the original .env file
    cp .env .env.backup
    # Remove existing ES_DATA_STREAM_NAMESPACE line if it exists
    grep -v "^ES_DATA_STREAM_NAMESPACE=" .env > .env.temp
    # Add the new namespace variable
    echo "ES_DATA_STREAM_NAMESPACE=$NAMESPACE" >> .env.temp
    # Replace the original .env file
    mv .env.temp .env
    echo "Updated .env file with namespace: $NAMESPACE"
  else
    echo -e "${RED}Error: .env file not found.${NC}"
    exit 1
  fi

  # Run the setup script which will create the virtual environment
  echo "Running setup script..."
  ./setup.sh

  # Activate the virtual environment
  echo "Activating Python virtual environment..."
  source venv/bin/activate

  # Verify the virtual environment is activated
  if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${RED}Error: Failed to activate virtual environment.${NC}"
    exit 1
  fi
  echo -e "${GREEN}Virtual environment activated: $(basename $VIRTUAL_ENV)${NC}"

  # Check if the data stream setup script exists
  if [ ! -f setup_datastream.py ]; then
    echo -e "${RED}Error: setup_datastream.py not found.${NC}"
    exit 1
  fi
  
  # Run the data stream setup script with the appropriate namespace
  echo "Setting up Elasticsearch data stream with namespace $NAMESPACE..."
  python setup_datastream.py --namespace $NAMESPACE $LOGSDB_ARG

  # Start the containers
  echo "Starting Docker containers..."
  docker-compose --env-file .env up -d

  # Wait for Logstash to start processing
  echo "Waiting for Logstash to initialize (30 seconds)..."
  sleep 30

  # Check if services are running
  if ! docker-compose ps | grep -q "logstash.*Up"; then
    echo -e "${RED}Error: Logstash container is not running.${NC}"
    docker-compose logs logstash
    exit 1
  fi
  
  # Check if log-sender container started
  if ! docker-compose ps | grep -q "log-sender"; then
    echo -e "${RED}Error: Log-sender container did not start.${NC}"
    exit 1
  fi

  # Monitor log processing
  echo "Monitoring log processing progress..."
  MAX_WAIT=60  # 60 seconds max wait time
  start_time=$(date +%s)
  processed_lines=0
  
  # Construct the data stream name
  DATA_STREAM="logs-syslog-${NAMESPACE}"
  
  echo ""
  echo "┌─────────────────────────────────────────────────────────────────┐"
  echo "│                 ELASTICSEARCH QUERY INFORMATION                  │"
  echo "├─────────────────────────────────────────────────────────────────┤"
  echo "│ Elasticsearch URL:      $ES_URL"
  echo "│ Data stream:            $DATA_STREAM"
  echo "│ Using LogsDB mode:      $USE_LOGSDB"
  echo "└─────────────────────────────────────────────────────────────────┘"
  echo ""

  # Get the log line count from log-sender
  echo "Checking if logs are being ingested..."
  
  # Wait for log-sender to start sending logs
  sleep 10
  
  # Monitor log count with the test script
  python test_count_logs.py --namespace $NAMESPACE --watch --interval 10 --minutes 5
  
  # Final check for log count
  echo "Performing final log count check..."
  final_count=$(python test_count_logs.py --namespace $NAMESPACE | grep -o "Log count for.*: [0-9]*" | awk '{print $NF}')
  
  # Check if we have logs
  if [[ "$final_count" =~ ^[0-9]+$ ]] && [ "$final_count" -gt 0 ]; then
    echo -e "${GREEN}Test PASSED: Successfully ingested $final_count logs into Elasticsearch${NC}"
    TEST_RESULT="PASSED"
  else
    echo -e "${RED}Test FAILED: No logs were ingested into Elasticsearch${NC}"
    TEST_RESULT="FAILED"
  fi
  
  # Generate a test report
  echo "Generating test report..."
  cat > test_report.md << EOF
# Logstash Syslog Server to Elasticsearch Test Report

Test conducted on: $(date)

## Summary
- Test result: $TEST_RESULT
- Data stream: $DATA_STREAM
- LogsDB mode: $USE_LOGSDB
- Log lines ingested: $final_count

## Environment
- Docker version: $(docker --version)
- Docker Compose version: $(docker-compose --version)
- Python version: $($PYTHON_CMD --version)
- Elasticsearch URL: $ES_URL

## Container Status
\`\`\`
$(docker-compose ps)
\`\`\`

## Logstash Logs
\`\`\`
$(docker-compose logs --tail=20 logstash)
\`\`\`

## Log Sender Logs
\`\`\`
$(docker-compose logs --tail=20 log-sender)
\`\`\`
EOF
  
  echo -e "${YELLOW}Test report generated: test_report.md${NC}"
  echo -e "${GREEN}Test completed!${NC}"
}

# Call the main function
main "$@"