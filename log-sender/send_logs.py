#!/usr/bin/env python3
import os
import sys
import time
import socket
import argparse
import logging
import datetime
import glob
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("log-sender")

def get_hostname_from_log(line):
    """Extract hostname from syslog line if present"""
    try:
        # Attempt to extract hostname (assuming standard syslog format)
        parts = line.split(' ', 3)
        if len(parts) >= 3:
            return parts[1]
        return 'unknown-host'
    except:
        return 'unknown-host'

def format_syslog_message(line, host=None):
    """
    Format message in syslog format if it isn't already
    """
    # Check if line is empty
    if line.strip() == '':
        return None
        
    # If the line already starts with a date (like "Jan 15"), assume it's already in syslog format
    if line[:6].find(' ') > 0 and line[0].isalpha():
        # Extract hostname if not provided
        if not host:
            host = get_hostname_from_log(line)
        return line
    
    # Otherwise, add timestamp and hostname
    timestamp = datetime.datetime.now().strftime("%b %d %H:%M:%S")
    if not host:
        host = socket.gethostname()
    
    return f"{timestamp} {host} {line}"

def send_log(sock, logstash_host, logstash_port, line, protocol='tcp'):
    """Send a log line to the syslog server"""
    try:
        if protocol.lower() == 'tcp':
            sock.send((line + '\n').encode('utf-8', errors='replace'))
        else:  # UDP
            sock.sendto((line + '\n').encode('utf-8', errors='replace'), (logstash_host, logstash_port))
        return True
    except Exception as e:
        logger.error(f"Error sending log: {e}")
        return False

def find_log_files(log_dir, log_type):
    """Find log files based on log type"""
    log_files = []
    log_type_lower = log_type.lower()
    
    logger.info(f"Looking for log files of type '{log_type}' in {log_dir}")
    
    if log_type_lower == 'all':
        # Get all log files
        log_files = glob.glob(f"{log_dir}/**/*.log", recursive=True)
        log_files.extend(glob.glob(f"{log_dir}/*.log"))
        logger.info(f"Found {len(log_files)} log files for all types")
    else:
        # Look for the specific type's directory
        type_dir = os.path.join(log_dir, log_type.capitalize())
        if os.path.exists(type_dir):
            logger.info(f"Found directory for {log_type}: {type_dir}")
            log_files.extend(glob.glob(f"{type_dir}/**/*.log", recursive=True))
        
        # Look for files with the log type in their name
        main_log_file = os.path.join(log_dir, f"{log_type}.log")
        main_log_file_cap = os.path.join(log_dir, f"{log_type.capitalize()}.log")
        
        if os.path.exists(main_log_file):
            logger.info(f"Found main log file: {main_log_file}")
            log_files.append(main_log_file)
        
        if os.path.exists(main_log_file_cap) and main_log_file_cap != main_log_file:
            logger.info(f"Found capitalized log file: {main_log_file_cap}")
            log_files.append(main_log_file_cap)
        
        # Search for files that start with the log type
        for log_file in glob.glob(f"{log_dir}/*.log"):
            file_basename = os.path.basename(log_file).lower()
            if file_basename.startswith(log_type_lower) and log_file not in log_files:
                logger.info(f"Found matching log file: {log_file}")
                log_files.append(log_file)
        
        # Search subdirectories too
        for log_file in glob.glob(f"{log_dir}/**/*.log", recursive=True):
            file_basename = os.path.basename(log_file).lower()
            if file_basename.startswith(log_type_lower) and log_file not in log_files:
                logger.info(f"Found matching log file in subdirectory: {log_file}")
                log_files.append(log_file)
    
    # Remove duplicates while preserving order
    unique_files = []
    for file_path in log_files:
        if file_path not in unique_files:
            unique_files.append(file_path)
    
    # Log what we found
    if not unique_files:
        logger.warning(f"No log files found for type '{log_type}'")
    else:
        logger.info(f"Found {len(unique_files)} unique log files for type '{log_type}':")
        for log_file in unique_files:
            logger.info(f"  - {log_file}")
    
    return unique_files

