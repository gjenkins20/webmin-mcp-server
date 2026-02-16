"""Shared pytest fixtures for Webmin MCP Server tests."""

from unittest.mock import MagicMock, patch
from typing import Any, Callable
import xmlrpc.client

import pytest
from pytest_httpx import HTTPXMock

from src.config import WebminConfig


@pytest.fixture
def webmin_config() -> WebminConfig:
    """Create a test Webmin configuration."""
    return WebminConfig(
        host="webmin.test.local",
        port=10000,
        use_https=True,
        verify_ssl=False,
        username="testuser",
        password="testpass",  # type: ignore[arg-type]
        connect_timeout=5.0,
        read_timeout=10.0,
    )


class MockXMLRPCProxy:
    """Mock XML-RPC ServerProxy for testing.

    Simulates Webmin XML-RPC responses.
    """

    def __init__(self) -> None:
        self._responses: dict[str, Any] = {}
        self._errors: dict[str, Exception] = {}

    def set_response(self, method: str, response: Any) -> None:
        """Set a response for a method call."""
        self._responses[method] = response

    def set_error(self, method: str, error: Exception) -> None:
        """Set an error for a method call."""
        self._errors[method] = error

    def __getattr__(self, name: str) -> Callable[..., Any]:
        """Handle method calls like webmin::get_webmin_version."""
        def method_call(*args: Any) -> Any:
            if name in self._errors:
                raise self._errors[name]
            if name in self._responses:
                return self._responses[name]
            raise xmlrpc.client.Fault(1, f"Unknown method: {name}")
        return method_call


@pytest.fixture
def mock_xmlrpc_proxy() -> MockXMLRPCProxy:
    """Create a mock XML-RPC proxy."""
    return MockXMLRPCProxy()


@pytest.fixture
def mock_xmlrpc_version_success(mock_xmlrpc_proxy: MockXMLRPCProxy) -> MockXMLRPCProxy:
    """Mock successful version retrieval via XML-RPC."""
    mock_xmlrpc_proxy.set_response("webmin::get_webmin_version", "2.105")
    mock_xmlrpc_proxy.set_response("webmin::get_system_hostname", "server.example.com")
    return mock_xmlrpc_proxy


@pytest.fixture
def mock_xmlrpc_auth_failure(mock_xmlrpc_proxy: MockXMLRPCProxy) -> MockXMLRPCProxy:
    """Mock authentication failure via XML-RPC."""
    mock_xmlrpc_proxy.set_error(
        "webmin::get_webmin_version",
        xmlrpc.client.ProtocolError(
            "https://webmin.test.local:10000/xmlrpc.cgi",
            401,
            "Unauthorized",
            {},
        )
    )
    return mock_xmlrpc_proxy


@pytest.fixture
def mock_xmlrpc_rpc_disabled(mock_xmlrpc_proxy: MockXMLRPCProxy) -> MockXMLRPCProxy:
    """Mock RPC permission denied."""
    mock_xmlrpc_proxy.set_error(
        "webmin::get_webmin_version",
        xmlrpc.client.ProtocolError(
            "https://webmin.test.local:10000/xmlrpc.cgi",
            403,
            "Forbidden",
            {},
        )
    )
    return mock_xmlrpc_proxy


@pytest.fixture
def mock_cgi_version_page(httpx_mock: HTTPXMock) -> HTTPXMock:
    """Mock Webmin main page with version info (CGI fallback)."""
    httpx_mock.add_response(
        method="GET",
        url="https://webmin.test.local:10000/",
        status_code=200,
        text="""
        <html>
        <head><title>Webmin 2.105 on server.example.com (Ubuntu Linux 22.04)</title></head>
        <body>
        <div class="brand">Webmin 2.105</div>
        </body>
        </html>
        """,
    )
    return httpx_mock


@pytest.fixture
def mock_cgi_auth_failure(httpx_mock: HTTPXMock) -> HTTPXMock:
    """Mock CGI authentication failure."""
    httpx_mock.add_response(
        method="GET",
        url="https://webmin.test.local:10000/",
        status_code=401,
        text="Unauthorized",
    )
    return httpx_mock
