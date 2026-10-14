import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.entities import AdminAction, Campus, GraphEvent, GraphState, PathEdge
from app.services.seed import demo_id, seed_demo
from app.tests.conftest import PASSWORD, headers, login

CID = str(demo_id("campus"))
RAMP = str(demo_id("edge:ramp-cross"))


def version(client):
    result = client.get(f"/api/v1/campuses/{CID}/graph-version")
    assert result.status_code == 200, result.text
    return int(result.json()["graph_version"])


def test_geojson_and_measured_distances(client):
    r = client.get(f"/api/v1/campuses/{CID}/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data_origin"] == "synthetic_demo" and body["graph_version"] == "1"
    assert len(body["features"]) == 22
    edges = [f for f in body["features"] if f["geometry"]["type"] == "LineString"]
    assert len(edges) == 13
    assert all(f["properties"]["distance_m"] > 0 for f in edges)
    unknown = next(f for f in edges if f["id"] == str(demo_id("edge:unknown-direct")))
    assert unknown["properties"]["width_m"] is None
    assert unknown["properties"]["accessibility"] == "unknown"
    with Session(engine()) as db:
        mismatches = db.scalar(
            text(
                "SELECT count(*) FROM path_edges WHERE abs(distance_m-ST_Length(geometry::geography)) > 1e-8"
            )
        )
        assert mismatches == 0


def test_location_search_pagination_and_access_points(client):
    r = client.get("/api/v1/locations", params={"campus_id": CID, "limit": 1})
    assert r.status_code == 200 and r.json()["next_cursor"]
    first = r.json()["items"][0]
    assert first["access_points"][0]["node_id"]
    second = client.get(
        "/api/v1/locations",
        params={"campus_id": CID, "limit": 1, "cursor": r.json()["next_cursor"]},
    )
    assert second.json()["items"][0]["id"] != first["id"]
    assert (
        client.get("/api/v1/locations", params={"campus_id": CID, "cursor": "bad"}).status_code
        == 400
    )
    assert (
        client.get(
            "/api/v1/locations",
            params={"campus_id": CID, "cursor": r.json()["next_cursor"], "q": "Library"},
        ).status_code
        == 400
    )
    result = client.get("/api/v1/locations", params={"campus_id": CID, "q": "Library"}).json()
    assert len(result["items"]) == 1
    assert (
        client.get("/api/v1/locations/" + result["items"][0]["id"]).json()["name"] == "Demo Library"
    )


def test_infrastructure_bounds_and_mappings(client):
    r = client.get(
        "/api/v1/infrastructure", params={"campus_id": CID, "bbox": "-0.001,-0.001,0.001,0.001"}
    )
    assert r.status_code == 200 and len(r.json()["items"]) == 2
    assert all(item["edge_ids"] for item in r.json()["items"])
    assert (
        client.get(
            "/api/v1/infrastructure", params={"campus_id": CID, "bbox": "0,0,nan,1"}
        ).status_code
        == 422
    )
    key = r.json()["items"][0]["id"]
    assert client.get("/api/v1/infrastructure/" + key).status_code == 200


def test_normal_user_cannot_change_graph(client, user):
    _, h = user
    before = version(client)
    result = client.patch(
        f"/api/v1/admin/path-edges/{RAMP}",
        headers=h,
        json={"availability": "closed", "expected_version": 1, "reason": "Unauthorized attempt"},
    )
    assert result.status_code == 403 and version(client) == before
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 0


def test_edge_update_cas_event_and_audit_are_atomic(client, admin):
    body = {
        "availability": "closed",
        "expected_version": 1,
        "reason": "Verified demonstration closure",
    }
    before = version(client)
    result = client.patch(f"/api/v1/admin/path-edges/{RAMP}", json=body, headers=admin)
    assert result.status_code == 200, result.text
    assert result.json()["row_version"] == 2 and result.json()["availability"] == "closed"
    assert version(client) == before + 1
    stale = client.patch(f"/api/v1/admin/path-edges/{RAMP}", json=body, headers=admin)
    assert stale.status_code == 409 and stale.json()["current_version"] == 2
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 1
        event = db.get(GraphEvent, (demo_id("campus"), before + 1))
        assert demo_id("edge:ramp-cross") in event.changed_edge_ids


