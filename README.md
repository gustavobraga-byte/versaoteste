# UFVAI — Pesquisa científica com integridade

> **UFVAI** é a marca do assistente; o motor/código é o PesquisAI (este repositório). v0.6.10

[![Abrir no Colab](https://img.shields.io/badge/Clique_aqui-Comece_a_usar-brightgreen?style=for-the-badge)](https://colab.research.google.com/github/gustavobraga-byte/PesquisAI/blob/main/PesquisAI.ipynb)

[![Licença MIT](https://img.shields.io/badge/licença-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow.svg)]()
[![SisPPG/UFV](https://img.shields.io/badge/SisPPG-10356285004-blue.svg)](http://sisppg.ufv.br)
[![Versão](https://img.shields.io/badge/versão-0.6.10-orange.svg)]()

> Ecossistema de agentes de IA para acelerar a pesquisa científica.

---

## 📑 Sumário

- [Visão geral](#-visão-geral)
- [Capacidades](#-capacidades)
- [Início rápido](#-início-rápido)
- [Skills disponíveis](#-skills-disponíveis)
- [Roadmap](#-roadmap)
- [Arquitetura](#-arquitetura)
- [Limitações](#-limitações)
- [Citação](#-citação)
- [Declaração de uso de IA](#-declaração-de-uso-de-ia)
- [Disclaimer](#-disclaimer)
- [Como contribuir](#-como-contribuir)
- [Contato](#-contato)

---

## 🧠 Visão geral

O **PesquisAI** é um agente de Inteligência Artificial construído sobre a arquitetura **OpenCode**, projetado especificamente para pesquisadores, acadêmicos e cientistas. Ele automatiza etapas que vão do levantamento bibliográfico à estruturação de artigos, integrando fontes de dados públicos do Brasil.

> **🚨 Atenção:** O PesquisAI é uma ferramenta de apoio — **não substitui** a curadoria humana. Sempre revise os resultados gerados.

---

## ✨ Capacidades

| Área | O que faz |
|------|-----------|
| 📊 **Dados IBGE** | Consulta e extração de dados estatísticos, demográficos e socioeconômicos |
| 🏥 **DataSUS** | Acesso e análise de dados públicos de saúde (mortalidade, internações, vacinação) |
| 🌾 **Agro & Ambiente** | Dados do agronegócio brasileiro e cadastro ambiental rural (CAR) |
| 🇧🇷 **Dados Brasil** | Conjunto amplo de indicadores e datasets oficiais brasileiros |
| 📚 **Pesquisa científica** | Mineração de textos, revisão bibliográfica e suporte metodológico |
| ✍️ **Redação acadêmica** | Auxílio na estruturação e revisão de artigos científicos |
| 🔬 **Análise qualitativa** | Métodos clássicos e avançados (Reinert, similitude, codificação) |
| 📐 **Normas ABNT/UFV** | Formatação e normalização de trabalhos acadêmicos |

---

## 🚀 Início rápido

### Opção 1 — Google Colab (recomendada)

Sem instalação, pronto em ~2 minutos:

1. Clique no badge do Colab abaixo  
   [![Abrir no Colab](https://img.shields.io/badge/Clique_aqui-Comece_a_usar-brightgreen?style=for-the-badge)](https://colab.research.google.com/github/gustavobraga-byte/PesquisAI/blob/main/PesquisAI.ipynb)

2. No menu do Colab, vá em **Ambiente de execução → Executar tudo** (`Ctrl+F9`)

3. Role até a última célula e clique em **🤖 Abrir o UFVAI**

### Opção 2 — Instalação local

```bash
git clone https://github.com/gustavobraga-byte/PesquisAI.git
cd PesquisAI
uv sync
# ... (consulte o MANUAL.md para detalhes)
```

---

### Opção 2 - Uso offline - SO Linux

O PesquisAI pode ser executado **100% offline** em sistemas Debian/Ubuntu, ideal para
ambientes sem internet, necessidade de sigilo dos dados processados ou com restrições de conectividade.

### Instalação Rápida

```bash
# Baixe o pacote .deb mais recente
wget https://github.com/gustavobraga-byte/PesquisAI/raw/main/debs/pesquisai_0.6.10-offline_amd64.deb -O /tmp/pesquisai.deb && \
sudo apt install /tmp/pesquisai.deb -y && \
rm /tmp/pesquisai.deb

# Execute
pesquisai
```

### Requisitos Mínimos

| Requisito | Especificação |
|-----------|---------------|
| **SO** | Debian 10+ / Ubuntu 26.04+ (amd64) |
| **RAM** | 4 GB (mín.) · 8 GB+ (recomendado) Usando LLM em núvem|
| **Disco** | 500 MB livres |
| **Python** | 3.10+ (instalado como dependência) |
| **Portas** | `8000` (Terminal TTYD) · `8001` (Interface Web) |

### LLM Local (Ollama) — Para Offline Total

Para funcionar **sem nenhuma conexão com a internet**, é necessário um LLM local via
[Ollama](https://ollama.com):

```bash
# Instale o Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Baixe um modelo compatível (256k de contexto)
ollama pull mistral-small:24b    # Melhor custo-benefício (14 GB VRAM)
ollama pull qwen2.5:7b           # Para hardware limitado (6 GB VRAM)
ollama pull kimi/kimi2.6         # Melhor qualidade geral
```

Configure o PesquisAI para usar o modelo local editando (exemplo com o mistral-small:24b)
`~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "http://localhost:11434/v1"
      },
      "models": {
        "mistral-small:24b": {
          "name": "mistral-small:24b",
          "contextWindow": 256000
        }
      }
    }
  }
}
```

### Liberar Portas no Firewall (em caso de falha)

```bash
sudo ufw allow 8000/tcp   # Terminal TTYD
sudo ufw allow 8001/tcp   # Interface Web
sudo ufw allow 11434/tcp  # Ollama API (se usar LLM local)
```



> 📖 **Documentação completa da versão offline:**
> [`debs/README.md`](debs/README.md) — inclui solução de problemas, estrutura de
> diretórios, modelos recomendados e configuração avançada.

---

## 🛠️ Skills disponíveis

O PesquisAI opera por módulos especializados (*skills*). Cada skill conecta o agente a uma fonte de dados ou capacidade específica.

| Skill | Descrição | Autor |
|-------|-----------|-------|
| `skill-ibge` | Consulta automatizada à API do IBGE (Censo, PNAD, PIB, etc.) | [@gustavobraga-byte](https://github.com/gustavobraga-byte) |
| `skill-datasus` | Integração com OpenDataSUS (mortalidade, internações, vacinação) | [@gustavobraga-byte](https://github.com/gustavobraga-byte) |
| `skill-UFV-ABNT` | Formatação segundo normas UFV/ABNT | [@gustavobraga-byte](https://github.com/gustavobraga-byte) |
| `skill-analise-qualitativa` | Análise de conteúdo com métodos clássicos e avançados (NVivo-like) | [@gustavobraga-byte](https://github.com/gustavobraga-byte) |
| `scientific-skills` | Mineração de textos, revisão bibliográfica, suporte metodológico | [@K-Dense-AI](https://github.com/K-Dense-AI) |
| `skill-dados-brasil` | Indicadores e datasets oficiais complementares | [@gustavobraga-byte](https://github.com/gustavobraga-byte) |
| `skill-agrobr` | Dados do agronegócio (produção, pecuária, CAR) | [@gustavobraga-byte](https://github.com/gustavobraga-byte) |
| `skill-obsidian-memory` | Memória persistente via Obsidian vault no Google Drive 🧠 | [@gustavobraga-byte](https://github.com/gustavobraga-byte) |
| `skill-memorial-ufv` | Geração automática de Memorial RSC-PCCTAE conforme normas UFV/ABNT 📜 | [@gustavobraga-byte](https://github.com/gustavobraga-byte) |

---

## 🆕 Novidades v0.6.10 — Memória BM25 cache + Nome+IP + Responsiva mobile

**Versão 0.6.10** — pacote offline `pesquisai_0.6.10-offline_amd64.deb` — todas as entregas abaixo já estão nesta build.

### 📜 Termos de Uso v2.1 → v6 (re-consentimento `_TV=6`)
- **Telemetria opt-out (LGPD art. 7º IX):** caixa vem **marcada por padrão** e é **ativa** sem cookie (`analytics_storage:'denied'` — sem `_ga`); oposição a qualquer momento via caixa ou `UFVAI_TELEMETRY=0`.
- **E-mail de ativação obrigatório (LGPD art. 7º V):** `POST /api/consent` devolve **400** sem e-mail válido; eliminação mantida (art. 18).
- **Coleta resumida:** canal client-side limitado ao `page_view` padrão — evento custom `ufvai_session` removido.

### 🔐 Perfil persistente e pré-preenchimento
- Arquivo `backups/ufvai_consentimento.json` (Colab: Drive · offline: `~/PesquisAI/backups/`) guarda `{email, name, email_sha256, ip, analytics, terms_version, accepted_at, app_version}`.
- `GET /api/consent` inclui `"profile"` → frontend **pré-preenche** e-mail/checkboxes; se mesma versão já aceita, **pula a tela**.

### 👋 Tela "Bem-vindo de volta" (reabertura)
- Ao reabrir, se `profile.accepted && profile.terms_version === "6"` (perfil sobrevive à sessão), exibe overlay **"Bem-vindo de volta!"** com Nome + e-mail:
  - e-mail persistido em destaque (`#w-email`);
  - botão **"Continuar como este usuário"** → dispara `POST /api/access` (heartbeat) e fecha;
  - botão **"Se não é você, alterar e-mail"** → abre os Termos com campo editável pré-preenchido, checkbox restaurado e foco no e-mail.
- Responsiva (mobile/tablet, `env(safe-area-inset)`, `visualViewport`) e acessível (`role=dialog`, `aria-modal`).

### 📊 Cada novo acesso → planilha de contatos
- **Webhook único** `UFVAI_CONTACT_ENDPOINT` (Apps Script → Planilha Google):
  - `https://script.google.com/macros/s/AKfycbxel3-_75htD3b5bd0HEPLSCWHSj79CR_Tf4IH6sEWscBlhF3jOjcNBaKbCuffcWskH/exec`
  - Payload: `{product, email, email_sha256, environment, app_version, sent_at, flag}`.
  - `flag = "novo_contato"` (primeiro aceite) ou `"usuario_ativo"` (cada reabertura via Bem-vindo de volta).
  - Sheet: `Contatos` com colunas `Timestamp | Email | Email SHA-256 | Ambiente | Versão | Flag` · limite anti-abuso 1000 linhas · sem IP por privacidade.
- **Heartbeat** `telemetry.notify_active_user()` → `POST /api/access` → `_forward_contact(..., "usuario_ativo")` (fire-and-forget, logs em `~/PesquisAI/logs/contato.log` e `telemetria.log`).
- Configuração: painel **📊 Telemetria (Admin)** → campo **✉️ URL de contato** ou `UFVAI_CONTACT_ENDPOINT` em env/`ufvai.env`. Apps Script em `scripts/webhook-contatos.gs` (SPREADSHEET_ID já preenchido).

### 🖥️ Outros v0.6.7–v0.6.10
- **Painel único (Colab):** todo feedback visual pelo `_BootPanel` (barra contínua tema UFVAI papel/navy/dourado, logo base64); prints verbosos suprimidos.
- **Botão 📘 Manual** ao lado do Dashboard de Saúde; rota `GET /api/manual` serve `MANUAL.md` local (fallback GitHub); modal com Recarregar/Ver fonte.
- **Offline completo:** wheels bundle no `.deb` (offline-first `pip --no-index`), bind `0.0.0.0` + `::` (resolve `127.0.1.1`/`::1` Ubuntu), tela 8002 instantânea mesmo com Drive montado via rclone, fallback vault `~/PesquisAI/vault` quando Drive read-only.

---

## 🗺️ Roadmap

| Fase | Período | Foco |
|------|---------|------|
| **1 — Base sólida** | Meses 1–3 | CLI, testes, CI/CD, instalação local |
| **2 — Expansão de dados** | Meses 4–7 | Novas skills: IPEA, INEP, Sucupira/CAPES, plugins |
| **3 — Interface** | Meses 8–11 | Interface web aprimorada, editor de artigos, copilot |
| **4 — Ecossistema** | Meses 12–18 | API pública, versão SaaS, integração institucional |

---

## ⚙️ Arquitetura

O PesquisAI usa **ttyd** para renderizar um terminal Linux interativo no navegador via Google Colab, com o ecossistema OpenCode injetado:

```
Google Colab
└── ttyd (terminal web na porta 8000)
    └── opencode (runtime do agente)
        ├── skill-ibge
        ├── skill-datasus
        ├── skill-dados-brasil
        ├── skill-agrobr
        ├── skill-UFV-ABNT
        ├── skill-analise-qualitativa
        ├── scientific-skills
        ├── skill-obsidian-memory  ← memória persistente (v0.5.0+)
        ├── skill-memorial-ufv    ← Memorial RSC-PCCTAE UFV/ABNT (v0.5.1.8+)
        └── pesquisai (instruções do agente)
```

Dependências gerenciadas pelo [uv (Astral)](https://github.com/astral-sh/uv) para instalação rápida e reproduzível.

---

## ⚠️ Limitações

O PesquisAI **não substitui** o julgamento humano e apresenta as seguintes limitações:

- ❌ **Não** realiza revisão por pares nem validação científica profunda.
- ❌ **Não** acessa bases pagas sem integração específica.
- ❌ **Não** coleta dados primários (entrevistas, experimentos, surveys).
- ❌ **Não** garante atualização em tempo real — depende das APIs externas.
- ❗ **Alucinações possíveis:** sempre verifique os resultados com fontes confiáveis.

---

## 📚 Citação

**ABNT NBR 6023:2018:**

```
BRAGA, Gustavo Bastos. UFVAI: agente de inteligência artificial para pesquisa
científica. Versão 0.6.10. Viçosa: Universidade Federal de Viçosa, 2026.
Disponível em: https://colab.research.google.com/github/gustavobraga-byte/PesquisAI/.
Acesso em: DD mês. AAAA.

Projeto registrado no SisPPG/UFV sob nº 10356285004.
Verificar autenticidade em: http://sisppg.ufv.br
```

**BibTeX:**

```bibtex
@software{braga2026ufvai,
  author       = {Gustavo Bastos Braga},
  title        = {{UFVAI}: Agente de Intelig{\^e}ncia Artificial
                  para Pesquisa Cient{\'\i}fica},
  year         = {2026},
  version      = {0.6.10},
  institution  = {Universidade Federal de Vi{\c{c}}osa (UFV)},
  url          = {https://colab.research.google.com/github/gustavobraga-byte/PesquisAI/}
}
```

---

## 🤖 Declaração de uso de IA

O uso do PesquisAI em trabalhos acadêmicos **deve ser declarado** conforme diretrizes do COPE, CAPES e principais periódicos. Consulte o arquivo [`declaracao_uso_ia.md`](declaracao_uso_ia.md) para modelos prontos (ABNT, ICMJE, Nature, Science, Elsevier, Springer).

---

## ⚖️ Disclaimer

O PesquisAI é um **software experimental fornecido "como está"**, sem garantias. LLMs podem **alucinar** — é responsabilidade exclusiva do usuário validar todos os dados, análises e referências gerados. Consulte o [`disclaimer_pesquisai.md`](disclaimer_pesquisai.md) para os termos completos.

---

## 🤝 Como contribuir

Contribuições são bem-vindas — especialmente novas skills para fontes de dados públicos brasileiros.

```bash
# 1. Fork e clone
git clone https://github.com/SEU_USUARIO/PesquisAI.git

# 2. Crie uma branch
git checkout -b feature/nova-skill

# 3. Desenvolva, teste e abra um Pull Request
```

Consulte o [`AGENTS.md`](AGENTS.md) para entender a arquitetura das skills.

**Ideias de contribuição:**
- Skills para IPEA, INEP, ANEEL, ANS, IBICT, etc.
- Melhorias na skill científica (SciELO, BDTD)
- Traduções da documentação
- Casos de uso e exemplos práticos

---

## 📬 Contato

Desenvolvido por **Gustavo Bastos Braga** na Universidade Federal de Viçosa (UFV).

- ✉️ gustavo.braga@ufv.br
- 🐙 [@gustavobraga-byte](https://github.com/gustavobraga-byte)

---

Feito com 💙 para impulsionar a ciência brasileira.

---

## 📜 Termos · 🔒 Privacidade · 📊 Telemetria

- Ao abrir a interface você aceita os [Termos de Uso](docs/TERMS_OF_USE.md) e a [Licença MIT](LICENSE).
- Telemetria é **opt-in, anônima e desligável**: [`TELEMETRY.md`](TELEMETRY.md) · [`PRIVACY.md`](PRIVACY.md).

## 🌐 Idiomas

🇧🇷 pt_BR · 🇺🇸 en_US · 🇪🇸 es_ES · 🇫🇷 fr_FR · 🇨🇳 zh_CN（简体中文）
