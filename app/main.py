"""FastAPI application — public and admin endpoints."""

import asyncio
import json
import random
from datetime import datetime

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.config import Settings, get_settings
from app.database import get_db, init_db
from app.models import Order, OrderStatus
from app.schemas import (
    AdminApproveResponse,
    EngineeringPartResponse,
    HealthResponse,
    MilestonePaymentRequest,
    MilestonePaymentResponse,
    MilestoneStatus,
    OrderCreateRequest,
    OrderCreateResponse,
    OrderPublicResponse,
    PartLineItem,
    PartsCatalogResponse,
    PaymentConfigResponse,
    PitchGenerateRequest,
    PitchGenerateResponse,
    PitchGenerateItem,
    QuickScanRequest,
    QuickScanResponse,
    SampleReportPreview,
    StageLogEntry,
)
from app.services.pitch_crm import generate_pitch_batch
from app.services.quick_scan import run_quick_scan
from app.services.telegram_hitl import notify_payment_received
from app.services.order_helpers import (
    apply_first_payment,
    apply_milestone_payment,
    can_start_pipeline,
    milestones_for_order,
    order_progress_percent,
    parse_json_list,
    parse_line_items,
    parse_milestones,
    serialize_milestones,
)
from app.services.payment_verifier import verify_payment, verify_stripe_webhook_signature
from app.services.pricing_catalog import (
    COMPANY_LEGAL_NAME,
    COMPANY_NUMBER,
    MILESTONE_MIN_TOTAL,
    amount_due_now,
    list_parts,
    milestones_allowed,
    paid_total,
    validate_part_ids,
)
from app.worker import STAGE_TITLES, process_order_pipeline

