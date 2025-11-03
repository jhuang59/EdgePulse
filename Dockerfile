FROM ubuntu:22.04

# Install required packages
RUN apt-get update && \
    apt-get install -y \
    iputils-ping \
    iproute2 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir schedule

# Create app directory
WORKDIR /app

# Copy the benchmark script
COPY ping_benchmark.py /app/
COPY config.json /app/

# Run the benchmark script
CMD ["python3", "-u", "ping_benchmark.py"]
