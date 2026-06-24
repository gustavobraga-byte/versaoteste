"""
fapesp.py — Fetcher de editais da FAPESP (Fundação de Amparo à Pesquisa
do Estado de São Paulo).
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


FAPESP_URL: str = "https://fapesp.br/oportunidades/"


class FapespFetcher(GrantFetcher):
    agency = "FAPESP"
    country = "BR"

    def fetch_open_grants(self) -> list[Grant]:
        if not _HAS_HTTP:
            return []
        return [Grant(
            id="fapesp-oportunidades",
            title="FAPESP — Oportunidades de Fomento",
            agency="FAPESP",
            country="BR",
            description=(
                "A FAPESP mantém chamadas contínuas em várias modalidades "
                "(Pesquisa Regular, Jovem Pesquisador, Temático, PIPE, SPEC, "
                "Bolsa, Auxílio-Participação em Reunião, entre outras). "
                "Consulte o portal para editais vigentes."
            ),
            url=FAPESP_URL,
            status=GrantStatus.OPEN,
            eligible_states=["SP"],
            language="pt",
            fetched_at=date.today().isoformat(),
        )]
