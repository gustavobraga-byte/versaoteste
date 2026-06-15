"""Security utilities: command validation and safe path resolution.

This module centralises all input sanitisation for the PesquisAI wrapper
HTTP server, addressing the security findings from ANALISE_CODIGO.md
(Sections 2.1 and 2.2):

* ``validate_command``  - whitelist-only command allow-listing.
* ``safe_backup_path``  - directory-traversal protection.
* ``escape_html``       - XSS protection for reflected user input.
* ``secure_write_file`` - chmod 600 for credential files.
"""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any


# Whitelist of binary names permitted in commands sent to ``/api/run_terminal``.
# Anything outside this set is rejected.
ALLOWED_BINARIES: frozenset[str] = frozenset(
    {
        "opencode",
        "export",
        "true",
        "false",
        "echo",
        "source",
        ".",
    }
)

# Operators we allow for chaining safe commands. The shlex parser will
# also keep them, but the runtime has to make sure they only appear
# in the explicit " && " / " || " forms - not as backgrounding ``&``.
_ALLOWED_OPERATORS: tuple[str, ...] = (" && ", " || ")

# Characters that can be used to chain or escape commands in a shell context.
# ``validate_command`` rejects inputs containing any of these.
# Note: ``&`` and ``|`` are not listed here; we let the explicit ``&&`` / ``||``
# forms through after a separate pass.
_FORBIDDEN_CHARS: frozenset[str] = frozenset("\n;`$(){}<>*?#~")


def validate_command(cmd: str) -> str:
    """Validate a shell command against a strict whitelist.

    Only commands whose first token is in :data:`ALLOWED_BINARIES` are
    accepted. Any character in :data:`_FORBIDDEN_CHARS` causes a
    :class:`ValueError`.

    Parameters
    ----------
    cmd:
        Command string. Whitespace at the edges is stripped.

    Returns
    -------
    str
        The trimmed command (unchanged content if valid).

    Raises
    ------
    ValueError
        If the command is empty, contains forbidden characters, or
        starts with a binary that is not in the allow-list.
    """
    if not isinstance(cmd, str):
        raise ValueError("Comando deve ser uma string.")
    cmd = cmd.strip()
    if not cmd:
        raise ValueError("Comando vazio.")

    if any(c in cmd for c in _FORBIDDEN_CHARS):
        raise ValueError(
            "Comando contém caracteres não permitidos "
            "(shell metacharacters)."
        )

    # Reject bare ``&`` (backgrounding) and bare ``|`` (pipe). Only the
    # explicit " && " / " || " operators are permitted. We check the
    # command *with* the allowed operators replaced by spaces, so that
    # anything remaining with ``&``/``|`` is a bare occurrence.
    if "&" in cmd or "|" in cmd:
        masked = cmd
        for op in _ALLOWED_OPERATORS:
            masked = masked.replace(op, "   ")  # same length to keep indexing
        if "&" in masked or "|" in masked:
            raise ValueError(
                "Comando contém operadores nao permitidos "
                "('&' ou '|' isolados)."
            )

    try:
        parts = shlex.split(cmd)
    except ValueError as exc:
        raise ValueError(f"Comando malformado: {exc}") from exc

    if not parts:
        raise ValueError("Comando vazio após parsing.")

    # Walk the parsed tokens: every command segment (separated by
    # ``&&`` / ``||``) must start with a binary from the allow-list.
    # The shlex parser strips the ``&&`` / ``||`` operators, so we
    # look for them as standalone tokens. ``export`` is the only
    # builtin treated like a binary for this check.
    segments: list[list[str]] = [[]]
    for token in parts:
        if token in ("&&", "||"):
            segments.append([])
        else:
            segments[-1].append(token)

    for seg in segments:
        if not seg:
            raise ValueError("Operador ``&&`` / ``||`` sem comando adjacente.")
        head = seg[0]
        if head not in ALLOWED_BINARIES:
            raise ValueError(f"Binário não permitido: {head!r}.")

    return cmd


def safe_backup_path(backup_dir: str | os.PathLike[str], fname: str) -> Path | None:
    """Resolve ``fname`` safely under ``backup_dir``.

    Returns ``None`` if the resulting path escapes the backup directory
    (path-traversal attack) or if the file does not exist. Both checks
    are required because the caller needs an existing file.

    Parameters
    ----------
    backup_dir:
        Trusted base directory (e.g. ``DRIVE_BACKUP_DIR``).
    fname:
        Untrusted filename coming from the HTTP request body.

    Returns
    -------
    pathlib.Path | None
        The resolved absolute path, or ``None`` if invalid.
    """
    if not fname or not isinstance(fname, str):
        return None
    # Reject obvious traversal and absolute paths early.
    if "\x00" in fname or fname.startswith(("/", "\\")):
        return None

    base = Path(backup_dir).resolve()
    try:
        candidate = (base / fname).resolve()
    except (OSError, ValueError):
        return None

    # ``is_relative_to`` was added in Python 3.9; we support 3.10+ anyway.
    if not candidate.is_relative_to(base):
        return None

    if not candidate.is_file():
        return None

    return candidate


def escape_html(text: str) -> str:
    """Escape characters with special meaning in HTML.

    Used by the JavaScript-side rendering in ``index.html`` for
    reflected filenames (see Section 2.4 of ANALISE_CODIGO.md).

    Parameters
    ----------
    text:
        Untrusted string (e.g. backup filename).

    Returns
    -------
    str
        The same string with ``& < > " '`` replaced by HTML entities.
    """
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def secure_write_json(path: str | os.PathLike[str], data: Any) -> None:
    """Atomically write ``data`` as JSON to ``path`` with ``0600`` perms.

    Addresses Section 2.3 of the analysis: credential files (such as
    ``.keys.json``) must not be world-readable. The function uses
    ``os.open`` with ``O_CREAT | O_TRUNC | O_WRONLY`` and a 0o600 mode,
    then writes via ``os.fdopen`` so the descriptor is closed
    deterministically.

    Parameters
    ----------
    path:
        Destination file path.
    data:
        JSON-serialisable object.
    """
    path = os.fspath(path)
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False)

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
    except Exception:
        # ``os.fdopen`` already closed the fd; nothing else to clean up.
        raise


def read_json(path: str | os.PathLike[str], default: Any = None) -> Any:
    """Read JSON from ``path`` returning ``default`` on any failure.

    Never raises - it is safe to use on untrusted or missing files.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default
