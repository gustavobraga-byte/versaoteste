"""Servidor do Assistente de Voz LFM3-Omni para UFVAI.

Sobe uma interface web local (porta 8010) com suporte a:
- Gravação de áudio pelo navegador (MediaRecorder)
- Transcrição local via LFM3-Omni-2B (ASR)
- Síntese de voz neural local via LFM3-Omni-2B (TTS)
- Integração com o motor UFVAI para pesquisa científica
"""
from __future__ import annotations

import os
import sys
import time
import uuid
import threading
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from engine import VoiceEngine
from bridge import UFVAIBridge
from live import LiveSession, DEFAULT_MODEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("lfm3-voz")

BASE = Path(__file__).resolve().parent
TMP = BASE / "tmp"
TMP.mkdir(exist_ok=True)

app = FastAPI(title="UFVAI Voz — LFM3-Omni")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
engine = VoiceEngine.get()
bridge = UFVAIBridge()

# Histórico de conversa local (para o modelo de voz)
history: list[dict] = []


def load_model_bg():
    # O modelo local (9 GB RAM) só é carregado sob demanda, para não derrubar
    # o servidor quando o usuário só quer a conversa ao vivo via Gemini.
    if os.environ.get("UFVAI_VOZ_PRELOAD", "0") == "1":
        engine.load()


@app.on_event("startup")
def startup():
    threading.Thread(target=load_model_bg, daemon=True).start()


@app.get("/ufvai.css")
def ufvai_css():
    """Identidade visual UFVAI (navy + ouro) compartilhada pelas páginas."""
    return Response(
        (BASE / "static" / "ufvai.css").read_text(encoding="utf-8"),
        media_type="text/css",
    )


@app.get("/common.js")
def common_js():
    """Header, tema e ícones SVG compartilhados."""
    return Response(
        (BASE / "static" / "common.js").read_text(encoding="utf-8"),
        media_type="application/javascript",
    )


# Arquivo onde a chave Gemini informada pelo usuário é guardada (somente leitura
# pelo processo local; nunca enviada a terceiros além da própria Gemini API).
_GEMINI_KEY_FILE = BASE / ".gemini_key"


def _saved_gemini_key() -> str:
    try:
        return _GEMINI_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


