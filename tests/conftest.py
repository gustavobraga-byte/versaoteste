"""Pytest configuration for PesquisAI.

Adds the project root to ``sys.path`` so tests can import the
``pesquisai`` package without installing it.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
