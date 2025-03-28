# Logstash Syslog Server with Elasticsearch Data Stream Integration

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌────────────────┐     ┌─────────────────┐
│  Log Source │     │ Log Sender  │     │    Logstash    │     │  Elasticsearch  │
│  (External) │────>│ (Container) │────>│   (Container)  │────>│  (External/Cloud│
└─────────────┘     └─────────────┘     └────────────────┘     │     Service)    │
                         │                      │               └─────────────────┘
                         │                      │                        ▲
                         │                      │                        │
                    ┌────▼──────┐         ┌─────▼────┐              ┌───┴────┐
                    │   logs/   │         │ logstash/ │              │ Setup  │
                    │ directory │         │ pipeline/ │              │ Scripts│
                    └───────────┘         └──────────┘              └────────┘
```

### Components

- **Log Source**: External systems generating logs (not part of this project)
- **Log Sender Container**: Downloads sample logs and sends them to Logstash
- **Logstash Container**: Receives, processes, and forwards logs
- **Elasticsearch**: External service that stores the processed logs (prerequisite, not included)
- **Setup Scripts**: Configure the data stream and test the system

### Prerequisites (Not Included in Project)

- **Elasticsearch Deployment**: You must have an Elasticsearch instance running (self-hosted or cloud)
- **Elasticsearch API Keys**: You need to create API keys with appropriate permissions:
  - Logstash API Key: For indexing data
  - Admin API Key: For managing data streams and index templates
- **Docker and Docker Compose**: Required to run the containers
- **Python 3.6+**: Required for setup and test scripts

This project provides a complete system for ingesting syslog data into Elasticsearch with flexible storage optimization options. It includes:

1. A Logstash server that receives syslog messages (TCP and UDP on port 5514)
2. A log sender component that can simulate different types of log data
3. Integration with Elasticsearch using Data Streams
4. Comprehensive testing and configuration tools

## Quick Start

### Prerequisites

Before you begin, ensure you have:

1. **Elasticsearch Deployment**:
   - A running Elasticsearch 8.x instance (cloud-based or self-hosted)
   - Network connectivity from your host to Elasticsearch
   - Sufficient privileges to create index templates and data streams

2. **Elasticsearch API Keys**:
   - Create a Logstash API key with `create_doc` permissions on `logs-*` indices
   - Create an Admin API key with `manage_index_templates` and `manage_data_stream` permissions

3. **Local Environment**:
   - Docker and Docker Compose installed
   - Python 3.6+ with pip
   - Git (to clone the repository)
   - 500MB+ free disk space for sample logs
   - Open port 5514 (if receiving external syslog messages)

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/yourusername/logstash-syslog-elasticsearch.git
cd logstash-syslog-elasticsearch

# Run the setup script
chmod +x setup.sh
./setup.sh

# Edit your .env file with your Elasticsearch details
nano .env
# Important: Update ES_ENDPOINT, ELASTIC_LOGSTASH_API_KEY, and ELASTIC_ADMIN_API_KEY

# Run the test script with default settings
python test_syslog_server.py
```

The test script will:
1. Set up the Elasticsearch data stream
2. Start the Docker containers
3. Send sample logs to Logstash
4. Verify ingestion into Elasticsearch
5. Generate a test report

## Test Script Options

The `test_syslog_server.py` script provides a comprehensive way to test and configure the system. Here's a detailed explanation of all available options:

### Basic Usage

```bash
python test_syslog_server.py [options]
```

### Log Type Selection (--log-type)

Determines which type of log files to process:

```bash
python test_syslog_server.py --log-type linux
```

Options:
- `windows`: Process only Windows event logs *(Note: Currently commented out in the code due to large size - over 20GB)*
- `linux`: Process only Linux system logs
- `mac`: Process only macOS logs
- `ssh`: Process only SSH authentication logs
- `apache`: Process only Apache web server logs
- `all`: Process all log types (default)

