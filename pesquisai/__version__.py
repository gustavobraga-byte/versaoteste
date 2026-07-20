"""
__version__.py — Fonte única de versão do PesquisAI v0.6.0 (WEBCLI Mode).

v0.6.0 WEBCLI: ttyd removido, substituído pelo `opencode web` (webcli oficial).
O wrapper Python customizado (FastAPI, React, WebSocket) foi eliminado.
O `opencode web` serve a interface web completa nativamente.

Estrutura do repositório (v0.6.0 WEBCLI):
  /                       # PesquisAI v0.6.0 WEBCLI
  ├── agents/             # AGENTS.md multilíngues (4 idiomas)
  ├── assets/             # Logo e ícones
  ├── docs/               # Documentação (CHANGELOG, PATCH, etc.)
  ├── i18n/               # Módulo multilíngue
  ├── pesquisai/          # Módulo PesquisAI (v0.6.0)
  │   ├── __version__.py  # ⭐ Fonte única da versão
  │   ├── setup.py        # Setup (substitui run_fast.py)
  │   └── obsidian/       # Memória persistente
  ├── scripts/            # Scripts de instalação e vault
  └── tests/              # Testes pytest
"""

# ── Versão semântica (SemVer) ──────────────────────────────────
__version__: str = "0.6.0"

# ── Metadados do release ───────────────────────────────────────
__release_date__: str = "2026-07-20"
__codename__: str = "WEBCLI Mode (opencode web)"

# ── Identidade do projeto ──────────────────────────────────────
__author__: str = "Gustavo Bastos Braga"
__author_email__: str = "gustavo.braga@ufv.br"
__institution__: str = "Universidade Federal de Viçosa (UFV)"
__registry__: str = "10356285004"
__repo_url__: str = "https://github.com/gustavobraga-byte/PesquisAI"
__license__: str = "MIT"

# ── Compatibilidade ────────────────────────────────────────────
__pesquisai_min_version__: str = "0.6.0"
__pesquisai_max_version__: str = "0.6.x"

# ── Tema padrão ────────────────────────────────────────────────
__default_theme__: str = "pesquisai"
__supported_themes__: list[str] = ["pesquisai", "pesquisai-light"]

# ── Componentes incluídos neste release ─────────────────────────
__components__: dict[str, str] = {
    "webcli": "0.6.0",
    "obsidian_memory": "0.5.0",
    "obsidian_autopilot": "0.5.1",
    "grant_finder": "0.1.0",
    "i18n": "0.2.0",
    "agents_multilingual": "0.1.0",
}

# ── Idiomas suportados ─────────────────────────────────────────
__supported_languages__: list[str] = ["pt_BR", "en_US", "es_ES", "fr_FR"]

# ── Saudações iniciais por idioma ──────────────────────────────
# Usadas pelo setup e pelo agente para mensagem de boas-vindas.
__language_greetings__: dict[str, tuple[str, str, str]] = {
    "pt_BR": (
        "Olá!",
        "A partir de agora responda em português brasileiro.",
        "Dica",
    ),
    "en_US": (
        "Hello!",
        "From now on, please respond in English.",
        "Tip",
    ),
    "es_ES": (
        "¡Hola!",
        "A partir de ahora responda en español.",
        "Consejo",
    ),
    "fr_FR": (
        "Bonjour !",
        "À partir de maintenant, répondez en français.",
        "Astuce",
    ),
}

# ── Agências de fomento integradas ─────────────────────────────
__supported_grant_agencies__: list[str] = [
    # Brasil
    "CNPq", "CAPES", "FAPEMIG", "FAPESP", "FINEP",
    # Internacional
    "NIH", "NSF", "ERC", "Wellcome", "Horizon_Europe",
]

# ── Skills extras ───────────────────────────────────────────────
__extra_skills__: list[dict[str, str]] = [
    {
        "id": "grant-finder",
        "name": "Grant Finder",
        "description": "Busca de editais de fomento em agências BR e internacionais.",
        "repo": "https://github.com/gustavobraga-byte/grant-finder",
        "local_path": "skills/grant-finder/",
    },
    {
        "id": "meta-search-br",
        "name": "Meta-Search BR",
        "description": "Busca unificada em 7 bases acadêmicas (PubMed, SciELO, LILACS, BDTD, OpenAlex, arXiv, bioRxiv).",
        "repo": "https://github.com/gustavobraga-byte/meta-search-br",
        "local_path": "skills/meta-search-br/",
    },
]


def get_version() -> str:
    """Retorna a versão formatada para exibição."""
    return f"v{__version__} ({__codename__})"


def get_version_short() -> str:
    """Retorna apenas o número da versão."""
    return __version__


def get_greeting(lang: str = "pt_BR") -> str:
    """Retorna a saudação para o idioma solicitado.

    Formato: "{saudação_curta} ({dica}: {instrução_persistente})"
    Exemplo pt_BR: "Olá! (Dica: A partir de agora responda em português brasileiro.)"
    """
    lang = (lang or "pt_BR").split("_")[0]
    full_lang = {"pt": "pt_BR", "en": "en_US", "es": "es_ES", "fr": "fr_FR"}.get(lang, "pt_BR")
    greeting, persist, tip = __language_greetings__.get(
        full_lang, __language_greetings__["pt_BR"]
    )
    return f"{greeting} ({tip}: {persist})"


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
        "extra_skills": ", ".join(s["id"] for s in __extra_skills__),
    }
