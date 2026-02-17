# Webmin API Map

This document contains the canonical reference for all discovered Webmin API
endpoints used by this MCP server.
**Owner:** API Integration Specialist

---

## Overview

This MCP server uses **XML-RPC** as the primary API transport, with **CGI
fallback** for operations not well-supported by XML-RPC.

### API Strategy

| Transport | Endpoint | Auth Method | Use Case |
|-----------|----------|-------------|----------|
| XML-RPC (primary) | `/xmlrpc.cgi` | HTTP Basic Auth in URL | Most module functions |
| CGI (fallback) | `/module/script.cgi` | HTTP Basic Auth header | HTML parsing, json=1 |

### Prerequisites

For XML-RPC to work, the Webmin server must have:

1. **XML::Parser Perl module** installed
   - Webmin → Tools → Perl Modules → Install from CPAN → `XML::Parser`

2. **RPC permissions enabled** for the user
   - Webmin → Webmin Users → select user → "Can accept RPC calls" = Yes

3. **Port 10000 accessible** over HTTPS

---

## Authentication

### XML-RPC Authentication

Credentials are embedded in the URL:
```
https://username:password@host:10000/xmlrpc.cgi
```

Special characters in username/password must be URL-encoded.

### CGI Authentication

HTTP Basic Auth header:
```
Authorization: Basic base64(username:password)
```

---

## XML-RPC Method Naming

XML-RPC methods follow the pattern: `module::function`

Examples:
- `webmin::get_webmin_version`
- `init::list_services`
- `cron::list_jobs`

---

## Module: webmin (Core)

### get_webmin_version

Get the Webmin server version.

- **Method:** `webmin::get_webmin_version`
- **Arguments:** None
- **Returns:** String (e.g., "2.105")
- **Example:**
  ```python
  version = await client.call("webmin", "get_webmin_version")
  # Returns: "2.105"
  ```

### get_system_hostname

Get the server hostname.

- **Method:** `webmin::get_system_hostname`
- **Arguments:** None
- **Returns:** String (e.g., "server.example.com")
- **Example:**
  ```python
  hostname = await client.call("webmin", "get_system_hostname")
  # Returns: "server.example.com"
  ```

---

## Module: init (Services)

### list_services

List all system services.

- **Method:** `init::list_services`
- **Arguments:** None
- **Returns:** List of service dictionaries
- **Example:**
  ```python
  services = await client.call("init", "list_services")
  # Returns: [{"name": "sshd", "status": 1, ...}, ...]
  ```

### get_service_status

Get status of a specific service.

- **Method:** `init::get_service_status`
- **Arguments:** `service_name` (string)
- **Returns:** Dictionary with status info
- **Known Quirks:** Status codes vary by init system (systemd vs sysvinit)

### start_service / stop_service / restart_service

Control a service.

- **Methods:**
  - `init::start_service`
  - `init::stop_service`
  - `init::restart_service`
- **Arguments:** `service_name` (string)
- **Returns:** Success/failure indication
- **Safety Tier:** Moderate (restart), Moderate (start/stop)

---

## Module: cron (Scheduled Tasks)

### list_jobs

List all cron jobs.

- **Method:** `cron::list_jobs`
- **Arguments:** None
- **Returns:** List of cron job dictionaries
- **Example:**
  ```python
  jobs = await client.call("cron", "list_jobs")
  ```

### create_job

Create a new cron job.

- **Method:** `cron::create_job`
- **Arguments:** Job specification dictionary
- **Returns:** New job ID
- **Safety Tier:** Moderate

### delete_job

Delete a cron job.

- **Method:** `cron::delete_job`
- **Arguments:** `job_id` (integer)
- **Returns:** Success/failure
- **Safety Tier:** Dangerous

---

## Module: useradmin (Users & Groups)

### list_users

List all system users.

