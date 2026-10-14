"""Committed replay, stream admission and source-grain analytics with real PostGIS."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Problem
from app.db.session import engine
from app.models.entities import Campus, GraphEvent, GraphState, PathEdge
from app.models.reporting import SSELease
from app.services import events
from app.services.seed import demo_id
from app.tests.conftest import login
from app.tests.integration.test_reporting import CID, RAMP, review, submit


def test_initial_replay_after_committed_review_and_resolution_has_only_curated_data(
    client, user, admin
):
    initial = events.event_batch(demo_id("campus"), None)
    assert initial[0]["event"] == "graph.reset" and initial[0]["id"] == "1"
    headers = login(client, "user@example.com")
    row = submit(client, headers)
    assert events.event_batch(demo_id("campus"), "1") == []
    headers = login(client, "admin@example.com")
    verified = review(client, headers, row)
    assert verified.status_code == 200, verified.text
    resolved = client.post(
        f"/api/v1/admin/reports/{row['id']}/resolve",
        json={"expected_version": 2, "reason": "Fictional hazard cleared"},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert resolved.status_code == 200, resolved.text
    # There is no notification dependency; an independent reader replays committed DB rows.
    batch = events.event_batch(demo_id("campus"), "1")
    assert [item["id"] for item in batch] == ["2", "3"]
    assert [item["data"]["reason"] for item in batch] == ["report_verified", "report_resolved"]
    assert all(item["data"]["changed_edge_ids"] == [RAMP] for item in batch)
    assert (
        row["description"] not in str(batch)
        and "reporter" not in str(batch)
        and row["id"] not in str(batch)
    )
    assert "id: 2\nevent: graph.updated\n" in events.encode_event(batch[0])
    assert events.event_batch(demo_id("campus"), "3") == []


@pytest.mark.parametrize("cursor", ["bad", "-1", "0", "2", "999999999999999999999", "１２"])
def test_invalid_missing_future_cursor_resets(cursor):
    batch = events.event_batch(demo_id("campus"), cursor)
    assert len(batch) == 1 and batch[0]["event"] == "graph.reset" and batch[0]["id"] == "1"


def test_expired_cursor_and_internal_gap_reset_and_live_reset_does_not_loop():
    owner = create_engine(get_settings().database_url(owner=True), hide_parameters=True)
    with owner.begin() as db:
        db.execute(text("TRUNCATE graph_events"))
        db.execute(
            text(
                "INSERT INTO graph_events(campus_id,graph_version,event_type,changed_edge_ids,reason,occurred_at) VALUES (:campus,1,'graph.reset','{}'::uuid[],'test_expired',clock_timestamp()-interval '8 days')"
            ),
            {"campus": CID},
        )
    owner.dispose()
    assert events.event_batch(demo_id("campus"), "1")[0]["event"] == "graph.reset"
    assert events.event_batch(demo_id("campus"), "1", trusted=True) == []
    with Session(engine()) as db, db.begin():
        state = db.get(GraphState, demo_id("campus"))
        state.version = 3
        db.add(
            GraphEvent(
                campus_id=state.campus_id,
                graph_version=3,
                event_type="graph.updated",
                changed_edge_ids=[],
                reason="test_gap",
            )
        )
    batch = events.event_batch(demo_id("campus"), "1", trusted=True)
    assert batch[0]["event"] == "graph.reset" and batch[0]["data"]["reason"] == "replay_gap"


def test_stream_leases_are_capped_released_expired_and_refreshed():
    leases = [events.claim_stream("test-identity") for _ in range(3)]
    with pytest.raises(Problem) as blocked:
        events.claim_stream("test-identity")
    assert blocked.value.status == 429
    events.release_stream(leases[0])
    replacement = events.claim_stream("test-identity")
    assert replacement not in leases
    with Session(engine()) as db, db.begin():
        row = db.get(SSELease, replacement)
        row.expires_at = db.scalar(select(func.clock_timestamp())) - timedelta(seconds=1)
    with pytest.raises(Problem) as expired:
        events.event_batch(demo_id("campus"), "1", replacement)
    assert expired.value.code == "STREAM_EXPIRED"
    fresh = events.claim_stream("test-identity")
    events.event_batch(demo_id("campus"), "1", fresh)
    with Session(engine()) as db:
        assert db.get(SSELease, replacement) is None
        assert db.get(SSELease, fresh).expires_at > db.scalar(
            select(func.clock_timestamp())
        ) + timedelta(seconds=40)
    for lease in [*leases, fresh]:
        events.release_stream(lease)


def window(client, headers, from_time=None, to_time=None, campus_id=CID):
    now = datetime.now(UTC)
    response = client.get(
        "/api/v1/admin/analytics",
        params={
            "campus_id": campus_id,
            "from": (from_time or now - timedelta(days=1)).isoformat(),
            "to": (to_time or now + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_analytics_counts_reports_and_physical_edges_without_restriction_or_evidence_duplication(
    client, user, admin
):
    headers = login(client, "user@example.com")
    rows = [submit(client, headers), submit(client, headers, category="temporary_obstacle")]
    headers = login(client, "admin@example.com")
    with Session(engine()) as db:
        extra = str(
            db.scalar(
                select(PathEdge.id).where(
                    PathEdge.active, PathEdge.id != demo_id("edge:ramp-cross")
                )
            )
        )
        total = db.scalar(select(func.sum(PathEdge.distance_m)).where(PathEdge.active))
    for row in rows:
        response = review(client, headers, row, confirmed_edge_ids=[RAMP, extra])
        assert response.status_code == 200, response.text
    data = window(client, headers)
    assert data["active_verified_obstacles"] == 2 and data["pending_reports"] == 0
    assert data["submitted_report_count"] == 2
    assert {entry["category"]: entry["count"] for entry in data["category_distribution"]} == {
        "blocked_ramp": 1,
        "temporary_obstacle": 1,
    }
    assert data["active_physical_pathways"] == 13
    assert data["mapping_total_length_m"] == pytest.approx(total)
    assert data["accessibility_mapping_coverage"] == pytest.approx(
        data["mapping_known_current_length_m"] / total
    )
    assert data["average_resolution_seconds"] is None and data["resolved_report_count"] == 0
    assert data["data_origin"] == "synthetic_demo"
    response = client.post(
        f"/api/v1/admin/reports/{rows[0]['id']}/resolve",
        json={"expected_version": 2, "reason": "Fictional first concern cleared"},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 200, response.text
    resolved = response.json()
    data = window(client, headers)
    assert data["active_verified_obstacles"] == 1 and data["resolved_report_count"] == 1
    assert sum(item["count"] for item in data["resolution_trend"]) == 1
    expected = (
        datetime.fromisoformat(resolved["resolved_at"])
        - datetime.fromisoformat(resolved["created_at"])
    ).total_seconds()
    assert data["average_resolution_seconds"] == pytest.approx(expected)
    assert (
        data["resolution_trend"][0]["day"]
        == datetime.fromisoformat(resolved["resolved_at"]).astimezone(UTC).date().isoformat()
    )
    audit = client.get(f"/api/v1/admin/audit?campus_id={CID}&limit=1").json()
    assert len(audit["items"]) == 1 and audit["next_cursor"]
    assert audit["items"][0]["graph_version"] == "2"


def test_flow_window_is_from_inclusive_to_exclusive(client, user, admin):
    headers = login(client, "user@example.com")
    row = submit(client, headers)
    created = datetime.fromisoformat(row["created_at"])
    headers = login(client, "admin@example.com")
    assert (
        window(client, headers, created, created + timedelta(seconds=1))["submitted_report_count"]
        == 1
    )
    assert (
        window(client, headers, created - timedelta(seconds=1), created)["submitted_report_count"]
        == 0
    )
    assert (
        window(
            client, headers, created + timedelta(microseconds=1), created + timedelta(seconds=1)
        )["submitted_report_count"]
        == 0
    )


def test_empty_campus_has_null_denominators_and_zero_counts(client, admin):
    identity = uuid.uuid4()
    with Session(engine()) as db, db.begin():
        db.add(
            Campus(
                id=identity,
                name="Empty synthetic campus",
                data_origin="synthetic_demo",
                attribution="Test only",
            )
        )
        db.flush()
        db.add(GraphState(campus_id=identity))
    data = window(client, admin, campus_id=str(identity))
    assert data["active_physical_pathways"] == 0 and data["mapping_total_length_m"] == 0
    assert (
        data["accessibility_mapping_coverage"] is None
        and data["average_resolution_seconds"] is None
    )
    assert data["category_distribution"] == [] and data["resolution_trend"] == []


@pytest.mark.parametrize(
    "from_time,to_time",
    [
        ("2026-01-01T00:00:00", "2026-02-01T00:00:00Z"),
        ("2026-02-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        ("2024-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
    ],
)
def test_invalid_analytics_window_is_rejected(client, admin, from_time, to_time):
    response = client.get(
        "/api/v1/admin/analytics", params={"campus_id": CID, "from": from_time, "to": to_time}
    )
    assert response.status_code == 422
