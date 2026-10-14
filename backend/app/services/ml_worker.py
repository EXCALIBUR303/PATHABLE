"""Dedicated restricted-role worker; short leases, bounded child and atomic outputs."""

import json
import math
import subprocess
import time
from datetime import timedelta
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import and_, create_engine, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import ROOT, get_settings
from app.ml_contracts import AssetError, digest
from app.models.ml import InferenceJob, ModelVersion, Prediction
from app.models.reporting import ReportEvidence
from app.services import evidence, ml_assets


@lru_cache
def worker_engine():
    return create_engine(
        get_settings().worker_database_url(),
        hide_parameters=True,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000 -c lock_timeout=5000",
        },
    )


def claim(db):
    now = db.scalar(select(func.clock_timestamp()))
    # Finalize crashed jobs after the last bounded attempt, without losing their provenance.
    exhausted = list(
        db.scalars(
            select(InferenceJob)
            .where(
                InferenceJob.status == "running",
                InferenceJob.leased_until <= now,
                InferenceJob.attempts >= 3,
            )
            .with_for_update(skip_locked=True)
            .limit(100)
        )
    )
    for job in exhausted:
        job.status, job.error_code = "failed", "LEASE_ATTEMPTS_EXHAUSTED"
        job.lease_token = job.leased_until = None
        job.updated_at = now
    row = db.scalar(
        select(InferenceJob)
        .where(
            InferenceJob.attempts < 3,
            or_(
                and_(InferenceJob.status == "queued", InferenceJob.next_attempt_at <= now),
                and_(InferenceJob.status == "running", InferenceJob.leased_until <= now),
            ),
        )
        .order_by(InferenceJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if row:
        row.status = "running"
        row.attempts += 1
        row.lease_token = uuid4()
        row.leased_until = now + timedelta(seconds=120)
        row.updated_at = now
        db.flush()
        return row.id, row.lease_token
    return None


def compute(model, item):
    if not get_settings().ml_enabled:
        raise AssetError("ML_DISABLED")
    ml_assets.verify(model)
    path = evidence.content_path(item.storage_key)
    if item.status != "ready" or digest(path, 10 * 1024 * 1024) != item.sha256:
        raise AssetError("EVIDENCE_CHANGED_OR_UNAVAILABLE")
    result = subprocess.run(
        [
            str(get_settings().ml_python),
            "-m",
            "app.services.ml_tensor_process",
            str(ml_assets.model_root(model)),
            str(path),
        ],
        cwd=ROOT / "backend",
        env=ml_assets.child_environment(),
        timeout=30,
        capture_output=True,
        check=False,
    )
    if result.returncode or len(result.stdout) > 65536:
        raise AssetError("INFERENCE_FAILED")
    return json.loads(result.stdout)


def validate_result(result, model):
    classes = model.preprocessing_json["classes"]
    if (
        set(result) != {"scores", "abstained", "latency_ms"}
        or not isinstance(result["scores"], list)
        or len(result["scores"]) != len(classes)
    ):
        raise AssetError("INVALID_MODEL_OUTPUT")
    scores = {}
    for row in result["scores"]:
        if (
            set(row) != {"class_name", "score"}
            or row["class_name"] not in classes
            or row["class_name"] in scores
        ):
            raise AssetError("INVALID_MODEL_OUTPUT")
        value = row["score"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise AssetError("INVALID_MODEL_OUTPUT")
        scores[row["class_name"]] = value
    if (
        abs(sum(scores.values()) - 1) > 1e-5
        or isinstance(result["latency_ms"], bool)
        or not isinstance(result["latency_ms"], int)
        or not 0 <= result["latency_ms"] <= 120000
    ):
        raise AssetError("INVALID_MODEL_OUTPUT")
    order = sorted(scores.values(), reverse=True)
    abstained = (
        order[0] < model.preprocessing_json["score_threshold"]
        or order[0] - order[1] < model.preprocessing_json["margin_threshold"]
    )
    if not isinstance(result["abstained"], bool) or result["abstained"] != abstained:
        raise AssetError("INVALID_MODEL_OUTPUT")
    return scores


def finish(db, identity, token, result=None, error=None):
    now = db.scalar(select(func.clock_timestamp()))
    job = db.scalar(
        select(InferenceJob)
        .where(InferenceJob.id == identity)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not job or job.status != "running" or job.lease_token != token or job.leased_until <= now:
        return False
    evidence.lock_evidence_content(db, job.evidence_id)
    item = db.scalar(
        select(ReportEvidence)
        .where(ReportEvidence.id == job.evidence_id)
        .execution_options(populate_existing=True)
    )
    model = db.get(ModelVersion, job.model_version_id)
    if item.status != "ready" or item.sha256 != job.evidence_sha256:
        error = "EVIDENCE_CHANGED_OR_UNAVAILABLE"
    if result is not None and error is None:
        scores = validate_result(result, model)
        for label, value in scores.items():
            db.add(
                Prediction(
                    job_id=job.id,
                    report_id=job.report_id,
                    evidence_id=job.evidence_id,
                    model_version_id=job.model_version_id,
                    class_name=label,
                    score=value,
                )
            )
        db.flush()  # Source guard sees running; readiness and outputs commit together.
        job.status = "succeeded"
        job.abstained = result["abstained"]
        job.latency_ms = result["latency_ms"]
        job.error_code = None
    else:
        retryable = error in {"INFERENCE_TIMEOUT", "INFERENCE_FAILED"}
        job.status = (
            "queued"
            if retryable and job.attempts < 3
            else "unavailable"
            if error in {"ML_DISABLED", "MODEL_ASSETS_INVALID", "ML_RUNTIME_MISSING"}
            else "failed"
        )
        job.error_code = error or "INFERENCE_FAILED"
        job.next_attempt_at = now + timedelta(seconds=5 * job.attempts)
    job.lease_token = job.leased_until = None
    job.updated_at = now
    db.flush()
    return True


def run_once():
    with Session(worker_engine(), expire_on_commit=False) as db, db.begin():
        claimed = claim(db)
    if not claimed:
        return False
    identity, token = claimed
    with Session(worker_engine(), expire_on_commit=False) as db:
        job = db.get(InferenceJob, identity)
        model = db.get(ModelVersion, job.model_version_id)
        item = db.get(ReportEvidence, job.evidence_id)
    try:
        result = compute(model, item)
        validate_result(result, model)
        error = None
    except subprocess.TimeoutExpired:
        result, error = None, "INFERENCE_TIMEOUT"
    except (AssetError, OSError, ValueError, TypeError, KeyError):
        result, error = None, "INFERENCE_FAILED"
        # Stable typed unavailable states, without logging private paths/tracebacks.
        try:
            ml_assets.verify(model)
        except (AssetError, OSError, ValueError, TypeError, KeyError):
            error = "MODEL_ASSETS_INVALID"
        if not get_settings().ml_enabled:
            error = "ML_DISABLED"
        elif not get_settings().ml_python.is_file():
            error = "ML_RUNTIME_MISSING"
    with Session(worker_engine()) as db, db.begin():
        finish(db, identity, token, result, error)
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        print(json.dumps({"processed": run_once()}))
    else:
        while True:
            if not run_once():
                time.sleep(1)


if __name__ == "__main__":
    main()
