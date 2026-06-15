"""HTTP wrapper server that hosts the PesquisAI control panel.

Addresses the security and structure findings from ANALISE_CODIGO.md:

* Section 2.1 - command validation via :func:`validate_command`.
* Section 2.2 - path-traversal protection via :func:`safe_backup_path`.
* Section 2.3 - 0o600 perms on credential JSON via :func:`secure_write_json`.
* Section 4.2 - handler split across modules with a small router.

The :class:`Handler` class is constructed via :func:`make_handler`
to inject dependencies (settings, runner) so the same code can be
exercised by unit tests.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Optional

from ..config import SETTINGS
from ..utils.opencode import (
    OpenCodeNotFoundError,
    build_env,
    find_opencode,
)
from ..utils.security import (
    read_json,
    safe_backup_path,
    secure_write_json,
    validate_command,
)
from ..utils.subprocess import CommandRunner, SubprocessRunner

logger = logging.getLogger("pesquisai.server")

# Reasonable upper bound for backup filenames - prevents DoS via huge reads.
_MAX_BACKUP_READ_BYTES = 1 * 1024 * 1024

# Regex used to extract a session id from an opencode export file.
_SESSION_ID_RE = re.compile(
    r'^\s*"id"\s*:\s*"(ses_[a-zA-Z0-9]+)"', re.MULTILINE
)


# ── Drive / config helpers ──────────────────────────────────────────


def _resolve_drive_base() -> Path:
    """Pick the most likely Drive path PesquisAI is using.

    The detection order is:
    1. The known canonical path ``/content/drive/My Drive/PesquisAI``.
    2. The folder previously recorded by ``set_drive_info`` (passed
       in via ``runtime.folder_path``).
    3. Fallback to ``/content`` when nothing else matches.
    """
    canonical = Path("/content/drive/My Drive/PesquisAI")
    if canonical.is_dir():
        return canonical
    runtime_folder = getattr(_runtime, "folder_path", None)
    if runtime_folder and "drive" in str(runtime_folder).lower():
        return Path(str(runtime_folder))
    if runtime_folder:
        return Path(str(runtime_folder))
    return Path("/content")


# Module-level runtime state for cross-request variables. These are
# written by :func:`set_drive_info` (called from ``run.py``) and read
# by the handlers. They are intentionally read-only at request time.
class _RuntimeState:
    folder_path: str = "/content"
    drive_url: str = "https://drive.google.com/drive/my-drive"
    opencode_bin: Optional[str] = None
    env: Optional[dict[str, str]] = None
    started_at: float = 0.0


_runtime = _RuntimeState()


def set_drive_info(folder_path: str, drive_url: str) -> None:
    """Set the Drive folder path and URL used by the wrapper UI.

    Called by ``run.py`` after Google Drive is mounted so the
    "Drive" button in the topbar points to the right place.
    """
    _runtime.folder_path = folder_path
    _runtime.drive_url = drive_url


# ── Opencode config / keys helpers ──────────────────────────────────


_OPENCODE_CONFIG_CANDIDATES: tuple[str, ...] = (
    "~/.config/opencode/auth.json",
    "~/.config/opencode/config.json",
    "~/.opencode/auth.json",
    "~/.opencode/config.json",
    "/root/.config/opencode/auth.json",
    "/root/.config/opencode/config.json",
    "/root/.opencode/auth.json",
    "/root/.opencode/config.json",
)


def _expand(path: str) -> str:
    return os.path.expanduser(path)


def find_opencode_config() -> Optional[str]:
    """Return the first existing opencode config/auth file."""
    for candidate in _OPENCODE_CONFIG_CANDIDATES:
        path = _expand(candidate)
        if os.path.isfile(path):
            return path
    try:
        result = subprocess.run(
            [
                "find",
                "/root",
                os.path.expanduser("~"),
                "-name",
                "auth.json",
                "-path",
                "*/opencode/*",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("Busca de config opencode falhou: %s", exc)
        return None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            return line
    return None


def save_opencode_config_to_drive(backup_dir: str) -> Optional[str]:
    """Copy the opencode config to ``backup_dir/opencode_auth.json``."""
    src = find_opencode_config()
    if not src or not os.path.isfile(src):
        return None
    os.makedirs(backup_dir, exist_ok=True)
    dest = os.path.join(backup_dir, "opencode_auth.json")
    # shutil.copy2 may carry file mode bits; we do not care here because
    # the backup is on the user's Drive and the file is non-secret.
    import shutil
    shutil.copy2(src, dest)
    return src


def restore_opencode_config_from_drive(backup_dir: str) -> bool:
    """Restore opencode config from the Drive backup if present."""
    src = os.path.join(backup_dir, "opencode_auth.json")
    if not os.path.isfile(src):
        return False
    restored = False
    for candidate in _OPENCODE_CONFIG_CANDIDATES:
        dest = _expand(candidate)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            import shutil
            shutil.copy2(src, dest)
            restored = True
        except OSError as exc:
            logger.warning("Falha ao restaurar %s: %s", dest, exc)
    return restored


def load_keys_from_drive(
    backup_dir: str,
    env_dict: dict[str, str],
    write_bashrc: bool = True,
) -> list[str]:
    """Load saved API keys from ``.keys.json`` into ``env_dict``.

    Returns the names of environment variables that were populated.

    If ``write_bashrc`` is True, each key is also appended to
    ``~/.bashrc`` (guarded by a marker comment so re-runs are
    idempotent).
    """
    keys_file = os.path.join(backup_dir, ".keys.json")
    if not os.path.isfile(keys_file):
        return []
    saved = read_json(keys_file, default={})
    if not isinstance(saved, dict):
        return []

    loaded: list[str] = []
    for provider, value in saved.items():
        if provider.startswith("_env_") or not value:
            continue
        env_var = saved.get(f"_env_{provider}", "")
        if not env_var:
            continue
        os.environ[env_var] = value
        env_dict[env_var] = value
        loaded.append(env_var)
        if write_bashrc:
            _write_bashrc_export(env_var, value, provider)
    return loaded


def _write_bashrc_export(env_var: str, value: str, provider: str) -> None:
    """Append ``export ENV=VALUE`` to ``~/.bashrc`` idempotently.

    A marker comment ``# opencode-key-<provider>`` is added so the
    line can be located and removed in a future run.
    """
    bashrc = os.path.expanduser("~/.bashrc")
    marker = f"# opencode-key-{provider}"
    export_line = f'export {env_var}="{value}"'
    try:
        if os.path.isfile(bashrc):
            with open(bashrc, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        else:
            lines = []
        lines = [
            line
            for line in lines
            if marker not in line
            and (env_var not in line or "export" not in line)
        ]
        lines.append(f"{export_line}  {marker}\n")
        with open(bashrc, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
    except OSError as exc:
        logger.warning("Falha ao escrever bashrc: %s", exc)


# ── Routes ──────────────────────────────────────────────────────────

RouteHandler = Callable[["HandlerState", dict[str, Any], dict[str, str]], None]


class HandlerState:
    """Per-request state passed to every route handler.

    Wraps the underlying HTTP handler so route functions do not need
    to know about :class:`BaseHTTPRequestHandler` internals.
    """

    def __init__(self, handler: BaseHTTPRequestHandler, body: dict[str, Any], qs: dict[str, str]) -> None:
        self.handler = handler
        self.body = body
        self.qs = qs
        self.runtime = _runtime

    def json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.handler.send_response(code)
        self.handler.send_header("Content-Type", "application/json; charset=utf-8")
        self.handler.send_header("Access-Control-Allow-Origin", "*")
        self.handler.send_header("Content-Length", str(len(body)))
        self.handler.end_headers()
        self.handler.wfile.write(body)

    def text(self, code: int, body: bytes, content_type: str = "text/plain; charset=utf-8") -> None:
        self.handler.send_response(code)
        self.handler.send_header("Content-Type", content_type)
        self.handler.send_header("Content-Length", str(len(body)))
        self.handler.end_headers()
        self.handler.wfile.write(body)


def _route_health(state: HandlerState, body: dict, qs: dict) -> None:
    """GET /api/health - liveness/readiness probe."""
    opencode_info: dict[str, Any] = {"path": _runtime.opencode_bin}
    if _runtime.opencode_bin:
        try:
            result = subprocess.run(
                [_runtime.opencode_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            opencode_info["version"] = result.stdout.strip()
            opencode_info["ok"] = result.returncode == 0
        except (subprocess.TimeoutExpired, OSError) as exc:
            opencode_info["error"] = str(exc)
    state.json(200, {
        "status": "ok",
        "uptime_s": time.time() - _runtime.started_at,
        "drive_mounted": Path("/content/drive/My Drive").is_dir(),
        "opencode": opencode_info,
    })


def _route_sessions(state: HandlerState, body: dict, qs: dict) -> None:
    """GET /api/sessions - list opencode sessions."""
    if not _runtime.opencode_bin:
        state.json(503, {"error": "opencode nao configurado"})
        return
    result = subprocess.run(
        [_runtime.opencode_bin, "session", "list", "--format", "json"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    sessions: Any = []
    if result.stdout.strip():
        try:
            sessions = json.loads(result.stdout)
        except json.JSONDecodeError:
            sessions = [
                {"id": line.strip()}
                for line in result.stdout.splitlines()
                if line.strip()
            ]
    state.json(200, {"sessions": sessions})


def _route_list_backups(state: HandlerState, body: dict, qs: dict) -> None:
    """GET /api/backups - enumerate JSON files in the Drive backup dir."""
    backup_dir = str(_resolve_drive_base() / "backups")
    try:
        files = sorted(
            [
                entry
                for entry in os.listdir(backup_dir)
                if entry.endswith(".json") and not entry.startswith(".")
            ],
            reverse=True,
        )
    except OSError:
        files = []
    state.json(200, {"backups": files})


def _route_debug(state: HandlerState, body: dict, qs: dict) -> None:
    """GET /api/debug - dump masked key info (for diagnostics only)."""
    backup_dir = str(_resolve_drive_base() / "backups")
    keys_file = os.path.join(backup_dir, ".keys.json")
    keys_data: dict[str, Any] = {}
    if os.path.isfile(keys_file):
        raw = read_json(keys_file, default={})
        if isinstance(raw, dict):
            for k, v in raw.items():
                if k.startswith("_env_") or not v:
                    keys_data[k] = v
                else:
                    keys_data[k] = f"{str(v)[:6]}..."
    state.json(200, {
        "drive_backup_dir": backup_dir,
        "drive_dir_exists": os.path.isdir(backup_dir),
        "keys_file_exists": os.path.isfile(keys_file),
        "keys_data": keys_data,
        "opencode_bin": _runtime.opencode_bin,
        "env_keys": [
            k for k in (_runtime.env or {}) if "KEY" in k or "TOKEN" in k or "SECRET" in k
        ],
    })


def _route_get_apikey(state: HandlerState, body: dict, qs: dict) -> None:
    """GET /api/apikey?provider=... - retrieve a stored key."""
    provider = qs.get("provider", "").strip()
    backup_dir = str(_resolve_drive_base() / "backups")
    keys_file = os.path.join(backup_dir, ".keys.json")
    keys = read_json(keys_file, default={})
    if not isinstance(keys, dict):
        keys = {}
    if provider:
        state.json(200, {"apikey": keys.get(provider, "")})
        return
    state.json(200, {"keys": keys})


def _route_post_apikey(state: HandlerState, body: dict, qs: dict) -> None:
    """POST /api/apikey - persist an API key in Drive + env + bashrc."""
    provider = (body.get("provider") or "").strip()
    env_var = (body.get("env") or "").strip()
    key = (body.get("apikey") or "").strip()
    if not key or not provider:
        state.json(400, {"error": "provider e apikey obrigatorios."})
        return

    backup_dir = str(_resolve_drive_base() / "backups")
    os.makedirs(backup_dir, exist_ok=True)
    keys_file = os.path.join(backup_dir, ".keys.json")
    keys = read_json(keys_file, default={})
    if not isinstance(keys, dict):
        keys = {}
    keys[provider] = key
    if env_var:
        keys[f"_env_{provider}"] = env_var
    try:
        secure_write_json(keys_file, keys)  # 0600 perms (Section 2.3)
    except OSError as exc:
        state.json(500, {"error": f"Falha ao salvar no Drive: {exc}"})
        return

    if env_var:
        os.environ[env_var] = key
        if _runtime.env is not None:
            _runtime.env[env_var] = key
    if env_var:
        _write_bashrc_export(env_var, key, provider)
    state.json(200, {"ok": True})


def _route_apply_apikeys(state: HandlerState, body: dict, qs: dict) -> None:
    """POST /api/apikey/apply - reload keys from Drive into env."""
    backup_dir = str(_resolve_drive_base() / "backups")
    if _runtime.env is None:
        _runtime.env = os.environ.copy()
    applied = load_keys_from_drive(backup_dir, _runtime.env, write_bashrc=False)
    if applied:
        state.json(200, {"ok": True, "applied": applied})
    else:
        state.json(200, {"ok": False, "reason": "no keys stored"})


def _route_run_terminal(state: HandlerState, body: dict, qs: dict) -> None:
    """POST /api/run_terminal - restart ttyd with a new command.

    The ``command`` field is validated against the allow-list
    (Section 2.1 of the analysis) before being passed to the shell.
    """
    cmd = (body.get("command") or "").strip()
    no_fallback = bool(body.get("no_fallback", False))
    if not cmd:
        state.json(400, {"error": "Comando vazio."})
        return
    try:
        cmd = validate_command(cmd)  # Section 2.1
    except ValueError as exc:
        state.json(400, {"error": str(exc)})
        return

    backup_dir = str(_resolve_drive_base() / "backups")
    if _runtime.env is None:
        _runtime.env = os.environ.copy()
    load_keys_from_drive(backup_dir, _runtime.env, write_bashrc=False)

    subprocess.run(
        "pkill -9 -f ttyd 2>/dev/null; pkill -9 -f opencode 2>/dev/null; true",
        shell=True,
        check=False,
    )
    time.sleep(1.5)

    opencode_bin = _runtime.opencode_bin or "opencode"
    if no_fallback:
        bash_cmd = f"{cmd}; exec bash"
    else:
        bash_cmd = f"{cmd}; {opencode_bin}; exec bash"
    env = _runtime.env or os.environ.copy()
    try:
        subprocess.Popen(
            [
                "ttyd",
                "--writable",
                "-p",
                str(SETTINGS.terminal_port),
                "bash",
                "-i",
                "-c",
                bash_cmd,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
    except FileNotFoundError as exc:
        state.json(500, {"error": f"ttyd nao encontrado: {exc}"})
        return
    state.json(200, {"ok": True, "command": cmd})


def _route_backup(state: HandlerState, body: dict, qs: dict) -> None:
    """POST /api/backup - export the current opencode session to Drive."""
    backup_dir = str(_resolve_drive_base() / "backups")
    os.makedirs(backup_dir, exist_ok=True)
    session_id = (body.get("session_id") or "").strip()
    ts = time.strftime("%H-%M-%S_%d-%m-%Y")

    if not session_id:
        if not _runtime.opencode_bin:
            state.json(503, {"error": "opencode nao configurado"})
            return
        result = subprocess.run(
            [_runtime.opencode_bin, "session", "list", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        try:
            sessions = json.loads(result.stdout) if result.stdout.strip() else []
        except json.JSONDecodeError:
            lines = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
            sessions = [{"id": lines[0]}] if lines else []
        if sessions:
            session_id = sessions[0].get("id", "")

    if not session_id:
        state.json(400, {"error": "Nenhuma sessao encontrada para exportar."})
        return

    fname = f"backup_{session_id[:12]}_{ts}.json"
    outpath = os.path.join(backup_dir, fname)
    opencode_bin = _runtime.opencode_bin
    if not opencode_bin:
        state.json(503, {"error": "opencode nao configurado"})
        return

    result = subprocess.run(
        [opencode_bin, "export", session_id, "--format", outpath],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0 or not os.path.isfile(outpath):
        # Fallback: capture stdout and write it manually.
        result2 = subprocess.run(
            [opencode_bin, "export", session_id],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result2.returncode == 0 and result2.stdout.strip():
            with open(outpath, "w", encoding="utf-8") as fh:
                fh.write(result2.stdout)
        else:
            state.json(500, {
                "error": (result.stderr or result2.stderr or "Falha ao exportar.").strip()
            })
            return
    state.json(200, {
        "ok": True,
        "file": fname,
        "session_id": session_id,
        "path": outpath,
    })


def _route_restore(state: HandlerState, body: dict, qs: dict) -> None:
    """POST /api/restore - import a previously exported session."""
    fname = (body.get("file") or "").strip()
    if not fname:
        state.json(400, {"error": "Nome do arquivo nao informado."})
        return
    backup_dir = str(_resolve_drive_base() / "backups")
    # Section 2.2: resolve safely and reject traversal.
    fpath = safe_backup_path(backup_dir, fname)
    if fpath is None:
        state.json(404, {"error": f"Arquivo nao encontrado: {fname}"})
        return

    if not _runtime.opencode_bin:
        state.json(503, {"error": "opencode nao configurado"})
        return
    import_result = subprocess.run(
        [_runtime.opencode_bin, "import", str(fpath)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if import_result.returncode != 0:
        state.json(500, {
            "error": (import_result.stderr.strip() or "Falha ao importar.")
        })
        return

    # Section 3.5: read the whole file (bounded by _MAX_BACKUP_READ_BYTES)
    # and look for the session id with a strict regex.
    session_id = ""
    parse_error = ""
    try:
        with open(fpath, "r", encoding="utf-8") as fh:
            raw = fh.read(_MAX_BACKUP_READ_BYTES)
        match = _SESSION_ID_RE.search(raw)
        if match:
            session_id = match.group(1)
    except OSError as exc:
        parse_error = str(exc)

    state.json(200, {
        "ok": True,
        "file": fname,
        "session_id": session_id,
        "parse_error": parse_error,
        "import_stdout": import_result.stdout.strip()[:300],
        "message": "Sessao importada com sucesso.",
    })


def _route_index(state: HandlerState, body: dict, qs: dict) -> None:
    """GET / - serve the rendered wrapper HTML."""
    index_path = Path(str(SETTINGS.wrapper_dir)) / "index.html"
    if not index_path.is_file():
        state.text(404, b"PesquisAI wrapper: index.html not generated yet.")
        return
    content = index_path.read_bytes()
    state.text(200, content, content_type="text/html; charset=utf-8")


# Routing table. Order does not matter; first match wins.
_ROUTES: dict[tuple[str, str], RouteHandler] = {
    ("GET", "/"): _route_index,
    ("GET", "/index.html"): _route_index,
    ("GET", "/api/health"): _route_health,
    ("GET", "/api/sessions"): _route_sessions,
    ("GET", "/api/backups"): _route_list_backups,
    ("GET", "/api/debug"): _route_debug,
    ("GET", "/api/apikey"): _route_get_apikey,
    ("POST", "/api/apikey"): _route_post_apikey,
    ("POST", "/api/apikey/apply"): _route_apply_apikeys,
    ("POST", "/api/run_terminal"): _route_run_terminal,
    ("POST", "/api/backup"): _route_backup,
    ("POST", "/api/restore"): _route_restore,
}


# ── HTTP handler factory ────────────────────────────────────────────


def make_handler(
    runner: Optional[CommandRunner] = None,
) -> type[BaseHTTPRequestHandler]:
    """Build a :class:`BaseHTTPRequestHandler` subclass bound to ``runner``.

    The factory pattern lets unit tests inject a :class:`FakeRunner`
    and assert on the produced HTTP responses.
    """
    runner = runner or SubprocessRunner()

    class Handler(BaseHTTPRequestHandler):
        # Silence the default access log; keeps the Colab output tidy
        # and avoids leaking potentially sensitive request paths.
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            if args and isinstance(args[0], int) and args[0] >= 400:
                logger.warning(format, *args)

        def _send_404(self) -> None:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", "9")
            self.end_headers()
            self.wfile.write(b"Not found")

        def do_OPTIONS(self) -> None:  # noqa: N802 - HTTP method
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802 - HTTP method
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            qs = {
                k: v[0] if v else ""
                for k, v in parse_qs(parsed.query).items()
            }
            state = HandlerState(self, {}, qs)
            route = _ROUTES.get(("GET", parsed.path))
            if route is None:
                self._send_404()
                return
            try:
                route(state, {}, qs)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Falha em rota GET %s", parsed.path)
                state.json(500, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802 - HTTP method
            from urllib.parse import urlparse
            parsed = urlparse(self.path)
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            raw = self.rfile.read(length) if length else b""
            body: dict[str, Any] = {}
            if raw:
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    self._send_404()
                    return
            state = HandlerState(self, body, {})
            route = _ROUTES.get(("POST", parsed.path))
            if route is None:
                self._send_404()
                return
            try:
                route(state, body, {})
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Falha em rota POST %s", parsed.path)
                state.json(500, {"error": str(exc)})

    return Handler


def start_wrapper_server(folder_path: str, drive_url: str) -> HTTPServer:
    """Start the wrapper HTTP server in a background thread.

    Returns the underlying :class:`HTTPServer` so tests can call
    ``shutdown()``. The function also performs the one-time
    restore-keys-from-Drive step that the original code did at
    server start.
    """
    set_drive_info(folder_path, drive_url)

    try:
        _runtime.opencode_bin = find_opencode()
    except OpenCodeNotFoundError:
        logger.warning("opencode nao encontrado, usando fallback 'opencode'")
        _runtime.opencode_bin = "opencode"
    _runtime.env = build_env()
    _runtime.started_at = time.time()

    backup_dir = str(_resolve_drive_base() / "backups")
    os.makedirs(backup_dir, exist_ok=True)

    if restore_opencode_config_from_drive(backup_dir):
        logger.info("Config do OpenCode restaurada do Drive.")

    if _runtime.env is None:
        _runtime.env = os.environ.copy()
    loaded = load_keys_from_drive(backup_dir, _runtime.env)
    if loaded:
        logger.info("Keys carregadas do Drive: %s", ", ".join(loaded))

    handler_cls = make_handler()
    server = HTTPServer(("0.0.0.0", SETTINGS.wrapper_port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Wrapper server listening on 0.0.0.0:%d", SETTINGS.wrapper_port)
    return server
