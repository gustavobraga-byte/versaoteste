# Changelog — PesquisAI


## [0.6.4] — 2026-08-22 — 🪪 Marca UFVAI completa · 🎨 Temas UFVAI no terminal · 🖼️ Logo oficial · 📜 Termos v2

### Marca (PesquisAI → UFVAI)
- **AGENTS.md + `agents/AGENTS.{pt,en,es,fr,zh}.md`**: o agente agora se apresenta como **UFVAI** — frontmatter (`name`, versão 0.6.4, cor dourada `#b29149`), título, identidade (§1), capacidades, memória, limitações e rodapé. IDs técnicos preservados: `PESQUISAI_OBSIDIAN_VAULT`, caminhos `~/PesquisAI` e `/content/drive/My Drive/PesquisAI/`, tags `pesquisai/*`, pacote Python `pesquisai`.
- Agente gerado pelo OpenCode (`run_fast._setup_theme_and_agent()`): `name: UFVAI` + cor dourada.
- Strings de UI do wrapper (i18n inline em 5 idiomas): "Memória/Memory/Mémoire UFVAI", "Regras e princípios do UFVAI".

### Terminal — temas harmonizados com a identidade UFVAI
- **Temas do TUI regenerados** (`pesquisai.json` / `pesquisai-light.json`): escuro com fundos azul-noite `#141c24/#1f2831` (rail da marca), acento primário **dourado** `#d4b56a/#b29149`, amarelo UFV `#D1A705`, secundário azul-aço dessaturado; claro com papel quente e texto azul-escuro `#1f2831`. Azul antigo do PesquisAI (`#4fc3f7`) eliminado de todos os pontos.
- **Wrapper HTML**: o fallback JS do `applyWrapperTheme()` sobrescrevia o CSS canônico com teal antigo (`#157a73`/`#46a39b`) — agora reflete a paleta UFVAI; tema claro dourado sobre papel quente (antes teal/laranja); anti-flash e `theme-color` em `#141c24`; banner Colab ("ABRIR O UFVAI") em gradiente dourado.

### Abertura — logo oficial + fim do modal antigo
- **REMOVIDO o onboarding antigo do PesquisAI** (`welcome-hint`: logo do GitHub + botão "Começar") que empilhava com a tela de Termos. A tela de **Termos de Uso é a única abertura**.
- **Logomarca oficial** (`logo_8x8cm_300dpi.jpg`, otimizada p/ 288 px / 6,9 KB) exibida na tela de Termos via nova rota **`/assets/*` offline-safe** (whitelist estrita + traversal guard; procura no diretório do código → `/opt/pesquisai/assets` → `~/PesquisAI/assets`; `onerror` esconde graciosamente). Resolve o bug do logo que dependia de `raw.githubusercontent.com`.

### Legal
- **Termos de Uso v2.0** (`docs/TERMS_OF_USE.md`): definições, distinção licença×termos, integridade acadêmica alinhada à **Portaria CNPq nº 2.664/2026** e normas UFV (**POSIC — Resolução Consu/UFV nº 12/2024**, Código de Ética — Res. Consu nº 04/2024), LGPD completa (consentimento art. 7º I, direitos art. 18, transferência internacional arts. 33–36), foro Viçosa/MG, cessação e contato/DPO.
- **PRIVACY.md**: seção "Seus direitos" reescrita com os 9 direitos do art. 18, canal do titular e DPO UFV (`dgi.ufv.br/privacidade`), nota sobre pseudonimização do `client_id` e registro das operações (art. 37).
- **LICENSE**: titular atualizado para "Gustavo Bastos Braga — Universidade Federal de Viçosa (DER/UFV)" + bloco **NOTICE** (marca UFVAI, Termos v2.0, integridade científica).
- **Overlay de Termos** atualizado (menção à Portaria CNPq e LGPD) e **re-consentimento forçado** (`ufvai_terms_version = 2`).

