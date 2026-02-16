"""System information and monitoring tools for Webmin MCP Server.

Phase 1 read-only tools for system monitoring and information gathering.
"""

from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


async def get_system_info(client: WebminClient) -> ToolResult:
    """Get comprehensive system information.

    Combines data from multiple Webmin endpoints to provide a complete
    system overview including OS, kernel, CPU, memory, and disk info.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with system information.
    """
    try:
        # Gather data from multiple sources
        version = await client.call("webmin", "get_webmin_version")
        hostname = await client.call("webmin", "get_system_hostname")
        os_info = await client.call("webmin", "detect_operating_system")
        system_info = await client.call("system-status", "collect_system_info")

        # Parse OS info (returns flat list of key-value pairs)
        os_data = {}
        if isinstance(os_info, list):
            for i in range(0, len(os_info) - 1, 2):
                os_data[os_info[i]] = os_info[i + 1]

        # Parse CPU info from load array
        load = system_info.get("load", [])
        cpu_info = {
            "load_1min": load[0] if len(load) > 0 else None,
            "load_5min": load[1] if len(load) > 1 else None,
            "load_15min": load[2] if len(load) > 2 else None,
            "running_processes": load[3] if len(load) > 3 else None,
            "model": load[4] if len(load) > 4 else None,
            "vendor": load[5] if len(load) > 5 else None,
            "cache_kb": load[6] if len(load) > 6 else None,
            "cores": load[7] if len(load) > 7 else None,
        }

        # Parse memory info
        mem = system_info.get("mem", [])
        mem_info = {
            "total_kb": mem[0] if len(mem) > 0 else None,
            "used_kb": mem[1] if len(mem) > 1 else None,
            "buffers_kb": mem[2] if len(mem) > 2 else None,
            "cached_kb": mem[3] if len(mem) > 3 else None,
            "free_kb": mem[4] if len(mem) > 4 else None,
        }

        # Parse kernel info
        kernel = system_info.get("kernel", {})

        return ToolResult.ok({
            "hostname": hostname,
            "webmin_version": str(version),
            "os": {
                "type": os_data.get("os_type"),
                "name": os_data.get("real_os_type"),
                "version": os_data.get("real_os_version"),
            },
            "kernel": {
                "os": kernel.get("os"),
                "version": kernel.get("version"),
                "arch": kernel.get("arch"),
            },
            "cpu": cpu_info,
            "memory": mem_info,
            "disk": {
                "total_bytes": system_info.get("disk_total"),
                "used_bytes": system_info.get("disk_used"),
                "free_bytes": system_info.get("disk_free"),
            },
            "process_count": system_info.get("procs"),
            "updates_available": len(system_info.get("poss", [])),
            "reboot_required": bool(system_info.get("reboot")),
        })

    except Exception as e:
        return ToolResult.fail(
            code="SYSTEM_INFO_ERROR",
            message=f"Failed to get system info: {e}",
        )


