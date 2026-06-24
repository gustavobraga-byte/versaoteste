"""
matcher.py — Núcleo de busca e elegibilidade de editais.

Implementa:
  - ResearcherProfile: dataclass com metadados do pesquisador
  - Grant: dataclass com metadados do edital
  - EligibilityReport: resultado da verificação de elegibilidade
  - search_grants(): ponto de entrada principal
  - GrantFinder: classe de alto nível com cache

Os editais são lidos de fontes oficiais via módulos em `sources/`.
Quando uma API não estiver disponível, usa dados cacheados em `data/`
com declaração explícita da data da última atualização.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Optional, Iterator

# ── Caminhos e constantes ────────────────────────────────────────

DATA_DIR: Path = Path(__file__).parent / "data"
CACHE_TTL_SECONDS: int = 24 * 60 * 60  # 24 horas

SUPPORTED_COUNTRIES: list[str] = ["BR", "US", "GB", "DE", "FR", "EU", "CA", "AU"]
SUPPORTED_AGENCIES_BR: list[str] = [
    "CNPq", "CAPES", "FAPEMIG", "FAPESP", "FAPERJ", "FAPERGS",
    "FAPEAL", "FAPEB", "FAPEPI", "FAPEAM", "FINEP", "BNDES",
]
SUPPORTED_AGENCIES_INTL: list[str] = [
    "NIH", "NSF", "ERC", "Wellcome", "Horizon_Europe", "CIHR", "NHMRC",
]


class Degree(str, Enum):
    """Nível de titulação do pesquisador."""
    UNDERGRAD = "graduacao"
    SPECIALIST = "especializacao"
    MASTER = "mestrado"
    PHD = "doutorado"
    POSTDOC = "pos_doutorado"


class GrantStatus(str, Enum):
    """Status do edital."""
    OPEN = "aberto"
    UPCOMING = "previsto"
    CLOSED = "encerrado"
    UNKNOWN = "desconhecido"


# ── Dataclasses ──────────────────────────────────────────────────


@dataclass
class ResearcherProfile:
    """Perfil do pesquisador para matching com editais."""
    name: str
    degree: Degree
    institution: str
    area: str  # ex: "Ciências Agrárias", "Engenharias"
    state: Optional[str] = None  # UF (sigla de 2 letras)
    country: str = "BR"
    is_PI: bool = True  # Pesquisador Principal?
    has_postdoc_supervision: bool = False
    years_since_phd: Optional[int] = None
    publications_count: Optional[int] = None
    keywords: list[str] = field(default_factory=list)
    orcid: Optional[str] = None
    lattes_id: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.degree, str):
            self.degree = Degree(self.degree)
        if self.state:
            self.state = self.state.upper()
        if self.country:
            self.country = self.country.upper()


@dataclass
class Grant:
    """Edital de fomento à pesquisa."""
    id: str
    title: str
    agency: str
    country: str
    description: str
    url: str
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    currency: str = "BRL"
    open_date: Optional[str] = None  # ISO 8601
    close_date: Optional[str] = None  # ISO 8601
    status: GrantStatus = GrantStatus.UNKNOWN
    min_degree: Optional[Degree] = None
    eligible_areas: list[str] = field(default_factory=list)
    eligible_states: list[str] = field(default_factory=list)  # UFs; vazio = todas
    requires_PI: Optional[bool] = None
    duration_months: Optional[int] = None
    language: str = "pt"
    source_query: Optional[str] = None
    fetched_at: Optional[str] = None  # ISO 8601

    def is_open(self) -> bool:
        """Verifica se o edital está aberto hoje."""
        if self.status != GrantStatus.OPEN:
            return False
        if not self.close_date:
            return True
        try:
            close = date.fromisoformat(self.close_date)
            return close >= date.today()
        except (ValueError, TypeError):
            return False

    def days_to_close(self) -> Optional[int]:
        """Dias restantes até o fechamento (None se já fechou ou sem data)."""
        if not self.close_date:
            return None
        try:
            close = date.fromisoformat(self.close_date)
            return (close - date.today()).days
        except (ValueError, TypeError):
            return None


@dataclass
class EligibilityReport:
    """Relatório de elegibilidade para um edital."""
    grant: Grant
    profile: ResearcherProfile
    is_eligible: bool
    score: float  # 0.0 a 1.0 — quão bem o perfil se encaixa
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "grant_id": self.grant.id,
            "grant_title": self.grant.title,
            "is_eligible": self.is_eligible,
            "score": round(self.score, 3),
            "reasons": self.reasons,
            "warnings": self.warnings,
            "required_actions": self.required_actions,
        }


# ── Verificação de elegibilidade ─────────────────────────────────


_DEGREE_RANK: dict[Degree, int] = {
    Degree.UNDERGRAD: 1,
    Degree.SPECIALIST: 2,
    Degree.MASTER: 3,
    Degree.PHD: 4,
    Degree.POSTDOC: 5,
}


def _area_matches(profile_area: str, eligible_areas: list[str]) -> bool:
    """Verifica correspondência entre área do pesquisador e elegíveis do edital."""
    if not eligible_areas:
        return True  # sem restrição
    pa = profile_area.lower()
    for ea in eligible_areas:
        if ea.lower() in pa or pa in ea.lower():
            return True
    return False


def _state_matches(profile_state: Optional[str], eligible_states: list[str]) -> bool:
    """Verifica correspondência de UF."""
    if not eligible_states or not profile_state:
        return True
    return profile_state.upper() in [s.upper() for s in eligible_states]


def check_eligibility(grant: Grant, profile: ResearcherProfile) -> EligibilityReport:
    """Avalia se um pesquisador é elegível para um edital.

    Retorna EligibilityReport com score (0-1), razões, avisos e ações necessárias.
    """
    reasons: list[str] = []
    warnings: list[str] = []
    actions: list[str] = []
    score = 1.0
    is_eligible = True

    # 1. Status do edital
    if not grant.is_open():
        is_eligible = False
        reasons.append(
            f"Edital não está aberto (status: {grant.status.value})."
        )
        return EligibilityReport(
            grant=grant, profile=profile, is_eligible=False,
            score=0.0, reasons=reasons, warnings=warnings, required_actions=actions,
        )

    # 2. País
    if grant.country and profile.country and grant.country != profile.country:
        is_eligible = False
        reasons.append(
            f"Edital restrito a {grant.country}; pesquisador está em {profile.country}."
        )
        return EligibilityReport(
            grant=grant, profile=profile, is_eligible=False,
            score=0.0, reasons=reasons, warnings=warnings, required_actions=actions,
        )
    if grant.country and profile.country and grant.country == profile.country:
        reasons.append(f"País compatível: {profile.country}.")

    # 3. Titulação mínima
    if grant.min_degree and profile.degree:
        if _DEGREE_RANK[profile.degree] < _DEGREE_RANK[grant.min_degree]:
            is_eligible = False
            reasons.append(
                f"Edital exige no mínimo {grant.min_degree.value}; "
                f"pesquisador possui {profile.degree.value}."
            )
        else:
            reasons.append(
                f"Titulação adequada: {profile.degree.value} ≥ {grant.min_degree.value}."
            )

    # 4. Área de conhecimento
    if grant.eligible_areas:
        if _area_matches(profile.area, grant.eligible_areas):
            reasons.append(f"Área '{profile.area}' é elegível.")
        else:
            is_eligible = False
            reasons.append(
                f"Área '{profile.area}' não está entre as elegíveis: "
                f"{', '.join(grant.eligible_areas)}."
            )

    # 5. Estado (UF) — para FAPs estaduais
    if grant.eligible_states and not _state_matches(profile.state, grant.eligible_states):
        warnings.append(
            f"Edital restrito a {grant.eligible_states}; "
            f"pesquisador está em {profile.state}. Verificar regras de exceção."
        )
        score -= 0.1
        actions.append("Confirmar regras de elegibilidade por UF na página do edital.")

    # 6. Requisito de ser PI
    if grant.requires_PI is True and not profile.is_PI:
        is_eligible = False
        reasons.append("Edital exige Pesquisador Principal; perfil não é PI.")
    elif grant.requires_PI is False and profile.is_PI:
        warnings.append("Edital é para membro de equipe; pesquisador é PI.")

    # 7. Idioma
    if grant.language and grant.language not in ("pt", "any", ""):
        if grant.language == "en" and profile.country == "BR":
            warnings.append("Edital exige submissão em inglês.")

    # 8. Valor
    if grant.amount_min and grant.amount_max:
        reasons.append(
            f"Faixa de financiamento: {grant.currency} "
            f"{grant.amount_min:,.0f} – {grant.amount_max:,.0f}."
        )

    # 9. Prazo
    days = grant.days_to_close()
    if days is not None:
        if days <= 7:
            warnings.append(
                f"⚠️ ATENÇÃO: edital fecha em {days} dia(s). "
                f"Data de fechamento: {grant.close_date}."
            )
            actions.append(f"Iniciar submissão imediatamente (fecha em {days} dias).")
        elif days <= 30:
            actions.append(f"Planejar submissão nos próximos dias (fecha em {days} dias).")
        reasons.append(f"Prazo: {grant.close_date} (faltam {days} dias).")

    # 10. ORCID / Lattes
    if profile.orcid is None and profile.lattes_id is None:
        warnings.append(
            "Pesquisador sem ORCID ou Lattes cadastrado. "
            "Muitos editais exigem um dos dois."
        )
        actions.append("Cadastrar ORCID (orcid.org) ou Lattes (lattes.cnpq.br).")

    return EligibilityReport(
        grant=grant, profile=profile, is_eligible=is_eligible,
        score=max(0.0, min(1.0, score)),
        reasons=reasons, warnings=warnings, required_actions=actions,
    )


# ── Busca ────────────────────────────────────────────────────────


def _load_cache(agency: str) -> list[Grant]:
    """Carrega editais do cache local (data/agency.json)."""
    cache_file = DATA_DIR / f"{agency.lower()}.json"
    if not cache_file.exists():
        return []
    try:
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        # Suporta dois formatos: {"grants": [...]} ou lista direta
        if isinstance(data, dict) and "grants" in data:
            items = data["grants"]
        elif isinstance(data, list):
            items = data
        else:
            return []
        grants: list[Grant] = []
        for item in items:
            try:
                item["status"] = GrantStatus(item.get("status", "desconhecido"))
                if "min_degree" in item and item["min_degree"]:
                    item["min_degree"] = Degree(item["min_degree"])
                grants.append(Grant(**item))
            except (ValueError, TypeError):
                # entrada corrompida — pula
                continue
        return grants
    except (json.JSONDecodeError, OSError):
        return []


def _is_cache_fresh(agency: str) -> bool:
    """Verifica se o cache ainda é válido (TTL)."""
    cache_file = DATA_DIR / f"{agency.lower()}.json"
    if not cache_file.exists():
        return False
    try:
        mtime = cache_file.stat().st_mtime
        return (time.time() - mtime) < CACHE_TTL_SECONDS
    except OSError:
        return False


def _fetch_from_source(agency: str) -> list[Grant]:
    """Busca editais via fonte oficial (sources/). Implementações específicas
    ficam nos módulos de cada agência. Retorna lista vazia se falhar."""
    try:
        # Importação tardia para evitar import circular
        from . import sources
        fetcher = sources.get_fetcher(agency)
        if fetcher is None:
            return []
        return fetcher.fetch_open_grants()
    except Exception:
        return []


def _filter_grants(
    grants: list[Grant],
    profile: Optional[ResearcherProfile],
    country: Optional[str],
    amount_min: Optional[float],
    keywords: Optional[list[str]],
    status: Optional[GrantStatus],
) -> list[Grant]:
    """Aplica filtros do usuário sobre a lista de editais."""
    result: list[Grant] = []
    for g in grants:
        if country and g.country != country.upper():
            continue
        if amount_min is not None and g.amount_max and g.amount_max < amount_min:
            continue
        if status and g.status != status:
            continue
        if keywords:
            blob = (g.title + " " + g.description).lower()
            if not any(k.lower() in blob for k in keywords):
                continue
        # Filtro de elegibilidade rápida: área
        if profile is not None and g.eligible_areas and not _area_matches(profile.area, g.eligible_areas):
            continue
        result.append(g)
    return result


def search_grants(
    profile: Optional[ResearcherProfile] = None,
    country: str = "BR",
    agency: Optional[str] = None,
    amount_min: Optional[float] = None,
    keywords: Optional[list[str]] = None,
    status: GrantStatus = GrantStatus.OPEN,
    use_cache: bool = True,
) -> list[Grant]:
    """Busca editais abertos compatíveis com o perfil.

    Args:
        profile: Perfil do pesquisador (opcional; melhora filtragem).
        country: Código do país ("BR", "US", "GB", "EU"...).
        agency: Filtrar por agência específica ("CNPq", "FAPEMIG"...).
        amount_min: Valor mínimo desejado (na moeda do edital).
        keywords: Palavras-chave no título/descrição.
        status: Status dos editais (padrão: abertos).
        use_cache: Se True, usa cache de 24h antes de consultar fonte.

    Returns:
        Lista de editais compatíveis.
    """
    agencies = (
        [agency] if agency
        else (SUPPORTED_AGENCIES_BR if country.upper() == "BR" else SUPPORTED_AGENCIES_INTL)
    )
    all_grants: list[Grant] = []

    for ag in agencies:
        # Tenta cache primeiro
        if use_cache and _is_cache_fresh(ag):
            grants = _load_cache(ag)
        else:
            # Tenta fonte oficial; se falhar, usa cache (mesmo antigo)
            grants = _fetch_from_source(ag)
            if not grants:
                grants = _load_cache(ag)
        all_grants.extend(grants)

    return _filter_grants(all_grants, profile, country, amount_min, keywords, status)


# ── Classe de alto nível com cache persistente ───────────────────


class GrantFinder:
    """Interface de alto nível com cache persistente em disco."""

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self.cache_dir = cache_dir or DATA_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, list[Grant]] = {}

    def search(
        self,
        profile: ResearcherProfile,
        country: str = "BR",
        agency: Optional[str] = None,
        amount_min: Optional[float] = None,
        keywords: Optional[list[str]] = None,
    ) -> list[EligibilityReport]:
        """Busca editais e retorna relatórios de elegibilidade ordenados por score."""
        grants = search_grants(
            profile=profile, country=country, agency=agency,
            amount_min=amount_min, keywords=keywords,
        )
        reports = [check_eligibility(g, profile) for g in grants]
        # Ordena: elegíveis primeiro, depois por score desc, depois por proximidade do prazo
        reports.sort(
            key=lambda r: (
                not r.is_eligible,
                -r.score,
                r.grant.days_to_close() if r.grant.days_to_close() is not None else 9999,
            )
        )
        return reports

    def refresh(self, agency: str) -> int:
        """Força atualização do cache para uma agência. Retorna nº de editais."""
        grants = _fetch_from_source(agency)
        if grants:
            cache_file = self.cache_dir / f"{agency.lower()}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(g) for g in grants],
                    f, indent=2, ensure_ascii=False, default=str,
                )
            self._memory_cache[agency] = grants
        return len(grants)

    def export_report(
        self,
        reports: list[EligibilityReport],
        format: str = "markdown",
    ) -> str:
        """Exporta lista de editais compatíveis em formato legível."""
        if format == "markdown":
            return self._export_markdown(reports)
        if format == "json":
            return json.dumps([r.to_dict() for r in reports], indent=2, ensure_ascii=False)
        raise ValueError(f"Formato não suportado: {format}")

    @staticmethod
    def _export_markdown(reports: list[EligibilityReport]) -> str:
        lines: list[str] = [
            "# Relatório de Editais Compatíveis",
            "",
            f"Data da consulta: {datetime.now().isoformat(timespec='seconds')}",
            "",
        ]
        if not reports:
            lines.append("[SEM DADOS SUFICIENTES] Nenhum edital compatível encontrado.")
            return "\n".join(lines)

        for i, r in enumerate(reports, 1):
            g = r.grant
            lines.extend([
                f"## {i}. {g.title}",
                f"- **Agência:** {g.agency} ({g.country})",
                f"- **Status:** {g.status.value}",
            ])
            if g.amount_min or g.amount_max:
                amt = f"{g.currency} "
                amt += f"{g.amount_min:,.0f}" if g.amount_min else "—"
                amt += " – "
                amt += f"{g.amount_max:,.0f}" if g.amount_max else "—"
                lines.append(f"- **Faixa de valor:** {amt}")
            if g.close_date:
                lines.append(f"- **Prazo:** {g.close_date}")
            if g.url:
                lines.append(f"- **Link:** {g.url}")
            lines.append(f"- **Score de adequação:** {r.score:.0%}")
            lines.append("- **Elegível:** " + ("Sim ✅" if r.is_eligible else "Não ❌"))
            if r.reasons:
                lines.append("- **Razões:**")
                for reason in r.reasons:
                    lines.append(f"  - {reason}")
            if r.warnings:
                lines.append("- **Avisos:**")
                for w in r.warnings:
                    lines.append(f"  - {w}")
            if r.required_actions:
                lines.append("- **Ações necessárias:**")
                for a in r.required_actions:
                    lines.append(f"  - {a}")
            lines.append("")
        return "\n".join(lines)
