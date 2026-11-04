"""SQLAlchemy models for orders, stages, and reports."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderStatus(str, enum.Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    AWAITING_ADMIN_APPROVAL = "AWAITING_ADMIN_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    client_access_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    client_email: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str] = mapped_column(String(255))
    package_type: Mapped[str] = mapped_column(String(64), default="modular")
    target_asset: Mapped[str] = mapped_column(Text)
    tech_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(64))
    tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payment_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    selected_parts_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parts_pricing_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    payment_plan: Mapped[str] = mapped_column(String(32), default="full")
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    milestones_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    current_stage: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(64), default=OrderStatus.PENDING_VERIFICATION.value)

    audit_findings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    posture_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pdf_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)

    stage_logs_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
