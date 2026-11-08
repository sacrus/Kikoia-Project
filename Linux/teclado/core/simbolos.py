"""Simbolos que cada tecla escreve com Shift, como num teclado real (1 -> !, ç -> Ç).

Cada idioma tem a sua tabela, do teclado mais comum nesse idioma. Uma tecla de layout pode
trazer o seu proprio simbolo com Shift (campo "shift"); se nao trouxer, usa esta tabela.
"""

from __future__ import annotations

SIMBOLOS_SHIFT: dict[str, dict[str, str]] = {
    "pt-PT": {
        "1": "!", "2": '"', "3": "#", "4": "$", "5": "%", "6": "&", "7": "/", "8": "(", "9": ")", "0": "=",
        "'": "?", "+": "*", "<": ">", ",": ";", ".": ":", "-": "_", "ç": "Ç", "º": "ª",
    },
    "en": {
        "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
        "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|", ";": ":", "'": '"', ",": "<", ".": ">",
        "/": "?", "`": "~",
    },
    "es": {
        "1": "!", "2": '"', "3": "·", "4": "$", "5": "%", "6": "&", "7": "/", "8": "(", "9": ")", "0": "=",
        "'": "?", "¡": "¿", "+": "*", "ç": "Ç", "ñ": "Ñ", ",": ";", ".": ":", "-": "_",
    },
    "fr": {
        ",": "?", ";": ".", ":": "/", "!": "§", "-": "_", "ç": "Ç", "à": "À", "é": "É", "è": "È", "ù": "Ù",
    },
}


def simbolos_para(idioma: str) -> dict[str, str]:
    """Tabela de Shift do idioma (vazia se o idioma nao tiver uma)."""
    return SIMBOLOS_SHIFT.get(idioma, {})
