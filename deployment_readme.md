# Router Ping Benchmark - Deployment Guide

## Overview
This distributed system benchmarks router performance across multiple locations with centralized visualization and remote command execution.

**Architecture:**
- **Stage 1 (Clients)**: Benchmark clients deployed on machines with multiple network interfaces
- **Stage 2 (Server)**: Center server that collects logs, provides visualization, and sends remote commands

## Prerequisites
- **For Clients**: Ubuntu computer with two network interfaces (one per router)
- **For Server**: Any machine (cloud or local) with Docker installed
- Docker and Docker Compose installed on all machines
- Network connectivity between clients and server

## Deployment Overview

**Recommended deployment order:**
1. Deploy center server first (Stage 2)
2. Initialize admin account
3. Register clients
4. Configure and deploy benchmark clients (Stage 1)
5. Access the web dashboard to view results and send commands

---

## Stage 2: Deploy Center Server

### 1. Prepare Server Machine
```bash
# Create project directory
mkdir -p ~/router-benchmark-center
cd ~/router-benchmark-center

# Copy center_server files to this directory
# You need: center_server/ directory with all its contents
```

### 2. Deploy Center Server
```bash
cd ~/router-benchmark-center/center_server
docker-compose up -d
```

### 3. Verify Server is Running
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs -f

# Test API endpoint
curl http://localhost:5000/health
```

### 4. Initialize Admin Account
```bash
curl -X POST http://localhost:5000/api/admin/init \
  -H "Content-Type: application/json" \
  -d '{"admin_name": "admin"}'
```

**IMPORTANT:** Save the `api_key` from the response - you'll need it!

Example response:
```json
{
  "status": "success",
  "message": "Admin account created. SAVE THIS API KEY - it cannot be retrieved later!",
  "api_key": "a1b2c3d4e5f6...",
  "admin_name": "admin"
}
```

### 5. Access Dashboard
Open browser: `http://YOUR_SERVER_IP:5000`

**Note:** Make sure port 5000 is open in your firewall and accessible from client machines.

See [center_server/README.md](center_server/README.md) for detailed server documentation.

---

## Stage 1: Deploy Benchmark Clients

### 1. Register Client on Server

Before deploying a client, register it on the server:

```bash
curl -X POST http://YOUR_SERVER_IP:5000/api/clients/register \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: YOUR_ADMIN_API_KEY" \
  -d '{"client_id": "office-client-1"}'
```

**IMPORTANT:** Save the `secret_key` from the response!

Example response:
```json
{
  "status": "success",
  "message": "Client registered. SAVE THIS SECRET KEY - it cannot be retrieved later!",
  "client_id": "office-client-1",
  "secret_key": "x1y2z3..."
}
```

### 2. Install Docker (if not installed)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### 3. Install Docker Compose (if not installed)
```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### 4. Create Project Directory
```bash
mkdir -p ~/router-benchmark
cd ~/router-benchmark
```

### 5. Create Project Files
SCP the following files to `~/router-benchmark`:
- `Dockerfile`
- `ping_benchmark.py`
- `config.json`
- `docker-compose.yml`

### 6. Configure Your Client
Edit `config.json`:

```json
{
  "router1": {
    "gateway": "192.168.1.1",
    "interface": "eth0"
  },
  "router2": {
    "gateway": "192.168.2.1",
    "interface": "eth1"
  },
  "ping_target": "8.8.8.8",
  "ping_count": 20,
  "test_interval_seconds": 300,
  "results_dir": "/app/results",
  "center_server_url": "http://YOUR_CENTER_SERVER_IP:5000",
  "heartbeat_interval_seconds": 60,
  "client_id": "office-client-1",
  "secret_key": "YOUR_SECRET_KEY_FROM_REGISTRATION",
  "remote_commands_enabled": true,
  "command_poll_interval_seconds": 10
}
```

**Key Configuration:**
- Replace `YOUR_CENTER_SERVER_IP` with actual server IP
- Set `client_id` to match the registered name
- Set `secret_key` to the key from registration
- Set `remote_commands_enabled` to `true` to allow remote commands

### 7. Deploy the Container
```bash
cd ~/router-benchmark
docker-compose up -d
```

### 8. Verify Client is Running
```bash
# View logs
docker-compose logs -f

