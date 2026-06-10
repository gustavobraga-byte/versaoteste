"""Interface web do PesquisAI: servidor ttyd + wrapper HTTP com API REST."""

import os
import sys
import atexit
import subprocess
import time
import threading
import json
import shutil
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

try:
    from google.colab import output
    from IPython.display import display, HTML
    IN_COLAB = True
except ImportError:
    IN_COLAB = False
    output = None
    display = None
    HTML = None

from constants import TERMINAL_PORT, WRAPPER_PORT, WRAPPER_DIR, VERSION, logger
from jokes import next_joke
from opencode_utils import find_opencode, build_env
from i18n import _

_opencode_bin = None
_env = None
_drive_url = "https://drive.google.com/drive/my-drive"
_folder_path = "/content"
PROJECTS_DIR_NAME = "projetos"
_start_time = time.time()


def _get_drive_backup_dir():
    base = "/content/drive/My Drive/PesquisAI"
    if os.path.isdir(base):
        return os.path.join(base, "backups")
    if os.path.isdir(_folder_path) and "drive" in _folder_path.lower():
        return os.path.join(_folder_path, "backups")
    return os.path.join(_folder_path, "backups")


def _get_projects_dir():
    base = "/content/drive/My Drive/PesquisAI"
    if os.path.isdir(base):
        return os.path.join(base, PROJECTS_DIR_NAME)
    return os.path.join(_folder_path, PROJECTS_DIR_NAME)


OPENCODE_CONFIG_CANDIDATES = [
    os.path.expanduser("~/.config/opencode/auth.json"),
    os.path.expanduser("~/.config/opencode/config.json"),
    os.path.expanduser("~/.opencode/auth.json"),
    os.path.expanduser("~/.opencode/config.json"),
    "/root/.config/opencode/auth.json",
    "/root/.config/opencode/config.json",
    "/root/.opencode/auth.json",
    "/root/.opencode/config.json",
]


def set_drive_info(folder_path, drive_url):
    global _drive_url, _folder_path
    _drive_url = drive_url
    _folder_path = folder_path


def resolve_opencode():
    global _opencode_bin, _env
    try:
        _opencode_bin = find_opencode()
    except FileNotFoundError:
        logger.warning("opencode não encontrado, usando fallback 'opencode'")
        _opencode_bin = "opencode"
    _env = build_env()
    print(f"🔍 OpenCode binário: {_opencode_bin}")
    return _opencode_bin, _env


