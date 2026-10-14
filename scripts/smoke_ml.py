#!/usr/bin/env python3
"""Read-only optional ML status smoke; never creates accounts, jobs or predictions."""

import json
import os
import urllib.request

port = os.environ.get("API_PORT", "8000")
with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/ml/status", timeout=5) as response:
    result = json.load(response)
assert isinstance(result["available"], bool)
if result["available"]:
    assert result["reason"] == "READY" and result["model_version_id"] and result["model_name"]
else:
    assert result["reason"] in {
        "DISABLED",
        "EVALUATED_MODEL_MISSING",
        "TEST_FIXTURE_NOT_PRODUCT_MODEL",
        "ML_RUNTIME_MISSING",
        "ML_WORKER_NOT_CONFIGURED",
        "MODEL_ASSETS_INVALID",
    }
    assert result["model_version_id"] is None
print(
    "PASS optional ML status:",
    result["reason"],
    "(manual reporting/routing remain independent)",
)
