"""
sources/ — Conectores com fontes oficiais de editais.

Cada módulo implementa uma interface comum: ``fetch_open_grants() -> list[Grant]``.

Quando uma API oficial não estiver disponível ou falhar, retornar lista
vazia — o matcher.py usará o cache local com data explícita.
"""

from __future__ import annotations

from typing import Optional

from ..matcher import Grant, GrantStatus


class GrantFetcher:
    """Interface base para fontes de editais."""

    agency: str = "GENERIC"
    country: str = "BR"

    def fetch_open_grants(self) -> list[Grant]:
        """Busca editais abertos na fonte oficial. Deve retornar [] em falha."""
        raise NotImplementedError


_REGISTRY: dict[str, GrantFetcher] = {}


def register(fetcher: GrantFetcher) -> None:
    """Registra um fetcher no registry."""
    _REGISTRY[fetcher.agency.upper()] = fetcher


def get_fetcher(agency: str) -> Optional[GrantFetcher]:
    """Retorna o fetcher registrado para a agência."""
    return _REGISTRY.get(agency.upper())


# ── Importações e registros (lazy) ───────────────────────────────

def _register_all() -> None:
    """Importa e registra todos os fetchers disponíveis."""
    if _REGISTRY:
        return
    try:
        from . import cnpq, capes, fapemig, fapesp, finep, international
        register(cnpq.CNPqFetcher())
        register(capes.CapesFetcher())
        register(fapemig.FapemigFetcher())
        register(fapesp.FapespFetcher())
        register(finep.FinepFetcher())
        for fetcher in international.get_all_fetchers():
            register(fetcher)
    except ImportError:
        # algum módulo não está disponível — registra só os que estão
        pass


# Força registro ao importar o pacote
_register_all()


__all__ = ["GrantFetcher", "get_fetcher", "register"]
