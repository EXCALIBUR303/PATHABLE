from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.requests import AccessInput, Line, Point


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProblemOut(Output):
    type: str
    title: str
    status: int
    code: str
    detail: str
    request_id: str
    field_errors: list[dict[str, str]] | None = None
    current_version: int | None = None
    current_graph_version: str | None = None


class UserOut(Output):
    id: UUID
    email: str
    display_name: str
    role: Literal["user", "admin"]
    row_version: int


class SessionOut(Output):
    user: UserOut | None
    csrf_token: str
    expires_at: datetime


class Resource(Output):
    id: UUID
    row_version: int
    created_at: datetime
    updated_at: datetime


class ProfileOut(Resource):
    avoid_stairs: bool
    max_slope_pct: float | None
    min_width_m: float | None
    excluded_surfaces: list[str]
    unknown_policy: Literal["exclude", "allow_with_warning"]
    travel_speed_mps: float


class CampusOut(Resource):
    name: str
    data_origin: Literal["synthetic_demo", "surveyed"]
    attribution: str
    default_timezone: str


class LocationOut(Resource):
    campus_id: UUID
    name: str
    kind: str
    description: str
    point: Point
    active: bool
    access_points: list[AccessInput]


class NodeOut(Resource):
    campus_id: UUID
    name: str | None
    level: int
    point: Point
    active: bool


class ObservedOut(Resource):
    campus_id: UUID
    accessibility: Literal["accessible", "inaccessible", "unknown"]
    availability: Literal["open", "closed", "temporarily_blocked"]
    verification: Literal["verified", "unverified", "needs_review"]
    verified_at: datetime | None
    verified_until: datetime | None
    provenance: str
    active: bool


class InfrastructureOut(ObservedOut):
    name: str
    kind: str
    location_id: UUID | None
    point: Point
    edge_ids: list[UUID]


class EdgeOut(ObservedOut):
    source_node_id: UUID
    target_node_id: UUID
    geometry: Line
    distance_m: float
    direction: Literal["both", "forward", "reverse"]
    width_m: float | None
    slope_pct: float | None
    surface: str
    has_stairs: bool | None
    has_ramp: bool | None
    effective_availability: Literal["open", "closed", "temporarily_blocked"] = "open"
    active_restriction_count: int = 0


class SavedOut(Resource):
    campus_id: UUID
    location_id: UUID
    label: str


class Page[T](Output):
    items: list[T]
    next_cursor: str | None


class VersionOut(Output):
    graph_version: str
    validated_at: datetime
    valid_until: datetime | None
    data_origin: Literal["synthetic_demo", "surveyed"]
    cost_model_version: str
    policy_version: str


class Feature(Output):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: Point | Line
    properties: NodeOut | EdgeOut


class GraphOut(VersionOut):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature]
