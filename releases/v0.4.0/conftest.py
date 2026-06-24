"""
conftest.py — Configuração pytest para o pacote pesquisai-v0.4.0.

Adiciona o diretório raiz ao sys.path para permitir imports diretos
de `grant_finder` e `i18n` durante os testes, sem necessidade de instalar
o pacote.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao sys.path
_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
