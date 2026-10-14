from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.reporting import IdempotencyKey, authenticated_actor
from app.api.routes import DB, Limit
from app.core.errors import Problem
from app.models.ml import InferenceJob, Prediction
from app.repositories.views import page
from app.schemas.ml import InferenceRequest, JobOut, MLStatus, PredictionOut, PredictionReview
from app.schemas.responses import Page
from app.services import auth, inference, ml_assets, reporting

router = APIRouter(prefix="/api/v1")


@router.get("/ml/status", response_model=MLStatus)
def status(db: DB):
    model, reason = ml_assets.availability(db)
    return MLStatus(
        available=model is not None,
        reason=reason,
        model_version_id=model.id if model else None,
        model_name=model.name if model else None,
    )


@router.post("/reports/{key}/inference", status_code=202, response_model=JobOut)
def submit(
    key: UUID, payload: InferenceRequest, request: Request, db: DB, idempotency_key: IdempotencyKey
):
    actor = authenticated_actor(request, db)
    auth.rate_limit("inference", str(actor.id), 20, 3600)
    return inference.submit(db, key, payload, actor, idempotency_key)


@router.get("/reports/{key}/inference/{job_id}", response_model=JobOut)
def job(key: UUID, job_id: UUID, request: Request, db: DB):
    actor = authenticated_actor(request, db)
    reporting.current_actor(db, actor)
    reporting.require_report(db, key, actor)
    row = db.scalar(
        select(InferenceJob).where(InferenceJob.id == job_id, InferenceJob.report_id == key)
    )
    if row is None:
        raise Problem(404, "NOT_FOUND", "Inference job not found")
    return inference.job_view(row)


@router.get("/reports/{key}/predictions", response_model=Page[PredictionOut])
def predictions(key: UUID, request: Request, db: DB, limit: Limit = 25, cursor: str | None = None):
    actor = authenticated_actor(request, db)
    reporting.current_actor(db, actor)
    reporting.require_report(db, key, actor)
    rows, cursor = page(
        db,
        select(Prediction).where(Prediction.report_id == key),
        Prediction,
        limit,
        cursor,
        f"predictions:{key}:{actor.id}",
    )
    return {
        "items": [inference.prediction_view(db, row) for row in rows],
        "next_cursor": cursor,
    }


@router.post("/admin/predictions/{key}/review", response_model=PredictionOut)
def review(
    key: UUID, payload: PredictionReview, request: Request, db: DB, idempotency_key: IdempotencyKey
):
    actor = authenticated_actor(request, db, admin=True)
    return inference.review(db, key, payload, actor, request.state.request_id, idempotency_key)
