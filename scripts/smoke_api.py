#!/usr/bin/env python3
"""Read-only functional checks against a real running API; no preview links."""

import json
import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

base = f"http://127.0.0.1:{int(os.environ.get('API_PORT', '8000'))}/api/v1"


def get(path):
    with urllib.request.urlopen(base + path, timeout=10) as r:
        assert r.status == 200
        return json.load(r)


assert get("/health/ready") == {"status": "ready"}
campuses = get("/campuses")["items"]
assert campuses
campus = next(c for c in campuses if c["data_origin"] == "synthetic_demo")
graph = get(f"/campuses/{campus['id']}/graph")
edges = [f for f in graph["features"] if f["geometry"]["type"] == "LineString"]
assert edges and all(e["properties"]["distance_m"] > 0 for e in edges)
assert any(e["properties"]["accessibility"] == "unknown" for e in edges)
locations = get(f"/locations?campus_id={campus['id']}")["items"]
assert locations and all(location["access_points"] for location in locations)
assert get("/auth/session")["csrf_token"]
print(
    f"PASS live API smoke: readiness, synthetic campus, {len(edges)} measured edges, access points, anonymous session"
)