def main():
    parser = argparse.ArgumentParser(description='Send log files to syslog server')
    parser.add_argument('--host', dest='host', help='Logstash host', 
                        default=os.environ.get('LOGSTASH_HOST', 'logstash'))
    parser.add_argument('--port', dest='port', type=int, help='Logstash port', 
                        default=int(os.environ.get('LOGSTASH_PORT', 5514)))
    parser.add_argument('--log-dir', dest='log_dir', help='Log directory', 
                        default=os.environ.get('LOG_DIR', '/logs'))
    parser.add_argument('--interval', dest='interval', type=float, help='Seconds between log sends (0 for no delay)', 
                        default=float(os.environ.get('LOG_SEND_INTERVAL', 0)))
    parser.add_argument('--protocol', dest='protocol', help='Protocol (tcp or udp)', 
                        default=os.environ.get('PROTOCOL', 'tcp'))
    parser.add_argument('--loop', dest='loop', action='store_true', help='Loop through logs continuously')
    parser.add_argument('--log-type', dest='log_type', help='Log type to filter (windows, linux, mac, all)', 
                        default=os.environ.get('LOG_TYPE', 'all'))
    parser.add_argument('--delete-after-send', dest='delete_after_send', action='store_true',
                        help='Delete log files after sending', default=False)
    parser.add_argument('--keep-logs', dest='keep_logs', action='store_true',
                        help='Keep log files after sending (overrides delete-after-send)', default=True)
    
    args = parser.parse_args()
    
    # Display starting configuration
    logger.info("=== Log Sender Configuration ===")
    logger.info(f"Logstash Host: {args.host}")
    logger.info(f"Logstash Port: {args.port}")
    logger.info(f"Log Directory: {args.log_dir}")
    logger.info(f"Log Type: {args.log_type}")
    logger.info(f"Protocol: {args.protocol}")
    logger.info(f"Interval: {args.interval} seconds")
    logger.info(f"Loop Mode: {args.loop}")
    logger.info(f"Delete After Send: {args.delete_after_send and not args.keep_logs}")
    
    # Determine whether to delete logs after sending
    delete_after_send = args.delete_after_send and not args.keep_logs
    
    # Create socket based on protocol
    if args.protocol.lower() == 'tcp':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((args.host, args.port))
            logger.info(f"Connected to syslog server at {args.host}:{args.port} via TCP")
        except Exception as e:
            logger.error(f"Failed to connect to syslog server: {e}")
            sys.exit(1)
    else:  # UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.info(f"Created UDP socket for syslog server at {args.host}:{args.port}")
    
    # Find log files for the specified type
    log_files = find_log_files(args.log_dir, args.log_type)
    
    if not log_files:
        logger.error(f"No log files found for type '{args.log_type}' in {args.log_dir}")
        sys.exit(1)
    
    # Track files that have been processed and can be deleted
    processed_files = []
    
    # Process each log file
    while True:
        total_sent = 0
        total_lines = 0
        
        for log_file in log_files:
            filename = os.path.basename(log_file)
            hostname = filename.split('.')[0]  # Use filename as hostname
            
            try:
                # Count lines for progress bar
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    line_count = sum(1 for _ in f)
                
                logger.info(f"Processing {filename} ({line_count} lines)")
                
                # Open file again to read content
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    for line in tqdm(f, total=line_count, desc=filename):
                        total_lines += 1
                        formatted_line = format_syslog_message(line.strip(), hostname)
                        
                        if formatted_line:
                            if send_log(sock, args.host, args.port, formatted_line, args.protocol):
                                total_sent += 1
                            
                            # Add delay if specified
                            if args.interval > 0:
                                time.sleep(args.interval)
                
                # Add file to processed list for deletion
                if delete_after_send and log_file not in processed_files:
                    processed_files.append(log_file)
            
            except Exception as e:
                logger.error(f"Error processing {log_file}: {e}")
        
        logger.info(f"Sent {total_sent} of {total_lines} log lines to syslog server")
        
        # Delete processed files if requested
        if delete_after_send and processed_files:
            logger.info(f"Deleting {len(processed_files)} processed log files")
            for file_path in processed_files:
                try:
                    # Check if the file still exists (may be deleted in a previous loop)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
            
            # Empty the processed files list
            processed_files = []
            
            # Update the list of log files (remove deleted files)
            if args.loop:
                log_files = [f for f in log_files if os.path.exists(f)]
                logger.info(f"Updated log file list: {len(log_files)} files remaining")
                
                # Exit if no log files remain
                if not log_files:
                    logger.info("No log files remaining. Exiting.")
                    break
        
        if not args.loop:
            break
        
        logger.info("Completed one cycle. Looping back to the beginning...")
        time.sleep(5)  # Wait 5 seconds before restarting
    
    # Close socket when done
    if args.protocol.lower() == 'tcp':
        sock.close()
    
    logger.info("Log sending completed")

if __name__ == "__main__":
    main()