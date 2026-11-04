"""Telegram admin alerts (English-only copy for global operations)."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

_BRAND = "ETHAR LABS UK LTD — Security Engineering Agency"
_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")


def _assert_english(text: str) -> str:
    if _ARABIC_RE.search(text):
        logger.error("Telegram copy must be English-only; blocked outbound message.")
        raise ValueError("Telegram notifications must use English only.")
    return text


async def _send_markdown(settings: Settings, text: str) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False
    body = _assert_english(text)
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": body,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except httpx.HTTPError:
        logger.exception("Failed to send Telegram message")
        return False


def _footer() -> str:
    return f"\n\n_{_BRAND}_"


async def notify_admin_for_approval(
    settings: Settings,
    order_code: str,
    organization: str,
    package_type: str,
    posture_score: int | None,
    target_asset: str,
) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info(
            "Telegram not configured; admin approval link: %s",
            _approval_url(settings, order_code),
        )
        return False

    approve_url = _approval_url(settings, order_code)
    score_text = str(posture_score) if posture_score is not None else "N/A"
    text = (
        "Executive QA — approval required\n\n"
        f"*Order:* `{order_code}`\n"
        f"*Organization:* {organization}\n"
        f"*Package:* {package_type}\n"
        f"*Target:* {target_asset[:200]}\n"
        f"*Posture score:* {score_text}/100\n\n"
        f"[Approve and release report]({approve_url})"
        f"{_footer()}"
    )
    return await _send_markdown(settings, text)


async def notify_payment_received(
    settings: Settings,
    order_code: str,
    organization: str,
    total_amount: float,
    paid_amount: float,
    payment_plan: str,
    target_asset: str,
    *,
    milestone_label: str | None = None,
) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("Telegram not configured for payment alert: %s", order_code)
        return False

    track = f"{settings.frontend_url.rstrip('/')}/track.html?order={order_code}"
    if milestone_label:
        headline = "Milestone payment verified"
        plan_line = f"*Milestone:* {milestone_label}\n*Plan:* {payment_plan}\n"
    else:
        headline = "Payment verified — new engagement"
        plan_line = f"*Plan:* {payment_plan}\n"

    text = (
        f"{headline}\n\n"
        f"*Order:* `{order_code}`\n"
        f"*Organization:* {organization}\n"
        f"{plan_line}"
        f"*Paid:* ${paid_amount:.2f} / ${total_amount:.2f}\n"
        f"*Target:* {target_asset[:180]}\n\n"
        f"[Track order]({track})"
        f"{_footer()}"
    )
    return await _send_markdown(settings, text)


def _approval_url(settings: Settings, order_code: str) -> str:
    base = settings.public_api_base_url.rstrip("/")
    secret = quote(settings.admin_secret, safe="")
    return f"{base}/api/v1/admin/orders/{order_code}/approve?secret={secret}"
