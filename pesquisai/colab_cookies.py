"""
colab_cookies.py — Verifica se o Colab permite cookies de terceiros para o proxy.

A interface do UFVAI abre pelo proxy do Colab (https://<porta>-<id>.prod.colab.dev).
Quando o navegador bloqueia cookies de terceiros, esse proxy não abre. O teste
roda num iframe dentro da própria saída da célula, apontando para uma página
mínima servida pelo kernel através do proxy. Essa página tenta gravar um cookie
e avisa a célula por postMessage. Sem resposta a tempo, o alerta é mostrado
como "não confirmado".

Sem Colab (offline/.deb) o módulo não faz nada.
"""

from __future__ import annotations

import html
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .constants import logger

try:  # pragma: no cover - depende do ambiente
    import google.colab  # type: ignore  # noqa: F401
    IN_COLAB = True
except ImportError:  # pragma: no cover
    IN_COLAB = False

PROBE_PATH = "/ufvai-cookie-probe"
DEFAULT_TIMEOUT_S = 20.0


# Página servida pelo kernel (através do proxy). Roda como terceiro no iframe.
PROBE_PAGE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>UFVAI · teste de cookies</title></head>
<body>
<script>
(function () {
  var result = {ufvai: "cookie-probe", ok: false, cookieEnabled: navigator.cookieEnabled, error: ""};
  try {
    document.cookie = "ufvai_probe=1; path=/; SameSite=None; Secure";
    result.ok = document.cookie.indexOf("ufvai_probe=1") !== -1;
  } catch (e) {
    result.error = String((e && e.message) || e);
  }
  try { window.parent.postMessage(result, "*"); } catch (e) {}
})();
</script>
</body></html>
"""

INSTRUCTIONS_HTML = """
<ol style="margin:8px 0 0 18px;line-height:1.55">
  <li><b>Chrome / Edge:</b> clique no cadeado ao lado do endereço &rarr; <i>Configurações do site</i>
      &rarr; <i>Cookies</i> &rarr; <i>Permitir</i>. Ou em <i>Configurações &rarr; Privacidade e segurança
      &rarr; Cookies de terceiros</i> escolha permitir e inclua <code>[*.]colab.research.google.com</code>
      e <code>[*.]prod.colab.dev</code> como exceções. Os nomes dos menus podem variar conforme a versão.</li>
  <li><b>Firefox:</b> clique no escudo ao lado do endereço &rarr; <i>Desativar proteção contra rastreamento
      para este site</i>. No modo <i>Estrito</i>, o bloqueio de cookies entre sites também precisa ser liberado.</li>
  <li><b>Brave:</b> clique no ícone do leão &rarr; <i>Shields</i> &rarr; desative para este site
      (ou libere cookies para <code>colab.research.google.com</code> e <code>prod.colab.dev</code>).</li>
  <li><b>Safari:</b> <i>Ajustes &rarr; Privacidade</i>: desmarque <i>Impedir rastreamento entre sites</i> e
      <i>Bloquear todos os cookies</i>.</li>
  <li>Use uma janela <b>normal</b> (não anônima/privada) e <b>execute esta célula de novo</b>.
      Depois de confirmado, clique em <b>ABRIR O UFVAI</b>.</li>
</ol>
"""


def probe_page_html() -> str:
    """HTML da página de teste servida pelo kernel."""
    return PROBE_PAGE


def build_status_html(probe_url: str, timeout_ms: int = int(DEFAULT_TIMEOUT_S * 1000)) -> str:
    """Bloco HTML/JS da célula: iframe de teste, estado e instruções.

    O bloco de instruções aparece SEMPRE em um <details> (funciona sem JS). Quando o
    teste falha (ou não responde), o alerta em destaque é exibido por JS.
    """
    url = html.escape(probe_url, quote=True)
    return f"""
<div id="ufvai-cookie-box" style="max-width:640px;margin:10px auto;padding:16px 18px;
     border-radius:12px;border:1px solid rgba(43,45,58,.18);background:#f6f5f0;
     font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#1f2831">
  <div id="ufvai-cookie-status" style="font-size:15px;font-weight:600">
    &#9203; Verificando se o navegador permite cookies de terceiros para o proxy do Colab&hellip;
  </div>
  <div id="ufvai-cookie-warn" style="display:none;margin-top:12px;padding:12px 14px;
       border-radius:10px;background:#fdecea;border:1px solid #e0a09a;color:#571512">
    <div style="font-weight:700;font-size:15px">&#9888;&#65039; Cookies de terceiros bloqueados ou não confirmados</div>
    <div style="margin-top:6px;font-size:14px">
      A interface do UFVAI roda em <code>*.prod.colab.dev</code>. Sem cookies de terceiros,
      o endereço <b>não abre</b>. Para liberar:
    </div>
    {INSTRUCTIONS_HTML}
  </div>
  <details style="margin-top:12px;font-size:13px">
    <summary style="cursor:pointer">Como liberar cookies (ver sempre)</summary>
    {INSTRUCTIONS_HTML}
  </details>
  <iframe id="ufvai-cookie-frame" src="{url}" title="teste de cookies UFVAI"
          style="width:0;height:0;border:0" tabindex="-1" aria-hidden="true"></iframe>