app = FastAPI(title="ETHAR LABS UK LTD — Security Engineering API", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


def _generate_order_code() -> str:
    return f"ORD-{random.randint(1000, 9999)}"


def _parse_stage_logs(raw: str | None) -> list[StageLogEntry]:
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out: list[StageLogEntry] = []
    for item in items:
        ts = item.get("timestamp")
        if isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            ts_dt = datetime.utcnow()
        out.append(
            StageLogEntry(
                stage=int(item.get("stage", 0)),
                title=str(item.get("title", "")),
                message=str(item.get("message", "")),
                timestamp=ts_dt,
                completed=bool(item.get("completed", False)),
            )
        )
    return out


def _order_to_public(order: Order) -> OrderPublicResponse:
    milestones = parse_milestones(order.milestones_json)
    line_items_raw = parse_line_items(order.parts_pricing_json)
    line_items = [PartLineItem(**li) for li in line_items_raw]
    ms_models = [MilestoneStatus(**m) for m in milestones]
    nxt = next((m for m in ms_models if not m.paid), None)
    report_available = order.status == OrderStatus.COMPLETED.value and bool(order.pdf_filename)
    return OrderPublicResponse(
        order_code=order.order_code,
        organization=order.organization,
        package_type=order.package_type,
        target_asset=order.target_asset,
        current_stage=order.current_stage,
        status=order.status,
        payment_verified=order.payment_verified,
        payment_plan=order.payment_plan,
        total_amount=float(order.total_amount or 0),
        paid_amount=float(order.paid_amount or 0),
        amount_due_now=amount_due_now(milestones),
        progress_percent=order_progress_percent(order),
        selected_parts=parse_json_list(order.selected_parts_json),
        line_items=line_items,
        milestones=ms_models,
        next_milestone=nxt,
        posture_score=order.posture_score,
        executive_summary=order.executive_summary
        if report_available or order.status == OrderStatus.AWAITING_ADMIN_APPROVAL.value
        else None,
        report_available=report_available,
        stage_logs=_parse_stage_logs(order.stage_logs_json),
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@app.post(f"{get_settings().api_prefix}/public/quick-scan", response_model=QuickScanResponse)
async def public_quick_scan(body: QuickScanRequest) -> QuickScanResponse:
    result = await run_quick_scan(body.target, body.organization)
    return QuickScanResponse(**result)


@app.post(f"{get_settings().api_prefix}/admin/pitch/generate", response_model=PitchGenerateResponse)
async def admin_generate_pitch_links(
    body: PitchGenerateRequest,
    secret: str = Query(...),
    settings: Settings = Depends(get_settings),
) -> PitchGenerateResponse:
    if secret.strip() != settings.admin_secret.strip():
        raise HTTPException(status_code=403, detail="Invalid admin secret.")
    items = generate_pitch_batch(
        settings.frontend_url,
        [{"domain": p.domain, "organization": p.organization or p.domain} for p in body.prospects],
    )
    return PitchGenerateResponse(
        items=[PitchGenerateItem(**i) for i in items],
        company_name=COMPANY_LEGAL_NAME,
        company_number=COMPANY_NUMBER,
    )


@app.get(f"{get_settings().api_prefix}/config/parts", response_model=PartsCatalogResponse)
async def parts_catalog() -> PartsCatalogResponse:
    return PartsCatalogResponse(
        company_name=COMPANY_LEGAL_NAME,
        company_number=COMPANY_NUMBER,
        parts=[EngineeringPartResponse(**p) for p in list_parts()],
        milestone_min_total_usd=MILESTONE_MIN_TOTAL,
    )


@app.get(f"{get_settings().api_prefix}/config/payments", response_model=PaymentConfigResponse)
async def payment_config(settings: Settings = Depends(get_settings)) -> PaymentConfigResponse:
    return PaymentConfigResponse(
        usdt_bep20_wallet=settings.usdt_bep20_wallet,
        usdt_trc20_wallet=settings.usdt_trc20_wallet,
        company_name=COMPANY_LEGAL_NAME,
        company_number=COMPANY_NUMBER,
        allow_test_card_references=settings.payments_allow_test_references(),
    )


async def _assert_payment_ref_unused(
    db: AsyncSession,
    payment_ref: str | None,
    *,
    exclude_order_code: str | None = None,
) -> None:
    if not payment_ref or not str(payment_ref).strip():
        return
    ref = str(payment_ref).strip()
    q = select(Order).where(Order.tx_hash == ref)
    if exclude_order_code:
        q = q.where(Order.order_code != exclude_order_code)
    existing = await db.execute(q)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This transaction hash or reference was already used.")


@app.get(f"{get_settings().api_prefix}/sample-report", response_model=SampleReportPreview)
async def sample_report() -> SampleReportPreview:
    return SampleReportPreview(
        sections=[
            {
                "title": "Executive Risk Summary",
                "body": "ETHAR LABS UK LTD — modular posture score 78/100 across selected parts.",
            },
            {
                "title": "Perimeter & TLS",
                "body": "HSTS missing; TLS 1.3 supported; certificate valid 62 days.",
            },
            {
                "title": "Edge & Container Hygiene",
                "body": "Cloudflare rate limits recommended; compose file binds DB port publicly.",
            },
            {
                "title": "Certification",
                "body": "Company No. 17032523 — Reviewed by Lead Systems Architect (defensive scope).",
            },
        ]
    )


@app.post(f"{get_settings().api_prefix}/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature")
    if not verify_stripe_webhook_signature(payload, sig, settings.stripe_webhook_secret):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature.")
    try:
        event = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        return {"received": True}
    if event.get("type") == "checkout.session.completed":
        session = (event.get("data") or {}).get("object") or {}
        if session.get("payment_status") == "paid":
            order_code = (session.get("metadata") or {}).get("order_code")
            ref = session.get("id") or session.get("payment_intent")
            if order_code and ref:
                result = await db.execute(select(Order).where(Order.order_code == order_code))
                order = result.scalar_one_or_none()
                if order and not order.payment_verified:
                    order.tx_hash = f"STRIPE-{ref}"
                    order.payment_verified = True
                    order.status = OrderStatus.IN_PROGRESS.value
                    await db.commit()
                    asyncio.create_task(process_order_pipeline(order.id))
    return {"received": True}


@app.post(f"{get_settings().api_prefix}/orders", response_model=OrderCreateResponse)
async def create_order(
    body: OrderCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderCreateResponse:
    ok, msg = validate_part_ids(list(body.selected_parts))
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    milestones, total, lines = milestones_for_order(list(body.selected_parts), body.payment_plan)
    if body.payment_plan == "milestones" and not milestones_allowed(total):
        raise HTTPException(
            status_code=400,
            detail=f"Milestone plan requires order total above ${MILESTONE_MIN_TOTAL:.0f}.",
        )

    due_now = amount_due_now(milestones)
    payment_ref = body.tx_hash if body.payment_method.startswith("usdt") else body.card_reference
    await _assert_payment_ref_unused(db, payment_ref)
    verified, pay_msg = await verify_payment(
        settings,
        body.payment_method,
        body.tx_hash,
        body.card_reference,
        expected_amount_usd=due_now if body.payment_method.startswith("usdt") else None,
    )

    if verified:
        milestones, paid = apply_first_payment(milestones, payment_ref)
    else:
        paid = 0.0

    if verified and paid + 0.01 < due_now and body.payment_plan == "milestones":
        verified = False
        pay_msg = f"Initial milestone underpaid. Due now: ${due_now:.2f}."

    order_code = _generate_order_code()
    for _ in range(5):
        existing = await db.execute(select(Order).where(Order.order_code == order_code))
        if not existing.scalar_one_or_none():
            break
        order_code = _generate_order_code()

    initial_logs = json.dumps(
        [
            {
                "stage": 0,
                "title": "Order Received",
                "message": pay_msg,
                "timestamp": datetime.utcnow().isoformat(),
                "completed": verified,
            }
        ]
    )

    order = Order(
        order_code=order_code,
        client_email=str(body.client_email),
        organization=body.organization,
        package_type="modular",
        target_asset=body.target_asset,
        tech_notes=body.tech_notes,
        payment_method=body.payment_method,
        tx_hash=payment_ref,
        payment_verified=verified and can_start_pipeline(milestones),
        selected_parts_json=json.dumps(body.selected_parts),
        parts_pricing_json=json.dumps(lines),
        total_amount=total,
        payment_plan=body.payment_plan,
        paid_amount=paid,
        milestones_json=serialize_milestones(milestones),
        current_stage=0,
        status=OrderStatus.IN_PROGRESS.value
        if verified and can_start_pipeline(milestones)
        else OrderStatus.PENDING_VERIFICATION.value,
        stage_logs_json=initial_logs,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)
    order_db_id = order.id
    await db.commit()

    if order.payment_verified:
        background_tasks.add_task(process_order_pipeline, order_db_id)
        background_tasks.add_task(
            notify_payment_received,
            settings,
            order_code,
            body.organization,
            total,
            paid,
            body.payment_plan,
            body.target_asset,
        )

    track_url = f"{settings.frontend_url.rstrip('/')}/track.html?order={order_code}"
    return OrderCreateResponse(
        order_id=order_code,
        status=order.status,
        payment_verified=order.payment_verified,
        total_amount=total,
        paid_amount=paid,
        amount_due_now=amount_due_now(milestones),
        track_url=track_url,
    )


@app.post(
    f"{get_settings().api_prefix}/orders/{{order_code}}/milestones/pay",
    response_model=MilestonePaymentResponse,
)
async def pay_next_milestone(
    order_code: str,
    body: MilestonePaymentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MilestonePaymentResponse:
    result = await db.execute(select(Order).where(Order.order_code == order_code))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    milestones = parse_milestones(order.milestones_json)
    next_ms = next((m for m in milestones if not m.get("paid")), None)
    if not next_ms:
        raise HTTPException(status_code=400, detail="All milestones are already paid.")

    payment_ref = body.tx_hash if body.payment_method.startswith("usdt") else body.card_reference
    await _assert_payment_ref_unused(db, payment_ref, exclude_order_code=order_code)
    due_usd = float(next_ms["amount_usd"])
    verified, pay_msg = await verify_payment(
        settings,
        body.payment_method,
        body.tx_hash,
        body.card_reference,
        expected_amount_usd=due_usd if body.payment_method.startswith("usdt") else None,
    )
    if not verified:
        raise HTTPException(status_code=402, detail=pay_msg)

    milestones, paid = apply_milestone_payment(
        milestones, int(next_ms["milestone"]), payment_ref
    )
    order.milestones_json = serialize_milestones(milestones)
    order.paid_amount = paid
    order.payment_method = body.payment_method
    if payment_ref:
        order.tx_hash = payment_ref

    logs = json.loads(order.stage_logs_json or "[]")
    logs.append(
        {
            "stage": order.current_stage,
            "title": "Milestone Payment",
            "message": f"{next_ms['label']} received — {pay_msg}",
            "timestamp": datetime.utcnow().isoformat(),
            "completed": True,
        }
    )
    order.stage_logs_json = json.dumps(logs)

    resume = False
    if order.status == OrderStatus.AWAITING_PAYMENT.value:
        order.status = OrderStatus.IN_PROGRESS.value
        resume = True
    if not order.payment_verified and can_start_pipeline(milestones):
        order.payment_verified = True
        order.status = OrderStatus.IN_PROGRESS.value
        resume = True

    await db.commit()

    if resume:
        background_tasks.add_task(process_order_pipeline, order.id)
    background_tasks.add_task(
        notify_payment_received,
        settings,
        order_code,
        order.organization,
        float(order.total_amount),
        paid,
        order.payment_plan,
        order.target_asset,
    )

    ms_models = [MilestoneStatus(**m) for m in milestones]
    return MilestonePaymentResponse(
        order_code=order_code,
        paid_amount=paid,
        amount_due_now=amount_due_now(milestones),
        milestones=ms_models,
        status=order.status,
        message=pay_msg,
    )


@app.get(f"{get_settings().api_prefix}/orders/{{order_code}}", response_model=OrderPublicResponse)
async def get_order(order_code: str, db: AsyncSession = Depends(get_db)) -> OrderPublicResponse:
    result = await db.execute(select(Order).where(Order.order_code == order_code))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return _order_to_public(order)


@app.get(f"{get_settings().api_prefix}/orders/{{order_code}}/report")
async def download_report(
    order_code: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    result = await db.execute(select(Order).where(Order.order_code == order_code))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.status != OrderStatus.COMPLETED.value or not order.pdf_filename:
        raise HTTPException(status_code=403, detail="Report not yet released.")

    path = settings.reports_dir / order.pdf_filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report file missing.")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=order.pdf_filename,
    )


@app.post(
    f"{get_settings().api_prefix}/admin/orders/{{order_code}}/approve",
    response_model=AdminApproveResponse,
)
async def approve_order(
    order_code: str,
    secret: str = Query(...),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminApproveResponse:
    if secret.strip() != settings.admin_secret.strip():
        raise HTTPException(status_code=403, detail="Invalid admin secret.")

    result = await db.execute(select(Order).where(Order.order_code == order_code))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.status != OrderStatus.AWAITING_ADMIN_APPROVAL.value:
        raise HTTPException(status_code=409, detail="Order is not awaiting admin approval.")
    if not order.pdf_filename:
        raise HTTPException(status_code=409, detail="Report PDF not ready yet.")

    milestones = parse_milestones(order.milestones_json)
    if paid_total(milestones) + 0.01 < float(order.total_amount):
        raise HTTPException(status_code=409, detail="Outstanding milestone balance must be settled first.")

    logs_raw = order.stage_logs_json or "[]"
    try:
        logs = json.loads(logs_raw)
    except json.JSONDecodeError:
        logs = []

    logs.append(
        {
            "stage": 4,
            "title": STAGE_TITLES[4],
            "message": "Principal Engineer approved — certified report released to client portal.",
            "timestamp": datetime.utcnow().isoformat(),
            "completed": True,
        }
    )
    order.stage_logs_json = json.dumps(logs)
    order.current_stage = 4
    order.status = OrderStatus.COMPLETED.value
    await db.flush()

    return AdminApproveResponse(
        order_code=order_code,
        status=order.status,
        message="Report approved and released.",
    )
