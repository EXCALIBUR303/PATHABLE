"""Private API job/review transactions. Predictions are annotations only."""

from sqlalchemy import func, select, text

from app.core.errors import Problem
from app.models.entities import AdminAction
from app.models.ml import InferenceJob, ModelVersion, Prediction
from app.models.reporting import ReportEvidence
from app.schemas.ml import JobOut, PredictionOut
from app.services import graph, ml_assets, reporting


def job_view(row):
    return JobOut.model_validate(row, from_attributes=True).model_dump(mode="json")


def prediction_view(db, row):
    job = db.get(InferenceJob, row.job_id)
    model = db.get(ModelVersion, row.model_version_id)
    return PredictionOut(
        **{key: getattr(row, key) for key in Prediction.__table__.columns.keys()},
        model_name=model.name,
        abstained=bool(job.abstained),
        test_fixture=model.test_fixture,
    ).model_dump(mode="json")


def submit(db, report_id, payload, actor, key):
    actor = reporting.current_actor(db, actor)
    report = reporting.require_report(db, report_id, actor, lock=True)
    record, replay = reporting.claim(
        db, actor, f"inference:{report_id}", key, payload.model_dump(mode="json")
    )
    if replay:
        return replay
    evidence = db.scalar(
        select(ReportEvidence)
        .where(ReportEvidence.id == payload.evidence_id, ReportEvidence.report_id == report.id)
        .with_for_update()
    )
    if evidence is None:
        raise Problem(404, "NOT_FOUND", "Evidence not found")
    if evidence.status != "ready":
        raise Problem(422, "EVIDENCE_NOT_READY", "Inference requires a normalized ready image")
    model, reason = ml_assets.availability(db)
    if model is None:
        raise Problem(503, "ML_UNAVAILABLE", "Image analysis is unavailable: " + reason)
    # Serialize admission and unique evidence/model jobs without long compute transactions.
    db.execute(text("SELECT pg_advisory_xact_lock(5149052)"))
    job = db.scalar(
        select(InferenceJob).where(
            InferenceJob.evidence_id == evidence.id, InferenceJob.model_version_id == model.id
        )
    )
    if job is None:
        active = db.scalar(
            select(func.count())
            .select_from(InferenceJob)
            .where(InferenceJob.status.in_(["queued", "running"]))
        )
        if active >= 100:
            raise Problem(503, "ML_QUEUE_FULL", "Image analysis queue is full; try later")
        job = InferenceJob(
            report_id=report.id,
            evidence_id=evidence.id,
            requested_by=actor.id,
            model_version_id=model.id,
            evidence_sha256=evidence.sha256,
        )
        db.add(job)
        db.flush()
    return reporting.complete(db, record, job_view(job), status=202)


def review(db, key, payload, actor, request_id, idempotency_key):
    actor = reporting.current_actor(db, actor, admin=True)
    row = db.scalar(
        select(Prediction)
        .where(Prediction.id == key)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise Problem(404, "NOT_FOUND", "Prediction not found")
    record, replay = reporting.claim(
        db, actor, f"prediction-review:{key}", idempotency_key, payload.model_dump(mode="json")
    )
    if replay:
        return replay
    graph.expect_version(row, payload.expected_version)
    if row.status != "proposed":
        raise Problem(422, "PREDICTION_ALREADY_REVIEWED", "Prediction review is final")
    now = db.scalar(select(func.clock_timestamp()))
    row.status = "accepted" if payload.decision == "accept" else "rejected"
    row.reviewer_id, row.reviewed_at, row.review_reason = actor.id, now, payload.reason
    row.row_version += 1
    report = reporting.require_report(db, row.report_id, actor)
    db.add(
        AdminAction(
            actor_id=actor.id,
            campus_id=report.campus_id,
            action_type="prediction_" + row.status,
            resource_type="predictions",
            resource_id=row.id,
            before_json={"status": "proposed"},
            after_json={"status": row.status, "model_version_id": str(row.model_version_id)},
            reason=payload.reason,
            request_id=request_id,
            graph_version=None,
            created_at=now,
        )
    )
    db.flush()
    return reporting.complete(db, record, prediction_view(db, row))