### Telemetria — canal duplo + painel Admin na UI
- **Google tag (gtag.js) client-side** com o ID de medição do admin (`G-CMVTFP2M6F` embutido como default; override por `UFVAI_GA_MEASUREMENT_ID`): rastreia sessões no Colab/local (`page_view`, `ufvai_session` com versão/ambiente/idioma, `anonymize_ip`). **Consent-gate**: só carrega após aceite dos Termos com estatísticas marcadas — sem consentimento não há requisição ao googletagmanager nem cookie `_ga`.
- **Painel 📊 Telemetria (Admin)** na barra superior: estado em tempo real (ativa/inativa/motivo), campos ID de medição + API Secret salvos em `~/.config/ufvai_telemetry.json` (chmod 600, aplicados imediatamente no processo; secret nunca é devolvido pela API). Novos endpoints `GET/POST /api/admin/telemetry` (mesmo token da sessão). Strings i18n nos 5 idiomas.
- `telemetry.py`: `_ga_config()` agora lê env → arquivo local; novas funções `save_admin_config()` e `masked_state()`.
- **TELEMETRY.md §0 — Guia do administrador em 8 passos**: criar propriedade GA4 → fluxo Web → Measurement ID → segredo MP → `~/PesquisAI/config/ufvai.env` (offline) ou `os.environ` (Colab) → validação via DebugView → o que o admin vê × nunca vê → conformidade LGPD operacional.

### Offline
- **install-offline.sh reescrito (v0.6.4)**: marca UFVAI, portas corretas (UI 8001 · terminal 8000), atalho `ufvai` (+ alias `pesquisa` mantido por compatibilidade), modelo comentado de `config/ufvai.env`, verificação de requisitos robusta.

### Validação
- `py_compile` OK · **pytest 202/202** · smoke do wrapper (12 verificações) e dos temas (9) aprovados.


## [0.6.3] — 2026-08-22 — 🔌 Servidor persistente offline · 🎨 Ícone UFVAI no dock

### Correções
- **BUG CRÍTICO (offline) — "conexão recusada" em localhost:8001**: o wrapper HTTP roda em **thread daemon**; ao fim de `run()` a main thread terminava e o interpretador encerrava o processo, matando o servidor segundos depois da inicialização (no Colab não aparecia, pois o kernel permanece vivo). Agora `run_fast._offline_keep_alive()` mantém o processo ativo fora do Colab — encerra com Ctrl+C (foreground) ou `kill $(cat ~/PesquisAI/pesquisai.pid)` (background); `UFVAI_NO_KEEPALIVE=1` desabilita.
- **Regressão restaurada — servidor dual-stack**: o 0.5.x bindava IPv4+IPv6 no loopback justamente porque Chromium/Firefox preferem `::1` ao resolver "localhost"; o hardening v0.6.0 deixou só IPv4. Agora, além do listener principal, sobe um loopback IPv6 (`::1`) adicional quando local.

### Interface
- **Ícone UFVAI no dock**: a janela aberta pelo launcher usa `--class="UFVAI"`, que agora casa com o novo `ufvai-app.desktop` (`StartupWMClass=UFVAI`) e PNGs instalados nos temas hicolor (256/128/64) — a barra/dock mostra a lupa dourada da marca em vez do ícone do navegador. `postinst` instala ícones + desktop entry e atualiza os caches.


## [0.6.2] — 2026-08-22 — ⌨️ Terminal gravável · 🖥️ Launcher app-mode · 📊 Telemetria debug

### Correções
- **BUG CRÍTICO — não dava para digitar no terminal**: o v0.6.0 perdeu a flag `--writable` do ttyd (regressão do hardening) e o terminal ficava **read-only**. Restaurada em `start_ttyd()` e na restauração de sessão (`/api/run_terminal`).
- **Modo offline (.deb) não abria a interface**: o launcher do v0.6.0 apenas imprimia a URL em background, sem feedback. Restaurado o comportamento do launcher v0.5.1.10: espera ativa da porta 8001 via `curl` (até 180 s na 1ª execução), abertura como **app separado** (Chrome `--app` com perfil próprio → Chromium → Firefox → `xdg-open`), PID-file e reabertura da UI se já estiver rodando. Fonte versionada em `debs/launcher/ufvai-launcher.sh`.

