"""MCP Server for Webmin system administration.

This module sets up the MCP server and registers all available tools
for managing Linux systems via Webmin. Supports multiple Webmin servers.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .config import (
    MultiServerConfig,
    ServerEntry,
    WebminConfig,
    get_server_config,
    load_multi_server_config,
    reset_config_cache,
)
from .models import ToolResult
from .tools import admin, cron, database, files, packages, security, services, storage, system, users
from .webmin_client import (
    WebminAuthError,
    WebminClient,
    WebminClientError,
    WebminConnectionError,
    WebminRPCError,
)

logger = logging.getLogger(__name__)

# Global server instance
server = Server("webmin-mcp-server")


@asynccontextmanager
async def get_client(config: WebminConfig) -> AsyncIterator[WebminClient]:
    """Get a Webmin client.

    XML-RPC uses HTTP Basic Auth on each request, so no explicit
    authentication step is needed.

    Args:
        config: Webmin connection configuration.

    Yields:
        WebminClient instance ready for API calls.
    """
    async with WebminClient(config) as client:
        yield client


def format_result(result: ToolResult) -> list[TextContent]:
    """Format a ToolResult as MCP TextContent.

    Args:
        result: The tool result to format.

    Returns:
        List containing a single TextContent with JSON result.
    """
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


# Common server parameter for all tools
SERVER_PARAM = {
    "server": {
        "type": "string",
        "description": "Server alias (e.g., 'pi1', 'web-server'). Uses default server if not specified.",
    }
}


# Tool definitions
TOOLS = [
    # Management tools for multi-server support
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
                **SERVER_PARAM,
            },
            "required": [],
        },
    ),
    # Phase 0-1: Core system tools
    Tool(
        name="get_webmin_version",
        description=(
            "Get the version of the connected Webmin server. "
            "Returns the version string and hostname."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_system_info",
        description=(
            "Get comprehensive system information including OS, kernel, "
            "CPU, memory, disk usage, and update status. "
            "This is a good starting point for understanding system state."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="list_services",
        description=(
            "List all system services (systemd units or init scripts). "
            "Returns service names. Use get_service_status to check "
            "if a specific service is running."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_service_status",
        description=(
            "Get the status of a specific system service. "
            "Returns whether the service is running or stopped."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "service": {
                    "type": "string",
                    "description": "Name of the service (e.g., 'sshd', 'nginx', 'cron')",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="list_users",
        description=(
            "List all system users. Returns both regular users (UID >= 1000) "
            "and system users separately, with details like home directory and shell."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_disk_usage",
        description=(
            "Get disk usage information for all mounted filesystems. "
            "Shows total, used, and free space, plus inode usage."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_memory_usage",
        description=(
            "Get memory usage information. Shows total, used, and free memory "
            "in KB, MB, and GB, plus buffer and cache usage."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="list_cron_jobs",
        description=(
            "List all scheduled cron jobs. Shows the schedule, command, "
            "user, and whether each job is active."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_network_info",
        description=(
            "Get network configuration including all interfaces (with IP, MAC, "
            "speed), routing table, and default gateway."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    # Phase 2: Service Management Tools
    Tool(
        name="restart_service",
        description=(
            "Restart a system service. The service will be stopped and then "
            "started again. Some critical services (ssh, webmin) may be blocked "
            "in safe mode."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "service": {
                    "type": "string",
                    "description": "Name of the service to restart (e.g., 'nginx', 'cron')",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="start_service",
        description=(
            "Start a stopped system service. If the service is already running, "
            "this is a no-op."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "service": {
                    "type": "string",
                    "description": "Name of the service to start",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="stop_service",
        description=(
            "Stop a running system service. Critical services (ssh, webmin, "
            "systemd services) are blocked to prevent system lockout."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "service": {
                    "type": "string",
                    "description": "Name of the service to stop",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="enable_service",
        description=(
            "Enable a service to start automatically at system boot."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "service": {
                    "type": "string",
                    "description": "Name of the service to enable at boot",
                },
            },
            "required": ["service"],
        },
    ),
    Tool(
        name="disable_service",
        description=(
            "Disable a service from starting automatically at system boot. "
            "Critical services are blocked to prevent boot failures."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "service": {
                    "type": "string",
                    "description": "Name of the service to disable at boot",
                },
            },
            "required": ["service"],
        },
    ),
    # Phase 2: Cron Management Tools
    Tool(
        name="create_cron_job",
        description=(
            "Create a new scheduled cron job. Specify the command to run and "
            "the schedule using cron syntax (minutes, hours, days, months, weekdays). "
            "Use '*' for 'every' (e.g., '*/5' for every 5 minutes)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "command": {
                    "type": "string",
                    "description": "Command to execute",
                },
                "minutes": {
                    "type": "string",
                    "description": "Minutes (0-59, or * for every minute, or */5 for every 5 minutes)",
                    "default": "*",
                },
                "hours": {
                    "type": "string",
                    "description": "Hours (0-23, or * for every hour)",
                    "default": "*",
                },
                "days": {
                    "type": "string",
                    "description": "Day of month (1-31, or * for every day)",
                    "default": "*",
                },
                "months": {
                    "type": "string",
                    "description": "Month (1-12, or * for every month)",
                    "default": "*",
                },
                "weekdays": {
                    "type": "string",
                    "description": "Day of week (0-7, 0 and 7 are Sunday, or * for every day)",
                    "default": "*",
                },
                "user": {
                    "type": "string",
                    "description": "User to run the job as",
                    "default": "root",
                },
                "active": {
                    "type": "boolean",
                    "description": "Whether the job is active",
                    "default": True,
                },
            },
            "required": ["command"],
        },
    ),
    Tool(
        name="edit_cron_job",
        description=(
            "Edit an existing cron job. Use list_cron_jobs to find the job index. "
            "Only specify the fields you want to change."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "index": {
                    "type": "integer",
                    "description": "Index of the job to edit (from list_cron_jobs)",
                },
                "command": {
                    "type": "string",
                    "description": "New command to execute",
                },
                "minutes": {
                    "type": "string",
                    "description": "New minutes value",
                },
                "hours": {
                    "type": "string",
                    "description": "New hours value",
                },
                "days": {
                    "type": "string",
                    "description": "New day of month value",
                },
                "months": {
                    "type": "string",
                    "description": "New month value",
                },
                "weekdays": {
                    "type": "string",
                    "description": "New day of week value",
                },
                "user": {
                    "type": "string",
                    "description": "New user to run as",
                },
                "active": {
                    "type": "boolean",
                    "description": "New active state",
                },
            },
            "required": ["index"],
        },
    ),
    Tool(
        name="delete_cron_job",
        description=(
            "Delete a cron job. This is a dangerous operation and is blocked "
            "in safe mode. Use list_cron_jobs to find the job index."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "index": {
                    "type": "integer",
                    "description": "Index of the job to delete (from list_cron_jobs)",
                },
            },
            "required": ["index"],
        },
    ),
    # Phase 3: User Management Tools
    Tool(
        name="list_groups",
        description=(
            "List all system groups. Returns both regular groups (GID >= 1000) "
            "and system groups separately, with member information."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="create_user",
        description=(
            "Create a new system user. This is a dangerous operation and is "
            "blocked in safe mode."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "username": {
                    "type": "string",
                    "description": "Username (lowercase letters, digits, underscores, hyphens)",
                },
                "password": {
                    "type": "string",
                    "description": "Password for the new user",
                },
                "real_name": {
                    "type": "string",
                    "description": "Full name or comment",
                },
                "home_dir": {
                    "type": "string",
                    "description": "Home directory (default: /home/username)",
                },
                "shell": {
                    "type": "string",
                    "description": "Login shell (default: /bin/bash)",
                },
                "uid": {
                    "type": "integer",
                    "description": "User ID (auto-assigned if not specified)",
                },
                "gid": {
                    "type": "integer",
                    "description": "Group ID (auto-assigned if not specified)",
                },
            },
            "required": ["username", "password"],
        },
    ),
    Tool(
        name="delete_user",
        description=(
            "Delete a system user. This is a dangerous operation and is "
            "blocked in safe mode. Critical system users cannot be deleted."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "username": {
                    "type": "string",
                    "description": "Username of the user to delete",
                },
                "delete_home": {
                    "type": "boolean",
                    "description": "Whether to delete the user's home directory",
                    "default": False,
                },
            },
            "required": ["username"],
        },
    ),
    Tool(
        name="modify_user",
        description=(
            "Modify an existing system user. Only specify fields you want to change."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "username": {
                    "type": "string",
                    "description": "Current username of the user to modify",
                },
                "new_username": {
                    "type": "string",
                    "description": "New username",
                },
                "real_name": {
                    "type": "string",
                    "description": "New full name or comment",
                },
                "home_dir": {
                    "type": "string",
                    "description": "New home directory",
                },
                "shell": {
                    "type": "string",
                    "description": "New login shell",
                },
                "uid": {
                    "type": "integer",
                    "description": "New user ID",
                },
                "gid": {
                    "type": "integer",
                    "description": "New group ID",
                },
            },
            "required": ["username"],
        },
    ),
    Tool(
        name="change_password",
        description=(
            "Change a user's password. This is a dangerous operation and is "
            "blocked in safe mode."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "username": {
                    "type": "string",
                    "description": "Username of the user",
                },
                "new_password": {
                    "type": "string",
                    "description": "New password",
                },
            },
            "required": ["username", "new_password"],
        },
    ),
    # Phase 3: Package Information Tools (Read-only)
    Tool(
        name="get_package_info",
        description=(
            "Get detailed information about an installed package including "
            "version, description, maintainer, and install date."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "package_name": {
                    "type": "string",
                    "description": "Name of the package to query",
                },
            },
            "required": ["package_name"],
        },
    ),
    Tool(
        name="list_available_updates",
        description=(
            "List all available package updates including security updates. "
            "Shows current and new versions for each package."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_package_count",
        description="Get the total count of installed packages on the system.",
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    # Phase 4: File Management Tools
    Tool(
        name="read_file",
        description=(
            "Read the contents of a file from the remote system. "
            "Can return content as a string or as an array of lines."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to read",
                },
                "as_lines": {
                    "type": "boolean",
                    "description": "If true, return content as array of lines",
                    "default": False,
                },
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="write_file",
        description=(
            "Write content to a file. This is a dangerous operation. "
            "In safe mode, only writes to /tmp and /var/tmp are allowed. "
            "System directories (/etc, /bin, /usr, etc.) are always blocked."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
    ),
    Tool(
        name="delete_file",
        description=(
            "Delete a file or empty directory. This is a dangerous operation. "
            "In safe mode, only deletes in /tmp and /var/tmp are allowed. "
            "System directories are always protected."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file or directory to delete",
                },
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="copy_file",
        description=(
            "Copy a file to a new location. In safe mode, destination must be "
            "in /tmp or /var/tmp."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "source": {
                    "type": "string",
                    "description": "Absolute path to the source file",
                },
                "destination": {
                    "type": "string",
                    "description": "Absolute path to the destination",
                },
            },
            "required": ["source", "destination"],
        },
    ),
    Tool(
        name="rename_file",
        description=(
            "Rename or move a file. In safe mode, both source and destination "
            "must be in /tmp or /var/tmp."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "source": {
                    "type": "string",
                    "description": "Absolute path to the source file",
                },
                "destination": {
                    "type": "string",
                    "description": "Absolute path to the new location/name",
                },
            },
            "required": ["source", "destination"],
        },
    ),
    Tool(
        name="create_directory",
        description=(
            "Create a new directory. In safe mode, only directories in "
            "/tmp or /var/tmp can be created."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "path": {
                    "type": "string",
                    "description": "Absolute path to the directory to create",
                },
                "mode": {
                    "type": "integer",
                    "description": "Permission mode (e.g., 755)",
                    "default": 755,
                },
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="list_processes",
        description=(
            "List all running processes on the system. Shows PID, user, "
            "CPU usage, memory, and command for each process."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="list_mounts",
        description=(
            "List all mounted filesystems. Shows mount point, device, "
            "filesystem type, and mount options."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    # Phase 5: Storage Management Tools
    Tool(
        name="list_disks",
        description=(
            "List all physical disks with SMART capability. Shows device path, "
            "model, serial number, capacity, and whether SMART is enabled."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_disk_health",
        description=(
            "Get SMART health status for a specific disk. Returns overall health, "
            "temperature, power-on hours, SMART attributes, and any errors or warnings."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "device": {
                    "type": "string",
                    "description": "Device path (e.g., '/dev/sda', '/dev/nvme0n1')",
                },
            },
            "required": ["device"],
        },
    ),
    Tool(
        name="list_volume_groups",
        description=(
            "List all LVM volume groups. Shows name, total size, free space, "
            "physical volume count, and logical volume count for each VG."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="list_logical_volumes",
        description=(
            "List all LVM logical volumes. Shows name, size, volume group, "
            "device path, and mount point for each LV."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "volume_group": {
                    "type": "string",
                    "description": "Optional volume group name to filter by",
                },
            },
            "required": [],
        },
    ),
    # Phase 6: System Administration Tools
    Tool(
        name="get_system_time",
        description=(
            "Get the current system time and timezone configuration."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="list_runlevels",
        description=(
            "List system runlevels and their descriptions."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_ssh_config",
        description=(
            "Get SSH server (sshd) configuration settings including port, "
            "authentication methods, and security options."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    # Phase 6: Audit & Logging Tools
    Tool(
        name="list_webmin_logs",
        description=(
            "List Webmin action/audit logs. Shows recent actions performed "
            "through Webmin including user, module, and action details."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of log entries to return (default: 100)",
                },
                "module": {
                    "type": "string",
                    "description": "Filter by module name (e.g., 'useradmin', 'init')",
                },
                "user": {
                    "type": "string",
                    "description": "Filter by username",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="list_backups",
        description=(
            "List Webmin configuration backups. Shows available backups "
            "that can be restored."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    # Phase 6: Security Tools (Fail2ban)
    Tool(
        name="list_fail2ban_jails",
        description=(
            "List all Fail2ban jails and their status. Shows which jails "
            "are enabled and their current ban counts."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_fail2ban_status",
        description=(
            "Get Fail2ban status for a specific jail or overall. Returns "
            "currently banned IPs and ban counts."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "jail": {
                    "type": "string",
                    "description": "Jail name for specific status (optional)",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="list_banned_ips",
        description=(
            "List all currently banned IP addresses from Fail2ban."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                **SERVER_PARAM,
                "jail": {
                    "type": "string",
                    "description": "Filter by jail name (optional)",
                },
            },
            "required": [],
        },
    ),
    # Phase 6: Database Tools (MySQL)
    Tool(
        name="list_mysql_databases",
        description=(
            "List all MySQL databases. Separates user databases from "
            "system databases (information_schema, mysql, etc.)."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="list_mysql_users",
        description=(
            "List all MySQL users and their host permissions."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
    Tool(
        name="get_mysql_status",
        description=(
            "Get MySQL server status including version, uptime, "
            "connections, and query statistics."
        ),
        inputSchema={
            "type": "object",
            "properties": {**SERVER_PARAM},
            "required": [],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls with multi-server support.

    Args:
        name: Name of the tool to call.
        arguments: Tool arguments (may include 'server' for multi-server).

    Returns:
        Tool result as TextContent.
    """
    logger.debug("Tool call: %s with args: %s", name, arguments)

    # Handle management tools that don't need a server connection
    if name == "list_webmin_servers":
        try:
            config = load_multi_server_config()
            return format_result(ToolResult.ok({
                "servers": config.list_servers(),
                "count": len(config.servers),
            }))
        except Exception as e:
            return format_result(ToolResult.fail(
                code="CONFIG_ERROR",
                message=f"Failed to load server configuration: {e}",
            ))

    # Get multi-server configuration
    try:
        multi_config = load_multi_server_config()
    except Exception as e:
        logger.error("Configuration error: %s", e)
        return format_result(
            ToolResult.fail(
                code="CONFIG_ERROR",
                message="Webmin configuration is missing or invalid. "
                "Either create webmin-servers.json or set WEBMIN_* environment variables.",
                details={"error": str(e)},
            )
        )

    # Extract server alias from arguments (optional)
    server_alias = arguments.pop("server", None)

    # Get the specific server config
    try:
        alias, server_entry = multi_config.get_server(server_alias)
    except ValueError as e:
        return format_result(ToolResult.fail(
            code="UNKNOWN_SERVER",
            message=str(e),
            details={"available_servers": list(multi_config.servers.keys())},
        ))

    # Convert to WebminConfig for compatibility
    config = server_entry.to_webmin_config()

    logger.debug("Using server '%s' (%s:%d)", alias, server_entry.host, server_entry.port)

    # Execute tool
    try:
        async with get_client(config) as client:
            result = await dispatch_tool(client, name, arguments, config, alias)
            return format_result(result)

    except WebminAuthError as e:
        logger.error("[%s] Authentication error: %s", alias, e)
        return format_result(ToolResult.fail(
            code=e.code,
            message=f"[{alias}] {e.message}",
        ))

    except WebminConnectionError as e:
        logger.error("[%s] Connection error: %s", alias, e)
        return format_result(ToolResult.fail(
            code=e.code,
            message=f"[{alias}] {e.message}",
        ))

    except WebminRPCError as e:
        logger.error("[%s] RPC error: %s", alias, e)
        return format_result(ToolResult.fail(
            code=e.code,
            message=f"[{alias}] {e.message}",
        ))

    except WebminClientError as e:
        logger.error("[%s] Webmin client error: %s", alias, e)
        return format_result(ToolResult.fail(
            code=e.code,
            message=f"[{alias}] {e.message}",
        ))


