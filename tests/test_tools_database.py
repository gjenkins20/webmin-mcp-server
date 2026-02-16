"""Tests for Phase 6 database tools (MySQL)."""

from unittest.mock import AsyncMock

import pytest

from src.tools import database


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestListMysqlDatabases:
    """Tests for list_mysql_databases tool."""

    async def test_list_databases_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing databases."""
        mock_client.call.return_value = [
            {"name": "wordpress", "tables": 12, "size": 52428800, "collation": "utf8mb4_unicode_ci"},
            {"name": "app_db", "tables": 25, "size": 104857600, "collation": "utf8mb4_unicode_ci"},
            {"name": "information_schema", "tables": 80, "size": 0, "collation": "utf8mb3_general_ci"},
            {"name": "mysql", "tables": 37, "size": 2097152, "collation": "utf8mb4_general_ci"},
        ]

        result = await database.list_mysql_databases(mock_client)

        assert result.success
        assert result.data["total_count"] == 4
        assert result.data["user_database_count"] == 2
        assert result.data["system_database_count"] == 2
        assert len(result.data["user_databases"]) == 2
        assert result.data["user_databases"][0]["name"] == "wordpress"

    async def test_list_databases_simple_names(self, mock_client: AsyncMock) -> None:
        """Test handling simple list of database names."""
        mock_client.call.return_value = ["wordpress", "mysql", "information_schema"]

        result = await database.list_mysql_databases(mock_client)

        assert result.success
        assert result.data["total_count"] == 3
        assert result.data["user_database_count"] == 1

    async def test_list_databases_empty(self, mock_client: AsyncMock) -> None:
        """Test handling no databases."""
        mock_client.call.return_value = []

        result = await database.list_mysql_databases(mock_client)

        assert result.success
        assert result.data["total_count"] == 0

    async def test_list_databases_only_system(self, mock_client: AsyncMock) -> None:
        """Test handling only system databases."""
        mock_client.call.return_value = [
            {"name": "information_schema"},
            {"name": "mysql"},
            {"name": "performance_schema"},
            {"name": "sys"},
        ]

        result = await database.list_mysql_databases(mock_client)

        assert result.success
        assert result.data["user_database_count"] == 0
        assert result.data["system_database_count"] == 4

    async def test_list_databases_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await database.list_mysql_databases(mock_client)

        assert not result.success
        assert result.error.code == "LIST_DATABASES_ERROR"


class TestListMysqlUsers:
    """Tests for list_mysql_users tool."""

    async def test_list_users_mysql_running(self, mock_client: AsyncMock) -> None:
        """Test when MySQL is running and users available."""
        mock_client.call.side_effect = [
            [1, ""],  # is_mysql_running - running
            [  # list_users
                {"user": "root", "host": "localhost", "pass": "***"},
                {"user": "wordpress", "host": "%", "pass": "***"},
            ],
        ]

        result = await database.list_mysql_users(mock_client)

        assert result.success
        assert result.data["count"] == 2
        assert result.data["mysql_running"] is True

    async def test_list_users_mysql_not_running(self, mock_client: AsyncMock) -> None:
        """Test when MySQL is not running."""
        mock_client.call.return_value = [0, "Can't connect to MySQL server"]

        result = await database.list_mysql_users(mock_client)

        assert result.success
        assert result.data["count"] == 0
        assert result.data["mysql_running"] is False

    async def test_list_users_function_not_available(
        self, mock_client: AsyncMock
    ) -> None:
        """Test when list_users function is not available via XML-RPC."""
        mock_client.call.side_effect = [
            [1, ""],  # is_mysql_running - running
            Exception("Undefined subroutine"),  # list_users fails
        ]

        result = await database.list_mysql_users(mock_client)

        assert result.success
        assert result.data["count"] == 0
        assert result.data["mysql_running"] is True
        assert "not available" in result.data.get("message", "").lower()

    async def test_list_users_error(self, mock_client: AsyncMock) -> None:
        """Test error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await database.list_mysql_users(mock_client)

        assert not result.success
        assert result.error.code == "LIST_MYSQL_USERS_ERROR"


class TestGetMysqlStatus:
    """Tests for get_mysql_status tool."""

    async def test_get_status_running(self, mock_client: AsyncMock) -> None:
        """Test when MySQL is running."""
        mock_client.call.side_effect = [
            [1, ""],  # is_mysql_running
            "8.0.35",  # get_mysql_version
            [{"name": "mysql", "file": "/etc/mysql/my.cnf"}],  # get_mysql_config
        ]

        result = await database.get_mysql_status(mock_client)

        assert result.success
        assert result.data["running"] is True
        assert result.data["version"] == "8.0.35"

    async def test_get_status_not_running(self, mock_client: AsyncMock) -> None:
        """Test when MySQL is not running."""
        mock_client.call.side_effect = [
            [0, "Can't connect to MySQL server through socket"],  # is_mysql_running
            "8.0.35",  # get_mysql_version still works
        ]

        result = await database.get_mysql_status(mock_client)

        assert result.success
        assert result.data["running"] is False
        assert result.data["version"] == "8.0.35"

    async def test_get_status_not_installed(self, mock_client: AsyncMock) -> None:
        """Test when MySQL is not installed."""
        mock_client.call.side_effect = [
            [0, "MySQL not installed"],  # is_mysql_running
            "",  # get_mysql_version - empty
        ]

        result = await database.get_mysql_status(mock_client)

        assert result.success
        assert result.data["running"] is False
        assert result.data["installed"] is False

    async def test_get_status_connection_error(self, mock_client: AsyncMock) -> None:
        """Test connection error is handled gracefully."""
        mock_client.call.side_effect = Exception("Can't connect to socket")

        result = await database.get_mysql_status(mock_client)

        assert result.success
        assert result.data["running"] is False

    async def test_get_status_other_error(self, mock_client: AsyncMock) -> None:
        """Test other errors are reported."""
        mock_client.call.side_effect = Exception("Permission denied")

        result = await database.get_mysql_status(mock_client)

        assert not result.success
        assert result.error.code == "MYSQL_STATUS_ERROR"
