"""Utilitários para localizar e configurar o binário do OpenCode."""

import os
import shutil
import subprocess

from constants import logger

OPENCODE_BIN = None

CANDIDATES = [
    os.path.expanduser("~/.local/bin/opencode"),
    os.path.expanduser("~/bin/opencode"),
    "/root/.local/bin/opencode",
    "/root/bin/opencode",
    "/usr/local/bin/opencode",
    "/usr/bin/opencode",
]


def _search() -> str | None:
    """Procure o binário opencode no sistema via find."""
    try:
        result = subprocess.run(
            ["find", "/root", "/home", "/usr/local", "-name", "opencode", "-type", "f"],
            capture_output=True, text=True, timeout=5
        )
        hits = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return hits[0] if hits else None
    except subprocess.TimeoutExpired:
        logger.warning("find para opencode excedeu timeout de 5s")
        return None


def find_opencode() -> str:
    """Localize o binário do OpenCode no sistema."""
    global OPENCODE_BIN
    if OPENCODE_BIN:
        return OPENCODE_BIN
    if "OPENCODE_BIN" in os.environ and os.path.isfile(os.environ["OPENCODE_BIN"]):
        OPENCODE_BIN = os.environ["OPENCODE_BIN"]
        return OPENCODE_BIN
    w = shutil.which("opencode")
    if w:
        OPENCODE_BIN = w
        return OPENCODE_BIN
    found = next((p for p in CANDIDATES if os.path.isfile(p)), None)
    if found:
        OPENCODE_BIN = found
        return OPENCODE_BIN
    found = _search()
    if found:
        OPENCODE_BIN = found
        return OPENCODE_BIN
    raise FileNotFoundError("opencode binary not found")


def ensure_opencode_in_path():
    """Garanta que o opencode esteja no PATH do sistema."""
    bin_path = find_opencode()
    bin_dir = os.path.dirname(bin_path)
    if bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_dir + ":" + os.environ["PATH"]
    os.environ["OPENCODE_BIN"] = bin_path
    logger.info("opencode encontrado: %s", bin_path)


def build_env(extra_vars: dict | None = None) -> dict:
    """Construa o dicionário de ambiente para execução do opencode."""
    env = {**os.environ}
    env["OPENCODE_EXPERIMENTAL_DISABLE_COPY_ON_SELECT"] = "1"
    bin_path = find_opencode()
    bin_dir = os.path.dirname(bin_path) if os.path.isfile(bin_path) else os.path.expanduser("~/.local/bin")
    env["PATH"] = env.get("PATH", "") + ":" + bin_dir
    if extra_vars:
        env.update(extra_vars)
    return env
