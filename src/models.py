"""Pydantic models for Webmin MCP Server request/response types."""

from typing import Any

from pydantic import BaseModel, Field


class WebminVersion(BaseModel):
    """Information about the Webmin server version."""

    version: str = Field(
        description="Webmin version string (e.g., '2.105')",
    )
    hostname: str | None = Field(
        default=None,
        description="Hostname of the Webmin server",
    )


class WebminError(BaseModel):
    """Error response from Webmin operations."""

    code: str = Field(
        description="Error code for programmatic handling",
    )
    message: str = Field(
        description="Human-readable error message",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error context",
    )


class ToolResult(BaseModel):
    """Generic result wrapper for MCP tool responses."""

    success: bool = Field(
        description="Whether the operation succeeded",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Result data on success",
    )
    error: WebminError | None = Field(
        default=None,
        description="Error details on failure",
    )

    @classmethod
    def ok(cls, data: dict[str, Any]) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, data=data)

    @classmethod
    def fail(
        cls,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> "ToolResult":
        """Create a failure result."""
        return cls(
            success=False,
            error=WebminError(code=code, message=message, details=details),
        )
