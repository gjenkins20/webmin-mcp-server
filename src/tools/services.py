"""Service management tools for Webmin MCP Server.

Phase 2 tools for starting, stopping, restarting, and managing
system services with safety framework enforcement.
"""

from ..models import ToolResult
from ..safety import safety_check_or_fail
from ..webmin_client import WebminClient


async def restart_service(
    client: WebminClient,
    service: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Restart a system service.

    Args:
        client: Authenticated WebminClient instance.
        service: Name of the service to restart.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with restart status.
    """
    # Safety check
    blocked = safety_check_or_fail("restart", service, safe_mode)
    if blocked:
        return blocked

    try:
        # Get current status
        pre_status = await client.call("init", "status_action", service)

        # Restart the service
        result = await client.call("init", "restart_action", service)

        # Get new status
        post_status = await client.call("init", "status_action", service)

        # Parse result - typically [exit_code, output]
        exit_code = result[0] if isinstance(result, list) else result
        output = result[1] if isinstance(result, list) and len(result) > 1 else ""

        return ToolResult.ok({
            "service": service,
            "action": "restart",
            "success": post_status == 1,  # 1 = running
            "running": post_status == 1,
            "exit_code": exit_code,
            "output": output,
            "status_before": "running" if pre_status == 1 else "stopped",
            "status_after": "running" if post_status == 1 else "stopped",
        })

    except Exception as e:
        return ToolResult.fail(
            code="RESTART_SERVICE_ERROR",
            message=f"Failed to restart service '{service}': {e}",
        )


async def start_service(
    client: WebminClient,
    service: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Start a system service.

    Args:
        client: Authenticated WebminClient instance.
        service: Name of the service to start.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with start status.
    """
    # Safety check
    blocked = safety_check_or_fail("start", service, safe_mode)
    if blocked:
        return blocked

    try:
        # Get current status
        pre_status = await client.call("init", "status_action", service)

        if pre_status == 1:
            return ToolResult.ok({
                "service": service,
                "action": "start",
                "success": True,
                "running": True,
                "message": "Service is already running",
                "status_before": "running",
                "status_after": "running",
            })

        # Start the service
        result = await client.call("init", "start_action", service)

        # Get new status
        post_status = await client.call("init", "status_action", service)

        # Parse result
        exit_code = result[0] if isinstance(result, list) else result
        output = result[1] if isinstance(result, list) and len(result) > 1 else ""

        return ToolResult.ok({
            "service": service,
            "action": "start",
            "success": post_status == 1,
            "running": post_status == 1,
            "exit_code": exit_code,
            "output": output,
            "status_before": "stopped",
            "status_after": "running" if post_status == 1 else "stopped",
        })

    except Exception as e:
        return ToolResult.fail(
            code="START_SERVICE_ERROR",
            message=f"Failed to start service '{service}': {e}",
        )


async def stop_service(
    client: WebminClient,
    service: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Stop a system service.

    Args:
        client: Authenticated WebminClient instance.
        service: Name of the service to stop.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with stop status.
    """
    # Safety check
    blocked = safety_check_or_fail("stop", service, safe_mode)
    if blocked:
        return blocked

    try:
        # Get current status
        pre_status = await client.call("init", "status_action", service)

        if pre_status == 0:
            return ToolResult.ok({
                "service": service,
                "action": "stop",
                "success": True,
                "running": False,
                "message": "Service is already stopped",
                "status_before": "stopped",
                "status_after": "stopped",
            })

        # Stop the service
        result = await client.call("init", "stop_action", service)

        # Get new status
        post_status = await client.call("init", "status_action", service)

        # Parse result
        exit_code = result[0] if isinstance(result, list) else result
        output = result[1] if isinstance(result, list) and len(result) > 1 else ""

        return ToolResult.ok({
            "service": service,
            "action": "stop",
            "success": post_status == 0,
            "running": post_status == 1,
            "exit_code": exit_code,
            "output": output,
            "status_before": "running",
            "status_after": "stopped" if post_status == 0 else "running",
        })

    except Exception as e:
        return ToolResult.fail(
            code="STOP_SERVICE_ERROR",
            message=f"Failed to stop service '{service}': {e}",
        )


async def enable_service(
    client: WebminClient,
    service: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Enable a service to start at boot.

    Args:
        client: Authenticated WebminClient instance.
        service: Name of the service to enable.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with enable status.
    """
    # Safety check (enable is generally safe)
    blocked = safety_check_or_fail("enable", service, safe_mode)
    if blocked:
        return blocked

    try:
        # Get current boot status
        pre_boot_status = await client.call("init", "action_status", service)

        # Enable at boot
        result = await client.call("init", "enable_at_boot", service)

        # Get new boot status
        post_boot_status = await client.call("init", "action_status", service)

        # Boot status: 2 seems to indicate enabled
        enabled_before = pre_boot_status == 2
        enabled_after = post_boot_status == 2

        return ToolResult.ok({
            "service": service,
            "action": "enable",
            "success": enabled_after,
            "enabled_at_boot": enabled_after,
            "boot_status_code": post_boot_status,
            "was_enabled": enabled_before,
        })

    except Exception as e:
        return ToolResult.fail(
            code="ENABLE_SERVICE_ERROR",
            message=f"Failed to enable service '{service}': {e}",
        )


async def disable_service(
    client: WebminClient,
    service: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Disable a service from starting at boot.

    Args:
        client: Authenticated WebminClient instance.
        service: Name of the service to disable.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with disable status.
    """
    # Safety check
    blocked = safety_check_or_fail("disable", service, safe_mode)
    if blocked:
        return blocked

    try:
        # Get current boot status
        pre_boot_status = await client.call("init", "action_status", service)

        # Disable at boot
        result = await client.call("init", "disable_at_boot", service)

        # Get new boot status
        post_boot_status = await client.call("init", "action_status", service)

        # Boot status: 2 = enabled, other values = disabled
        enabled_before = pre_boot_status == 2
        enabled_after = post_boot_status == 2

        return ToolResult.ok({
            "service": service,
            "action": "disable",
            "success": not enabled_after,
            "enabled_at_boot": enabled_after,
            "boot_status_code": post_boot_status,
            "was_enabled": enabled_before,
        })

    except Exception as e:
        return ToolResult.fail(
            code="DISABLE_SERVICE_ERROR",
            message=f"Failed to disable service '{service}': {e}",
        )
