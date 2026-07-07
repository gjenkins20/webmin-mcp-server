"""Tests for the Webmin API client."""

import xmlrpc.client
from unittest.mock import patch, MagicMock

import pytest
from pytest_httpx import HTTPXMock

from src.config import WebminConfig
from src.webmin_client import (
    WebminAuthError,
    WebminClient,
    WebminClientError,
    WebminConnectionError,
    WebminRPCError,
)
from tests.conftest import MockXMLRPCProxy


class TestWebminClientXMLRPC:
    """Tests for XML-RPC operations."""

    async def test_get_version_via_xmlrpc(
        self,
        webmin_config: WebminConfig,
        mock_xmlrpc_version_success: MockXMLRPCProxy,
    ) -> None:
        """Test successful version retrieval via XML-RPC."""
        with patch("src.webmin_client.xmlrpc.client.ServerProxy") as mock_proxy_class:
            mock_proxy_class.return_value = mock_xmlrpc_version_success

            async with WebminClient(webmin_config) as client:
                version = await client.get_version()

            assert version.version == "2.105"
            assert version.hostname == "server.example.com"

    async def test_xmlrpc_auth_failure(
        self,
        webmin_config: WebminConfig,
        mock_xmlrpc_auth_failure: MockXMLRPCProxy,
    ) -> None:
        """Test authentication failure via XML-RPC."""
        with patch("src.webmin_client.xmlrpc.client.ServerProxy") as mock_proxy_class:
            mock_proxy_class.return_value = mock_xmlrpc_auth_failure

            async with WebminClient(webmin_config) as client:
                with pytest.raises(WebminAuthError) as exc_info:
                    await client.call("webmin", "get_webmin_version")

            assert "Authentication failed" in str(exc_info.value)
            assert "two-factor" in str(exc_info.value)

    async def test_xmlrpc_rpc_forbidden(
        self,
        webmin_config: WebminConfig,
        mock_xmlrpc_rpc_disabled: MockXMLRPCProxy,
    ) -> None:
        """Test RPC permission denied."""
        with patch("src.webmin_client.xmlrpc.client.ServerProxy") as mock_proxy_class:
            mock_proxy_class.return_value = mock_xmlrpc_rpc_disabled

            async with WebminClient(webmin_config) as client:
                with pytest.raises(WebminAuthError) as exc_info:
                    await client.call("webmin", "get_webmin_version")

            assert "RPC permissions" in str(exc_info.value)
            assert "RPC/API-only" in str(exc_info.value)

    async def test_xmlrpc_call_generic_method(
        self,
        webmin_config: WebminConfig,
        mock_xmlrpc_proxy: MockXMLRPCProxy,
    ) -> None:
        """Test calling a generic module function."""
        mock_xmlrpc_proxy.set_response("init::list_services", [
            {"name": "sshd", "status": "running"},
            {"name": "nginx", "status": "stopped"},
        ])

        with patch("src.webmin_client.xmlrpc.client.ServerProxy") as mock_proxy_class:
            mock_proxy_class.return_value = mock_xmlrpc_proxy

            async with WebminClient(webmin_config) as client:
                result = await client.call("init", "list_services")

            assert len(result) == 2
            assert result[0]["name"] == "sshd"

    async def test_xmlrpc_module_error(
        self,
        webmin_config: WebminConfig,
        mock_xmlrpc_proxy: MockXMLRPCProxy,
    ) -> None:
        """Test handling Webmin module errors."""
        mock_xmlrpc_proxy.set_error(
            "cron::create_job",
            xmlrpc.client.Fault(100, "Invalid cron expression"),
        )

        with patch("src.webmin_client.xmlrpc.client.ServerProxy") as mock_proxy_class:
            mock_proxy_class.return_value = mock_xmlrpc_proxy

            async with WebminClient(webmin_config) as client:
                with pytest.raises(WebminRPCError) as exc_info:
                    await client.call("cron", "create_job", "invalid")

            assert "Invalid cron expression" in str(exc_info.value)


