"""
proposal.py — Minutas de propostas de fomento.

Gera templates estruturados para as seções típicas:
  - Resumo / Abstract
  - Justificativa
  - Objetivos
  - Metodologia
  - Cronograma
  - Equipe
  - Orçamento
  - Referências
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from .budget import Budget
from .matcher import Grant, ResearcherProfile


TEMPLATES_DIR: Path = Path(__file__).parent / "templates"


# ── Templates em código (caso arquivos .md não existam) ─────────

DEFAULT_PROPOSAL_PT: str = """# {title}

## Resumo

[Descrever de forma concisa (até 500 palavras) o problema, a abordagem metodológica, os resultados esperados e o impacto. Evitar jargão excessivo; o resumo deve ser compreensível para um avaliador de área adjacente.]

**Palavras-chave:** {keywords}

## 1. Justificativa e Relevância

[Por que esta pesquisa é necessária? Qual o estado da arte? Qual a lacuna de conhecimento que este projeto preenche? Citar literatura fundamental (mínimo 5 referências, todas verificáveis).]

## 2. Objetivos

### 2.1 Objetivo Geral
[Verbo no infinitivo + objeto + condição. Ex: "Avaliar o impacto do PRONAF sobre a produtividade da agricultura familiar no Semiárido brasileiro no período 2010-2024."]

### 2.2 Objetivos Específicos
1. [Verbo + objeto + condição]
2. [Verbo + objeto + condição]
3. [Verbo + objeto + condição]

## 3. Metodologia

### 3.1 Área de Estudo
[Localização, recorte temporal, unidades de análise]

### 3.2 Fontes de Dados
[Listar bases de dados a serem utilizadas, com justificativa de escolha]

### 3.3 Métodos e Técnicas
[Detalhar métodos qualitativos e quantitativos. Indicar software (R, Python, Stata, etc.)]

### 3.4 Análise dos Dados
[Descrever plano analítico: estatística descritiva, inferencial, modelagem]

### 3.5 Limitações Metodológicas Esperadas
[Antecipar limitações e estratégias de mitigação]

## 4. Cronograma de Execução

| Atividade | Meses |
|-----------|-------|
| ...       | 1-3   |
| ...       | 4-6   |
| ...       | ...   |

## 5. Equipe

{team}

## 6. Orçamento Resumido

[Resumo do orçamento detalhado em anexo]

## 7. Referências Bibliográficas

[ABNT NBR 6023:2018 — todas as citações devem ter DOI verificável]

---

