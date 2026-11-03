"""Desk 4: Executive PDF report generation."""

from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import Settings
from app.services.pricing_catalog import (
    COMPANY_JURISDICTION,
    COMPANY_LEGAL_NAME,
    COMPANY_NUMBER,
)


def generate_executive_pdf(
    settings: Settings,
    order_code: str,
    organization: str,
    target_asset: str,
    line_items: list[dict[str, Any]],
    total_amount: float,
    audit: dict[str, Any],
    remediation: str,
    executive_summary: str,
) -> str:
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{order_code}-Executive-Audit.pdf"
    path = settings.reports_dir / filename

    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AgencyTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#0B0F19"),
        spaceAfter=8,
    )
    sub_style = ParagraphStyle(
        "AgencySub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#374151"),
    )
    body = styles["Normal"]

    score = audit.get("posture_score", 0)
    findings = audit.get("findings") or []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story: list[Any] = []
    story.append(Paragraph(COMPANY_LEGAL_NAME, title_style))
    story.append(
        Paragraph(
            f"Company No. {COMPANY_NUMBER} · Registered in {COMPANY_JURISDICTION}",
            sub_style,
        )
    )
    story.append(Paragraph("Certified Executive Security Audit Report", styles["Heading2"]))
    story.append(
        Paragraph(
            "UK GDPR &amp; Cyber Essentials Aligned Defensive Engineering",
            sub_style,
        )
    )
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"<b>Order ID:</b> {order_code}", body))
    story.append(Paragraph(f"<b>Client Organization:</b> {organization}", body))
    story.append(Paragraph(f"<b>Target Asset:</b> {target_asset[:500]}", body))
    story.append(Paragraph(f"<b>Report Date:</b> {now}", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Itemized Engineering Scope", styles["Heading3"]))
    parts_table = [["Part", "Description", "Fee (USD)"]]
    for li in line_items:
        parts_table.append(
            [
                li.get("part_id", ""),
                (li.get("title", "") or "")[:55],
                f"${li.get('line_total_usd', 0):.2f}",
            ]
        )
    parts_table.append(["", "Total", f"${total_amount:.2f}"])
    pt = Table(parts_table, colWidths=[0.9 * inch, 3.8 * inch, 1.0 * inch])
    pt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story.append(pt)
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Executive Risk Summary", styles["Heading3"]))
    story.append(Paragraph(executive_summary.replace("\n", "<br/>"), body))
    story.append(
        Paragraph(
            f"<b>Overall Security Posture Score:</b> {score}/100",
            ParagraphStyle("Score", parent=body, fontSize=14, textColor=colors.HexColor("#059669")),
        )
    )
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Detailed Findings", styles["Heading3"]))
    table_data = [["Severity", "Component", "Observation", "Impact"]]
    for f in findings[:40]:
        table_data.append(
            [
                f.get("severity", ""),
                f.get("component", "")[:30],
                (f.get("observation", "") or "")[:80],
                (f.get("impact", "") or "")[:80],
            ]
        )
    if len(table_data) == 1:
        table_data.append(["INFO", "Audit", "No material findings recorded.", "Maintain baseline monitoring."])

    table = Table(table_data, colWidths=[0.9 * inch, 1.1 * inch, 2.2 * inch, 2.2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Remediation & Hardening Blueprint", styles["Heading3"]))
    for line in remediation.splitlines()[:120]:
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe, sub_style))

    story.append(Spacer(1, 0.4 * inch))
    story.append(
        Paragraph(
            "<b>Digital Sign-off</b><br/>Reviewed &amp; Certified by Lead Systems Architect<br/>"
            f"{COMPANY_LEGAL_NAME} — Defensive Audit Division",
            body,
        )
    )

    doc.build(story)
    return filename