- **Method:** `useradmin::list_users`
- **Arguments:** None
- **Returns:** List of user dictionaries with keys: `user`, `uid`, `gid`, `real`, `home`, `shell`, `line`
- **Example:**
  ```python
  users = await client.call("useradmin", "list_users")
  # Returns: [{"user": "root", "uid": 0, "gid": 0, "real": "root", "home": "/root", "shell": "/bin/bash", "line": "root:x:0:0:root:/root:/bin/bash"}, ...]
  ```

### list_groups

List all system groups.

- **Method:** `useradmin::list_groups`
- **Arguments:** None
- **Returns:** List of group dictionaries with keys: `group`, `gid`, `members`
- **Example:**
  ```python
  groups = await client.call("useradmin", "list_groups")
  # Returns: [{"group": "root", "gid": 0, "members": ""}, {"group": "sudo", "gid": 27, "members": "admin,user"}, ...]
  ```

### create_user

Create a new system user.

- **Method:** `useradmin::create_user`
- **Arguments:** User dictionary with keys: `user`, `pass`, `uid`, `gid`, `real`, `home`, `shell`
- **Returns:** Integer (1 on success)
- **Safety Tier:** Dangerous
- **Example:**
  ```python
  user_data = {
      "user": "newuser",
      "pass": "password123",
      "uid": 1001,
      "gid": 1001,
      "real": "New User",
      "home": "/home/newuser",
      "shell": "/bin/bash"
  }
  result = await client.call("useradmin", "create_user", user_data)
  # Returns: 1
  ```

### modify_user

Modify an existing user.

- **Method:** `useradmin::modify_user`
- **Arguments:** `old_user` (dict), `new_user` (dict) — both full user dictionaries
- **Returns:** Integer (1 on success)
- **Safety Tier:** Moderate
- **Example:**
  ```python
  old_user = users[0]  # From list_users
  new_user = old_user.copy()
  new_user["shell"] = "/bin/zsh"
  result = await client.call("useradmin", "modify_user", old_user, new_user)
  ```

### delete_user

Delete a system user.

- **Method:** `useradmin::delete_user`
- **Arguments:** User dictionary (must include `line` field from list_users)
- **Returns:** None
- **Safety Tier:** Dangerous
- **Known Quirks:** Requires the full user dictionary including the `line` field
- **Example:**
  ```python
  user_to_delete = users[0]  # From list_users - must have 'line' field
  await client.call("useradmin", "delete_user", user_to_delete)
  ```

---

## Module: software (Package Management)

### list_packages

Get count of installed packages.

- **Method:** `software::list_packages`
- **Arguments:** None
- **Returns:** Integer (package count)
- **Example:**
  ```python
  count = await client.call("software", "list_packages")
  # Returns: 1249
  ```

### package_info

Get detailed information about an installed package.

- **Method:** `software::package_info`
- **Arguments:** `package_name` (string)
- **Returns:** List with package details: [name, type, description, arch, version, maintainer, install_date, url]
- **Known Quirks:** Description may be a Binary object (xmlrpc.client.Binary) that needs decoding
- **Example:**
  ```python
  info = await client.call("software", "package_info", "bash")
  # Returns: ["bash", "deb", "GNU Bourne Again SHell", "amd64", "5.2.21-2ubuntu4", "Ubuntu Developers", None, "https://www.gnu.org/software/bash/"]
  ```

### Package Updates (via system-status)

Available package updates are returned by `system-status::collect_system_info` in the `poss` field.

- **Method:** `system-status::collect_system_info`
- **Field:** `poss` — List of available updates
- **Example:**
  ```python
  info = await client.call("system-status", "collect_system_info")
  updates = info.get("poss", [])
  # Returns: [{"name": "bash", "oldversion": "5.2.20", "version": "5.2.21", "security": 0, ...}, ...]
  ```

### Package Install/Remove (NOT Available via XML-RPC)

Package installation and removal operations are **NOT available** via XML-RPC.
They require CGI form submissions and are not implemented in this MCP server.

---

## Module: webmin (File Operations)

### read_file_contents

Read file contents as a string.

