"""Disk quota management tools for Webmin MCP Server.

Phase 7 tools for viewing and managing disk quotas on filesystems
that support quota enforcement.
"""

from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


async def list_quota_filesystems(client: WebminClient) -> ToolResult:
    """List filesystems with quota support.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of filesystems and their quota status.
    """
    try:
        fs_raw = await client.call("quota", "list_filesystems")

        filesystems = []
        if isinstance(fs_raw, list):
            for fs in fs_raw:
                if isinstance(fs, (list, tuple)) and len(fs) >= 5:
                    # Format: [mount_point, device, type, options, quota_type, active, ...]
                    quota_type = fs[4] if len(fs) > 4 else 0
                    active = fs[5] if len(fs) > 5 else 0

                    # quota_type: 0=none, 1=user, 2=group, 3=both
                    try:
                        quota_type = int(quota_type)
                    except (ValueError, TypeError):
                        quota_type = 0

                    try:
                        active = int(active)
                    except (ValueError, TypeError):
                        active = 0

                    filesystems.append({
                        "mount_point": fs[0],
                        "device": fs[1] if len(fs) > 1 else None,
                        "type": fs[2] if len(fs) > 2 else None,
                        "quota_support": quota_type > 0,
                        "quota_type": (
                            "none" if quota_type == 0
                            else "user" if quota_type == 1
                            else "group" if quota_type == 2
                            else "both" if quota_type == 3
                            else f"unknown({quota_type})"
                        ),
                        "quota_enabled": bool(active),
                    })
                elif isinstance(fs, dict):
                    filesystems.append({
                        "mount_point": fs.get("dir") or fs.get("mount"),
                        "device": fs.get("dev") or fs.get("device"),
                        "type": fs.get("type"),
                        "quota_support": bool(fs.get("quota")),
                        "quota_enabled": bool(fs.get("active")),
                    })

        quota_enabled = [f for f in filesystems if f.get("quota_enabled")]
        quota_capable = [f for f in filesystems if f.get("quota_support")]

        return ToolResult.ok({
            "total_count": len(filesystems),
            "quota_capable_count": len(quota_capable),
            "quota_enabled_count": len(quota_enabled),
            "filesystems": filesystems,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_QUOTA_FILESYSTEMS_ERROR",
            message=f"Failed to list quota filesystems: {e}",
        )


async def list_user_quotas(
    client: WebminClient,
    filesystem: str,
) -> ToolResult:
    """List all user quotas on a filesystem.

    Calls quota::filesystem_users(filesystem) to get quota data for all users
    on the given filesystem. Note: this function populates a Perl global hash;
    over XML-RPC the structured data may or may not be available depending on
    the Webmin version. Falls back to returning the user count if full data
    is not available.

    Args:
        client: Authenticated WebminClient instance.
        filesystem: Mount point of the filesystem.

    Returns:
        ToolResult with list of user quotas.
    """
    if not filesystem:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: filesystem",
        )

    try:
        # Get block size for human-readable conversion
        block_size = 1024  # Default
        try:
            bs = await client.call("quota", "block_size", filesystem)
            if bs and int(bs) > 0:
                block_size = int(bs)
        except Exception:
            pass

        users_raw = await client.call("quota", "filesystem_users", filesystem)

        quotas = []
        if isinstance(users_raw, list):
            for entry in users_raw:
                if isinstance(entry, (list, tuple)) and len(entry) >= 7:
                    # Format: [user, used_blocks, soft_blocks, hard_blocks, used_files, soft_files, hard_files, ...]
                    quotas.append({
                        "user": entry[0],
                        "used_blocks": _safe_int(entry[1]),
                        "soft_block_limit": _safe_int(entry[2]),
                        "hard_block_limit": _safe_int(entry[3]),
                        "used_bytes": _safe_int(entry[1]) * block_size,
                        "soft_limit_bytes": _safe_int(entry[2]) * block_size,
                        "hard_limit_bytes": _safe_int(entry[3]) * block_size,
                        "used_files": _safe_int(entry[4]),
                        "soft_file_limit": _safe_int(entry[5]),
                        "hard_file_limit": _safe_int(entry[6]),
                        "grace_blocks": entry[7] if len(entry) > 7 else None,
                        "grace_files": entry[8] if len(entry) > 8 else None,
                    })
                elif isinstance(entry, dict):
                    quotas.append(_parse_quota_dict(entry, block_size))

        # If filesystem_users returned just a count (integer), report it
        if isinstance(users_raw, int):
            return ToolResult.ok({
                "filesystem": filesystem,
                "block_size": block_size,
                "count": users_raw,
                "quotas": [],
                "note": "Only user count available; use get_user_quota for individual details.",
            })

        return ToolResult.ok({
            "filesystem": filesystem,
            "block_size": block_size,
            "count": len(quotas),
            "quotas": quotas,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_USER_QUOTAS_ERROR",
            message=f"Failed to list user quotas on '{filesystem}': {e}",
        )


async def get_user_quota(
    client: WebminClient,
    username: str,
    filesystem: str,
) -> ToolResult:
    """Get quota limits and usage for a specific user on a filesystem.

    Uses quota::user_quota(user, filesystem) which returns a clean 6-element
    array: [used_blocks, soft_blocks, hard_blocks, used_files, soft_files, hard_files].
    Returns empty array if user has no quota.

    Args:
        client: Authenticated WebminClient instance.
        username: Username to get quota for.
        filesystem: Mount point of the filesystem.

    Returns:
        ToolResult with user's quota details.
    """
    if not username:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: username",
        )
    if not filesystem:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: filesystem",
        )

    try:
        # Get block size
        block_size = 1024
        try:
            bs = await client.call("quota", "block_size", filesystem)
            if bs and int(bs) > 0:
                block_size = int(bs)
        except Exception:
            pass

        # Use quota::user_quota which returns a clean 6-element array
        quota_data = await client.call("quota", "user_quota", username, filesystem)

        if isinstance(quota_data, (list, tuple)) and len(quota_data) >= 6:
            return ToolResult.ok({
                "user": username,
                "filesystem": filesystem,
                "block_size": block_size,
                "quota_enabled": True,
                "used_blocks": _safe_int(quota_data[0]),
                "soft_block_limit": _safe_int(quota_data[1]),
                "hard_block_limit": _safe_int(quota_data[2]),
                "used_bytes": _safe_int(quota_data[0]) * block_size,
                "soft_limit_bytes": _safe_int(quota_data[1]) * block_size,
                "hard_limit_bytes": _safe_int(quota_data[2]) * block_size,
                "used_files": _safe_int(quota_data[3]),
                "soft_file_limit": _safe_int(quota_data[4]),
                "hard_file_limit": _safe_int(quota_data[5]),
            })

        # Empty array or unexpected format - user has no quota (valid, not an error)
        return ToolResult.ok({
            "user": username,
            "filesystem": filesystem,
            "quota_enabled": False,
            "used_blocks": 0,
            "soft_block_limit": 0,
            "hard_block_limit": 0,
            "used_files": 0,
            "soft_file_limit": 0,
            "hard_file_limit": 0,
        })

    except Exception as e:
        return ToolResult.fail(
            code="GET_USER_QUOTA_ERROR",
            message=f"Failed to get quota for user '{username}' on '{filesystem}': {e}",
        )


