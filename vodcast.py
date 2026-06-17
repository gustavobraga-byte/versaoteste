"""
vodcast.py — Motor de Vodcast Acadêmico estilo NotebookLM

Gera vídeos com diálogo entre dois hosts (vozes naturais edge-tts),
slides acadêmicos com dados reais (IBGE/DataSUS/AgroBR),
legendas sincronizadas e roteiro em markdown.

Fases:
  Fase 1 (atual): Diálogo 2 vozes + slides + gráficos + .mp4 + .mp3 + .srt
  Fase 2: Transições animadas entre slides
  Fase 3: Avatar IA (API externa)

Dependências:
  - edge-tts (vozes naturais PT-BR gratuitas)
  - moviepy + ffmpeg (montagem de vídeo)
  - matplotlib + numpy (gráficos acadêmicos)
  - Pillow (processamento de imagem)

Uso:
    from vodcast import Vodcast
    
    v = Vodcast()
    resultado = v.produzir("Mortalidade infantil no Nordeste 2010-2024")
    print(resultado["video"])  # caminho do .mp4
"""

import os
import json
import hashlib
import logging
import asyncio
import subprocess
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np

logger = logging.getLogger("pesquisai.vodcast")

# ── Bibliotecas opcionais com fallback informativo ────────────

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    from moviepy import (
        ImageClip, AudioFileClip, concatenate_videoclips,
        CompositeVideoClip, TextClip, ColorClip
    )
    HAS_MOVIEPY = True
except ImportError:
    try:
        from moviepy.editor import (
            ImageClip, AudioFileClip, concatenate_videoclips,
            CompositeVideoClip, TextClip, ColorClip
        )
        HAS_MOVIEPY = True
    except ImportError:
        HAS_MOVIEPY = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

SLIDE_WIDTH: int = 1920
SLIDE_HEIGHT: int = 1080
SLIDE_DPI: int = 100
FPS: int = 24

COR_VERDE_UFV: str = "#1B5E20"
COR_VERDE_CLARO: str = "#4CAF50"
COR_OURO: str = "#FFD54F"
COR_CINZA: str = "#757575"
COR_CINZA_CLARO: str = "#BBBBBB"
COR_FUNDO: str = "#FAFAFA"

FONTE_TITULO: str = "Liberation Sans"
FONTE_CORPO: str = "Liberation Serif"
FONTE_MONO: str = "Liberation Mono"

DIR_VODCAST: str = "/content/drive/My Drive/PesquisAI/vodcasts"

# Vozes PT-BR disponíveis no edge-tts
VOZES_DISPONIVEIS: dict = {
    "francisca": "pt-BR-FranciscaNeural",   # Feminino
    "antonio": "pt-BR-AntonioNeural",        # Masculino
    "thalita": "pt-BR-ThalitaMultilingualNeural",  # Feminino multilíngue
}

# Configuração padrão dos hosts
HOST_PADRAO: list[dict] = [
    {"nome": "Dra. Ana", "voz": "pt-BR-FranciscaNeural", "genero": "F"},
    {"nome": "Prof. Carlos", "voz": "pt-BR-AntonioNeural", "genero": "M"},
]


# ═══════════════════════════════════════════════════════════════
# ESTRUTURAS DE DADOS
# ═══════════════════════════════════════════════════════════════

@dataclass
class Cena:
    """Uma cena do vodcast: um slide + a fala correspondente."""
    tipo: str  # abertura, texto, grafico, citacao, destaque, encerramento
    host: int  # índice do host que fala (0 ou 1)
    fala: str  # texto que o host diz
    duracao: float  # segundos estimados
    titulo: str = ""
    subtitulo: str = ""
    conteudo: str = ""
    citacao: str = ""
    fonte: str = ""
    # Para gráficos
    dados: Optional[dict] = None
    tipo_grafico: str = "line"  # line, bar
    # Para tabelas
    tabela: Optional[list] = None
    cabecalho_tabela: Optional[list] = None
    # Metadados
    legenda: str = ""


@dataclass
class Roteiro:
    """Roteiro completo do vodcast."""
    tema: str
    slug: str
    hosts: list[dict] = field(default_factory=lambda: HOST_PADRAO)
    cenas: list[Cena] = field(default_factory=list)
    data_geracao: str = field(default_factory=lambda: datetime.now().isoformat())
    instituicao: str = "Universidade Federal de Viçosa (UFV)"
    fontes: list[str] = field(default_factory=list)
    
    @property
    def duracao_total(self) -> float:
        return sum(c.duracao for c in self.cenas)


# ═══════════════════════════════════════════════════════════════
# GERADOR DE ROTEIRO
# ═══════════════════════════════════════════════════════════════

