from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.requests import Input, Point, Reason, Version
from app.schemas.responses import Output, Resource

Category = Literal[
    "blocked_ramp",
    "inaccessible_entrance",
    "damaged_pathway",
    "elevator_unavailable",
    "temporary_obstacle",
    "other_accessibility_concern",
]
ReportStatus = Literal["pending_review", "verified", "rejected", "resolved"]


class ReportCreate(Input):
    campus_id: UUID
    category: Category
    description: str = Field(min_length=10, max_length=2000)
    point: Point
    location_id: UUID | None = None
    infrastructure_id: UUID | None = None
    suggested_edge_ids: list[UUID] = Field(default_factory=list, max_length=50)

    @field_validator("suggested_edge_ids")
    @classmethod
    def unique_edges(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Physical edge IDs must be unique")
        return sorted(values)


class ReportReview(Version):
    decision: Literal["verify", "reject"]
    confirmed_edge_ids: list[UUID] = Field(default_factory=list, max_length=50)
    restriction_kind: Literal["closed", "temporarily_blocked"] = "temporarily_blocked"
    reason: Reason

    @model_validator(mode="after")
    def edges(self):
        if len(set(self.confirmed_edge_ids)) != len(self.confirmed_edge_ids):
            raise ValueError("Physical edge IDs must be unique")
        self.confirmed_edge_ids.sort()
        if self.decision == "reject" and self.confirmed_edge_ids:
            raise ValueError("A rejection cannot create restrictions")
        return self


class ReportResolve(Version):
    reason: Reason


class EvidenceOut(Output):
    id: UUID
    media_type: str
    byte_size: int
    width_px: int | None
    height_px: int | None
    sha256: str | None
    status: Literal["processing", "ready", "rejected", "deleted"]
    failure_code: str | None
    created_at: datetime


class ReportHistoryOut(Output):
    id: UUID
    from_status: str | None
    to_status: str
    note: str
    occurred_at: datetime
    resulting_row_version: int


class ReportOut(Resource):
    campus_id: UUID
    data_origin: Literal["synthetic_demo", "surveyed"]
    reporter_id: UUID
    category: Category
    description: str
    point: Point
    location_id: UUID | None
    infrastructure_id: UUID | None
    status: ReportStatus
    reviewer_id: UUID | None
    reviewed_at: datetime | None
    resolution_note: str | None
    resolved_at: datetime | None
    suggested_edge_ids: list[UUID]
    confirmed_edge_ids: list[UUID]
    history: list[ReportHistoryOut]
    evidence: list[EvidenceOut]


class AuditOut(Output):
    id: UUID
    actor_id: UUID | None
    campus_id: UUID | None
    action_type: str
    resource_type: str
    resource_id: UUID
    before_json: dict
    after_json: dict
    reason: str
    request_id: str
    graph_version: str | None
    created_at: datetime


class CountByCategory(Output):
    category: Category
    count: int


class ResolutionDay(Output):
    day: str
    count: int


class AnalyticsOut(Output):
    campus_id: UUID
    data_origin: Literal["synthetic_demo", "surveyed"]
    as_of: datetime
    from_time: datetime
    to_time: datetime
    mapped_infrastructure_count: int
    active_physical_pathways: int
    verified_accessible_pathways: int
    unknown_accessibility_pathways: int
    needs_review_pathways: int
    unverified_pathways: int
    active_verified_obstacles: int
    pending_reports: int
    category_distribution: list[CountByCategory]
    submitted_report_count: int
    resolution_trend: list[ResolutionDay]
    resolved_report_count: int
    average_resolution_seconds: float | None
    mapping_known_current_length_m: float
    mapping_total_length_m: float
    accessibility_mapping_coverage: float | None
