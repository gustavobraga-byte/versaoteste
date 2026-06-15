"""Dependency installer: opencode + apt packages + pip packages.

Replaces the duplicated routines from the original ``run_fast.py`` and
``launch_app.py``. The module exposes a single :func:`install_all`
function that the orchestrator calls.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Iterable

from .config import SETTINGS

logger = logging.getLogger("pesquisai.deps")


def _check_bin(name: str) -> bool:
    """Return True if ``name`` is on PATH or in a known install prefix."""
    if shutil.which(name):
        return True
    for d in ("~/.local/bin", "~/.npm-global/bin", "~/.opencode/bin", "/usr/local/bin"):
        path = os.path.expanduser(os.path.join(d, name))
        if os.path.isfile(path):
            return True
    return False


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """Wrapper around ``subprocess.run`` with safe defaults."""
    kw.setdefault("check", False)
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    return subprocess.run(cmd, **kw)


def install_opencode() -> bool:
    """Install the opencode CLI from the official installer. Idempotent."""
    if _check_bin("opencode"):
        logger.info("opencode ja instalado - pulando.")
        return True
    print("Instalando OpenCode...")
    result = _run(["bash", "-c", "curl -fsSL https://opencode.ai/install | bash"])
    if result.returncode == 0 and _check_bin("opencode"):
        return True
    logger.error("Instalacao do opencode falhou.")
    return False


def install_system_deps(extra: Iterable[str] = ()) -> bool:
    """Install ttyd, xclip, xsel, uv and any ``extra`` packages via apt.

    Falls back to a direct download of ``ttyd`` from the GitHub
    release page when apt fails. Returns True if the essential
    ``ttyd`` binary is present after the call.
    """
    tasks: list[str] = []
    if not _check_bin("ttyd"):
        tasks.append("ttyd")
    if not _check_bin("xclip"):
        tasks.append("xclip")
    if not _check_bin("xsel"):
        tasks.append("xsel")
    tasks.extend(pkg for pkg in extra if pkg and not _check_bin(pkg))

    if tasks:
        unique = sorted(set(tasks))
        pkgs = " ".join(unique)
        print(f"Instalando pacotes apt: {pkgs}")
        apt = _run(
            ["bash", "-c", f"apt-get update -qq && apt-get install -y -qq {pkgs}"]
        )
        if apt.returncode != 0 and "ttyd" in unique:
            logger.warning("apt falhou; baixando ttyd manualmente.")
            _run(
                [
                    "bash",
                    "-c",
                    "curl -fsSL "
                    "https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64"
                    " -o /usr/local/bin/ttyd && chmod +x /usr/local/bin/ttyd",
                ]
            )
    else:
        print("Dependencias de sistema ja instaladas - pulando.")

    if not _check_bin("uv"):
        _run(["bash", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"])
    else:
        logger.info("uv ja instalado - pulando.")
    return _check_bin("ttyd")


def install_python_deps() -> None:
    """Install the Google API client libraries used by Drive listing."""
    _run(
        [
            "pip",
            "install",
            "--quiet",
            "--no-cache-dir",
            "google-api-python-client",
            "google-auth-httplib2",
            "google-auth-oauthlib",
        ]
    )


def install_all(extra: Iterable[str] = ()) -> None:
    """Run every installer in the right order. Top-level convenience."""
    install_opencode()
    install_system_deps(extra)
    install_python_deps()