class GeradorRoteiro:
    """Gera roteiros de diálogo acadêmico a partir de um tema e dados."""

    # Templates de diálogo para cada tipo de cena
    _abertura = [
        'Olá! Seja bem-vindo ao PesquisAI Dialogue. Hoje vamos mergulhar em um tema fascinante:',
        'E eu sou {host2}. {host1}, que tema vamos explorar hoje?',
    ]
    
    _transicoes = [
        'Isso me leva a pensar em outro aspecto importante...',
        'E o que os dados mostram sobre isso?',
        'Excelente ponto! Falando nisso...',
        'Interessante! E você sabia que...',
    ]
    
    _chamadas_grafico = [
        'Dá uma olhada neste gráfico que preparei com os dados...',
        'E os números confirmam isso claramente...',
        'Visualizando os dados, fica ainda mais evidente...',
        'Olha só que interessante este padrão...',
    ]
    
    _encerramento = [
        'E com isso chegamos ao final do nosso diálogo de hoje.',
        'Exato! Fica aqui o convite para continuarem explorando o tema. Até a próxima!',
    ]

    @classmethod
    def gerar(cls, tema: str, dados: Optional[dict] = None) -> Roteiro:
        """Gera roteiro completo a partir de um tema.

        Args:
            tema: Tema da pesquisa (ex: "Mortalidade infantil no Nordeste")
            dados: Dados opcionais para enriquecer o roteiro.
                  Pode conter: fontes, indicadores, citacoes, graficos.

        Returns:
            Roteiro estruturado com cenas.
        """
        slug = cls._criar_slug(tema)
        hosts = HOST_PADRAO
        fontes = []
        cenas = []

        if dados and "fontes" in dados:
            fontes = dados["fontes"]

        # ── Cena 1: Abertura ──────────────────────────────────
        cenas.append(Cena(
            tipo="abertura",
            host=0,
            fala=f'{cls._abertura[0]} "{tema}".',
            duracao=7.0,
            titulo=tema,
            subtitulo="PesquisAI Dialogue · Dados oficiais do Brasil",
        ))
        cenas.append(Cena(
            tipo="abertura",
            host=1,
            fala=f'E eu sou o {hosts[1]["nome"]}. {hosts[0]["nome"]}, por onde começamos?',
            duracao=4.0,
            titulo=tema,
            subtitulo="Uma conversa sobre dados e evidências",
        ))

        # ── Cenas de contexto / análise ───────────────────────
        if dados and "indicadores" in dados:
            for i, ind in enumerate(dados["indicadores"]):
                host_idx = i % 2
                cenas.append(cls._cena_contexto(
                    host_idx, ind, dados, i, len(dados["indicadores"])
                ))
                
                # Se tiver dados para gráfico
                if "grafico" in ind:
                    cenas.append(Cena(
                        tipo="grafico",
                        host=(i + 1) % 2,
                        fala=cls._chamadas_grafico[i % len(cls._chamadas_grafico)],
                        duracao=10.0,
                        titulo=ind.get("titulo", "Dados"),
                        dados=ind["grafico"],
                        tipo_grafico=ind.get("tipo_grafico", "bar"),
                        fonte=ind.get("fonte", ""),
                    ))

        # ── Cena de citação (se houver) ───────────────────────
        if dados and "citacoes" in dados:
            for i, cit in enumerate(dados["citacoes"]):
                host_idx = (i + len(cenas)) % 2
                cenas.append(Cena(
                    tipo="citacao",
                    host=host_idx,
                    fala=f'Como citado por {cit.get("autor", "estudo recente")}: '
                         f'"{cit.get("texto", "")}"',
                    duracao=8.0,
                    titulo="Referência da Literatura",
                    conteudo=cit.get("texto", ""),
                    citacao=f'{cit.get("autor", "")} ({cit.get("ano", "")})',
                    fonte=cit.get("fonte", ""),
                ))

        # ── Encerramento ──────────────────────────────────────
        cenas.append(Cena(
            tipo="encerramento",
            host=0,
            fala=cls._encerramento[0],
            duracao=5.0,
            titulo="Conclusões",
            conteudo=f"Este vodcast foi gerado pelo PesquisAI com dados oficiais do Brasil.",
        ))
        cenas.append(Cena(
            tipo="encerramento",
            host=1,
            fala=cls._encerramento[1],
            duracao=4.0,
            titulo="Continue Explorando",
            conteudo="Acesse a pasta vodcasts/ no seu Drive para baixar os arquivos.",
        ))

        return Roteiro(
            tema=tema,
            slug=slug,
            hosts=hosts,
            cenas=cenas,
            fontes=fontes,
        )

    @classmethod
    def _cena_contexto(cls, host_idx: int, ind: dict, dados: dict,
                       i: int, total: int) -> Cena:
        """Cria cena de contexto/análise de um indicador."""
        nome = ind.get("nome", "indicador")
        valor = ind.get("valor", "")
        comparacao = ind.get("comparacao", "")
        periodo = ind.get("periodo", "")
        fonte = ind.get("fonte", "")

        fala = f'{nome}: {valor}'
        if comparacao:
            fala += f', {comparacao}'
        if periodo:
            fala += f', no período de {periodo}.'

        return Cena(
            tipo="texto",
            host=host_idx,
            fala=fala,
            duracao=10.0,
            titulo=nome,
            conteudo=f"{nome}: {valor}",
            citacao=f"Fonte: {fonte}" if fonte else "",
            fonte=fonte,
        )

    @staticmethod
    def _criar_slug(tema: str) -> str:
        """Cria um slug a partir do tema."""
        slug = tema.lower().strip()
        slug = slug.replace(" ", "_")
        slug = "".join(c for c in slug if c.isalnum() or c in "_-")
        slug = slug[:60].strip("_")
        if not slug:
            slug = "vodcast"
        return slug


