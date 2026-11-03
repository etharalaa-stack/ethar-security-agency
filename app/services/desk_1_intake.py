"""Desk 1: Scope validation and target reachability."""

import json
import re
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


def _normalize_url(target: str) -> str | None:
    t = target.strip()
    if not t:
        return None
    if not t.startswith(("http://", "https://")):
        t = f"https://{t}"
    parsed = urlparse(t)
    if not parsed.netloc:
        return None
    return t


async def run_intake_desk(
    target_asset: str,
    tech_notes: str | None,
    selected_parts: list[str],
) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    scope_valid = True
    normalized_target = target_asset.strip()

    if "part_1" in selected_parts or "part_3" in selected_parts:
        url = _normalize_url(target_asset)
        if not url:
            scope_valid = False
            findings.append(
                {
                    "severity": "HIGH",
                    "component": "Scope",
                    "observation": "Target domain/URL could not be parsed.",
                    "impact": "Audit cannot proceed without a valid HTTPS endpoint.",
                }
            )
        else:
            host = urlparse(url).hostname or ""
            if not DOMAIN_RE.match(host) and host not in ("localhost",):
                findings.append(
                    {
                        "severity": "MEDIUM",
                        "component": "Scope",
                        "observation": f"Non-standard hostname format: {host}",
                        "impact": "Manual triage recommended before external scanning.",
                    }
                )
            reachable, detail = await _check_http_reachability(url)
            normalized_target = url
            if not reachable:
                findings.append(
                    {
                        "severity": "MEDIUM",
                        "component": "Reachability",
                        "observation": detail,
                        "impact": "Passive header/TLS checks may be limited if endpoint is down.",
                    }
                )
            else:
                findings.append(
                    {
                        "severity": "INFO",
                        "component": "Reachability",
                        "observation": detail,
                        "impact": "Target responded to defensive connectivity check.",
                    }
                )

    elif "part_2" in selected_parts:
        blob = (tech_notes or "") + "\n" + target_asset
        if "dockerfile" not in blob.lower() and "docker-compose" not in blob.lower():
            if len(target_asset.strip()) < 20:
                findings.append(
                    {
                        "severity": "MEDIUM",
                        "component": "Scope",
                        "observation": "Limited container configuration provided in intake.",
                        "impact": "Desk 2 will apply pattern-based Dockerfile/compose lint only.",
                    }
                )

    elif "part_4" in selected_parts:
        os_hint = target_asset.lower()
        if not any(x in os_hint for x in ("ubuntu", "debian", "linux", "22.04", "24.04")):
            findings.append(
                {
                    "severity": "LOW",
                    "component": "Scope",
                    "observation": "OS version not explicitly specified; defaulting to Ubuntu 24.04 templates.",
                    "impact": "Hardening script uses Ubuntu/Debian-compatible defaults.",
                }
            )

    return {
        "scope_valid": scope_valid,
        "normalized_target": normalized_target,
        "intake_notes": tech_notes or "",
        "findings": findings,
        "selected_parts": selected_parts,
    }


async def _check_http_reachability(url: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            verify=True,
        ) as client:
            resp = await client.head(url)
            if resp.status_code >= 400:
                resp = await client.get(url)
            return True, f"HTTP {resp.status_code} from {url}"
    except httpx.HTTPError as exc:
        host = urlparse(url).hostname
        if host:
            try:
                socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
                return False, f"DNS resolves but HTTP failed: {exc}"
            except socket.gaierror:
                return False, f"DNS resolution failed for {host}"
        return False, f"Reachability check failed: {exc}"


def intake_summary_json(result: dict[str, Any]) -> str:
    return json.dumps(result, default=str)
