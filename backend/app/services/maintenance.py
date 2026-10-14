"""Explicit owner-role retention and orphan cleanup; never deletes ready evidence."""

import re
from datetime import timedelta

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import GraphEvent
from app.models.reporting import IdempotencyRecord, ObstacleReport, ReportEvidence, SSELease


def maintain():
    settings = get_settings()
    owner = create_engine(settings.database_url(owner=True), hide_parameters=True)
    removed = {}
    try:
        with Session(owner) as db, db.begin():
            now = db.scalar(select(func.clock_timestamp()))
            for model, label, condition in (
                (GraphEvent, "graph_events", GraphEvent.occurred_at < now - timedelta(days=7)),
                (IdempotencyRecord, "idempotency_records", IdempotencyRecord.expires_at <= now),
                (SSELease, "stream_leases", SSELease.expires_at <= now),
            ):
                removed[label] = db.execute(delete(model).where(condition)).rowcount
            stale = list(
                db.scalars(
                    select(ReportEvidence).where(
                        ReportEvidence.status == "processing",
                        ReportEvidence.created_at < now - timedelta(hours=24),
                    )
                )
            )
            reports = sorted({item.report_id for item in stale})
            for key in reports:
                report = db.scalar(
                    select(ObstacleReport).where(ObstacleReport.id == key).with_for_update()
                )
                report.row_version += 1
            for item in stale:
                item.status = "rejected"
                item.failure_code = "IMAGE_PROCESSING_INTERRUPTED"
            removed["interrupted_uploads"] = len(stale)
            db.flush()
            retained = set(
                db.scalars(
                    select(ReportEvidence.storage_key).where(
                        ReportEvidence.status.in_(["ready", "processing"])
                    )
                )
            )
        removed["private_orphan_files"] = 0
        root = settings.private_upload_root
        if root.exists():
            cutoff = (now - timedelta(hours=24)).timestamp()
            for path in root.iterdir():
                if path.is_symlink() or not path.is_file() or path.name in retained:
                    continue
                if (
                    re.fullmatch(r"[0-9a-f]{32}\.(input|normalized|png|jpg)", path.name)
                    and path.stat().st_mtime < cutoff
                ):
                    path.unlink()
                    removed["private_orphan_files"] += 1
        return removed
    finally:
        owner.dispose()
