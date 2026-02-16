"""Security tools for Webmin MCP Server.

Phase 6 tools for Fail2ban intrusion prevention monitoring.
"""

from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


async def list_fail2ban_jails(client: WebminClient) -> ToolResult:
    """List all Fail2ban jails and their status.

    Returns information about configured jails including whether they
    are enabled and their current ban counts.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with jail information.
    """
    try:
        jails_raw = await client.call("fail2ban", "list_jails")

        jails = []
        if isinstance(jails_raw, list):
            for jail in jails_raw:
                if isinstance(jail, dict):
                    jails.append({
                        "name": jail.get("name"),
                        "enabled": bool(jail.get("enabled")),
                        "filter": jail.get("filter"),
                        "action": jail.get("action"),
                        "logpath": jail.get("logpath"),
                        "maxretry": jail.get("maxretry"),
                        "findtime": jail.get("findtime"),
                        "bantime": jail.get("bantime"),
                        "currently_banned": jail.get("banned"),
                        "total_banned": jail.get("total_banned"),
                    })
                elif isinstance(jail, str):
                    jails.append({
                        "name": jail,
                        "enabled": None,
                    })

        return ToolResult.ok({
            "count": len(jails),
            "jails": jails,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_JAILS_ERROR",
            message=f"Failed to list Fail2ban jails: {e}",
        )


async def get_fail2ban_status(client: WebminClient, jail: str | None = None) -> ToolResult:
    """Get Fail2ban status for a specific jail or overall.

    Returns current status including banned IPs and counts.

    Args:
        client: Authenticated WebminClient instance.
        jail: Optional jail name for specific status.

    Returns:
        ToolResult with Fail2ban status.
    """
    try:
        # First check if fail2ban is running
        running_check = await client.call("fail2ban", "is_fail2ban_running")
        is_running = bool(running_check) if running_check else False

        # Get jail list to find banned counts
        jails_raw = await client.call("fail2ban", "list_jails")

        if jail:
            # Filter to specific jail
            jail_info = None
            if isinstance(jails_raw, list):
                for j in jails_raw:
                    if isinstance(j, dict) and j.get("name") == jail:
                        jail_info = j
                        break
            if jail_info:
                return ToolResult.ok({
                    "jail": jail,
                    "running": is_running,
                    "enabled": bool(jail_info.get("enabled")),
                    "currently_banned": jail_info.get("banned", 0),
                    "total_banned": jail_info.get("total_banned"),
                    "banned_ips": jail_info.get("banned_ips", []),
                })
            else:
                return ToolResult.ok({
                    "jail": jail,
                    "running": is_running,
                    "found": False,
                })
        else:
            # Overall status
            total_banned = 0
            jail_count = 0
            if isinstance(jails_raw, list):
                jail_count = len(jails_raw)
                for j in jails_raw:
                    if isinstance(j, dict):
                        total_banned += j.get("banned", 0)

            return ToolResult.ok({
                "running": is_running,
                "jail_count": jail_count,
                "total_currently_banned": total_banned,
            })

    except Exception as e:
        error_str = str(e).lower()
        # Check if fail2ban is simply not installed
        if "does not exist" in error_str or "not found" in error_str:
            return ToolResult.ok({
                "running": False,
                "installed": False,
                "message": "Fail2ban does not appear to be installed",
            })
        return ToolResult.fail(
            code="FAIL2BAN_STATUS_ERROR",
            message=f"Failed to get Fail2ban status: {e}",
        )


async def list_banned_ips(client: WebminClient, jail: str | None = None) -> ToolResult:
    """List currently banned IP addresses.

    Returns all IPs currently banned by Fail2ban, optionally filtered
    by jail name.

    Args:
        client: Authenticated WebminClient instance.
        jail: Optional jail name to filter by.

    Returns:
        ToolResult with banned IP list.
    """
    try:
        # Get jail list which includes banned info
        jails_raw = await client.call("fail2ban", "list_jails")

        banned_ips = []
        if isinstance(jails_raw, list):
            for j in jails_raw:
                if isinstance(j, dict):
                    jail_name = j.get("name")
                    # Apply jail filter if specified
                    if jail and jail_name != jail:
                        continue

                    # Extract banned IPs from jail info
                    jail_banned = j.get("banned_ips", [])
                    if isinstance(jail_banned, list):
                        for ip in jail_banned:
                            if isinstance(ip, dict):
                                banned_ips.append({
                                    "ip": ip.get("ip"),
                                    "jail": jail_name,
                                    "ban_time": ip.get("time"),
                                    "expires": ip.get("expires"),
                                })
                            elif isinstance(ip, str):
                                banned_ips.append({
                                    "ip": ip,
                                    "jail": jail_name,
                                })
                    elif isinstance(jail_banned, str):
                        for ip in jail_banned.split():
                            if ip.strip():
                                banned_ips.append({
                                    "ip": ip.strip(),
                                    "jail": jail_name,
                                })

        return ToolResult.ok({
            "count": len(banned_ips),
            "jail_filter": jail,
            "banned_ips": banned_ips,
        })

    except Exception as e:
        error_str = str(e).lower()
        if "does not exist" in error_str or "not found" in error_str:
            return ToolResult.ok({
                "count": 0,
                "jail_filter": jail,
                "banned_ips": [],
                "message": "Fail2ban does not appear to be installed",
            })
        return ToolResult.fail(
            code="LIST_BANNED_ERROR",
            message=f"Failed to list banned IPs: {e}",
        )
