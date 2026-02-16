"""Tests for Phase 3 user management tools."""

from unittest.mock import AsyncMock

import pytest

from src.tools import users


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestListGroups:
    """Tests for list_groups tool."""

    async def test_list_groups_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing groups."""
        mock_client.call.return_value = [
            {"group": "root", "gid": 0, "members": ""},
            {"group": "sudo", "gid": 27, "members": "admin,testuser"},
            {"group": "users", "gid": 1000, "members": "testuser"},
            {"group": "developers", "gid": 1001, "members": "dev1,dev2,dev3"},
        ]

        result = await users.list_groups(mock_client)

        assert result.success
        assert result.data["total_count"] == 4
        assert result.data["system_count"] == 2  # root, sudo (gid < 1000)
        assert result.data["regular_count"] == 2  # users, developers (gid >= 1000)

    async def test_list_groups_parses_members(self, mock_client: AsyncMock) -> None:
        """Test that members are parsed into a list."""
        mock_client.call.return_value = [
            {"group": "developers", "gid": 1001, "members": "dev1,dev2,dev3"},
        ]

        result = await users.list_groups(mock_client)

        assert result.success
        group = result.data["regular_groups"][0]
        assert group["members"] == ["dev1", "dev2", "dev3"]
        assert group["member_count"] == 3

    async def test_list_groups_empty_members(self, mock_client: AsyncMock) -> None:
        """Test groups with no members."""
        mock_client.call.return_value = [
            {"group": "nobody", "gid": 99, "members": ""},  # System group (gid < 1000)
        ]

        result = await users.list_groups(mock_client)

        assert result.success
        group = result.data["system_groups"][0]
        assert group["members"] == []
        assert group["member_count"] == 0

    async def test_list_groups_error(self, mock_client: AsyncMock) -> None:
        """Test error handling when listing groups fails."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await users.list_groups(mock_client)

        assert not result.success
        assert result.error.code == "LIST_GROUPS_ERROR"


