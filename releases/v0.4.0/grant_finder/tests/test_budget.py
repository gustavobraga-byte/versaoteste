"""Tests para budget.py."""

import pytest

from grant_finder.budget import (
    Budget, BudgetItem, ExpenseType, Agency,
    generate_budget, _default_scholarship_value,
)


class TestBudgetItem:
    def test_calculates_total(self):
        item = BudgetItem(
            description="X", expense_type=ExpenseType.CONSUMABLE,
            quantity=5, unit_value=100.0,
        )
        assert item.total == 500.0

    def test_keeps_explicit_total(self):
        item = BudgetItem(
            description="X", expense_type=ExpenseType.CONSUMABLE,
            quantity=5, unit_value=100.0, total=600.0,
        )
        assert item.total == 600.0


class TestGenerateBudget:
    def test_minimal_budget(self):
        b = generate_budget(
            agency="CNPq",
            project_title="Test",
            duration_months=12,
        )
        assert b.agency == Agency.CNPQ
        assert b.total() == 0
        assert b.duration_months == 12

    def test_with_consumables(self):
        b = generate_budget(
            agency="CNPq",
            project_title="Test",
            duration_months=12,
            consumables=[
                ("Reagentes", 5000, "PCR"),
                ("Material de campo", 3000, "Coleta"),
            ],
        )
        assert b.total() == 8000
        assert "consumo" in b.by_category()

    def test_with_equipment(self):
        b = generate_budget(
            agency="CNPq",
            project_title="Test",
            duration_months=12,
            equipment=[("Microscópio", 12000, "Triagem")],
        )
        assert b.total() == 12000
        assert b.by_category()["equipamento"] == 12000

    def test_with_scholarships(self):
        b = generate_budget(
            agency="CNPq",
            project_title="Test",
            duration_months=12,
            scholarships=[("Bolsista IC", "iniciacao_cientifica", 12)],
        )
        # 700/mês × 12 meses = 8400
        assert b.total() == 8400.0
        assert b.by_category()["bolsa"] == 8400.0

    def test_agency_string_parsed(self):
        b = generate_budget(
            agency="FAPEMIG",
            project_title="X",
            duration_months=12,
        )
        assert b.agency == Agency.FAPEMIG

    def test_unknown_agency_falls_back_to_generic(self):
        b = generate_budget(
            agency="AgenciaInventada",
            project_title="X",
            duration_months=12,
        )
        assert b.agency == Agency.GENERIC

    def test_to_markdown_contains_table(self):
        b = generate_budget(
            agency="CNPq",
            project_title="Análise Teste",
            duration_months=24,
            consumables=[("Reagentes", 5000, "PCR")],
        )
        md = b.to_markdown()
        assert "# Orçamento" in md
        assert "| " in md
        assert "Análise Teste" in md
        assert "Total" in md

    def test_to_dict_has_all_fields(self):
        b = generate_budget(
            agency="CNPq",
            project_title="X",
            duration_months=12,
            consumables=[("Y", 1000, "Z")],
        )
        d = b.to_dict()
        assert d["agency"] == "CNPq"
        assert d["project_title"] == "X"
        assert d["duration_months"] == 12
        assert d["total"] == 1000
        assert "items" in d
        assert "by_category" in d


class TestDefaultScholarshipValue:
    def test_cnpq_phd(self):
        v = _default_scholarship_value(Agency.CNPQ, "doutorado")
        assert v == 3200.00

    def test_cnpq_undergrad(self):
        v = _default_scholarship_value(Agency.CNPQ, "iniciacao_cientifica")
        assert v == 700.00

    def test_unknown_level_returns_none(self):
        v = _default_scholarship_value(Agency.CNPQ, "nivel_inventado")
        assert v is None

    def test_unknown_agency_returns_none(self):
        v = _default_scholarship_value(Agency.GENERIC, "doutorado")
        assert v is None
