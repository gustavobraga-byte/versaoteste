"""Tests para proposal.py."""

import pytest
from datetime import date, timedelta

from grant_finder.budget import generate_budget
from grant_finder.matcher import Grant, GrantStatus, Degree
from grant_finder.proposal import draft_proposal, make_timeline


class TestDraftProposal:
    def test_minimal_proposal_pt(self):
        p = draft_proposal(
            title="Análise Teste",
            researcher="Maria Silva",
            institution="UFV",
            keywords=["x", "y"],
        )
        assert "# Análise Teste" in p
        assert "Maria Silva" in p
        assert "UFV" in p
        assert "Palavras-chave" in p
        assert "Resumo" in p
        assert "Objetivos" in p
        assert "Metodologia" in p
        assert "Cronograma" in p
        assert "Referências" in p

    def test_proposal_includes_team(self):
        p = draft_proposal(
            title="X", researcher="Y", institution="UFV",
            keywords=["a"], team=["Membro 1", "Membro 2"],
        )
        assert "- Membro 1" in p
        assert "- Membro 2" in p

    def test_proposal_includes_grant_info(self):
        g = Grant(
            id="x", title="Edital Teste", agency="CNPq", country="BR",
            description="X", url="https://example.com",
            amount_max=100000, currency="BRL",
            close_date="2026-12-31", status=GrantStatus.OPEN,
        )
        p = draft_proposal(
            title="X", researcher="Y", institution="UFV",
            keywords=["a"], grant=g,
        )
        assert "Anexo: Edital-Alvo" in p
        assert "CNPq" in p
        assert "https://example.com" in p

    def test_proposal_includes_budget(self):
        b = generate_budget(
            agency="CNPq", project_title="X", duration_months=12,
            consumables=[("Reagentes PCR para sequenciamento", 5000, "Análise molecular")],
        )
        p = draft_proposal(
            title="X", researcher="Y", institution="UFV",
            keywords=["a"], budget=b,
        )
        assert "Anexo: Orçamento Detalhado" in p
        # Verifica que a seção de orçamento está presente
        assert "Orçamento" in p
        assert "5,000" in p  # valor formatado

    def test_english_proposal(self):
        p = draft_proposal(
            title="Test Analysis", researcher="Maria Silva",
            institution="UFV", keywords=["a", "b"], language="en",
        )
        assert "# Test Analysis" in p
        assert "## Abstract" in p
        assert "## 1. Background" in p
        assert "## 3. Methodology" in p
        assert "PI:** Maria Silva" in p

    def test_default_team_is_just_researcher(self):
        p = draft_proposal(
            title="X", researcher="Maria", institution="UFV", keywords=["a"],
        )
        assert "- Maria" in p


class TestMakeTimeline:
    def test_basic_timeline(self):
        activities = ["Coleta de dados", "Análise", "Redação"]
        tl = make_timeline(duration_months=12, activities=activities)
        assert "| # | Atividade |" in tl
        assert "Coleta de dados" in tl
        assert "Análise" in tl
        assert "Redação" in tl

    def test_quarters_calculation(self):
        tl = make_timeline(duration_months=24, activities=["A", "B"])
        # 24/3 = 8 trimestres
        assert "T1" in tl
        assert "T8" in tl

    def test_single_activity(self):
        tl = make_timeline(duration_months=6, activities=["A única atividade"])
        assert "A única atividade" in tl

    def test_empty_activities(self):
        tl = make_timeline(duration_months=12, activities=[])
        assert "| Atividade" in tl  # cabeçalho
