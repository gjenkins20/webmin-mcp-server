"""Configuration management for Webmin MCP Server.

Supports both single-server (env vars) and multi-server (JSON) configurations.
"""

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebminConfig(BaseSettings):
    """Configuration for connecting to a Webmin server (legacy single-server).

    All settings can be configured via environment variables with the
    WEBMIN_ prefix (e.g., WEBMIN_HOST, WEBMIN_USERNAME).
    """

    model_config = SettingsConfigDict(
        env_prefix="WEBMIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Connection settings
    host: str = Field(
        default="",
        description="Webmin server hostname or IP address",
    )
    port: int = Field(
        default=10000,
        description="Webmin server port",
        ge=1,
        le=65535,
    )
    use_https: bool = Field(
        default=True,
        description="Use HTTPS for connection",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificate (disable for self-signed certs)",
    )

    # Authentication
    username: str = Field(
        default="",
        description="Webmin username",
    )
    password: SecretStr = Field(
        default=SecretStr(""),
        description="Webmin password",
    )

    # Timeouts
    connect_timeout: float = Field(
        default=10.0,
        description="Connection timeout in seconds",
        gt=0,
    )
    read_timeout: float = Field(
        default=30.0,
        description="Read timeout in seconds",
        gt=0,
    )

    # Safety settings
    safe_mode: bool = Field(
        default=True,
        description="Enable safe mode to block dangerous operations",
    )

    @property
    def base_url(self) -> str:
        """Construct the base URL for the Webmin server."""
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{self.host}:{self.port}"


class ServerEntry(BaseModel):
    """Configuration for a single Webmin server in multi-server setup."""

    host: str = Field(description="Webmin server hostname or IP address")
    port: int = Field(default=10000, ge=1, le=65535)
    username: str = Field(description="Webmin username")
    password: str = Field(description="Webmin password")
    use_https: bool = Field(default=True)
    verify_ssl: bool = Field(default=True)
    safe_mode: bool = Field(default=True)
    connect_timeout: float = Field(default=10.0, gt=0)
    read_timeout: float = Field(default=30.0, gt=0)

    @property
    def base_url(self) -> str:
        """Construct the base URL for the Webmin server."""
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{self.host}:{self.port}"

    def to_webmin_config(self) -> WebminConfig:
        """Convert to WebminConfig for compatibility with existing code."""
        return WebminConfig(
            host=self.host,
            port=self.port,
            username=self.username,
            password=SecretStr(self.password),
            use_https=self.use_https,
            verify_ssl=self.verify_ssl,
            safe_mode=self.safe_mode,
            connect_timeout=self.connect_timeout,
            read_timeout=self.read_timeout,
        )


class MultiServerConfig(BaseModel):
    """Configuration for multiple Webmin servers."""

    default_server: str = Field(description="Alias of the default server")
    servers: dict[str, ServerEntry] = Field(description="Server configs by alias")

    def get_server(self, alias: str | None = None) -> tuple[str, ServerEntry]:
        """Get server config by alias, or default if not specified.

        Args:
            alias: Server alias, or None to use default.

        Returns:
            Tuple of (alias, ServerEntry).

        Raises:
            ValueError: If alias not found.
        """
        if alias is None:
            alias = self.default_server

        if alias not in self.servers:
            available = list(self.servers.keys())
            raise ValueError(
                f"Unknown server '{alias}'. Available servers: {available}"
            )

        return alias, self.servers[alias]

    def list_servers(self) -> list[dict[str, Any]]:
        """List all configured servers with metadata."""
        return [
            {
                "alias": alias,
                "host": config.host,
                "port": config.port,
                "is_default": alias == self.default_server,
                "safe_mode": config.safe_mode,
            }
            for alias, config in self.servers.items()
        ]


class MCPServerConfig(BaseSettings):
    """Configuration for the MCP server itself."""

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )


# Global config cache
_multi_server_config: MultiServerConfig | None = None


def load_multi_server_config() -> MultiServerConfig:
    """Load multi-server configuration from available sources.

    Priority:
    1. WEBMIN_CONFIG_FILE env var - path to JSON file
    2. WEBMIN_SERVERS_JSON env var - inline JSON string
    3. ./webmin-servers.json - local file
    4. ~/.config/webmin-mcp/servers.json - user config
    5. WEBMIN_* env vars - legacy single-server (creates "default" server)

    Returns:
        MultiServerConfig with one or more servers.

    Raises:
        ValueError: If no valid configuration found.
    """
    global _multi_server_config

    if _multi_server_config is not None:
        return _multi_server_config

    # Priority 1: Explicit config file path
    if config_file := os.environ.get("WEBMIN_CONFIG_FILE"):
        _multi_server_config = _load_from_file(Path(config_file))
        return _multi_server_config

    # Priority 2: Inline JSON in env var
    if json_str := os.environ.get("WEBMIN_SERVERS_JSON"):
        data = json.loads(json_str)
        _multi_server_config = MultiServerConfig(**data)
        return _multi_server_config

    # Priority 3: Local file
    local_file = Path("webmin-servers.json")
    if local_file.exists():
        _multi_server_config = _load_from_file(local_file)
        return _multi_server_config

    # Priority 4: User config directory
    user_config = Path.home() / ".config" / "webmin-mcp" / "servers.json"
    if user_config.exists():
        _multi_server_config = _load_from_file(user_config)
        return _multi_server_config

    # Priority 5: Legacy single-server env vars
    _multi_server_config = _load_legacy_config()
    return _multi_server_config


def _load_from_file(path: Path) -> MultiServerConfig:
    """Load multi-server config from JSON file."""
    with open(path) as f:
        data = json.load(f)
    return MultiServerConfig(**data)


def _load_legacy_config() -> MultiServerConfig:
    """Load legacy single-server config from WEBMIN_* env vars.

    Creates a MultiServerConfig with a single server named "default".
    """
    config = WebminConfig()

    if not config.host or not config.username:
        raise ValueError(
            "No Webmin configuration found. Either:\n"
            "  1. Create webmin-servers.json with multiple servers, or\n"
            "  2. Set WEBMIN_HOST, WEBMIN_USERNAME, WEBMIN_PASSWORD env vars"
        )

    return MultiServerConfig(
        default_server="default",
        servers={
            "default": ServerEntry(
                host=config.host,
                port=config.port,
                username=config.username,
                password=config.password.get_secret_value(),
                use_https=config.use_https,
                verify_ssl=config.verify_ssl,
                safe_mode=config.safe_mode,
                connect_timeout=config.connect_timeout,
                read_timeout=config.read_timeout,
            )
        },
    )


def reset_config_cache() -> None:
    """Reset the config cache. Useful for testing."""
    global _multi_server_config
    _multi_server_config = None


# Legacy functions for backward compatibility
def get_webmin_config() -> WebminConfig:
    """Load and return Webmin configuration from environment.

    Deprecated: Use load_multi_server_config() for multi-server support.
    """
    return WebminConfig()


def get_server_config() -> MCPServerConfig:
    """Load and return MCP server configuration from environment."""
    return MCPServerConfig()
