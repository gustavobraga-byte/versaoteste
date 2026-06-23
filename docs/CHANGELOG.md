# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.4.1] — 2026-06-23 — UI Fixes (Responsive + Theme + Language)

### 🏗️ Reorganização da Estrutura (2026-06-23)
- **Estrutura do repositório reformatada** para separar código do PesquisAI de
  arquivos pessoais (sandbox):
  - `docs/` — toda documentação (CHANGELOG, PATCH, MOBILE, INTEGRITY)
  - `releases/v0.4.0/` — release isolada completa (com pyproject.toml, LICENSE, CI, etc.)
  - `sandbox/` — artigos, projetos, datasets, figuras, TCCs, scripts, utils (138MB)
  - `sessions/` — logs de sessão
  - Raiz reduzida de 145MB para ~7MB (apenas código PesquisAI)
- **README.md** criado na raiz explicando a nova estrutura
- **`__version__.py`** atualizado com `__default_theme__ = "pesquisai"` (escuro)

### 🌙 Tema Padrão: ESCURO (anti-flash)
- **Script anti-flash no `<head>`** executa ANTES do CSS, lendo cookie/localStorage
  e aplicando tema escuro como padrão (só troca para claro se persistido)
- **CSS `html { background: #0d0f10; color: #e8e6e0; }` inline** garante que o
  body já inicia com fundo escuro (sem flash branco no carregamento)
- **Classe `html.theme-light`** no CSS para override do tema claro
- **`<html data-theme="pesquisai">`** explícito como padrão
- **Sincronização em `applyWrapperTheme()`** que adiciona/remove a classe
  `.theme-light` no `<html>` para que o CSS use as variáveis corretas

### 🐛 Bug Fixes Críticos (reportados pelo usuário em 2026-06-23)

### 🐛 Bug Fixes Críticos (reportados pelo usuário em 2026-06-23)

#### 📱 1. Site NÃO estava responsivo
- **Problema:** o `launch_app.py` do PesquisAI principal no GitHub não tinha
  media queries. Topbar de 8 botões estourava em mobile, modais 400-520px não
  cabiam, sem hamburger menu.
- **Correção:** adicionadas 6 media queries (5 breakpoints + landscape) com
  hamburger drawer, modais fluidos (95vw em mobile), touch targets ≥ 32-44px
  (Apple HIG / WCAG 2.5.5), hamburger mobile menu com todos os itens da
  topbar reorganizados.

#### 🎨 2. Tema claro/escuro NÃO recarregava o terminal
- **Problema:** `toggleTheme()` chamava `applyWrapperTheme()` que só mudava
  as CSS variables do wrapper, mas NUNCA recarregava o iframe do ttyd.
  Resultado: a UI mudava, mas o terminal continuava com o tema antigo.
- **Correção:** após aplicar o tema na UI, recarrega o iframe do ttyd
  com cache-busting (`?theme=pesquisai-light&t=<timestamp>`), mesmo padrão
  usado em `confirmProvider()` / `restoreSession()` / `doRestore()`. Tempo
  de reload: 3.5s (aguarda restart do ttyd no backend).

#### 🌐 3. Idioma sem opção na interface
- **Problema:** o módulo `i18n` estava completo (4 idiomas, JSONs), mas
  não havia seletor visível na topbar. Usuário não tinha como trocar idioma.
- **Correção:** adicionado dropdown na topbar com 4 idiomas (🇧🇷 PT, 🇺🇸 EN,
  🇪🇸 ES, 🇫🇷 FR), persistência em cookie `pesquisai_lang` + localStorage,
  query param `?lang=xx_XX` para forçar via URL, atualização do atributo
  `<html lang="xx-XX">` e de todas as strings visíveis via `data-i18n`.

### 🆕 Funcionalidades Adicionais

- **Cookie helpers** (`setCookie` / `getCookie`) para tema e idioma
- **Detecção automática de idioma** com prioridade: URL > cookie > localStorage > `navigator.language` > padrão
- **Indicador visual do tema ativo** no botão (`#theme-toggle[data-theme="pesquisai-light"]` → cor amber)
- **Meta `theme-color` dinâmica** (muda junto com o tema para a barra de status do navegador mobile)
- **40+ strings traduzidas inline** no client-side para feedback instantâneo
- **Endpoint backend opcional** `GET/POST /api/lang` para persistir idioma no Drive
- **Click-outside** para fechar dropdown de idioma
- **Tecla `Escape`** fecha também o dropdown de idioma e o mobile menu

### 📁 Arquivos Novos

- `pesquisai/launch_app_responsive_v041.py` — **drop-in patch** para o `launch_app.py` do GitHub
- `docs/PATCH_v0.4.1.md` — documentação completa do patch (instalação + testes)
- `i18n/translations/fr_FR.json` — 🇫🇷 francês (NOVO em v0.4.0, expandido em v0.4.1)

### 🔄 Arquivos Atualizados

- `pesquisai/launch_app_responsive.py` — agora contém as 3 correções (era v0.1.0 → v0.2.0)
- `__version__.py` — `0.4.0` → `0.4.1`, codinome "UI Fixes (Responsive + Theme + Language)"

