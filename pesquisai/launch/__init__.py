"""Launch subsystem: HTTP server, ttyd management and template rendering.

Public surface:

* :func:`launch` - top-level orchestration used by ``run.py``.
* :func:`start_ttyd` - bring up the ttyd process.
* :func:`render_wrapper` - render ``index.html`` from the template.
* :func:`start_wrapper_server` - start the HTTP server.
* :func:`show_ready_message`, :func:`show_launch_button` - Colab UI bits.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from ..config import SETTINGS
from ..utils.opencode import (
    OpenCodeNotFoundError,
    build_env,
    ensure_ttyd,
    find_opencode,
)

logger = logging.getLogger("pesquisai.launch")


# ── Colab detection (kept as in original) ──────────────────────────

try:
    from google.colab import output as _colab_output  # type: ignore
    from IPython.display import display as _display  # type: ignore
    from IPython.display import HTML as _HTML  # type: ignore

    IN_COLAB = True
except ImportError:
    _colab_output = None
    _display = None
    _HTML = None
    IN_COLAB = False


# ── Template rendering ──────────────────────────────────────────────


_TEMPLATE_FILENAME = "index.html.tmpl"


def _read_template() -> str:
    """Load ``index.html.tmpl`` from the package templates directory."""
    base = Path(__file__).resolve().parent / "templates"
    return (base / _TEMPLATE_FILENAME).read_text(encoding="utf-8")


def render_wrapper(terminal_url: str, drive_url: str) -> Path:
    """Render the wrapper HTML to ``wrapper_dir/index.html``.

    Returns the path of the written file. Static assets are copied
    next to it so the page can be served as-is.

    The template uses ``{{ key }}`` for placeholders, which we
    replace manually to avoid clashes with the CSS curly braces in
    the embedded ``<style>`` blocks.
    """
    template = _read_template()
    institution_short = "UFV - Vicosa, MG - Brasil"
    placeholders = {
        "{{ terminal_url }}": terminal_url,
        "{{ drive_url }}": drive_url,
        "{{ version }}": SETTINGS.version,
        "{{ author_email }}": SETTINGS.author_email,
        "{{ repo_url }}": SETTINGS.repo_url,
        "{{ institution_short }}": institution_short,
        "{{ static_prefix }}": "",
    }
    html = template
    for needle, value in placeholders.items():
        html = html.replace(needle, value)
    out_dir = Path(str(SETTINGS.wrapper_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")

    # Copy static assets (CSS + JS) next to index.html
    static_src = Path(__file__).resolve().parent / "static"
    for asset in ("style.css", "app.js"):
        src = static_src / asset
        if src.is_file():
            shutil.copy2(src, out_dir / asset)
    logger.info("Wrapper HTML rendered to %s", out_file)
    return out_file


# ── ttyd lifecycle ─────────────────────────────────────────────────


def kill_previous() -> None:
    """Terminate any prior ttyd / wrapper python processes."""
    subprocess.run("pkill -f ttyd 2>/dev/null || true", shell=True, check=False)
    subprocess.run(
        f"pkill -f 'python3.*{SETTINGS.wrapper_port}' 2>/dev/null || true",
        shell=True,
        check=False,
    )
    time.sleep(0.5)


def start_ttyd() -> str:
    """Bring up ttyd hosting the opencode TUI.

    Returns the opencode binary path (also cached on the runtime
    state by :func:`start_wrapper_server`).
    """
    try:
        opencode_bin = find_opencode()
    except OpenCodeNotFoundError:
        logger.warning("opencode nao encontrado, usando fallback 'opencode'")
        opencode_bin = "opencode"

    env = build_env()
    subprocess.Popen(
        [
            "ttyd",
            "-p",
            str(SETTINGS.terminal_port),
            "bash",
            "-i",
            "-c",
            f"{opencode_bin} --prompt 'oi' ; exec bash",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    logger.info("ttyd iniciado na porta %d", SETTINGS.terminal_port)
    time.sleep(2)
    return opencode_bin


# ── Colab display helpers ──────────────────────────────────────────


def show_ready_message() -> None:
    """Display a 'PesquisAI ready' badge in the Colab cell output."""
    if not IN_COLAB or _display is None or _HTML is None:
        print("\nPesquisAI pronto!\n")
        return
    _display(_HTML("""
<style>
@keyframes glow {
    0%, 100% { box-shadow: 0 0 20px rgba(93, 186, 126, 0.3); }
    50% { box-shadow: 0 0 40px rgba(93, 186, 126, 0.6); }
}
.ready-container {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 20px 20px 0px 20px;
}
.ready-badge {
    display: inline-flex; align-items: center; gap: 12px;
    padding: 16px 32px; background: rgba(93, 186, 126, 0.12);
    border: 2px solid rgba(93, 186, 126, 0.4); border-radius: 12px;
    animation: glow 2s ease-in-out infinite;
}
.ready-icon { font-size: 28px; }
.ready-text {
    font-family: 'DM Mono', monospace; font-size: 18px;
    font-weight: 600; color: #5dba7e;
}
</style>
<div class="ready-container">
    <div class="ready-badge">
        <span class="ready-icon">*</span>
        <span class="ready-text">PesquisAI pronto!</span>
    </div>
