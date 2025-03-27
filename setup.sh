#!/bin/bash

# Exit on error
set -e

echo "=========================================="
echo "  Logstash Syslog Server Setup            "
echo "=========================================="

# Create required directories
echo "Creating directory structure..."
mkdir -p logstash/pipeline logstash/secrets logs archive

# Create logstash.yml if it doesn't exist
if [ ! -f logstash.yml ]; then
    cat > logstash.yml << EOF
http.host: 0.0.0.0
log.level: info
path.config: /usr/share/logstash/pipeline
config.reload.automatic: true
config.reload.interval: 30s
pipeline.batch.delay: 50
pipeline.batch.size: 125
pipeline.workers: 2
EOF
    echo "Created logstash.yml"
fi

# Verify syslog server configuration exists
if [ ! -f logstash/pipeline/syslog-server.conf ]; then
    echo "ERROR: logstash/pipeline/syslog-server.conf not found."
    echo "Please ensure this file exists before continuing."
    exit 1
fi

# Verify log-sender files exist
if [ ! -d log-sender ] || [ ! -f log-sender/Dockerfile ]; then
    echo "ERROR: log-sender directory or Dockerfile not found."
    echo "Please ensure the log-sender directory is set up correctly."
    exit 1
fi

# Make entrypoint script executable
if [ -f log-sender/entrypoint.sh ]; then
    chmod +x log-sender/entrypoint.sh
    echo "Made log-sender/entrypoint.sh executable."
fi

# Create a Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    
    # Try python3 first, then fall back to python
    if command -v python3 &>/dev/null; then
        python3 -m venv venv
    elif command -v python &>/dev/null; then
        python -m venv venv
    else
        echo "ERROR: Neither python3 nor python is available. Please install Python."
        exit 1
    fi
    
    # Activate the virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "Python virtual environment created and dependencies installed."
else
    echo "Python virtual environment already exists."
    # Activate the virtual environment
    source venv/bin/activate
    
    # Check if requirements need updating
    echo "Checking Python dependencies..."
    pip install --upgrade -r requirements.txt
fi

# Create .env file from example if it doesn't exist
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo "Created .env file from .env.example."
    echo "IMPORTANT: Update the .env file with your actual credentials before proceeding."
fi

# Ensure proper permissions
if [ -f .env ]; then
    chmod 600 .env
    echo "Set secure permissions on .env file."
else
    echo "WARNING: .env file not found. Create it before running docker-compose."
fi

# Create secrets directory with proper permissions
mkdir -p logstash/secrets
chmod 700 logstash/secrets
echo "Set secure permissions on logstash/secrets directory."

# Make test_syslog_server.py executable
if [ -f test_syslog_server.py ]; then
    chmod +x test_syslog_server.py
    echo "Made test_syslog_server.py executable."
fi

# Make setup_datastream.py executable
if [ -f setup_datastream.py ]; then
    chmod +x setup_datastream.py
    echo "Made setup_datastream.py executable."
fi

# Final instructions
echo ""
echo "Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Ensure your .env file is configured with proper Elasticsearch credentials"
echo "2. Run 'python setup_datastream.py' to configure the Elasticsearch data stream"
echo "3. Start the system by running: docker-compose up -d"
echo "4. Monitor the logs with: docker-compose logs -f"
echo ""
echo "Or run the test script with: python test_syslog_server.py [--log-type windows|linux|mac|all] [--logsdb]"
echo ""
echo "For more information, refer to the README.md file."