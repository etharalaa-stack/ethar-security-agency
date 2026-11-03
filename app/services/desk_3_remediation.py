"""Desk 3: Remediation scripts and patch synthesis."""

import logging
from typing import Any

from app.config import Settings
from app.services.llm_engine import analyze_findings_for_remediation

logger = logging.getLogger(__name__)


async def run_remediation_desk(
    settings: Settings,
    target_asset: str,
    audit: dict[str, Any],
    selected_parts: list[str],
    line_items: list[dict],
) -> dict[str, Any]:
    findings = audit.get("findings") or []
    template_body = _build_template_remediation(selected_parts, target_asset, findings)

    enriched = await analyze_findings_for_remediation(
        settings, target_asset, selected_parts, findings, template_body
    )
    executive = _build_executive_summary(
        audit.get("posture_score", 0), findings, selected_parts, line_items
    )

    return {
        "remediation_script": enriched,
        "executive_summary": executive,
    }


def _build_executive_summary(
    score: int,
    findings: list[dict[str, str]],
    selected_parts: list[str],
    line_items: list[dict],
) -> str:
    high = sum(1 for f in findings if f.get("severity") == "HIGH")
    med = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    titles = ", ".join(li.get("title", "") for li in line_items) or ", ".join(selected_parts)

    posture = "Strong" if score >= 85 else "Moderate" if score >= 65 else "Needs Improvement"
    return (
        f"Executive Summary — ETHAR LABS UK LTD Modular Engagement\n"
        f"Scope: {titles}\n\n"
        f"Overall Security Posture Score: {score}/100 ({posture}).\n"
        f"Findings: {high} high, {med} medium severity items requiring engineering attention.\n\n"
        "Principal recommendations: implement missing transport and browser security headers at the edge, "
        "eliminate secret material from repository and compose files, and apply the enclosed hardening "
        "automation during a approved maintenance window. All remediations are defensive and "
        "configuration-focused; no intrusive exploitation was performed."
    )


def _build_template_remediation(
    selected_parts: list[str],
    target: str,
    findings: list[dict[str, str]],
) -> str:
    sections: list[str] = [
        "#!/usr/bin/env bash",
        "# Generated Remediation & Hardening Blueprint",
        "# Review in staging before production deployment.",
        "set -euo pipefail",
        "",
    ]

    if "part_1" in selected_parts:
        sections.extend(_nginx_headers_block(target))
    if "part_2" in selected_parts:
        sections.extend(_docker_compose_hardening())
    if "part_3" in selected_parts:
        sections.extend(_cloudflare_rules_snippet())
        sections.extend(_cloudflare_rate_limit_snippet())
    if "part_4" in selected_parts:
        sections.extend(_ubuntu_hardening_script())
    if "part_5" in selected_parts:
        sections.extend(_cicd_hardening_notes())

    sections.append("")
    sections.append("# --- Finding-specific notes ---")
    for i, f in enumerate(findings[:25], 1):
        if f.get("severity") in ("HIGH", "MEDIUM"):
            sections.append(f"# {i}. [{f.get('severity')}] {f.get('component')}: {f.get('observation')}")

    return "\n".join(sections)


def _nginx_headers_block(target: str) -> list[str]:
    return [
        "# Nginx security headers (include in server block)",
        "cat <<'NGINX_EOF' | sudo tee /etc/nginx/snippets/security-headers.conf",
        "add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains; preload\" always;",
        "add_header X-Content-Type-Options \"nosniff\" always;",
        "add_header X-Frame-Options \"SAMEORIGIN\" always;",
        "add_header Referrer-Policy \"strict-origin-when-cross-origin\" always;",
        "add_header Permissions-Policy \"geolocation=(), microphone=(), camera=()\" always;",
        "add_header Content-Security-Policy \"default-src 'self'; frame-ancestors 'self'; base-uri 'self';\" always;",
        "NGINX_EOF",
        "sudo nginx -t && sudo systemctl reload nginx",
        f"# Target reference: {target[:200]}",
        "",
    ]


