"""Tests for Phase 5 storage management tools."""

from unittest.mock import AsyncMock

import pytest

from src.tools import storage


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestListDisks:
    """Tests for list_disks tool."""

    async def test_list_disks_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing disks."""
        mock_client.call.return_value = [
            {
                "device": "/dev/sda",
                "model": "Samsung SSD 870",
                "serial": "S5XXNX0T123456",
                "capacity": "500GB",
                "smart": 1,
                "type": "sata",
            },
            {
                "device": "/dev/nvme0n1",
                "model": "Samsung 980 PRO",
                "serial": "S6XXNX0T789012",
                "capacity": "1TB",
                "smart": 1,
                "type": "nvme",
            },
        ]

        result = await storage.list_disks(mock_client)

        assert result.success
        assert result.data["count"] == 2
        assert len(result.data["disks"]) == 2

        disk1 = result.data["disks"][0]
        assert disk1["device"] == "/dev/sda"
        assert disk1["model"] == "Samsung SSD 870"
        assert disk1["serial"] == "S5XXNX0T123456"
        assert disk1["smart_enabled"] is True

        disk2 = result.data["disks"][1]
        assert disk2["device"] == "/dev/nvme0n1"
        assert disk2["type"] == "nvme"

    async def test_list_disks_empty(self, mock_client: AsyncMock) -> None:
        """Test handling when no disks found."""
        mock_client.call.return_value = []

        result = await storage.list_disks(mock_client)

        assert result.success
        assert result.data["count"] == 0
        assert result.data["disks"] == []

    async def test_list_disks_smart_disabled(self, mock_client: AsyncMock) -> None:
        """Test handling of disks with SMART disabled."""
        mock_client.call.return_value = [
            {
                "device": "/dev/sdb",
                "model": "Old Disk",
                "smart": 0,
            },
        ]

        result = await storage.list_disks(mock_client)

        assert result.success
        assert result.data["disks"][0]["smart_enabled"] is False

    async def test_list_disks_partial_data(self, mock_client: AsyncMock) -> None:
        """Test handling of disks with partial data."""
        mock_client.call.return_value = [
            {
                "device": "/dev/sda",
                # Missing model, serial, etc.
            },
        ]

        result = await storage.list_disks(mock_client)

        assert result.success
        disk = result.data["disks"][0]
        assert disk["device"] == "/dev/sda"
        assert disk["model"] is None
        assert disk["serial"] is None

    async def test_list_disks_non_dict_items(self, mock_client: AsyncMock) -> None:
        """Test handling of non-dict items in response."""
        mock_client.call.return_value = [
            {"device": "/dev/sda", "model": "Good Disk"},
            "invalid item",
            123,
        ]

        result = await storage.list_disks(mock_client)

        assert result.success
        assert result.data["count"] == 1
        assert result.data["disks"][0]["device"] == "/dev/sda"

    async def test_list_disks_non_list_response(self, mock_client: AsyncMock) -> None:
        """Test handling of non-list response."""
        mock_client.call.return_value = "not a list"

        result = await storage.list_disks(mock_client)

        assert result.success
        assert result.data["count"] == 0
        assert result.data["disks"] == []

    async def test_list_disks_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during disk listing."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await storage.list_disks(mock_client)

        assert not result.success
        assert result.error.code == "LIST_DISKS_ERROR"
        assert "Connection failed" in result.error.message


class TestGetDiskHealth:
    """Tests for get_disk_health tool."""

    async def test_get_disk_health_success(self, mock_client: AsyncMock) -> None:
        """Test successfully getting disk health."""
        mock_client.call.return_value = {
            "health": "PASSED",
            "model": "Samsung SSD 870",
            "serial": "S5XXNX0T123456",
            "firmware": "SVT04B6Q",
            "capacity": "500GB",
            "temp": 35,
            "power_on": 1234,
            "power_cycles": 567,
            "attrs": [
                {
                    "id": 5,
                    "name": "Reallocated_Sector_Ct",
                    "value": 100,
                    "worst": 100,
                    "thresh": 10,
                    "raw": 0,
                    "type": "pre-fail",
                    "failed": False,
                },
                {
                    "id": 194,
                    "name": "Temperature_Celsius",
                    "value": 65,
                    "worst": 50,
                    "thresh": 0,
                    "raw": 35,
                    "type": "old-age",
                    "failed": False,
                },
            ],
            "errors": [],
        }

        result = await storage.get_disk_health(mock_client, "/dev/sda")

        assert result.success
        assert result.data["device"] == "/dev/sda"
        assert result.data["health"] == "PASSED"
        assert result.data["healthy"] is True
        assert result.data["model"] == "Samsung SSD 870"
        assert result.data["temperature"] == 35
        assert result.data["power_on_hours"] == 1234
        assert result.data["power_cycles"] == 567
        assert len(result.data["attributes"]) == 2
        assert result.data["failed_attributes"] == []
        assert result.data["error_count"] == 0

    async def test_get_disk_health_with_failed_attributes(
        self, mock_client: AsyncMock
    ) -> None:
        """Test disk health with failing attributes."""
        mock_client.call.return_value = {
            "health": "FAILED",
            "model": "Failing Disk",
            "attrs": [
                {
                    "id": 5,
                    "name": "Reallocated_Sector_Ct",
                    "value": 5,
                    "worst": 5,
                    "thresh": 10,
                    "raw": 100,
                    "type": "pre-fail",
                    "failed": True,
                },
            ],
            "errors": ["Disk self-test failed"],
        }

        result = await storage.get_disk_health(mock_client, "/dev/sda")

        assert result.success
        assert result.data["health"] == "FAILED"
        assert result.data["healthy"] is False
        assert len(result.data["failed_attributes"]) == 1
        assert result.data["failed_attributes"][0]["name"] == "Reallocated_Sector_Ct"
        assert result.data["error_count"] == 1
        assert "Disk self-test failed" in result.data["errors"]

    async def test_get_disk_health_various_health_statuses(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that various health statuses are correctly interpreted."""
        test_cases = [
            ("PASSED", True),
            ("passed", True),
            ("OK", True),
            ("ok", True),
            ("GOOD", True),
            ("good", True),
            ("FAILED", False),
            ("failed", False),
            ("WARNING", False),
            ("UNKNOWN", False),
        ]

        for health_status, expected_healthy in test_cases:
            mock_client.call.return_value = {
                "health": health_status,
                "attrs": [],
                "errors": [],
            }

            result = await storage.get_disk_health(mock_client, "/dev/sda")

            assert result.success, f"Failed for health status: {health_status}"
            assert result.data["healthy"] == expected_healthy, (
                f"Expected healthy={expected_healthy} for status '{health_status}'"
            )

    async def test_get_disk_health_empty_attributes(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of empty attributes list."""
        mock_client.call.return_value = {
            "health": "PASSED",
            "attrs": [],
            "errors": [],
        }

        result = await storage.get_disk_health(mock_client, "/dev/sda")

        assert result.success
        assert result.data["attributes"] == []

    async def test_get_disk_health_missing_fields(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of missing optional fields."""
        mock_client.call.return_value = {
            "health": "PASSED",
            # Missing most fields
        }

        result = await storage.get_disk_health(mock_client, "/dev/sda")

        assert result.success
        assert result.data["device"] == "/dev/sda"
        assert result.data["model"] is None
        assert result.data["temperature"] is None
        assert result.data["attributes"] == []

    async def test_get_disk_health_invalid_response(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of invalid response format."""
        mock_client.call.return_value = "not a dict"

        result = await storage.get_disk_health(mock_client, "/dev/sda")

        assert not result.success
        assert result.error.code == "INVALID_RESPONSE"

    async def test_get_disk_health_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during health check."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await storage.get_disk_health(mock_client, "/dev/sda")

        assert not result.success
        assert result.error.code == "DISK_HEALTH_ERROR"
        assert "/dev/sda" in result.error.message


class TestListVolumeGroups:
    """Tests for list_volume_groups tool."""

    async def test_list_volume_groups_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing volume groups."""
        mock_client.call.return_value = [
            {
                "name": "vg_data",
                "size": 107374182400,  # 100GB in bytes
                "free": 53687091200,  # 50GB in bytes
                "pvs": 2,
                "lvs": 3,
                "pe_size": 4194304,  # 4MB
                "pe_total": 25600,
                "pe_free": 12800,
            },
            {
                "name": "vg_system",
                "size": 53687091200,  # 50GB
                "free": 10737418240,  # 10GB
                "pvs": 1,
                "lvs": 2,
                "pe_size": 4194304,
                "pe_total": 12800,
                "pe_free": 2560,
            },
        ]

        result = await storage.list_volume_groups(mock_client)

        assert result.success
        assert result.data["count"] == 2

        vg1 = result.data["volume_groups"][0]
        assert vg1["name"] == "vg_data"
        assert vg1["size_bytes"] == 107374182400
        assert vg1["size_mb"] == 102400.0
        assert vg1["free_bytes"] == 53687091200
        assert vg1["pv_count"] == 2
        assert vg1["lv_count"] == 3

        vg2 = result.data["volume_groups"][1]
        assert vg2["name"] == "vg_system"

    async def test_list_volume_groups_empty(self, mock_client: AsyncMock) -> None:
        """Test handling when no volume groups exist."""
        mock_client.call.return_value = []

        result = await storage.list_volume_groups(mock_client)

        assert result.success
        assert result.data["count"] == 0
        assert result.data["volume_groups"] == []

    async def test_list_volume_groups_partial_data(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of volume groups with partial data."""
        mock_client.call.return_value = [
            {
                "name": "vg_minimal",
                # Missing size, free, etc.
            },
        ]

        result = await storage.list_volume_groups(mock_client)

        assert result.success
        vg = result.data["volume_groups"][0]
        assert vg["name"] == "vg_minimal"
        assert vg["size_bytes"] is None
        assert vg["size_mb"] is None

    async def test_list_volume_groups_non_dict_items(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of non-dict items in response."""
        mock_client.call.return_value = [
            {"name": "vg_good"},
            "invalid",
            123,
        ]

        result = await storage.list_volume_groups(mock_client)

        assert result.success
        assert result.data["count"] == 1

    async def test_list_volume_groups_non_list_response(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of non-list response."""
        mock_client.call.return_value = "not a list"

        result = await storage.list_volume_groups(mock_client)

        assert result.success
        assert result.data["count"] == 0

    async def test_list_volume_groups_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during VG listing."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await storage.list_volume_groups(mock_client)

        assert not result.success
        assert result.error.code == "LIST_VGS_ERROR"


class TestListLogicalVolumes:
    """Tests for list_logical_volumes tool."""

    async def test_list_logical_volumes_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing logical volumes."""
        mock_client.call.return_value = [
            {
                "name": "lv_root",
                "vg": "vg_system",
                "size": 21474836480,  # 20GB
                "device": "/dev/vg_system/lv_root",
                "active": 1,
                "mount": "/",
                "stripes": 1,
                "stripesize": None,
            },
            {
                "name": "lv_home",
                "vg": "vg_data",
                "size": 53687091200,  # 50GB
                "device": "/dev/vg_data/lv_home",
                "active": 1,
                "mount": "/home",
                "stripes": 2,
                "stripesize": 65536,
            },
        ]

        result = await storage.list_logical_volumes(mock_client)

        assert result.success
        assert result.data["count"] == 2
        assert result.data["volume_group"] is None

        lv1 = result.data["logical_volumes"][0]
        assert lv1["name"] == "lv_root"
        assert lv1["volume_group"] == "vg_system"
        assert lv1["size_bytes"] == 21474836480
        assert lv1["size_mb"] == 20480.0
        assert lv1["device"] == "/dev/vg_system/lv_root"
        assert lv1["active"] is True
        assert lv1["mounted"] == "/"

        lv2 = result.data["logical_volumes"][1]
        assert lv2["stripes"] == 2

    async def test_list_logical_volumes_filter_by_vg(
        self, mock_client: AsyncMock
    ) -> None:
        """Test filtering logical volumes by volume group."""
        mock_client.call.return_value = [
            {"name": "lv_root", "vg": "vg_system", "size": 20000000000},
            {"name": "lv_home", "vg": "vg_data", "size": 50000000000},
            {"name": "lv_var", "vg": "vg_system", "size": 10000000000},
        ]

        result = await storage.list_logical_volumes(mock_client, volume_group="vg_system")

        assert result.success
        assert result.data["count"] == 2
        assert result.data["volume_group"] == "vg_system"
        assert all(
            lv["volume_group"] == "vg_system" for lv in result.data["logical_volumes"]
        )

    async def test_list_logical_volumes_filter_no_match(
        self, mock_client: AsyncMock
    ) -> None:
        """Test filtering when no LVs match the VG."""
        mock_client.call.return_value = [
            {"name": "lv_root", "vg": "vg_system"},
        ]

        result = await storage.list_logical_volumes(
            mock_client, volume_group="vg_nonexistent"
        )

        assert result.success
        assert result.data["count"] == 0
        assert result.data["logical_volumes"] == []

    async def test_list_logical_volumes_empty(self, mock_client: AsyncMock) -> None:
        """Test handling when no logical volumes exist."""
        mock_client.call.return_value = []

        result = await storage.list_logical_volumes(mock_client)

        assert result.success
        assert result.data["count"] == 0
        assert result.data["logical_volumes"] == []

    async def test_list_logical_volumes_inactive(self, mock_client: AsyncMock) -> None:
        """Test handling of inactive logical volumes."""
        mock_client.call.return_value = [
            {
                "name": "lv_inactive",
                "vg": "vg_system",
                "active": 0,
                "mount": None,
            },
        ]

        result = await storage.list_logical_volumes(mock_client)

        assert result.success
        lv = result.data["logical_volumes"][0]
        assert lv["active"] is False
        assert lv["mounted"] is None

    async def test_list_logical_volumes_partial_data(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of LVs with partial data."""
        mock_client.call.return_value = [
            {
                "name": "lv_minimal",
                "vg": "vg_test",
                # Missing size, device, etc.
            },
        ]

        result = await storage.list_logical_volumes(mock_client)

        assert result.success
        lv = result.data["logical_volumes"][0]
        assert lv["name"] == "lv_minimal"
        assert lv["size_bytes"] is None
        assert lv["device"] is None

    async def test_list_logical_volumes_non_list_response(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of non-list response."""
        mock_client.call.return_value = "not a list"

        result = await storage.list_logical_volumes(mock_client)

        assert result.success
        assert result.data["count"] == 0

    async def test_list_logical_volumes_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during LV listing."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await storage.list_logical_volumes(mock_client)

        assert not result.success
        assert result.error.code == "LIST_LVS_ERROR"


class TestBytesToMb:
    """Tests for _bytes_to_mb helper function."""

    def test_bytes_to_mb_valid(self) -> None:
        """Test valid byte to MB conversion."""
        assert storage._bytes_to_mb(1048576) == 1.0  # 1MB
        assert storage._bytes_to_mb(104857600) == 100.0  # 100MB
        assert storage._bytes_to_mb(1073741824) == 1024.0  # 1GB

    def test_bytes_to_mb_zero(self) -> None:
        """Test zero bytes."""
        assert storage._bytes_to_mb(0) == 0.0

    def test_bytes_to_mb_none(self) -> None:
        """Test None input."""
        assert storage._bytes_to_mb(None) is None

    def test_bytes_to_mb_string(self) -> None:
        """Test string input that can be converted."""
        assert storage._bytes_to_mb("1048576") == 1.0

    def test_bytes_to_mb_invalid_string(self) -> None:
        """Test invalid string input."""
        assert storage._bytes_to_mb("not a number") is None

    def test_bytes_to_mb_float(self) -> None:
        """Test float input."""
        result = storage._bytes_to_mb(1048576.5)
        assert result is not None
        assert abs(result - 1.0) < 0.01