# ═══════════════════════════════════════════════════════════════
# GERADOR DE SLIDES (MATPLOTLIB)
# ═══════════════════════════════════════════════════════════════

class GeradorSlides:
    """Gera slides acadêmicos em PNG a partir do roteiro."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def gerar_todos(self, roteiro: Roteiro, dados_adicionais: Optional[dict] = None) -> list[str]:
        """Gera PNGs para todas as cenas do roteiro.

        Returns:
            Lista de caminhos dos PNGs gerados, na ordem das cenas.
        """
        caminhos = []
        for i, cena in enumerate(roteiro.cenas):
            caminho = os.path.join(self.output_dir, f"slide_{i:03d}.png")
            self._gerar_slide(cena, roteiro, i, len(roteiro.cenas), caminho)
            caminhos.append(caminho)
        return caminhos

    def _base_fig(self) -> tuple:
        """Cria figura base 1920x1080 com fundo limpo."""
        fig, ax = plt.subplots(figsize=(SLIDE_WIDTH / SLIDE_DPI, SLIDE_HEIGHT / SLIDE_DPI),
                               dpi=SLIDE_DPI)
        fig.patch.set_facecolor(COR_FUNDO)
        ax.set_facecolor(COR_FUNDO)

        # Remove bordas
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])

        # Limites relativos (0 a 1)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        return fig, ax

    def _add_footer(self, ax, texto: str = "PesquisAI · UFV",
                    fonte: str = ""):
        """Adiciona rodapé padronizado."""
        footer = f"PesquisAI · UFV | {datetime.now().strftime('%Y')}"
        if fonte:
            footer += f" | Fonte: {fonte}"
        ax.text(0.03, 0.01, footer, transform=ax.transAxes,
                fontsize=10, fontfamily=FONTE_CORPO, color=COR_CINZA_CLARO,
                ha="left", va="bottom")

    def _add_titulo_barra(self, ax, titulo: str):
        """Adiciona barra de título no topo."""
        # Fundo verde
        ax.axhspan(0.85, 1.0, xmin=0, xmax=1, facecolor=COR_VERDE_UFV, alpha=0.95)
        # Título
        ax.text(0.05, 0.915, titulo, fontsize=28, fontweight="bold",
                fontfamily=FONTE_TITULO, color="white",
                ha="left", va="center", transform=ax.transAxes)

    def _add_host_label(self, ax, host_name: str, cena_idx: int):
        """Adiciona indicador de quem está falando."""
        colors = ["#1B5E20", "#1565C0"]
        ax.text(0.97, 0.88, f"🎙 {host_name}", fontsize=14,
                fontfamily=FONTE_TITULO, color=colors[cena_idx % 2],
                ha="right", va="center", transform=ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                         edgecolor=colors[cena_idx % 2], alpha=0.9))

    def _gerar_slide(self, cena: Cena, roteiro: Roteiro, idx: int,
                     total: int, caminho: str):
        """Gera um slide PNG baseado no tipo da cena."""
        if cena.tipo == "abertura":
            self._slide_abertura(cena, roteiro, caminho)
        elif cena.tipo == "texto":
            self._slide_texto(cena, roteiro, idx, caminho)
        elif cena.tipo == "grafico":
            self._slide_grafico(cena, roteiro, idx, caminho)
        elif cena.tipo == "citacao":
            self._slide_citacao(cena, roteiro, idx, caminho)
        elif cena.tipo == "encerramento":
            self._slide_encerramento(cena, roteiro, caminho)
        else:
            self._slide_texto(cena, roteiro, idx, caminho)

    def _slide_abertura(self, cena: Cena, roteiro: Roteiro, caminho: str):
        """Slide de abertura com tema central."""
        fig, ax = self._base_fig()

        # Faixa decorativa superior
        ax.axhspan(0.7, 1.0, xmin=0, xmax=1, facecolor=COR_VERDE_UFV, alpha=0.95)

        # Título principal
        ax.text(0.5, 0.82, cena.titulo, fontsize=44, fontweight="bold",
                fontfamily=FONTE_TITULO, color="white",
                ha="center", va="center", transform=ax.transAxes,
                wrap=True)

        # Subtítulo
        ax.text(0.5, 0.72, cena.subtitulo, fontsize=22,
                fontfamily=FONTE_CORPO, color="#E0E0E0",
                ha="center", va="center", transform=ax.transAxes)

        # Apresentação dos hosts
        h1, h2 = roteiro.hosts[0]["nome"], roteiro.hosts[1]["nome"]
        ax.text(0.5, 0.50, f"🎙  {h1}  ·  {h2}", fontsize=26,
                fontfamily=FONTE_TITULO, color=COR_VERDE_UFV,
                ha="center", va="center", transform=ax.transAxes,
                fontweight="bold")

        # Selo UFV
        ax.text(0.5, 0.35, roteiro.instituicao, fontsize=16,
                fontfamily=FONTE_CORPO, color=COR_CINZA,
                ha="center", va="center", transform=ax.transAxes)

        self._add_footer(ax)
        plt.savefig(caminho, dpi=SLIDE_DPI, bbox_inches="tight",
                    facecolor=COR_FUNDO, pad_inches=0)
        plt.close()

    def _slide_texto(self, cena: Cena, roteiro: Roteiro, idx: int,
                     caminho: str):
        """Slide com conteúdo textual."""
        fig, ax = self._base_fig()
        self._add_titulo_barra(ax, cena.titulo)
        self._add_host_label(ax, roteiro.hosts[cena.host]["nome"], idx)

        # Conteúdo principal
        ax.text(0.08, 0.70, cena.conteudo if cena.conteudo else cena.fala,
                fontsize=22, fontfamily=FONTE_CORPO, color="#333333",
                ha="left", va="top", transform=ax.transAxes,
                wrap=True, linespacing=1.5)

        # Citação / fonte
        if cena.citacao:
            ax.text(0.08, 0.12, f"📚 {cena.citacao}", fontsize=14,
                    fontfamily=FONTE_TITULO, color=COR_CINZA,
                    ha="left", va="bottom", transform=ax.transAxes,
                    style="italic")

        self._add_footer(ax, fonte=cena.fonte)
        plt.savefig(caminho, dpi=SLIDE_DPI, bbox_inches="tight",
                    facecolor=COR_FUNDO, pad_inches=0)
        plt.close()

    def _slide_grafico(self, cena: Cena, roteiro: Roteiro, idx: int,
                       caminho: str):
        """Slide com gráfico acadêmico."""
        if not cena.dados:
            self._slide_texto(cena, roteiro, idx, caminho)
            return

        fig, ax = self._base_fig()

        # Título na parte superior
        ax.text(0.05, 0.92, cena.titulo, fontsize=24, fontweight="bold",
                fontfamily=FONTE_TITULO, color=COR_VERDE_UFV,
                ha="left", va="center", transform=ax.transAxes)

        self._add_host_label(ax, roteiro.hosts[cena.host]["nome"], idx)

        # Área do gráfico (transform para coordenadas do axes)
        # Vamos criar um inset axes para o gráfico
        ax_graf = fig.add_axes([0.08, 0.18, 0.84, 0.62])
        ax_graf.set_facecolor("white")

        dados = cena.dados
        labels = dados.get("labels", [])
        valores = dados.get("valores", [])
        cor_bar = COR_VERDE_UFV
        cor_line = "#1565C0"

        if cena.tipo_grafico == "bar":
            bars = ax_graf.bar(labels, valores, color=cor_bar, alpha=0.85,
                              edgecolor="white", linewidth=0.5)
            # Rótulos nos valores
            for bar, val in zip(bars, valores):
                ax_graf.text(bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + max(valores) * 0.01,
                            f"{val}", ha="center", va="bottom",
                            fontsize=11, fontfamily=FONTE_CORPO,
                            color=COR_CINZA)
        elif cena.tipo_grafico == "line":
            x = range(len(labels))
            ax_graf.plot(x, valores, "o-", color=cor_line, linewidth=2.5,
                        markersize=8, markerfacecolor="white",
                        markeredgecolor=cor_line, markeredgewidth=2)
            # Preencher área
            ax_graf.fill_between(x, valores, alpha=0.1, color=cor_line)
            # Rótulos nos pontos
            for xi, val in zip(x, valores):
                ax_graf.text(xi, val + max(valores) * 0.02,
                            f"{val}", ha="center", va="bottom",
                            fontsize=11, fontfamily=FONTE_CORPO,
                            color=COR_CINZA)
            ax_graf.set_xticks(x)
            ax_graf.set_xticklabels(labels)

        # Formatação acadêmica do gráfico
        ax_graf.tick_params(axis="both", labelsize=12)
        ax_graf.spines["top"].set_visible(False)
        ax_graf.spines["right"].set_visible(False)
        ax_graf.spines["left"].set_color("#CCCCCC")
        ax_graf.spines["bottom"].set_color("#CCCCCC")
        ax_graf.grid(axis="y", alpha=0.3, color="#CCCCCC", linestyle="--")

        # Fonte
        if cena.fonte:
            fig.text(0.08, 0.05, f"Fonte: {cena.fonte}", fontsize=11,
                    fontfamily=FONTE_CORPO, color=COR_CINZA,
                    ha="left")

        self._add_footer(ax, fonte=cena.fonte)
        plt.savefig(caminho, dpi=SLIDE_DPI, bbox_inches="tight",
                    facecolor=COR_FUNDO, pad_inches=0)
        plt.close()

    def _slide_citacao(self, cena: Cena, roteiro: Roteiro, idx: int,
                       caminho: str):
        """Slide de citação em destaque."""
        fig, ax = self._base_fig()

        # Aspas decorativas
        ax.text(0.08, 0.85, '"', fontsize=120, fontfamily=FONTE_CORPO,
                color=COR_VERDE_CLARO, alpha=0.3,
                ha="left", va="center", transform=ax.transAxes)

        # Citação
        ax.text(0.15, 0.70, cena.conteudo if cena.conteudo else cena.fala,
                fontsize=28, fontfamily=FONTE_CORPO, color="#222222",
                ha="left", va="top", transform=ax.transAxes,
                wrap=True, linespacing=1.6, fontstyle="italic")

        # Autor da citação
        if cena.citacao:
            ax.text(0.15, 0.18, f"— {cena.citacao}", fontsize=20,
                    fontfamily=FONTE_TITULO, color=COR_VERDE_UFV,
                    ha="left", va="bottom", transform=ax.transAxes)

        self._add_host_label(ax, roteiro.hosts[cena.host]["nome"], idx)
        self._add_footer(ax, fonte=cena.fonte)
        plt.savefig(caminho, dpi=SLIDE_DPI, bbox_inches="tight",
                    facecolor=COR_FUNDO, pad_inches=0)
        plt.close()

    def _slide_encerramento(self, cena: Cena, roteiro: Roteiro, caminho: str):
        """Slide de encerramento."""
        fig, ax = self._base_fig()

        # Faixa verde
        ax.axhspan(0.55, 1.0, xmin=0, xmax=1, facecolor=COR_VERDE_UFV, alpha=0.95)

        # Título
        ax.text(0.5, 0.88, cena.titulo, fontsize=40, fontweight="bold",
                fontfamily=FONTE_TITULO, color="white",
                ha="center", va="center", transform=ax.transAxes)

        # Conteúdo
        if cena.conteudo:
            ax.text(0.5, 0.72, cena.conteudo, fontsize=20,
                    fontfamily=FONTE_CORPO, color="#E0E0E0",
                    ha="center", va="center", transform=ax.transAxes)

        # Fontes
        if roteiro.fontes:
            ax.text(0.5, 0.42, "Fontes consultadas:", fontsize=16,
                    fontfamily=FONTE_TITULO, color=COR_VERDE_UFV,
                    ha="center", va="center", transform=ax.transAxes,
                    fontweight="bold")
            for i, f in enumerate(roteiro.fontes[:5]):
                ax.text(0.5, 0.36 - i * 0.04, f"• {f}", fontsize=13,
                        fontfamily=FONTE_CORPO, color=COR_CINZA,
                        ha="center", va="center", transform=ax.transAxes)

        # Créditos
        ax.text(0.5, 0.08, f"Gerado por PesquisAI · {roteiro.instituicao}",
                fontsize=14, fontfamily=FONTE_TITULO, color=COR_CINZA_CLARO,
                ha="center", va="center", transform=ax.transAxes)

        self._add_footer(ax)
        plt.savefig(caminho, dpi=SLIDE_DPI, bbox_inches="tight",
                    facecolor=COR_FUNDO, pad_inches=0)
        plt.close()


# ═══════════════════════════════════════════════════════════════
# GERADOR DE ÁUDIO (EDGE-TTS)
# ═══════════════════════════════════════════════════════════════

class GeradorAudio:
    """Gera arquivos de áudio com vozes naturais via edge-tts."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def gerar_todos(self, roteiro: Roteiro) -> list[str]:
        """Gera MP3 para cada cena do roteiro.

        Returns:
            Lista de caminhos dos MP3 gerados.
        """
        caminhos = []
        for i, cena in enumerate(roteiro.cenas):
            voz = roteiro.hosts[cena.host]["voz"]
            caminho = os.path.join(self.output_dir, f"audio_{i:03d}.mp3")
            self._gerar_fala(cena.fala, voz, caminho)
            caminhos.append(caminho)
        return caminhos

    def _gerar_fala(self, texto: str, voz: str, caminho: str):
        """Gera arquivo de áudio para um texto com a voz especificada."""
        if not HAS_EDGE_TTS:
            # Fallback: criar áudio silencioso
            logger.warning("edge-tts não disponível. Gerando áudio mudo.")
            self._gerar_silencio(caminho, duracao=2.0)
            return

        try:
            asyncio.run(self._async_tts(texto, voz, caminho))
        except Exception as e:
            logger.error("Falha no edge-tts: %s. Gerando áudio mudo.", e)
            self._gerar_silencio(caminho, duracao=2.0)

    @staticmethod
    async def _async_tts(texto: str, voz: str, caminho: str):
        """Função assíncrona do edge-tts."""
        communicate = edge_tts.Communicate(texto, voz)
        await communicate.save(caminho)

    @staticmethod
    def _gerar_silencio(caminho: str, duracao: float = 2.0):
        """Gera áudio silencioso como fallback."""
        import struct
        import wave

        sample_rate = 24000
        n_samples = int(sample_rate * duracao)
        with wave.open(caminho, "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00" * n_samples * 2)


