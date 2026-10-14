import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, column_property, mapped_column


class Base(DeclarativeBase):
    pass


class Identity:
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    row_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class User(Identity, Base):
    __tablename__ = "users"
    normalized_email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10), default="user", server_default="user")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    auth_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    __table_args__ = (CheckConstraint("role IN ('user','admin')", name="user_role"),)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    issued_auth_version: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Profile(Identity, Base):
    __tablename__ = "accessibility_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    avoid_stairs: Mapped[bool] = mapped_column(default=True)
    max_slope_pct: Mapped[float | None] = mapped_column(Float, default=8)
    min_width_m: Mapped[float | None] = mapped_column(Float, default=0.9)
    excluded_surfaces: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=lambda: ["uneven", "gravel"]
    )
    unknown_policy: Mapped[str] = mapped_column(default="exclude")
    travel_speed_mps: Mapped[float] = mapped_column(Float, default=1)
    __table_args__ = (
        CheckConstraint("max_slope_pct BETWEEN 0 AND 100", name="profile_slope"),
        CheckConstraint("min_width_m > 0 AND min_width_m <= 10", name="profile_width"),
        CheckConstraint("travel_speed_mps BETWEEN 0.1 AND 3", name="profile_speed"),
        CheckConstraint(
            "unknown_policy IN ('exclude','allow_with_warning')", name="profile_unknown"
        ),
        CheckConstraint(
            "excluded_surfaces <@ ARRAY['smooth','uneven','gravel']::text[]",
            name="profile_surfaces",
        ),
    )


class Campus(Identity, Base):
    __tablename__ = "campuses"
    name: Mapped[str] = mapped_column(String(120))
    data_origin: Mapped[str] = mapped_column(String(20))
    attribution: Mapped[str] = mapped_column(Text)
    default_timezone: Mapped[str] = mapped_column(default="UTC")
    boundary = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    __table_args__ = (
        CheckConstraint("data_origin IN ('synthetic_demo','surveyed')", name="campus_origin"),
    )


class CampusRow(Identity):
    campus_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campuses.id"), index=True)


class Location(CampusRow, Base):
    __tablename__ = "locations"
    name: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(default=True)
    point = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    point_json = column_property(func.ST_AsGeoJSON(point))
    __table_args__ = (UniqueConstraint("campus_id", "id"),)


class PathNode(CampusRow, Base):
    __tablename__ = "path_nodes"
    name: Mapped[str | None] = mapped_column(String(120))
    level: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(default=True)
    point = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    point_json = column_property(func.ST_AsGeoJSON(point))
    __table_args__ = (
        UniqueConstraint("campus_id", "id"),
        CheckConstraint("level BETWEEN -20 AND 200", name="node_level"),
    )


class AccessPoint(Base):
    __tablename__ = "location_access_points"
    campus_id: Mapped[uuid.UUID] = mapped_column(UUID)
    location_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    node_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    label: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(default="entrance")
    is_primary: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (
        ForeignKeyConstraint(["campus_id", "location_id"], ["locations.campus_id", "locations.id"]),
        ForeignKeyConstraint(["campus_id", "node_id"], ["path_nodes.campus_id", "path_nodes.id"]),
        Index(
            "one_primary_access_point",
            "location_id",
            unique=True,
            postgresql_where=is_primary.is_(True),
        ),
        CheckConstraint("kind IN ('entrance','junction')", name="access_kind"),
    )


class Observations:
    accessibility: Mapped[str] = mapped_column(default="unknown")
    availability: Mapped[str] = mapped_column(default="open")
    verification: Mapped[str] = mapped_column(default="unverified")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    provenance: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(default=True)


def observation_constraints(prefix):
    return (
        CheckConstraint(
            "accessibility IN ('accessible','inaccessible','unknown')",
            name=prefix + "_accessibility",
        ),
        CheckConstraint(
            "availability IN ('open','closed','temporarily_blocked')", name=prefix + "_availability"
        ),
        CheckConstraint(
            "verification IN ('verified','unverified','needs_review')",
            name=prefix + "_verification",
        ),
        CheckConstraint(
            "verification <> 'verified' OR (verified_at IS NOT NULL AND verified_until IS NOT NULL AND verified_by IS NOT NULL AND verified_until > verified_at AND length(provenance) > 0)",
            name=prefix + "_verified_evidence",
        ),
    )


