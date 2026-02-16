"""Storage management tools for Webmin MCP Server.

Phase 5 tools for SMART disk health monitoring and LVM management.
"""

from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


async def list_disks(client: WebminClient) -> ToolResult:
    """List all disks with SMART capability.

    Returns information about physical disks including device path,
    model, serial number, and whether SMART is enabled.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of disks.
    """
    try:
        disks_raw = await client.call("smart-status", "list_smart_disks_partitions")

        disks = []
        if isinstance(disks_raw, list):
            for disk in disks_raw:
                if isinstance(disk, dict):
                    disks.append({
                        "device": disk.get("device"),
                        "model": disk.get("model"),
                        "serial": disk.get("serial"),
                        "capacity": disk.get("capacity"),
                        "smart_enabled": bool(disk.get("smart")),
                        "type": disk.get("type"),
                    })

        return ToolResult.ok({
            "count": len(disks),
            "disks": disks,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_DISKS_ERROR",
            message=f"Failed to list disks: {e}",
        )


async def get_disk_health(client: WebminClient, device: str) -> ToolResult:
    """Get SMART health status for a specific disk.

    Returns detailed SMART attributes, health status, and any warnings
    for the specified disk device.

    Args:
        client: Authenticated WebminClient instance.
        device: Device path (e.g., '/dev/sda', '/dev/nvme0n1').

    Returns:
        ToolResult with disk health information.
    """
    try:
        status_raw = await client.call("smart-status", "get_drive_status", device)

        if not isinstance(status_raw, dict):
            return ToolResult.fail(
                code="INVALID_RESPONSE",
                message=f"Unexpected response format for device '{device}'",
            )

        # Parse SMART attributes
        attributes = []
        attrs_raw = status_raw.get("attrs", [])
        if isinstance(attrs_raw, list):
            for attr in attrs_raw:
                if isinstance(attr, dict):
                    attributes.append({
                        "id": attr.get("id"),
                        "name": attr.get("name"),
                        "value": attr.get("value"),
                        "worst": attr.get("worst"),
                        "threshold": attr.get("thresh"),
                        "raw": attr.get("raw"),
                        "type": attr.get("type"),
                        "failed": bool(attr.get("failed")),
                    })

        # Determine overall health
        health_status = status_raw.get("health", "unknown")
        errors = status_raw.get("errors", [])

        # Check for failed attributes
        failed_attrs = [a for a in attributes if a.get("failed")]

        return ToolResult.ok({
            "device": device,
            "health": health_status,
            "healthy": health_status.lower() in ("passed", "ok", "good"),
            "model": status_raw.get("model"),
            "serial": status_raw.get("serial"),
            "firmware": status_raw.get("firmware"),
            "capacity": status_raw.get("capacity"),
            "temperature": status_raw.get("temp"),
            "power_on_hours": status_raw.get("power_on"),
            "power_cycles": status_raw.get("power_cycles"),
            "attributes": attributes,
            "failed_attributes": failed_attrs,
            "errors": errors if isinstance(errors, list) else [],
            "error_count": len(errors) if isinstance(errors, list) else 0,
        })

    except Exception as e:
        return ToolResult.fail(
            code="DISK_HEALTH_ERROR",
            message=f"Failed to get health status for device '{device}': {e}",
        )


async def list_volume_groups(client: WebminClient) -> ToolResult:
    """List all LVM volume groups.

    Returns information about all volume groups including name, size,
    physical volumes, and logical volumes contained.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of volume groups.
    """
    try:
        vgs_raw = await client.call("lvm", "list_volume_groups")

        volume_groups = []
        if isinstance(vgs_raw, list):
            for vg in vgs_raw:
                if isinstance(vg, dict):
                    volume_groups.append({
                        "name": vg.get("name"),
                        "size_bytes": vg.get("size"),
                        "size_mb": _bytes_to_mb(vg.get("size")),
                        "free_bytes": vg.get("free"),
                        "free_mb": _bytes_to_mb(vg.get("free")),
                        "pv_count": vg.get("pvs"),
                        "lv_count": vg.get("lvs"),
                        "extent_size": vg.get("pe_size"),
                        "extent_count": vg.get("pe_total"),
                        "free_extents": vg.get("pe_free"),
                    })

        return ToolResult.ok({
            "count": len(volume_groups),
            "volume_groups": volume_groups,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_VGS_ERROR",
            message=f"Failed to list volume groups: {e}",
        )


async def list_logical_volumes(
    client: WebminClient,
    volume_group: str | None = None,
) -> ToolResult:
    """List all LVM logical volumes.

    Returns information about logical volumes including name, size,
    and the volume group they belong to.

    Args:
        client: Authenticated WebminClient instance.
        volume_group: Optional volume group name to filter by.

    Returns:
        ToolResult with list of logical volumes.
    """
    try:
        lvs_raw = await client.call("lvm", "list_logical_volumes")

        logical_volumes = []
        if isinstance(lvs_raw, list):
            for lv in lvs_raw:
                if isinstance(lv, dict):
                    # Filter by volume group if specified
                    vg_name = lv.get("vg")
                    if volume_group and vg_name != volume_group:
                        continue

                    logical_volumes.append({
                        "name": lv.get("name"),
                        "volume_group": vg_name,
                        "size_bytes": lv.get("size"),
                        "size_mb": _bytes_to_mb(lv.get("size")),
                        "device": lv.get("device"),
                        "active": bool(lv.get("active")),
                        "mounted": lv.get("mount"),
                        "stripes": lv.get("stripes"),
                        "stripe_size": lv.get("stripesize"),
                    })

        return ToolResult.ok({
            "count": len(logical_volumes),
            "volume_group": volume_group,
            "logical_volumes": logical_volumes,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_LVS_ERROR",
            message=f"Failed to list logical volumes: {e}",
        )


def _bytes_to_mb(bytes_val: Any) -> float | None:
    """Convert bytes to megabytes.

    Args:
        bytes_val: Value in bytes.

    Returns:
        Value in megabytes, or None if conversion fails.
    """
    if bytes_val is None:
        return None
    try:
        return round(int(bytes_val) / (1024 * 1024), 2)
    except (TypeError, ValueError):
        return None
