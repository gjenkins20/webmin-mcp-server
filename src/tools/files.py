"""File management tools for Webmin MCP Server.

Phase 4 tools for reading, writing, and managing files on the remote system.
Includes safety framework enforcement to protect critical system paths.
"""

import os
from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


# Paths that are always blocked for write/delete operations
BLOCKED_PATHS = frozenset({
    "/",
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/lib",
    "/lib32",
    "/lib64",
    "/libx32",
    "/opt",
    "/proc",
    "/root",
    "/run",
    "/sbin",
    "/srv",
    "/sys",
    "/usr",
    "/var/lib",
    "/var/log",
})

# Paths that are allowed for write operations even in safe mode
SAFE_WRITE_PATHS = frozenset({
    "/tmp",
    "/var/tmp",
})

# File patterns that are always blocked
BLOCKED_PATTERNS = frozenset({
    ".bashrc",
    ".bash_profile",
    ".profile",
    ".ssh",
    "authorized_keys",
    "shadow",
    "passwd",
    "sudoers",
})


def _is_path_blocked(path: str) -> tuple[bool, str]:
    """Check if a path is blocked for write/delete operations.

    Args:
        path: The file path to check.

    Returns:
        Tuple of (is_blocked, reason).
    """
    # Normalize the path
    normalized = os.path.normpath(path)

    # Check for blocked patterns in filename
    basename = os.path.basename(normalized)
    for pattern in BLOCKED_PATTERNS:
        if pattern in basename:
            return True, f"File pattern '{pattern}' is protected"

    # Check if path is in or under a blocked directory
    for blocked in BLOCKED_PATHS:
        if normalized == blocked or normalized.startswith(blocked + "/"):
            # Allow reads but block writes to these paths
            return True, f"Path '{blocked}' is a protected system directory"

    return False, ""


def _is_safe_write_path(path: str) -> bool:
    """Check if a path is in a safe write location.

    Args:
        path: The file path to check.

    Returns:
        True if the path is in a safe write location.
    """
    normalized = os.path.normpath(path)
    for safe_path in SAFE_WRITE_PATHS:
        if normalized.startswith(safe_path + "/") or normalized == safe_path:
            return True
    return False


async def read_file(
    client: WebminClient,
    path: str,
    as_lines: bool = False,
) -> ToolResult:
    """Read the contents of a file.

    Args:
        client: Authenticated WebminClient instance.
        path: Absolute path to the file to read.
        as_lines: If True, return content as array of lines.

    Returns:
        ToolResult with file contents.
    """
    if not path or not path.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="File path cannot be empty",
        )

    if not path.startswith("/"):
        return ToolResult.fail(
            code="INVALID_PATH",
            message="File path must be absolute (start with /)",
        )

    try:
        if as_lines:
            lines = await client.call("webmin", "read_file_lines", path)
            return ToolResult.ok({
                "path": path,
                "lines": lines if isinstance(lines, list) else [],
                "line_count": len(lines) if isinstance(lines, list) else 0,
            })
        else:
            content = await client.call("webmin", "read_file_contents", path)
            return ToolResult.ok({
                "path": path,
                "content": content if isinstance(content, str) else "",
                "size": len(content) if isinstance(content, str) else 0,
            })

    except Exception as e:
        error_msg = str(e).lower()
        if "no such file" in error_msg or "does not exist" in error_msg:
            return ToolResult.fail(
                code="FILE_NOT_FOUND",
                message=f"File not found: {path}",
            )
        if "permission denied" in error_msg:
            return ToolResult.fail(
                code="PERMISSION_DENIED",
                message=f"Permission denied reading: {path}",
            )
        return ToolResult.fail(
            code="READ_FILE_ERROR",
            message=f"Failed to read file '{path}': {e}",
        )


