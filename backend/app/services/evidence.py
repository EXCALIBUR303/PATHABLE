"""Private normalized evidence, bounded reservations and crash-safe readiness."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from threading import BoundedSemaphore
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Problem
from app.db.session import engine
from app.models.reporting import ReportEvidence
from app.schemas.reporting import EvidenceOut
from app.services import auth, graph, reporting

DECODERS = BoundedSemaphore(2)
MAX_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_BYTES + 65536


def storage_root():
    root = get_settings().private_upload_root
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def content_path(key):
    if not re.fullmatch(r"[0-9a-f]{32}\.(png|jpg)", key):
        raise Problem(503, "EVIDENCE_UNAVAILABLE", "Stored evidence reference is invalid")
    return storage_root() / key


def require_pending(db, report_id, actor, expected_version):
    row = reporting.require_report(db, report_id, actor, lock=True)
    if row.reporter_id != actor.id:
        raise Problem(404, "NOT_FOUND", "Report not found")
    graph.expect_version(row, expected_version)
    if row.status != "pending_review":
        raise Problem(
            422, "REPORT_NOT_PENDING", "Evidence can change only while a report awaits review"
        )
    return row


def reserve(report_id, actor, expected_version, mime, size):
    with Session(engine(), expire_on_commit=False) as db, db.begin():
        # Serialize per-user storage across reports, then this report's three-slot quota.
        actor = auth.current_actor(db, actor, exclusive=True)
        row = require_pending(db, report_id, actor, expected_version)
        count = db.scalar(
            select(func.count())
            .select_from(ReportEvidence)
            .where(
                ReportEvidence.report_id == row.id,
                ReportEvidence.status.in_(["processing", "ready"]),
            )
        )
        used = db.scalar(
            select(func.coalesce(func.sum(ReportEvidence.byte_size), 0)).where(
                ReportEvidence.uploader_id == actor.id,
                ReportEvidence.status.in_(["processing", "ready"]),
            )
        )
        if count >= 3:
            raise Problem(409, "EVIDENCE_LIMIT", "A report can hold at most three images")
        # Reserve the maximum normalized size, since re-encoding may expand a small input.
        if used + MAX_BYTES > get_settings().upload_user_quota_bytes:
            raise Problem(413, "STORAGE_QUOTA", "Your private evidence storage quota is full")
        identity = uuid4()
        evidence = ReportEvidence(
            id=identity,
            report_id=row.id,
            uploader_id=actor.id,
            storage_key=identity.hex + (".jpg" if mime == "image/jpeg" else ".png"),
            media_type=mime,
            byte_size=MAX_BYTES,
            status="processing",
        )
        db.add(evidence)
        row.row_version += 1
        db.flush()
        return evidence


def process_upload(report_id, actor, expected_version, mime, filename, data):
    if not DECODERS.acquire(blocking=False):
        raise Problem(503, "IMAGE_PROCESSING_BUSY", "Image processing is busy; try again shortly")
    try:
        return _process_upload(report_id, actor, expected_version, mime, filename, data)
    finally:
        DECODERS.release()


def _process_upload(report_id, actor, expected_version, mime, filename, data):
    if mime not in ("image/jpeg", "image/png"):
        raise Problem(415, "UNSUPPORTED_IMAGE", "Only JPEG and PNG evidence is supported")
    if (
        not filename
        or "/" in filename
        or "\\" in filename
        or "\x00" in filename
        or filename in (".", "..")
    ):
        raise Problem(422, "INVALID_FILENAME", "Choose a file without path components")
    if not data or len(data) > MAX_BYTES:
        raise Problem(413, "IMAGE_TOO_LARGE", "Evidence must contain between 1 byte and 10 MiB")
    evidence = reserve(report_id, actor, expected_version, mime, len(data))
    root = storage_root()
    raw = root / (evidence.id.hex + ".input")
    normalized = root / (evidence.id.hex + ".normalized")
    result = {"ok": False, "code": "IMAGE_PROCESSING_FAILED"}
    try:
        descriptor = os.open(raw, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        worker = subprocess.run(
            [sys.executable, "-m", "app.services.image_worker", str(raw), str(normalized), mime],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        if worker.stdout:
            result = json.loads(worker.stdout)
        if result.get("ok") and worker.returncode != 0:
            result = {"ok": False, "code": "IMAGE_PROCESSING_FAILED"}
        with Session(engine(), expire_on_commit=False) as db, db.begin():
            authorization_error = None
            try:
                actor = auth.current_actor(db, actor)
            except Problem as error:
                # Decoding runs without a DB lock. Revoke readiness if the account
                # changed meanwhile, and release the existing quota reservation.
                authorization_error = error
                result = {"ok": False, "code": error.code}
            row = reporting.require_report(db, report_id, actor, lock=True)
            stored = db.get(ReportEvidence, evidence.id)
            if row.status != "pending_review":
                result = {"ok": False, "code": "REPORT_NOT_PENDING"}
            if result.get("ok"):
                os.chmod(normalized, 0o600)
                os.replace(normalized, content_path(stored.storage_key))
                stored.status = "ready"
                for field in ("width_px", "height_px", "byte_size", "sha256"):
                    setattr(stored, field, result[field])
            else:
                stored.status = "rejected"
                stored.failure_code = result["code"]
            row.row_version += 1
            db.flush()
            response = EvidenceOut.model_validate(stored).model_dump(mode="json")
        if authorization_error:
            raise authorization_error
        if not result.get("ok"):
            raise Problem(
                422,
                result["code"],
                "Image could not be accepted; refresh the report and choose a valid JPEG or PNG",
            )
        return response
    except (subprocess.TimeoutExpired, ValueError, OSError):
        with Session(engine()) as db, db.begin():
            row = reporting.require_report(db, report_id, actor, lock=True)
            stored = db.get(ReportEvidence, evidence.id)
            if stored.status == "processing":
                stored.status = "rejected"
                stored.failure_code = "IMAGE_PROCESSING_FAILED"
                row.row_version += 1
        raise Problem(
            422, "IMAGE_PROCESSING_FAILED", "Image processing failed or exceeded its limits"
        ) from None
    finally:
        raw.unlink(missing_ok=True)
        normalized.unlink(missing_ok=True)


def lock_evidence_content(db, evidence_id):
    # Shared with the restricted ML worker, which intentionally has no evidence UPDATE grant.
    db.execute(
        select(
            func.pg_advisory_xact_lock(func.hashtextextended("ml-evidence:" + str(evidence_id), 0))
        )
    )


def delete_evidence(db, report_id, evidence_id, actor, expected_version):
    actor = auth.current_actor(db, actor)
    row = require_pending(db, report_id, actor, expected_version)
    lock_evidence_content(db, evidence_id)
    evidence = db.scalar(
        select(ReportEvidence)
        .where(ReportEvidence.id == evidence_id, ReportEvidence.report_id == row.id)
        .with_for_update()
    )
    if evidence is None:
        raise Problem(404, "NOT_FOUND", "Evidence not found")
    if evidence.status == "processing":
        raise Problem(409, "EVIDENCE_PROCESSING", "Wait for image processing before removal")
    if evidence.status != "deleted":
        evidence.status = "deleted"
        row.row_version += 1
    # Commit the authorization/state before removing an immutable file. A crash can
    # leave a private orphan, but never a ready reference to a deleted file.
    db.commit()
    content_path(evidence.storage_key).unlink(missing_ok=True)
