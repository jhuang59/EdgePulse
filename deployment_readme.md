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
  "command_poll_interval_seconds": 10,
  "web_shell_enabled": true,
  "geolocation": {
    "source": "disabled",
    "ros": {
      "container_name": "ros_container",
      "topic": "/gps/fix"
    },
    "sim7600": {
      "serial_port": "/dev/ttyUSB2",
      "baud_rate": 115200
    }
  }
}
```

**Key Configuration:**
- Replace `YOUR_CENTER_SERVER_IP` with actual server IP
- Set `client_id` to match the registered name
- Set `secret_key` to the key from registration
- Set `remote_commands_enabled` to `true` to allow remote commands

### 7. Deploy the Client

#### Option A: Native Deployment (Recommended for Web Shell)

Runs directly on the host — Web Shell connects to the actual host system.

```bash
# Install Python 3.7 and pip (required — Python 3.6 on Ubuntu 18.04 is not compatible)
sudo apt-get install -y python3.7 python3.7-distutils python3-pip

# Install dependencies
python3.7 -m pip install requests python-socketio websocket-client

# Set results_dir in config.json to a writable path (not /app/results)
# e.g. "results_dir": "/home/Downloads/EdgePulse/results"

# Run the client in background (logs saved to /tmp/edgepulse_client.log)
python3.7 -u /home/Downloads/EdgePulse/ping_benchmark.py > /tmp/edgepulse_client.log 2>&1 &

# Monitor logs
tail -f /tmp/edgepulse_client.log

# Stop the client
pkill -f ping_benchmark.py
```

#### Option B: Docker Deployment

Runs in a container — Web Shell connects to the container environment, not the host.

```bash
cd ~/router-benchmark
docker-compose up -d
```

### 8. Verify Client is Running
```bash
# Option A (native) - view logs
tail -f /tmp/edgepulse_client.log

# Option B (Docker) - view logs
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
| `web_shell_enabled` | Enable web shell access | true |
| `geolocation.source` | GPS source: `ros`, `sim7600`, or `disabled` | disabled |
| `geolocation.ros.container_name` | Docker container running ROS | ros_container |
| `geolocation.ros.topic` | ROS GPS topic (NavSatFix) | /gps/fix |
| `geolocation.sim7600.serial_port` | Serial port for SIM7600 | /dev/ttyUSB2 |
| `geolocation.sim7600.baud_rate` | Baud rate for SIM7600 | 115200 |

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

## GPS Module Setup (for Coverage Map)

EdgePulse supports GPS tracking to visualize where mobile hosts experience connectivity issues. Two GPS sources are supported:

### Option 1: ROS GPS (sensor_msgs/NavSatFix)

If your robot runs ROS inside a Docker container with a GPS node publishing to a topic:

#### 1. Verify ROS GPS Output

```bash
# Check if ROS container is running
docker ps | grep ros

# List available topics
docker exec ros_container rostopic list | grep -i gps

# View GPS data (run for a few seconds, then Ctrl+C)
docker exec ros_container rostopic echo -n 1 /gps/fix
```

**Expected output:**
```yaml
header:
  seq: 12345
  stamp:
    secs: 1708456789
    nsecs: 123456789
  frame_id: "gps"
status:
  status: 0
  service: 1
latitude: 35.6812
longitude: 139.7671
altitude: 45.2
position_covariance: [...]
position_covariance_type: 0
```

#### 2. Enable ROS GPS in config.json

```json
"geolocation": {
  "source": "ros",
  "ros": {
    "container_name": "ros_container",
    "topic": "/gps/fix"
  }
}
```

**Note:** The client must run **natively on the host** (not in Docker) to use `docker exec` to read from the ROS container.

---

### Option 2: SIM7600G-H 4G/GNSS Module

If your Jetson has a SIM7600G-H module connected via USB:

#### 1. Identify the Serial Port

```bash
# List USB serial devices
ls -la /dev/ttyUSB*

# Common SIM7600 ports:
# /dev/ttyUSB0 - Diagnostic port
# /dev/ttyUSB1 - NMEA GPS output
# /dev/ttyUSB2 - AT command port (use this one)
# /dev/ttyUSB3 - Modem port
```

#### 2. Enable GPS on SIM7600 (first time only)

```bash
# Install screen or minicom for serial communication
sudo apt-get install screen

# Connect to AT command port
sudo screen /dev/ttyUSB2 115200

# Enable GPS (type these commands, press Enter after each):
AT+CGPS=1

# Check GPS status
AT+CGPS?

# Response should be: +CGPS: 1,1

# Exit screen: Ctrl+A, then K, then Y
```

#### 3. Verify GPS Output

```bash
# Test GPS info (requires GPS fix - may take 30-60 seconds outdoors)
sudo screen /dev/ttyUSB2 115200

# Query GPS position
AT+CGPSINFO

# Expected response (with fix):
# +CGPSINFO: 3568.1234,N,13976.5678,E,210224,123456.0,45.2,0.5,0

# Format: lat,N/S,lon,E/W,date,time,altitude,speed,course

# No fix response:
# +CGPSINFO: ,,,,,,,,

# Exit screen: Ctrl+A, then K, then Y
```

