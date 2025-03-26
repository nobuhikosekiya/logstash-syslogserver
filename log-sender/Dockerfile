FROM python:3.9-slim

WORKDIR /app

# Install required packages - removed netcat
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        rsyslog \
        curl \
        tar \
        logrotate \
        coreutils \
        ca-certificates \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create log directory
RUN mkdir -p /logs

# Copy the scripts
COPY download_logs.py /app/
COPY send_logs.py /app/
COPY requirements.txt /app/
COPY entrypoint.sh /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set executable permissions
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV LOGSTASH_HOST=logstash
ENV LOGSTASH_PORT=5514
ENV DOWNLOAD_LOGS=true
ENV LOG_SEND_INTERVAL=0
ENV LOG_TYPE=all