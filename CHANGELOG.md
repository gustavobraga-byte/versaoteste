# Changelog

## v0.2.1 (2026-06-15) — Melhorias de Qualidade de Código

### Correções de Bugs
- **`constants.py`**: Versão unificada para `VERSION = "0.2"` (estava `"1.0"` — inconsistente com o resto do projeto)
- **`progress_bar.py`**: Correção do bug na declaração de `IN_COLAB` — agora a variável é corretamente detectada via import do IPython

### Qualidade de Código
- **`pyproject.toml`**: Build backend modernizado para `hatchling` (substitui `setuptools.backends._legacy`)
- **Type hints**: Adicionados em `constants.py`, `opencode_utils.py`, `progress_bar.py`, `run_fast.py` e funções principais de `launch_app.py`
- **Configuração Ruff**: Linter e formatador configurados no `pyproject.toml`
- **Configuração Mypy**: Type checker configurado para validação opcional

### CI/CD
- **`.github/workflows/ci.yml`**: Pipeline de integração contínua com 3 jobs:
  - Lint (Ruff) + Format check + Type check (Mypy)
  - Testes (pytest + coverage) em Python 3.10, 3.11, 3.12
  - Gate de qualidade: testes só rodam se lint passar

### Testes
- **`tests/`**: Estrutura de testes com pytest criada (3 suites iniciais):
  - `test_constants.py` — 12 testes: versão, autor, skills, portas, consistência pyproject.toml
  - `test_jokes.py` — 9 testes: categorias, rotação, fallback, 10 piadas por categoria
  - `test_progress_bar.py` — 7 testes: HTML, estágios, cores, edge cases
  - `test_opencode_utils.py` — 3 testes: candidatos, busca, fallback

### Arquitetura
- **`constants.py`**: Skills centralizadas em `SKILL_REGISTRY` com flag `requerida` para fallback inteligente
- **`constants.py`**: `ESSENTIAL_SKILLS` como conjunto derivado para validação
- **`run_fast.py`**: Importa `SKILL_REGISTRY` e `ESSENTIAL_SKILLS` de `constants.py` (antes estava hardcoded)

### Segurança
- **`SECURITY.md`**: Política de segurança, reporte de vulnerabilidades e boas práticas

### Deploy
- **`Dockerfile`**: Imagem Docker para execução local (fora do Colab)

### Infraestrutura
- **`.gitignore`**: Aprimorado com entradas para Python, IDE, OpenCode, Colab, cache
- **`pyproject.toml`**: Seções `[project.optional-dependencies]` para `dev` e `test`

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
- `Ctrl+Shift+C` no ttyd para copiar (atalho padrão, funciona no Chrome)
- `Ctrl+C` mantém SIGINT (interromper comandos)
- Footer alterado para "UFV · Viçosa, MG - Brasil"

### Provedores
- Lista de provedores ordenada alfabeticamente
- Adicionados **OpenCode Zen** (`OPENCODE_ZEN_API_KEY`) e **OpenCode Go** (`OPENCODE_GO_API_KEY`)

### Registro SisPPG/UFV
- Badge SisPPG com nº **10356285004** adicionado ao README
- Citações ABNT atualizadas com nº de registro em README, MANUAL, citacao_pesquisai, declaracao_uso_ia
- Rodapé do AGENTS.md com nº SisPPG
- Notebooks atualizados com citação e badge
- URL corrigida: `https://www.sisppg.ufv.br` → `http://sisppg.ufv.br`

### Notebook
- Loading animado via `IPython.display`
- Repositório usa `git pull` se já existe (não recria toda execução)
- `clear_output()` antes de rodar (interface mais limpa)
- Markdown simplificado e reorganizado

### Arquivos Novos
- `run_fast.py` — Versão otimizada com paralelismo e cache, substitui o fluxo do `main.py`
- `CHANGELOG.md` — Este arquivo
- `SisPPG - Sistema de Pesquisa e Pós-Graduação.pdf` — Comprovante de registro

### Integridade de Referências
- AGENTS.md — Nova seção `3.1 Sub-fluxo de Verificação de Referências` com 4 subpassos (rastreamento, confirmação de 3 campos, link/DOI obrigatório, inclusão) e regra de ouro contra fabricação
- `run_fast.py` — Descrição do agente atualizada para incluir "verificação obrigatória de referências"

### Alterações em Arquivos Existentes
- `AGENTS.md` — Versão `v0.01` → `v0.2`; seção 3.1 adicionada
- `.gitignore` — Criado
- `MANUAL.md` — Numeração corrigida + citações com SisPPG
- `launch_app.py` — Função `load_keys_from_drive()` extraída; provedores ordenados + Zen/Go
- `progress_bar.py` — `finish()` com `clear_output(wait=True)`
- `main.py` — Simplificado para delegar a `run_fast.py`
- `README.md` — Badge SisPPG + citação atualizada
- `citacao_pesquisai.md` — Citação com SisPPG
- `declaracao_uso_ia.md` — Citação com SisPPG
- `PesquisAI.ipynb` — Loading animado, git pull, markdown simplificado
- `PesquisAI_Colab.ipynb` — Badge SisPPG

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