class TestWebminClientCGIFallback:
    """Tests for CGI fallback operations."""

    async def test_get_version_via_cgi_fallback(
        self,
        webmin_config: WebminConfig,
        mock_xmlrpc_proxy: MockXMLRPCProxy,
        mock_cgi_version_page: HTTPXMock,
    ) -> None:
        """Test version retrieval falls back to CGI when XML-RPC fails."""
        # Make XML-RPC fail with RPC error (not auth)
        mock_xmlrpc_proxy.set_error(
            "webmin::get_webmin_version",
            xmlrpc.client.Fault(1, "Function not found"),
        )

        with patch("src.webmin_client.xmlrpc.client.ServerProxy") as mock_proxy_class:
            mock_proxy_class.return_value = mock_xmlrpc_proxy

            async with WebminClient(webmin_config) as client:
                version = await client.get_version()

            assert version.version == "2.105"
            assert version.hostname == "server.example.com"

    async def test_cgi_request(
        self,
        webmin_config: WebminConfig,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test direct CGI request."""
        httpx_mock.add_response(
            method="GET",
            url="https://webmin.test.local:10000/proc/index.cgi?json=1",
            status_code=200,
            json={"processes": [{"pid": 1, "name": "init"}]},
        )

        with patch("src.webmin_client.xmlrpc.client.ServerProxy"):
            async with WebminClient(webmin_config) as client:
                response = await client.cgi_request(
                    "GET",
                    "/proc/index.cgi",
                    params={"json": "1"},
                )

            assert response.status_code == 200
            assert response.json()["processes"][0]["pid"] == 1


class TestWebminClientContextManager:
    """Tests for client context manager behavior."""

    async def test_client_requires_context_manager(
        self,
        webmin_config: WebminConfig,
    ) -> None:
        """Test that client operations fail without context manager."""
        client = WebminClient(webmin_config)

        with pytest.raises(WebminClientError) as exc_info:
            await client.call("webmin", "get_webmin_version")

        assert "Client not initialized" in str(exc_info.value)

    async def test_check_rpc_available_returns_true(
        self,
        webmin_config: WebminConfig,
        mock_xmlrpc_version_success: MockXMLRPCProxy,
    ) -> None:
        """Test check_rpc_available returns True when RPC works."""
        with patch("src.webmin_client.xmlrpc.client.ServerProxy") as mock_proxy_class:
            mock_proxy_class.return_value = mock_xmlrpc_version_success

            async with WebminClient(webmin_config) as client:
                result = await client.check_rpc_available()

            assert result is True

    async def test_check_rpc_available_returns_false(
        self,
        webmin_config: WebminConfig,
        mock_xmlrpc_auth_failure: MockXMLRPCProxy,
    ) -> None:
        """Test check_rpc_available returns False when RPC fails."""
        with patch("src.webmin_client.xmlrpc.client.ServerProxy") as mock_proxy_class:
            mock_proxy_class.return_value = mock_xmlrpc_auth_failure

            async with WebminClient(webmin_config) as client:
                result = await client.check_rpc_available()

            assert result is False


class TestWebminClientURLBuilding:
    """Tests for URL building."""

    def test_xmlrpc_url_https(self, webmin_config: WebminConfig) -> None:
        """Test XML-RPC URL building with HTTPS."""
        client = WebminClient(webmin_config)
        url = client._build_xmlrpc_url()

        assert url == "https://testuser:testpass@webmin.test.local:10000/xmlrpc.cgi"

    def test_xmlrpc_url_http(self) -> None:
        """Test XML-RPC URL building with HTTP."""
        config = WebminConfig(
            host="webmin.test.local",
            port=10000,
            use_https=False,
            username="admin",
            password="secret",  # type: ignore[arg-type]
        )
        client = WebminClient(config)
        url = client._build_xmlrpc_url()

        assert url == "http://admin:secret@webmin.test.local:10000/xmlrpc.cgi"

    def test_xmlrpc_url_special_chars(self) -> None:
        """Test XML-RPC URL building with special characters in password."""
        config = WebminConfig(
            host="webmin.test.local",
            port=10000,
            use_https=True,
            username="admin",
            password="p@ss:word/123",  # type: ignore[arg-type]
        )
        client = WebminClient(config)
        url = client._build_xmlrpc_url()

        # Special chars should be URL-encoded
        assert "p%40ss%3Aword%2F123" in url
        assert "@webmin.test.local" in url
