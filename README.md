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
```

### `restart_service`

Restart a system service. Some critical services may be blocked in safe mode.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `service` | string | Yes | Name of the service to restart |

**Returns:**
```json
{
  "success": true,
  "data": {
    "service": "nginx",
    "action": "restart",
    "success": true,
    "running": true,
    "status_before": "running",
    "status_after": "running"
  }
}
```

### `start_service`

Start a stopped system service.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `service` | string | Yes | Name of the service to start |

**Returns:**
```json
{
  "success": true,
  "data": {
    "service": "nginx",
    "action": "start",
    "success": true,
    "running": true,
    "status_before": "stopped",
    "status_after": "running"
  }
}
```

### `stop_service`

Stop a running system service. Critical services (ssh, webmin, systemd) are blocked.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `service` | string | Yes | Name of the service to stop |

**Returns:**
```json
{
  "success": true,
  "data": {
    "service": "nginx",
    "action": "stop",
    "success": true,
    "running": false,
    "status_before": "running",
    "status_after": "stopped"
  }
}
```

### `enable_service`

Enable a service to start automatically at boot.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `service` | string | Yes | Name of the service to enable |

**Returns:**
```json
{
  "success": true,
  "data": {
    "service": "nginx",
    "action": "enable",
    "success": true,
    "enabled_at_boot": true,
    "was_enabled": false
  }
}
```

### `disable_service`

Disable a service from starting at boot. Critical services are blocked.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `service` | string | Yes | Name of the service to disable |

**Returns:**
```json
{
  "success": true,
  "data": {
    "service": "nginx",
    "action": "disable",
    "success": true,
    "enabled_at_boot": false,
    "was_enabled": true
  }
}
```

### `create_cron_job`

Create a new scheduled cron job.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `command` | string | Yes | Command to execute |
| `minutes` | string | No | Minutes (0-59, *, */N). Default: * |
| `hours` | string | No | Hours (0-23, *, */N). Default: * |
| `days` | string | No | Day of month (1-31, *, */N). Default: * |
| `months` | string | No | Month (1-12, *, */N). Default: * |
| `weekdays` | string | No | Day of week (0-7, *, 0=Sunday). Default: * |
| `user` | string | No | User to run as. Default: root |
| `active` | boolean | No | Whether job is active. Default: true |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "create",
    "success": true,
    "job": {
      "command": "/usr/bin/backup.sh",
      "schedule": "0 2 * * *",
      "user": "root",
      "active": true,
      "index": 13
    },
    "total_jobs": 14
  }
}
```

### `edit_cron_job`

Edit an existing cron job. Only specify fields you want to change.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `index` | integer | Yes | Job index (from list_cron_jobs) |
| `command` | string | No | New command |
| `minutes` | string | No | New minutes value |
| `hours` | string | No | New hours value |
| `days` | string | No | New days value |
| `months` | string | No | New months value |
| `weekdays` | string | No | New weekdays value |
| `user` | string | No | New user |
| `active` | boolean | No | New active state |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "edit",
    "success": true,
    "job": {
      "index": 13,
      "command": "/usr/bin/backup.sh",
      "schedule": "30 3 * * *",
      "user": "root",
      "active": true
    }
  }
}
```

### `delete_cron_job`

Delete a cron job. **Dangerous operation - blocked in safe mode.**

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `index` | integer | Yes | Job index (from list_cron_jobs) |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "delete",
    "success": true,
    "deleted_job": {
      "index": 13,
      "command": "/usr/bin/backup.sh",
      "user": "root"
    },
    "jobs_before": 14,
    "jobs_after": 13
  }
}
```

### `list_groups`

List all system groups.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "total_count": 78,
    "regular_count": 5,
    "system_count": 73,
    "regular_groups": [
      {"name": "users", "gid": 1000, "members": ["admin"], "member_count": 1}
    ],
    "system_groups": [
      {"name": "root", "gid": 0, "members": [], "member_count": 0}
    ]
  }
}
```

### `create_user`

Create a new system user. **Dangerous operation - blocked in safe mode.**

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Username (lowercase, max 32 chars) |
| `password` | string | Yes | Password for the new user |
| `real_name` | string | No | Full name/comment |
| `home_dir` | string | No | Home directory (default: /home/username) |
| `shell` | string | No | Login shell (default: /bin/bash) |
| `uid` | integer | No | User ID (auto-assigned if not specified) |
| `gid` | integer | No | Group ID (auto-assigned if not specified) |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "create",
    "success": true,
    "user": {
      "username": "newuser",
      "uid": 1001,
      "gid": 1001,
      "real_name": "New User",
      "home": "/home/newuser",
      "shell": "/bin/bash"
    }
  }
}
```

### `delete_user`

Delete a system user. **Dangerous operation - blocked in safe mode.**

Critical users (root, daemon, bin, nobody, etc.) cannot be deleted.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Username to delete |
| `delete_home` | boolean | No | Whether to delete home directory (default: false) |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "delete",
    "success": true,
    "deleted_user": {
      "username": "olduser",
      "uid": 1001,
      "home": "/home/olduser"
    },
    "home_deleted": false
  }
}
```

### `modify_user`

Modify an existing system user. Only specify fields you want to change.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Current username |
| `new_username` | string | No | New username |
| `real_name` | string | No | New full name |
| `home_dir` | string | No | New home directory |
| `shell` | string | No | New login shell |
| `uid` | integer | No | New user ID |
| `gid` | integer | No | New group ID |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "modify",
    "success": true,
    "user": {
      "username": "testuser",
      "uid": 1000,
      "gid": 1000,
      "real_name": "Updated Name",
      "home": "/home/testuser",
      "shell": "/bin/zsh"
    },
    "changes": {
      "real_name": true,
      "shell": true
    }
  }
}
```

