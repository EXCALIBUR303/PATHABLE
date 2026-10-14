"""Reproduce transient pre-exec process identity without signaling any real process."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dev  # noqa: E402
import web  # noqa: E402


@pytest.mark.parametrize(
    "helper,command",
    [
        (dev, "python -m uvicorn app.main:app"),
        (web, "node /checkout/frontend/node_modules/vite/bin/vite.js"),
    ],
)
def test_start_waits_for_exec_identity_and_can_be_recognized_again(
    helper, command, tmp_path, monkeypatch
):
    monkeypatch.setattr(helper, "LOCAL", tmp_path)
    monkeypatch.setattr(helper, "STATE", tmp_path / "process.json")
    monkeypatch.setattr(helper, "PORT", 0)
    stable = "Tue Oct 13 15:17:31 2026 " + command
    samples = iter(["Tue Oct 13 15:17:31 2026 [child]", stable, stable, stable])
    monkeypatch.setattr(helper, "identity", lambda pid: next(samples))
    monkeypatch.setattr(
        helper.subprocess, "Popen", lambda *a, **k: SimpleNamespace(pid=42, poll=lambda: None)
    )
    monkeypatch.setattr(helper.time, "sleep", lambda delay: None)
    monkeypatch.setattr(helper, "ready", lambda: True)
    helper.start()
    assert helper.owned()["identity"] == stable
    helper.start()  # Repeat startup must recognize the same child rather than refuse it.


@pytest.mark.parametrize("helper", [dev, web])
def test_mismatched_process_is_never_signaled(helper, tmp_path, monkeypatch):
    state = tmp_path / "process.json"
    state.write_text(json.dumps({"pid": 42, "identity": "previous child", "port": 0}))
    monkeypatch.setattr(helper, "STATE", state)
    monkeypatch.setattr(helper, "identity", lambda pid: "unrelated process")
    monkeypatch.setattr(
        helper.os, "kill", lambda *args: pytest.fail("Never signal a mismatched process")
    )
    with pytest.raises(SystemExit, match="another process"):
        helper.stop()
    assert json.loads(state.read_text())["identity"] == "previous child"
