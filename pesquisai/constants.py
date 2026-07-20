"""
constants.py — Constantes centralizadas do PesquisAI v0.6.0 (WEBCLI Mode).

v0.6.0 WEBCLI: usa `opencode web` (o webcli oficial do opencode) para
servir a interface web. Não há mais ttyd, nem servidor FastAPI
customizado — o opencode web faz tudo.
"""
import os
import logging

# ── Versão ─────────────────────────────────────────────────────
VERSION = "0.6.0"
AUTHOR_NAME = "Gustavo Bastos Braga"
AUTHOR_EMAIL = "gustavo.braga@ufv.br"
INSTITUTION = "Universidade Federal de Viçosa (UFV)"
SISPPG_REGISTRY = "10356285004"
REPO_URL = "https://github.com/gustavobraga-byte/PesquisAI"

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pesquisai")

# ── Google Drive (Colab) ───────────────────────────────────────
DRIVE_FOLDER = "PesquisAI"
MOUNT_PATH = "/content/drive"
DRIVE_PATH = os.path.join(MOUNT_PATH, "My Drive", DRIVE_FOLDER)
FALLBACK_URL = "https://drive.google.com/drive/my-drive"

# ── Diretórios temporários ────────────────────────────────────
WORK_DIR = "/tmp/pesquisai"

# ── OpenCode ──────────────────────────────────────────────────
SKILLS_DIR = os.path.expanduser("~/.agents/skills")
THEME_DIR = os.path.expanduser("~/.config/opencode/themes")
AGENT_DIR = os.path.expanduser("~/.config/opencode/agent")  # singular!
OPENCODE_CFG = os.path.expanduser("~/.config/opencode/config.json")
TUI_JSON = os.path.expanduser("~/.config/opencode/tui.json")

# ── Porta do opencode web (webcli) ────────────────────────────
WEBCLI_PORT = 8000  # porta padrão do opencode web (v0.6.0)

# ── Skills registradas ────────────────────────────────────────
SkillEntry = tuple[str, str, bool]

SKILL_REGISTRY: list[SkillEntry] = [
    ("https://github.com/gustavobraga-byte/Skill-IBGE.git", "ibge-br", True),
    ("https://github.com/gustavobraga-byte/Skill-DataSus.git", "opendatasus", True),
    ("https://github.com/gustavobraga-byte/scientific-agent-skills.git", "scientific", True),
    ("https://github.com/gustavobraga-byte/PesquisAI.git", "pesquisai", True),
    ("https://github.com/gustavobraga-byte/UFV-ABNT.git", "ufv-abnt", False),
    ("https://github.com/gustavobraga-byte/Skill_Analise_qualitativa.git", "qualitativa", False),
    ("https://github.com/gustavobraga-byte/skill_dados_brasil.git", "dados-brasil", False),
    ("https://github.com/gustavobraga-byte/skill_agrobr.git", "agrobr", False),
    ("https://github.com/gustavobraga-byte/grant-finder.git", "grant-finder", False),
    ("https://github.com/gustavobraga-byte/meta-search-br.git", "meta-search-br", False),
    ("https://github.com/gustavobraga-byte/skill-obsidian-memory.git", "obsidian-memory", False),
    ("https://github.com/gustavobraga-byte/Memorial_ufv.git", "memorial", False),
    ("https://github.com/gustavobraga-byte/BR-DWGD.git", "BR-DWGD", False),
]

SKILL_MAPPINGS: list[tuple[str, str]] = [
    ("/tmp/skill_ibge-br", "ibge-br"),
    ("/tmp/skill_opendatasus", "opendatasus"),
    ("/tmp/skill_scientific/skills", "scientific"),
    ("/tmp/skill_ufv-abnt", "ufv-abnt"),
    ("/tmp/skill_qualitativa", "qualitativa"),
    ("/tmp/skill_dados-brasil", "dados-brasil"),
    ("/tmp/skill_agrobr", "agrobr"),
    ("/tmp/skill_grant-finder", "grant-finder"),
    ("/tmp/skill_meta-search-br", "meta-search-br"),
    ("/tmp/skill_obsidian-memory", "obsidian-memory"),
    ("/tmp/skill_memorial", "memorial"),
    ("/tmp/skill_BR-DWGD", "BR-DWGD"),
]

ESSENTIAL_SKILLS: set[str] = {
    name for _, name, required in SKILL_REGISTRY if required
}

# ── Obsidian vault ────────────────────────────────────────────
OBSIDIAN_VAULT_ENV = "PESQUISAI_OBSIDIAN_VAULT"
OBSIDIAN_DEFAULT_VAULT = "/content/drive/My Drive/PesquisAI/vault"

# ── i18n ──────────────────────────────────────────────────────
DEFAULT_LANG = "pt_BR"
SUPPORTED_LANGS = ["pt_BR", "en_US", "es_ES", "fr_FR"]


# ── Detecção de ambiente ──────────────────────────────────────
def is_colab() -> bool:
    """Detecta se está rodando no Google Colab."""
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def is_drive_mounted() -> bool:
    """Verifica se o Google Drive está montado."""
    return os.path.exists("/content/drive/My Drive")


def get_pesquisai_path() -> str:
    """Retorna o caminho de trabalho do PesquisAI (Drive no Colab, local fora)."""
    if is_colab() and is_drive_mounted():
        return DRIVE_PATH
    return WORK_DIR
