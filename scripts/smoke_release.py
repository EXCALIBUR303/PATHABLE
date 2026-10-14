#!/usr/bin/env python3
"""Strict-certificate HTTPS release checks, including actual bounded SSE through Nginx."""

import argparse
import math
import ssl
from pathlib import Path

import httpx
from release_support import ROOT, configuration


def client_for(config):
    values = config[1]
    context = ssl.create_default_context(cafile=values.get("RELEASE_CA_FILE") or None)
    return httpx.Client(
        base_url=values["APP_ORIGIN"] + "/api/v1", verify=context, timeout=20, trust_env=False
    )


def check(config):
    with client_for(config) as client:
        ready = client.get("/health/ready")
        assert ready.status_code == 200 and ready.json() == {"status": "ready"}
        for name in (
            "strict-transport-security",
            "content-security-policy",
            "referrer-policy",
            "permissions-policy",
        ):
            assert ready.headers.get(name)
        assert "frame-ancestors 'none'" in ready.headers["content-security-policy"]
        assert ready.headers["x-frame-options"] == "DENY"
        session = client.get("/auth/session")
        cookie = session.headers["set-cookie"]
        assert "__Host-pathable_session=" in cookie and "Secure" in cookie and "HttpOnly" in cookie
        assert "Domain=" not in cookie and "SameSite=lax" in cookie
        assert session.headers["cache-control"] == "no-store"
        campus = client.get("/campuses").json()["items"][0]
        assert campus["data_origin"] == "synthetic_demo"
        locations = client.get("/locations", params={"campus_id": campus["id"]}).json()["items"]
        nodes = [entry["node_id"] for place in locations for entry in place["access_points"]]
        payload = {
            "campus_id": campus["id"],
            "source_id": nodes[0],
            "destination_id": nodes[1],
            "accessibility_profile": {
                "avoid_stairs": True,
                "max_slope_pct": 8,
                "min_width_m": 0.9,
                "excluded_surfaces": ["uneven", "gravel"],
                "unknown_policy": "exclude",
                "travel_speed_mps": 1,
            },
            "alternatives_limit": 0,
        }
        results = []
        for algorithm in ("dijkstra", "astar"):
            result = client.post(
                "/routes/calculate", json={**payload, "selected_algorithm": algorithm}
            )
            assert result.status_code == 200, result.text
            value = result.json()
            assert value["status"] == "found" and value["graph_version"]
            results.append(value["primary"]["cost_m_equivalent"])
        assert math.isclose(*results, rel_tol=1e-9, abs_tol=1e-6)
        with client.stream("GET", f"/campuses/{campus['id']}/events", timeout=5) as stream:
            assert stream.status_code == 200
            assert stream.headers["content-type"].startswith("text/event-stream")
            lines = []
            for line in stream.iter_lines():
                lines.append(line)
                if not line:
                    break
            assert len("\n".join(lines)) < 65536 and "event: graph.reset" in lines
        assert client.get("/ml/status").json()["reason"] == "DISABLED"
        html = client.get(config[1]["APP_ORIGIN"] + "/navigate")
        assert html.status_code == 200 and '<div id="root">' in html.text
        assert "/assets/" in html.text and "/src/main.tsx" not in html.text
    print(
        "PASS strict HTTPS release: production UI, headers/cookie, DB, matching route algorithms, unbuffered SSE and disabled ML"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".local/release/config.env")
    args = parser.parse_args()
    check(configuration(args.env))


if __name__ == "__main__":
    main()
