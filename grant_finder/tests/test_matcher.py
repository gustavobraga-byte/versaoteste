"""Tests para o matcher da skill grant_finder."""

import json
import pytest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, mock_open

from grant_finder.matcher import (
    Degree, Grant, GrantStatus, ResearcherProfile,
    EligibilityReport, check_eligibility, search_grants, _DEGREE_RANK,
)


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def profile_phd_mg():
    return ResearcherProfile(
        name="Maria Silva",
        degree=Degree.PHD,
        institution="UFV",
        area="Ciências Agrárias",
        state="MG",
        is_PI=True,
        years_since_phd=5,
        publications_count=15,
        keywords=["agricultura", "semiárido"],
        orcid="0000-0000-0000-0000",
    )


@pytest.fixture
def profile_msc_sp():
    return ResearcherProfile(
        name="João Souza",
        degree=Degree.MASTER,
        institution="USP",
        area="Engenharia",
        state="SP",
        is_PI=False,
    )


@pytest.fixture
def sample_grant_cnpq():
    return Grant(
        id="test-001",
        title="Chamada Universal CNPq 2026",
        agency="CNPq",
        country="BR",
        description="Fomento à pesquisa em todas as áreas",
        url="https://example.com/cnpq",
        amount_min=30000,
        amount_max=120000,
        currency="BRL",
        open_date="2026-05-15",
        close_date=(date.today() + timedelta(days=45)).isoformat(),
        status=GrantStatus.OPEN,
        min_degree=Degree.PHD,
        requires_PI=True,
        language="pt",
    )


@pytest.fixture
def sample_grant_fapemig_mg():
    return Grant(
        id="test-002",
        title="FAPEMIG Demanda Universal",
        agency="FAPEMIG",
        country="BR",
        description="Pesquisa em MG",
        url="https://example.com/fapemig",
        amount_min=5000,
        amount_max=150000,
        currency="BRL",
        close_date=(date.today() + timedelta(days=60)).isoformat(),
        status=GrantStatus.OPEN,
        eligible_states=["MG"],
        min_degree=Degree.PHD,
        requires_PI=True,
    )


@pytest.fixture
def sample_grant_nih():
    return Grant(
        id="test-003",
        title="NIH R01",
        agency="NIH",
        country="US",
        description="Pesquisa biomédica nos EUA",
        url="https://example.com/nih",
        amount_min=250000,
        amount_max=2500000,
        currency="USD",
        close_date=(date.today() + timedelta(days=120)).isoformat(),
        status=GrantStatus.OPEN,
        min_degree=Degree.PHD,
        language="en",
        requires_PI=True,
    )


# ── Testes de ResearcherProfile ────────────────────────────────

class TestResearcherProfile:
    def test_creation_with_enum(self):
        p = ResearcherProfile(name="X", degree=Degree.PHD, institution="UFV", area="X")
        assert p.degree == Degree.PHD

    def test_creation_with_string(self):
        p = ResearcherProfile(name="X", degree="doutorado", institution="UFV", area="X")
        assert p.degree == Degree.PHD

    def test_state_normalized_to_upper(self):
        p = ResearcherProfile(name="X", degree="doutorado", institution="UFV", area="X", state="mg")
        assert p.state == "MG"

    def test_invalid_degree_raises(self):
        with pytest.raises(ValueError):
            ResearcherProfile(name="X", degree="invalid", institution="UFV", area="X")


# ── Testes de Grant ─────────────────────────────────────────────

class TestGrant:
    def test_is_open_true(self, sample_grant_cnpq):
        assert sample_grant_cnpq.is_open() is True

    def test_days_to_close(self, sample_grant_cnpq):
        days = sample_grant_cnpq.days_to_close()
        assert days is not None
        assert 40 <= days <= 50

    def test_is_open_false_when_closed(self):
        g = Grant(
            id="x", title="X", agency="X", country="BR", description="X", url="X",
            status=GrantStatus.CLOSED,
        )
        assert g.is_open() is False

    def test_days_to_close_when_no_date(self):
        g = Grant(
            id="x", title="X", agency="X", country="BR", description="X", url="X",
        )
        assert g.days_to_close() is None

    def test_days_to_close_with_invalid_date(self):
        g = Grant(
            id="x", title="X", agency="X", country="BR", description="X", url="X",
            close_date="invalid",
        )
        assert g.days_to_close() is None


# ── Testes de elegibilidade ────────────────────────────────────

