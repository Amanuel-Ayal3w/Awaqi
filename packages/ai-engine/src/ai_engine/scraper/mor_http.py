"""Shared HTTP client settings for outbound MoR requests."""

from __future__ import annotations

import logging
import os
import ssl

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = os.getenv("MOR_SCRAPER_USER_AGENT", "AwaqiBot/1.0 (+https://github.com/aait/Awaqi)")


def mor_http_verify() -> bool | ssl.SSLContext:
    """
    SSL verification for mor.gov.et.

    MoR's certificate chain often fails on macOS/Python (``CERTIFICATE_VERIFY_FAILED``)
    while ``curl`` still works. Default is ``false`` so scraping works out of the box;
    set ``MOR_HTTP_SSL_VERIFY=true`` when the host presents a valid chain in your env.
    """
    raw = os.getenv("MOR_HTTP_SSL_VERIFY", "false").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return True
    return False


def create_mor_http_client(**extra: object) -> httpx.AsyncClient:
    """Build an ``httpx.AsyncClient`` configured for MoR API + PDF downloads."""
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(120.0, connect=30.0)
    verify = mor_http_verify()
    if verify is False:
        logger.debug("mor_http_client ssl_verify=disabled (MOR_HTTP_SSL_VERIFY)")
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        limits=limits,
        timeout=timeout,
        follow_redirects=True,
        verify=verify,
        **extra,  # type: ignore[arg-type]
    )
