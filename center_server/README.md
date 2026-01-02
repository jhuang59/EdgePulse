# EdgePulse Center Server

The central hub for EdgePulse that collects monitoring data, provides a web dashboard, and coordinates remote commands and shell access to edge devices.

## Features

- **Log Collection**: REST API to receive benchmark data from clients
- **Client Monitoring**: Track active clients with heartbeat mechanism
- **Real-time Dashboard**: Interactive charts and statistics
- **Remote Commands**: Execute whitelisted commands on clients
- **Web Shell**: Interactive terminal access via WebSocket
- **Admin Authentication**: API key-based access control
- **Audit Logging**: Complete audit trail of all activities

---

## Quick Start

### 1. Deploy the Server

```bash
cd center_server
docker-compose up -d --build
```

### 2. Initialize Admin Account

```bash
curl -X POST http://localhost:5000/api/admin/init \
  -H "Content-Type: application/json" \
  -d '{"admin_name": "admin"}'
```

**Save the `api_key` returned!**

### 3. Register Clients

```bash
curl -X POST http://localhost:5000/api/clients/register \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: YOUR_ADMIN_KEY" \
  -d '{"client_id": "my-client"}'
```

**Save the `secret_key` returned!**

### 4. Access Dashboard

Open `http://localhost:5000` in your browser.

---

## Dashboard Usage

### Monitoring Tab

View network performance metrics:

1. **Statistics Cards**: Show total records, packet loss %, and latency
2. **Active Clients Table**: Lists all clients with online/offline status
3. **Charts**: Visualize packet loss and latency trends
4. **Filters**:
   - Select specific client or "All Clients"
   - Choose time range (50, 100, 200, 500 records)

### Remote Commands Tab

Execute commands on remote clients:

1. **Enter Admin API Key**: Paste your key and click "Save Key"
2. **Select Target Client**: Choose from dropdown
3. **Select Command**: Pick from categorized whitelist
4. **Enter Parameters**: Fill in required values (e.g., target IP for ping)
5. **Click "Send Command"**
6. **View Results**: Results appear in the table below

### Web Shell Tab

Open interactive terminal sessions:

1. **First**: Save your Admin API Key in Remote Commands tab
2. **Select Client**: Choose an online client from dropdown
3. **Click "Connect"**: Opens terminal session
4. **Use Terminal**: Type commands, full shell access
5. **Click "Disconnect"**: Close session (or Ctrl+D)

**Requirements:**
- Admin API Key must be saved first
- Client must be online
- Client must have `web_shell_enabled: true`

---

## API Reference

### Authentication

**Admin Authentication:**
```
Header: X-Admin-API-Key: <your-admin-key>
```

**Client Authentication:**
```
Header: X-Client-ID: <client-id>
Header: X-Client-API-Key: <secret-key>
```

---

### Admin Management

#### POST /api/admin/init
Initialize first admin account (only works once).

**Request:**
```bash
curl -X POST http://localhost:5000/api/admin/init \
  -H "Content-Type: application/json" \
  -d '{"admin_name": "admin"}'
```

**Response:**
```json
{
  "status": "success",
  "api_key": "generated-api-key",
  "admin_name": "admin"
}
```

#### POST /api/admin/create
Create additional admin (requires admin auth).

**Request:**
```bash
curl -X POST http://localhost:5000/api/admin/create \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: YOUR_KEY" \
  -d '{"admin_name": "admin2"}'
```

---

### Client Registration

#### POST /api/clients/register
Register a new client (requires admin auth).

**Request:**
```bash
curl -X POST http://localhost:5000/api/clients/register \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: YOUR_KEY" \
  -d '{"client_id": "jetbot-01"}'
```

**Response:**
```json
{
  "status": "success",
  "client_id": "jetbot-01",
  "secret_key": "generated-secret-key"
}
```

#### GET /api/clients/registered
List all registered clients (requires admin auth).

#### POST /api/clients/{client_id}/revoke
Revoke a client's access (requires admin auth).

---

### Monitoring Endpoints

#### POST /api/logs
Receive benchmark logs from clients.

**Request Body:**
```json
{
  "timestamp": "2025-01-02T10:00:00",
  "client_id": "jetbot-01",
  "router1": {
    "router": "Router 1",
    "packet_loss_pct": 0.0,
    "avg_ms": 15.5
  },
  "router2": {
    "router": "Router 2",
    "packet_loss_pct": 0.0,
    "avg_ms": 18.2
  }
}
```

#### GET /api/data
Get benchmark data for visualization.

