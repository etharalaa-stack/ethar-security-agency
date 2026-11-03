"""Desk 2: Passive defensive security and configuration audit."""

import json
import re
import socket
import ssl
from typing import Any
from urllib.parse import urlparse

import httpx

SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
]

SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{8,}", "Possible secret in configuration"),
    (r"AKIA[0-9A-Z]{16}", "Possible AWS access key pattern"),
    (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "Private key material in snippet"),
]

DOCKER_ISSUES = [
    (r"(?i)^USER\s+root\s*$", "Container may run as root"),
    (r"(?i)--privileged", "Privileged container flag detected"),
    (r"(?i)0\.0\.0\.0:\d+", "Service bound to all interfaces"),
    (r"(?i)password\s*:\s*\S+", "Plaintext password in compose file"),
]


async def run_audit_desk(
    target_asset: str,
    intake: dict[str, Any],
    tech_notes: str | None,
    selected_parts: list[str],
) -> dict[str, Any]:
    findings: list[dict[str, str]] = list(intake.get("findings") or [])
    config_blob = "\n".join(filter(None, [target_asset, tech_notes or ""]))
    url = intake.get("normalized_target") or target_asset
    host = urlparse(url if "://" in url else f"https://{url}").hostname if url else None

    if "part_1" in selected_parts:
        findings.extend(await _audit_http_headers(url))
        if host:
            findings.extend(_audit_tls(host))
            findings.extend(await _audit_dns_email(host))

    if "part_2" in selected_parts and config_blob:
        findings.extend(_audit_docker_and_secrets(config_blob))

    if "part_3" in selected_parts:
        findings.extend(await _audit_edge_waf(url))

    if "part_4" in selected_parts:
        findings.extend(_audit_vps_metadata(target_asset, tech_notes))

    if "part_5" in selected_parts:
        findings.extend(_audit_cicd_access(config_blob))

    score = _compute_posture_score(findings)
    return {
        "findings": findings,
        "posture_score": score,
        "audit_metadata": {
            "selected_parts": selected_parts,
            "target": intake.get("normalized_target", target_asset),
        },
    }


async def _audit_dns_email(hostname: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for rr_type, label in (("TXT", "SPF/DMARC"),):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://cloudflare-dns.com/dns-query",
                    params={"name": hostname, "type": rr_type},
                    headers={"accept": "application/dns-json"},
                )
                resp.raise_for_status()
                data = resp.json()
            answers = data.get("Answer") or []
            txt = " ".join(a.get("data", "") for a in answers).lower()
            if "v=spf1" not in txt:
                results.append(
                    {
                        "severity": "MEDIUM",
                        "component": "DNS Email",
                        "observation": "No SPF (v=spf1) TXT record detected at apex.",
                        "impact": "Email spoofing risk for domain; publish SPF at DNS.",
                    }
                )
            if "v=dmarc1" not in txt:
                results.append(
                    {
                        "severity": "MEDIUM",
                        "component": "DNS Email",
                        "observation": "No DMARC (v=DMARC1) policy detected.",
                        "impact": "Limited visibility and control over abusive email streams.",
                    }
                )
            if "v=spf1" in txt and "v=dmarc1" in txt:
                results.append(
                    {
                        "severity": "INFO",
                        "component": "DNS Email",
                        "observation": f"{label} records present (passive DNS lookup).",
                        "impact": "Validate policy strictness (p=reject/quarantine).",
                    }
                )
        except httpx.HTTPError as exc:
            results.append(
                {
                    "severity": "LOW",
                    "component": "DNS Email",
                    "observation": f"Passive DNS lookup failed: {exc}",
                    "impact": "Manual DNS review recommended.",
                }
            )
    return results


