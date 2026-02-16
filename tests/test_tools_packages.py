"""Tests for Phase 3 package information tools."""

from unittest.mock import AsyncMock
import xmlrpc.client

import pytest

from src.tools import packages


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestGetPackageInfo:
    """Tests for get_package_info tool."""

    async def test_get_package_info_success(self, mock_client: AsyncMock) -> None:
        """Test successfully getting package info."""
        mock_client.call.return_value = [
            "bash",  # name
            "deb",  # type
            "GNU Bourne Again SHell",  # description
            "amd64",  # architecture
            "5.2.21-2ubuntu4",  # version
            "Ubuntu Developers",  # maintainer
            "2024-01-15",  # install_date
            "https://www.gnu.org/software/bash/",  # url
        ]

        result = await packages.get_package_info(mock_client, "bash")

        assert result.success
        assert result.data["name"] == "bash"
        assert result.data["type"] == "deb"
        assert result.data["description"] == "GNU Bourne Again SHell"
        assert result.data["architecture"] == "amd64"
        assert result.data["version"] == "5.2.21-2ubuntu4"
        assert result.data["maintainer"] == "Ubuntu Developers"

    async def test_get_package_info_binary_description(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of Binary description objects."""
        binary_desc = xmlrpc.client.Binary(b"Binary description text")
        mock_client.call.return_value = [
            "testpkg",
            "deb",
            binary_desc,  # Binary object
            "amd64",
            "1.0",
            "Maintainer",
            None,
            None,
        ]

        result = await packages.get_package_info(mock_client, "testpkg")

        assert result.success
        assert result.data["description"] == "Binary description text"

    async def test_get_package_info_partial_data(self, mock_client: AsyncMock) -> None:
        """Test handling of partial package data."""
        mock_client.call.return_value = [
            "minimalpkg",
            "deb",
        ]  # Only name and type

        result = await packages.get_package_info(mock_client, "minimalpkg")

        assert result.success
        assert result.data["name"] == "minimalpkg"
        assert result.data["type"] == "deb"
        assert result.data["description"] is None
        assert result.data["version"] is None

    async def test_get_package_info_empty_name(self, mock_client: AsyncMock) -> None:
        """Test that empty package name is rejected."""
        result = await packages.get_package_info(mock_client, "")

        assert not result.success
        assert result.error.code == "INVALID_ARGUMENT"
        mock_client.call.assert_not_called()

    async def test_get_package_info_whitespace_name(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that whitespace-only package name is rejected."""
        result = await packages.get_package_info(mock_client, "   ")

        assert not result.success
        assert result.error.code == "INVALID_ARGUMENT"
        mock_client.call.assert_not_called()

    async def test_get_package_info_not_found_empty_response(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling when package returns empty response."""
        mock_client.call.return_value = None

        result = await packages.get_package_info(mock_client, "nonexistent")

        assert not result.success
        assert result.error.code == "PACKAGE_NOT_FOUND"

    async def test_get_package_info_not_found_not_list(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling when package returns non-list response."""
        mock_client.call.return_value = "not a list"

        result = await packages.get_package_info(mock_client, "nonexistent")

        assert not result.success
        assert result.error.code == "PACKAGE_NOT_FOUND"

    async def test_get_package_info_not_found_error(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling when package is not found via exception."""
        mock_client.call.side_effect = Exception("Package not found")

        result = await packages.get_package_info(mock_client, "nonexistent")

        assert not result.success
        assert result.error.code == "PACKAGE_NOT_FOUND"

    async def test_get_package_info_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during package info retrieval."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await packages.get_package_info(mock_client, "bash")

        assert not result.success
        assert result.error.code == "PACKAGE_INFO_ERROR"


class TestListAvailableUpdates:
    """Tests for list_available_updates tool."""

    async def test_list_available_updates_success(
        self, mock_client: AsyncMock
    ) -> None:
        """Test successfully listing available updates."""
        mock_client.call.return_value = {
            "poss": [
                {
                    "name": "bash",
                    "oldversion": "5.2.20-1",
                    "version": "5.2.21-2",
                    "desc": "GNU Bourne Again SHell",
                    "source": "apt",
                    "system": "apt",
                    "security": 0,
                },
                {
                    "name": "openssl",
                    "oldversion": "3.0.12",
                    "version": "3.0.13",
                    "desc": "SSL toolkit",
                    "source": "apt",
                    "system": "apt",
                    "security": 1,  # Security update
                },
            ],
        }

        result = await packages.list_available_updates(mock_client)

        assert result.success
        assert result.data["total_count"] == 2
        assert result.data["security_count"] == 1
        assert len(result.data["updates"]) == 2
        assert len(result.data["security_updates"]) == 1

    async def test_list_available_updates_categorization(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that updates are correctly categorized."""
        mock_client.call.return_value = {
            "poss": [
                {
                    "name": "regular-pkg",
                    "oldversion": "1.0",
                    "version": "1.1",
                    "security": 0,
                },
                {
                    "name": "security-pkg",
                    "oldversion": "2.0",
                    "version": "2.1",
                    "security": 1,
                },
            ],
        }

        result = await packages.list_available_updates(mock_client)

        assert result.success
        # Check regular update
        regular = [u for u in result.data["updates"] if u["name"] == "regular-pkg"][0]
        assert regular["is_security"] is False

        # Check security update
        security = [u for u in result.data["updates"] if u["name"] == "security-pkg"][
            0
        ]
        assert security["is_security"] is True
        assert security in result.data["security_updates"]

    async def test_list_available_updates_empty(self, mock_client: AsyncMock) -> None:
        """Test handling when no updates available."""
        mock_client.call.return_value = {"poss": []}

        result = await packages.list_available_updates(mock_client)

        assert result.success
        assert result.data["total_count"] == 0
        assert result.data["security_count"] == 0
        assert result.data["updates"] == []
        assert result.data["security_updates"] == []

    async def test_list_available_updates_no_poss_field(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling when poss field is missing."""
        mock_client.call.return_value = {}  # No poss field

        result = await packages.list_available_updates(mock_client)

        assert result.success
        assert result.data["total_count"] == 0
        assert result.data["updates"] == []

    async def test_list_available_updates_parse_details(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that update details are correctly parsed."""
        mock_client.call.return_value = {
            "poss": [
                {
                    "name": "testpkg",
                    "oldversion": "1.0.0",
                    "version": "2.0.0",
                    "desc": "Test package",
                    "source": "apt",
                    "system": "apt",
                    "security": 0,
                },
            ],
        }

        result = await packages.list_available_updates(mock_client)

        assert result.success
        update = result.data["updates"][0]
        assert update["name"] == "testpkg"
        assert update["current_version"] == "1.0.0"
        assert update["new_version"] == "2.0.0"
        assert update["description"] == "Test package"
        assert update["source"] == "apt"
        assert update["system"] == "apt"
        assert update["is_security"] is False

    async def test_list_available_updates_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during update listing."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await packages.list_available_updates(mock_client)

        assert not result.success
        assert result.error.code == "LIST_UPDATES_ERROR"


class TestGetPackageCount:
    """Tests for get_package_count tool."""

    async def test_get_package_count_success(self, mock_client: AsyncMock) -> None:
        """Test successfully getting package count."""
        mock_client.call.return_value = 1249

        result = await packages.get_package_count(mock_client)

        assert result.success
        assert result.data["installed_count"] == 1249

    async def test_get_package_count_zero(self, mock_client: AsyncMock) -> None:
        """Test handling of zero packages."""
        mock_client.call.return_value = 0

        result = await packages.get_package_count(mock_client)

        assert result.success
        assert result.data["installed_count"] == 0

    async def test_get_package_count_non_int_response(
        self, mock_client: AsyncMock
    ) -> None:
        """Test handling of non-integer response."""
        mock_client.call.return_value = "not a number"

        result = await packages.get_package_count(mock_client)

        assert result.success
        assert result.data["installed_count"] == 0

    async def test_get_package_count_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during count retrieval."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await packages.get_package_count(mock_client)

        assert not result.success
        assert result.error.code == "PACKAGE_COUNT_ERROR"
