# 🚀 UFVAI v0.6.5 — Terminal à prova de travamentos · Splash de carregamento · /api/ttyd_ready

> **Data:** 22/08/2026 · **Pacote:** `pesquisai_0.6.5-1_amd64.deb` · Engine: PesquisAI

## ✨ Destaques

### 🔐 Kill cirúrgico do terminal (sem danos colaterais)
- O **ttyd agora é o líder do próprio grupo de processos** (`start_new_session=True`) e fica
  rastreado em `_TTYD_PROC`: `_stop_terminal()` mata a **árvore inteira** (ttyd + bash + opencode)
  com um único `killpg`, sem o antigo `pkill -f opencode` **global**, que matava qualquer processo
  com "opencode" na linha de comando — inclusive o agente hospedeiro.
- Fallback determinístico: `pkill -9 -x ttyd` (COMM **exato**), nunca `-f`. O mesmo cuidado foi
  aplicado ao temporário de preparação do mobile (`--index`), com terminate/wait antes do killpg.
- `kill_previous()` no boot também migrou para `pkill -x`.

### 🖥️ Endpoint `/api/ttyd_ready` + splash de carregamento na UI
- Novo endpoint consultado pelo frontend **antes de apontar o iframe**: fim do
  **ERR_CONNECTION_REFUSED** exibido no boot, na troca de idioma e na restauração de sessão.
- **Splash de carregamento** (`boot-splash`) com a logomarca UFVAI, spinner e status
  ("Iniciando terminal…" / "Reiniciando…" / "Restaurando sessão…"), timeout e botão Recarregar —
  **nos 5 idiomas** (pt/en/es/fr/zh), com fallback honesto (nada de reload às cegas).

### 🔁 Restart por idioma e restauração de sessão honestos
- `_build_ttyd_cmd()` extraído para permitir retry determinístico; troca de idioma e restauração
  usam `_ensure_terminal_ready()` com **retorno real** (antes respondiam "ok" mesmo quando a porta
  nunca abria — causa raiz do refresco que encontrava o terminal morto).

## 🧪 Validação
- `py_compile` OK · **pytest completo** (suite de 202+ testes, workaround `--override-ini`) ·
  smoke do wrapper (i18n do splash, 5 idiomas) · `md5 deb ↔ fonte` consistente.

## 📦 Instalação
```bash
sudo dpkg -i pesquisai_0.6.5-1_amd64.deb
# ou, instalando a partir da fonte:
bash install-offline.sh
```

> ⚠️ **Teste local recomendado (mantenedor):** keep-alive (porta 8001 após fechar), terminal
> gravável, logo offline nos Termos, temas do terminal, re-consentimento dos Termos v2 e
> DebugView da telemetria com credenciais GA4 reais.
