"""Phase 4 persistence. Evidence contents and reporter identity stay private."""

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
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
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.models.entities import Base, CampusRow


class ObstacleReport(CampusRow, Base):
    __tablename__ = "obstacle_reports"
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    point = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    point_json = column_property(func.ST_AsGeoJSON(point, 15))
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    infrastructure_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    status: Mapped[str] = mapped_column(String(20), default="pending_review")
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("campus_id", "id"),
        ForeignKeyConstraint(["campus_id", "location_id"], ["locations.campus_id", "locations.id"]),
        ForeignKeyConstraint(
            ["campus_id", "infrastructure_id"], ["infrastructure.campus_id", "infrastructure.id"]
        ),
        CheckConstraint(
            "category IN ('blocked_ramp','inaccessible_entrance','damaged_pathway','elevator_unavailable','temporary_obstacle','other_accessibility_concern')",
            name="report_category",
        ),
        CheckConstraint("length(description) BETWEEN 10 AND 2000", name="report_description"),
        CheckConstraint(
            "status IN ('pending_review','verified','rejected','resolved')", name="report_status"
        ),
        CheckConstraint("row_version >= 1", name="report_version"),
        CheckConstraint(
            "(status = 'pending_review' AND reviewer_id IS NULL AND reviewed_at IS NULL AND resolved_at IS NULL) OR (status IN ('verified','rejected') AND reviewer_id IS NOT NULL AND reviewed_at IS NOT NULL AND resolved_at IS NULL) OR (status = 'resolved' AND reviewer_id IS NOT NULL AND reviewed_at IS NOT NULL AND resolved_at IS NOT NULL AND resolution_note IS NOT NULL)",
            name="report_review_metadata",
        ),
        Index("ix_reports_campus_status_created", "campus_id", "status", "created_at"),
    )


class ReportEdge(Base):
    __tablename__ = "report_edges"
    campus_id: Mapped[uuid.UUID] = mapped_column(UUID)
    report_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    edge_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["campus_id", "report_id"], ["obstacle_reports.campus_id", "obstacle_reports.id"]
        ),
        ForeignKeyConstraint(["campus_id", "edge_id"], ["path_edges.campus_id", "path_edges.id"]),
    )


class ReportStatusEvent(Base):
    __tablename__ = "report_status_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("obstacle_reports.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resulting_row_version: Mapped[int] = mapped_column(Integer)
    __table_args__ = (
        CheckConstraint(
            "to_status IN ('submitted','pending_review','verified','rejected','resolved')",
            name="history_status",
        ),
        CheckConstraint(
            "from_status IS NULL OR from_status IN ('submitted','pending_review','verified')",
            name="history_from",
        ),
        CheckConstraint("resulting_row_version >= 1", name="history_version"),
    )


class ReportEvidence(Base):
    __tablename__ = "report_evidence"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("obstacle_reports.id"), index=True)
    uploader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(80), unique=True)
    media_type: Mapped[str] = mapped_column(String(20))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    width_px: Mapped[int | None] = mapped_column(Integer)
    height_px: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="processing")
    failure_code: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("report_id", "id"),
        CheckConstraint(
            "status IN ('processing','ready','rejected','deleted')", name="evidence_status"
        ),
        CheckConstraint("media_type IN ('image/jpeg','image/png')", name="evidence_type"),
        CheckConstraint("byte_size BETWEEN 1 AND 10485760", name="evidence_bytes"),
        CheckConstraint(
            "status <> 'ready' OR (width_px IS NOT NULL AND height_px IS NOT NULL AND width_px > 0 AND height_px > 0 AND width_px::bigint * height_px <= 20000000 AND sha256 IS NOT NULL)",
            name="evidence_dimensions",
        ),
        CheckConstraint("storage_key ~ '^[0-9a-f]{32}\\.(png|jpg)$'", name="evidence_key"),
    )


class EdgeRestriction(Base):
    __tablename__ = "edge_restrictions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    campus_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campuses.id"))
    report_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    edge_id: Mapped[uuid.UUID] = mapped_column(UUID)
    kind: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    released_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["campus_id", "report_id"], ["obstacle_reports.campus_id", "obstacle_reports.id"]
        ),
        ForeignKeyConstraint(["campus_id", "edge_id"], ["path_edges.campus_id", "path_edges.id"]),
        CheckConstraint("kind IN ('closed','temporarily_blocked')", name="restriction_kind"),
        CheckConstraint(
            "(released_at IS NULL) = (released_by IS NULL)", name="restriction_release"
        ),
        Index("ix_active_edge_restrictions", "edge_id", postgresql_where=released_at.is_(None)),
        Index(
            "one_active_report_restriction",
            "report_id",
            "edge_id",
            unique=True,
            postgresql_where=released_at.is_(None) & report_id.is_not(None),
        ),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    operation: Mapped[str] = mapped_column(String(100))
    key: Mapped[uuid.UUID] = mapped_column(UUID)
    request_hash: Mapped[str] = mapped_column(String(64))
    result_status: Mapped[int | None] = mapped_column(Integer)
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    __table_args__ = (UniqueConstraint("actor_id", "operation", "key"),)


class SSELease(Base):
    __tablename__ = "sse_leases"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    identifier_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