- **Method:** `webmin::read_file_contents`
- **Arguments:** `path` (string) — absolute file path
- **Returns:** String with file contents
- **Example:**
  ```python
  content = await client.call("webmin", "read_file_contents", "/etc/hostname")
  # Returns: "server.example.com\n"
  ```

### read_file_lines

Read file contents as array of lines.

- **Method:** `webmin::read_file_lines`
- **Arguments:** `path` (string) — absolute file path
- **Returns:** List of strings (lines)
- **Example:**
  ```python
  lines = await client.call("webmin", "read_file_lines", "/etc/hosts")
  # Returns: ["127.0.0.1 localhost", "::1 localhost", ...]
  ```

### write_file_contents

Write content to a file.

- **Method:** `webmin::write_file_contents`
- **Arguments:** `path` (string), `content` (string)
- **Returns:** Integer (1 on success)
- **Safety Tier:** Dangerous
- **Example:**
  ```python
  result = await client.call("webmin", "write_file_contents", "/tmp/test.txt", "Hello")
  # Returns: 1
  ```

### unlink_file

Delete a file or empty directory.

- **Method:** `webmin::unlink_file`
- **Arguments:** `path` (string)
- **Returns:** List [success (int), error_message (string)]
- **Safety Tier:** Dangerous
- **Example:**
  ```python
  result = await client.call("webmin", "unlink_file", "/tmp/test.txt")
  # Returns: [1, ""]
  ```

### copy_source_dest

Copy a file to a new location.

- **Method:** `webmin::copy_source_dest`
- **Arguments:** `source` (string), `destination` (string)
- **Returns:** List [success (int), error_message (string)]
- **Safety Tier:** Moderate
- **Example:**
  ```python
  result = await client.call("webmin", "copy_source_dest", "/etc/hostname", "/tmp/hostname_copy")
  # Returns: [1, ""]
  ```

### rename_file

Rename or move a file.

- **Method:** `webmin::rename_file`
- **Arguments:** `old_path` (string), `new_path` (string)
- **Returns:** Integer (1 on success)
- **Safety Tier:** Moderate
- **Example:**
  ```python
  result = await client.call("webmin", "rename_file", "/tmp/old.txt", "/tmp/new.txt")
  # Returns: 1
  ```

### make_dir

Create a new directory.

- **Method:** `webmin::make_dir`
- **Arguments:** `path` (string), `mode` (int)
- **Returns:** Integer (1 on success)
- **Safety Tier:** Moderate
- **Example:**
  ```python
  result = await client.call("webmin", "make_dir", "/tmp/newdir", 755)
  # Returns: 1
  ```

---

## Module: proc (Process Management)

### list_processes

List all running processes.

- **Method:** `proc::list_processes`
- **Arguments:** None
- **Returns:** List of process dictionaries with keys: `pid`, `ppid`, `user`, `cpu`, `size`, `bytes`, `time`, `args`, `nice`, `_tty`
- **Example:**
  ```python
  processes = await client.call("proc", "list_processes")
  # Returns: [{"pid": 1, "user": "root", "args": "/sbin/init", ...}, ...]
  ```

---

## Module: mount (Filesystem Management)

### list_mounted

List all mounted filesystems.

- **Method:** `mount::list_mounted`
- **Arguments:** None
- **Returns:** List of lists: [mount_point, device, type, options]
- **Example:**
  ```python
  mounts = await client.call("mount", "list_mounted")
  # Returns: [["/", "/dev/sda1", "ext4", "rw,relatime"], ...]
  ```

---

## CGI Fallback Endpoints

For modules with limited XML-RPC support, use direct CGI requests.

### System Information (proc module)

- **Endpoint:** `/proc/index.cgi`
- **Method:** GET
- **Parameters:** `json=1` for JSON output
- **Returns:** Process list and system stats

### Disk Usage

- **Endpoint:** `/mount/index.cgi`
- **Method:** GET
- **Parameters:** `json=1`
- **Returns:** Mount points and disk usage

### Network Information

- **Endpoint:** `/net/index.cgi`
- **Method:** GET
- **Parameters:** `json=1`
- **Returns:** Network interface information

