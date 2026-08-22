# 🚀 UFVAI v0.6.4 — Marca completa · Temas UFVAI no terminal · Logo oficial · Termos v2 · Telemetria GA4

> **Data:** 22/08/2026 · **Pacote:** `pesquisai_0.6.4-1_amd64.deb` (~963 KB) · Engine: PesquisAI

## ✨ Destaques

### 🪪 O agente agora é o UFVAI — em todos os lugares
- `AGENTS.md` + diretrizes em 5 idiomas (pt/en/es/fr/zh): identidade, frontmatter, rodapé e cor da marca.
- IDs técnicos preservados por compatibilidade (`PESQUISAI_OBSIDIAN_VAULT`, pasta `~/PesquisAI`, pacote `pesquisai`).

### 🎨 Temas do TERMINAL na identidade UFVAI
- Escuro: fundos azul-noite `#141c24/#1f2831` · acento dourado `#d4b56a/#b29149` · amarelo UFV `#D1A705`.
- Claro: papel quente com texto azul-escuro. Azul antigo do PesquisAI eliminado (incluindo fallback JS que sobrescrevia o CSS).

### 🖼️ Abertura nova com a logomarca oficial
- Modal de onboarding antigo **removido** — a tela de **Termos de Uso** (com a logomarca oficial, servida localmente via `/assets`) é a única abertura.
- Corrige o bug do logo que dependia de URL externa no modo offline.

### 📊 Telemetria GA4 — canal duplo + painel Admin
- **Google tag (gtag.js)** com ID de medição embutido (`G-CMVTFP2M6F`; override por `UFVAI_GA_MEASUREMENT_ID`): rastreia sessões Colab/local (`page_view` + `ufvai_session`, `anonymize_ip`).
- **Measurement Protocol server-side** mantido para eventos do aplicativo (backups, provedores, idioma…).
- **Painel 📊 Telemetria (Admin)** na barra superior: estado em tempo real, cole ID + Secret sem editar arquivos (`~/.config/ufvai_telemetry.json`, chmod 600; secret nunca exibido de novo).
- 🔒 **Consent-gate único**: nada carrega/envia antes do aceite dos Termos com estatísticas marcadas. Kill-switch: `UFVAI_TELEMETRY=0`.

### 📜 Jurídico atualizado
- **Termos de Uso v2.0**: LGPD (art. 7º-I, 18, 33–36), Portaria CNPq nº 2.664/2026 (declaração de uso de IA), normas UFV (POSIC Res. Consu 12/2024, Código de Ética 04/2024), foro Viçosa/MG.
- **PRIVACY.md**: direitos do titular completos + DPO UFV. **LICENSE**: NOTICE de marca UFVAI.
- Re-consentimento automático na primeira abertura.

### 🛠️ Offline
- `install-offline.sh` reescrito (portas corretas 8001/8000, atalho `ufvai`, modelo `config/ufvai.env`).
- Correções acumuladas 0.6.x: servidor persistente, terminal gravável (`--writable`), auto-open, idioma do sistema.

## ✅ Qualidade
pytest **202/202** · smoke do wrapper, temas, rota `/assets` e painel admin aprovados · md5 pacote↔fonte conferidos.

## ⬇️ Instalação
```bash
sudo apt install ./pesquisai_0.6.4-1_amd64.deb
```
Iniciar: `pesquisa` (ou menu de aplicativos → UFVAI). Interface: http://localhost:8001

## ⚙️ Para administradores (ativar telemetria completa)
1. GA4 → Fluxo de dados `G-CMVTFP2M6F` → **Eventos de Measurement Protocol → Configurar** → copie o API Secret;
2. Na UI do UFVAI, abra o painel **📊 Telemetria** e cole ID + Secret;
3. Valide no DebugView (`export UFVAI_TELEMETRY_DEBUG=1`). Guia completo: `TELEMETRY.md §0`.

---
*UFVAI · Universidade Federal de Viçosa — DER · gustavo.braga@ufv.br*