async def write_file(
    client: WebminClient,
    path: str,
    content: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Write content to a file.

    This is a dangerous operation. In safe mode, only writes to /tmp
    and /var/tmp are allowed.

    Args:
        client: Authenticated WebminClient instance.
        path: Absolute path to the file to write.
        content: Content to write to the file.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with write status.
    """
    if not path or not path.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="File path cannot be empty",
        )

    if not path.startswith("/"):
        return ToolResult.fail(
            code="INVALID_PATH",
            message="File path must be absolute (start with /)",
        )

    # Check for blocked paths
    is_blocked, reason = _is_path_blocked(path)
    if is_blocked:
        return ToolResult.fail(
            code="PATH_BLOCKED",
            message=f"Cannot write to this path: {reason}",
        )

    # In safe mode, only allow writes to safe paths
    if safe_mode and not _is_safe_write_path(path):
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message=f"Writing to '{path}' is blocked in safe mode. "
            "Only /tmp and /var/tmp are allowed. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to write elsewhere.",
        )

    try:
        result = await client.call("webmin", "write_file_contents", path, content)

        return ToolResult.ok({
            "action": "write",
            "path": path,
            "success": result == 1,
            "bytes_written": len(content),
        })

    except Exception as e:
        error_msg = str(e).lower()
        if "permission denied" in error_msg:
            return ToolResult.fail(
                code="PERMISSION_DENIED",
                message=f"Permission denied writing to: {path}",
            )
        return ToolResult.fail(
            code="WRITE_FILE_ERROR",
            message=f"Failed to write file '{path}': {e}",
        )


async def delete_file(
    client: WebminClient,
    path: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Delete a file or empty directory.

    This is a dangerous operation and is blocked in safe mode.

    Args:
        client: Authenticated WebminClient instance.
        path: Absolute path to the file/directory to delete.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with deletion status.
    """
    if not path or not path.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="File path cannot be empty",
        )

    if not path.startswith("/"):
        return ToolResult.fail(
            code="INVALID_PATH",
            message="File path must be absolute (start with /)",
        )

    # Check for blocked paths
    is_blocked, reason = _is_path_blocked(path)
    if is_blocked:
        return ToolResult.fail(
            code="PATH_BLOCKED",
            message=f"Cannot delete this path: {reason}",
        )

    # In safe mode, only allow deletes in safe paths
    if safe_mode and not _is_safe_write_path(path):
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message=f"Deleting '{path}' is blocked in safe mode. "
            "Only /tmp and /var/tmp are allowed. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to delete elsewhere.",
        )

    try:
        result = await client.call("webmin", "unlink_file", path)

        # Result is [success, error_message]
        success = result[0] == 1 if isinstance(result, list) else result == 1

        return ToolResult.ok({
            "action": "delete",
            "path": path,
            "success": success,
        })

    except Exception as e:
        error_msg = str(e).lower()
        if "no such file" in error_msg or "does not exist" in error_msg:
            return ToolResult.fail(
                code="FILE_NOT_FOUND",
                message=f"File not found: {path}",
            )
        if "permission denied" in error_msg:
            return ToolResult.fail(
                code="PERMISSION_DENIED",
                message=f"Permission denied deleting: {path}",
            )
        return ToolResult.fail(
            code="DELETE_FILE_ERROR",
            message=f"Failed to delete '{path}': {e}",
        )


async def copy_file(
    client: WebminClient,
    source: str,
    destination: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Copy a file to a new location.

    Args:
        client: Authenticated WebminClient instance.
        source: Absolute path to the source file.
        destination: Absolute path to the destination.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with copy status.
    """
    if not source or not source.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="Source path cannot be empty",
        )

    if not destination or not destination.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="Destination path cannot be empty",
        )

    if not source.startswith("/") or not destination.startswith("/"):
        return ToolResult.fail(
            code="INVALID_PATH",
            message="Paths must be absolute (start with /)",
        )

    # Check destination for blocked paths
    is_blocked, reason = _is_path_blocked(destination)
    if is_blocked:
        return ToolResult.fail(
            code="PATH_BLOCKED",
            message=f"Cannot copy to this path: {reason}",
        )

    # In safe mode, only allow copies to safe paths
    if safe_mode and not _is_safe_write_path(destination):
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message=f"Copying to '{destination}' is blocked in safe mode. "
            "Only /tmp and /var/tmp are allowed. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to copy elsewhere.",
        )

    try:
        result = await client.call("webmin", "copy_source_dest", source, destination)

        # Result is [success, error_message]
        success = result[0] == 1 if isinstance(result, list) else result == 1

        return ToolResult.ok({
            "action": "copy",
            "source": source,
            "destination": destination,
            "success": success,
        })

    except Exception as e:
        error_msg = str(e).lower()
        if "no such file" in error_msg or "does not exist" in error_msg:
            return ToolResult.fail(
                code="FILE_NOT_FOUND",
                message=f"Source file not found: {source}",
            )
        return ToolResult.fail(
            code="COPY_FILE_ERROR",
            message=f"Failed to copy '{source}' to '{destination}': {e}",
        )


async def rename_file(
    client: WebminClient,
    source: str,
    destination: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Rename or move a file.

    Args:
        client: Authenticated WebminClient instance.
        source: Absolute path to the source file.
        destination: Absolute path to the new location/name.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with rename status.
    """
    if not source or not source.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="Source path cannot be empty",
        )

    if not destination or not destination.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="Destination path cannot be empty",
        )

    if not source.startswith("/") or not destination.startswith("/"):
        return ToolResult.fail(
            code="INVALID_PATH",
            message="Paths must be absolute (start with /)",
        )

    # Check both paths for blocked paths
    is_blocked, reason = _is_path_blocked(source)
    if is_blocked:
        return ToolResult.fail(
            code="PATH_BLOCKED",
            message=f"Cannot rename from this path: {reason}",
        )

    is_blocked, reason = _is_path_blocked(destination)
    if is_blocked:
        return ToolResult.fail(
            code="PATH_BLOCKED",
            message=f"Cannot rename to this path: {reason}",
        )

    # In safe mode, both source and destination must be in safe paths
    if safe_mode:
        if not _is_safe_write_path(source):
            return ToolResult.fail(
                code="SAFETY_BLOCKED",
                message=f"Renaming from '{source}' is blocked in safe mode. "
                "Only /tmp and /var/tmp are allowed.",
            )
        if not _is_safe_write_path(destination):
            return ToolResult.fail(
                code="SAFETY_BLOCKED",
                message=f"Renaming to '{destination}' is blocked in safe mode. "
                "Only /tmp and /var/tmp are allowed.",
            )

    try:
        result = await client.call("webmin", "rename_file", source, destination)

        return ToolResult.ok({
            "action": "rename",
            "source": source,
            "destination": destination,
            "success": result == 1,
        })

    except Exception as e:
        error_msg = str(e).lower()
        if "no such file" in error_msg or "does not exist" in error_msg:
            return ToolResult.fail(
                code="FILE_NOT_FOUND",
                message=f"Source file not found: {source}",
            )
        return ToolResult.fail(
            code="RENAME_FILE_ERROR",
            message=f"Failed to rename '{source}' to '{destination}': {e}",
        )


