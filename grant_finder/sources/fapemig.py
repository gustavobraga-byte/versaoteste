"""
fapemig.py — Fetcher de editais da FAPEMIG (Fundação de Amparo à Pesquisa
do Estado de Minas Gerais).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

try:
    import requests
    _HAS_HTTP = True
except ImportError:
    _HAS_HTTP = False

from ..matcher import Grant, GrantStatus, Degree
from . import GrantFetcher


FAPEMIG_URL: str = "http://www.fapemig.br/pt/menu_pt/editais/"
TIMEOUT: int = 15


class FapemigFetcher(GrantFetcher):
    agency = "FAPEMIG"
    country = "BR"

    def fetch_open_grants(self) -> list[Grant]:
        if not _HAS_HTTP:
            return []
        try:
            r = requests.get(FAPEMIG_URL, timeout=TIMEOUT, headers={"User-Agent": "PesquisAI/0.1"})
            r.raise_for_status()
        except Exception:
            return []
        # Implementação simplificada: FAPEMIG usa plataforma SUCUPIRA.
        # Aqui retornamos o link direto para a página de editais como
        # um edital-âncora que o usuário pode explorar.
        return [Grant(
            id="fapemig-portal-editais",
            title="FAPEMIG — Editais Abertos (consulte o portal)",
            agency="FAPEMIG",
            country="BR",
            description=(
                "Portal de editais da FAPEMIG. A FAPEMIG publica editais por meio "
                "de chamadas públicas temáticas (Demanda Universal, PPSUS, PIT, "
                "PEE, entre outros). Esta entrada aponta para o portal — sempre "
                "verificar os editais vigentes diretamente no site."
            ),
            url=FAPEMIG_URL,
            status=GrantStatus.OPEN,
            eligible_states=["MG"],
            language="pt",
            fetched_at=date.today().isoformat(),
        )]
