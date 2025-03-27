#!/usr/bin/env python3
import os
import sys
import argparse
import time
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

def check_datastream_exists(client, data_stream_name):
    """Check if a data stream already exists"""
    try:
        result = client.indices.get_data_stream(name=data_stream_name)
        return len(result.get("data_streams", [])) > 0
    except Exception:
        return False

def delete_datastream(client, data_stream_name):
    """Delete a data stream if it exists"""
    try:
        if check_datastream_exists(client, data_stream_name):
            client.indices.delete_data_stream(name=data_stream_name)
            print(f"Existing data stream '{data_stream_name}' deleted successfully")
            
            # Verify deletion
            for _ in range(5):
                if not check_datastream_exists(client, data_stream_name):
                    print(f"Verified data stream '{data_stream_name}' no longer exists")
                    return True
                print("Waiting for data stream deletion to complete...")
                time.sleep(2)
            
            if check_datastream_exists(client, data_stream_name):
                print(f"Warning: Data stream '{data_stream_name}' still exists after deletion")
                return False
            return True
        else:
            print(f"No existing data stream '{data_stream_name}' found")
            return True
    except Exception as e:
        print(f"Error deleting data stream: {str(e)}")
        return False

def create_index_template(client, template_name, index_pattern, logsdb_mode=False):
    """Create an index template for the data stream"""
    # Start with base settings
    settings = {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index": {
            "codec": "best_compression"
        }
    }
    
    # Add logsdb mode if specified
    if logsdb_mode:
        settings["index"]["mode"] = "logsdb"
    
    template = {
        "index_patterns": [index_pattern],
        "data_stream": {},
        "priority": 500,
        "template": {
            "settings": settings,
            "mappings": {
                "properties": {
                    "@timestamp": {"type": "date"},
                    "host": {
                        "properties": {
                            "name": {"type": "keyword"}
                        }
                    },
                    "message": {"type": "text"},
                    "log_type": {"type": "keyword"},
                    "log": {
                        "properties": {
                            "syslog": {
                                "properties": {
                                    "facility": {
                                        "properties": {
                                            "name": {"type": "keyword"}
                                        }
                                    },
                                    "severity": {
                                        "properties": {
                                            "name": {"type": "keyword"}
                                        }
                                    },
                                    "priority": {"type": "long"}
                                }
                            }
                        }
                    },
                    "source": {
                        "properties": {
                            "ip": {"type": "ip"}
                        }
                    }
                }
            }
        }
    }
    
    try:
        response = client.indices.put_index_template(name=template_name, body=template)
        if response.get("acknowledged"):
            print(f"Index template '{template_name}' created successfully")
        else:
            print(f"Failed to create index template: {response}")
            sys.exit(1)
    except Exception as e:
        print(f"Error creating index template: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Set up Elasticsearch index template for Logstash syslog ingestion')
    parser.add_argument('--type', dest='type', help='Data stream type', default='logs')
    parser.add_argument('--dataset', dest='dataset', help='Data stream dataset', default='syslog')
    parser.add_argument('--namespace', dest='namespace', help='Data stream namespace', default='default')
    parser.add_argument('--es-endpoint', dest='es_endpoint', help='Elasticsearch endpoint (overrides .env)', default=None)
    parser.add_argument('--api-key', dest='api_key', help='Elasticsearch API Key (overrides .env)', default=None)
    parser.add_argument('--logsdb', dest='logsdb_mode', action='store_true', help='Enable logsdb mode in index settings')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    try:
        # Try to load from .env first
        if args.debug:
            print("Debug mode enabled")
            print("Loading environment variables from .env file...")
            
        es_endpoint, api_key = load_env_variables()
        
        if args.debug:
            print(f"ES_ENDPOINT from environment: {es_endpoint}")
            print(f"API_KEY from environment: {'*' * 8} (masked)")
        
        # Override with command line if provided
        if args.es_endpoint:
            es_endpoint = args.es_endpoint
            if args.debug:
                print(f"Overriding ES_ENDPOINT with command line value: {es_endpoint}")
        if args.api_key:
            api_key = args.api_key
            if args.debug:
                print("Overriding API_KEY with command line value (masked)")
        
        # Create Elasticsearch client
        client = create_es_client(es_endpoint, api_key)
        
        # Construct the data stream name (format: {type}-{dataset}-{namespace})
        data_stream_name = f"{args.type}-{args.dataset}-{args.namespace}"
        
        # Use a wildcard pattern for the template to match any namespace
        template_name = f"{args.type}-{args.dataset}-template"
        
        # Use wildcard pattern for the index template to match any namespace
        index_pattern = f"{args.type}-{args.dataset}-*"
        
        print(f"Setting up data stream: {data_stream_name}")
        print(f"Using index pattern: {index_pattern}")
        
        if args.logsdb_mode:
            print("LogsDB mode is enabled for this data stream")
        
        # Delete existing data stream if it exists
        deletion_success = delete_datastream(client, data_stream_name)
        if not deletion_success:
            print("Warning: Could not completely delete the existing data stream.")
        
        # Create index template (required for data stream auto-creation)
        create_index_template(client, template_name, index_pattern, args.logsdb_mode)
        
        print("Setup completed successfully!")
        print("The data stream will be created automatically when Logstash ingests the first log entry.")
        print(f"Data stream name: {data_stream_name}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()