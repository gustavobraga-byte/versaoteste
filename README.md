# 🔬 PesquisAI

> **Versão:** 0.4.2.2 (ses_10a4+ polish: footer PC + skills + sessions + lang + version)
> **Data:** 2026-06-24
> **Status:** ✅ Pronto para deploy
> **Tema padrão:** 🌙 **Escuro** (com anti-flash CSS)

Agente de IA para pesquisadores, executado em ttyd (terminal) + OpenCode + 10+ skills científicas.

---

## 📂 Estrutura do Repositório

```
PesquisAI/
│
├── README.md                          ⭐ Este arquivo
├── pyproject.toml                     # Configuração do projeto
├── LICENSE                            # MIT
│
├── 🔬 pesquisai/                      # Módulo principal do PesquisAI (v0.4.2.2)
│   ├── __version__.py                 # ⭐ Fonte única da versão (v0.4.2.2)
│   ├── launch_app_responsive.py       # ✅ v0.4.2.1 (responsivo + tema + idioma + rodapé + AGENTS + markdown)
│   └── launch_app_responsive_v041.py  # ✅ Drop-in patch para launch_app.py do GitHub (v0.4.2.2)
│
├── 🤖 agents/                         # AGENTS.md multilíngues (4 idiomas)
│   ├── AGENTS.pt.md                   🇧🇷 (padrão)
│   ├── AGENTS.en.md                   🇺🇸
│   ├── AGENTS.es.md                   🇪🇸
│   ├── AGENTS.fr.md                   🇫🇷
│   └── README.md
│
├── 🌐 i18n/                           # Módulo multilíngue (4 idiomas, 31 testes)
│   ├── __init__.py
│   ├── translator.py
│   ├── detector.py
│   └── translations/
│       ├── pt_BR.json
│       ├── en_US.json
│       ├── es_ES.json
│       └── fr_FR.json
│
├── 🔍 grant_finder/                   # Skill de busca de fomento (13 agências, 48 testes)
│   ├── matcher.py · budget.py · proposal.py
│   ├── sources/  (CNPq, CAPES, FAPEMIG, FAPESP, FINEP, NIH, NSF, ERC, Wellcome, Horizon)
│   ├── data/     (5 caches JSON)
│   └── tests/    (48 testes ✅)
│
├── 🛠️ skills/                        # Skills adicionais (organizadas em skills/)
│   ├── grant-finder/                  # ⭐ v0.4.2.2: clone link + README + SKILL
│   │   ├── README.md
│   │   ├── SKILL.md
│   │   └── __init__.py
│   └── meta-search-br/                # Busca unificada em 7 bases acadêmicas
│       ├── README.md                  # ⭐ v0.4.2.2: novo
│       ├── SKILL.md                   # ⭐ v0.4.2.2: clone URL
│       ├── __init__.py
│       ├── meta_search.py
│       ├── sources.py
│       └── tests/    (40 testes ✅)
│
├── 📚 docs/                           # Documentação completa
│   ├── CHANGELOG.md                   # ⭐ v0.4.2.2: +6 entradas
│   ├── CHANGELOG.pdf                  # ⭐ v0.4.2.2: regenerado
│   ├── ENTREGAS_JUNHO_2026.md         # Resumo das entregas
│   ├── INTEGRITY.md                   # Política de integridade científica
│   ├── MOBILE_RESPONSIVE_PATCH.md     # Patch mobile/tablet (v0.4.0)
│   └── gerar_pdf.py                   # Utilitário: Markdown → PDF
│
├── 🔄 .github/workflows/ci.yml        # CI/CD
└── .gitignore
```

---

## 🚀 Quick Start

### 1. Usar o PesquisAI localmente

```bash
# Clone o repositório principal
git clone https://github.com/gustavobraga-byte/PesquisAI.git
cd PesquisAI

# Use o wrapper responsivo (v0.4.2.2)
python -m pesquisai.main
```

### 2. Aplicar o patch v0.4.2.2 em um PesquisAI existente

```bash
# Copie o patch para o PesquisAI
cp pesquisai/launch_app_responsive_v041.py \
   /caminho/pesquisai-existente/pesquisai/
cp pesquisai/__version__.py \
   /caminho/pesquisai-existente/pesquisai/

# Edite o launch_app.py existente
# Substitua a definição de create_wrapper_html por:
#   from .launch_app_responsive_v041 import create_wrapper_html
```

### 3. Instalar as 2 skills extras (grant-finder, meta-search-br)

```bash
# Via clone direto:
git clone https://github.com/gustavobraga-byte/grant-finder.git skills/grant-finder
git clone https://github.com/gustavobraga-byte/meta-search-br.git skills/meta-search-br

# Ou use a versão local inclusa no repositório
ls skills/grant-finder/ skills/meta-search-br/
```

---

