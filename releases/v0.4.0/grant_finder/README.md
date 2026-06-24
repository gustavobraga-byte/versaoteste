# 🔍 Grant Finder — Skill de Busca de Fomento à Pesquisa

> **Versão:** 0.1.0
> **Domínio:** Agências de fomento brasileiras (CNPq, CAPES, FAPs, FINEP) e internacionais (NIH, NSF, ERC, Wellcome, Horizon Europe)
> **Integridade:** Política de zero-fabricação — SEMPRE declarar data da consulta e fonte. Editais mudam: conferir link oficial antes de submeter.

## 🎯 O que esta skill faz

1. **Busca editais abertos** em 12+ agências de fomento (BR + internacionais)
2. **Verifica elegibilidade** com base no perfil do pesquisador (titulação, área, UF, experiência)
3. **Gera relatórios** ordenados por score de adequação, com razões, avisos e ações necessárias
4. **Cria orçamentos** estruturados conforme rubricas da agência
5. **Elabora minutas** de propostas com seções padrão (Resumível/Abstract, Justificativa, Objetivos, Metodologia, Cronograma, Equipe, Orçamento)
6. **Exporta em Markdown e JSON** para integração com outros sistemas

## 🚀 Uso Rápido

### Programático (Python)

```python
from grant_finder import (
    ResearcherProfile, Degree, search_grants, check_eligibility,
    generate_budget, draft_proposal, Agency
)

# 1. Definir perfil
profile = ResearcherProfile(
    name="Maria Silva",
    degree=Degree.PHD,
    institution="UFV",
    area="Ciências Agrárias",
    state="MG",
    is_PI=True,
    years_since_phd=8,
    publications_count=25,
    keywords=["agricultura familiar", "semiárido"],
)

# 2. Buscar editais
grants = search_grants(
    profile=profile,
    country="BR",
    amount_min=50_000,
)

# 3. Avaliar elegibilidade
for g in grants:
    report = check_eligibility(g, profile)
    print(f"{g.title} → {report.score:.0%} {'✅' if report.is_eligible else '❌'}")

# 4. Gerar orçamento
budget = generate_budget(
    agency="FAPEMIG",
    project_title="Análise da biodiversidade do Cerrado",
    duration_months=24,
    consumables=[("Reagentes", 8000, "PCR, sequenciamento")],
    equipment=[("Microscópio", 12000, "Triagem")],
    scholarships=[
        ("Bolsista IC", "iniciacao_cientifica", 12),
        ("Bolsista Mestrado", "mestrado", 24),
    ],
)
print(budget.to_markdown())

# 5. Elaborar minuta de proposta
proposal = draft_proposal(
    title="Análise da biodiversidade do Cerrado",
    researcher="Maria Silva",
    institution="UFV",
    keywords=["biodiversidade", "cerrado", "agricultura familiar"],
    grant=grants[0] if grants else None,
    budget=budget,
    team=["Maria Silva (PI)", "João Souza (Co-PI)", "Ana Lima (Bolsista IC)"],
    duration_months=24,
    language="pt",
)
```

### Via PesquisAI (linguagem natural)

```
"Busque editais abertos em Minas Gerais para pesquisador doutor em Agronomia 
com valor mínimo de R$ 50 mil."

"Verifique se meu perfil é elegível para a Chamada Universal 2026 do CNPq."

"Gere um orçamento de R$ 80 mil para um projeto de 24 meses em Ciências Agrárias, 
incluindo 1 bolsa IC e 1 bolsa de mestrado."

"Elabore uma minuta de proposta para o edital da FAPEMIG sobre Agricultura Familiar."
```

## 📋 Fontes Suportadas

### Brasil
| Agência | Tipo | URL |
|---------|------|-----|
| CNPq | Federal | https://www.gov.br/cnpq/pt-br/assuntos/editais |
| CAPES | Federal | https://www.gov.br/capes/pt-br/ |
| FAPEMIG | Estadual (MG) | http://www.fapemig.br/pt/menu_pt/editais/ |
| FAPESP | Estadual (SP) | https://fapesp.br/oportunidades/ |
| FINEP | Federal | https://www.finep.gov.br/chamadas-publicas |
| Outras FAPs | Estaduais | via cache local |

### Internacional
| Agência | País | URL |
|---------|------|-----|
| NIH | EUA | https://grants.nih.gov/ |
| NSF | EUA | https://www.nsf.gov/funding/ |
| ERC | UE | https://erc.europa.eu/funding |
| Wellcome | UK | https://wellcome.org/research-funding |
| Horizon Europe | UE | https://ec.europa.eu/info/funding-tenders/ |

## ⚙️ Arquitetura

```
grant_finder/
├── __init__.py            # Interface pública
├── matcher.py             # ResearcherProfile, Grant, EligibilityReport
├── budget.py              # Budget, generate_budget, rubricas
├── proposal.py            # draft_proposal, make_timeline
├── sources/               # Conectores com fontes oficiais
│   ├── cnpq.py
│   ├── capes.py
│   ├── fapemig.py
│   ├── fapesp.py
│   ├── finep.py
│   └── international.py
├── data/                  # Cache local (data/<agencia>.json)
│   ├── cnpq.json
│   ├── capes.json
│   ├── fapemig.json
│   ├── fapesp.json
│   └── nih.json
├── templates/             # Templates de proposta
└── tests/                 # Testes pytest
```

## 🛡️ Integridade Científica

Esta skill implementa a **Política de Zero-Fabricação** do PesquisAI:

- ✅ Toda resposta inclui `data da consulta` e `fonte`
- ✅ Marcadores `[DADO CONFIRMADO]` quando extraído de fonte primária
- ✅ Marcadores `[ESTIMATIVA FUNDAMENTADA]` quando baseado em padrões de mercado (ex.: valores de bolsa)
- ✅ Marcador `[SEM DADOS SUFICIENTES]` quando a fonte não retornou dados
- ⚠️ **AVISO:** Editais mudam. SEMPRE conferir data, valor, prazo e regras no link oficial antes de submeter
- ❌ NUNCA inventar prazos, valores ou requisitos

## 🧪 Testes

```bash
cd /content/drive/My\ Drive/PesquisAI
python -m pytest grant_finder/tests/ -v
```

## 📦 Instalação no PesquisAI

Esta skill é autocontida. Para integração com a registry do PesquisAI, adicione em `pesquisai/constants.py`:

```python
SKILL_REGISTRY: list[SkillEntry] = [
    # ... skills existentes ...
    ("local", "grant_finder", False),  # caminho local
]
```

## 📄 Licença

MIT — Copyright (c) 2026 Gustavo Bastos Braga (UFV)

## 📬 Contato

Gustavo Bastos Braga — gustavo.braga@ufv.br — Universidade Federal de Viçosa
