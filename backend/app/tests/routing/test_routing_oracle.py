"""Independent exhaustive oracle and adversarial checks for the pure route engine.

The oracle consumes physical records directly. It does not call engine filtering,
cost, adjacency, reconstruction, or shortest-path helpers. Tiny graphs make complete
simple-path enumeration practical and give an algorithm-independent optimum.
"""

import json
import math
import random
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.routing import (
    Dependency,
    Edge,
    EndpointNotFound,
    GraphInvalid,
    GraphSnapshot,
    Node,
    Profile,
    RoutingBudgetExceeded,
    SearchLimits,
    calculate,
    chord_distance,
    ecef,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
FUTURE = NOW + timedelta(days=30)
PAST = NOW - timedelta(seconds=1)
GENERAL = Profile()
PERMISSIVE = Profile(unknown_policy="allow_with_warning")
STEP_FREE = Profile(
    avoid_stairs=True,
    max_slope_pct=8,
    min_width_m=0.9,
    excluded_surfaces=("gravel", "uneven"),
)
PROFILES = (
    GENERAL,
    PERMISSIVE,
    STEP_FREE,
    replace(STEP_FREE, unknown_policy="allow_with_warning"),
)


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    """Override the inherited integration fixture: this module needs no DB."""


@pytest.fixture(autouse=True)
def reset_database():
    """Override integration seeding so pure algorithm tests remain pure."""


def nodes(*names):
    return tuple(Node(name, (-0.12 + i * 0.00001, 51.5)) for i, name in enumerate(names))


def edge(key, source, target, graph_nodes, distance=10.0, **changes):
    by_id = {node.id: node for node in graph_nodes}
    return Edge(
        id=key,
        source_id=source,
        target_id=target,
        geometry=(by_id[source].point, by_id[target].point),
        distance_m=distance,
        direction=changes.pop("direction", "forward"),
        accessibility=changes.pop("accessibility", "accessible"),
        availability=changes.pop("availability", "open"),
        verification=changes.pop("verification", "verified"),
        expires_at=changes.pop("expires_at", FUTURE),
        width_m=changes.pop("width_m", 1.2),
        slope_pct=changes.pop("slope_pct", 0),
        surface=changes.pop("surface", "smooth"),
        has_stairs=changes.pop("has_stairs", False),
        **changes,
    )


def snapshot(graph_nodes, graph_edges):
    return GraphSnapshot(tuple(graph_nodes), tuple(graph_edges), NOW)


def independently_current(observation):
    return (
        observation.verification == "verified"
        and observation.expires_at is not None
        and observation.expires_at > NOW
    )


def independently_admissible(record, profile, active_nodes):
    """Translate the published eligibility table, independently of the engine."""
    if (
        not record.active
        or record.source_id not in active_nodes
        or record.target_id not in active_nodes
    ):
        return False, False
    if record.availability != "open" or record.restricted or record.accessibility == "inaccessible":
        return False, False
    for dependency in record.dependencies:
        if (
            not dependency.active
            or dependency.availability != "open"
            or dependency.accessibility == "inaccessible"
        ):
            return False, False
    current = independently_current(record)
    checks = (
        (profile.avoid_stairs, record.has_stairs is False),
        (
            profile.max_slope_pct is not None,
            record.slope_pct is not None
            and (profile.max_slope_pct is None or abs(record.slope_pct) <= profile.max_slope_pct),
        ),
        (
            profile.min_width_m is not None,
            record.width_m is not None
            and (profile.min_width_m is None or record.width_m >= profile.min_width_m),
        ),
        (
            bool(profile.excluded_surfaces),
            record.surface != "unknown" and record.surface not in profile.excluded_surfaces,
        ),
    )
    if any(required and (not current or not proved) for required, proved in checks):
        return False, False
    uncertain = (
        not current
        or record.accessibility == "unknown"
        or record.has_stairs is None
        or record.width_m is None
        or record.slope_pct is None
        or record.surface == "unknown"
        or any(
            not independently_current(dependency) or dependency.accessibility == "unknown"
            for dependency in record.dependencies
        )
    )
    return not (uncertain and profile.unknown_policy == "exclude"), uncertain


def independently_weight(record, uncertain):
    # Published metre-equivalent cost. Never call the production cost helper.
    grade_penalty = 0 if record.slope_pct is None else 2 * abs(record.slope_pct) / 100
    surface_penalty = {"smooth": 0, "uneven": 0.30, "gravel": 0.50, "unknown": 0.15}[record.surface]
    return record.distance_m * (1 + grade_penalty + surface_penalty + (0.50 if uncertain else 0))


def enumerate_all_simple_paths(graph, source, destination, profile):
    """A deliberately tiny DFS enumerator, with no priority queue or heuristics."""
    active_nodes = {node.id for node in graph.nodes if node.active}
    if source not in active_nodes or destination not in active_nodes:
        return []
    adjacency = {key: [] for key in active_nodes}
    for record in graph.edges:
        eligible, uncertain = independently_admissible(record, profile, active_nodes)
        if not eligible:
            continue
        cost = independently_weight(record, uncertain)
        if record.direction in ("forward", "both"):
            adjacency[record.source_id].append((record.target_id, record.id, "forward", cost))
        if record.direction in ("reverse", "both"):
            adjacency[record.target_id].append((record.source_id, record.id, "reverse", cost))
    found = []

    def visit(current, visited, arcs, costs):
        if current == destination:
            found.append((math.fsum(costs), tuple(arcs), tuple(visited)))
            return
        for target, key, direction, cost in adjacency[current]:
            if target not in visited:
                visit(target, [*visited, target], [*arcs, (key, direction)], [*costs, cost])

    visit(source, [source], [], [])
    return sorted(found)


def route_identity(route):
    return tuple((arc.edge_id, arc.direction) for arc in route.arcs)


def assert_route_matches_records(route, graph, profile, source, destination):
    by_id = {record.id: record for record in graph.edges}
    active_nodes = {node.id for node in graph.nodes if node.active}
    assert route.node_ids[0] == source
    assert route.node_ids[-1] == destination
    assert len(set(route.node_ids)) == len(route.node_ids)
    assert len(route.node_ids) == len(route.arcs) + 1
    distances, weights, coordinates = [], [], []
    for index, reference in enumerate(route.arcs):
        record = by_id[reference.edge_id]
        eligible, uncertain = independently_admissible(record, profile, active_nodes)
        assert eligible
        start, end = record.source_id, record.target_id
        geometry = record.geometry
        if reference.direction == "reverse":
            assert record.direction in ("reverse", "both")
            start, end = end, start
            geometry = tuple(reversed(geometry))
        else:
            assert reference.direction == "forward"
            assert record.direction in ("forward", "both")
        assert (route.node_ids[index], route.node_ids[index + 1]) == (start, end)
        coordinates.extend(geometry if not coordinates else geometry[1:])
        distances.append(record.distance_m)
        weights.append(independently_weight(record, uncertain))
    assert route.total_distance_m == pytest.approx(math.fsum(distances), rel=1e-12, abs=1e-12)
    assert route.cost_m_equivalent == pytest.approx(math.fsum(weights), rel=1e-12, abs=1e-12)
    assert route.estimated_duration_s == pytest.approx(
        math.fsum(distances) / profile.travel_speed_mps
    )
    if coordinates:
        assert route.geometry["type"] == "LineString"
        assert [tuple(point) for point in route.geometry["coordinates"]] == coordinates
    else:
        assert route.geometry["type"] == "Point"
        assert tuple(route.geometry["coordinates"]) == next(
            node.point for node in graph.nodes if node.id == source
        )


def generated_graph(seed):
    rng = random.Random(seed)
    graph_nodes = nodes("s", "a", "b", "c", "d", "t")
    graph_edges = []
    # Some seeds are completely measured; others mix adverse observations. This
    # avoids generated coverage degenerating into exclusively no-route results.
    adverse = seed % 3 != 0
    for source in graph_nodes:
        for target in graph_nodes:
            if source.id == target.id or rng.random() > 0.34:
                continue
            for parallel in range(1 + (rng.random() < 0.18)):
                change = {"direction": rng.choice(("forward", "reverse", "both"))}
                if adverse:
                    change.update(
                        accessibility=rng.choice(("accessible",) * 7 + ("unknown", "inaccessible")),
                        availability=rng.choice(("open",) * 12 + ("closed", "temporarily_blocked")),
                        verification=rng.choice(
                            ("verified",) * 10 + ("unverified", "needs_review")
                        ),
                        expires_at=rng.choice((FUTURE,) * 10 + (NOW, PAST, None)),
                        width_m=rng.choice((None, 0.8, 0.9, 1.2, 2.0)),
                        slope_pct=rng.choice((None, -9, -8, 0, 4, 8, 9)),
                        surface=rng.choice(("smooth", "smooth", "uneven", "gravel", "unknown")),
                        has_stairs=rng.choice((False, False, False, True, None)),
                    )
                    if rng.random() < 0.2:
                        change["dependencies"] = (
                            Dependency(
                                id=f"dependency-{source.id}-{target.id}-{parallel}",
                                accessibility=rng.choice(("accessible", "unknown", "inaccessible")),
                                availability=rng.choice(("open", "open", "closed")),
                                verification=rng.choice(("verified", "needs_review")),
                                expires_at=rng.choice((FUTURE, PAST)),
                            ),
                        )
                graph_edges.append(
                    edge(
                        f"{source.id}-{target.id}-{parallel}",
                        source.id,
                        target.id,
                        graph_nodes,
                        distance=rng.choice((10.0, 12.0, 14.0, 20.0, 25.0)),
                        **change,
                    )
                )
    return snapshot(graph_nodes, graph_edges)


@pytest.mark.parametrize("seed", range(24))
@pytest.mark.parametrize(
    "profile", PROFILES, ids=("general", "permissive", "step-free", "step-free-warn")
)
def test_generated_directed_multigraphs_match_exhaustive_oracle(seed, profile):
    graph = generated_graph(seed)
    expected = enumerate_all_simple_paths(graph, "s", "t", profile)
    for algorithm in ("dijkstra", "astar"):
        actual = calculate(graph, "s", "t", profile, algorithm=algorithm, alternatives_limit=2)
        if not expected:
            assert actual.status == "no_route"
            assert actual.primary is None
            assert not actual.alternatives
            continue
        assert actual.status == "found"
        assert actual.primary.cost_m_equivalent == pytest.approx(expected[0][0], abs=1e-6, rel=1e-9)
        valid_paths = {arcs: cost for cost, arcs, _ in expected}
        returned = (actual.primary, *actual.alternatives)
        identities = [route_identity(route) for route in returned]
        assert len(set(identities)) == len(identities)
        assert len(actual.alternatives) <= 2
        lengths = {record.id: record.distance_m for record in graph.edges}
        for index, route in enumerate(returned):
            assert_route_matches_records(route, graph, profile, "s", "t")
            assert route_identity(route) in valid_paths
            assert route.cost_m_equivalent <= actual.primary.cost_m_equivalent * 1.5
            for earlier in returned[:index]:
                common = {arc.edge_id for arc in route.arcs} & {arc.edge_id for arc in earlier.arcs}
                overlap = math.fsum(lengths[key] for key in common)
                assert overlap <= 0.8 * min(route.total_distance_m, earlier.total_distance_m)


@pytest.mark.parametrize("algorithm", ("dijkstra", "astar"))
def test_parallel_arcs_equal_costs_and_sub_tolerance_improvement(algorithm):
    graph_nodes = nodes("s", "a", "t")
    graph = snapshot(
        graph_nodes,
        (
            edge("equal-direct", "s", "t", graph_nodes, 20),
            edge("slightly-shorter", "s", "t", graph_nodes, 20 - 1e-8),
            edge("parallel-slow", "s", "a", graph_nodes, 15),
            edge("parallel-fast", "s", "a", graph_nodes, 10),
            edge("finish", "a", "t", graph_nodes, 10),
        ),
    )
    result = calculate(graph, "s", "t", GENERAL, algorithm=algorithm, alternatives_limit=2)
    assert route_identity(result.primary) == (("slightly-shorter", "forward"),)
    assert result.primary.cost_m_equivalent == 20 - 1e-8
    assert_route_matches_records(result.primary, graph, GENERAL, "s", "t")


@pytest.mark.parametrize("algorithm", ("dijkstra", "astar"))
def test_reverse_geometry_stays_ordered_and_no_visual_crossing_creates_connectivity(algorithm):
    graph_nodes = (
        Node("s", (0, 0)),
        Node("a", (0.00001, 0.00001)),
        Node("t", (0.00002, 0)),
        Node("same-xy-other-level", (0.00001, 0.00001)),
    )
    graph = snapshot(
        graph_nodes,
        (
            edge("first", "a", "s", graph_nodes, direction="reverse", slope_pct=-8),
            edge("second", "a", "t", graph_nodes, direction="both", slope_pct=8),
        ),
    )
    result = calculate(graph, "s", "t", STEP_FREE, algorithm=algorithm)
    assert route_identity(result.primary) == (("first", "reverse"), ("second", "forward"))
    assert_route_matches_records(result.primary, graph, STEP_FREE, "s", "t")
    assert calculate(graph, "t", "s", GENERAL, algorithm=algorithm).status == "no_route"
    assert (
        calculate(graph, "s", "same-xy-other-level", GENERAL, algorithm=algorithm).status
        == "no_route"
    )


@pytest.mark.parametrize(
    ("changes", "profile", "allowed"),
    [
        ({"slope_pct": 8}, STEP_FREE, True),
        ({"slope_pct": -8}, STEP_FREE, True),
        ({"slope_pct": math.nextafter(8, math.inf)}, STEP_FREE, False),
        ({"slope_pct": math.nextafter(-8, -math.inf)}, STEP_FREE, False),
        ({"width_m": 0.9}, STEP_FREE, True),
        ({"width_m": math.nextafter(0.9, 0)}, STEP_FREE, False),
        ({"slope_pct": None}, replace(STEP_FREE, unknown_policy="allow_with_warning"), False),
        ({"width_m": None}, replace(STEP_FREE, unknown_policy="allow_with_warning"), False),
        ({"has_stairs": None}, replace(STEP_FREE, unknown_policy="allow_with_warning"), False),
        ({"surface": "unknown"}, replace(STEP_FREE, unknown_policy="allow_with_warning"), False),
        (
            {"verification": "unverified"},
            replace(STEP_FREE, unknown_policy="allow_with_warning"),
            False,
        ),
        ({"expires_at": NOW}, replace(STEP_FREE, unknown_policy="allow_with_warning"), False),
        ({"expires_at": NOW + timedelta(microseconds=1)}, STEP_FREE, True),
        ({"expires_at": None}, GENERAL, False),
        ({"expires_at": None}, PERMISSIVE, True),
        ({"accessibility": "unknown"}, GENERAL, False),
        ({"accessibility": "unknown"}, PERMISSIVE, True),
        ({"accessibility": "inaccessible"}, PERMISSIVE, False),
        ({"availability": "closed", "verification": "needs_review"}, PERMISSIVE, False),
        ({"availability": "temporarily_blocked", "verification": "unverified"}, PERMISSIVE, False),
        ({"has_stairs": True}, STEP_FREE, False),
        ({"surface": "gravel"}, STEP_FREE, False),
        ({"surface": "uneven"}, STEP_FREE, False),
        ({"restricted": True}, PERMISSIVE, False),
        ({"has_ramp": None}, STEP_FREE, True),
    ],
)
def test_exact_hard_boundaries_currentness_and_unknown_policy(changes, profile, allowed):
    graph_nodes = nodes("s", "t")
    graph = snapshot(graph_nodes, (edge("only", "s", "t", graph_nodes, **changes),))
    for algorithm in ("dijkstra", "astar"):
        result = calculate(graph, "s", "t", profile, algorithm=algorithm)
        assert (result.status == "found") is allowed
        if allowed:
            assert_route_matches_records(result.primary, graph, profile, "s", "t")
        else:
            assert result.reason == "constraints_exclude_all_paths"


@pytest.mark.parametrize(
    ("change", "general_allowed", "permissive_allowed"),
    [
        ({}, True, True),
        ({"availability": "closed", "verification": "needs_review"}, False, False),
        ({"availability": "temporarily_blocked", "expires_at": PAST}, False, False),
        ({"active": False}, False, False),
        ({"accessibility": "inaccessible"}, False, False),
        ({"accessibility": "unknown"}, False, True),
        ({"verification": "unverified"}, False, True),
        ({"verification": "needs_review"}, False, True),
        ({"expires_at": NOW}, False, True),
        ({"expires_at": None}, False, True),
    ],
)
def test_mapped_infrastructure_gates_both_directions(change, general_allowed, permissive_allowed):
    dependency = replace(
        Dependency("ramp", accessibility="accessible", verification="verified", expires_at=FUTURE),
        **change,
    )
    graph_nodes = nodes("s", "t")
    graph = snapshot(
        graph_nodes,
        (edge("both", "s", "t", graph_nodes, direction="both", dependencies=(dependency,)),),
    )
    for profile, allowed in ((GENERAL, general_allowed), (PERMISSIVE, permissive_allowed)):
        for start, end in (("s", "t"), ("t", "s")):
            result = calculate(graph, start, end, profile)
            assert (result.status == "found") is allowed
            if allowed:
                assert_route_matches_records(result.primary, graph, profile, start, end)


def test_unknown_cost_keeps_distance_duration_and_uncertainty_separate():
    graph_nodes = nodes("s", "t")
    graph = snapshot(
        graph_nodes,
        (
            edge(
                "unknown",
                "s",
                "t",
                graph_nodes,
                distance=20,
                accessibility="unknown",
                verification="unverified",
                expires_at=None,
                slope_pct=None,
                width_m=None,
                surface="unknown",
                has_stairs=None,
            ),
        ),
    )
    result = calculate(graph, "s", "t", replace(PERMISSIVE, travel_speed_mps=2))
    assert result.primary.total_distance_m == 20
    assert result.primary.estimated_duration_s == 10
    assert result.primary.cost_m_equivalent == 33
    assert result.primary.warnings
    assert_route_matches_records(
        result.primary, graph, replace(PERMISSIVE, travel_speed_mps=2), "s", "t"
    )


@pytest.mark.parametrize("algorithm", ("dijkstra", "astar"))
def test_same_node_disconnected_missing_and_inactive_nodes(algorithm):
    graph_nodes = (*nodes("s", "t", "isolated"), Node("inactive", (0, 0), active=False))
    graph = snapshot(graph_nodes, (edge("only", "s", "t", graph_nodes),))
    same = calculate(graph, "s", "s", STEP_FREE, algorithm=algorithm, alternatives_limit=2)
    assert same.status == "found"
    assert not same.primary.arcs
    assert not same.primary.instructions
    assert not same.alternatives
    assert_route_matches_records(same.primary, graph, STEP_FREE, "s", "s")
    disconnected = calculate(graph, "s", "isolated", GENERAL, algorithm=algorithm)
    assert disconnected.status == "no_route"
    assert disconnected.reason == "disconnected"
    assert disconnected.primary is None
    with pytest.raises(EndpointNotFound):
        calculate(graph, "s", "missing", GENERAL, algorithm=algorithm)
    inactive = calculate(graph, "s", "inactive", GENERAL, algorithm=algorithm)
    assert inactive.status == "no_route"


@pytest.mark.parametrize("seed", range(8))
def test_ecef_consistency_and_admissibility_against_all_simple_paths(seed):
    graph = generated_graph(seed * 3)
    goal = next(node for node in graph.nodes if node.id == "t")
    by_id = {node.id: node for node in graph.nodes}
    estimates = {node.id: chord_distance(node.point, goal.point) for node in graph.nodes}
    assert estimates["t"] == 0
    for record in graph.edges:
        physical_chord = chord_distance(
            by_id[record.source_id].point, by_id[record.target_id].point
        )
        assert record.distance_m >= physical_chord
        for start, end in (
            (record.source_id, record.target_id),
            (record.target_id, record.source_id),
        ):
            assert estimates[start] <= record.distance_m + estimates[end] + 1e-9
    for node in graph.nodes:
        paths = enumerate_all_simple_paths(graph, node.id, "t", GENERAL)
        if paths:
            assert estimates[node.id] <= paths[0][0] + 1e-9


def test_ecef_is_wgs84_and_chord_handles_dateline_and_poles():
    a, flattening = 6378137, 1 / 298.257223563
    polar_radius = a * (1 - flattening)
    assert ecef((0, 0)) == pytest.approx((a, 0, 0), abs=1e-8)
    assert ecef((90, 0)) == pytest.approx((0, a, 0), abs=1e-8)
    assert ecef((0, 90)) == pytest.approx((0, 0, polar_radius), abs=1e-8)
    assert chord_distance((0, 0), (180, 0)) == pytest.approx(2 * a)
    assert chord_distance((179.999, 0), (-179.999, 0)) < 223
    assert chord_distance((0, 90), (180, 90)) < 1e-8


@pytest.mark.parametrize("invalid_distance", (0.0, -1.0, math.nan, math.inf, -math.inf, 0.01))
def test_invalid_edge_distance_or_heuristic_bound_is_rejected(invalid_distance):
    graph_nodes = nodes("s", "t")
    with pytest.raises(GraphInvalid):
        calculate(
            snapshot(graph_nodes, (edge("bad", "s", "t", graph_nodes, invalid_distance),)),
            "s",
            "t",
            GENERAL,
        )


@pytest.mark.parametrize(
    "defect",
    (
        "duplicate-node",
        "duplicate-edge",
        "missing-endpoint",
        "geometry-endpoint",
        "nan-point",
        "bad-slope",
        "bad-width",
    ),
)
def test_invalid_graph_records_fail_instead_of_silently_disappearing(defect):
    graph_nodes = nodes("s", "t")
    graph_edges = (edge("only", "s", "t", graph_nodes),)
    if defect == "duplicate-node":
        graph_nodes = (*graph_nodes, graph_nodes[0])
    elif defect == "duplicate-edge":
        graph_edges = (*graph_edges, graph_edges[0])
    elif defect == "missing-endpoint":
        graph_edges = (replace(graph_edges[0], target_id="missing"),)
    elif defect == "geometry-endpoint":
        graph_edges = (replace(graph_edges[0], geometry=tuple(reversed(graph_edges[0].geometry))),)
    elif defect == "nan-point":
        graph_nodes = (replace(graph_nodes[0], point=(math.nan, 0)), graph_nodes[1])
    elif defect == "bad-slope":
        graph_edges = (replace(graph_edges[0], slope_pct=math.nan),)
    else:
        graph_edges = (replace(graph_edges[0], width_m=math.inf),)
    with pytest.raises(GraphInvalid):
        calculate(snapshot(graph_nodes, graph_edges), "s", "t", GENERAL)


def test_alternative_cost_and_overlap_cutoffs_are_not_relaxed_by_epsilon():
    graph_nodes = nodes("s", "a", "b", "t")
    graph = snapshot(
        graph_nodes,
        (
            edge("best", "s", "t", graph_nodes, 20),
            edge("at-cost-bound", "s", "t", graph_nodes, 30),
            edge("past-cost-bound", "s", "t", graph_nodes, math.nextafter(30, math.inf)),
        ),
    )
    result = calculate(graph, "s", "t", GENERAL, alternatives_limit=2)
    assert [route_identity(route) for route in result.alternatives] == [
        (("at-cost-bound", "forward"),)
    ]
    # Sharing exactly 80% of the shorter route is permitted; the next float over
    # the published threshold is not. Separate graphs prevent candidate ordering
    # from determining which of these near-identical alternatives is retained.
    for shared, expected_count in ((16.0, 1), (math.nextafter(16.0, math.inf), 0)):
        graph = snapshot(
            graph_nodes,
            (
                edge("shared", "s", "a", graph_nodes, shared),
                edge("best", "a", "t", graph_nodes, 20 - shared),
                edge("detour1", "a", "b", graph_nodes, 5),
                edge("detour2", "b", "t", graph_nodes, 5),
            ),
        )
        result = calculate(graph, "s", "t", GENERAL, alternatives_limit=2)
        assert len(result.alternatives) == expected_count


def test_primary_and_alternative_budgets_have_distinct_outcomes():
    graph_nodes = nodes("s", "a", "b", "t")
    graph = snapshot(
        graph_nodes,
        (
            edge("first", "s", "a", graph_nodes),
            edge("finish", "a", "t", graph_nodes),
            edge("other1", "s", "b", graph_nodes),
            edge("other2", "b", "t", graph_nodes),
        ),
    )
    for algorithm in ("dijkstra", "astar"):
        with pytest.raises(RoutingBudgetExceeded):
            calculate(
                graph, "s", "t", GENERAL, algorithm=algorithm, limits=SearchLimits(max_expansions=1)
            )
    capped = calculate(
        graph,
        "s",
        "t",
        GENERAL,
        alternatives_limit=2,
        limits=SearchLimits(max_alternative_candidates=0),
    )
    assert capped.status == "found"
    assert capped.primary.cost_m_equivalent == 20
    assert not capped.alternatives
    assert capped.alternatives_exhaustive is False


def test_phase_zero_numerical_cases_against_production_algorithms():
    examples = Path(__file__).resolve().parents[4] / "docs" / "examples"
    fixture = json.loads((examples / "campus-graph.json").read_text())
    cases = json.loads((examples / "routing-cases.json").read_text())
    # The design fixture deliberately used XY toy lengths and approximate degrees.
    # Shrink coordinates only in this adapter to preserve its exact numerical
    # scenarios while satisfying the production WGS84 chord ingestion contract.
    graph_nodes = tuple(
        Node(row["id"], tuple(value * 0.99 for value in row["lon_lat"])) for row in fixture["nodes"]
    )
    for case in cases:
        profile = Profile(**(fixture["profiles"][case["profile"]] | case["profile_overrides"]))
        graph_edges = []
        for original in fixture["edges"]:
            record = original | case["edge_overrides"].get(original["id"], {})
            fields = {
                key: value
                for key, value in record.items()
                if key not in {"id", "source", "target", "distance_m"}
            }
            fields["restricted"] = record["id"] in case["blocked_edges"]
            graph_edges.append(
                edge(
                    record["id"],
                    record["source"],
                    record["target"],
                    graph_nodes,
                    record["distance_m"],
                    **fields,
                )
            )
        graph = snapshot(graph_nodes, graph_edges)
        for algorithm in ("dijkstra", "astar"):
            result = calculate(
                graph, case["source"], case["destination"], profile, algorithm=algorithm
            )
            if case["expected_cost"] is None:
                assert result.status == "no_route", case["id"]
            else:
                assert result.status == "found", case["id"]
                assert result.primary.cost_m_equivalent == pytest.approx(case["expected_cost"]), (
                    case["id"]
                )
                assert [arc.edge_id for arc in result.primary.arcs] == case["expected_edges"], case[
                    "id"
                ]
                assert_route_matches_records(
                    result.primary, graph, profile, case["source"], case["destination"]
                )
