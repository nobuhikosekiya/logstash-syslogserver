# Logstash Syslog Server with Elasticsearch Data Stream Integration

This project sets up a complete system to:
1. Run Logstash as a syslog server (listening on TCP and UDP port 5514)
2. Collect and process syslog messages
3. Store the data in Elasticsearch using data streams
4. Include test scripts to verify data ingestion

## Architecture

- **Logstash Container**: Runs the syslog server and processes logs
- **Log Sender Container**: Downloads sample logs and sends them to Logstash via syslog protocol
- **Elasticsearch**: External service that stores the processed logs in a data stream

## Prerequisites

- Docker and Docker Compose installed
- Elasticsearch deployment (cloud or self-hosted) with API key access
- Python 3.6+ (for setup scripts and testing)

## Quick Start

1. **Clone this repository**
   ```bash
   git clone https://github.com/yourusername/logstash-syslog-elasticsearch.git
   cd logstash-syslog-elasticsearch
   ```

2. **Run the setup script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Edit your .env file**
   ```bash
   # Update with your Elasticsearch details
   nano .env
   ```

4. **Set up the Elasticsearch data stream**
   ```bash
   source venv/bin/activate
   python setup_datastream.py
   ```

5. **Start the services**
   ```bash
   docker-compose up -d
   ```

6. **Monitor the logs**
   ```bash
   docker-compose logs -f
   ```

7. **Verify log ingestion**
   ```bash
   python test_count_logs.py --watch
   ```

## Configuration Details

### Environment Variables

Edit the `.env` file to configure the system:

```
# Elasticsearch connection settings
ES_ENDPOINT="https://your-es-endpoint.cloud.es.io"
ES_PORT=443
ELASTIC_LOGSTASH_API_KEY="your_logstash_api_key_here"
ELASTIC_ADMIN_API_KEY="your_admin_api_key_here"

# Log sender configuration
DOWNLOAD_LOGS=true
LOG_SEND_INTERVAL=0.01
PROTOCOL=tcp
LOOP_LOGS=false
KEEP_RUNNING=false
```

#### Important Notes on Environment Variables

- Docker Compose will automatically load variables from the `.env` file when in the same directory
- To ensure proper loading, always use `docker-compose --env-file .env` when running manually
- The `ELASTIC_LOGSTASH_API_KEY` is used by Logstash to write to Elasticsearch
- The `ELASTIC_ADMIN_API_KEY` is used by setup scripts to manage index templates and data streams
- Both API keys should have appropriate permissions in Elasticsearch:
  - `ELASTIC_LOGSTASH_API_KEY`: write access to logs indices and data streams
  - `ELASTIC_ADMIN_API_KEY`: manage index templates and data streams


### Customizing Logstash Pipeline

The Logstash pipeline is defined in `logstash/pipeline/syslog.conf`. You can modify this file to customize how logs are processed before being sent to Elasticsearch.

### Data Stream Configuration

The data stream is set up using the `setup_datastream.py` script. By default, it creates a data stream with:
- Type: `logs`
- Dataset: `syslog`
- Namespace: `default`

The resulting data stream name is `logs-syslog-default`.

You can customize these values:
```bash
python setup_datastream.py --namespace production
```

### LogsDB Mode

This setup supports Elasticsearch's LogsDB mode, which is optimized for logs storage. To enable LogsDB mode:

```bash
python setup_datastream.py --logsdb
```

When LogsDB mode is enabled, the namespace is automatically set to `logsdb` and the index settings are configured with:
```json
"index": {
    "mode": "logsdb",
    "codec": "best_compression"
}
```

Without LogsDB mode, the index settings still use best compression:
```json
"index": {
    "codec": "best_compression"
}
```

## Testing

You can test the system by monitoring log ingestion using the provided test scripts:

```bash
# Basic count
python test_count_logs.py

# Watch mode (updates every 5 seconds)
python test_count_logs.py --watch

# Count logs from last hour only
python test_count_logs.py --minutes 60

# Use custom namespace
python test_count_logs.py --namespace production
```

## Using the Test Script

The `test_syslog_server.sh` script provides an automated way to test the entire pipeline from Logstash syslog ingestion to Elasticsearch data storage. It handles setup, running containers, and verification of log ingestion.

### Prerequisites for Testing

- Ensure your `.env` file is properly configured with Elasticsearch credentials
- Make sure Docker and Docker Compose are running
- Set executable permissions: `chmod +x test_syslog_server.sh`

