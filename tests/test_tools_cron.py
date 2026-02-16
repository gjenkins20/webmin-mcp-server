"""Tests for Phase 2 cron management tools."""

from unittest.mock import AsyncMock

import pytest

from src.tools import cron


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestCreateCronJob:
    """Tests for create_cron_job tool."""

    async def test_create_cron_job_success(self, mock_client: AsyncMock) -> None:
        """Test successfully creating a cron job."""
        mock_client.call.side_effect = [
            14,  # create_cron_job returns new job count
            [  # list_cron_jobs
                {
                    "index": 13,
                    "command": "/bin/echo test",
                    "user": "root",
                    "mins": "30",
                    "hours": "2",
                    "days": "*",
                    "months": "*",
                    "weekdays": "*",
                    "active": 1,
                    "file": "/var/spool/cron/crontabs/root",
                }
            ],
        ]

        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            minutes="30",
            hours="2",
            safe_mode=True,
        )

        assert result.success
        assert result.data["action"] == "create"
        assert result.data["job"]["command"] == "/bin/echo test"
        assert result.data["job"]["schedule"] == "30 2 * * *"

    async def test_create_cron_job_empty_command(self, mock_client: AsyncMock) -> None:
        """Test that empty command is rejected."""
        result = await cron.create_cron_job(
            mock_client,
            command="",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_ARGUMENT"
        mock_client.call.assert_not_called()

    async def test_create_cron_job_invalid_minutes(self, mock_client: AsyncMock) -> None:
        """Test that invalid minutes are rejected."""
        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            minutes="60",  # Invalid: must be 0-59
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_SCHEDULE"
        mock_client.call.assert_not_called()

    async def test_create_cron_job_invalid_hours(self, mock_client: AsyncMock) -> None:
        """Test that invalid hours are rejected."""
        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            hours="25",  # Invalid: must be 0-23
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_SCHEDULE"

    async def test_create_cron_job_with_step_values(self, mock_client: AsyncMock) -> None:
        """Test creating job with step values like */5."""
        mock_client.call.side_effect = [14, []]

        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            minutes="*/5",
            hours="*/2",
            safe_mode=True,
        )

        assert result.success

    async def test_create_cron_job_with_range(self, mock_client: AsyncMock) -> None:
        """Test creating job with range values like 1-5."""
        mock_client.call.side_effect = [14, []]

        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            weekdays="1-5",  # Monday to Friday
            safe_mode=True,
        )

        assert result.success

    async def test_create_cron_job_with_list(self, mock_client: AsyncMock) -> None:
        """Test creating job with list values like 1,3,5."""
        mock_client.call.side_effect = [14, []]

        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            hours="9,12,18",
            safe_mode=True,
        )

        assert result.success

    async def test_create_cron_job_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during creation."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "CREATE_CRON_ERROR"


