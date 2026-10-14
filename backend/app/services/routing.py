"""Database snapshot and currentness boundary around the pure routing engine."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import rfc8785
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, load_only

from app.core.errors import Problem
from app.db.session import engine
from app.models.entities import (
    AccessPoint,
    Campus,
    GraphState,
    Infrastructure,
    InfrastructureEdge,
    Location,
    PathEdge,
    PathNode,
)
from app.models.reporting import EdgeRestriction
from app.routing import (
    Dependency,
    Edge,
    EndpointNotFound,
    GraphInvalid,
    GraphSnapshot,
    Node,
    Profile,
    RoutingBudgetExceeded,
    calculate,
)
from app.schemas.routing import RouteRequest, RoutingProfile
from app.services.graph import expire_observations

MAX_GRAPH_ROWS = 10000
MAX_DEPENDENCIES = 100000
MAX_GEOMETRY_POINTS = 100000


@dataclass(frozen=True)
class LoadedGraph:
    snapshot: GraphSnapshot
    version: int
    policy_version: str
    cost_model_version: str
    valid_until: datetime | None


def profile_fingerprint(profile: RoutingProfile) -> str:
    """Canonical JSON equates 1 and 1.0, negative zero and unordered surface sets."""
    return hashlib.sha256(rfc8785.dumps(profile.model_dump())).hexdigest()


def bounded_rows(db, statement, limit=MAX_GRAPH_ROWS):
    rows = list(db.execute(statement.limit(limit + 1)))
    if len(rows) > limit:
        raise Problem(503, "GRAPH_TOO_LARGE", "Campus graph exceeds the routing snapshot limit")
    return rows


def maintain_freshness(campus_id: UUID):
    # Commit the shared expiry primitive before the separate repeatable-read snapshot.
    with Session(engine()) as db, db.begin():
        if db.get(Campus, campus_id) is None:
            raise Problem(404, "NOT_FOUND", "Campus not found")
        if db.get(GraphState, campus_id) is None:
            raise Problem(503, "GRAPH_INVALID", "Campus graph metadata is missing")
        expire_observations(db, campus_id)


def load_snapshot(request: RouteRequest) -> LoadedGraph:
    """All graph rows, associations, metadata and endpoint checks use one DB snapshot."""
    bind = engine().execution_options(isolation_level="REPEATABLE READ")
    with Session(bind) as db, db.begin():
        db.execute(text("SET TRANSACTION READ ONLY"))
        campus = db.get(Campus, request.campus_id)
        if campus is None:
            raise Problem(404, "NOT_FOUND", "Campus not found")
        state = db.get(GraphState, request.campus_id)
        if state is None:
            raise Problem(503, "GRAPH_INVALID", "Campus graph metadata is missing")
        if (
            state.cost_model_version != "walking-effort-v1"
            or state.policy_version != "accessibility-v1"
        ):
            raise Problem(503, "GRAPH_INVALID", "Campus graph policy is not supported")
        endpoints = dict(
            db.execute(
                select(PathNode.id, PathNode.campus_id).where(
                    PathNode.id.in_({request.source_id, request.destination_id})
                )
            ).all()
        )
        for key in (request.source_id, request.destination_id):
            if key not in endpoints:
                raise Problem(404, "NOT_FOUND", "Route endpoint not found")
            if endpoints[key] != request.campus_id:
                raise Problem(422, "CROSS_CAMPUS_ENDPOINT", "Route endpoints must share a campus")

        evaluated_at = db.scalar(select(func.clock_timestamp()))
        # Bound geometry before transferring/decoding it, within the same MVCC snapshot.
        edge_count, point_count, largest_edge = db.execute(
            select(
                func.count(PathEdge.id),
                func.coalesce(func.sum(func.ST_NPoints(PathEdge.geometry)), 0),
                func.max(func.ST_NPoints(PathEdge.geometry)),
            ).where(PathEdge.campus_id == request.campus_id, PathEdge.active)
        ).one()
        if largest_edge is not None and largest_edge > 1000:
            raise Problem(503, "GRAPH_INVALID", "Stored pathway geometry exceeds its point limit")
        if edge_count > MAX_GRAPH_ROWS or point_count > MAX_GEOMETRY_POINTS:
            raise Problem(503, "GRAPH_TOO_LARGE", "Campus graph exceeds the routing geometry limit")
        # Explicit 15-digit GeoJSON avoids rounding exact node/edge endpoints to nine decimals.
        node_rows = bounded_rows(
            db,
            select(PathNode, func.ST_AsGeoJSON(PathNode.point, 15))
            .options(load_only(PathNode.id, PathNode.name, PathNode.active))
            .where(PathNode.campus_id == request.campus_id)
            .order_by(PathNode.id),
        )
        edge_rows = bounded_rows(
            db,
            select(PathEdge, func.ST_AsGeoJSON(PathEdge.geometry, 15))
            .options(
                load_only(
                    PathEdge.id,
                    PathEdge.source_node_id,
                    PathEdge.target_node_id,
                    PathEdge.distance_m,
                    PathEdge.direction,
                    PathEdge.accessibility,
                    PathEdge.availability,
                    PathEdge.verification,
                    PathEdge.verified_until,
                    PathEdge.width_m,
                    PathEdge.slope_pct,
                    PathEdge.surface,
                    PathEdge.has_stairs,
                    PathEdge.has_ramp,
                    PathEdge.active,
                )
            )
            .where(PathEdge.campus_id == request.campus_id, PathEdge.active)
            .order_by(PathEdge.id),
        )
        infrastructure_rows = bounded_rows(
            db,
            select(Infrastructure)
            .options(
                load_only(
                    Infrastructure.id,
                    Infrastructure.accessibility,
                    Infrastructure.availability,
                    Infrastructure.verification,
                    Infrastructure.verified_until,
                    Infrastructure.active,
                )
            )
            .where(Infrastructure.campus_id == request.campus_id)
            .order_by(Infrastructure.id),
        )
        link_rows = bounded_rows(
            db,
            select(InfrastructureEdge.edge_id, InfrastructureEdge.infrastructure_id)
            .where(InfrastructureEdge.campus_id == request.campus_id)
            .order_by(InfrastructureEdge.edge_id, InfrastructureEdge.infrastructure_id),
            MAX_DEPENDENCIES,
        )
        names = {}
        for node_id, label, name in bounded_rows(
            db,
            select(AccessPoint.node_id, AccessPoint.label, Location.name)
            .join(Location, Location.id == AccessPoint.location_id)
            .where(AccessPoint.campus_id == request.campus_id, Location.active)
            .order_by(AccessPoint.is_primary.desc(), Location.id, AccessPoint.node_id),
            MAX_DEPENDENCIES,
        ):
            names.setdefault(node_id, f"{name} — {label}")
        dependencies = {
            row.id: Dependency(
                id=str(row.id),
                accessibility=row.accessibility,
                availability=row.availability,
                verification=row.verification,
                expires_at=row.verified_until,
                active=row.active,
            )
            for (row,) in infrastructure_rows
        }
        links: dict[UUID, list[Dependency]] = {}
        for edge_id, infrastructure_id in link_rows:
            if infrastructure_id not in dependencies:
                raise Problem(503, "GRAPH_INVALID", "Mapped infrastructure is missing")
            links.setdefault(edge_id, []).append(dependencies[infrastructure_id])
        restricted = {
            edge_id
            for (edge_id,) in bounded_rows(
                db,
                select(EdgeRestriction.edge_id)
                .where(
                    EdgeRestriction.campus_id == request.campus_id,
                    EdgeRestriction.released_at.is_(None),
                )
                .order_by(EdgeRestriction.edge_id),
                MAX_DEPENDENCIES,
            )
        }
        try:
            nodes = tuple(
                Node(
                    id=str(row.id),
                    point=tuple(json.loads(point)["coordinates"]),
                    name=names.get(row.id, row.name),
                    active=row.active,
                )
                for row, point in node_rows
            )
            edges = tuple(
                Edge(
                    id=str(row.id),
                    source_id=str(row.source_node_id),
                    target_id=str(row.target_node_id),
                    geometry=tuple(tuple(point) for point in json.loads(shape)["coordinates"]),
                    distance_m=row.distance_m,
                    direction=row.direction,
                    accessibility=row.accessibility,
                    availability=row.availability,
                    verification=row.verification,
                    expires_at=row.verified_until,
                    width_m=row.width_m,
                    slope_pct=row.slope_pct,
                    surface=row.surface,
                    has_stairs=row.has_stairs,
                    has_ramp=row.has_ramp,
                    active=row.active,
                    dependencies=tuple(links.get(row.id, ())),
                    restricted=row.id in restricted,
                )
                for row, shape in edge_rows
            )
        except (KeyError, TypeError, ValueError) as error:
            raise Problem(503, "GRAPH_INVALID", "Stored graph geometry is invalid") from error
        return LoadedGraph(
            snapshot=GraphSnapshot(nodes, edges, evaluated_at, campus.data_origin),
            version=state.version,
            policy_version=state.policy_version,
            cost_model_version=state.cost_model_version,
            valid_until=state.next_expiry_at,
        )


def validate_currentness(campus_id: UUID, loaded: LoadedGraph):
    """Validate under the shared mutation lock; no search holds this lock."""
    with Session(engine()) as db, db.begin():
        state = expire_observations(db, campus_id)
        validated_at = db.scalar(select(func.clock_timestamp()))
        current = (
            state.version == loaded.version
            and state.policy_version == loaded.policy_version
            and state.cost_model_version == loaded.cost_model_version
            and (loaded.valid_until is None or validated_at < loaded.valid_until)
            and (state.next_expiry_at is None or validated_at < state.next_expiry_at)
        )
        return current, state.version, validated_at


def route_response(request: RouteRequest):
    values = request.accessibility_profile.model_dump()
    values["excluded_surfaces"] = tuple(values["excluded_surfaces"])
    profile = Profile(**values)
    for _attempt in range(2):
        maintain_freshness(request.campus_id)
        try:
            loaded = load_snapshot(request)
            result = calculate(
                loaded.snapshot,
                str(request.source_id),
                str(request.destination_id),
                profile,
                algorithm=request.selected_algorithm,
                alternatives_limit=request.alternatives_limit,
            )
        except GraphInvalid as error:
            raise Problem(
                503, "GRAPH_INVALID", "Stored campus graph failed routing validation"
            ) from error
        except EndpointNotFound as error:
            raise Problem(404, "NOT_FOUND", "Route endpoint not found") from error
        except RoutingBudgetExceeded as error:
            raise Problem(
                503, "ROUTING_BUDGET_EXCEEDED", "Route search exceeded its work budget"
            ) from error
        current, latest, validated_at = validate_currentness(request.campus_id, loaded)
        if current:
            return {
                **result.to_dict(),
                "campus_id": request.campus_id,
                "source_id": request.source_id,
                "destination_id": request.destination_id,
                "accessibility_profile": request.accessibility_profile,
                "profile_fingerprint": profile_fingerprint(request.accessibility_profile),
                "algorithm": request.selected_algorithm,
                "graph_version": str(loaded.version),
                "policy_version": loaded.policy_version,
                "cost_model_version": loaded.cost_model_version,
                "validated_at": validated_at,
                "valid_until": loaded.valid_until,
                "data_origin": loaded.snapshot.data_origin,
            }
    raise Problem(
        409,
        "GRAPH_CHANGED_RETRY",
        "Campus observations changed during calculation; please calculate again",
        current_graph_version=str(latest),
    )
