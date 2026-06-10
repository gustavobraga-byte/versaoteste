# Changelog

## v0.2 (2026-06-10)

### Otimizações de Performance
- Clonagem de skills paralelizada com `ThreadPoolExecutor(max_workers=8)` — 8 repositórios clonados simultaneamente
- Cache de repositórios: skills já em `/tmp/` fazem `git pull --depth 1 --ff-only` em vez de clonar do zero
- `--single-branch --depth 1` em todos os clones (baixa só o branch padrão)
- Detecção de binários existentes: pula opencode, uv, ttyd se já instalados
- `apt-get update` executado uma única vez (antes rodava em duas etapas separadas)
- `pip install` com `--no-cache-dir` para evitar overhead de cache
- `_check_bin()` aprimorado: busca também em `~/.local/bin`, `~/.npm-global/bin`, `~/.opencode/bin`

### Correções
- **Item 2** — Versão do AGENTS.md corrigida de `v0.01` para `v0.2`
- **Item 4** — `.gitignore` criado com `__pycache__/`, `*.pyc`, `*.pyo`, etc.
- **Item 6** — Numeração duplicada no MANUAL.md corrigida (seção `## 1. Primeiros Passos` removida; seções 1–10 renumeradas)
- **Item 7** — Lógica de carregamento de chaves extraída para `load_keys_from_drive()`, eliminando 3 ocorrências duplicadas

### Interface
- **Item 30** — Barra de progresso com `display_id=True` (sem acumular HTML)
- `clear_output(wait=True)` ao final para limpar textos de setup, restando apenas o botão de launch
- `show_ready_message()` e `show_launch_button()` reexibidos após limpeza
- `copyOnSelect=true` no ttyd — selecionar texto com mouse copia automaticamente
- `Ctrl+Shift+C` para copiar (atalho padrão do ttyd, funciona no Chrome)
- `Ctrl+C` mantém SIGINT (interromper comandos)

### Arquivos Novos
- `run_fast.py` — Versão otimizada com paralelismo e cache, substitui o fluxo do `main.py`
- `CHANGELOG.md` — Este arquivo

### Alterações em Arquivos Existentes
- `AGENTS.md` — Versão `v0.01` → `v0.2`
- `.gitignore` — Criado
- `MANUAL.md` — Numeração corrigida
- `launch_app.py` — Função `load_keys_from_drive()` extraída
- `progress_bar.py` — `finish()` com `clear_output(wait=True)`
- `main.py` — Simplificado para delegar a `run_fast.py`

## v0.001 (2026-06-10)

### Funções Iniciais
- **setup_drive.py** — Montagem do Google Drive, autenticação Google API, criação do diretório de trabalho
- **setup_dependencies.py** — Instalação do opencode (curl/pip/npm), uv, xclip/xsel, tema e agente
- **setup_skills.py** — Clonagem sequencial de 8 skills (ibge, datasus, scientific, pesquisai, ufv-abnt, qualitativa, dados-brasil, agrobr)
- **launch_app.py** — Instalação do ttyd, servidor web wrapper com backup/restore de sessão e gerenciamento de provedores de IA
- **main.py** — Orquestrador chamando drive → dependências → skills → launch
- **constants.py** — Constantes de caminhos e configuração
- **opencode_utils.py** — Busca do binário opencode e construção de environment
- **jokes.py** — Piagens temáticas exibidas durante o loading
- **PesquisAI.ipynb** — Notebook Colab principal
- Fluxo sequencial de inicialização (sem paralelismo)
- Numeração duplicada no MANUAL.md
- Código duplicado de carregamento de chaves em 3 locais
- Sem barra de progresso
- Sem `.gitignore`
