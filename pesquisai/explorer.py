"""web26_explorer.py — mini navigateur de arquivos do agente (v0.7.11-web26).

Painel lateral na interface web que navega pela **pasta do agente** (o
diretório do projeto, no Google Drive) e mostra um visualizador mínimo:

* **texto** (``.md``, ``.txt``, ``.csv``, ``.json``, código-fonte…) — lido e
  exibido no painel;
* **imagem** (``.png``, ``.jpg``, ``.gif``, ``.webp``, ``.svg``…) — servida
  inline pelo gateway;
* **suite Office** (``.docx``, ``.xlsx``, ``.pptx``, ``.odt``, ``.ods``…) —
  o texto é extraído do próprio pacote (ZIP + XML, só biblioteca padrão) e
  mostrado de forma resumida, com o link para a versão completa no Drive.

Mais o **download** do arquivo e o **link para editar no Google Drive**.

Regras de segurança (as mesmas do Drive Guard do motor):
* todo caminho é resolvido e precisa ficar **dentro** de uma raiz permitida
  (o diretório do agente) — nada fora é servido;
* a leitura de arquivo é limitada em tamanho;
* nada é escrito — o painel é somente leitura.
"""

from __future__ import annotations

import html
import os
import re
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

__all__ = [
    "allowed_roots",
    "safe_path",
    "listing",
    "preview",
    "read_bytes",
    "drive_link",
    "DRIVE_HOME",
]

#: Página inicial do Drive usada nos links.
DRIVE_HOME = "https://drive.google.com/drive/u/0/my-drive"

TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".log", ".txt",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".bash", ".zsh", ".css",
    ".scss", ".html", ".htm", ".xml", ".sql", ".r", ".jl", ".tex", ".bib",
    ".tex", ".ipynb", ".env", ".gitignore", ".dockerfile", ".makefile",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".avif"}
OFFICE_SUFFIXES = {
    ".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".doc", ".xls", ".ppt",
}
PDF_SUFFIXES = {".pdf"}

MAX_TEXT_BYTES = 200_000
MAX_BINARY_BYTES = 25 * 1024 * 1024


def _engine_sessions() -> list[dict]:
    try:
        from .webapi import engine_json  # type: ignore

        data = engine_json("/api/session", timeout=10)
    except Exception:  # pragma: no cover — motor fora do ar
        return []
    rows = data.get("data") if isinstance(data, dict) else data
    return [r for r in (rows or []) if isinstance(r, dict)]


def allowed_roots() -> list[Path]:
    """Diretórios em que o agente pode estar (o do projeto em execução)."""
    roots: list[Path] = []
    for row in _engine_sessions():
        directory = (row.get("location") or {}).get("directory")
        if directory:
            try:
                roots.append(Path(str(directory)).resolve())
            except OSError:
                continue
    if not roots:
        try:
            roots.append(Path.cwd().resolve())
        except OSError:
            roots.append(Path("/"))
    # mantém a ordem e remove duplicatas
    uniq: list[Path] = []
    for root in roots:
        if root not in uniq:
            uniq.append(root)
    return uniq


def safe_path(relative: str, roots: list[Path] | None = None) -> Path | None:
    """Resolve um caminho **dentro** de uma raiz permitida (ou ``None``)."""
    rel = str(relative or "").strip().lstrip("/")
    for root in (roots if roots is not None else allowed_roots()):
        try:
            base = root.resolve()
        except OSError:
            continue
        target = (base / rel) if rel else base
        try:
            resolved = target.resolve()
        except OSError:
            resolved = target
        try:
            resolved.relative_to(base)
        except ValueError:
            continue
        return resolved
    return None


def _mime_of(path: Path) -> str:
    import mimetypes

    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _kind_of(path: Path) -> str:
    suffix = path.suffix.lower()
    if path.is_dir():
        return "directory"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in OFFICE_SUFFIXES:
        return "office"
    if suffix in PDF_SUFFIXES:
        return "pdf"
    if suffix in TEXT_SUFFIXES or not suffix:
        return "text"
    return "binary"


