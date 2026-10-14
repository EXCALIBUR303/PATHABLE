"""Read-only live routing checks against the retained development campus."""

import json
import math
import os
import urllib.request

from dev import ROOT

BASE = f"http://127.0.0.1:{int(os.environ.get('API_PORT', '8000'))}/api/v1"


def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        assert response.status == 200
        return json.load(response)


assert ROOT.is_dir()
campus = next(
    item
    for item in call("/campuses")["items"]
    if item["data_origin"] == "synthetic_demo"
)
locations = call(f"/locations?campus_id={campus['id']}&limit=100")["items"]
entrances = [
    entry["node_id"] for place in locations for entry in place["access_points"]
]
assert len(entrances) >= 2
payload = {
    "campus_id": campus["id"],
    "source_id": entrances[0],
    "destination_id": entrances[1],
    "accessibility_profile": {
        "avoid_stairs": True,
        "max_slope_pct": 8,
        "min_width_m": 0.9,
        "excluded_surfaces": ["uneven", "gravel"],
        "unknown_policy": "exclude",
        "travel_speed_mps": 1,
    },
    "alternatives_limit": 2,
}
results = []
for algorithm in ("dijkstra", "astar"):
    result = call("/routes/calculate", {**payload, "selected_algorithm": algorithm})
    assert result["algorithm"] == algorithm
    assert result["status"] in {"found", "no_route"}
    assert result["data_origin"] == "synthetic_demo"
    assert len(result["profile_fingerprint"]) == 64
    assert result["policy_version"] == "accessibility-v1"
    assert result["cost_model_version"] == "walking-effort-v1"
    if result["status"] == "found":
        for route in (result["primary"], *result["alternatives"]):
            assert route["node_ids"][0] == entrances[0]
            assert route["node_ids"][-1] == entrances[1]
            assert route["cost_m_equivalent"] >= route["total_distance_m"]
            assert route["estimated_duration_s"] == route["total_distance_m"]
            assert route["verification"]["uncertain_distance_m"] == 0
            assert math.isclose(
                sum(item["distance_m"] for item in route["instructions"]),
                route["total_distance_m"],
                abs_tol=1e-6,
            )
    else:
        assert result["primary"] is None and result["alternatives"] == []
    results.append(result)
assert results[0]["status"] == results[1]["status"]
assert results[0]["graph_version"] == results[1]["graph_version"]
if results[0]["status"] == "found":
    assert math.isclose(
        results[0]["primary"]["cost_m_equivalent"],
        results[1]["primary"]["cost_m_equivalent"],
        rel_tol=1e-9,
        abs_tol=1e-6,
    )
print(
    "PASS live routing: public Dijkstra/A*, matching results, explicit constraints, "
    "profile/snapshot identity and reconciled route totals"
)