def test_invalid_geometry_rolls_back_entire_mutation(client, admin):
    bad = {
        "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
        "availability": "closed",
        "expected_version": 1,
        "reason": "Bad geometry",
    }
    assert (
        client.patch(f"/api/v1/admin/path-edges/{RAMP}", headers=admin, json=bad).status_code == 422
    )
    assert version(client) == 1
    with Session(engine()) as db:
        row = db.get(PathEdge, demo_id("edge:ramp-cross"))
        assert row.row_version == 1 and row.availability == "open"
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 0


def test_remeasurement_invalidates_old_verification(client, admin):
    result = client.patch(
        f"/api/v1/admin/path-edges/{RAMP}",
        headers=admin,
        json={"width_m": None, "expected_version": 1, "reason": "Measurement unknown"},
    )
    assert result.status_code == 200, result.text
    assert result.json()["width_m"] is None and result.json()["verification"] == "needs_review"
    result = client.patch(
        f"/api/v1/admin/path-edges/{RAMP}",
        headers=admin,
        json={
            "width_m": 1.2,
            "verification": "verified",
            "provenance": "Synthetic re-observation",
            "expected_version": 2,
            "reason": "Reverify observation",
        },
    )
    assert result.status_code == 200 and result.json()["verification"] == "verified"


def test_expiry_increments_version_once_and_changes_status(client):
    with Session(engine()) as db, db.begin():
        row = db.get(PathEdge, demo_id("edge:ramp-cross"))
        now = db.scalar(select(func.clock_timestamp()))
        row.verified_at = now - timedelta(days=31)
        row.verified_until = now - timedelta(seconds=1)
        db.get(GraphState, demo_id("campus")).next_expiry_at = row.verified_until
    assert version(client) == 2 and version(client) == 2
    with Session(engine()) as db:
        assert db.get(PathEdge, demo_id("edge:ramp-cross")).verification == "needs_review"
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 1


