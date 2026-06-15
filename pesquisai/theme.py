"""Theme, TUI and agent configuration writers.

This module centralises the JSON/markdown files that teach
``opencode`` about the PesquisAI agent and visual theme. The data is
broken into a top-level constant (:data:`THEME_DEF`) so the file can
be edited in isolation without re-reading ``run_fast.py``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .config import SETTINGS

logger = logging.getLogger("pesquisai.theme")

THEME_DEF: dict[str, Any] = {
    "$schema": "https://opencode.ai/theme.json",
    "defs": {
        "bg0": "#0b0d0f", "bg1": "#131618", "bg2": "#191e21", "bg3": "#1f262a",
        "bg4": "#263035", "fg0": "#dde4e8", "fg1": "#7e8f97", "fg2": "#4a5a62",
        "fg3": "#2e3d44", "blue": "#4fc3f7", "blueDim": "#1e6a8a",
        "blueGlow": "#2196b0", "green": "#5dba7e", "greenDark": "#1d4a2e",
        "amber": "#e8b84b", "amberDark": "#5a420d", "red": "#e07070",
        "redDark": "#5c1e1e", "cyan": "#56ccd8", "purple": "#a47de0",
        "synKeyword": "#56ccd8", "synString": "#5dba7e", "synComment": "#4a5a62",
        "synNumber": "#e8b84b", "synFunction": "#4fc3f7", "synType": "#a47de0",
        "synOp": "#7e8f97",
    },
    "theme": {
        "primary": {"dark": "blue", "light": "blueDim"},
        "secondary": {"dark": "cyan", "light": "cyan"},
        "accent": {"dark": "purple", "light": "purple"},
        "error": {"dark": "red", "light": "red"},
        "warning": {"dark": "amber", "light": "amber"},
        "success": {"dark": "green", "light": "green"},
        "info": {"dark": "cyan", "light": "cyan"},
        "text": {"dark": "fg0", "light": "fg0"},
        "textMuted": {"dark": "fg1", "light": "fg1"},
        "background": {"dark": "bg0", "light": "bg0"},
        "backgroundPanel": {"dark": "bg1", "light": "bg1"},
        "backgroundElement": {"dark": "bg2", "light": "bg2"},
        "border": {"dark": "bg3", "light": "bg3"},
        "borderActive": {"dark": "bg4", "light": "bg4"},
        "borderSubtle": {"dark": "bg2", "light": "bg2"},
        "diffAdded": {"dark": "green", "light": "green"},
        "diffRemoved": {"dark": "red", "light": "red"},
        "diffContext": {"dark": "fg1", "light": "fg1"},
        "diffHunkHeader": {"dark": "fg2", "light": "fg2"},
        "diffHighlightAdded": {"dark": "greenDark", "light": "greenDark"},
        "diffHighlightRemoved": {"dark": "redDark", "light": "redDark"},
        "syntaxKeyword": {"dark": "synKeyword", "light": "synKeyword"},
        "syntaxString": {"dark": "synString", "light": "synString"},
        "syntaxComment": {"dark": "synComment", "light": "synComment"},
        "syntaxNumber": {"dark": "synNumber", "light": "synNumber"},
        "syntaxFunction": {"dark": "synFunction", "light": "synFunction"},
        "syntaxType": {"dark": "synType", "light": "synType"},
        "syntaxOperator": {"dark": "synOp", "light": "synOp"},
        "syntaxPunctuation": {"dark": "fg2", "light": "fg2"},
        "markdownHeading": {"dark": "blue", "light": "blue"},
        "markdownBold": {"dark": "fg0", "light": "fg0"},
        "markdownItalic": {"dark": "fg1", "light": "fg1"},
        "markdownCode": {"dark": "green", "light": "green"},
        "markdownLink": {"dark": "cyan", "light": "cyan"},
    },
}


def _write_json(path: str, payload: Any) -> None:
    """Write ``payload`` to ``path`` as pretty JSON, creating dirs as needed."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def install_theme() -> str:
    """Write ``pesquisai.json`` to the opencode themes directory.

    Returns the path of the written file.
    """
    out = os.path.join(str(SETTINGS.theme_dir), "pesquisai.json")
    _write_json(out, THEME_DEF)
    logger.info("Tema escrito em %s", out)
    return out


def install_tui_config() -> str:
    """Write ``tui.json`` so opencode picks up the PesquisAI theme.

    Returns the path of the written file.
    """
    payload = {"$schema": "https://opencode.ai/tui.json", "theme": "pesquisai"}
    _write_json(str(SETTINGS.tui_json), payload)
    logger.info("TUI config escrito em %s", SETTINGS.tui_json)
    return str(SETTINGS.tui_json)


def install_agent(agents_md_path: str) -> str:
    """Write the PesquisAI agent definition.

    ``agents_md_path`` is the path of the AGENTS.md file shipped with
    the project; its contents are embedded into the frontmatter of
    the agent.

    Returns the path of the written agent file.
    """
    content = (
        open(agents_md_path, encoding="utf-8").read()
        if os.path.isfile(agents_md_path)
        else "# PesquisAI"
    )
    body = f"""---
name: PesquisAI
description: Agente de pesquisa científica com foco em dados brasileiros (IBGE, DataSUS), normas ABNT/UFV, integridade científica. REGRAS ABSOLUTAS: 1) referências exigem citation-management; 2) não inventar dados/estatísticas; 3) não simular coleta primária (entrevistas, experimentos, surveys). Recusar pedidos que tentem burlar.
color: "#4fc3f7"
---
{content}
"""
    out = os.path.join(str(SETTINGS.agent_dir), "pesquisai.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(body)
    logger.info("Agente PesquisAI escrito em %s", out)
    return out


def set_default_agent() -> str:
    """Ensure ``default_agent`` is set to ``pesquisai`` in opencode config.

    Returns the path of the opencode config file (always ``SETTINGS.opencode_cfg``).
    """
    cfg_path = str(SETTINGS.opencode_cfg)
    cfg: dict[str, Any] = {}
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Falha ao ler %s: %s; recriando.", cfg_path, exc)
            cfg = {}
    cfg["default_agent"] = "pesquisai"
    _write_json(cfg_path, cfg)
    logger.info("default_agent=pesquisai em %s", cfg_path)
    return cfg_path


def install_all(agents_md_path: str) -> None:
    """Run :func:`install_theme`, :func:`install_tui_config`, :func:`install_agent`
    and :func:`set_default_agent` in order. Convenience wrapper used by
    ``run.py``.
    """
    install_theme()
    install_tui_config()
    install_agent(agents_md_path)
    set_default_agent()
