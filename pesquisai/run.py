"""PesquisAI main orchestrator.

Replaces ``run_fast.py`` (which had several latent issues described in
ANALISE_CODIGO.md) with a thin pipeline that delegates to dedicated
modules:

* :mod:`pesquisai.config` - typed settings
* :mod:`pesquisai.skills` - skill registry and installer
* :mod:`pesquisai.theme` - theme/agent/TUI configuration
* :mod:`pesquisai.progress` - terminal / Colab progress bar
* :mod:`pesquisai.launch` - ttyd and HTTP wrapper
* :mod:`pesquisai.dependencies` - apt/pip installs
* :mod:`pesquisai.drive` - Google Drive mounting
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import SETTINGS
from .launch import launch as launch_app
from .progress import finish as progress_finish
from .progress import show as progress_show
from .theme import install_all as install_theme_and_agent

logger = logging.getLogger("pesquisai.run")

# Default AGENTS.md location - looked up relative to this file so the
# project works both as a package and as a flat script checkout.
_DEFAULT_AGENTS_MD = Path(__file__).resolve().parent.parent / "AGENTS.md"


def setup_drive() -> tuple[str, str]:
    """Mount Google Drive and locate the PesquisAI folder.

    Returns ``(folder_path, drive_url)``. Outside Colab the function
    falls back to a local working directory.
    """
    progress_show(1, 4, "Montando Google Drive...")
    try:
        from google.colab import auth, drive  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError:
        fallback = "/tmp/pesquisai_work"
        os.makedirs(fallback, exist_ok=True)
        logger.info("Fora do Colab; usando %s", fallback)
        return fallback, SETTINGS.fallback_drive_url

    if not Path("/content/drive/My Drive").exists():
        print("Montando Google Drive...")
        drive.mount(str(SETTINGS.mount_path), force_remount=False)

    os.makedirs(str(SETTINGS.drive_path), exist_ok=True)
    os.chdir(str(SETTINGS.drive_path))

    folder_url = SETTINGS.fallback_drive_url
    try:
        auth.authenticate_user()
        service = build("drive", "v3")
        result = service.files().list(
            q="name='PesquisAI' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id)",
        ).execute()
        files = result.get("files", [])
        if files:
            folder_url = f"https://drive.google.com/drive/folders/{files[0]['id']}"
    except Exception as exc:  # noqa: BLE001 - optional step
        logger.debug("Listagem de pastas do Drive falhou: %s", exc)

    print(f"Diretorio: {SETTINGS.drive_path}")
    return str(SETTINGS.drive_path), folder_url


def setup_dependencies() -> None:
    """Install runtime dependencies (opencode + apt + pip)."""
    progress_show(2, 4, "Instalando opencode e dependencias de sistema...")
    from .dependencies import install_all  # local import keeps the top clean

    # Section 5.2: run apt + pip in parallel - both are I/O bound.
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_opencode = pool.submit(install_all)
        f_theme = pool.submit(install_theme_and_agent, str(_DEFAULT_AGENTS_MD))
        f_opencode.result()
        f_theme.result()


def setup_skills() -> None:
    """Clone / pull every skill in the registry."""
    progress_show(3, 4, "Clonando repositorios de skills (em paralelo)...")
    from .skills import install_all

    results = install_all()
    failed = [name for name, ok in results.items() if not ok]
    if failed:
        logger.warning("Skills que falharam: %s", ", ".join(failed))
    installed = [name for name, ok in results.items() if ok]
    if installed:
        print(f"Skills instaladas: {', '.join(installed)}")


def setup_launch(folder_path: str, drive_url: str) -> str:
    """Start ttyd + the wrapper server and display the launch banner."""
    progress_show(4, 4, "Iniciando servidores e interface web...")
    banner_url = launch_app(folder_path, drive_url)
    progress_finish()
    return banner_url


def run() -> str:
    """Top-level entry point used by ``main.py``.

    Returns the URL the user should open to access the UI.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )

    t0 = time.time()
    progress_show(0, 4, "Preparando...")

    print("=" * 50)
    print("  PESQUISAI v" + SETTINGS.version + " (MODO RAPIDO)")
    print("=" * 50)

    folder_path, drive_url = setup_drive()
    setup_dependencies()
    setup_skills()
    banner_url = setup_launch(folder_path, drive_url)

    elapsed = time.time() - t0
    print(f"\nInicializado em {elapsed:.0f}s")
    return banner_url


if __name__ == "__main__":  # pragma: no cover - manual entry
    run()
