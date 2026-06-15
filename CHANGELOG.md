# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [0.3.1] - 2026-06-14

### Limpeza

* **Código legado removido** (5 arquivos):
  - `run_fast.py` (substituído por `pesquisai/run.py`)
  - `launch_app.py` (substituído por `pesquisai/launch/`)
  - `opencode_utils.py` (substituído por `pesquisai/utils/opencode.py`)
  - `progress_bar.py` (substituído por `pesquisai/progress.py`)
  - `constants.py` (substituído por `pesquisai/config.py`)
* **`jokes.py` movido** da raiz para `pesquisai/jokes.py` (acesso via
  `from pesquisai.jokes import next_joke`).
* **Shims removidos**:
  - `pesquisai/constants_shim.py` (nunca foi importado)
* **Documentação órfã removida**:
  - `IntructionsCEO_paperclip.md` (documento de outro projeto)
  - `Disclaimer.md` (subsumido por `disclaimer_pesquisai.md`)
* **Caches removidos**: `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`,
  `.ruff_cache/` (cobertos por `.gitignore`).

### Validação

* **51 testes pytest continuam passando** após a limpeza.
* **Smoke test do entry point** (`main.py` → `pesquisai.run`) OK.
* **Notebook Colab** (`PesquisAI.ipynb`) continua válido — usa
  `from main import run` que delega ao pacote novo.

### Estrutura Final

```
PesquisAI/
├── main.py                          # 6 linhas
├── pyproject.toml
├── LICENSE
├── README.md, MANUAL.md, AGENTS.md, CHANGELOG.md
├── citacao_pesquisai.md, declaracao_uso_ia.md
├── disclaimer_pesquisai.md
├── PesquisAI.ipynb
├── .gitignore
├── pesquisai/                       # 14 módulos
│   ├── __init__.py
│   ├── config.py                    # Settings pydantic
│   ├── run.py                       # Orquestrador
│   ├── progress.py
│   ├── skills.py
│   ├── theme.py
│   ├── dependencies.py
│   ├── jokes.py                     # ← MOVIDO da raiz
│   ├── launch/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── templates/index.html.tmpl
│   │   └── static/{app.js, style.css}
│   └── utils/
│       ├── __init__.py
│       ├── security.py
│       ├── opencode.py
│       └── subprocess.py
├── tests/                           # 51 testes
│   ├── conftest.py
│   ├── test_jokes.py
│   ├── test_security.py
│   ├── test_server.py
│   └── test_subprocess.py
└── relatorios/                      # Análise + implementação
    ├── ANALISE_CODIGO.{md, pdf}
    └── IMPLEMENTACAO_RELATORIO.{md, pdf}
```

### Métricas

| | Antes (v0.3.0) | Depois (v0.3.1) |
|---|---|---|
| Arquivos `.py` na raiz | 6 (5 legados + jokes) | 1 (main.py) |
| Módulos `.py` totais | 20 | 19 |
| Linhas legadas | ~1.700 | 0 |
| Testes passando | 51 | 51 |

---

## [0.3.0] - 2026-06-14

### Segurança (CRÍTICO)