class TestCreateUser:
    """Tests for create_user tool."""

    async def test_create_user_blocked_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that user creation is blocked in safe mode."""
        result = await users.create_user(
            mock_client,
            username="testuser",
            password="password123",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_create_user_success(self, mock_client: AsyncMock) -> None:
        """Test successfully creating a user."""
        mock_client.call.side_effect = [
            [],  # list_users - empty, no existing users
            1,  # create_user returns 1 on success
            [{"user": "newuser", "uid": 1000, "gid": 1000}],  # list_users after
        ]

        result = await users.create_user(
            mock_client,
            username="newuser",
            password="password123",
            real_name="New User",
            safe_mode=False,
        )

        assert result.success
        assert result.data["action"] == "create"
        assert result.data["user"]["username"] == "newuser"
        assert result.data["user"]["uid"] == 1000

    async def test_create_user_already_exists(self, mock_client: AsyncMock) -> None:
        """Test that duplicate username is rejected."""
        mock_client.call.return_value = [
            {"user": "existinguser", "uid": 1000},
        ]

        result = await users.create_user(
            mock_client,
            username="existinguser",
            password="password123",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "USER_EXISTS"

    async def test_create_user_invalid_username_empty(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that empty username is rejected."""
        result = await users.create_user(
            mock_client,
            username="",
            password="password123",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"
        mock_client.call.assert_not_called()

    async def test_create_user_invalid_username_uppercase(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that uppercase username is rejected."""
        result = await users.create_user(
            mock_client,
            username="TestUser",
            password="password123",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"

    async def test_create_user_invalid_username_starts_with_number(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that username starting with number is rejected."""
        result = await users.create_user(
            mock_client,
            username="1user",
            password="password123",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"

    async def test_create_user_invalid_username_too_long(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that username over 32 characters is rejected."""
        result = await users.create_user(
            mock_client,
            username="a" * 33,
            password="password123",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"

    async def test_create_user_empty_password(self, mock_client: AsyncMock) -> None:
        """Test that empty password is rejected."""
        result = await users.create_user(
            mock_client,
            username="testuser",
            password="",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_PASSWORD"

    async def test_create_user_invalid_uid_negative(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that negative UID is rejected."""
        result = await users.create_user(
            mock_client,
            username="testuser",
            password="password123",
            uid=-1,
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_UID"

    async def test_create_user_invalid_uid_too_large(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that UID over 65534 is rejected."""
        result = await users.create_user(
            mock_client,
            username="testuser",
            password="password123",
            uid=70000,
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_UID"

    async def test_create_user_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during user creation."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await users.create_user(
            mock_client,
            username="testuser",
            password="password123",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "CREATE_USER_ERROR"


class TestDeleteUser:
    """Tests for delete_user tool."""

    async def test_delete_user_blocked_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that user deletion is blocked in safe mode."""
        result = await users.delete_user(
            mock_client,
            username="testuser",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_delete_user_critical_user_blocked(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that critical system users cannot be deleted."""
        for critical_user in ["root", "daemon", "bin", "nobody"]:
            result = await users.delete_user(
                mock_client,
                username=critical_user,
                safe_mode=False,
            )

            assert not result.success
            assert result.error.code == "CRITICAL_USER"

    async def test_delete_user_success(self, mock_client: AsyncMock) -> None:
        """Test successfully deleting a user."""
        mock_client.call.side_effect = [
            [  # list_users before
                {"user": "testuser", "uid": 1000, "home": "/home/testuser", "line": "testuser:x:1000:1000::"}
            ],
            None,  # delete_user
            [],  # list_users after
        ]

        result = await users.delete_user(
            mock_client,
            username="testuser",
            safe_mode=False,
        )

        assert result.success
        assert result.data["action"] == "delete"
        assert result.data["deleted_user"]["username"] == "testuser"

    async def test_delete_user_not_found(self, mock_client: AsyncMock) -> None:
        """Test deleting a user that doesn't exist."""
        mock_client.call.return_value = []  # No users

        result = await users.delete_user(
            mock_client,
            username="nonexistent",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "USER_NOT_FOUND"

    async def test_delete_user_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during user deletion."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await users.delete_user(
            mock_client,
            username="testuser",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "DELETE_USER_ERROR"


class TestModifyUser:
    """Tests for modify_user tool."""

    async def test_modify_user_success(self, mock_client: AsyncMock) -> None:
        """Test successfully modifying a user."""
        mock_client.call.side_effect = [
            [  # list_users
                {
                    "user": "testuser",
                    "uid": 1000,
                    "gid": 1000,
                    "real": "Test User",
                    "home": "/home/testuser",
                    "shell": "/bin/bash",
                }
            ],
            1,  # modify_user returns 1
        ]

        result = await users.modify_user(
            mock_client,
            username="testuser",
            real_name="Updated Name",
            shell="/bin/zsh",
            safe_mode=True,
        )

        assert result.success
        assert result.data["action"] == "modify"
        assert result.data["changes"]["real_name"] is True
        assert result.data["changes"]["shell"] is True

    async def test_modify_user_not_found(self, mock_client: AsyncMock) -> None:
        """Test modifying a user that doesn't exist."""
        mock_client.call.return_value = []  # No users

        result = await users.modify_user(
            mock_client,
            username="nonexistent",
            real_name="New Name",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "USER_NOT_FOUND"

    async def test_modify_user_no_changes(self, mock_client: AsyncMock) -> None:
        """Test modifying with no changes specified."""
        mock_client.call.return_value = [
            {"user": "testuser", "uid": 1000, "gid": 1000, "real": "Test", "home": "/home/testuser", "shell": "/bin/bash"}
        ]

        result = await users.modify_user(
            mock_client,
            username="testuser",
            safe_mode=True,
        )

        assert result.success
        assert result.data["message"] == "No changes specified"

    async def test_modify_user_invalid_new_username(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that invalid new username is rejected."""
        result = await users.modify_user(
            mock_client,
            username="testuser",
            new_username="Invalid User",  # Contains space
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"

    async def test_modify_user_invalid_uid(self, mock_client: AsyncMock) -> None:
        """Test that invalid UID is rejected."""
        result = await users.modify_user(
            mock_client,
            username="testuser",
            uid=-1,
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_UID"

    async def test_modify_user_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during user modification."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await users.modify_user(
            mock_client,
            username="testuser",
            real_name="New Name",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "MODIFY_USER_ERROR"


class TestChangePassword:
    """Tests for change_password tool."""

    async def test_change_password_blocked_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that password change is blocked in safe mode."""
        result = await users.change_password(
            mock_client,
            username="testuser",
            new_password="newpassword123",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_change_password_success(self, mock_client: AsyncMock) -> None:
        """Test successfully changing a password."""
        mock_client.call.side_effect = [
            [  # list_users
                {
                    "user": "testuser",
                    "uid": 1000,
                    "gid": 1000,
                    "real": "Test User",
                    "home": "/home/testuser",
                    "shell": "/bin/bash",
                }
            ],
            1,  # modify_user returns 1
        ]

        result = await users.change_password(
            mock_client,
            username="testuser",
            new_password="newpassword123",
            safe_mode=False,
        )

        assert result.success
        assert result.data["action"] == "change_password"
        assert result.data["username"] == "testuser"

    async def test_change_password_empty_password(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that empty password is rejected."""
        result = await users.change_password(
            mock_client,
            username="testuser",
            new_password="",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_PASSWORD"

    async def test_change_password_user_not_found(
        self, mock_client: AsyncMock
    ) -> None:
        """Test changing password for non-existent user."""
        mock_client.call.return_value = []  # No users

        result = await users.change_password(
            mock_client,
            username="nonexistent",
            new_password="newpassword123",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "USER_NOT_FOUND"

    async def test_change_password_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during password change."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await users.change_password(
            mock_client,
            username="testuser",
            new_password="newpassword123",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "CHANGE_PASSWORD_ERROR"


class TestUsernameValidation:
    """Tests for username validation."""

    async def test_valid_username_lowercase(self, mock_client: AsyncMock) -> None:
        """Test that lowercase usernames are valid."""
        mock_client.call.side_effect = [[], 1, [{"user": "testuser"}]]

        result = await users.create_user(
            mock_client,
            username="testuser",
            password="password123",
            safe_mode=False,
        )

        assert result.success

    async def test_valid_username_with_underscore(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that usernames with underscores are valid."""
        mock_client.call.side_effect = [[], 1, [{"user": "test_user"}]]

        result = await users.create_user(
            mock_client,
            username="test_user",
            password="password123",
            safe_mode=False,
        )

        assert result.success

    async def test_valid_username_with_hyphen(self, mock_client: AsyncMock) -> None:
        """Test that usernames with hyphens are valid."""
        mock_client.call.side_effect = [[], 1, [{"user": "test-user"}]]

        result = await users.create_user(
            mock_client,
            username="test-user",
            password="password123",
            safe_mode=False,
        )

        assert result.success

    async def test_valid_username_with_numbers(self, mock_client: AsyncMock) -> None:
        """Test that usernames with numbers (not at start) are valid."""
        mock_client.call.side_effect = [[], 1, [{"user": "user123"}]]

        result = await users.create_user(
            mock_client,
            username="user123",
            password="password123",
            safe_mode=False,
        )

        assert result.success

    async def test_valid_username_starts_with_underscore(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that usernames starting with underscore are valid."""
        mock_client.call.side_effect = [[], 1, [{"user": "_service"}]]

        result = await users.create_user(
            mock_client,
            username="_service",
            password="password123",
            safe_mode=False,
        )

        assert result.success
