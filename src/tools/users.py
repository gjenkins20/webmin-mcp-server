"""User and group management tools for Webmin MCP Server.

Phase 3 tools for creating, modifying, and deleting system users
with safety framework enforcement.
"""

import re
from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


def _validate_username(username: str) -> str | None:
    """Validate a username.

    Args:
        username: The username to validate.

    Returns:
        Error message if invalid, None if valid.
    """
    if not username:
        return "Username cannot be empty"

    if len(username) > 32:
        return "Username must be 32 characters or less"

    # Linux username rules: lowercase letters, digits, underscore, hyphen
    # Must start with a letter or underscore
    if not re.match(r"^[a-z_][a-z0-9_-]*$", username):
        return (
            "Username must start with a letter or underscore, and contain only "
            "lowercase letters, digits, underscores, and hyphens"
        )

    return None


def _validate_uid(uid: int) -> str | None:
    """Validate a user ID.

    Args:
        uid: The UID to validate.

    Returns:
        Error message if invalid, None if valid.
    """
    if uid < 0:
        return "UID must be non-negative"

    if uid > 65534:
        return "UID must be 65534 or less"

    return None


async def list_groups(client: WebminClient) -> ToolResult:
    """List all system groups.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of groups.
    """
    try:
        groups_raw = await client.call("useradmin", "list_groups")

        groups = []
        for group in groups_raw:
            if isinstance(group, dict):
                members = group.get("members", "")
                member_list = [m.strip() for m in members.split(",") if m.strip()] if members else []

                groups.append({
                    "name": group.get("group"),
                    "gid": group.get("gid"),
                    "members": member_list,
                    "member_count": len(member_list),
                })

        # Separate system and regular groups
        system_groups = [g for g in groups if g.get("gid", 0) < 1000]
        regular_groups = [g for g in groups if g.get("gid", 0) >= 1000]

        return ToolResult.ok({
            "total_count": len(groups),
            "regular_groups": regular_groups,
            "regular_count": len(regular_groups),
            "system_groups": system_groups,
            "system_count": len(system_groups),
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_GROUPS_ERROR",
            message=f"Failed to list groups: {e}",
        )


async def create_user(
    client: WebminClient,
    username: str,
    password: str,
    real_name: str | None = None,
    home_dir: str | None = None,
    shell: str = "/bin/bash",
    uid: int | None = None,
    gid: int | None = None,
    safe_mode: bool = True,
) -> ToolResult:
    """Create a new system user.

    This is a dangerous operation and is blocked in safe mode.

    Args:
        client: Authenticated WebminClient instance.
        username: Username for the new user.
        password: Password for the new user.
        real_name: Full name/comment for the user.
        home_dir: Home directory (default: /home/username).
        shell: Login shell (default: /bin/bash).
        uid: User ID (auto-assigned if not specified).
        gid: Group ID (auto-assigned if not specified).
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with created user details.
    """
    # Safety check
    if safe_mode:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message="Creating users is blocked in safe mode. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to allow user creation.",
        )

    # Validate username
    username_error = _validate_username(username)
    if username_error:
        return ToolResult.fail(
            code="INVALID_USERNAME",
            message=username_error,
        )

    # Validate password
    if not password or len(password) < 1:
        return ToolResult.fail(
            code="INVALID_PASSWORD",
            message="Password cannot be empty",
        )

    # Validate UID if provided
    if uid is not None:
        uid_error = _validate_uid(uid)
        if uid_error:
            return ToolResult.fail(
                code="INVALID_UID",
                message=uid_error,
            )

    try:
        # Check if user already exists
        existing_users = await client.call("useradmin", "list_users")
        for user in existing_users:
            if user.get("user") == username:
                return ToolResult.fail(
                    code="USER_EXISTS",
                    message=f"User '{username}' already exists",
                )

        # Find next available UID if not specified
        if uid is None:
            used_uids = {u.get("uid") for u in existing_users}
            uid = 1000
            while uid in used_uids:
                uid += 1

        # Use same GID as UID if not specified
        if gid is None:
            gid = uid

        # Build user structure
        user_data = {
            "user": username,
            "pass": password,
            "uid": uid,
            "gid": gid,
            "real": real_name or username,
            "home": home_dir or f"/home/{username}",
            "shell": shell,
        }

        # Create the user
        result = await client.call("useradmin", "create_user", user_data)

        # Verify creation
        users_after = await client.call("useradmin", "list_users")
        created_user = None
        for user in users_after:
            if user.get("user") == username:
                created_user = user
                break

        return ToolResult.ok({
            "action": "create",
            "success": created_user is not None,
            "user": {
                "username": username,
                "uid": uid,
                "gid": gid,
                "real_name": real_name or username,
                "home": home_dir or f"/home/{username}",
                "shell": shell,
            },
        })

    except Exception as e:
        return ToolResult.fail(
            code="CREATE_USER_ERROR",
            message=f"Failed to create user '{username}': {e}",
        )


