"""Subprocess runner abstraction with a real and a fake implementation.

The :class:`CommandRunner` Protocol and its :class:`SubprocessRunner`
implementation address the testability findings from
ANALISE_CODIGO.md (Section 6.3). Code that needs to spawn subprocesses
should depend on the Protocol so unit tests can swap in
:class:`FakeRunner`.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger("pesquisai.subprocess")


class CommandRunner(Protocol):
    """Minimal subprocess runner contract.

    Implementations may be backed by ``subprocess.run`` (production) or
    a recording fake (tests). The contract is intentionally narrow to
    keep fakes easy to write.
    """

    def run(self, cmd: list[str], **kw: Any) -> subprocess.CompletedProcess: ...
    def popen(self, cmd: list[str], **kw: Any) -> subprocess.Popen: ...


class SubprocessRunner:
    """Default :class:`CommandRunner` backed by the stdlib."""

    def run(self, cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        # ``capture_output=True`` so the test fake can ignore it cleanly.
        kw.setdefault("capture_output", True)
        kw.setdefault("text", True)
        return subprocess.run(cmd, **kw)

    def popen(self, cmd: list[str], **kw: Any) -> subprocess.Popen:
        return subprocess.Popen(cmd, **kw)


@dataclass
class FakeRunner:
    """In-memory runner for tests.

    Records every command passed to :meth:`run` and :meth:`popen`, and
    returns pre-configured responses. Resolution order:

    1. A response registered in :attr:`responses` keyed by the full
       command tuple.
    2. The next item in :attr:`queued_responses` (FIFO).
    3. The :attr:`default_returncode`/``default_stdout``/``default_stderr``.

    Example
    -------
    >>> r = FakeRunner()
    >>> r.responses[("which", "opencode")] = subprocess.CompletedProcess(
    ...     args=["which", "opencode"], returncode=0, stdout="/usr/bin/opencode"
    ... )
    >>> result = r.run(["which", "opencode"])
    >>> result.returncode
    0
    >>> r.calls
    [['which', 'opencode']]
    """

    calls: list[list[str]] = field(default_factory=list)
    responses: dict[tuple[str, ...], subprocess.CompletedProcess] = field(
        default_factory=dict
    )
    popen_calls: list[list[str]] = field(default_factory=list)
    queued_responses: list[subprocess.CompletedProcess] = field(default_factory=list)
    default_returncode: int = 0
    default_stdout: str = ""
    default_stderr: str = ""

    def _key(self, cmd: list[str]) -> tuple[str, ...]:
        return tuple(cmd)

    def run(self, cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
        self.calls.append(list(cmd))
        key = self._key(cmd)
        if key in self.responses:
            return self.responses[key]
        if self.queued_responses:
            return self.queued_responses.pop(0)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=self.default_returncode,
            stdout=self.default_stdout,
            stderr=self.default_stderr,
        )

    def popen(self, cmd: list[str], **kw: Any) -> subprocess.Popen:
        self.popen_calls.append(list(cmd))
        # Return a real Popen pointing at /bin/true so .poll() etc. work
        # without actually executing the user-provided command.
        return subprocess.Popen(["/bin/true"])
