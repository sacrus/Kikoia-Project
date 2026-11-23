"""Sincronizacao bidirecional de tema (Claro/Escuro) entre o Teclado Kikoia e o Quadro Interativo.

Guarda um ficheiro leve na pasta partilhada do utilizador (`%LOCALAPPDATA%\\Kikoia\\tema_partilhado.json`
no Windows, `~/.local/share/Kikoia/tema_partilhado.json` no Linux), sem dados pessoais.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

NOME_FICHEIRO = "tema_partilhado.json"


def caminho_tema(base: Path | None = None) -> Path:
    if base is not None:
        return base / NOME_FICHEIRO
    if sys.platform == "win32":
        raiz = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(raiz) / "Kikoia" / NOME_FICHEIRO
    raiz = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(raiz) / "Kikoia" / NOME_FICHEIRO


def ler_tema(base: Path | None = None) -> dict | None:
    """Devolve {'escuro': bool, 'tema': str, 'atualizado_em': float} ou None se nao existir."""
    ficheiro = caminho_tema(base)
    try:
        dados = json.loads(ficheiro.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("escuro"), bool):
        return None
    return {
        "escuro": dados["escuro"],
        "tema": dados.get("tema") if isinstance(dados.get("tema"), str) else ("Escuro" if dados["escuro"] else "Claro"),
        "atualizado_em": float(dados.get("atualizado_em", 0.0)),
    }


def guardar_tema(escuro: bool, tema: str | None = None, base: Path | None = None) -> float:
    """Guarda o tema partilhado de forma atomica. Devolve o timestamp gravado."""
    destino = caminho_tema(base)
    destino.parent.mkdir(parents=True, exist_ok=True)
    agora = time.time()
    payload = {
        "escuro": bool(escuro),
        "tema": tema or ("Escuro" if escuro else "Claro"),
        "atualizado_em": agora,
    }
    tmp = destino.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, destino)
    return agora
