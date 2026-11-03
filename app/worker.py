"""Background paced execution pipeline for engineering desk progression."""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import AsyncSessionLocal, SyncSessionLocal, init_db
from app.models import Order, OrderStatus
from app.services.desk_1_intake import intake_summary_json, run_intake_desk
from app.services.desk_2_audit import audit_findings_json, run_audit_desk
from app.services.desk_3_remediation import run_remediation_desk
from app.services.desk_4_reporting import generate_executive_pdf
from app.services.order_helpers import parse_json_list, parse_line_items, parse_milestones
from app.services.pricing_catalog import milestone_paid_for_stage
from app.services.telegram_hitl import notify_admin_for_approval

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
logger = logging.getLogger(__name__)

STAGE_TITLES = {
    1: "Intake & Scope Verified",
    2: "Security & Configuration Audit in Progress",
    3: "Engineering Remediation & Patch Synthesis",
    4: "Principal Engineer QA & Final Sign-Off",
}


def _load_logs(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _save_logs(logs: list[dict]) -> str:
    return json.dumps(logs, default=str)


def _append_log(logs: list[dict], stage: int, message: str, completed: bool = False) -> None:
    logs.append(
        {
            "stage": stage,
            "title": STAGE_TITLES.get(stage, f"Stage {stage}"),
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "completed": completed,
        }
    )


_running_orders: set[int] = set()


def _milestones_ready_for_stage(milestones: list[dict], stage: int) -> bool:
    for m in milestones:
        due = int(m.get("due_at_stage", 0))
        if due > 0 and due <= stage and not m.get("paid"):
            return False
    return True


async def _pause_for_milestone(order_id: int, stage: int) -> bool:
    """Return False if pipeline must stop until client pays next milestone."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return False
        milestones = parse_milestones(order.milestones_json)
        if order.payment_plan == "full":
            return True
        if _milestones_ready_for_stage(milestones, stage):
            return True
        logs = _load_logs(order.stage_logs_json)
        _append_log(
            logs,
            stage,
            "Awaiting milestone payment before proceeding to the next engineering desk.",
            completed=False,
        )
        order.stage_logs_json = _save_logs(logs)
        order.status = OrderStatus.AWAITING_PAYMENT.value
        await session.commit()
        logger.info("Order %s paused — milestone due before stage %s", order.order_code, stage)
        return False


async def process_order_pipeline(order_id: int) -> None:
    if order_id in _running_orders:
        return
    _running_orders.add(order_id)
    settings = get_settings()
    delay = settings.stage_delay_seconds
    jitter = max(1, int(delay * 0.05))

    target_asset = ""
    tech_notes: str | None = None
    order_code = ""
    selected_parts: list[str] = []
    line_items: list[dict] = []

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order or not order.payment_verified:
            _running_orders.discard(order_id)
            return
        if order.status in (
            OrderStatus.COMPLETED.value,
            OrderStatus.AWAITING_ADMIN_APPROVAL.value,
            OrderStatus.FAILED.value,
        ):
            _running_orders.discard(order_id)
            return
        if order.current_stage >= 4 and order.pdf_filename:
            _running_orders.discard(order_id)
            return

        target_asset = order.target_asset
        tech_notes = order.tech_notes
        order_code = order.order_code
        selected_parts = parse_json_list(order.selected_parts_json) or ["part_1"]
        line_items = parse_line_items(order.parts_pricing_json)
        order.status = OrderStatus.IN_PROGRESS.value
        if order.current_stage < 1:
            order.current_stage = 1
        await session.commit()

    intake_data: dict = {}
    audit_data: dict = {}

    remediation: dict = {"remediation_script": "", "executive_summary": ""}

    try:
        cs = await _get_stage(order_id)
        if cs < 1:
            await _set_stage(order_id, 1, OrderStatus.IN_PROGRESS.value)
            await _sleep_paced(delay, jitter)
            intake_data = await run_intake_desk(target_asset, tech_notes, selected_parts)
            await _update_order_logs(
                order_id,
                1,
                "Scope validated; architecture mapping complete.",
                intake_json=intake_summary_json(intake_data),
            )

        cs = await _get_stage(order_id)
        if cs < 2:
            await _set_stage(order_id, 2, OrderStatus.IN_PROGRESS.value)
            await _sleep_paced(delay, jitter)
            if not intake_data:
                intake_data = {"findings": [], "normalized_target": target_asset}
            audit_data = await run_audit_desk(
                target_asset,
                intake_data,
                tech_notes,
                selected_parts,
            )
            await _update_order_logs(
                order_id,
                2,
                f"Passive audit complete. Posture score: {audit_data.get('posture_score', 0)}/100.",
                audit_json=audit_findings_json(audit_data),
                posture_score=audit_data.get("posture_score"),
            )

        if not await _pause_for_milestone(order_id, 3):
            return

        cs = await _get_stage(order_id)
        if cs < 3:
            await _set_stage(order_id, 3, OrderStatus.IN_PROGRESS.value)
            await _sleep_paced(delay, jitter)
            if not audit_data:
                audit_data = {"findings": [], "posture_score": 0}
            remediation = await run_remediation_desk(
                settings,
                target_asset,
                audit_data,
                selected_parts,
                line_items,
            )
            await _update_order_logs(
                order_id,
                3,
                "Remediation scripts and patch bundles synthesized.",
                remediation_script=remediation.get("remediation_script"),
                executive_summary=remediation.get("executive_summary"),
            )

        if not await _pause_for_milestone(order_id, 4):
            return

        await _set_stage(order_id, 4, OrderStatus.IN_PROGRESS.value)
        await _sleep_paced(delay, jitter)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one()
            if order.status == OrderStatus.COMPLETED.value:
                return
            if not audit_data and order.audit_findings_json:
                audit_data = json.loads(order.audit_findings_json)
            if not remediation.get("remediation_script") and order.remediation_script:
                remediation["remediation_script"] = order.remediation_script
            if not remediation.get("executive_summary") and order.executive_summary:
                remediation["executive_summary"] = order.executive_summary

            pdf_name = generate_executive_pdf(
                settings,
                order.order_code,
                order.organization,
                order.target_asset,
                line_items or parse_line_items(order.parts_pricing_json),
                float(order.total_amount),
                audit_data,
                remediation.get("remediation_script") or "",
                remediation.get("executive_summary") or "",
            )
            logs = _load_logs(order.stage_logs_json)
            _append_log(
                logs,
                4,
                "Executive PDF generated; pending Principal Engineer sign-off.",
                completed=False,
            )
            order.pdf_filename = pdf_name
            order.stage_logs_json = _save_logs(logs)
            order.status = OrderStatus.AWAITING_ADMIN_APPROVAL.value
            await session.commit()

            await notify_admin_for_approval(
                settings,
                order.order_code,
                order.organization,
                order.package_type,
                order.posture_score,
                order.target_asset,
            )

        logger.info("Order %s awaiting admin approval", order_code)

    except Exception as exc:
        logger.exception("Pipeline failed for order %s: %s", order_id, exc)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            if order:
                order.status = OrderStatus.FAILED.value
                logs = _load_logs(order.stage_logs_json)
                _append_log(logs, order.current_stage or 1, f"Pipeline error: {exc}")
                order.stage_logs_json = _save_logs(logs)
                await session.commit()
    finally:
        _running_orders.discard(order_id)


async def _get_stage(order_id: int) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one()
        return int(order.current_stage)


async def _sleep_paced(delay: int, jitter: int) -> None:
    await asyncio.sleep(delay + random.randint(0, jitter))


async def _set_stage(order_id: int, stage: int, status: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one()
        order.current_stage = stage
        order.status = status
        logs = _load_logs(order.stage_logs_json)
        _append_log(logs, stage, f"{STAGE_TITLES.get(stage)} — started.")
        order.stage_logs_json = _save_logs(logs)
        await session.commit()


async def _update_order_logs(
    order_id: int,
    stage: int,
    message: str,
    intake_json: str | None = None,
    audit_json: str | None = None,
    remediation_script: str | None = None,
    executive_summary: str | None = None,
    posture_score: int | None = None,
) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one()
        logs = _load_logs(order.stage_logs_json)
        _append_log(logs, stage, message, completed=True)
        order.stage_logs_json = _save_logs(logs)
        order.current_stage = stage
        if audit_json:
            order.audit_findings_json = audit_json
        if remediation_script:
            order.remediation_script = remediation_script
        if executive_summary:
            order.executive_summary = executive_summary
        if posture_score is not None:
            order.posture_score = posture_score
        await session.commit()
        return logs


def fetch_pending_order_ids() -> list[int]:
    with SyncSessionLocal() as session:
        rows = (
            session.query(Order.id)
            .filter(
                Order.payment_verified.is_(True),
                Order.status == OrderStatus.IN_PROGRESS.value,
                Order.current_stage < 4,
                Order.pdf_filename.is_(None),
            )
            .all()
        )
        return [r[0] for r in rows]


def mark_in_progress_if_verified(session: Session) -> list[int]:
    orders = (
        session.query(Order)
        .filter(
            Order.payment_verified.is_(True),
            Order.status == OrderStatus.PENDING_VERIFICATION.value,
            Order.current_stage == 0,
        )
        .all()
    )
    ids = []
    for o in orders:
        milestones = parse_milestones(o.milestones_json)
        if not milestone_paid_for_stage(milestones, 0):
            continue
        o.status = OrderStatus.IN_PROGRESS.value
        o.current_stage = 1
        ids.append(o.id)
    session.commit()
    return ids


async def worker_loop() -> None:
    await init_db()
    settings = get_settings()
    logger.info("Worker started; stage delay=%ss", settings.stage_delay_seconds)

    while True:
        with SyncSessionLocal() as sync_sess:
            new_ids = mark_in_progress_if_verified(sync_sess)

        for oid in new_ids:
            asyncio.create_task(process_order_pipeline(oid))

        pending = fetch_pending_order_ids()
        for oid in pending:
            asyncio.create_task(process_order_pipeline(oid))

        await asyncio.sleep(5)


def main() -> None:
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
