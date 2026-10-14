"""Deterministic pure-engine benchmark; synthetic distances are not survey evidence."""

import json
import math
import os
import platform
import statistics
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.routing import Edge, GraphSnapshot, Node, Profile, calculate
from app.routing.engine import chord_distance


def graph():
    width, height = 40, 50
    nodes = tuple(
        Node(str(y * width + x), (x * 0.00004, y * 0.00004))
        for y in range(height)
        for x in range(width)
    )
    now = datetime.now(UTC)
    pairs = []
    for y in range(height):
        for x in range(width):
            node = y * width + x
            if x + 1 < width:
                pairs.append((node, node + 1))
            if y + 1 < height:
                pairs.append((node, node + width))
    for y in range(height - 1):
        for x in range(width - 1):
            if len(pairs) < 5000:
                node = y * width + x
                pairs.append((node, node + width + 1))
    edges = tuple(
        Edge(
            id=f"edge-{index}",
            source_id=nodes[a].id,
            target_id=nodes[b].id,
            geometry=(nodes[a].point, nodes[b].point),
            distance_m=chord_distance(nodes[a].point, nodes[b].point) * 1.002,
            accessibility="accessible",
            verification="verified",
            expires_at=now + timedelta(days=30),
            width_m=1.2,
            slope_pct=0,
            surface="smooth",
            has_stairs=False,
            has_ramp=False,
        )
        for index, (a, b) in enumerate(pairs)
    )
    assert len(nodes) == 2000 and len(edges) == 5000
    return GraphSnapshot(nodes, edges, now)


def main():
    snapshot = graph()
    profile = Profile(True, 8, 0.9, ("uneven", "gravel"), "exclude", 1)
    cases = [
        ("0", "1999"),
        ("39", "1960"),
        ("400", "1599"),
        ("19", "1979"),
        ("800", "1199"),
    ]
    runs = []
    reference = {}
    for alternatives in (0, 2):
        for algorithm in ("dijkstra", "astar"):
            for source, destination in cases:
                started = time.perf_counter()
                result = calculate(
                    snapshot, source, destination, profile, algorithm, alternatives
                )
                elapsed = (time.perf_counter() - started) * 1000
                assert result.status == "found" and result.primary is not None
                key = (source, destination)
                cost = result.primary.cost_m_equivalent
                if key in reference:
                    assert math.isclose(
                        cost, reference[key], rel_tol=1e-9, abs_tol=1e-6
                    )
                reference[key] = cost
                runs.append(
                    {
                        "algorithm": algorithm,
                        "alternatives_requested": alternatives,
                        "source": source,
                        "destination": destination,
                        "wall_elapsed_ms": elapsed,
                        "cost_m_equivalent": cost,
                        "alternatives_returned": len(result.alternatives),
                        "alternatives_exhaustive": result.alternatives_exhaustive,
                        **result.to_dict()["stats"],
                    }
                )
    summary = []
    for alternatives in (0, 2):
        for algorithm in ("dijkstra", "astar"):
            group = [
                run
                for run in runs
                if run["algorithm"] == algorithm
                and run["alternatives_requested"] == alternatives
            ]
            values = sorted(run["wall_elapsed_ms"] for run in group)
            summary.append(
                {
                    "algorithm": algorithm,
                    "alternatives_requested": alternatives,
                    "samples": len(values),
                    "median_ms": statistics.median(values),
                    "p95_nearest_rank_ms": values[math.ceil(0.95 * len(values)) - 1],
                    "incomplete_alternative_searches": sum(
                        not run["alternatives_exhaustive"] for run in group
                    ),
                }
            )
    output = {
        "measured_at": datetime.now(UTC).isoformat(),
        "scope": "Synthetic pure-engine workload; includes graph validation/filter/search, excludes HTTP/DB",
        "nodes": 2000,
        "physical_edges": 5000,
        "directed_arcs": 10000,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "summary": summary,
        "runs": runs,
    }
    destination = ROOT / ".local/routing-benchmark.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {"nodes": 2000, "physical_edges": 5000, "summary": summary}, indent=2
        )
    )


if __name__ == "__main__":
    main()