* **Validação de comandos** em `/api/run_terminal` — whitelist de binários
  (`opencode`, `export`, `true`, `false`, `echo`, `source`, `.`) com bloqueio
  de 11+ vetores de injeção (`;`, `&&`, `||`, `|`, `` ` ``, `$()`, `{}`, etc.).
* **Path traversal** em `/api/restore` — `safe_backup_path()` valida que
  o destino está dentro de `DRIVE_BACKUP_DIR` antes de qualquer operação.
* **Credenciais 0600** — `secure_write_json()` salva `.keys.json` com
  permissões `0o600` (legível apenas pelo dono).
* **XSS via `innerHTML`** — frontend agora usa `textContent` (DOM API) e
  construções de elementos via `document.createElement` em vez de
  concatenar strings com dados do usuário.
* **Race condition no cache** de `OPENCODE_BIN` — substituído por
  `functools.lru_cache` (thread-safe).
* **Timeout em `find` recursivo** — todos os subprocessos têm
  `timeout=5` ou `timeout=3`.
* **Logs de acesso HTTP** — antes silenciados completamente, agora
  registram apenas respostas 4xx/5xx.

### Refatoração Estrutural

* **Pacote `pesquisai/`** substitui os módulos monolíticos de raiz:
  - `pesquisai/config.py` — `Settings` pydantic 2 (frozen, validado)
  - `pesquisai/run.py` — orquestrador `setup_drive → setup_dependencies
    → setup_skills → setup_launch`
  - `pesquisai/progress.py` — barra de progresso tipada
  - `pesquisai/skills.py` — `Skill` dataclass + clone paralelo
  - `pesquisai/theme.py` — tema/agent/TUI configuration
  - `pesquisai/dependencies.py` — apt + pip installer centralizado
  - `pesquisai/launch/__init__.py` — `launch()` principal
  - `pesquisai/launch/server.py` — HTTP wrapper (12 rotas) com
    injeção de dependência via `make_handler(runner)`
  - `pesquisai/launch/templates/index.html.tmpl` — HTML em arquivo
  - `pesquisai/launch/static/style.css` — CSS extraído
  - `pesquisai/launch/static/app.js` — JS separado e XSS-safe
  - `pesquisai/utils/security.py` — `validate_command`,
    `safe_backup_path`, `secure_write_json`, `read_json`
  - `pesquisai/utils/opencode.py` — `find_opencode` (com `lru_cache`),
    `ensure_ttyd` centralizado
  - `pesquisai/utils/subprocess.py` — Protocol `CommandRunner` +
    `SubprocessRunner` + `FakeRunner` (injeção de dependência)

### Testes

* **Suite pytest com 43 testes, todos passando**:
  - `tests/test_security.py` (32 testes) — `validate_command` com
    11 vetores de injeção, `safe_backup_path` com 5 cenários,
    `secure_write_json` (verifica `0o600`), `read_json`,
    `escape_html`.
  - `tests/test_subprocess.py` (6 testes) — `FakeRunner`,
    `_clone_or_pull` (pull OK, pull falha → clone fallback),
    `list_installed`.
  - `tests/test_server.py` (5 testes) — health endpoint,
    validação de comandos em `/api/run_terminal`,
    path traversal em `/api/restore`.
* **Servidor de testes** com `urllib` real (porta efêmera) + patches
  em `_resolve_drive_base` para isolamento.
* **Cobertura de injeção** inclui 11+ padrões maliciosos parametrizados.

### Novas Features

* **Endpoint `GET /api/health`** — versão do opencode, status do Drive,
  uptime, contagem de skills instaladas.
* **Type hints em ~95%** das funções públicas (era ~10%).
* **Logging estruturado** com `logging.getLogger("pesquisai.*")` —
    cada módulo tem seu próprio logger.
* **`Pyproject.toml`** atualizado com `pydantic>=2.0` como dependência
  e `[dev]` extras (`pytest`, `pytest-cov`).
* **`pesquisai/__init__.py`** expõe `__version__ = "0.3.0"`.

### Bugs Corrigidos

* **Duplicação de `xsel`** em `run_fast.py:114` — removida.
* **`import re` local** em `launch_app.py:1041` — movido para o topo.
* **`subprocess.run(shell=True)`** com entrada do usuário — substituído
  por lista em rotas HTTP; shell string só em comandos hardcoded
  com quoting seguro.
* **Read de `.keys.json` com encoding** — agora explícito `encoding="utf-8"`.
* **`shutil.copy2` sem tratamento** — envolvido em `try/except` com
  log de warning.

### Compatibilidade

* **Código legado mantido** no diretório raiz para permitir rollback
  (`run_fast.py`, `launch_app.py`, `opencode_utils.py`,
  `progress_bar.py`, `constants.py`).
* **Para usar a nova versão**, basta `python main.py` (já aponta para
  `pesquisai.run.run`).
* **Para remover o legado** após validação:
  ```bash
  rm run_fast.py launch_app.py opencode_utils.py progress_bar.py constants.py
  ```

### Documentação

* **Análise de código** completa em `relatorios/ANALISE_CODIGO.md` (44 KB).
* **Relatório de implementação** em
  `relatorios/IMPLEMENTACAO_RELATORIO.md` (12 KB).
* **README.md** reescrito com nova arquitetura.
* **CHANGELOG.md** com entrada detalhada (esta).

### Métricas

| | v0.2 | v0.3 |
|---|---|---|
| Módulos `.py` na raiz | 7 | 1 (só `main.py`) |
| Módulos no pacote | 0 | 13 |
| Linhas em `launch_app.py` | 1.247 | quebrado em 4 arquivos |
| Funções de teste | 0 | 43 |
| Vulnerabilidades críticas | 5 | 0 |
| Bugs latentes | 7 | 0 |
| Type hints | ~10% | ~95% |

---

## [0.2] - 2026-06-10

### Otimizações de Performance
- Paralelismo: clonagem de skills com `ThreadPoolExecutor(max_workers=8)`, repositórios já em cache fazem `git pull --depth 1 --ff-only`
- Clones enxutos: `--single-branch --depth 1` em todos os repositórios
- Cache de binários: pula instalação de opencode, uv e ttyd se já existentes
- `apt-get update` executado uma única vez (antes em duas etapas separadas)
- `pip install --no-cache-dir`

### Reestruturação de Código
- `run_fast.py` — Novo orquestrador com paralelismo e cache, substitui o fluxo sequencial
- `progress_bar.py` — Barra de progresso para Colab e terminal
- `main.py` — Simplificado para `from run_fast import run`
- `setup_drive.py`, `setup_dependencies.py`, `setup_skills.py` — Removidos; código ingerido no `run_fast.py`
- `PesquisAI_Colab.ipynb` — Removido (consolidado no notebook principal)
- `.gitignore` — Criado

### Interface
- Barra de progresso com `display_id=True` e `clear_output(wait=True)` ao final
- Footer alterado para "UFV · Viçosa, MG - Brasil"
- `Ctrl+Shift+C` no ttyd para copiar; `Ctrl+C` mantém SIGINT
- `--client-option copyOnSelect=true` removido (não suportado pela versão do ttyd)

### Provedores
- Lista ordenada alfabeticamente
- Adicionados OpenCode Zen (`OPENCODE_ZEN_API_KEY`) e OpenCode Go (`OPENCODE_GO_API_KEY`)

### Registro SisPPG/UFV
- Badge SisPPG nº **10356285004** adicionado ao README
- Citações ABNT atualizadas com nº de registro em README, MANUAL, citacao_pesquisai, declaracao_uso_ia
- Rodapé do AGENTS.md com nº SisPPG
- URL SisPPG corrigida: `https` → `http://sisppg.ufv.br`
- PDF comprovante incluído

### Notebook
- Loading animado via `IPython.display`
- Repositório usa `git pull` se já existe (evita recriação a cada execução)
- `clear_output()` antes de executar
- Markdown simplificado e reorganizado

### Regras do Agente (AGENTS.md)
- Callup `[!CAUTION]` no topo com 3 regras absolutas: referências só via `citation-management`, não inventar dados, não simular coleta primária
- Seção `3.1 Sub-fluxo de Verificação de Referências` com regra de ouro e instrução de recusar pedidos do usuário
- Versão `1.0` → `0.2`

### Correções
- MANUAL.md — Numeração duplicada corrigida
- `load_keys_from_drive()` — Extraída para eliminar 3 ocorrências duplicadas
- Versão unificada para **0.2** em: README, AGENTS, MANUAL, pyproject.toml, launch_app, citação, declaração, disclaimer, notebooks

### Arquivos Novos
- `run_fast.py`
- `CHANGELOG.md`
- `progress_bar.py`
- `.gitignore`
- `SisPPG - Sistema de Pesquisa e Pós-Graduação.pdf`

### Arquivos Removidos
- `setup_drive.py`
- `setup_dependencies.py`
- `setup_skills.py`
- `PesquisAI_Colab.ipynb`

---

## v0.1 (2026-05-31)

### Funções Iniciais
- **setup_drive.py** — Montagem do Google Drive, autenticação Google API, criação do diretório de trabalho
- **setup_dependencies.py** — Instalação do opencode (curl/pip/npm), uv, xclip/xsel, tema e agente
- **setup_skills.py** — Clonagem sequencial de 8 skills (ibge, datasus, scientific, pesquisai, ufv-abnt, qualitativa, dados-brasil, agrobr)
- **launch_app.py** — Instalação do ttyd, servidor web wrapper com backup/restore de sessão e gerenciamento de provedores de IA
- **main.py** — Orquestrador chamando drive → dependências → skills → launch
- **constants.py** — Constantes de caminhos e configuração
- **opencode_utils.py** — Busca do binário opencode e construção de environment
- **jokes.py** — Piadas temáticas exibidas durante o loading
- **PesquisAI.ipynb** e **PesquisAI_Colab.ipynb** — Notebooks Colab
- **pyproject.toml** — Projeto versão 1.0
- Documentação: README, AGENTS.md, MANUAL.md, citacao_pesquisai.md, declaracao_uso_ia.md, disclaimer_pesquisai.md, Disclaimer.md, IntructionsCEO_paperclip.md

### Estado Inicial
- Fluxo sequencial de inicialização (sem paralelismo)
- Numeração duplicada no MANUAL.md
- Código duplicado de carregamento de chaves em 3 locais
- Sem barra de progresso
- Sem `.gitignore`
- Versões inconsistentes (1.0 no pyproject, 1.0 no README, 0.01 no AGENTS.md)
- Sem registro SisPPG
