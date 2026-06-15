"""Testes para opencode_utils.py — localização do binário opencode."""

import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from opencode_utils import _search, CANDIDATES


class TestOpenCodeUtils:
    """Testa utilitários do OpenCode."""

    def test_candidates_are_absolute(self):
        """Candidatos devem ser paths absolutos."""
        for path in CANDIDATES:
            assert os.path.isabs(path), f"Candidato não absoluto: {path}"

    @patch("opencode_utils.subprocess.run")
    def test_search_calls_find(self, mock_run):
        """_search deve executar find com os diretórios corretos."""
        mock_process = MagicMock()
        mock_process.stdout = "/usr/local/bin/opencode\n"
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        result = _search()
        assert result == "/usr/local/bin/opencode"
        # Verificar que find foi chamado com os diretórios esperados
        call_args = mock_run.call_args[0][0]
        assert "/root" in call_args
        assert "/home" in call_args
        assert "/usr/local" in call_args

    @patch("opencode_utils.subprocess.run")
    def test_search_no_results(self, mock_run):
        """_search deve retornar None se nada for encontrado."""
        mock_process = MagicMock()
        mock_process.stdout = ""
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        result = _search()
        assert result is None