async def _audit_edge_waf(url: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    if not url.startswith("http"):
        url = f"https://{url}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url)
        headers = {k.lower(): v for k, v in resp.headers.items()}
        if "cf-ray" in headers:
            results.append(
                {
                    "severity": "INFO",
                    "component": "Cloudflare Edge",
                    "observation": f"Cloudflare proxy detected (CF-RAY present).",
                    "impact": "Validate WAF custom rules and rate limits in Cloudflare dashboard.",
                }
            )
        else:
            results.append(
                {
                    "severity": "LOW",
                    "component": "Cloudflare Edge",
                    "observation": "No Cloudflare CF-RAY header on sampled response.",
                    "impact": "If Cloudflare is planned, configure Transform Rules and rate limiting.",
                }
            )
        if "cf-cache-status" not in headers:
            results.append(
                {
                    "severity": "LOW",
                    "component": "Cloudflare Edge",
                    "observation": "Cache status header absent; edge caching policy unclear.",
                    "impact": "Define cache rules to reduce origin load and abuse surface.",
                }
            )
    except httpx.HTTPError as exc:
        results.append(
            {
                "severity": "MEDIUM",
                "component": "Edge WAF",
                "observation": f"Edge posture sample failed: {exc}",
                "impact": "Could not assess CDN/WAF headers passively.",
            }
        )
    return results


def _audit_cicd_access(blob: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    lower = blob.lower()
    if any(k in lower for k in (".github/workflows", "gitlab-ci", "jenkins", "circleci")):
        results.append(
            {
                "severity": "INFO",
                "component": "CI/CD",
                "observation": "CI/CD pipeline references found in submitted scope.",
                "impact": "Review secret injection, branch protections, and artifact signing.",
            }
        )
    else:
        results.append(
            {
                "severity": "LOW",
                "component": "CI/CD",
                "observation": "No CI/CD manifest detected in intake text.",
                "impact": "Provide workflow YAML for deeper access-control review.",
            }
        )
    if "0.0.0.0" in blob or "bind: 0.0.0.0" in lower:
        results.append(
            {
                "severity": "MEDIUM",
                "component": "Network Isolation",
                "observation": "Wide network bind patterns referenced in configuration.",
                "impact": "Restrict services to private subnets and security groups.",
            }
        )
    if "backup" not in lower:
        results.append(
            {
                "severity": "LOW",
                "component": "Backup Policy",
                "observation": "No backup/retention policy described in intake.",
                "impact": "Document RPO/RTO and encrypted off-site backups.",
            }
        )
    return results


async def _audit_http_headers(url: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    if not url.startswith("http"):
        url = f"https://{url}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
        headers = {k.lower(): v for k, v in resp.headers.items()}

        for h in SECURITY_HEADERS:
            if h not in headers:
                results.append(
                    {
                        "severity": "MEDIUM" if h == "strict-transport-security" else "LOW",
                        "component": "HTTP Headers",
                        "observation": f"Missing {h} header.",
                        "impact": "Increased risk of downgrade, clickjacking, or MIME sniffing attacks.",
                    }
                )
            else:
                results.append(
                    {
                        "severity": "INFO",
                        "component": "HTTP Headers",
                        "observation": f"{h}: {headers[h][:120]}",
                        "impact": "Header present — verify policy strictness in remediation.",
                    }
                )

        server = headers.get("server", "")
        if server and any(x in server.lower() for x in ("apache/", "nginx/", "iis/")):
            results.append(
                {
                    "severity": "LOW",
                    "component": "HTTP Headers",
                    "observation": f"Server banner disclosed: {server[:80]}",
                    "impact": "Version disclosure assists targeted exploits; suppress in production.",
                }
            )

        if "access-control-allow-origin" in headers:
            acao = headers["access-control-allow-origin"]
            if acao.strip() == "*":
                results.append(
                    {
                        "severity": "MEDIUM",
                        "component": "CORS",
                        "observation": "Access-Control-Allow-Origin is wildcard (*).",
                        "impact": "Any origin may read responses if credentials are not properly isolated.",
                    }
                )

    except httpx.HTTPError as exc:
        results.append(
            {
                "severity": "HIGH",
                "component": "HTTP",
                "observation": f"Passive HTTP request failed: {exc}",
                "impact": "Could not complete perimeter header assessment.",
            }
        )
    return results


def _audit_tls(hostname: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                proto = ssock.version() or "unknown"
                not_after = cert.get("notAfter", "unknown")
                results.append(
                    {
                        "severity": "INFO",
                        "component": "TLS",
                        "observation": f"Protocol {proto}; certificate expires {not_after}.",
                        "impact": "Verify auto-renewal and minimum TLS 1.2+ at edge.",
                    }
                )
                if proto in ("TLSv1", "TLSv1.1", "SSLv3"):
                    results.append(
                        {
                            "severity": "HIGH",
                            "component": "TLS",
                            "observation": f"Deprecated protocol negotiated: {proto}",
                            "impact": "Upgrade cipher suites and disable legacy protocols.",
                        }
                    )
    except (ssl.SSLError, OSError, socket.timeout) as exc:
        results.append(
            {
                "severity": "HIGH",
                "component": "TLS",
                "observation": f"TLS handshake failed: {exc}",
                "impact": "Certificate or chain misconfiguration likely.",
            }
        )
    return results


def _audit_docker_and_secrets(blob: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for pattern, msg in SECRET_PATTERNS:
        if re.search(pattern, blob):
            results.append(
                {
                    "severity": "HIGH",
                    "component": "Secrets",
                    "observation": msg,
                    "impact": "Rotate credentials and move secrets to a vault or CI secret store.",
                }
            )
    for line in blob.splitlines():
        for pattern, msg in DOCKER_ISSUES:
            if re.search(pattern, line):
                results.append(
                    {
                        "severity": "MEDIUM",
                        "component": "Container Config",
                        "observation": f"{msg}: {line.strip()[:100]}",
                        "impact": "Reduce container privilege and network exposure.",
                    }
                )
    if "healthcheck" not in blob.lower() and "docker-compose" in blob.lower():
        results.append(
            {
                "severity": "LOW",
                "component": "Container Config",
                "observation": "No HEALTHCHECK defined in provided compose/Dockerfile context.",
                "impact": "Orchestrators cannot automatically replace unhealthy instances.",
            }
        )
    return results


def _audit_vps_metadata(target: str, notes: str | None) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    combined = f"{target}\n{notes or ''}".lower()
    if "passwordauthentication yes" in combined.replace(" ", ""):
        results.append(
            {
                "severity": "HIGH",
                "component": "SSH",
                "observation": "PasswordAuthentication may be enabled.",
                "impact": "Brute-force exposure; enforce key-based auth and Fail2ban.",
            }
        )
    if "permitrootlogin yes" in combined.replace(" ", ""):
        results.append(
            {
                "severity": "HIGH",
                "component": "SSH",
                "observation": "PermitRootLogin may be enabled.",
                "impact": "Direct root login increases compromise blast radius.",
            }
        )
    if "3306" in combined or "5432" in combined:
        results.append(
            {
                "severity": "MEDIUM",
                "component": "Network",
                "observation": "Database port reference found in scope metadata.",
                "impact": "Ensure DB listeners bind to private interfaces only.",
            }
        )
    if not results:
        results.append(
            {
                "severity": "INFO",
                "component": "VPS Baseline",
                "observation": "No critical misconfigurations detected in submitted metadata.",
                "impact": "Desk 3 will deliver full hardening blueprint regardless.",
            }
        )
    return results


def _compute_posture_score(findings: list[dict[str, str]]) -> int:
    score = 100
    weights = {"HIGH": 15, "MEDIUM": 8, "LOW": 3, "INFO": 0}
    for f in findings:
        sev = f.get("severity", "INFO").upper()
        score -= weights.get(sev, 0)
    return max(0, min(100, score))


def audit_findings_json(audit: dict[str, Any]) -> str:
    return json.dumps(audit, default=str)
