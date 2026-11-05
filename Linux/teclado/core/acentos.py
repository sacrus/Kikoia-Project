"""Acentos de tecla morta: nome -> (marca combinatoria Unicode, sinal isolado).

A marca combinatoria junta-se a letra seguinte (NFC). O sinal isolado sai
quando nao ha combinacao possivel, ou quando o acento nao e seguido de letra.
So se combinam as letras em que o acento existe em portugues.
"""

from __future__ import annotations

import unicodedata

ACENTOS: dict[str, tuple[str, str]] = {
    "agudo": ("\u0301", "\u00b4"),
    "grave": ("\u0300", "`"),
    "circunflexo": ("\u0302", "^"),
    "til": ("\u0303", "~"),
}

_VOGAIS = "aeiouAEIOU"
COMBINAVEIS: dict[str, frozenset[str]] = {
    "agudo": frozenset(_VOGAIS),
    "grave": frozenset("aeiouAEIOU"),
    "circunflexo": frozenset(_VOGAIS),
    "til": frozenset("aoAO"),
}


def combinar(letra: str, acento: str) -> str | None:
    """Devolve a letra acentuada (um so caracter), ou None se o acento nao existe nessa letra."""
    if letra not in COMBINAVEIS[acento]:
        return None
    resultado = unicodedata.normalize("NFC", letra + ACENTOS[acento][0])
    return resultado if len(resultado) == 1 else None
