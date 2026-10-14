import asyncio
import time
from datetime import datetime
from typing import Annotated
from uuid import UUID

import anyio
from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.api.routes import DB, Limit
from app.core.errors import Problem
from app.models.entities import AdminAction, Campus
from app.models.reporting import ObstacleReport, ReportEvidence
from app.repositories.views import page
from app.schemas.reporting import (
    AnalyticsOut,
    AuditOut,
    Category,
    EvidenceOut,
    ReportCreate,
    ReportOut,
    ReportResolve,
    ReportReview,
    ReportStatus,
)
from app.schemas.requests import Version
from app.schemas.responses import Page
from app.services import analytics, auth, events, evidence, graph, reporting

router = APIRouter(prefix="/api/v1")
IdempotencyKey = Annotated[UUID, Header(alias="Idempotency-Key")]


def authenticated_actor(request, db, *, admin=False, quota=None):
    actor = auth.require_user(request, db, admin=admin)
    # Release the optional/auth session connection before independent quota/decoder sessions.
    db.commit()
    if quota:
        auth.rate_limit(quota, str(actor.id), 10 if quota == "report" else 20, 3600)
    return actor


@router.post("/reports", status_code=201, response_model=ReportOut)
def submit(payload: ReportCreate, request: Request, db: DB, idempotency_key: IdempotencyKey):
    actor = authenticated_actor(request, db, quota="report")
    return reporting.create_report(db, payload, actor, idempotency_key)


@router.get("/reports", response_model=Page[ReportOut])
def own_reports(
    request: Request,
    db: DB,
    campus_id: UUID | None = None,
    status: ReportStatus | None = None,
    limit: Limit = 25,
    cursor: str | None = None,
):
    actor = auth.require_user(request, db)
    query = select(ObstacleReport).where(ObstacleReport.reporter_id == actor.id)
    if campus_id:
        query = query.where(ObstacleReport.campus_id == campus_id)
    if status:
        query = query.where(ObstacleReport.status == status)
    rows, next_cursor = page(
        db, query, ObstacleReport, limit, cursor, f"reports:{actor.id}:{campus_id}:{status}"
    )
    return {"items": [reporting.report_view(db, row) for row in rows], "next_cursor": next_cursor}


@router.get("/reports/{key}", response_model=ReportOut)
def report_detail(key: UUID, request: Request, db: DB):
    actor = auth.require_user(request, db)
    return reporting.report_view(db, reporting.require_report(db, key, actor))


@router.get("/admin/reports", response_model=Page[ReportOut])
def queue(
    request: Request,
    db: DB,
    campus_id: UUID,
    status: ReportStatus | None = None,
    category: Category | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    limit: Limit = 25,
    cursor: str | None = None,
):
    auth.require_user(request, db, admin=True)
    graph.require_row(db, Campus, campus_id)
    if (
        (from_time and not from_time.tzinfo)
        or (to_time and not to_time.tzinfo)
        or (from_time and to_time and from_time >= to_time)
    ):
        raise Problem(422, "INVALID_WINDOW", "Use increasing timezone-aware dates")
    query = select(ObstacleReport).where(ObstacleReport.campus_id == campus_id)
    if status:
        query = query.where(ObstacleReport.status == status)
    if category:
        query = query.where(ObstacleReport.category == category)
    if from_time:
        query = query.where(ObstacleReport.created_at >= from_time)
    if to_time:
        query = query.where(ObstacleReport.created_at < to_time)
    rows, next_cursor = page(
        db,
        query,
        ObstacleReport,
        limit,
        cursor,
        f"admin-reports:{campus_id}:{status}:{category}:{from_time}:{to_time}",
    )
    return {"items": [reporting.report_view(db, row) for row in rows], "next_cursor": next_cursor}


@router.post("/admin/reports/{key}/review", response_model=ReportOut)
def review(
    key: UUID, payload: ReportReview, request: Request, db: DB, idempotency_key: IdempotencyKey
):
    actor = authenticated_actor(request, db, admin=True)
    return reporting.decide_report(
        db, key, payload, actor, request.state.request_id, idempotency_key
    )


@router.post("/admin/reports/{key}/resolve", response_model=ReportOut)
def resolve(
    key: UUID, payload: ReportResolve, request: Request, db: DB, idempotency_key: IdempotencyKey
):
    actor = authenticated_actor(request, db, admin=True)
    return reporting.decide_report(
        db, key, payload, actor, request.state.request_id, idempotency_key, resolve=True
    )


