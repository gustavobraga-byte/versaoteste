"""pesquisai/ocweb.py — v0.7.11-web: proxy da interface web do OpenCode.

O OpenCode V2 serve uma SPA em ``http://127.0.0.1:<porta>`` (a mesma do
``service.json``) protegida por HTTP Basic. Este módulo publica essa SPA em
``0.0.0.0:8002`` para o Colab (``proxyPort(8002)``) e para o wrapper,
**injetando a autenticação** e o **tema do UFVAI** (cores, tipografia e
assinatura), sem alterar o binário do motor.

Por que um proxy e não um iframe direto:

* o serviço escuta em ``127.0.0.1`` e exige Basic — o navegador não tem a
  senha (nem deve ter);
* a SPA usa caminhos absolutos (``/_assets/...``) e SSE em ``/api/event``;
  servir na própria origem (porta 8002) evita reescrever o bundle;
* o CSS injetado usa ``style-src 'unsafe-inline'`` do próprio CSP do motor,
  então não é preciso afrouxar a política de scripts.

Compatibilidade: HTTP/1.1, SSE (streaming em chunks) e WebSocket (túnel).
"""
from __future__ import annotations

import base64
import gzip
import http.client
import json
import os
import select
import socket
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .constants import CURRENT_SESSION_FILE

OCWEB_PORT: int = 8002
UPSTREAM_HOST: str = "127.0.0.1"

_THEME = """<style id="ufvai-ocweb-theme">
/* v0.7.11-web — paleta UFVAI (navy + dourado + creme) sobre os tokens do motor */
:root{
  --v2-background-bg-base:#f6f5f0!important;
  --v2-background-bg-deep:#efece4!important;
  --v2-background-bg-layer-01:#ffffff!important;
  --v2-background-bg-layer-02:#f4f2ec!important;
  --v2-background-bg-layer-03:#ebe7dd!important;
  --v2-text-text-base:#23282c!important;
  --v2-text-text-muted:#5f6468!important;
  --v2-text-text-faint:#8b8f92!important;
  --v2-border-border-base:#ddd8cc!important;
  --v2-border-border-muted:#e7e2d6!important;
  --v2-text-text-accent:#8a6d33!important;
  --v2-icon-icon-accent:#8a6d33!important;
  --v2-background-bg-accent:#8a6d33!important;
}
html{background-color:#f6f5f0!important}
html[data-color-scheme="dark"]{
  --v2-background-bg-base:#111518!important;
  --v2-background-bg-deep:#0d0f10!important;
  --v2-background-bg-layer-01:#161b1e!important;
  --v2-background-bg-layer-02:#1b2125!important;
  --v2-background-bg-layer-03:#222a2f!important;
  --v2-text-text-base:#f2f1ea!important;
  --v2-text-text-muted:#a8a49a!important;
  --v2-text-text-faint:#7d7a72!important;
  --v2-border-border-base:#2a3136!important;
  --v2-border-border-muted:#20262a!important;
  --v2-text-text-accent:#d9b45c!important;
  --v2-icon-icon-accent:#d9b45c!important;
  --v2-background-bg-accent:#b29149!important;
  background-color:#0d0f10!important;
}
html::before{content:"";position:fixed;top:0;left:0;right:0;height:3px;
  z-index:2147483647;pointer-events:none;
  background:linear-gradient(90deg,#1e2a34 0%,#1e2a34 58%,#b29149 58%,#b29149 100%)}
body{font-family:"Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif!important}
.ufvai-oc-badge{position:fixed;left:12px;bottom:10px;z-index:2147483647;
  display:flex;align-items:center;gap:5px;padding:5px 9px;border-radius:999px;
  background:rgba(13,15,16,.82);border:1px solid rgba(178,145,73,.5);
  color:#f2f1ea;font:600 10px/1 "Segoe UI",system-ui,sans-serif;
  letter-spacing:.08em;opacity:.9;pointer-events:none;
  box-shadow:0 4px 14px rgba(0,0,0,.25);backdrop-filter:blur(6px)}
.ufvai-oc-badge b{color:#d9b45c;font-weight:800}
</style>"""

