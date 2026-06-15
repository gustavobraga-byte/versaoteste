"""Progress bar for terminal and Colab contexts.

This is a typed, documented rewrite of the original ``progress_bar.py``
that addresses the encoding/typing gaps in the analysis (Section 4).
"""

from __future__ import annotations

from typing import Any, Optional

# Detect Colab / IPython availability once at import time so the
# rest of the module stays simple.
IN_COLAB: bool = False
_display: Optional[Any] = None
_HTML: Optional[Any] = None
_clear_output: Optional[Any] = None

try:
    from IPython.display import display as _display_fn  # type: ignore
    from IPython.display import HTML as _HTML_cls  # type: ignore
    from IPython.display import clear_output as _clear_output_fn  # type: ignore

    _display = _display_fn
    _HTML = _HTML_cls
    _clear_output = _clear_output_fn
    IN_COLAB = True
except ImportError:
    pass


STAGES: tuple[str, ...] = (
    "Configurando Google Drive",
    "Instalando dependências",
    "Instalando skills",
    "Iniciando interface",
)

COLORS: tuple[str, ...] = ("#4fc3f7", "#5dba7e", "#e8b84b", "#a47de0")

# Module-level state for the Colab display handle.
_handle: Optional[Any] = None


def _render_html(step: int, total: int, message: str, percent: int) -> str:
    """Return the HTML markup for the Colab progress widget."""
    if total <= 0:
        total = 1
    idx = min(step, total - 1)
    stage = STAGES[idx] if idx < len(STAGES) else "Finalizando"
    color = COLORS[idx % len(COLORS)]
    bar_w = max(percent, 2)
    return f"""<div id="ppbar" style="
    max-width:680px; margin:20px auto 16px; padding:16px 22px;
    background:#0d0f10; border:1px solid rgba(255,255,255,.07);
    border-radius:10px; font-family:system-ui,-apple-system,sans-serif;
">
    <div style="display:flex; align-items:center; gap:11px; margin-bottom:12px;">
        <div style="
            width:24px; height:24px; border-radius:50%;
            border:3px solid {color}; border-top-color:transparent;
            animation:ppsp 0.85s linear infinite;
        ""></div>
        <div>
            <div style="color:#e8e6e0; font-size:14px; font-weight:600;">
                {stage}
            </div>
            <div style="color:#8a8780; font-size:11.5px; margin-top:1px;">
                {message}
            </div>
        </div>
        <div style="margin-left:auto; color:{color}; font-size:13px; font-weight:700;">
            {percent}%
        </div>
    </div>
    <div style="
        width:100%; height:5px; background:rgba(255,255,255,.05);
        border-radius:3px; overflow:hidden;
    ">
        <div style="
            width:{percent}%; height:100%;
            background:linear-gradient(90deg, {color}, {color}cc);
            border-radius:3px; transition:width .35s ease;
        ""></div>
    </div>
    <style>
        @keyframes ppsp{{to{{transform:rotate(360deg)}}}}
    </style>
</div>"""


def _render_terminal(step: int, total: int, message: str, percent: int) -> str:
    """Return a plain-text progress bar for non-Colab contexts."""
    if total <= 0:
        total = 1
    idx = min(step, total - 1)
    stage = STAGES[idx] if idx < len(STAGES) else "Finalizando"
    bar = "█" * (percent // 4) + "░" * (25 - percent // 4)
    return f"\r  {stage:<38} {bar} {percent:>3}%  {message}"


def show(step: int = 0, total: int = 4, message: str = "Iniciando...") -> None:
    """Display the progress bar at ``step``/``total`` with a status message.

    In Colab the widget is rendered as HTML; in a plain terminal the
    function falls back to a one-line ASCII bar.
    """
    global _handle
    if total <= 0:
        total = 1
    percent = min(int((step / total) * 100), 100)

    if IN_COLAB and _display is not None and _HTML is not None:
        html = _render_html(step, total, message, percent)
        if _handle is None:
            _handle = _display(_HTML(html), display_id=True)
        else:
            _handle.update(_HTML(html))
        return

    line = _render_terminal(step, total, message, percent)
    print(line, end="", flush=True)


def finish() -> None:
    """Finalise the progress display (clears it in Colab, newline in TTY)."""
    global _handle
    if IN_COLAB and _clear_output is not None:
        _clear_output(wait=True)
        _handle = None
        return
    print()
