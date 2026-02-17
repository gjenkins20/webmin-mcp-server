# API Reference

Complete documentation for all Webmin MCP Server tools.

All tools (except `list_webmin_servers`) accept an optional `server` parameter to specify which Webmin server to use. If not specified, the default server is used.

---

## Server Management

### `list_webmin_servers`

List all configured Webmin servers with their aliases and status.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "servers": [
      {
        "alias": "pi1",
        "host": "192.168.1.100",
        "port": 10000,
        "is_default": true,
        "safe_mode": true
      },
      {
        "alias": "web-server",
        "host": "192.168.1.50",
        "port": 10000,
        "is_default": false,
        "safe_mode": true
      }
    ],
    "count": 2
  }
}
```

### `test_server_connection`

Test connectivity to a specific Webmin server.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `server` | string | No | Server alias to test (uses default if not specified) |

**Returns:**
```json
{
  "success": true,
  "data": {
    "server": "pi1",
    "reachable": true,
    "webmin_version": "2.105",
    "hostname": "raspberrypi",
    "response_time_ms": 125
  }
}
```

### `get_webmin_version`

Get the version of the connected Webmin server.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `server` | string | No | Server alias (uses default if not specified) |

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

---

## System Information

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

### `get_system_time`

Get the current system time and timezone configuration.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "timezone": "America/New_York",
    "year": 2026,
    "month": 2,
    "day": 16,
    "hour": 10,
    "minute": 30,
    "second": 45
  }
}
```

### `list_runlevels`

List system runlevels and their descriptions.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 7,
    "runlevels": [
      {"level": "0", "name": "halt", "description": "System halt"},
      {"level": "3", "name": "multi", "description": "Multi-user mode"}
    ]
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

---

## Service Management

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

---

## User & Group Management

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

---

## Scheduled Tasks

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

---

## Network

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

---

## Package Management

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

---

## File Operations

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

Write content to a file. **Dangerous operation.** In safe mode, only writes to `/tmp` and `/var/tmp` are allowed.

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

---

## Storage

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

### `list_disks`

List all physical disks with SMART capability.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 2,
    "disks": [
      {
        "device": "/dev/sda",
        "model": "Samsung SSD 870",
        "serial": "S5XXNX0T123456",
        "capacity": "500GB",
        "smart_enabled": true,
        "type": "sata"
      }
    ]
  }
}
```

### `get_disk_health`

Get SMART health status for a specific disk.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `device` | string | Yes | Device path (e.g., "/dev/sda") |

**Returns:**
```json
{
  "success": true,
  "data": {
    "device": "/dev/sda",
    "health": "PASSED",
    "healthy": true,
    "model": "Samsung SSD 870",
    "serial": "S5XXNX0T123456",
    "firmware": "SVT04B6Q",
    "temperature": 35,
    "power_on_hours": 1234,
    "power_cycles": 567,
    "attributes": [
      {
        "id": 5,
        "name": "Reallocated_Sector_Ct",
        "value": 100,
        "worst": 100,
        "threshold": 10,
        "raw": 0,
        "type": "pre-fail",
        "failed": false
      }
    ],
    "failed_attributes": [],
    "errors": [],
    "error_count": 0
  }
}
```

### `list_volume_groups`

List all LVM volume groups.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 1,
    "volume_groups": [
      {
        "name": "vg_data",
        "size_bytes": 107374182400,
        "size_mb": 102400.0,
        "free_bytes": 53687091200,
        "free_mb": 51200.0,
        "pv_count": 2,
        "lv_count": 3,
        "extent_size": 4194304,
        "extent_count": 25600,
        "free_extents": 12800
      }
    ]
  }
}
```

### `list_logical_volumes`

List all LVM logical volumes.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `volume_group` | string | No | Filter by volume group name |

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 2,
    "volume_group": null,
    "logical_volumes": [
      {
        "name": "lv_root",
        "volume_group": "vg_system",
        "size_bytes": 21474836480,
        "size_mb": 20480.0,
        "device": "/dev/vg_system/lv_root",
        "active": true,
        "mounted": "/",
        "stripes": 1,
        "stripe_size": null
      }
    ]
  }
}
```

---

## SSH Configuration

### `get_ssh_config`

Get SSH server (sshd) configuration settings.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "settings": {
      "port": "22",
      "permit_root_login": "no",
      "password_authentication": "yes",
      "pubkey_authentication": "yes"
    }
  }
}
```