@router.post(
    "/reports/{key}/evidence",
    status_code=201,
    response_model=EvidenceOut,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file", "expected_version"],
                        "additionalProperties": False,
                        "properties": {
                            "file": {"type": "string", "format": "binary"},
                            "expected_version": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 2147483647,
                            },
                        },
                    }
                }
            },
        }
    },
)
async def upload(key: UUID, request: Request, db: DB):
    actor = await run_in_threadpool(authenticated_actor, request, db, quota="upload")
    # Authorize the resource before parsing even a bounded multipart body.
    row = await run_in_threadpool(reporting.require_report, db, key, actor)
    if row.reporter_id != actor.id:
        raise Problem(404, "NOT_FOUND", "Report not found")
    await run_in_threadpool(db.commit)
    async with request.form(max_files=1, max_fields=1, max_part_size=1024) as form:
        file = form.get("file")
        version = form.get("expected_version")
        if (
            not isinstance(file, UploadFile)
            or not isinstance(version, str)
            or not version.isascii()
            or not version.isdigit()
            or not 0 < int(version) < 2**31
            or set(form.keys()) != {"file", "expected_version"}
        ):
            raise Problem(422, "INVALID_UPLOAD", "Supply one file and the report expected_version")
        data = await file.read(evidence.MAX_BYTES + 1)
        return await run_in_threadpool(
            evidence.process_upload,
            key,
            actor,
            int(version),
            file.content_type,
            file.filename,
            data,
        )


@router.get(
    "/reports/{key}/evidence/{evidence_id}/content",
    response_class=FileResponse,
    responses={
        200: {
            "description": "Authorized private normalized image",
            "content": {
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
def content(key: UUID, evidence_id: UUID, request: Request, db: DB):
    actor = auth.require_user(request, db)
    reporting.require_report(db, key, actor)
    row = db.scalar(
        select(ReportEvidence).where(
            ReportEvidence.id == evidence_id,
            ReportEvidence.report_id == key,
            ReportEvidence.status == "ready",
        )
    )
    if row is None:
        raise Problem(404, "NOT_FOUND", "Ready evidence not found")
    path = evidence.content_path(row.storage_key)
    if not path.is_file() or path.is_symlink():
        raise Problem(503, "EVIDENCE_UNAVAILABLE", "Private evidence file is unavailable")
    return FileResponse(
        path,
        media_type=row.media_type,
        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline"},
    )


@router.delete("/reports/{key}/evidence/{evidence_id}", status_code=204)
def remove_evidence(key: UUID, evidence_id: UUID, payload: Version, request: Request, db: DB):
    actor = authenticated_actor(request, db)
    evidence.delete_evidence(db, key, evidence_id, actor, payload.expected_version)


@router.get("/admin/analytics", response_model=AnalyticsOut)
def dashboard(
    request: Request,
    db: DB,
    campus_id: UUID,
    from_time: Annotated[datetime, Query(alias="from")],
    to_time: Annotated[datetime, Query(alias="to")],
):
    auth.require_user(request, db, admin=True)
    return analytics.analytics(db, campus_id, from_time, to_time)


@router.get("/admin/audit", response_model=Page[AuditOut])
def audit(request: Request, db: DB, campus_id: UUID, limit: Limit = 25, cursor: str | None = None):
    auth.require_user(request, db, admin=True)
    graph.require_row(db, Campus, campus_id)
    rows, next_cursor = page(
        db,
        select(AdminAction).where(AdminAction.campus_id == campus_id),
        AdminAction,
        limit,
        cursor,
        f"audit:{campus_id}",
    )
    return {
        "items": [
            AuditOut.model_validate(
                {
                    **{
                        field: getattr(row, field)
                        for field in AuditOut.model_fields
                        if field != "graph_version"
                    },
                    "graph_version": str(row.graph_version)
                    if row.graph_version is not None
                    else None,
                }
            )
            for row in rows
        ],
        "next_cursor": next_cursor,
    }


@router.get(
    "/campuses/{campus_id}/events",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Public durable graph SSE replay and heartbeat comments",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        }
    },
)
def event_stream(
    campus_id: UUID,
    request: Request,
    db: DB,
    last_event_id: Annotated[str | None, Header(max_length=100)] = None,
):
    _, actor, _ = auth.current_session(request, db, required=False)
    identity = str(actor.id) if actor else auth.client_identifier(request)
    graph.require_row(db, Campus, campus_id)
    db.commit()
    initial = events.event_batch(campus_id, last_event_id)
    lease = events.claim_stream(identity)

    async def stream():
        cursor = last_event_id
        heartbeat = time.monotonic()
        try:
            batch = initial
            if not batch:
                # Flush data immediately when a retained cursor has no new events;
                # otherwise HTTP proxies may hold headers until the first heartbeat.
                yield ": heartbeat\n\n"
            while True:
                for event in batch:
                    cursor = event["id"]
                    yield events.encode_event(event)
                if time.monotonic() - heartbeat >= 15:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic()
                await asyncio.sleep(1)
                batch = await run_in_threadpool(
                    events.event_batch, campus_id, cursor, lease, trusted=True
                )
        except (Problem, DBAPIError):
            # A dependency failure terminates the stream; clients must revalidate.
            yield 'event: stream.error\ndata: {"code":"STREAM_UNAVAILABLE"}\n\n'
        finally:
            with anyio.CancelScope(shield=True):
                try:
                    await run_in_threadpool(events.release_stream, lease)
                except Exception:
                    pass  # Expiring DB lease bounds cleanup after an outage/process death.

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
