"""
telemetry.py — Telemetria anônima opt-in do UFVAI/PesquisAI (v0.6.0).

Princípios:
  1. OPT-IN explícito: nada é enviado sem consentimento gravado em
     ~/.config/ufvai_consent.json (tela de Termos de Uso → checkbox próprio).
  2. ZERO conteúdo: apenas contadores de eventos e metadados não-pessoais
     (versão, idioma, provedor). Nunca caminhos, notas, chaves ou prompts.
  3. Fail-safe total: qualquer erro é silencioso; envio roda em thread
     daemon com timeout curto — nunca bloqueia nem quebra o app.
  4. Kill-switch: UFVAI_TELEMETRY=0 desliga globalmente.

Configuração do produtor (dono do projeto):
  UFVAI_GA_MEASUREMENT_ID  — ID GA4 (G-XXXXXXX)
  UFVAI_GA_API_SECRET      — segredo do Measurement Protocol

Sem essas variáveis a telemetria fica inativa mesmo com consentimento.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
import uuid

_CID_FILE = os.path.expanduser("~/.config/ufvai_cid")
_CONSENT_FILE = os.path.expanduser("~/.config/ufvai_consent.json")
_ADMIN_CFG_FILE = os.path.expanduser("~/.config/ufvai_telemetry.json")  # v0.6.4
_MP_URL = "https://www.google-analytics.com/mp/collect"

_FALSEY = ("0", "false", "off", "no")


def _admin_local_config() -> tuple[str, str]:
    """(v0.6.4) Credenciais salvas via painel Admin da UI (~/.config/ufvai_telemetry.json)."""
    try:
        with open(_ADMIN_CFG_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return str(d.get("measurement_id", "")).strip(), str(d.get("api_secret", "")).strip()
    except Exception:
        return "", ""


def _ga_config() -> tuple[str, str]:
    """Retorna (measurement_id, api_secret).

    Prioridade v0.6.4: variáveis de ambiente > arquivo local do painel Admin.
    """
    mid = os.environ.get("UFVAI_GA_MEASUREMENT_ID", "").strip()
    sec = os.environ.get("UFVAI_GA_API_SECRET", "").strip()
    if mid and sec:
        return mid, sec
    lmid, lsec = _admin_local_config()
    return (mid or lmid).strip(), (sec or lsec).strip()


def save_admin_config(measurement_id: str, api_secret: str) -> tuple[bool, str]:
    """(v0.6.4) Salva credenciais configuradas pelo painel Admin da UI.

    Validação básica de formato; arquivo local com permissão 600.
    Retorna (ok, mensagem).
    """
    mid = str(measurement_id or "").strip()
    sec = str(api_secret or "").strip()
    if not mid or not sec:
        return False, "Informe o ID de medição e o API Secret."
    if not re.fullmatch(r"G-[A-Z0-9]{6,12}", mid):
        return False, "ID de medição inválido (formato esperado: G-XXXXXXXXXX)."
    if len(sec) < 8:
        return False, "API Secret muito curto."
    try:
        os.makedirs(os.path.dirname(_ADMIN_CFG_FILE), exist_ok=True)
        with open(_ADMIN_CFG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "measurement_id": mid,
                "api_secret": sec,
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, f)
        os.chmod(_ADMIN_CFG_FILE, 0o600)
        # Aplica imediatamente no processo em execução
        os.environ["UFVAI_GA_MEASUREMENT_ID"] = mid
        os.environ["UFVAI_GA_API_SECRET"] = sec
        return True, "Configuração salva. A coleta inicia quando o usuário aceitar o opt-in nos Termos."
    except Exception as e:
        return False, f"Falha ao salvar: {e}"


def masked_state() -> dict:
    """(v0.6.4) Estado para exibição no painel Admin — NUNCA expõe o secret."""
    mid, sec = _ga_config()
    consent = read_consent()
    return {
        "configured": configured(),
        "measurement_id": (mid[:2] + "***" + mid[-7:]) if mid else "",
        "api_secret_set": bool(sec),
        "source": ("env" if os.environ.get("UFVAI_GA_MEASUREMENT_ID") else ("file" if mid else "none")),
        "consent_accepted": bool(consent.get("accepted")),
        "consent_analytics": bool(consent.get("analytics")),
        "kill_switch": kill_switch_active(),
        "enabled": enabled(),
    }


def kill_switch_active() -> bool:
    """True se UFVAI_TELEMETRY=0/false/off."""
    return os.environ.get("UFVAI_TELEMETRY", "1").strip().lower() in _FALSEY


def configured() -> bool:
    """True se as credenciais GA4 estão presentes no ambiente."""
    mid, sec = _ga_config()
    return bool(mid and sec)


def consented() -> bool:
    """True se o usuário aceitou estatísticas anônimas na tela de Termos."""
    try:
        with open(_CONSENT_FILE, encoding="utf-8") as f:
            return bool(json.load(f).get("analytics"))
    except Exception:
        return False


def enabled() -> bool:
    """Telemetria ativa = configurada E consentida E sem kill-switch."""
    if kill_switch_active():
        return False
    if not configured():
        return False
    return consented()


def read_consent() -> dict:
    """Lê o estado atual do consentimento (para exibição/debug)."""
    try:
        with open(_CONSENT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"accepted": False, "analytics": False}


def set_consent(analytics: bool) -> None:
    """Grava o consentimento de telemetria (chamado por /api/consent)."""
    try:
        state = read_consent() or {}
        state["analytics"] = bool(analytics)
        state["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        os.makedirs(os.path.dirname(_CONSENT_FILE), exist_ok=True)
        with open(_CONSENT_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


def _client_id() -> str:
    """UUID anônimo estável por máquina (não é identidade pessoal)."""
    try:
        if os.path.exists(_CID_FILE):
            cid = open(_CID_FILE, encoding="utf-8").read().strip()
            if cid:
                return cid
    except Exception:
        pass
    cid = str(uuid.uuid4())
    try:
        os.makedirs(os.path.dirname(_CID_FILE), exist_ok=True)
        with open(_CID_FILE, "w", encoding="utf-8") as f:
            f.write(cid)
    except Exception:
        pass
    return cid


def event(name: str, params: dict | None = None) -> None:
    """Dispara um evento anônimo via GA4 Measurement Protocol.

    Fire-and-forget: nunca levanta, nunca bloqueia. Silencioso se
    desabilitado (sem consent/config/kill-switch).
    """
    try:
        if not enabled():
            return
        mid, sec = _ga_config()
        payload = {
            "client_id": _client_id(),
            "non_personalized_ads": True,
            "events": [{"name": str(name)[:40], "params": {**(params or {})}}],
        }
        data = json.dumps(payload).encode("utf-8")
        url = f"{_MP_URL}?measurement_id={mid}&api_secret={sec}"
        # v0.6.2: UFVAI_TELEMETRY_DEBUG=1 → envia para o DebugView do GA4
        # (visível em tempo real em Admin → DebugView), sem gravar relatórios.
        if os.environ.get("UFVAI_TELEMETRY_DEBUG", "").strip().lower() in ("1", "true", "yes", "on"):
            url += "&debug_view=1"

        def _send() -> None:
            try:
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=3).read(16)
            except Exception:
                pass

        threading.Thread(target=_send, daemon=True).start()
    except Exception:
        pass
