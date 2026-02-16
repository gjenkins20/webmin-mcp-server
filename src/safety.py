"""Safety framework for Webmin MCP Server.

This module implements the safety tier system to prevent dangerous
operations on critical services and enforce safe mode restrictions.
"""

from enum import Enum
from typing import NamedTuple

from .models import ToolResult


class SafetyTier(str, Enum):
    """Safety tier levels for operations.

    - READ: No system changes. Always allowed.
    - SAFE: Low-risk changes. Allowed in safe mode.
    - MODERATE: Reversible changes. May be blocked for critical services.
    - DANGEROUS: Potentially destructive. Blocked in safe mode.
    """

    READ = "read"
    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"


class SafetyCheckResult(NamedTuple):
    """Result of a safety check."""

    allowed: bool
    reason: str | None = None


# Services that should never be stopped, disabled, or restarted
# These are critical for system operation and remote access
BLOCKED_SERVICES = frozenset({
    # SSH - needed for remote access
    "ssh",
    "sshd",
    "openssh-server",
    # Webmin itself
    "webmin",
    # Core system services
    "systemd-journald",
    "systemd-networkd",
    "systemd-resolved",
    "systemd-udevd",
    "systemd-logind",
    "dbus",
    "dbus-daemon",
    # Networking
    "networking",
    "NetworkManager",
    # Init system
    "init",
    "systemd",
})

# Services that can be restarted but not stopped
RESTART_ONLY_SERVICES = frozenset({
    "cron",
    "rsyslog",
    "syslog",
})


def check_service_operation(
    service: str,
    operation: str,
    safe_mode: bool = True,
) -> SafetyCheckResult:
    """Check if a service operation is allowed.

    Args:
        service: Name of the service.
        operation: Type of operation (start, stop, restart, enable, disable).
        safe_mode: Whether safe mode is enabled.

    Returns:
        SafetyCheckResult indicating if the operation is allowed.
    """
    service_lower = service.lower()

    # Check if service is in blocked list
    if service_lower in BLOCKED_SERVICES:
        if operation in ("stop", "disable"):
            return SafetyCheckResult(
                allowed=False,
                reason=f"Cannot {operation} critical service '{service}'. "
                f"This service is required for system operation or remote access.",
            )
        if operation == "restart" and safe_mode:
            return SafetyCheckResult(
                allowed=False,
                reason=f"Cannot restart critical service '{service}' in safe mode. "
                f"Disable safe mode (WEBMIN_SAFE_MODE=false) to allow this operation.",
            )

    # Check restart-only services
    if service_lower in RESTART_ONLY_SERVICES:
        if operation == "stop" and safe_mode:
            return SafetyCheckResult(
                allowed=False,
                reason=f"Cannot stop service '{service}' in safe mode. "
                f"This service provides important functionality. "
                f"Use restart instead, or disable safe mode.",
            )

    return SafetyCheckResult(allowed=True)


def get_operation_tier(operation: str) -> SafetyTier:
    """Get the safety tier for an operation.

    Args:
        operation: Type of operation.

    Returns:
        SafetyTier for the operation.
    """
    tier_map = {
        # Read operations
        "status": SafetyTier.READ,
        "list": SafetyTier.READ,
        # Safe operations
        "enable": SafetyTier.SAFE,
        # Moderate operations
        "start": SafetyTier.MODERATE,
        "stop": SafetyTier.MODERATE,
        "restart": SafetyTier.MODERATE,
        "disable": SafetyTier.MODERATE,
        # Dangerous operations
        "delete": SafetyTier.DANGEROUS,
        "remove": SafetyTier.DANGEROUS,
    }
    return tier_map.get(operation, SafetyTier.MODERATE)


def check_safety(
    operation: str,
    target: str | None = None,
    safe_mode: bool = True,
) -> SafetyCheckResult:
    """General safety check for any operation.

    Args:
        operation: Type of operation (e.g., "stop", "restart").
        target: Target of the operation (e.g., service name).
        safe_mode: Whether safe mode is enabled.

    Returns:
        SafetyCheckResult indicating if the operation is allowed.
    """
    tier = get_operation_tier(operation)

    # Dangerous operations are blocked in safe mode
    if tier == SafetyTier.DANGEROUS and safe_mode:
        return SafetyCheckResult(
            allowed=False,
            reason=f"Operation '{operation}' is classified as dangerous and is blocked "
            f"in safe mode. Disable safe mode (WEBMIN_SAFE_MODE=false) to allow.",
        )

    # For service operations, do additional checks
    if target and operation in ("start", "stop", "restart", "enable", "disable"):
        return check_service_operation(target, operation, safe_mode)

    return SafetyCheckResult(allowed=True)


def safety_check_or_fail(
    operation: str,
    target: str | None = None,
    safe_mode: bool = True,
) -> ToolResult | None:
    """Perform safety check and return ToolResult if blocked.

    This is a convenience function for use in tool implementations.
    Returns None if the operation is allowed, or a failure ToolResult
    if blocked.

    Args:
        operation: Type of operation.
        target: Target of the operation.
        safe_mode: Whether safe mode is enabled.

    Returns:
        None if allowed, ToolResult.fail() if blocked.
    """
    result = check_safety(operation, target, safe_mode)
    if not result.allowed:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message=result.reason or "Operation blocked by safety framework",
        )
    return None