class TestEditCronJob:
    """Tests for edit_cron_job tool."""

    async def test_edit_cron_job_success(self, mock_client: AsyncMock) -> None:
        """Test successfully editing a cron job."""
        mock_client.call.side_effect = [
            [  # list_cron_jobs
                {
                    "index": 5,
                    "command": "/bin/echo test",
                    "user": "root",
                    "mins": "30",
                    "hours": "2",
                    "days": "*",
                    "months": "*",
                    "weekdays": "*",
                    "active": 1,
                    "file": "/var/spool/cron/crontabs/root",
                }
            ],
            1,  # change_cron_job returns 1
        ]

        result = await cron.edit_cron_job(
            mock_client,
            index=5,
            minutes="45",
            hours="3",
            safe_mode=True,
        )

        assert result.success
        assert result.data["action"] == "edit"
        assert result.data["job"]["schedule"] == "45 3 * * *"
        assert result.data["changes"]["schedule"] is True

    async def test_edit_cron_job_not_found(self, mock_client: AsyncMock) -> None:
        """Test editing a job that doesn't exist."""
        mock_client.call.return_value = []  # No jobs

        result = await cron.edit_cron_job(
            mock_client,
            index=999,
            minutes="45",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "JOB_NOT_FOUND"

    async def test_edit_cron_job_change_command(self, mock_client: AsyncMock) -> None:
        """Test changing just the command."""
        mock_client.call.side_effect = [
            [{"index": 5, "command": "/bin/echo old", "user": "root", "mins": "*", "hours": "*", "days": "*", "months": "*", "weekdays": "*", "active": 1, "file": "/tmp/cron"}],
            1,
        ]

        result = await cron.edit_cron_job(
            mock_client,
            index=5,
            command="/bin/echo new",
            safe_mode=True,
        )

        assert result.success
        assert result.data["changes"]["command"] is True
        assert result.data["changes"]["schedule"] is False

    async def test_edit_cron_job_empty_command_rejected(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that empty command is rejected."""
        mock_client.call.return_value = [
            {"index": 5, "command": "/bin/echo test", "user": "root", "mins": "*", "hours": "*", "days": "*", "months": "*", "weekdays": "*", "active": 1, "file": "/tmp/cron"}
        ]

        result = await cron.edit_cron_job(
            mock_client,
            index=5,
            command="",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_ARGUMENT"

    async def test_edit_cron_job_invalid_schedule(self, mock_client: AsyncMock) -> None:
        """Test that invalid schedule is rejected."""
        mock_client.call.return_value = [
            {"index": 5, "command": "/bin/echo test", "user": "root", "mins": "*", "hours": "*", "days": "*", "months": "*", "weekdays": "*", "active": 1, "file": "/tmp/cron"}
        ]

        result = await cron.edit_cron_job(
            mock_client,
            index=5,
            minutes="99",  # Invalid
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_SCHEDULE"

    async def test_edit_cron_job_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during edit."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await cron.edit_cron_job(
            mock_client,
            index=5,
            minutes="30",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "EDIT_CRON_ERROR"


class TestDeleteCronJob:
    """Tests for delete_cron_job tool."""

    async def test_delete_cron_job_blocked_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that deletion is blocked in safe mode."""
        result = await cron.delete_cron_job(mock_client, index=5, safe_mode=True)

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_delete_cron_job_success(self, mock_client: AsyncMock) -> None:
        """Test successfully deleting a cron job."""
        mock_client.call.side_effect = [
            [  # list_cron_jobs before
                {
                    "index": 5,
                    "command": "/bin/echo test",
                    "user": "root",
                    "file": "/var/spool/cron/crontabs/root",
                }
            ],
            None,  # delete_cron_job
            [],  # list_cron_jobs after
        ]

        result = await cron.delete_cron_job(mock_client, index=5, safe_mode=False)

        assert result.success
        assert result.data["action"] == "delete"
        assert result.data["deleted_job"]["index"] == 5
        assert result.data["jobs_before"] == 1
        assert result.data["jobs_after"] == 0

    async def test_delete_cron_job_not_found(self, mock_client: AsyncMock) -> None:
        """Test deleting a job that doesn't exist."""
        mock_client.call.return_value = []  # No jobs

        result = await cron.delete_cron_job(mock_client, index=999, safe_mode=False)

        assert not result.success
        assert result.error.code == "JOB_NOT_FOUND"

    async def test_delete_cron_job_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during deletion."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await cron.delete_cron_job(mock_client, index=5, safe_mode=False)

        assert not result.success
        assert result.error.code == "DELETE_CRON_ERROR"


class TestScheduleValidation:
    """Tests for cron schedule validation."""

    async def test_valid_wildcard(self, mock_client: AsyncMock) -> None:
        """Test that * is valid."""
        mock_client.call.side_effect = [14, []]

        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            minutes="*",
            hours="*",
            days="*",
            months="*",
            weekdays="*",
            safe_mode=True,
        )

        assert result.success

    async def test_valid_step_value(self, mock_client: AsyncMock) -> None:
        """Test that */N is valid."""
        mock_client.call.side_effect = [14, []]

        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            minutes="*/15",
            safe_mode=True,
        )

        assert result.success

    async def test_invalid_step_zero(self, mock_client: AsyncMock) -> None:
        """Test that */0 is invalid."""
        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            minutes="*/0",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_SCHEDULE"

    async def test_invalid_range_reversed(self, mock_client: AsyncMock) -> None:
        """Test that 10-5 is invalid."""
        result = await cron.create_cron_job(
            mock_client,
            command="/bin/echo test",
            hours="10-5",  # End < Start
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_SCHEDULE"

    async def test_valid_complex_schedule(self, mock_client: AsyncMock) -> None:
        """Test complex but valid schedule."""
        mock_client.call.side_effect = [14, []]

        result = await cron.create_cron_job(
            mock_client,
            command="/bin/backup.sh",
            minutes="0",
            hours="2",
            days="1,15",  # 1st and 15th
            months="*/3",  # Every 3 months
            weekdays="*",
            safe_mode=True,
        )

        assert result.success
