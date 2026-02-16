# Multi-Server Configuration Design

## Overview

This document describes the design for supporting multiple Webmin servers in a single MCP server instance, allowing users to manage multiple hosts through natural language.

## Goals

1. **User-friendly aliases** - Name servers `pi1`, `web-server`, etc.
2. **Backward compatible** - Existing single-server configs continue to work
3. **Natural language** - "List services on pi1" works intuitively
4. **Default server** - Commands without server specified use default
5. **Per-server settings** - Each server can have different timeouts, safe_mode, etc.

## Configuration Schema

### Option A: JSON Configuration File (Recommended)

**File: `webmin-servers.json` or `~/.config/webmin-mcp/servers.json`**

```json
{
  "default_server": "pi1",
  "servers": {
    "pi1": {
      "host": "192.168.1.120",
      "port": 10000,
      "username": "webmin-mcp",
      "password": "secret123",
      "use_https": true,
      "verify_ssl": false,
      "safe_mode": true,
      "connect_timeout": 10.0,
      "read_timeout": 30.0
    },
    "web-server": {
      "host": "192.168.1.50",
      "port": 10000,
      "username": "admin",
      "password": "different-secret",
      "use_https": true,
      "verify_ssl": false,
      "safe_mode": false
    },
    "nas": {
      "host": "nas.local",
      "port": 10000,
      "username": "root",
      "password": "nas-password"
    }
  }
}
```

### Option B: Environment Variables (Single Server - Backward Compatible)

Existing env var format continues to work for single-server setups:

```bash
WEBMIN_HOST=192.168.1.120
WEBMIN_PORT=10000
WEBMIN_USERNAME=webmin-mcp
WEBMIN_PASSWORD=secret123
```

When JSON config exists, it takes precedence over env vars.

### Option C: Claude Desktop Config (Inline)

For Claude Desktop users, servers can be defined inline:

```json
{
  "mcpServers": {
    "webmin": {
      "command": "/path/to/uv",
      "args": ["run", "--directory", "/path/to/webmin-mcp-server", "python", "-m", "src.server"],
      "env": {
        "WEBMIN_SERVERS_JSON": "{\"default_server\":\"pi1\",\"servers\":{\"pi1\":{\"host\":\"192.168.1.120\",...}}}"
      }
    }
  }
}
```

Or reference an external file:

```json
{
  "env": {
    "WEBMIN_CONFIG_FILE": "/path/to/webmin-servers.json"
  }
}
```

## Configuration Loading Priority

1. `WEBMIN_CONFIG_FILE` env var → Load JSON from specified path
2. `WEBMIN_SERVERS_JSON` env var → Parse inline JSON
3. `./webmin-servers.json` → Local file in working directory
4. `~/.config/webmin-mcp/servers.json` → User config directory
5. `WEBMIN_*` env vars → Single server fallback (backward compatible)

## Pydantic Models

### New Models in `config.py`

```python
from typing import Dict, Optional
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings

class ServerConfig(BaseModel):
    """Configuration for a single Webmin server."""

    host: str = Field(description="Webmin server hostname or IP")
    port: int = Field(default=10000, ge=1, le=65535)
    username: str = Field(description="Webmin username")
    password: SecretStr = Field(description="Webmin password")
    use_https: bool = Field(default=True)
    verify_ssl: bool = Field(default=True)
    safe_mode: bool = Field(default=True)
    connect_timeout: float = Field(default=10.0, gt=0)
    read_timeout: float = Field(default=30.0, gt=0)

    @property
    def base_url(self) -> str:
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{self.host}:{self.port}"


class MultiServerConfig(BaseModel):
    """Configuration for multiple Webmin servers."""

    default_server: str = Field(description="Alias of default server")
    servers: Dict[str, ServerConfig] = Field(description="Server configs by alias")

    def get_server(self, alias: Optional[str] = None) -> tuple[str, ServerConfig]:
        """Get server config by alias, or default if not specified.

        Returns:
            Tuple of (alias, config)
        """
        if alias is None:
            alias = self.default_server

        if alias not in self.servers:
            raise ValueError(f"Unknown server: {alias}. Available: {list(self.servers.keys())}")

        return alias, self.servers[alias]

    def list_servers(self) -> list[dict]:
        """List all configured servers with metadata."""
        return [
            {
                "alias": alias,
                "host": config.host,
                "port": config.port,
                "is_default": alias == self.default_server,
            }
            for alias, config in self.servers.items()
        ]
```

### Configuration Loading Function

