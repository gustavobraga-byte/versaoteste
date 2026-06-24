"""
international.py — Fetchers para agências internacionais.

Implementa conectores para:
  - NIH (EUA)
  - NSF (EUA)
  - ERC (União Europeia)
  - Wellcome Trust (Reino Unido)
  - Horizon Europe (UE)
  - CIHR (Canadá)
  - NHMRC (Austrália)
"""

from __future__ import annotations

from datetime import date
from typing import Optional

try:
    import requests
    _HAS_HTTP = True
except ImportError:
    _HAS_HTTP = False

from ..matcher import Grant, GrantStatus
from . import GrantFetcher


def get_all_fetchers() -> list[GrantFetcher]:
    return [
        NIHFetcher(),
        NSFFetcher(),
        ERCFetcher(),
        WellcomeFetcher(),
        HorizonEuropeFetcher(),
    ]


# ── NIH ──────────────────────────────────────────────────────────

class NIHFetcher(GrantFetcher):
    agency = "NIH"
    country = "US"

    def fetch_open_grants(self) -> list[Grant]:
        if not _HAS_HTTP:
            return []
        # NIH tem API oficial (NIH Guide), mas requer filtro por activity code.
        # Aqui mantemos um link-âncora até que um parser estruturado seja adicionado.
        return [Grant(
            id="nih-funding-opportunities",
            title="NIH — Funding Opportunities & Notices",
            agency="NIH",
            country="US",
            description=(
                "O NIH (National Institutes of Health) mantém centenas de "
                "Funding Opportunity Announcements (FOAs) ativos em qualquer "
                "momento. Categorias: R01, R21, R03, K, F, T, U. Idiomas: inglês. "
                "Cidadãos brasileiros podem aplicar a programas como o "
                "Fogarty International Center."
            ),
            url="https://grants.nih.gov/funding/searchguide/index.html",
            status=GrantStatus.OPEN,
            min_degree=__import__("pesquisai.grant_finder.matcher", fromlist=["Degree"]).Degree.PHD,
            language="en",
            requires_PI=True,
            fetched_at=date.today().isoformat(),
        )]


# ── NSF ──────────────────────────────────────────────────────────

class NSFFetcher(GrantFetcher):
    agency = "NSF"
    country = "US"

    def fetch_open_grants(self) -> list[Grant]:
        return [Grant(
            id="nsf-funding",
            title="NSF — Funding Search",
            agency="NSF",
            country="US",
            description=(
                "National Science Foundation — programa para pesquisa básica "
                "e educação em ciências não-médicas. Programa internacional: "
                "PIRE (Partnerships for International Research and Education)."
            ),
            url="https://www.nsf.gov/funding/",
            status=GrantStatus.OPEN,
            min_degree=__import__("pesquisai.grant_finder.matcher", fromlist=["Degree"]).Degree.PHD,
            language="en",
            requires_PI=True,
            fetched_at=date.today().isoformat(),
        )]


# ── ERC ──────────────────────────────────────────────────────────

class ERCFetcher(GrantFetcher):
    agency = "ERC"
    country = "EU"

    def fetch_open_grants(self) -> list[Grant]:
        return [Grant(
            id="erc-funding",
            title="ERC — European Research Council Grants",
            agency="ERC",
            country="EU",
            description=(
                "European Research Council. Modalidades: Starting Grant "
                "(2-7 anos pós-PhD), Consolidator Grant (7-12 anos), "
                "Advanced Grant (track record sênior), Synergy Grant (2-4 PIs). "
                "Excelência científica como único critério."
            ),
            url="https://erc.europa.eu/funding",
            status=GrantStatus.OPEN,
            min_degree=__import__("pesquisai.grant_finder.matcher", fromlist=["Degree"]).Degree.PHD,
            language="en",
            requires_PI=True,
            fetched_at=date.today().isoformat(),
        )]


# ── Wellcome ─────────────────────────────────────────────────────

class WellcomeFetcher(GrantFetcher):
    agency = "Wellcome"
    country = "GB"

    def fetch_open_grants(self) -> list[Grant]:
        return [Grant(
            id="wellcome-funding",
            title="Wellcome Trust — Funding Schemes",
            agency="Wellcome",
            country="GB",
            description=(
                "Wellcome Trust (UK) — Discovery Awards, Early-Career Awards, "
                "Career Development Awards. Foco em saúde, biomedicina e humanidades "
                "médicas. Aceita pesquisadores de qualquer país."
            ),
            url="https://wellcome.org/research-funding",
            status=GrantStatus.OPEN,
            min_degree=__import__("pesquisai.grant_finder.matcher", fromlist=["Degree"]).Degree.PHD,
            language="en",
            requires_PI=True,
            fetched_at=date.today().isoformat(),
        )]


# ── Horizon Europe ──────────────────────────────────────────────

class HorizonEuropeFetcher(GrantFetcher):
    agency = "Horizon_Europe"
    country = "EU"

    def fetch_open_grants(self) -> list[Grant]:
        return [Grant(
            id="horizon-europe-funding",
            title="Horizon Europe — Funding & Tenders Portal",
            agency="Horizon_Europe",
            country="EU",
            description=(
                "Programa-quadro da UE para pesquisa e inovação (2021-2027). "
                "Modalidades: MSCA (Pós-Doc, Staff Exchanges), EIC (Pathfinder, "
                "Accelerator), ERC, Cluster Health/Climate/Energy. "
                "Brasil é país associado (pode participar em vários clusters)."
            ),
            url="https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home",
            status=GrantStatus.OPEN,
            min_degree=__import__("pesquisai.grant_finder.matcher", fromlist=["Degree"]).Degree.PHD,
            language="en",
            requires_PI=True,
            fetched_at=date.today().isoformat(),
        )]