### Telemetria
- `UFVAI_TELEMETRY_DEBUG=1` envia os eventos para o **DebugView** do GA4 (tempo real, sem gravar relatórios) — facilita validar a configuração.
- O launcher agora carrega `~/PesquisAI/config/ufvai.env` antes de iniciar: coloque lá `UFVAI_GA_MEASUREMENT_ID` e `UFVAI_GA_API_SECRET` para ativar a telemetria no modo offline.

### Requisitos para a telemetria enviar de verdade (os 3 precisam estar ativos)
1. Credenciais no ambiente: `UFVAI_GA_MEASUREMENT_ID` + `UFVAI_GA_API_SECRET`;
2. Consentimento: checkbox "estatísticas anônimas" marcado na tela de Termos (`~/.config/ufvai_consent.json` → `"analytics": true`);
3. Kill-switch desligado (`UFVAI_TELEMETRY` ≠ `0`).


## [0.6.1] — 2026-08-22 — 🌐 Idioma do sistema · 🔁 Troca de idioma robusta · 🌍 Auto-open offline

### Correções
- **Troca de idioma agora muda a mensagem inicial** (Colab e .deb): o frontend recarregava a página em 700 ms enquanto o backend ainda reiniciava o ttyd (~3–4 s) — o iframe reconectava num terminal morto/antigo e a saudação não mudava. `setLang()` passou a ser `async` (aguarda o POST `/api/lang` com timeout de segurança de 15 s) e o backend só responde depois que a porta do terminal já aceita conexões (`_wait_port_open`, até 12 s).
- **Idioma do SISTEMA detectado na 1ª execução** (`$LANGUAGE` → `$LC_ALL` → `$LC_MESSAGES` → `$LANG` → `locale`): saudação inicial no idioma do usuário (pt/en/es/fr/zh); preferência persistida em `~/.config/pesquisai_lang`. O frontend já usava `navigator.language` como fallback da UI.
- **Modo offline (.deb) abre o navegador sozinho**: launcher roda em background e antes não havia feedback ("parecia não iniciar"). Agora thread daemon espera a porta da UI responder (até 30 s) e abre o navegador (`webbrowser` → fallback `xdg-open`/`open`). Desabilitar com `UFVAI_NO_OPEN=1`.

### Marca
- Banners Colab/console atualizados para UFVAI: "✨ UFVAI pronto!" · "ABRIR O UFVAI".

### Arquivos
- `pesquisai/launch_app.py`: `_detect_system_lang()`, `_persist_lang()`, `_wait_port_open()`, `_auto_open_browser()`; unificação do mapa de idiomas em `_LANG_MAP`; restart do ttyd com espera ativa da porta.
- `pesquisai/launch_app_responsive_v041.py`: `setLang()` assíncrono com await + fallback.
- `pesquisai/__version__.py` / `pyproject.toml`: 0.6.0 → **0.6.1**.


## [0.6.0] — 2026-08-21 — 🏷️ UFVAI · 🔐 Hardening · 📊 Telemetria opt-in · 🇨🇳 zh_CN · 📜 Termos

### Marca
- **Rebrand visual PesquisAI → UFVAI** (wrapper/notebook/assets): paleta dourado `#b29149`/`#D1A705` + azul profundo `#141c24`/`#1f2831`, wordmark **UFV**(700)+**AI**(600) em Montserrat, ícone lupa dourada. Identificadores técnicos preservados (pacote `pesquisai`, pasta Drive `PesquisAI`, endpoints `/api/*`).

