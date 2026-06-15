# 🔬 PesquisAI — Agente de IA para Pesquisadores Científicos

[![Abrir no Colab](https://img.shields.io/badge/Clique_aqui-Comece_a_usar-brightgreen?style=for-the-badge)](https://colab.research.google.com/github/gustavobraga-byte/PesquisAI/blob/main/PesquisAI.ipynb)
[![Licença MIT](https://img.shields.io/badge/licença-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow.svg)]()
[![SisPPG/UFV](https://img.shields.io/badge/SisPPG-10356285004-blue.svg)](http://sisppg.ufv.br)
[![Tests](https://img.shields.io/badge/tests-43%20passing-brightgreen.svg)](tests/)

> Ecossistema de agentes de IA para acelerar a pesquisa científica brasileira.

O **PesquisAI** é um agente de Inteligência Artificial construído sobre a arquitetura **OpenCode**, projetado especificamente para pesquisadores, acadêmicos e cientistas. Ele automatiza etapas que vão do levantamento bibliográfico à estruturação de artigos, integrando fontes de dados públicos do Brasil (IBGE, DataSUS, agro, etc.) com **regras rígidas de integridade científica** (nenhuma referência fabricada, nenhum dado inventado).

---

## ✨ O que ele faz

| Capacidade | Descrição |
|---|---|
| 📊 **Dados IBGE** | Consulta e extração de dados estatísticos, demográficos e socioeconômicos |
| 🏥 **Dados DataSUS** | Acesso e análise de dados públicos de saúde via OpenDataSUS |
| 🌾 **Dados Agro & Ambientais** | Acesso a dados do agronegócio brasileiro e cadastro ambiental rural |
| 🇧🇷 **Dados Brasil** | Conjunto amplo de indicadores e datasets oficiais brasileiros |
| 📚 **Pesquisa científica** | Mineração de textos, revisão bibliográfica e suporte metodológico |
| ✍️ **Redação acadêmica** | Auxílio na estruturação e revisão de artigos científicos |
| 🔬 **Análise qualitativa** | Análise de conteúdo com métodos clássicos e avançados (Reinert, similitude, codificação) |
| 📐 **Normas ABNT/UFV** | Formatação e normalização de trabalhos acadêmicos |

---

## 🚀 Início rápido

### Opção 1 — Google Colab (sem instalação)

1. Clique no badge do **Colab** acima
2. No menu: **Ambiente de execução → Executar tudo** (ou `Ctrl+F9`)
3. Aguarde ~2 minutos para o ambiente carregar
4. Role até a última célula e clique em **🚀 ABRIR O PESQUISAI**

### Opção 2 — Local (para desenvolvedores)

```bash
git clone https://github.com/gustavobraga-byte/PesquisAI.git
cd PesquisAI
pip install -e ".[dev]"
python main.py
```

---

## 🛠️ Skills disponíveis

O PesquisAI opera por módulos especializados (*skills*). Cada skill conecta o agente a uma fonte de dados ou capacidade específica:

| Skill | Mantenedor | Descrição |
|---|---|---|
| `ibge-br` | @gustavobraga-byte | API do IBGE (Censo, PNAD, PIB, índices de preços) |
| `datasus` | @gustavobraga-byte | OpenDataSUS: mortalidade, internações, cobertura vacinal |
| `UFV-ABNT` | @gustavobraga-byte | Formatação e normalização conforme UFV/ABNT |
| `analise-qualitativa` | @gustavobraga-byte | Análise qualitativa: Reinert, similitude, codificação |
| `scientific-agent-skills` | @K-Dense-AI | Mineração, revisão bibliográfica, estrutura IMRaD |
| `dados-brasil` | @gustavobraga-byte | Indicadores e datasets oficiais brasileiros |
| `agrobr` | @gustavobraga-byte | Agronegócio: produção, pecuária, CAR |

---

## ⚙️ Arquitetura (v0.3 — refatorada)

A partir da versão 0.3, o PesquisAI é distribuído como um **pacote Python modular**:

```
PesquisAI/
├── main.py                       # Entry point (3 linhas)
├── pyproject.toml
├── pesquisai/                    # Pacote principal
│   ├── config.py                 # Settings pydantic 2
│   ├── run.py                    # Orquestrador
│   ├── progress.py               # Barra de progresso
│   ├── skills.py                 # Skill dataclass + clone paralelo
│   ├── theme.py                  # Tema/agente/TUI config
│   ├── dependencies.py           # apt + pip installer
│   ├── launch/
│   │   ├── __init__.py           # launch() principal
│   │   ├── server.py             # HTTP wrapper (seguro)
│   │   ├── templates/            # HTML estático
│   │   └── static/               # CSS + JS separados
│   └── utils/
│       ├── security.py           # validate_command, safe_backup_path
│       ├── opencode.py           # find/install centralizado
│       └── subprocess.py         # CommandRunner protocol + FakeRunner
└── tests/                        # 43 testes pytest (todos passando)
    ├── test_security.py          # 32 testes
    ├── test_subprocess.py        # 6 testes
    └── test_server.py            # 5 testes
```

### Diagrama de runtime

```
Google Colab
└── ttyd (terminal web na porta 8000)
    └── opencode (runtime do agente)
        ├── skill-ibge
        ├── skill-datasus
        ├── skill-dados-brasil
        ├── skill-agrobr
        ├── ufv-abnt
        ├── skill-analise-qualitativa
        ├── scientific-skills
        └── pesquisai (instruções do agente)
```

---

## 🔒 Segurança (novo na v0.3)

A v0.3 corrige **5 vulnerabilidades críticas** identificadas em auditoria:

| Vetor | Proteção |
|---|---|
| Injeção de comando em `/api/run_terminal` | Whitelist de binários + validação de shell metacharacters |
| Path traversal em `/api/restore` | Resolução de path segura com `is_relative_to` |
| Credenciais `.keys.json` expostas | `chmod 0o600` automático |
| XSS via nome de arquivo de backup | Renderização via `textContent` (DOM API) |
| DoS em `find` recursivo | `timeout=5s` |

---

## 🗺️ Roadmap

| Fase | Período | Foco |
|---|---|---|
| **1 — Base sólida** ✅ | Meses 1–3 | CLI, testes, CI/CD, instalação local |
| **2 — Expansão de dados** | Meses 4–7 | IPEA, INEP, Sucupira/CAPES, plugins... |
| **3 — Interface** | Meses 8–11 | Aprimorar interface web, editor de artigos, copilot |
| **4 — Ecossistema** | Meses 12–18 | API pública, versão SaaS, integração institucional |

---

## 🤝 Como contribuir

```bash
git clone https://github.com/SEU_USUARIO/PesquisAI.git
cd PesquisAI
pip install -e ".[dev]"
python -m pytest tests/ -v   # 43 testes
```

**Idéias:**
- Skills para IPEA, INEP, ANEEL, ANS, IBICT
- Mais bases científicas (SciELO, BDTD)
- Traduções da documentação
- Casos de uso e exemplos de pesquisa

Consulte [`AGENTS.md`](AGENTS.md) para a arquitetura das skills e o [`relatorios/IMPLEMENTACAO_RELATORIO.md`](relatorios/IMPLEMENTACAO_RELATORIO.md) para o histórico técnico da refatoração.

---

## 🧪 Desenvolvimento

```bash
# Instalar dependências de dev
pip install -e ".[dev]"

# Rodar testes
python -m pytest tests/ -v

# Validar template
python -c "from pesquisai.launch import render_wrapper; print(render_wrapper('http://localhost:8000', 'http://drive.test'))"
```

---

## Declaração de Limitações

O PesquisAI:
- **Não substitui** a revisão por pares nem o julgamento de um pesquisador humano.
- **Não acessa** bases de dados pagas sem integração configurada.
- **Não realiza** coleta primária de dados (entrevistas, experimentos, surveys).
- **Não garante** atualização em tempo real; a disponibilidade dos dados depende das APIs externas.
- 🚨 **ATENÇÃO:** Sempre revise e confirme a precisão de todas as informações geradas por esta IA antes de utilizá-las em decisões ou projetos críticos.

---

## Citação (v0.3.0)

**ABNT NBR 6023:2018:**

```
BRAGA, Gustavo Bastos. PesquisAI: agente de inteligência artificial para pesquisa
científica. Versão 0.3.0. Viçosa: Universidade Federal de Viçosa, 2026.
Disponível em: https://github.com/gustavobraga-byte/PesquisAI.
Acesso em: DD mês. AAAA.

Projeto registrado no SisPPG/UFV sob nº 10356285004.
Verificar autenticidade em: http://sisppg.ufv.br
```

**BibTeX:**

```bibtex
@software{braga2026pesquisai,
  author       = {Gustavo Bastos Braga},
  title        = {{PesquisAI}: Agente de Intelig{\^e}ncia Artificial
                  para Pesquisa Cient{\'\i}fica},
  year         = {2026},
  version      = {0.3.0},
  institution  = {Universidade Federal de Vi{\c{c}}osa (UFV)},
  url          = {https://github.com/gustavobraga-byte/PesquisAI}
}
```

---

## Declaração de Uso de IA

O uso do PesquisAI em trabalhos acadêmicos **deve ser declarado** conforme diretrizes do COPE, CAPES e principais periódicos. Consulte [`declaracao_uso_ia.md`](declaracao_uso_ia.md) para modelos prontos.

---

## Disclaimer

O PesquisAI é um **software experimental fornecido "como está"**, sem garantias. LLMs podem **alucinar** — é responsabilidade exclusiva do usuário validar todos os dados, análises e referências gerados. Consulte [`disclaimer_pesquisai.md`](disclaimer_pesquisai.md) para os termos completos.

---

## 📬 Contato

Desenvolvido por **Gustavo Bastos Braga** na Universidade Federal de Viçosa (UFV).

- ✉️ gustavo.braga@ufv.br
- 🐙 [@gustavobraga-byte](https://github.com/gustavobraga-byte)

---

Feito com 💙 para impulsionar a ciência brasileira.