def drive_link(name: str) -> str:
    """Link para o arquivo no Google Drive.

    A montagem FUSE do Drive não expõe o *file id*, então o link vai para a
    **busca no My Drive** pelo nome exato — abre o arquivo em uma etapa.
    """
    return f"{DRIVE_HOME}?q={quote(str(name or ''), safe='')}"


def listing(relative: str = "") -> dict[str, Any]:
    """Conteúdo de uma pasta do agente."""
    roots = allowed_roots()
    target = safe_path(relative, roots)
    if target is None:
        return {"error": "caminho fora da pasta do agente", "path": relative, "items": []}
    if not target.exists():
        return {"error": "pasta não encontrada", "path": relative, "items": []}
    if not target.is_dir():
        return {"error": "não é uma pasta", "path": relative, "items": []}
    items: list[dict] = []
    try:
        entries = sorted(os.scandir(target), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError as exc:
        return {"error": f"não foi possível ler a pasta: {exc}", "path": relative, "items": []}
    parent = ""
    rel = str(relative or "").strip("/")
    if rel:
        parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
    for entry in entries:
        if entry.name.startswith("."):
            continue
        path = Path(entry.path)
        is_dir = entry.is_dir()
        try:
            stat = entry.stat()
            size = 0 if is_dir else int(stat.st_size)
            modified = int(stat.st_mtime * 1000)
        except OSError:
            size, modified = 0, 0
        item_rel = f"{rel}/{entry.name}" if rel else entry.name
        items.append(
            {
                "name": entry.name,
                "path": item_rel,
                "type": "directory" if is_dir else "file",
                "size": size,
                "modified": modified,
                "mime": "" if is_dir else _mime_of(path),
                "kind": _kind_of(path),
                "driveUrl": drive_link(entry.name),
            }
        )
    return {
        "path": rel,
        "parent": parent,
        "root": str(target),
        "items": items,
        "driveHome": DRIVE_HOME,
        "error": "",
    }


def read_bytes(relative: str, max_bytes: int = MAX_BINARY_BYTES) -> tuple[bytes | None, str]:
    """Lê o arquivo (bytes crus + caminho absoluto) dentro da raiz permitida."""
    target = safe_path(relative)
    if target is None or not target.is_file():
        return None, ""
    try:
        size = target.stat().st_size
    except OSError:
        return None, ""
    try:
        with open(target, "rb") as handle:
            data = handle.read(min(size, max_bytes) + 1)
    except OSError:
        return None, ""
    if len(data) > max_bytes:
        data = data[:max_bytes]
    return data, str(target)


# ── extração de texto da suíte Office (só biblioteca padrão) ───────────────

def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(_BytesIO(data)) as zf:
        try:
            xml = zf.read("word/document.xml").decode("utf-8", "replace")
        except KeyError:
            return ""
    # um parágrafo por linha: as quebras vivem em </w:p>, não nos <w:t>
    paragraphs: list[str] = []
    for block in re.findall(r"<w:p\b.*?</w:p>", xml, re.S):
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", block, re.S)
        if texts:
            paragraphs.append(html.unescape("".join(texts)))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(paragraphs))


def _xlsx_text(data: bytes) -> str:
    with zipfile.ZipFile(_BytesIO(data)) as zf:
        shared: list[str] = []
        try:
            sxml = zf.read("xl/sharedStrings.xml").decode("utf-8", "replace")
            for si in re.findall(r"<si>(.*?)</si>", sxml, re.S):
                shared.append(html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S))))
        except KeyError:
            shared = []
        names = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/sheet"))
        out: list[str] = []
        for name in names:
            try:
                sheet = zf.read(name).decode("utf-8", "replace")
            except KeyError:
                continue
            out.append(f"— {name.split('/')[-1]} —")
            for row in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.S):
                cells: list[str] = []
                for cell in re.findall(r"<c\b([^>]*)>(.*?)</c>", row, re.S):
                    attrs, body = cell
                    value = ""
                    if 't="s"' in attrs:
                        m = re.search(r"<v>(\d+)</v>", body)
                        if m:
                            idx = int(m.group(1))
                            value = shared[idx] if idx < len(shared) else ""
                    else:
                        m = re.search(r"<v>(.*?)</v>", body, re.S)
                        value = m.group(1) if m else ""
                        m2 = re.search(r"<is>.*?<t[^>]*>(.*?)</t>", body, re.S)
                        if m2:
                            value = html.unescape(m2.group(1))
                    cells.append(value)
                if any(cells):
                    out.append(" | ".join(cells))
    return "\n".join(out)


