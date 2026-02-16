"""Tests for Phase 4 file management tools."""

from unittest.mock import AsyncMock

import pytest

from src.tools import files


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock WebminClient."""
    client = AsyncMock()
    return client


class TestReadFile:
    """Tests for read_file tool."""

    async def test_read_file_success(self, mock_client: AsyncMock) -> None:
        """Test successfully reading a file."""
        mock_client.call.return_value = "Hello, World!\n"

        result = await files.read_file(mock_client, "/etc/hostname")

        assert result.success
        assert result.data["path"] == "/etc/hostname"
        assert result.data["content"] == "Hello, World!\n"
        assert result.data["size"] == 14

    async def test_read_file_as_lines(self, mock_client: AsyncMock) -> None:
        """Test reading file as lines."""
        mock_client.call.return_value = ["line1", "line2", "line3"]

        result = await files.read_file(mock_client, "/etc/hosts", as_lines=True)

        assert result.success
        assert result.data["lines"] == ["line1", "line2", "line3"]
        assert result.data["line_count"] == 3

    async def test_read_file_empty_path(self, mock_client: AsyncMock) -> None:
        """Test that empty path is rejected."""
        result = await files.read_file(mock_client, "")

        assert not result.success
        assert result.error.code == "INVALID_ARGUMENT"
        mock_client.call.assert_not_called()

    async def test_read_file_relative_path(self, mock_client: AsyncMock) -> None:
        """Test that relative path is rejected."""
        result = await files.read_file(mock_client, "relative/path.txt")

        assert not result.success
        assert result.error.code == "INVALID_PATH"

    async def test_read_file_not_found(self, mock_client: AsyncMock) -> None:
        """Test handling of file not found."""
        mock_client.call.side_effect = Exception("No such file or directory")

        result = await files.read_file(mock_client, "/nonexistent/file")

        assert not result.success
        assert result.error.code == "FILE_NOT_FOUND"

    async def test_read_file_permission_denied(self, mock_client: AsyncMock) -> None:
        """Test handling of permission denied."""
        mock_client.call.side_effect = Exception("Permission denied")

        result = await files.read_file(mock_client, "/root/secret")

        assert not result.success
        assert result.error.code == "PERMISSION_DENIED"

    async def test_read_file_error(self, mock_client: AsyncMock) -> None:
        """Test general error handling."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await files.read_file(mock_client, "/some/file")

        assert not result.success
        assert result.error.code == "READ_FILE_ERROR"