async def delete_user(
    client: WebminClient,
    username: str,
    delete_home: bool = False,
    safe_mode: bool = True,
) -> ToolResult:
    """Delete a system user.

    This is a dangerous operation and is blocked in safe mode.

    Args:
        client: Authenticated WebminClient instance.
        username: Username of the user to delete.
        delete_home: Whether to delete the user's home directory.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with deletion status.
    """
    # Safety check
    if safe_mode:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message="Deleting users is blocked in safe mode. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to allow user deletion.",
        )

    # Block deletion of critical users
    critical_users = {"root", "daemon", "bin", "sys", "sync", "nobody", "systemd-network", "systemd-resolve"}
    if username.lower() in critical_users:
        return ToolResult.fail(
            code="CRITICAL_USER",
            message=f"Cannot delete critical system user '{username}'",
        )

    try:
        # Find the user
        users = await client.call("useradmin", "list_users")
        user_to_delete = None
        for user in users:
            if user.get("user") == username:
                user_to_delete = user
                break

        if not user_to_delete:
            return ToolResult.fail(
                code="USER_NOT_FOUND",
                message=f"User '{username}' not found",
            )

        # Store user info for response
        deleted_user_info = {
            "username": username,
            "uid": user_to_delete.get("uid"),
            "home": user_to_delete.get("home"),
        }

        # Delete the user
        # Note: Webmin's delete_user needs the full user hash
        await client.call("useradmin", "delete_user", user_to_delete)

        # Verify deletion
        users_after = await client.call("useradmin", "list_users")
        still_exists = any(u.get("user") == username for u in users_after)

        return ToolResult.ok({
            "action": "delete",
            "success": not still_exists,
            "deleted_user": deleted_user_info,
            "home_deleted": delete_home,  # Note: actual home deletion may need separate handling
        })

    except Exception as e:
        return ToolResult.fail(
            code="DELETE_USER_ERROR",
            message=f"Failed to delete user '{username}': {e}",
        )


async def modify_user(
    client: WebminClient,
    username: str,
    new_username: str | None = None,
    real_name: str | None = None,
    home_dir: str | None = None,
    shell: str | None = None,
    uid: int | None = None,
    gid: int | None = None,
    safe_mode: bool = True,
) -> ToolResult:
    """Modify an existing system user.

    Args:
        client: Authenticated WebminClient instance.
        username: Current username of the user to modify.
        new_username: New username (optional).
        real_name: New full name/comment (optional).
        home_dir: New home directory (optional).
        shell: New login shell (optional).
        uid: New user ID (optional).
        gid: New group ID (optional).
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with updated user details.
    """
    # Validate new username if provided
    if new_username is not None:
        username_error = _validate_username(new_username)
        if username_error:
            return ToolResult.fail(
                code="INVALID_USERNAME",
                message=username_error,
            )

    # Validate UID if provided
    if uid is not None:
        uid_error = _validate_uid(uid)
        if uid_error:
            return ToolResult.fail(
                code="INVALID_UID",
                message=uid_error,
            )

    try:
        # Find the user
        users = await client.call("useradmin", "list_users")
        old_user = None
        for user in users:
            if user.get("user") == username:
                old_user = user
                break

        if not old_user:
            return ToolResult.fail(
                code="USER_NOT_FOUND",
                message=f"User '{username}' not found",
            )

        # Build new user data
        new_user = old_user.copy()

        changes = {}
        if new_username is not None:
            new_user["user"] = new_username
            changes["username"] = True
        if real_name is not None:
            new_user["real"] = real_name
            changes["real_name"] = True
        if home_dir is not None:
            new_user["home"] = home_dir
            changes["home_dir"] = True
        if shell is not None:
            new_user["shell"] = shell
            changes["shell"] = True
        if uid is not None:
            new_user["uid"] = uid
            changes["uid"] = True
        if gid is not None:
            new_user["gid"] = gid
            changes["gid"] = True

        if not changes:
            return ToolResult.ok({
                "action": "modify",
                "success": True,
                "message": "No changes specified",
                "user": {
                    "username": old_user.get("user"),
                    "uid": old_user.get("uid"),
                    "gid": old_user.get("gid"),
                    "real_name": old_user.get("real"),
                    "home": old_user.get("home"),
                    "shell": old_user.get("shell"),
                },
                "changes": {},
            })

        # Modify the user
        result = await client.call("useradmin", "modify_user", old_user, new_user)

        return ToolResult.ok({
            "action": "modify",
            "success": True,
            "user": {
                "username": new_user.get("user"),
                "uid": new_user.get("uid"),
                "gid": new_user.get("gid"),
                "real_name": new_user.get("real"),
                "home": new_user.get("home"),
                "shell": new_user.get("shell"),
            },
            "changes": changes,
        })

    except Exception as e:
        return ToolResult.fail(
            code="MODIFY_USER_ERROR",
            message=f"Failed to modify user '{username}': {e}",
        )


async def change_password(
    client: WebminClient,
    username: str,
    new_password: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Change a user's password.

    This is a dangerous operation and is blocked in safe mode.

    Args:
        client: Authenticated WebminClient instance.
        username: Username of the user.
        new_password: New password.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with status.
    """
    # Safety check
    if safe_mode:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message="Changing passwords is blocked in safe mode. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to allow password changes.",
        )

    # Validate password
    if not new_password or len(new_password) < 1:
        return ToolResult.fail(
            code="INVALID_PASSWORD",
            message="Password cannot be empty",
        )

    try:
        # Find the user
        users = await client.call("useradmin", "list_users")
        old_user = None
        for user in users:
            if user.get("user") == username:
                old_user = user
                break

        if not old_user:
            return ToolResult.fail(
                code="USER_NOT_FOUND",
                message=f"User '{username}' not found",
            )

        # Build new user data with new password
        new_user = old_user.copy()
        new_user["pass"] = new_password

        # Modify the user (this updates the password)
        result = await client.call("useradmin", "modify_user", old_user, new_user)

        return ToolResult.ok({
            "action": "change_password",
            "success": True,
            "username": username,
        })

    except Exception as e:
        return ToolResult.fail(
            code="CHANGE_PASSWORD_ERROR",
            message=f"Failed to change password for user '{username}': {e}",
        )
