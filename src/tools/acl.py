"""Webmin ACL (Access Control List) management tools.

Phase 7 tools for managing Webmin user accounts and permissions.
These manage Webmin-level users (who can log into the Webmin UI),
NOT system-level users (managed by useradmin module).
"""

import re
from typing import Any

from ..models import ToolResult
from ..webmin_client import WebminClient


def _validate_webmin_username(username: str) -> str | None:
    """Validate a Webmin username.

    Args:
        username: The username to validate.

    Returns:
        Error message if invalid, None if valid.
    """
    if not username:
        return "Username cannot be empty"

    if len(username) > 64:
        return "Username must be 64 characters or less"

    # Webmin usernames: letters, digits, underscores, hyphens, dots
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.\-]*$", username):
        return (
            "Username must start with a letter or underscore, and contain only "
            "letters, digits, underscores, hyphens, and dots"
        )

    return None


async def list_webmin_users(client: WebminClient) -> ToolResult:
    """List all Webmin user accounts.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of Webmin users.
    """
    try:
        users_raw = await client.call("acl", "list_users")

        users = []
        for user in users_raw:
            if isinstance(user, dict):
                modules = user.get("modules", [])
                if isinstance(modules, str):
                    modules = [m.strip() for m in modules.split() if m.strip()]

                users.append({
                    "name": user.get("name"),
                    "modules": modules,
                    "module_count": len(modules),
                    "has_all_modules": "*" in modules if isinstance(modules, list) else False,
                })

        return ToolResult.ok({
            "count": len(users),
            "users": users,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_WEBMIN_USERS_ERROR",
            message=f"Failed to list Webmin users: {e}",
        )


async def get_webmin_user(client: WebminClient, username: str) -> ToolResult:
    """Get detailed information about a Webmin user.

    Uses acl::get_user(username) for direct lookup instead of listing all users.

    Args:
        client: Authenticated WebminClient instance.
        username: Webmin username to look up.

    Returns:
        ToolResult with user details and permissions.
    """
    if not username:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: username",
        )

    try:
        user = await client.call("acl", "get_user", username)

        if not user or not isinstance(user, dict):
            return ToolResult.fail(
                code="USER_NOT_FOUND",
                message=f"Webmin user '{username}' not found",
            )

        modules = user.get("modules", [])
        if isinstance(modules, str):
            modules = [m.strip() for m in modules.split() if m.strip()]

        return ToolResult.ok({
            "name": user.get("name"),
            "modules": modules,
            "module_count": len(modules),
            "has_all_modules": "*" in modules if isinstance(modules, list) else False,
            "lang": user.get("lang"),
            "theme": user.get("theme"),
            "readonly": user.get("readonly"),
        })

    except Exception as e:
        return ToolResult.fail(
            code="GET_WEBMIN_USER_ERROR",
            message=f"Failed to get Webmin user '{username}': {e}",
        )


async def list_webmin_modules(client: WebminClient) -> ToolResult:
    """List all available Webmin modules.

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        ToolResult with list of installed modules.
    """
    try:
        modules_raw = await client.call("acl", "list_module_infos")

        modules = []
        if isinstance(modules_raw, list):
            for mod in modules_raw:
                if isinstance(mod, dict):
                    modules.append({
                        "name": mod.get("dir") or mod.get("name"),
                        "description": mod.get("desc"),
                        "category": mod.get("category"),
                    })
        elif isinstance(modules_raw, dict):
            for name, info in modules_raw.items():
                if isinstance(info, dict):
                    modules.append({
                        "name": name,
                        "description": info.get("desc"),
                        "category": info.get("category"),
                    })

        return ToolResult.ok({
            "count": len(modules),
            "modules": modules,
        })

    except Exception as e:
        return ToolResult.fail(
            code="LIST_WEBMIN_MODULES_ERROR",
            message=f"Failed to list Webmin modules: {e}",
        )


async def _count_superusers(client: WebminClient) -> int:
    """Count the number of Webmin users with full admin access.

    A superuser is one whose modules list contains '*' (all modules).

    Args:
        client: Authenticated WebminClient instance.

    Returns:
        Number of superuser accounts.
    """
    users_raw = await client.call("acl", "list_users")
    count = 0
    for user in users_raw:
        if isinstance(user, dict):
            modules = user.get("modules", [])
            if (isinstance(modules, list) and "*" in modules) or (
                isinstance(modules, str) and "*" in modules.split()
            ):
                count += 1
    return count


async def create_webmin_user(
    client: WebminClient,
    username: str,
    password: str,
    modules: list[str] | None = None,
    safe_mode: bool = True,
) -> ToolResult:
    """Create a new Webmin user account.

    This is a dangerous operation and is blocked in safe mode.

    Args:
        client: Authenticated WebminClient instance.
        username: Username for the new Webmin account.
        password: Password for the new account.
        modules: List of module names to grant access to.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with created user details.
    """
    if safe_mode:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message="Creating Webmin users is blocked in safe mode. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to allow Webmin user creation.",
        )

    # Validate username
    username_error = _validate_webmin_username(username)
    if username_error:
        return ToolResult.fail(
            code="INVALID_USERNAME",
            message=username_error,
        )

    # Validate password
    if not password:
        return ToolResult.fail(
            code="INVALID_PASSWORD",
            message="Password cannot be empty",
        )

    try:
        # Check if user already exists using direct lookup
        existing = await client.call("acl", "get_user", username)
        if existing and isinstance(existing, dict):
            return ToolResult.fail(
                code="USER_EXISTS",
                message=f"Webmin user '{username}' already exists",
            )

        # Encrypt password before storing (Webmin requires pre-encrypted passwords)
        encrypted_pass = await client.call("acl", "encrypt_password", password)

        # Build user structure
        user_data: dict[str, Any] = {
            "name": username,
            "pass": encrypted_pass,
            "modules": modules or [],
        }

        # Create the user
        await client.call("acl", "create_user", user_data)

        return ToolResult.ok({
            "action": "create",
            "success": True,
            "user": {
                "name": username,
                "modules": modules or [],
                "module_count": len(modules) if modules else 0,
            },
        })

    except Exception as e:
        return ToolResult.fail(
            code="CREATE_WEBMIN_USER_ERROR",
            message=f"Failed to create Webmin user '{username}': {e}",
        )


