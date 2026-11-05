"""Verificacao de atualizacoes: do teclado (GitHub Releases) e das dependencias (PyPI).

Esta modulo so consulta e, quando pedido, atualiza as dependencias com pip. Nunca instala
o teclado sozinho: o utilizador abre a pagina da versao nova e transfere-a.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from .paths import RAIZ

VERSAO = "0.1.0"
# "dono/repositorio" no GitHub. Enquanto estiver a None, a verificacao do teclado fica desativada.
REPOSITORIO: str | None = "sacrus/Kikoia-Project"
TIMEOUT_S = 8
REQUISITOS = RAIZ / "requirements.txt"


@dataclass(frozen=True)
class Dependencia:
    nome: str
    instalada: str | None
    mais_recente: str | None

    @property
    def desatualizada(self) -> bool:
        return bool(
            self.instalada and self.mais_recente
            and versao_tupla(self.mais_recente) > versao_tupla(self.instalada)
        )


@dataclass(frozen=True)
class Atualizacao:
    versao: str
    pagina: str


def versao_tupla(texto: str) -> tuple[int, ...]:
    """'v1.2.10' -> (1, 2, 10). Compara numericamente, por isso 1.10 > 1.9."""
    sem_epoca = re.sub(r"^\d+!", "", texto)  # '4!10.0' (epoca do PEP 440) compara como '10.0'
    numeros = [int(n) for n in re.findall(r"\d+", sem_epoca)[:4]]
    return tuple(numeros) or (0,)


def nomes_dependencias(ficheiro: Path = REQUISITOS) -> list[str]:
    """Nomes dos pacotes do requirements.txt que se aplicam a este sistema."""
    nomes: list[str] = []
    for linha in ficheiro.read_text(encoding="utf-8").splitlines():
        linha = linha.split("#", 1)[0].strip()
        if not linha:
            continue
        if ";" in linha:
            linha, marcador = (parte.strip() for parte in linha.split(";", 1))
            if "win32" in marcador and sys.platform != "win32":
                continue
        correspondencia = re.match(r"[A-Za-z0-9_.\-]+", linha)
        if correspondencia:
            nomes.append(correspondencia.group(0))
    return nomes


def _json(url: str) -> dict[str, Any]:
    pedido = urllib.request.Request(url, headers={"User-Agent": f"Kikoia/{VERSAO}"})
    with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def versao_instalada(nome: str) -> str | None:
    try:
        return metadata.version(nome)
    except metadata.PackageNotFoundError:
        return None


def versao_pypi(nome: str, buscar: Callable[[str], dict[str, Any]] = _json) -> str | None:
    dados = buscar(f"https://pypi.org/pypi/{nome}/json")
    versao = dados.get("info", {}).get("version")
    return versao if isinstance(versao, str) else None


def verificar_dependencias(
    nomes: list[str] | None = None,
    buscar: Callable[[str], dict[str, Any]] = _json,
) -> list[Dependencia]:
    """Compara cada dependencia instalada com a versao mais recente no PyPI.

    Um pacote que nao responde (sem rede) fica com 'mais_recente' a None: nao e marcado como
    desatualizado.
    """
    resultados = []
    if nomes is None and empacotado():
        return resultados
    for nome in nomes if nomes is not None else nomes_dependencias():
        try:
            recente = versao_pypi(nome, buscar)
        except (OSError, ValueError):
            recente = None
        resultados.append(Dependencia(nome, versao_instalada(nome), recente))
    return resultados


def teclado_configurado() -> bool:
    return REPOSITORIO is not None


def empacotado() -> bool:
    """True no executavel (PyInstaller): nao ha pip, por isso as dependencias nao se atualizam aqui."""
    return bool(getattr(sys, "frozen", False))


def verificar_teclado(buscar: Callable[[str], dict[str, Any]] = _json) -> Atualizacao | None:
    """Devolve a versao mais recente do GitHub se for maior que a instalada; senao None."""
    if REPOSITORIO is None:
        return None
    dados = buscar(f"https://api.github.com/repos/{REPOSITORIO}/releases/latest")
    etiqueta = dados.get("tag_name")
    if not isinstance(etiqueta, str):
        return None
    if versao_tupla(etiqueta) <= versao_tupla(VERSAO):
        return None
    pagina = dados.get("html_url")
    return Atualizacao(etiqueta.lstrip("vV"), pagina if isinstance(pagina, str) else "")


def comando_atualizar(nomes: list[str]) -> list[str]:
    """Argumentos para pip atualizar os pacotes indicados, com o mesmo Python que corre o teclado."""
    return [sys.executable, "-m", "pip", "install", "--upgrade", *nomes]
