"""Public route contract; a computational profile has no persisted row version."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.requests import Input, Point
from app.schemas.responses import Output, VersionOut


class RoutingProfile(Input):
    avoid_stairs: bool = Field(strict=True)
    max_slope_pct: float | None = Field(ge=0, le=100, strict=True)
    min_width_m: float | None = Field(gt=0, le=10, strict=True)
    excluded_surfaces: list[Literal["smooth", "uneven", "gravel"]] = Field(max_length=3)
    unknown_policy: Literal["exclude", "allow_with_warning"]
    travel_speed_mps: float = Field(ge=0.1, le=3, strict=True)

    @field_validator("excluded_surfaces")
    @classmethod
    def canonical_surfaces(cls, value):
        return sorted(set(value))


class RouteRequest(Input):
    campus_id: UUID
    source_id: UUID
    destination_id: UUID
    accessibility_profile: RoutingProfile
    selected_algorithm: Literal["dijkstra", "astar"] = "astar"
    alternatives_limit: int = Field(default=2, ge=0, le=2, strict=True)


class RouteWarning(Output):
    code: Literal[
        "UNKNOWN_ACCESSIBILITY",
        "UNVERIFIED_OBSERVATION",
        "MISSING_OBSERVATION",
        "DEPENDENCY_UNCERTAINTY",
        "DURATION_ESTIMATE",
        "SYNTHETIC_DATA",
    ]
    message: str
    edge_ids: list[UUID]


class RouteArc(Output):
    edge_id: UUID
    direction: Literal["forward", "reverse"]


class RouteInstruction(Output):
    edge_id: UUID
    distance_m: float = Field(ge=0)
    text: str
    maneuver: Literal["depart", "continue", "turn_left", "turn_right", "turn_back"]
    node_id: UUID
    slope_pct: float | None


class RouteVerification(Output):
    summary: Literal["observations_current", "contains_uncertainty"]
    verified_distance_m: float = Field(ge=0)
    uncertain_distance_m: float = Field(ge=0)
    earliest_expiry_at: datetime | None


class RouteLine(Output):
    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]] = Field(min_length=2)


class Route(Output):
    node_ids: list[UUID]
    arcs: list[RouteArc]
    geometry: Point | RouteLine
    total_distance_m: float = Field(ge=0)
    estimated_duration_s: float = Field(ge=0)
    cost_m_equivalent: float = Field(ge=0)
    instructions: list[RouteInstruction]
    verification: RouteVerification
    warnings: list[RouteWarning]


class RouteStats(Output):
    expansions: int = Field(ge=0)
    searches: int = Field(ge=0)
    elapsed_ms: float = Field(ge=0)
    alternative_candidates: int = Field(ge=0)


class RouteResultBase(VersionOut):
    campus_id: UUID
    source_id: UUID
    destination_id: UUID
    accessibility_profile: RoutingProfile
    profile_fingerprint: str
    algorithm: Literal["dijkstra", "astar"]
    alternatives_exhaustive: bool
    excluded_edge_counts: dict[str, int]
    warnings: list[RouteWarning]
    stats: RouteStats


class RouteFound(RouteResultBase):
    status: Literal["found"]
    reason: None = None
    primary: Route
    alternatives: list[Route]


class RouteNoRoute(RouteResultBase):
    status: Literal["no_route"]
    reason: Literal["disconnected", "constraints_exclude_all_paths"]
    primary: None = None
    alternatives: list[Route] = Field(max_length=0)
