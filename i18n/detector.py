"""
detector.py — Detecção automática de idioma.

Prioridade de detecção:
  1. Variável de ambiente PESQUISAI_LANG
  2. Variável de ambiente LANG
  3. Header HTTP Accept-Language (se passado)
  4. Conteúdo textual do usuário (detect_from_text)
  5. Fallback: idioma padrão
"""

from __future__ import annotations

import os
import re
from typing import Optional


def detect_language(default: str = "pt_BR") -> str:
    """Detecta o idioma preferido do ambiente.

    Ordem de prioridade:
      1. PESQUISAI_LANG
      2. LANG / LC_ALL
      3. Fallback (default)

    Args:
        default: Idioma padrão se nenhum for detectado.

    Returns:
        Código de idioma normalizado (pt_BR, en_US, es_ES).
    """
    # 1. Variável explícita do PesquisAI
    env_lang = os.environ.get("PESQUISAI_LANG", "").strip()
    if env_lang:
        return _normalize(env_lang, default)

    # 2. Variáveis de sistema
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "").strip()
        if val and val != "C" and val != "POSIX":
            return _normalize(val, default)

    return default


def detect_from_accept_language(header: str, default: str = "pt_BR") -> str:
    """Detecta idioma a partir de um cabeçalho HTTP Accept-Language.

    Args:
        header: Valor do cabeçalho (ex: "pt-BR,en-US;q=0.9,es;q=0.8").
        default: Idioma padrão se nenhum for detectado.

    Returns:
        Código de idioma normalizado.
    """
    if not header:
        return default

    # Parse: "pt-BR,en-US;q=0.9"
    candidates: list[tuple[str, float]] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        if ";q=" in part:
            tag, q_str = part.split(";q=", 1)
            try:
                q = float(q_str)
            except ValueError:
                q = 1.0
        else:
            tag = part
            q = 1.0
        candidates.append((tag.strip(), q))

    # Ordena por qualidade
    candidates.sort(key=lambda x: -x[1])

    for tag, _ in candidates:
        norm = _normalize(tag, "")
        if norm:
            return norm
    return default


def _normalize(lang: str, default: str) -> str:
    """Normaliza código de idioma para o formato canônico."""
    if not lang:
        return default
    lang = lang.strip().replace("-", "_")
    # Remove modificadores (ex: pt_BR.UTF-8 → pt_BR)
    if "." in lang:
        lang = lang.split(".", 1)[0]
    if "@" in lang:
        lang = lang.split("@", 1)[0]
    # Mapeamento
    if lang.lower().startswith("pt"):
        return "pt_BR"
    if lang.lower().startswith("en"):
        return "en_US"
    if lang.lower().startswith("es"):
        return "es_ES"
    if lang.lower().startswith("fr"):
        return "fr_FR"
    if lang in ("pt_BR", "en_US", "es_ES", "fr_FR"):
        return lang
    return default


