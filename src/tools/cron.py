"""Cron job management tools for Webmin MCP Server.

Phase 2 tools for creating, editing, and deleting scheduled cron jobs
with safety framework enforcement.
"""

from typing import Any

from ..models import ToolResult
from ..safety import check_safety, SafetyTier
from ..webmin_client import WebminClient


def _validate_schedule_field(value: str, field: str, min_val: int, max_val: int) -> str | None:
    """Validate a cron schedule field.

    Args:
        value: The value to validate.
        field: Field name for error messages.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.

    Returns:
        Error message if invalid, None if valid.
    """
    if value == "*":
        return None

    # Handle ranges (e.g., "1-5")
    if "-" in value:
        parts = value.split("-")
        if len(parts) != 2:
            return f"Invalid range format for {field}: {value}"
        try:
            start, end = int(parts[0]), int(parts[1])
            if start < min_val or end > max_val or start > end:
                return f"Invalid range for {field}: {value} (must be {min_val}-{max_val})"
        except ValueError:
            return f"Invalid range values for {field}: {value}"
        return None

    # Handle lists (e.g., "1,3,5")
    if "," in value:
        for part in value.split(","):
            error = _validate_schedule_field(part.strip(), field, min_val, max_val)
            if error:
                return error
        return None

    # Handle step values (e.g., "*/5")
    if "/" in value:
        parts = value.split("/")
        if len(parts) != 2:
            return f"Invalid step format for {field}: {value}"
        base, step = parts
        if base != "*":
            error = _validate_schedule_field(base, field, min_val, max_val)
            if error:
                return error
        try:
            step_val = int(step)
            if step_val < 1:
                return f"Step value must be positive for {field}: {value}"
        except ValueError:
            return f"Invalid step value for {field}: {value}"
        return None

    # Single value
    try:
        val = int(value)
        if val < min_val or val > max_val:
            return f"Value out of range for {field}: {value} (must be {min_val}-{max_val})"
    except ValueError:
        return f"Invalid value for {field}: {value}"

    return None


def _validate_cron_schedule(
    minutes: str,
    hours: str,
    days: str,
    months: str,
    weekdays: str,
) -> str | None:
    """Validate a complete cron schedule.

    Args:
        minutes: Cron minutes field (0-59).
        hours: Cron hours field (0-23).
        days: Cron days field (1-31).
        months: Cron months field (1-12).
        weekdays: Cron weekdays field (0-7, 0 and 7 are Sunday).

    Returns:
        Error message if invalid, None if valid.
    """
    validations = [
        (minutes, "minutes", 0, 59),
        (hours, "hours", 0, 23),
        (days, "days", 1, 31),
        (months, "months", 1, 12),
        (weekdays, "weekdays", 0, 7),
    ]

    for value, field, min_val, max_val in validations:
        error = _validate_schedule_field(str(value), field, min_val, max_val)
        if error:
            return error

    return None


async def create_cron_job(
    client: WebminClient,
    command: str,
    minutes: str = "*",
    hours: str = "*",
    days: str = "*",
    months: str = "*",
    weekdays: str = "*",
    user: str = "root",
    active: bool = True,
    safe_mode: bool = True,
) -> ToolResult:
    """Create a new cron job.

    Args:
        client: Authenticated WebminClient instance.
        command: Command to execute.
        minutes: Cron minutes field (0-59 or *).
        hours: Cron hours field (0-23 or *).
        days: Cron days field (1-31 or *).
        months: Cron months field (1-12 or *).
        weekdays: Cron weekdays field (0-7 or *, 0 and 7 are Sunday).
        user: User to run the job as.
        active: Whether the job is active.
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with created job details.
    """
    # Validate command
    if not command or not command.strip():
        return ToolResult.fail(
            code="INVALID_ARGUMENT",
            message="Command cannot be empty",
        )

    # Validate schedule
    schedule_error = _validate_cron_schedule(minutes, hours, days, months, weekdays)
    if schedule_error:
        return ToolResult.fail(
            code="INVALID_SCHEDULE",
            message=schedule_error,
        )

    try:
        # Build job structure
        job = {
            "user": user,
            "command": command,
            "mins": str(minutes),
            "hours": str(hours),
            "days": str(days),
            "months": str(months),
            "weekdays": str(weekdays),
            "active": 1 if active else 0,
        }

        # Create the job
        result = await client.call("cron", "create_cron_job", job)

        # Get the created job details
        jobs = await client.call("cron", "list_cron_jobs")
        created_job = None
        for j in jobs:
            if j.get("command") == command and j.get("user") == user:
                created_job = j
                break

        schedule = f"{minutes} {hours} {days} {months} {weekdays}"

        return ToolResult.ok({
            "action": "create",
            "success": True,
            "job": {
                "command": command,
                "schedule": schedule,
                "user": user,
                "active": active,
                "file": created_job.get("file") if created_job else None,
                "index": created_job.get("index") if created_job else None,
            },
            "total_jobs": result if isinstance(result, int) else len(jobs),
        })

    except Exception as e:
        return ToolResult.fail(
            code="CREATE_CRON_ERROR",
            message=f"Failed to create cron job: {e}",
        )