---

## Error Handling

### XML-RPC Errors

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 401 | Bad credentials | Check username/password |
| 403 | RPC not permitted | Enable "Can accept RPC calls" |
| 404 | No XML-RPC endpoint | Install XML::Parser or use CGI fallback |
| 500 | Server error | Check Webmin logs |

### XML-RPC Faults

Webmin returns `xmlrpc.client.Fault` for module-level errors:
- Invalid function name
- Missing required arguments
- Permission denied for operation

---

## Version Compatibility

| Webmin Version | XML-RPC Support | Notes |
|----------------|-----------------|-------|
| < 1.300 | No | CGI only |
| 1.300 - 1.999 | Yes | Requires XML::Parser |
| 2.000+ | Yes | Modern API, better JSON support |

---

## Module: smart-status (SMART Disk Health)

### list_smart_disks_partitions

List all SMART-capable disks and partitions.

- **Method:** `smart-status::list_smart_disks_partitions`
- **Arguments:** None
- **Returns:** List of disk dictionaries with keys: `device`, `model`, `serial`, `capacity`, `smart`, `type`
- **Example:**
  ```python
  disks = await client.call("smart-status", "list_smart_disks_partitions")
  # Returns: [{"device": "/dev/sda", "model": "Samsung SSD", "smart": 1, ...}, ...]
  ```

### get_drive_status

Get detailed SMART status for a specific drive.

- **Method:** `smart-status::get_drive_status`
- **Arguments:** `device` (string) — device path (e.g., "/dev/sda")
- **Returns:** Dictionary with keys: `health`, `model`, `serial`, `firmware`, `temp`, `power_on`, `power_cycles`, `attrs`, `errors`
- **Example:**
  ```python
  status = await client.call("smart-status", "get_drive_status", "/dev/sda")
  # Returns: {"health": "PASSED", "temp": 35, "attrs": [...], ...}
  ```

---

## Module: lvm (Logical Volume Manager)

### list_volume_groups

List all LVM volume groups.

- **Method:** `lvm::list_volume_groups`
- **Arguments:** None
- **Returns:** List of VG dictionaries with keys: `name`, `size`, `free`, `pvs`, `lvs`, `pe_size`, `pe_total`, `pe_free`
- **Example:**
  ```python
  vgs = await client.call("lvm", "list_volume_groups")
  # Returns: [{"name": "vg_data", "size": 107374182400, "free": 53687091200, ...}, ...]
  ```

### list_logical_volumes

List all LVM logical volumes.

- **Method:** `lvm::list_logical_volumes`
- **Arguments:** None
- **Returns:** List of LV dictionaries with keys: `name`, `vg`, `size`, `device`, `active`, `mount`, `stripes`, `stripesize`
- **Example:**
  ```python
  lvs = await client.call("lvm", "list_logical_volumes")
  # Returns: [{"name": "lv_root", "vg": "vg_system", "size": 21474836480, ...}, ...]
  ```

---

---

## Module: time (System Time)

### get_system_time

Get the current system time and timezone.

- **Method:** `time::get_system_time`
- **Arguments:** None
- **Returns:** Dictionary or list with time components (year, month, day, hour, minute, second, timezone)
- **Example:**
  ```python
  time = await client.call("time", "get_system_time")
  # Returns: {"year": 2026, "month": 2, "day": 16, "hour": 10, ...}
  ```

---

## Module: init (Runlevels)

### list_runlevels

List system runlevels.

- **Method:** `init::list_runlevels`
- **Arguments:** None
- **Returns:** List of runlevel dictionaries or simple level identifiers
- **Example:**
  ```python
  levels = await client.call("init", "list_runlevels")
  # Returns: [{"level": "0", "name": "halt", "desc": "System halt"}, ...]
  ```

---

## Module: sshd (SSH Configuration)

### get_sshd_config

Get SSH daemon configuration.

