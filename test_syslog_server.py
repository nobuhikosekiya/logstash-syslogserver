#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import time
import platform
import shutil
import signal
import datetime
from pathlib import Path
import re

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color

def colored_print(text, color):
    """Print colored text to the terminal"""
    print(f"{color}{text}{Colors.NC}")

def run_command(command, shell=False, env=None, capture_output=False):
    """Run a command and return its output"""
    try:
        if isinstance(command, str) and not shell:
            command = command.split()
        
        # Pass current environment variables plus any additional ones
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        result = subprocess.run(
            command, 
            shell=shell, 
            env=process_env, 
            check=True, 
            text=True,
            capture_output=capture_output
        )
        
        if capture_output:
            return result.stdout.strip()
        return True
    except subprocess.CalledProcessError as e:
        if capture_output:
            print(f"Command failed: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
        else:
            print(f"Command failed: {e}")
        return False

def command_exists(command):
    """Check if a command is available in the system PATH"""
    return shutil.which(command) is not None

def backup_env_file():
    """Create a backup of the .env file"""
    if os.path.exists(".env"):
        shutil.copy(".env", ".env.backup")
        print("Created backup of .env file")
        return True
    return False

def restore_env_file():
    """Restore the .env file from backup"""
    if os.path.exists(".env.backup"):
        shutil.move(".env.backup", ".env")
        print("Restored .env file from backup")
        return True
    return False

def update_env_file(namespace, log_type):
    """Update the .env file with the namespace and log type"""
    if not os.path.exists(".env"):
        print(".env file not found")
        return False
    
    # Read the current .env file
    with open(".env", "r") as file:
        lines = file.readlines()
    
    # Filter out existing namespace and log type settings
    filtered_lines = [line for line in lines if not line.startswith("ES_DATA_STREAM_NAMESPACE=") 
                      and not line.startswith("LOG_TYPE=")]
    
    # Add the new values
    filtered_lines.append(f"ES_DATA_STREAM_NAMESPACE={namespace}\n")
    filtered_lines.append(f"LOG_TYPE={log_type}\n")
    
    # Write back to the .env file
    with open(".env", "w") as file:
        file.writelines(filtered_lines)
    
    print(f"Updated .env file with namespace: {namespace} and log type: {log_type}")
    
    # Verify the changes
    with open(".env", "r") as file:
        content = file.read()
        ns_pattern = re.compile(r"ES_DATA_STREAM_NAMESPACE\s*=\s*{0}".format(namespace))
        log_pattern = re.compile(r"LOG_TYPE\s*=\s*{0}".format(log_type))
        
        if not ns_pattern.search(content):
            print("WARNING: ES_DATA_STREAM_NAMESPACE not correctly set in .env")
        if not log_pattern.search(content):
            print("WARNING: LOG_TYPE not correctly set in .env")
    
    return True

def activate_virtualenv():
    """Activate the Python virtual environment"""
    if platform.system() == "Windows":
        venv_activate = os.path.join("venv", "Scripts", "activate")
    else:
        venv_activate = os.path.join("venv", "bin", "activate")
    
    if not os.path.exists(venv_activate):
        print(f"Virtual environment activation script not found at {venv_activate}")
        return False
    
    # On Windows, we need a different approach since source/. doesn't work
    if platform.system() == "Windows":
        # On Windows, we set the virtual environment path in the environment
        os.environ["VIRTUAL_ENV"] = os.path.abspath("venv")
        os.environ["PATH"] = os.path.join(os.environ["VIRTUAL_ENV"], "Scripts") + os.pathsep + os.environ["PATH"]
    else:
        # On Unix-like systems, we need to run the activate script in the current shell
        # This doesn't work directly in Python, so we'll use a workaround
        # We'll export the VIRTUAL_ENV environment variable ourselves
        os.environ["VIRTUAL_ENV"] = os.path.abspath("venv")
        os.environ["PATH"] = os.path.join(os.environ["VIRTUAL_ENV"], "bin") + os.pathsep + os.environ["PATH"]
    
    print(f"Activated virtual environment: {os.environ.get('VIRTUAL_ENV')}")
    return True

def check_elasticsearch_settings(env_file=".env"):
    """Check if Elasticsearch settings are configured in the .env file"""
    required_vars = ["ES_ENDPOINT", "ELASTIC_LOGSTASH_API_KEY", "ELASTIC_ADMIN_API_KEY"]
    
    if not os.path.exists(env_file):
        return False
    
    # Read the .env file and check for required variables
    with open(env_file, "r") as file:
        content = file.read()
        for var in required_vars:
            if not re.search(f"{var}=.+", content):
                print(f"Missing required environment variable: {var}")
                return False
    
    return True

def create_test_report(data_stream, use_logsdb, log_type, final_count, test_result="UNKNOWN"):
    """Generate a test report markdown file"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get Docker and Python versions
    docker_version = run_command("docker --version", capture_output=True) or "Unknown"
    compose_version = run_command("docker-compose --version", capture_output=True) or "Unknown"
    python_version = run_command(sys.executable + " --version", capture_output=True) or "Unknown"
    
    # Get container status and logs
    container_status = run_command("docker-compose ps", capture_output=True) or "No containers running"
    logstash_logs = run_command("docker-compose logs --tail=20 logstash", capture_output=True) or "No logs available"
    log_sender_logs = run_command("docker-compose logs --tail=20 log-sender", capture_output=True) or "No logs available"
    
    report = f"""# Logstash Syslog Server to Elasticsearch Test Report

Test conducted on: {now}

## Summary
- Test result: {test_result}
- Data stream: {data_stream}
- LogsDB mode: {use_logsdb}
- Log type: {log_type}
- Log lines ingested: {final_count}

## Environment
- Docker version: {docker_version}
- Docker Compose version: {compose_version}
- Python version: {python_version}
- Elasticsearch URL: {os.environ.get('ES_ENDPOINT', 'Unknown')}:{os.environ.get('ES_PORT', 'Unknown')}

## Container Status
```
{container_status}
```

## Logstash Logs
```
{logstash_logs}
```

## Log Sender Logs
```
{log_sender_logs}
```
"""
    
    # Write the report to a file
    with open("test_report.md", "w") as file:
        file.write(report)
    
    print(f"Test report generated: test_report.md")

def main():
    parser = argparse.ArgumentParser(description='Test Logstash Syslog Server to Elasticsearch setup')
    parser.add_argument('--log-type', choices=['windows', 'linux', 'mac', 'all'], default='all',
                        help='Log type to process (windows, linux, mac, or all)')
    parser.add_argument('--logsdb', action='store_true', 
                        help='Enable LogsDB mode for Elasticsearch indices')
    parser.add_argument('--no-cleanup', action='store_true',
                        help='Do not restore .env file or stop containers after test')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    
    args = parser.parse_args()
    
    # Set default values
    use_logsdb = args.logsdb
    log_type = args.log_type
    
    colored_print("Starting test of Logstash Syslog Server to Elasticsearch setup...", Colors.YELLOW)
    print(f"Using log type: {log_type}")
    print(f"LogsDB mode: {use_logsdb}")
    
    # Register cleanup handler for Ctrl+C
    def cleanup_handler(sig, frame):
        print("\nInterrupted. Cleaning up...")
        if not args.no_cleanup:
            run_command("docker-compose down")
            restore_env_file()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, cleanup_handler)
    
    # Check prerequisites
    print("Checking prerequisites...")
    for cmd in ["docker", "docker-compose"]:
        if not command_exists(cmd):
            colored_print(f"Error: {cmd} is not installed. Please install it and try again.", Colors.RED)
            sys.exit(1)
    
    # Check if Python is available
    if not os.path.exists(sys.executable):
        colored_print("Error: Python executable not found.", Colors.RED)
        sys.exit(1)
    print(f"Using Python: {sys.executable}")
    
    # Check environment variables
    print("Checking environment variables...")
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print("Creating .env file from .env.example for testing...")
            shutil.copy(".env.example", ".env")
            print("You'll need to update the .env file with your actual credentials before the test will pass.")
        else:
            colored_print("Error: .env file not found and no .env.example to copy from.", Colors.RED)
            sys.exit(1)
    
    # Backup .env file
    backup_env_file()
    
    # Check Elasticsearch settings
    if not check_elasticsearch_settings():
        colored_print("Error: Required Elasticsearch settings not found in .env file.", Colors.RED)
        sys.exit(1)
    
    # Set the base namespace based on LogsDB mode
    base_namespace = "logsdb" if use_logsdb else "default"
    
    # Append log type to namespace
    namespace = f"{base_namespace}-{log_type}"
    colored_print(f"Using namespace: {namespace}", Colors.GREEN)
    
    # Update .env file with namespace and log type
    update_env_file(namespace, log_type)
    
    # Load environment variables from .env file
    print("Loading environment variables from .env file...")
    try:
        with open(".env", "r") as file:
            for line in file:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    # Strip quotes if present
                    value = value.strip('"\'')
                    os.environ[key] = value
                    if args.debug:
                        if 'KEY' in key:  # Don't print actual API keys
                            print(f"Set environment variable: {key}=******")
                        else:
                            print(f"Set environment variable: {key}={value}")
    except Exception as e:
        colored_print(f"Error loading environment variables: {e}", Colors.RED)
        if not args.no_cleanup:
            restore_env_file()
        sys.exit(1)
        
    # Ensure ES_ENDPOINT is properly formatted
    es_endpoint = os.environ.get('ES_ENDPOINT', '')
    if not (es_endpoint.startswith('http://') or es_endpoint.startswith('https://')):
        os.environ['ES_ENDPOINT'] = 'https://' + es_endpoint
        colored_print(f"Added https:// to ES_ENDPOINT: {os.environ['ES_ENDPOINT']}", Colors.YELLOW)
    
    # Run setup script
    print("Running setup script...")
    if platform.system() == "Windows":
        setup_result = run_command("./setup.sh" if os.path.exists("./setup.sh") else "setup.sh", shell=True)
    else:
        setup_result = run_command("./setup.sh", shell=True)
    
    if not setup_result:
        colored_print("Error: Setup script failed.", Colors.RED)
        if not args.no_cleanup:
            restore_env_file()
        sys.exit(1)
    
    # Activate virtual environment
    if not activate_virtualenv():
        colored_print("Error: Failed to activate virtual environment.", Colors.RED)
        if not args.no_cleanup:
            restore_env_file()
        sys.exit(1)
    
    # Check if the data stream setup script exists
    if not os.path.exists("setup_datastream.py"):
        colored_print("Error: setup_datastream.py not found.", Colors.RED)
        if not args.no_cleanup:
            restore_env_file()
        sys.exit(1)
    
    # Run the data stream setup script
    print(f"Setting up Elasticsearch data stream with namespace {namespace}...")
    logsdb_arg = "--logsdb" if use_logsdb else ""
    
    # Debug environment variables
    if args.debug:
        print("\nDebug: Environment Variables for Data Stream Setup:")
        for key, value in os.environ.items():
            if key.startswith('ES_') or key == 'ELASTIC_ADMIN_API_KEY':
                if 'KEY' in key:
                    print(f"  {key}=******")
                else:
                    print(f"  {key}={value}")
        print("")
    
    setup_datastream_cmd = f"{sys.executable} setup_datastream.py --namespace {namespace} {logsdb_arg}"
    if args.debug:
        setup_datastream_cmd += " --debug"
    
    try:
        setup_datastream_result = run_command(setup_datastream_cmd, shell=True)
        
        if not setup_datastream_result:
            colored_print("Error: Failed to set up data stream.", Colors.RED)
            if not args.no_cleanup:
                restore_env_file()
            sys.exit(1)
    except Exception as e:
        colored_print(f"Exception during data stream setup: {e}", Colors.RED)
        if not args.no_cleanup:
            restore_env_file()
        sys.exit(1)
    
    # Export environment variables for docker-compose
    os.environ["LOG_TYPE"] = log_type
    os.environ["ES_DATA_STREAM_NAMESPACE"] = namespace
    
    # Start the containers
    print("Starting Docker containers...")
    start_result = run_command("docker-compose --env-file .env up -d")
    
    if not start_result:
        colored_print("Error: Failed to start Docker containers.", Colors.RED)
        if not args.no_cleanup:
            restore_env_file()
        sys.exit(1)
    
    # Wait for Logstash to initialize
    print("Waiting for Logstash to initialize (30 seconds)...")
    time.sleep(30)
    
    # Check if services are running
    logstash_running = run_command("docker-compose ps | grep logstash", shell=True, capture_output=True)
    log_sender_running = run_command("docker-compose ps | grep log-sender", shell=True, capture_output=True)
    
    if not logstash_running:
        colored_print("Error: Logstash container is not running.", Colors.RED)
        run_command("docker-compose logs logstash")
        if not args.no_cleanup:
            run_command("docker-compose down")
            restore_env_file()
        sys.exit(1)
    
    if not log_sender_running:
        colored_print("Error: Log-sender container did not start.", Colors.RED)
        run_command("docker-compose logs log-sender")
        if not args.no_cleanup:
            run_command("docker-compose down")
            restore_env_file()
        sys.exit(1)
    
    # Check log-sender container environment
    print("Checking log-sender container environment:")
    run_command("docker-compose exec log-sender env | grep LOG_TYPE", shell=True)
    
    # Construct the data stream name
    data_stream = f"logs-syslog-{namespace}"
    
    # Print Elasticsearch query information
    print("")
    print("┌─────────────────────────────────────────────────────────────────┐")
    print("│                 ELASTICSEARCH QUERY INFORMATION                  │")
    print("├─────────────────────────────────────────────────────────────────┤")
    print(f"│ Elasticsearch URL:      {os.environ.get('ES_ENDPOINT')}:{os.environ.get('ES_PORT', '9200')}")
    print(f"│ Data stream:            {data_stream}")
    print(f"│ Using LogsDB mode:      {use_logsdb}")
    print(f"│ Log Type:               {log_type}")
    print(f"│ Namespace:              {namespace} (includes log type)")
    print("└─────────────────────────────────────────────────────────────────┘")
    print("")
    
    # Wait for log-sender to start sending logs
    print("Waiting for log-sender to start sending logs (10 seconds)...")
    time.sleep(10)
    
    # Monitor log count with the test script
    print("Monitoring log count until ingestion is complete (10 seconds with no new logs)...")
    try:
        run_command(f"{sys.executable} test_count_logs.py --namespace {namespace} --watch --interval 2 --timeout 300 --no-change-timeout 10", shell=True)
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user.")
    
    # Final check for log count
    print("Performing final log count check...")
    final_count_output = run_command(f"{sys.executable} test_count_logs.py --namespace {namespace}", shell=True, capture_output=True)
    
    final_count = 0
    if final_count_output:
        count_match = re.search(r"Log count for.*: (\d+)", final_count_output)
        if count_match:
            final_count = int(count_match.group(1))
    
    # Check if we have logs
    if final_count > 0:
        colored_print(f"Test PASSED: Successfully ingested {final_count} logs into Elasticsearch", Colors.GREEN)
        test_result = "PASSED"
    else:
        colored_print("Test FAILED: No logs were ingested into Elasticsearch", Colors.RED)
        test_result = "FAILED"
    
    # Generate a test report
    create_test_report(data_stream, use_logsdb, log_type, final_count, test_result)
    
    # Cleanup if not disabled
    if not args.no_cleanup:
        print("Cleaning up...")
        run_command("docker-compose down")
        restore_env_file()
    else:
        print("Cleanup skipped (--no-cleanup). Containers left running and .env not restored.")
    
    colored_print("Test completed!", Colors.GREEN)
    
    # Exit with appropriate exit code
    sys.exit(0 if test_result == "PASSED" else 1)

if __name__ == "__main__":
    main()