async def list_services(client: WebminClient) -> ToolResult:
    """List all system services.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of services.
    """
    try:
        actions = await client.call("init", "list_actions")

        services = []
        for action in actions:
            if isinstance(action, str):
                # Format is "service_name timestamp"
                parts = action.split()
                name = parts[0] if parts else action
                services.append({"name": name})
            else:
                services.append(action)

        return ToolResult.ok({
            "count": len(services),
            "services": services,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_SERVICES_ERROR",
            message=f"Failed to list services: {e}",
        )


async def get_service_status(client: WebminClient, service: str) -> ToolResult:
    """Get the status of a specific service.

    Args:
        client: Authenticated WebminClient instance.
        service: Name of the service to check.

    Returns:
        ToolResult with service status.
    """
    try:
        status_code = await client.call("init", "status_action", service)

        # Status codes: 0 = stopped, 1 = running (verified against live system)
        status_map = {
            0: "stopped",
            1: "running",
        }
        status = status_map.get(status_code, f"unknown ({status_code})")

        return ToolResult.ok({
            "service": service,
            "status": status,
            "status_code": status_code,
            "running": status_code == 1,
        })

    except Exception as e:
        return ToolResult.fail(
            code="SERVICE_STATUS_ERROR",
            message=f"Failed to get status for service '{service}': {e}",
        )


async def list_users(client: WebminClient) -> ToolResult:
    """List all system users.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of users.
    """
    try:
        users_raw = await client.call("useradmin", "list_users")

        users = []
        for user in users_raw:
            if isinstance(user, dict):
                users.append({
                    "username": user.get("user"),
                    "uid": user.get("uid"),
                    "gid": user.get("gid"),
                    "name": user.get("real"),
                    "home": user.get("home"),
                    "shell": user.get("shell"),
                })

        # Separate system and regular users
        system_users = [u for u in users if u.get("uid", 0) < 1000]
        regular_users = [u for u in users if u.get("uid", 0) >= 1000]

        return ToolResult.ok({
            "total_count": len(users),
            "regular_users": regular_users,
            "regular_count": len(regular_users),
            "system_users": system_users,
            "system_count": len(system_users),
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_USERS_ERROR",
            message=f"Failed to list users: {e}",
        )


async def get_disk_usage(client: WebminClient) -> ToolResult:
    """Get disk usage information for all filesystems.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with disk usage per filesystem.
    """
    try:
        system_info = await client.call("system-status", "collect_system_info")

        filesystems = []
        for fs in system_info.get("disk_fs", []):
            if isinstance(fs, dict):
                filesystems.append({
                    "mount_point": fs.get("dir"),
                    "device": fs.get("device"),
                    "type": fs.get("type"),
                    "total_bytes": fs.get("total"),
                    "used_bytes": fs.get("used"),
                    "free_bytes": fs.get("free"),
                    "used_percent": fs.get("used_percent"),
                    "inodes_total": fs.get("itotal"),
                    "inodes_used": fs.get("iused"),
                    "inodes_free": fs.get("ifree"),
                    "inodes_used_percent": fs.get("iused_percent"),
                })

        return ToolResult.ok({
            "total_bytes": system_info.get("disk_total"),
            "used_bytes": system_info.get("disk_used"),
            "free_bytes": system_info.get("disk_free"),
            "filesystems": filesystems,
        })

    except Exception as e:
        return ToolResult.fail(
            code="DISK_USAGE_ERROR",
            message=f"Failed to get disk usage: {e}",
        )


async def get_memory_usage(client: WebminClient) -> ToolResult:
    """Get memory usage information.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with memory usage details.
    """
    try:
        system_info = await client.call("system-status", "collect_system_info")

        mem = system_info.get("mem", [])

        # Memory values are in KB
        total_kb = mem[0] if len(mem) > 0 else 0
        used_kb = mem[1] if len(mem) > 1 else 0
        buffers_kb = mem[2] if len(mem) > 2 else 0
        cached_kb = mem[3] if len(mem) > 3 else 0
        free_kb = mem[4] if len(mem) > 4 else 0

        # Calculate percentages
        used_percent = round((used_kb / total_kb) * 100, 1) if total_kb else 0
        free_percent = round((free_kb / total_kb) * 100, 1) if total_kb else 0

        return ToolResult.ok({
            "total_kb": total_kb,
            "total_mb": round(total_kb / 1024, 1),
            "total_gb": round(total_kb / 1024 / 1024, 2),
            "used_kb": used_kb,
            "used_mb": round(used_kb / 1024, 1),
            "used_percent": used_percent,
            "free_kb": free_kb,
            "free_mb": round(free_kb / 1024, 1),
            "free_percent": free_percent,
            "buffers_kb": buffers_kb,
            "cached_kb": cached_kb,
        })

    except Exception as e:
        return ToolResult.fail(
            code="MEMORY_USAGE_ERROR",
            message=f"Failed to get memory usage: {e}",
        )


async def list_cron_jobs(client: WebminClient) -> ToolResult:
    """List all cron jobs.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of cron jobs.
    """
    try:
        jobs_raw = await client.call("cron", "list_cron_jobs")

        jobs = []
        for job in jobs_raw:
            if isinstance(job, dict):
                # Build cron schedule string
                schedule = " ".join([
                    str(job.get("mins", "*")),
                    str(job.get("hours", "*")),
                    str(job.get("days", "*")),
                    str(job.get("months", "*")),
                    str(job.get("weekdays", "*")),
                ])

                jobs.append({
                    "user": job.get("user"),
                    "command": job.get("command"),
                    "schedule": schedule,
                    "active": bool(job.get("active")),
                    "file": job.get("file"),
                    "index": job.get("index"),
                })

        return ToolResult.ok({
            "count": len(jobs),
            "jobs": jobs,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_CRON_ERROR",
            message=f"Failed to list cron jobs: {e}",
        )


async def get_network_info(client: WebminClient) -> ToolResult:
    """Get network interface and routing information.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with network configuration.
    """
    try:
        interfaces_raw = await client.call("net", "active_interfaces")
        routes_raw = await client.call("net", "list_routes")

        interfaces = []
        for iface in interfaces_raw:
            if isinstance(iface, dict):
                interfaces.append({
                    "name": iface.get("name"),
                    "fullname": iface.get("fullname"),
                    "address": iface.get("address"),
                    "netmask": iface.get("netmask"),
                    "broadcast": iface.get("broadcast"),
                    "mac": iface.get("ether"),
                    "mtu": iface.get("mtu"),
                    "up": bool(iface.get("up")),
                    "speed": iface.get("speed"),
                    "duplex": iface.get("duplex"),
                    "ipv6_addresses": iface.get("address6", []),
                })

        routes = []
        for route in routes_raw:
            if isinstance(route, dict):
                routes.append({
                    "destination": route.get("dest"),
                    "gateway": route.get("gateway"),
                    "netmask": route.get("netmask"),
                    "interface": route.get("iface"),
                })

        # Find default gateway
        default_gateway = None
        for route in routes:
            if route.get("destination") == "0.0.0.0":
                default_gateway = route.get("gateway")
                break

        return ToolResult.ok({
            "interfaces": interfaces,
            "interface_count": len(interfaces),
            "routes": routes,
            "default_gateway": default_gateway,
        })

    except Exception as e:
        return ToolResult.fail(
            code="NETWORK_INFO_ERROR",
            message=f"Failed to get network info: {e}",
        )
