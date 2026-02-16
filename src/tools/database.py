"""Database tools for Webmin MCP Server.

Phase 6 tools for MySQL database monitoring (read-only).
"""

from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


async def list_mysql_databases(client: WebminClient) -> ToolResult:
    """List all MySQL databases.

    Returns information about databases on the MySQL server.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with database list.
    """
    try:
        dbs_raw = await client.call("mysql", "list_databases")

        databases = []
        if isinstance(dbs_raw, list):
            for db in dbs_raw:
                if isinstance(db, dict):
                    databases.append({
                        "name": db.get("name"),
                        "tables": db.get("tables"),
                        "size": db.get("size"),
                        "collation": db.get("collation"),
                    })
                elif isinstance(db, str):
                    databases.append({
                        "name": db,
                    })

        # Filter out system databases for display
        user_databases = [
            db for db in databases
            if db.get("name") not in ("information_schema", "performance_schema", "mysql", "sys")
        ]
        system_databases = [
            db for db in databases
            if db.get("name") in ("information_schema", "performance_schema", "mysql", "sys")
        ]

        return ToolResult.ok({
            "total_count": len(databases),
            "user_database_count": len(user_databases),
            "system_database_count": len(system_databases),
            "user_databases": user_databases,
            "system_databases": system_databases,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_DATABASES_ERROR",
            message=f"Failed to list MySQL databases: {e}",
        )


async def list_mysql_users(client: WebminClient) -> ToolResult:
    """List all MySQL users.

    Returns information about users configured in MySQL.
    Note: This requires MySQL to be running and accessible.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with user list.
    """
    try:
        # First check if MySQL is running
        running_check = await client.call("mysql", "is_mysql_running")
        if isinstance(running_check, list) and len(running_check) > 0:
            status_code = running_check[0]
            if status_code != 1:
                error_msg = running_check[1] if len(running_check) > 1 else "MySQL is not running"
                return ToolResult.ok({
                    "count": 0,
                    "users": [],
                    "mysql_running": False,
                    "message": str(error_msg)[:200],
                })

        # Try to list users - this function may not be available via XML-RPC
        try:
            users_raw = await client.call("mysql", "list_users")
        except Exception:
            # Function not available, return info about MySQL status
            return ToolResult.ok({
                "count": 0,
                "users": [],
                "mysql_running": True,
                "message": "User listing not available via XML-RPC. Use Webmin UI.",
            })

        users = []
        if isinstance(users_raw, list):
            for user in users_raw:
                if isinstance(user, dict):
                    users.append({
                        "user": user.get("user"),
                        "host": user.get("host"),
                        "password_set": bool(user.get("pass") or user.get("password")),
                        "ssl": user.get("ssl"),
                        "grants": user.get("grants"),
                    })
                elif isinstance(user, str):
                    parts = user.split("@")
                    users.append({
                        "user": parts[0] if parts else user,
                        "host": parts[1] if len(parts) > 1 else "%",
                    })

        return ToolResult.ok({
            "count": len(users),
            "users": users,
            "mysql_running": True,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_MYSQL_USERS_ERROR",
            message=f"Failed to list MySQL users: {e}",
        )


async def get_mysql_status(client: WebminClient) -> ToolResult:
    """Get MySQL server status.

    Returns MySQL server status variables and connection info.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with MySQL status.
    """
    try:
        # Check if MySQL is running first
        running_check = await client.call("mysql", "is_mysql_running")

        is_running = False
        error_message = None

        if isinstance(running_check, list) and len(running_check) > 0:
            status_code = running_check[0]
            is_running = status_code == 1
            if not is_running and len(running_check) > 1:
                error_message = str(running_check[1])[:200]
        elif isinstance(running_check, (int, bool)):
            is_running = bool(running_check)

        if not is_running:
            # Get version info even if not running
            version = await client.call("mysql", "get_mysql_version")
            return ToolResult.ok({
                "running": False,
                "installed": bool(version),
                "version": version if version else None,
                "error": error_message,
            })

        # Try to get detailed status
        try:
            version = await client.call("mysql", "get_mysql_version")
            config = await client.call("mysql", "get_mysql_config")

            return ToolResult.ok({
                "running": True,
                "version": version if version else None,
                "config_files": len(config) if isinstance(config, list) else 0,
            })
        except Exception:
            return ToolResult.ok({
                "running": True,
                "message": "MySQL is running but detailed status not available via XML-RPC",
            })

    except Exception as e:
        error_str = str(e).lower()
        if "connect" in error_str or "running" in error_str or "socket" in error_str:
            return ToolResult.ok({
                "running": False,
                "error": str(e)[:200],
            })
        return ToolResult.fail(
            code="MYSQL_STATUS_ERROR",
            message=f"Failed to get MySQL status: {e}",
        )
