# Webmin MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/docker/v/gjenkins20/webmin-mcp-server?label=docker&sort=semver)](https://hub.docker.com/r/gjenkins20/webmin-mcp-server)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server that provides Claude with tools to manage Linux systems via [Webmin](https://webmin.com)'s administration interface.

## Features

- **Multi-Server Support** -- Manage multiple Webmin servers with user-friendly aliases
- **System Monitoring** -- System info, memory, disk, network, and process status
- **Service Management** -- Start, stop, restart, enable, and disable services
- **User & Group Administration** -- Create, modify, and delete system users and groups
- **Scheduled Tasks** -- View, create, edit, and delete cron jobs
- **Package Management** -- Package info and available updates
- **File Operations** -- Read, write, copy, rename, and delete remote files
- **Storage** -- SMART disk health monitoring and LVM volume management
- **Security** -- Fail2ban jail status and banned IP management
- **Database** -- MySQL databases, users, and server status
- **Webmin ACL** -- Manage Webmin user accounts and module permissions
- **Disk Quotas** -- Monitor and set disk quota limits for users and groups
- **Audit & Backup** -- Webmin action logs, SSH config, and configuration backups
- **Safety Framework** -- Tiered safety system with safe mode to prevent dangerous operations

## Quick Start

1. **Install** (choose one):

   **From source:**
   ```bash
   git clone https://github.com/gjenkins20/webmin-mcp-server.git
   cd webmin-mcp-server
   pip install -e .
   ```

   **With Docker:**
   ```bash
   docker pull gjenkins20/webmin-mcp-server
   ```

