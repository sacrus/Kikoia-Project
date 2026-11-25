"""Textos da interface em varios idiomas.

Os textos estao em data/idiomas/<codigo>.json (chave -> texto). Chaves que faltam num
idioma usam o portugues de Portugal, por isso um idioma incompleto nunca mostra chaves
em bruto. O idioma escolhido aplica-se ao arrancar o teclado.
"""

from __future__ import annotations

import json
import os
import sys
import time
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


def caminho_partilhado(base: Path | None = None) -> Path:
    if base is not None:
        return base / "idioma_partilhado.json"
    if sys.platform == "win32":
        raiz = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(raiz) / "Kikoia" / "idioma_partilhado.json"
    raiz = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(raiz) / "Kikoia" / "idioma_partilhado.json"


def ler_partilhado(base: Path | None = None) -> dict | None:
    ficheiro = caminho_partilhado(base)
    try:
        dados = json.loads(ficheiro.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or dados.get("idioma") not in IDIOMAS:
        return None
    return {"idioma": dados["idioma"], "atualizado_em": float(dados.get("atualizado_em", 0.0))}


def guardar_partilhado(codigo: str, base: Path | None = None) -> float:
    codigo = idioma_valido(codigo)
    destino = caminho_partilhado(base)
    destino.parent.mkdir(parents=True, exist_ok=True)
    agora = time.time()
    tmp = destino.with_suffix(".tmp")
    tmp.write_text(json.dumps({"idioma": codigo, "atualizado_em": agora}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, destino)
    return agora
