"""Tests for configuration management."""

import os

import pytest
from pydantic import ValidationError

from src.config import WebminConfig


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

    def test_config_missing_required_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing required fields raise ValidationError."""
        # Clear any environment variables that might be set
        monkeypatch.delenv("WEBMIN_HOST", raising=False)
        monkeypatch.delenv("WEBMIN_USERNAME", raising=False)
        monkeypatch.delenv("WEBMIN_PASSWORD", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            WebminConfig(_env_file=None)  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}

        assert "host" in missing_fields
        assert "username" in missing_fields
        assert "password" in missing_fields

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
