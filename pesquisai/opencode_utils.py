"""
opencode_utils.py — Utilitários para localizar e configurar o OpenCode CLI.
"""
import os
import shutil
import subprocess
from typing import Optional

from .constants import logger

OPENCODE_BIN: Optional[str] = None

CANDIDATES: list[str] = [
    os.path.expanduser("~/.local/bin/opencode"),
    os.path.expanduser("~/.opencode/bin/opencode"),
    os.path.expanduser("~/bin/opencode"),
    "/root/.local/bin/opencode",
    "/root/.opencode/bin/opencode",
    "/root/bin/opencode",
    "/usr/local/bin/opencode",
    "/usr/bin/opencode",
]


def _search() -> Optional[str]:
    """Busca recursivamente o binário opencode no sistema."""
    try:
        result = subprocess.run(
            ["find", "/root", "/home", "/usr/local", "-name", "opencode", "-type", "f"],
            capture_output=True, text=True, timeout=10,
        )
        hits = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return hits[0] if hits else None
    except Exception:
        return None


def find_opencode() -> Optional[str]:
    """Localiza o binário do opencode."""
    global OPENCODE_BIN
    if OPENCODE_BIN and os.path.isfile(OPENCODE_BIN):
        return OPENCODE_BIN
    if os.environ.get("OPENCODE_BIN") and os.path.isfile(os.environ["OPENCODE_BIN"]):
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
    return None


def opencode_installed() -> bool:
    """Verifica se o opencode está instalado."""
    return find_opencode() is not None


def install_opencode() -> bool:
    """Instala o opencode via script oficial."""
    install_script = "curl -fsSL https://opencode.ai/install | bash"
    logger.info("Instalando opencode...")
    try:
        r = subprocess.run(install_script, shell=True, capture_output=True, text=True, timeout=180)
        if r.returncode == 0 and opencode_installed():
            logger.info("✅ opencode instalado com sucesso.")
            return True
        logger.error("Falha na instalação: %s", r.stderr[:500])
        return False
    except Exception as e:
        logger.error("Erro ao instalar opencode: %s", e)
        return False


def ensure_opencode_in_path() -> None:
    """Garante que o diretório do opencode está no PATH."""
    bin_path = find_opencode()
    if not bin_path:
        return
    bin_dir = os.path.dirname(bin_path)
    if bin_dir and bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_dir + ":" + os.environ.get("PATH", "")
    os.environ["OPENCODE_BIN"] = bin_path


def get_opencode_version() -> Optional[str]:
    """Retorna a versão do opencode."""
    bin_path = find_opencode()
    if not bin_path:
        return None
    try:
        r = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None
