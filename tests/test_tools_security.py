"""Tests for Phase 6 security tools (Fail2ban)."""

from unittest.mock import AsyncMock

import pytest

from src.tools import security


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestListFail2banJails:
    """Tests for list_fail2ban_jails tool."""

    async def test_list_jails_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing jails."""
        mock_client.call.return_value = [
            {
                "name": "sshd",
                "enabled": 1,
                "filter": "sshd",
                "action": "iptables-multiport",
                "logpath": "/var/log/auth.log",
                "maxretry": 5,
                "findtime": 600,
                "bantime": 3600,
                "banned": 3,
                "total_banned": 150,
            },
            {
                "name": "nginx-http-auth",
                "enabled": 1,
                "filter": "nginx-http-auth",
                "action": "iptables-multiport",
                "logpath": "/var/log/nginx/error.log",
                "maxretry": 3,
                "findtime": 300,
                "bantime": 7200,
                "banned": 0,
                "total_banned": 25,
            },
        ]

        result = await security.list_fail2ban_jails(mock_client)

        assert result.success
        assert result.data["count"] == 2
        jail = result.data["jails"][0]
        assert jail["name"] == "sshd"
        assert jail["enabled"] is True
        assert jail["maxretry"] == 5
        assert jail["currently_banned"] == 3

    async def test_list_jails_simple_names(self, mock_client: AsyncMock) -> None:
        """Test handling simple list of jail names."""
        mock_client.call.return_value = ["sshd", "nginx", "postfix"]

        result = await security.list_fail2ban_jails(mock_client)

        assert result.success
        assert result.data["count"] == 3
        assert result.data["jails"][0]["name"] == "sshd"
        assert result.data["jails"][0]["enabled"] is None

    async def test_list_jails_empty(self, mock_client: AsyncMock) -> None:
        """Test handling no jails."""
        mock_client.call.return_value = []

        result = await security.list_fail2ban_jails(mock_client)

        assert result.success
        assert result.data["count"] == 0

    async def test_list_jails_disabled(self, mock_client: AsyncMock) -> None:
        """Test handling disabled jail."""
        mock_client.call.return_value = [
            {"name": "sshd", "enabled": 0},
        ]

        result = await security.list_fail2ban_jails(mock_client)

        assert result.success
        assert result.data["jails"][0]["enabled"] is False

    async def test_list_jails_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await security.list_fail2ban_jails(mock_client)

        assert not result.success
        assert result.error.code == "LIST_JAILS_ERROR"


class TestGetFail2banStatus:
    """Tests for get_fail2ban_status tool."""

    async def test_get_status_overall(self, mock_client: AsyncMock) -> None:
        """Test getting overall status."""
        mock_client.call.side_effect = [
            True,  # is_fail2ban_running
            [  # list_jails
                {"name": "sshd", "banned": 3},
                {"name": "nginx", "banned": 2},
            ],
        ]

        result = await security.get_fail2ban_status(mock_client)

        assert result.success
        assert result.data["running"] is True
        assert result.data["jail_count"] == 2
        assert result.data["total_currently_banned"] == 5

    async def test_get_status_specific_jail(self, mock_client: AsyncMock) -> None:
        """Test getting jail-specific status."""
        mock_client.call.side_effect = [
            True,  # is_fail2ban_running
            [{"name": "sshd", "enabled": 1, "banned": 3, "total_banned": 50}],  # list_jails
        ]

        result = await security.get_fail2ban_status(mock_client, jail="sshd")

        assert result.success
        assert result.data["jail"] == "sshd"
        assert result.data["running"] is True
        assert result.data["currently_banned"] == 3

    async def test_get_status_jail_not_found(self, mock_client: AsyncMock) -> None:
        """Test when specified jail is not found."""
        mock_client.call.side_effect = [
            True,  # is_fail2ban_running
            [{"name": "sshd", "banned": 3}],  # list_jails - no nginx
        ]

        result = await security.get_fail2ban_status(mock_client, jail="nginx")

        assert result.success
        assert result.data["jail"] == "nginx"
        assert result.data["found"] is False

    async def test_get_status_not_running(self, mock_client: AsyncMock) -> None:
        """Test handling when fail2ban is not running."""
        mock_client.call.side_effect = [
            "",  # is_fail2ban_running returns empty string
            [],  # list_jails
        ]

        result = await security.get_fail2ban_status(mock_client)

        assert result.success
        assert result.data["running"] is False

    async def test_get_status_not_installed(self, mock_client: AsyncMock) -> None:
        """Test handling when fail2ban is not installed."""
        mock_client.call.side_effect = Exception("config directory does not exist")

        result = await security.get_fail2ban_status(mock_client)

        assert result.success
        assert result.data["installed"] is False

    async def test_get_status_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await security.get_fail2ban_status(mock_client)

        assert not result.success
        assert result.error.code == "FAIL2BAN_STATUS_ERROR"


class TestListBannedIps:
    """Tests for list_banned_ips tool."""

    async def test_list_banned_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing banned IPs from jail info."""
        mock_client.call.return_value = [
            {
                "name": "sshd",
                "banned_ips": [
                    {"ip": "192.168.1.100", "time": 1708091445},
                    {"ip": "10.0.0.50", "time": 1708091500},
                ],
            },
        ]

        result = await security.list_banned_ips(mock_client)

        assert result.success
        assert result.data["count"] == 2
        assert result.data["banned_ips"][0]["ip"] == "192.168.1.100"
        assert result.data["banned_ips"][0]["jail"] == "sshd"

    async def test_list_banned_with_jail_filter(self, mock_client: AsyncMock) -> None:
        """Test filtering by jail."""
        mock_client.call.return_value = [
            {"name": "sshd", "banned_ips": ["192.168.1.100"]},
            {"name": "nginx", "banned_ips": ["10.0.0.1"]},
        ]

        result = await security.list_banned_ips(mock_client, jail="sshd")

        assert result.success
        assert result.data["jail_filter"] == "sshd"
        assert result.data["count"] == 1
        assert result.data["banned_ips"][0]["jail"] == "sshd"

    async def test_list_banned_simple_ip_list(self, mock_client: AsyncMock) -> None:
        """Test handling simple list of IPs in jail info."""
        mock_client.call.return_value = [
            {"name": "sshd", "banned_ips": ["192.168.1.100", "10.0.0.50"]},
        ]

        result = await security.list_banned_ips(mock_client)

        assert result.success
        assert result.data["count"] == 2

    async def test_list_banned_string_ips(self, mock_client: AsyncMock) -> None:
        """Test handling space-separated IPs in jail info."""
        mock_client.call.return_value = [
            {"name": "sshd", "banned_ips": "192.168.1.100 10.0.0.50"},
        ]

        result = await security.list_banned_ips(mock_client)

        assert result.success
        assert result.data["count"] == 2

    async def test_list_banned_empty(self, mock_client: AsyncMock) -> None:
        """Test handling no banned IPs."""
        mock_client.call.return_value = []

        result = await security.list_banned_ips(mock_client)

        assert result.success
        assert result.data["count"] == 0

    async def test_list_banned_not_installed(self, mock_client: AsyncMock) -> None:
        """Test handling when fail2ban is not installed."""
        mock_client.call.side_effect = Exception("config does not exist")

        result = await security.list_banned_ips(mock_client)

        assert result.success
        assert result.data["count"] == 0
        assert "message" in result.data

    async def test_list_banned_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await security.list_banned_ips(mock_client)

        assert not result.success
        assert result.error.code == "LIST_BANNED_ERROR"
