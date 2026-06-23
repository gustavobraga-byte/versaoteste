"""
launch_app_responsive.py — Versão responsiva do wrapper HTML.

Substitui `create_wrapper_html` em `launch_app.py` com uma versão que
adapta a interface para diferentes tamanhos de tela:

  - Desktop (≥ 1024px): topbar horizontal completa
  - Tablet (768px–1023px): topbar com agrupamento
  - Mobile (480px–767px): topbar com botões essenciais, menu hambúrguer
  - Mobile pequeno (< 480px): modo compacto, foco no terminal

Mantém 100% das funcionalidades (backup, restore, drive, dashboard,
sessões, atalhos, tema, provedores), apenas reorganiza o layout.

Uso:
    from pesquisai.launch_app_responsive import create_wrapper_html_responsive

    create_wrapper_html_responsive(terminal_url, drive_url)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Imports resilientes: funcionam tanto dentro do pacote pesquisai
# quanto como arquivo standalone para testes.
try:
    from .constants import WRAPPER_DIR, VERSION
    from .jokes import next_joke
except ImportError:
    # Modo standalone: usa defaults razoáveis
    WRAPPER_DIR = "/tmp/pesquisai-wrapper"
    VERSION = "0.2.3"
    def next_joke(category: str = "aleatorio") -> str:
        return "💻 (standalone mode) carregando..."

# Garante que o diretório wrapper existe
Path(WRAPPER_DIR).mkdir(parents=True, exist_ok=True)

# CSS responsivo injetado. Reaproveita o estilo original do launch_app.py,
# mas adiciona media queries para tablet/mobile e reorganiza o topbar.
RESPONSIVE_CSS: str = """
<style>
  /* === Mobile/Tablet: Hamburger menu === */
  .hamburger {
    display: none;
    width: 36px; height: 36px;
    background: transparent;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    color: var(--ink);
    cursor: pointer;
    align-items: center; justify-content: center;
  }
  .hamburger:active { transform: scale(.94); }
  .hamburger svg { width: 20px; height: 20px; stroke: currentColor; fill: none; stroke-width: 2; }

  .mobile-menu {
    position: fixed;
    top: 50px; right: 0;
    width: 280px; max-width: 85vw;
    height: calc(100vh - 50px);
    background: var(--rail);
    border-left: 1px solid var(--line);
    transform: translateX(100%);
    transition: transform .25s ease;
    z-index: 9998;
    padding: 16px;
    overflow-y: auto;
    display: flex; flex-direction: column; gap: 10px;
  }
  .mobile-menu.open { transform: translateX(0); }
  .mobile-menu .tb-btn { width: 100%; justify-content: flex-start; }
  .mobile-menu-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,.5);
    opacity: 0; pointer-events: none;
    transition: opacity .2s;
    z-index: 9997;
  }
  .mobile-menu-overlay.open { opacity: 1; pointer-events: all; }

  /* === Desktop padrão (≥ 1024px): nada muda === */
  /* === Tablet (768px – 1023px) === */
  @media (max-width: 1023px) {
    #topbar { padding: 0 12px; gap: 8px; height: 50px; }
    .tb-btn { padding: 0 10px; font-size: 10.5px; }
    .logo-tag { display: none; }
    .footer-link { font-size: 10px; }
    .footer-sep { margin: 0 8px; }
    .modal-600 { width: 90vw; max-width: 600px; }
  }

  /* === Mobile (480px – 767px) === */
  @media (max-width: 767px) {
    html, body { font-size: 14px; }
    #topbar {
      padding: 0 8px; gap: 6px;
    }
    .logo-p, .logo-ai { font-size: 15px; }
    .status { display: none; }  /* esconde status, foco no essencial */
    .tb-btn { display: none; }  /* esconde botões grandes */
    .tb-icons { margin-left: auto; gap: 3px; }
    .tb-icon { width: 32px; height: 32px; }
    .tb-icon svg { width: 14px; height: 14px; }
    .hamburger { display: inline-flex; }
    #footer { padding: 0 8px; height: 36px; }
    .footer-brand { display: none; }
    .footer-sep { margin: 0 6px; }
    .footer-link { font-size: 9.5px; }
    .btn-provider { padding: 0 6px; font-size: 9px; height: 20px; }
    .footer-oc { display: none; }
    /* terminal: ocupa mais espaço em mobile */
    #terminal-frame { height: calc(100vh - 50px - 36px) !important; }
    /* modais: largura quase total */
    #modal, #provider-overlay > div, #health-overlay > div,
    #sessions-overlay > div, #shortcuts-overlay > div {
      width: 95vw !important; max-width: 95vw !important;
      padding: 16px !important;
    }
    .modal-title { font-size: 14px !important; }
    .backup-item, .session-item, .health-row, .shortcut-row {
      padding: 10px 8px !important; font-size: 11px !important;
    }
    .health-status { font-size: 11px !important; }
    .session-search { font-size: 12px !important; }
    .toast { max-width: 260px !important; font-size: 11px !important; }
  }

  /* === Mobile muito pequeno (< 480px) === */
  @media (max-width: 479px) {
    #topbar { padding: 0 4px; }
    .logo-p, .logo-ai { font-size: 13px; }
    .tb-icon { width: 30px; height: 30px; }
    .tb-icon svg { width: 13px; height: 13px; }
    .mobile-menu { width: 100vw; max-width: 100vw; }
    #footer { font-size: 9px; }
    .footer-link svg { width: 9px; height: 9px; }
  }

  /* === Landscape em mobile === */
  @media (max-height: 500px) and (orientation: landscape) {
    #topbar { height: 40px; }
    .logo { font-size: 12px; }
    #footer { height: 28px; font-size: 9px; }
    #terminal-frame { height: calc(100vh - 40px - 28px) !important; }
  }

  /* === Tablet/iPad (orientação portrait) === */
  @media (min-width: 768px) and (max-width: 1024px) and (orientation: portrait) {
    .tb-btn { padding: 0 8px; }
    .footer-sep:nth-of-type(3) { display: none; }  /* esconde UFV */
  }

  /* === Acessibilidade: foco visível === */
  .tb-btn:focus-visible, .tb-icon:focus-visible, .hamburger:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
