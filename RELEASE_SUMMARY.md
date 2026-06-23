# 📦 PesquisAI v0.4.0 — Release Summary

> **Data:** 2026-06-23
> **Versão:** 0.4.0 (International & Mobile)
> **Status:** ✅ Pronto para PR / publicação

---

## 🎯 Resumo do Release

Adições do **PesquisAI v0.4.0** — extensão modular do projeto principal com 3 grandes features:

| Feature | Tipo | Tamanho | Testes |
|---|---|---|---|
| 🔍 **grant_finder** | Nova skill | ~1.500 linhas | 48 ✅ |
| 🌐 **i18n (4 idiomas)** | Novo módulo | ~700 linhas + 4 JSON | 31 ✅ |
| 📱 **launch_app_responsive** | Patch | ~600 linhas | Manual |
| 🤖 **agents/** multilíngues | Documentação | 4 AGENTS.md | Manual |

**Total:** 51 arquivos · 79 testes · 83% de cobertura · 4 idiomas · 13 agências

---

## 🌍 Idiomas Suportados

| Bandeira | Código | Idioma | Status |
|---|---|---|---|
| 🇧🇷 | `pt_BR` | Português (Brasil) | ✅ Padrão |
| 🇺🇸 | `en_US` | English (United States) | ✅ |
| 🇪🇸 | `es_ES` | Español (España) | ✅ |
| 🇫🇷 | `fr_FR` | Français (France) | ✅ **NOVO v0.4.0** |

---

## 🏛️ Agências de Fomento Integradas (13)

### 🇧🇷 Brasil (8)
1. **CNPq** — Conselho Nacional de Desenvolvimento Científico e Tecnológico
2. **CAPES** — Coordenação de Aperfeiçoamento de Pessoal de Nível Superior
3. **FAPEMIG** — Fundação de Amparo à Pesquisa de Minas Gerais
4. **FAPESP** — Fundação de Amparo à Pesquisa de São Paulo
5. **FINEP** — Financiadora de Estudos e Projetos
6. **FAPERJ** — Fundação de Amparo à Pesquisa do Rio de Janeiro
7. **FAPERGS** — Fundação de Amparo à Pesquisa do Rio Grande do Sul
8. **BNDES** — Banco Nacional de Desenvolvimento Econômico e Social

### 🌎 Internacional (5)
9. **NIH** — National Institutes of Health (EUA)
10. **NSF** — National Science Foundation (EUA)
11. **ERC** — European Research Council (UE)
12. **Wellcome** — Wellcome Trust (Reino Unido)
13. **Horizon Europe** — Programa-quadro UE para pesquisa e inovação

---

## 📊 Estatísticas

| Métrica | Valor |
|---|---|
| **Versão** | 0.4.0 (International & Mobile) |
| **Data de release** | 2026-06-23 |
| **Codename** | International & Mobile |
| **Autor** | Gustavo Bastos Braga (UFV) |
| **Email** | gustavo.braga@ufv.br |
| **Licença** | MIT |
| **SisPPG/UFV Registry** | 10356285004 |
| **Compatibilidade PesquisAI** | 0.2.1+ |
| **Python** | 3.10+ |
| **Tamanho total do pacote** | 328 KB |
| **Total de arquivos** | 51 |
| **Arquivos Python** | 26 |
| **Arquivos Markdown** | 12 |
| **Arquivos JSON** | 9 |
| **Linhas de código** | ~2.800 |
| **Linhas de docs** | ~1.500 |
| **Linhas de JSON (i18n + cache)** | ~800 |
| **Funções públicas** | 30+ |
| **Classes (dataclasses)** | 14 |
| **Testes totais** | 79 |
| **Cobertura de testes** | 83% |

---

## 📂 Estrutura Final do Pacote

```
pesquisai-v0.4.0/
│
├── 📄 README.md                          ← Documentação principal
├── 📄 CHANGELOG.md                       ← Histórico de versões
├── 📄 LICENSE                            ← MIT
├── 📄 pyproject.toml                     ← Configuração do pacote
├── 📄 .gitignore
├── 🐍 __version__.py                     ← Fonte única de versão
│
├── 🤖 agents/                            ← AGENTS.md multilíngues
│   ├── AGENTS.pt.md                      🇧🇷
│   ├── AGENTS.en.md                      🇺🇸
│   ├── AGENTS.es.md                      🇪🇸
│   ├── AGENTS.fr.md                      🇫🇷 (NOVO)
│   └── README.md
│
├── 🔍 grant_finder/                      ← Skill de fomento
│   ├── __init__.py
│   ├── matcher.py                        (24 testes)
│   ├── budget.py                         (14 testes)
│   ├── proposal.py                       (10 testes)
│   ├── README.md
│   ├── SKILL.md
│   ├── sources/                          (6 conectores)
│   │   ├── cnpq.py · capes.py
│   │   ├── fapemig.py · fapesp.py
│   │   ├── finep.py
│   │   └── international.py              (NIH, NSF, ERC, Wellcome, Horizon)
│   ├── data/                             (5 caches JSON)
│   ├── templates/
│   └── tests/                            (48 testes ✅)
│
├── 🌐 i18n/                              ← Módulo multilíngue
│   ├── __init__.py
│   ├── translator.py
│   ├── detector.py
│   ├── README.md
│   ├── translations/                     (4 idiomas)
│   │   ├── pt_BR.json                    🇧🇷
│   │   ├── en_US.json                    🇺🇸
│   │   ├── es_ES.json                    🇪🇸
│   │   └── fr_FR.json                    🇫🇷 (NOVO)
│   └── tests/                            (31 testes ✅)
│
├── 🔬 pesquisai/
│   └── launch_app_responsive.py          ← Patch mobile
│
├── 📚 docs/
│   ├── MOBILE_RESPONSIVE_PATCH.md
│   └── ENTREGAS_JUNHO_2026.md
│
├── 🧪 conftest.py                        ← Configuração pytest
│
└── 🔄 .github/
    └── workflows/
        └── ci.yml                        ← CI/CD (lint + tests + i18n)
```

---

## ✅ Testes

**Resultado final: 79/79 passando (83% cobertura)**

```bash
$ python3 -m pytest grant_finder/tests/ i18n/tests/

grant_finder/tests/test_budget.py    14 passed
grant_finder/tests/test_matcher.py   24 passed
grant_finder/tests/test_proposal.py  10 passed
i18n/tests/test_translator.py        31 passed
                                    ──────────
                                     79 passed in 11.64s

Coverage:
  grant_finder/   87%
  i18n/           91%
  TOTAL           83%
```

**Suítes de teste:**

| Suíte | Testes | Categorias |
|---|---|---|
| `test_matcher.py` | 24 | ResearcherProfile, Grant, EligibilityReport, busca, cache |
| `test_budget.py` | 14 | Budget, ExpenseType, rubricas, exportação Markdown/JSON |
| `test_proposal.py` | 10 | minutas PT/EN, cronograma, anexos |
| `test_translator.py` | 31 | tradução, troca de idioma, detecção, Accept-Language |

---

## 🚀 Como Subir para o GitHub

### Opção A — Fork + PR (recomendado para o PesquisAI principal)

```bash
# 1. Fork do PesquisAI
#    https://github.com/gustavobraga-byte/PesquisAI

# 2. Clone seu fork
git clone https://github.com/SEU_USUARIO/PesquisAI.git
cd PesquisAI

# 3. Criar branch para a feature
git checkout -b feature/v0.4.0-additions

# 4. Copiar arquivos do release
cp -r /caminho/pesquisai-v0.4.0/grant_finder ./
cp -r /caminho/pesquisai-v0.4.0/i18n ./
cp -r /caminho/pesquisai-v0.4.0/agents ./
cp /caminho/pesquisai-v0.4.0/pesquisai/launch_app_responsive.py ./pesquisai/
cp /caminho/pesquisai-v0.4.0/.github/workflows/ci.yml ./.github/workflows/

# 5. Atualizar CHANGELOG do repositório principal
cat /caminho/pesquisai-v0.4.0/CHANGELOG.md >> CHANGELOG.md

# 6. Commit
git add .
git commit -m "feat: add grant_finder skill, i18n (4 langs), and mobile responsive

- New skill grant_finder with 13 funding agencies (BR + international)
- New i18n module with 4 languages (pt_BR, en_US, es_ES, fr_FR)
- New launch_app_responsive with 5 breakpoints and hamburger menu
- New agents/AGENTS.{pt,en,es,fr}.md multilingual variants
- 79 new tests passing (83% coverage)
- Bump version to 0.4.0"

# 7. Push e abrir PR
git push origin feature/v0.4.0-additions
# Abra PR no GitHub
```

### Opção B — Repositório independente (release isolado)

```bash
# 1. Criar novo repositório no GitHub
#    https://github.com/SEU_USUARIO/pesquisai-additions

# 2. Inicializar git no diretório
cd pesquisai-v0.4.0
git init
git add .
git commit -m "Initial release: PesquisAI Additions v0.4.0"

# 3. Conectar ao GitHub
git remote add origin https://github.com/SEU_USUARIO/pesquisai-additions.git
git branch -M main
git push -u origin main

# 4. Criar release/tag
git tag -a v0.4.0 -m "International & Mobile"
git push origin v0.4.0
```

---

## 📝 Notas de Migração (v0.2.x → v0.4.0)

### Mudanças Quebrantes (breaking changes)
Nenhuma — adições são puramente incrementais.

### Novas Dependências Python
```toml
# Adicionar ao pyproject.toml principal
requests>=2.31
beautifulsoup4>=4.12
```

### Mudanças no `pesquisai/constants.py`
```python
# Adicionar à SKILL_REGISTRY:
SKILL_REGISTRY: list[SkillEntry] = [
    # ... skills existentes ...
    ("local", "grant_finder", False),  # NOVO
]
```

### Mudanças no `pesquisai/launch_app.py`
```python
# Substituir a importação do create_wrapper_html:
from .launch_app_responsive import create_wrapper_html_responsive as create_wrapper_html
```

---

## 📬 Contato

- **Autor:** Gustavo Bastos Braga
- **Email:** gustavo.braga@ufv.br
- **GitHub:** [@gustavobraga-byte](https://github.com/gustavobraga-byte)
- **Instituição:** Universidade Federal de Viçosa (UFV)
- **SisPPG/UFV:** nº 10356285004
- **Licença:** MIT

---

*PesquisAI · v0.4.0 · "International & Mobile" · Junho 2026*