def test_infrastructure_closure_records_dependent_edges(client, admin):
    key = str(demo_id("infrastructure:ramp"))
    result = client.patch(
        f"/api/v1/admin/infrastructure/{key}",
        headers=admin,
        json={
            "availability": "temporarily_blocked",
            "expected_version": 1,
            "reason": "Demo ramp closed",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["edge_ids"] == [RAMP]
    with Session(engine()) as db:
        assert (
            demo_id("edge:ramp-cross")
            in db.get(GraphEvent, (demo_id("campus"), 2)).changed_edge_ids
        )


def test_concurrent_updates_one_success_one_conflict(client, admin):
    cookies = dict(client.cookies)
    barrier = Barrier(2)

    def change(value):
        with TestClient(app) as other:
            other.cookies.update(cookies)
            barrier.wait(timeout=10)
            return other.patch(
                f"/api/v1/admin/path-edges/{RAMP}",
                headers=admin,
                json={"availability": value, "expected_version": 1, "reason": "Concurrent update"},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(change, ("closed", "temporarily_blocked")))
    assert sorted(results) == [200, 409]
    assert version(client) == 2
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 1


def test_seed_repeatability_and_no_overwrite(client, admin):
    with Session(engine()) as db, db.begin():
        assert "already present" in seed_demo(db)
    assert (
        client.patch(
            f"/api/v1/admin/path-edges/{RAMP}",
            headers=admin,
            json={"availability": "closed", "expected_version": 1, "reason": "Changed seed row"},
        ).status_code
        == 200
    )
    with Session(engine()) as db:
        with pytest.raises(RuntimeError, match="refusing to overwrite"):
            seed_demo(db)


def test_database_rejects_cross_campus_and_nonfinite_measurements():
    with Session(engine()) as db:
        row = db.get(PathEdge, demo_id("edge:ramp-cross"))
        row.width_m = float("nan")
        with pytest.raises(IntegrityError):
            db.commit()
    other = uuid.uuid4()
    with Session(engine()) as db, db.begin():
        db.add(
            Campus(
                id=other,
                name="Another synthetic campus",
                data_origin="synthetic_demo",
                attribution="Test only",
            )
        )
    with Session(engine()) as db:
        row = db.get(PathEdge, demo_id("edge:ramp-cross"))
        row.campus_id = other
        with pytest.raises(IntegrityError):
            db.commit()


def test_application_role_cannot_change_audit_or_schema():
    with Session(engine()) as db:
        with pytest.raises(DBAPIError):
            db.execute(text("CREATE TABLE unauthorized (id int)"))
    with Session(engine()) as db:
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM graph_events"))


def test_saved_destination_ownership(client, user):
    _, h = user
    loc = str(demo_id("location:t"))
    result = client.post("/api/v1/me/saved-destinations", headers=h, json={"location_id": loc})
    assert result.status_code == 201, result.text
    key = result.json()["id"]
    assert (
        client.post(
            "/api/v1/me/saved-destinations", headers=h, json={"location_id": loc}
        ).status_code
        == 409
    )
    assert client.get("/api/v1/me/saved-destinations").json()["items"][0]["id"] == key
    with TestClient(app) as other:
        other.post(
            "/api/v1/auth/register",
            headers=headers(other),
            json={"email": "other@example.com", "password": PASSWORD, "display_name": "Other"},
        )
        h2 = login(other, "other@example.com")
        assert other.delete("/api/v1/me/saved-destinations/" + key, headers=h2).status_code == 404
    assert client.delete("/api/v1/me/saved-destinations/" + key, headers=h).status_code == 204


def test_create_edit_retire_resources(client, admin):
    node = client.post(
        "/api/v1/admin/path-nodes",
        headers=admin,
        json={
            "campus_id": CID,
            "name": "New junction",
            "point": {"type": "Point", "coordinates": [0.0004, 0]},
            "reason": "Add demonstration node",
        },
    )
    assert node.status_code == 201, node.text
    node_id = node.json()["id"]
    location = client.post(
        "/api/v1/admin/locations",
        headers=admin,
        json={
            "campus_id": CID,
            "name": "New location",
            "kind": "building",
            "point": {"type": "Point", "coordinates": [0.0004, 0]},
            "reason": "Add demonstration location",
        },
    )
    assert location.status_code == 201, location.text
    loc = client.patch(
        "/api/v1/admin/locations/" + location.json()["id"],
        headers=admin,
        json={
            "expected_version": 1,
            "reason": "Link access point",
            "access_points": [{"node_id": node_id, "label": "New entrance", "is_primary": True}],
        },
    )
    assert loc.status_code == 200 and loc.json()["access_points"][0]["node_id"] == node_id
    edge = client.post(
        "/api/v1/admin/path-edges",
        headers=admin,
        json={
            "campus_id": CID,
            "source_node_id": str(demo_id("node:u")),
            "target_node_id": node_id,
            "geometry": {"type": "LineString", "coordinates": [[0.0003, 0], [0.0004, 0]]},
            "reason": "Add demonstration path",
        },
    )
    assert edge.status_code == 201 and edge.json()["distance_m"] > 10, edge.text
    infrastructure = client.post(
        "/api/v1/admin/infrastructure",
        headers=admin,
        json={
            "campus_id": CID,
            "location_id": location.json()["id"],
            "name": "New entrance",
            "kind": "entrance",
            "point": {"type": "Point", "coordinates": [0.0004, 0]},
            "edge_ids": [edge.json()["id"]],
            "reason": "Link new entrance",
        },
    )
    assert infrastructure.status_code == 201, infrastructure.text
    retired = client.post(
        "/api/v1/admin/path-edges/" + edge.json()["id"] + "/retire",
        headers=admin,
        json={"expected_version": 1, "reason": "Retire demonstration path"},
    )
    assert retired.status_code == 200 and retired.json()["active"] is False


def test_node_move_requires_atomic_incident_geometry_updates(client, admin):
    node_id = str(demo_id("node:u"))
    body = {
        "point": {"type": "Point", "coordinates": [0.0004, 0]},
        "expected_version": 1,
        "reason": "Move node atomically",
    }
    assert (
        client.patch(f"/api/v1/admin/path-nodes/{node_id}", headers=admin, json=body).status_code
        == 422
    )
    body["incident_geometries"] = [
        {
            "edge_id": str(demo_id("edge:gravel-west")),
            "expected_version": 1,
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [0.0004, 0]]},
        },
        {
            "edge_id": str(demo_id("edge:gravel-east")),
            "expected_version": 1,
            "geometry": {"type": "LineString", "coordinates": [[0.0004, 0], [0.0002, 0]]},
        },
    ]
    result = client.patch(f"/api/v1/admin/path-nodes/{node_id}", headers=admin, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["point"]["coordinates"] == [0.0004, 0]