class TestWriteFile:
    """Tests for write_file tool."""

    async def test_write_file_success_in_tmp(self, mock_client: AsyncMock) -> None:
        """Test writing to /tmp succeeds in safe mode."""
        mock_client.call.return_value = 1

        result = await files.write_file(
            mock_client,
            path="/tmp/test.txt",
            content="Hello, World!",
            safe_mode=True,
        )

        assert result.success
        assert result.data["action"] == "write"
        assert result.data["path"] == "/tmp/test.txt"
        assert result.data["bytes_written"] == 13

    async def test_write_file_blocked_system_path(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that writing to system paths is blocked."""
        result = await files.write_file(
            mock_client,
            path="/etc/passwd",
            content="malicious",
            safe_mode=False,  # Even with safe mode off
        )

        assert not result.success
        assert result.error.code == "PATH_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_write_file_blocked_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that writing outside safe paths is blocked in safe mode."""
        result = await files.write_file(
            mock_client,
            path="/home/user/file.txt",
            content="content",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
        mock_client.call.assert_not_called()

    async def test_write_file_allowed_without_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that writing to home is allowed without safe mode."""
        mock_client.call.return_value = 1

        result = await files.write_file(
            mock_client,
            path="/home/user/file.txt",
            content="content",
            safe_mode=False,
        )

        assert result.success

    async def test_write_file_empty_path(self, mock_client: AsyncMock) -> None:
        """Test that empty path is rejected."""
        result = await files.write_file(
            mock_client,
            path="",
            content="content",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_ARGUMENT"

    async def test_write_file_relative_path(self, mock_client: AsyncMock) -> None:
        """Test that relative path is rejected."""
        result = await files.write_file(
            mock_client,
            path="relative/path.txt",
            content="content",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_PATH"

    async def test_write_file_error(self, mock_client: AsyncMock) -> None:
        """Test error handling during write."""
        mock_client.call.side_effect = Exception("Disk full")

        result = await files.write_file(
            mock_client,
            path="/tmp/test.txt",
            content="content",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "WRITE_FILE_ERROR"


class TestDeleteFile:
    """Tests for delete_file tool."""

    async def test_delete_file_success_in_tmp(self, mock_client: AsyncMock) -> None:
        """Test deleting from /tmp succeeds in safe mode."""
        mock_client.call.return_value = [1, ""]

        result = await files.delete_file(
            mock_client,
            path="/tmp/test.txt",
            safe_mode=True,
        )

        assert result.success
        assert result.data["action"] == "delete"

    async def test_delete_file_blocked_system_path(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that deleting system paths is blocked."""
        result = await files.delete_file(
            mock_client,
            path="/etc/passwd",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "PATH_BLOCKED"

    async def test_delete_file_blocked_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that deleting outside safe paths is blocked in safe mode."""
        result = await files.delete_file(
            mock_client,
            path="/home/user/file.txt",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"

    async def test_delete_file_not_found(self, mock_client: AsyncMock) -> None:
        """Test handling of file not found."""
        mock_client.call.side_effect = Exception("No such file")

        result = await files.delete_file(
            mock_client,
            path="/tmp/nonexistent",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "FILE_NOT_FOUND"


class TestCopyFile:
    """Tests for copy_file tool."""

    async def test_copy_file_success_to_tmp(self, mock_client: AsyncMock) -> None:
        """Test copying to /tmp succeeds in safe mode."""
        mock_client.call.return_value = [1, ""]

        result = await files.copy_file(
            mock_client,
            source="/etc/hostname",
            destination="/tmp/hostname_copy",
            safe_mode=True,
        )

        assert result.success
        assert result.data["action"] == "copy"
        assert result.data["source"] == "/etc/hostname"
        assert result.data["destination"] == "/tmp/hostname_copy"

    async def test_copy_file_blocked_destination(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that copying to system paths is blocked."""
        result = await files.copy_file(
            mock_client,
            source="/tmp/file.txt",
            destination="/etc/file.txt",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "PATH_BLOCKED"

    async def test_copy_file_blocked_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that copying outside safe paths is blocked in safe mode."""
        result = await files.copy_file(
            mock_client,
            source="/etc/hostname",
            destination="/home/user/hostname",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"

    async def test_copy_file_empty_source(self, mock_client: AsyncMock) -> None:
        """Test that empty source is rejected."""
        result = await files.copy_file(
            mock_client,
            source="",
            destination="/tmp/dest",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_ARGUMENT"

    async def test_copy_file_empty_destination(self, mock_client: AsyncMock) -> None:
        """Test that empty destination is rejected."""
        result = await files.copy_file(
            mock_client,
            source="/tmp/src",
            destination="",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_ARGUMENT"


class TestRenameFile:
    """Tests for rename_file tool."""

    async def test_rename_file_success_in_tmp(self, mock_client: AsyncMock) -> None:
        """Test renaming within /tmp succeeds in safe mode."""
        mock_client.call.return_value = 1

        result = await files.rename_file(
            mock_client,
            source="/tmp/old.txt",
            destination="/tmp/new.txt",
            safe_mode=True,
        )

        assert result.success
        assert result.data["action"] == "rename"

    async def test_rename_file_blocked_source(self, mock_client: AsyncMock) -> None:
        """Test that renaming from system paths is blocked."""
        result = await files.rename_file(
            mock_client,
            source="/etc/passwd",
            destination="/tmp/passwd",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "PATH_BLOCKED"

    async def test_rename_file_blocked_in_safe_mode_source(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that renaming from unsafe paths is blocked in safe mode."""
        result = await files.rename_file(
            mock_client,
            source="/home/user/file.txt",
            destination="/tmp/file.txt",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"

    async def test_rename_file_blocked_in_safe_mode_dest(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that renaming to unsafe paths is blocked in safe mode."""
        result = await files.rename_file(
            mock_client,
            source="/tmp/file.txt",
            destination="/home/user/file.txt",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"


class TestCreateDirectory:
    """Tests for create_directory tool."""

    async def test_create_directory_success_in_tmp(
        self, mock_client: AsyncMock
    ) -> None:
        """Test creating directory in /tmp succeeds in safe mode."""
        mock_client.call.return_value = 1

        result = await files.create_directory(
            mock_client,
            path="/tmp/newdir",
            mode=755,
            safe_mode=True,
        )

        assert result.success
        assert result.data["action"] == "create_directory"
        assert result.data["mode"] == 755

    async def test_create_directory_blocked_system_path(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that creating in system paths is blocked."""
        result = await files.create_directory(
            mock_client,
            path="/etc/newdir",
            safe_mode=False,
        )

        assert not result.success
        assert result.error.code == "PATH_BLOCKED"

    async def test_create_directory_blocked_in_safe_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that creating outside safe paths is blocked in safe mode."""
        result = await files.create_directory(
            mock_client,
            path="/home/user/newdir",
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"

    async def test_create_directory_invalid_mode(
        self, mock_client: AsyncMock
    ) -> None:
        """Test that invalid mode is rejected."""
        result = await files.create_directory(
            mock_client,
            path="/tmp/newdir",
            mode=999,
            safe_mode=True,
        )

        assert not result.success
        assert result.error.code == "INVALID_MODE"


class TestListProcesses:
    """Tests for list_processes tool."""

    async def test_list_processes_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing processes."""
        mock_client.call.return_value = [
            {
                "pid": 1,
                "ppid": 0,
                "user": "root",
                "cpu": "0.1 %",
                "size": "1024 kB",
                "bytes": 1048576,
                "time": "00:01:00",
                "args": "/sbin/init",
                "nice": 0,
                "_tty": "None",
            },
            {
                "pid": 100,
                "ppid": 1,
                "user": "www-data",
                "cpu": "2.5 %",
                "size": "512 kB",
                "bytes": 524288,
                "time": "00:05:00",
                "args": "nginx: worker",
                "nice": 0,
                "_tty": "None",
            },
        ]

        result = await files.list_processes(mock_client)

        assert result.success
        assert result.data["count"] == 2
        assert len(result.data["processes"]) == 2
        assert result.data["processes"][0]["pid"] == 1
        assert result.data["processes"][0]["user"] == "root"

    async def test_list_processes_error(self, mock_client: AsyncMock) -> None:
        """Test error handling when listing processes fails."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await files.list_processes(mock_client)

        assert not result.success
        assert result.error.code == "LIST_PROCESSES_ERROR"


class TestListMounts:
    """Tests for list_mounts tool."""

    async def test_list_mounts_success(self, mock_client: AsyncMock) -> None:
        """Test successfully listing mounts."""
        mock_client.call.return_value = [
            ["/", "/dev/sda1", "ext4", "rw,relatime"],
            ["/home", "/dev/sda2", "ext4", "rw,relatime"],
            ["/proc", "proc", "proc", "rw,nosuid"],
            ["/sys", "sysfs", "sysfs", "rw,nosuid"],
        ]

        result = await files.list_mounts(mock_client)

        assert result.success
        assert result.data["total_count"] == 4
        assert result.data["real_filesystem_count"] == 2  # Excludes proc, sysfs
        assert len(result.data["real_filesystems"]) == 2
        assert result.data["real_filesystems"][0]["mount_point"] == "/"

    async def test_list_mounts_error(self, mock_client: AsyncMock) -> None:
        """Test error handling when listing mounts fails."""
        mock_client.call.side_effect = Exception("Connection failed")

        result = await files.list_mounts(mock_client)

        assert not result.success
        assert result.error.code == "LIST_MOUNTS_ERROR"


class TestPathBlocking:
    """Tests for path blocking logic."""

    async def test_blocked_paths(self, mock_client: AsyncMock) -> None:
        """Test that various system paths are blocked."""
        blocked_paths = [
            "/etc/passwd",
            "/bin/bash",
            "/usr/bin/python",
            "/boot/grub",
            "/var/lib/dpkg",
        ]

        for path in blocked_paths:
            result = await files.write_file(
                mock_client, path=path, content="test", safe_mode=False
            )
            assert not result.success, f"Path {path} should be blocked"
            assert result.error.code == "PATH_BLOCKED"

    async def test_blocked_patterns(self, mock_client: AsyncMock) -> None:
        """Test that blocked file patterns are rejected."""
        blocked_files = [
            "/home/user/.bashrc",
            "/home/user/.ssh/authorized_keys",
            "/tmp/.profile",
        ]

        for path in blocked_files:
            result = await files.write_file(
                mock_client, path=path, content="test", safe_mode=False
            )
            assert not result.success, f"Pattern in {path} should be blocked"
            assert result.error.code == "PATH_BLOCKED"

    async def test_safe_paths_allowed(self, mock_client: AsyncMock) -> None:
        """Test that safe paths are allowed."""
        mock_client.call.return_value = 1

        safe_paths = [
            "/tmp/test.txt",
            "/var/tmp/test.txt",
            "/tmp/subdir/file.txt",
        ]

        for path in safe_paths:
            result = await files.write_file(
                mock_client, path=path, content="test", safe_mode=True
            )
            assert result.success, f"Path {path} should be allowed in safe mode"
