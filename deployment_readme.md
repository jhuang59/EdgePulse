# Router Ping Benchmark - Deployment Guide

## Overview
This containerized solution benchmarks two routers by pinging internet targets through each router's gateway and interface. It runs continuously, summarizing results and storing them for analysis.

## Prerequisites
- Upper computer(ubuntu) with two network interfaces (one per router)
- Docker and Docker Compose installed
- Both routers providing internet access

## Quick Start

### 1. Install Docker (already installed)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### 2. Install Docker Compose (already installed)
```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### 3. Create Project Directory
```bash
mkdir -p ~/router-benchmark
cd ~/router-benchmark
```

### 4. Create Project Files
SCP the following files in the `~/router-benchmark` directory:
- `Dockerfile`
- `ping_benchmark.py`
- `config.json`
- `docker-compose.yml`

### 5. Configure Your Routers (already configured)
Edit `config.json` to match your setup:

```json
{
  "router1": {
    "gateway": "192.168.1.1",     // Your router 1 gateway IP
    "interface": "eth0"             // Network interface for router 1
  },
  "router2": {
    "gateway": "192.168.2.1",     // Your router 2 gateway IP
    "interface": "eth1"             // Network interface for router 2
  },
  "ping_target": "8.8.8.8",       // Target to ping (Google DNS)
  "ping_count": 20,                // Number of pings per test
  "test_interval_seconds": 300,    // Time between tests (5 minutes)
  "results_dir": "/app/results"
}
```

### 6. Deploy the Container
```bash
cd ~/router-benchmark
docker-compose up -d
```

### 7. View Logs
```bash
# View live logs
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `gateway` | Router gateway IP address | 192.168.1.1 |
| `interface` | Network interface name | eth0 |
| `ping_target` | Internet target to ping | 8.8.8.8 |
| `ping_count` | Number of pings per test | 20 |
| `test_interval_seconds` | Seconds between tests | 300 (5 min) |
| `results_dir` | Results storage directory | /app/results |

**Alternative Ping Targets:**
- `1.1.1.1` - Cloudflare DNS
- `208.67.222.222` - OpenDNS
- `www.google.com` - Google web server

## Results

### Result Files
Results are stored in `./results/`:
- `benchmark_YYYYMMDD_HHMMSS.json` - Individual test results
- `benchmark_log.jsonl` - Cumulative log of all tests (one JSON per line)

### Example Output
```
==========================================================
BENCHMARK SUMMARY
==========================================================

Router 1:
  Interface: eth0
  Gateway: 192.168.1.1
  Packet Loss: 0.0%
  Latency:
    Min:    15.23 ms
    Avg:    18.45 ms
    Median: 17.89 ms
    Max:    25.67 ms
    StdDev: 2.34 ms

Router 2:
  Interface: eth1
  Gateway: 192.168.2.1
  Packet Loss: 5.0%
  Latency:
    Min:    20.12 ms
    Avg:    28.91 ms
    Median: 27.45 ms
    Max:    45.23 ms
    StdDev: 6.78 ms

==========================================================
COMPARISON:
==========================================================
Router 1 is FASTER by 10.46 ms average
Router 1 has BETTER packet loss by 5.0%
```

## Management Commands

### Start the Container
```bash
docker-compose up -d
```

### Stop the Container
```bash
docker-compose down
```

### Restart the Container
```bash
docker-compose restart
```

### View Real-time Logs
```bash
docker-compose logs -f
```

### Check Container Status
```bash
docker-compose ps
```

### Update Configuration
1. Edit `config.json`
2. Restart container: `docker-compose restart`

### Remove Everything (including results)
```bash
docker-compose down -v
rm -rf results/
```

## Analyzing Results

### View Latest Test
```bash
cat results/benchmark_*.json | tail -n 1 | jq .
```

### Count Total Tests
```bash
wc -l results/benchmark_log.jsonl
```

### Extract All Router 1 Average Latencies
```bash
cat results/benchmark_log.jsonl | jq -r '.router1.avg_ms' | grep -v null
```

### Calculate Overall Average for Router 1
```bash
cat results/benchmark_log.jsonl | jq -r '.router1.avg_ms' | grep -v null | awk '{sum+=$1; count++} END {print sum/count}'
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs for errors
docker-compose logs

# Verify network interfaces exist
ip addr show

# Test ping manually
ping -I eth0 -c 4 8.8.8.8
```

### No Results Being Generated
```bash
# Check if container is running
docker compose ps

# Check permissions on results directory
ls -la results/

# Verify config.json is valid JSON
cat config.json | jq .
```

### High Packet Loss on Both Routers
- Check physical connections
- Verify internet connectivity: `ping 8.8.8.8`
- Test if gateway is reachable: `ping -c 4 192.168.1.1`

## Network Configuration Notes

The container runs in **host network mode** to access the host's network interfaces directly. This means:
- The container can see all host network interfaces
- No port mapping needed
- Requires `privileged: true` for raw socket access (ping)

## Auto-Start on Boot

The container is configured with `restart: unless-stopped`, which means it will:
- Automatically start when Docker daemon starts
- Restart if it crashes
- Persist across system reboots

To disable auto-start:
```bash
docker-compose stop
```


