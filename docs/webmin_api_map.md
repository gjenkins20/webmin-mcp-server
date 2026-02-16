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
- **Returns:** List of user dictionaries

### list_groups

List all system groups.

- **Method:** `useradmin::list_groups`
- **Arguments:** None
- **Returns:** List of group dictionaries

### create_user / delete_user

Manage users.

- **Methods:**
  - `useradmin::create_user`
  - `useradmin::delete_user`
- **Safety Tier:** Dangerous

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
- [ ] software:: — Package management
- [ ] smart_status:: — SMART disk health
- [ ] backup_config:: — Configuration backups
- [ ] webminlog:: — Audit log access
- [ ] firewall:: — Firewall rules
- [ ] bind8:: — DNS configuration

---

Document Version: 1.1
Last Updated: February 16, 2026