### 🔒 Compatibilidade

- ✅ **Backward compatible** — sem breaking changes
- ✅ **API inalterada** — `create_wrapper_html(terminal_url, drive_url)` mantém a assinatura
- ✅ **CSS puro** — sem dependências externas adicionais
- ✅ **Fallback gracioso** — se JS do hamburger falhar, topbar original ainda funciona

### 🧪 Validação

- 79 testes continuam passando (48 grant_finder + 31 i18n) — 100% das suítes verdes
- HTML gerado tem **60.582 caracteres** (vs. ~38.000 do v0.4.0) — todas as correções injetadas
- 26 validações automáticas aprovadas (mobile menu, lang selector, toggleTheme reload, JSON válido, etc.)

---

## [0.4.0] — 2026-06-23 — International & Mobile

### 🎉 Funcionalidades Principais

#### 📱 Site Responsivo Mobile
- **`pesquisai/launch_app_responsive.py`** — Wrapper HTML adaptativo substitui layout estático
- **5 breakpoints:** mobile pequeno (< 480px), mobile (480-767px), tablet (768-1023px), tablet portrait, desktop (≥ 1024px), landscape
- **Hamburger menu drawer** lateral em mobile (280px / 85vw)
- **Modais fluidos** (95vw em mobile, até 600px em tablet)
- **Touch targets ≥ 32-44px** (Apple HIG / WCAG 2.5.5)
- **Acessibilidade:** `aria-label`, `aria-hidden`, foco visível, `Escape` para fechar
- **Meta tags:** `viewport-fit=cover`, `theme-color`, `-webkit-tap-highlight-color`

#### 🔍 Skill grant_finder (Nova)
- **13 agências** integradas:
  - **Brasil (8):** CNPq, CAPES, FAPEMIG, FAPESP, FINEP, FAPERJ, FAPERGS, BNDES
  - **Internacional (5):** NIH, NSF, ERC, Wellcome, Horizon Europe
- **5 funções públicas:** `search_grants`, `check_eligibility`, `generate_budget`, `draft_proposal`, `make_timeline`
- **4 dataclasses:** `ResearcherProfile`, `Grant`, `EligibilityReport`, `Budget`
- **Cache local** com TTL de 24h e `fetched_at` explícito
- **Verificação de elegibilidade** com score 0-1, razões, avisos e ações
- **Geração de orçamento** estruturado por rubricas (custeio, capital, bolsas)
- **Minutas de proposta** em PT e EN com seções padrão (IMRaD)
- **48 testes passando** em 3 suítes (test_matcher, test_budget, test_proposal)

#### 🌐 Suporte Multilíngue (i18n)
- **4 idiomas:** 🇧🇷 pt_BR, 🇺🇸 en_US, 🇪🇸 es_ES, 🇫🇷 fr_FR
- **Detecção automática** via variável `PESQUISAI_LANG`, `LANG`, `LC_ALL`, `Accept-Language`
- **API limpa:** `t("chave.subchave")` com fallback automático
- **Sistema de interpolação** com `{variavel}`
- **Quality-based selection** de `Accept-Language` (q=0.9, q=0.8…)
- **CLI helper:** `set_language()`, `get_language()`, `detect()`, `t_for()`, `available_languages()`
- **31 testes passando** em 5 categorias

#### 🤖 Agents Multilíngues
- `agents/AGENTS.pt.md` — 🇧🇷 Português (Brasil) — padrão
- `agents/AGENTS.en.md` — 🇺🇸 English (United States)
- `agents/AGENTS.es.md` — 🇪🇸 Español (España)
- `agents/AGENTS.fr.md` — 🇫🇷 Français (France) — **NOVO**
- 100% das regras de integridade científica preservadas em todas as variantes
- Marcadores de evidência traduzidos (`[DADO CONFIRMADO]` / `[CONFIRMED DATA]` / `[DATO CONFIRMADO]` / `[DONNÉE CONFIRMÉE]`)

### 🧪 Qualidade de Código

- **79 testes passando** (48 grant_finder + 31 i18n) — 100% das suítes verdes
- Cobertura estimada > 85% nos módulos novos
- Type hints em todas as funções públicas
- Docstrings em todas as classes e funções
- 4 suítes pytest: test_matcher, test_budget, test_proposal, test_translator
- Testes de edge cases: cache corrompido, JSON truncado, normalização de locale, encoding UTF-8

### 🔒 Segurança e Integridade Científica

- **Política de zero-fabricação** mantida em todos os novos módulos
- `grant_finder`: sempre declara `fetched_at` e link oficial para conferência
- Marcador `[SEM DADOS SUFICIENTES]` / `[NO DATA AVAILABLE]` / `[SIN DATOS SUFICIENTES]` / `[DONNÉES INSUFFISANTES]`
- Aviso explícito: "SEMPRE conferir link oficial antes de submeter proposta"

### 📦 Estrutura do Release

