"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

PaymentMethodLiteral = Literal["usdt_bep20", "usdt_trc20", "card_reference"]
PaymentPlanLiteral = Literal["full", "milestones"]
PartIdLiteral = Literal["part_1", "part_2", "part_3", "part_4", "part_5"]


class OrderCreateRequest(BaseModel):
    client_email: EmailStr
    organization: str = Field(min_length=1, max_length=255)
    selected_parts: list[PartIdLiteral] = Field(min_length=1)
    target_asset: str = Field(min_length=1)
    tech_notes: str | None = None
    payment_plan: PaymentPlanLiteral = "full"
    payment_method: PaymentMethodLiteral
    tx_hash: str | None = None
    card_reference: str | None = None
    authorized_scope: bool

    @field_validator("authorized_scope")
    @classmethod
    def must_authorize(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Authorized scope confirmation is required.")
        return v


class OrderCreateResponse(BaseModel):
    order_id: str
    status: str
    payment_verified: bool
    total_amount: float
    paid_amount: float
    amount_due_now: float
    track_url: str


class MilestoneStatus(BaseModel):
    milestone: int
    label: str
    percent: float
    amount_usd: float
    due_at_stage: int
    paid: bool
    tx_hash: str | None = None


class PartLineItem(BaseModel):
    part_id: str
    title: str
    unit_price_usd: float
    line_total_usd: float


class StageLogEntry(BaseModel):
    stage: int
    title: str
    message: str
    timestamp: datetime
    completed: bool


class OrderPublicResponse(BaseModel):
    order_code: str
    organization: str
    package_type: str
    target_asset: str
    current_stage: int
    status: str
    payment_verified: bool
    payment_plan: str
    total_amount: float
    paid_amount: float
    amount_due_now: float
    progress_percent: float
    selected_parts: list[str]
    line_items: list[PartLineItem]
    milestones: list[MilestoneStatus]
    next_milestone: MilestoneStatus | None = None
    posture_score: int | None = None
    executive_summary: str | None = None
    report_available: bool
    stage_logs: list[StageLogEntry]
    created_at: datetime
    updated_at: datetime


class MilestonePaymentRequest(BaseModel):
    payment_method: PaymentMethodLiteral
    tx_hash: str | None = None
    card_reference: str | None = None


class MilestonePaymentResponse(BaseModel):
    order_code: str
    paid_amount: float
    amount_due_now: float
    milestones: list[MilestoneStatus]
    status: str
    message: str


class AdminApproveResponse(BaseModel):
    order_code: str
    status: str
    message: str


class EngineeringPartResponse(BaseModel):
    id: str
    title: str
    price_usd: float
    summary: str
    badge: str | None = None
    eta_hours: int | None = None
    deliverables: list[str] = Field(default_factory=list)
    preview_sample: str | None = None


class QuickScanRequest(BaseModel):
    target: str = Field(min_length=3, max_length=512)
    organization: str | None = None


class QuickScanAlert(BaseModel):
    severity: str
    component: str
    title: str
    impact: str
    remediation_preview: str


class QuickScanResponse(BaseModel):
    target: str
    hostname: str
    organization: str | None = None
    posture_score: int
    posture_label: str
    alerts: list[QuickScanAlert]
    recommended_parts: list[str]
    recommended_part_details: list[dict[str, Any]]
    personalized_greeting: str
    scan_disclaimer: str


class PitchProspect(BaseModel):
    domain: str = Field(min_length=3)
    organization: str | None = None


class PitchGenerateRequest(BaseModel):
    prospects: list[PitchProspect] = Field(min_length=1, max_length=100)


class PitchGenerateItem(BaseModel):
    domain: str
    organization: str
    pitch_link: str
    email_template: str


class PitchGenerateResponse(BaseModel):
    items: list[PitchGenerateItem]
    company_name: str
    company_number: str


class PartsCatalogResponse(BaseModel):
    company_name: str
    company_number: str
    parts: list[EngineeringPartResponse]
    milestone_min_total_usd: float


class PaymentConfigResponse(BaseModel):
    usdt_bep20_wallet: str
    usdt_trc20_wallet: str
    company_name: str
    company_number: str


class HealthResponse(BaseModel):
    status: str
    version: str


class SampleReportPreview(BaseModel):
    sections: list[dict[str, Any]]
