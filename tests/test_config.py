"""Tests for configuration management."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config import (
    MultiServerConfig,
    ServerEntry,
    WebminConfig,
    load_multi_server_config,
    reset_config_cache,
)


class TestWebminConfig:
    """Tests for WebminConfig."""

    def test_config_from_explicit_values(self) -> None:
        """Test creating config with explicit values."""
        config = WebminConfig(
            host="192.168.1.100",
            username="admin",
            password="secret",  # type: ignore[arg-type]
        )

        assert config.host == "192.168.1.100"
        assert config.port == 10000  # default
        assert config.use_https is True  # default
        assert config.username == "admin"
        assert config.password.get_secret_value() == "secret"

    def test_config_base_url_https(self) -> None:
        """Test base_url property with HTTPS."""
        config = WebminConfig(
            host="webmin.example.com",
            port=10000,
            use_https=True,
            username="admin",
            password="secret",  # type: ignore[arg-type]
        )

        assert config.base_url == "https://webmin.example.com:10000"

    def test_config_base_url_http(self) -> None:
        """Test base_url property with HTTP."""
        config = WebminConfig(
            host="webmin.example.com",
            port=8080,
            use_https=False,
            username="admin",
            password="secret",  # type: ignore[arg-type]
        )

        assert config.base_url == "http://webmin.example.com:8080"

    def test_config_allows_empty_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that WebminConfig allows empty defaults for multi-server support."""
        # Clear any environment variables that might be set
        monkeypatch.delenv("WEBMIN_HOST", raising=False)
        monkeypatch.delenv("WEBMIN_USERNAME", raising=False)
        monkeypatch.delenv("WEBMIN_PASSWORD", raising=False)

        # Should not raise - empty defaults are allowed
        config = WebminConfig(_env_file=None)  # type: ignore[call-arg]

        assert config.host == ""
        assert config.username == ""
        assert config.password.get_secret_value() == ""

    def test_config_invalid_port(self) -> None:
        """Test that invalid port raises ValidationError."""
        with pytest.raises(ValidationError):
            WebminConfig(
                host="localhost",
                port=99999,  # invalid
                username="admin",
                password="secret",  # type: ignore[arg-type]
            )

    def test_config_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading config from environment variables."""
        monkeypatch.setenv("WEBMIN_HOST", "env-host.example.com")
        monkeypatch.setenv("WEBMIN_PORT", "10001")
        monkeypatch.setenv("WEBMIN_USERNAME", "envuser")
        monkeypatch.setenv("WEBMIN_PASSWORD", "envpass")
        monkeypatch.setenv("WEBMIN_USE_HTTPS", "false")

        config = WebminConfig()  # type: ignore[call-arg]

        assert config.host == "env-host.example.com"
        assert config.port == 10001
        assert config.username == "envuser"
        assert config.password.get_secret_value() == "envpass"
        assert config.use_https is False

    def test_password_not_exposed_in_repr(self) -> None:
        """Test that password is not exposed in string representation."""
        config = WebminConfig(
            host="localhost",
            username="admin",
            password="supersecret",  # type: ignore[arg-type]
        )

        repr_str = repr(config)
        str_str = str(config)

        assert "supersecret" not in repr_str
        assert "supersecret" not in str_str


class TestServerEntry:
    """Tests for ServerEntry model."""

    def test_server_entry_defaults(self) -> None:
        """Test ServerEntry with minimal required fields."""
        entry = ServerEntry(
            host="192.168.1.100",
            username="admin",
            password="secret",
        )

        assert entry.host == "192.168.1.100"
        assert entry.port == 10000
        assert entry.use_https is True
        assert entry.verify_ssl is True
        assert entry.safe_mode is True

    def test_server_entry_to_webmin_config(self) -> None:
        """Test converting ServerEntry to WebminConfig."""
        entry = ServerEntry(
            host="192.168.1.100",
            port=10001,
            username="admin",
            password="secret",
            use_https=False,
            safe_mode=False,
        )

        config = entry.to_webmin_config()

        assert config.host == "192.168.1.100"
        assert config.port == 10001
        assert config.username == "admin"
        assert config.password.get_secret_value() == "secret"
        assert config.use_https is False
        assert config.safe_mode is False


class TestMultiServerConfig:
    """Tests for MultiServerConfig model."""

    def test_multi_server_config_get_server_default(self) -> None:
        """Test getting default server."""
        config = MultiServerConfig(
            default_server="pi1",
            servers={
                "pi1": ServerEntry(host="192.168.1.100", username="admin", password="pass1"),
                "pi2": ServerEntry(host="192.168.1.101", username="admin", password="pass2"),
            },
        )

        alias, server = config.get_server()

        assert alias == "pi1"
        assert server.host == "192.168.1.100"

    def test_multi_server_config_get_server_by_alias(self) -> None:
        """Test getting server by alias."""
        config = MultiServerConfig(
            default_server="pi1",
            servers={
                "pi1": ServerEntry(host="192.168.1.100", username="admin", password="pass1"),
                "pi2": ServerEntry(host="192.168.1.101", username="admin", password="pass2"),
            },
        )

        alias, server = config.get_server("pi2")

        assert alias == "pi2"
        assert server.host == "192.168.1.101"

    def test_multi_server_config_get_server_unknown(self) -> None:
        """Test getting unknown server raises error."""
        config = MultiServerConfig(
            default_server="pi1",
            servers={
                "pi1": ServerEntry(host="192.168.1.100", username="admin", password="pass1"),
            },
        )

        with pytest.raises(ValueError) as exc_info:
            config.get_server("unknown")

        assert "Unknown server 'unknown'" in str(exc_info.value)
        assert "pi1" in str(exc_info.value)

    def test_multi_server_config_list_servers(self) -> None:
        """Test listing servers."""
        config = MultiServerConfig(
            default_server="pi1",
            servers={
                "pi1": ServerEntry(host="192.168.1.100", username="admin", password="pass1"),
                "pi2": ServerEntry(host="192.168.1.101", username="admin", password="pass2", safe_mode=False),
            },
        )

        servers = config.list_servers()

        assert len(servers) == 2
        pi1 = next(s for s in servers if s["alias"] == "pi1")
        pi2 = next(s for s in servers if s["alias"] == "pi2")

        assert pi1["is_default"] is True
        assert pi1["safe_mode"] is True
        assert pi2["is_default"] is False
        assert pi2["safe_mode"] is False


class TestLoadMultiServerConfig:
    """Tests for load_multi_server_config function."""

    def setup_method(self) -> None:
        """Reset config cache before each test."""
        reset_config_cache()

    def teardown_method(self) -> None:
        """Reset config cache after each test."""
        reset_config_cache()

    def test_load_from_json_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading config from WEBMIN_SERVERS_JSON env var."""
        json_config = json.dumps({
            "default_server": "test",
            "servers": {
                "test": {
                    "host": "test.local",
                    "username": "testuser",
                    "password": "testpass",
                }
            }
        })
        monkeypatch.setenv("WEBMIN_SERVERS_JSON", json_config)
        monkeypatch.delenv("WEBMIN_CONFIG_FILE", raising=False)

        config = load_multi_server_config()

        assert config.default_server == "test"
        assert "test" in config.servers
        assert config.servers["test"].host == "test.local"

    def test_load_from_legacy_env_vars(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test loading config from legacy WEBMIN_* env vars."""
        monkeypatch.delenv("WEBMIN_SERVERS_JSON", raising=False)
        monkeypatch.delenv("WEBMIN_CONFIG_FILE", raising=False)
        monkeypatch.setenv("WEBMIN_HOST", "legacy.local")
        monkeypatch.setenv("WEBMIN_USERNAME", "legacyuser")
        monkeypatch.setenv("WEBMIN_PASSWORD", "legacypass")

        # Change to temp directory to avoid loading local webmin-servers.json
        monkeypatch.chdir(tmp_path)

        config = load_multi_server_config()

        assert config.default_server == "default"
        assert "default" in config.servers
        assert config.servers["default"].host == "legacy.local"
        assert config.servers["default"].username == "legacyuser"

    def test_load_missing_config_raises_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that missing config raises ValueError."""
        monkeypatch.delenv("WEBMIN_SERVERS_JSON", raising=False)
        monkeypatch.delenv("WEBMIN_CONFIG_FILE", raising=False)
        monkeypatch.delenv("WEBMIN_HOST", raising=False)
        monkeypatch.delenv("WEBMIN_USERNAME", raising=False)
        monkeypatch.delenv("WEBMIN_PASSWORD", raising=False)

        # Change to temp directory to avoid loading .env file from project root
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError) as exc_info:
            load_multi_server_config()

        assert "No Webmin configuration found" in str(exc_info.value)