async def modify_webmin_user(
    client: WebminClient,
    username: str,
    password: str | None = None,
    modules: list[str] | None = None,
    safe_mode: bool = True,
) -> ToolResult:
    """Modify a Webmin user's permissions or password.

    This is a dangerous operation and is blocked in safe mode.

    Args:
        client: Authenticated WebminClient instance.
        username: Username of the Webmin user to modify.
        password: New password (optional).
        modules: New list of module names (optional).
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with updated user details.
    """
    if safe_mode:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message="Modifying Webmin users is blocked in safe mode. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to allow modifications.",
        )

    try:
        # Find the user
        users_raw = await client.call("acl", "list_users")
        old_user = None
        for user in users_raw:
            if isinstance(user, dict) and user.get("name") == username:
                old_user = user
                break

        if not old_user:
            return ToolResult.fail(
                code="USER_NOT_FOUND",
                message=f"Webmin user '{username}' not found",
            )

        # Check superuser demotion protection
        if modules is not None:
            old_modules = old_user.get("modules", [])
            if isinstance(old_modules, str):
                old_modules = old_modules.split()
            was_superuser = "*" in old_modules
            will_be_superuser = "*" in modules

            if was_superuser and not will_be_superuser:
                superuser_count = await _count_superusers(client)
                if superuser_count <= 1:
                    return ToolResult.fail(
                        code="LAST_SUPERUSER",
                        message="Cannot demote the last superuser account. "
                        "This would lock out all admin access to Webmin.",
                    )

        # Build updated user data
        new_user = old_user.copy()
        changes: dict[str, bool] = {}

        if password is not None:
            # Encrypt password before storing (Webmin requires pre-encrypted passwords)
            new_user["pass"] = await client.call("acl", "encrypt_password", password)
            changes["password"] = True
        if modules is not None:
            new_user["modules"] = modules
            changes["modules"] = True

        if not changes:
            return ToolResult.ok({
                "action": "modify",
                "success": True,
                "message": "No changes specified",
                "user": {"name": username},
                "changes": {},
            })

        # Modify the user
        await client.call("acl", "modify_user", username, new_user)

        result_modules = modules if modules is not None else old_user.get("modules", [])

        return ToolResult.ok({
            "action": "modify",
            "success": True,
            "user": {
                "name": username,
                "modules": result_modules,
                "module_count": len(result_modules) if isinstance(result_modules, list) else 0,
            },
            "changes": changes,
        })

    except Exception as e:
        return ToolResult.fail(
            code="MODIFY_WEBMIN_USER_ERROR",
            message=f"Failed to modify Webmin user '{username}': {e}",
        )


async def delete_webmin_user(
    client: WebminClient,
    username: str,
    safe_mode: bool = True,
) -> ToolResult:
    """Delete a Webmin user account.

    This is a dangerous operation and is blocked in safe mode.
    Deletion of the last superuser account is ALWAYS blocked
    regardless of safe mode to prevent Webmin lockout.

    Args:
        client: Authenticated WebminClient instance.
        username: Username of the Webmin user to delete.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with deletion status.
    """
    if safe_mode:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message="Deleting Webmin users is blocked in safe mode. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to allow deletion.",
        )

    if not username:
        return ToolResult.fail(
            code="MISSING_ARGUMENT",
            message="Missing required argument: username",
        )

    try:
        # Find the user
        users_raw = await client.call("acl", "list_users")
        target_user = None
        for user in users_raw:
            if isinstance(user, dict) and user.get("name") == username:
                target_user = user
                break

        if not target_user:
            return ToolResult.fail(
                code="USER_NOT_FOUND",
                message=f"Webmin user '{username}' not found",
            )

        # UNCONDITIONAL: Block deletion of the last superuser
        target_modules = target_user.get("modules", [])
        if isinstance(target_modules, str):
            target_modules = target_modules.split()
        is_superuser = "*" in target_modules

        if is_superuser:
            superuser_count = await _count_superusers(client)
            if superuser_count <= 1:
                return ToolResult.fail(
                    code="LAST_SUPERUSER",
                    message="Cannot delete the last superuser account. "
                    "This would permanently lock out all admin access to Webmin.",
                )

        # Remove from groups before deletion
        await client.call("acl", "delete_from_groups", username)
        # Delete the user
        await client.call("acl", "delete_user", username)

        return ToolResult.ok({
            "action": "delete",
            "success": True,
            "deleted_user": {"name": username},
        })

    except Exception as e:
        return ToolResult.fail(
            code="DELETE_WEBMIN_USER_ERROR",
            message=f"Failed to delete Webmin user '{username}': {e}",
        )
