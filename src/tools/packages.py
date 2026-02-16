"""Package information tools for Webmin MCP Server.

Phase 3 read-only tools for querying package information.
Note: Install/remove/update operations require CGI fallback and are not implemented.
"""

from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


async def get_package_info(
    client: WebminClient,
    package_name: str,
) -> ToolResult:
    """Get detailed information about an installed package.

    Args:
        client: Authenticated WebminClient instance.
        package_name: Name of the package to query.

    Returns:
        ToolResult with package details.
    """
    if not package_name or not package_name.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="Package name cannot be empty",
        )

    try:
        # software::package_info returns a list:
        # [name, type, description, arch, version, maintainer, install_date, url]
        info = await client.call("software", "package_info", package_name)

        if not info or not isinstance(info, list):
            return ToolResult.fail(
                code="PACKAGE_NOT_FOUND",
                message=f"Package '{package_name}' not found or not installed",
            )

        # Parse the info list
        # Handle Binary objects (description might be binary)
        description = info[2] if len(info) > 2 else None
        if hasattr(description, "data"):
            # It's an xmlrpc.client.Binary object
            description = description.data.decode("utf-8", errors="replace")

        return ToolResult.ok({
            "name": info[0] if len(info) > 0 else package_name,
            "type": info[1] if len(info) > 1 else None,
            "description": description,
            "architecture": info[3] if len(info) > 3 else None,
            "version": info[4] if len(info) > 4 else None,
            "maintainer": info[5] if len(info) > 5 else None,
            "install_date": info[6] if len(info) > 6 else None,
            "url": info[7] if len(info) > 7 else None,
        })

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            return ToolResult.fail(
                code="PACKAGE_NOT_FOUND",
                message=f"Package '{package_name}' not found or not installed",
            )
        return ToolResult.fail(
            code="PACKAGE_INFO_ERROR",
            message=f"Failed to get package info for '{package_name}': {e}",
        )


async def list_available_updates(client: WebminClient) -> ToolResult:
    """List all available package updates.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of available updates.
    """
    try:
        # Get system info which includes package updates in 'poss' field
        system_info = await client.call("system-status", "collect_system_info")

        updates_raw = system_info.get("poss", [])

        updates = []
        security_updates = []

        for update in updates_raw:
            if isinstance(update, dict):
                update_info = {
                    "name": update.get("name"),
                    "current_version": update.get("oldversion"),
                    "new_version": update.get("version"),
                    "description": update.get("desc"),
                    "source": update.get("source"),
                    "system": update.get("system"),  # e.g., "apt"
                    "is_security": bool(update.get("security")),
                }
                updates.append(update_info)

                if update.get("security"):
                    security_updates.append(update_info)

        return ToolResult.ok({
            "total_count": len(updates),
            "security_count": len(security_updates),
            "updates": updates,
            "security_updates": security_updates,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_UPDATES_ERROR",
            message=f"Failed to list available updates: {e}",
        )


async def get_package_count(client: WebminClient) -> ToolResult:
    """Get the total count of installed packages.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with package count.
    """
    try:
        # software::list_packages returns the count of installed packages
        count = await client.call("software", "list_packages")

        return ToolResult.ok({
            "installed_count": count if isinstance(count, int) else 0,
        })

    except Exception as e:
        return ToolResult.fail(
            code="PACKAGE_COUNT_ERROR",
            message=f"Failed to get package count: {e}",
        )
