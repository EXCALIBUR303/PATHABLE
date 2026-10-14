"""Optional model registry and durable private inference; no graph write authority."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.entities import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    architecture: Mapped[str] = mapped_column(String(80))
    weights_sha256: Mapped[str] = mapped_column(String(64))
    dataset_manifest_sha256: Mapped[str] = mapped_column(String(64))
    manifest_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    bundle_key: Mapped[str] = mapped_column(String(32), unique=True)
    code_revision: Mapped[str] = mapped_column(String(200))
    license_summary: Mapped[str] = mapped_column(Text)
    preprocessing_json: Mapped[dict] = mapped_column(JSONB)
    evaluation_json: Mapped[dict] = mapped_column(JSONB)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    test_fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint(
            "weights_sha256 ~ '^[0-9a-f]{64}$' AND dataset_manifest_sha256 ~ '^[0-9a-f]{64}$' AND manifest_sha256 ~ '^[0-9a-f]{64}$'",
            name="model_hashes",
        ),
        CheckConstraint("bundle_key ~ '^[0-9a-f]{32}$'", name="model_bundle_key"),
        CheckConstraint("NOT (enabled AND test_fixture)", name="no_fixture_activation"),
    )


class InferenceJob(Base):
    __tablename__ = "inference_jobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("obstacle_reports.id"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID)
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    model_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_versions.id"))
    evidence_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    error_code: Mapped[str | None] = mapped_column(String(80))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    abstained: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(
            ["report_id", "evidence_id"], ["report_evidence.report_id", "report_evidence.id"]
        ),
        UniqueConstraint("evidence_id", "model_version_id"),
        UniqueConstraint("id", "report_id", "evidence_id", "model_version_id"),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','unavailable')", name="job_status"
        ),
        CheckConstraint("attempts BETWEEN 0 AND 3", name="job_attempts"),
        CheckConstraint(
            "(status = 'running') = (lease_token IS NOT NULL AND leased_until IS NOT NULL)",
            name="job_lease",
        ),
        CheckConstraint("evidence_sha256 ~ '^[0-9a-f]{64}$'", name="job_hash"),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms BETWEEN 0 AND 120000", name="job_latency"
        ),
        Index("ix_jobs_claim", "status", "next_attempt_at", "leased_until"),
    )


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("obstacle_reports.id"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID)
    model_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_versions.id"))
    class_name: Mapped[str] = mapped_column(String(60))
    score: Mapped[float] = mapped_column(Float)
    box_xyxy: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_reason: Mapped[str | None] = mapped_column(Text)
    row_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(
            ["job_id", "report_id", "evidence_id", "model_version_id"],
            [
                "inference_jobs.id",
                "inference_jobs.report_id",
                "inference_jobs.evidence_id",
                "inference_jobs.model_version_id",
            ],
        ),
        UniqueConstraint("job_id", "class_name"),
        CheckConstraint(
            "class_name IN ('stairs','pathway_obstruction','damaged_pavement','ramp_obstruction','no_visible_target')",
            name="prediction_class",
        ),
        CheckConstraint(
            "score >= 0 AND score <= 1 AND score < 'Infinity'::float8", name="prediction_score"
        ),
        CheckConstraint("box_xyxy IS NULL", name="classification_no_boxes"),
        CheckConstraint("row_version >= 1", name="prediction_version"),
        CheckConstraint(
            "(status = 'proposed' AND reviewer_id IS NULL AND reviewed_at IS NULL AND review_reason IS NULL) OR (status IN ('accepted','rejected') AND reviewer_id IS NOT NULL AND reviewed_at IS NOT NULL AND length(review_reason) BETWEEN 5 AND 2000)",
            name="prediction_review",
        ),
    )
