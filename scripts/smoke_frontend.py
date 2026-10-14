#!/usr/bin/env python3
"""Functional frontend compilation and same-origin API-proxy smoke checks."""

import json
import os
import urllib.request

from dev import ROOT

base = f"http://127.0.0.1:{int(os.environ.get('FRONTEND_PORT', '5173'))}"


def fetch(path):
    with urllib.request.urlopen(base + path, timeout=10) as response:
        assert response.status == 200
        return response.read().decode()


assert ROOT.is_dir()
assert "PathAble" in fetch("/")
assert "createRoot" in fetch("/src/main.tsx")
assert json.loads(fetch("/api/v1/health/ready")) == {"status": "ready"}
campuses = json.loads(fetch("/api/v1/campuses"))["items"]
campus = next(item for item in campuses if item["data_origin"] == "synthetic_demo")
graph = json.loads(fetch(f"/api/v1/campuses/{campus['id']}/graph"))
assert graph["features"] and graph["data_origin"] == "synthetic_demo"
print(
    "PASS frontend smoke: HTML, compiled React entry, same-origin proxy and real synthetic graph"
)

request = urllib.request.Request(
    base + f"/api/v1/campuses/{campus['id']}/events",
    headers={"Accept": "text/event-stream", "Last-Event-ID": graph["graph_version"]},
)
with urllib.request.urlopen(request, timeout=5) as response:
    assert response.status == 200
    assert response.readline(65537).strip() == b": heartbeat"
print("PASS frontend SSE proxy: immediate keepalive for a current retained cursor")
