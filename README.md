# 🔬 PesquisAI

> **Versão:** 0.4.1 (UI Fixes — Responsive + Theme + Language)
> **Data:** 2026-06-23
> **Status:** ✅ Pronto para deploy
> **Tema padrão:** 🌙 **Escuro** (com anti-flash CSS)

Agente de IA para pesquisadores, executado em ttyd (terminal) + OpenCode + 8+ skills científicas.

---

## 📂 Estrutura do Repositório

```
PesquisAI/
│
├── README.md                          ⭐ Este arquivo
├── __version__.py                     # 0.4.1
│
├── 🔬 pesquisai/                      # Módulo principal do PesquisAI
│   ├── launch_app_responsive.py       # ✅ v0.4.1 (responsivo + tema + idioma)
│   └── launch_app_responsive_v041.py  # ✅ Drop-in patch para launch_app.py do GitHub
│
├── 🤖 agents/                         # AGENTS.md multilíngues
│   ├── AGENTS.pt.md                   🇧🇷
│   ├── AGENTS.en.md                   🇺🇸
│   ├── AGENTS.es.md                   🇪🇸
│   └── AGENTS.fr.md                   🇫🇷
│
├── 🌐 i18n/                           # Módulo multilíngue (4 idiomas)
│   ├── __init__.py
│   ├── translator.py
│   ├── detector.py
│   └── translations/
│       ├── pt_BR.json
│       ├── en_US.json
│       ├── es_ES.json
│       └── fr_FR.json
│
├── 🔍 grant_finder/                   # Skill de busca de fomento (13 agências)
│   ├── matcher.py · budget.py · proposal.py
│   ├── sources/  (CNPq, CAPES, FAPEMIG, FAPESP, FINEP, NIH, NSF, ERC, Wellcome, Horizon)
│   ├── data/     (5 caches JSON)
│   └── tests/    (48 testes ✅)
│
├── 🛠️ skills/                        # Skills adicionais
│   └── meta-search-br/                # Busca meta em fontes BR
│
├── 📚 docs/                           # Documentação completa
│   ├── CHANGELOG.md                   # Histórico de versões (v0.001 → v0.4.1)
│   ├── PATCH_v0.4.1.md                # 🐛 3 correções críticas
│   ├── MOBILE_RESPONSIVE_PATCH.md     # Patch mobile/tablet (v0.4.0)
│   ├── ENTREGAS_JUNHO_2026.md         # Resumo das entregas
│   ├── INTEGRITY.md                   # Política de integridade científica
│   ├── gerar_pdf.py                   # Utilitário: Markdown → PDF
│   └── *.pdf                          # Versões PDF dos .md acima
│
├── 📦 releases/                       # Releases completas (isoladas)
│   └── v0.4.0/                        # Release v0.4.0/1 (52 arquivos, 79 testes)
│       ├── README.md
│       ├── pyproject.toml
│       ├── LICENSE
│       ├── __version__.py
│       ├── CHANGELOG.md
│       ├── RELEASE_SUMMARY.md         # Resumo do release
│       ├── RELEASE_SUMMARY.pdf
│       ├── PATCH_v0.4.1.md            # (versão completa dentro do release)
│       ├── PATCH_v0.4.1.pdf
│       ├── ENTREGAS_JUNHO_2026.md
│       ├── ENTREGAS_JUNHO_2026.pdf
│       ├── MOBILE_RESPONSIVE_PATCH.md
│       ├── conftest.py
│       ├── .github/workflows/ci.yml
│       ├── agents/  (4 AGENTS.md)
│       ├── grant_finder/
│       ├── i18n/
│       ├── docs/  (PATCH_v0.4.1, etc.)
│       └── pesquisai/
│
├── 💾 backups/                        # Backups automáticos do sistema
│   └── *.json                         # Snapshots de sessão
│
├── 📜 sessions/                       # Logs de sessão do PesquisAI
│   ├── session-ses_10b7.md
│   └── session-ses_127f.md
│
└── 🗂️ sandbox/                        # 🏖️ Sandbox pessoal (não-PesquisAI)
    ├── artigos/                       # Artigos publicados, TCCs
    ├── projetos/                      # Projetos de pesquisa (10+)
    ├── figuras/                       # Figuras geradas
    ├── documentos/                    # Documentos auxiliares
    ├── dados/                         # Datasets
    ├── douglas/                       # Arquivos de alunos
    ├── scripts/                       # Scripts auxiliares
    ├── utils/                         # Utilitários
    ├── configuracao/                  # Configs de ambiente
    └── node_modules/                  # Dependências npm (histórico)
```

---

## 🚀 Quick Start

### 1. Usar o PesquisAI localmente

```bash
# Clone o repositório principal
git clone https://github.com/gustavobraga-byte/PesquisAI.git
cd PesquisAI

# Use o wrapper responsivo (v0.4.1)
python -m pesquisai.main
```

### 2. Aplicar o patch v0.4.1 em um PesquisAI existente

```bash
# Copie o patch para o PesquisAI
cp pesquisai/launch_app_responsive_v041.py \
   /caminho/pesquisai-existente/pesquisai/

# Edite o launch_app.py existente
# Substitua a definição de create_wrapper_html por:
#   from .launch_app_responsive_v041 import create_wrapper_html
```

### 3. Gerar uma release standalone

```bash
cd releases/v0.4.0
zip -r ../pesquisai-v0.4.1.zip .
```

---

## 🐛 Correções v0.4.1 (2026-06-23)

Bugs reportados pelo usuário no chat `session-ses_10b7.md`:

| # | Bug | Solução | Detalhes |
|---|-----|---------|----------|
| 1 | Site não responsivo | 6 media queries + hamburger | `docs/PATCH_v0.4.1.md` §1 |
| 2 | Tema não recarrega terminal | `toggleTheme()` recarrega iframe do ttyd | `docs/PATCH_v0.4.1.md` §2 |
| 3 | Idioma sem opção na UI | Dropdown 4 idiomas + cookie | `docs/PATCH_v0.4.1.md` §3 |

**Tema padrão:** 🌙 **Escuro** (com anti-flash CSS para evitar flash branco no load).

---

## 🧪 Testes

```bash
cd releases/v0.4.0
python3 -m pytest grant_finder/tests/ i18n/tests/

# Resultado: 79 passed (100% verdes) · 83% cobertura
```

---

## 📊 Estatísticas

| Métrica | Valor |
|---------|-------|
| Versão | 0.4.1 |
| Idiomas | 4 (pt_BR, en_US, es_ES, fr_FR) |
| Agências de fomento | 13 (BR + internacional) |
| Testes | 79 (100% verdes) |
| Cobertura | 83% |
| Media queries | 6 (5 breakpoints + landscape) |
| Strings traduzidas inline | 40+ |

---

## 🔗 Links

- **Repositório:** https://github.com/gustavobraga-byte/PesquisAI
- **Documentação completa:** `docs/`
- **Release notes:** `docs/CHANGELOG.md`
- **OpenCode:** https://opencode.ai

---

## ✍️ Autoria

**Gustavo Bastos Braga** — Universidade Federal de Viçosa (UFV)
**Email:** gustavo.braga@ufv.br
**SisPPG/UFV:** 10356285004
**Licença:** MIT

---

**Última atualização:** 2026-06-23 (v0.4.1)
