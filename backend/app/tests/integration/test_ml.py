"""Real DB/API optional-ML boundaries; model outputs below are explicit test doubles."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine
from app.main import app
from app.models.entities import AdminAction, GraphEvent, GraphState
from app.models.ml import InferenceJob, ModelVersion, Prediction
from app.models.reporting import EdgeRestriction
from app.services import ml_assets, ml_worker
from app.tests.conftest import login
from app.tests.integration.test_evidence import upload
from app.tests.integration.test_reporting import submit


@pytest.fixture
def prepared(client, user, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "upload_root", tmp_path / "uploads")
    report = submit(client, user[1])
    image = upload(client, user[1], report)
    assert image.status_code == 201
    return report, image.json()


@pytest.fixture
def fixture_model():
    owner = create_engine(get_settings().database_url(owner=True), hide_parameters=True)
    with Session(owner, expire_on_commit=False) as db, db.begin():
        row = ModelVersion(
            name="EXPLICIT SYNTHETIC TEST DOUBLE",
            architecture="pathable-small-cnn-v1",
            weights_sha256="a" * 64,
            dataset_manifest_sha256="b" * 64,
            manifest_sha256=uuid.uuid4().hex * 2,
            bundle_key=uuid.uuid4().hex,
            code_revision="test-double",
            license_summary="test-only",
            preprocessing_json={
                "classes": ["stairs", "pathway_obstruction"],
                "score_threshold": 0.7,
                "margin_threshold": 0.15,
            },
            evaluation_json={"synthetic_fixture": True},
            evaluated_at=datetime.now(UTC),
            test_fixture=True,
        )
        db.add(row)
        db.flush()
    owner.dispose()
    return row


def allow_test_model(monkeypatch, model):
    # No product activation: all fake outputs keep the persisted test_fixture marker.
    monkeypatch.setattr(
        ml_assets, "availability", lambda db: (db.get(ModelVersion, model.id), "TEST_DOUBLE")
    )


def enqueue(client, headers, report, image, key=None):
    return client.post(
        f"/api/v1/reports/{report['id']}/inference",
        json={"evidence_id": image["id"]},
        headers={**headers, "Idempotency-Key": str(key or uuid.uuid4())},
    )


def graph_identity(db, campus):
    return (
        db.get(GraphState, uuid.UUID(campus)).version,
        db.scalar(select(func.count()).select_from(GraphEvent)),
        db.scalar(select(func.count()).select_from(EdgeRestriction)),
    )


def output():
    return {
        "scores": [
            {"class_name": "stairs", "score": 0.8},
            {"class_name": "pathway_obstruction", "score": 0.2},
        ],
        "abstained": False,
        "latency_ms": 5,
    }


def complete_fixture(job_id):
    with Session(engine()) as db, db.begin():
        identity, token = ml_worker.claim(db)
        assert identity == uuid.UUID(job_id)
    with Session(engine()) as db, db.begin():
        assert ml_worker.finish(db, identity, token, output())


def test_unavailable_does_not_create_job_or_restrict_manual_report(client, user, prepared):
    report, image = prepared
    before = client.get(f"/api/v1/campuses/{report['campus_id']}/graph-version").json()[
        "graph_version"
    ]
    assert client.get("/api/v1/ml/status").json()["available"] is False
    response = enqueue(client, user[1], report, image)
    assert response.status_code == 503 and response.json()["code"] == "ML_UNAVAILABLE"
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(InferenceJob)) == 0
        assert db.scalar(select(func.count()).select_from(EdgeRestriction)) == 0
    assert client.get(f"/api/v1/reports/{report['id']}").json()["status"] == "pending_review"
    assert (
        client.get(f"/api/v1/campuses/{report['campus_id']}/graph-version").json()["graph_version"]
        == before
    )


def test_missing_model_is_explicit_even_when_operator_enables_ml(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "ml_enabled", True)
    result = client.get("/api/v1/ml/status").json()
    assert result["available"] is False and result["reason"] == "EVALUATED_MODEL_MISSING"


def test_fixture_cannot_be_activated_at_database_boundary(fixture_model):
    owner = create_engine(get_settings().database_url(owner=True), hide_parameters=True)
    with pytest.raises(DBAPIError), owner.begin() as db:
        db.execute(
            text("UPDATE model_versions SET enabled=true WHERE id=:id"), {"id": fixture_model.id}
        )
    owner.dispose()


def test_idempotent_submission_and_unique_evidence_model_job(
    client, user, prepared, fixture_model, monkeypatch
):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    key = uuid.uuid4()
    first = enqueue(client, user[1], report, image, key)
    second = enqueue(client, user[1], report, image, key)
    third = enqueue(client, user[1], report, image)
    assert first.status_code == second.status_code == third.status_code == 202
    assert first.json() == second.json() and third.json()["id"] == first.json()["id"]
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(InferenceJob)) == 1


def test_proposed_and_accepted_prediction_never_mutate_graph_critical_f(
    client, user, prepared, admin, fixture_model, monkeypatch
):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    user_headers = login(client, "user@example.com")
    with Session(engine()) as db:
        before = graph_identity(db, report["campus_id"])
    job = enqueue(client, user_headers, report, image).json()
    complete_fixture(job["id"])
    values = client.get(f"/api/v1/reports/{report['id']}/predictions").json()["items"]
    assert len(values) == 2 and all(x["test_fixture"] for x in values)
    with Session(engine()) as db:
        assert graph_identity(db, report["campus_id"]) == before
    admin_headers = login(client, "admin@example.com")
    prediction = values[0]
    payload = {
        "decision": "accept",
        "reason": "Accept image annotation only",
        "expected_version": 1,
    }
    headers = {**admin_headers, "Idempotency-Key": str(uuid.uuid4())}
    response = client.post(
        f"/api/v1/admin/predictions/{prediction['id']}/review", json=payload, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"
    assert (
        client.post(
            f"/api/v1/admin/predictions/{prediction['id']}/review", json=payload, headers=headers
        ).json()
        == response.json()
    )
    with Session(engine()) as db:
        assert graph_identity(db, report["campus_id"]) == before
        action = db.scalar(select(AdminAction).where(AdminAction.resource_type == "predictions"))
        assert action.graph_version is None and action.action_type == "prediction_accepted"


def test_owner_scope_csrf_and_non_admin_review(client, user, prepared, fixture_model, monkeypatch):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    assert (
        client.post(
            f"/api/v1/reports/{report['id']}/inference",
            json={"evidence_id": image["id"]},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        ).status_code
        == 403
    )
    job = enqueue(client, user[1], report, image).json()
    complete_fixture(job["id"])
    item = client.get(f"/api/v1/reports/{report['id']}/predictions").json()["items"][0]
    response = client.post(
        f"/api/v1/admin/predictions/{item['id']}/review",
        json={
            "decision": "accept",
            "reason": "Unauthorized annotation review",
            "expected_version": 1,
        },
        headers={**user[1], "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 403
    with TestClient(app) as stranger:
        assert stranger.get(f"/api/v1/reports/{report['id']}/predictions").status_code == 401
        assert (
            stranger.get(f"/api/v1/reports/{report['id']}/inference/{job['id']}").status_code == 401
        )


def test_worker_role_has_no_graph_or_prediction_review_privileges():
    settings = get_settings()
    worker = create_engine(settings.worker_database_url(), hide_parameters=True)
    for statement in [
        "SELECT * FROM graph_state",
        "UPDATE graph_state SET version=version+1",
        "INSERT INTO edge_restrictions(id) VALUES (gen_random_uuid())",
        "UPDATE predictions SET status='accepted'",
        "DELETE FROM report_evidence",
        "INSERT INTO model_versions(id) VALUES (gen_random_uuid())",
    ]:
        with pytest.raises(DBAPIError), worker.begin() as db:
            db.execute(text(statement))
    with worker.connect() as db:
        assert db.execute(text("SELECT count(*) FROM inference_jobs")).scalar() == 0
    worker.dispose()


def test_expired_worker_lease_cannot_publish_or_duplicate_outputs(
    client, user, prepared, fixture_model, monkeypatch
):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    job = enqueue(client, user[1], report, image).json()
    with Session(engine()) as db, db.begin():
        identity, old = ml_worker.claim(db)
        assert identity == uuid.UUID(job["id"])
    with Session(engine()) as db, db.begin():
        db.get(InferenceJob, identity).leased_until = datetime.now(UTC) - timedelta(seconds=1)
    with Session(engine()) as db, db.begin():
        identity, new = ml_worker.claim(db)
    assert new != old
    with Session(engine()) as db, db.begin():
        assert not ml_worker.finish(db, identity, old, output())
    with Session(engine()) as db, db.begin():
        assert ml_worker.finish(db, identity, new, output())
    with Session(engine()) as db, db.begin():
        assert not ml_worker.finish(db, identity, new, output())
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(Prediction)) == 2


@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_outputs_rollback_and_never_publish(
    client, user, prepared, fixture_model, monkeypatch, bad_score
):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    enqueue(client, user[1], report, image)
    with Session(engine()) as db, db.begin():
        identity, token = ml_worker.claim(db)
    result = output()
    result["scores"][0]["score"] = bad_score
    with pytest.raises(ValueError), Session(engine()) as db, db.begin():
        ml_worker.finish(db, identity, token, result)
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(Prediction)) == 0
        assert db.get(InferenceJob, identity).status == "running"


def test_inference_timeout_has_bounded_retry_and_terminal_failure(
    client, user, prepared, fixture_model, monkeypatch
):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    enqueue(client, user[1], report, image)
    for _attempt in range(1, 4):
        with Session(engine()) as db, db.begin():
            job = db.scalar(select(InferenceJob))
            job.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        with Session(engine()) as db, db.begin():
            identity, token = ml_worker.claim(db)
        with Session(engine()) as db, db.begin():
            assert ml_worker.finish(db, identity, token, error="INFERENCE_TIMEOUT")
    with Session(engine()) as db:
        row = db.get(InferenceJob, identity)
        assert row.attempts == 3 and row.status == "failed"
        assert db.scalar(select(func.count()).select_from(Prediction)) == 0


def test_independent_workers_claim_only_one_job(client, user, prepared, fixture_model, monkeypatch):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    enqueue(client, user[1], report, image)
    barrier = Barrier(2)

    def invoke():
        with Session(engine()) as db, db.begin():
            barrier.wait(timeout=5)
            return ml_worker.claim(db)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: invoke(), range(2)))
    assert sum(x is not None for x in results) == 1


def test_actual_restricted_worker_claims_and_commits_only_synthetic_outputs(
    client, user, prepared, fixture_model, monkeypatch
):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    submitted = enqueue(client, user[1], report, image)
    assert submitted.status_code == 202
    monkeypatch.setattr(ml_worker, "compute", lambda model, item: output())
    ml_worker.worker_engine.cache_clear()
    try:
        assert ml_worker.run_once()
        assert not ml_worker.run_once()
        result = client.get(f"/api/v1/reports/{report['id']}/inference/{submitted.json()['id']}")
        assert result.json()["status"] == "succeeded"
        values = client.get(f"/api/v1/reports/{report['id']}/predictions").json()["items"]
        assert len(values) == 2 and all(value["test_fixture"] for value in values)
    finally:
        ml_worker.worker_engine().dispose()
        ml_worker.worker_engine.cache_clear()


def test_deleted_evidence_cannot_receive_a_late_prediction(
    client, user, prepared, fixture_model, monkeypatch
):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    assert enqueue(client, user[1], report, image).status_code == 202
    with Session(engine()) as db, db.begin():
        identity, token = ml_worker.claim(db)
    version = client.get(f"/api/v1/reports/{report['id']}").json()["row_version"]
    removed = client.request(
        "DELETE",
        f"/api/v1/reports/{report['id']}/evidence/{image['id']}",
        headers=user[1],
        json={"expected_version": version},
    )
    assert removed.status_code == 204
    with Session(engine()) as db, db.begin():
        assert ml_worker.finish(db, identity, token, output())
    with Session(engine()) as db:
        assert db.get(InferenceJob, identity).status == "failed"
        assert db.get(InferenceJob, identity).error_code == "EVIDENCE_CHANGED_OR_UNAVAILABLE"
        assert db.scalar(select(func.count()).select_from(Prediction)) == 0


def test_concurrent_opposing_annotation_reviews_commit_once_without_graph_changes(
    client, user, prepared, admin, fixture_model, monkeypatch
):
    allow_test_model(monkeypatch, fixture_model)
    report, image = prepared
    owner_headers = login(client, "user@example.com")
    job = enqueue(client, owner_headers, report, image).json()
    complete_fixture(job["id"])
    prediction = client.get(f"/api/v1/reports/{report['id']}/predictions").json()["items"][0]
    with Session(engine()) as db:
        before = graph_identity(db, report["campus_id"])
    clients = [TestClient(app), TestClient(app)]
    headers = [login(item, "admin@example.com") for item in clients]
    barrier = Barrier(2)

    def invoke(index):
        barrier.wait(timeout=5)
        return clients[index].post(
            f"/api/v1/admin/predictions/{prediction['id']}/review",
            json={
                "decision": ["accept", "reject"][index],
                "reason": "Concurrent annotation-only decision",
                "expected_version": 1,
            },
            headers={**headers[index], "Idempotency-Key": str(uuid.uuid4())},
        )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(invoke, range(2)))
        assert sorted(response.status_code for response in responses) == [200, 409]
        with Session(engine()) as db:
            assert graph_identity(db, report["campus_id"]) == before
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(AdminAction)
                    .where(AdminAction.resource_type == "predictions")
                )
                == 1
            )
    finally:
        for item in clients:
            item.close()