class TestCheckEligibility:
    def test_phd_eligible_for_cnpq(self, profile_phd_mg, sample_grant_cnpq):
        report = check_eligibility(sample_grant_cnpq, profile_phd_mg)
        assert report.is_eligible is True
        assert report.score >= 0.8
        assert any("Titulação" in r or "Brasil" in r for r in report.reasons)

    def test_msc_not_eligible_for_cnpq(self, profile_msc_sp, sample_grant_cnpq):
        report = check_eligibility(sample_grant_cnpq, profile_msc_sp)
        assert report.is_eligible is False
        assert any("doutorado" in r.lower() for r in report.reasons)

    def test_br_profile_not_eligible_for_us_grant(self, profile_phd_mg, sample_grant_nih):
        report = check_eligibility(sample_grant_nih, profile_phd_mg)
        assert report.is_eligible is False
        assert any("restrito" in r.lower() for r in report.reasons)

    def test_mg_profile_eligible_for_fapemig(self, profile_phd_mg, sample_grant_fapemig_mg):
        report = check_eligibility(sample_grant_fapemig_mg, profile_phd_mg)
        assert report.is_eligible is True

    def test_sp_profile_warning_for_fapemig(self, profile_msc_sp, sample_grant_fapemig_mg):
        # MSc não é elegível por titulação, mas também tem warning de UF
        report = check_eligibility(sample_grant_fapemig_mg, profile_msc_sp)
        # Como o perfil MSc falha em titulação, o report não chega à verificação de UF
        # mas se fosse PHD em SP, teríamos warning. Vamos testar com PHD-SP:
        phd_sp = ResearcherProfile(
            name="X", degree=Degree.PHD, institution="USP", area="Eng", state="SP", is_PI=True,
        )
        report_phd = check_eligibility(sample_grant_fapemig_mg, phd_sp)
        assert any("MG" in w or "UF" in w for w in report_phd.warnings)

    def test_non_pi_for_pi_grant(self, profile_msc_sp, sample_grant_cnpq):
        # Mesmo sendo MSc, o aviso de não-PI seria gerado se passasse nos outros filtros
        # Como MSc já bloqueia, vamos testar com PHD não-PI
        profile = ResearcherProfile(
            name="X", degree=Degree.PHD, institution="UFV", area="X", is_PI=False,
        )
        report = check_eligibility(sample_grant_cnpq, profile)
        assert any("PI" in r or "Principal" in r for r in report.reasons)

    def test_warning_for_closing_soon(self, profile_phd_mg):
        g = Grant(
            id="x", title="X", agency="X", country="BR", description="X", url="X",
            status=GrantStatus.OPEN,
            min_degree=Degree.PHD,
            close_date=(date.today() + timedelta(days=3)).isoformat(),
        )
        report = check_eligibility(g, profile_phd_mg)
        assert any("ATENÇÃO" in w or "dias" in w for w in report.warnings)
        assert any("Iniciar" in a for a in report.required_actions)

    def test_warning_for_missing_orcid_and_lattes(self, profile_phd_mg):
        profile_phd_mg.orcid = None
        profile_phd_mg.lattes_id = None
        g = Grant(
            id="x", title="X", agency="X", country="BR", description="X", url="X",
            status=GrantStatus.OPEN,
            min_degree=Degree.PHD,
        )
        report = check_eligibility(g, profile_phd_mg)
        assert any("ORCID" in w or "Lattes" in w for w in report.warnings)


# ── Testes de search_grants ─────────────────────────────────────

class TestSearchGrants:
    def test_search_br_returns_list(self, profile_phd_mg):
        # Pode retornar vazio se cache vazio, mas não pode dar erro
        grants = search_grants(profile=profile_phd_mg, country="BR")
        assert isinstance(grants, list)

    def test_search_filters_by_amount(self, profile_phd_mg):
        grants = search_grants(
            profile=profile_phd_mg, country="BR",
            amount_min=1_000_000,  # valor muito alto
        )
        # Não deve retornar editais menores
        for g in grants:
            assert g.amount_max is None or g.amount_max >= 1_000_000

    def test_search_filters_by_keywords(self, profile_phd_mg):
        grants = search_grants(
            profile=profile_phd_mg, country="BR",
            keywords=["xyzzy_impossivel_999"],
        )
        assert len(grants) == 0

    def test_search_without_profile(self):
        # Busca sem perfil deve funcionar (perfil=None)
        grants = search_grants(country="BR", profile=None)
        assert isinstance(grants, list)


# ── Testes de Degree ────────────────────────────────────────────

class TestDegreeRank:
    def test_phd_greater_than_master(self):
        assert _DEGREE_RANK[Degree.PHD] > _DEGREE_RANK[Degree.MASTER]

    def test_master_greater_than_undergrad(self):
        assert _DEGREE_RANK[Degree.MASTER] > _DEGREE_RANK[Degree.UNDERGRAD]

    def test_all_degrees_have_rank(self):
        for d in Degree:
            assert d in _DEGREE_RANK
            assert _DEGREE_RANK[d] > 0
