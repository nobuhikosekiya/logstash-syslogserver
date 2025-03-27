### LogsDB Mode

For optimized log storage in Elasticsearch, you can enable LogsDB mode:

```bash
python test_syslog_server.py --log-type linux --logsdb
```

This configures Elasticsearch indices with LogsDB-specific settings that optimize storage and query performance for logs.# Logstash Syslog Server with Elasticsearch Data Stream Integration

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

## Using the Test Script

The quickest way to test the entire setup is to use the provided test script:

```bash
python test_syslog_server.py --log-type linux --logsdb
```

This will:
- Set up everything automatically
- Configure Elasticsearch with the appropriate data stream
- Process Linux logs specifically (options: windows, linux, mac, all)
- Use LogsDB mode for Elasticsearch (optional)
- Monitor log ingestion until all logs are successfully ingested
- Automatically stop when all logs have been indexed

The test script includes automatic verification that all logs have been properly ingested before finishing.

## Configuration Options

### Log Type Selection

The system supports filtering logs by type using the `--log-type` option:

```bash
# Test with Windows logs only
python test_syslog_server.py --log-type windows

# Test with Linux logs only
python test_syslog_server.py --log-type linux

# Test with Mac logs only
python test_syslog_server.py --log-type mac

# Test with all logs (default)
python test_syslog_server.py --log-type all
```

The log type selection determines which log files are sent to Logstash, but the log counting will include all logs in the data stream regardless of type.

### Additional Options

```bash
# Skip cleanup after test (for debugging)
python test_syslog_server.py --no-cleanup

# Enable additional debug output
python test_syslog_server.py --debug
```

## Environment Variables

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
LOG_TYPE=all
```

## Customizing Logstash Pipeline

The Logstash pipeline is defined in `logstash/pipeline/syslog-server.conf`. You can modify this file to customize how logs are processed before being sent to Elasticsearch.

## Monitoring Log Ingestion

You can use the `test_count_logs.py` script to monitor log ingestion:

```bash
# Basic count of all logs in the data stream
python test_count_logs.py

# Watch mode with automatic stopping
python test_count_logs.py --watch --auto-stop

# Watch with custom interval and timeout
python test_count_logs.py --watch --auto-stop --interval 2 --timeout 600

# List all available data streams
python test_count_logs.py --list-streams
```

The `--auto-stop` feature will:
1. Count the log lines in source files to determine the expected count
2. Monitor log ingestion in real-time
3. Automatically stop when the log count matches the expected number
4. Timeout after a specified duration (default: 300 seconds)

This is particularly useful in automated testing scenarios where you want to verify that all logs have been correctly ingested into Elasticsearch.

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
python setup_datastream.py --namespace default-linux

# Check if it exists
python test_count_logs.py --list-streams
```

## Security Considerations

- The `.env` file contains sensitive credentials - keep it secure and excluded from version control
- API keys should have the minimum required permissions
- Consider using a dedicated Elasticsearch role for Logstash with limited privileges
- For production use, enable SSL/TLS for Logstash inputs

## Storage Optimization Options

This system offers two primary ways to optimize log storage in Elasticsearch:

### 1. LogsDB Mode

For optimized log storage in Elasticsearch, you can enable LogsDB mode:

```bash
python test_syslog_server.py --log-type linux --logsdb
```

This configures Elasticsearch indices with LogsDB-specific settings that optimize storage and query performance for logs.

### 2. Drop event.original Field

To reduce storage requirements further, you can configure Logstash to drop the `event.original` field:

```bash
python test_syslog_server.py --drop-event-original
```

The `event.original` field typically contains a copy of the original raw message, which can significantly increase storage requirements. Dropping this field can lead to substantial storage savings, especially with high-volume log ingestion.

You can combine both options for maximum storage efficiency:

```bash
python test_syslog_server.py --log-type linux --logsdb --drop-event-original
```

### Additional Environment Variables

You can also set these options directly in your `.env` file:

```
# Enable LogsDB mode
ES_DATA_STREAM_NAMESPACE=logsdb

# Drop event.original field
DROP_EVENT_ORIGINAL=true
```

## Storage Optimization Options

This system offers several ways to optimize log storage in Elasticsearch:

### 1. LogsDB Mode

For optimized log storage in Elasticsearch, you can enable LogsDB mode:

```bash
python test_syslog_server.py --log-type linux --logsdb
```

This configures Elasticsearch indices with LogsDB-specific settings that optimize storage and query performance for logs.

### 2. Optimizing the event.original Field

The `event.original` field contains a copy of the original raw message and can significantly increase storage requirements. You have two options to optimize this:

#### Option A: Change event.original to keyword type (Default)

By default, the system will map `event.original` as a `keyword` type instead of `text`. This reduces storage requirements and improves query performance while keeping the original message data available.

No additional configuration is needed for this option as it's the default behavior.

#### Option B: Drop event.original field entirely

For maximum storage savings, you can configure Logstash to drop the `event.original` field completely:

```bash
python test_syslog_server.py --drop-event-original
```

This option will save the most space but means you won't have access to the full original message.

### Combined Optimizations

You can combine all optimizations for maximum storage efficiency:

```bash
python test_syslog_server.py --log-type linux --logsdb --drop-event-original
```

### Environment Variables

You can also set these options directly in your `.env` file:

```
# Enable LogsDB mode
ES_DATA_STREAM_NAMESPACE=logsdb

# Drop event.original field
DROP_EVENT_ORIGINAL=true
```

### Storage Comparison

Based on typical usage patterns, you can expect approximately these storage savings:

| Optimization | Approximate Storage Savings |
|--------------|----------------------------|
| Default (text field) | Baseline |
| Keyword mapping | 10-20% savings |
| Drop event.original | 30-50% savings |
| LogsDB mode | 20-40% savings |
| All combined | 50-70% savings |

Actual savings will vary based on your specific log data.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Data Stream Naming Conventions

The system uses a predictable naming convention for data streams to make it easy to identify the configuration:

```
logs-syslog-{base_namespace}-{log_type}[-no-original]
```

Where:
- **base_namespace**: Either "default" or "logsdb" depending on whether LogsDB mode is enabled
- **log_type**: The type of logs being processed (windows, linux, mac, ssh, apache, all)
- **-no-original**: Appended when event.original field is dropped

Examples:
- `logs-syslog-default-linux`: Standard configuration with Linux logs
- `logs-syslog-logsdb-windows`: LogsDB mode with Windows logs
- `logs-syslog-default-all-no-original`: All log types without event.original field
- `logs-syslog-logsdb-apache-no-original`: LogsDB mode with Apache logs and no event.original field

This naming convention makes it easy to identify the storage optimization settings used for each data stream.