# ═══════════════════════════════════════════════════════════════
# GERADOR DE LEGENDAS (SRT)
# ═══════════════════════════════════════════════════════════════

class GeradorLegendas:
    """Gera arquivo .srt sincronizado com o roteiro."""

    @staticmethod
    def gerar(roteiro: Roteiro) -> str:
        """Gera conteúdo .srt a partir do roteiro.

        Returns:
            Conteúdo do arquivo .srt como string.
        """
        linhas = []
        idx = 1
        tempo_atual = 0.0

        for cena in roteiro.cenas:
            inicio = tempo_atual
            fim = tempo_atual + cena.duracao
            host = roteiro.hosts[cena.host]["nome"]

            linhas.append(str(idx))
            linhas.append(
                f"{_srt_time(inicio)} --> {_srt_time(fim)}"
            )
            linhas.append(f"{host}: {cena.fala}")
            linhas.append("")

            idx += 1
            tempo_atual = fim

        return "\n".join(linhas)


def _srt_time(segundos: float) -> str:
    """Converte segundos para formato SRT (HH:MM:SS,mmm)."""
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos - int(segundos)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ═══════════════════════════════════════════════════════════════
# MONTADOR DE VÍDEO (MOVIEPY)
# ═══════════════════════════════════════════════════════════════

