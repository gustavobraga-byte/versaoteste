"""
__version__.py — Fonte única de versão do PesquisAI v0.4.2.1.

Este repositório contém o **PesquisAI release v0.4.2.1** + sandbox pessoal:

Estrutura do repositório:
  /                       # PesquisAI release v0.4.2.1 (raiz)
  ├── agents/             # AGENTS.md multilíngues (4 idiomas, v0.4.1)
  ├── docs/               # Documentação (CHANGELOG, PATCH, etc.)
  ├── grant_finder/       # Skill de busca de fomento
  ├── i18n/               # Módulo multilíngue
  ├── pesquisai/          # Módulo PesquisAI (v0.4.2.1 corrigido)
  ├── releases/v0.4.0/    # Release isolada completa
  ├── sandbox/            # 🏖️ Arquivos não-PesquisAI
  ├── sessions/           # Logs de sessão
  └── skills/             # Skills adicionais

Compatível com o PesquisAI principal (v0.2.1+).

═════════════════════════════════════════════════════════════════════════
Histórico de versões:
═════════════════════════════════════════════════════════════════════════
  v0.4.0  — Release inicial com agente de pesquisa
  v0.4.1  — UI Fixes (Responsive + Theme + Language)
            • 6 media queries + hamburger menu
            • toggleTheme() recarrega iframe ttyd
            • Dropdown 4 idiomas (pt_BR, en_US, es_ES, fr_FR)
  v0.4.2  — Footer Responsive + Multilingual AGENTS.md
            • Rodapé 100% responsivo (flex-wrap + 2 linhas)
            • Modal de Diretrizes com AGENTS.md multilíngue
            • Endpoint GET /api/agents?lang=xx_XX
  v0.4.2.1 — Ses_10a4: 3 correções da sessão do usuário
            • Tema CLARO: contraste corrigido nos 6 modais
              (background:#181b1e fixo → variável CSS .modal-shell)
            • Dashboard de Saúde: openHealth() faz fetch em /api/health
              e popula a lista com badges de status
            • Modal de Diretrizes renderiza markdown (marked.js +
              github-markdown-css) ao invés de mostrar o .md como texto cru
"""

# ── Versão semântica (SemVer) ──────────────────────────────────
__version__: str = "0.4.2.1"

# ── Metadados do release ───────────────────────────────────────
__release_date__: str = "2026-06-23"
__codename__: str = "ses_10a4 fixes (theme contrast + health + markdown)"

# ── Identidade do projeto ──────────────────────────────────────
__author__: str = "Gustavo Bastos Braga"
__author_email__: str = "gustavo.braga@ufv.br"
__institution__: str = "Universidade Federal de Viçosa (UFV)"
__registry__: str = "10356285004"
__repo_url__: str = "https://github.com/gustavobraga-byte/PesquisAI"
__license__: str = "MIT"

# ── Compatibilidade ────────────────────────────────────────────
__pesquisai_min_version__: str = "0.2.1"
__pesquisai_max_version__: str = "0.3.x"  # até próximo major

# ── Tema padrão (v0.4.2.1) ─────────────────────────────────────
__default_theme__: str = "pesquisai"  # 🌙 ESCURO (anti-flash CSS ativo)
__supported_themes__: list[str] = ["pesquisai", "pesquisai-light"]

# ── Componentes incluídos neste release ─────────────────────────
__components__: dict[str, str] = {
    "grant_finder": "0.1.0",
    "i18n": "0.2.0",
    "launch_app_responsive": "0.2.0",     # base responsiva
    "launch_app_responsive_v041": "0.1.0",  # drop-in patch v0.4.1
    "launch_app_responsive_v0421": "0.1.0",  # NOVO v0.4.2.1: 3 correções ses_10a4
    "agents_multilingual": "0.1.0",
    "agents_modal": "0.1.0",              # modal de Diretrizes com markdown
    "footer_responsive": "0.1.0",         # footer com flex-wrap + 2 linhas
}

# ── Idiomas suportados ─────────────────────────────────────────
__supported_languages__: list[str] = ["pt_BR", "en_US", "es_ES", "fr_FR"]

# ── Agências de fomento integradas ─────────────────────────────
__supported_grant_agencies__: list[str] = [
    # Brasil
    "CNPq", "CAPES", "FAPEMIG", "FAPESP", "FINEP",
    # Internacional
    "NIH", "NSF", "ERC", "Wellcome", "Horizon_Europe",
]

# ── Endpoints REST disponíveis ─────────────────────────────────
__api_endpoints__: list[str] = [
    "GET  /",                       # Wrapper HTML
    "GET  /api/sessions",           # Lista sessões
    "GET  /api/backups",            # Lista backups do Drive
    "GET  /api/health",             # Diagnóstico do sistema
    "GET  /api/theme",              # Tema atual
    "POST /api/theme",              # Persiste tema
    "GET  /api/diagnose",           # Diagnóstico completo
    "GET  /api/debug",              # Debug de chaves
    "GET  /api/apikey",             # Lista/máscara chaves
    "POST /api/apikey",             # Salva chave criptografada
    "POST /api/apikey/apply",       # Aplica chaves no env
    "POST /api/run_terminal",       # Executa comando no ttyd
    "POST /api/backup",             # Exporta sessão para Drive
    "POST /api/restore",            # Importa sessão do Drive
    "GET  /api/agents?lang=xx_XX",  # v0.4.2: serve AGENTS.md no idioma
]


def get_version() -> str:
    """Retorna a versão formatada para exibição."""
    return f"v{__version__} ({__codename__})"


def get_version_short() -> str:
    """Retorna apenas o número da versão."""
    return __version__


def get_full_metadata() -> dict[str, str]:
    """Retorna todos os metadados como dict (útil para logging/diagnóstico)."""
    return {
        "version": __version__,
        "release_date": __release_date__,
        "codename": __codename__,
        "author": __author__,
        "email": __author_email__,
        "institution": __institution__,
        "registry": __registry__,
        "license": __license__,
        "languages": ", ".join(__supported_languages__),
        "agencies": ", ".join(__supported_grant_agencies__),
        "endpoints_count": len(__api_endpoints__),
    }
