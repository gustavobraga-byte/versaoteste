"""
tui_prompt.py — Textos do prompt da TUI por idioma (patch seguro do binário).

O que é alterado (confirmado no binário do OpenCode v2.0.32 em 18/10/2026):

1. **Exemplos de tarefa** (tela inicial) — `gc={normal:["Fix a TODO in the
   codebase","What is the tech stack of this project?","Fix broken tests"],…}`.
   Vivem em duas tabelas: UTF-8 (usada pelo array de módulo) e a cópia do
   fonte JS.
2. **Prefixo do prompt** — `Ask anything… "` / `Run a command… "`. Vivem na
   tabela **UTF-16** do renderizador (a cópia UTF-8/fonte não é a usada).
3. **Dica da sessão** — `Ask anything, / for commands, @ for context`.

Não existe chave de configuração nem hook de plugin para nada disso.

Como é feito: substituição **byte a byte com o MESMO comprimento** (o binário é
`@bun @bytecode`; alterar tamanho deslocaria todos os offsets). O mesmo texto é
procurado nas duas codificações (UTF-8 e UTF-16LE) e trocado pela variante
correspondente, o que cobre todas as cópias de cada string:

- `examples`  → 26 / 39 / 16 bytes
- `ask_prefix` → 15 unidades UTF-16 (`Ask anything… "`)
- `run_prefix` → 16 unidades UTF-16 (`Run a command… "`)
- `hint`      → 38 bytes (`Ask anything, / for commands, @ for context`)

As sobras são preenchidas com espaços à direita (invisíveis).

Segurança:
- só reescreve quando o tamanho bate exatamente (em bytes/code units);
- escrita atômica (temporário + `os.replace`) e backup único
  (`<binário>.orig-ufvai`);
- verificação pós-patch (`opencode --version`); falha → conteúdo original é
  restaurado na hora;
- idempotente: se já estiver no idioma pedido, nada é escrito.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

# ─────────────────────────────────────────────────────────────────
# Textos originais (inglês) — a âncora de tamanho de cada campo
# ─────────────────────────────────────────────────────────────────

ORIGINAL_EXAMPLES: tuple[str, str, str] = (
    "Fix a TODO in the codebase",
    "What is the tech stack of this project?",
    "Fix broken tests",
)
ORIGINAL_ASK_PREFIX = 'Ask anything… "'
ORIGINAL_RUN_PREFIX = 'Run a command… "'
ORIGINAL_HINT = "Ask anything, / for commands, @ for context"

SUPPORTED_LOCALES: tuple[str, ...] = ("pt-BR", "en", "es", "fr", "zh")
BACKUP_SUFFIX = ".orig-ufvai"

# ─────────────────────────────────────────────────────────────────
# Textos por idioma (tarefas científicas práticas nos exemplos)
# ─────────────────────────────────────────────────────────────────

PROMPT_TEXTS: dict[str, dict[str, object]] = {
    "pt-BR": {
        "examples": ("Compare grupos com teste t", "Revise a literatura e valide as fontes", "Valide as fontes"),
        "ask_prefix": 'O que buscar… "',
        "run_prefix": 'Execute algo… "',
        "hint": "Pergunte algo, / comandos, @ contexto",
    },
    "en": {
        "examples": ORIGINAL_EXAMPLES,
        "ask_prefix": ORIGINAL_ASK_PREFIX,
        "run_prefix": ORIGINAL_RUN_PREFIX,
        "hint": ORIGINAL_HINT,
    },
    "es": {
        "examples": ("Compara grupos con test t", "Revisa la literatura y valida fuentes", "Valida las citas"),
        "ask_prefix": 'Buscar datos… "',
        "run_prefix": 'Ejecuta algo… "',
        "hint": "Pregunta algo, / comandos, @ contexto",
    },
    "fr": {
        "examples": ("Cherche des données IBGE", "Revise la littérature et les sources", "Cite les sources"),
        "ask_prefix": 'Que chercher… "',
        "run_prefix": 'Commande… "',
        "hint": "Posez une question, / commandes, @ ctx",
    },
    "zh": {
        "examples": ("在 SIDRA 查 IBGE 数据", "做系统综述并核对引用与 DOI", "查 IBGE 数据"),
        "ask_prefix": '想查什么… "',
        "run_prefix": '运行命令… "',
        "hint": "提问, / 命令, @ 上下文",
    },
}


# ─────────────────────────────────────────────────────────────────
# Ajuste de tamanho / variantes
# ─────────────────────────────────────────────────────────────────

def _utf8(text: str) -> bytes:
    return text.encode("utf-8")


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-le")


# Codificação em que cada texto é lido em runtime (confirmado no binário):
# exemplos e dica estão na tabela UTF-8; os prefixos, na tabela UTF-16.
FIELD_ENCODING: dict[str, str] = {
    "example": "utf-8",
    "hint": "utf-8",
    "ask_prefix": "utf-16",
    "run_prefix": "utf-16",
}


def _encode(text: str, encoding: str) -> bytes:
    return text.encode("utf-16-le") if encoding == "utf-16" else text.encode("utf-8")


def fit(text: str, original: str, encoding: str) -> str:
    """Preenche com espaços à direita até o MESMO tamanho do original."""
    if encoding == "utf-16":
        target, size = len(original), len(text)
    else:
        target, size = len(original.encode("utf-8")), len(text.encode("utf-8"))
    if size > target:
        raise ValueError(
            f"texto maior que o alvo em {encoding}: {text!r} ({size} > {target})"
        )
    return text + " " * (target - size)


def examples_for(locale: str) -> tuple[str, str, str]:
    table = PROMPT_TEXTS.get(locale) or PROMPT_TEXTS["pt-BR"]
    raw = table["examples"]
    assert isinstance(raw, tuple)
    return tuple(  # type: ignore[return-value]
        fit(text, original, FIELD_ENCODING["example"])
        for text, original in zip(raw, ORIGINAL_EXAMPLES)
    )


def ask_prefix_for(locale: str) -> str:
    table = PROMPT_TEXTS.get(locale) or PROMPT_TEXTS["pt-BR"]
    return fit(str(table["ask_prefix"]), ORIGINAL_ASK_PREFIX, FIELD_ENCODING["ask_prefix"])


def run_prefix_for(locale: str) -> str:
    table = PROMPT_TEXTS.get(locale) or PROMPT_TEXTS["pt-BR"]
    return fit(str(table["run_prefix"]), ORIGINAL_RUN_PREFIX, FIELD_ENCODING["run_prefix"])


def hint_for(locale: str) -> str:
    table = PROMPT_TEXTS.get(locale) or PROMPT_TEXTS["pt-BR"]
    return fit(str(table["hint"]), ORIGINAL_HINT, FIELD_ENCODING["hint"])


def fields_for(locale: str) -> dict[str, list[str]]:
    """Todos os campos do idioma já ajustados ao tamanho original."""
    return {
        "example": list(examples_for(locale)),
        "ask_prefix": [ask_prefix_for(locale)],
        "run_prefix": [run_prefix_for(locale)],
        "hint": [hint_for(locale)],
    }


def _originals_by_field() -> dict[str, list[str]]:
    return {
        "example": list(ORIGINAL_EXAMPLES),
        "ask_prefix": [ORIGINAL_ASK_PREFIX],
        "run_prefix": [ORIGINAL_RUN_PREFIX],
        "hint": [ORIGINAL_HINT],
    }


def _variants(field: str, index: int) -> list[str]:
    """Todas as grafias conhecidas (original + idiomas) para o campo."""
    values: list[str] = []
    base = _originals_by_field()[field][index]
    for locale in ["en"] + [loc for loc in SUPPORTED_LOCALES if loc != "en"]:
        value = fields_for(locale)[field][index]
        if value not in values:
            values.append(value)
    assert base in values
    return values


def _read(path: str) -> bytes | None:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def _encoders(field: str) -> list[str]:
    """Codificação principal do campo + a alternativa (cópias do fonte)."""
    primary = FIELD_ENCODING[field]
    return [primary] + (["utf-16"] if primary == "utf-8" else ["utf-8"])


def _apply(data: bytearray, field: str, index: int, target: str) -> int:
    """Troca todas as variantes conhecidas do campo pelo texto alvo."""
    replaced = 0
    for variant in _variants(field, index):
        if variant == target:
            continue
        for encoding in _encoders(field):
            needle = _encode(variant, encoding)
            replacement = _encode(target, encoding)
            if len(needle) != len(replacement):
                # Tamanho diferente nessa codificação — não é seguro mexer.
                continue
            if needle not in data:
                continue
            data[:] = data.replace(needle, replacement)  # mesmo tamanho
            replaced += 1
    return replaced


def is_patched(binary: str, locale: str) -> bool:
    """True quando o binário já está com os textos do idioma pedido.

    Para idiomas cujo texto é igual ao original (inglês), exige que nenhuma
    variante traduzida esteja presente — é assim que voltamos ao original.
    """
    data = _read(binary)
    if data is None:
        return False
    encoding = None
    target = fields_for(locale)
    for field, values in target.items():
        encoding = FIELD_ENCODING[field]
        for index, value in enumerate(values):
            original = _originals_by_field()[field][index]
            if value == original:
                # Nenhuma grafia traduzida pode estar no arquivo.
                for other in _variants(field, index):
                    if other == original:
                        continue
                    if _encode(other, encoding) in data:
                        return False
                continue
            if _encode(value, encoding) not in data:
                return False
    return True


def patch_prompt_texts(
    binary: str,
    locale: str,
    *,
    backup: bool = True,
    verify: bool = True,
) -> dict[str, object]:
    """Aplica os textos do idioma no binário do OpenCode.

    Returns:
        ``{"status", "locale", "changes", "missing", "backup"}`` — status em
        ``patched`` / ``already`` / ``not-found`` / ``unreadable`` / ``restored``.
    """
    result: dict[str, object] = {
        "status": "unreadable", "locale": locale, "changes": 0, "missing": [], "backup": None,
    }
    raw = _read(binary)
    if raw is None:
        return result

    if is_patched(binary, locale):
        result["status"] = "already"
        return result

    data = bytearray(raw)
    changes = 0
    missing: list[str] = []
    target = fields_for(locale)

    for field, values in target.items():
        for index, value in enumerate(values):
            original = _originals_by_field()[field][index]
            found = any(
                _encode(variant, FIELD_ENCODING[field]) in data
                for variant in _variants(field, index)
            )
            if not found:
                missing.append(f"{field}[{index}]")
                continue
            changes += _apply(data, field, index, value)

    result["changes"] = changes
    result["missing"] = missing

    if changes == 0:
        result["status"] = "not-found" if missing else "already"
        return result

    if len(data) != len(raw):
        # Nunca deveria acontecer (substituição com tamanho preservado).
        result["status"] = "unreadable"
        result["error"] = "comprimento alterado"
        return result

    backup_path = binary + BACKUP_SUFFIX
    if backup and not os.path.exists(backup_path):
        try:
            shutil.copy2(binary, backup_path)
            result["backup"] = backup_path
        except OSError:
            result["backup"] = None

    directory = os.path.dirname(binary) or "."
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".ufvai-prompt-", delete=False) as handle:
            handle.write(bytes(data))
        os.chmod(handle.name, 0o755)
        os.replace(handle.name, binary)
    except OSError as exc:
        result["status"] = "unreadable"
        result["error"] = str(exc)
        return result

    if verify and not _verify(binary):
        try:
            with open(binary, "wb") as out:
                out.write(raw)
            os.chmod(binary, 0o755)
        except OSError:
            pass
        result["status"] = "restored"
        return result

    result["status"] = "patched"
    return result


def restore_backup(binary: str) -> bool:
    """Restaura o binário original a partir do backup, se existir."""
    backup_path = binary + BACKUP_SUFFIX
    if not os.path.exists(backup_path):
        return False
    try:
        shutil.copy2(backup_path, binary)
        os.chmod(binary, 0o755)
    except OSError:
        return False
    return True


def _verify(binary: str, timeout: float = 25.0) -> bool:
    """Confere que o binário ainda executa (checagem barata de integridade)."""
    try:
        completed = subprocess.run(
            [binary, "--version"], capture_output=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0
