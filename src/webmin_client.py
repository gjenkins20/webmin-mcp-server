"""Webmin API client using XML-RPC as primary transport.

This module handles XML-RPC communication with Webmin servers, with
CGI fallback for modules that don't support XML-RPC well.
"""

import asyncio
import logging
import re
import ssl
import xmlrpc.client
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Self
from urllib.parse import quote

import httpx

from .config import WebminConfig
from .models import WebminVersion

logger = logging.getLogger(__name__)

# Thread pool for running synchronous XML-RPC calls
_executor = ThreadPoolExecutor(max_workers=4)


class WebminClientError(Exception):
    """Base exception for Webmin client errors."""

    def __init__(self, message: str, code: str = "WEBMIN_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class WebminAuthError(WebminClientError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTH_ERROR")


class WebminConnectionError(WebminClientError):
    """Connection to Webmin server failed."""

    def __init__(self, message: str = "Connection failed") -> None:
        super().__init__(message, code="CONNECTION_ERROR")


class WebminRPCError(WebminClientError):
    """XML-RPC call failed."""

    def __init__(self, message: str = "RPC call failed") -> None:
        super().__init__(message, code="RPC_ERROR")


class SafeTransport(xmlrpc.client.SafeTransport):
    """Custom HTTPS transport that can skip SSL verification."""

    def __init__(self, verify_ssl: bool = True, timeout: float = 30.0) -> None:
        super().__init__()
        self._verify_ssl = verify_ssl
        self._timeout = timeout

    def make_connection(self, host: str) -> Any:
        """Create connection with custom SSL context."""
        conn = super().make_connection(host)
        if not self._verify_ssl:
            # Create unverified SSL context for self-signed certs
            conn._http_vsn = 11
            conn._http_vsn_str = "HTTP/1.1"
            if hasattr(conn, "_context"):
                conn._context = ssl._create_unverified_context()
        conn.timeout = self._timeout
        return conn