async def get_group_quota(
    client: WebminClient,
    group: str,
    filesystem: str,
) -> ToolResult:
    """Get quota limits and usage for a specific group on a filesystem.

    Uses quota::group_quota(group, filesystem) which returns a clean 6-element
    array: [used_blocks, soft_blocks, hard_blocks, used_files, soft_files, hard_files].
    Returns empty array if group has no quota.

    Args:
        client: Authenticated WebminClient instance.
        group: Group name to get quota for.
        filesystem: Mount point of the filesystem.

    Returns:
        ToolResult with group's quota details.
    """
    if not group:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: group",
        )
    if not filesystem:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: filesystem",
        )

    try:
        block_size = 1024
        try:
            bs = await client.call("quota", "block_size", filesystem)
            if bs and int(bs) > 0:
                block_size = int(bs)
        except Exception:
            pass

        # Use quota::group_quota which returns a clean 6-element array
        quota_data = await client.call("quota", "group_quota", group, filesystem)

        if isinstance(quota_data, (list, tuple)) and len(quota_data) >= 6:
            return ToolResult.ok({
                "group": group,
                "filesystem": filesystem,
                "block_size": block_size,
                "quota_enabled": True,
                "used_blocks": _safe_int(quota_data[0]),
                "soft_block_limit": _safe_int(quota_data[1]),
                "hard_block_limit": _safe_int(quota_data[2]),
                "used_bytes": _safe_int(quota_data[0]) * block_size,
                "soft_limit_bytes": _safe_int(quota_data[1]) * block_size,
                "hard_limit_bytes": _safe_int(quota_data[2]) * block_size,
                "used_files": _safe_int(quota_data[3]),
                "soft_file_limit": _safe_int(quota_data[4]),
                "hard_file_limit": _safe_int(quota_data[5]),
            })

        return ToolResult.ok({
            "group": group,
            "filesystem": filesystem,
            "quota_enabled": False,
            "used_blocks": 0,
            "soft_block_limit": 0,
            "hard_block_limit": 0,
            "used_files": 0,
            "soft_file_limit": 0,
            "hard_file_limit": 0,
        })

    except Exception as e:
        return ToolResult.fail(
            code="GET_GROUP_QUOTA_ERROR",
            message=f"Failed to get quota for group '{group}' on '{filesystem}': {e}",
        )