</div>
"""))


def show_launch_button(banner_url: str) -> None:
    """Display a clickable 'ABRIR O PESQUISAI' button in the Colab output."""
    if not IN_COLAB or _display is None or _HTML is None:
        print(f"\nAcesse: {banner_url}\n")
        return
    _display(_HTML(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@500;700&family=Syne:wght@700;800&display=swap');
  @keyframes pulse-glow {{
    0%, 100% {{ box-shadow: 0 0 20px rgba(79,195,247,0.3), 0 4px 12px rgba(0,0,0,0.3); }}
    50% {{ box-shadow: 0 0 40px rgba(79,195,247,0.6), 0 6px 20px rgba(0,0,0,0.4); }}
  }}
  .btn-container {{
    display: flex; justify-content: center; padding: 20px; margin-top: 10px;
  }}
  .pesquisai-launch {{
    display: inline-flex; align-items: center; justify-content: center;
    gap: 16px; padding: 24px 56px;
    font-family: "Syne", sans-serif; font-size: 22px; font-weight: 800;
    letter-spacing: 0.08em; color: #0d0f10;
    background: linear-gradient(135deg, #4fc3f7 0%, #29b6f6 50%, #03a9f4 100%);
    border: none; border-radius: 14px; cursor: pointer;
    text-decoration: none; transition: all 0.2s ease;
    animation: pulse-glow 2.5s ease-in-out infinite;
    position: relative; overflow: hidden;
  }}
  .pesquisai-launch:hover {{
    transform: translateY(-4px) scale(1.02); filter: brightness(1.1);
    box-shadow: 0 12px 40px rgba(79,195,247,0.5), 0 8px 24px rgba(0,0,0,0.4);
  }}
  .pesquisai-launch:active {{ transform: translateY(-1px) scale(0.99); }}
  .btn-icon {{ font-size: 28px; }}
  .btn-text {{ display: flex; flex-direction: column; align-items: flex-start; gap: 2px; }}
  .btn-main {{ font-size: 22px; font-weight: 800; }}
  .btn-sub {{
    font-family: "DM Mono", monospace; font-size: 11px;
    font-weight: 500; opacity: 0.8; letter-spacing: 0.1em;
  }}
  .arrow {{ font-size: 28px; font-weight: 500; transition: transform 0.2s ease; }}
  .pesquisai-launch:hover .arrow {{ transform: translateX(8px); }}
</style>
<div class="btn-container">
  <a href="{banner_url}" target="_blank" class="pesquisai-launch">
    <span class="btn-icon">&gt;</span>
    <span class="btn-text">
      <span class="btn-main">ABRIR O PESQUISAI</span>
      <span class="btn-sub">clique para comecar</span>
    </span>
    <span class="arrow">&rarr;</span>
  </a>
</div>
"""))


# ── Top-level orchestration ────────────────────────────────────────


def resolve_proxy_urls() -> tuple[str, str]:
    """Return the user-facing URLs for ttyd and the wrapper UI.

    In Colab the kernel proxy is used; otherwise a localhost URL is
    returned.
    """
    if IN_COLAB and _colab_output is not None:
        terminal_url = _colab_output.eval_js(
            f"google.colab.kernel.proxyPort({SETTINGS.terminal_port})"
        )
        banner_url = _colab_output.eval_js(
            f"google.colab.kernel.proxyPort({SETTINGS.wrapper_port})"
        )
    else:
        terminal_url = f"http://localhost:{SETTINGS.terminal_port}"
        banner_url = f"http://localhost:{SETTINGS.wrapper_port}"
    return terminal_url, banner_url


def launch(folder_path: str, drive_url: str) -> str:
    """Top-level orchestration: ttyd + wrapper + UI banner.

    Returns the URL the user should click to open the interface.
    """
    ensure_ttyd()
    kill_previous()
    start_ttyd()

    from .server import start_wrapper_server  # local import: avoid cycle
    terminal_url, banner_url = resolve_proxy_urls()
    render_wrapper(terminal_url=terminal_url, drive_url=drive_url)
    start_wrapper_server(folder_path, drive_url)

    time.sleep(1)
    show_ready_message()
    show_launch_button(banner_url)
    return banner_url


__all__ = [
    "IN_COLAB",
    "launch",
    "render_wrapper",
    "start_ttyd",
    "start_wrapper_server",
    "show_ready_message",
    "show_launch_button",
    "kill_previous",
]