def _pptx_text(data: bytes) -> str:
    with zipfile.ZipFile(_BytesIO(data)) as zf:
        names = sorted(n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n))
        out: list[str] = []
        for name in names:
            try:
                xml = zf.read(name).decode("utf-8", "replace")
            except KeyError:
                continue
            texts = re.findall(r"<a:t[^>]*>(.*?)</a:t>", xml, re.S)
            if texts:
                out.append(f"— {name.split('/')[-1]} —")
                out.append(html.unescape(" ".join(texts)))
    return "\n".join(out)


def _odf_text(data: bytes) -> str:
    with zipfile.ZipFile(_BytesIO(data)) as zf:
        try:
            xml = zf.read("content.xml").decode("utf-8", "replace")
        except KeyError:
            return ""
    xml = re.sub(r"</text:p>", "\n", xml)
    xml = re.sub(r"</table:table-row>", "\n", xml)
    texts = re.findall(r"<text:p[^>]*>(.*?)</text:p>", xml, re.S)
    joined = "\n".join(html.unescape("".join(re.findall(r"<[^>]+>|([^<]+)", t))) for t in texts)
    return re.sub(r"\n{3,}", "\n\n", joined)


def _BytesIO(data: bytes):  # noqa: N802 — helper local
    import io

    return io.BytesIO(data)


def office_text(path: Path) -> str:
    """Texto extraído de um arquivo da suíte Office (best-effort)."""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    suffix = path.suffix.lower()
    try:
        if suffix == ".docx":
            return _docx_text(data)
        if suffix == ".xlsx":
            return _xlsx_text(data)
        if suffix == ".pptx":
            return _pptx_text(data)
        if suffix in (".odt", ".ods", ".odp"):
            return _odf_text(data)
    except (zipfile.BadZipFile, OSError, ValueError):
        return ""
    return ""


def preview(relative: str) -> dict[str, Any]:
    """Prévia de um arquivo para o painel (texto, imagem ou Office)."""
    target = safe_path(relative)
    if target is None:
        return {"error": "caminho fora da pasta do agente"}
    if not target.is_file():
        return {"error": "arquivo não encontrado"}
    kind = _kind_of(target)
    name = target.name
    info: dict[str, Any] = {
        "name": name,
        "path": str(relative),
        "kind": kind,
        "mime": _mime_of(target),
        "driveUrl": drive_link(name),
        "downloadUrl": f"api/ufvai/explorer/download?path={quote(str(relative), safe='')}",
        "text": "",
        "truncated": False,
        "error": "",
    }
    try:
        info["size"] = int(target.stat().st_size)
    except OSError:
        info["size"] = 0
    if kind == "image":
        info["inlineUrl"] = (
            f"api/ufvai/explorer/download?path={quote(str(relative), safe='')}&inline=1"
        )
        return info
    if kind == "office":
        text = office_text(target)
        if not text:
            info["error"] = (
                "não foi possível extrair o texto (formato legado ou protegido); "
                "abra no Google Drive"
            )
        info["text"] = text[:MAX_TEXT_BYTES]
        info["truncated"] = len(text) > MAX_TEXT_BYTES
        return info
    if kind == "pdf":
        info["error"] = "PDF: abra no Google Drive ou baixe o arquivo"
        return info
    if kind == "binary":
        info["error"] = "arquivo binário — baixe ou abra no Google Drive"
        return info
    # texto
    try:
        raw = target.read_bytes()[: MAX_TEXT_BYTES + 1]
    except OSError as exc:
        info["error"] = f"não foi possível ler: {exc}"
        return info
    info["truncated"] = len(raw) > MAX_TEXT_BYTES
    raw = raw[:MAX_TEXT_BYTES]
    try:
        info["text"] = raw.decode("utf-8")
    except UnicodeDecodeError:
        info["text"] = raw.decode("latin-1", "replace")
    return info