_BADGE = (
    '<div class="ufvai-oc-badge" title="UFVAI · OpenCode web">'
    "<span>UFV</span><b>AI</b></div>"
)

_BLOCKED_HEADERS = {
    "transfer-encoding", "content-length", "connection", "content-encoding",
    "proxy-connection", "keep-alive",
}
_SKIP_REQUEST_HEADERS = {
    "host", "authorization", "accept-encoding", "connection",
    "proxy-connection", "content-length",
}


# ── descoberta do serviço ─────────────────────────────────────

def service_file() -> Path:
    """Caminho do ``service.json`` do OpenCode (XDG, HOME ou /root)."""
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        candidate = Path(xdg) / "opencode" / "service.json"
        if candidate.exists():
            return candidate
    home = Path(os.path.expanduser("~")) / ".local" / "state" / "opencode" / "service.json"
    if home.exists():
        return home
    return Path("/root/.local/state/opencode/service.json")


def service_info() -> tuple[str, int, str]:
    """(host, porta, senha) do serviço em execução; ``(host, 0, '')`` se ausente."""
    try:
        data = json.loads(service_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return UPSTREAM_HOST, 0, ""
    url = str(data.get("url") or "")
    port = 0
    if ":" in url:
        try:
            port = int(url.rsplit(":", 1)[1].strip("/"))
        except ValueError:
            port = 0
    return UPSTREAM_HOST, port, str(data.get("password") or "")


def _basic(password: str) -> str:
    raw = f"opencode:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _inject_html(data: bytes, session_id: str = "") -> bytes:
    text = data.decode("utf-8", errors="replace")
    text = text.replace(
        "<title data-sm>OpenCode</title>",
        "<title data-sm>UFVAI · OpenCode</title>",
    )
    if "</head>" in text:
        text = text.replace("</head>", _THEME + "</head>", 1)
    if "</body>" in text:
        text = text.replace("</body>", _BOOT_TAG + _BADGE + "</body>", 1)
    return text.encode("utf-8")



_BOOT_JS = """(function(){
  try{var f=window.fetch;window.fetch=function(u,o){o=o||{};if(o.credentials===undefined||o.credentials==="omit")o.credentials="same-origin";return f.call(this,u,o)}}catch(e){}
  function b64(s){return btoa(unescape(encodeURIComponent(s))).replace(/\\+/g,"-").replace(/\\//g,"_").replace(/=+$/,"")}
  function key(){var a=document.querySelector('a[href*="/server/"][href*="/session/"]');if(!a)return "";var m=(a.getAttribute("href")||"").match(/\\/server\\/([^\\/]+)\\/session\\//);return m?m[1]:""}
  function catalog(cb){fetch("/__ufvai/catalog",{cache:"no-store"}).then(function(r){return r.ok?r.json():null}).then(function(d){cb(d||{ready:true})}).catch(function(){cb({ready:true})})}
  function whenReady(cb,t){
    catalog(function(d){
      if(d&&d.ready)return cb(true);
      if(t<=0)return cb(false);
      setTimeout(function(){whenReady(cb,t-1)},600);
    });
  }
  // Sessão: espera o catálogo de provedores/modelos antes de navegar.
  var n=0,t=setInterval(function(){
    n++;
    if(location.pathname!=="/"){clearInterval(t);return}
    var k=key();if(!k&&n>=6)k=b64(location.origin);
    if(!k){if(n>40)clearInterval(t);return}
    clearInterval(t);
    fetch("/__ufvai/session?fallback=1",{cache:"no-store"}).then(function(r){return r.ok?r.json():null}).then(function(d){
      var go=function(){ if(d&&d.sid)location.replace("/server/"+k+"/session/"+d.sid); };
      if(d&&d.sid)whenReady(go,20); else go();
    }).catch(function(){});
  },700);
  // Numa sessão aberta direto: se o catálogo NÃO estava pronto no load e
  // ficou pronto depois, recarrega UMA vez para a SPA buscar os modelos.
  if(/^\\/server\\/[^\\/]+\\/session\\//.test(location.pathname)){
    catalog(function(d0){
      if(d0&&d0.ready)return;
      whenReady(function(ok){
        if(!ok)return;
        try{
          var k="ufvai.catalog.reload."+location.pathname;
          if(sessionStorage.getItem(k))return;
          sessionStorage.setItem(k,"1");
          setTimeout(function(){location.reload()},400);
        }catch(e){}
      },20);
    });
  }
})();"""


_BOOT_TAG = '<script src="/__ufvai/boot.js"></script>'


def current_session() -> str:
    """Sessão que a interface deve abrir (gravada por launch_app)."""
    try:
        return Path(CURRENT_SESSION_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _session_exists(host: str, port: int, password: str, sid: str) -> bool:
    if not sid:
        return False
    conn = http.client.HTTPConnection(host, port, timeout=3)
    try:
        conn.request("GET", f"/api/session/{sid}",
                     headers={"Authorization": _basic(password)})
        resp = conn.getresponse()
        resp.read()
        return resp.status == 200
    except OSError:
        return False
    finally:
        conn.close()


def _api_json(path: str, timeout: float = 5.0):
    """GET JSON no serviço do OpenCode (``None`` em falha)."""
    host, port, password = service_info()
    if not port:
        return None
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request(
            "GET",
            path,
            headers={"Authorization": _basic(password), "Accept": "application/json"},
        )
        resp = conn.getresponse()
        data = resp.read()
        if resp.status != 200:
            return None
        return json.loads(data.decode("utf-8", "replace"))
    except (OSError, ValueError):
        return None
    finally:
        conn.close()


_CATALOG_CACHE: dict = {"ts": 0.0, "data": {"ready": False, "models": 0, "providers": 0}}
_CATALOG_LOCK = threading.Lock()


def catalog(force: bool = False, ttl: float = 5.0) -> dict:
    """Estado do catálogo do motor: provedores e modelos já carregados.

    A SPA consulta ``/api/model`` e ``/api/provider`` ao abrir a sessão. Se o
    motor ainda estiver subindo, a resposta pode vir vazia e o seletor de
    modelos fica em branco até um recarregamento. O ``boot.js`` usa este
    endpoint para esperar o catálogo antes de navegar.
    """
    now = time.time()
    with _CATALOG_LOCK:
        if not force and now - float(_CATALOG_CACHE["ts"]) < ttl:
            return dict(_CATALOG_CACHE["data"])
    models = _api_json("/api/model")
    providers = _api_json("/api/provider")
    rows = models.get("data") if isinstance(models, dict) else None
    provs = providers.get("data") if isinstance(providers, dict) else None
    data = {
        "ready": bool(rows),
        "models": len(rows or []),
        "providers": len(provs or []),
        "upstream": f"http://{service_info()[0]}:{service_info()[1]}",
    }
    with _CATALOG_LOCK:
        _CATALOG_CACHE.update(ts=now, data=data)
    return dict(data)


def latest_session() -> str:
    """Sessão usada pelo terminal: ativa ou a mais recente."""
    active = _api_json("/api/session/active")
    data = active.get("data") if isinstance(active, dict) else None
    if isinstance(data, dict):
        for sid, info in data.items():
            if not isinstance(info, dict):
                continue
            if info.get("type") in ("running", "busy", "pending"):
                return str(sid)
    listing = _api_json("/api/session?limit=1&order=desc")
    rows = listing.get("data") if isinstance(listing, dict) else None
    if isinstance(rows, list) and rows:
        return str(rows[0].get("id") or "")
    return ""


_SYNC_EVENTS = {
    "session.created",
    "session.viewed",
    "session.execution.started",
    "session.model.selected",
}


def _remember_session(sid: str) -> None:
    sid = str(sid or "").strip()
    if not sid:
        return
    try:
        tmp = f"{CURRENT_SESSION_FILE}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(sid)
        os.replace(tmp, CURRENT_SESSION_FILE)
    except OSError:
        pass


def _sync_session_from_event(chunk: bytes) -> None:
    """Persiste a sessão ativa vista no SSE (terminal ↔ web).

    O terminal e a SPA usam o mesmo motor; quando o usuário cria/troca de
    sessão na TUI, o evento chega aqui e o próximo boot/reload da web abre
    a mesma conversa.
    """
    try:
        text = chunk.decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return
    for block in text.split("\n\n"):
        if not any(ev in block for ev in _SYNC_EVENTS):
            continue
        line = next(
            (ln for ln in block.splitlines() if ln.startswith("data: ")), None
        )
        if not line:
            continue
        try:
            payload = json.loads(line[6:])
        except ValueError:
            continue
        if payload.get("type") not in _SYNC_EVENTS:
            continue
        data = payload.get("data") or {}
        if not isinstance(data, dict):
            continue
        sid = data.get("sessionID")
        if not sid and isinstance(data.get("session"), dict):
            sid = data["session"].get("id")
        if sid:
            _remember_session(str(sid))




# ── proxy HTTP/SSE/WebSocket ─────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "UFVAI-OCWeb/0.7.11"

    def log_message(self, *_args):  # silencioso (o wrapper já tem log)
        pass

    def _upstream(self) -> tuple[str, int, str]:
        host, port, password = service_info()
        if not port:
            raise ConnectionError(
                "serviço do OpenCode sem service.json — aguardando o motor subir"
            )
        return host, port, password

    def _read_body(self) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        return self.rfile.read(length) if length > 0 else None

    def _forward_headers(self, password: str) -> dict[str, str]:
        headers: dict[str, str] = {}
        for key, value in self.headers.items():
            if key.lower() in _SKIP_REQUEST_HEADERS:
                continue
            headers[key] = value
        headers["Authorization"] = _basic(password)
        headers["Accept-Encoding"] = "identity"
        headers["Connection"] = "close"
        return headers

    # WebSocket: túnel cru (a SPA usa SSE para o chat; o WS cobre o PTY)
    def _websocket(self, host: str, port: int, password: str) -> None:
        try:
            upstream = socket.create_connection((host, port), timeout=10)
        except OSError:
            self.send_error(502, "OpenCode indisponível")
            return
        lines = [f"GET {self.path} HTTP/1.1", f"Host: {host}:{port}"]
        for key, value in self.headers.items():
            if key.lower() in {"host", "authorization", "connection"}:
                continue
            lines.append(f"{key}: {value}")
        lines.append(f"Authorization: {_basic(password)}")
        lines.append("Connection: Upgrade")
        request = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1", "replace")
        try:
            upstream.sendall(request)
            head = b""
            while b"\r\n\r\n" not in head and len(head) < 65536:
                chunk = upstream.recv(4096)
                if not chunk:
                    break
                head += chunk
            self.wfile.write(head)
            self.wfile.flush()
            sockets = [self.connection, upstream]
            while True:
                read, _, _ = select.select(sockets, [], [], 60)
                if not read:
                    continue
                for sock in read:
                    data = sock.recv(65536)
                    if not data:
                        return
                    (upstream if sock is self.connection else self.connection).sendall(data)
        except OSError:
            pass
        finally:
            upstream.close()

    def _health(self) -> None:
        """``/__ufvai_ready`` — estado do proxy e do motor, com CORS.

        Serve de health-check independente do wrapper (o boot pode consultar
        direto a porta 8002) e evita depender de uma rota ``/api/*`` que o
        motor possa reivindicar no futuro.
        """
        host, port, _ = service_info()
        body = json.dumps(
            {
                "ready": bool(port) and ready(self.server.server_address[1], timeout=0.25),
                "proxy": "ufvai-ocweb",
                "upstream": f"http://{host}:{port}" if port else "",
                "pid": os.getpid(),
            }
        ).encode("utf-8")
        self.send_response(200 if port else 503)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _boot_js(self) -> None:
        body = _BOOT_JS.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _catalog_info(self) -> None:
        body = json.dumps(catalog()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _session_info(self) -> None:
        host, port, password = service_info()
        sid = current_session()
        source = "persisted"
        if not _session_exists(host, port, password, sid):
            sid = ""
        qs = parse_qs(urlparse(self.path).query)
        fallback = qs.get("fallback", ["0"])[0].lower() in ("1", "true", "yes")
        if not sid and fallback:
            # v0.7.11-web5: o terminal pode ter criado/trocado a sessão sem
            # reiniciar o ttyd. Cair para a sessão ativa/mais recente mantém
            # web e terminal na mesma conversa.
            sid = latest_session()
            source = "latest"
        body = json.dumps({"sid": sid, "source": source}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method: str) -> None:
        rota = self.path.split("?", 1)[0]
        if rota == "/__ufvai_ready":
            self._health()
            return
        if rota == "/__ufvai/boot.js":
            self._boot_js()
            return
        if rota == "/__ufvai/session":
            self._session_info()
            return
        if rota == "/__ufvai/catalog":
            self._catalog_info()
            return

        if self.headers.get("Upgrade", "").lower() == "websocket":
            host, port, password = self._upstream()
            self._websocket(host, port, password)
            return

        try:
            host, port, password = self._upstream()
        except ConnectionError as exc:
            body = (
                "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
                "<meta http-equiv=\"refresh\" content=\"3\">"
                "<title>UFVAI · OpenCode</title><style>"
                "body{margin:0;min-height:100vh;display:flex;align-items:center;"
                "justify-content:center;background:#0d0f10;color:#f2f1ea;"
                "font:14px/1.6 'Segoe UI',system-ui,sans-serif}"
                ".b{max-width:520px;padding:28px 32px;border:1px solid #2a3136;"
                "border-radius:16px;background:#111518}"
                "b{color:#d9b45c}small{color:#a8a49a;display:block;margin-top:8px}"
                "</style></head><body><div class=\"b\">"
                "<h2 style=\"margin:0 0 8px\">UFV<b>AI</b> · OpenCode</h2>"
                "<p>O motor do OpenCode ainda não está disponível.</p>"
                "<small>Esta página recarrega sozinha a cada 3 s. "
                "Se persistir, conclua o onboarding da chave de API.</small>"
                "</div></body></html>"
            ).encode("utf-8")
            self.send_response(503)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Retry-After", "3")
            self.end_headers()
            self.wfile.write(body)
            return

        body = self._read_body()
        headers = self._forward_headers(password)
        conn = http.client.HTTPConnection(host, port, timeout=600)
        try:
            # v0.7.11-web5: uma tentativa extra cobre o reinício do motor
            # (service.json muda de porta) sem devolver 502 para a SPA.
            resp = None
            for attempt in range(2):
                try:
                    conn.request(method, self.path, body=body, headers=headers)
                    resp = conn.getresponse()
                    break
                except OSError:
                    try:
                        conn.close()
                    except OSError:
                        pass
                    if attempt == 0:
                        time.sleep(0.15)
                        conn = http.client.HTTPConnection(host, port, timeout=600)
                        continue
                    raise
            assert resp is not None
            ctype = (resp.getheader("Content-Type") or "").lower()

            if ctype.startswith("text/event-stream"):
                self.send_response(resp.status)
                for key, value in resp.getheaders():
                    if key.lower() in _BLOCKED_HEADERS:
                        continue
                    self.send_header(key, value)
                self.send_header("Transfer-Encoding", "chunked")
                self.send_header("Cache-Control", "no-cache, no-store, no-transform")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                self.close_connection = True
                tail = b""
                try:
                    while True:
                        chunk = resp.read1(4096)
                        if not chunk:
                            break
                        if tail or b'"type":"session.' in chunk:
                            buf = tail + chunk
                            if b"\n\n" in buf:
                                events, _, tail = buf.rpartition(b"\n\n")
                                _sync_session_from_event(events)
                                if len(tail) > 65536:
                                    tail = tail[-4096:]
                            else:
                                tail = buf[-65536:]
                        self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
                        self.wfile.flush()
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return

            data = resp.read()
            encoding = (resp.getheader("Content-Encoding") or "").lower().strip()
            if encoding in ("gzip", "x-gzip"):
                try:
                    data = gzip.decompress(data)
                except OSError:
                    pass
            elif encoding == "deflate":
                try:
                    data = zlib.decompress(data)
                except zlib.error:
                    try:
                        data = zlib.decompress(data, -zlib.MAX_WBITS)
                    except zlib.error:
                        pass
            if ctype.startswith("text/html") and resp.status == 200:
                sid = current_session()
                if not _session_exists(host, port, password, sid):
                    sid = ""
                data = _inject_html(data, sid)

            self.send_response(resp.status)
            for key, value in resp.getheaders():
                if key.lower() in _BLOCKED_HEADERS:
                    continue
                self.send_header(key, value)
            # v0.7.11-web5: API nunca deve vir do cache do navegador — um
            # /api/model vazio (motor subindo) ficaria "grudado" no reload.
            if self.path.startswith("/api/") or self.path.startswith("/__ufvai/"):
                self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except OSError:
            try:
                self.send_error(502, "OpenCode indisponível")
            except OSError:
                pass
        finally:
            conn.close()

    do_GET = lambda self: self._handle("GET")  # type: ignore[assignment]
    do_POST = lambda self: self._handle("POST")  # type: ignore[assignment]
    do_PUT = lambda self: self._handle("PUT")  # type: ignore[assignment]
    do_PATCH = lambda self: self._handle("PATCH")  # type: ignore[assignment]
    do_DELETE = lambda self: self._handle("DELETE")  # type: ignore[assignment]
    do_HEAD = lambda self: self._handle("HEAD")  # type: ignore[assignment]
    do_OPTIONS = lambda self: self._handle("OPTIONS")  # type: ignore[assignment]


# ── ciclo de vida ────────────────────────────────────────────

_SERVER: ThreadingHTTPServer | None = None
_THREAD: threading.Thread | None = None
_LOCK = threading.Lock()


class _Server(ThreadingHTTPServer):
    """Servidor do proxy com fila maior.

    A SPA dispara ~20 requisições em paralelo ao abrir uma sessão. O backlog
    padrão do ``socketserver`` (5) recusava conexões nesse pico — a SPA
    marcava "Can't reach this server" e algumas mensagens ficavam pendentes.
    """

    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128


def start(port: int = 8002) -> bool:
    """Sobe o proxy em ``0.0.0.0:<port>`` (idempotente)."""
    return _start(port)


def _start(port: int = 8002) -> bool:
    global _SERVER, _THREAD
    with _LOCK:
        if _SERVER is not None:
            return True
        try:
            server = _Server(("0.0.0.0", int(port)), _Handler)
            thread = threading.Thread(
                target=server.serve_forever,
                name="ufvai-ocweb",
                daemon=True,
            )
            thread.start()
            _SERVER, _THREAD = server, thread
            return True
        except OSError:
            return False


def stop() -> None:
    global _SERVER, _THREAD
    with _LOCK:
        server, _SERVER = _SERVER, None
        _THREAD = None
    if server is not None:
        try:
            server.shutdown()
            server.server_close()
        except OSError:
            pass


def status() -> dict:
    host, port, _ = service_info()
    server = _SERVER
    return {
        "proxy_port": int(server.server_address[1]) if server else 0,
        "upstream": f"http://{host}:{port}" if port else "",
        "upstream_ready": bool(port),
        "running": bool(server),
    }


def ready(port: int = 8002, timeout: float = 0.4) -> bool:
    """Proxy no ar **e** serviço do OpenCode respondendo."""
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
            pass
    except OSError:
        return False
    host, upstream, _ = service_info()
    if not upstream:
        return False
    try:
        with socket.create_connection((host, int(upstream)), timeout=timeout):
            return True
    except OSError:
        return False
