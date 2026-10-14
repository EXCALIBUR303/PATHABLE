"""Owner-scoped reports and atomic, source-specific administrative decisions."""

import hashlib
import json
from datetime import timedelta
from uuid import uuid4

import rfc8785
from sqlalchemy import case, func, select, text
from sqlalchemy.dialects.postgresql import insert

from app.core.errors import Problem
from app.models.entities import (
    AdminAction,
    Campus,
    Infrastructure,
    InfrastructureEdge,
    Location,
    PathEdge,
)
from app.models.reporting import (
    EdgeRestriction,
    IdempotencyRecord,
    ObstacleReport,
    ReportEdge,
    ReportEvidence,
    ReportStatusEvent,
)
from app.schemas.reporting import EvidenceOut, ReportHistoryOut, ReportOut
from app.services import graph
from app.services.auth import current_actor


def require_report(db, key, actor, *, lock=False):
    query = select(ObstacleReport).where(ObstacleReport.id == key)
    if actor.role != "admin":
        query = query.where(ObstacleReport.reporter_id == actor.id)
    if lock:
        query = query.with_for_update()
    row = db.scalar(query.execution_options(populate_existing=True))
    if row is None:
        raise Problem(404, "NOT_FOUND", "Report not found")
    return row


def claim(db, actor, operation, key, payload):
    digest = hashlib.sha256(rfc8785.dumps(payload)).hexdigest()
    now = db.scalar(select(func.clock_timestamp()))
    existing = db.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.actor_id == actor.id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.key == key,
        )
        .with_for_update()
    )
    if existing and existing.expires_at <= now:
        db.delete(existing)
        db.flush()
    identity = uuid4()
    inserted = db.scalar(
        insert(IdempotencyRecord)
        .values(
            id=identity,
            actor_id=actor.id,
            operation=operation,
            key=key,
            request_hash=digest,
            expires_at=now + timedelta(hours=24),
        )
        .on_conflict_do_nothing(index_elements=["actor_id", "operation", "key"])
        .returning(IdempotencyRecord.id)
    )
    row = (
        db.get(IdempotencyRecord, inserted)
        if inserted
        else db.scalar(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.actor_id == actor.id,
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.key == key,
            )
            .with_for_update()
        )
    )
    if row.request_hash != digest:
        raise Problem(
            409, "IDEMPOTENCY_CONFLICT", "This request key was used for a different payload"
        )
    return row, row.result_json


def complete(db, claim_row, value, status=200):
    claim_row.result_status = status
    claim_row.result_json = value
    db.flush()
    db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    return value


def report_view(db, row):
    campus = db.get(Campus, row.campus_id)
    history = list(
        db.scalars(
            select(ReportStatusEvent)
            .where(ReportStatusEvent.report_id == row.id)
            .order_by(
                ReportStatusEvent.resulting_row_version,
                ReportStatusEvent.occurred_at,
                case((ReportStatusEvent.to_status == "submitted", 0), else_=1),
                ReportStatusEvent.id,
            )
        )
    )
    # Active evidence is never hidden by older terminal upload attempts.
    evidence = list(
        db.scalars(
            select(ReportEvidence)
            .where(ReportEvidence.report_id == row.id)
            .order_by(
                ReportEvidence.status.in_(["ready", "processing"]).desc(),
                ReportEvidence.created_at.desc(),
                ReportEvidence.id,
            )
            .limit(103)
        )
    )
    value = {
        "id": row.id,
        "campus_id": row.campus_id,
        "data_origin": campus.data_origin,
        "reporter_id": row.reporter_id,
        "category": row.category,
        "description": row.description,
        "point": json.loads(row.point_json),
        "location_id": row.location_id,
        "infrastructure_id": row.infrastructure_id,
        "status": row.status,
        "reviewer_id": row.reviewer_id,
        "reviewed_at": row.reviewed_at,
        "resolution_note": row.resolution_note,
        "resolved_at": row.resolved_at,
        "row_version": row.row_version,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "suggested_edge_ids": list(
            db.scalars(
                select(ReportEdge.edge_id)
                .where(ReportEdge.report_id == row.id)
                .order_by(ReportEdge.edge_id)
            )
        ),
        "confirmed_edge_ids": list(
            db.scalars(
                select(EdgeRestriction.edge_id)
                .where(EdgeRestriction.report_id == row.id)
                .distinct()
                .order_by(EdgeRestriction.edge_id)
            )
        ),
        "history": [
            ReportHistoryOut.model_validate(item).model_dump(mode="json") for item in history
        ],
        "evidence": [
            EvidenceOut.model_validate(item).model_dump(mode="json") for item in reversed(evidence)
        ],
    }
    return ReportOut.model_validate(value).model_dump(mode="json")


