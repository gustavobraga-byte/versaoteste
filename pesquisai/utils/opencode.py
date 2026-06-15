"""Helpers for locating and installing the ``opencode`` CLI and ``ttyd``.

Addresses Section 5.2 of ANALISE_CODIGO.md: the previous code had two
near-duplicate copies of the ``ttyd`` install routine (one in
``run_fast.py``, one in ``launch_app.py``). This module centralises
both into a single source of truth.

The :func:`find_opencode` function is decorated with :func:`functools.lru_cache`
to avoid the race condition flagged in Section 3.3 of the analysis.
"""

from __future__ import annotations

import functools
import logging
import os
import shutil
import subprocess
from typing import Optional

logger = logging.getLogger("pesquisai.opencode")

# Candidate install locations for the ``opencode`` binary.
_CANDIDATES: tuple[str, ...] = (
    "~/.local/bin/opencode",
    "~/bin/opencode",
    "/root/.local/bin/opencode",
    "/root/bin/opencode",
    "/usr/local/bin/opencode",
    "/usr/bin/opencode",
)

_TTYD_DOWNLOAD_URL = (
    "https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64"
)


class OpenCodeNotFoundError(FileNotFoundError):
    """Raised when the opencode binary cannot be located on the system."""


@functools.lru_cache(maxsize=1)
def find_opencode() -> str:
    """Return the absolute path to the ``opencode`` binary.

    The function is cached: subsequent calls return the same path
    without re-scanning the filesystem. The first call may raise
    :class:`OpenCodeNotFoundError` if no binary is found.

    Resolution order
    ----------------
    1. ``$OPENCODE_BIN`` environment variable (if it points to a file).
    2. ``shutil.which("opencode")``.
    3. Hard-coded candidate list in :data:`_CANDIDATES`.
    4. A bounded ``find`` over ``/root``, ``/home`` and ``/usr/local``.

    Raises
    ------
    OpenCodeNotFoundError
        If the binary cannot be found in any of the locations above.
    """
    env_bin = os.environ.get("OPENCODE_BIN")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    which = shutil.which("opencode")
    if which:
        return which

    for candidate in _CANDIDATES:
        expanded = os.path.expanduser(candidate)
        if os.path.isfile(expanded):
            return expanded

    try:
        result = subprocess.run(
            [
                "find",
                "/root",
                "/home",
                "/usr/local",
                "-name",
                "opencode",
                "-type",
                "f",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("Busca por opencode falhou: %s", exc)
        result = None  # type: ignore[assignment]

    if result is not None and result.stdout:
        hits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if hits:
            return hits[0]

    raise OpenCodeNotFoundError("opencode binary not found")


def ensure_opencode_in_path() -> str:
    """Make sure the opencode directory is on ``$PATH`` for child procs.

    Returns the binary path (also cached under ``OPENCODE_BIN`` env var).
    """
    bin_path = find_opencode()
    bin_dir = os.path.dirname(bin_path)
    current_path = os.environ.get("PATH", "")
    if bin_dir and bin_dir not in current_path.split(":"):
        os.environ["PATH"] = f"{bin_dir}:{current_path}"
    os.environ["OPENCODE_BIN"] = bin_path
    logger.info("opencode encontrado: %s", bin_path)
    return bin_path


def build_env(extra_vars: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Construct an environment dict for child processes.

    Adds the ``OPENCODE_EXPERIMENTAL_DISABLE_COPY_ON_SELECT`` flag and
    prepends the opencode binary directory to ``$PATH`` so subshells
    (e.g. ``bash -c``) can locate the binary.
    """
    env = os.environ.copy()
    env["OPENCODE_EXPERIMENTAL_DISABLE_COPY_ON_SELECT"] = "1"
    try:
        bin_path = find_opencode()
        bin_dir = os.path.dirname(bin_path)
    except OpenCodeNotFoundError:
        bin_dir = os.path.expanduser("~/.local/bin")
    if bin_dir:
        env["PATH"] = f"{env.get('PATH', '')}:{bin_dir}"
    if extra_vars:
        env.update(extra_vars)
    return env


def ensure_ttyd() -> bool:
    """Install ``ttyd`` via apt (with curl fallback).

    Returns ``True`` if the binary is present after this call.

    The function is idempotent: it skips apt entirely when ``ttyd`` is
    already on ``$PATH``. It always falls back to a direct download
    from the GitHub release page when apt fails, mirroring the
    behaviour of the original ``install_ttyd`` function in
    ``launch_app.py``.
    """
    if shutil.which("ttyd"):
        logger.info("ttyd já instalado — pulando.")
        return True

    logger.info("Instalando ttyd via apt-get...")
    apt = subprocess.run(
        ["bash", "-c", "apt-get update -qq && apt-get install -y -qq ttyd"],
        capture_output=True,
        text=True,
    )
    if apt.returncode == 0:
        return True

    logger.warning("apt-get falhou; tentando download manual de ttyd.")
    curl = subprocess.run(
        [
            "bash",
            "-c",
            f"curl -fsSL {_TTYD_DOWNLOAD_URL} -o /usr/local/bin/ttyd "
            f"&& chmod +x /usr/local/bin/ttyd",
        ],
        capture_output=True,
        text=True,
    )
    return curl.returncode == 0
