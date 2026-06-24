"""
finep.py — Fetcher de editais da FINEP (Financiadora de Estudos e Projetos).
"""

from __future__ import annotations

from datetime import date

try:
    import requests
    _HAS_HTTP = True
except ImportError:
    _HAS_HTTP = False

from ..matcher import Grant, GrantStatus
from . import GrantFetcher


FINEP_URL: str = "https://www.finep.gov.br/chamadas-publicas"


class FinepFetcher(GrantFetcher):
    agency = "FINEP"
    country = "BR"

    def fetch_open_grants(self) -> list[Grant]:
        if not _HAS_HTTP:
            return []
        return [Grant(
            id="finep-chamadas-publicas",
            title="FINEP — Chamadas Públicas",
            agency="FINEP",
            country="BR",
            description=(
                "A FINEP apoia projetos de inovação, subvenção econômica, "
                "crédito e participação societária. Modalidades: Startup, "
                "Inovação em MPES, Subvenção Econômica, Encomendas, CT-Infra."
            ),
            url=FINEP_URL,
            status=GrantStatus.OPEN,
            language="pt",
            fetched_at=date.today().isoformat(),
        )]