### Segurança (auditoria completa — docs/SECURITY_AUDIT_2026-08-21.md)
- **CORS `*` removido** de todos os endpoints; token de sessão obrigatório em `/api/*` (injetado no HTML; patch global de `window.fetch`). Fecha exfiltração de API keys por páginas maliciosas.
- **Sanitização por segmento `&&`**: valida cada comando após `&&` contra a allowlist (fecha RCE pós-&&).
- **`opencode_auth.json` agora é gravado CIFRADO** (Fernet) no Drive; leitura aceita legado plaintext.
- `GET /api/apikey?provider=` retorna chave sempre mascarada; `/api/debug`/`diagnose`/`health` não listam mais nomes de env secrets.
- `/api/restore` com sanitização anti-path-traversal; nome de backup saneado.
- `ThreadingHTTPServer`, cap de corpo (10 MB), rate limit generoso (120/min/IP), headers `nosniff`/`no-referrer`/`SAMEORIGIN`.
- Bind: Colab mantém `0.0.0.0`; local passa a `127.0.0.1` (override `UFVAI_BIND_HOST`).
- `--yolo` **mantido por padrão** (decisão do usuário); desligável com `PESQUISAI_YOLO=0`.
- Bugfix: `/api/run_terminal` aceita `cmd` OU `command` (botão "Restaurar sessão" voltou a funcionar).
- Normalização de 12 escapes JS-regex latentes em strings Python (elimina SyntaxWarning/erro em py≥3.12; saída idêntica).

### Telemetria anônima opt-in
- Novo módulo `pesquisai/telemetry.py` (GA4 Measurement Protocol server-side). Sem consentimento/config não envia nada; kill-switch `UFVAI_TELEMETRY=0`. Zero conteúdo — só contadores. Detalhes: `TELEMETRY.md` e `PRIVACY.md`.

### Termos de Uso
- Tela de aceite obrigatória na 1ª entrada (overlay bloqueante, i18n, links para LICENSE/TERMOS/PRIVACIDADE no GitHub) + endpoint `/api/consent`.

### Internacionalização
- **中文（简体） zh_CN completo**: menu 🇨🇳, detector, saudação do agente, traduções inline + `zh_CN.json`.

### Correções
- Versão sincronizada 0.6.0 (`__version__.py`/`pyproject.toml`/Dockerfile); Dockerfile label corrigido.

---
## [0.5.1.9] - 2026-07-18 - Versão Offline para Linux e atualização do AGENTS.md

### 🚀 Major Changes

-**Instalador offline para Linux**: Instalador em formato .deb para utilização offline do PesquisAI.
- **Reescrita completa do AGENTS.md**: Principal atualização desde a introdução da memória persistente. O documento foi reformulado do zero para maior clareza, consistência normativa, economia de tokens e alinhamento com o código-fonte (`constants.SKILL_REGISTRY`).
- **Nova arquitetura de diretórios**: Introduzida separação oficial entre `vault/` (memória interna do agente) e `outputs-<slug-do-projeto>/` (entregáveis finais organizados por projeto). Isso melhora organização, reprodutibilidade e experiência do usuário final.
- **Fortalecimento de Integridade e Segurança**: 
  - Protocolo completo de defesa contra prompt injection (ignorar, manter tarefa original e avisar usuário).
  - Proteção explícita contra acesso a arquivos de segredos (`keys_store.json` e `keys_encryption_key.bin`).
  - LGPD com "hard stop": interrupção obrigatória de gravação ao detectar dados sensíveis não anonimizados.

### ✨ Improvements

- **Catálogo de Skills**: Totalmente sincronizado com o registry real. Removidas referências infladas ("147+ skills") e adicionados IDs canônicos (`qualitativa`, `grant-finder`, `memorial`, `obsidian-memory`, `BR-DWGD`, `meta-search-br`).
- **Gestão de Memória**: 
  - Frontmatter enriquecido com `updated`, `accessed_at`, `dataset_version`, `evidence_refs` e `source_language`.
  - Atualização automática e obrigatória de `moc/last-state.md` no fim de sessões/tarefas relevantes.
  - Clarificada a condicionalidade do salvamento (obrigatório apenas quando `PESQUISAI_OBSIDIAN_VAULT` está ativa).
