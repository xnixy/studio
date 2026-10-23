"""URL validation to reduce SSRF risk when fetching competitor landing pages."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse


class UnsafeUrlError(ValueError):
    """Raised when a URL is not safe to fetch from application workers."""


_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata",
    }
)


def _host_is_blocked_name(host: str) -> bool:
    lowered = host.strip(".").lower()
    if lowered in _BLOCKED_HOSTS:
        return True
    if lowered.endswith(".localhost") or lowered.endswith(".local") or lowered.endswith(".internal"):
        return True
    return False


def _ip_is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        return False
    if ip.is_unspecified:
        return False
    # Cloud metadata / common link-local
    if isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("169.254.0.0/16"):
        return False
    return bool(ip.is_global)


def assert_public_http_url(url: str, *, allow_ports: frozenset[int] | None = None) -> str:
    """Validate *url* is absolute http(s) pointing at a public host.

    Resolves DNS and rejects private / loopback / link-local addresses.
    Returns the normalized URL string.
    """
    if not url or not isinstance(url, str):
        raise UnsafeUrlError("URL is required")
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("Only http and https URLs are allowed")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL host is required")
    if _host_is_blocked_name(host):
        raise UnsafeUrlError("Host is not allowed")

    ports = allow_ports or frozenset({80, 443})
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    if port not in ports:
        raise UnsafeUrlError(f"Port {port} is not allowed")

    # Literal IP in hostname
    try:
        literal = ipaddress.ip_address(host)
        if not _ip_is_public(literal):
            raise UnsafeUrlError("IP address is not publicly routable")
        return cleaned
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve host: {host}") from exc
    if not infos:
        raise UnsafeUrlError(f"Could not resolve host: {host}")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if not _ip_is_public(ip):
            raise UnsafeUrlError("Resolved address is not publicly routable")
    return cleaned


def resolve_redirect(base_url: str, location: str) -> str:
    """Join a Location header against the previous URL and re-validate."""
    if not location:
        raise UnsafeUrlError("Empty redirect location")
    joined = urljoin(base_url, location)
    return assert_public_http_url(joined)
