"""Tests for Phase 7 Webmin ACL management tools."""

from unittest.mock import AsyncMock

import pytest

from src.tools import acl


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestListWebminUsers:
    """Tests for list_webmin_users tool."""

    async def test_list_webmin_users_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing Webmin users."""
        mock_client.call.return_value = [
            {"name": "admin", "modules": ["*"]},
            {"name": "readonly", "modules": ["system-status", "proc"]},
        ]

        result = await acl.list_webmin_users(mock_client)

        assert result.success
        assert result.data["count"] == 2
        assert result.data["users"][0]["name"] == "admin"
        assert result.data["users"][0]["has_all_modules"] is True
        assert result.data["users"][1]["name"] == "readonly"
        assert result.data["users"][1]["module_count"] == 2

    async def test_list_webmin_users_empty(self, mock_client: AsyncMock) -> None:
        """Test listing when no users exist."""
        mock_client.call.return_value = []

        result = await acl.list_webmin_users(mock_client)

        assert result.success
        assert result.data["count"] == 0
        assert result.data["users"] == []

    async def test_list_webmin_users_error(self, mock_client: AsyncMock) -> None:
        """Test error handling when listing fails."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await acl.list_webmin_users(mock_client)

        assert not result.success
        assert result.error.code == "LIST_WEBMIN_USERS_ERROR"


class TestGetWebminUser:
    """Tests for get_webmin_user tool."""

    async def test_get_webmin_user_success(self, mock_client: AsyncMock) -> None:
        """Test successfully getting a Webmin user via get_user()."""
        mock_client.call.return_value = {
            "name": "admin", "modules": ["*"], "lang": "en", "theme": "authentic-theme",
        }

        result = await acl.get_webmin_user(mock_client, "admin")

        assert result.success
        assert result.data["name"] == "admin"
        assert result.data["has_all_modules"] is True
        assert result.data["lang"] == "en"
        # Verify direct lookup was used
        mock_client.call.assert_called_once_with("acl", "get_user", "admin")

    async def test_get_webmin_user_not_found(self, mock_client: AsyncMock) -> None:
        """Test getting a non-existent user."""
        mock_client.call.return_value = None  # get_user returns None for not found

        result = await acl.get_webmin_user(mock_client, "nonexistent")

        assert not result.success
        assert result.error.code == "USER_NOT_FOUND"

    async def test_get_webmin_user_empty_username(self, mock_client: AsyncMock) -> None:
        """Test with empty username."""
        result = await acl.get_webmin_user(mock_client, "")

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_get_webmin_user_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await acl.get_webmin_user(mock_client, "admin")

        assert not result.success
        assert result.error.code == "GET_WEBMIN_USER_ERROR"


class TestListWebminModules:
    """Tests for list_webmin_modules tool."""

    async def test_list_webmin_modules_success_list(self, mock_client: AsyncMock) -> None:
        """Test listing modules when returned as list."""
        mock_client.call.return_value = [
            {"dir": "useradmin", "desc": "Users and Groups", "category": "system"},
            {"dir": "init", "desc": "Bootup and Shutdown", "category": "system"},
        ]

        result = await acl.list_webmin_modules(mock_client)

        assert result.success
        assert result.data["count"] == 2
        assert result.data["modules"][0]["name"] == "useradmin"
        # Verify correct API call
        mock_client.call.assert_called_once_with("acl", "list_module_infos")

    async def test_list_webmin_modules_success_dict(self, mock_client: AsyncMock) -> None:
        """Test listing modules when returned as dict."""
        mock_client.call.return_value = {
            "useradmin": {"desc": "Users and Groups", "category": "system"},
            "init": {"desc": "Bootup and Shutdown", "category": "system"},
        }

        result = await acl.list_webmin_modules(mock_client)

        assert result.success
        assert result.data["count"] == 2

    async def test_list_webmin_modules_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await acl.list_webmin_modules(mock_client)

        assert not result.success
        assert result.error.code == "LIST_WEBMIN_MODULES_ERROR"