def validate_edges(db, campus_id, ids):
    rows = list(
        db.scalars(
            select(PathEdge).where(PathEdge.id.in_(ids)).order_by(PathEdge.id).with_for_update()
        )
    )
    if len(rows) != len(ids) or any(row.campus_id != campus_id or not row.active for row in rows):
        raise Problem(422, "INVALID_ASSOCIATION", "Choose active physical pathways in this campus")
    return rows


def create_report(db, payload, actor, key):
    actor = current_actor(db, actor)
    claimed, replay = claim(db, actor, "report:create", key, payload.model_dump(mode="json"))
    if replay is not None:
        return replay
    campus = graph.require_row(db, Campus, payload.campus_id)
    if campus.boundary is None or not db.scalar(
        select(func.ST_Covers(Campus.boundary, graph.geometry(payload.point.model_dump()))).where(
            Campus.id == campus.id
        )
    ):
        raise Problem(422, "OUTSIDE_CAMPUS", "Select a point within the supported campus boundary")
    for model, identity in (
        (Location, payload.location_id),
        (Infrastructure, payload.infrastructure_id),
    ):
        if identity is not None:
            row = graph.require_row(db, model, identity)
            if row.campus_id != campus.id or not row.active:
                raise Problem(
                    422,
                    "INVALID_ASSOCIATION",
                    "Report references must be active and in this campus",
                )
    # Submission does not change or lock graph state; suggestions never restrict an edge.
    rows = list(db.scalars(select(PathEdge).where(PathEdge.id.in_(payload.suggested_edge_ids))))
    if len(rows) != len(payload.suggested_edge_ids) or any(
        row.campus_id != campus.id or not row.active for row in rows
    ):
        raise Problem(
            422, "INVALID_ASSOCIATION", "Suggested pathways must be active and in this campus"
        )
    now = db.scalar(select(func.clock_timestamp()))
    row = ObstacleReport(
        campus_id=campus.id,
        reporter_id=actor.id,
        category=payload.category,
        description=payload.description,
        point=graph.geometry(payload.point.model_dump()),
        location_id=payload.location_id,
        infrastructure_id=payload.infrastructure_id,
        status="pending_review",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    db.add_all(
        ReportEdge(campus_id=campus.id, report_id=row.id, edge_id=edge)
        for edge in payload.suggested_edge_ids
    )
    for before, after, note in (
        (None, "submitted", "Concern submitted"),
        ("submitted", "pending_review", "Awaiting administrator review"),
    ):
        db.add(
            ReportStatusEvent(
                report_id=row.id,
                from_status=before,
                to_status=after,
                actor_id=actor.id,
                note=note,
                occurred_at=now,
                resulting_row_version=1,
            )
        )
    db.flush()
    db.refresh(row)
    return complete(db, claimed, report_view(db, row), 201)


def decide_report(db, key, payload, actor, request_id, idempotency_key, *, resolve=False):
    # Recheck and lock authorization inside the domain transaction.
    actor = current_actor(db, actor, admin=True)
    # Authorize before accessing or replaying private data.
    original = require_report(db, key, actor)
    operation = ("report:resolve:" if resolve else "report:review:") + str(key)
    claimed, replay = claim(db, actor, operation, idempotency_key, payload.model_dump(mode="json"))
    if replay is not None:
        return replay
    state = graph.lock_graph(db, original.campus_id)
    row = require_report(db, key, actor, lock=True)
    graph.expect_version(row, payload.expected_version)
    required = "verified" if resolve else "pending_review"
    if row.status != required:
        raise Problem(
            422,
            "INVALID_TRANSITION",
            f"Only {required.replace('_', ' ')} reports support this action",
        )
    if (
        not resolve
        and payload.decision == "verify"
        and db.scalar(
            select(func.count())
            .select_from(ReportEvidence)
            .where(ReportEvidence.report_id == row.id, ReportEvidence.status == "processing")
        )
    ):
        raise Problem(
            409, "EVIDENCE_PROCESSING", "Wait for evidence processing before verification"
        )
    before = {"status": row.status, "row_version": row.row_version}
    now = db.scalar(select(func.clock_timestamp()))
    affected = []
    if resolve:
        restrictions = list(
            db.scalars(
                select(EdgeRestriction)
                .where(EdgeRestriction.report_id == row.id, EdgeRestriction.released_at.is_(None))
                .order_by(EdgeRestriction.edge_id)
                .with_for_update()
            )
        )
        affected = sorted({item.edge_id for item in restrictions})
        validate_edges_for_resolution = list(
            db.scalars(
                select(PathEdge.id)
                .where(PathEdge.id.in_(affected))
                .order_by(PathEdge.id)
                .with_for_update()
            )
        )
        if len(validate_edges_for_resolution) != len(affected):
            raise Problem(503, "GRAPH_INVALID", "A restricted physical pathway is missing")
        for item in restrictions:
            item.released_by = actor.id
            item.released_at = now
        row.status = "resolved"
        row.resolved_at = now
        row.resolution_note = payload.reason
    elif payload.decision == "verify":
        ids = payload.confirmed_edge_ids
        if not ids and row.infrastructure_id:
            infrastructure = graph.require_row(db, Infrastructure, row.infrastructure_id, lock=True)
            if infrastructure.active:
                ids = list(
                    db.scalars(
                        select(InfrastructureEdge.edge_id)
                        .where(InfrastructureEdge.infrastructure_id == infrastructure.id)
                        .order_by(InfrastructureEdge.edge_id)
                    )
                )
        if not ids:
            raise Problem(
                422,
                "CONFIRMED_EDGES_REQUIRED",
                "Verification requires at least one confirmed physical pathway",
            )
        validate_edges(db, row.campus_id, ids)
        affected = ids
        db.add_all(
            EdgeRestriction(
                campus_id=row.campus_id,
                report_id=row.id,
                edge_id=edge,
                kind=payload.restriction_kind,
                reason=payload.reason,
                created_by=actor.id,
                created_at=now,
            )
            for edge in ids
        )
        row.status = "verified"
        row.reviewer_id = actor.id
        row.reviewed_at = now
    else:
        row.status = "rejected"
        row.reviewer_id = actor.id
        row.reviewed_at = now
    row.row_version += 1
    row.updated_at = now
    db.add(
        ReportStatusEvent(
            report_id=row.id,
            from_status=before["status"],
            to_status=row.status,
            actor_id=actor.id,
            note=payload.reason,
            occurred_at=now,
            resulting_row_version=row.row_version,
        )
    )
    if affected:
        graph.bump(
            db,
            state,
            [str(edge) for edge in affected],
            "report_resolved" if resolve else "report_verified",
            occurred_at=now,
        )
    db.add(
        AdminAction(
            actor_id=actor.id,
            campus_id=row.campus_id,
            action_type="report_" + row.status,
            resource_type="obstacle_reports",
            resource_id=row.id,
            before_json=before,
            after_json={
                "status": row.status,
                "row_version": row.row_version,
                "edge_ids": [str(edge) for edge in affected],
            },
            reason=payload.reason,
            request_id=request_id,
            graph_version=state.version if affected else None,
            created_at=now,
        )
    )
    db.flush()
    return complete(db, claimed, report_view(db, row))
