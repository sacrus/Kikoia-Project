"""Teclas personalizadas do PC: cada uma executa um programa ou comando.

Seguranca: o telemovel nunca envia texto de comando. Envia so o identificador de uma
tecla, e o PC executa o comando guardado nas suas definicoes. Criar, alterar e apagar
comandos e uma configuracao (pede codigo do adulto em perfis supervisionados).
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ID_RE = re.compile(r"[a-z0-9_]{1,40}")
MAX_ROTULO = 30
MAX_COMANDO = 300
FICHEIRO = "comandos.json"


class ComandoErro(RuntimeError):
    """Nao foi possivel executar o comando. A mensagem e para o utilizador."""


@dataclass(frozen=True)
class Comando:
    id: str
    rotulo: str
    comando: str


def validar(rotulo: str | None, comando: str | None) -> tuple[str, str]:
    r = (rotulo or "").strip()
    c = (comando or "").strip()
    if not r or len(r) > MAX_ROTULO:
        raise ValueError(f"O nome da tecla deve ter entre 1 e {MAX_ROTULO} caracteres.")
    if not c or len(c) > MAX_COMANDO:
        raise ValueError(f"O programa ou comando deve ter entre 1 e {MAX_COMANDO} caracteres.")
    if any(ord(ch) < 32 for ch in c):
        raise ValueError("O comando não pode ter quebras de linha.")
    return r, c


def novo_id() -> str:
    return "c" + secrets.token_hex(4)


def carregar(pasta: Path) -> dict[str, Comando]:
    caminho = Path(pasta) / FICHEIRO
    if not caminho.is_file():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    resultado: dict[str, Comando] = {}
    for item in dados if isinstance(dados, list) else []:
        try:
            id_ = str(item["id"])
            if not ID_RE.fullmatch(id_):
                continue
            rotulo, comando = validar(item["rotulo"], item["comando"])
        except (KeyError, TypeError, ValueError):
            continue
        resultado[id_] = Comando(id_, rotulo, comando)
    return resultado


def gravar(pasta: Path, comandos: dict[str, Comando]) -> None:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    dados = [{"id": c.id, "rotulo": c.rotulo, "comando": c.comando} for c in comandos.values()]
    temporario = pasta / (FICHEIRO + ".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, pasta / FICHEIRO)


def executar(texto: str) -> None:
    """Abre um ficheiro (como no Explorador) ou executa um programa com argumentos opcionais."""
    comando = texto.strip()
    try:
        if sys.platform == "win32":
            if os.path.exists(comando.strip('"')):
                os.startfile(comando.strip('"'))  # type: ignore[attr-defined]
                return
            subprocess.Popen(comando)
        else:
            subprocess.Popen(shlex.split(comando))
    except (OSError, ValueError) as erro:
        raise ComandoErro(f"Não foi possível executar: {comando}") from erro