```
pesquisai-v0.4.0/
├── README.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── CHANGELOG.md
├── __version__.py
├── agents/
│   ├── AGENTS.pt.md
│   ├── AGENTS.en.md
│   ├── AGENTS.es.md
│   └── AGENTS.fr.md  ← NOVO
├── grant_finder/
│   ├── matcher.py
│   ├── budget.py
│   ├── proposal.py
│   ├── sources/ (6 conectores)
│   ├── data/ (5 caches JSON)
│   └── tests/ (48 testes)
├── i18n/
│   ├── translator.py
│   ├── detector.py
│   ├── translations/ (4 idiomas)
│   └── tests/ (31 testes)
├── pesquisai/
│   └── launch_app_responsive.py  ← NOVO
└── docs/
    ├── MOBILE_RESPONSIVE_PATCH.md
    └── ENTREGAS_JUNHO_2026.md
```

### 📊 Estatísticas

| Métrica | Valor |
|---|---|
| Arquivos criados | 53 |
| Linhas de código Python | ~2.800 |
| Linhas de documentação | ~1.500 |
| Linhas de JSON (translations + cache) | ~800 |
| Funções públicas | 30+ |
| Classes (dataclasses) | 14 |
| Agências de fomento | 13 |
| Idiomas | 4 |
| Testes | 79 |
| Cobertura estimada | >85% |

---

## [0.3.0] — 2026-06-20 — (Reservado / Não publicado)

Versão reservada para próximos desenvolvimentos.

---

## [0.2.3] — 2026-06-18 — Backup Integrity Fix

### 🐛 Bug Crítico
- **Backups quebrados (corrupção intermitente)**: Google Drive FUSE trunca escrita em limites de buffer interno. `launch_app.py /api/backup` agora valida JSON antes e depois de copiar para o Drive, com `os.fsync()` + `os.sync()` + backoff exponencial + lock de arquivo (`fcntl.flock`)
- **`launch_app.py /api/restore`**: valida JSON ANTES de copiar para `/tmp/`
- 4 novos testes em `TestBackupIntegrity` (JSON válido, truncamento 64KB, 256KB, fcntl)
- **192 testes** no PesquisAI principal

---

## [0.2.2] — 2026-06-18 — Stable Base Integration

- 188 testes no PesquisAI principal (cobertura 29% → 57%)
- 3.2 Dashboard de Saúde (`GET /api/health`)
- 3.3 Busca/Histórico de Sessões (`/api/sessions`)
- 3.6 Atalhos de Teclado Visíveis
- 3.8 Tema Claro (acessibilidade)
- Integração com base estável v0.2

---

## [0.2.1] — 2026-06-16 — Secure Keys

- Módulo `security.py` com criptografia AES-128-CBC + HMAC-SHA256 (Fernet)
- Sanitização de comandos (whitelist + bloqueio de injection)
- `save_encrypted_keys()` / `load_encrypted_keys()` com defesa em profundidade
- `__version__.py` como fonte única de versão
- 18 testes de segurança
- CI/CD com Ruff + Mypy + pytest em 3 Python versions

---

## [0.2] — 2026-06-10 — Otimizações de Performance

- Skills clonadas em paralelo com `ThreadPoolExecutor(max_workers=8)`
- Cache de repositórios: `git pull --depth 1` se já existir
- `--single-branch --depth 1` em todos os clones
- Detecção de binários existentes (opencode, uv, ttyd)
- `apt-get update` único (antes rodava em 2 etapas)
- `pip install` com `--no-cache-dir`

---

## [0.001] — 2026-06-10 — Release Inicial

- `setup_drive.py` — Montagem do Google Drive
- `setup_dependencies.py` — Instalação do opencode
- `setup_skills.py` — Clonagem sequencial de 8 skills
- `launch_app.py` — ttyd + servidor wrapper
- `main.py` — Orquestrador

---

## Tipos de Mudanças

- `🎉 Funcionalidades Principais` — Para novas funcionalidades
- `📱` — Para mudanças de UI/UX
- `🐛 Bug Crítico` — Para correções de bug crítico
- `🧪 Qualidade de Código` — Para mudanças que não afetam o comportamento
- `🔒 Segurança` — Para mudanças relacionadas a vulnerabilidades
- `📦 Estrutura` — Para mudanças em arquivos de build/dependências
- `📚 Documentação` — Para mudanças apenas em documentação
- `⚡ Performance` — Para mudanças de performance

---

[0.4.0]: https://github.com/gustavobraga-byte/PesquisAI/releases/tag/v0.4.0
[0.3.0]: https://github.com/gustavobraga-byte/PesquisAI/releases/tag/v0.3.0
[0.2.3]: https://github.com/gustavobraga-byte/PesquisAI/releases/tag/v0.2.3
[0.2.2]: https://github.com/gustavobraga-byte/PesquisAI/releases/tag/v0.2.2
[0.2.1]: https://github.com/gustavobraga-byte/PesquisAI/releases/tag/v0.2.1
[0.2]: https://github.com/gustavobraga-byte/PesquisAI/releases/tag/v0.2
[0.001]: https://github.com/gustavobraga-byte/PesquisAI/releases/tag/v0.001