**Query Parameters:**
- `limit` (optional): Number of records (default: 100)
- `client_id` (optional): Filter by client

#### GET /api/stats
Get summary statistics.

**Query Parameters:**
- `client_id` (optional): Filter by client

#### POST /api/heartbeat
Receive heartbeat from clients.

**Request Body:**
```json
{
  "client_id": "jetbot-01",
  "hostname": "jetbot",
  "router1_interface": "usb0",
  "router2_interface": "wlan0"
}
```

#### GET /api/clients
Get list of clients with status.

**Query Parameters:**
- `timeout` (optional): Seconds to consider offline (default: 120)

#### GET /health
Health check endpoint.

---

### Command Endpoints

#### GET /api/commands/whitelist
Get available commands (no auth required).

**Response:**
```json
{
  "commands": [
    {
      "id": "system_info",
      "description": "Get system kernel and OS info",
      "category": "system",
      "params": [],
      "timeout": 10
    }
  ],
  "total": 22
}
```

#### POST /api/commands/send
Queue a command (requires admin auth).

**Request:**
```bash
curl -X POST http://localhost:5000/api/commands/send \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: YOUR_KEY" \
  -d '{
    "client_id": "jetbot-01",
    "command_id": "ping_test",
    "params": {"target": "8.8.8.8", "count": "4"}
  }'
```

#### GET /api/commands/poll
Client polls for commands (requires client auth).

#### POST /api/commands/result
Client submits result (requires client auth).

#### GET /api/commands/results
Get command results (requires admin auth).

**Query Parameters:**
- `client_id` (optional): Filter by client
- `limit` (optional): Max results (default: 100)

#### GET /api/commands/results/{command_uuid}
Get specific result (requires admin auth).

#### GET /api/commands/audit
Get audit log (requires admin auth).

---

## Available Commands

### System Commands

| Command | Description | Parameters |
|---------|-------------|------------|
| `system_info` | OS and kernel info | - |
| `hostname` | Machine hostname | - |
| `uptime` | System uptime | - |
| `disk_usage` | Disk usage | - |
| `memory_info` | Memory usage | - |
| `cpu_info` | CPU information | - |
| `process_list` | Top processes | - |
| `date_time` | Current date/time | - |

### Network Commands

| Command | Description | Parameters |
|---------|-------------|------------|
| `network_interfaces` | List interfaces | - |
| `routing_table` | Show routes | - |
| `dns_config` | DNS settings | - |
| `network_stats` | Network statistics | - |
| `ping_test` | Ping a host | `target`, `count` |
| `traceroute` | Trace route | `target` |
| `interface_stats` | Interface stats | `interface` |
| `connection_count` | Socket stats | - |
| `arp_table` | ARP table | - |

### Docker Commands

| Command | Description |
|---------|-------------|
| `docker_ps` | List containers |
| `docker_stats` | Container resources |

### Benchmark Commands

| Command | Description |
|---------|-------------|
| `benchmark_status` | Check if running |
| `benchmark_logs` | Show recent logs |

---

## Data Storage

Data is stored in `/app/data/`:

| File | Description |
|------|-------------|
| `benchmark_data.jsonl` | Benchmark results |
| `clients.json` | Client registry |
| `admin_secrets.json` | Admin API keys |
| `client_secrets.json` | Client secrets |
| `pending_commands.json` | Queued commands |
| `command_results.jsonl` | Execution results |
| `command_audit.jsonl` | Audit log |

---

## Server Management

### View logs
```bash
docker-compose logs -f
```

### Stop server
```bash
docker-compose down
```

### Restart server
```bash
docker-compose restart
```

### Rebuild after changes
```bash
docker-compose down
docker-compose up -d --build
```

### Clear all data
```bash
rm -rf data/*
docker-compose restart
```

---

## Troubleshooting

### Clients can't connect
- Check firewall (port 5000)
- Verify server IP in client config
- Check server is running: `docker-compose ps`
- Check logs: `docker-compose logs`

### Authentication errors
- Verify admin API key is correct
- Verify client `secret_key` matches registration
- Check if client was revoked

### Commands not executing
- Verify `remote_commands_enabled: true` on client
- Verify `secret_key` is correct
- Check client logs for errors

### Web Shell not connecting
- Save Admin API Key in Remote Commands tab first
- Verify `web_shell_enabled: true` on client
- Check client is online (green status in dashboard)
- Check browser dev tools for WebSocket errors
- Check server logs for shell-related errors

### No data in dashboard
- Verify clients are sending data
- Check: `cat data/benchmark_data.jsonl`
- Check browser console for errors
