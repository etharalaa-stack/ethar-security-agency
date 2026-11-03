"""Parse and serialize order pricing / milestone state."""

from __future__ import annotations

import json
from typing import Any

from app.models import Order
from app.services.pricing_catalog import (
    amount_due_now,
    build_milestones,
    itemized_quote,
    milestone_paid_for_stage,
    next_unpaid_milestone,
    paid_total,
)


def parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return list(data) if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def parse_line_items(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def parse_milestones(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def order_progress_percent(order: Order) -> float:
    if order.status == OrderStatus.COMPLETED.value:
        return 100.0
    stage = max(0, order.current_stage)
    base = min(stage / 4.0 * 100.0, 100.0)
    if order.status == OrderStatus.AWAITING_ADMIN_APPROVAL.value:
        return max(base, 90.0)
    return round(base, 1)


def compute_paid_amount(milestones: list[dict[str, Any]]) -> float:
    return paid_total(milestones)


# late import guard for type hint above
from app.models import OrderStatus  # noqa: E402


def apply_first_payment(
    milestones: list[dict[str, Any]],
    tx_ref: str | None,
) -> tuple[list[dict[str, Any]], float]:
    updated = [dict(m) for m in milestones]
    for m in updated:
        if not m.get("paid"):
            m["paid"] = True
            m["tx_hash"] = tx_ref
            break
    return updated, paid_total(updated)


def apply_milestone_payment(
    milestones: list[dict[str, Any]],
    milestone_number: int,
    tx_ref: str | None,
) -> tuple[list[dict[str, Any]], float]:
    updated = [dict(m) for m in milestones]
    for m in updated:
        if int(m["milestone"]) == milestone_number:
            m["paid"] = True
            m["tx_hash"] = tx_ref
            break
    return updated, paid_total(updated)


def milestones_for_order(
    part_ids: list[str],
    payment_plan: str,
) -> tuple[list[dict[str, Any]], float, list[dict[str, Any]]]:
    lines, total = itemized_quote(part_ids)
    ms = build_milestones(total, payment_plan)
    return ms, total, lines


def can_start_pipeline(milestones: list[dict[str, Any]]) -> bool:
    return milestone_paid_for_stage(milestones, 0)


def serialize_milestones(milestones: list[dict[str, Any]]) -> str:
    return json.dumps(milestones)


def public_milestone_view(milestones: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "milestones": milestones,
        "paid_amount": paid_total(milestones),
        "amount_due_now": amount_due_now(milestones),
        "next_milestone": next_unpaid_milestone(milestones),
    }
