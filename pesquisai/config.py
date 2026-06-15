"""Typed configuration for PesquisAI.

Replaces the flat ``constants.py`` module with a pydantic ``Settings``
model (ANALISE_CODIGO.md Section 6.2). The model is immutable and
exposes derived paths as @properties to keep call-sites short.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

try:
    # Pydantic v2 settings module is optional; if unavailable we keep
    # the model usable in plain instantiation mode.
    from pydantic_settings import BaseSettings  # type: ignore

    _HAVE_SETTINGS = True
except ImportError:  # pragma: no cover - pydantic-settings is optional
    _HAVE_SETTINGS = False


def _default_terminal_port() -> int:
    return int(os.environ.get("PESQUISAI_TERMINAL_PORT", "8000"))


def _default_wrapper_port() -> int:
    return int(os.environ.get("PESQUISAI_WRAPPER_PORT", "8001"))


if _HAVE_SETTINGS:

    class Settings(BaseSettings):  # type: ignore[misc]
        """Application settings (env-overridable via pydantic-settings)."""

        model_config = ConfigDict(
            frozen=True,
            env_prefix="PESQUISAI_",
            extra="ignore",
        )

        drive_folder: str = "PesquisAI"
        mount_path: Path = Field(default_factory=lambda: Path("/content/drive"))
        work_dir: Path = Field(default_factory=lambda: Path("/tmp/pesquisai"))
        wrapper_dir: Path = Field(default_factory=lambda: Path("/tmp/pesquisai-wrapper"))
        fallback_drive_url: str = "https://drive.google.com/drive/my-drive"

        skills_dir: Path = Field(default_factory=lambda: Path.home() / ".agents/skills")
        theme_dir: Path = Field(default_factory=lambda: Path.home() / ".config/opencode/themes")
        agent_dir: Path = Field(default_factory=lambda: Path.home() / ".config/opencode/agents")
        opencode_cfg: Path = Field(
            default_factory=lambda: Path.home() / ".config/opencode/config.json"
        )
        tui_json: Path = Field(
            default_factory=lambda: Path.home() / ".config/opencode/tui.json"
        )

        terminal_port: int = Field(default_factory=_default_terminal_port)
        wrapper_port: int = Field(default_factory=_default_wrapper_port)

        repo_url: str = "https://github.com/gustavobraga-byte/PesquisAI.git"
        author_name: str = "Gustavo Bastos Braga"
        author_email: str = "gustavo.braga@ufv.br"
        institution: str = "Universidade Federal de Viçosa (UFV)"
        version: str = "0.3"

        @property
        def drive_path(self) -> Path:
            return self.mount_path / "My Drive" / self.drive_folder

        @property
        def backup_dir(self) -> Path:
            return self.drive_path / "backups"

else:

    class Settings(BaseModel):  # type: ignore[no-redef]
        """Plain-pydantic settings (env vars must be applied manually)."""

        model_config = ConfigDict(frozen=True, extra="ignore")

        drive_folder: str = "PesquisAI"
        mount_path: Path = Field(default_factory=lambda: Path("/content/drive"))
        work_dir: Path = Field(default_factory=lambda: Path("/tmp/pesquisai"))
        wrapper_dir: Path = Field(default_factory=lambda: Path("/tmp/pesquisai-wrapper"))
        fallback_drive_url: str = "https://drive.google.com/drive/my-drive"

        skills_dir: Path = Field(default_factory=lambda: Path.home() / ".agents/skills")
        theme_dir: Path = Field(default_factory=lambda: Path.home() / ".config/opencode/themes")
        agent_dir: Path = Field(default_factory=lambda: Path.home() / ".config/opencode/agents")
        opencode_cfg: Path = Field(
            default_factory=lambda: Path.home() / ".config/opencode/config.json"
        )
        tui_json: Path = Field(
            default_factory=lambda: Path.home() / ".config/opencode/tui.json"
        )

        terminal_port: int = Field(default_factory=_default_terminal_port)
        wrapper_port: int = Field(default_factory=_default_wrapper_port)

        repo_url: str = "https://github.com/gustavobraga-byte/PesquisAI.git"
        author_name: str = "Gustavo Bastos Braga"
        author_email: str = "gustavo.braga@ufv.br"
        institution: str = "Universidade Federal de Viçosa (UFV)"
        version: str = "0.3"

        @field_validator(
            "mount_path",
            "work_dir",
            "wrapper_dir",
            "skills_dir",
            "theme_dir",
            "agent_dir",
            "opencode_cfg",
            "tui_json",
            mode="before",
        )
        @classmethod
        def _coerce_path(cls, v: Any) -> Path:
            return Path(os.path.expanduser(str(v)))

        @property
        def drive_path(self) -> Path:
            return self.mount_path / "My Drive" / self.drive_folder

        @property
        def backup_dir(self) -> Path:
            return self.drive_path / "backups"


# Singleton — instantiated at import time so other modules can simply
# ``from pesquisai.config import SETTINGS``.
SETTINGS = Settings()


def get_logger(name: str) -> logging_module_Logger:  # type: ignore[name-defined]
    """Return a namespaced logger using the project's configuration.

    Imported separately to avoid a circular dep with ``constants``.
    """
    import logging as _logging

    return _logging.getLogger(f"pesquisai.{name}")


# Late-bound to avoid importing logging before this module is fully
# evaluated in test contexts.
import logging as logging_module  # noqa: E402

Logger = logging_module.Logger