# You should see:
# Remote commands: ENABLED (poll interval: 10s)
# Command polling started for client: office-client-1
# Heartbeat started for client: office-client-1
```

---

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `gateway` | Router gateway IP address | 192.168.1.1 |
| `interface` | Network interface name | eth0 |
| `ping_target` | Internet target to ping | 8.8.8.8 |
| `ping_count` | Number of pings per test | 20 |
| `test_interval_seconds` | Seconds between tests | 300 (5 min) |
| `results_dir` | Results storage directory | /app/results |
| `center_server_url` | Center server URL | (required) |
| `heartbeat_interval_seconds` | Heartbeat interval | 60 |
| `client_id` | Client identifier | hostname |
| `secret_key` | Shared secret for auth | (required for commands) |
| `remote_commands_enabled` | Enable remote commands | true |
| `command_poll_interval_seconds` | Command poll interval | 10 |

---

## Using Remote Commands

### Via Dashboard

1. Open `http://YOUR_SERVER_IP:5000`
2. Click the "Remote Commands" tab
3. Enter your admin API key and click "Save Key"
4. Select a target client
5. Select a command from the dropdown
6. Fill in any required parameters
7. Click "Send Command"
8. View results in the "Command Results" section

### Via API

```bash
# Send a command
curl -X POST http://YOUR_SERVER_IP:5000/api/commands/send \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: YOUR_ADMIN_KEY" \
  -d '{
    "client_id": "office-client-1",
    "command_id": "system_info",
    "params": {}
  }'

# View results
curl http://YOUR_SERVER_IP:5000/api/commands/results \
  -H "X-Admin-API-Key: YOUR_ADMIN_KEY"
```

### Available Commands

| Category | Commands |
|----------|----------|
| System | `system_info`, `hostname`, `uptime`, `disk_usage`, `memory_info`, `cpu_info`, `process_list`, `date_time` |
| Network | `network_interfaces`, `routing_table`, `dns_config`, `network_stats`, `ping_test`, `traceroute`, `interface_stats`, `connection_count`, `arp_table` |
| Docker | `docker_ps`, `docker_stats` |
| Benchmark | `benchmark_status`, `benchmark_logs` |

See [center_server/REMOTE_COMMANDS_README.md](center_server/REMOTE_COMMANDS_README.md) for complete documentation.

---

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

---

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

### Remote Commands Not Working
```bash
# Check client logs
docker-compose logs | grep -i command

# Verify secret_key is set
cat config.json | jq '.secret_key'

# Verify remote_commands_enabled is true
cat config.json | jq '.remote_commands_enabled'
```

### Authentication Errors
- Verify `client_id` matches the registered name exactly
- Verify `secret_key` matches the one from registration
- Check if the client was revoked on the server
- Ensure server and client clocks are synchronized (within 5 minutes)

### High Packet Loss on Both Routers
- Check physical connections
- Verify internet connectivity: `ping 8.8.8.8`
- Test if gateway is reachable: `ping -c 4 192.168.1.1`

---

## Network Configuration Notes

The container runs in **host network mode** to access the host's network interfaces directly. This means:
- The container can see all host network interfaces
- No port mapping needed
- Requires `privileged: true` for raw socket access (ping)

---

## Security Notes

### Protect Your Keys
- Admin API keys grant full control over the server
- Client secret keys allow command execution on that client
- Store keys securely, never commit to version control

### Command Whitelist
- Only pre-approved commands can be executed
- Commands are defined in `center_server/command_whitelist.json`
- Modify the whitelist to add/remove allowed commands

### Mutual Authentication
- Clients verify server signatures before executing commands
- Prevents malicious actors from sending fake commands
- Replay attacks are prevented with timestamps and nonces

---

## Auto-Start on Boot

The container is configured with `restart: unless-stopped`, which means it will:
- Automatically start when Docker daemon starts
- Restart if it crashes
- Persist across system reboots

To disable auto-start:
```bash
docker-compose stop
```
