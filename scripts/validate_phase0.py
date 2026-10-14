#!/usr/bin/env python3
"""Standard-library design checks only; no production routing/API implementation."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "docs" / "examples"
SURFACE = {"smooth": 0.0, "uneven": 0.3, "gravel": 0.5, "unknown": 0.15}
CHECKS = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)
    print(f"PASS {name}")


def read_json(name):
    def invalid(value):
        raise ValueError(f"nonfinite JSON value: {value}")
    return json.loads((EXAMPLES / name).read_text(), parse_constant=invalid)


def uncertain(edge):
    return (
        edge["accessibility"] == "unknown"
        or edge["verification"] != "verified"
        or edge["surface"] == "unknown"
        or any(edge[key] is None for key in ("width_m", "slope_pct", "has_stairs"))
    )


def reasons(edge, profile, blocked):
    """Explicit design policy oracle; independent of any future engine."""
    result = set()
    current = edge["verification"] == "verified"
    if edge["id"] in blocked or edge["availability"] != "open":
        result.add("closed")
    if edge["accessibility"] == "inaccessible":
        result.add("inaccessible")
    if profile["avoid_stairs"]:
        if edge["has_stairs"] is True:
            result.add("stairs")
        elif edge["has_stairs"] is None or not current:
            result.add("stairs_unproven")
    if profile["max_slope_pct"] is not None:
        if edge["slope_pct"] is None or not current:
            result.add("slope_unproven")
        elif abs(edge["slope_pct"]) > profile["max_slope_pct"]:
            result.add("slope")
    if profile["min_width_m"] is not None:
        if edge["width_m"] is None or not current:
            result.add("width_unproven")
        elif edge["width_m"] < profile["min_width_m"]:
            result.add("width")
    if profile["excluded_surfaces"] and (
        not current or edge["surface"] == "unknown"
        or edge["surface"] in profile["excluded_surfaces"]
    ):
        result.add("surface")
    if profile["unknown_policy"] == "exclude" and uncertain(edge):
        result.add("unknown")
    return result


def cost(edge):
    grade = abs(edge["slope_pct"]) / 100 if edge["slope_pct"] is not None else 0
    return edge["distance_m"] * (1 + 2 * grade + SURFACE[edge["surface"]] + 0.5 * uncertain(edge))


def paths(graph, profile, source, destination, blocked=()):
    """Exhaustively enumerate tiny fixture paths; not Dijkstra, A*, or Yen."""
    adjacency = {n["id"]: [] for n in graph["nodes"]}
    for edge in graph["edges"]:
        if reasons(edge, profile, blocked):
            continue
        if edge["direction"] in ("both", "forward"):
            adjacency[edge["source"]].append((edge["target"], edge))
        if edge["direction"] in ("both", "reverse"):
            adjacency[edge["target"]].append((edge["source"], edge))
    result = []

    def visit(node, visited, edges, accumulated):
        if node == destination:
            result.append((accumulated, edges))
            return
        for neighbor, edge in adjacency[node]:
            if neighbor not in visited:
                visit(neighbor, visited | {neighbor}, edges + [edge["id"]], accumulated + cost(edge))

    visit(source, {source}, [], 0.0)
    return sorted(result, key=lambda item: (item[0], item[1]))


def ecef(lon_lat):
    lon, lat = map(math.radians, lon_lat)
    flattening = 1 / 298.257223563
    eccentricity_squared = flattening * (2 - flattening)
    radius = 6378137 / math.sqrt(1 - eccentricity_squared * math.sin(lat) ** 2)
    return (
        radius * math.cos(lat) * math.cos(lon),
        radius * math.cos(lat) * math.sin(lon),
        radius * (1 - eccentricity_squared) * math.sin(lat),
    )


def luminance(hex_color):
    values = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))


def validate():
    required = [
        "README.md", "AGENTS.md", ".env.example", ".gitignore", ".nvmrc", ".python-version",
        *["docs/" + name + ".md" for name in (
            "ARCHITECTURE", "IMPLEMENTATION_PLAN", "DATABASE_SCHEMA", "API_CONTRACT",
            "ROUTING_DESIGN", "MODEL_SWITCH_GUIDE", "PROJECT_STATUS", "RISK_REGISTER",
            "TESTING", "TEST_EVIDENCE", "DEPLOYMENT", "SECURITY", "REPORTING_AND_EVENTS",
            "AI_STRATEGY", "FRONTEND_DESIGN",
        )],
    ]
    check("required_documents", all((ROOT / p).is_file() and (ROOT / p).stat().st_size for p in required))
    directories = [
        "frontend/src/app", "frontend/src/components", "frontend/src/features", "frontend/src/pages",
        "frontend/src/hooks", "frontend/src/services", "frontend/src/types", "frontend/src/styles",
        "frontend/src/assets", "frontend/e2e", "backend/app/api", "backend/app/core", "backend/app/db",
        "backend/app/models", "backend/app/schemas", "backend/app/repositories", "backend/app/services",
        "backend/app/routing", "backend/app/tests/unit", "backend/app/tests/integration",
        "backend/app/tests/routing", "backend/alembic/versions", "ml/datasets", "ml/training",
        "ml/inference", "ml/evaluation", ".github/workflows",
    ]
    check("monorepo_scaffold", all((ROOT / p / ".gitkeep").is_file() for p in directories))
    broken = []
    for file in ROOT.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", file.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#")[0]
            if not (file.parent / target).resolve().exists():
                broken.append(f"{file.relative_to(ROOT)}: {target}")
    check("relative_document_links", not broken)
    whitespace_errors = []
    for file in ROOT.rglob("*"):
        if not file.is_file() or ".git" in file.relative_to(ROOT).parts:
            continue
        content = file.read_text()
        if content and not content.endswith("\n"):
            whitespace_errors.append(str(file.relative_to(ROOT)))
        if any(line.rstrip() != line for line in content.splitlines()):
            whitespace_errors.append(str(file.relative_to(ROOT)))
    check("tracked_and_untracked_text_whitespace", not whitespace_errors)
    forbidden = []
    for base in ("backend", "frontend", "ml"):
        forbidden.extend(str(p.relative_to(ROOT)) for p in (ROOT / base).rglob("*") if p.is_file() and p.name not in ("README.md", ".gitkeep"))
    check("phase_boundary_no_application_implementation", not forbidden)

    graph = read_json("campus-graph.json")
    cases = read_json("routing-cases.json")
    check("fixture_origin_is_explicit", graph["data_origin"] == "synthetic_demo" and "not production seed" in graph["purpose"])
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = {e["id"]: e for e in graph["edges"]}
    check("fixture_unique_ids_and_references", len(nodes) == len(graph["nodes"]) and len(edges) == len(graph["edges"]) and all(e["source"] in nodes and e["target"] in nodes and e["source"] != e["target"] for e in edges.values()))
    check("physical_distance_and_nonnegative_cost", all(math.isfinite(e["distance_m"]) and e["distance_m"] > 0 and math.isclose(e["distance_m"], math.dist(nodes[e["source"]]["xy_m"], nodes[e["target"]]["xy_m"]), abs_tol=1e-9) and cost(e) >= e["distance_m"] for e in edges.values()))
    coords = {n: ecef(value["lon_lat"]) for n, value in nodes.items()}
    check("ecef_edge_lower_bound", all(math.dist(coords[e["source"]], coords[e["target"]]) <= e["distance_m"] for e in edges.values()))
    violations = []
    for target in nodes:
        for e in edges.values():
            for a, b in ((e["source"], e["target"]), (e["target"], e["source"])):
                if math.dist(coords[a], coords[target]) > cost(e) + math.dist(coords[b], coords[target]) + 1e-9:
                    violations.append((target, e["id"]))
    check("heuristic_consistency_all_fixture_goals", not violations)

    for case in cases:
        candidate = copy.deepcopy(graph)
        for e in candidate["edges"]:
            e.update(case["edge_overrides"].get(e["id"], {}))
        profile = {**graph["profiles"][case["profile"]], **case["profile_overrides"]}
        result = paths(candidate, profile, case["source"], case["destination"], case["blocked_edges"])
        if case["expected_cost"] is None:
            matches = not result
        else:
            matches = bool(result) and math.isclose(result[0][0], case["expected_cost"], abs_tol=1e-6, rel_tol=1e-9) and result[0][1] == case["expected_edges"]
        if case.get("expected_uncertainty"):
            matches = matches and any(uncertain(edges[e]) for e in result[0][1])
        check("design_case_" + case["id"], matches)

    eligible_paths = paths(graph, graph["profiles"]["wheelchair"], "s", "t")
    primary_cost, primary_edges = eligible_paths[0]
    alternate_cost, alternate_edges = eligible_paths[1]
    shorter = min(sum(edges[e]["distance_m"] for e in route) for route in (primary_edges, alternate_edges))
    overlap = sum(edges[e]["distance_m"] for e in set(primary_edges) & set(alternate_edges))
    check("distinct_eligible_alternative", len(eligible_paths) == 2 and primary_edges != alternate_edges and overlap / shorter <= 0.8 and alternate_cost <= 1.5 * primary_cost)

    request, found, missing = [read_json(n) for n in ("route-request.json", "route-found.json", "route-no-route.json")]
    wire_id = lambda alias: str(uuid.uuid5(uuid.NAMESPACE_URL, "pathable:phase0:" + alias))
    wire_edges = {wire_id(alias): edge for alias, edge in edges.items()}
    check("wire_request_identity_and_profile", request["source_id"] == wire_id("s") and request["destination_id"] == wire_id("t") and request["accessibility_profile"] == graph["profiles"]["wheelchair"] and request["alternatives_limit"] == 2)
    for result in (found, missing):
        for field in ("campus_id", "source_id", "destination_id"):
            uuid.UUID(result[field])
        assert result["graph_version"].isdigit()
        assert result["data_origin"] == "synthetic_demo"
        # The tiny fixture uses only simple numeric values. This is JCS-compatible
        # for these values, not a general production canonical-JSON encoder.
        normalized = {k: int(v) if isinstance(v, float) and v.is_integer() else v for k, v in result["accessibility_profile"].items()}
        normalized["excluded_surfaces"] = sorted(set(normalized["excluded_surfaces"]))
        profile_bytes = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
        assert result["profile_fingerprint"] == hashlib.sha256(profile_bytes).hexdigest()
    check("wire_snapshot_identity", found["graph_version"] == "1" and missing["graph_version"] == "2")
    check("wire_found_alternative_count", found["status"] == "found" and len(found["alternatives"]) == 1 and found["alternatives_exhaustive"] is True)
    for index, route in enumerate([found["primary"], *found["alternatives"]]):
        route_edges = [wire_edges[arc["edge_id"]] for arc in route["arcs"]]
        expected_nodes = [wire_id(route_edges[0]["source"])] + [wire_id(e["target"]) for e in route_edges]
        node_coordinates = {wire_id(n): value["lon_lat"] for n, value in nodes.items()}
        distance = sum(e["distance_m"] for e in route_edges)
        check(f"wire_route_{index}_geometry_and_totals", route["node_ids"] == expected_nodes and all(arc["direction"] == "forward" for arc in route["arcs"]) and route["geometry"] == {"type": "LineString", "coordinates": [node_coordinates[n] for n in expected_nodes]} and math.isclose(route["total_distance_m"], distance) and math.isclose(route["estimated_duration_s"], distance / request["accessibility_profile"]["travel_speed_mps"]) and math.isclose(route["cost_m_equivalent"], sum(cost(e) for e in route_edges)) and math.isclose(sum(i["distance_m"] for i in route["instructions"]), distance))
    count = {}
    for edge in graph["edges"]:
        for reason in reasons(edge, graph["profiles"]["wheelchair"], ("ramp-cross", "lower-west")):
            count[reason] = count.get(reason, 0) + 1
    check("wire_no_route_honesty_and_counts", missing["status"] == "no_route" and missing["primary"] is None and missing["alternatives"] == [] and "geometry" not in missing and "total_distance_m" not in missing and missing["excluded_edge_counts"] == count)

    tokens = (ROOT / "docs" / "FRONTEND_DESIGN.md").read_text()
    contrast_pairs = [
        ("body", "#163C3A", "#FAF9F6", 4.5),
        ("muted", "#4C6360", "#FAF9F6", 4.5),
        ("primary_button", "#FFFFFF", "#0B625A", 4.5),
        ("sage_text", "#163C3A", "#DCE9DF", 4.5),
        ("accent_text", "#285F8F", "#FAF9F6", 4.5),
        ("warning", "#7A4B00", "#FFF1CC", 4.5),
        ("danger", "#A82D35", "#FFF0F0", 4.5),
        ("control_boundary", "#718B85", "#FFFFFF", 3.0),
    ]
    for name, fg, bg, minimum in contrast_pairs:
        light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
        ratio = (light + 0.05) / (dark + 0.05)
        check(f"contrast_{name}_{ratio:.2f}:1", fg in tokens and bg in tokens and ratio >= minimum)
    print(f"\n{len(CHECKS)} design checks passed; {len(cases)} exhaustive fixture scenarios.")
    print("Production algorithm, API, database, UI, and ML tests: UNRUN (later phases).")


if __name__ == "__main__":
    try:
        validate()
    except (AssertionError, ValueError, KeyError, OSError, IndexError) as error:
        print(f"FAIL after {len(CHECKS)} checks: {error}", file=sys.stderr)
        sys.exit(1)