- **Method:** `sshd::get_sshd_config`
- **Arguments:** None
- **Returns:** Dictionary with SSH configuration settings
- **Example:**
  ```python
  config = await client.call("sshd", "get_sshd_config")
  # Returns: {"Port": "22", "PermitRootLogin": "no", ...}
  ```

---

## Module: webminlog (Audit Logs)

### list_webmin_log

List Webmin action audit logs.

- **Method:** `webminlog::list_webmin_log`
- **Arguments:** None
- **Returns:** List of log entry dictionaries with keys: `id`, `time`, `user`, `module`, `script`, `desc`, `ip`, `sid`
- **Example:**
  ```python
  logs = await client.call("webminlog", "list_webmin_log")
  # Returns: [{"id": 1, "user": "admin", "module": "useradmin", ...}, ...]
  ```

---

## Module: backup-config (Configuration Backups)

### list_backups

List configured backups.

- **Method:** `backup-config::list_backups`
- **Arguments:** None
- **Returns:** List of backup configuration dictionaries
- **Example:**
  ```python
  backups = await client.call("backup-config", "list_backups")
  # Returns: [{"id": "backup1", "file": "/path/to/backup", ...}, ...]
  ```

---

## Module: fail2ban (Intrusion Prevention)

### list_jails

List configured Fail2ban jails.

- **Method:** `fail2ban::list_jails`
- **Arguments:** None
- **Returns:** List of jail configurations
- **Example:**
  ```python
  jails = await client.call("fail2ban", "list_jails")
  # Returns: [{"name": "sshd", "enabled": 1, "maxretry": 5, ...}, ...]
  ```

### get_status / get_jail_status

Get Fail2ban status (overall or for specific jail).

- **Methods:**
  - `fail2ban::get_status` (overall)
  - `fail2ban::get_jail_status` (specific jail)
- **Arguments:** `jail` (string) for get_jail_status
- **Returns:** Status dictionary with running state and banned IPs
- **Example:**
  ```python
  status = await client.call("fail2ban", "get_jail_status", "sshd")
  # Returns: {"running": True, "banned": ["192.168.1.100"], ...}
  ```

### list_banned / list_all_banned

List currently banned IP addresses.

- **Methods:**
  - `fail2ban::list_banned` (specific jail)
  - `fail2ban::list_all_banned` (all jails)
- **Arguments:** `jail` (string) for list_banned
- **Returns:** List of banned IPs
- **Example:**
  ```python
  banned = await client.call("fail2ban", "list_all_banned")
  # Returns: [{"ip": "192.168.1.100", "jail": "sshd", ...}, ...]
  ```

---

## Module: mysql (Database Management)

### list_databases

List MySQL databases.

- **Method:** `mysql::list_databases`
- **Arguments:** None
- **Returns:** List of database dictionaries
- **Example:**
  ```python
  dbs = await client.call("mysql", "list_databases")
  # Returns: [{"name": "wordpress", "tables": 12, ...}, ...]
  ```

### list_users

List MySQL users.

- **Method:** `mysql::list_users`
- **Arguments:** None
- **Returns:** List of user dictionaries
- **Example:**
  ```python
  users = await client.call("mysql", "list_users")
  # Returns: [{"user": "root", "host": "localhost", ...}, ...]
  ```

### get_mysql_status

Get MySQL server status.

- **Method:** `mysql::get_mysql_status`
- **Arguments:** None
- **Returns:** Status dictionary with version, uptime, connections, etc.
- **Example:**
  ```python
  status = await client.call("mysql", "get_mysql_status")
  # Returns: {"version": "8.0.35", "uptime": 86400, ...}
  ```

---

## Module: acl (Webmin ACL / User Management)

### list_users

List all Webmin user accounts.

- **Method:** `acl::list_users`
- **Arguments:** None (optional: array of usernames to filter)
- **Returns:** List of user dictionaries with keys: `name`, `pass`, `modules` (list of module names), `lang`, `theme`, `readonly`, `real`, `email`, and more
- **Example:**
  ```python
  users = await client.call("acl", "list_users")
  # Returns: [{"name": "admin", "modules": ["*"], ...}, ...]
  ```

