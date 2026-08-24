#!/bin/bash
# ============================================================================
# UFVAI Launcher v0.6.2 — standalone app mode (offline · Debian/Ubuntu)
# Restaura o comportamento do launcher v0.5.1.10 (Chrome --app + espera ativa)
# perdido na reformulação do v0.6.0, mantendo o rebrand UFVAI.
#
# Extras v0.6.2:
#   • Carrega ~/PesquisAI/config/ufvai.env antes de iniciar
#     (coloque lá ex.: UFVAI_GA_MEASUREMENT_ID / UFVAI_GA_API_SECRET)
#   • Se já estiver rodando, apenas reabre a interface
# ============================================================================
INSTALL_DIR="/opt/pesquisai"
USER_DIR="$HOME/PesquisAI"
LOG_FILE="$USER_DIR/logs/ufvai.log"
PID_FILE="$USER_DIR/pesquisai.pid"
CHROME_PROFILE="$USER_DIR/chrome-profile"
ENV_FILE="$USER_DIR/config/ufvai.env"
APP_URL="http://127.0.0.1:8001"

# ── Estrutura de diretórios do usuário ──────────────────────────────────────
mkdir -p "$USER_DIR/vault" "$USER_DIR/outputs" "$USER_DIR/backups" \
         "$USER_DIR/logs" "$USER_DIR/sessions" "$USER_DIR/chrome-profile" \
         "$USER_DIR/config" 2>/dev/null

# Auto-reparo: ~/PesquisAI root-owned de execuções antigas
if [ ! -w "$USER_DIR" ] 2>/dev/null; then
    sudo -n chown -R "$(id -un):$(id -un)" "$USER_DIR" 2>/dev/null || true
    sudo -n chmod -R u+rwX "$USER_DIR" 2>/dev/null || true
fi

# Fallback /tmp sem escrita em $HOME
if [ ! -w "$USER_DIR" ] 2>/dev/null; then
    USER_DIR="/tmp/PesquisAI"
    LOG_FILE="$USER_DIR/logs/ufvai.log"
    PID_FILE="$USER_DIR/pesquisai.pid"
    CHROME_PROFILE="$USER_DIR/chrome-profile"
    ENV_FILE="$USER_DIR/config/ufvai.env"
    mkdir -p "$USER_DIR/vault" "$USER_DIR/outputs" "$USER_DIR/backups" \
             "$USER_DIR/logs" "$USER_DIR/sessions" "$USER_DIR/chrome-profile" \
             "$USER_DIR/config"
fi

# ── Config local opcional (telemetria etc.) ─────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    echo "⚙️  Config carregada: $ENV_FILE"
fi

# ── Abre a interface como APP separado ──────────────────────────────────────
open_app() {
    if command -v google-chrome &>/dev/null; then
        nohup google-chrome --app="$APP_URL" \
            --user-data-dir="$CHROME_PROFILE" \
            --class="UFVAI" --app-name="UFVAI" \
            --no-first-run --no-default-browser-check \
            &>/dev/null &
        echo "   🖥️  App separado (Google Chrome)"
    elif command -v google-chrome-stable &>/dev/null; then
        nohup google-chrome-stable --app="$APP_URL" \
            --user-data-dir="$CHROME_PROFILE" \
            --class="UFVAI" --app-name="UFVAI" \
            --no-first-run --no-default-browser-check \
            &>/dev/null &
        echo "   🖥️  App separado (Chrome Stable)"
    elif command -v chromium-browser &>/dev/null || command -v chromium &>/dev/null; then
        CHROMIUM=$(command -v chromium-browser || command -v chromium)
        nohup "$CHROMIUM" --app="$APP_URL" \
            --user-data-dir="$CHROME_PROFILE" \
            --class="UFVAI" --app-name="UFVAI" \
            --no-first-run --no-default-browser-check \
            &>/dev/null &
        echo "   🖥️  App separado (Chromium)"
    elif command -v firefox &>/dev/null; then
        nohup firefox -new-window "$APP_URL" &>/dev/null &
        echo "   🖥️  Firefox"
    elif [ -z "${UFVAI_NO_OPEN:-}" ]; then
        xdg-open "$APP_URL" &>/dev/null &
        echo "   🌐 Navegador padrão"
    else
        echo "   🔇 UFVAI_NO_OPEN definido — navegador não aberto."
    fi
}

# ── Já está rodando? Só reabre a UI ─────────────────────────────────────────
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    if curl -s "$APP_URL" >/dev/null 2>&1; then
        echo "🧬 UFVAI já está rodando (PID $(cat "$PID_FILE"))."
        open_app
        echo "   💡 Interface: $APP_URL"
        echo "   💡 Para parar: kill \$(cat $PID_FILE)"
        exit 0
    fi
    # PID órfão (processo morreu) — limpar
    rm -f "$PID_FILE"
fi

cd "$INSTALL_DIR" || { echo "❌ $INSTALL_DIR não encontrado."; exit 1; }
export PESQUISAI_HOME="$USER_DIR"

# ── Inicia servidor em background ────────────────────────────────────────────
PYTHONPATH="$INSTALL_DIR:$PYTHONPATH" nohup python3 -c "from pesquisai.run_fast import run; run()" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "🧬 UFVAI iniciando… (a 1ª execução instala dependências e pode demorar)"
for i in $(seq 1 180); do          # até 3 min no primeiro boot
    if curl -s "$APP_URL" >/dev/null 2>&1; then
        echo "   ✅ Pronto! (PID $(cat "$PID_FILE"))"
        open_app
        echo "   📋 Logs: $LOG_FILE"
        echo "   🔗 URL: $APP_URL"
        echo ""
        echo "   💡 Abrir novamente: pesquisai (ou http://localhost:8001)"
        echo "   💡 Para parar: kill \$(cat $PID_FILE)"
        exit 0
    fi
    sleep 1
done

echo "⚠️  Tempo limite excedido (180 s). Últimas linhas do log:"
tail -15 "$LOG_FILE" 2>/dev/null
echo "   Log completo: $LOG_FILE"
echo "   Tente acessar manualmente: $APP_URL"
exit 1
