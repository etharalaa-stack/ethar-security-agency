"""Prospect pitch link and outreach template generation."""

from __future__ import annotations

from urllib.parse import quote

from app.services.pricing_catalog import COMPANY_JURISDICTION, COMPANY_LEGAL_NAME, COMPANY_NUMBER


def build_pitch_link(frontend_base: str, domain: str, organization: str) -> str:
    base = frontend_base.rstrip("/")
    q = f"target={quote(domain.strip())}&org={quote(organization.strip())}"
    return f"{base}/index.html?{q}"


def outreach_email_template(
    organization: str,
    domain: str,
    pitch_link: str,
    sender_name: str = "Lead Systems Architect",
) -> str:
    return f"""Subject: Defensive perimeter snapshot for {organization} ({domain})

Dear {organization} team,

ETHAR LABS UK LTD (Company No. {COMPANY_NUMBER}, registered in {COMPANY_JURISDICTION}) delivers modular, defensive security engineering with board-ready certification.

We prepared a personalized live posture teaser for your authorized perimeter:
{pitch_link}

Our four-desk model covers perimeter audits, container SecOps, Cloudflare edge shielding, VPS hardening, and CI/CD access reviews — with optional milestone billing for engagements over $150.

If you are the authorized administrator, you may proceed directly from the link above. All work is passive, scoped, and UK GDPR aligned.

Regards,
{sender_name}
ETHAR LABS UK LTD — Defensive Audit Division
"""


def generate_pitch_batch(
    frontend_base: str,
    prospects: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for p in prospects:
        domain = p.get("domain", "").strip()
        org = p.get("organization", domain).strip()
        if not domain:
            continue
        link = build_pitch_link(frontend_base, domain, org)
        rows.append(
            {
                "domain": domain,
                "organization": org,
                "pitch_link": link,
                "email_template": outreach_email_template(org, domain, link),
            }
        )
    return rows
