"""Configuration management for Webmin MCP Server.

Configuration is loaded from environment variables with sensible defaults.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebminConfig(BaseSettings):
    """Configuration for connecting to a Webmin server.

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
        description="Webmin username",
    )
    password: SecretStr = Field(
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


class ServerConfig(BaseSettings):
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


def get_webmin_config() -> WebminConfig:
    """Load and return Webmin configuration from environment."""
    return WebminConfig()


def get_server_config() -> ServerConfig:
    """Load and return MCP server configuration from environment."""
    return ServerConfig()