- **Regras de Precedência**: Seção dedicada e expandida, blindando integridade (§4.1), proibições de memória (§2.2.1), injeção de prompt e restrições de path traversal.
- **Geração de Arquivos**: PDF agora obrigatório apenas para entregáveis finais (artigos, memoriais, relatórios). Notas internas não geram mais PDF automaticamente.
- **Declaração de Uso de IA**: Agente agora sugere ativamente a inclusão da declaração em entregas acadêmicas finais.
- **Exemplos e Limitações**: Exemplos positivo/negativo mais robustos (incluindo proibição de URLs falsas). Seção de limitações expandida com "Non-goals" explícitos (pareceres médicos/jurídicos, CEP/CONEP, submissão automática, etc.).

### 🛡️ Security & Compliance

- Fechada brecha que permitia edição de notas humanas via `force=True`.
- LGPD reforçada com recusa explícita mesmo diante de insistência do usuário.
- Proteção contra path traversal e vazamento de segredos criptográficos.

### 📋 Documentation

- AGENTS.md agora funciona como fonte canônica de comportamento do agente em runtime.
- Melhoria significativa na legibilidade e na capacidade de manutenção futura.

### 🔄 Outras Alterações

- Alinhamento entre `AGENTS.md`, `docs/INTEGRITY.md`, `docs/OBSIDIAN_MEMORY_MODEL.md` e o código-fonte.
- Redução estimada de ~18–25% no consumo de tokens do prompt do sistema.
- Preparação para futuras features (Workspace de Projetos, Evidence Ledger e Reprodutibilidade) já contempladas na nova estrutura.


---
## [0.5.1.8] — 2026-07-10 — 🐛 3 bugfixes: provider buttons, session restore, backup confirm

### 🔧 Bugfix 1: Provider edit/delete buttons (SyntaxError)

**Problema:** `JSON.stringify(provider)` dentro de `onclick="..."` em uma string Python `"""..."""` gerava SyntaxError. O interpretador Python consumia as aspas escapadas, produzindo JavaScript inválido.

**Correção:**
- Substituído `onclick="editSavedKey(JSON.stringify(provider))"` por `data-provider="..." onclick="editSavedKey(this.dataset.provider)"`
- Mesmo padrão para `deleteSavedKey`
- Sem `JSON.stringify` inline = sem conflito de escapes com a string tripla do Python

**Arquivo:** `launch_app_responsive_v041.py` — função `renderSavedKeys()`

---

### 🔧 Bugfix 2: Session history não atualiza ttyd

**Problema:** O comando `opencode session restore <sessionId>` restaurava os dados da sessão no disco, mas o servidor sempre iniciava um **opencode novo do zero** após o comando (linha 1600 do `launch_app.py`: `bash_cmd = f"{cmd}; {_opencode_bin}; exec bash"`). O terminal nunca refletia a sessão restaurada.

**Correção:**
- Troca do comando para `opencode -s <sessionId>` com `no_fallback: true`
- `no_fallback: true` elimina o `; {_opencode_bin}` — o opencode já inicia **direto na sessão** restaurada
- `setTimeout(() => location.reload(), 2500)` recarrega a página para conectar ao novo ttyd
- Mesmo padrão do endpoint `/api/restore` (backup)

**Arquivo:** `launch_app_responsive_v041.py` — função `_doRestoreSession()`

---

### ✨ Feature 3: Confirmação antes de restaurar backup

**Problema:** `doRestore(file)` executava a importação do backup imediatamente, sem confirmação do usuário.

**Correção:**
- Toda a lógica de `doRestore()` foi envolvida em `pesquisaiConfirm()`
- Usa chave i18n `ui.restore` para o texto do botão
- Cancelar = não executa nada; Confirmar = importa o backup

**Arquivo:** `launch_app_responsive_v041.py` — função `doRestore()`

---

### 🧩 Nova skill: Memorial UFV

