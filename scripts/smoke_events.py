"""Read-only SSE readiness: consume a real reset frame and close the stream."""

import json
import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
base = f"http://127.0.0.1:{int(os.environ.get('API_PORT', '8000'))}/api/v1"
with urllib.request.urlopen(base + "/campuses", timeout=5) as response:
    campus = json.load(response)["items"][0]
request = urllib.request.Request(
    base + f"/campuses/{campus['id']}/events", headers={"Accept": "text/event-stream"}
)
with urllib.request.urlopen(request, timeout=5) as response:
    assert (
        response.status == 200
        and "text/event-stream" in response.headers["Content-Type"]
    )
    lines = []
    size = 0
    while True:
        line = response.readline(65537)
        size += len(line)
        assert line and size <= 65536
        if line in (b"\n", b"\r\n"):
            break
        lines.append(line.decode().strip())
    fields = dict(line.split(": ", 1) for line in lines if ": " in line)
    data = json.loads(fields["data"])
    assert fields["event"] == "graph.reset" and fields["id"] == data["graph_version"]
    assert data["campus_id"] == campus["id"] and data["changed_edge_ids"] == []
    assert set(data) == {
        "campus_id",
        "graph_version",
        "changed_edge_ids",
        "changes_truncated",
        "reason",
        "occurred_at",
    }
print(
    "PASS live SSE: bounded public reset frame, campus/revision identity and no private payload"
)
