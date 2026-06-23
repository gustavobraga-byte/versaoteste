"""
capes.py — Fetcher de editais da CAPES (Coordenação de Aperfeiçoamento
de Pessoal de Nível Superior).

Fonte: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas
"""

from __future__ import annotations

from datetime import date
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
    _HAS_HTTP = True
except ImportError:
    _HAS_HTTP = False

from ..matcher import Grant, GrantStatus
from . import GrantFetcher


CAPES_URL: str = "https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/programas"
TIMEOUT: int = 15


class CapesFetcher(GrantFetcher):
    agency = "CAPES"
    country = "BR"

    def fetch_open_grants(self) -> list[Grant]:
        if not _HAS_HTTP:
            return []
        try:
            r = requests.get(CAPES_URL, timeout=TIMEOUT, headers={"User-Agent": "PesquisAI/0.1"})
            r.raise_for_status()
        except Exception:
            return []

        grants: list[Grant] = []
        soup = BeautifulSoup(r.text, "html.parser")
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]
            if not text or len(text) < 10:
                continue
            if not any(w in text.lower() for w in ["edital", "chamada", "programa", "capes"]):
                continue
            if "capes.gov.br" not in href and "gov.br" not in href:
                continue

            grants.append(Grant(
                id=f"capes-{abs(hash(href)) % 10**8}",
                title=text[:200],
                agency="CAPES",
                country="BR",
                description="Programa ou edital da CAPES. Conferir regras específicas.",
                url=href,
                status=GrantStatus.OPEN,
                language="pt",
                fetched_at=date.today().isoformat(),
            ))
        return grants[:50]
