import json
from datetime import timedelta

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, or_, select, text

from app.core.errors import Problem
from app.models.entities import (
    AccessPoint,
    AdminAction,
    GraphEvent,
    GraphState,
    Infrastructure,
    InfrastructureEdge,
    Location,
    PathEdge,
    PathNode,
)
from app.repositories.views import record
from app.services.auth import current_actor

RESOURCES = {
    "locations": Location,
    "path-nodes": PathNode,
    "path-edges": PathEdge,
    "infrastructure": Infrastructure,
}


def geometry(value):
    return func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(value)), 4326)


def require_row(db, model, key, *, lock=False):
    query = select(model).where(model.id == key)
    if lock:
        query = query.with_for_update()
    row = db.scalar(query.execution_options(populate_existing=True))
    if row is None:
        raise Problem(404, "NOT_FOUND", "Resource not found")
    return row


def expect_version(row, expected):
    if row.row_version != expected:
        raise Problem(
            409,
            "STALE_VERSION",
            "Resource changed; reload before editing",
            current_version=row.row_version,
        )


def lock_graph(db, campus_id):
    state = db.scalar(
        select(GraphState)
        .where(GraphState.campus_id == campus_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not state:
        raise Problem(404, "NOT_FOUND", "Campus not found")
    return state


def next_expiry(db, campus_id):
    values = [
        db.scalar(
            select(func.min(model.verified_until)).where(
                model.campus_id == campus_id, model.active, model.verification == "verified"
            )
        )
        for model in (PathEdge, Infrastructure)
    ]
    return min((value for value in values if value is not None), default=None)


def bump(db, state, edge_ids, reason, *, occurred_at=None):
    db.flush()
    state.version += 1
    state.updated_at = occurred_at or db.scalar(select(func.clock_timestamp()))
    state.next_expiry_at = next_expiry(db, state.campus_id)
    db.add(
        GraphEvent(
            campus_id=state.campus_id,
            graph_version=state.version,
            event_type="graph.updated",
            changed_edge_ids=sorted(set(edge_ids)),
            reason=reason,
            occurred_at=state.updated_at,
        )
    )


def expire_observations(db, campus_id):
    state = lock_graph(db, campus_id)
    now = db.scalar(select(func.clock_timestamp()))
    affected = set()
    changed = False
    for model in (Infrastructure, PathEdge):
        rows = db.scalars(
            select(model)
            .where(
                model.campus_id == campus_id,
                model.active,
                model.verification == "verified",
                model.verified_until <= now,
            )
            .order_by(model.id)
            .with_for_update()
        )
        for row in rows:
            before = record(row)
            row.verification = "needs_review"
            row.row_version += 1
            changed = True
            if model is PathEdge:
                affected.add(row.id)
            else:
                affected.update(
                    db.scalars(
                        select(InfrastructureEdge.edge_id).where(
                            InfrastructureEdge.infrastructure_id == row.id
                        )
                    )
                )
            db.add(
                AdminAction(
                    actor_id=None,
                    campus_id=campus_id,
                    action_type="observation_expired",
                    resource_type=model.__tablename__,
                    resource_id=row.id,
                    before_json=jsonable_encoder(before),
                    after_json=jsonable_encoder(record(row)),
                    reason="Verification validity elapsed",
                    request_id="system:expiry",
                    graph_version=state.version + 1,
                )
            )
    if changed:
        bump(db, state, affected, "observation_expired")
    return state


def edit_resource(db, resource, data, actor, request_id, key=None, retire=False):
    actor = current_actor(db, actor, admin=True)
    model = RESOURCES[resource]
    payload = data.model_dump(mode="json", exclude_unset=key is not None)
    reason = payload.pop("reason")
    if key:
        original = require_row(db, model, key)
        campus_id = original.campus_id
    else:
        campus_id = data.campus_id
    state = lock_graph(db, campus_id)
    if key:
        row = require_row(db, model, key, lock=True)
        expect_version(row, payload.pop("expected_version"))
        before = record(row)
        row.row_version += 1
    else:
        row = model(campus_id=campus_id)
        payload.pop("campus_id")
        before = {}
        db.add(row)
    links = payload.pop("edge_ids", None)
    access = payload.pop("access_points", None)
    incident = payload.pop("incident_geometries", [])
    nullable = (
        {"width_m", "slope_pct", "has_stairs", "has_ramp", "location_id", "name"}
        if model is PathNode
        else {"width_m", "slope_pct", "has_stairs", "has_ramp", "location_id"}
    )
    for field, value in payload.items():
        if value is None and field not in nullable:
            raise Problem(422, "INVALID_INPUT", f"{field} cannot be null")
        setattr(row, field, geometry(value) if field in ("point", "geometry") else value)
    if retire:
        row.active = False
    if model in (PathEdge, Infrastructure):
        # Changed survey facts invalidate previous verification unless explicitly re-verified.
        measured = {
            "width_m",
            "slope_pct",
            "has_stairs",
            "has_ramp",
            "surface",
            "accessibility",
            "geometry",
            "point",
        }
        if key and measured.intersection(payload) and "verification" not in payload:
            row.verification = "needs_review"
        if payload.get("verification") == "verified":
            if not row.provenance:
                raise Problem(422, "PROVENANCE_REQUIRED", "Verification requires provenance")
            now = db.scalar(select(func.clock_timestamp()))
            row.verified_at, row.verified_until, row.verified_by = (
                now,
                now + timedelta(days=30),
                actor.id,
            )
    affected = set()
    if model is PathNode and key:
        incident_rows = list(
            db.scalars(
                select(PathEdge)
                .where(or_(PathEdge.source_node_id == key, PathEdge.target_node_id == key))
                .order_by(PathEdge.id)
                .with_for_update()
            )
        )
        affected.update(edge.id for edge in incident_rows)
        provided = {item["edge_id"]: item for item in incident}
        if len(provided) != len(incident):
            raise Problem(422, "DUPLICATE_EDGE", "Incident edge IDs must be unique")
        if "point" in payload and set(provided) != {str(edge.id) for edge in incident_rows}:
            raise Problem(
                422,
                "INCIDENT_GEOMETRIES_REQUIRED",
                "Moving a node requires every incident geometry and version",
            )
        if set(provided) - {str(edge.id) for edge in incident_rows}:
            raise Problem(422, "INVALID_ASSOCIATION", "Only incident edges can be updated")
        for edge in incident_rows:
            if str(edge.id) in provided:
                edit = provided[str(edge.id)]
                expect_version(edge, edit["expected_version"])
                edge.geometry = geometry(edit["geometry"])
                edge.row_version += 1
                edge.verification = "needs_review"
    db.flush()
    if model is PathEdge:
        affected.add(row.id)
    if model is Infrastructure:
        old = list(
            db.scalars(
                select(InfrastructureEdge.edge_id).where(
                    InfrastructureEdge.infrastructure_id == row.id
                )
            )
        )
        affected.update(old)
        if links is not None:
            if len(set(links)) != len(links):
                raise Problem(422, "DUPLICATE_EDGE", "Edge IDs must be unique")
            db.execute(
                delete(InfrastructureEdge).where(InfrastructureEdge.infrastructure_id == row.id)
            )
            db.add_all(
                InfrastructureEdge(campus_id=campus_id, infrastructure_id=row.id, edge_id=edge)
                for edge in links
            )
            affected.update(links)
    if model is Location and access is not None:
        db.execute(delete(AccessPoint).where(AccessPoint.location_id == row.id))
        db.add_all(
            AccessPoint(campus_id=campus_id, location_id=row.id, **point) for point in access
        )
    db.flush()
    # Deferred geometry constraints must fail before any response can be serialized.
    db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    db.refresh(row)
    bump(db, state, [str(edge) for edge in affected], "infrastructure_updated")
    db.add(
        AdminAction(
            actor_id=actor.id,
            campus_id=campus_id,
            action_type="create" if key is None else "update",
            resource_type=resource,
            resource_id=row.id,
            before_json=jsonable_encoder(before),
            after_json=jsonable_encoder(record(row)),
            reason=reason,
            request_id=request_id,
            graph_version=state.version,
        )
    )
    db.flush()
    return row