---

## Audit & Backup

### `list_webmin_logs`

List Webmin action/audit logs.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | integer | No | Max entries to return (default: 100) |
| `module` | string | No | Filter by module name |
| `user` | string | No | Filter by username |

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 50,
    "logs": [
      {
        "id": 1,
        "time": 1708091445,
        "user": "admin",
        "module": "useradmin",
        "action": "save_user.cgi",
        "description": "Created user testuser",
        "ip": "192.168.1.100"
      }
    ]
  }
}
```

### `list_backups`

List Webmin configuration backups.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 1,
    "backups": [
      {
        "id": "backup1",
        "file": "/var/webmin/backups/config.tar.gz",
        "schedule": "daily",
        "enabled": true
      }
    ]
  }
}
```

---

## Security (Fail2ban)

### `list_fail2ban_jails`

List all Fail2ban jails and their status.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 2,
    "jails": [
      {
        "name": "sshd",
        "enabled": true,
        "maxretry": 5,
        "bantime": 3600,
        "currently_banned": 3
      }
    ]
  }
}
```

### `get_fail2ban_status`

Get Fail2ban status for a specific jail or overall.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `jail` | string | No | Jail name for specific status |

**Returns:**
```json
{
  "success": true,
  "data": {
    "jail": "sshd",
    "running": true,
    "currently_banned": 3,
    "banned_ips": ["192.168.1.100", "10.0.0.50"]
  }
}
```

### `list_banned_ips`

List all currently banned IP addresses from Fail2ban.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `jail` | string | No | Filter by jail name |

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 3,
    "banned_ips": [
      {"ip": "192.168.1.100", "jail": "sshd"},
      {"ip": "10.0.0.50", "jail": "sshd"}
    ]
  }
}
```

---

## Database (MySQL)

### `list_mysql_databases`

List all MySQL databases.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "total_count": 6,
    "user_database_count": 2,
    "system_database_count": 4,
    "user_databases": [
      {"name": "wordpress", "tables": 12, "size": 52428800}
    ],
    "system_databases": [
      {"name": "mysql"},
      {"name": "information_schema"}
    ]
  }
}
```

### `list_mysql_users`

List all MySQL users and their host permissions.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 3,
    "users": [
      {"user": "root", "host": "localhost", "password_set": true},
      {"user": "wordpress", "host": "%", "password_set": true}
    ]
  }
}
```

### `get_mysql_status`

Get MySQL server status.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "running": true,
    "version": "8.0.35",
    "uptime": 86400,
    "threads": 5,
    "connections": 500
  }
}
```

---

## Webmin ACL Management

### `list_webmin_users`

List all Webmin user accounts (NOT system users).

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 2,
    "users": [
      {"name": "admin", "modules": ["*"], "module_count": 1, "has_all_modules": true},
      {"name": "operator", "modules": ["init", "proc"], "module_count": 2, "has_all_modules": false}
    ]
  }
}
```

### `get_webmin_user`

Get detailed permissions for a Webmin user.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Webmin username |

**Returns:**
```json
{
  "success": true,
  "data": {
    "name": "admin",
    "modules": ["*"],
    "module_count": 1,
    "has_all_modules": true,
    "lang": "en",
    "theme": "authentic-theme",
    "readonly": null
  }
}
```

### `list_webmin_modules`

List all available Webmin modules that can be assigned to users.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "count": 45,
    "modules": [
      {"name": "useradmin", "description": "Users and Groups", "category": "system"},
      {"name": "init", "description": "Bootup and Shutdown", "category": "system"}
    ]
  }
}
```

### `create_webmin_user`

Create a new Webmin user account. **Dangerous operation - blocked in safe mode.**

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Username for the new account |
| `password` | string | Yes | Password |
| `modules` | array | No | List of module names to grant access |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "create",
    "success": true,
    "user": {
      "name": "operator",
      "modules": ["init", "proc"],
      "module_count": 2
    }
  }
}
```