- **Nova skill `skill-memorial-ufv`** — Geração automática do Memorial RSC-PCCTAE (Relatório Detalhado → memorial formatado UFV/ABNT)
- Repositório: [github.com/gustavobraga-byte/Memorial_ufv](https://github.com/gustavobraga-byte/Memorial_ufv)
- Fluxo: lê o PDF do Relatório Detalhado RSC emitido pelo sistema oficial da UFV, extrai dados estruturados, gera narrativas longas em linguagem acadêmico-científica e formata conforme normas UFV/ABNT
- Gera saída em `.md` e `.docx` formatado

---

### 🧩 Alterações adicionais no provider flow

- **NOVO `prov-step0`**: Tela inicial do modal de provedores lista as chaves salvas no Drive com botões editar/excluir, antes de mostrar a lista de provedores para adicionar.
- **NOVO botão "Voltar"**: Navegação `prov-step1 → prov-step0` via `provBack()`.
- **NOVO botão "↻ Atualizar"**: No modal de sessões, recarrega a lista sem fechar.
- **Largura do modal de provedores**: 480px → 520px para acomodar os botões de ação das chaves salvas.

---

## [0.5.1.5] — 2026-07-01 — 🧠 Editor de Memória Obsidian no botão 🧠

> **Nota:** v0.5.1.5 foi um hotfix para v0.5.1.4. As versões 0.5.1.6 e 0.5.1.7 foram patches internos não lançados publicamente.

### 🧠 Editor de Memória (Obsidian Memory Editor)

- **Modal split view**: Lista de notas à esquerda + editor markdown com abas Edit / Preview / Split à direita
- **4 endpoints REST novos:**
  - `GET  /api/obsidian/note?path=...` — ler nota crua
  - `GET  /api/obsidian/tree?subdir=...` — árvore agrupada por subdiretório
  - `GET  /api/obsidian/search?q=...` — busca BM25 com debounce 150ms
  - `GET  /api/obsidian/tags` — lista de tags usadas com contagem
- **POST /api/obsidian/note** com 3 ações:
  - `action=save` — sobrescrever nota (force=true para notas humanas)
  - `action=create` — criar nova nota a partir de template
  - `action=delete` — mover para `.trash/` (force=true para notas humanas)
- **Preview markdown** via `marked.js` com destaque de `[[wikilinks]]` e `#tags`
- **Dirty indicator**: Indicador visual de edição não salva
- **20 novas chaves i18n** (`memory.editor.*`) em pt_BR, en_US, es_ES, fr_FR
- **Bugfix**: `from pathlib import Path` faltava — quebrava `tree` endpoint

### 🔧 Hotfix v0.5.1.5

- Botões do editor não funcionavam (SyntaxError JS em string multilinha) — **corrigido**

---

## [0.5.1.3] — 2026-06-30 — 🔌 Conectores de Provedor de IA

- **Bugfix:** `confirmProvider()` crashava com TypeError antes de salvar a API key
- Captura local de `_selProv.id`/`env`/`name` antes de `closeProvider()`
- Verifica `r.ok` e `d.ok` no fetch (antes: sempre exibia "✅ Salvo!")
- `closeProvider()` movido para após o sucesso do salvamento

---

## [0.5.1.2] — 2026-06-30 — 🧠 Botão Memória Obsidian no topbar

- **Overlay de Memória** mostra status (ready/disabled/...) + stats + notas recentes + daily notes
- **Endpoint**: `GET /api/obsidian` (status da memória persistente)

---

## [0.5.1] — 2026-06-29 — 🤖 Obsidian Autopilot (Salvamento Autônomo)

### 🤖 O agente agora SALVA SOZINHO

- **`pesquisai/obsidian/autopilot.py`** (NOVO) — API de alto nível com funções LLM:
  - `recall(query)` — busca no vault antes de responder
  - `save(title, body, tags)` — salva nota após concluir tarefa
  - `save_finding(text, source)` — captura rápida (1 linha)
  - `start_session()` / `end_session(summary)` — log automático
  - `log_skill(id)` / `log_file(path)` — tracking de atividades
  - `auto_init()` — inicializa vault + daily + MOC + sessão
- **`run_fast.py`** (EDITADO) — chama `auto_init()` na inicialização
- **Prompt do agente** injeta instruções de autopilot
- Vault criado automaticamente em `<DRIVE>/PesquisAI/vault/`
- Daily note e MOC raiz criados automaticamente
- **Tudo é no-op** se o vault não estiver disponível
- **Vault SEMPRE no Google Drive** (validação obrigatória)

---

## [0.5.0] — 2026-06-28 — 🧠 Obsidian Second Brain (Long-Term Memory)

- Módulo `pesquisai.obsidian` (8 arquivos, ~1.500 linhas)
- Skill `obsidian-memory` (repositório git separado)
- 10 templates Obsidian (daily, research, literature, session, methodology, datasource, hypothesis, reference, moc, inbox)
- Memória persistente entre sessões via vault no Google Drive
- Busca BM25 offline + backlinks + wikilinks + tags
- Taxonomia de tags `pesquisai/*` (19 tags oficiais)
- **REGRA:** vault SEMPRE no Google Drive (rejeita fora no Colab)
- 71 testes pytest (100% passing) + teste e2e validado

---

## [0.4.2.3] — 2026-06-27 — 🔥 BUGFIX CRÍTICO — Botões do wrapper quebrados

- **🛑 JS BROKEN:** A string tripla `"""..."""` do `launch_app_responsive_v041.py` continha escapes de aspas que Python removia durante a compilação, gerando JavaScript com sintaxe inválida → **TODOS os botões do HTML paravam de funcionar** (SyntaxError no `<script>`)
- ✅ `renderSessions`: `onclick` inline trocado por `data-session-id` + event delegation
- ✅ `restoreSession`: `confirm(...)` com aspas escapadas trocado por `confirm(...chr(34)...)` (concat JS)
- ✅ `escapeHtml`: object literal com aspas trocado por if/else chain
- ✅ Validado: Node.js `--check` passa, 79/79 testes pytest OK

---

## [0.4.2.2] — 2026-06-24 — Ses_10a4+: 6 correções adicionais

- **🖥️ FOOTER PC:** Botão provedor + "Powered by OpenCode" alinhados à direita no desktop (`margin-left: auto`)
- **🧩 SKILLS:** `grant-finder` e `meta-search-br` em `skills/` com links para clonar do GitHub
- **📜 SESSÕES:** `openSessions()` agora faz fetch em `/api/sessions` e popula a lista
- **🌍 LANG:** Ao trocar idioma, ttyd reinicia com saudação no idioma + instrução persistente
- **📦** `__version__.py` movido para `pesquisai/__version__.py`
- **🧹** AGENTS.md: removido `- [link/lien/enlace]` das 4 variantes

---

## [0.4.2.1] — 2026-06-23 — Ses_10a4: 3 correções

- **Tema CLARO:** Contraste corrigido nos 6 modais (`background:#181b1e` fixo → variável CSS `.modal-shell`)
- **Dashboard de Saúde:** `openHealth()` faz fetch em `/api/health` e popula lista com badges de status
- **Modal de Diretrizes:** Renderiza markdown (marked.js + github-markdown-css) ao invés de texto cru

---

## [0.4.2] — 2026-06-22 — Footer Responsivo + AGENTS.md Multilíngue

- Rodapé 100% responsivo (flex-wrap + 2 linhas)
- Modal de Diretrizes com AGENTS.md multilíngue
- Endpoint `GET /api/agents?lang=xx_XX`

---

## [0.4.1] — 2026-06-20 — UI Fixes (Responsivo + Tema + Idioma)

- 6 media queries + hamburger menu
- `toggleTheme()` recarrega iframe ttyd
- Dropdown 4 idiomas (pt_BR, en_US, es_ES, fr_FR)

---

## [0.4.0] — 2026-06-15 — Release Inicial

Primeira release do PesquisAI com:
- Agente de pesquisa científica via OpenCode
- Integração IBGE, DataSUS, dados-brasil, agrobr
- Wrapper HTML com ttyd
- Backup/restore de sessões
- Gerenciamento de provedores de IA
- Tema escuro "pesquisai"
- Suporte a 4 idiomas