</div>
<script>
(function () {{
  var box = document.getElementById("ufvai-cookie-box");
  if (!box) {{ return; }}
  var statusEl = document.getElementById("ufvai-cookie-status");
  var warnEl = document.getElementById("ufvai-cookie-warn");
  var frame = document.getElementById("ufvai-cookie-frame");
  var done = false;
  function show(state) {{
    if (done) {{ return; }}
    done = true;
    if (state === "ok") {{
      statusEl.style.color = "#2e7d32";
      statusEl.innerHTML = "&#9989; Cookies de terceiros liberados. Pode clicar em <b>ABRIR O UFVAI</b>.";
    }} else {{
      statusEl.style.color = "#901812";
      statusEl.innerHTML = "&#10060; Não foi possível confirmar os cookies de terceiros.";
      warnEl.style.display = "block";
    }}
  }}
  window.addEventListener("message", function (ev) {{
    if (!ev.data || ev.data.ufvai !== "cookie-probe") {{ return; }}
    if (frame && ev.source !== frame.contentWindow) {{ return; }}
    show(ev.data.ok ? "ok" : "blocked");
  }});
  setTimeout(function () {{ show("timeout"); }}, {int(timeout_ms)});
}})();
</script>
"""


class _ProbeHandler(BaseHTTPRequestHandler):
    """Serve a página de teste. Nenhum dado do usuário é lido ou gravado."""

    def do_GET(self) -> None:  # noqa: N802 (nome exigido pelo http.server)
        body = probe_page_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # silencia o log padrão
        return


def start_probe_server() -> tuple[ThreadingHTTPServer, int]:
    """Sobe o servidor efêmero em 127.0.0.1 numa porta livre."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ProbeHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="ufvai-cookie-probe")
    thread.start()
    return server, port


def _shutdown(server: ThreadingHTTPServer) -> None:
    try:
        server.shutdown()
        server.server_close()
    except Exception:  # noqa: BLE001
        pass


# Evita dois avisos de cookies na mesma execução (o notebook e o run_fast
# podem pedir o teste; o usuário deve ver apenas um bloco).
_COOKIE_CHECK_DONE = False


def ensure_cookie_check(timeout_s: float = DEFAULT_TIMEOUT_S, force: bool = False) -> dict:
    """Dispara o teste de cookies **uma única vez** por processo.

    Usado pelo notebook e pelo `run_fast.setup_launch()`: quem rodar o UFVAI
    por qualquer caminho vê o mesmo aviso, uma vez só.

    Returns:
        O dicionário de `show_cookie_check`, `{'state': 'done'}` quando já
        tinha sido disparado antes, ou `{'state': 'error', 'error': ...}` se a
        chamada falhar — nunca levanta.
    """
    global _COOKIE_CHECK_DONE
    if _COOKIE_CHECK_DONE and not force:
        return {"state": "done"}
    _COOKIE_CHECK_DONE = True
    try:
        return show_cookie_check(timeout_s=timeout_s)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Teste de cookies do Colab falhou: %s", exc)
        return {"state": "error", "error": str(exc)[:200]}


def show_cookie_check(timeout_s: float = DEFAULT_TIMEOUT_S) -> dict:
    """Mostra o teste de cookies na célula (somente no Colab).

    Não bloqueia: o resultado chega ao navegador por postMessage e é exibido
    no próprio bloco. O servidor efêmero é encerrado após o teto de tempo.

    Returns:
        {'state': 'checking', 'port': N} quando o teste foi disparado,
        {'state': 'skipped'} fora do Colab, ou {'state': 'error', 'error': ...}.
    """
    if not IN_COLAB:
        return {"state": "skipped"}
    try:  # pragma: no cover - exige o runtime do Colab
        from google.colab import output  # type: ignore
        from IPython.display import HTML, display  # type: ignore

        server, port = start_probe_server()
        base = output.eval_js(f"google.colab.kernel.proxyPort({port})")
        probe_url = str(base).rstrip("/") + PROBE_PATH
        display(HTML(build_status_html(probe_url, timeout_ms=int(timeout_s * 1000))))
        threading.Timer(timeout_s + 10.0, _shutdown, args=(server,)).start()
        return {"state": "checking", "port": port}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Teste de cookies do Colab falhou: %s", exc)
        return {"state": "error", "error": str(exc)[:200]}