### `change_password`

Change a user's password. **Dangerous operation - blocked in safe mode.**

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Username |
| `new_password` | string | Yes | New password |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "change_password",
    "success": true,
    "username": "testuser"
  }
}
```

### `get_package_info`

Get detailed information about an installed package.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `package_name` | string | Yes | Name of the package |

**Returns:**
```json
{
  "success": true,
  "data": {
    "name": "bash",
    "type": "deb",
    "description": "GNU Bourne Again SHell",
    "architecture": "amd64",
    "version": "5.2.21-2ubuntu4",
    "maintainer": "Ubuntu Developers",
    "install_date": "2024-01-15",
    "url": "https://www.gnu.org/software/bash/"
  }
}
```

### `list_available_updates`

List all available package updates, including security updates.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "total_count": 81,
    "security_count": 12,
    "updates": [
      {
        "name": "bash",
        "current_version": "5.2.20-1",
        "new_version": "5.2.21-2",
        "description": "GNU Bourne Again SHell",
        "source": "apt",
        "system": "apt",
        "is_security": false
      }
    ],
    "security_updates": [
      {
        "name": "openssl",
        "current_version": "3.0.12",
        "new_version": "3.0.13",
        "description": "SSL toolkit",
        "is_security": true
      }
    ]
  }
}
```

### `get_package_count`

Get the total count of installed packages.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "installed_count": 1249
  }
}
```

### `read_file`

Read the contents of a file from the remote system.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Absolute path to the file |
| `as_lines` | boolean | No | If true, return as array of lines (default: false) |

**Returns:**
```json
{
  "success": true,
  "data": {
    "path": "/etc/hostname",
    "content": "server.example.com\n",
    "size": 20
  }
}
```

### `write_file`

Write content to a file. **Dangerous operation.** In safe mode, only writes to `/tmp` and `/var/tmp` are allowed. System directories are always blocked.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Absolute path to the file |
| `content` | string | Yes | Content to write |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "write",
    "path": "/tmp/test.txt",
    "success": true,
    "bytes_written": 13
  }
}
```

### `delete_file`

Delete a file or empty directory. **Dangerous operation.** In safe mode, only deletes in `/tmp` and `/var/tmp` are allowed.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Absolute path to delete |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "delete",
    "path": "/tmp/old.txt",
    "success": true
  }
}
```

### `copy_file`

Copy a file to a new location. In safe mode, destination must be in `/tmp` or `/var/tmp`.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `source` | string | Yes | Absolute path to source file |
| `destination` | string | Yes | Absolute path to destination |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "copy",
    "source": "/etc/hostname",
    "destination": "/tmp/hostname_backup",
    "success": true
  }
}
```

### `rename_file`

Rename or move a file. In safe mode, both paths must be in `/tmp` or `/var/tmp`.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `source` | string | Yes | Absolute path to source |
| `destination` | string | Yes | Absolute path to new location |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "rename",
    "source": "/tmp/old.txt",
    "destination": "/tmp/new.txt",
    "success": true
  }
}
```

### `create_directory`

Create a new directory. In safe mode, only directories in `/tmp` or `/var/tmp` can be created.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | string | Yes | Absolute path to create |
| `mode` | integer | No | Permission mode (default: 755) |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "create_directory",
    "path": "/tmp/newdir",
    "mode": 755,
    "success": true
  }
}
```

### `list_processes`

List all running processes on the system.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 150,
    "processes": [
      {
        "pid": 1,
        "ppid": 0,
        "user": "root",
        "cpu": "0.1 %",
        "memory": "1024 kB",
        "memory_bytes": 1048576,
        "time": "00:01:00",
        "command": "/sbin/init",
        "nice": 0,
        "tty": "None"
      }
    ]
  }
}
```

### `list_mounts`

List all mounted filesystems.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "total_count": 15,
    "real_filesystem_count": 3,
    "mounts": [
      {
        "mount_point": "/",
        "device": "/dev/sda1",
        "type": "ext4",
        "options": "rw,relatime"
      }
    ],
    "real_filesystems": [
      {
        "mount_point": "/",
        "device": "/dev/sda1",
        "type": "ext4",
        "options": "rw,relatime"
      }
    ]
  }
}
```

## Safety Framework

The server includes a safety framework to prevent dangerous operations:

### Safety Tiers

- **Read**: No system changes (always allowed)
- **Safe**: Low-risk changes (allowed in safe mode)
- **Moderate**: Reversible changes (may be blocked for critical services)
- **Dangerous**: Potentially destructive (blocked in safe mode)

### Blocked Services

Critical services that cannot be stopped or disabled:
- `ssh`, `sshd` - Remote access
- `webmin` - Webmin itself
- `systemd-*` - Core system services
- `dbus`, `networking`

### Protected Users

Critical system users that cannot be deleted:
- `root`, `daemon`, `bin`, `sys`, `sync`, `nobody`
- `systemd-network`, `systemd-resolve`

### Protected Paths

File operations are blocked for critical system directories:
- `/etc`, `/bin`, `/sbin`, `/usr`, `/boot`, `/lib*`
- `/root`, `/proc`, `/sys`, `/dev`
- Files matching patterns: `.bashrc`, `.ssh`, `passwd`, `shadow`, `sudoers`

### Safe Mode

Safe mode is enabled by default (`WEBMIN_SAFE_MODE=true`). In safe mode:
- Dangerous operations are blocked (user creation/deletion, password changes, cron deletion)
- Critical services cannot be restarted
- Some services can only be restarted (not stopped)
- File writes/deletes only allowed in `/tmp` and `/var/tmp`

To disable safe mode:
```bash
export WEBMIN_SAFE_MODE=false
```

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
