"""Tests for Phase 1 system tools."""

from unittest.mock import AsyncMock, patch

import pytest

from src.config import WebminConfig
from src.tools import system
from src.webmin_client import WebminClient


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock(spec=WebminClient)
    return client


class TestGetSystemInfo:
    """Tests for get_system_info tool."""

    async def test_get_system_info_success(self, mock_client: AsyncMock) -> None:
        """Test successful system info retrieval."""
        # Setup mock responses
        mock_client.call.side_effect = [
            "2.105",  # webmin::get_webmin_version
            "testhost",  # webmin::get_system_hostname
            ["real_os_type", "Ubuntu Linux", "real_os_version", "24.04"],  # detect_operating_system
            {  # collect_system_info
                "load": [0.5, 0.3, 0.2, 100, "Test CPU", "TestVendor", 1024, 4],
                "mem": [4000000, 2000000, 100000, 500000, 1400000],
                "disk_total": 100000000000,
                "disk_used": 50000000000,
                "disk_free": 50000000000,
                "kernel": {"os": "Linux", "version": "6.1.0", "arch": "x86_64"},
                "procs": 150,
                "poss": [{"name": "pkg1"}, {"name": "pkg2"}],
                "reboot": 0,
            },
        ]

        result = await system.get_system_info(mock_client)

        assert result.success
        assert result.data["hostname"] == "testhost"
        assert result.data["webmin_version"] == "2.105"
        assert result.data["os"]["name"] == "Ubuntu Linux"
        assert result.data["cpu"]["cores"] == 4
        assert result.data["updates_available"] == 2

    async def test_get_system_info_error(self, mock_client: AsyncMock) -> None:
        """Test system info error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await system.get_system_info(mock_client)

        assert not result.success
        assert result.error.code == "SYSTEM_INFO_ERROR"


class TestListServices:
    """Tests for list_services tool."""

    async def test_list_services_success(self, mock_client: AsyncMock) -> None:
        """Test successful service listing."""
        mock_client.call.return_value = [
            "sshd 12345",
            "nginx 12346",
            "cron 12347",
        ]

        result = await system.list_services(mock_client)

        assert result.success
        assert result.data["count"] == 3
        assert result.data["services"][0]["name"] == "sshd"
        assert result.data["services"][1]["name"] == "nginx"

    async def test_list_services_empty(self, mock_client: AsyncMock) -> None:
        """Test empty service list."""
        mock_client.call.return_value = []

        result = await system.list_services(mock_client)

        assert result.success
        assert result.data["count"] == 0


class TestGetServiceStatus:
    """Tests for get_service_status tool."""

    async def test_get_service_status_running(self, mock_client: AsyncMock) -> None:
        """Test service status when running."""
        mock_client.call.return_value = 1  # 1 = running

        result = await system.get_service_status(mock_client, "sshd")

        assert result.success
        assert result.data["service"] == "sshd"
        assert result.data["status"] == "running"
        assert result.data["running"] is True

    async def test_get_service_status_stopped(self, mock_client: AsyncMock) -> None:
        """Test service status when stopped."""
        mock_client.call.return_value = 0  # 0 = stopped

        result = await system.get_service_status(mock_client, "nginx")

        assert result.success
        assert result.data["status"] == "stopped"
        assert result.data["running"] is False


class TestListUsers:
    """Tests for list_users tool."""

    async def test_list_users_success(self, mock_client: AsyncMock) -> None:
        """Test successful user listing."""
        mock_client.call.return_value = [
            {"user": "root", "uid": 0, "gid": 0, "real": "root", "home": "/root", "shell": "/bin/bash"},
            {"user": "testuser", "uid": 1000, "gid": 1000, "real": "Test User", "home": "/home/testuser", "shell": "/bin/bash"},
        ]

        result = await system.list_users(mock_client)

        assert result.success
        assert result.data["total_count"] == 2
        assert result.data["regular_count"] == 1
        assert result.data["system_count"] == 1
        assert result.data["regular_users"][0]["username"] == "testuser"


class TestGetDiskUsage:
    """Tests for get_disk_usage tool."""

    async def test_get_disk_usage_success(self, mock_client: AsyncMock) -> None:
        """Test successful disk usage retrieval."""
        mock_client.call.return_value = {
            "disk_total": 100000000000,
            "disk_used": 50000000000,
            "disk_free": 50000000000,
            "disk_fs": [
                {
                    "dir": "/",
                    "device": "/dev/sda1",
                    "type": "ext4",
                    "total": 100000000000,
                    "used": 50000000000,
                    "free": 50000000000,
                    "used_percent": 50,
                },
            ],
        }

        result = await system.get_disk_usage(mock_client)

        assert result.success
        assert result.data["total_bytes"] == 100000000000
        assert len(result.data["filesystems"]) == 1
        assert result.data["filesystems"][0]["mount_point"] == "/"


class TestGetMemoryUsage:
    """Tests for get_memory_usage tool."""

    async def test_get_memory_usage_success(self, mock_client: AsyncMock) -> None:
        """Test successful memory usage retrieval."""
        mock_client.call.return_value = {
            "mem": [4000000, 2000000, 100000, 500000, 1400000],
        }

        result = await system.get_memory_usage(mock_client)

        assert result.success
        assert result.data["total_kb"] == 4000000
        assert result.data["used_kb"] == 2000000
        assert result.data["used_percent"] == 50.0


class TestListCronJobs:
    """Tests for list_cron_jobs tool."""

    async def test_list_cron_jobs_success(self, mock_client: AsyncMock) -> None:
        """Test successful cron job listing."""
        mock_client.call.return_value = [
            {
                "user": "root",
                "command": "/usr/bin/backup.sh",
                "mins": "0",
                "hours": "2",
                "days": "*",
                "months": "*",
                "weekdays": "*",
                "active": 1,
                "file": "/etc/crontab",
                "index": 0,
            },
        ]

        result = await system.list_cron_jobs(mock_client)

        assert result.success
        assert result.data["count"] == 1
        assert result.data["jobs"][0]["user"] == "root"
        assert result.data["jobs"][0]["schedule"] == "0 2 * * *"
        assert result.data["jobs"][0]["active"] is True


class TestGetNetworkInfo:
    """Tests for get_network_info tool."""

    async def test_get_network_info_success(self, mock_client: AsyncMock) -> None:
        """Test successful network info retrieval."""
        mock_client.call.side_effect = [
            [  # active_interfaces
                {
                    "name": "eth0",
                    "fullname": "eth0",
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "broadcast": "192.168.1.255",
                    "ether": "00:11:22:33:44:55",
                    "mtu": 1500,
                    "up": 1,
                },
            ],
            [  # list_routes
                {
                    "dest": "0.0.0.0",
                    "gateway": "192.168.1.1",
                    "netmask": "0.0.0.0",
                    "iface": "eth0",
                },
            ],
        ]

        result = await system.get_network_info(mock_client)

        assert result.success
        assert result.data["interface_count"] == 1
        assert result.data["interfaces"][0]["address"] == "192.168.1.100"
        assert result.data["default_gateway"] == "192.168.1.1"