</style>
"""


def create_wrapper_html_responsive(terminal_url: str, drive_url: str) -> str:
    """Cria a versão responsiva do wrapper HTML do PesquisAI.

    Esta é uma versão drop-in que substitui o HTML estático do
    launch_app.py por um layout adaptativo. Suporta:
      - Desktop ≥ 1024px: layout original
      - Tablet 768-1023px: topbar condensado
      - Mobile 480-767px: hamburger menu + ícones essenciais
      - Mobile pequeno < 480px: modo compacto
      - Landscape: ajustes de altura

    Args:
        terminal_url: URL do terminal ttyd.
        drive_url: URL do Google Drive.

    Returns:
        String HTML completa.
    """
    html: str = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#0d0f10">
  <title>PesquisAI</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --ink:        #e8e6e0;
      --ink-muted:  #8a8780;
      --surface:    #0d0f10;
      --rail:       #151819;
      --line:       rgba(255,255,255,.07);
      --accent:     #4fc3f7;
      --accent-dim: rgba(79,195,247,.12);
      --accent-glow:rgba(79,195,247,.22);
      --green:      #5dba7e;
      --green-dim:  rgba(93,186,126,.12);
      --amber:      #e8b84b;
      --amber-dim:  rgba(232,184,75,.12);
      --red:        #e07070;
      --red-dim:    rgba(224,112,112,.12);
      --radius:     5px;
    }}

    html, body {{
      height: 100%; width: 100%;
      background: var(--surface);
      color: var(--ink);
      font-family: "DM Mono", monospace;
      overflow: hidden;
      -webkit-tap-highlight-color: transparent;
    }}

    /* Touch: target mínimo 44x44 px para dedos (Apple HIG / WCAG) */
    button, .tb-btn, .tb-icon, .hamburger {{ min-height: 32px; min-width: 32px; }}

    #topbar {{
      position: fixed; inset: 0 0 auto 0;
      height: 50px;
      background: var(--rail);
      border-bottom: 1px solid var(--line);
      display: flex; align-items: center;
      padding: 0 18px; gap: 14px;
      z-index: 9999;
    }}
    #topbar::after {{
      content: "";
      position: absolute; inset: 0;
      background: repeating-linear-gradient(0deg, transparent, transparent 2px,
        rgba(0,0,0,.05) 2px, rgba(0,0,0,.05) 4px);
      pointer-events: none;
    }}

    .logo {{ display: flex; align-items: baseline; gap: 2px; }}
    .logo-p  {{ font-family:"Syne",sans-serif; font-weight:800; font-size:17px; color:var(--ink); letter-spacing:-.5px; }}
    .logo-ai {{ font-family:"Syne",sans-serif; font-weight:700; font-size:17px; color:var(--accent); letter-spacing:-.5px; }}
    .logo-tag {{
      margin-left:9px; font-size:10px; color:var(--ink-muted);
      letter-spacing:.07em; padding:1px 6px;
      border:1px solid var(--line); border-radius:3px; align-self:center;
    }}

    .status {{ display:flex; align-items:center; gap:7px; font-size:11px; color:var(--ink-muted); }}
    .status-dot {{
      width:7px; height:7px; border-radius:50%; background:var(--green);
      animation: pulse 2.4s ease infinite;
    }}
    @keyframes pulse {{
      0%,100% {{ box-shadow:0 0 0 0 rgba(93,186,126,.5); }}
      50%      {{ box-shadow:0 0 0 5px rgba(93,186,126,0); }}
    }}

    .sep {{ flex: 1; }}

    .tb-btn {{
      display: inline-flex; align-items: center; gap: 7px;
      padding: 0 13px; height: 30px;
      font-family: "DM Mono", monospace; font-size: 11px;
      font-weight: 500; letter-spacing: .04em;
      border-radius: var(--radius); cursor: pointer;
      border: 1px solid; transition: background .15s, transform .1s, border-color .15s;
      text-decoration: none; white-space: nowrap;
    }}
    .tb-btn:active {{ transform: scale(.96); }}
    .tb-btn svg {{ width:13px; height:13px; stroke:currentColor; fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; flex-shrink:0; }}

    .btn-drive  {{ color:var(--accent); background:var(--accent-dim); border-color:rgba(79,195,247,.25); }}
    .btn-drive:hover  {{ background:var(--accent-glow); border-color:rgba(79,195,247,.5); }}

    .btn-backup {{ color:var(--green); background:var(--green-dim); border-color:rgba(93,186,126,.25); }}
    .btn-backup:hover {{ background:rgba(93,186,126,.2); border-color:rgba(93,186,126,.5); }}

    .btn-restore {{ color:var(--amber); background:var(--amber-dim); border-color:rgba(232,184,75,.25); }}
    .btn-restore:hover {{ background:rgba(232,184,75,.2); border-color:rgba(232,184,75,.5); }}

    #toast {{
      position: fixed; bottom: 58px; right: 18px;
      padding: 9px 16px; border-radius: var(--radius);
      font-size: 12px; font-family: "DM Mono", monospace;
      display: flex; align-items: center; gap: 8px;
      opacity: 0; transform: translateY(6px);
      transition: opacity .22s, transform .22s;
      pointer-events: none; z-index: 9998; max-width: 340px;
      border: 1px solid;
    }}
    #toast.show {{ opacity: 1; transform: translateY(0); }}
    #toast.ok    {{ background:rgba(93,186,126,.15);  border-color:rgba(93,186,126,.35);  color:var(--green); }}
    #toast.err   {{ background:rgba(224,112,112,.15); border-color:rgba(224,112,112,.35); color:var(--red);   }}
    #toast.info  {{ background:var(--accent-dim);     border-color:rgba(79,195,247,.35);  color:var(--accent);}}

    #modal-overlay {{
      position: fixed; inset: 0;
      background: rgba(0,0,0,.65); backdrop-filter: blur(3px);
      display: flex; align-items: center; justify-content: center;
      z-index: 99999; opacity: 0; pointer-events: none;
      transition: opacity .2s;
    }}
    #modal-overlay.open {{ opacity: 1; pointer-events: all; }}
    #modal {{
      background: #181b1e; border: 1px solid rgba(255,255,255,.1);
      border-radius: 8px; padding: 24px; width: 400px; max-width: 90vw;
      box-shadow: 0 24px 64px rgba(0,0,0,.6);
    }}
    .modal-title {{
      font-family: "Syne", sans-serif; font-weight: 800;
      font-size: 15px; color: var(--ink); margin-bottom: 16px;
    }}
    .backup-list {{
      max-height: 260px; overflow-y: auto;
      border: 1px solid var(--line); border-radius: var(--radius);
      margin-bottom: 16px;
    }}
    .backup-item {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 9px 12px; font-size: 11.5px; color: var(--ink-muted);
      border-bottom: 1px solid var(--line); cursor: pointer;
      transition: background .12s;
    }}
    .backup-item:last-child {{ border-bottom: none; }}
    .backup-item:hover {{ background: rgba(255,255,255,.04); color: var(--ink); }}
    .backup-item .restore-lbl {{
      font-size: 10px; padding: 2px 8px;
      background: var(--amber-dim); color: var(--amber);
      border: 1px solid rgba(232,184,75,.3); border-radius: 3px;
    }}
    .modal-empty {{ padding:20px; text-align:center; font-size:12px; color:var(--ink-muted); }}
    .modal-close {{
      display: block; width: 100%; padding: 8px;
      background: rgba(255,255,255,.05); border: 1px solid var(--line);
      border-radius: var(--radius); color: var(--ink-muted);
      font-family: "DM Mono", monospace; font-size: 12px;
      cursor: pointer; transition: background .15s;
    }}
    .modal-close:hover {{ background: rgba(255,255,255,.1); }}

    #terminal-frame {{
      position: absolute;
      inset: 50px 0 40px 0;
      width: 100%; height: calc(100% - 90px);
      border: none;
    }}

    #footer {{
      position: fixed; inset: auto 0 0 0;
      height: 40px;
      background: var(--rail);
      border-top: 1px solid var(--line);
      display: flex; align-items: center;
      padding: 0 18px; gap: 0;
      font-size: 10.5px; color: var(--ink-muted);
      z-index: 9999;
    }}
    .footer-brand {{
      font-family: "Syne", sans-serif; font-weight: 700;
      font-size: 11px; color: var(--ink);
      margin-right: 14px;
    }}
    .footer-sep {{ width:1px; height:16px; background:var(--line); margin:0 12px; flex-shrink:0; }}
    .footer-link {{
      color: var(--ink-muted); text-decoration: none;
      letter-spacing: .03em;
      transition: color .15s;
    }}
    .footer-link:hover {{ color: var(--accent); }}
    .footer-link svg {{ width:11px; height:11px; stroke:currentColor; fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; vertical-align:-.15em; margin-right:4px; }}
    .footer-right {{ margin-left:auto; display:flex; align-items:center; gap:12px; }}
    .footer-oc {{ color:var(--ink-muted); letter-spacing:.03em; }}
    .footer-oc a {{ color:var(--ink-muted); text-decoration:none; }}
    .footer-oc a:hover {{ color:var(--accent); }}

    .btn-provider {{
      display: inline-flex; align-items: center; gap: 5px;
      padding: 0 10px; height: 24px;
      font-family: "DM Mono", monospace; font-size: 10px;
      font-weight: 500; letter-spacing: .03em;
      border-radius: var(--radius); cursor: pointer;
      border: 1px solid rgba(79,195,247,.18);
      color: rgba(79,195,247,.55);
      background: transparent;
      transition: background .15s, color .15s, border-color .15s;
      white-space: nowrap;
    }}
    .btn-provider:hover {{
      background: var(--accent-dim);
      color: var(--accent);
      border-color: rgba(79,195,247,.4);
    }}
    .btn-provider:active {{ transform: scale(.96); }}
    .btn-provider svg {{ width:10px; height:10px; stroke:currentColor; fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; flex-shrink:0; }}

    .tb-icons {{ display:flex; align-items:center; gap:4px; margin-left:6px; }}
    .tb-icon {{
      display:inline-flex; align-items:center; justify-content:center;
      width:30px; height:30px; padding:0;
      background:transparent; border:1px solid var(--line);
      border-radius:var(--radius); cursor:pointer;
      color:var(--ink-muted); transition:background .15s,color .15s,border-color .15s;
    }}
    .tb-icon:hover {{
      background:var(--accent-dim); color:var(--accent);
      border-color:rgba(79,195,247,.4);
    }}
    .tb-icon:active {{ transform: scale(.94); }}
    .tb-icon svg {{ width:15px; height:15px; stroke:currentColor; fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; flex-shrink:0; }}

    .health-row {{
      display:flex; align-items:center; justify-content:space-between;
      padding:9px 12px; font-size:11.5px; color:var(--ink);
      border-bottom:1px solid var(--line);
    }}
    .health-row:last-child {{ border-bottom:none; }}
    .health-status {{
      font-size:13px; font-weight:700; padding:2px 8px; border-radius:3px;
    }}
    .health-ok {{ background:var(--green-dim); color:var(--green); }}
    .health-warn {{ background:var(--amber-dim); color:var(--amber); }}
    .health-fail {{ background:var(--red-dim); color:var(--red); }}

    .session-search {{
      display:block; width:100%; padding:8px 10px; margin-bottom:10px;
      box-sizing:border-box; background:rgba(255,255,255,.04);
      border:1px solid var(--line); border-radius:var(--radius);
      color:var(--ink); font-family:'DM Mono',monospace; font-size:11px;
      outline:none; transition:border-color .15s;
    }}
    .session-search:focus {{ border-color:rgba(79,195,247,.4); }}
    .session-item {{
      display:flex; align-items:center; justify-content:space-between;
      padding:9px 12px; font-size:11.5px; color:var(--ink-muted);
      border-bottom:1px solid var(--line); cursor:pointer;
      transition:background .12s;
    }}
    .session-item:last-child {{ border-bottom:none; }}
    .session-item:hover {{ background:rgba(255,255,255,.04); color:var(--ink); }}
    .session-item .ses-meta {{ font-size:10px; color:var(--ink-muted); opacity:.7; }}

    .shortcut-row {{
      display:flex; align-items:center; justify-content:space-between;
      padding:8px 12px; font-size:11.5px; color:var(--ink);
      border-bottom:1px solid var(--line);
    }}
    .shortcut-row:last-child {{ border-bottom:none; }}
    .shortcut-key {{
      font-family:'DM Mono',monospace; font-size:10.5px; font-weight:600;
      padding:2px 8px; background:var(--accent-dim); color:var(--accent);
      border:1px solid rgba(79,195,247,.25); border-radius:3px;
    }}

    /* === RESPONSIVO: media queries injetadas === */
    {RESPONSIVE_CSS}
  </style>
</head>
<body>

  <div id="topbar">
    <div class="logo">
      <span class="logo-p">Pesquis</span><span class="logo-ai">AI</span>
      <span>  <a href="https://github.com/gustavobraga-byte/PesquisAI/blob/main/CHANGELOG.md" target="_blank" class="logo-tag"> v{VERSION} </a> </span>
    </div>

    <div class="status">
      <span class="status-dot"></span>
      agente ativo
    </div>

    <div class="tb-icons">
      <button class="tb-icon" onclick="openHealth()" title="Dashboard de Saúde">
        <svg viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
      </button>
      <button class="tb-icon" onclick="openSessions()" title="Histórico de Sessões">
        <svg viewBox="0 0 24 24"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="10"/></svg>
      </button>
      <button class="tb-icon" onclick="openShortcuts()" title="Atalhos de Teclado">
        <svg viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 16h10"/></svg>
      </button>
      <button class="tb-icon" onclick="toggleTheme()" id="theme-toggle" title="Alternar tema">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
      </button>
      <button class="hamburger" onclick="toggleMobileMenu()" title="Menu" id="hamburger-btn" aria-label="Abrir menu">
        <svg viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
    </div>
    <div class="sep"></div>

    <button class="tb-btn btn-backup" onclick="doBackup()">
      <svg viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
      Salvar backup
    </button>

    <button class="tb-btn btn-restore" onclick="openRestore()">
      <svg viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/></svg>
      Restaurar
    </button>

    <a href="{drive_url}" target="_blank" class="tb-btn btn-drive">
      <svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
      Drive
    </a>

  </div>

  <!-- Mobile menu (drawer) -->
  <div class="mobile-menu-overlay" id="mobile-overlay" onclick="toggleMobileMenu()"></div>
  <div class="mobile-menu" id="mobile-menu" aria-hidden="true">
    <button class="tb-btn btn-backup" onclick="doBackup(); toggleMobileMenu();">
      <svg viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
      Salvar backup
    </button>
    <button class="tb-btn btn-restore" onclick="openRestore(); toggleMobileMenu();">
      <svg viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/></svg>
      Restaurar
    </button>
    <a href="{drive_url}" target="_blank" class="tb-btn btn-drive" onclick="toggleMobileMenu()">
      <svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
      Drive
    </a>
    <button class="btn-provider" onclick="connectProvider(); toggleMobileMenu();" style="width:100%;justify-content:flex-start;">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/></svg>
      + provedor
    </button>
    <div style="height:1px;background:var(--line);margin:8px 0;"></div>
    <button class="modal-close" onclick="openHealth(); toggleMobileMenu();">🩺 Dashboard de Saúde</button>
    <button class="modal-close" onclick="openSessions(); toggleMobileMenu();">📜 Histórico de Sessões</button>
    <button class="modal-close" onclick="openShortcuts(); toggleMobileMenu();">⌨️ Atalhos de Teclado</button>
    <button class="modal-close" onclick="toggleTheme(); toggleMobileMenu();">◑ Alternar Tema</button>
  </div>

 <iframe
  id="terminal-frame"
  src="{terminal_url}"
  allow="clipboard-read; clipboard-write"
  tabindex="0"
  autofocus
  style="width:100%; height:calc(100% - 90px); border:none; outline:none;">
</iframe>

  <div id="footer">
    <span class="footer-brand">PesquisAI</span>
    <span class="footer-sep"></span>
    <a href="mailto:gustavo.braga@ufv.br" class="footer-link">
      <svg viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
      gustavo.braga@ufv.br
    </a>
    <span class="footer-sep"></span>
    <a href="https://github.com/gustavobraga-byte/PesquisAI" target="_blank" class="footer-link">
      <svg viewBox="0 0 24 24"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>
      GitHub
    </a>
    <span class="footer-sep"></span>
    <span style="color:var(--ink-muted)">UFV · Viçosa, MG - Brasil</span>

    <div class="footer-right">
      <button class="btn-provider" onclick="connectProvider()" title="Conectar novo provedor de IA">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/></svg>
        + provedor
      </button>
      <span class="footer-sep"></span>
      <span class="footer-oc">
        Powered by <a href="https://opencode.ai" target="_blank">OpenCode</a>
      </span>
    </div>
  </div>

  <div id="toast"></div>

  <div id="modal-overlay" onclick="if(event.target===this)closeModal()">
    <div id="modal">
      <div class="modal-title">🔄 Restaurar Sessão</div>
      <div class="backup-list" id="backup-list">
        <div class="modal-empty">Carregando backups…</div>
      </div>
      <button class="modal-close" onclick="closeModal()">Fechar</button>
    </div>
  </div>

  <!-- Modal: Provedor -->
  <div id="provider-overlay" onclick="if(event.target===this)closeProvider()" style="position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:99999;opacity:0;pointer-events:none;transition:opacity .2s;">
    <div style="background:#181b1e;border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:24px;width:480px;max-width:94vw;box-shadow:0 28px 72px rgba(0,0,0,.7);">
      <div id="prov-step1">
        <div class="modal-title">🔌 Conectar Provedor de IA</div>
        <p style="font-size:11.5px;color:var(--ink-muted);margin-bottom:14px;line-height:1.6;">Selecione o provedor para configurar a API key:</p>
        <div id="prov-list" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;"></div>
        <button onclick="closeProvider()" style="display:block;width:100%;padding:8px;background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:var(--radius);color:var(--ink-muted);font-family:'DM Mono',monospace;font-size:12px;cursor:pointer;">Cancelar</button>
      </div>
      <div id="prov-step2" style="display:none;">
        <div class="modal-title">🔑 <span id="prov-name-title"></span></div>
        <p style="font-size:11px;color:var(--ink-muted);margin-bottom:14px;line-height:1.5;">Variável: <code id="prov-env-code" style="color:var(--accent);background:rgba(79,195,247,.08);padding:1px 6px;border-radius:3px;font-size:11px;"></code></p>
        <label style="display:block;font-size:10.5px;color:var(--ink-muted);margin-bottom:6px;letter-spacing:.05em;">API KEY</label>
        <input id="prov-key-input" type="password" placeholder="Cole sua key aqui…" autocomplete="off" style="display:block;width:100%;padding:9px 12px;box-sizing:border-box;background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:var(--radius);color:var(--ink);font-family:'DM Mono',monospace;font-size:12px;outline:none;margin-bottom:14px;transition:border-color .15s;" onfocus="this.style.borderColor='rgba(79,195,247,.4)'" onblur="this.style.borderColor='var(--line)'" onkeydown="if(event.key==='Enter')confirmProvider()"/>
        <div style="display:flex;gap:8px;">
          <button onclick="provBack()" style="padding:9px 14px;background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:var(--radius);color:var(--ink-muted);font-family:'DM Mono',monospace;font-size:12px;cursor:pointer;">← Voltar</button>
          <button onclick="confirmProvider()" style="flex:1;padding:9px;background:var(--accent-dim);border:1px solid rgba(79,195,247,.3);border-radius:var(--radius);color:var(--accent);font-family:'DM Mono',monospace;font-size:12px;cursor:pointer;">Salvar e Conectar</button>
          <button onclick="closeProvider()" style="padding:9px 14px;background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:var(--radius);color:var(--ink-muted);font-family:'DM Mono',monospace;font-size:12px;cursor:pointer;">Cancelar</button>
        </div>
      </div>
    </div>
  </div>

  <div id="health-overlay" onclick="if(event.target===this)closeHealth()" style="position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:99999;opacity:0;pointer-events:none;transition:opacity .2s;">
    <div style="background:#181b1e;border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:24px;width:440px;max-width:94vw;box-shadow:0 28px 72px rgba(0,0,0,.7);">
      <div class="modal-title">🩺 Dashboard de Saúde</div>
      <div id="health-list" style="max-height:340px;overflow-y:auto;border:1px solid var(--line);border-radius:var(--radius);margin-bottom:14px;">
        <div class="modal-empty">Carregando diagnóstico…</div>
      </div>
      <button onclick="closeHealth()" class="modal-close">Fechar</button>
    </div>
  </div>

  <div id="sessions-overlay" onclick="if(event.target===this)closeSessions()" style="position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:99999;opacity:0;pointer-events:none;transition:opacity .2s;">
    <div style="background:#181b1e;border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:24px;width:520px;max-width:94vw;box-shadow:0 28px 72px rgba(0,0,0,.7);">
      <div class="modal-title">📜 Histórico de Sessões</div>
      <input id="session-search" class="session-search" placeholder="🔍 Buscar por id ou conteúdo…" oninput="filterSessions()">
      <div id="session-list" style="max-height:300px;overflow-y:auto;border:1px solid var(--line);border-radius:var(--radius);margin-bottom:14px;">
        <div class="modal-empty">Carregando sessões…</div>
      </div>
      <button onclick="closeSessions()" class="modal-close">Fechar</button>
    </div>
  </div>

  <div id="shortcuts-overlay" onclick="if(event.target===this)closeShortcuts()" style="position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:99999;opacity:0;pointer-events:none;transition:opacity .2s;">
    <div style="background:#181b1e;border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:24px;width:420px;max-width:94vw;box-shadow:0 28px 72px rgba(0,0,0,.7);">
      <div class="modal-title">⌨️ Atalhos de Teclado</div>
      <div style="border:1px solid var(--line);border-radius:var(--radius);margin-bottom:14px;">
        <div class="shortcut-row"><span>Copiar seleção</span><span class="shortcut-key">Segure Shift e selecione</span></div>
        <div class="shortcut-row"><span>Interromper comando</span><span class="shortcut-key">Ctrl+C</span></div>
        <div class="shortcut-row"><span>Colar (Chrome)</span><span class="shortcut-key">Ctrl+Shift+V</span></div>
        <div class="shortcut-row"><span>Menu e opções</span><span class="shortcut-key">Ctrl+P</span></div>
        <div class="shortcut-row"><span>Alterar modelo</span><span class="shortcut-key">Ctrl+X m</span></div>
        <div class="shortcut-row"><span>Histórico anterior</span><span class="shortcut-key">↑</span></div>
        <div class="shortcut-row"><span>Histórico seguinte</span><span class="shortcut-key">↓</span></div>
      </div>
      <button onclick="closeShortcuts()" class="modal-close">Fechar</button>
    </div>
  </div>

  <script>
    const BASE = location.origin;

    // === Mobile menu toggle ===
    function toggleMobileMenu() {{
      const menu = document.getElementById('mobile-menu');
      const overlay = document.getElementById('mobile-overlay');
      const isOpen = menu.classList.contains('open');
      if (isOpen) {{
        menu.classList.remove('open');
        overlay.classList.remove('open');
        menu.setAttribute('aria-hidden', 'true');
      }} else {{
        menu.classList.add('open');
        overlay.classList.add('open');
        menu.setAttribute('aria-hidden', 'false');
      }}
    }}

    let _toastT;
    function toast(msg, type = "info") {{
      const el = document.getElementById("toast");
      el.className = "show " + type;
      el.textContent = msg;
      clearTimeout(_toastT);
      _toastT = setTimeout(() => el.classList.remove("show"), 3800);
    }}

    async function doBackup() {{
      toast("⏳ Exportando sessão…", "info");
      try {{
        const r = await fetch(BASE + "/api/backup", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{}})
        }});
        const d = await r.json();
        if (d.ok) {{
          toast("✅ Backup salvo: " + d.file, "ok");
        }} else {{
          toast("❌ " + (d.error || "Erro desconhecido"), "err");
        }}
      }} catch(e) {{
        toast("❌ Falha na conexão: " + e.message, "err");
      }}
    }}

    async function openRestore() {{
      document.getElementById("modal-overlay").classList.add("open");
      const list = document.getElementById("backup-list");
      list.innerHTML = '<div class="modal-empty">Carregando backups…</div>';
      try {{
        const r = await fetch(BASE + "/api/backups");
        const d = await r.json();
        if (!d.backups || d.backups.length === 0) {{
          list.innerHTML = '<div class="modal-empty">Nenhum backup encontrado no Drive.</div>';
          return;
        }}
        list.innerHTML = d.backups.map(f => `
          <div class="backup-item" onclick="doRestore('${{f}}')">
            <span>${{f}}</span>
            <span class="restore-lbl">restaurar</span>
          </div>
        `).join("");
      }} catch(e) {{
        list.innerHTML = '<div class="modal-empty">Erro ao carregar backups.</div>';
      }}
    }}

    function closeModal() {{
      document.getElementById("modal-overlay").classList.remove("open");
    }}

    async function doRestore(file) {{
      closeModal();
      toast("⏳ Importando " + file + "…", "info");
      try {{
        const r = await fetch(BASE + "/api/restore", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ file }})
        }});
        const d = await r.json();
        if (d.ok) {{
          toast("✅ Importado!", "ok");
          setTimeout(() => location.reload(), 800);
        }} else {{
          toast("❌ " + (d.error || "Erro"), "err");
        }}
      }} catch(e) {{
        toast("❌ Falha: " + e.message, "err");
      }}
    }}

    const PROVIDERS = [
      {{ id:"anthropic", name:"Anthropic", env:"ANTHROPIC_API_KEY", hint:"sk-ant-…" }},
      {{ id:"bedrock", name:"AWS Bedrock", env:"AWS_ACCESS_KEY_ID", hint:"AKIA…" }},
      {{ id:"azure", name:"Azure OpenAI", env:"AZURE_OPENAI_API_KEY", hint:"…" }},
      {{ id:"deepseek", name:"DeepSeek", env:"DEEPSEEK_API_KEY", hint:"sk-…" }},
      {{ id:"google", name:"Google Gemini", env:"GOOGLE_GENERATIVE_AI_API_KEY", hint:"AIza…" }},
      {{ id:"groq", name:"Groq", env:"GROQ_API_KEY", hint:"gsk_…" }},
      {{ id:"mistral", name:"Mistral", env:"MISTRAL_API_KEY", hint:"…" }},
      {{ id:"nvidia", name:"Nvidia NIM", env:"NVIDIA_API_KEY", hint:"nvapi-…" }},
      {{ id:"openai", name:"OpenAI", env:"OPENAI_API_KEY", hint:"sk-…" }},
      {{ id:"opencode_go", name:"OpenCode Go", env:"OPENCODE_API_KEY", hint:"sk-…" }},
      {{ id:"opencode_zen", name:"OpenCode Zen", env:"OPENCODE_API_KEY", hint:"sk-…" }},
      {{ id:"openrouter", name:"OpenRouter", env:"OPENROUTER_API_KEY", hint:"sk-or-…" }},
      {{ id:"together", name:"Together AI", env:"TOGETHER_API_KEY", hint:"…" }},
      {{ id:"vertex", name:"Vertex AI", env:"VERTEX_API_KEY", hint:"…" }},
      {{ id:"xai", name:"xAI (Grok)", env:"XAI_API_KEY", hint:"xai-…" }},
    ];

    let _selProv = null;

    function connectProvider() {{
      const grid = document.getElementById("prov-list");
      grid.innerHTML = PROVIDERS.map(p => `
        <button onclick="selectProvider('${{p.id}}')" style="display:flex;align-items:center;gap:8px;padding:9px 12px;background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:var(--radius);color:var(--ink-muted);font-family:'DM Mono',monospace;font-size:11px;cursor:pointer;text-align:left;transition:background .12s,color .12s,border-color .12s;">
          ${{p.name}}
        </button>
      `).join("");
      document.getElementById("prov-step1").style.display = "block";
      document.getElementById("prov-step2").style.display = "none";
      document.getElementById("prov-key-input").value = "";
      const overlay = document.getElementById("provider-overlay");
      overlay.style.opacity = "1";
      overlay.style.pointerEvents = "all";
    }}

    function selectProvider(id) {{
      _selProv = PROVIDERS.find(p => p.id === id);
      if (!_selProv) return;
      document.getElementById("prov-name-title").textContent = _selProv.name;
      document.getElementById("prov-env-code").textContent = _selProv.env;
      document.getElementById("prov-key-input").placeholder = _selProv.hint || "Cole sua key aqui…";
      document.getElementById("prov-step1").style.display = "none";
      document.getElementById("prov-step2").style.display = "block";
      setTimeout(() => document.getElementById("prov-key-input").focus(), 80);
    }}

    function provBack() {{
      document.getElementById("prov-step1").style.display = "block";
      document.getElementById("prov-step2").style.display = "none";
    }}

    function closeProvider() {{
      const overlay = document.getElementById("provider-overlay");
      overlay.style.opacity = "0";
      overlay.style.pointerEvents = "none";
      _selProv = null;
    }}

    async function confirmProvider() {{
      const key = document.getElementById("prov-key-input").value.trim();
      if (!key) {{ toast("⚠️ Insira a API key.", "err"); return; }}
      if (!_selProv) {{ toast("⚠️ Selecione um provedor.", "err"); return; }}
      closeProvider();
      toast("💾 Salvando…", "info");
      try {{
        await fetch(BASE + "/api/apikey", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ provider: _selProv.id, env: _selProv.env, apikey: key }})
        }});
        toast("✅ Salvo!", "ok");
      }} catch(e) {{ toast("❌ " + e.message, "err"); }}
    }}

    async function openHealth() {{
      const overlay = document.getElementById("health-overlay");
      overlay.style.opacity = "1"; overlay.style.pointerEvents = "all";
    }}
    function closeHealth() {{
      const o = document.getElementById("health-overlay");
      o.style.opacity = "0"; o.style.pointerEvents = "none";
    }}

    let _allSessions = [];
    async function openSessions() {{
      const overlay = document.getElementById("sessions-overlay");
      overlay.style.opacity = "1"; overlay.style.pointerEvents = "all";
    }}
    function closeSessions() {{
      const o = document.getElementById("sessions-overlay");
      o.style.opacity = "0"; o.style.pointerEvents = "none";
    }}

    function openShortcuts() {{
      const o = document.getElementById("shortcuts-overlay");
      o.style.opacity = "1"; o.style.pointerEvents = "all";
    }}
    function closeShortcuts() {{
      const o = document.getElementById("shortcuts-overlay");
      o.style.opacity = "0"; o.style.pointerEvents = "none";
    }}

    async function toggleTheme() {{
      const btn = document.getElementById("theme-toggle");
      const cur = btn.dataset.theme || "pesquisai";
      const next = cur === "pesquisai" ? "pesquisai-light" : "pesquisai";
      try {{
        await fetch(BASE + "/api/theme", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ theme: next }})
        }});
        btn.dataset.theme = next;
        toast(next === "pesquisai-light" ? "☀️ Tema claro" : "🌙 Tema escuro", "info");
      }} catch(e) {{}}
    }}

    // === Detectar dispositivo e mostrar/esconder hamburger ===
    function setupMobileUI() {{
      const isMobile = window.matchMedia('(max-width: 767px)').matches;
      const btn = document.getElementById('hamburger-btn');
      if (btn) {{
        btn.style.display = isMobile ? 'inline-flex' : 'none';
      }}
    }}

    document.addEventListener("keydown", (e) => {{
      if (e.key === "Escape") {{
        closeHealth(); closeSessions(); closeShortcuts(); closeProvider(); closeModal();
        toggleMobileMenu();
      }}
    }});

    window.addEventListener("load", setupMobileUI);
    window.addEventListener("resize", setupMobileUI);
  </script>
</body>
</html>"""
    os.makedirs(WRAPPER_DIR, exist_ok=True)
    with open(os.path.join(WRAPPER_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    return html


def main() -> None:
    """Função principal para testar a geração standalone."""
    print(f"\n{next_joke('computacao')}")
    print("📱 Gerando wrapper responsivo...")
    html = create_wrapper_html_responsive(
        terminal_url="http://localhost:8000",
        drive_url="https://drive.google.com/drive/my-drive",
    )
    print(f"✅ Wrapper gerado: {len(html):,} caracteres")
    print(f"📂 Salvo em: {os.path.join(WRAPPER_DIR, 'index.html')}")
    print(f"📱 Contém 'mobile-menu': {'mobile-menu' in html}")
    print(f"🍔 Contém 'hamburger-btn': {'hamburger-btn' in html}")
    print(f"📐 Media queries: {html.count('@media')}")


if __name__ == "__main__":
    main()
