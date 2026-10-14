"""Route HTTP contracts exercised against the migrated, isolated PostGIS database."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine
from app.main import app
from app.models.entities import (
    AdminAction,
    AuthSession,
    Campus,
    GraphEvent,
    GraphState,
    Infrastructure,
    PathEdge,
    PathNode,
    Profile,
    User,
)
from app.routing import SearchLimits
from app.schemas.requests import InfrastructureEdit
from app.schemas.routing import RouteRequest
from app.services import auth, graph, routing
from app.services.seed import POSITIONS, demo_id

URL = "/api/v1/routes/calculate"
CID = str(demo_id("campus"))
RAMP = str(demo_id("edge:ramp-cross"))
UNKNOWN = str(demo_id("edge:unknown-direct"))
STEP_FREE = {
    "avoid_stairs": True,
    "max_slope_pct": 8,
    "min_width_m": 0.9,
    "excluded_surfaces": ["uneven", "gravel"],
    "unknown_policy": "exclude",
    "travel_speed_mps": 1,
}


def request_body(*, source="s", destination="t", profile=None, **options):
    return {
        "campus_id": CID,
        "source_id": str(demo_id("node:" + source)),
        "destination_id": str(demo_id("node:" + destination)),
        "accessibility_profile": {
            "avoid_stairs": False,
            "max_slope_pct": None,
            "min_width_m": None,
            "excluded_surfaces": [],
            "unknown_policy": "exclude",
            "travel_speed_mps": 1,
            **(profile or {}),
        },
        **options,
    }


def route(client, **options):
    response = client.post(URL, json=request_body(**options))
    assert response.status_code == 200, response.text
    return response.json()


def edge_ids(result):
    return {arc["edge_id"] for arc in result["arcs"]}


def all_routes(result):
    return [result["primary"], *result["alternatives"]]


def commit_ramp_change(availability):
    """Real atomic graph mutation in a transaction independent of the route request."""
    with Session(engine()) as db, db.begin():
        actor = db.scalar(select(User).where(User.normalized_email == "admin@example.com"))
        row = db.get(Infrastructure, demo_id("infrastructure:ramp"))
        graph.edit_resource(
            db,
            "infrastructure",
            InfrastructureEdit(
                availability=availability,
                expected_version=row.row_version,
                reason="Committed concurrent routing test observation",
            ),
            actor,
            "test:routing-concurrency",
            key=row.id,
        )


def test_public_calculation_has_no_cookie_csrf_or_persisted_profile_side_effect(client):
    with Session(engine()) as db:
        before = {
            model: db.scalar(select(func.count()).select_from(model))
            for model in (AuthSession, Profile, User, AdminAction, GraphEvent)
        }
    response = client.post(URL, json=request_body())
    assert response.status_code == 200, response.text
    assert "set-cookie" not in response.headers
    assert not client.cookies
    assert response.json()["graph_version"] == "1"
    with Session(engine()) as db:
        assert before == {
            model: db.scalar(select(func.count()).select_from(model)) for model in before
        }


def test_concurrent_requests_release_auth_connections_before_independent_routing(monkeypatch):
    original = auth.current_session
    connections_at_barrier = []
    barrier = Barrier(
        10, action=lambda: connections_at_barrier.append(engine().pool.checkedout()), timeout=10
    )

    def synchronized_session(*args, **kwargs):
        result = original(*args, **kwargs)
        barrier.wait()
        return result

    monkeypatch.setattr(auth, "current_session", synchronized_session)

    def calculate(_index):
        with TestClient(app, raise_server_exceptions=False) as concurrent_client:
            response = concurrent_client.post(
                URL, json=request_body(profile=STEP_FREE, alternatives_limit=0)
            )
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(calculate, range(10), timeout=20))
    assert connections_at_barrier == [10]
    assert all(status == 200 for status, _ in results), results
    assert all(body["status"] == "found" for _, body in results)
    assert all(body["graph_version"] == "1" for _, body in results)


def test_algorithms_choose_stairs_or_step_free_and_preserve_geojson_totals(client):
    stairs = route(client)
    assert edge_ids(stairs["primary"]) == {
        str(demo_id("edge:stairs-west")),
        str(demo_id("edge:stairs-east")),
    }
    results = [
        route(client, profile={**STEP_FREE, "travel_speed_mps": 0.75}, selected_algorithm=name)
        for name in ("dijkstra", "astar")
    ]
    assert results[0]["primary"]["cost_m_equivalent"] == pytest.approx(
        results[1]["primary"]["cost_m_equivalent"], abs=1e-6, rel=1e-9
    )
    features = client.get(f"/api/v1/campuses/{CID}/graph").json()["features"]
    edges = {item["id"]: item for item in features if item["geometry"]["type"] == "LineString"}
    for result in results:
        assert result["status"] == "found" and result["reason"] is None
        assert result["data_origin"] == "synthetic_demo"
        assert result["policy_version"] == "accessibility-v1"
        assert result["cost_model_version"] == "walking-effort-v1"
        assert datetime.fromisoformat(result["validated_at"]) < datetime.fromisoformat(
            result["valid_until"]
        )
        assert result["stats"]["expansions"] > 0
        assert result["stats"]["searches"] > 0
        assert result["stats"]["elapsed_ms"] >= 0
        assert RAMP in edge_ids(result["primary"])
        assert len(result["alternatives"]) >= 1
        for candidate in all_routes(result):
            shapes = []
            total = 0
            cost = 0
            assert len(candidate["node_ids"]) == len(candidate["arcs"]) + 1
            assert len(set(candidate["node_ids"])) == len(candidate["node_ids"])
            assert len(candidate["instructions"]) == len(candidate["arcs"])
            for arc, instruction in zip(candidate["arcs"], candidate["instructions"], strict=True):
                edge = edges[arc["edge_id"]]
                values = edge["properties"]
                assert values["has_stairs"] is False
                assert values["width_m"] >= 0.9
                assert abs(values["slope_pct"]) <= 8
                assert values["surface"] == "smooth"
                assert values["verification"] == "verified"
                total += values["distance_m"]
                cost += values["distance_m"] * (1 + 2 * abs(values["slope_pct"]) / 100)
                shape = edge["geometry"]["coordinates"]
                if arc["direction"] == "reverse":
                    shape = list(reversed(shape))
                shapes.extend(shape if not shapes else shape[1:])
                assert instruction["edge_id"] == arc["edge_id"]
                assert instruction["distance_m"] == values["distance_m"]
                assert instruction["text"]
            assert candidate["geometry"] == {"type": "LineString", "coordinates": shapes}
            assert shapes[0] == POSITIONS["s"] and shapes[-1] == POSITIONS["t"]
            assert candidate["total_distance_m"] == pytest.approx(total)
            assert candidate["estimated_duration_s"] == pytest.approx(total / 0.75)
            assert candidate["cost_m_equivalent"] == pytest.approx(cost)
            assert candidate["verification"]["summary"] == "observations_current"
            assert candidate["verification"]["verified_distance_m"] == pytest.approx(total)
            assert candidate["verification"]["uncertain_distance_m"] == 0
            assert candidate["instructions"][0]["maneuver"] == "depart"
            assert {warning["code"] for warning in candidate["warnings"]} == {
                "SYNTHETIC_DATA",
                "DURATION_ESTIMATE",
            }


def test_reverse_route_reverses_geometry_instructions_and_signed_grade(client):
    result = route(client, source="c", destination="b", profile=STEP_FREE)
    primary = result["primary"]
    assert primary["arcs"] == [{"edge_id": RAMP, "direction": "reverse"}]
    assert primary["geometry"]["coordinates"] == [POSITIONS["c"], POSITIONS["b"]]
    assert primary["instructions"][0]["slope_pct"] == -4
    assert primary["instructions"][0]["node_id"] == str(demo_id("node:b"))
    assert "Demo Learning Hall" in primary["instructions"][0]["text"]


def test_same_node_is_zero_point_and_constraints_no_route_has_no_fabricated_route(client):
    same = route(client, destination="s", profile=STEP_FREE)
    primary = same["primary"]
    assert same["status"] == "found" and same["alternatives"] == []
    assert primary["node_ids"] == [str(demo_id("node:s"))]
    assert primary["arcs"] == primary["instructions"] == []
    assert primary["geometry"] == {"type": "Point", "coordinates": POSITIONS["s"]}
    assert primary["total_distance_m"] == primary["estimated_duration_s"] == 0
    assert primary["cost_m_equivalent"] == 0
    impossible = route(client, profile={**STEP_FREE, "min_width_m": 10})
    assert impossible["status"] == "no_route"
    assert impossible["reason"] == "constraints_exclude_all_paths"
    assert impossible["primary"] is None and impossible["alternatives"] == []
    assert impossible["excluded_edge_counts"]["width_limit"] > 0
    assert impossible["accessibility_profile"]["min_width_m"] == 10


def test_disconnected_real_node_is_distinguished_from_filtered_route(client):
    key = uuid.uuid4()
    with Session(engine()) as db, db.begin():
        db.add(
            PathNode(
                id=key,
                campus_id=demo_id("campus"),
                name="Isolated synthetic node",
                point=graph.geometry({"type": "Point", "coordinates": [0.0008, 0.0008]}),
            )
        )
    result = route(client, destination_id=str(key))
    assert result["status"] == "no_route" and result["reason"] == "disconnected"
    assert result["primary"] is None and result["alternatives"] == []


@pytest.mark.parametrize("field", ["source_id", "destination_id", "campus_id"])
def test_unknown_endpoint_or_campus_is_404(client, field):
    response = client.post(URL, json=request_body(**{field: str(uuid.uuid4())}))
    assert response.status_code == 404 and response.json()["code"] == "NOT_FOUND"


def test_location_ids_are_not_path_nodes_and_cross_campus_is_rejected(client):
    wrong_kind = client.post(URL, json=request_body(source_id=str(demo_id("location:s"))))
    assert wrong_kind.status_code == 404
    campus_id, node_id = uuid.uuid4(), uuid.uuid4()
    with Session(engine()) as db, db.begin():
        db.add(
            Campus(
                id=campus_id,
                name="Other synthetic campus",
                data_origin="synthetic_demo",
                attribution="Integration test only",
            )
        )
        db.flush()
        db.add(
            PathNode(
                id=node_id,
                campus_id=campus_id,
                point=graph.geometry({"type": "Point", "coordinates": [1, 1]}),
            )
        )
    response = client.post(URL, json=request_body(destination_id=str(node_id)))
    assert response.status_code == 422
    assert response.json()["code"] == "CROSS_CAMPUS_ENDPOINT"


@pytest.mark.parametrize(
    "changes",
    [
        {"avoid_stairs": "false"},
        {"max_slope_pct": "8"},
        {"max_slope_pct": True},
        {"max_slope_pct": -0.00001},
        {"max_slope_pct": float("inf")},
        {"min_width_m": 0},
        {"min_width_m": float("nan")},
        {"travel_speed_mps": 0},
        {"travel_speed_mps": "1"},
        {"unknown_policy": "pretend_accessible"},
        {"excluded_surfaces": ["unknown"]},
        {"expected_version": 1},
    ],
)
def test_computational_profile_requires_strict_finite_bounded_values(client, changes):
    payload = request_body(profile=changes)
    # Raw JSON permits explicit nonfinite fault injection; the server must reject it.
    response = client.post(
        URL, content=json.dumps(payload), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "INVALID_INPUT"
    assert response.json()["field_errors"]
    assert all("input" not in error for error in response.json()["field_errors"])


@pytest.mark.parametrize(
    "changes",
    [
        {"selected_algorithm": "breadth_first"},
        {"alternatives_limit": 3},
        {"alternatives_limit": True},
        {"alternatives_limit": "1"},
        {"accessibility_profile": None},
        {"accessibility_profile": {"avoid_stairs": True}},
        {"negative_weights": True},
    ],
)
def test_complete_profile_algorithm_and_options_are_validated(client, changes):
    response = client.post(URL, json={**request_body(), **changes})
    assert response.status_code == 422 and response.json()["code"] == "INVALID_INPUT"


def test_canonical_fingerprint_equates_numbers_negative_zero_and_surface_sets(client):
    first = route(
        client,
        profile={
            "max_slope_pct": 0,
            "min_width_m": 1,
            "travel_speed_mps": 1,
            "excluded_surfaces": ["uneven", "gravel", "uneven"],
        },
    )
    equivalent = route(
        client,
        profile={
            "max_slope_pct": -0.0,
            "min_width_m": 1.0,
            "travel_speed_mps": 1.0,
            "excluded_surfaces": ["gravel", "uneven"],
        },
    )
    assert first["profile_fingerprint"] == equivalent["profile_fingerprint"]
    assert len(first["profile_fingerprint"]) == 64
    assert first["accessibility_profile"]["excluded_surfaces"] == ["gravel", "uneven"]
    different = route(client, profile={**first["accessibility_profile"], "avoid_stairs": True})
    assert first["profile_fingerprint"] != different["profile_fingerprint"]


def test_unknown_measurements_remain_null_and_cannot_prove_hard_constraints(client, admin):
    # Close each known departure through the ordinary graph mutation API.
    for name in ("stairs-west", "upper-west", "lower-west", "gravel-west"):
        response = client.patch(
            f"/api/v1/admin/path-edges/{demo_id('edge:' + name)}",
            headers=admin,
            json={
                "availability": "closed",
                "expected_version": 1,
                "reason": "Test departure closure",
            },
        )
        assert response.status_code == 200, response.text
    result = route(client, profile={"unknown_policy": "allow_with_warning"})
    assert edge_ids(result["primary"]) == {UNKNOWN}
    assert result["primary"]["verification"]["summary"] == "contains_uncertainty"
    assert result["primary"]["instructions"][0]["slope_pct"] is None
    assert result["primary"]["verification"]["verified_distance_m"] == 0
    assert {"UNKNOWN_ACCESSIBILITY", "MISSING_OBSERVATION", "UNVERIFIED_OBSERVATION"} <= {
        item["code"] for item in result["primary"]["warnings"]
    }
    assert {item["code"] for item in result["warnings"]} == {
        "DURATION_ESTIMATE",
        "SYNTHETIC_DATA",
    }
    constrained = route(
        client, profile={"unknown_policy": "allow_with_warning", "min_width_m": 0.9}
    )
    assert constrained["status"] == "no_route"
    assert constrained["excluded_edge_counts"]["unproven_width"] > 0
    with Session(engine()) as db:
        row = db.get(PathEdge, demo_id("edge:unknown-direct"))
        assert row.width_m is row.slope_pct is row.has_stairs is None


def test_mapped_closure_removes_both_directions_and_new_version_has_no_stale_route(client, admin):
    for source, destination in (("b", "c"), ("c", "b")):
        before = route(client, source=source, destination=destination, profile=STEP_FREE)
        assert RAMP in edge_ids(before["primary"]) and before["graph_version"] == "1"
    response = client.patch(
        f"/api/v1/admin/infrastructure/{demo_id('infrastructure:ramp')}",
        headers=admin,
        json={"availability": "closed", "expected_version": 1, "reason": "Close mapped ramp"},
    )
    assert response.status_code == 200, response.text
    for source, destination in (("b", "c"), ("c", "b")):
        after = route(client, source=source, destination=destination, profile=STEP_FREE)
        assert after["graph_version"] == "2" and after["status"] == "found"
        assert all(RAMP not in edge_ids(candidate) for candidate in all_routes(after))
        assert after["excluded_edge_counts"]["unavailable_dependency"] == 1


def test_expiry_is_committed_once_and_does_not_relax_permissive_hard_limits(client):
    assert RAMP in edge_ids(route(client, profile=STEP_FREE)["primary"])
    with Session(engine()) as db, db.begin():
        row = db.get(PathEdge, demo_id("edge:ramp-cross"))
        now = db.scalar(select(func.clock_timestamp()))
        row.verified_at = now - timedelta(days=31)
        row.verified_until = now - timedelta(seconds=1)
        db.get(GraphState, demo_id("campus")).next_expiry_at = row.verified_until
    for _ in range(2):
        result = route(client, profile={**STEP_FREE, "unknown_policy": "allow_with_warning"})
        assert result["graph_version"] == "2"
        assert all(RAMP not in edge_ids(candidate) for candidate in all_routes(result))
        assert result["excluded_edge_counts"]["unproven_slope"] > 0
    with Session(engine()) as db:
        row = db.get(PathEdge, demo_id("edge:ramp-cross"))
        assert row.verification == "needs_review" and row.row_version == 2
        assert row.slope_pct == 4 and row.width_m == 1.2
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 1
        assert (
            demo_id("edge:ramp-cross")
            in db.get(GraphEvent, (demo_id("campus"), 2)).changed_edge_ids
        )


def test_snapshot_is_read_only_repeatable_read_across_committed_graph_mutation(admin, monkeypatch):
    original = routing.bounded_rows
    calls = 0

    def concurrent_rows(db, statement, limit=routing.MAX_GRAPH_ROWS):
        nonlocal calls
        if calls == 0:
            assert db.scalar(text("SHOW transaction_isolation")) == "repeatable read"
            assert db.scalar(text("SHOW transaction_read_only")) == "on"
            commit_ramp_change("closed")
        calls += 1
        return original(db, statement, limit)

    monkeypatch.setattr(routing, "bounded_rows", concurrent_rows)
    payload = RouteRequest.model_validate(request_body(profile=STEP_FREE))
    loaded = routing.load_snapshot(payload)
    assert calls == 6 and loaded.version == 1
    ramp = next(edge for edge in loaded.snapshot.edges if edge.id == RAMP)
    assert ramp.dependencies[0].availability == "open"
    with Session(engine()) as db:
        assert db.get(GraphState, demo_id("campus")).version == 2
        assert db.get(Infrastructure, demo_id("infrastructure:ramp")).availability == "closed"
    fresh = routing.load_snapshot(payload)
    assert fresh.version == 2
    assert (
        next(edge for edge in fresh.snapshot.edges if edge.id == RAMP).dependencies[0].availability
        == "closed"
    )


def test_calculation_retries_after_real_committed_mutation(client, admin, monkeypatch):
    original = routing.calculate
    observed = []

    def concurrent_calculate(snapshot, *args, **kwargs):
        computed = original(snapshot, *args, **kwargs)
        observed.append(computed)
        if len(observed) == 1:
            commit_ramp_change("closed")
        return computed

    monkeypatch.setattr(routing, "calculate", concurrent_calculate)
    result = route(client, profile=STEP_FREE)
    assert len(observed) == 2
    assert RAMP in {arc.edge_id for arc in observed[0].primary.arcs}
    assert result["graph_version"] == "2"
    assert all(RAMP not in edge_ids(candidate) for candidate in all_routes(result))


def test_continual_graph_mutations_return_bounded_conflict_without_stale_primary(
    client, admin, monkeypatch
):
    original = routing.calculate
    calls = 0

    def concurrent_calculate(snapshot, *args, **kwargs):
        nonlocal calls
        computed = original(snapshot, *args, **kwargs)
        calls += 1
        commit_ramp_change("closed" if calls == 1 else "open")
        return computed

    monkeypatch.setattr(routing, "calculate", concurrent_calculate)
    response = client.post(URL, json=request_body(profile=STEP_FREE))
    assert calls == 2 and response.status_code == 409
    assert response.json()["code"] == "GRAPH_CHANGED_RETRY"
    assert response.json()["current_graph_version"] == "3"
    assert "primary" not in response.json()
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 2


def test_invalid_stored_geometry_is_service_error_not_no_route(client):
    # This is valid PostGIS geometry, but exceeds the routing graph complexity contract.
    # A small bend gives a clear distance lower bound even with 1,000 tiny segments.
    points = [
        [0.0002 * index / 1000, 0.0001 + min(index, 1000 - index) * 1e-8] for index in range(1001)
    ]
    points[0], points[-1] = POSITIONS["b"], POSITIONS["c"]
    with Session(engine()) as db, db.begin():
        db.get(PathEdge, demo_id("edge:ramp-cross")).geometry = graph.geometry(
            {"type": "LineString", "coordinates": points}
        )
    response = client.post(URL, json=request_body(profile=STEP_FREE))
    assert response.status_code == 503 and response.json()["code"] == "GRAPH_INVALID"
    assert "primary" not in response.json()


def test_geometry_total_is_bounded_before_decoding_any_graph_geometry(client, monkeypatch):
    with Session(engine()) as db:
        assert db.scalar(select(func.sum(func.ST_NPoints(PathEdge.geometry)))) == 26
    decoded_shapes = []

    def decode(shape):
        decoded_shapes.append(shape)
        return json.loads(shape)

    monkeypatch.setattr(routing, "MAX_GEOMETRY_POINTS", 25)
    # Replace only this service's decoder, not the shared JSON module used by HTTP parsing.
    monkeypatch.setattr(routing, "json", SimpleNamespace(loads=decode))
    response = client.post(URL, json=request_body(profile=STEP_FREE))
    assert response.status_code == 503 and response.json()["code"] == "GRAPH_TOO_LARGE"
    assert decoded_shapes == []
    assert "primary" not in response.json()


def test_existing_campus_without_graph_metadata_is_unavailable_not_missing(client):
    owner = create_engine(get_settings().database_url(owner=True), hide_parameters=True)
    try:
        with Session(owner) as db, db.begin():
            db.delete(db.get(GraphState, demo_id("campus")))
    finally:
        owner.dispose()
    response = client.post(URL, json=request_body())
    assert response.status_code == 503 and response.json()["code"] == "GRAPH_INVALID"
    assert "primary" not in response.json()
    with Session(engine()) as db:
        assert db.get(Campus, demo_id("campus")) is not None
        assert db.scalar(select(func.count()).select_from(PathEdge)) == 13


@pytest.mark.parametrize("field", ["cost_model_version", "policy_version"])
def test_unsupported_stored_version_is_service_error(client, field):
    with Session(engine()) as db, db.begin():
        setattr(db.get(GraphState, demo_id("campus")), field, "unsupported-test-version")
    response = client.post(URL, json=request_body())
    assert response.status_code == 503 and response.json()["code"] == "GRAPH_INVALID"


def test_primary_budget_exhaustion_is_503_and_secondary_budget_keeps_primary(client, monkeypatch):
    original = routing.calculate

    def exhausted_primary(*args, **kwargs):
        return original(*args, **kwargs, limits=SearchLimits(max_expansions=0))

    monkeypatch.setattr(routing, "calculate", exhausted_primary)
    response = client.post(URL, json=request_body(profile=STEP_FREE))
    assert response.status_code == 503
    assert response.json()["code"] == "ROUTING_BUDGET_EXCEEDED"
    assert "primary" not in response.json()

    def exhausted_alternatives(*args, **kwargs):
        return original(*args, **kwargs, limits=SearchLimits(max_alternative_candidates=0))

    monkeypatch.setattr(routing, "calculate", exhausted_alternatives)
    result = route(client, profile=STEP_FREE)
    assert result["status"] == "found" and RAMP in edge_ids(result["primary"])
    assert result["alternatives_exhaustive"] is False and result["alternatives"] == []
    monkeypatch.setattr(routing, "calculate", original)
    normal = route(client, profile=STEP_FREE)
    assert normal["primary"]["cost_m_equivalent"] == result["primary"]["cost_m_equivalent"]
    assert normal["alternatives"]
