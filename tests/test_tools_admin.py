"""Tests for Phase 6 system administration tools."""

from unittest.mock import AsyncMock

import pytest

from src.tools import admin


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestGetSystemTime:
    """Tests for get_system_time tool."""

    async def test_get_system_time_dict_response(self, mock_client: AsyncMock) -> None:
        """Test handling dict response."""
        mock_client.call.return_value = {
            "timezone": "America/New_York",
            "timezone_name": "EST",
            "year": 2026,
            "month": 2,
            "day": 16,
            "hour": 10,
            "min": 30,
            "sec": 45,
            "dow": 1,
            "hardware": "UTC",
        }

        result = await admin.get_system_time(mock_client)

        assert result.success
        assert result.data["timezone"] == "America/New_York"
        assert result.data["year"] == 2026
        assert result.data["month"] == 2
        assert result.data["day"] == 16
        assert result.data["hour"] == 10
        assert result.data["minute"] == 30
        assert result.data["second"] == 45

    async def test_get_system_time_list_response(self, mock_client: AsyncMock) -> None:
        """Test handling list response (Perl localtime format)."""
        # Perl localtime returns: [sec, min, hour, mday, mon, year, wday, yday, isdst]
        # year is years since 1900, month is 0-indexed
        mock_client.call.return_value = [45, 30, 10, 16, 1, 126, 1, 46, 0]

        result = await admin.get_system_time(mock_client)

        assert result.success
        assert result.data["second"] == 45
        assert result.data["minute"] == 30
        assert result.data["hour"] == 10
        assert result.data["day"] == 16
        assert result.data["month"] == 2  # 1 + 1 = 2 (February)
        assert result.data["year"] == 2026  # 126 + 1900 = 2026

    async def test_get_system_time_other_response(self, mock_client: AsyncMock) -> None:
        """Test handling unexpected response type."""
        mock_client.call.return_value = "1708091445"

        result = await admin.get_system_time(mock_client)

        assert result.success
        assert "raw" in result.data

    async def test_get_system_time_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await admin.get_system_time(mock_client)

        assert not result.success
        assert result.error.code == "SYSTEM_TIME_ERROR"


class TestListRunlevels:
    """Tests for list_runlevels tool."""

    async def test_list_runlevels_dict_items(self, mock_client: AsyncMock) -> None:
        """Test handling dict items."""
        mock_client.call.return_value = [
            {"level": "0", "name": "halt", "desc": "System halt"},
            {"level": "1", "name": "single", "desc": "Single user mode"},
            {"level": "3", "name": "multi", "desc": "Multi-user mode"},
            {"level": "5", "name": "graphical", "desc": "Graphical mode"},
            {"level": "6", "name": "reboot", "desc": "System reboot"},
        ]

        result = await admin.list_runlevels(mock_client)

        assert result.success
        assert result.data["count"] == 5
        assert result.data["runlevels"][0]["level"] == "0"
        assert result.data["runlevels"][0]["name"] == "halt"

    async def test_list_runlevels_simple_list(self, mock_client: AsyncMock) -> None:
        """Test handling simple list of runlevels."""
        mock_client.call.return_value = ["0", "1", "2", "3", "4", "5", "6"]

        result = await admin.list_runlevels(mock_client)

        assert result.success
        assert result.data["count"] == 7
        assert result.data["runlevels"][0]["level"] == "0"

    async def test_list_runlevels_empty(self, mock_client: AsyncMock) -> None:
        """Test handling empty response."""
        mock_client.call.return_value = []

        result = await admin.list_runlevels(mock_client)

        assert result.success
        assert result.data["count"] == 0

    async def test_list_runlevels_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await admin.list_runlevels(mock_client)

        assert not result.success
        assert result.error.code == "LIST_RUNLEVELS_ERROR"


class TestGetSshConfig:
    """Tests for get_ssh_config tool."""

    async def test_get_ssh_config_success(self, mock_client: AsyncMock) -> None:
        """Test successfully getting SSH config."""
        mock_client.call.return_value = {
            "Port": "22",
            "PermitRootLogin": "no",
            "PasswordAuthentication": "yes",
            "PubkeyAuthentication": "yes",
            "X11Forwarding": "no",
            "MaxAuthTries": "3",
            "UsePAM": "yes",
            "file": "/etc/ssh/sshd_config",
        }

        result = await admin.get_ssh_config(mock_client)

        assert result.success
        assert result.data["settings"]["port"] == "22"
        assert result.data["settings"]["permit_root_login"] == "no"
        assert result.data["settings"]["password_authentication"] == "yes"

    async def test_get_ssh_config_lowercase_keys(self, mock_client: AsyncMock) -> None:
        """Test handling lowercase config keys."""
        mock_client.call.return_value = {
            "port": "2222",
            "permit_root_login": "yes",
        }

        result = await admin.get_ssh_config(mock_client)

        assert result.success
        assert result.data["settings"]["port"] == "2222"

    async def test_get_ssh_config_non_dict(self, mock_client: AsyncMock) -> None:
        """Test handling non-dict response."""
        mock_client.call.return_value = "config data"

        result = await admin.get_ssh_config(mock_client)

        assert result.success
        assert "raw" in result.data

    async def test_get_ssh_config_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await admin.get_ssh_config(mock_client)

        assert not result.success
        assert result.error.code == "SSH_CONFIG_ERROR"


