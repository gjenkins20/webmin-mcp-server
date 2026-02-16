"""MCP Server for Webmin system administration.

This module sets up the MCP server and registers all available tools
for managing Linux systems via Webmin.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .config import WebminConfig, get_server_config, get_webmin_config
from .models import ToolResult
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


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="get_webmin_version",
            description=(
                "Get the version of the connected Webmin server. "
                "Returns the version string and optionally the hostname. "
                "Uses XML-RPC with CGI fallback."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls.

    Args:
        name: Name of the tool to call.
        arguments: Tool arguments (may be empty).

    Returns:
        Tool result as TextContent.
    """
    logger.debug("Tool call: %s with args: %s", name, arguments)

    if name == "get_webmin_version":
        return await handle_get_webmin_version()

    return format_result(
        ToolResult.fail(
            code="UNKNOWN_TOOL",
            message=f"Unknown tool: {name}",
        )
    )


async def handle_get_webmin_version() -> list[TextContent]:
    """Handle the get_webmin_version tool call.

    Returns:
        Version information or error.
    """
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

    try:
        async with get_client(config) as client:
            version_info = await client.get_version()
            return format_result(
                ToolResult.ok(
                    {
                        "version": version_info.version,
                        "hostname": version_info.hostname,
                    }
                )
            )
    except WebminAuthError as e:
        logger.error("Authentication error: %s", e)
        return format_result(
            ToolResult.fail(
                code=e.code,
                message=e.message,
            )
        )
    except WebminConnectionError as e:
        logger.error("Connection error: %s", e)
        return format_result(
            ToolResult.fail(
                code=e.code,
                message=e.message,
            )
        )
    except WebminRPCError as e:
        logger.error("RPC error: %s", e)
        return format_result(
            ToolResult.fail(
                code=e.code,
                message=e.message,
            )
        )
    except WebminClientError as e:
        logger.error("Webmin client error: %s", e)
        return format_result(
            ToolResult.fail(
                code=e.code,
                message=e.message,
            )
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