class WebminClient:
    """Client for Webmin API operations using XML-RPC.

    Uses XML-RPC (/xmlrpc.cgi) as the primary transport with HTTP Basic Auth.
    Falls back to CGI requests for operations not well-supported by XML-RPC.

    Usage:
        async with WebminClient(config) as client:
            version = await client.get_version()
            services = await client.call("init", "list_services")
    """

    def __init__(self, config: WebminConfig) -> None:
        """Initialize the Webmin client.

        Args:
            config: Webmin connection configuration.
        """
        self._config = config
        self._proxy: xmlrpc.client.ServerProxy | None = None
        self._http_client: httpx.AsyncClient | None = None

    def _build_xmlrpc_url(self) -> str:
        """Build XML-RPC URL with embedded Basic Auth credentials.

        Returns:
            URL like https://user:pass@host:port/xmlrpc.cgi
        """
        scheme = "https" if self._config.use_https else "http"
        # URL-encode username and password for special characters
        username = quote(self._config.username, safe="")
        password = quote(self._config.password.get_secret_value(), safe="")
        return (
            f"{scheme}://{username}:{password}@"
            f"{self._config.host}:{self._config.port}/xmlrpc.cgi"
        )

    async def __aenter__(self) -> Self:
        """Enter async context and create clients."""
        # Create XML-RPC proxy with custom transport
        transport = SafeTransport(
            verify_ssl=self._config.verify_ssl,
            timeout=self._config.read_timeout,
        )
        self._proxy = xmlrpc.client.ServerProxy(
            self._build_xmlrpc_url(),
            transport=transport,
            allow_none=True,
        )

        # Create HTTP client for CGI fallback
        self._http_client = httpx.AsyncClient(
            base_url=self._config.base_url,
            verify=self._config.verify_ssl,
            auth=(
                self._config.username,
                self._config.password.get_secret_value(),
            ),
            timeout=httpx.Timeout(
                connect=self._config.connect_timeout,
                read=self._config.read_timeout,
                write=self._config.read_timeout,
                pool=self._config.connect_timeout,
            ),
        )

        logger.debug("Webmin client initialized for %s", self._config.base_url)
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context and close clients."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        # ServerProxy doesn't need explicit cleanup
        self._proxy = None

    def _ensure_proxy(self) -> xmlrpc.client.ServerProxy:
        """Ensure XML-RPC proxy is available."""
        if self._proxy is None:
            raise WebminClientError(
                "Client not initialized. Use 'async with WebminClient(...)' context.",
                code="CLIENT_NOT_INITIALIZED",
            )
        return self._proxy

    def _ensure_http_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is available for CGI fallback."""
        if self._http_client is None:
            raise WebminClientError(
                "Client not initialized. Use 'async with WebminClient(...)' context.",
                code="CLIENT_NOT_INITIALIZED",
            )
        return self._http_client

    async def call(
        self,
        module: str,
        function: str,
        *args: Any,
    ) -> Any:
        """Call a Webmin module function via XML-RPC.

        Args:
            module: Webmin module name (e.g., "webmin", "init", "cron").
            function: Function name within the module.
            *args: Arguments to pass to the function.

        Returns:
            Result from the XML-RPC call.

        Raises:
            WebminAuthError: If authentication fails.
            WebminConnectionError: If connection fails.
            WebminRPCError: If the RPC call fails.
        """
        proxy = self._ensure_proxy()
        method_name = f"{module}::{function}"

        logger.debug("XML-RPC call: %s(%s)", method_name, args)

        def _do_call() -> Any:
            """Execute XML-RPC call synchronously."""
            method = getattr(proxy, method_name)
            return method(*args)

        try:
            # Run synchronous XML-RPC call in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(_executor, _do_call)
            logger.debug("XML-RPC result: %s", result)
            return result

        except xmlrpc.client.ProtocolError as e:
            if e.errcode == 401:
                raise WebminAuthError(
                    "Authentication failed. Check username/password and "
                    "ensure user has 'Can accept RPC calls' permission. If "
                    "this account has two-factor authentication enabled, "
                    "Webmin 2.640+ rejects RPC requests the same way — use "
                    "an account without 2FA, or a dedicated RPC/API-only "
                    "account (Webmin 2.650+)."
                ) from e
            elif e.errcode == 403:
                raise WebminAuthError(
                    "Access forbidden. User may not have RPC permissions. "
                    "If this account has two-factor authentication enabled, "
                    "Webmin 2.640+ rejects RPC requests the same way — use "
                    "an account without 2FA, or a dedicated RPC/API-only "
                    "account (Webmin 2.650+)."
                ) from e
            elif e.errcode == 404:
                raise WebminRPCError(
                    "XML-RPC endpoint not found. Ensure Webmin has "
                    "XML-RPC enabled (/xmlrpc.cgi)."
                ) from e
            else:
                raise WebminRPCError(
                    f"XML-RPC protocol error: HTTP {e.errcode} {e.errmsg}"
                ) from e

        except xmlrpc.client.Fault as e:
            # Webmin module/function error
            raise WebminRPCError(
                f"Webmin error in {method_name}: {e.faultString}"
            ) from e

        except ConnectionRefusedError as e:
            raise WebminConnectionError(
                f"Connection refused to {self._config.base_url}"
            ) from e

        except TimeoutError as e:
            raise WebminConnectionError("Connection timed out") from e

        except OSError as e:
            # Covers various network errors
            raise WebminConnectionError(f"Network error: {e}") from e

        except ssl.SSLError as e:
            raise WebminConnectionError(
                f"SSL error: {e}. Try setting WEBMIN_VERIFY_SSL=false for "
                "self-signed certificates."
            ) from e

    async def get_version(self) -> WebminVersion:
        """Get the Webmin server version.

        Uses XML-RPC to call webmin::get_webmin_version().

        Returns:
            WebminVersion with version string and hostname.

        Raises:
            WebminClientError: If version cannot be retrieved.
        """
        logger.debug("Fetching Webmin version via XML-RPC")

        try:
            # Try XML-RPC first
            version = await self.call("webmin", "get_webmin_version")

            # Also try to get hostname
            hostname = None
            try:
                hostname = await self.call("webmin", "get_system_hostname")
            except WebminRPCError:
                # Hostname is optional, don't fail if unavailable
                logger.debug("Could not get hostname via XML-RPC")

            return WebminVersion(version=str(version), hostname=hostname)

        except WebminRPCError as e:
            # Fall back to CGI if XML-RPC fails
            logger.warning(
                "XML-RPC version call failed, trying CGI fallback: %s", e
            )
            return await self._get_version_via_cgi()

    async def _get_version_via_cgi(self) -> WebminVersion:
        """Get version by parsing the Webmin main page (CGI fallback).

        Returns:
            WebminVersion with version string and hostname.

        Raises:
            WebminClientError: If version cannot be retrieved.
        """
        client = self._ensure_http_client()

        try:
            response = await client.get("/")
        except httpx.ConnectError as e:
            raise WebminConnectionError(
                f"Failed to connect to Webmin: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise WebminConnectionError(f"Connection timed out: {e}") from e

        if response.status_code == 401:
            raise WebminAuthError("Authentication failed")

        if response.status_code != 200:
            raise WebminClientError(
                f"Failed to get version: HTTP {response.status_code}",
                code="VERSION_ERROR",
            )

        html = response.text
        version = self._parse_version_from_html(html)
        hostname = self._parse_hostname_from_html(html)

        return WebminVersion(version=version, hostname=hostname)

    def _parse_version_from_html(self, html: str) -> str:
        """Extract version string from Webmin HTML response.

        Args:
            html: HTML content from Webmin page.

        Returns:
            Version string.

        Raises:
            WebminClientError: If version cannot be parsed.
        """
        patterns = [
            r"Webmin\s+(\d+\.\d+(?:\.\d+)?)",  # "Webmin 2.105"
            r"version\s+(\d+\.\d+(?:\.\d+)?)",  # "version 2.105"
            r"<title>.*?(\d+\.\d+(?:\.\d+)?).*?</title>",  # In title
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)

        raise WebminClientError(
            "Could not parse Webmin version from response",
            code="PARSE_ERROR",
        )

    def _parse_hostname_from_html(self, html: str) -> str | None:
        """Extract hostname from Webmin HTML response.

        Args:
            html: HTML content from Webmin page.

        Returns:
            Hostname if found, None otherwise.
        """
        pattern = r"on\s+([a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9])"
        match = re.search(pattern, html)
        if match:
            return match.group(1)
        return None

    async def cgi_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request to a Webmin CGI endpoint.

        Use this for operations not well-supported by XML-RPC.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: CGI path (e.g., "/proc/index.cgi").
            **kwargs: Additional arguments for httpx.

        Returns:
            HTTP response.

        Raises:
            WebminClientError: If request fails.
        """
        client = self._ensure_http_client()

        try:
            response = await client.request(method, path, **kwargs)
            return response
        except httpx.ConnectError as e:
            raise WebminConnectionError(
                f"Failed to connect to Webmin: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise WebminConnectionError(f"Request timed out: {e}") from e

    async def check_rpc_available(self) -> bool:
        """Check if XML-RPC is available and configured.

        Returns:
            True if XML-RPC works, False otherwise.
        """
        try:
            await self.call("webmin", "get_webmin_version")
            return True
        except (WebminAuthError, WebminRPCError, WebminConnectionError):
            return False
