#!/usr/bin/env python3
import os
import sys
import requests
import tarfile
from tqdm import tqdm
import concurrent.futures
import argparse

# URLs for the log files
LOG_FILES = {
    "windows": "https://zenodo.org/records/8196385/files/Windows.tar.gz?download=1",
    "linux": "https://zenodo.org/records/8196385/files/Linux.tar.gz?download=1",
    "mac": "https://zenodo.org/records/8196385/files/Mac.tar.gz?download=1"
}

def download_file(url, output_dir):
    """
    Download a file from a URL with progress bar
    """
    # Get the filename from the URL
    filename = url.split('/')[-1].split('?')[0]
    output_path = os.path.join(output_dir, filename)
    
    # Get base name without extension (e.g., "Linux" from "Linux.tar.gz")
    base_name = filename.split('.')[0]
    
    print(f"Checking for existing files for: {base_name}")
    
    # Check if the tar.gz file itself already exists
    if os.path.exists(output_path):
        print(f"File {filename} already exists. Skipping download.")
        return output_path
        
    # Check if a directory with the base name exists
    if os.path.exists(os.path.join(output_dir, base_name)):
        print(f"Directory {base_name} already exists. Skipping download.")
        return None
    
    # Check if any file with same base name exists (e.g., Linux.log)
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isfile(item_path):
            item_base = os.path.splitext(item)[0]
            if item_base.lower() == base_name.lower():
                print(f"File with base name {base_name} already exists ({item}). Skipping download.")
                return None
    
    print(f"Downloading {filename}...")
    
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
        
    print(f"Extracting {os.path.basename(file_path)}...")
    with tarfile.open(file_path, "r:gz") as tar:
        tar.extractall(path=output_dir)
    print(f"Extracted {os.path.basename(file_path)}")

def main():
    parser = argparse.ArgumentParser(description='Download and extract log files')
    parser.add_argument('--log-type', dest='log_type', choices=['windows', 'linux', 'mac', 'all'],
                      help='Type of log to download (windows, linux, mac, or all)', default='all')
    parser.add_argument('--output-dir', dest='output_dir', help='Output directory',
                      default="/logs")
    
    args = parser.parse_args()
    
    # Use the output_dir from args directly - no need for global
    output_dir = args.output_dir
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    # List current directory contents before starting
    print(f"Current contents of {output_dir}:")
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path):
            print(f"  DIR: {item}")
        else:
            print(f"  FILE: {item}")
    
    downloaded_files = []
    
    # Select which logs to download
    if args.log_type == 'all':
        urls = list(LOG_FILES.values())
    else:
        if args.log_type in LOG_FILES:
            urls = [LOG_FILES[args.log_type]]
        else:
            print(f"Error: Invalid log type '{args.log_type}'")
            sys.exit(1)
    
    # Print debug info
    print(f"Selected log type: {args.log_type}")
    print(f"Output directory: {output_dir}")
    print(f"URLs to download: {len(urls)}")
    
    # Download files sequentially with progress bars
    for url in urls:
        try:
            file_path = download_file(url, output_dir)
            if file_path:
                downloaded_files.append(file_path)
        except Exception as e:
            print(f"Error downloading {url}: {e}")
    
    if downloaded_files:
        print("\nAll downloads completed.")
        
        # Extract files in parallel for better performance
        print("\nExtracting files...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            for file_path in downloaded_files:
                executor.submit(extract_tarfile, file_path, output_dir)
        
        print("\nAll files have been downloaded and extracted to the output directory.")
        
        # Remove the tar.gz files after extraction
        print("\nCleaning up archive files...")
        for file_path in downloaded_files:
            os.remove(file_path)
            print(f"Removed {os.path.basename(file_path)}")
    else:
        print("\nNo new files were downloaded.")
        
    # List contents of output directory after processing
    print("\nFinal contents of output directory:")
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path):
            print(f"  DIR: {item} ({len(os.listdir(item_path))} items)")
        else:
            print(f"  FILE: {item} ({os.path.getsize(item_path)} bytes)")

if __name__ == "__main__":
    main()