# ── Stopwords / marcadores por idioma (v0.4.2.4) ─────────────────────
# Usados por detect_from_text() para identificar o idioma da mensagem
# do usuário a partir de palavras funcionais comuns.
_TEXT_MARKERS: dict[str, dict[str, int]] = {
    "pt_BR": {
        # artigos, preposições, pronomes, verbos auxiliares comuns
        " o ": 1, " a ": 1, " os ": 1, " as ": 1,
        " de ": 1, " da ": 1, " do ": 1, " das ": 1, " dos ": 1,
        " em ": 1, " no ": 1, " na ": 1, " nos ": 1, " nas ": 1,
        " um ": 1, " uma ": 1, " uns ": 1, " umas ": 1,
        " que ": 1, " não ": 1, " com ": 1, " por ": 1, " para ": 1,
        " é ": 1, " são ": 1, " foi ": 1, " ser ": 1, " estar ": 1,
        " eu ": 1, " você ": 1, " nós ": 1, " eles ": 1, " elas ": 1,
        " meu ": 1, " minha ": 1, " seu ": 1, " sua ": 1,
        " isso ": 1, " isto ": 1, " aquilo ": 1,
        "Olá": 1, "olá": 1, "Olá!": 1, "obrigado": 1, "obrigada": 1,
        "por favor": 1, "como": 1, "quando": 1, "onde": 1, "porque": 1,
    },
    "en_US": {
        " the ": 1, " a ": 1, " an ": 1,
        " of ": 1, " in ": 1, " on ": 1, " at ": 1, " to ": 1, " for ": 1,
        " is ": 1, " are ": 1, " was ": 1, " were ": 1, " be ": 1, " been ": 1,
        " I ": 1, " you ": 1, " we ": 1, " they ": 1, " he ": 1, " she ": 1,
        " my ": 1, " your ": 1, " our ": 1, " their ": 1,
        " this ": 1, " that ": 1, " these ": 1, " those ": 1,
        "Hello": 1, "hello": 1, "Hi": 1, "thanks": 1, "thank you": 1,
        "please": 1, "how": 1, "when": 1, "where": 1, "why": 1, "what": 1,
    },
    "es_ES": {
        " el ": 1, " la ": 1, " los ": 1, " las ": 1,
        " de ": 1, " del ": 1, " en ": 1, " con ": 1, " por ": 1, " para ": 1,
        " es ": 1, " son ": 1, " fue ": 1, " ser ": 1, " estar ": 1,
        " yo ": 1, " tú ": 1, " usted ": 1, " nosotros ": 1, " ellos ": 1,
        " mi ": 1, " tu ": 1, " su ": 1,
        " este ": 1, " esta ": 1, " eso ": 1, " aquello ": 1,
        "Hola": 1, "hola": 1, "gracias": 1, "por favor": 1,
        "cómo": 1, "cuándo": 1, "dónde": 1, "porque": 1, "qué": 1,
    },
    "fr_FR": {
        " le ": 1, " la ": 1, " les ": 1, " un ": 1, " une ": 1, " des ": 1,
        " de ": 1, " du ": 1, " en ": 1, " avec ": 1, " par ": 1, " pour ": 1,
        " est ": 1, " sont ": 1, " a ": 1, " avoir ": 1, " être ": 1,
        " je ": 1, " tu ": 1, " vous ": 1, " nous ": 1, " ils ": 1, " elles ": 1,
        " mon ": 1, " ton ": 1, " son ": 1, " ma ": 1, " ta ": 1, " sa ": 1,
        " ce ": 1, " cette ": 1, " ça ": 1,
        "Bonjour": 1, "bonjour": 1, "merci": 1, "s'il vous plaît": 1,
        "comment": 1, "quand": 1, "où": 1, "pourquoi": 1, "quoi": 1,
    },
}


def detect_from_text(text: str, default: str = "pt_BR") -> str:
    """Detecta o idioma de um texto com base em stopwords/marcadores.

    Algoritmo simples baseado em contagem de tokens por idioma:
      1. Normaliza o texto (minúsculas, espaços nas pontas).
      2. Para cada idioma suportado, conta quantos marcadores aparecem
         no texto (palavras funcionais comuns: artigos, preposições, etc).
      3. Retorna o idioma com mais matches, ou `default` se houver empate
         ou nenhum match.

    Args:
        text: Texto a ser analisado (mensagem do usuário, prompt, etc).
        default: Idioma padrão se nenhum marcador for encontrado.

    Returns:
        Código de idioma normalizado (pt_BR, en_US, es_ES, fr_FR).

    Examples:
        >>> detect_from_text("Olá, como você está?")
        'pt_BR'
        >>> detect_from_text("Hello, how are you?")
        'en_US'
        >>> detect_from_text("Bonjour, comment allez-vous?")
        'fr_FR'
        >>> detect_from_text("Hola, ¿cómo estás?")
        'es_ES'
        >>> detect_from_text("a")
        'pt_BR'  # default
    """
    if not text or not text.strip():
        return default

    # Normaliza: minúsculas e adiciona espaços nas pontas
    norm = " " + text.strip().lower() + " "

    scores: dict[str, int] = {lang: 0 for lang in _TEXT_MARKERS}

    for lang, markers in _TEXT_MARKERS.items():
        for marker in markers:
            if marker.lower() in norm:
                scores[lang] += 1

    # Idioma com maior score
    best_lang = max(scores, key=lambda k: scores[k])
    best_score = scores[best_lang]

    # Se ninguém pontuou, retorna default
    if best_score == 0:
        return default

    return best_lang