class TestListWebminLogs:
    """Tests for list_webmin_logs tool."""

    async def test_list_webmin_logs_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing logs."""
        mock_client.call.return_value = [
            {
                "id": 1,
                "time": 1708091445,
                "user": "admin",
                "module": "useradmin",
                "script": "save_user.cgi",
                "desc": "Created user testuser",
                "ip": "192.168.1.100",
                "sid": "abc123",
            },
            {
                "id": 2,
                "time": 1708091500,
                "user": "admin",
                "module": "init",
                "script": "restart.cgi",
                "desc": "Restarted nginx",
                "ip": "192.168.1.100",
                "sid": "abc123",
            },
        ]

        result = await admin.list_webmin_logs(mock_client)

        assert result.success
        assert result.data["count"] == 2
        assert result.data["logs"][0]["user"] == "admin"
        assert result.data["logs"][0]["module"] == "useradmin"

    async def test_list_webmin_logs_with_module_filter(
        self, mock_client: AsyncMock
    ) -> None:
        """Test filtering by module."""
        mock_client.call.return_value = [
            {"id": 1, "module": "useradmin", "user": "admin"},
            {"id": 2, "module": "init", "user": "admin"},
            {"id": 3, "module": "useradmin", "user": "admin"},
        ]

        result = await admin.list_webmin_logs(mock_client, module="useradmin")

        assert result.success
        assert result.data["count"] == 2
        assert result.data["filter_module"] == "useradmin"
        assert all(log["module"] == "useradmin" for log in result.data["logs"])

    async def test_list_webmin_logs_with_user_filter(
        self, mock_client: AsyncMock
    ) -> None:
        """Test filtering by user."""
        mock_client.call.return_value = [
            {"id": 1, "module": "init", "user": "admin"},
            {"id": 2, "module": "init", "user": "root"},
            {"id": 3, "module": "init", "user": "admin"},
        ]

        result = await admin.list_webmin_logs(mock_client, user="admin")

        assert result.success
        assert result.data["count"] == 2
        assert result.data["filter_user"] == "admin"

    async def test_list_webmin_logs_with_limit(self, mock_client: AsyncMock) -> None:
        """Test applying limit."""
        mock_client.call.return_value = [
            {"id": i, "module": "test", "user": "admin"} for i in range(200)
        ]

        result = await admin.list_webmin_logs(mock_client, limit=50)

        assert result.success
        assert result.data["count"] == 50
        assert result.data["limit"] == 50

    async def test_list_webmin_logs_empty(self, mock_client: AsyncMock) -> None:
        """Test handling empty logs."""
        mock_client.call.return_value = []

        result = await admin.list_webmin_logs(mock_client)

        assert result.success
        assert result.data["count"] == 0

    async def test_list_webmin_logs_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await admin.list_webmin_logs(mock_client)

        assert not result.success
        assert result.error.code == "WEBMIN_LOGS_ERROR"


class TestListBackups:
    """Tests for list_backups tool."""

    async def test_list_backups_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing backups."""
        mock_client.call.return_value = [
            {
                "id": "backup1",
                "file": "/var/webmin/backups/config.tar.gz",
                "dest": "/backups",
                "mods": ["useradmin", "init"],
                "sched": "daily",
                "enabled": 1,
                "email": "admin@example.com",
                "desc": "Daily config backup",
            },
        ]

        result = await admin.list_backups(mock_client)

        assert result.success
        assert result.data["count"] == 1
        backup = result.data["backups"][0]
        assert backup["id"] == "backup1"
        assert backup["enabled"] is True
        assert backup["schedule"] == "daily"

    async def test_list_backups_empty(self, mock_client: AsyncMock) -> None:
        """Test handling no backups."""
        mock_client.call.return_value = []

        result = await admin.list_backups(mock_client)

        assert result.success
        assert result.data["count"] == 0

    async def test_list_backups_disabled(self, mock_client: AsyncMock) -> None:
        """Test handling disabled backup."""
        mock_client.call.return_value = [
            {"id": "backup1", "enabled": 0},
        ]

        result = await admin.list_backups(mock_client)

        assert result.success
        assert result.data["backups"][0]["enabled"] is False

    async def test_list_backups_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await admin.list_backups(mock_client)

        assert not result.success
        assert result.error.code == "LIST_BACKUPS_ERROR"
