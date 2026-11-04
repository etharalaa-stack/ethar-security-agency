"""USDT (BEP20/TRC20) and card reference payment verification."""

from __future__ import annotations

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

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4c11628f71e5f6548"
TX_HEX_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
TRON_TX_RE = re.compile(r"^[a-fA-F0-9]{64}$")


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


def _amount_matches(received_usd: float, expected_usd: float, tolerance: float) -> bool:
    if expected_usd <= 0:
        return received_usd > 0
    return received_usd + tolerance >= expected_usd and received_usd >= expected_usd - tolerance


async def verify_payment(
    settings: Settings,
    payment_method: str,
    tx_hash: str | None,
    card_reference: str | None,
    *,
    expected_amount_usd: float | None = None,
) -> tuple[bool, str]:
    if payment_method == "card_reference":
        return _verify_card_reference(settings, card_reference)

    if not tx_hash or not tx_hash.strip():
        return False, "Transaction hash is required for USDT payments."

    tx_hash = tx_hash.strip()

    if payment_method == "usdt_bep20":
        return await _verify_bep20(settings, tx_hash, expected_amount_usd)
    if payment_method == "usdt_trc20":
        return await _verify_trc20(settings, tx_hash, expected_amount_usd)

    return False, f"Unsupported payment method: {payment_method}"


def _verify_card_reference(settings: Settings, reference: str | None) -> tuple[bool, str]:
    if not reference or not reference.strip():
        return False, "Card or invoice reference is required."
    ref = reference.strip().upper()
    prefix = settings.stripe_test_reference_prefix.upper()
    if ref.startswith(prefix):
        if settings.payments_allow_test_references():
            return True, "Test reference accepted."
        return False, "Test payment references are disabled in production."
    if ref.startswith("INV-") or ref.startswith("CARD-"):
        return True, "Reference recorded; reconcile against your card processor or invoice ledger."
    return False, "Invalid reference. Use INV-* / CARD-* for live invoices, or enable test mode."


async def _verify_bep20(
    settings: Settings,
    tx_hash: str,
    expected_amount_usd: float | None,
) -> tuple[bool, str]:
    if not TX_HEX_RE.match(tx_hash):
        return False, "Invalid BEP20 transaction hash format."

    if not settings.bscscan_api_key:
        if settings.debug:
            logger.warning("BSCScan API key not set; USDT hash accepted in debug mode only.")
            return True, "Payment recorded (debug — configure BSCSCAN_API_KEY for production)."
        return False, "BEP20 verification unavailable. Contact support or use TRC20."

    url = "https://api.bscscan.com/api"
    params = {
        "module": "proxy",
        "action": "eth_getTransactionReceipt",
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

    receipt = data.get("result")
    if not receipt or receipt == "null":
        return False, "Transaction not found on BSC."

    if receipt.get("status") not in ("0x1", "1", 1):
        return False, "Transaction failed on-chain."

    wallet = settings.usdt_bep20_wallet.lower()
    contract = settings.usdt_bep20_contract.lower()
    decimals = settings.usdt_bep20_decimals
    matched = False
    received_usd = 0.0

    for log in receipt.get("logs") or []:
        if (log.get("address") or "").lower() != contract:
            continue
        topics = log.get("topics") or []
        if not topics or topics[0].lower() != TRANSFER_TOPIC.lower():
            continue
        if len(topics) < 3:
            continue
        to_addr = ("0x" + topics[2][-40:]).lower()
        if wallet and to_addr != wallet:
            continue
        raw = int(log.get("data") or "0x0", 16)
        received_usd = raw / (10**decimals)
        matched = True
        break

    if not matched:
        return False, "No USDT transfer to agency BEP20 wallet found in this transaction."

    if expected_amount_usd is not None and not _amount_matches(
        received_usd, expected_amount_usd, settings.payment_amount_tolerance_usd
    ):
        return False, (
            f"USDT amount mismatch. Expected ~${expected_amount_usd:.2f}, "
            f"received ~${received_usd:.2f}."
        )

    return True, f"BEP20 USDT payment verified (${received_usd:.2f})."


async def _verify_trc20(
    settings: Settings,
    tx_hash: str,
    expected_amount_usd: float | None,
) -> tuple[bool, str]:
    clean = tx_hash.lower().removeprefix("0x")
    if not TRON_TX_RE.match(clean):
        return False, "Invalid TRC20 transaction hash format."

    wallet = settings.usdt_trc20_wallet
    if not wallet or wallet.startswith("TYour"):
        if settings.debug:
            return True, "Payment recorded (debug — set USDT_TRC20_WALLET for production)."
        return False, "TRC20 wallet not configured on server."

    events_url = f"{settings.tron_api_base.rstrip('/')}/v1/transactions/{clean}/events"
    headers: dict[str, str] = {}
    if settings.tron_api_key:
        headers["TRON-PRO-API-KEY"] = settings.tron_api_key

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(events_url, headers=headers)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
    except httpx.HTTPError as exc:
        logger.exception("TronGrid events request failed")
        if settings.debug:
            return True, "Payment recorded (debug — Tron verify failed)."
        return False, f"Unable to verify TRC20 transaction: {exc}"

    events = data.get("data") or []
    contract = settings.usdt_trc20_contract
    decimals = settings.usdt_trc20_decimals
    matched = False
    received_usd = 0.0

    for ev in events:
        if ev.get("contract_address") != contract and ev.get("contractAddress") != contract:
            continue
        if ev.get("event_name") != "Transfer" and ev.get("eventName") != "Transfer":
            continue
        result = ev.get("result") or {}
        to_addr = result.get("to") or result.get("1")
        if to_addr and to_addr != wallet:
            continue
        value_raw = result.get("value") or result.get("2") or "0"
        try:
            raw = int(value_raw)
        except (TypeError, ValueError):
            continue
        received_usd = raw / (10**decimals)
        matched = True
        break

    if not matched:
        if settings.debug and not events:
            return True, "Payment recorded (debug — no TRC20 events parsed)."
        return False, "No USDT transfer to agency TRC20 wallet found in this transaction."

    if expected_amount_usd is not None and not _amount_matches(
        received_usd, expected_amount_usd, settings.payment_amount_tolerance_usd
    ):
        return False, (
            f"USDT amount mismatch. Expected ~${expected_amount_usd:.2f}, "
            f"received ~${received_usd:.2f}."
        )

    return True, f"TRC20 USDT payment verified (${received_usd:.2f})."
