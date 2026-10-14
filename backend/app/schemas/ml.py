from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas.requests import Input, Reason, Version
from app.schemas.responses import Output


class MLStatus(Output):
    available: bool
    reason: str
    model_version_id: UUID | None = None
    model_name: str | None = None


class InferenceRequest(Input):
    evidence_id: UUID


class JobOut(Output):
    id: UUID
    report_id: UUID
    evidence_id: UUID
    model_version_id: UUID
    evidence_sha256: str
    status: Literal["queued", "running", "succeeded", "failed", "unavailable"]
    attempts: int
    error_code: str | None
    latency_ms: int | None
    abstained: bool | None
    created_at: datetime
    updated_at: datetime


class PredictionOut(Output):
    id: UUID
    job_id: UUID
    report_id: UUID
    evidence_id: UUID
    model_version_id: UUID
    model_name: str
    class_name: str
    score: float
    box_xyxy: list[float] | None
    status: Literal["proposed", "accepted", "rejected"]
    reviewer_id: UUID | None
    reviewed_at: datetime | None
    review_reason: str | None
    row_version: int
    created_at: datetime
    abstained: bool
    test_fixture: bool


class PredictionReview(Version):
    decision: Literal["accept", "reject"]
    reason: Reason
