#!/usr/bin/env python3
import os
import sys
import requests
import tarfile
from tqdm import tqdm
import concurrent.futures
import argparse
import shutil

# URLs for the log files
LOG_FILES = {
    "windows": "https://zenodo.org/records/8196385/files/Windows.tar.gz?download=1",
    "linux": "https://zenodo.org/records/8196385/files/Linux.tar.gz?download=1",
    "mac": "https://zenodo.org/records/8196385/files/Mac.tar.gz?download=1",
    "ssh": "https://zenodo.org/records/8196385/files/SSH.tar.gz?download=1",
    "apache": "https://zenodo.org/records/8196385/files/Apache.tar.gz?download=1"
}

def download_file(url, archive_dir):
    """
    Download a file from a URL with progress bar to the archive directory
    """
    # Get the filename from the URL
    filename = url.split('/')[-1].split('?')[0]
    output_path = os.path.join(archive_dir, filename)
    
    # Get base name without extension (e.g., "Linux" from "Linux.tar.gz")
    base_name = filename.split('.')[0]
    
    print(f"Checking for existing archive for: {base_name}")
    
    # Check if the tar.gz file already exists in the archive
    if os.path.exists(output_path):
        print(f"Archive {filename} already exists in archive directory. Skipping download.")
        return output_path
    
    print(f"Downloading {filename} to archive directory...")
    
    # Stream the download with progress bar
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte
    
    with open(output_path, 'wb') as file, tqdm(
            desc=filename,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
        for data in response.iter_content(block_size):
            size = file.write(data)
            bar.update(size)
    
    return output_path

def extract_tarfile(file_path, output_dir):
    """
    Extract a tar.gz file
    """
    if file_path is None:
        return
        
    print(f"Extracting {os.path.basename(file_path)} to {output_dir}...")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with tarfile.open(file_path, "r:gz") as tar:
        tar.extractall(path=output_dir)
    
    print(f"Extracted {os.path.basename(file_path)}")

def check_existing_logs(log_dir, log_type):
    """
    Check if logs for the specified type already exist in the logs directory
    """
    if log_type == 'all':
        for log_type_name in LOG_FILES.keys():
            # Check if a directory with this log type exists
            type_dir = os.path.join(log_dir, log_type_name.capitalize())
            if os.path.exists(type_dir) and len(os.listdir(type_dir)) > 0:
                print(f"Found existing logs for {log_type_name} in {type_dir}")
                continue
            
            # Check for log files with this type in the name
            matching_files = any(
                f.lower().startswith(log_type_name.lower()) and f.endswith('.log')
                for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))
            )
            
            if not matching_files:
                # No logs found for this type
                return False
        
        # All log types found
        return True
    else:
        # Check for a specific log type
        type_dir = os.path.join(log_dir, log_type.capitalize())
        if os.path.exists(type_dir) and len(os.listdir(type_dir)) > 0:
            return True
        
        # Check for log files with this type in the name
        matching_files = any(
            f.lower().startswith(log_type.lower()) and f.endswith('.log')
            for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))
        )
        
        return matching_files

def main():
    parser = argparse.ArgumentParser(description='Download and extract log files')
    parser.add_argument('--log-type', dest='log_type', choices=['windows', 'linux', 'mac', 'ssh', 'apache', 'all'], 
                      help='Type of log to download (windows, linux, mac, ssh, apache or all)', default='all')
    parser.add_argument('--output-dir', dest='output_dir', help='Output directory',
                      default="/logs")
    parser.add_argument('--archive-dir', dest='archive_dir', help='Archive directory for downloaded files',
                      default="/archive")
    parser.add_argument('--force-download', dest='force_download', action='store_true',
                      help='Force download even if archives exist')
    
    args = parser.parse_args()
    
    # Use the output_dir and archive_dir from args
    output_dir = args.output_dir
    archive_dir = args.archive_dir
    
    # Create directories if they don't exist
    for directory in [output_dir, archive_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")
    
    # List current directory contents before starting
    print(f"Current contents of archive directory {archive_dir}:")
    for item in os.listdir(archive_dir):
        item_path = os.path.join(archive_dir, item)
        if os.path.isdir(item_path):
            print(f"  DIR: {item}")
        else:
            print(f"  FILE: {item} ({os.path.getsize(item_path)} bytes)")
    
    print(f"Current contents of logs directory {output_dir}:")
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path):
            print(f"  DIR: {item}")
        else:
            print(f"  FILE: {item} ({os.path.getsize(item_path)} bytes)")
    
    # Check if logs already exist and skip if they do
    if not args.force_download and check_existing_logs(output_dir, args.log_type):
        print(f"Logs for {args.log_type} already exist in {output_dir}. Skipping download and extraction.")
        return
    
    # Select which logs to download
    if args.log_type == 'all':
        urls = list(LOG_FILES.values())
        log_types = list(LOG_FILES.keys())
    else:
        if args.log_type in LOG_FILES:
            urls = [LOG_FILES[args.log_type]]
            log_types = [args.log_type]
        else:
            print(f"Error: Invalid log type '{args.log_type}'")
            sys.exit(1)
    
    # Download and extract files
    for url, log_type in zip(urls, log_types):
        try:
            # Download file to archive directory (or use existing archive)
            archive_path = download_file(url, archive_dir)
            
            # Extract the file to output directory
            if archive_path:
                extract_tarfile(archive_path, output_dir)
        except Exception as e:
            print(f"Error processing {url}: {e}")
    
    # List contents of output directory after processing
    print("\nFinal contents of logs directory:")
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path):
            file_count = sum(len(files) for _, _, files in os.walk(item_path))
            print(f"  DIR: {item} ({file_count} files)")
        else:
            print(f"  FILE: {item} ({os.path.getsize(item_path)} bytes)")

if __name__ == "__main__":
    main()