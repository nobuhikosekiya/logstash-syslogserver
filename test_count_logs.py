#!/usr/bin/env python3
import os
import sys
import time
import argparse
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
    
    # Set default port based on protocol if ES_PORT is not provided
    es_port = os.environ.get('ES_PORT')
    if not es_port:
        if es_endpoint.startswith('https://'):
            es_port = '443'
            print("ES_PORT not set, defaulting to 443 for HTTPS")
        else:
            es_port = '9200'
            print("ES_PORT not set, defaulting to 9200 for HTTP")
    
    # Return full endpoint with port
    return f"{es_endpoint}:{es_port}", api_key

def create_es_client(es_endpoint, api_key):
    """Create an Elasticsearch client"""
    client = Elasticsearch(
        es_endpoint,
        api_key=api_key,
        verify_certs=True
    )
    
    # Check if connection was successful
    if not client.ping():
        raise ConnectionError("Could not connect to Elasticsearch. Please check your credentials.")
    
    print(f"Successfully connected to Elasticsearch: {es_endpoint}")
    return client

def count_logs(client, data_stream, time_range_minutes=None, query=None):
    """Count logs in the specified data stream"""
    query_body = {"query": {"match_all": {}}}
    
    # Apply time range filter if specified
    if time_range_minutes:
        now = datetime.utcnow()
        from_time = now - timedelta(minutes=time_range_minutes)
        
        query_body = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": from_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                        "lte": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    }
                }
            }
        }
    
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
    
    args = parser.parse_args()
    
    try:
        # Try to load from .env first
        es_endpoint, api_key = load_env_variables()
        
        # Override with command line if provided
        if args.es_endpoint:
            es_endpoint = args.es_endpoint
        if args.api_key:
            api_key = args.api_key
        
        # Create Elasticsearch client
        client = create_es_client(es_endpoint, api_key)
        
        # Construct the data stream name (format: {type}-{dataset}-{namespace})
        data_stream_name = f"{args.type}-{args.dataset}-{args.namespace}"
        
        if args.watch:
            print(f"Watching log count for data stream: {data_stream_name}")
            print(f"Press Ctrl+C to stop...")
            
            prev_count = 0
            try:
                while True:
                    count = count_logs(client, data_stream_name, args.minutes, args.query)
                    new_logs = count - prev_count if count > prev_count else 0
                    
                    if prev_count == 0:
                        print(f"Current log count: {count}")
                    else:
                        print(f"Current log count: {count} (+{new_logs} new)")
                    
                    prev_count = count
                    time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\nWatch mode stopped.")
                sys.exit(0)
        else:
            # Single count
            count = count_logs(client, data_stream_name, args.minutes, args.query)
            print(f"Log count for '{data_stream_name}': {count}")
            
            if args.minutes:
                print(f"(Limited to logs from the last {args.minutes} minutes)")
                
            # Print information about namespace vs dataset
            print(f"\nData stream info:")
            print(f"  Type:      {args.type}")
            print(f"  Dataset:   {args.dataset}")
            print(f"  Namespace: {args.namespace}")
            
            if count == 0:
                print("\nPossible reasons for 0 count:")
                print("1. The data stream doesn't exist yet (will be created when logs are first sent)")
                print("2. No logs have been sent yet")
                print("3. Logs were sent outside the specified time range")
                print("4. The Logstash configuration is incorrect")
                print("\nTry the following:")
                print("- Verify Docker containers are running: docker-compose ps")
                print("- Check Logstash logs: docker-compose logs logstash")
                print("- Check log-sender logs: docker-compose logs log-sender")
                print("- Use --watch flag to monitor as logs come in")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()