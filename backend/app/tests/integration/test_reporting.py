"""Real report/review/restriction transactions and authorization boundaries."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.entities import AdminAction, GraphEvent, GraphState
from app.models.reporting import (
    EdgeRestriction,
    IdempotencyRecord,
    ObstacleReport,
    ReportStatusEvent,
)
from app.services import reporting
from app.services.seed import demo_id
from app.tests.conftest import login
from app.tests.integration.test_routing import CID, STEP_FREE, request_body

RAMP = str(demo_id("edge:ramp-cross"))


def payload(**changes):
    return {
        "campus_id": CID,
        "category": "blocked_ramp",
        "description": "A fictional barrier is blocking the mapped ramp.",
        "point": {"type": "Point", "coordinates": [0.0001, 0.0001]},
        "infrastructure_id": str(demo_id("infrastructure:ramp")),
        "suggested_edge_ids": [RAMP],
        **changes,
    }


def submit(client, headers, **changes):
    response = client.post(
        "/api/v1/reports",
        json=payload(**changes),
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 201, response.text
    return response.json()


def review(client, headers, row, decision="verify", **changes):
    return client.post(
        f"/api/v1/admin/reports/{row['id']}/review",
        json={
            "expected_version": row["row_version"],
            "decision": decision,
            "confirmed_edge_ids": [RAMP] if decision == "verify" else [],
            "reason": "Fictional concern examined by administrator",
            **changes,
        },
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )


def counts():
    with Session(engine()) as db:
        return {
            model.__tablename__: db.scalar(select(func.count()).select_from(model))
            for model in (
                ObstacleReport,
                EdgeRestriction,
                ReportStatusEvent,
                IdempotencyRecord,
                AdminAction,
                GraphEvent,
            )
        }


def graph_version():
    with Session(engine()) as db:
        return db.get(GraphState, demo_id("campus")).version


def test_creation_history_ownership_and_idempotent_replay(client, user):
    actor, headers = user
    body = payload()
    key = str(uuid.uuid4())
    response = client.post(
        "/api/v1/reports", json=body, headers={**headers, "Idempotency-Key": key}
    )
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["status"] == "pending_review" and row["row_version"] == 1
    assert row["reporter_id"] == actor["id"] and row["data_origin"] == "synthetic_demo"
    assert [event["to_status"] for event in row["history"]] == ["submitted", "pending_review"]
    assert row["suggested_edge_ids"] == [RAMP] and row["confirmed_edge_ids"] == []
    assert graph_version() == 1
    before = counts()
    assert (
        client.post(
            "/api/v1/reports", json=body, headers={**headers, "Idempotency-Key": key}
        ).json()
        == row
    )
    assert counts() == before
    conflict = client.post(
        "/api/v1/reports",
        json={**body, "description": "Different reported concern at the same point"},
        headers={**headers, "Idempotency-Key": key},
    )
    assert conflict.status_code == 409 and conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert client.get("/api/v1/reports").json()["items"] == [row]
    assert client.get(f"/api/v1/reports/{row['id']}").json() == row


@pytest.mark.parametrize(
    "change",
    [
        {"point": {"type": "Point", "coordinates": [5, 5]}},
        {"description": "short"},
        {"status": "verified"},
        {"reporter_id": str(uuid.uuid4())},
        {"suggested_edge_ids": [RAMP, RAMP]},
        {"suggested_edge_ids": [str(uuid.uuid4())]},
        {"category": "unsupported"},
    ],
)
def test_invalid_submission_has_no_partial_state(client, user, change):
    _, headers = user
    before = counts()
    response = client.post(
        "/api/v1/reports",
        json=payload(**change),
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 422, response.text
    assert counts() == before and graph_version() == 1


def test_report_admin_permissions_and_another_owner_are_enforced(client, user, admin):
    # Create under the normal account after the admin fixture changed this client's session.
    headers = login(client, "user@example.com")
    row = submit(client, headers)
    before = counts()
    assert review(client, headers, row).status_code == 403
    assert client.get(f"/api/v1/admin/reports?campus_id={CID}").status_code == 403
    assert client.get(f"/api/v1/admin/audit?campus_id={CID}").status_code == 403
    assert (
        client.get(
            f"/api/v1/admin/analytics?campus_id={CID}&from=2026-01-01T00:00:00Z&to=2026-12-01T00:00:00Z"
        ).status_code
        == 403
    )
    assert counts() == before and graph_version() == 1
    with Session(engine()) as db:
        from app.models.entities import User
        from app.services.auth import hasher

        with db.begin():
            db.add(
                User(
                    normalized_email="other@example.com",
                    display_name="Other",
                    password_hash=hasher.hash("another test-only password"),
                )
            )
    login(client, "other@example.com", "another test-only password")
    assert client.get(f"/api/v1/reports/{row['id']}").status_code == 404
    assert client.get("/api/v1/reports").json()["items"] == []


def test_verified_report_changes_real_routes_both_directions_and_replays_once(client, user, admin):
    headers = login(client, "user@example.com")
    row = submit(client, headers)
    before = client.post("/api/v1/routes/calculate", json=request_body(profile=STEP_FREE)).json()
    assert RAMP in {arc["edge_id"] for arc in before["primary"]["arcs"]}
    headers = login(client, "admin@example.com")
    key = str(uuid.uuid4())
    body = {
        "expected_version": 1,
        "decision": "verify",
        "confirmed_edge_ids": [RAMP],
        "reason": "Confirmed fictional ramp obstruction",
    }
    url = f"/api/v1/admin/reports/{row['id']}/review"
    response = client.post(url, json=body, headers={**headers, "Idempotency-Key": key})
    assert response.status_code == 200, response.text
    verified = response.json()
    assert (
        verified["status"] == "verified"
        and verified["row_version"] == 2
        and verified["confirmed_edge_ids"] == [RAMP]
    )
    assert graph_version() == 2
    saved = counts()
    assert (
        client.post(url, json=body, headers={**headers, "Idempotency-Key": key}).json() == verified
    )
    assert counts() == saved and graph_version() == 2
    for source, destination in [("s", "t"), ("t", "s")]:
        result = client.post(
            "/api/v1/routes/calculate",
            json=request_body(source=source, destination=destination, profile=STEP_FREE),
        ).json()
        assert result["status"] == "found" and result["graph_version"] == "2"
        assert all(
            RAMP not in {arc["edge_id"] for arc in path["arcs"]}
            for path in [result["primary"], *result["alternatives"]]
        )
    graph = client.get(f"/api/v1/campuses/{CID}/graph").json()
    edge = next(feature["properties"] for feature in graph["features"] if feature["id"] == RAMP)
    assert (
        edge["active_restriction_count"] == 1
        and edge["effective_availability"] == "temporarily_blocked"
    )
    assert "reporter_id" not in str(graph) and row["description"] not in str(graph)


def test_resolving_one_hazard_preserves_other_restrictions_and_baseline(client, user, admin):
    headers = login(client, "user@example.com")
    rows = [submit(client, headers) for _ in range(2)]
    headers = login(client, "admin@example.com")
    verified = []
    for row in rows:
        response = review(client, headers, row)
        assert response.status_code == 200, response.text
        verified.append(response.json())
    assert graph_version() == 3
    body = {"expected_version": 2, "reason": "First fictional obstruction removed"}
    url = f"/api/v1/admin/reports/{verified[0]['id']}/resolve"
    key = str(uuid.uuid4())
    resolved = client.post(url, json=body, headers={**headers, "Idempotency-Key": key})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved" and graph_version() == 4
    saved = counts()
    assert (
        client.post(url, json=body, headers={**headers, "Idempotency-Key": key}).json()
        == resolved.json()
    )
    assert counts() == saved and graph_version() == 4
    result = client.post("/api/v1/routes/calculate", json=request_body(profile=STEP_FREE)).json()
    assert RAMP not in {arc["edge_id"] for arc in result["primary"]["arcs"]}
    with Session(engine()) as db:
        remaining = list(
            db.scalars(select(EdgeRestriction).where(EdgeRestriction.released_at.is_(None)))
        )
        assert len(remaining) == 1 and str(remaining[0].report_id) == rows[1]["id"]
    # Administrative closure is independent and survives release of the final report.
    with Session(engine()) as db, db.begin():
        from app.models.entities import PathEdge, User
        from app.schemas.requests import EdgeEdit
        from app.services import graph as mutation

        actor = db.scalar(select(User).where(User.role == "admin"))
        edge = db.get(PathEdge, demo_id("edge:ramp-cross"))
        mutation.edit_resource(
            db,
            "path-edges",
            EdgeEdit(
                availability="closed",
                reason="Independent administrative baseline closure",
                expected_version=edge.row_version,
            ),
            actor,
            "test:baseline",
            edge.id,
        )
    last = client.post(
        f"/api/v1/admin/reports/{rows[1]['id']}/resolve",
        json={"expected_version": 2, "reason": "Second report-specific obstruction removed"},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert last.status_code == 200, last.text
    result = client.post("/api/v1/routes/calculate", json=request_body(profile=STEP_FREE)).json()
    assert RAMP not in {arc["edge_id"] for arc in result["primary"]["arcs"]}


def test_rejection_and_invalid_transitions_do_not_change_graph(client, user, admin):
    headers = login(client, "user@example.com")
    row = submit(client, headers, infrastructure_id=None, suggested_edge_ids=[])
    headers = login(client, "admin@example.com")
    empty = review(client, headers, row, confirmed_edge_ids=[])
    assert empty.status_code == 422 and empty.json()["code"] == "CONFIRMED_EDGES_REQUIRED"
    rejected = review(client, headers, row, "reject")
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected" and graph_version() == 1
    again = review(client, headers, rejected.json())
    assert again.status_code == 422 and graph_version() == 1
    assert counts()["edge_restrictions"] == 0


def test_infrastructure_mapping_can_confirm_real_physical_edges(client, user, admin):
    headers = login(client, "user@example.com")
    row = submit(client, headers, suggested_edge_ids=[])
    headers = login(client, "admin@example.com")
    response = review(client, headers, row, confirmed_edge_ids=[])
    assert response.status_code == 200, response.text
    assert RAMP in response.json()["confirmed_edge_ids"]


def test_failure_after_graph_mutation_rolls_back_every_table(client, user, admin, monkeypatch):
    headers = login(client, "user@example.com")
    row = submit(client, headers)
    headers = login(client, "admin@example.com")
    before = counts()

    def fail(*args, **kwargs):
        raise RuntimeError("Injected crash before transaction commit")

    monkeypatch.setattr(reporting, "complete", fail)
    with TestClient(app, raise_server_exceptions=False) as other:
        other.cookies.update(client.cookies)
        response = review(other, headers, row)
        assert response.status_code == 500
    assert counts() == before and graph_version() == 1
    with Session(engine()) as db:
        stored = db.get(ObstacleReport, uuid.UUID(row["id"]))
        assert stored.status == "pending_review" and stored.row_version == 1


@pytest.mark.parametrize("same_key", [False, True])
def test_concurrent_review_is_one_transition_or_identical_replay(
    client, user, admin, monkeypatch, same_key
):
    headers = login(client, "user@example.com")
    row = submit(client, headers)
    headers = login(client, "admin@example.com")
    barrier = Barrier(2)
    original = reporting.claim

    def synchronized(*args, **kwargs):
        barrier.wait(timeout=10)
        return original(*args, **kwargs)

    monkeypatch.setattr(reporting, "claim", synchronized)
    shared_key = str(uuid.uuid4())

    def call(decision):
        with TestClient(app) as other:
            other.cookies.update(client.cookies)
            body = {
                "expected_version": 1,
                "decision": "verify" if same_key else decision,
                "confirmed_edge_ids": [RAMP] if same_key or decision == "verify" else [],
                "reason": "Concurrent administrator decision",
            }
            return other.post(
                f"/api/v1/admin/reports/{row['id']}/review",
                json=body,
                headers={
                    **headers,
                    "Idempotency-Key": shared_key if same_key else str(uuid.uuid4()),
                },
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(call, ["verify", "reject"]))
    assert sorted(response.status_code for response in responses) == (
        [200, 200] if same_key else [200, 409]
    ), [response.text for response in responses]
    if same_key:
        assert responses[0].json() == responses[1].json()
    with Session(engine()) as db:
        status = db.get(ObstacleReport, uuid.UUID(row["id"])).status
        assert (
            db.scalar(
                select(func.count())
                .select_from(AdminAction)
                .where(AdminAction.resource_id == uuid.UUID(row["id"]))
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(ReportStatusEvent)
                .where(ReportStatusEvent.report_id == uuid.UUID(row["id"]))
            )
            == 3
        )
    assert graph_version() == (2 if status == "verified" else 1)


def test_database_prevents_verified_report_without_restrictions(client, user):
    from sqlalchemy.exc import IntegrityError

    _, headers = user
    row = submit(client, headers)
    with pytest.raises(IntegrityError), Session(engine()) as db, db.begin():
        db.execute(
            text(
                "UPDATE obstacle_reports SET status='verified', reviewer_id=reporter_id, reviewed_at=clock_timestamp() WHERE id=:id"
            ),
            {"id": row["id"]},
        )
    assert graph_version() == 1


@pytest.mark.parametrize(
    "availability,active,expected",
    [
        ("closed", True, "closed"),
        ("temporarily_blocked", True, "temporarily_blocked"),
        ("open", False, "closed"),
    ],
)
def test_public_effective_availability_includes_mapped_infrastructure(
    client, admin, availability, active, expected
):
    from app.models.entities import Infrastructure, User
    from app.schemas.requests import InfrastructureEdit
    from app.services import graph as mutation

    with Session(engine()) as db, db.begin():
        actor = db.scalar(select(User).where(User.role == "admin"))
        row = db.get(Infrastructure, demo_id("infrastructure:ramp"))
        mutation.edit_resource(
            db,
            "infrastructure",
            InfrastructureEdit(
                availability=availability,
                active=active,
                expected_version=row.row_version,
                reason="Check public effective pathway availability",
            ),
            actor,
            "test:effective-availability",
            row.id,
        )
    output = client.get(f"/api/v1/campuses/{CID}/graph")
    assert output.status_code == 200, output.text
    edge = next(item["properties"] for item in output.json()["features"] if item["id"] == RAMP)
    assert edge["availability"] == "open"
    assert edge["effective_availability"] == expected
    assert edge["active_restriction_count"] == 0


def test_role_revocation_after_initial_auth_cannot_authorize_a_review(
    client, user, admin, monkeypatch
):
    from app.models.entities import User

    h = login(client, "user@example.com")
    row = submit(client, h)
    h = login(client, "admin@example.com")
    before = counts()
    original = reporting.decide_report

    def revoked(db, key, payload, actor, *args, **kwargs):
        with Session(engine()) as independent, independent.begin():
            current = independent.get(User, actor.id)
            current.role = "user"
        return original(db, key, payload, actor, *args, **kwargs)

    monkeypatch.setattr(reporting, "decide_report", revoked)
    response = review(client, h, row)
    assert response.status_code == 403 and response.json()["code"] == "ADMIN_REQUIRED"
    assert counts() == before and graph_version() == 1
