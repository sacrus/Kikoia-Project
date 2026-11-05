"""Textos da interface em varios idiomas.

Os textos estao em data/idiomas/<codigo>.json (chave -> texto). Chaves que faltam num
idioma usam o portugues de Portugal, por isso um idioma incompleto nunca mostra chaves
em bruto. O idioma escolhido aplica-se ao arrancar o teclado.
"""

from __future__ import annotations

import json
from pathlib import Path

from .paths import DADOS_PROJETO

IDIOMA_PADRAO = "pt-PT"
IDIOMAS = {
    "pt-PT": "Português (Portugal)",
    "en": "English",
    "es": "Español",
    "fr": "Français",
}

_pasta = DADOS_PROJETO / "idiomas"
_catalogos: dict[str, dict[str, str]] = {}
_atual = IDIOMA_PADRAO


def _carregar(codigo: str) -> dict[str, str]:
    if codigo not in _catalogos:
        caminho: Path = _pasta / f"{codigo}.json"
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            dados = {}
        _catalogos[codigo] = {k: v for k, v in dados.items() if isinstance(v, str)}
    return _catalogos[codigo]


def idioma_valido(codigo: object) -> str:
    return codigo if isinstance(codigo, str) and codigo in IDIOMAS else IDIOMA_PADRAO


def definir(codigo: object) -> str:
    """Escolhe o idioma da interface. Codigos desconhecidos usam o padrao."""
    global _atual
    _atual = idioma_valido(codigo)
    return _atual


def atual() -> str:
    return _atual


def t(chave: str, **valores: object) -> str:
    """Texto da chave no idioma atual (ou em portugues, se faltar). Aceita {campos}."""
    texto = _carregar(_atual).get(chave)
    if texto is None:
        texto = _carregar(IDIOMA_PADRAO).get(chave, chave)
    return texto.format(**valores) if valores else texto
