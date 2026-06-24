"""
cnpq.py — Fetcher de editais do CNPq (Conselho Nacional de Desenvolvimento
Científico e Tecnológico).

Fonte: https://www.gov.br/cnpq/pt-br/assuntos/editais

O CNPq não expõe API pública estruturada para editais. Esta implementação
lê a página de editais e extrai metadados básicos. Se a página mudar,
retornará lista vazia e o sistema usará o cache local com data explícita.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
    _HAS_HTTP = True
except ImportError:
    _HAS_HTTP = False

from ..matcher import Grant, GrantStatus, Degree
from . import GrantFetcher


CNPQ_URL: str = "https://www.gov.br/cnpq/pt-br/assuntos/editais"
TIMEOUT: int = 15


class CNPqFetcher(GrantFetcher):
    agency = "CNPq"
    country = "BR"

    def fetch_open_grants(self) -> list[Grant]:
        if not _HAS_HTTP:
            return []
        try:
            r = requests.get(CNPQ_URL, timeout=TIMEOUT, headers={"User-Agent": "PesquisAI/0.1"})
            r.raise_for_status()
        except Exception:
            return []

        return self._parse_html(r.text)

    def _parse_html(self, html: str) -> list[Grant]:
        if not _HAS_HTTP:
            return []
        soup = BeautifulSoup(html, "html.parser")
        grants: list[Grant] = []
        # Procura por links que pareçam editais
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]
            if not text or len(text) < 10:
                continue
            if "edital" not in text.lower() and "chamada" not in text.lower():
                continue
            url = urljoin(CNPQ_URL, href)
            if "cnpq" not in url and "gov.br" not in url:
                continue
            # Inferência rudimentar de status
            status = GrantStatus.OPEN
            lower = text.lower()
            if any(w in lower for w in ["encerrado", "fechado", "resultado final"]):
                status = GrantStatus.CLOSED
            elif any(w in lower for w in ["previsto", "em breve", "abertura em"]):
                status = GrantStatus.UPCOMING

            grants.append(Grant(
                id=f"cnpq-{abs(hash(url)) % 10**8}",
                title=text[:200],
                agency="CNPq",
                country="BR",
                description="Editado no portal do CNPq. Verificar regras específicas.",
                url=url,
                status=status,
                language="pt",
                fetched_at=date.today().isoformat(),
            ))
        return grants[:50]  # limita para evitar sobrecarga