class MontadorVideo:
    """Monta o vídeo final a partir dos slides e áudios."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def montar(self, slides: list[str], audios: list[str],
               roteiro: Roteiro) -> str:
        """Monta vídeo MP4 com slides + áudio sincronizados.

        Args:
            slides: Lista de caminhos dos PNGs.
            audios: Lista de caminhos dos MP3s.
            roteiro: Roteiro para obter durações.

        Returns:
            Caminho do arquivo .mp4 gerado.
        """
        if not HAS_MOVIEPY:
            logger.error("moviepy não disponível. Não é possível montar vídeo.")
            return ""

        if len(slides) != len(audios):
            logger.warning(
                "Nº slides (%d) ≠ nº áudios (%d). Usando mínimo.",
                len(slides), len(audios)
            )

        n = min(len(slides), len(audios))
        clips = []

        try:
            for i in range(n):
                slide_path = slides[i]
                audio_path = audios[i]

                if not os.path.exists(slide_path):
                    logger.warning("Slide %d não encontrado: %s", i, slide_path)
                    continue

                # Duração da cena
                duracao = roteiro.cenas[i].duracao if i < len(roteiro.cenas) else 5.0

                # Clip de imagem
                clip = ImageClip(slide_path, duration=duracao)

                # Áudio
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 100:
                    try:
                        audio = AudioFileClip(audio_path)
                        clip = clip.with_audio(audio)
                    except Exception as e:
                        logger.warning("Erro ao carregar áudio %s: %s", audio_path, e)

                clips.append(clip)

            if not clips:
                logger.error("Nenhum clip válido para montar.")
                return ""

            # Concatena todos os clips
            logger.info("Concatenando %d clips...", len(clips))
            video = concatenate_videoclips(clips, method="compose")

            # Caminho de saída
            output_path = os.path.join(
                self.output_dir, f"{roteiro.slug}.mp4"
            )

            # Exporta
            logger.info("Exportando vídeo para %s...", output_path)
            video.write_videofile(
                output_path,
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                bitrate="2000k",
                audio_bitrate="128k",
                preset="medium",
                logger=None,
                threads=2,
            )

            # Fecha clips
            video.close()
            for clip in clips:
                clip.close()

            return output_path

        except Exception as e:
            logger.error("Falha na montagem do vídeo: %s", e)
            return ""


# ═══════════════════════════════════════════════════════════════
# CLASSE PRINCIPAL: VODCAST
# ═══════════════════════════════════════════════════════════════

class Vodcast:
    """Motor principal de geração de vodcasts acadêmicos.

    Uso:
        v = Vodcast()
        resultado = v.produzir("Mortalidade infantil no Nordeste", dados={...})
        print(f"Vídeo: {resultado['video']}")
        print(f"Áudio: {resultado['audio']}")
    """

    def __init__(self, output_dir: str = DIR_VODCAST):
        """Inicializa o motor de vodcast.

        Args:
            output_dir: Diretório para salvar os arquivos gerados.
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._log_diagnostics()

    def _log_diagnostics(self):
        """Registra diagnóstico das dependências disponíveis."""
        logger.info("Vodcast inicializado em: %s", self.output_dir)
        logger.info("  edge-tts:  %s", "✅" if HAS_EDGE_TTS else "❌")
        logger.info("  moviepy:   %s", "✅" if HAS_MOVIEPY else "❌")
        logger.info("  matplotlib:%s", "✅" if HAS_MPL else "❌")
        logger.info("  ffmpeg:    %s",
                    "✅" if subprocess.run(["which", "ffmpeg"],
                                         capture_output=True).returncode == 0
                    else "❌")

    def produzir(self, tema: str, dados: Optional[dict] = None) -> dict:
        """Pipeline completa: tema → roteiro → slides → áudio → vídeo.

        Args:
            tema: Tema do vodcast (ex: "Evolução do preço da soja no Brasil")
            dados: Dados opcionais. Se None, o roteiro será genérico.
                  Estrutura esperada:
                    {
                        "fontes": ["IBGE", "DataSUS"],
                        "indicadores": [
                            {
                                "nome": "Taxa de mortalidade infantil",
                                "valor": "12,4 por mil nascidos vivos",
                                "comparacao": "queda de 45% desde 2010",
                                "periodo": "2010-2024",
                                "fonte": "DataSUS/SIM",
                                "grafico": {
                                    "labels": ["2010", "2014", "2018", "2022", "2024"],
                                    "valores": [22.5, 18.3, 15.1, 13.2, 12.4],
                                },
                                "tipo_grafico": "line",
                            }
                        ],
                        "citacoes": [
                            {
                                "autor": "Silva et al.",
                                "ano": "2023",
                                "texto": "A expansão da ESF foi determinante...",
                                "fonte": "Rev. Saúde Pública",
                            }
                        ],
                    }

        Returns:
            Dict com caminhos dos arquivos gerados:
                {
                    "video": "path/to/video.mp4",
                    "audio": "path/to/audio.mp3",
                    "slides": [...],
                    "legendas": "path/to/legendas.srt",
                    "roteiro": "path/to/roteiro.md",
                    "duracao": 123.0,
                }
        """
        resultado = {
            "tema": tema,
            "video": "",
            "audio": "",
            "slides": [],
            "legendas": "",
            "roteiro_md": "",
            "duracao": 0.0,
            "status": "iniciado",
        }

        logger.info("═" * 50)
        logger.info("🎬 Vodcast: %s", tema)
        logger.info("═" * 50)

        # ── 1. Gera roteiro ───────────────────────────────────
        logger.info("[1/5] Gerando roteiro...")
        roteiro = GeradorRoteiro.gerar(tema, dados)
        resultado["duracao"] = roteiro.duracao_total
        logger.info("  → %d cenas, ~%.0f segundos",
                    len(roteiro.cenas), roteiro.duracao_total)

        # ── 2. Gera slides ────────────────────────────────────
        logger.info("[2/5] Gerando slides...")
        slides_dir = os.path.join(self.output_dir, f"{roteiro.slug}_slides")
        gerador_slides = GeradorSlides(slides_dir)
        slides = gerador_slides.gerar_todos(roteiro, dados)
        resultado["slides"] = slides
        logger.info("  → %d slides gerados", len(slides))

        # ── 3. Gera áudio ─────────────────────────────────────
        logger.info("[3/5] Gerando áudio (edge-tts)...")
        audio_dir = os.path.join(self.output_dir, f"{roteiro.slug}_audio")
        gerador_audio = GeradorAudio(audio_dir)
        audios = gerador_audio.gerar_todos(roteiro)
        logger.info("  → %d arquivos de áudio", len(audios))

        # ── 4. Gera legendas ──────────────────────────────────
        logger.info("[4/5] Gerando legendas SRT...")
        srt_conteudo = GeradorLegendas.gerar(roteiro)
        srt_path = os.path.join(self.output_dir, f"{roteiro.slug}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_conteudo)
        resultado["legendas"] = srt_path
        logger.info("  → Legendas salvas")

        # ── 5. Monta vídeo ────────────────────────────────────
        logger.info("[5/5] Montando vídeo...")
        montador = MontadorVideo(self.output_dir)
        video_path = montador.montar(slides, audios, roteiro)
        resultado["video"] = video_path

        # ── 6. Gera MP3 completo ──────────────────────────────
        logger.info("[Extra] Gerando MP3 completo...")
        audio_completo = self._concatenar_audios(audios, roteiro)
        resultado["audio"] = audio_completo

        # ── 7. Salva roteiro em Markdown ──────────────────────
        logger.info("[Extra] Salvando roteiro MD...")
        roteiro_md = self._salvar_roteiro_md(roteiro)
        resultado["roteiro_md"] = roteiro_md

        # Final
        if video_path:
            resultado["status"] = "concluido"
            logger.info("═" * 50)
            logger.info("✅ Vodcast concluído!")
            logger.info("  📹 Vídeo: %s", video_path)
            logger.info("  🎵 Áudio: %s", audio_completo)
            logger.info("  📝 Roteiro: %s", roteiro_md)
            logger.info("  💬 Legendas: %s", srt_path)
            logger.info("  ⏱️ Duração: %.0f segundos (%.1f min)",
                        roteiro.duracao_total, roteiro.duracao_total / 60)
        else:
            resultado["status"] = "erro"
            logger.error("❌ Falha na geração do vodcast.")

        return resultado

    def _concatenar_audios(self, audios: list[str], roteiro: Roteiro) -> str:
        """Concatena todos os áudios em um MP3 único."""
        from io import BytesIO

        output = os.path.join(self.output_dir, f"{roteiro.slug}.mp3")

        if not audios:
            return ""

        # Usa ffmpeg para concatenar (mais rápido que moviepy para áudio)
        try:
            # Cria lista de arquivos para o ffmpeg
            lista_path = os.path.join(self.output_dir, f"{roteiro.slug}_lista.txt")
            with open(lista_path, "w") as f:
                for a in audios:
                    if os.path.exists(a) and os.path.getsize(a) > 100:
                        f.write(f"file '{os.path.abspath(a)}'\n")

            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", lista_path,
                 "-c", "copy",
                 "-loglevel", "quiet",
                 output],
                check=True,
                capture_output=True,
            )
            os.remove(lista_path)
            return output
        except Exception as e:
            logger.warning("Falha ao concatenar áudios: %s", e)
            # Fallback: retorna primeiro áudio
            return audios[0] if audios else ""

    def _salvar_roteiro_md(self, roteiro: Roteiro) -> str:
        """Salva o roteiro em formato Markdown."""
        caminho = os.path.join(self.output_dir, f"{roteiro.slug}_roteiro.md")

        linhas = [
            f"# 🎬 {roteiro.tema}",
            "",
            f"**Duração:** {roteiro.duracao_total:.0f}s ({roteiro.duracao_total/60:.1f}min)",
            f"**Data:** {roteiro.data_geracao[:10]}",
            f"**Instituição:** {roteiro.instituicao}",
            "",
            "---",
            "## 🎙️ Elenco",
            f"- **{roteiro.hosts[0]['nome']}** — Voz: {roteiro.hosts[0]['voz']}",
            f"- **{roteiro.hosts[1]['nome']}** — Voz: {roteiro.hosts[1]['voz']}",
            "",
            "---",
            "## 📋 Roteiro",
            "",
        ]

        for i, cena in enumerate(roteiro.cenas):
            host = roteiro.hosts[cena.host]["nome"]
            emoji = {"abertura": "🎬", "texto": "📊", "grafico": "📈",
                     "citacao": "📚", "destaque": "💡",
                     "encerramento": "🏁"}.get(cena.tipo, "📌")

            linhas.append(f"### {emoji} Cena {i+1}: {cena.titulo} ({cena.duracao:.0f}s)")
            linhas.append("")
            linhas.append(f"**{host}:** {cena.fala}")
            linhas.append("")
            if cena.conteudo:
                linhas.append(f"> {cena.conteudo}")
                linhas.append("")
            if cena.citacao:
                linhas.append(f"📚 *{cena.citacao}*")
                linhas.append("")
            linhas.append("---")
            linhas.append("")

        # Fontes
        if roteiro.fontes:
            linhas.append("## 📚 Fontes")
            for f in roteiro.fontes:
                linhas.append(f"- {f}")

        with open(caminho, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))

        return caminho


