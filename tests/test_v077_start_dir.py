"""Diretório inicial do UFVAI = pasta PesquisAI no Drive (v0.7.7, sem bump).

Relato do autor (27/10/2026): "a versão 0.7.7 quando inicia está no root, deve
iniciar na pasta PesquisAI no drive".

Causa confirmada no runtime: o serviço de background do OpenCode
(``opencode serve --service``) nascia com cwd ``/root`` (kernel do Colab) e as
sessões criadas sem ``location`` herdavam esse diretório — o agente executava
ferramentas em ``/root`` mesmo com o ``cd`` no comando do ttyd.

Cobertura:
  * ``launch_app._project_dir()`` nunca devolve a raiz;
  * ``_spawn_ttyd`` passa ``cwd`` explícito ao ttyd;
  * ``preflight_ufvai_session_info`` cria a sessão com ``location`` explícita;
  * ``ensure_service_project_dir`` é fast-path quando o serviço já está certo.

    pytest -o addopts="" tests/test_v077_start_dir.py -v
"""
from __future__ import annotations

import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pesquisai import constants, launch_app as la, run_fast as rf  # noqa: E402


def test_project_dir_prefere_drive(tmp_path, monkeypatch):
    drive = tmp_path / "My Drive" / "PesquisAI"
    drive.mkdir(parents=True)
    home = tmp_path / "home"
    (home / "PesquisAI").mkdir(parents=True)
    monkeypatch.setattr(constants, "DRIVE_PATH", str(drive))
    monkeypatch.setenv("HOME", str(home))

    assert la._workspace_dir() == str(drive)


def test_project_dir_cai_para_home_pesquisai(tmp_path, monkeypatch):
    """Sem Drive (offline/.deb), usa ~/PesquisAI — nunca o cwd do processo."""
    home = tmp_path / "home"
    (home / "PesquisAI").mkdir(parents=True)
    monkeypatch.setattr(constants, "DRIVE_PATH", str(tmp_path / "sem-drive"))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)

    assert la._workspace_dir() == str(home / "PesquisAI")


def test_spawn_ttyd_passa_cwd_do_projeto(tmp_path, monkeypatch):
    drive = tmp_path / "My Drive" / "PesquisAI"
    drive.mkdir(parents=True)
    monkeypatch.setattr(constants, "DRIVE_PATH", str(drive))
    import io
    monkeypatch.setattr(la, "_ttyd_log_file", lambda: io.StringIO())

    captured: dict = {}

    class _FakeProc:
        pid = 1234

        def poll(self):  # pragma: no cover - só contrato
            return None

    def _fake_popen(args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)
        return _FakeProc()

    monkeypatch.setattr(la.subprocess, "Popen", _fake_popen)
    la._spawn_ttyd(["ttyd", "-p", "8000"], {})

    assert captured["cwd"] == str(drive)
    assert captured.get("start_new_session") is True


def test_preflight_cria_sessao_com_location(tmp_path, monkeypatch):
    projeto = tmp_path / "PesquisAI"
    projeto.mkdir()
    monkeypatch.setattr(rf, "find_opencode", lambda: "/usr/bin/opencode")

    seen: dict = {}

    def _fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return types.SimpleNamespace(
            stdout='{"data": {"id": "ses_teste123", "agent": "UFVAI"}}',
            stderr="",
            returncode=0,
        )

    monkeypatch.setattr(rf.subprocess, "run", _fake_run)
    sid, created = rf.preflight_ufvai_session_info(cwd=str(projeto), timeout_s=2)

    assert sid == "ses_teste123" and created is True
    payload = json.loads(seen["cmd"][seen["cmd"].index("--data") + 1])
    assert payload["location"] == {"directory": os.path.abspath(str(projeto))}
    assert payload["agent"] == "UFVAI"


def test_ensure_service_fast_path(tmp_path, monkeypatch):
    """Serviço já no projeto: não para nem sobe nada."""
    projeto = tmp_path / "PesquisAI"
    projeto.mkdir()
    monkeypatch.setattr(rf, "_service_cwd", lambda: str(projeto))

    chamadas: list = []
    monkeypatch.setattr(
        rf.subprocess, "run",
        lambda *a, **k: chamadas.append(a) or types.SimpleNamespace(stdout="", returncode=0),
    )
    monkeypatch.setattr(
        rf.subprocess, "Popen",
        lambda *a, **k: chamadas.append(("Popen", a)),
    )

    assert rf.ensure_service_project_dir(str(projeto)) is True
    assert chamadas == []
