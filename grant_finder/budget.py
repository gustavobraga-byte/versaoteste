"""
budget.py — Geração de orçamentos para propostas de fomento.

Implementa:
  - Budget: dataclass de orçamento com rubricas
  - generate_budget(): cria orçamento baseado em rubricas da agência

As rubricas seguem o padrão brasileiro:
  - Custeio (consumo, serviços, diárias, passagens)
  - Capital (equipamentos, material permanente)
  - Bolsas (modalidades conforme agência)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import Optional


class ExpenseType(str, Enum):
    """Tipos de despesa."""
    CONSUMABLE = "consumo"  # material de consumo
    SERVICES = "servicos"   # serviços de terceiros
    TRAVEL = "passagens_diarias"  # passagens e diárias
    EQUIPMENT = "equipamento"  # capital
    SOFTWARE = "software"   # licenças
    PUBLICATION = "publicacao"  # taxas de publicação
    SCHOLARSHIP = "bolsa"  # bolsas
    OTHER = "outros"


class Agency(str, Enum):
    """Agências com rubricas específicas."""
    CNPQ = "CNPq"
    CAPES = "CAPES"
    FAPEMIG = "FAPEMIG"
    FAPESP = "FAPESP"
    FINEP = "FINEP"
    GENERIC = "GENERIC"


# ── Tabelas de bolsas (valores mensais em BRL, 2024) ─────────────
# [DADO REFERENCIAL] Valores médios por modalidade. Sempre conferir
# a portaria vigente da agência no momento da submissão.

SCHOLARSHIP_TABLE_BR_2024: dict[str, dict[str, float]] = {
    "CNPq": {
        "iniciacao_cientifica": 700.00,
        "mestrado": 2100.00,
        "doutorado": 3200.00,
        "pos_doutorado_junior": 5100.00,
        "pos_doutorado_senior": 6200.00,
    },
    "CAPES": {
        "mestrado": 2100.00,
        "doutorado": 3100.00,
        "pos_doutorado": 5200.00,
    },
    "FAPEMIG": {
        "iniciacao_cientifica": 600.00,
        "mestrado": 1900.00,
        "doutorado": 2900.00,
        "pos_doutorado": 4500.00,
    },
}


@dataclass
class BudgetItem:
    """Item individual do orçamento."""
    description: str
    expense_type: ExpenseType
    quantity: float
    unit_value: float
    total: float = 0.0
    justification: str = ""

    def __post_init__(self) -> None:
        if self.total == 0.0:
            self.total = self.quantity * self.unit_value


@dataclass
class Budget:
    """Orçamento completo de uma proposta."""
    agency: Agency
    project_title: str
    duration_months: int
    items: list[BudgetItem] = field(default_factory=list)
    currency: str = "BRL"
    notes: str = ""

    def total(self) -> float:
        return sum(i.total for i in self.items)

    def by_category(self) -> dict[str, float]:
        """Total agrupado por tipo de despesa."""
        result: dict[str, float] = {}
        for item in self.items:
            key = item.expense_type.value
            result[key] = result.get(key, 0.0) + item.total
        return result

    def to_dict(self) -> dict:
        return {
            "agency": self.agency.value,
            "project_title": self.project_title,
            "duration_months": self.duration_months,
            "currency": self.currency,
            "items": [asdict(i) for i in self.items],
            "total": self.total(),
            "by_category": self.by_category(),
            "notes": self.notes,
        }

    def to_markdown(self) -> str:
        """Renderiza orçamento em tabela Markdown."""
        lines: list[str] = [
            f"# Orçamento — {self.project_title}",
            "",
            f"- **Agência:** {self.agency.value}",
            f"- **Duração:** {self.duration_months} meses",
            f"- **Moeda:** {self.currency}",
            f"- **Total:** {self.currency} {self.total():,.2f}",
            "",
            "| # | Descrição | Tipo | Qtd | Valor Unit. | Total | Justificativa |",
            "|---|-----------|------|-----|-------------|-------|---------------|",
        ]
        for i, item in enumerate(self.items, 1):
            lines.append(
                f"| {i} | {item.description} | {item.expense_type.value} | "
                f"{item.quantity:g} | {item.unit_value:,.2f} | {item.total:,.2f} | "
                f"{item.justification[:60]} |"
            )
        lines.append("")
        lines.append("## Totais por Categoria")
        lines.append("")
        for cat, total in sorted(self.by_category().items()):
            lines.append(f"- **{cat}:** {self.currency} {total:,.2f}")
        if self.notes:
            lines.append("")
            lines.append("## Observações")
            lines.append(self.notes)
        return "\n".join(lines)


def _default_scholarship_value(agency: Agency, level: str) -> Optional[float]:
    """Retorna valor de bolsa padrão para uma agência/nível."""
    table = SCHOLARSHIP_TABLE_BR_2024.get(agency.value, {})
    return table.get(level)


def generate_budget(
    agency: Agency | str,
    project_title: str,
    duration_months: int,
    *,
    consumables: Optional[list[tuple[str, float, str]]] = None,
    equipment: Optional[list[tuple[str, float, str]]] = None,
    services: Optional[list[tuple[str, float, str]]] = None,
    travel: Optional[list[tuple[str, float, int, str]]] = None,
    scholarships: Optional[list[tuple[str, str, int]]] = None,
    publications: Optional[list[tuple[str, float, int, str]]] = None,
    other: Optional[list[tuple[str, float, str]]] = None,
    notes: str = "",
) -> Budget:
    """Gera um orçamento estruturado.

    Args:
        agency: Agência financiadora.
        project_title: Título do projeto.
        duration_months: Duração em meses.
        consumables: Lista (descrição, valor_total, justificativa).
        equipment: Lista (descrição, valor, justificativa) — capital.
        services: Lista (descrição, valor_total, justificativa) — serviços PJ.
        travel: Lista (descrição, valor_unit, quantidade, justificativa).
        scholarships: Lista (descrição, nível, meses) — ex: ("Bolsista IC", "iniciacao_cientifica", 12).
        publications: Lista (descrição, valor_unit, quantidade, justificativa).
        other: Lista (descrição, valor, justificativa).
        notes: Observações gerais.

    Returns:
        Budget completo e estruturado.

    Examples:
        >>> budget = generate_budget(
        ...     agency="CNPq",
        ...     project_title="Análise da biodiversidade do Cerrado",
        ...     duration_months=24,
        ...     consumables=[
        ...         ("Reagentes de laboratório", 5000, "PCR, sequenciamento"),
        ...         ("Material de campo", 3000, "Coleta de amostras"),
        ...     ],
        ...     equipment=[
        ...         ("Microscópio estereoscópio", 12000, "Triagem de amostras"),
        ...     ],
        ...     scholarships=[
        ...         ("Bolsista IC", "iniciacao_cientifica", 12),
        ...         ("Bolsista Mestrado", "mestrado", 24),
        ...     ],
        ... )
        >>> budget.total()
        57100.0
    """
    if isinstance(agency, str):
        try:
            agency = Agency(agency)
        except ValueError:
            agency = Agency.GENERIC

    items: list[BudgetItem] = []

    for desc, value, justif in (consumables or []):
        items.append(BudgetItem(
            description=desc, expense_type=ExpenseType.CONSUMABLE,
            quantity=1, unit_value=value, justification=justif,
        ))

    for desc, value, justif in (equipment or []):
        items.append(BudgetItem(
            description=desc, expense_type=ExpenseType.EQUIPMENT,
            quantity=1, unit_value=value, justification=justif,
        ))

    for desc, value, justif in (services or []):
        items.append(BudgetItem(
            description=desc, expense_type=ExpenseType.SERVICES,
            quantity=1, unit_value=value, justification=justif,
        ))

    for desc, value, qty, justif in (travel or []):
        items.append(BudgetItem(
            description=desc, expense_type=ExpenseType.TRAVEL,
            quantity=qty, unit_value=value, justification=justif,
        ))

    for desc, level, months in (scholarships or []):
        monthly = _default_scholarship_value(agency, level) or 0.0
        items.append(BudgetItem(
            description=f"{desc} ({level}, {months} meses)",
            expense_type=ExpenseType.SCHOLARSHIP,
            quantity=months, unit_value=monthly,
            justification=f"Baseado em tabela de bolsas {agency.value}",
        ))

    for desc, value, qty, justif in (publications or []):
        items.append(BudgetItem(
            description=desc, expense_type=ExpenseType.PUBLICATION,
            quantity=qty, unit_value=value, justification=justif,
        ))

    for desc, value, justif in (other or []):
        items.append(BudgetItem(
            description=desc, expense_type=ExpenseType.OTHER,
            quantity=1, unit_value=value, justification=justif,
        ))

    return Budget(
        agency=agency, project_title=project_title,
        duration_months=duration_months, items=items, notes=notes,
    )