@app.get("/api/gemini/key")
def gemini_key_status():
    """Informa se há chave Gemini (valor nunca é devolvido ao navegador)."""
    configured = bool(
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
        or _saved_gemini_key()
    )
    return {"configured": configured, "source": "ambiente" if (
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")) else ("arquivo" if _saved_gemini_key() else "nenhuma")}


@app.post("/api/gemini/key")
def gemini_key_save(payload: dict):
    """Salva a chave Gemini digitada pelo usuário (equivale ao onboarding)."""
    key = str(payload.get("key", "")).strip()
    if not key:
        return {"ok": False, "error": "Cole uma chave da Gemini API para continuar."}
    try:
        _GEMINI_KEY_FILE.write_text(key, encoding="utf-8")
        os.environ["GEMINI_API_KEY"] = key
        os.environ["GOOGLE_API_KEY"] = key
        return {"ok": True, "configured": True}
    except OSError as exc:
        return {"ok": False, "error": f"Não foi possível salvar a chave: {exc}"}


@app.get("/start", response_class=HTMLResponse)
def start_page():
    """Página inicial: usuário escolhe Google Live ou LFM local."""
    return (BASE / "static" / "start.html").read_text(encoding="utf-8")


@app.get("/local", response_class=HTMLResponse)
def local_page():
    """Página do LFM local — download do modelo é sob demanda."""
    return (BASE / "static" / "local.html").read_text(encoding="utf-8")


@app.get("/key", response_class=HTMLResponse)
def key_page():
    """Pedido da chave Gemini (mesmo padrão do onboarding do UFVAI)."""
    return (BASE / "static" / "key.html").read_text(encoding="utf-8")


@app.get("/api/local/status")
def local_status():
    """Estado do modelo local para a UI: baixado / carregando / pronto."""
    from engine import MODEL_DIR
    model_file = MODEL_DIR / "model.safetensors"
    downloaded = model_file.exists() and model_file.stat().st_size > 1_000_000_000
    return {
        "downloaded": downloaded,
        "loaded": engine.loaded,
        "loading": engine.loading,
        "downloading": _DL_STATE["running"],
        "percent": _DL_STATE["percent"],
        "progress": _DL_STATE["message"],
        "error": engine.error,
    }


@app.post("/api/local/download")
def local_download():
    """Baixa o modelo LFM3-Omni-2B apenas quando o usuário pede."""
    if _DL_STATE["running"]:
        return {"ok": False, "error": "download já em andamento"}
    threading.Thread(target=_download_model_bg, daemon=True).start()
    return {"ok": True, "started": True}


@app.post("/api/local/load")
def local_load():
    """Carrega o modelo na memória quando o usuário pede."""
    if not engine.loaded and not engine.loading:
        threading.Thread(target=engine.load, daemon=True).start()
    return {"ok": True}


def _download_model_bg():
    import subprocess
    from engine import MODEL_DIR

    _DL_STATE.update(running=True, percent=1, message="Iniciando download de ~4,1 GB…")
    try:
        cmd = [
            sys.executable, "-m", "huggingface_hub", "cli", "download",
            "LiquidAI/LFM3-Omni-2B", "--local-dir", str(MODEL_DIR),
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc.stdout or []:
            line = line.strip()
            if "%" in line:
                import re
                m = re.search(r"(\d{1,3})%", line)
                if m:
                    _DL_STATE["percent"] = int(m.group(1))
            if line:
                _DL_STATE["message"] = line[-160:]
        proc.wait()
        _DL_STATE["percent"] = 100
        _DL_STATE["message"] = "Download concluído. Carregando modelo…"
        engine.load()
    except Exception as exc:  # noqa: BLE001
        _DL_STATE["message"] = f"Erro: {exc}"
        logger.exception("Falha no download do modelo local")
    finally:
        _DL_STATE["running"] = False


_DL_STATE = {"running": False, "percent": 0, "message": ""}


@app.get("/live", response_class=HTMLResponse)
def live_page():
    return (BASE / "static" / "live.html").read_text(encoding="utf-8")


@app.websocket("/ws/live")
async def live_ws(ws: WebSocket):
    await ws.accept()
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
        or ws.query_params.get("key", "")
        or _saved_gemini_key()
    )
    if not api_key:
        await ws.send_json({
            "type": "error",
            "message": "Configure GEMINI_API_KEY (gratuita em aistudio.google.com/apikey) para usar a conversa ao vivo.",
        })
        await ws.close()
        return
    session = LiveSession(ws, api_key=api_key)
    await session.run()


@app.get("/", response_class=HTMLResponse)
def index():
    """Raiz = seletor de motor (Google Live ou LFM local)."""
    return (BASE / "static" / "start.html").read_text(encoding="utf-8")


@app.get("/api/status")
def status():
    return {
        "loaded": engine.loaded,
        "loading": engine.loading,
        "error": engine.error,
        "device": engine.device,
        "ufvai_available": bridge.available(),
        "live_model": DEFAULT_MODEL,
        "live_key_configured": bool(
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
            or _saved_gemini_key()
        ),
    }


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not engine.loaded:
        return JSONResponse({"error": "Modelo não carregado"}, status_code=503)
    
    ext = Path(file.filename).suffix or ".webm"
    path = TMP / f"rec_{uuid.uuid4().hex}{ext}"
    content = await file.read()
    path.write_bytes(content)
    
    # Converte para WAV 16kHz mono se necessário (via ffmpeg ou librosa)
    wav_path = path.with_suffix(".wav")
    try:
        import librosa
        import soundfile as sf
        y, sr = librosa.load(str(path), sr=16000, mono=True)
        sf.write(str(wav_path), y, 16000)
    except Exception as e:
        logger.error("Erro na conversão de áudio: %s", e)
        return JSONResponse({"error": f"Falha ao processar áudio: {e}"}, status_code=400)
    
    try:
        text = engine.transcribe(str(wav_path))
        return {"text": text}
    except Exception as e:
        logger.exception("Erro no ASR")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)


@app.post("/api/chat")
async def chat(payload: dict):
    if not engine.loaded:
        return JSONResponse({"error": "Modelo não carregado"}, status_code=503)
    
    user_text = payload.get("text", "").strip()
    use_ufvai = payload.get("use_ufvai", False)
    sid = payload.get("sid")
    grillme = payload.get("grillme", False)
    is_research = False
    if not user_text:
        return {"text": "", "audio": None}
    
    # Modo grill-me (LFM local): entrevista para montar o prompt do UFVAI.
    # Nunca delega ao UFVAI nesse modo — o objetivo é esclarecer a intenção.
    if grillme:
        logger.info("Grill-me local: %s", user_text[:60])
        sys = (
            "Você é o assistente de voz do UFVAI e está entrevistando o usuário "
            "para montar o melhor COMANDO para o UFVAI. Use sempre a palavra "
            "'comando', nunca 'prompt'. Fale em português brasileiro, frases curtas "
            "e naturais. Faça UMA pergunta por vez, em no máximo 6 rodadas, "
            "esclarecendo: tema/objetivo, tipo de entrega, dados disponíveis, recorte e "
            "normas (ABNT/APA/Vancouver). Quando tiver informação suficiente, apresente "
            "o comando final completo entre <<<COMANDO_UFVAI>>> e <<<FIM_COMANDO>>>, "
            "incluindo a exigência de não inventar dados nem referências. "
            "SEMPRE pergunte por voz se o comando está aprovado. Se o usuário confirmar "
            "(sim, pode executar, está bom), responda apenas: 'Comando aprovado. "
            "Executando agora.' Se não concordar, continue a entrevista e apresente um "
            "novo bloco <<<COMANDO_UFVAI>>> atualizado. Não invente dados."
        )
        reply_text = engine.chat(user_text, history=history[-8:], system_prompt=sys)
        speech_text = reply_text.replace("<<<COMANDO_UFVAI>>>", "").replace("<<<FIM_COMANDO>>>", "")[:600]
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply_text})
    else:
        # Roteamento: se estiver integrado à sessão do UFVAI, sempre delega.
        ufvai_keywords = ["pesquise", "ufvai", "artigo", "paper", "dados", "ibge", "datasus", "referência", "citação"]
        is_research = bool(sid) or use_ufvai or any(k in user_text.lower() for k in ufvai_keywords)
        if is_research and bridge.available():
            logger.info("Delegando ao UFVAI (sid=%s): %s", sid, user_text)
            reply_text = bridge.ask(user_text, sid=sid)
            speech_text = reply_text.replace("*", "").replace("#", "").replace("`", "")
            if len(speech_text) > 600:
                speech_text = speech_text[:600] + "... O restante está na tela."
        else:
            logger.info("Respondendo localmente: %s", user_text)
            system_prompt = (
                "Você é o assistente de voz do UFVAI, um agente de pesquisa científica da UFV. "
                "Responda em português brasileiro, de forma clara, concisa e adequada para síntese de voz. "
                "Não invente dados nem referências."
            )
            reply_text = engine.chat(user_text, history=history[-6:], system_prompt=system_prompt)
            speech_text = reply_text
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply_text})
    
    # Sintetiza a resposta
    audio_b64 = None
    try:
        wav_bytes = engine.synthesize(speech_text)
        import base64
        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
    except Exception as e:
        logger.error("Erro no TTS: %s", e)
    
    source = "grillme" if grillme else ("ufvai" if is_research and bridge.available() else "local")
    return {
        "text": reply_text,
        "audio": audio_b64,
        "source": source
    }


@app.post("/api/tts")
async def tts(payload: dict):
    if not engine.loaded:
        return JSONResponse({"error": "Modelo não carregado"}, status_code=503)
    text = payload.get("text", "")
    try:
        wav_bytes = engine.synthesize(text)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    port = int(os.environ.get("LFM3_VOZ_PORT", 8010))
    print(f"\n🎙️  UFVAI Voz (LFM3-Omni-2B) rodando em http://127.0.0.1:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
