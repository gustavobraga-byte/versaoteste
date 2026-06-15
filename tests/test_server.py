"""Tests for the HTTP wrapper server (Section 4.2 of the analysis).

These tests use the real :class:`HTTPServer` bound to an ephemeral
port, talking to it through ``urllib`` - the same code path the
browser will use, but isolated from the Colab-specific globals.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from pesquisai.launch.server import (
    HandlerState,
    _runtime,
    _route_backup,
    _route_get_apikey,
    _route_post_apikey,
    _route_run_terminal,
    _route_restore,
    make_handler,
    set_drive_info,
)
from pesquisai.utils.subprocess import FakeRunner


def _free_port() -> int:
    """Ask the kernel for a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server(tmp_path: Path, monkeypatch):
    """Start an HTTPServer on a free port and tear it down after the test."""
    # Make sure the server uses the tmp_path as the Drive base. The
    # patch must be in place before the server's handlers resolve
    # the path, so we apply it before HTTPServer starts.
    monkeypatch.setattr(
        "pesquisai.launch.server._resolve_drive_base", lambda: tmp_path
    )
    monkeypatch.setattr(
        "pesquisai.launch.server._runtime.opencode_bin", None
    )
    monkeypatch.setattr(
        "pesquisai.launch.server._runtime.env", {"PATH": os.environ.get("PATH", "")}
    )

    port = _free_port()
    handler_cls = make_handler()
    server = HTTPServer(("127.0.0.1", port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    (tmp_path / "backups").mkdir(exist_ok=True)
    set_drive_info(str(tmp_path), "https://example.test/drive")
    try:
        yield port, str(tmp_path)
    finally:
        server.shutdown()
        server.server_close()


def _http_get(port: int, path: str, data: dict | None = None) -> tuple[int, dict]:
    url = f"http://127.0.0.1:{port}{path}"
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req = Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    else:
        req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - test surface
        # HTTPError carries the actual response; use it when present.
        code = getattr(exc, "code", 0)
        if hasattr(exc, "read"):
            try:
                return code, json.loads(exc.read().decode("utf-8"))
            except Exception:  # noqa: BLE001
                pass
        return code, {"error": str(exc)}


# ── handler unit tests ──────────────────────────────────────────────


class TestValidateCommandInRunTerminal:
    """Section 2.1: ``/api/run_terminal`` must validate the command."""

    def test_rejects_injection(self, tmp_path: Path):
        state = HandlerState.__new__(HandlerState)  # bypass __init__
        state.json = lambda code, payload: setattr(state, "out", (code, payload))
        state.body = {"command": "opencode; rm -rf /", "no_fallback": True}
        state.qs = {}
        state.runtime = _runtime
        _route_run_terminal(state, state.body, state.qs)
        code, payload = state.out
        assert code == 400
        assert "permitid" in payload["error"].lower()

    def test_rejects_unknown_binary(self, tmp_path: Path):
        state = HandlerState.__new__(HandlerState)
        state.json = lambda code, payload: setattr(state, "out", (code, payload))
        state.body = {"command": "python -c 'print(1)'", "no_fallback": True}
        state.qs = {}
        state.runtime = _runtime
        _route_run_terminal(state, state.body, state.qs)
        code, payload = state.out
        assert code == 400
        assert "permitido" in payload["error"].lower()


# ── live server tests (health, backups) ─────────────────────────────


class TestHealthEndpoint:
    def test_health_responds_ok(self, live_server):
        port, _ = live_server
        code, body = _http_get(port, "/api/health")
        assert code == 200
        assert body["status"] == "ok"
        assert "uptime_s" in body


class TestBackupRouting:
    def test_backup_rejects_when_no_session(self, live_server):
        port, _ = live_server
        # No opencode configured, and no session_id in the body.
        code, body = _http_get(port, "/api/backup", data={})
        # 503 because opencode bin is not set in tests.
        assert code in (400, 503)
        assert "error" in body

    def test_restore_blocks_traversal(self, live_server):
        port, _ = live_server
        code, body = _http_get(port, "/api/restore", data={"file": "../../etc/passwd"})
        # safe_backup_path returns None -> 404
        assert code == 404
        assert "nao encontrado" in body["error"] or "error" in body
