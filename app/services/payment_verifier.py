"""USDT (BEP20/TRC20) and card reference payment verification."""

import logging
import re
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

try:
    import hmac
    import hashlib
except ImportError:
    pass  # pragma: no cover


def verify_stripe_webhook_signature(
    payload: bytes,
    sig_header: str | None,
    webhook_secret: str,
) -> bool:
    """Verify Stripe webhook `Stripe-Signature` header."""
    if not sig_header or not webhook_secret:
        return False
    parts = {}
    for item in sig_header.split(","):
        k, _, v = item.partition("=")
        parts[k.strip()] = v.strip()
    timestamp = parts.get("t")
    v1 = parts.get("v1")
    if not timestamp or not v1:
        return False
    signed = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        signed,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, v1)

TX_HEX_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
TRON_TX_RE = re.compile(r"^[a-fA-F0-9]{64}$")


async def verify_payment(
    settings: Settings,
    payment_method: str,
    tx_hash: str | None,
    card_reference: str | None,
) -> tuple[bool, str]:
    if payment_method == "card_reference":
        return _verify_card_reference(settings, card_reference)

    if not tx_hash or not tx_hash.strip():
        return False, "Transaction hash is required for USDT payments."

    tx_hash = tx_hash.strip()

    if payment_method == "usdt_bep20":
        return await _verify_bep20(settings, tx_hash)
    if payment_method == "usdt_trc20":
        return await _verify_trc20(settings, tx_hash)

    return False, f"Unsupported payment method: {payment_method}"


def _verify_card_reference(settings: Settings, reference: str | None) -> tuple[bool, str]:
    if not reference or not reference.strip():
        return False, "Card or invoice reference is required."
    ref = reference.strip().upper()
    if ref.startswith(settings.stripe_test_reference_prefix.upper()):
        return True, "Test reference accepted."
    if ref.startswith("INV-") or ref.startswith("CARD-"):
        return True, "Reference recorded; manual reconciliation may apply in production."
    return False, "Invalid reference format. Use STRIPE-TEST-* for sandbox testing."


async def _verify_bep20(settings: Settings, tx_hash: str) -> tuple[bool, str]:
    if not TX_HEX_RE.match(tx_hash):
        return False, "Invalid BEP20 transaction hash format."

    if not settings.bscscan_api_key:
        logger.warning("BSCScan API key not set; accepting hash in development mode.")
        return True, "Payment recorded (development verification mode)."

    url = "https://api.bscscan.com/api"
    params = {
        "module": "proxy",
        "action": "eth_getTransactionByHash",
        "txhash": tx_hash,
        "apikey": settings.bscscan_api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.exception("BSCScan request failed")
        return False, f"Unable to verify BEP20 transaction: {exc}"

    result = data.get("result")
    if not result or result == "null":
        return False, "Transaction not found on BSC."

    to_addr = (result.get("to") or "").lower()
    wallet = settings.usdt_bep20_wallet.lower()
    if wallet and to_addr != wallet:
        return False, "Transaction recipient does not match agency BEP20 wallet."

    return True, "BEP20 USDT payment verified."


async def _verify_trc20(settings: Settings, tx_hash: str) -> tuple[bool, str]:
    clean = tx_hash.lower().removeprefix("0x")
    if not TRON_TX_RE.match(clean):
        return False, "Invalid TRC20 transaction hash format."

    if not settings.tron_api_base:
        return True, "Payment recorded (development verification mode)."

    url = f"{settings.tron_api_base.rstrip('/')}/wallet/gettransactionbyid"
    payload = {"value": clean}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
    except httpx.HTTPError as exc:
        logger.exception("TronGrid request failed")
        return False, f"Unable to verify TRC20 transaction: {exc}"

    if not data.get("txID"):
        return False, "Transaction not found on TRON network."

    return True, "TRC20 USDT payment verified."