class TestCreateWebminUser:
    """Tests for create_webmin_user tool."""

    async def test_create_blocked_in_safe_mode(self, mock_client: AsyncMock) -> None:
        """Test that creation is blocked in safe mode."""
        result = await acl.create_webmin_user(
            mock_client, username="newuser", password="pass123", safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_create_success(self, mock_client: AsyncMock) -> None:
        """Test successfully creating a Webmin user."""
        mock_client.call.side_effect = [
            None,  # get_user returns None (user doesn't exist)
            "$1$salt$encrypted_hash",  # encrypt_password
            None,  # create_user
        ]

        result = await acl.create_webmin_user(
            mock_client,
            username="newuser",
            password="pass123",
            modules=["useradmin", "init"],
            safe_mode=False,
        )

        assert result.success
        assert result.data["action"] == "create"
        assert result.data["user"]["name"] == "newuser"
        assert result.data["user"]["module_count"] == 2
        # Verify encrypt_password was called
        calls = mock_client.call.call_args_list
        assert calls[1].args == ("acl", "encrypt_password", "pass123")

    async def test_create_already_exists(self, mock_client: AsyncMock) -> None:
        """Test creating a user that already exists."""
        mock_client.call.return_value = {"name": "existing", "modules": ["*"]}

        result = await acl.create_webmin_user(
            mock_client, username="existing", password="pass123", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "USER_EXISTS"

    async def test_create_invalid_username_empty(self, mock_client: AsyncMock) -> None:
        """Test that empty username is rejected."""
        result = await acl.create_webmin_user(
            mock_client, username="", password="pass123", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"

    async def test_create_invalid_username_special_chars(self, mock_client: AsyncMock) -> None:
        """Test that username with special chars is rejected."""
        result = await acl.create_webmin_user(
            mock_client, username="user@name", password="pass123", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"

    async def test_create_empty_password(self, mock_client: AsyncMock) -> None:
        """Test that empty password is rejected."""
        result = await acl.create_webmin_user(
            mock_client, username="newuser", password="", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_PASSWORD"

    async def test_create_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during creation."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await acl.create_webmin_user(
            mock_client, username="newuser", password="pass123", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "CREATE_WEBMIN_USER_ERROR"


class TestModifyWebminUser:
    """Tests for modify_webmin_user tool."""

    async def test_modify_blocked_in_safe_mode(self, mock_client: AsyncMock) -> None:
        """Test that modification is blocked in safe mode."""
        result = await acl.modify_webmin_user(
            mock_client, username="admin", password="newpass", safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_modify_success(self, mock_client: AsyncMock) -> None:
        """Test successfully modifying a user."""
        mock_client.call.side_effect = [
            [{"name": "admin", "modules": ["*"]}],  # list_users
            "$1$salt$new_encrypted",  # encrypt_password
            None,  # modify_user
        ]

        result = await acl.modify_webmin_user(
            mock_client, username="admin", password="newpass", safe_mode=False,
        )

        assert result.success
        assert result.data["action"] == "modify"
        assert result.data["changes"]["password"] is True
        # Verify password was encrypted
        calls = mock_client.call.call_args_list
        assert calls[1].args == ("acl", "encrypt_password", "newpass")

    async def test_modify_user_not_found(self, mock_client: AsyncMock) -> None:
        """Test modifying a non-existent user."""
        mock_client.call.return_value = []

        result = await acl.modify_webmin_user(
            mock_client, username="nonexistent", password="pass", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "USER_NOT_FOUND"

    async def test_modify_no_changes(self, mock_client: AsyncMock) -> None:
        """Test modifying with no changes."""
        mock_client.call.return_value = [
            {"name": "admin", "modules": ["*"]},
        ]

        result = await acl.modify_webmin_user(
            mock_client, username="admin", safe_mode=False,
        )

        assert result.success
        assert result.data["message"] == "No changes specified"

    async def test_modify_demote_last_superuser_blocked(self, mock_client: AsyncMock) -> None:
        """Test that demoting the last superuser is blocked."""
        mock_client.call.side_effect = [
            # list_users for finding the user
            [{"name": "admin", "modules": ["*"]}],
            # list_users for counting superusers
            [{"name": "admin", "modules": ["*"]}],
        ]

        result = await acl.modify_webmin_user(
            mock_client,
            username="admin",
            modules=["useradmin"],  # Demoting from superuser
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "LAST_SUPERUSER"

    async def test_modify_demote_allowed_with_other_superusers(self, mock_client: AsyncMock) -> None:
        """Test that demoting is allowed when other superusers exist."""
        mock_client.call.side_effect = [
            # list_users for finding the user
            [
                {"name": "admin", "modules": ["*"]},
                {"name": "admin2", "modules": ["*"]},
            ],
            # list_users for counting superusers
            [
                {"name": "admin", "modules": ["*"]},
                {"name": "admin2", "modules": ["*"]},
            ],
            None,  # modify_user (no password change, so no encrypt_password call)
        ]

        result = await acl.modify_webmin_user(
            mock_client,
            username="admin",
            modules=["useradmin"],
            safe_mode=False,
        )

        assert result.success

    async def test_modify_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await acl.modify_webmin_user(
            mock_client, username="admin", password="pass", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "MODIFY_WEBMIN_USER_ERROR"


class TestDeleteWebminUser:
    """Tests for delete_webmin_user tool."""

    async def test_delete_blocked_in_safe_mode(self, mock_client: AsyncMock) -> None:
        """Test that deletion is blocked in safe mode."""
        result = await acl.delete_webmin_user(
            mock_client, username="testuser", safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_delete_success(self, mock_client: AsyncMock) -> None:
        """Test successfully deleting a user."""
        mock_client.call.side_effect = [
            # list_users
            [
                {"name": "admin", "modules": ["*"]},
                {"name": "testuser", "modules": ["useradmin"]},
            ],
            None,  # delete_from_groups
            None,  # delete_user
        ]

        result = await acl.delete_webmin_user(
            mock_client, username="testuser", safe_mode=False,
        )

        assert result.success
        assert result.data["action"] == "delete"
        assert result.data["deleted_user"]["name"] == "testuser"
        # Verify delete_from_groups was called before delete_user
        calls = mock_client.call.call_args_list
        assert calls[1].args == ("acl", "delete_from_groups", "testuser")
        assert calls[2].args == ("acl", "delete_user", "testuser")

    async def test_delete_user_not_found(self, mock_client: AsyncMock) -> None:
        """Test deleting a non-existent user."""
        mock_client.call.return_value = []

        result = await acl.delete_webmin_user(
            mock_client, username="nonexistent", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "USER_NOT_FOUND"

    async def test_delete_last_superuser_blocked_unconditionally(
        self, mock_client: AsyncMock,
    ) -> None:
        """Test that deleting the last superuser is ALWAYS blocked, even with safe_mode=False."""
        mock_client.call.side_effect = [
            # list_users
            [{"name": "admin", "modules": ["*"]}],
            # list_users for counting superusers
            [{"name": "admin", "modules": ["*"]}],
        ]

        result = await acl.delete_webmin_user(
            mock_client, username="admin", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "LAST_SUPERUSER"
        assert "permanently lock out" in result.error.message

    async def test_delete_superuser_allowed_with_others(self, mock_client: AsyncMock) -> None:
        """Test that deleting a superuser is allowed when others exist."""
        mock_client.call.side_effect = [
            # list_users
            [
                {"name": "admin", "modules": ["*"]},
                {"name": "admin2", "modules": ["*"]},
            ],
            # list_users for counting superusers
            [
                {"name": "admin", "modules": ["*"]},
                {"name": "admin2", "modules": ["*"]},
            ],
            None,  # delete_from_groups
            None,  # delete_user
        ]

        result = await acl.delete_webmin_user(
            mock_client, username="admin", safe_mode=False,
        )

        assert result.success

    async def test_delete_empty_username(self, mock_client: AsyncMock) -> None:
        """Test deleting with empty username."""
        result = await acl.delete_webmin_user(
            mock_client, username="", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "MISSING_ARGUMENT"

    async def test_delete_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await acl.delete_webmin_user(
            mock_client, username="testuser", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "DELETE_WEBMIN_USER_ERROR"


class TestWebminUsernameValidation:
    """Tests for Webmin username validation."""

    async def test_valid_username(self, mock_client: AsyncMock) -> None:
        """Test valid usernames."""
        mock_client.call.side_effect = [
            None,  # get_user returns None (not found)
            "$1$salt$hash",  # encrypt_password
            None,  # create_user
        ]

        result = await acl.create_webmin_user(
            mock_client, username="admin_user", password="pass123", safe_mode=False,
        )
        assert result.success

    async def test_valid_username_with_dots(self, mock_client: AsyncMock) -> None:
        """Test that dots are allowed in Webmin usernames."""
        mock_client.call.side_effect = [
            None,  # get_user returns None (not found)
            "$1$salt$hash",  # encrypt_password
            None,  # create_user
        ]

        result = await acl.create_webmin_user(
            mock_client, username="john.doe", password="pass123", safe_mode=False,
        )
        assert result.success

    async def test_invalid_username_starts_with_number(self, mock_client: AsyncMock) -> None:
        """Test that username starting with number is rejected."""
        result = await acl.create_webmin_user(
            mock_client, username="1admin", password="pass123", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"

    async def test_invalid_username_too_long(self, mock_client: AsyncMock) -> None:
        """Test that username over 64 characters is rejected."""
        result = await acl.create_webmin_user(
            mock_client, username="a" * 65, password="pass123", safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "INVALID_USERNAME"
