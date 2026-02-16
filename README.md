# Webmin MCP Server

An MCP (Model Context Protocol) server that provides Claude with tools to
manage Linux systems via Webmin's web-based administration interface.

## Features

- **System Monitoring**: Comprehensive system info, memory, disk, and network status
- **Service Management**: List services and check their status
- **User Administration**: List and inspect system users
- **Scheduled Tasks**: View cron jobs and schedules
- **Network Configuration**: Interface details, routing, and gateway info

## Requirements

- Python 3.11+
- A running Webmin instance (typically on port 10000)
- Webmin credentials with appropriate permissions

### Webmin Server Requirements

The MCP server uses Webmin's XML-RPC API. Ensure your Webmin server is configured:

1. **Enable RPC Access**: In Webmin → Webmin Users → (your user) → enable "Can accept RPC calls"
2. **Install XML::Parser**: The Perl XML::Parser module must be installed:
   ```bash
   # Debian/Ubuntu
   sudo apt install libxml-parser-perl

   # RHEL/CentOS
   sudo yum install perl-XML-Parser
   ```
3. **Module Access**: Grant the user access to required modules (System Status, Bootup and Shutdown, Users and Groups, Scheduled Cron Jobs, Network Configuration)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/webmin-mcp-server.git
cd webmin-mcp-server

# Install dependencies
pip install -e ".[dev]"
```

## Configuration

Set the following environment variables:

```bash
export WEBMIN_HOST="your-webmin-server.com"
export WEBMIN_PORT="10000"
export WEBMIN_USERNAME="admin"
export WEBMIN_PASSWORD="your-password"
export WEBMIN_USE_HTTPS="true"
export WEBMIN_VERIFY_SSL="true"  # Set to false for self-signed certs
```

Or create a `.env` file (see `.env.example`).

## Usage

### With Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "webmin": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/webmin-mcp-server",
      "env": {
        "WEBMIN_HOST": "your-webmin-server.com",
        "WEBMIN_USERNAME": "admin",
        "WEBMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

### Standalone

```bash
python -m src.server
```

## Available Tools

### `get_webmin_version`

Get the version of the connected Webmin server.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "version": "2.105",
    "hostname": "server.example.com"
  }
}
```

### `get_system_info`

Get comprehensive system information including OS, kernel, CPU, memory, and disk usage.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "hostname": "server.example.com",
    "webmin_version": "2.105",
    "os": {"type": "linux", "name": "Ubuntu Linux", "version": "24.04"},
    "kernel": {"os": "Linux", "version": "6.1.0", "arch": "x86_64"},
    "cpu": {"cores": 4, "model": "ARM Cortex-A72", "load_1min": 0.5},
    "memory": {"total_kb": 4000000, "used_kb": 2000000, "free_kb": 1400000},
    "disk": {"total_bytes": 100000000000, "used_bytes": 50000000000},
    "process_count": 150,
    "updates_available": 2,
    "reboot_required": false
  }
}
```

### `list_services`

List all system services (systemd units or init scripts).

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 45,
    "services": [
      {"name": "sshd"},
      {"name": "nginx"},
      {"name": "cron"}
    ]
  }
}
```

### `get_service_status`

Get the status of a specific service.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `service` | string | Yes | Name of the service (e.g., "sshd", "nginx") |

**Returns:**
```json
{
  "success": true,
  "data": {
    "service": "sshd",
    "status": "running",
    "status_code": 0,
    "running": true
  }
}
```

### `list_users`

List all system users, separated into regular users (UID >= 1000) and system users.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "total_count": 25,
    "regular_count": 3,
    "system_count": 22,
    "regular_users": [
      {"username": "admin", "uid": 1000, "gid": 1000, "name": "Admin User", "home": "/home/admin", "shell": "/bin/bash"}
    ],
    "system_users": [
      {"username": "root", "uid": 0, "gid": 0, "name": "root", "home": "/root", "shell": "/bin/bash"}
    ]
  }
}
```

### `get_disk_usage`

Get disk usage information for all mounted filesystems.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "total_bytes": 100000000000,
    "used_bytes": 50000000000,
    "free_bytes": 50000000000,
    "filesystems": [
      {
        "mount_point": "/",
        "device": "/dev/sda1",
        "type": "ext4",
        "total_bytes": 100000000000,
        "used_bytes": 50000000000,
        "free_bytes": 50000000000,
        "used_percent": 50
      }
    ]
  }
}
```

### `get_memory_usage`

Get memory usage information in multiple units (KB, MB, GB).

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "total_kb": 4000000,
    "total_mb": 3906.3,
    "total_gb": 3.81,
    "used_kb": 2000000,
    "used_mb": 1953.1,
    "used_percent": 50.0,
    "free_kb": 1400000,
    "free_mb": 1367.2,
    "free_percent": 35.0,
    "buffers_kb": 100000,
    "cached_kb": 500000
  }
}
```

### `list_cron_jobs`

List all scheduled cron jobs with their schedules and status.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 5,
    "jobs": [
      {
        "user": "root",
        "command": "/usr/bin/backup.sh",
        "schedule": "0 2 * * *",
        "active": true,
        "file": "/etc/crontab",
        "index": 0
      }
    ]
  }
}
```

### `get_network_info`

Get network interface and routing information.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "interface_count": 2,
    "interfaces": [
      {
        "name": "eth0",
        "address": "192.168.1.100",
        "netmask": "255.255.255.0",
        "broadcast": "192.168.1.255",
        "mac": "00:11:22:33:44:55",
        "mtu": 1500,
        "up": true
      }
    ],
    "routes": [
      {
        "destination": "0.0.0.0",
        "gateway": "192.168.1.1",
        "netmask": "0.0.0.0",
        "interface": "eth0"
      }
    ],
    "default_gateway": "192.168.1.1"
  }
}

## Development

### Running Tests

```bash
pytest
```

### Linting

```bash
ruff check src tests
ruff format src tests
```

### Type Checking

```bash
mypy src
```

## Project Structure

```
webmin-mcp-server/
├── src/
│   ├── server.py         # MCP server setup
│   ├── webmin_client.py  # Webmin API client
│   ├── config.py         # Configuration management
│   ├── models.py         # Pydantic models
│   └── tools/            # MCP tool implementations
├── tests/                # Test suite
├── docs/                 # Documentation
│   ├── task_tracker.md   # Project task tracking
│   ├── webmin_api_map.md # Webmin API documentation
│   └── qa_review.md      # QA review log
└── agents/               # Agent team prompts
```

## License

MIT