**What it changes:**
- Filters which log files are sent to Logstash
- Affects the data stream namespace (adds the log type to the namespace)
- Changes expected log count and processing time

### LogsDB Mode (--logsdb)

Enables LogsDB mode for optimized log storage in Elasticsearch:

```bash
python test_syslog_server.py --logsdb
```

**What it changes:**
- Modifies Elasticsearch index settings with LogsDB-specific optimizations
- Changes the base namespace from "default" to "logsdb"
- Typically reduces storage by 20-40% compared to standard mode
- Optimizes indexing performance and search speed for log data
- Adds specific index settings:
  - Configures codec to use "best_compression"
  - Sets the index mode to "logsdb"
  - Optimizes refresh intervals and merge policies

### Drop event.original Field (--drop-event-original)

Removes the event.original field from indexed documents:

```bash
python test_syslog_server.py --drop-event-original
```

**What it changes:**
- Adds a filter in Logstash to remove the event.original field before indexing
- Adds "-no-original" to the data stream namespace
- Typically reduces storage by 30-50% compared to keeping the field
- Removes the raw, unprocessed log message that's normally kept for reference
- Affects troubleshooting capabilities as the original message is no longer available

### Drop message Field (--drop-msg)

Removes the message field from indexed documents:

```bash
python test_syslog_server.py --drop-message
```

**What it changes:**
- Adds a filter in Logstash to remove the message field before indexing
- Adds "-no-msg" to the data stream namespace
- Typically reduces storage by 20-40% compared to keeping the field
- Removes the processed log message content
- Affects searchability as the main message content is no longer available
- Only use this when all important data has already been extracted to structured fields

### Debug Mode (--debug)

Enables additional debug output:

```bash
python test_syslog_server.py --debug
```

**What it changes:**
- Increases verbosity of console output
- Shows environment variable values (except API keys)
- Shows commands being executed
- Passes debug flag to dependent scripts

### Skip Cleanup (--no-cleanup)

Prevents automatic cleanup after test completion:

```bash
python test_syslog_server.py --no-cleanup
```

**What it changes:**
- Keeps Docker containers running after test completion
- Does not restore .env file from backup
- Useful for debugging or when you want to examine the environment after a test

## Combining Options

You can combine multiple options to customize your test setup. For example:

```bash
# Test with Linux logs using LogsDB mode and dropping both fields for maximum storage savings
python test_syslog_server.py --log-type linux --logsdb --drop-event-original --drop-message

# Test with Apache logs in debug mode without cleanup
python test_syslog_server.py --log-type apache --debug --no-cleanup
```

## Data Stream Naming Convention

The system uses a consistent naming pattern for data streams:

```
logs-syslog-{base_namespace}-{log_type}[-no-original][-no-msg]
```

Where:
- **base_namespace**: "default" or "logsdb" (if LogsDB mode is enabled)
- **log_type**: The type of logs being processed (windows, linux, mac, ssh, apache, all)
- **-no-original**: Added when event.original field is dropped
- **-no-msg**: Added when message field is dropped

Examples:
- `logs-syslog-default-linux`: Standard configuration with Linux logs
- `logs-syslog-logsdb-windows`: LogsDB mode with Windows logs
- `logs-syslog-default-all-no-original`: All log types without event.original field
- `logs-syslog-logsdb-apache-no-original-no-msg`: LogsDB mode with Apache logs, dropping both fields

## Storage Optimization Comparison

*Note: The storage savings percentages below are estimated values and not based on actual benchmarks. These are assumptions created for illustrative purposes.*

| Configuration | Approximate Storage Savings | Impact on Functionality |
|---------------|----------------------------|-------------------------|
| Default | Baseline | Full functionality, largest storage footprint |
| LogsDB mode | 20-40% savings | Full functionality with optimized indices |
| Drop event.original | 30-50% savings | Lose ability to see original raw message |
| Drop message | 20-40% savings | Lose ability to search message content |
| All optimizations | 60-80% savings | Most space-efficient, but limited functionality |