## 🐛 Histórico de Correções (v0.4.1 + v0.4.2 + v0.4.2.1 + v0.4.2.2)

Bugs reportados pelo usuário nas sessões `session-ses_10b7.md`, `session-ses_10a4.md` e `ses_10a4+`:

| # | Bug | Solução | Versão |
|---|-----|---------|--------|
| 1 | Site não responsivo | 6 media queries + hamburger | v0.4.1 |
| 2 | Tema não recarrega terminal | `toggleTheme()` recarrega iframe do ttyd | v0.4.1 |
| 3 | Idioma sem opção na UI | Dropdown 4 idiomas + cookie | v0.4.1 |
| 4 | Rodapé não responsivo | `flex-wrap` + 2 linhas + media queries | v0.4.2 |
| 5 | Idioma não troca AGENTS.md | Modal Diretrizes + endpoint `/api/agents` | v0.4.2 |
| 6 | Tema CLARO: textos invisíveis nos modais | Nova classe `.modal-shell` com variáveis CSS | v0.4.2.1 |
| 7 | Dashboard de Saúde não carrega | `openHealth()` faz fetch em `/api/health` | v0.4.2.1 |
| 8 | Modal Diretrizes mostra MD cru | `marked.js` + `github-markdown-css` renderizam markdown | v0.4.2.1 |
| 9 | Footer PC: provedor e OpenCode à esquerda | `margin-left: auto` em `.footer-row-2` no desktop | **v0.4.2.2** |
| 10 | Skills sem organização | `skills/grant-finder/` e `skills/meta-search-br/` com clone URL | **v0.4.2.2** |
| 11 | Histórico de sessão não carregava | `openSessions()` faz fetch em `/api/sessions` | **v0.4.2.2** |
| 12 | Saudação ttyd sempre "oi" | `start_ttyd(lang)` com saudação por idioma + `POST /api/lang` | **v0.4.2.2** |
| 13 | `__version__.py` na raiz | Movido para `pesquisai/__version__.py` | **v0.4.2.2** |
| 14 | AGENTS.md com "- [link/lien/enlace]" | Removido e padronizado nas 4 variantes | **v0.4.2.2** |

**Tema padrão:** 🌙 **Escuro** (com anti-flash CSS para evitar flash branco no load).

---

## 🧪 Testes

```bash
cd pesquisai-v0.4.2.2
python3 -m pytest grant_finder/tests/ i18n/tests/ skills/meta-search-br/tests/

# Resultado: 119 passed (100% verdes) · 71.58% cobertura
```

---

## 📊 Estatísticas (v0.4.2.2)

| Métrica | Valor |
|---------|-------|
| Versão | 0.4.2.2 |
| Codinome | ses_10a4+ polish |
| Data | 2026-06-24 |
| Idiomas | 4 (pt_BR, en_US, es_ES, fr_FR) |
| Agências de fomento | 13 (BR + internacional) |
| Skills extras | 2 (grant-finder, meta-search-br) |
| Testes | 119 (100% verdes) |
| Cobertura | 71.58% |
| Media queries | 7 (5 breakpoints + landscape + desktop) |
| Strings traduzidas inline | 70+ |
| Endpoints REST | 17 |
| Componentes | 11 |
| HTML gerado | 88.517 chars |

---

## 🌍 Saudações Multilíngues (v0.4.2.2)

Ao iniciar o ttyd, o PesquisAI envia uma saudação curta no idioma selecionado,
seguida da instrução persistente entre parênteses:

| Idioma | Saudação |
|---|---|
| 🇧🇷 pt_BR | "Olá! (Dica: A partir de agora responda em português brasileiro.)" |
| 🇺🇸 en_US | "Hello! (Tip: From now on, please respond in English.)" |
| 🇪🇸 es_ES | "¡Hola! (Consejo: A partir de ahora responda en español.)" |
| 🇫🇷 fr_FR | "Bonjour ! (Astuce: À partir de maintenant, répondez en français.)" |

A palavra "Dica" é traduzida para cada idioma (Tip / Consejo / Astuce).

---

## 🔗 Links

- **Repositório:** https://github.com/gustavobraga-byte/PesquisAI
- **Documentação completa:** `docs/`
- **Release notes:** `docs/CHANGELOG.md`
- **OpenCode:** https://opencode.ai
- **Skill grant-finder:** https://github.com/gustavobraga-byte/grant-finder
- **Skill meta-search-br:** https://github.com/gustavobraga-byte/meta-search-br

---

## ✍️ Autoria

**Gustavo Bastos Braga** — Universidade Federal de Viçosa (UFV)
**Email:** gustavo.braga@ufv.br
**SisPPG/UFV:** 10356285004
**Licença:** MIT

---

**Última atualização:** 2026-06-24 (v0.4.2.2 — ses_10a4+ polish)
