"""Modular engineering parts catalog and milestone calculations."""

from __future__ import annotations

from typing import Any

COMPANY_LEGAL_NAME = "ETHAR LABS UK LTD"
COMPANY_NUMBER = "17032523"
COMPANY_JURISDICTION = "England & Wales, London, United Kingdom"

ENGINEERING_PARTS: dict[str, dict[str, Any]] = {
    "part_1": {
        "id": "part_1",
        "title": "Web & API Perimeter Audit",
        "price_usd": 100.0,
        "summary": "SSL/TLS cipher strength, HTTP security headers (CSP, HSTS, X-Frame), DNS/SPF/DMARC hygiene.",
        "badge": "Most Popular",
        "eta_hours": 6,
        "deliverables": [
            "TLS & cipher posture report",
            "HTTP header gap analysis",
            "DNS SPF/DMARC review",
            "Nginx/Apache header patch block",
        ],
        "preview_sample": "Strict-Transport-Security max-age=31536000; includeSubDomains; preload",
    },
    "part_2": {
        "id": "part_2",
        "title": "Container & Repository SecOps Review",
        "price_usd": 120.0,
        "summary": "Dockerfile & docker-compose hardening, secret leak scan, dependency hygiene patches.",
        "badge": "DevSecOps",
        "eta_hours": 8,
        "deliverables": [
            "Dockerfile/compose lint",
            "Secret pattern findings",
            "Non-root user patch",
            "Git-ready remediation diff",
        ],
        "preview_sample": "USER 1000:1000 + cap_drop: [ALL] + read_only: true",
    },
    "part_3": {
        "id": "part_3",
        "title": "Cloudflare WAF & Edge Shielding",
        "price_usd": 80.0,
        "summary": "Cloudflare Transform Rules, rate limiting, endpoint defense configuration.",
        "badge": "Fast Win",
        "eta_hours": 4,
        "deliverables": [
            "Transform header rules",
            "Rate limit policies",
            "Bot fight mode guidance",
            "API path shielding",
        ],
        "preview_sample": "Rate limit: /api/* → 100 requests/min/IP → Block 60s",
    },
    "part_4": {
        "id": "part_4",
        "title": "Linux VPS & Kernel Hardening",
        "price_usd": 150.0,
        "summary": "Ubuntu/Debian Bash hardening: SSH, UFW, Docker daemon isolation, sysctl tuning.",
        "badge": "Priority",
        "eta_hours": 10,
        "deliverables": [
            "Idempotent Bash hardening kit",
            "SSH key-only lockdown",
            "UFW + Fail2ban baseline",
            "Docker daemon.json secure profile",
        ],
        "preview_sample": "PermitRootLogin no · PasswordAuthentication no · ufw enable",
    },
    "part_5": {
        "id": "part_5",
        "title": "CI/CD Pipeline & Data Access Review",
        "price_usd": 90.0,
        "summary": "Access control audit, internal network isolation, backup policy review.",
        "badge": "Compliance",
        "eta_hours": 6,
        "deliverables": [
            "Pipeline secret hygiene review",
            "Network bind exposure check",
            "Backup/RPO checklist",
            "OIDC federation recommendations",
        ],
        "preview_sample": "Protected branches + OIDC to cloud — no long-lived CI keys",
    },
}

MILESTONE_MIN_TOTAL = 150.0
MILESTONE_SPLITS = (0.40, 0.40, 0.20)


def list_parts() -> list[dict[str, Any]]:
    return list(ENGINEERING_PARTS.values())


def validate_part_ids(part_ids: list[str]) -> tuple[bool, str]:
    if not part_ids:
        return False, "Select at least one engineering part."
    unknown = [p for p in part_ids if p not in ENGINEERING_PARTS]
    if unknown:
        return False, f"Unknown parts: {', '.join(unknown)}"
    return True, ""


def itemized_quote(part_ids: list[str]) -> tuple[list[dict[str, Any]], float]:
    lines: list[dict[str, Any]] = []
    total = 0.0
    for pid in part_ids:
        part = ENGINEERING_PARTS[pid]
        lines.append(
            {
                "part_id": pid,
                "title": part["title"],
                "unit_price_usd": part["price_usd"],
                "line_total_usd": part["price_usd"],
            }
        )
        total += float(part["price_usd"])
    return lines, round(total, 2)


def milestones_allowed(total: float) -> bool:
    return total > MILESTONE_MIN_TOTAL


def build_milestones(total: float, payment_plan: str) -> list[dict[str, Any]]:
    if payment_plan == "full":
        return [
            {
                "milestone": 1,
                "label": "Full upfront payment",
                "percent": 100.0,
                "amount_usd": round(total, 2),
                "due_at_stage": 0,
                "paid": False,
                "tx_hash": None,
            }
        ]

    m1 = round(total * MILESTONE_SPLITS[0], 2)
    m2 = round(total * MILESTONE_SPLITS[1], 2)
    m3 = round(total - m1 - m2, 2)
    return [
        {
            "milestone": 1,
            "label": "Milestone 1 — Scope triage & passive recon (40%)",
            "percent": 40.0,
            "amount_usd": m1,
            "due_at_stage": 0,
            "paid": False,
            "tx_hash": None,
        },
        {
            "milestone": 2,
            "label": "Milestone 2 — Remediation & patch synthesis (40%)",
            "percent": 40.0,
            "amount_usd": m2,
            "due_at_stage": 3,
            "paid": False,
            "tx_hash": None,
        },
        {
            "milestone": 3,
            "label": "Milestone 3 — Principal QA & PDF release (20%)",
            "percent": 20.0,
            "amount_usd": m3,
            "due_at_stage": 4,
            "paid": False,
            "tx_hash": None,
        },
    ]


def amount_due_now(milestones: list[dict[str, Any]]) -> float:
    for m in milestones:
        if not m.get("paid"):
            return float(m["amount_usd"])
    return 0.0


def paid_total(milestones: list[dict[str, Any]]) -> float:
    return round(sum(float(m["amount_usd"]) for m in milestones if m.get("paid")), 2)


def milestone_paid_for_stage(milestones: list[dict[str, Any]], stage: int) -> bool:
    """Return True if all milestones with due_at_stage <= stage are paid."""
    for m in milestones:
        if int(m.get("due_at_stage", 0)) <= stage and not m.get("paid"):
            return False
    return True


def next_unpaid_milestone(milestones: list[dict[str, Any]]) -> dict[str, Any] | None:
    for m in sorted(milestones, key=lambda x: int(x["milestone"])):
        if not m.get("paid"):
            return m
    return None
