"""Tests for Phase 7 disk quota management tools."""

from unittest.mock import AsyncMock

import pytest

from src.tools import quota


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestListQuotaFilesystems:
    """Tests for list_quota_filesystems tool."""

    async def test_list_filesystems_success_arrays(self, mock_client: AsyncMock) -> None:
        """Test listing filesystems returned as arrays."""
        mock_client.call.return_value = [
            ["/", "/dev/sda1", "ext4", "rw", 3, 1],
            ["/home", "/dev/sda2", "ext4", "rw", 3, 1],
            ["/tmp", "/dev/sda3", "ext4", "rw", 0, 0],
        ]

        result = await quota.list_quota_filesystems(mock_client)

        assert result.success
        assert result.data["total_count"] == 3
        assert result.data["quota_capable_count"] == 2
        assert result.data["quota_enabled_count"] == 2
        assert result.data["filesystems"][0]["mount_point"] == "/"
        assert result.data["filesystems"][0]["quota_support"] is True
        assert result.data["filesystems"][0]["quota_enabled"] is True
        assert result.data["filesystems"][2]["quota_support"] is False

    async def test_list_filesystems_success_dicts(self, mock_client: AsyncMock) -> None:
        """Test listing filesystems returned as dicts."""
        mock_client.call.return_value = [
            {"dir": "/", "dev": "/dev/sda1", "type": "ext4", "quota": 1, "active": 1},
        ]

        result = await quota.list_quota_filesystems(mock_client)

        assert result.success
        assert result.data["total_count"] == 1

    async def test_list_filesystems_empty(self, mock_client: AsyncMock) -> None:
        """Test listing when no filesystems exist."""
        mock_client.call.return_value = []

        result = await quota.list_quota_filesystems(mock_client)

        assert result.success
        assert result.data["total_count"] == 0

    async def test_list_filesystems_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await quota.list_quota_filesystems(mock_client)

        assert not result.success
        assert result.error.code == "LIST_QUOTA_FILESYSTEMS_ERROR"


class TestListUserQuotas:
    """Tests for list_user_quotas tool."""

    async def test_list_user_quotas_success(self, mock_client: AsyncMock) -> None:
        """Test listing user quotas on a filesystem."""
        mock_client.call.side_effect = [
            1024,  # block_size
            [
                ["alice", 500, 1000, 2000, 50, 100, 200],
                ["bob", 100, 500, 1000, 10, 50, 100],
            ],  # filesystem_users
        ]

        result = await quota.list_user_quotas(mock_client, "/")

        assert result.success
        assert result.data["filesystem"] == "/"
        assert result.data["count"] == 2
        assert result.data["quotas"][0]["user"] == "alice"
        assert result.data["quotas"][0]["used_blocks"] == 500
        assert result.data["quotas"][0]["soft_block_limit"] == 1000
        assert result.data["quotas"][0]["used_bytes"] == 500 * 1024

    async def test_list_user_quotas_count_only(self, mock_client: AsyncMock) -> None:
        """Test when filesystem_users returns only a count (Perl global hash not serialized)."""
        mock_client.call.side_effect = [
            1024,  # block_size
            5,  # filesystem_users returns just a count
        ]

        result = await quota.list_user_quotas(mock_client, "/")

        assert result.success
        assert result.data["count"] == 5
        assert result.data["quotas"] == []
        assert "note" in result.data

    async def test_list_user_quotas_missing_filesystem(self, mock_client: AsyncMock) -> None:
        """Test with missing filesystem argument."""
        result = await quota.list_user_quotas(mock_client, "")

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_list_user_quotas_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await quota.list_user_quotas(mock_client, "/")

        assert not result.success
        assert result.error.code == "LIST_USER_QUOTAS_ERROR"


class TestGetUserQuota:
    """Tests for get_user_quota tool."""

    async def test_get_user_quota_success(self, mock_client: AsyncMock) -> None:
        """Test getting a specific user's quota via user_quota()."""
        mock_client.call.side_effect = [
            1024,  # block_size
            [500, 1000, 2000, 50, 100, 200],  # user_quota returns 6-element array
        ]

        result = await quota.get_user_quota(mock_client, "alice", "/")

        assert result.success
        assert result.data["used_blocks"] == 500
        assert result.data["soft_block_limit"] == 1000
        assert result.data["hard_block_limit"] == 2000
        assert result.data["used_bytes"] == 500 * 1024
        assert result.data["used_files"] == 50
        assert result.data["soft_file_limit"] == 100
        assert result.data["hard_file_limit"] == 200

    async def test_get_user_quota_not_set_returns_graceful_result(
        self, mock_client: AsyncMock,
    ) -> None:
        """Test that a user with no quota returns a valid result, not an error."""
        mock_client.call.side_effect = [
            1024,  # block_size
            [],  # user_quota returns empty array - no quota set
        ]

        result = await quota.get_user_quota(mock_client, "newuser", "/")

        assert result.success
        assert result.data["quota_enabled"] is False
        assert result.data["used_blocks"] == 0
        assert result.data["soft_block_limit"] == 0

    async def test_get_user_quota_missing_username(self, mock_client: AsyncMock) -> None:
        """Test with missing username."""
        result = await quota.get_user_quota(mock_client, "", "/")

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_get_user_quota_missing_filesystem(self, mock_client: AsyncMock) -> None:
        """Test with missing filesystem."""
        result = await quota.get_user_quota(mock_client, "alice", "")

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_get_user_quota_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await quota.get_user_quota(mock_client, "alice", "/")

        assert not result.success
        assert result.error.code == "GET_USER_QUOTA_ERROR"