async def dispatch_tool(
    client: WebminClient,
    name: str,
    arguments: dict[str, Any],
    config: WebminConfig,
    server_alias: str = "default",
) -> ToolResult:
    """Dispatch a tool call to the appropriate handler.

    Args:
        client: Authenticated WebminClient.
        name: Tool name.
        arguments: Tool arguments.
        config: Webmin configuration (for safety settings).
        server_alias: Alias of the server being queried.

    Returns:
        ToolResult from the tool handler.
    """
    # Phase 0 tools
    if name == "get_webmin_version" or name == "test_server_connection":
        version_info = await client.get_version()
        return ToolResult.ok({
            "server": server_alias,
            "host": config.host,
            "version": version_info.version,
            "hostname": version_info.hostname,
        })

    # Phase 1 tools
    if name == "get_system_info":
        return await system.get_system_info(client)

    if name == "list_services":
        return await system.list_services(client)

    if name == "get_service_status":
        service = arguments.get("service")
        if not service:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: service",
            )
        return await system.get_service_status(client, service)

    if name == "list_users":
        return await system.list_users(client)

    if name == "get_disk_usage":
        return await system.get_disk_usage(client)

    if name == "get_memory_usage":
        return await system.get_memory_usage(client)

    if name == "list_cron_jobs":
        return await system.list_cron_jobs(client)

    if name == "get_network_info":
        return await system.get_network_info(client)

    # Phase 2 tools - Service Management
    if name == "restart_service":
        service = arguments.get("service")
        if not service:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: service",
            )
        return await services.restart_service(client, service, config.safe_mode)

    if name == "start_service":
        service = arguments.get("service")
        if not service:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: service",
            )
        return await services.start_service(client, service, config.safe_mode)

    if name == "stop_service":
        service = arguments.get("service")
        if not service:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: service",
            )
        return await services.stop_service(client, service, config.safe_mode)

    if name == "enable_service":
        service = arguments.get("service")
        if not service:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: service",
            )
        return await services.enable_service(client, service, config.safe_mode)

    if name == "disable_service":
        service = arguments.get("service")
        if not service:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: service",
            )
        return await services.disable_service(client, service, config.safe_mode)

    # Phase 2 tools - Cron Management
    if name == "create_cron_job":
        command = arguments.get("command")
        if not command:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: command",
            )
        return await cron.create_cron_job(
            client,
            command=command,
            minutes=arguments.get("minutes", "*"),
            hours=arguments.get("hours", "*"),
            days=arguments.get("days", "*"),
            months=arguments.get("months", "*"),
            weekdays=arguments.get("weekdays", "*"),
            user=arguments.get("user", "root"),
            active=arguments.get("active", True),
            safe_mode=config.safe_mode,
        )

    if name == "edit_cron_job":
        index = arguments.get("index")
        if index is None:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: index",
            )
        return await cron.edit_cron_job(
            client,
            index=index,
            command=arguments.get("command"),
            minutes=arguments.get("minutes"),
            hours=arguments.get("hours"),
            days=arguments.get("days"),
            months=arguments.get("months"),
            weekdays=arguments.get("weekdays"),
            user=arguments.get("user"),
            active=arguments.get("active"),
            safe_mode=config.safe_mode,
        )

    if name == "delete_cron_job":
        index = arguments.get("index")
        if index is None:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: index",
            )
        return await cron.delete_cron_job(client, index, config.safe_mode)

    # Phase 3 tools - User Management
    if name == "list_groups":
        return await users.list_groups(client)

    if name == "create_user":
        username = arguments.get("username")
        password = arguments.get("password")
        if not username:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: username",
            )
        if not password:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: password",
            )
        return await users.create_user(
            client,
            username=username,
            password=password,
            real_name=arguments.get("real_name"),
            home_dir=arguments.get("home_dir"),
            shell=arguments.get("shell", "/bin/bash"),
            uid=arguments.get("uid"),
            gid=arguments.get("gid"),
            safe_mode=config.safe_mode,
        )

    if name == "delete_user":
        username = arguments.get("username")
        if not username:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: username",
            )
        return await users.delete_user(
            client,
            username=username,
            delete_home=arguments.get("delete_home", False),
            safe_mode=config.safe_mode,
        )

    if name == "modify_user":
        username = arguments.get("username")
        if not username:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: username",
            )
        return await users.modify_user(
            client,
            username=username,
            new_username=arguments.get("new_username"),
            real_name=arguments.get("real_name"),
            home_dir=arguments.get("home_dir"),
            shell=arguments.get("shell"),
            uid=arguments.get("uid"),
            gid=arguments.get("gid"),
            safe_mode=config.safe_mode,
        )

    if name == "change_password":
        username = arguments.get("username")
        new_password = arguments.get("new_password")
        if not username:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: username",
            )
        if not new_password:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: new_password",
            )
        return await users.change_password(
            client,
            username=username,
            new_password=new_password,
            safe_mode=config.safe_mode,
        )

    # Phase 3 tools - Package Information
    if name == "get_package_info":
        package_name = arguments.get("package_name")
        if not package_name:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: package_name",
            )
        return await packages.get_package_info(client, package_name)

    if name == "list_available_updates":
        return await packages.list_available_updates(client)

    if name == "get_package_count":
        return await packages.get_package_count(client)

    # Phase 4 tools - File Management
    if name == "read_file":
        path = arguments.get("path")
        if not path:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: path",
            )
        return await files.read_file(
            client,
            path=path,
            as_lines=arguments.get("as_lines", False),
        )

    if name == "write_file":
        path = arguments.get("path")
        content = arguments.get("content")
        if not path:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: path",
            )
        if content is None:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: content",
            )
        return await files.write_file(
            client,
            path=path,
            content=content,
            safe_mode=config.safe_mode,
        )

    if name == "delete_file":
        path = arguments.get("path")
        if not path:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: path",
            )
        return await files.delete_file(
            client,
            path=path,
            safe_mode=config.safe_mode,
        )

    if name == "copy_file":
        source = arguments.get("source")
        destination = arguments.get("destination")
        if not source:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: source",
            )
        if not destination:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: destination",
            )
        return await files.copy_file(
            client,
            source=source,
            destination=destination,
            safe_mode=config.safe_mode,
        )

    if name == "rename_file":
        source = arguments.get("source")
        destination = arguments.get("destination")
        if not source:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: source",
            )
        if not destination:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: destination",
            )
        return await files.rename_file(
            client,
            source=source,
            destination=destination,
            safe_mode=config.safe_mode,
        )

    if name == "create_directory":
        path = arguments.get("path")
        if not path:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: path",
            )
        return await files.create_directory(
            client,
            path=path,
            mode=arguments.get("mode", 755),
            safe_mode=config.safe_mode,
        )

    if name == "list_processes":
        return await files.list_processes(client)

    if name == "list_mounts":
        return await files.list_mounts(client)

    # Phase 5 tools - Storage Management
    if name == "list_disks":
        return await storage.list_disks(client)

    if name == "get_disk_health":
        device = arguments.get("device")
        if not device:
            return ToolResult.fail(
                code="MISSING_ARGUMENT",
                message="Missing required argument: device",
            )
        return await storage.get_disk_health(client, device)

    if name == "list_volume_groups":
        return await storage.list_volume_groups(client)

    if name == "list_logical_volumes":
        return await storage.list_logical_volumes(
            client,
            volume_group=arguments.get("volume_group"),
        )

    # Phase 6 tools - System Administration
    if name == "get_system_time":
        return await admin.get_system_time(client)

    if name == "list_runlevels":
        return await admin.list_runlevels(client)

    if name == "get_ssh_config":
        return await admin.get_ssh_config(client)

    # Phase 6 tools - Audit & Logging
    if name == "list_webmin_logs":
        return await admin.list_webmin_logs(
            client,
            limit=arguments.get("limit", 100),
            module=arguments.get("module"),
            user=arguments.get("user"),
        )

    if name == "list_backups":
        return await admin.list_backups(client)

    # Phase 6 tools - Security (Fail2ban)
    if name == "list_fail2ban_jails":
        return await security.list_fail2ban_jails(client)

    if name == "get_fail2ban_status":
        return await security.get_fail2ban_status(
            client,
            jail=arguments.get("jail"),
        )

    if name == "list_banned_ips":
        return await security.list_banned_ips(
            client,
            jail=arguments.get("jail"),
        )

    # Phase 6 tools - Database (MySQL)
    if name == "list_mysql_databases":
        return await database.list_mysql_databases(client)

    if name == "list_mysql_users":
        return await database.list_mysql_users(client)

    if name == "get_mysql_status":
        return await database.get_mysql_status(client)

    # Unknown tool
    return ToolResult.fail(
        code="UNKNOWN_TOOL",
        message=f"Unknown tool: {name}",
    )


def setup_logging(level: str) -> None:
    """Configure logging for the server.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR).
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def run_server() -> None:
    """Run the MCP server using stdio transport."""
    server_config = get_server_config()
    setup_logging(server_config.log_level)

    logger.info("Starting Webmin MCP Server")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for the MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