def _cloudflare_rules_snippet() -> list[str]:
    return [
        "# Cloudflare Transform Rule (Response Header Modification) — configure in dashboard:",
        "# Rule: Set static security headers on all HTML/API responses",
        "# HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy",
        "",
    ]


def _cloudflare_rate_limit_snippet() -> list[str]:
    return [
        "# Cloudflare Rate Limiting (Security > WAF > Rate limiting rules):",
        "# - /api/* : 100 req/min per IP, block 60s",
        "# - /login : 10 req/min per IP, managed challenge",
        "",
    ]


def _cicd_hardening_notes() -> list[str]:
    return [
        "# CI/CD hardening checklist",
        "# - Store secrets in GitHub Actions secrets / GitLab CI variables (protected)",
        "# - Require signed commits and branch protection on main",
        "# - Enable OIDC federation instead of long-lived cloud keys",
        "# - Encrypt backup buckets with SSE-KMS and test restore quarterly",
        "",
    ]


def _docker_compose_hardening() -> list[str]:
    return [
        "# docker-compose.override.yml (security hardening)",
        "cat <<'COMPOSE_EOF' > docker-compose.override.yml",
        "services:",
        "  app:",
        "    user: \"1000:1000\"",
        "    read_only: true",
        "    security_opt:",
        "      - no-new-privileges:true",
        "    cap_drop:",
        "      - ALL",
        "    tmpfs:",
        "      - /tmp",
        "COMPOSE_EOF",
        "",
        "# Dockerfile snippet — add non-root user:",
        "# RUN useradd -r -u 1000 appuser",
        "# USER appuser",
        "",
    ]


def _ubuntu_hardening_script() -> list[str]:
    return [
        "if [[ $(id -u) -ne 0 ]]; then echo 'Run as root or via sudo'; exit 1; fi",
        "export DEBIAN_FRONTEND=noninteractive",
        "apt-get update -qq",
        "apt-get install -y -qq ufw fail2ban unattended-upgrades apt-listchanges",
        "",
        "# SSH hardening",
        "sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config",
        "sed -i 's/^#\\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config",
        "systemctl reload ssh || systemctl reload sshd",
        "",
        "# UFW firewall",
        "ufw default deny incoming",
        "ufw default allow outgoing",
        "ufw allow 22/tcp",
        "ufw allow 80/tcp",
        "ufw allow 443/tcp",
        "ufw --force enable",
        "",
        "# Sysctl network tuning",
        "cat <<'SYSCTL_EOF' > /etc/sysctl.d/99-agency-hardening.conf",
        "net.ipv4.conf.all.rp_filter=1",
        "net.ipv4.conf.default.rp_filter=1",
        "net.ipv4.tcp_syncookies=1",
        "net.ipv4.conf.all.accept_redirects=0",
        "net.ipv6.conf.all.accept_redirects=0",
        "SYSCTL_EOF",
        "sysctl --system",
        "",
        "# Docker daemon (if installed)",
        "if command -v docker >/dev/null; then",
        "  mkdir -p /etc/docker",
        "  cat <<'DOCKER_EOF' > /etc/docker/daemon.json",
        "{",
        "  \"icc\": false,",
        "  \"live-restore\": true,",
        "  \"userland-proxy\": false,",
        "  \"no-new-privileges\": true,",
        "  \"log-driver\": \"json-file\",",
        "  \"log-opts\": { \"max-size\": \"10m\", \"max-file\": \"3\" }",
        "}",
        "DOCKER_EOF",
        "  systemctl restart docker || true",
        "fi",
        "",
        "systemctl enable fail2ban unattended-upgrades",
        "systemctl restart fail2ban",
        "echo 'VPS hardening baseline applied.'",
        "",
    ]