### Running the Test

1. **Standard Mode**:
   ```bash
   ./test_syslog_server.sh
   ```
   This will:
   - Run setup and create required directories
   - Configure the data stream with namespace "default"
   - Start Logstash and log-sender containers
   - Monitor log ingestion for 5 minutes
   - Generate a test report in test_report.md

2. **LogsDB Mode**:
   ```bash
   ./test_syslog_server.sh --logsdb
   ```
   This adds LogsDB mode optimization to Elasticsearch indices:
   - Sets namespace to "logsdb"
   - Configures index settings for LogsDB mode
   - All other test steps remain the same

### Test Results

The script will:
- Display real-time log count updates
- Show a final success/failure message
- Generate a detailed test report in `test_report.md`
- Clean up containers after test completion

### Troubleshooting Failed Tests

If the test fails:
1. Check the test_report.md for error details
2. Verify Elasticsearch connection settings in .env
3. Ensure Logstash has proper permissions to write to Elasticsearch
4. Check Docker logs: `docker-compose logs logstash`
5. Verify network connectivity to Elasticsearch

### Running Multiple Tests

If you want to test different configurations sequentially:
```bash
# Test standard mode first
./test_syslog_server.sh

# Then test LogsDB mode
./test_syslog_server.sh --logsdb

# Compare the test reports
diff test_report.md test_report_logsdb.md  # Will need to rename reports between tests
```


## Log Sender Configuration

The log sender container has several configurable options through environment variables in the .env file:

- `DOWNLOAD_LOGS`: Whether to download sample logs (true/false)
- `LOG_SEND_INTERVAL`: Delay between sending log entries (seconds)
- `PROTOCOL`: Syslog protocol to use (tcp/udp)
- `LOOP_LOGS`: Continuously loop through logs (true/false)
- `KEEP_RUNNING`: Keep container running after sending logs (true/false)

## Directory Structure

```
.
├── docker-compose.yml               # Docker Compose configuration
├── .env                             # Environment variables (created from .env.example)
├── .env.example                     # Example environment variables
├── logstash/                        # Logstash configuration
│   ├── config/                      # Logstash main configuration
│   │   └── logstash.yml             # Logstash settings
│   └── pipeline/                    # Logstash pipeline configurations
│       └── syslog.conf              # Syslog server configuration
├── log-sender/                      # Log sender container files
│   ├── Dockerfile                   # Container definition
│   ├── download_logs.py             # Script to download sample logs
│   ├── send_logs.py                 # Script to send logs to syslog server
│   ├── entrypoint.sh                # Container entrypoint script
│   └── requirements.txt             # Python dependencies
├── logs/                            # Directory for log files
├── setup_datastream.py              # Script to set up Elasticsearch data stream
├── test_count_logs.py               # Script to test log ingestion
├── setup.sh                         # Setup script
└── README.md                        # This file
```

## Troubleshooting

### Common Issues

1. **No logs appearing in Elasticsearch**
   - Check Logstash logs: `docker-compose logs logstash`
   - Verify Elasticsearch connection details in `.env`
   - Ensure data stream was created: `python setup_datastream.py`

2. **Log-sender container exits immediately**
   - Check logs: `docker-compose logs log-sender`
   - Verify if Logstash is running and ready
   - Set `KEEP_RUNNING=true` in `.env` to keep container running for debugging

3. **Logstash errors**
   - Check Logstash logs: `docker-compose logs logstash`
   - Verify your Elasticsearch API key has proper permissions
   - Check SSL/TLS settings match your Elasticsearch deployment

### Data Stream Issues

If you're having trouble with the data stream:

```bash
# Delete and recreate it
python setup_datastream.py --type logs --dataset syslog --namespace default

# Check if it exists
python test_count_logs.py
```

## Using Your Own Log Files

To use your own log files instead of downloading sample logs:

1. Set `DOWNLOAD_LOGS=false` in `.env`
2. Place your log files in the `logs/` directory (ensure they end with `.log`)
3. Restart the log-sender container: `docker-compose restart log-sender`

## Security Considerations

- The `.env` file contains sensitive credentials - keep it secure and excluded from version control
- API keys should have the minimum required permissions
- Consider using a dedicated Elasticsearch role for Logstash with limited privileges
- For production use, enable SSL/TLS for Logstash inputs

## License

This project is licensed under the MIT License - see the LICENSE file for details.