def install_ttyd():
    if shutil.which("ttyd"):
        print("✅ ttyd já está instalado.")
        return
    print(f"\n{next_joke('economia')}")
    print("📦 Instalando ttyd...")
    r1 = subprocess.run(
        "apt-get update -qq && apt-get install -y -qq ttyd",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    if r1.returncode != 0:
        print("⚠️  apt-get falhou. Tentando download manual do ttyd...")
        url = "https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64"
        r2 = subprocess.run(
            f"curl -fsSL {url} -o /usr/local/bin/ttyd && chmod +x /usr/local/bin/ttyd",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if r2.returncode != 0:
            print("⚠️  Download manual do ttyd também falhou. Continuando mesmo assim.")
        else:
            print("✅ ttyd baixado manualmente.")
    else:
        print("✅ ttyd instalado.")


def kill_previous():
    subprocess.run("pkill -f ttyd 2>/dev/null || true", shell=True)
    subprocess.run(f"pkill -f 'python3.*{WRAPPER_PORT}' 2>/dev/null || true", shell=True)
    time.sleep(0.5)


def start_ttyd():
    print(f"\n{next_joke('economia')}")
    opencode_bin, env = resolve_opencode()
    subprocess.Popen(
        ["ttyd", "-p", str(TERMINAL_PORT), "bash", "-i", "-c", f"{opencode_bin}; exec bash"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    print("🚀 Terminal iniciado.")
    time.sleep(2)


def create_wrapper_html(terminal_url, drive_url):
    from html_template import render_wrapper_html
    wrapper_html = render_wrapper_html(terminal_url, drive_url)
    os.makedirs(WRAPPER_DIR, exist_ok=True)
    with open(os.path.join(WRAPPER_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(wrapper_html)


def _find_opencode_config():
    for p in OPENCODE_CONFIG_CANDIDATES:
        if os.path.exists(p):
            return p
    try:
        r = subprocess.run(
            ["find", "/root", os.path.expanduser("~"), "-name", "auth.json", "-path", "*/opencode/*"],
            capture_output=True, text=True, timeout=3
        )
        hits = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        if hits:
            return hits[0]
    except Exception:
        pass
    return None


def _get_keys_file(backup_dir):
    return os.path.join(backup_dir, ".keys.json")


def load_keys_from_drive(backup_dir, env=None):
    loaded = []
    keys_file = _get_keys_file(backup_dir)
    if not os.path.exists(keys_file):
        return loaded
    try:
        with open(keys_file, "r") as f:
            saved = json.load(f)
        for k, v in saved.items():
            if k.startswith("_env_"):
                continue
            env_var = saved.get(f"_env_{k}", "")
            if env_var and v:
                os.environ[env_var] = v
                if env is not None:
                    env[env_var] = v
                _write_key_to_bashrc(env_var, v, k)
                loaded.append(env_var)
    except Exception as e:
        logger.warning("Erro ao carregar keys do Drive: %s", e)
    return loaded


def _write_key_to_bashrc(env_var, value, provider_key):
    try:
        bashrc = os.path.expanduser("~/.bashrc")
        marker = f"# opencode-key-{provider_key}"
        export_line = f'export {env_var}="{value}"'
        lines = []
        if os.path.exists(bashrc):
            with open(bashrc, "r") as f:
                lines = f.readlines()
        lines = [l for l in lines if marker not in l and (env_var not in l or "export" not in l)]
        lines.append(f"{export_line}  {marker}\n")
        with open(bashrc, "w") as f:
            f.writelines(lines)
    except Exception:
        pass


def _save_key_to_drive(backup_dir, provider, key, env_var):
    keys_file = _get_keys_file(backup_dir)
    try:
        try:
            with open(keys_file, "r") as f:
                keys = json.load(f)
        except Exception:
            keys = {}
        keys[provider] = key
        if env_var:
            keys[f"_env_{provider}"] = env_var
        with open(keys_file, "w") as f:
            json.dump(keys, f, indent=2)
        return True
    except Exception as e:
        logger.error("Falha ao salvar key no Drive: %s", e)
        return False


def _run_opencode(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, env=_env, **kw)


def _get_system_info():
    info = {
        "version": VERSION,
        "uptime_seconds": int(time.time() - _start_time),
        "opencode_bin": _opencode_bin,
        "ttyd_installed": shutil.which("ttyd") is not None,
        "drive_mounted": os.path.isdir("/content/drive/My Drive"),
    }
    try:
        import psutil
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        info["memory"] = {
            "total_mb": round(psutil.virtual_memory().total / 1024 / 1024),
            "available_mb": round(psutil.virtual_memory().available / 1024 / 1024),
            "percent": psutil.virtual_memory().percent,
        }
        info["disk"] = {
            "total_gb": round(psutil.disk_usage("/").total / 1024 / 1024 / 1024, 1),
            "free_gb": round(psutil.disk_usage("/").free / 1024 / 1024 / 1024, 1),
            "percent": psutil.disk_usage("/").percent,
        }
    except ImportError:
        try:
            r = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=2)
            info["memory_raw"] = r.stdout
        except Exception:
            pass
    return info


def _export_session_to_doc(session_id, backup_dir):
    r = _run_opencode([_opencode_bin, "export", session_id, "--format", "json"])
    if r.returncode != 0:
        r2 = _run_opencode([_opencode_bin, "export", session_id])
        if r2.returncode != 0:
            return None, "Erro ao exportar sessão."
        content = r2.stdout
    else:
        content = r.stdout
    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(backup_dir, f"export_{session_id[:12]}_{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(content)
    md_path = os.path.join(backup_dir, f"export_{session_id[:12]}_{ts}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Sessão PesquisAI: {session_id}\n\n")
        f.write(f"Exportada em: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        f.write("```json\n")
        f.write(content[:10000])
        f.write("\n```\n")
    return {"json": json_path, "md": md_path}, None


def _list_projects(projects_dir):
    if not os.path.isdir(projects_dir):
        return []
    projects = []
    for name in sorted(os.listdir(projects_dir)):
        proj_path = os.path.join(projects_dir, name)
        if os.path.isdir(proj_path):
            meta = {"name": name, "path": proj_path}
            meta_file = os.path.join(proj_path, ".project.json")
            if os.path.exists(meta_file):
                try:
                    with open(meta_file) as f:
                        meta.update(json.load(f))
                except Exception:
                    pass
            projects.append(meta)
    return projects


def _create_project(projects_dir, name, description=""):
    proj_path = os.path.join(projects_dir, name)
    os.makedirs(proj_path, exist_ok=True)
    meta = {
        "name": name,
        "description": description,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(os.path.join(proj_path, ".project.json"), "w") as f:
        json.dump(meta, f, indent=2)
    subdirs = ["backups", "exports", "notes"]
    for d in subdirs:
        os.makedirs(os.path.join(proj_path, d), exist_ok=True)
    return meta


def start_wrapper_server():
    backup_dir = _get_drive_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    print(f"📁 {_('backup_dir')}: {backup_dir}")

    projects_dir = _get_projects_dir()

    config_backup = os.path.join(backup_dir, "opencode_auth.json")

    def _save_opencode_config():
        src = _find_opencode_config()
        if src and os.path.exists(src):
            shutil.copy2(src, config_backup)
            return src
        return None

    def _restore_opencode_config():
        if not os.path.exists(config_backup):
            return False
        restored = False
        for dest in OPENCODE_CONFIG_CANDIDATES:
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(config_backup, dest)
                restored = True
            except Exception:
                pass
        return restored

    if _restore_opencode_config():
        print(f"🔑 {_('key_restored')}")

    loaded = load_keys_from_drive(backup_dir, env=_env)
    if loaded:
        print(f"🔑 {_('key_loaded')}: {', '.join(loaded)}")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            logger.info("HTTP %s — %s", self.address_string(), fmt % args)

        def _json(self, code, data):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST")
            self.end_headers()

        def do_GET(self):
            p = urlparse(self.path).path

            if p in ("/", "/index.html"):
                idx = os.path.join(WRAPPER_DIR, "index.html")
                content = open(idx, "rb").read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

            if p == "/api/sessions":
                r = _run_opencode(cmd=["opencode", "session", "list", "--format", "json"])
                try:
                    sessions = json.loads(r.stdout) if r.stdout.strip() else []
                except Exception:
                    sessions = [{"id": l.strip()} for l in r.stdout.splitlines() if l.strip()]
                self._json(200, {"sessions": sessions})
                return

            if p == "/api/backups":
                try:
                    files = sorted(
                        [f for f in os.listdir(backup_dir) if f.endswith(".json") and not f.startswith(".")],
                        reverse=True
                    )
                except Exception:
                    files = []
                self._json(200, {"backups": files})
                return

            if p == "/api/health":
                info = _get_system_info()
                info["status"] = "ok"
                info["drive_url"] = _drive_url
                self._json(200, info)
                return

            if p == "/api/debug":
                keys_file = os.path.join(backup_dir, ".keys.json")
                keys_exist = os.path.exists(keys_file)
                keys_data = {}
                if keys_exist:
                    try:
                        with open(keys_file) as f:
                            raw = json.load(f)
                        keys_data = {k: (v[:6] + "…" if not k.startswith("_env_") and v else v)
                                     for k, v in raw.items()}
                    except Exception as e:
                        keys_data = {"error": str(e)}
                self._json(200, {
                    "drive_backup_dir": backup_dir,
                    "drive_dir_exists": os.path.isdir(backup_dir),
                    "keys_file_exists": keys_exist,
                    "keys_data": keys_data,
                    "opencode_bin": _opencode_bin,
                    "env_keys": [k for k in _env if "KEY" in k or "TOKEN" in k or "SECRET" in k],
                })
                return

            if p == "/api/apikey":
                qs = parse_qs(urlparse(self.path).query)
                provider = qs.get("provider", [""])[0].strip()
                keys_file = os.path.join(backup_dir, ".keys.json")
                try:
                    with open(keys_file, "r") as f:
                        keys = json.load(f)
                except Exception:
                    keys = {}
                if provider:
                    self._json(200, {"apikey": keys.get(provider, "")})
                else:
                    self._json(200, {"keys": keys})
                return

            if p == "/api/projects":
                projects = _list_projects(projects_dir)
                self._json(200, {"projects": projects})
                return

            if p.startswith("/api/projects/") and p.endswith("/switch"):
                name = p.split("/")[3]
                proj_path = os.path.join(projects_dir, name)
                if os.path.isdir(proj_path):
                    logger.info(f"Projeto alterado para: {name}")
                    self._json(200, {"ok": True, "project": name})
                else:
                    self._json(404, {"error": f"Projeto não encontrado: {name}"})
                return

            self.send_error(404)

        def do_POST(self):
            p = urlparse(self.path).path
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            if p == "/api/apikey":
                provider = body.get("provider", "").strip()
                env_var = body.get("env", "").strip()
                key = body.get("apikey", "").strip()
                if not key or not provider:
                    self._json(400, {"error": "provider e apikey obrigatórios."})
                    return
                if not _save_key_to_drive(backup_dir, provider, key, env_var):
                    self._json(500, {"error": "Falha ao salvar no Drive"})
                    return
                if env_var:
                    os.environ[env_var] = key
                    _env[env_var] = key
                _write_key_to_bashrc(env_var, key, provider)
                self._json(200, {"ok": True})
                return

            if p == "/api/apikey/apply":
                applied = load_keys_from_drive(backup_dir, env=_env)
                self._json(200, {"ok": True, "applied": applied})
                return

            if p == "/api/run_terminal":
                cmd = body.get("command", "").strip()
                no_fallback = body.get("no_fallback", False)
                if not cmd:
                    self._json(400, {"error": "Comando vazio."})
                    return
                load_keys_from_drive(backup_dir, env=_env)
                subprocess.run(
                    "pkill -9 -f ttyd 2>/dev/null; pkill -9 -f opencode 2>/dev/null; true",
                    shell=True
                )
                time.sleep(1.5)
                bash_cmd = f"{cmd}; exec bash" if no_fallback else f"{cmd}; {_opencode_bin}; exec bash"
                subprocess.Popen(
                    ["ttyd", "--writable", "-p", str(TERMINAL_PORT),
                     "bash", "-i", "-c", bash_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=_env,
                )
                self._json(200, {"ok": True, "command": cmd})
                return

            if p == "/api/backup":
                os.makedirs(backup_dir, exist_ok=True)
                session_id = body.get("session_id", "")
                ts = time.strftime("%H-%M-%S_%d-%m-%Y")
                if not session_id:
                    r = _run_opencode([_opencode_bin, "session", "list", "--format", "json"])
                    try:
                        sessions = json.loads(r.stdout)
                        session_id = sessions[0].get("id", "") if sessions else ""
                    except Exception:
                        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
                        session_id = lines[0] if lines else ""
                if not session_id:
                    self._json(400, {"error": _("no_session")})
                    return
                fname = f"backup_{session_id[:12]}_{ts}.json"
                outpath = os.path.join(backup_dir, fname)
                r = _run_opencode([_opencode_bin, "export", session_id, "--format", outpath])
                if r.returncode != 0 or not os.path.exists(outpath):
                    r2 = _run_opencode([_opencode_bin, "export", session_id])
                    if r2.returncode == 0 and r2.stdout.strip():
                        with open(outpath, "w") as f:
                            f.write(r2.stdout)
                    else:
                        self._json(500, {"error": r.stderr or r2.stderr or "Falha ao exportar."})
                        return
                self._json(200, {
                    "ok": True, "file": fname,
                    "session_id": session_id, "path": outpath,
                })
                return

            if p == "/api/restore":
                fname = body.get("file", "")
                if not fname:
                    self._json(400, {"error": "Nome do arquivo não informado."})
                    return
                fpath = os.path.join(backup_dir, fname)
                if not os.path.exists(fpath):
                    self._json(404, {"error": f"Arquivo não encontrado: {fname}"})
                    return
                r = _run_opencode([_opencode_bin, "import", fpath])
                if r.returncode != 0:
                    self._json(500, {"error": r.stderr.strip() or "Falha ao importar."})
                    return
                session_id = ""
                parse_error = ""
                try:
                    import re as _re
                    with open(fpath, "r", encoding="utf-8") as jf:
                        raw = jf.read(4096)
                    m = _re.search(r'"id"\s*:\s*"(ses_[a-zA-Z0-9]+)"', raw)
                    if m:
                        session_id = m.group(1)
                except Exception as e:
                    parse_error = str(e)
                self._json(200, {
                    "ok": True, "file": fname, "session_id": session_id,
                    "parse_error": parse_error,
                    "import_stdout": r.stdout.strip()[:300],
                    "message": _("session_imported"),
                })
                return

            if p == "/api/export":
                session_id = body.get("session_id", "")
                if not session_id:
                    r = _run_opencode([_opencode_bin, "session", "list", "--format", "json"])
                    try:
                        sessions = json.loads(r.stdout)
                        session_id = sessions[0].get("id", "") if sessions else ""
                    except Exception:
                        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
                        session_id = lines[0] if lines else ""
                if not session_id:
                    self._json(400, {"error": _("no_session")})
                    return
                result, err = _export_session_to_doc(session_id, backup_dir)
                if err:
                    self._json(500, {"error": err})
                    return
                self._json(200, {
                    "ok": True, "session_id": session_id,
                    "files": result,
                    "message": _("session_exported"),
                })
                return

            if p == "/api/projects":
                name = body.get("name", "").strip()
                if not name:
                    self._json(400, {"error": "Nome do projeto é obrigatório."})
                    return
                description = body.get("description", "")
                meta = _create_project(projects_dir, name, description)
                self._json(200, {"ok": True, "project": meta})
                return

            self.send_error(404)

    threading.Thread(
        target=lambda: HTTPServer(("0.0.0.0", WRAPPER_PORT), Handler).serve_forever(),
        daemon=True,
    ).start()
    print(f"\n{next_joke('economia')}")
    print(f"🚀 {_('launch_wrapper')} {WRAPPER_PORT}")


def show_ready_message():
    if not IN_COLAB or not display or not HTML:
        print(f"\n✨ {_('launch_ready')}\n")
        return
    from html_template import render_ready_badge_html
    display(HTML(render_ready_badge_html()))


def show_launch_button(banner_url):
    if not IN_COLAB or not display or not HTML:
        print(f"\n🎉 Acesse: {banner_url}")
        return

    display(HTML(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@500;700&family=Syne:wght@700;800&display=swap');
  @keyframes pulse-glow {{
    0%, 100% {{ box-shadow: 0 0 20px rgba(79,195,247,0.3), 0 4px 12px rgba(0,0,0,0.3); }}
    50% {{ box-shadow: 0 0 40px rgba(79,195,247,0.6), 0 6px 20px rgba(0,0,0,0.4); }}
  }}
  .btn-container {{
    display: flex; justify-content: center; padding: 20px; margin-top: 10px;
  }}
  .pesquisai-launch {{
    display: inline-flex; align-items: center; justify-content: center;
    gap: 16px; padding: 24px 56px;
    font-family: "Syne", sans-serif; font-size: 22px; font-weight: 800;
    letter-spacing: 0.08em; color: #0d0f10;
    background: linear-gradient(135deg, #4fc3f7 0%, #29b6f6 50%, #03a9f4 100%);
    border: none; border-radius: 14px; cursor: pointer; text-decoration: none;
    animation: pulse-glow 2.5s ease-in-out infinite;
    position: relative; overflow: hidden;
  }}
  .pesquisai-launch::before {{
    content: ''; position: absolute; top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    transition: left 0.5s;
  }}
  .pesquisai-launch:hover::before {{ left: 100%; }}
  .pesquisai-launch:hover {{
    transform: translateY(-4px) scale(1.02); filter: brightness(1.1);
    box-shadow: 0 12px 40px rgba(79,195,247,0.5), 0 8px 24px rgba(0,0,0,0.4);
  }}
  .pesquisai-launch:active {{ transform: translateY(-1px) scale(0.99); }}
  .btn-icon {{ font-size: 28px; }}
  .btn-text {{ display: flex; flex-direction: column; align-items: flex-start; gap: 2px; }}
  .btn-main {{ font-size: 22px; font-weight: 800; }}
  .btn-sub {{
    font-family: "DM Mono", monospace; font-size: 11px; font-weight: 500;
    opacity: 0.8; letter-spacing: 0.1em;
  }}
  .arrow {{ font-size: 28px; font-weight: 500; transition: transform 0.2s ease; }}
  .pesquisai-launch:hover .arrow {{ transform: translateX(8px); }}
</style>
<div class="btn-container">
  <a href="{banner_url}" target="_blank" class="pesquisai-launch">
    <span class="btn-icon">🚀</span>
    <span class="btn-text">
      <span class="btn-main">ABRIR O PESQUISAI</span>
      <span class="btn-sub">clique para começar</span>
    </span>
    <span class="arrow">→</span>
  </a>
</div>
"""))


def cleanup():
    subprocess.run("pkill -f ttyd 2>/dev/null || true", shell=True)
    subprocess.run(f"pkill -f 'python3.*{WRAPPER_PORT}' 2>/dev/null || true", shell=True)
    logger.info("Processos limpados no encerramento")


def signal_handler(signum, frame):
    logger.info("Recebido sinal %s, encerrando...", signum)
    cleanup()
    sys.exit(0)


atexit.register(cleanup)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def launch():
    global _drive_url

    resolve_opencode()
    install_ttyd()
    kill_previous()
    start_ttyd()

    if IN_COLAB and output:
        terminal_url = output.eval_js(f"google.colab.kernel.proxyPort({TERMINAL_PORT})")
        banner_url = output.eval_js(f"google.colab.kernel.proxyPort({WRAPPER_PORT})")
    else:
        terminal_url = f"http://localhost:{TERMINAL_PORT}"
        banner_url = f"http://localhost:{WRAPPER_PORT}"

    create_wrapper_html(terminal_url, _drive_url)
    start_wrapper_server()

    time.sleep(1)
    show_ready_message()
    show_launch_button(banner_url)

    return banner_url


if __name__ == "__main__":
    launch()