### `modify_webmin_user`

Modify a Webmin user's permissions or password. **Dangerous operation - blocked in safe mode.** Cannot demote the last superuser.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Webmin username to modify |
| `password` | string | No | New password |
| `modules` | array | No | New module list (replaces existing) |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "modify",
    "success": true,
    "user": {"name": "operator", "modules": ["init", "proc", "cron"], "module_count": 3},
    "changes": {"modules": true}
  }
}
```

### `delete_webmin_user`

Delete a Webmin user account. **Dangerous operation - blocked in safe mode.** The last superuser account cannot be deleted regardless of safe mode.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Webmin username to delete |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "delete",
    "success": true,
    "deleted_user": {"name": "operator"}
  }
}
```

---

## Disk Quota Management

### `list_quota_filesystems`

List filesystems with disk quota support.

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "data": {
    "total_count": 3,
    "quota_capable_count": 2,
    "quota_enabled_count": 2,
    "filesystems": [
      {
        "mount_point": "/",
        "device": "/dev/sda1",
        "type": "ext4",
        "quota_support": true,
        "quota_type": "both",
        "quota_enabled": true
      }
    ]
  }
}
```

### `list_user_quotas`

List all user quotas on a filesystem.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `filesystem` | string | Yes | Mount point (e.g., "/") |

**Returns:**
```json
{
  "success": true,
  "data": {
    "filesystem": "/",
    "block_size": 1024,
    "count": 2,
    "quotas": [
      {
        "user": "alice",
        "used_blocks": 500,
        "soft_block_limit": 1000,
        "hard_block_limit": 2000,
        "used_bytes": 512000,
        "soft_limit_bytes": 1024000,
        "hard_limit_bytes": 2048000,
        "used_files": 50,
        "soft_file_limit": 100,
        "hard_file_limit": 200
      }
    ]
  }
}
```

### `get_user_quota`

Get quota limits and usage for a specific user.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Username |
| `filesystem` | string | Yes | Mount point |

**Returns:**
```json
{
  "success": true,
  "data": {
    "user": "alice",
    "filesystem": "/",
    "block_size": 1024,
    "quota_enabled": true,
    "used_blocks": 500,
    "soft_block_limit": 1000,
    "hard_block_limit": 2000,
    "used_bytes": 512000,
    "used_files": 50,
    "soft_file_limit": 100,
    "hard_file_limit": 200
  }
}
```

### `get_group_quota`

Get quota limits and usage for a specific group.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `group` | string | Yes | Group name |
| `filesystem` | string | Yes | Mount point |

**Returns:**
```json
{
  "success": true,
  "data": {
    "group": "developers",
    "filesystem": "/home",
    "block_size": 1024,
    "quota_enabled": true,
    "used_blocks": 2000,
    "soft_block_limit": 5000,
    "hard_block_limit": 10000,
    "used_bytes": 2048000,
    "used_files": 500,
    "soft_file_limit": 1000,
    "hard_file_limit": 2000
  }
}
```

### `set_user_quota`

Set disk quota limits for a user. **Dangerous operation - blocked in safe mode.**

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `username` | string | Yes | Username |
| `filesystem` | string | Yes | Mount point |
| `soft_block_limit` | integer | No | Soft block limit (0 = unlimited) |
| `hard_block_limit` | integer | No | Hard block limit (0 = unlimited) |
| `soft_file_limit` | integer | No | Soft file limit (0 = unlimited) |
| `hard_file_limit` | integer | No | Hard file limit (0 = unlimited) |

**Returns:**
```json
{
  "success": true,
  "data": {
    "action": "set_quota",
    "success": true,
    "user": "alice",
    "filesystem": "/",
    "soft_block_limit": 1000,
    "hard_block_limit": 2000,
    "soft_file_limit": 100,
    "hard_file_limit": 200
  }
}
```
