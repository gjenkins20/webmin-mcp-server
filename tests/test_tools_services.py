"""Tests for Phase 2 service management tools."""

from unittest.mock import AsyncMock

import pytest

from src.tools import services


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestRestartService:
    """Tests for restart_service tool."""

    async def test_restart_service_success(self, mock_client: AsyncMock) -> None:
        """Test successful service restart."""
        # Setup: service is running before and after
        mock_client.call.side_effect = [
            1,  # status_action (running)
            [0, ""],  # restart_action
            1,  # status_action (running)
        ]

        result = await services.restart_service(mock_client, "nginx", safe_mode=True)

        assert result.success
        assert result.data["service"] == "nginx"
        assert result.data["action"] == "restart"
        assert result.data["running"] is True
        assert result.data["status_before"] == "running"
        assert result.data["status_after"] == "running"

    async def test_restart_service_blocked_for_ssh(self, mock_client: AsyncMock) -> None:
        """Test that restarting sshd is blocked in safe mode."""
        result = await services.restart_service(mock_client, "sshd", safe_mode=True)

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        # Ensure no API calls were made
        mock_client.call.assert_not_called()

    async def test_restart_service_allowed_without_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that restarting sshd is allowed without safe mode."""
        mock_client.call.side_effect = [
            1,  # status_action (running)
            [0, ""],  # restart_action
            1,  # status_action (running)
        ]

        result = await services.restart_service(mock_client, "sshd", safe_mode=False)

        assert result.success
        assert result.data["service"] == "sshd"

    async def test_restart_service_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during restart."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await services.restart_service(mock_client, "nginx", safe_mode=True)

        assert not result.success
        assert result.error.code == "RESTART_SERVICE_ERROR"


class TestStartService:
    """Tests for start_service tool."""

    async def test_start_service_success(self, mock_client: AsyncMock) -> None:
        """Test successfully starting a stopped service."""
        mock_client.call.side_effect = [
            0,  # status_action (stopped)
            [0, ""],  # start_action
            1,  # status_action (running)
        ]

        result = await services.start_service(mock_client, "nginx", safe_mode=True)

        assert result.success
        assert result.data["service"] == "nginx"
        assert result.data["action"] == "start"
        assert result.data["running"] is True
        assert result.data["status_before"] == "stopped"
        assert result.data["status_after"] == "running"

    async def test_start_service_already_running(self, mock_client: AsyncMock) -> None:
        """Test starting a service that's already running."""
        mock_client.call.side_effect = [
            1,  # status_action (running)
        ]

        result = await services.start_service(mock_client, "nginx", safe_mode=True)

        assert result.success
        assert result.data["message"] == "Service is already running"
        # Only one call should be made (status check)
        assert mock_client.call.call_count == 1

    async def test_start_service_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during start."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await services.start_service(mock_client, "nginx", safe_mode=True)

        assert not result.success
        assert result.error.code == "START_SERVICE_ERROR"


class TestStopService:
    """Tests for stop_service tool."""

    async def test_stop_service_success(self, mock_client: AsyncMock) -> None:
        """Test successfully stopping a running service."""
        mock_client.call.side_effect = [
            1,  # status_action (running)
            [0, ""],  # stop_action
            0,  # status_action (stopped)
        ]

        result = await services.stop_service(mock_client, "nginx", safe_mode=True)

        assert result.success
        assert result.data["service"] == "nginx"
        assert result.data["action"] == "stop"
        assert result.data["running"] is False
        assert result.data["status_before"] == "running"
        assert result.data["status_after"] == "stopped"

    async def test_stop_service_already_stopped(self, mock_client: AsyncMock) -> None:
        """Test stopping a service that's already stopped."""
        mock_client.call.side_effect = [
            0,  # status_action (stopped)
        ]

        result = await services.stop_service(mock_client, "nginx", safe_mode=True)

        assert result.success
        assert result.data["message"] == "Service is already stopped"
        assert mock_client.call.call_count == 1

    async def test_stop_service_blocked_for_ssh(self, mock_client: AsyncMock) -> None:
        """Test that stopping sshd is always blocked."""
        result = await services.stop_service(mock_client, "sshd", safe_mode=True)

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_stop_service_blocked_for_cron_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that stopping cron is blocked in safe mode."""
        result = await services.stop_service(mock_client, "cron", safe_mode=True)

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_stop_cron_allowed_without_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that stopping cron is allowed without safe mode."""
        mock_client.call.side_effect = [
            1,  # status_action (running)
            [0, ""],  # stop_action
            0,  # status_action (stopped)
        ]

        result = await services.stop_service(mock_client, "cron", safe_mode=False)

        assert result.success

    async def test_stop_service_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during stop."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await services.stop_service(mock_client, "nginx", safe_mode=True)

        assert not result.success
        assert result.error.code == "STOP_SERVICE_ERROR"


class TestEnableService:
    """Tests for enable_service tool."""

    async def test_enable_service_success(self, mock_client: AsyncMock) -> None:
        """Test successfully enabling a service at boot."""
        mock_client.call.side_effect = [
            0,  # action_status (disabled)
            [],  # enable_at_boot
            2,  # action_status (enabled)
        ]

        result = await services.enable_service(mock_client, "nginx", safe_mode=True)

        assert result.success
        assert result.data["service"] == "nginx"
        assert result.data["action"] == "enable"
        assert result.data["enabled_at_boot"] is True
        assert result.data["was_enabled"] is False

    async def test_enable_service_already_enabled(self, mock_client: AsyncMock) -> None:
        """Test enabling a service that's already enabled."""
        mock_client.call.side_effect = [
            2,  # action_status (enabled)
            [],  # enable_at_boot
            2,  # action_status (enabled)
        ]

        result = await services.enable_service(mock_client, "nginx", safe_mode=True)

        assert result.success
        assert result.data["enabled_at_boot"] is True
        assert result.data["was_enabled"] is True

    async def test_enable_service_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during enable."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await services.enable_service(mock_client, "nginx", safe_mode=True)

        assert not result.success
        assert result.error.code == "ENABLE_SERVICE_ERROR"


class TestDisableService:
    """Tests for disable_service tool."""

    async def test_disable_service_success(self, mock_client: AsyncMock) -> None:
        """Test successfully disabling a service at boot."""
        mock_client.call.side_effect = [
            2,  # action_status (enabled)
            0,  # disable_at_boot
            0,  # action_status (disabled)
        ]

        result = await services.disable_service(mock_client, "nginx", safe_mode=True)

        assert result.success
        assert result.data["service"] == "nginx"
        assert result.data["action"] == "disable"
        assert result.data["enabled_at_boot"] is False
        assert result.data["was_enabled"] is True

    async def test_disable_service_blocked_for_ssh(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that disabling sshd is blocked."""
        result = await services.disable_service(mock_client, "sshd", safe_mode=True)

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_disable_service_blocked_for_webmin(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that disabling webmin is blocked."""
        result = await services.disable_service(mock_client, "webmin", safe_mode=True)

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_disable_service_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during disable."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await services.disable_service(mock_client, "nginx", safe_mode=True)

        assert not result.success
        assert result.error.code == "DISABLE_SERVICE_ERROR"