### get_user

Get a single Webmin user by name (more efficient than list_users + filter).

- **Method:** `acl::get_user`
- **Arguments:** `username` (string)
- **Returns:** User dictionary (same format as list_users entries), or `None` if not found
- **Example:**
  ```python
  user = await client.call("acl", "get_user", "admin")
  # Returns: {"name": "admin", "modules": ["*"], "lang": "en", ...}
  ```

### list_module_infos

List all available Webmin modules with descriptions.

- **Method:** `acl::list_module_infos`
- **Arguments:** None
- **Returns:** List of module dictionaries with keys: `dir`, `desc`, `category`
- **Example:**
  ```python
  modules = await client.call("acl", "list_module_infos")
  # Returns: [{"dir": "useradmin", "desc": "Users and Groups", "category": "system"}, ...]
  ```

### encrypt_password

Encrypt a plaintext password for use in create_user/modify_user.

- **Method:** `acl::encrypt_password`
- **Arguments:** `password` (string), optional `salt` (string)
- **Returns:** Encrypted password string (MD5/SHA512/DES depending on configuration)
- **Known Quirks:** Passwords MUST be encrypted before passing to create_user or modify_user.
- **Example:**
  ```python
  encrypted = await client.call("acl", "encrypt_password", "plaintext")
  # Returns: "$1$salt$encrypted_hash"
  ```

### create_user

Create a new Webmin user account.

- **Method:** `acl::create_user`
- **Arguments:** User dictionary with keys: `name`, `pass` (must be pre-encrypted), `modules`
- **Returns:** None
- **Safety Tier:** Dangerous
- **Known Quirks:** Username "webmin" is explicitly forbidden by the Webmin API.
- **Example:**
  ```python
  encrypted = await client.call("acl", "encrypt_password", "password")
  user_data = {"name": "operator", "pass": encrypted, "modules": ["init", "proc"]}
  await client.call("acl", "create_user", user_data)
  ```

### modify_user

Modify an existing Webmin user.

- **Method:** `acl::modify_user`
- **Arguments:** `old_name` (string), `new_user` (dict with `pass` pre-encrypted if changing)
- **Returns:** None
- **Safety Tier:** Dangerous
- **Example:**
  ```python
  encrypted = await client.call("acl", "encrypt_password", "newpass")
  new_user = {"name": "operator", "pass": encrypted, "modules": ["init", "proc", "cron"]}
  await client.call("acl", "modify_user", "operator", new_user)
  ```

### delete_from_groups

Remove a user from all Webmin groups. Should be called before delete_user.

- **Method:** `acl::delete_from_groups`
- **Arguments:** `username` (string)
- **Returns:** None
- **Example:**
  ```python
  await client.call("acl", "delete_from_groups", "operator")
  ```

### delete_user

Delete a Webmin user account.

- **Method:** `acl::delete_user`
- **Arguments:** `username` (string)
- **Returns:** None
- **Safety Tier:** Dangerous
- **Known Quirks:** Deleting the last superuser account will permanently lock out admin access. Call `delete_from_groups` first to clean up group memberships.
- **Example:**
  ```python
  await client.call("acl", "delete_from_groups", "operator")
  await client.call("acl", "delete_user", "operator")
  ```

---

## Module: quota (Disk Quota Management)

### list_filesystems

List all filesystems and their quota support status.

- **Method:** `quota::list_filesystems`
- **Arguments:** None
- **Returns:** List of arrays: [mount_point, device, type, options, quota_type, active, ...]
- **Example:**
  ```python
  filesystems = await client.call("quota", "list_filesystems")
  # Returns: [["/", "/dev/sda1", "ext4", "rw", 3, 1], ...]
  ```

### filesystem_users

List all users with quotas on a filesystem.

