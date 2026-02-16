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

## Endpoints To Be Documented

The following endpoints will be documented as features are implemented:

- [ ] quota:: — Disk quota management
- [ ] passwd:: — Password changes
- [ ] acl:: — Webmin ACL management
- [x] software:: — Package management (read-only)
- [ ] smart_status:: — SMART disk health
- [ ] backup_config:: — Configuration backups
- [ ] webminlog:: — Audit log access
- [ ] firewall:: — Firewall rules
- [ ] bind8:: — DNS configuration

---

Document Version: 1.2
Last Updated: February 16, 2026