```python
import json
import os
from pathlib import Path

def load_config() -> MultiServerConfig:
    """Load server configuration from available sources."""

    # Priority 1: Explicit config file path
    if config_file := os.environ.get("WEBMIN_CONFIG_FILE"):
        return _load_from_file(Path(config_file))

    # Priority 2: Inline JSON in env var
    if json_str := os.environ.get("WEBMIN_SERVERS_JSON"):
        data = json.loads(json_str)
        return MultiServerConfig(**data)

    # Priority 3: Local file
    local_file = Path("webmin-servers.json")
    if local_file.exists():
        return _load_from_file(local_file)

    # Priority 4: User config directory
    user_config = Path.home() / ".config" / "webmin-mcp" / "servers.json"
    if user_config.exists():
        return _load_from_file(user_config)

    # Priority 5: Legacy single-server env vars (backward compatible)
    return _load_legacy_config()


def _load_from_file(path: Path) -> MultiServerConfig:
    """Load config from JSON file."""
    with open(path) as f:
        data = json.load(f)
    return MultiServerConfig(**data)


def _load_legacy_config() -> MultiServerConfig:
    """Load legacy single-server config from env vars."""
    # Creates a single server named "default" from WEBMIN_* env vars
    config = WebminConfig()  # Existing class, loads from env

    return MultiServerConfig(
        default_server="default",
        servers={
            "default": ServerConfig(
                host=config.host,
                port=config.port,
                username=config.username,
                password=config.password,
                use_https=config.use_https,
                verify_ssl=config.verify_ssl,
                safe_mode=config.safe_mode,
                connect_timeout=config.connect_timeout,
                read_timeout=config.read_timeout,
            )
        }
    )
```

## Tool Schema Changes

### Adding `server` Parameter to All Tools

Every tool gets an optional `server` parameter:

```python
Tool(
    name="get_system_info",
    description=(
        "Get comprehensive system information. "
        "Optionally specify which server to query."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Server alias (e.g., 'pi1', 'web-server'). Uses default if not specified.",
            },
        },
        "required": [],
    },
),
```

### New Management Tools

```python
Tool(
    name="list_webmin_servers",
    description="List all configured Webmin servers and their connection status.",
    inputSchema={
        "type": "object",
        "properties": {},
        "required": [],
    },
),

Tool(
    name="get_server_info",
    description="Get detailed information about a specific configured server.",
    inputSchema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Server alias to get info for. Uses default if not specified.",
            },
        },
        "required": [],
    },
),
```

## Dispatch Changes

### Updated `call_tool` Handler

```python
# Global config loaded once at startup
_config: MultiServerConfig | None = None

def get_config() -> MultiServerConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls with multi-server support."""

    config = get_config()

    # Extract server alias from arguments (optional)
    server_alias = arguments.pop("server", None)

    try:
        alias, server_config = config.get_server(server_alias)
    except ValueError as e:
        return format_result(ToolResult.fail(
            code="UNKNOWN_SERVER",
            message=str(e),
            details={"available_servers": list(config.servers.keys())},
        ))

    # Execute tool against selected server
    try:
        async with get_client(server_config) as client:
            result = await dispatch_tool(client, name, arguments, server_config, alias)
            return format_result(result)
    except WebminConnectionError as e:
        # Include server alias in error for clarity
        return format_result(ToolResult.fail(
            code=e.code,
            message=f"[{alias}] {e.message}",
        ))
```

## User Experience Examples

### Natural Language Queries

| User Query | Parsed Tool Call |
|------------|------------------|
| "List services" | `list_services(server=None)` → uses default |
| "List services on pi1" | `list_services(server="pi1")` |
| "Show disk usage on web-server" | `get_disk_usage(server="web-server")` |
| "What servers are configured?" | `list_webmin_servers()` |
| "Is SSH running on the NAS?" | `get_service_status(service="ssh", server="nas")` |
| "Compare uptime on all servers" | Multiple calls to each server |

### Response Format

Responses include server context:

```json
{
  "success": true,
  "data": {
    "server": "pi1",
    "server_host": "192.168.1.120",
    "hostname": "raspberrypi",
    "os": "Debian Linux 12",
    "uptime": "15 days, 3:42"
  }
}
```

## Migration Path

1. **Phase 1**: Add multi-server config loading with backward compatibility
2. **Phase 2**: Add `server` parameter to all tool schemas
3. **Phase 3**: Update dispatch to use server parameter
4. **Phase 4**: Add management tools (`list_webmin_servers`, etc.)
5. **Phase 5**: Update documentation and examples

## Security Considerations

1. **Password storage**: JSON config contains plaintext passwords
   - Recommend file permissions `600` (owner read/write only)
   - Future: Support for secret references (env vars, keychains)

