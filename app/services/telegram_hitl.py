"""Telegram admin bot notifications for human-in-the-loop approval."""

import logging
from urllib.parse import quote

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


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
        "🔐 *Executive QA — Approval Required*\n\n"
        f"*Order:* `{order_code}`\n"
        f"*Organization:* {organization}\n"
        f"*Package:* {package_type}\n"
        f"*Target:* {target_asset[:200]}\n"
        f"*Posture Score:* {score_text}/100\n\n"
        f"[Approve & Release Report]({approve_url})"
    )

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except httpx.HTTPError:
        logger.exception("Failed to send Telegram approval message")
        return False


async def notify_payment_received(
    settings: Settings,
    order_code: str,
    organization: str,
    total_amount: float,
    paid_amount: float,
    payment_plan: str,
    target_asset: str,
) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("Telegram not configured for payment alert: %s", order_code)
        return False

    track = f"{settings.frontend_url.rstrip('/')}/track.html?order={order_code}"
    text = (
        "💰 *Payment Verified — New Engagement*\n\n"
        f"*Order:* `{order_code}`\n"
        f"*Organization:* {organization}\n"
        f"*Plan:* {payment_plan}\n"
        f"*Paid:* ${paid_amount:.2f} / ${total_amount:.2f}\n"
        f"*Target:* {target_asset[:180]}\n\n"
        f"[Track Order]({track})"
    )
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except httpx.HTTPError:
        logger.exception("Failed to send Telegram payment notification")
        return False


def _approval_url(settings: Settings, order_code: str) -> str:
    base = settings.public_api_base_url.rstrip("/")
    secret = quote(settings.admin_secret, safe="")
    return f"{base}/api/v1/admin/orders/{order_code}/approve?secret={secret}"
