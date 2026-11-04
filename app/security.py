"""Security helpers: SSRF guard, secrets, paths, rate limits."""

from __future__ import annotations

import ipaddress
import secrets as pysecrets
import re
import socket
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException, Request

_PRIVATE_NETS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
)

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.goog",
        "169.254.169.254",
    }
)

_ORDER_CODE_RE = re.compile(r"^ORD-[A-Z0-9]{4,16}$")


def verify_secret(provided: str, expected: str) -> bool:
    if not expected:
        return False
    a = provided.strip().encode("utf-8")
    b = expected.strip().encode("utf-8")
    if len(a) != len(b):
        return False
    return pysecrets.compare_digest(a, b)


def assert_public_scan_target(raw: str) -> str:
    """Normalize URL and block SSRF to private/metadata addresses."""
    t = (raw or "").strip()
    if len(t) > 2048:
        raise HTTPException(status_code=400, detail="Target URL too long.")
    if not t.startswith(("http://", "https://")):
        t = f"https://{t}"
    parsed = urlparse(t)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http(s) targets are allowed.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise HTTPException(status_code=400, detail="Invalid target host.")
    if host in _BLOCKED_HOSTS or host.endswith(".local"):
        raise HTTPException(status_code=400, detail="Target host is not allowed.")
    try:
        for fam, _, _, _, sockaddr in socket.getaddrinfo(host, None):
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            for net in _PRIVATE_NETS:
                if ip in net:
                    raise HTTPException(
                        status_code=400,
                        detail="Private or internal targets are not permitted.",
                    )
    except socket.gaierror:
        pass
    return t


def safe_report_path(reports_dir: Path, filename: str) -> Path:
    name = Path(filename).name
    if not name or name != filename.replace("\\", "/").split("/")[-1]:
        raise HTTPException(status_code=400, detail="Invalid report path.")
    if ".." in name or name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid report filename.")
    base = reports_dir.resolve()
    path = (base / name).resolve()
    if not str(path).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid report path.")
    return path


def normalize_order_code(code: str) -> str:
    c = (code or "").strip().upper()
    if not _ORDER_CODE_RE.match(c):
        raise HTTPException(status_code=400, detail="Invalid order code format.")
    return c


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        window_start = now - window_seconds
        bucket = self._hits[key]
        self._hits[key] = [t for t in bucket if t >= window_start]
        if len(self._hits[key]) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again shortly.",
            )
        self._hits[key].append(now)


limiter = SlidingWindowRateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return "unknown"
