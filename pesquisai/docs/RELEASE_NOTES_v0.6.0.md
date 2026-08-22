# 🚀 Release Notes — UFVAI v0.6.0 (21/08/2026)

**Marca nova, mais seguro, contando uso com o seu consentimento — e falando chinês.**

Destaques → detalhes completos no `CHANGELOG.md`; auditoria em `docs/SECURITY_AUDIT_2026-08-21.md`.

## 🏷️ UFVAI é a nova marca
- Interface (wrapper + botão de lançamento no notebook) rebrandada: paleta dourado/azul-profundo,
  wordmark **UFV**AI em Montserrat, ícone lupa dourada.
- **Nada quebra:** pacote Python continua `pesquisai`, sua pasta do Drive continua
  `PesquisAI/`, endpoints `/api/*` inalterados. Temas antigos (`pesquisai`/`pesquisai-light`)
  continuam válidos; aliases `ufvai`/`ufvai-light` também funcionam.

## 🔐 Segurança (auditoria integral)
- Fechadas **2 falhas críticas de exposição**: exfiltração de API keys via CORS aberto e RCE
  pós-`&&` na sanitização de comandos; tokens do OpenCode agora cifrados no Drive.
- Token de sessão obrigatório em `/api/*` (transparente para o usuário da UI).
- Rate limit generoso, cap de payload, headers seguros, sanitização anti-traversal.
- **`--yolo` mantido** por decisão do projeto; opcionalmente desligue com `PESQUISAI_YOLO=0`.
- Bugfix funcional: botão "Restaurar sessão" voltou a operar (`cmd`/`command`).

## 📊 Telemetria anônima opt-in
- Contadores de uso via GA4 Measurement Protocol — **sem cookies, sem conteúdo, sem PII**.
- Só envia com: consentimento explícito (tela de Termos) + credenciais GA4 configuradas +
  kill-switch não acionado (`UFVAI_TELEMETRY=0`).
- Guia completo: [`TELEMETRY.md`](../TELEMETRY.md) · privacidade: [`PRIVACY.md`](../PRIVACY.md).

## 📜 Termos de Uso na entrada
- Overlay bloqueante na 1ª abertura: aceite obrigatório com link para a **licença MIT no GitHub**,
  checkbox opcional e separado para telemetria, recusa educada, persistência local.

## 🇨🇳 中文（简体）
- Quinto idioma completo: menu 🇨🇳, detecção automática, saudação do agente
  ("你好！(提示：从现在开始请用简体中文回答。)"), traduções inline + `zh_CN.json`.

## ✅ Qualidade
- Suíte: **233 testes passando** (novos vetores de segurança + telemetria).
- Versão sincronizada em `__version__.py` / `pyproject.toml` / Dockerfile.

## ⬆️ Como publicar (checklist do mantenedor)
1. Subir esta pasta para o repo (commit único ou por área);
2. Criar propriedade GA4 → obter `G-XXXX` + API secret;
3. No Colab/notebook oficial, exportar `UFVAI_GA_MEASUREMENT_ID` e `UFVAI_GA_API_SECRET`
   (sem isso a telemetria permanece inativa mesmo com aceite dos usuários);
4. Tag `v0.6.0` + GitHub Release anexando `debs/` se aplicável;
5. Conferir página de Terms/Privacy renderizando os .md no GitHub.
