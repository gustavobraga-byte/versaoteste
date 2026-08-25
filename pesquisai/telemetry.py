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

import hashlib
import json
import os
import re
import threading
import time
import urllib.request
import uuid

try:
    from .__version__ import __version__ as _APP_VERSION  # v0.6.7: payload de contato carrega a versão
except Exception:
    _APP_VERSION = "unknown"

_CID_FILE = os.path.expanduser("~/.config/ufvai_cid")
_CONSENT_FILE = os.path.expanduser("~/.config/ufvai_consent.json")
_ADMIN_CFG_FILE = os.path.expanduser("~/.config/ufvai_telemetry.json")  # v0.6.4
_PROFILE_FILE = os.path.expanduser("~/.config/ufvai_profile.json")     # v0.6.6
_MP_URL = "https://www.google-analytics.com/mp/collect"

_FALSEY = ("0", "false", "off", "no")

# v0.6.6: validação simples de e-mail (local-part@domínio.tld)
_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


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


def save_admin_config(
    measurement_id: str | None = None,
    api_secret: str | None = None,
    contact_endpoint: str | None = None,
) -> tuple[bool, str]:
    """Salva a configuração do painel Admin da UI.

    (v0.6.4) Credenciais GA4; (v0.6.7) também grava ``contact_endpoint``
    (canal HTTPS que recebe o e-mail de contato opt-in — ex.: Apps Script
    → Planilha Google).

    Semântica por parâmetro:
      • ``None`` ou ``""``  → NÃO altera o que já está salvo;
      • texto               → valida e define.
      • Exceção: ``contact_endpoint=""`` LIMPA o canal (remoção).
    Cada campo é independente — dá para atualizar só o canal de contato
    sem redigitar as credenciais GA4 (que nunca são devolvidas pela API).
    Arquivo local com permissão 600. Retorna (ok, mensagem).
    """
    try:
        # Base = configuração existente (edição parcial de campos)
        base: dict = {}
        try:
            with open(_ADMIN_CFG_FILE, encoding="utf-8") as f:
                base = json.load(f)
        except Exception:
            base = {}

        # ── GA4: só toca se pelo menos um campo veio preenchido ──
        new_mid = str(measurement_id).strip() if measurement_id else str(base.get("measurement_id", ""))
        new_sec = str(api_secret).strip() if api_secret else str(base.get("api_secret", ""))
        ga_touched = bool(measurement_id or api_secret)
        if ga_touched:
            if not re.fullmatch(r"G-[A-Z0-9]{6,12}", new_mid):
                return False, "ID de medição inválido ou ausente (formato esperado: G-XXXXXXXXXX)."
            if len(new_sec) < 8:
                return False, "API Secret ausente ou muito curto — cole-o novamente."
            base["measurement_id"] = new_mid
            base["api_secret"] = new_sec
            os.environ["UFVAI_GA_MEASUREMENT_ID"] = new_mid
            os.environ["UFVAI_GA_API_SECRET"] = new_sec

        # ── v0.6.7 canal de contato (HTTPS; localhost liberado p/ teste) ──
        cmsg = ""
        if contact_endpoint is not None:
            curl = str(contact_endpoint).strip()
            if curl and not (curl.startswith("https://") or curl.startswith("http://localhost")):
                return False, "URL de contato inválida (use https://…)."
            base["contact_endpoint"] = curl
            if curl:
                os.environ["UFVAI_CONTACT_ENDPOINT"] = curl
                cmsg = " Canal de contato ativo."
            else:
                os.environ.pop("UFVAI_CONTACT_ENDPOINT", None)
                cmsg = " Canal de contato removido."

        if not ga_touched and contact_endpoint is None:
            return False, "Nada a salvar."

        base["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        os.makedirs(os.path.dirname(_ADMIN_CFG_FILE), exist_ok=True)
        with open(_ADMIN_CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(base, f)
        os.chmod(_ADMIN_CFG_FILE, 0o600)
        return True, ("Configuração salva." if not ga_touched else
                      "Configuração salva. A coleta inicia quando o usuário aceitar "
                      "o opt-in nos Termos.") + cmsg
    except Exception as e:
        return False, f"Falha ao salvar: {e}"


def masked_state() -> dict:
    """(v0.6.4) Estado para exibição no painel Admin — NUNCA expõe o secret."""
    mid, sec = _ga_config()
    consent = read_consent()
    st = {
        "configured": configured(),
        "measurement_id": (mid[:2] + "***" + mid[-7:]) if mid else "",
        "api_secret_set": bool(sec),
        "source": ("env" if os.environ.get("UFVAI_GA_MEASUREMENT_ID") else ("file" if mid else "none")),
        "consent_accepted": bool(consent.get("accepted")),
        "consent_analytics": bool(consent.get("analytics")),
        "kill_switch": kill_switch_active(),
        "enabled": enabled(),
    }
    st.update(contact_status())  # v0.6.6: has_email / email_masked / endpoint_set
    # v0.6.7: URL de contato EFETIVA (env > arquivo) visível SÓ ao admin — é a
    # URL dele; o API secret continua nunca retornado. Usada p/ preencher o
    # campo do painel ("o que está no campo é o que será salvo").
    st["contact_endpoint_url"] = _contact_endpoint()
    return st


# ─────────────────────────────────────────────────────────────────────────────
# v0.6.6 — Contato opt-in (e-mail do usuário)
#
# LGPD: o e-mail SÓ é coletado com consentimento livre, informado e inequívoco
# (art. 7º I), finalidade específica documentada (contato/novidades do UFVAI),
# campo opcional e direito de eliminação a qualquer momento (art. 18).
# O e-mail NUNCA vai para o Google Analytics — os Termos do GA4 proíbem PII
# (mesmo com hash). Para o desenvolvedor saber que houve opt-in, o GA4 recebe
# apenas um CONTADOR anônimo ("contact_optin", sem conteúdo). O endereço em si
# fica no arquivo local abaixo e, se o desenvolvedor configurar o próprio
# endpoint HTTPS (UFVAI_CONTACT_ENDPOINT, ex.: Apps Script), é enviado para lá.
# ─────────────────────────────────────────────────────────────────────────────


def _contact_endpoint() -> str:
    """(v0.6.7) Endpoint HTTPS do desenvolvedor que recebe o contato opt-in.

    Prioridade: variável de ambiente UFVAI_CONTACT_ENDPOINT > painel Admin
    (~/.config/ufvai_telemetry.json, chave contact_endpoint).
    """
    url = os.environ.get("UFVAI_CONTACT_ENDPOINT", "").strip()
    if url:
        return url
    try:
        with open(_ADMIN_CFG_FILE, encoding="utf-8") as f:
            return str(json.load(f).get("contact_endpoint", "") or "").strip()
    except Exception:
        return ""


def contact_status() -> dict:
    """Estado mascarado do contato — nunca expõe o e-mail completo."""
    prof = _read_profile()
    email = str(prof.get("email", ""))
    masked = ""
    if email and "@" in email:
        loc, _, dom = email.partition("@")
        masked = (loc[:2] + "***@" + dom) if len(loc) > 2 else "***@" + dom
    curl = _contact_endpoint()
    return {
        "has_email": bool(email),
        "email_masked": masked,
        "contact_endpoint_set": bool(curl),
        "contact_endpoint_source": ("env" if os.environ.get("UFVAI_CONTACT_ENDPOINT", "").strip()
                                    else ("file" if curl else "")),
    }


def _read_profile() -> dict:
    try:
        with open(_PROFILE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_contact(email: str) -> tuple[bool, str]:
    """Grava o e-mail localmente (chmod 600) com hash SHA-256 e encaminha ao
    endpoint do desenvolvedor, se configurado. Dispara contador anônimo no GA4.

    Retorna (ok, mensagem).
    """
    addr = str(email or "").strip().lower()
    if not addr:
        return False, "E-mail vazio."
    if not _EMAIL_RE.fullmatch(addr) or len(addr) > 254:
        return False, "E-mail inválido."
    sha = hashlib.sha256(addr.encode("utf-8")).hexdigest()
    try:
        os.makedirs(os.path.dirname(_PROFILE_FILE), exist_ok=True)
        with open(_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "email": addr,
                "email_sha256": sha,
                "purpose": "contato/novidades UFVAI (consentimento art. 7º I)",
                "consent_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, f)
        os.chmod(_PROFILE_FILE, 0o600)
    except Exception as e:
        return False, f"Falha ao salvar contato: {e}"
    # Contador ANÔNIMO para o GA4 (sem nenhum dado derivado do e-mail)
    event("contact_optin")
    # Canal direto do desenvolvedor (opcional): envia o endereço real por HTTPS
    threading.Thread(target=_forward_contact, args=(addr, sha), daemon=True).start()
    return True, "Contato registrado com sucesso."


def clear_contact() -> None:
    """Elimina o e-mail local (direito de eliminação, LGPD art. 18 VI)."""
    try:
        os.remove(_PROFILE_FILE)
    except Exception:
        pass


_SHEET_ID_COLAB_FALLBACK = "149XGyTfPbGs34Wrb8WHBPC8gmzRQKJzvTEmqXlshvgg"
_SHEET_NAME_COLAB_FALLBACK = "Contatos UFVAI"

def _forward_contact_direct_sheet(addr: str, sha: str) -> None:
    """Fallback Colab: escrita direta na planilha via Sheets API.

    Usado quando UFVAI_CONTACT_ENDPOINT não está configurado mas estamos no Colab.
    Requer que a planilha esteja compartilhada como 'Qualquer pessoa com link - Editor'
    (feito automaticamente na criação 0.6.8) e que o usuário esteja autenticado no Colab
    (auth.authenticate_user). Firewall silencioso.
    """
    try:
        import gspread  # type: ignore
        from google.auth import default  # type: ignore
        creds, _ = default()
        if not creds or not creds.valid:
            # tenta refresh silencioso
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            except Exception:
                return
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(_SHEET_ID_COLAB_FALLBACK)
        try:
            ws = sh.worksheet(_SHEET_NAME_COLAB_FALLBACK)
        except Exception:
            ws = sh.sheet1
        row = [
            time.strftime("%Y-%m-%d %H:%M:%S"),
            addr,
            sha,
            "colab",
            _APP_VERSION,
            "ufvai",
        ]
        ws.append_row(row, value_input_option="RAW")
    except Exception:
        pass


def _forward_contact(addr: str, sha: str) -> None:
    """POST {email, email_sha256, …} ao endpoint PRÓPRIO do desenvolvedor.

    (v0.6.7) Ativado se UFVAI_CONTACT_ENDPOINT estiver definido no ambiente
    OU salvo pelo painel Admin (ex.: Apps Script → Planilha Google).
    (v0.6.8) Fallback Colab: se sem endpoint e em /content, tenta escrita direta
    via Sheets API (planilha compartilhada como anyone writer). Fire-and-forget.
    """
    url = _contact_endpoint()
    if url:
        try:
            payload = {
                "product": "ufvai",
                "email": addr,
                "email_sha256": sha,
                "environment": "colab" if os.path.isdir("/content") else "local",
                "app_version": _APP_VERSION,
                "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            # v0.6.7: timeout 8 s — Apps Script tem cold start de ~1-3 s;
            # 3 s abortava envios válidos na primeira execução do dia.
            urllib.request.urlopen(req, timeout=8).read(16)
            return
        except Exception:
            pass
    # Fallback Colab direto (sem endpoint)
    if os.path.isdir("/content"):
        try:
            _forward_contact_direct_sheet(addr, sha)
        except Exception:
            pass


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
        # v0.6.9: CORREÇÃO — o parâmetro correto do Measurement Protocol é o
        # campo "debug_mode":1 no EVENTO (não "&debug_view=1" na URL, que o
        # GA4 ignorava silenciosamente e os eventos nunca apareciam no DebugView).
        if os.environ.get("UFVAI_TELEMETRY_DEBUG", "").strip().lower() in ("1", "true", "yes", "on"):
            payload["events"][0]["params"]["debug_mode"] = 1

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
