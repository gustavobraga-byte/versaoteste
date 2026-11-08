"""Testes da variante web (v0.7.11-web).

Cobrem o proxy que publica a SPA do OpenCode com autenticação injetada e o
tema do UFVAI, e a troca do iframe do ttyd pela URL do proxy no wrapper.
"""
from __future__ import annotations

import json
from pathlib import Path

from pesquisai import ocweb
from pesquisai.launch_app_responsive_v041 import create_wrapper_html


def test_service_info_reads_url_and_password(monkeypatch, tmp_path):
    path = tmp_path / "service.json"
    path.write_text(
        json.dumps({"url": "http://127.0.0.1:45999", "password": "segredo"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ocweb, "service_file", lambda: path)
    assert ocweb.service_info() == ("127.0.0.1", 45999, "segredo")


def test_service_info_missing_file(monkeypatch):
    monkeypatch.setattr(ocweb, "service_file", lambda: Path("/nao/existe.json"))
    host, port, password = ocweb.service_info()
    assert host == "127.0.0.1"
    assert port == 0
    assert password == ""


def test_basic_auth_header():
    import base64

    raw = base64.b64decode(ocweb._basic("abc").split(" ", 1)[1]).decode()
    assert raw == "opencode:abc"


def test_inject_html_adds_theme_badge_and_title():
    html = (
        b"<html><head><title data-sm>OpenCode</title></head>"
        b"<body><div id='root'></div></body></html>"
    )
    out = ocweb._inject_html(html).decode("utf-8")
    assert "UFVAI · OpenCode" in out
    assert "ufvai-ocweb-theme" in out
    assert "ufvai-oc-badge" in out
    assert out.index("ufvai-ocweb-theme") < out.index("</head>")


def test_inject_html_adds_theme_once():
    out = ocweb._inject_html(b"<html><head></head><body></body></html>")
    assert out.count(b"ufvai-ocweb-theme") == 1


def test_ready_false_without_service(monkeypatch):
    monkeypatch.setattr(ocweb, "service_file", lambda: Path("/nao/existe.json"))
    assert ocweb.ready(65530, timeout=0.05) is False


def test_status_without_server(monkeypatch):
    monkeypatch.setattr(ocweb, "service_file", lambda: Path("/nao/existe.json"))
    st = ocweb.status()
    assert st["running"] is False
    assert st["upstream_ready"] is False


def test_wrapper_web_mode_uses_ocweb_ready():
    html = create_wrapper_html(
        "http://localhost:8002", "https://drive.google.com/x", web_mode=True
    )
    assert "/api/ocweb_ready" in html
    assert "{__READY_URL__}" not in html
    assert "http://localhost:8002" in html


def test_wrapper_default_keeps_ttyd_ready():
    html = create_wrapper_html("http://localhost:8000", "https://drive.google.com/x")
    assert "/api/ttyd_ready" in html
    assert "{__READY_URL__}" not in html
