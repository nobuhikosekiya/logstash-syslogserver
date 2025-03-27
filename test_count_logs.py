#!/usr/bin/env python3
import os
import sys
import time
import argparse
import glob
from datetime import datetime, timedelta
import json
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

def load_env_variables():
    """Load environment variables from .env file"""
    load_dotenv()
    
    es_endpoint = os.environ.get('ES_ENDPOINT')
    api_key = os.environ.get('ELASTIC_ADMIN_API_KEY')
    
    if not es_endpoint or not api_key:
        raise ValueError("ES_ENDPOINT and ELASTIC_ADMIN_API_KEY must be set in the .env file")
    
    # Clean up the ES_ENDPOINT to ensure it's properly formatted
    if es_endpoint.endswith('/'):
        es_endpoint = es_endpoint[:-1]  # Remove trailing slash if present
    
    # Ensure ES_ENDPOINT has a scheme
    if not (es_endpoint.startswith('http://') or es_endpoint.startswith('https://')):
        es_endpoint = 'https://' + es_endpoint
        print(f"Added https:// to ES_ENDPOINT: {es_endpoint}")
    
    # Set default port based on protocol if ES_PORT is not provided
    es_port = os.environ.get('ES_PORT')
    if not es_port:
        if es_endpoint.startswith('https://'):
            es_port = '443'
            print("ES_PORT not set, defaulting to 443 for HTTPS")
        else:
            es_port = '9200'
            print("ES_PORT not set, defaulting to 9200 for HTTP")
    
    # Check if endpoint already contains port
    import re
    port_in_url = re.search(r':\d+($|/)', es_endpoint)
    
    # Return full endpoint with port if not already included
    if not port_in_url:
        # Add the port to the URL
        host_part = es_endpoint.split('://', 1)[1].split('/', 1)[0]
        scheme = es_endpoint.split('://', 1)[0]
        path = ''
        if '/' in es_endpoint.split('://', 1)[1]:
            path = '/' + es_endpoint.split('://', 1)[1].split('/', 1)[1]
        
        full_url = f"{scheme}://{host_part}:{es_port}{path}"
        print(f"Constructed Elasticsearch URL: {full_url}")
        return full_url, api_key
    else:
        # Port is already in the URL
        print(f"Using Elasticsearch URL as provided: {es_endpoint}")
        return es_endpoint, api_key

def create_es_client(es_endpoint, api_key):
    """Create an Elasticsearch client"""
    try:
        print(f"Attempting to connect to Elasticsearch at: {es_endpoint}")
        
        # Check if the URL format is valid
        import re
        if not re.match(r'^https?://[^:]+:\d+', es_endpoint):
            raise ValueError(f"Invalid Elasticsearch URL format: {es_endpoint}. URL must include a 'scheme', 'host', and 'port' component (ie 'https://localhost:9200')")
        
        client = Elasticsearch(
            es_endpoint,
            api_key=api_key,
            verify_certs=True,
            timeout=30
        )
        
        # Check if connection was successful
        if not client.ping():
            raise ConnectionError("Could not connect to Elasticsearch. Please check your credentials and endpoint.")
        
        print(f"Successfully connected to Elasticsearch: {es_endpoint}")
        return client
    except Exception as e:
        print(f"Error creating Elasticsearch client: {str(e)}")
        raise

def count_logs(client, data_stream, query=None):
    """Count logs in the specified data stream"""
    query_body = {"query": {"match_all": {}}}
    
    # Apply custom query if specified
    if query:
        try:
            custom_query = json.loads(query)
            query_body = {"query": custom_query}
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON query, using default query instead")
    
    try:
        # Check if the data stream exists
        if not check_data_stream_exists(client, data_stream):
            print(f"Data stream '{data_stream}' does not exist")
            return 0
        
        # Count logs
        response = client.count(index=data_stream, body=query_body)
        return response.get("count", 0)
    except Exception as e:
        print(f"Error counting logs: {str(e)}")
        return 0

def check_data_stream_exists(client, data_stream):
    """Check if the data stream exists"""
    try:
        result = client.indices.get_data_stream(name=data_stream)
        return len(result.get("data_streams", [])) > 0
    except Exception:
        return False

def list_data_streams(client, pattern="logs-syslog-*"):
    """List all data streams matching the given pattern"""
    try:
        result = client.indices.get_data_stream(name=pattern)
        return [ds["name"] for ds in result.get("data_streams", [])]
    except Exception as e:
        print(f"Error listing data streams: {str(e)}")
        return []

def count_log_lines_in_files(log_dir, log_type):
    """Count total number of log lines in the log files"""
    total_lines = 0
    
    # Determine which files to count based on log_type
    if log_type.lower() == 'all':
        log_files = glob.glob(f"{log_dir}/**/*.log", recursive=True)
    else:
        # Check if a specific directory for this log type exists
        type_dir = os.path.join(log_dir, log_type.capitalize())
        if os.path.exists(type_dir):
            log_files = glob.glob(f"{type_dir}/**/*.log", recursive=True)
        else:
            # Try finding files with matching filename pattern
            log_files = glob.glob(f"{log_dir}/**/{log_type}*.log", recursive=True)
            log_files.extend(glob.glob(f"{log_dir}/**/{log_type.capitalize()}*.log", recursive=True))
    
    if not log_files:
        print(f"No log files found for type '{log_type}' in {log_dir}")
        return 0
    
    print(f"Counting lines in {len(log_files)} log files...")
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                line_count = sum(1 for line in f if line.strip())  # Count non-empty lines
                total_lines += line_count
                print(f"  {os.path.basename(log_file)}: {line_count} lines")
        except Exception as e:
            print(f"Error reading file {log_file}: {e}")
    
    return total_lines

