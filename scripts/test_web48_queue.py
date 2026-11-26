#!/usr/bin/env python3
"""web48 — validação da fila multi-sessão (backend + contratos do frontend).

Roda: python3 scripts/test_web48_queue.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ok = 0
fail = 0


def check(label: str, cond: bool) -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok  {label}")
    else:
        fail += 1
        print(f"  FAIL {label}")


print("\n[1] normalize_event: session.inbox.enqueued")
# Carrega o arquivo DESTA árvore (o ambiente tem /tmp/pesquisai no sys.path,
# que aponta para uma cópia antiga com o bug do UnboundLocalError).
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "webapi_web48", ROOT / "pesquisai" / "webapi.py"
)
webapi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(webapi)
check("webapi carregado da árvore web48", str(ROOT) in str(webapi.__file__))

for evento in (
    {"type": "session.inbox.enqueued", "data": {"sessionID": "s1", "text": "ola"}},
    {"type": "session.inbox.enqueued", "data": {"sessionID": "s1", "item": {"text": "ola"}}},
    {"type": "session.inbox.enqueued", "data": {"sessionID": "s1", "payload": {"text": "ola"}}},
):
    try:
        ev = webapi.normalize_event(evento)
        check(f"sid/text preservados ({list(evento['data'])[1]})",
              ev == {"type": "inbox.enqueued", "sid": "s1", "text": "ola"})
    except Exception as exc:  # noqa: BLE001
        check(f"sem exceção ({list(evento['data'])[1]}): {exc}", False)

ev = webapi.normalize_event(
    {"type": "session.inbox.delivered", "data": {"sessionID": "s2"}}
)
check("inbox.delivered preserva o sid", ev == {"type": "inbox.delivered", "sid": "s2"})

print("\n[2] contratos do frontend")
app = (ROOT / "pesquisai/webui/app.js").read_text(encoding="utf-8")
check("item da fila carrega sid", "const item = { sid: destino, text," in app)
check("postQueuedItem resolve sid antes do await",
      "const sid = item.sid || state.sessionId;" in app)
check("POST usa sid do item",
      "await apiPost(`/sessions/${encodeURIComponent(sid)}/message`" in app)
check("flush filtra por sessão de destino",
      "(it) => !it.sid || !state.sessionId || it.sid === state.sessionId" in app)
check("fallback do flush passa sid explícito",
      "await send({ force: true, sid: item.sid || state.sessionId });" in app)
check("SSE reconecta no sid de destino", "connectEvents(desejado);" in app)
check("inbox tratada antes do filtro de sessão", "handleInboxEvent(ev);" in app)

print(f"\nRESULTADO: {ok} passaram, {fail} falharam")
sys.exit(1 if fail else 0)