- **Method:** `quota::filesystem_users`
- **Arguments:** `filesystem` (string) — mount point
- **Returns:** Integer count of users with quotas. Quota data is populated into a Perl global `%user` hash which may not be accessible over XML-RPC.
- **Known Quirks:** Over XML-RPC, typically only the count is returned. Use `user_quota` for individual lookups.
- **Example:**
  ```python
  count = await client.call("quota", "filesystem_users", "/")
  # Returns: 5
  ```

### user_quota

Get quota limits and usage for a specific user on a filesystem.

- **Method:** `quota::user_quota`
- **Arguments:** `username` (string), `filesystem` (string)
- **Returns:** 6-element array: [used_blocks, soft_blocks, hard_blocks, used_files, soft_files, hard_files]. Empty array if no quota set.
- **Example:**
  ```python
  quota = await client.call("quota", "user_quota", "alice", "/")
  # Returns: [500, 1000, 2000, 50, 100, 200]
  ```

### group_quota

Get quota limits and usage for a specific group on a filesystem.

- **Method:** `quota::group_quota`
- **Arguments:** `group` (string), `filesystem` (string)
- **Returns:** 6-element array (same format as user_quota). Empty array if no quota set.
- **Example:**
  ```python
  quota = await client.call("quota", "group_quota", "developers", "/home")
  # Returns: [2000, 5000, 10000, 500, 1000, 2000]
  ```

### block_size

Get the block size for a filesystem.

- **Method:** `quota::block_size`
- **Arguments:** `filesystem` (string) — mount point
- **Returns:** Integer (block size in bytes, typically 1024)
- **Example:**
  ```python
  bs = await client.call("quota", "block_size", "/")
  # Returns: 1024
  ```

### edit_user_quota

Set quota limits for a user on a filesystem.

- **Method:** `quota::edit_user_quota`
- **Arguments:** `user` (string), `filesystem` (string), `soft_blocks` (int), `hard_blocks` (int), `soft_files` (int), `hard_files` (int)
- **Returns:** None
- **Safety Tier:** Dangerous
- **Example:**
  ```python
  await client.call("quota", "edit_user_quota", "alice", "/", 1000, 2000, 100, 200)
  ```

### user_filesystems

Get quota usage for a user across all filesystems.

- **Method:** `quota::user_filesystems`
- **Arguments:** `username` (string)
- **Returns:** Integer count of filesystems. Quota data is stored in Perl global `%filesys` hash.
- **Known Quirks:** Over XML-RPC, only the count is returned. Prefer `user_quota(user, fs)` for reliable data retrieval.

---

## Module: passwd (Password Changes)

**Status: Integrated.** The `change_password` tool uses `passwd::find_user` and `passwd::change_password` instead of `useradmin::modify_user` directly. This provides proper password encryption, shadow timestamp updates, file locking, pre/post hooks, cross-module propagation (Samba, MySQL, etc.), and LDAP user support.

### Functions Used

| Function | Parameters | Returns | Notes |
|----------|------------|---------|-------|
| `passwd::find_user` | `name` (string) | User hash with `mod` key, or `undef` | Searches both local and LDAP backends |
| `passwd::change_password` | `user` (hash), `pass` (string), `do_others` (0\|1) | Nothing | Encrypts password, updates timestamps, runs hooks, propagates to other modules |

---

## Endpoints To Be Documented

The following endpoints may be documented in future phases:

- [x] quota:: — Disk quota management
- [x] passwd:: — Password changes (skipped — covered by useradmin::modify_user)
- [x] acl:: — Webmin ACL management
- [x] software:: — Package management (read-only)
- [x] smart-status:: — SMART disk health
- [x] lvm:: — Logical Volume Manager
- [x] backup-config:: — Configuration backups
- [x] webminlog:: — Audit log access
- [x] time:: — System time
- [x] sshd:: — SSH configuration
- [x] init:: — Runlevels
- [x] fail2ban:: — Intrusion prevention
- [x] mysql:: — Database management
- [ ] firewall:: — Firewall rules (not available on some systems)
- [ ] bind8:: — DNS configuration (not available on some systems)

---

Document Version: 1.6
Last Updated: February 16, 2026
