"""
grant_finder — Skill de busca e gestão de fomento à pesquisa.

Esta skill ajuda pesquisadores a:
  - Buscar editais abertos em agências brasileiras (CNPq, CAPES, FAPs, FINEP)
    e internacionais (NIH, NSF, ERC, Wellcome, Horizon Europe)
  - Verificar elegibilidade com base no perfil do pesquisador
  - Gerar orçamento conforme rubricas da agência
  - Elaborar minutas de propostas com seções padrão

Uso programático:
    from grant_finder import GrantFinder, ResearcherProfile, search_grants

    profile = ResearcherProfile(
        name="Maria Silva",
        degree="doutorado",
        institution="UFV",
        area="Agronomia",
        state="MG",
        is_PI=True,
    )
    results = search_grants(profile, country="BR", amount_min=10_000)

Uso via PesquisAI:
    "Busque editais abertos da FAPEMIG para pesquisador doutor em Agronomia
     com até R$ 100 mil."

Integridade científica:
    - SEMPRE declarar data da consulta à fonte.
    - NUNCA inventar prazos, valores ou requisitos. Se a API retornar dado
      parcial, declarar explicitamente.
    - Editais mudam: sempre conferir link oficial antes de submeter.
"""

from .matcher import (
    Grant,
    GrantStatus,
    ResearcherProfile,
    EligibilityReport,
    Degree,
    search_grants,
    check_eligibility,
    GrantFinder,
)
from .budget import Budget, generate_budget, Agency, ExpenseType
from .proposal import draft_proposal, make_timeline

__version__ = "0.1.0"
__all__ = [
    "Grant",
    "GrantStatus",
    "ResearcherProfile",
    "EligibilityReport",
    "Degree",
    "search_grants",
    "check_eligibility",
    "GrantFinder",
    "Budget",
    "Agency",
    "ExpenseType",
    "generate_budget",
    "draft_proposal",
    "make_timeline",
]