class PathEdge(CampusRow, Observations, Base):
    __tablename__ = "path_edges"
    source_node_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    target_node_id: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    geometry = mapped_column(Geometry("LINESTRING", srid=4326), nullable=False)
    geometry_json = column_property(func.ST_AsGeoJSON(geometry))
    distance_m: Mapped[float] = mapped_column(Float, server_default="0")
    direction: Mapped[str] = mapped_column(default="both")
    width_m: Mapped[float | None] = mapped_column(Float)
    slope_pct: Mapped[float | None] = mapped_column(Float)
    surface: Mapped[str] = mapped_column(default="unknown")
    has_stairs: Mapped[bool | None]
    has_ramp: Mapped[bool | None]
    __table_args__ = (
        UniqueConstraint("campus_id", "id"),
        ForeignKeyConstraint(
            ["campus_id", "source_node_id"], ["path_nodes.campus_id", "path_nodes.id"]
        ),
        ForeignKeyConstraint(
            ["campus_id", "target_node_id"], ["path_nodes.campus_id", "path_nodes.id"]
        ),
        CheckConstraint("source_node_id <> target_node_id", name="edge_distinct_nodes"),
        CheckConstraint("distance_m > 0 AND distance_m < 'Infinity'::float8", name="edge_distance"),
        CheckConstraint("width_m > 0 AND width_m <= 10", name="edge_width"),
        CheckConstraint("slope_pct BETWEEN -100 AND 100", name="edge_slope"),
        CheckConstraint("direction IN ('both','forward','reverse')", name="edge_direction"),
        CheckConstraint("surface IN ('smooth','uneven','gravel','unknown')", name="edge_surface"),
        *observation_constraints("edge"),
    )


class Infrastructure(CampusRow, Observations, Base):
    __tablename__ = "infrastructure"
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str]
    point = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    point_json = column_property(func.ST_AsGeoJSON(point))
    __table_args__ = (
        UniqueConstraint("campus_id", "id"),
        ForeignKeyConstraint(["campus_id", "location_id"], ["locations.campus_id", "locations.id"]),
        CheckConstraint(
            "kind IN ('ramp','stairs','entrance','elevator','pathway')", name="infrastructure_kind"
        ),
        *observation_constraints("infrastructure"),
    )


class InfrastructureEdge(Base):
    __tablename__ = "infrastructure_edges"
    campus_id: Mapped[uuid.UUID] = mapped_column(UUID)
    infrastructure_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    edge_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["campus_id", "infrastructure_id"], ["infrastructure.campus_id", "infrastructure.id"]
        ),
        ForeignKeyConstraint(["campus_id", "edge_id"], ["path_edges.campus_id", "path_edges.id"]),
    )


class SavedDestination(Identity, Base):
    __tablename__ = "saved_destinations"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    campus_id: Mapped[uuid.UUID] = mapped_column(UUID)
    location_id: Mapped[uuid.UUID] = mapped_column(UUID)
    label: Mapped[str] = mapped_column(String(120))
    __table_args__ = (
        ForeignKeyConstraint(["campus_id", "location_id"], ["locations.campus_id", "locations.id"]),
        UniqueConstraint("user_id", "location_id"),
    )


class GraphState(Base):
    __tablename__ = "graph_state"
    campus_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campuses.id"), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    cost_model_version: Mapped[str] = mapped_column(default="walking-effort-v1")
    policy_version: Mapped[str] = mapped_column(default="accessibility-v1")
    next_expiry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("version >= 1", name="graph_version_positive"),)


class GraphEvent(Base):
    __tablename__ = "graph_events"
    campus_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campuses.id"), primary_key=True)
    graph_version: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_type: Mapped[str]
    changed_edge_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID))
    reason: Mapped[str]
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AdminAction(Base):
    __tablename__ = "admin_actions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    campus_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campuses.id"))
    action_type: Mapped[str]
    resource_type: Mapped[str]
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID)
    before_json: Mapped[dict] = mapped_column(JSONB)
    after_json: Mapped[dict] = mapped_column(JSONB)
    reason: Mapped[str]
    request_id: Mapped[str]
    graph_version: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class RateBucket(Base):
    __tablename__ = "rate_limit_buckets"
    scope: Mapped[str] = mapped_column(String(40), primary_key=True)
    identifier_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    bucket_start: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    count: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