def main():
    parser = argparse.ArgumentParser(description='Count logs in Elasticsearch data stream')
    parser.add_argument('--type', dest='type', help='Data stream type', default='logs')
    parser.add_argument('--dataset', dest='dataset', help='Data stream dataset', default='syslog')
    parser.add_argument('--namespace', dest='namespace', help='Data stream namespace', default='default')
    parser.add_argument('--minutes', dest='minutes', type=int, help='Time range in minutes', default=None)
    parser.add_argument('--query', dest='query', help='Custom query (JSON string)', default=None)
    parser.add_argument('--es-endpoint', dest='es_endpoint', help='Elasticsearch endpoint (overrides .env)', default=None)
    parser.add_argument('--api-key', dest='api_key', help='Elasticsearch API Key (overrides .env)', default=None)
    parser.add_argument('--watch', dest='watch', action='store_true', help='Watch mode: continuously check count')
    parser.add_argument('--interval', dest='interval', type=int, help='Watch interval in seconds', default=5)
    parser.add_argument('--log-type', dest='log_type', help='Filter by log type', default=None)
    parser.add_argument('--list-streams', dest='list_streams', action='store_true', help='List all syslog data streams')
    parser.add_argument('--log-dir', dest='log_dir', help='Directory containing log files', default='logs')
    parser.add_argument('--auto-stop', dest='auto_stop', action='store_true', 
                        help='Auto stop when log count matches expected line count')
    parser.add_argument('--timeout', dest='timeout', type=int, help='Maximum watch time in seconds', default=300)
    parser.add_argument('--debug', dest='debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    try:
        # Try to load from .env first
        es_endpoint, api_key = load_env_variables()
        
        # Override with command line if provided
        if args.es_endpoint:
            es_endpoint = args.es_endpoint
        if args.api_key:
            api_key = args.api_key
        
        # Get log_type from environment if not specified
        if args.log_type is None:
            args.log_type = os.environ.get('LOG_TYPE', 'all')
            if args.debug:
                print(f"Using LOG_TYPE from environment: {args.log_type}")
        
        # Create Elasticsearch client
        client = create_es_client(es_endpoint, api_key)
        
        # List data streams if requested
        if args.list_streams:
            data_streams = list_data_streams(client)
            if data_streams:
                print("Available syslog data streams:")
                for ds in data_streams:
                    print(f"  - {ds}")
            else:
                print("No syslog data streams found.")
            return
        
        # Construct the data stream name (format: {type}-{dataset}-{namespace})
        data_stream_name = f"{args.type}-{args.dataset}-{args.namespace}"
        
        if args.watch:
            # Only count log lines if auto-stop is enabled
            expected_line_count = 0
            if args.auto_stop:
                expected_line_count = count_log_lines_in_files(args.log_dir, args.log_type)
                print(f"Expected log count based on files: {expected_line_count}")
            
            print(f"Watching log count for data stream: {data_stream_name}")
            if args.log_type:
                print(f"Filtering for log type: {args.log_type}")
            
            if not args.auto_stop:
                print("Press Ctrl+C to stop...")
            
            prev_count = 0
            start_time = time.time()
            try:
                while True:
                    current_time = time.time()
                    elapsed_seconds = int(current_time - start_time)
                    
                    count = count_logs(client, data_stream_name, args.query)
                    new_logs = count - prev_count if count > prev_count else 0
                    
                    # Show elapsed time and count
                    if prev_count == 0:
                        print(f"[{elapsed_seconds}s] Current log count: {count}")
                    else:
                        print(f"[{elapsed_seconds}s] Current log count: {count} (+{new_logs} new)")
                    
                    prev_count = count
                    
                    # Check auto-stop conditions
                    if args.auto_stop and expected_line_count > 0 and count >= expected_line_count:
                        print(f"\nTarget log count reached: {count} of {expected_line_count}")
                        print("Auto-stopping watch mode.")
                        break
                    
                    # Check timeout
                    if args.timeout > 0 and elapsed_seconds >= args.timeout:
                        print(f"\nTimeout reached ({args.timeout} seconds)")
                        if args.auto_stop and expected_line_count > 0:
                            print(f"Only received {count} of expected {expected_line_count} logs ({count/expected_line_count:.1%})")
                        print("Stopping watch mode.")
                        break
                    
                    time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\nWatch mode stopped by user.")
        else:
            # Single count
            count = count_logs(client, data_stream_name, args.query)
            print(f"Log count for '{data_stream_name}': {count}")
                
            # Print information about namespace vs dataset
            print(f"\nData stream info:")
            print(f"  Type:      {args.type}")
            print(f"  Dataset:   {args.dataset}")
            print(f"  Namespace: {args.namespace}")
            
            if count == 0:
                print("\nPossible reasons for 0 count:")
                print("1. The data stream doesn't exist yet (will be created when logs are first sent)")
                print("2. No logs have been sent yet")
                print("3. The Logstash configuration is incorrect")
                print("\nTry the following:")
                print("- Use --list-streams to see all available data streams")
                print("- Verify Docker containers are running: docker-compose ps")
                print("- Check Logstash logs: docker-compose logs logstash")
                print("- Check log-sender logs: docker-compose logs log-sender")
                print("- Use --watch --auto-stop flag to monitor as logs come in")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()