**Tip:** GPS requires clear sky view. Cold start can take 30-60 seconds. Move outdoors for first fix.

#### 4. Enable SIM7600 GPS in config.json

```json
"geolocation": {
  "source": "sim7600",
  "sim7600": {
    "serial_port": "/dev/ttyUSB2",
    "baud_rate": 115200
  }
}
```

#### 5. Install pyserial (required for SIM7600)

```bash
pip3 install pyserial
# or
python3.7 -m pip install pyserial
```

---

### Verifying GPS Data Flow

After configuring GPS and restarting the client:

#### 1. Check Client Logs

```bash
# Native deployment
tail -f /tmp/edgepulse_client.log | grep -i geolocation

# Docker deployment
docker-compose logs -f | grep -i geolocation
```

**Expected log messages:**
```
[Geolocation] Initialized with source: ros
[Geolocation] ROS container: ros_container, topic: /gps/fix
```

#### 2. Check Coverage Data on Server

```bash
# View recent coverage points
curl http://YOUR_SERVER_IP:5000/api/coverage?hours=1 | python3 -m json.tool

# Check coverage data file directly (on server)
tail -5 center_server/data/coverage_data.jsonl
```

#### 3. View Coverage Map

1. Open dashboard: `http://YOUR_SERVER_IP:5000`
2. Click **Coverage Map** tab
3. Select your client from dropdown
4. Click **Refresh**
5. Map should show GPS points with color-coded markers

---

### GPS Data Update Frequency

| Event | Interval | GPS Included |
|-------|----------|--------------|
| Heartbeat | 60 seconds | Yes |
| Benchmark | 300 seconds (5 min) | Yes |

To increase GPS resolution, reduce `heartbeat_interval_seconds` in config.json:

```json
"heartbeat_interval_seconds": 10
```

**Note:** More frequent heartbeats increase network usage but provide finer GPS tracking.

---

## Management Commands

### Native Deployment (Option A)

#### Start the Client
```bash
python3.7 -u /home/Downloads/EdgePulse/ping_benchmark.py > /tmp/edgepulse_client.log 2>&1 &
```

#### Stop the Client
```bash
pkill -f ping_benchmark.py
```

#### Restart the Client
```bash
pkill -f ping_benchmark.py && sleep 1 && python3.7 -u /home/Downloads/EdgePulse/ping_benchmark.py > /tmp/edgepulse_client.log 2>&1 &
```

#### View Real-time Logs
```bash
tail -f /tmp/edgepulse_client.log
```

#### Update Configuration
1. Edit `config.json`
2. Restart: `pkill -f ping_benchmark.py && python3.7 -u /home/Downloads/EdgePulse/ping_benchmark.py > /tmp/edgepulse_client.log 2>&1 &`

---

### Docker Deployment (Option B)

#### Start the Container
```bash
docker-compose up -d
```

#### Stop the Container
```bash
docker-compose down
```

#### Restart the Container
```bash
docker-compose restart
```

#### View Real-time Logs
```bash
docker-compose logs -f
```

#### Check Container Status
```bash
docker-compose ps
```

#### Update Configuration
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

### GPS Not Working

#### ROS GPS Issues
```bash
# Check if ROS container is running
docker ps | grep ros

# Check if topic exists
docker exec ros_container rostopic list | grep gps

# Test reading from topic (should return data within 10 seconds)
timeout 10 docker exec ros_container rostopic echo -n 1 /gps/fix

# If timeout: ROS GPS node may not be publishing
# Check ROS node status
docker exec ros_container rosnode list
docker exec ros_container rosnode info /gps_node
```

#### SIM7600 GPS Issues
```bash
# Check if serial port exists
ls -la /dev/ttyUSB*

# Check if port is accessible (no permission denied)
sudo screen /dev/ttyUSB2 115200
# Type: AT
# Should respond: OK
# Exit: Ctrl+A, K, Y

# If permission denied, add user to dialout group:
sudo usermod -aG dialout $USER
# Log out and back in

# Check if GPS is enabled
# In screen session, type:
AT+CGPS?
# Should respond: +CGPS: 1,1

# If +CGPS: 0,1 - GPS is disabled, enable it:
AT+CGPS=1

# No GPS fix (returns empty +CGPSINFO: ,,,,,,,,)
# - Move device outdoors with clear sky view
# - Wait 30-60 seconds for cold start fix
# - Check antenna connection
```

#### GPS Data Not Appearing in Coverage Map
1. Verify `geolocation.source` is set correctly in config.json (not `disabled`)
2. Restart the client after config change
3. Check client logs for `[Geolocation]` messages
4. Wait for at least one heartbeat (60s) or benchmark (300s) cycle
5. Click **Refresh** on Coverage Map tab
6. Check API directly: `curl http://SERVER:5000/api/coverage?hours=1`

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
