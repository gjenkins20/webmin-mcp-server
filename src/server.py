"""MCP Server for Webmin system administration.

This module sets up the MCP server and registers all available tools
for managing Linux systems via Webmin.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .config import WebminConfig, get_server_config, get_webmin_config
from .models import ToolResult
from .tools import services, system
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


# Tool definitions for Phase 1
TOOLS = [
    Tool(
        name="get_webmin_version",
        description=(
            "Get the version of the connected Webmin server. "
            "Returns the version string and hostname."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
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
            "properties": {},
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
            "properties": {},
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
            "properties": {},
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
            "properties": {},
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
            "properties": {},
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
            "properties": {},
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
            "properties": {},
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
                "service": {
                    "type": "string",
                    "description": "Name of the service to disable at boot",
                },
            },
            "required": ["service"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls.

    Args:
        name: Name of the tool to call.
        arguments: Tool arguments.

    Returns:
        Tool result as TextContent.
    """
    logger.debug("Tool call: %s with args: %s", name, arguments)

    # Get configuration
    try:
        config = get_webmin_config()
    except Exception as e:
        logger.error("Configuration error: %s", e)
        return format_result(
            ToolResult.fail(
                code="CONFIG_ERROR",
                message="Webmin configuration is missing or invalid. "
                "Ensure WEBMIN_HOST, WEBMIN_USERNAME, and WEBMIN_PASSWORD "
                "environment variables are set.",
                details={"error": str(e)},
            )
        )

    # Execute tool
    try:
        async with get_client(config) as client:
            result = await dispatch_tool(client, name, arguments, config)
            return format_result(result)

    except WebminAuthError as e:
        logger.error("Authentication error: %s", e)
        return format_result(ToolResult.fail(code=e.code, message=e.message))

    except WebminConnectionError as e:
        logger.error("Connection error: %s", e)
        return format_result(ToolResult.fail(code=e.code, message=e.message))

    except WebminRPCError as e:
        logger.error("RPC error: %s", e)
        return format_result(ToolResult.fail(code=e.code, message=e.message))

    except WebminClientError as e:
        logger.error("Webmin client error: %s", e)
        return format_result(ToolResult.fail(code=e.code, message=e.message))


async def dispatch_tool(
    client: WebminClient,
    name: str,
    arguments: dict[str, Any],
    config: WebminConfig,
) -> ToolResult:
    """Dispatch a tool call to the appropriate handler.

    Args:
        client: Authenticated WebminClient.
        name: Tool name.
        arguments: Tool arguments.
        config: Webmin configuration (for safety settings).

    Returns:
        ToolResult from the tool handler.
    """
    # Phase 0 tools
    if name == "get_webmin_version":
        version_info = await client.get_version()
        return ToolResult.ok({
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
