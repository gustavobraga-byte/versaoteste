"""Testes para progress_bar.py — componentes da barra de progresso."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from progress_bar import _html, STAGES, COLORS


class TestProgressBar:
    """Testa componentes da barra de progresso."""

    def test_stages_count(self):
        """Deve haver 4 estágios definidos."""
        assert len(STAGES) == 4

    def test_colors_count(self):
        """Deve haver 4 cores definidas."""
        assert len(COLORS) == 4

    def test_html_output_basic(self):
        """HTML deve conter elementos essenciais."""
        html = _html(0, 4, "Testando...", 25)
        assert "ppbar" in html
        assert "Testando..." in html
        assert "25%" in html
        assert "linear-gradient" in html

    def test_html_with_percentage(self):
        """HTML deve refletir a porcentagem fornecida."""
        html = _html(2, 4, "Fazendo...", 50)
        assert "Fazendo..." in html
        assert "50%" in html

    def test_html_handles_zero_total(self):
        """Não deve quebrar com total = 0."""
        html = _html(0, 0, "Teste", 0)
        assert html is not None
        assert len(html) > 0

    def test_html_handles_negative_step(self):
        """Passo negativo deve ser tratado (step < 0)."""
        html = _html(-1, 4, "Teste", 0)
        assert html is not None
        assert len(html) > 0

    def test_html_percent_preserves_input(self):
        """O HTML gerado deve refletir o percent informado (clamping é responsabilidade do caller)."""
        html_over = _html(5, 4, "Over", 200)
        assert "200%" in html_over  # a função _html não clamp; show() faz isso
        assert "Over" in html_over

    def test_stage_content(self):
        """Estágio correto deve ser exibido."""
        html = _html(1, 4, "Mensagem", 25)
        assert STAGES[1] in html
        assert "Mensagem" in html
