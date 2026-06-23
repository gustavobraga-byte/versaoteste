"""
__version__.py — Fonte única de versão do PesquisAI v0.4.2.

Este repositório contém o **PesquisAI release v0.4.2** + sandbox pessoal:

Estrutura do repositório:
  /                       # PesquisAI release v0.4.2 (raiz)
  ├── agents/             # AGENTS.md multilíngues (4 idiomas)
  ├── docs/               # Documentação (CHANGELOG, PATCH, etc.)
  ├── grant_finder/       # Skill de busca de fomento
  ├── i18n/               # Módulo multilíngue
  ├── pesquisai/          # Módulo PesquisAI (v0.4.2 corrigido)
  ├── releases/v0.4.0/    # Release isolada completa
  ├── sandbox/            # 🏖️ Arquivos não-PesquisAI
  ├── sessions/           # Logs de sessão
  └── skills/             # Skills adicionais

Compatível com o PesquisAI principal (v0.2.1+).

Novidades da v0.4.2 (2026-06-23):
  🐛 Rodapé responsivo (flex-wrap + 2 linhas + media queries)
  🐛 Modal de Diretrizes com AGENTS.md multilíngue
  🆕 Endpoint GET /api/agents?lang=xx_XX
  🆕 Cache client-side do AGENTS.md por idioma
  🆕 Botões: 📋 Copiar · ↻ Recarregar · 🔗 Ver fonte
"""

# ── Versão semântica (SemVer) ──────────────────────────────────
__version__: str = "0.4.2"

# ── Metadados do release ───────────────────────────────────────
__release_date__: str = "2026-06-23"
__codename__: str = "Footer Responsive + Multilingual AGENTS.md"

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

# ── Tema padrão (v0.4.1) ──────────────────────────────────────
__default_theme__: str = "pesquisai"  # 🌙 ESCURO (anti-flash CSS ativo)
__supported_themes__: list[str] = ["pesquisai", "pesquisai-light"]

# ── Componentes incluídos neste release ─────────────────────────
__components__: dict[str, str] = {
    "grant_finder": "0.1.0",
    "i18n": "0.2.0",
    "launch_app_responsive": "0.2.0",  # 0.1.0 → 0.2.0 (3 correções aplicadas)
    "launch_app_responsive_v041": "0.2.0",  # v0.4.1 → v0.4.2 (rodapé + AGENTS.md)
    "agents_multilingual": "0.1.0",
    "agents_modal": "0.1.0",  # NOVO em v0.4.2: modal de Diretrizes
    "footer_responsive": "0.1.0",  # NOVO em v0.4.2: rodapé 100% responsivo
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
    }
