"""Public instant perimeter teaser scan (passive, rate-limited)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.services.desk_1_intake import run_intake_desk
from app.services.desk_2_audit import run_audit_desk
from app.services.pricing_catalog import ENGINEERING_PARTS

REDACT_TAIL = "\n# ███ Full production-ready patch available in certified engagement — order Part remediation.\n"


def _normalize_url(raw: str) -> str:
    t = raw.strip()
    if not t.startswith(("http://", "https://")):
        t = f"https://{t}"
    return t


def _redact_remediation_snippet(component: str) -> str:
    samples = {
        "HTTP Headers": "add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains; preload\" always;",
        "TLS": "# enforce TLS 1.2+ at load balancer / origin",
        "DNS Email": "v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com",
        "CORS": "# restrict Access-Control-Allow-Origin to trusted app origins",
        "Cloudflare Edge": "# Cloudflare Rate Limiting rule: /api/* 100 req/min block 60s",
    }
    line = samples.get(component, "# hardening snippet")
    return line + REDACT_TAIL


def _recommend_parts(findings: list[dict[str, str]]) -> list[str]:
    parts: set[str] = set()
    for f in findings:
        comp = (f.get("component") or "").lower()
        sev = (f.get("severity") or "").upper()
        if sev not in ("HIGH", "MEDIUM", "LOW"):
            continue
        if comp in ("http headers", "tls", "dns email", "http", "cors"):
            parts.add("part_1")
        if comp in ("cloudflare edge", "edge waf"):
            parts.add("part_3")
        if "container" in comp or "secrets" in comp:
            parts.add("part_2")
        if comp in ("ssh", "network", "vps baseline"):
            parts.add("part_4")
        if comp in ("ci/cd", "backup policy", "network isolation"):
            parts.add("part_5")
    if not parts:
        parts.add("part_1")
    return sorted(parts, key=lambda x: int(x.split("_")[1]))


def _teaser_alerts(findings: list[dict[str, str]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for f in findings:
        if f.get("severity") in ("HIGH", "MEDIUM"):
            alerts.append(
                {
                    "severity": f.get("severity"),
                    "component": f.get("component"),
                    "title": (f.get("observation") or "")[:160],
                    "impact": (f.get("impact") or "")[:200],
                    "remediation_preview": _redact_remediation_snippet(f.get("component", "HTTP Headers")),
                }
            )
    return alerts[:12]


async def run_quick_scan(target: str, organization: str | None = None) -> dict[str, Any]:
    url = _normalize_url(target)
    host = urlparse(url).hostname or target.strip()

    intake = await run_intake_desk(url, None, ["part_1", "part_3"])
    audit = await run_audit_desk(url, intake, None, ["part_1", "part_3"])
    findings = audit.get("findings") or []
    score = int(audit.get("posture_score", 0))
    recommended = _recommend_parts(findings)
    org_line = organization.strip() if organization else None

    return {
        "target": url,
        "hostname": host,
        "organization": org_line,
        "posture_score": score,
        "posture_label": "Strong" if score >= 85 else "Moderate" if score >= 65 else "Needs Improvement",
        "alerts": _teaser_alerts(findings),
        "recommended_parts": recommended,
        "recommended_part_details": [
            {
                "part_id": pid,
                "title": ENGINEERING_PARTS[pid]["title"],
                "price_usd": ENGINEERING_PARTS[pid]["price_usd"],
            }
            for pid in recommended
            if pid in ENGINEERING_PARTS
        ],
        "personalized_greeting": (
            f"Pre-audit snapshot prepared for {org_line} — perimeter review of {host}."
            if org_line
            else f"Live perimeter snapshot for {host}."
        ),
        "scan_disclaimer": (
            "Passive teaser scan only. Full modular engagement includes signed PDF certification by ETHAR LABS UK LTD."
        ),
    }