# ═══════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL (CLI)
# ═══════════════════════════════════════════════════════════════

def produzir(tema: str, dados: Optional[dict] = None) -> dict:
    """Função de conveniência para gerar um vodcast rapidamente.

    Uso:
        from vodcast import produzir
        resultado = produzir("Evolução do preço da soja no Brasil")
    """
    v = Vodcast()
    return v.produzir(tema, dados)


if __name__ == "__main__":
    # Exemplo de uso direto
    logging.basicConfig(level=logging.INFO)

    vodcast = Vodcast()
    
    # Dados de exemplo
    dados_exemplo = {
        "fontes": [
            "DataSUS/SIM (Sistema de Informação de Mortalidade)",
            "IBGE/PNAD Contínua",
        ],
        "indicadores": [
            {
                "nome": "Taxa de Mortalidade Infantil (Brasil)",
                "valor": "12,4 óbitos por mil nascidos vivos",
                "comparacao": "queda de 45% em relação a 2010",
                "periodo": "2010-2024",
                "fonte": "DataSUS/SIM",
                "grafico": {
                    "labels": ["2010", "2012", "2014", "2016", "2018", "2020", "2022", "2024"],
                    "valores": [22.5, 20.8, 18.3, 16.2, 15.1, 14.0, 13.2, 12.4],
                },
                "tipo_grafico": "line",
            },
            {
                "nome": "Cobertura da Estratégia Saúde da Família",
                "valor": "75,3% da população",
                "comparacao": "aumento de 15 pontos percentuais desde 2010",
                "periodo": "2010-2024",
                "fonte": "DataSUS/e-Gestor",
                "grafico": {
                    "labels": ["2010", "2014", "2018", "2022", "2024"],
                    "valores": [60.2, 65.8, 70.1, 73.5, 75.3],
                },
                "tipo_grafico": "bar",
            },
        ],
        "citacoes": [
            {
                "autor": "Victora et al.",
                "ano": "2021",
                "texto": "A Estratégia Saúde da Família é responsável por cerca de 40% da redução da mortalidade infantil no Brasil na última década.",
                "fonte": "The Lancet",
            },
        ],
    }

    resultado = vodcast.produzir(
        "Mortalidade Infantil no Brasil: 2010-2024",
        dados=dados_exemplo,
    )
    
    print("\n✅ Vodcast gerado!")
    for k, v in resultado.items():
        print(f"  {k}: {v}")
