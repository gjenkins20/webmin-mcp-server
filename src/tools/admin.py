"""System administration tools for Webmin MCP Server.

Phase 6 tools for system time, runlevels, SSH config, logs, and backups.
"""

from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


async def get_system_time(client: WebminClient) -> ToolResult:
    """Get the current system time and timezone.

    Returns the system's current date, time, and timezone configuration.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with system time information.
    """
    try:
        time_info = await client.call("time", "get_system_time")

        if isinstance(time_info, dict):
            return ToolResult.ok({
                "timezone": time_info.get("timezone"),
                "timezone_name": time_info.get("timezone_name"),
                "year": time_info.get("year"),
                "month": time_info.get("month"),
                "day": time_info.get("day"),
                "hour": time_info.get("hour"),
                "minute": time_info.get("min"),
                "second": time_info.get("sec"),
                "day_of_week": time_info.get("dow"),
                "hardware_time": time_info.get("hardware"),
            })
        elif isinstance(time_info, list):
            # Returns Perl localtime() array: [sec, min, hour, mday, mon, year, wday, yday, isdst]
            # year is years since 1900, month is 0-indexed
            year_raw = time_info[5] if len(time_info) > 5 else None
            month_raw = time_info[4] if len(time_info) > 4 else None
            return ToolResult.ok({
                "second": time_info[0] if len(time_info) > 0 else None,
                "minute": time_info[1] if len(time_info) > 1 else None,
                "hour": time_info[2] if len(time_info) > 2 else None,
                "day": time_info[3] if len(time_info) > 3 else None,
                "month": month_raw + 1 if month_raw is not None else None,  # Convert to 1-indexed
                "year": year_raw + 1900 if year_raw is not None else None,  # Convert from years since 1900
                "day_of_week": time_info[6] if len(time_info) > 6 else None,
                "year_day": time_info[7] if len(time_info) > 7 else None,
                "is_dst": bool(time_info[8]) if len(time_info) > 8 else None,
            })
        else:
            return ToolResult.ok({
                "raw": str(time_info),
            })

    except Exception as e:
        return ToolResult.fail(
            code="SYSTEM_TIME_ERROR",
            message=f"Failed to get system time: {e}",
        )


async def list_runlevels(client: WebminClient) -> ToolResult:
    """List system runlevels and their descriptions.

    Returns information about available runlevels on the system.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with runlevel information.
    """
    try:
        runlevels_raw = await client.call("init", "list_runlevels")

        runlevels = []
        if isinstance(runlevels_raw, list):
            for rl in runlevels_raw:
                if isinstance(rl, dict):
                    runlevels.append({
                        "level": rl.get("level"),
                        "name": rl.get("name"),
                        "description": rl.get("desc"),
                    })
                elif isinstance(rl, (str, int)):
                    runlevels.append({
                        "level": str(rl),
                        "name": None,
                        "description": None,
                    })

        return ToolResult.ok({
            "count": len(runlevels),
            "runlevels": runlevels,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_RUNLEVELS_ERROR",
            message=f"Failed to list runlevels: {e}",
        )


async def get_ssh_config(client: WebminClient) -> ToolResult:
    """Get SSH server (sshd) configuration.

    Returns key SSH daemon configuration settings.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with SSH configuration.
    """
    try:
        config_raw = await client.call("sshd", "get_sshd_config")

        if isinstance(config_raw, dict):
            # Parse common SSH settings
            config = {
                "port": config_raw.get("Port", config_raw.get("port")),
                "permit_root_login": config_raw.get(
                    "PermitRootLogin", config_raw.get("permit_root_login")
                ),
                "password_authentication": config_raw.get(
                    "PasswordAuthentication", config_raw.get("password_authentication")
                ),
                "pubkey_authentication": config_raw.get(
                    "PubkeyAuthentication", config_raw.get("pubkey_authentication")
                ),
                "x11_forwarding": config_raw.get(
                    "X11Forwarding", config_raw.get("x11_forwarding")
                ),
                "max_auth_tries": config_raw.get(
                    "MaxAuthTries", config_raw.get("max_auth_tries")
                ),
                "permit_empty_passwords": config_raw.get(
                    "PermitEmptyPasswords", config_raw.get("permit_empty_passwords")
                ),
                "challenge_response": config_raw.get(
                    "ChallengeResponseAuthentication",
                    config_raw.get("challenge_response_authentication"),
                ),
                "use_pam": config_raw.get("UsePAM", config_raw.get("use_pam")),
                "listen_address": config_raw.get(
                    "ListenAddress", config_raw.get("listen_address")
                ),
                "protocol": config_raw.get("Protocol", config_raw.get("protocol")),
                "config_file": config_raw.get("file"),
            }

            # Clean up None values for readability
            config = {k: v for k, v in config.items() if v is not None}

            return ToolResult.ok({
                "settings": config,
                "raw_config": config_raw,
            })
        else:
            return ToolResult.ok({
                "raw": config_raw,
            })

    except Exception as e:
        return ToolResult.fail(
            code="SSH_CONFIG_ERROR",
            message=f"Failed to get SSH configuration: {e}",
        )


async def list_webmin_logs(
    client: WebminClient,
    limit: int = 100,
    module: str | None = None,
    user: str | None = None,
) -> ToolResult:
    """List Webmin action/audit logs.

    Returns recent actions performed through Webmin.

    Args:
        client: Authenticated WebminClient instance.
        limit: Maximum number of log entries to return.
        module: Optional module name to filter by.
        user: Optional username to filter by.

    Returns:
        ToolResult with log entries.
    """
    try:
        logs_raw = await client.call("webminlog", "list_webmin_log")

        logs = []
        if isinstance(logs_raw, list):
            for entry in logs_raw:
                if isinstance(entry, dict):
                    # Apply filters
                    if module and entry.get("module") != module:
                        continue
                    if user and entry.get("user") != user:
                        continue

                    logs.append({
                        "id": entry.get("id"),
                        "time": entry.get("time"),
                        "user": entry.get("user"),
                        "module": entry.get("module"),
                        "action": entry.get("script"),
                        "description": entry.get("desc"),
                        "ip": entry.get("ip"),
                        "session": entry.get("sid"),
                    })

                    if len(logs) >= limit:
                        break

        return ToolResult.ok({
            "count": len(logs),
            "limit": limit,
            "filter_module": module,
            "filter_user": user,
            "logs": logs,
        })

    except Exception as e:
        return ToolResult.fail(
            code="WEBMIN_LOGS_ERROR",
            message=f"Failed to list Webmin logs: {e}",
        )


async def list_backups(client: WebminClient) -> ToolResult:
    """List Webmin configuration backups.

    Returns available configuration backups that can be restored.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with backup information.
    """
    try:
        backups_raw = await client.call("backup-config", "list_backups")

        backups = []
        if isinstance(backups_raw, list):
            for backup in backups_raw:
                if isinstance(backup, dict):
                    backups.append({
                        "id": backup.get("id"),
                        "file": backup.get("file"),
                        "dest": backup.get("dest"),
                        "modules": backup.get("mods"),
                        "schedule": backup.get("sched"),
                        "enabled": bool(backup.get("enabled")),
                        "email": backup.get("email"),
                        "description": backup.get("desc"),
                    })

        return ToolResult.ok({
            "count": len(backups),
            "backups": backups,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_BACKUPS_ERROR",
            message=f"Failed to list backups: {e}",
        )