Actual storage savings will vary based on log content, volume, and specific use cases. It's recommended to test each optimization option with your specific log data to determine actual storage impacts.

## Environment Variables

The `.env` file controls the system configuration:

```properties
# Elasticsearch connection settings
ES_ENDPOINT="https://your-es-endpoint.cloud.es.io"
ES_PORT=443
ELASTIC_LOGSTASH_API_KEY="your_logstash_api_key_here"
ELASTIC_ADMIN_API_KEY="your_admin_api_key_here"
ES_DATA_STREAM_NAMESPACE="default"  # Or "logsdb" for LogsDB mode

# Field removal options
DROP_EVENT_ORIGINAL=false  # Set to true to drop the event.original field
DROP_MESSAGE=false  # Set to true to drop the message field

# Log sender configuration
DOWNLOAD_LOGS=true
LOG_SEND_INTERVAL=0.01
PROTOCOL=tcp
LOOP_LOGS=false
KEEP_RUNNING=false
LOG_TYPE=all
```

The test script updates these values based on the command-line options you provide.

## Logstash Pipeline Details

The Logstash pipeline (`logstash/pipeline/syslog-server.conf`) performs these processing steps:

1. Receives syslog messages on port 5514 (TCP and UDP)
2. Handles character encoding issues
3. Extracts hostname, timestamp, and message content using Grok patterns
4. Updates fields to follow the Elastic Common Schema (ECS)
5. Conditionally removes fields based on configuration:
   - Removes event.original if DROP_EVENT_ORIGINAL=true
   - Removes message if DROP_MESSAGE=true
6. Sends data to Elasticsearch using the configured data stream

## Test Report

After each test run, a `test_report.md` file is generated containing:

- Test configuration details
- Test results (PASSED/FAILED)
- Log ingestion statistics
- Container status and logs
- Environment information

This report is useful for documenting your test results and troubleshooting any issues.

## Docker Components

The system consists of two Docker containers:

1. **Logstash**: Runs the syslog server and processes logs
   - Listens on TCP and UDP port 5514
   - Processes and transforms log data
   - Indexes data to Elasticsearch

2. **Log Sender**: Simulates log sources
   - Downloads sample logs if needed
   - Sends logs to Logstash via syslog protocol
   - Can be configured to send different log types

## Troubleshooting

If you encounter issues, check the following:

1. **No logs in Elasticsearch**
   - Verify Elasticsearch connection details in .env
   - Check Logstash logs: `docker-compose logs logstash`
   - Test connectivity to Elasticsearch
   - Verify API key permissions

2. **Logstash errors**
   - Check Logstash configuration
   - Verify field references in pipeline
   - Check available memory/resources

3. **Log sender issues**
   - Check if sample logs were downloaded: `ls -la logs/`
   - Verify connectivity to Logstash: `nc -v localhost 5514`
   - Check log sender logs: `docker-compose logs log-sender`

Use the `--debug` flag for additional diagnostic information.

## Advanced Use Cases

### Enabling TLS/SSL for Syslog Input

For secure transmission, modify the syslog input to use SSL:

```ruby
input {
  syslog {
    port => 5514
    type => "syslog"
    ssl_enable => true
    ssl_cert => "/usr/share/logstash/secrets/server.crt"
    ssl_key => "/usr/share/logstash/secrets/server.key"
    # ... other settings
  }
}
```

### Custom Fields Extraction

Modify the Logstash pipeline to extract additional fields from your logs:

```ruby
filter {
  # Extract specific fields for your application
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:log_level} \[%{DATA:service}\] %{GREEDYDATA:log_message}" }
  }
  
  # ... rest of pipeline
}
```

### Integration with Filebeat

To use this setup with Filebeat instead of direct syslog input:

1. Configure Logstash to listen for Filebeat input
2. Configure Filebeat to forward to Logstash
3. Use the same storage optimization options

## License

This project is licensed under the MIT License - see the LICENSE file for details.