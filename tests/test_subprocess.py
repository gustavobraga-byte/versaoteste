"""Tests for the FakeRunner and skill clone logic."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from pesquisai.config import SETTINGS
from pesquisai.skills import Skill, _clone_or_pull, list_installed
from pesquisai.utils.subprocess import FakeRunner


# ── FakeRunner ──────────────────────────────────────────────────────


class TestFakeRunner:
    def test_records_calls(self):
        r = FakeRunner()
        r.run(["ls", "-la"])
        assert r.calls == [["ls", "-la"]]

    def test_returns_default_response(self):
        r = FakeRunner()
        result = r.run(["anything"])
        assert result.returncode == 0
        assert result.stdout == ""

    def test_returns_specific_response(self):
        r = FakeRunner()
        r.responses[("which", "opencode")] = subprocess.CompletedProcess(
            args=["which", "opencode"], returncode=0, stdout="/usr/bin/opencode"
        )
        out = r.run(["which", "opencode"])
        assert out.returncode == 0
        assert out.stdout == "/usr/bin/opencode"

    def test_popen_uses_safe_binary(self):
        r = FakeRunner()
        proc = r.popen(["rm", "-rf", "/"])
        # The real Popen runs /bin/true; it should be terminated on
        # __del__ or via poll() returning success.
        proc.wait(timeout=2)
        assert proc.returncode == 0
        assert r.popen_calls == [["rm", "-rf", "/"]]


# ── Skill clone helpers ─────────────────────────────────────────────


class TestCloneOrPull:
    def test_pulls_when_dest_exists(self, tmp_path: Path, monkeypatch):
        dest = tmp_path / "skill_test"
        dest.mkdir()
        (dest / ".git").mkdir()

        runner = FakeRunner()  # default returncode=0 -> pull "succeeds"
        skill = Skill("https://example.com/repo.git", "test")
        # Override clone_dest to point at our tmp dir.
        with patch.object(Skill, "clone_dest", new=property(lambda self: str(dest))):
            result = _clone_or_pull(skill, runner=runner)
        assert result is True
        # The first call to ``run`` must be a ``git pull`` because
        # the destination directory already exists.
        assert runner.calls[0][:3] == ["git", "-C", str(dest)]
        assert "pull" in runner.calls[0]

    def test_falls_back_to_clone_when_pull_fails(self, tmp_path: Path, monkeypatch):
        dest = tmp_path / "skill_test"
        dest.mkdir()
        (dest / ".git").mkdir()

        # Queue: first response = pull failure, second response = clone success.
        import subprocess as _sp
        runner = FakeRunner()
        runner.queued_responses.append(
            _sp.CompletedProcess(args=["git", "pull"], returncode=1, stdout="", stderr="conflict")
        )
        runner.queued_responses.append(
            _sp.CompletedProcess(args=["git", "clone"], returncode=0, stdout="", stderr="")
        )
        skill = Skill("https://example.com/repo.git", "test")
        with patch.object(Skill, "clone_dest", new=property(lambda self: str(dest))):
            result = _clone_or_pull(skill, runner=runner)
        assert result is True
        # First call: pull (failed). Second call: clone (succeeded).
        assert "pull" in runner.calls[0]
        assert "clone" in runner.calls[1]


# ── list_installed ──────────────────────────────────────────────────


class TestListInstalled:
    def test_returns_empty_for_missing_dir(self, tmp_path: Path, monkeypatch):
        # Point the helper at a tmp dir that does not exist.
        import os as _os
        target = tmp_path / "no-such-dir"
        assert not target.exists()
        monkeypatch.setattr(
            "pesquisai.config.SETTINGS", type(SETTINGS)()  # fresh instance
        )
        # Override the skills_dir on the *new* SETTINGS via model_copy.
        from pesquisai.config import SETTINGS as _real
        new_settings = _real.model_copy(update={"skills_dir": target})
        monkeypatch.setattr("pesquisai.config.SETTINGS", new_settings)
        # The ``list_installed`` function reads from the module-level
        # SETTINGS in ``pesquisai.skills``, so patch that one too.
        monkeypatch.setattr("pesquisai.skills.SETTINGS", new_settings)
        assert list_installed() == []
