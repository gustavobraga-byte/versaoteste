"""Skill registry and clone helpers.

Replaces the two parallel ``SKILLS`` / ``SKILL_MAPPINGS`` lists in
``run_fast.py`` (Section 4.6 of ANALISE_CODIGO.md) with a single
:class:`Skill` dataclass that owns its clone destination, agent
destination, and optional subpath.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .config import SETTINGS
from .utils.subprocess import CommandRunner, SubprocessRunner

logger = logging.getLogger("pesquisai.skills")

DEFAULT_CLONE_WORKERS = 8
DEFAULT_CLONE_TIMEOUT = 60
DEFAULT_PULL_TIMEOUT = 30


@dataclass(frozen=True)
class Skill:
    """A single skill repository known to PesquisAI.

    Attributes
    ----------
    repo_url:
        Git URL to clone (https or ssh).
    name:
        Logical name; also used as the destination folder name.
    local_subpath:
        Optional subdirectory inside the clone that contains the skill
        metadata. Useful for monorepos such as
        ``scientific-agent-skills`` where the actual skills live in a
        ``skills/`` subfolder.
    enabled:
        When ``False``, the skill is skipped during installation.
        Use it to temporarily opt-out without removing the entry.
    """

    repo_url: str
    name: str
    local_subpath: str = ""
    enabled: bool = True

    @property
    def clone_dest(self) -> str:
        return f"/tmp/skill_{self.name}"

    @property
    def source_path(self) -> str:
        """Path inside the clone that should be copied to the agent dir."""
        if self.local_subpath:
            return os.path.join(self.clone_dest, self.local_subpath)
        return self.clone_dest

    @property
    def agent_dest(self) -> str:
        return os.path.join(str(SETTINGS.skills_dir), self.name)


REGISTRY: list[Skill] = [
    Skill("https://github.com/gustavobraga-byte/Skill-IBGE.git", "ibge-br"),
    Skill("https://github.com/gustavobraga-byte/Skill-DataSus.git", "opendatasus"),
    Skill(
        "https://github.com/gustavobraga-byte/scientific-agent-skills.git",
        "scientific",
        local_subpath="skills",
    ),
    Skill("https://github.com/gustavobraga-byte/PesquisAI.git", "pesquisai"),
    Skill("https://github.com/gustavobraga-byte/UFV-ABNT.git", "ufv-abnt"),
    Skill(
        "https://github.com/gustavobraga-byte/Skill_Analise_qualitativa.git",
        "qualitativa",
    ),
    Skill(
        "https://github.com/gustavobraga-byte/skill_dados_brasil.git",
        "dados-brasil",
    ),
    Skill("https://github.com/gustavobraga-byte/skill_agrobr.git", "agrobr"),
]


def _clone_or_pull(
    skill: Skill,
    runner: Optional[CommandRunner] = None,
) -> bool:
    """Clone ``skill.repo_url`` into ``skill.clone_dest`` (or pull if exists).

    Returns ``True`` on success. The function tolerates a failing
    ``git pull`` by deleting the existing directory and re-cloning, so
    transient network issues during pull do not leave the skill in a
    half-updated state.
    """
    if not skill.enabled:
        logger.debug("Skill %s desabilitada — pulando.", skill.name)
        return False

    runner = runner or SubprocessRunner()
    dest = skill.clone_dest

    if os.path.isdir(dest):
        pull = runner.run(
            ["git", "-C", dest, "pull", "--depth", "1", "--ff-only"],
            timeout=DEFAULT_PULL_TIMEOUT,
        )
        if pull.returncode == 0:
            return True
        logger.warning("Pull falhou para %s; reclonando.", skill.name)
        shutil.rmtree(dest, ignore_errors=True)

    clone = runner.run(
        ["git", "clone", "--depth", "1", "--single-branch", skill.repo_url, dest],
        timeout=DEFAULT_CLONE_TIMEOUT,
    )
    return clone.returncode == 0


def install_all(
    skills: Optional[Iterable[Skill]] = None,
    runner: Optional[CommandRunner] = None,
    max_workers: int = DEFAULT_CLONE_WORKERS,
) -> dict[str, bool]:
    """Clone/pull every skill in the registry (in parallel).

    Returns a mapping ``{name: success}``. The function uses a
    :class:`concurrent.futures.ThreadPoolExecutor` because git clones
    are I/O bound and benefit from concurrency.
    """
    skills = list(skills) if skills is not None else REGISTRY
    runner = runner or SubprocessRunner()
    os.makedirs(str(SETTINGS.skills_dir), exist_ok=True)

    results: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_clone_or_pull, skill, runner): skill for skill in skills
        }
        for future in as_completed(futures):
            skill = futures[future]
            try:
                results[skill.name] = future.result()
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Skill %s falhou: %s", skill.name, exc)
                results[skill.name] = False

    # Copy from clone to agent dir (sequential — small files, fs-bound).
    for skill in skills:
        if not results.get(skill.name):
            continue
        src = skill.source_path
        dest = skill.agent_dest
        if not os.path.isdir(src):
            logger.warning("Origem ausente para %s: %s", skill.name, src)
            continue
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(src, dest, dirs_exist_ok=True)
        logger.info("Skill %s copiada para %s", skill.name, dest)

    return results


def list_installed() -> list[str]:
    """Return names of skills already present in the agent skills dir."""
    if not os.path.isdir(str(SETTINGS.skills_dir)):
        return []
    return sorted(
        entry.name
        for entry in Path(str(SETTINGS.skills_dir)).iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )
