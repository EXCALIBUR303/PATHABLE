from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Name = Annotated[str, Field(min_length=1, max_length=120)]
Reason = Annotated[str, Field(min_length=3, max_length=500)]
Surface = Literal["smooth", "uneven", "gravel", "unknown"]


class Input(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, str_strip_whitespace=True, hide_input_in_errors=True
    )


class Credentials(Input):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)
    # Password spaces are significant.
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=False)

    @field_validator("email", mode="before")
    @classmethod
    def email_normalize(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class Register(Credentials):
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError("Display name required")
        return value.strip()


class Version(Input):
    expected_version: int = Field(ge=1, strict=True)


class EditUser(Version):
    display_name: str = Field(min_length=1, max_length=80)


class ProfileInput(Version):
    avoid_stairs: bool = Field(strict=True)
    max_slope_pct: float | None = Field(ge=0, le=100)
    min_width_m: float | None = Field(gt=0, le=10)
    excluded_surfaces: list[Literal["smooth", "uneven", "gravel"]] = Field(max_length=3)
    unknown_policy: Literal["exclude", "allow_with_warning"]
    travel_speed_mps: float = Field(ge=0.1, le=3)


class Point(Input):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]

    @field_validator("coordinates")
    @classmethod
    def bounds(cls, value):
        if not (-180 <= value[0] <= 180 and -90 <= value[1] <= 90):
            raise ValueError("WGS84 longitude/latitude required")
        return value


class Line(Input):
    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]] = Field(min_length=2, max_length=1000)

    @field_validator("coordinates")
    @classmethod
    def bounds(cls, value):
        for point in value:
            Point(coordinates=point)
        return value


class AdminCreate(Input):
    campus_id: UUID
    reason: Reason


class AdminEdit(Version):
    reason: Reason


class NodeCreate(AdminCreate):
    name: Name | None = None
    point: Point
    level: int = Field(default=0, ge=-20, le=200, strict=True)


class IncidentGeometry(Version):
    edge_id: UUID
    geometry: Line


class NodeEdit(AdminEdit):
    name: Name | None = None
    point: Point | None = None
    level: int | None = Field(default=None, ge=-20, le=200, strict=True)
    active: bool | None = Field(default=None, strict=True)
    incident_geometries: list[IncidentGeometry] = Field(default_factory=list, max_length=1000)


class AccessInput(Input):
    node_id: UUID
    label: Name
    kind: Literal["entrance", "junction"] = "entrance"
    is_primary: bool = Field(default=False, strict=True)


class LocationCreate(AdminCreate):
    name: Name
    kind: Annotated[str, Field(min_length=1, max_length=30)]
    description: str = Field(default="", max_length=2000)
    point: Point


class LocationEdit(AdminEdit):
    name: Name | None = None
    kind: Annotated[str, Field(min_length=1, max_length=30)] | None = None
    description: str | None = Field(default=None, max_length=2000)
    point: Point | None = None
    active: bool | None = Field(default=None, strict=True)
    access_points: list[AccessInput] | None = Field(default=None, max_length=20)


class ObservationInput(Input):
    accessibility: Literal["accessible", "inaccessible", "unknown"] = "unknown"
    availability: Literal["open", "closed", "temporarily_blocked"] = "open"
    verification: Literal["verified", "unverified", "needs_review"] = "unverified"
    provenance: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def evidence_required(self):
        if self.verification == "verified" and not self.provenance:
            raise ValueError("Verification requires provenance")
        return self


class EdgeCreate(AdminCreate, ObservationInput):
    source_node_id: UUID
    target_node_id: UUID
    geometry: Line
    direction: Literal["both", "forward", "reverse"] = "both"
    width_m: float | None = Field(default=None, gt=0, le=10)
    slope_pct: float | None = Field(default=None, ge=-100, le=100)
    surface: Surface = "unknown"
    has_stairs: bool | None = Field(default=None, strict=True)
    has_ramp: bool | None = Field(default=None, strict=True)


class ObservationEdit(AdminEdit):
    accessibility: Literal["accessible", "inaccessible", "unknown"] | None = None
    availability: Literal["open", "closed", "temporarily_blocked"] | None = None
    verification: Literal["verified", "unverified", "needs_review"] | None = None
    provenance: str | None = Field(default=None, max_length=2000)
    active: bool | None = Field(default=None, strict=True)


class EdgeEdit(ObservationEdit):
    geometry: Line | None = None
    direction: Literal["both", "forward", "reverse"] | None = None
    width_m: float | None = Field(default=None, gt=0, le=10)
    slope_pct: float | None = Field(default=None, ge=-100, le=100)
    surface: Surface | None = None
    has_stairs: bool | None = Field(default=None, strict=True)
    has_ramp: bool | None = Field(default=None, strict=True)


class InfrastructureCreate(AdminCreate, ObservationInput):
    name: Name
    kind: Literal["ramp", "stairs", "entrance", "elevator", "pathway"]
    location_id: UUID | None = None
    point: Point
    edge_ids: list[UUID] = Field(default_factory=list, max_length=1000)


class InfrastructureEdit(ObservationEdit):
    name: Name | None = None
    kind: Literal["ramp", "stairs", "entrance", "elevator", "pathway"] | None = None
    location_id: UUID | None = None
    point: Point | None = None
    edge_ids: list[UUID] | None = Field(default=None, max_length=1000)


class SaveDestination(Input):
    location_id: UUID
    label: Name | None = None