**Pesquisador Responsável:** {researcher}
**Instituição Executora:** {institution}
**Data de submissão:** {submission_date}
"""


def draft_proposal(
    *,
    title: str,
    researcher: str,
    institution: str,
    keywords: list[str],
    grant: Optional[Grant] = None,
    budget: Optional[Budget] = None,
    team: Optional[list[str]] = None,
    duration_months: int = 24,
    language: str = "pt",
) -> str:
    """Gera minuta estruturada de uma proposta de fomento.

    Args:
        title: Título do projeto.
        researcher: Nome do pesquisador responsável.
        institution: Instituição de vínculo.
        keywords: 3 a 6 palavras-chave.
        grant: Edital-alvo (opcional; adapta linguagem).
        budget: Orçamento gerado (opcional; insere resumo).
        team: Lista de membros da equipe.
        duration_months: Duração em meses.
        language: Idioma da minuta ("pt" ou "en").

    Returns:
        String Markdown com a minuta pronta para revisão.
    """
    if language == "en":
        return _draft_proposal_en(
            title=title, researcher=researcher, institution=institution,
            keywords=keywords, grant=grant, budget=budget, team=team,
            duration_months=duration_months,
        )

    template_file = TEMPLATES_DIR / "proposal_pt.md"
    if template_file.exists():
        template = template_file.read_text(encoding="utf-8")
    else:
        template = DEFAULT_PROPOSAL_PT

    team_str = "\n".join(f"- {member}" for member in (team or [researcher]))

    proposal = template.format(
        title=title,
        keywords=", ".join(keywords),
        team=team_str,
        researcher=researcher,
        institution=institution,
        submission_date=date.today().isoformat(),
    )

    # Adapta para o edital, se informado
    if grant:
        proposal += f"\n\n---\n\n## Anexo: Edital-Alvo\n\n- **Agência:** {grant.agency}\n"
        if grant.amount_max:
            proposal += f"- **Teto disponível:** {grant.currency} {grant.amount_max:,.0f}\n"
        if grant.close_date:
            proposal += f"- **Data de fechamento:** {grant.close_date}\n"
        if grant.url:
            proposal += f"- **Link do edital:** {grant.url}\n"

    # Anexa orçamento
    if budget:
        proposal += "\n\n---\n\n## Anexo: Orçamento Detalhado\n\n"
        proposal += budget.to_markdown()

    return proposal


def _draft_proposal_en(
    *,
    title: str,
    researcher: str,
    institution: str,
    keywords: list[str],
    grant: Optional[Grant],
    budget: Optional[Budget],
    team: Optional[list[str]],
    duration_months: int,
) -> str:
    """Versão em inglês (esqueleto)."""
    parts: list[str] = [
        f"# {title}",
        "",
        "## Abstract",
        "",
        "[Up to 500 words: problem, methodology, expected results, impact.]",
        "",
        f"**Keywords:** {', '.join(keywords)}",
        "",
        "## 1. Background and Significance",
        "[State of the art, gap, contribution. Minimum 5 verifiable references with DOI.]",
        "",
        "## 2. Objectives",
        "### 2.1 General Objective",
        "### 2.2 Specific Objectives",
        "",
        "## 3. Methodology",
        "### 3.1 Study Area",
        "### 3.2 Data Sources",
        "### 3.3 Methods",
        "### 3.4 Data Analysis",
        "### 3.5 Methodological Limitations",
        "",
        f"## 4. Timeline ({duration_months} months)",
        "",
        "## 5. Team",
        "",
    ]
    parts.extend(f"- {m}" for m in (team or [researcher]))
    parts.extend([
        "",
        f"**PI:** {researcher}",
        f"**Institution:** {institution}",
        f"**Submission date:** {date.today().isoformat()}",
    ])

    if grant:
        parts.extend([
            "",
            "---",
            "",
            "## Annex: Target Call",
            "",
            f"- **Agency:** {grant.agency}",
            f"- **Country:** {grant.country}",
        ])
        if grant.amount_max:
            parts.append(f"- **Funding cap:** {grant.currency} {grant.amount_max:,.0f}")
        if grant.close_date:
            parts.append(f"- **Deadline:** {grant.close_date}")
        if grant.url:
            parts.append(f"- **URL:** {grant.url}")

    if budget:
        parts.extend(["", "---", "", "## Annex: Detailed Budget", "", budget.to_markdown()])

    return "\n".join(parts)


def make_timeline(duration_months: int, activities: list[str]) -> str:
    """Gera um cronograma em formato de tabela Markdown.

    Args:
        duration_months: Duração total em meses.
        activities: Lista de atividades (uma por linha).

    Returns:
        Tabela Markdown com matriz atividade × trimestre.
    """
    quarters = (duration_months + 2) // 3  # arredonda para cima
    header: list[str] = ["#", "Atividade"] + [f"T{i+1}" for i in range(quarters)]
    lines: list[str] = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for i, act in enumerate(activities, 1):
        # Distribui atividades linearmente nos trimestres como placeholder
        cells = [" "] * quarters
        if quarters > 0:
            start = (i - 1) * quarters // max(1, len(activities))
            end = min(quarters, start + max(1, quarters // max(1, len(activities))))
            for q in range(start, end):
                cells[q] = "X"
        lines.append(f"| {i} | {act} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