async def edit_cron_job(
    client: WebminClient,
    index: int,
    command: str | None = None,
    minutes: str | None = None,
    hours: str | None = None,
    days: str | None = None,
    months: str | None = None,
    weekdays: str | None = None,
    user: str | None = None,
    active: bool | None = None,
    safe_mode: bool = True,
) -> ToolResult:
    """Edit an existing cron job.

    Args:
        client: Authenticated WebminClient instance.
        index: Index of the job to edit (from list_cron_jobs).
        command: New command (optional).
        minutes: New minutes field (optional).
        hours: New hours field (optional).
        days: New days field (optional).
        months: New months field (optional).
        weekdays: New weekdays field (optional).
        user: New user (optional).
        active: New active state (optional).
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with updated job details.
    """
    try:
        # Get current jobs
        jobs = await client.call("cron", "list_cron_jobs")

        # Find the job by index
        old_job = None
        for job in jobs:
            if job.get("index") == index:
                old_job = job
                break

        if not old_job:
            return ToolResult.fail(
                code="JOB_NOT_FOUND",
                message=f"Cron job with index {index} not found",
            )

        # Build new job with updates
        new_job = old_job.copy()

        if command is not None:
            if not command.strip():
                return ToolResult.fail(
                    code="INVALID_ARGUMENT",
                    message="Command cannot be empty",
                )
            new_job["command"] = command

        if minutes is not None:
            new_job["mins"] = str(minutes)
        if hours is not None:
            new_job["hours"] = str(hours)
        if days is not None:
            new_job["days"] = str(days)
        if months is not None:
            new_job["months"] = str(months)
        if weekdays is not None:
            new_job["weekdays"] = str(weekdays)
        if user is not None:
            new_job["user"] = user
        if active is not None:
            new_job["active"] = 1 if active else 0

        # Validate new schedule
        schedule_error = _validate_cron_schedule(
            new_job.get("mins", "*"),
            new_job.get("hours", "*"),
            new_job.get("days", "*"),
            new_job.get("months", "*"),
            new_job.get("weekdays", "*"),
        )
        if schedule_error:
            return ToolResult.fail(
                code="INVALID_SCHEDULE",
                message=schedule_error,
            )

        # Update the job
        result = await client.call("cron", "change_cron_job", old_job, new_job)

        schedule = "{} {} {} {} {}".format(
            new_job.get("mins", "*"),
            new_job.get("hours", "*"),
            new_job.get("days", "*"),
            new_job.get("months", "*"),
            new_job.get("weekdays", "*"),
        )

        return ToolResult.ok({
            "action": "edit",
            "success": True,
            "job": {
                "index": index,
                "command": new_job.get("command"),
                "schedule": schedule,
                "user": new_job.get("user"),
                "active": bool(new_job.get("active")),
                "file": new_job.get("file"),
            },
            "changes": {
                "command": command is not None,
                "schedule": any(x is not None for x in [minutes, hours, days, months, weekdays]),
                "user": user is not None,
                "active": active is not None,
            },
        })

    except Exception as e:
        return ToolResult.fail(
            code="EDIT_CRON_ERROR",
            message=f"Failed to edit cron job: {e}",
        )


async def delete_cron_job(
    client: WebminClient,
    index: int,
    safe_mode: bool = True,
) -> ToolResult:
    """Delete a cron job.

    This is a dangerous operation and is blocked in safe mode.

    Args:
        client: Authenticated WebminClient instance.
        index: Index of the job to delete (from list_cron_jobs).
        safe_mode: Whether safe mode is enabled.

    Returns:
        ToolResult with deletion status.
    """
    # Safety check - delete is dangerous
    if safe_mode:
        return ToolResult.fail(
            code="SAFETY_BLOCKED",
            message="Deleting cron jobs is blocked in safe mode. "
            "Disable safe mode (WEBMIN_SAFE_MODE=false) to allow deletion.",
        )

    try:
        # Get current jobs
        jobs = await client.call("cron", "list_cron_jobs")
        jobs_before = len(jobs)

        # Find the job by index
        job_to_delete = None
        for job in jobs:
            if job.get("index") == index:
                job_to_delete = job
                break

        if not job_to_delete:
            return ToolResult.fail(
                code="JOB_NOT_FOUND",
                message=f"Cron job with index {index} not found",
            )

        # Store job info for response
        deleted_job_info = {
            "index": index,
            "command": job_to_delete.get("command"),
            "user": job_to_delete.get("user"),
            "file": job_to_delete.get("file"),
        }

        # Delete the job
        await client.call("cron", "delete_cron_job", job_to_delete)

        # Verify deletion
        jobs_after = await client.call("cron", "list_cron_jobs")

        return ToolResult.ok({
            "action": "delete",
            "success": len(jobs_after) < jobs_before,
            "deleted_job": deleted_job_info,
            "jobs_before": jobs_before,
            "jobs_after": len(jobs_after),
        })

    except Exception as e:
        return ToolResult.fail(
            code="DELETE_CRON_ERROR",
            message=f"Failed to delete cron job: {e}",
        )