async def set_user_quota(
    client: WebminClient,
    username: str,
    filesystem: str,
    soft_block_limit: int = 0,
    hard_block_limit: int = 0,
    soft_file_limit: int = 0,
    hard_file_limit: int = 0,
    safe_mode: bool = True,
) -> ToolResult:
    """Set disk quota limits for a user on a filesystem.

    This is a dangerous operation and is blocked in safe mode.

    Args:
        client: Authenticated WebminClient instance.
        username: Username to set quota for.
        filesystem: Mount point of the filesystem.
        soft_block_limit: Soft limit for disk blocks (0 = unlimited).
        hard_block_limit: Hard limit for disk blocks (0 = unlimited).
        soft_file_limit: Soft limit for file count (0 = unlimited).
        hard_file_limit: Hard limit for file count (0 = unlimited).
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with updated quota details.
    """
    if safe_mode:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message="Setting quotas is blocked in safe mode. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to allow quota changes.",
        )

    if not username:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: username",
        )
    if not filesystem:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: filesystem",
        )

    # Validate limits are non-negative
    for name, value in [
        ("soft_block_limit", soft_block_limit),
        ("hard_block_limit", hard_block_limit),
        ("soft_file_limit", soft_file_limit),
        ("hard_file_limit", hard_file_limit),
    ]:
        if value < 0:
            return ToolResult.fail(
                code="INVALID_QUOTA",
                message=f"{name} must be non-negative (got {value})",
            )

    try:
        await client.call(
            "quota", "edit_user_quota",
            username, filesystem,
            soft_block_limit, hard_block_limit,
            soft_file_limit, hard_file_limit,
        )

        return ToolResult.ok({
            "action": "set_quota",
            "success": True,
            "user": username,
            "filesystem": filesystem,
            "soft_block_limit": soft_block_limit,
            "hard_block_limit": hard_block_limit,
            "soft_file_limit": soft_file_limit,
            "hard_file_limit": hard_file_limit,
        })

    except Exception as e:
        return ToolResult.fail(
            code="SET_USER_QUOTA_ERROR",
            message=f"Failed to set quota for user '{username}' on '{filesystem}': {e}",
        )


def _safe_int(value: Any) -> int:
    """Safely convert a value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _parse_quota_dict(
    entry: dict,
    block_size: int,
    name: str | None = None,
    filesystem: str | None = None,
    is_group: bool = False,
) -> dict[str, Any]:
    """Parse a quota dict from Webmin into a standardized format."""
    result: dict[str, Any] = {}
    if is_group:
        result["group"] = name or entry.get("group") or entry.get("name")
    else:
        result["user"] = name or entry.get("user") or entry.get("name")

    if filesystem:
        result["filesystem"] = filesystem
    result["block_size"] = block_size
    result["quota_enabled"] = True

    ub = _safe_int(entry.get("ublocks", entry.get("used_blocks", 0)))
    sb = _safe_int(entry.get("sblocks", entry.get("soft_blocks", 0)))
    hb = _safe_int(entry.get("hblocks", entry.get("hard_blocks", 0)))

    result["used_blocks"] = ub
    result["soft_block_limit"] = sb
    result["hard_block_limit"] = hb
    result["used_bytes"] = ub * block_size
    result["soft_limit_bytes"] = sb * block_size
    result["hard_limit_bytes"] = hb * block_size
    result["used_files"] = _safe_int(entry.get("ufiles", entry.get("used_files", 0)))
    result["soft_file_limit"] = _safe_int(entry.get("sfiles", entry.get("soft_files", 0)))
    result["hard_file_limit"] = _safe_int(entry.get("hfiles", entry.get("hard_files", 0)))

    return result