class TestGetGroupQuota:
    """Tests for get_group_quota tool."""

    async def test_get_group_quota_success(self, mock_client: AsyncMock) -> None:
        """Test getting a group's quota via group_quota()."""
        mock_client.call.side_effect = [
            1024,  # block_size
            [2000, 5000, 10000, 500, 1000, 2000],  # group_quota returns 6-element array
        ]

        result = await quota.get_group_quota(mock_client, "developers", "/home")

        assert result.success
        assert result.data["group"] == "developers"
        assert result.data["used_blocks"] == 2000
        assert result.data["soft_block_limit"] == 5000
        assert result.data["hard_block_limit"] == 10000

    async def test_get_group_quota_not_set(self, mock_client: AsyncMock) -> None:
        """Test that a group with no quota returns valid result."""
        mock_client.call.side_effect = [
            1024,  # block_size
            [],  # group_quota returns empty array
        ]

        result = await quota.get_group_quota(mock_client, "newgroup", "/")

        assert result.success
        assert result.data["quota_enabled"] is False

    async def test_get_group_quota_missing_group(self, mock_client: AsyncMock) -> None:
        """Test with missing group name."""
        result = await quota.get_group_quota(mock_client, "", "/")

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_get_group_quota_missing_filesystem(self, mock_client: AsyncMock) -> None:
        """Test with missing filesystem."""
        result = await quota.get_group_quota(mock_client, "developers", "")

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_get_group_quota_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await quota.get_group_quota(mock_client, "developers", "/")

        assert not result.success
        assert result.error.code == "GET_GROUP_QUOTA_ERROR"


class TestSetUserQuota:
    """Tests for set_user_quota tool."""

    async def test_set_quota_blocked_in_safe_mode(self, mock_client: AsyncMock) -> None:
        """Test that setting quotas is blocked in safe mode."""
        result = await quota.set_user_quota(
            mock_client, username="alice", filesystem="/",
            soft_block_limit=1000, hard_block_limit=2000,
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_set_quota_success(self, mock_client: AsyncMock) -> None:
        """Test successfully setting a quota."""
        mock_client.call.return_value = None

        result = await quota.set_user_quota(
            mock_client,
            username="alice",
            filesystem="/",
            soft_block_limit=1000,
            hard_block_limit=2000,
            soft_file_limit=100,
            hard_file_limit=200,
            safe_mode=False,
        )

        assert result.success
        assert result.data["action"] == "set_quota"
        assert result.data["user"] == "alice"
        assert result.data["soft_block_limit"] == 1000
        assert result.data["hard_block_limit"] == 2000

    async def test_set_quota_missing_username(self, mock_client: AsyncMock) -> None:
        """Test with missing username."""
        result = await quota.set_user_quota(
            mock_client, username="", filesystem="/", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_set_quota_missing_filesystem(self, mock_client: AsyncMock) -> None:
        """Test with missing filesystem."""
        result = await quota.set_user_quota(
            mock_client, username="alice", filesystem="", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_set_quota_negative_limit(self, mock_client: AsyncMock) -> None:
        """Test that negative limits are rejected."""
        result = await quota.set_user_quota(
            mock_client,
            username="alice",
            filesystem="/",
            soft_block_limit=-100,
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_QUOTA"

    async def test_set_quota_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await quota.set_user_quota(
            mock_client, username="alice", filesystem="/", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "SET_USER_QUOTA_ERROR"


class TestQuotaNotEnabledGraceful:
    """Tests that quota-not-enabled states are handled gracefully."""

    async def test_quota_not_enabled_returns_graceful_result(
        self, mock_client: AsyncMock,
    ) -> None:
        """When quotas aren't enabled, return ok with quota_enabled=False, not an error."""
        mock_client.call.side_effect = [
            1024,  # block_size
            [],  # user_quota returns empty array - no quota data
        ]

        result = await quota.get_user_quota(mock_client, "testuser", "/")

        assert result.success
        assert result.data["quota_enabled"] is False
        assert "error" not in str(result.data).lower()

    async def test_filesystem_no_quota_support(self, mock_client: AsyncMock) -> None:
        """Test filesystem with no quota support."""
        mock_client.call.return_value = [
            ["/tmp", "/dev/sda3", "tmpfs", "rw", 0, 0],
        ]

        result = await quota.list_quota_filesystems(mock_client)

        assert result.success
        fs = result.data["filesystems"][0]
        assert fs["quota_support"] is False
        assert fs["quota_enabled"] is False