2. **Safe mode per-server**: Each server can have different safe_mode settings
   - Production servers: `safe_mode: true`
   - Dev/test servers: `safe_mode: false`

3. **Audit logging**: Include server alias in all log messages

## Tool Interface Changes

### All 48 Tools Requiring `server` Parameter

Each tool gets an optional `server` parameter added to its schema:

**Phase 0-1: Core System (9 tools)**
- `get_webmin_version`
- `get_system_info`
- `list_services`
- `get_service_status`
- `list_users`
- `get_disk_usage`
- `get_memory_usage`
- `list_cron_jobs`
- `get_network_info`

**Phase 2: Service Management (5 tools)**
- `restart_service`
- `start_service`
- `stop_service`
- `enable_service`
- `disable_service`

**Phase 2: Cron Management (3 tools)**
- `create_cron_job`
- `edit_cron_job`
- `delete_cron_job`

**Phase 3: User Management (5 tools)**
- `list_groups`
- `create_user`
- `delete_user`
- `modify_user`
- `change_password`

**Phase 3: Package Management (3 tools)**
- `get_package_info`
- `list_available_updates`
- `get_package_count`

**Phase 4: File Operations (6 tools)**
- `read_file`
- `write_file`
- `delete_file`
- `copy_file`
- `rename_file`
- `create_directory`

**Phase 4: Process Management (1 tool)**
- `list_processes`

**Phase 5: Storage Management (5 tools)**
- `list_mounts`
- `list_disks`
- `get_disk_health`
- `list_volume_groups`
- `list_logical_volumes`

**Phase 6: System Admin (5 tools)**
- `get_system_time`
- `list_runlevels`
- `get_ssh_config`
- `list_webmin_logs`
- `list_backups`

**Phase 6: Security (3 tools)**
- `list_fail2ban_jails`
- `get_fail2ban_status`
- `list_banned_ips`

**Phase 6: Database (3 tools)**
- `list_mysql_databases`
- `list_mysql_users`
- `get_mysql_status`

### New Management Tools (2 tools)

**Total after implementation: 50 tools**

```python
Tool(
    name="list_webmin_servers",
    description=(
        "List all configured Webmin servers with their aliases and connection info. "
        "Shows which server is the default."
    ),
    inputSchema={
        "type": "object",
        "properties": {},
        "required": [],
    },
),

Tool(
    name="test_server_connection",
    description=(
        "Test connectivity to a specific Webmin server. "
        "Returns version and hostname if successful."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "Server alias to test. Tests default if not specified.",
            },
        },
        "required": [],
    },
),
```

### Schema Update Pattern

To efficiently update all 48 tools, use a helper function:

```python
def add_server_param(schema: dict) -> dict:
    """Add optional server parameter to a tool schema."""
    props = schema.get("properties", {})
    props["server"] = {
        "type": "string",
        "description": "Server alias (e.g., 'pi1'). Uses default server if not specified.",
    }
    schema["properties"] = props
    return schema
```

Or define the server property once and merge:

```python
SERVER_PARAM = {
    "server": {
        "type": "string",
        "description": "Server alias (e.g., 'pi1'). Uses default server if not specified.",
    }
}

# In tool definition:
inputSchema={
    "type": "object",
    "properties": {
        **SERVER_PARAM,
        "service": {"type": "string", "description": "Service name"},
    },
    "required": ["service"],
},
```

## Implementation Order

1. **config.py changes**
   - Add `ServerConfig` model
   - Add `MultiServerConfig` model
   - Add `load_config()` function
   - Keep backward compatibility with `WebminConfig`

2. **server.py changes - Config loading**
   - Replace `get_webmin_config()` with `load_config()`
   - Update `call_tool()` to extract `server` param
   - Update dispatch to pass server alias

3. **server.py changes - Tool schemas**
   - Add `SERVER_PARAM` constant
   - Update all 48 tool schemas
   - Add 2 new management tools

4. **server.py changes - Dispatch**
   - Update `dispatch_tool()` signature
   - Add server alias to result data
   - Add handlers for new management tools

5. **Example config file**
   - Create `webmin-servers.example.json`
   - Update `.gitignore`

6. **Tests**
   - Add `test_config_multiserver.py`
   - Update existing tests for backward compat

## File Locations

| File | Purpose |
|------|---------|
| `src/config.py` | Add `MultiServerConfig`, `load_config()` |
| `src/server.py` | Update dispatch, add management tools |
| `webmin-servers.example.json` | Example multi-server config |
| `.gitignore` | Add `webmin-servers.json` |