2. **Configure** -- Create a `webmin-servers.json` (see [Configuration](#configuration)):
   ```json
   {
     "default_server": "my-server",
     "servers": {
       "my-server": {
         "host": "192.168.1.100",
         "port": 10000,
         "username": "admin",
         "password": "your-password",
         "use_https": true,
         "verify_ssl": false,
         "safe_mode": true
       }
     }
   }
   ```

3. **Add to Claude Desktop** (`claude_desktop_config.json`):

   **From source:**
   ```json
   {
     "mcpServers": {
       "webmin": {
         "command": "python",
         "args": ["-m", "src.server"],
         "cwd": "/path/to/webmin-mcp-server",
         "env": {
           "WEBMIN_CONFIG_FILE": "/path/to/webmin-servers.json"
         }
       }
     }
   }
   ```

   **With Docker:**
   ```json
   {
     "mcpServers": {
       "webmin": {
         "command": "docker",
         "args": [
           "run", "--rm", "-i",
           "-v", "/path/to/webmin-servers.json:/app/webmin-servers.json:ro",
           "gjenkins20/webmin-mcp-server"
         ]
       }
     }
   }
   ```

## Requirements

- Python 3.11+
- A running Webmin instance (typically on port 10000)
- Webmin credentials with appropriate permissions

### Webmin Server Setup

The MCP server uses Webmin's XML-RPC API. Ensure your Webmin server is configured:

1. **Provision the service account**:
   - **Webmin 2.650+ (recommended)**: Create a dedicated **RPC/API-only** account in Webmin -> Webmin Users. This account type exists specifically for automation like this MCP server -- it blocks browser/module access entirely and is unaffected by the two-factor caveat below.
   - **Older Webmin versions**: In Webmin -> Webmin Users -> (your user) -> enable "Can accept RPC calls".
   - **Two-factor authentication caveat**: Webmin 2.640+ rejects RPC Basic-Auth requests for accounts that have 2FA enabled -- the RPC call fails with a generic 401/403. If you enable 2FA on your Webmin users, use a dedicated RPC/API-only account for this MCP server rather than a 2FA-enrolled one.
2. **Install XML::Parser**: The Perl XML::Parser module must be installed:
   ```bash
   # Debian/Ubuntu
   sudo apt install libxml-parser-perl

   # RHEL/CentOS
   sudo yum install perl-XML-Parser
   ```
3. **Module Access**: Grant the user access to required modules (System Status, Bootup and Shutdown, Users and Groups, Scheduled Cron Jobs, Network Configuration)
4. **RPC timeout (optional)**: For tools that read/write large files, Webmin 2.620+ has a config option to raise the default RPC timeout (Webmin Configuration -> Advanced Options). Increase it if you see timeouts on large file operations.

## Configuration

### Multi-Server Configuration (Recommended)

Create a `webmin-servers.json` file to manage multiple Webmin servers. See [`webmin-servers.example.json`](webmin-servers.example.json) for a complete example.

**Configuration sources (priority order):**
1. `WEBMIN_CONFIG_FILE` env var -- path to JSON config file
2. `WEBMIN_SERVERS_JSON` env var -- inline JSON string
3. `./webmin-servers.json` -- local file in current directory
4. `~/.config/webmin-mcp/servers.json` -- user config directory
5. Legacy `WEBMIN_*` env vars -- single server (creates "default" alias)

### Single Server Configuration (Legacy)

For a single server, set environment variables:

```bash
export WEBMIN_HOST="your-webmin-server.com"
export WEBMIN_PORT="10000"
export WEBMIN_USERNAME="admin"
export WEBMIN_PASSWORD="your-password"
export WEBMIN_USE_HTTPS="true"
export WEBMIN_VERIFY_SSL="true"  # Set to false for self-signed certs
```

Or create a `.env` file (see [`.env.example`](.env.example)).

### Using Multiple Servers

With multi-server configuration, all tools accept an optional `server` parameter:

```
"Get system info from pi1"           -> Uses pi1 (default)
"Check disk usage on web-server"     -> Uses web-server
"List services on server: nas"       -> Uses nas
```

Use `list_webmin_servers` to see all configured servers and their aliases.

## Available Tools

All tools accept an optional `server` parameter to target a specific Webmin server. See the [full API reference](docs/api-reference.md) for detailed parameters and response formats.

| Category | Tools | Description |
|----------|-------|-------------|
| **Server** | `list_webmin_servers`, `test_server_connection`, `get_webmin_version` | Manage and test server connections |
| **System** | `get_system_info`, `get_memory_usage`, `get_system_time`, `list_runlevels`, `list_processes` | System monitoring and information |
| **Services** | `list_services`, `get_service_status`, `start_service`, `stop_service`, `restart_service`, `enable_service`, `disable_service` | Service lifecycle management |
| **Users & Groups** | `list_users`, `list_groups`, `create_user`, `modify_user`, `delete_user`, `change_password` | User and group administration |
| **Cron** | `list_cron_jobs`, `create_cron_job`, `edit_cron_job`, `delete_cron_job` | Scheduled task management |
| **Network** | `get_network_info` | Interface and routing details |
| **Packages** | `get_package_info`, `list_available_updates`, `get_package_count` | Package information and updates |
| **Files** | `read_file`, `write_file`, `delete_file`, `copy_file`, `rename_file`, `create_directory` | Remote file operations |
| **Storage** | `get_disk_usage`, `list_mounts`, `list_disks`, `get_disk_health`, `list_volume_groups`, `list_logical_volumes` | Disk, mount, SMART, and LVM management |
| **SSH** | `get_ssh_config` | SSH server configuration |
| **Audit** | `list_webmin_logs`, `list_backups` | Action logs and backups |
| **Security** | `list_fail2ban_jails`, `get_fail2ban_status`, `list_banned_ips` | Fail2ban intrusion prevention |
| **Database** | `list_mysql_databases`, `list_mysql_users`, `get_mysql_status` | MySQL database management |
| **Webmin ACL** | `list_webmin_users`, `get_webmin_user`, `list_webmin_modules`, `create_webmin_user`, `modify_webmin_user`, `delete_webmin_user` | Webmin user and permission management |
| **Disk Quotas** | `list_quota_filesystems`, `list_user_quotas`, `get_user_quota`, `get_group_quota`, `set_user_quota` | Disk quota monitoring and management |

## Safety Framework

The server includes a tiered safety system to prevent accidental damage.

### Safety Tiers

| Tier | Description | Safe Mode |
|------|-------------|-----------|
| **Read** | No system changes | Always allowed |
| **Safe** | Low-risk changes | Allowed |
| **Moderate** | Reversible changes | May block critical services |
| **Dangerous** | Destructive operations | Blocked |

### Safe Mode

Safe mode is **enabled by default**. When active:
- Dangerous operations are blocked (user creation/deletion, password changes, cron deletion)
- Critical services (`ssh`, `webmin`, `systemd-*`, `dbus`) cannot be stopped
- File writes/deletes are restricted to `/tmp` and `/var/tmp`
- Critical system users and paths are protected

Configure per-server in `webmin-servers.json`:
```json
{
  "servers": {
    "production": { "safe_mode": true },
    "development": { "safe_mode": false }
  }
}
```

Or globally via environment: `export WEBMIN_SAFE_MODE=false`

## Docker

### Pull from Docker Hub

```bash
docker pull gjenkins20/webmin-mcp-server
```

### Build locally

```bash
docker build -t webmin-mcp-server .
```

### Run standalone

```bash
# With config file
docker run --rm -i \
  -v /path/to/webmin-servers.json:/app/webmin-servers.json:ro \
  gjenkins20/webmin-mcp-server

# With environment variables
docker run --rm -i \
  -e WEBMIN_HOST=192.168.1.100 \
  -e WEBMIN_USERNAME=admin \
  -e WEBMIN_PASSWORD=your-password \
  gjenkins20/webmin-mcp-server
```

### Tagging strategy

| Tag | Description |
|-----|-------------|
| `latest` | Latest build from `main` branch |
| `0.1.0` | Specific release version |
| `0.1` | Latest patch for minor version |
| `abc1234` | Specific commit SHA |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check src tests
ruff format src tests

# Type check
mypy src
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to the project.

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
├── docs/
│   ├── api-reference.md  # Full API documentation
│   └── webmin_api_map.md # Webmin API endpoint mapping
├── .github/workflows/    # CI/CD (Docker build & push)
├── Dockerfile
└── webmin-servers.example.json
```

## License

[MIT](LICENSE)
