"""webapi.py — contrato do gateway da versão web do UFVAI (v0.7.11-web17).

Arquitetura **nova** da interface web (escrita do zero, sem a SPA anterior):

    navegador ──► webui_server (:8002) ──► motor OpenCode (API ``/api/*``)

Este módulo é a camada de *tradução*: conhece a API crua do motor e entrega ao
navegador um contrato pequeno, estável e já normalizado. O navegador nunca vê a
senha do motor (a autenticação Basic fica no servidor) e nunca baixa o catálogo
bruto (382 kB com ``settings``/``headers`` de cada modelo).

Nomes de rota usados pelo cliente (``/api/ufvai/*``) — todos devolvem JSON:

=========================================  ==================================
Rota                                       Função
=========================================  ==================================
``GET  /api/ufvai/bootstrap``              estado inicial (agentes, modelos,
                                           sessões, sessão ativa, motor)
``GET  /api/ufvai/models``                 catálogo compacto de modelos
``GET  /api/ufvai/sessions``               lista de sessões
``POST /api/ufvai/sessions``               cria sessão
``GET  /api/ufvai/sessions/{id}/messages`` mensagens normalizadas
``POST /api/ufvai/sessions/{id}/message``  envia prompt
``POST /api/ufvai/sessions/{id}/interrupt`` interrompe a execução
``POST /api/ufvai/sessions/{id}/model``    troca o modelo da sessão
``POST /api/ufvai/sessions/{id}/agent``    troca o agente da sessão
``GET  /api/ufvai/events``                SSE normalizado do motor
=========================================  ==================================
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote

__all__ = [
    "engine",
    "engine_json",
    "engine_request",
    "engine_events",
    "catalog",
    "sessions",
    "active_sessions",
    "session",
    "create_session",
    "messages",
    "send_prompt",
    "interrupt",
    "set_model",
    "set_agent",
    "agents",
    "commands",
    "normalize_event",
    "provider_available",
]

ENGINE_TIMEOUT = 25.0
EVENT_TIMEOUT = 600.0
CATALOG_TTL = 20.0

# Provedores que funcionam sem chave do usuário (conta pública do OpenCode).
_BUILTIN_PROVIDERS = ("opencode", "opencode-go")

# Variáveis de ambiente que habilitam um provedor (presença, nunca o valor).
_PROVIDER_ENV: dict[str, tuple[str, ...]] = {
    "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"),
    "openrouter": ("OPENROUTER_API_KEY",),
    "nvidia": ("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "mistral": ("MISTRAL_API_KEY",),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "xai": ("XAI_API_KEY",),
    "github-copilot": ("GITHUB_COPILOT_TOKEN",),
    "azure": ("AZURE_API_KEY",),
    "cohere": ("COHERE_API_KEY",),
    "opencode": (),
    "opencode-go": (),
}

_CACHE_LOCK = threading.Lock()
_CATALOG_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}


# ── descoberta do motor ──────────────────────────────────────────────────────

def _service_file() -> Path:
    """``service.json`` do OpenCode (XDG → HOME → /root)."""
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        candidate = Path(xdg) / "opencode" / "service.json"
        if candidate.exists():
            return candidate
    home = Path(os.path.expanduser("~")) / ".local" / "state" / "opencode" / "service.json"
    if home.exists():
        return home
    return Path("/root/.local/state/opencode/service.json")


_SERVICE: dict[str, Any] = {"key": None, "value": ("127.0.0.1", 0, "")}


def engine() -> tuple[str, int, str]:
    """``(host, porta, senha)`` do motor em execução.

    O ``service.json`` é relido a cada requisição (cache por ``mtime``): o motor
    reinicia durante o boot e troca de porta/senha.
    """
    path = _service_file()
    try:
        st = path.stat()
        key = (str(path), st.st_mtime_ns, st.st_size)
    except OSError:
        return "127.0.0.1", 0, ""
    with _CACHE_LOCK:
        if _SERVICE.get("key") == key and _SERVICE.get("value"):
            return _SERVICE["value"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "127.0.0.1", 0, ""
    url = str(data.get("url") or "")
    port = 0
    if ":" in url:
        try:
            port = int(url.rsplit(":", 1)[1].strip("/"))
        except ValueError:
            port = 0
    value = ("127.0.0.1", port, str(data.get("password") or ""))
    with _CACHE_LOCK:
        _SERVICE["key"] = key
        _SERVICE["value"] = value
    return value


def _auth(password: str) -> str:
    raw = f"opencode:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def engine_request(
    method: str,
    path: str,
    body: Any = None,
    timeout: float = ENGINE_TIMEOUT,
) -> tuple[int, Any]:
    """Chama o motor. Devolve ``(status, json|texto)``; nunca levanta."""
    host, port, password = engine()
    if not port:
        return 0, {"error": "motor indisponível"}
    url = f"http://{host}:{port}{path}"
    payload = None
    headers = {"Authorization": _auth(password), "Accept": "application/json"}
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=payload, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:  # o motor respondeu com erro
        raw = exc.read() if hasattr(exc, "read") else b""
        status = exc.code
    except (urllib.error.URLError, OSError, ValueError):
        return 0, {"error": "motor indisponível"}
    if not raw:
        return status, {}
    try:
        return status, json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError:
        return status, raw.decode("utf-8", errors="replace")


def engine_json(path: str, timeout: float = ENGINE_TIMEOUT) -> Any:
    """``GET`` no motor devolvendo o JSON (ou ``None`` em falha)."""
    status, data = engine_request("GET", path, timeout=timeout)
    if status != 200:
        return None
    return data


def engine_events(path: str = "/api/event") -> Iterator[dict]:
    """SSE do motor: dicionários ``{id, type, data, ...}``.

    O motor envia comentários (``: heartbeat``) que são ignorados; o stream
    termina quando a conexão cai — o cliente reabre.
    """
    host, port, password = engine()
    if not port:
        return
    request = urllib.request.Request(
        f"http://{host}:{port}{path}",
        headers={"Authorization": _auth(password), "Accept": "text/event-stream"},
    )
    try:
        response = urllib.request.urlopen(request, timeout=EVENT_TIMEOUT)
    except (urllib.error.URLError, OSError, ValueError):
        return
    try:
        for raw in response:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            try:
                event = json.loads(payload)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield event
    except (urllib.error.URLError, OSError, ValueError):
        return
    finally:
        try:
            response.close()
        except OSError:
            pass


# ── catálogo de modelos ──────────────────────────────────────────────────────

def provider_available(provider_id: str, used: set | None = None) -> bool:
    """Indica se o provedor tem credencial detectável neste ambiente.

    Três sinais, em ordem: provedor público do OpenCode (funciona sem chave),
    variável de ambiente presente, ou uso recente em uma sessão (prova de que
    a credencial funciona — o motor guarda a chave no banco interno e não
    expõe esse estado pela API).

    A ausência de sinal **não** prova que o provedor está inutilizável; por
    isso o cliente mostra a ressalva "chave não detectada", e não "bloqueado".
    """
    pid = str(provider_id or "").lower()
    if pid in _BUILTIN_PROVIDERS:
        return True
    if used and pid in used:
        return True
    names = _PROVIDER_ENV.get(pid)
    if names is None:
        # provedor desconhecido: sem sinal contra, o motor decide
        return True
    return any(os.environ.get(name) for name in names)


def _providers_in_use() -> set:
    """Provedores usados por sessões recentes (prova de credencial válida)."""
    used: set = set()
    try:
        for row in sessions()[:20]:
            provider = str((row.get("model") or {}).get("providerID") or "")
            if provider:
                used.add(provider.lower())
    except Exception:  # noqa: BLE001 — a lista é um Signals, nunca crítico
        return used
    return used


def _model_cost(model: dict) -> dict:
    """Custo do modelo normalizado (``{input, output, free}``)."""
    costs = model.get("cost") or []
    if not isinstance(costs, list) or not costs:
        return {"input": 0, "output": 0, "free": True}
    first = costs[0] if isinstance(costs[0], dict) else {}
    inp = float(first.get("input") or 0)
    out = float(first.get("output") or 0)
    return {"input": inp, "output": out, "free": inp <= 0 and out <= 0}


def catalog(force: bool = False) -> dict:
    """Catálogo compacto: provedores + modelos utilizáveis.

    O motor devolve ~380 kB (com ``settings``/``headers``/``package`` por
    modelo). Aqui vira um dicionário de poucos kB, com o campo ``available``
    indicando se o provedor tem credencial — é isso que faltava na versão
    anterior (a SPA mostrava ``modelo (unavailable)`` sem explicar o motivo).
    """
    now = time.time()
    with _CACHE_LOCK:
        if not force and _CATALOG_CACHE.get("data") is not None:
            if now - float(_CATALOG_CACHE.get("ts") or 0) < CATALOG_TTL:
                return dict(_CATALOG_CACHE["data"])

    providers_raw = engine_json("/api/provider", timeout=15) or {}
    models_raw = engine_json("/api/model", timeout=25) or {}

    prov_rows = providers_raw.get("data") if isinstance(providers_raw, dict) else providers_raw
    prov_rows = prov_rows if isinstance(prov_rows, list) else []
    names: dict[str, str] = {}
    for row in prov_rows:
        if isinstance(row, dict) and row.get("id"):
            names[str(row["id"])] = str(row.get("name") or row["id"])

    model_rows = models_raw.get("data") if isinstance(models_raw, dict) else models_raw
    model_rows = model_rows if isinstance(model_rows, list) else []

    used = _providers_in_use()
    models: list[dict] = []
    counts: dict[str, int] = {}
    for row in model_rows:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("providerID") or "")
        if not pid or not row.get("modelID"):
            continue
        limit = row.get("limit") or {}
        cost = _model_cost(row)
        models.append(
            {
                "providerID": pid,
                "id": str(row.get("modelID")),
                "name": str(row.get("name") or row.get("modelID")),
                "context": int(limit.get("context") or 0),
                "output": int(limit.get("output") or 0),
                "cost": cost,
                "available": provider_available(pid, used),
                "variants": [v for v in (row.get("variants") or []) if isinstance(v, str)],
            }
        )
        counts[pid] = counts.get(pid, 0) + 1

    provider_list = []
    for pid in sorted(counts, key=lambda p: (-counts[p], p)):
        provider_list.append(
            {
                "id": pid,
                "name": names.get(pid, pid),
                "models": counts[pid],
                "available": provider_available(pid, used),
                "inUse": pid in used,
            }
        )

    data = {
        "providers": provider_list,
        "models": models,
        "total": len(models),
        "available": sum(1 for m in models if m["available"]),
        "ts": int(now * 1000),
    }
    with _CACHE_LOCK:
        _CATALOG_CACHE["ts"] = now
        _CATALOG_CACHE["data"] = data
    return dict(data)


# ── sessões ──────────────────────────────────────────────────────────────────

def _session_row(row: dict) -> dict:
    time_info = row.get("time") or {}
    model = row.get("model") or {}
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or ""),
        "directory": str((row.get("location") or {}).get("directory") or ""),
        "agent": str(row.get("agent") or ""),
        "model": {
            "id": str(model.get("id") or ""),
            "providerID": str(model.get("providerID") or ""),
            "variant": str(model.get("variant") or ""),
        },
        "created": int(time_info.get("created") or 0),
        "updated": int(time_info.get("updated") or 0),
        "busy": int(time_info.get("busy") or 0),
        "tokens": row.get("tokens") or {},
        "cost": row.get("cost") or 0,
    }


def sessions() -> list[dict]:
    """Sessões do projeto atual, da mais recente para a mais antiga."""
    data = engine_json("/api/session", timeout=15)
    rows = data.get("data") if isinstance(data, dict) else data
    rows = rows if isinstance(rows, list) else []
    out = [_session_row(r) for r in rows if isinstance(r, dict) and r.get("id")]
    out.sort(key=lambda s: s.get("updated") or s.get("created") or 0, reverse=True)
    return out


def active_sessions() -> dict:
    """Sessões que o motor considera em execução."""
    data = engine_json("/api/session/active", timeout=8)
    rows = data.get("data") if isinstance(data, dict) else data
    return rows if isinstance(rows, dict) else {}


def session(sid: str) -> dict | None:
    data = engine_json(f"/api/session/{sid}", timeout=10)
    row = data.get("data") if isinstance(data, dict) else data
    if isinstance(row, dict) and row.get("id"):
        return _session_row(row)
    return None


def create_session(
    title: str | None = None,
    agent: str | None = None,
    model: dict | None = None,
    directory: str | None = None,
) -> dict | None:
    """Cria uma sessão no diretório de trabalho do projeto."""
    body: dict[str, Any] = {}
    if title:
        body["title"] = title
    if agent:
        body["agent"] = agent
    if model and model.get("id") and model.get("providerID"):
        body["model"] = {
            "id": str(model["id"]),
            "providerID": str(model["providerID"]),
        }
        if model.get("variant"):
            body["model"]["variant"] = str(model["variant"])
    if directory:
        body["location"] = {"directory": directory}
    status, data = engine_request("POST", "/api/session", body, timeout=20)
    if status not in (200, 201):
        return None
    row = data.get("data") if isinstance(data, dict) else data
    if isinstance(row, dict) and row.get("id"):
        return _session_row(row)
    return None


# ── mensagens ────────────────────────────────────────────────────────────────

def _tool_rows(content: list) -> list[dict]:
    tools = []
    for part in content or []:
        if not isinstance(part, dict) or part.get("type") != "tool":
            continue
        state = part.get("state") or {}
        output = state.get("output")
        if output is None:
            chunks = []
            for item in state.get("content") or []:
                if isinstance(item, dict) and item.get("text"):
                    chunks.append(str(item["text"]))
            output = "".join(chunks) or None
        tools.append(
            {
                "id": str(part.get("id") or ""),
                "name": str(part.get("name") or ""),
                "status": str(state.get("status") or "unknown"),
                "title": str(state.get("title") or ""),
                "input": state.get("input"),
                "output": output,
                "metadata": state.get("metadata") or {},
            }
        )
    return tools


def normalize_message(row: dict) -> dict:
    """Mensagem do motor → contrato do cliente."""
    kind = str(row.get("type") or "")
    time_info = row.get("time") or {}
    content = row.get("content") or []
    texts: list[str] = []
    reasoning: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and part.get("text"):
            texts.append(str(part["text"]))
        elif part.get("type") == "reasoning" and part.get("text"):
            reasoning.append(str(part["text"]))
    model = row.get("model") or {}
    error = row.get("error")
    return {
        "id": str(row.get("id") or ""),
        "role": "assistant" if kind == "assistant" else ("user" if kind == "user" else "system"),
        "kind": kind,
        "text": str(row.get("text") or "") if kind == "user" else "\n\n".join(texts),
        "reasoning": "\n\n".join(reasoning),
        "tools": _tool_rows(content),
        "agent": str(row.get("agent") or ""),
        "model": {
            "id": str(model.get("id") or ""),
            "providerID": str(model.get("providerID") or ""),
            "variant": str(model.get("variant") or ""),
        },
        "created": int(time_info.get("created") or 0),
        "completed": int(time_info.get("completed") or 0),
        "tokens": row.get("tokens") or {},
        "cost": row.get("cost") or 0,
        "outcome": row.get("outcome"),
        "error": str(error.get("message") if isinstance(error, dict) else error or ""),
    }


def messages(sid: str, limit: int = 200) -> list[dict]:
    """Mensagens da sessão em ordem cronológica (antiga → nova).

    O motor entrega a página mais recente primeiro; com ``order=asc`` as
    páginas vêm em ordem cronológica. Percorremos o cursor até ter o limite
    pedido (o histórico antigo continua acessível pela rolagem do terminal).
    """
    rows: list[dict] = []
    cursor = ""
    for _ in range(12):
        path = f"/api/session/{sid}/message?order=asc"
        if cursor:
            path += "&cursor=" + quote(cursor, safe="")
        data = engine_json(path, timeout=25)
        if not isinstance(data, dict):
            break
        page = data.get("data")
        if not isinstance(page, list) or not page:
            break
        rows.extend([r for r in page if isinstance(r, dict)])
        if limit and len(rows) >= limit:
            break
        nxt = (data.get("cursor") or {}).get("next")
        if not nxt or nxt == cursor:
            break
        cursor = str(nxt)

    rows.sort(key=lambda r: int((r.get("time") or {}).get("created") or 0))
    out = [normalize_message(r) for r in rows]
    out = [m for m in out if m["role"] != "system" or m.get("outcome")]
    if limit and len(out) > limit:
        out = out[-limit:]
    return out


def _ok(status: int) -> bool:
    """2xx = sucesso (o motor usa 204 em operações sem corpo)."""
    return 200 <= int(status) < 300


def send_prompt(sid: str, text: str) -> dict:
    """Envia um prompt para a sessão."""
    status, data = engine_request(
        "POST", f"/api/session/{sid}/prompt", {"text": text}, timeout=20
    )
    if not _ok(status):
        return {"ok": False, "error": _error_text(data) or f"HTTP {status}"}
    row = data.get("data") if isinstance(data, dict) else data
    return {"ok": True, "id": str((row or {}).get("id") or "")}


def interrupt(sid: str) -> dict:
    """Interrompe a execução em andamento."""
    status, data = engine_request("POST", f"/api/session/{sid}/interrupt", {}, timeout=15)
    if not _ok(status):
        return {"ok": False, "error": _error_text(data) or f"HTTP {status}"}
    return {"ok": True, "interrupted": bool((data or {}).get("interrupted", True))}


def set_model(sid: str, model: dict) -> dict:
    """Troca o modelo da sessão."""
    if not model.get("id") or not model.get("providerID"):
        return {"ok": False, "error": "modelo incompleto"}
    payload = {"id": str(model["id"]), "providerID": str(model["providerID"])}
    if model.get("variant"):
        payload["variant"] = str(model["variant"])
    status, data = engine_request(
        "POST", f"/api/session/{sid}/model", {"model": payload}, timeout=15
    )
    if not _ok(status):
        return {"ok": False, "error": _error_text(data) or f"HTTP {status}"}
    return {"ok": True, "model": payload}


def set_agent(sid: str, agent: str) -> dict:
    """Troca o agente da sessão."""
    status, data = engine_request(
        "POST", f"/api/session/{sid}/agent", {"agent": agent}, timeout=15
    )
    if not _ok(status):
        return {"ok": False, "error": _error_text(data) or f"HTTP {status}"}
    return {"ok": True, "agent": agent}


def _error_text(data: Any) -> str:
    if isinstance(data, dict):
        for key in ("error", "message", "data"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, dict):
                nested = value.get("message") or value.get("error")
                if isinstance(nested, str) and nested:
                    return nested
    return ""


# ── agentes e comandos ───────────────────────────────────────────────────────

def agents() -> list[dict]:
    """Agentes disponíveis (UFVAI e demais)."""
    data = engine_json("/api/agent", timeout=15)
    rows = data.get("data") if isinstance(data, dict) else data
    rows = rows if isinstance(rows, list) else []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model = row.get("model") or {}
        out.append(
            {
                "id": str(row.get("id") or row.get("name") or ""),
                "name": str(row.get("name") or row.get("id") or ""),
                "description": str(row.get("description") or "")[:200],
                "model": {
                    "id": str(model.get("id") or ""),
                    "providerID": str(model.get("providerID") or ""),
                },
            }
        )
    return out


def commands() -> list[dict]:
    """Comandos do agente (atalhos como ``/pesquisar``)."""
    data = engine_json("/api/command", timeout=12)
    rows = data.get("data") if isinstance(data, dict) else data
    rows = rows if isinstance(rows, list) else []
    return [
        {"name": str(r.get("name") or ""), "description": str(r.get("description") or "")}
        for r in rows
        if isinstance(r, dict) and r.get("name")
    ]


# ── eventos (motor → cliente) ────────────────────────────────────────────────

def normalize_event(event: dict) -> dict | None:
    """Traduz um evento do motor para o contrato do cliente.

    Devolve ``None`` para eventos irrelevantes (outras sessões, telemetria).
    """
    kind = str(event.get("type") or "")
    data = event.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    sid = str(data.get("sessionID") or "")
    message_id = str(data.get("assistantMessageID") or "")

    if kind == "session.execution.started":
        return {"type": "run.started", "sid": sid}
    if kind == "session.execution.succeeded":
        return {"type": "run.finished", "sid": sid}
    if kind == "session.execution.failed":
        return {"type": "run.failed", "sid": sid, "error": str(data.get("error") or "")}
    if kind == "session.step.started":
        model = data.get("model") or {}
        return {
            "type": "step.started",
            "sid": sid,
            "messageID": message_id,
            "agent": str(data.get("agent") or ""),
            "model": {
                "id": str(model.get("id") or ""),
                "providerID": str(model.get("providerID") or ""),
            },
        }
    if kind == "session.step.ended":
        return {
            "type": "step.ended",
            "sid": sid,
            "messageID": message_id,
            "finish": str(data.get("finish") or ""),
            "tokens": data.get("tokens") or {},
            "cost": data.get("cost") or 0,
        }
    if kind == "session.text.started":
        return {"type": "text.started", "sid": sid, "messageID": message_id}
    if kind == "session.text.delta":
        return {"type": "text.delta", "sid": sid, "messageID": message_id, "delta": str(data.get("delta") or "")}
    if kind == "session.text.ended":
        return {"type": "text.ended", "sid": sid, "messageID": message_id, "text": str(data.get("text") or "")}
    if kind == "session.reasoning.started":
        return {"type": "reasoning.started", "sid": sid, "messageID": message_id}
    if kind == "session.reasoning.delta":
        return {
            "type": "reasoning.delta",
            "sid": sid,
            "messageID": message_id,
            "delta": str(data.get("delta") or ""),
        }
    if kind == "session.reasoning.ended":
        return {"type": "reasoning.ended", "sid": sid, "messageID": message_id, "text": str(data.get("text") or "")}
    if kind == "session.tool.called":
        return {
            "type": "tool.started",
            "sid": sid,
            "messageID": message_id,
            "callID": str(data.get("id") or ""),
            "name": str(data.get("name") or ""),
            "input": data.get("input"),
        }
    if kind == "session.tool.progress":
        return {
            "type": "tool.progress",
            "sid": sid,
            "messageID": message_id,
            "callID": str(data.get("id") or ""),
            "metadata": data.get("metadata") or {},
        }
    if kind in ("session.tool.success", "session.tool.error"):
        chunks = []
        for item in data.get("content") or []:
            if isinstance(item, dict) and item.get("text"):
                chunks.append(str(item["text"]))
        return {
            "type": "tool.finished",
            "sid": sid,
            "messageID": message_id,
            "callID": str(data.get("id") or ""),
            "name": str(data.get("name") or ""),
            "status": "error" if kind.endswith("error") else "completed",
            "output": "".join(chunks) or None,
            "metadata": data.get("metadata") or {},
        }
    if kind == "session.inbox.enqueued":
        item = data.get("item") or {}
        payload = item.get("payload") or {}
        return {
            "type": "inbox.enqueued",
            "sid": sid,
            "text": str(payload.get("text") or ""),
        }
    if kind == "session.inbox.delivered":
        return {"type": "inbox.delivered", "sid": sid}
    if kind == "session.usage.updated":
        return {
            "type": "usage",
            "sid": sid,
            "tokens": data.get("tokens") or {},
            "cost": data.get("cost") or 0,
        }
    if kind == "session.updated":
        return {"type": "session.updated", "sid": sid, "title": str(data.get("title") or "")}
    if kind == "session.error" or kind == "message.error":
        error = data.get("error")
        text = error.get("message") if isinstance(error, dict) else error
        return {"type": "error", "sid": sid, "error": str(text or "erro desconhecido")}
    return None