async def create_directory(
    client: WebminClient,
    path: str,
    mode: int = 755,
    safe_mode: bool = True,
) -> ToolResult:
    """Create a new directory.

    Args:
        client: Authenticated WebminClient instance.
        path: Absolute path to the directory to create.
        mode: Permission mode (default: 755).
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with creation status.
    """
    if not path or not path.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="Directory path cannot be empty",
        )

    if not path.startswith("/"):
        return ToolResult.fail(
            code="INVALID_PATH",
            message="Directory path must be absolute (start with /)",
        )

    # Validate mode
    if mode < 0 or mode > 777:
        return ToolResult.fail(
            code="INVALID_MODE",
            message="Mode must be between 0 and 777",
        )

    # Check for blocked paths
    is_blocked, reason = _is_path_blocked(path)
    if is_blocked:
        return ToolResult.fail(
            code="PATH_BLOCKED",
            message=f"Cannot create directory at this path: {reason}",
        )

    # In safe mode, only allow directory creation in safe paths
    if safe_mode and not _is_safe_write_path(path):
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message=f"Creating directory at '{path}' is blocked in safe mode. "
            "Only /tmp and /var/tmp are allowed. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to create elsewhere.",
        )

    try:
        result = await client.call("webmin", "make_dir", path, mode)

        return ToolResult.ok({
            "action": "create_directory",
            "path": path,
            "mode": mode,
            "success": result == 1,
        })

    except Exception as e:
        error_msg = str(e).lower()
        if "exists" in error_msg:
            return ToolResult.fail(
                code="DIRECTORY_EXISTS",
                message=f"Directory already exists: {path}",
            )
        if "permission denied" in error_msg:
            return ToolResult.fail(
                code="PERMISSION_DENIED",
                message=f"Permission denied creating: {path}",
            )
        return ToolResult.fail(
            code="CREATE_DIR_ERROR",
            message=f"Failed to create directory '{path}': {e}",
        )


async def list_processes(client: WebminClient) -> ToolResult:
    """List all running processes.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with process list.
    """
    try:
        processes_raw = await client.call("proc", "list_processes")

        processes = []
        for proc in processes_raw:
            if isinstance(proc, dict):
                processes.append({
                    "pid": proc.get("pid"),
                    "ppid": proc.get("ppid"),
                    "user": proc.get("user"),
                    "cpu": proc.get("cpu"),
                    "memory": proc.get("size"),
                    "memory_bytes": proc.get("bytes"),
                    "time": proc.get("time"),
                    "command": proc.get("args"),
                    "nice": proc.get("nice"),
                    "tty": proc.get("_tty"),
                })

        return ToolResult.ok({
            "count": len(processes),
            "processes": processes,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_PROCESSES_ERROR",
            message=f"Failed to list processes: {e}",
        )


async def list_mounts(client: WebminClient) -> ToolResult:
    """List all mounted filesystems.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with mount list.
    """
    try:
        mounts_raw = await client.call("mount", "list_mounted")

        mounts = []
        for mount in mounts_raw:
            if isinstance(mount, (list, tuple)) and len(mount) >= 4:
                mounts.append({
                    "mount_point": mount[0],
                    "device": mount[1],
                    "type": mount[2],
                    "options": mount[3],
                })

        # Filter out pseudo-filesystems for a cleaner view
        real_mounts = [
            m for m in mounts
            if m["type"] not in ("sysfs", "proc", "devtmpfs", "devpts", "tmpfs",
                                  "securityfs", "cgroup", "cgroup2", "pstore",
                                  "debugfs", "tracefs", "configfs", "fusectl",
                                  "hugetlbfs", "mqueue", "binfmt_misc", "autofs",
                                  "efivarfs", "bpf")
        ]

        return ToolResult.ok({
            "total_count": len(mounts),
            "real_filesystem_count": len(real_mounts),
            "mounts": mounts,
            "real_filesystems": real_mounts,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_MOUNTS_ERROR",
            message=f"Failed to list mounts: {e}",
        )
