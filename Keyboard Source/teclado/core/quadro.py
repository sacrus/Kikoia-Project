"""Quadro Interativo: programa separado, transferido do GitHub quando o utilizador o pede.

O teclado so guarda o que precisa para abrir o Quadro. A transferencia usa a ultima release do
repositorio do Quadro; o ficheiro e verificado com o SHA-256 que o GitHub publica para o anexo.
Sem essa verificacao nada e instalado. Atualizacoes sao sempre uma escolha do utilizador.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from teclado.core.atualizacao import VERSAO, versao_tupla

REPOSITORIO = "sacrus/Kikoia-Project-Board"
NOME_ARQUIVO = "Kikoia-Quadro-Windows.zip" if sys.platform == "win32" else "Kikoia-Quadro-Linux-x86_64.zip"
EXECUTAVEL = "KikoiaQuadro.exe" if sys.platform == "win32" else "KikoiaQuadro"
TIMEOUT_S = 15
TAMANHO_BLOCO = 64 * 1024
_TAG = re.compile(r"v?[0-9][0-9A-Za-z.\-]*")


class QuadroErro(RuntimeError):
    """A mensagem e uma chave de traducao (ex.: quadro.verificacao_falhou)."""


@dataclass(frozen=True)
class Versao:
    tag: str
    ficheiro_url: str
    sha256: str
    tamanho: int


def suportado() -> bool:
    """O Quadro funciona em Windows e em Linux."""
    return sys.platform == "win32" or sys.platform.startswith("linux")


def pasta_quadro() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("XDG_DATA_HOME")
            or str(Path.home() / ".local" / "share")
        )
    return Path(base) / "Kikoia" / "Quadro"


def _json(url: str) -> dict:
    pedido = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"Kikoia/{VERSAO}"},
    )
    with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def ultima_versao(buscar: Callable[[str], dict] | None = None) -> Versao | None:
    """Ultima release publicada com o ficheiro do Quadro. None se ainda nao houver release."""
    buscar = buscar or _json
    try:
        dados = buscar(f"https://api.github.com/repos/{REPOSITORIO}/releases/latest")
    except urllib.error.HTTPError as erro:
        if erro.code == 404:
            return None
        raise
    tag = dados.get("tag_name")
    if not isinstance(tag, str) or not _TAG.fullmatch(tag):
        return None
    for anexo in dados.get("assets", []):
        if anexo.get("name") != NOME_ARQUIVO:
            continue
        digest = anexo.get("digest") or ""
        if not digest.startswith("sha256:"):
            raise QuadroErro("quadro.sem_verificacao")
        return Versao(tag, anexo["browser_download_url"], digest[len("sha256:"):], int(anexo.get("size", 0)))
    return None


def instalacao_atual(pasta: Path | None = None) -> dict | None:
    caminho = (pasta or pasta_quadro()) / "atual.json"
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(dados, dict) or not Path(str(dados.get("exe", ""))).is_file():
        return None
    return dados


def versao_instalada(pasta: Path | None = None) -> str | None:
    dados = instalacao_atual(pasta)
    return str(dados["versao"]) if dados else None


def exe_instalado(pasta: Path | None = None) -> Path | None:
    dados = instalacao_atual(pasta)
    return Path(str(dados["exe"])) if dados else None


def precisa_atualizar(instalada: str, recente: Versao) -> bool:
    return versao_tupla(recente.tag) > versao_tupla(instalada)


def _sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with open(caminho, "rb") as ficheiro:
        for bloco in iter(lambda: ficheiro.read(TAMANHO_BLOCO), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _baixar_ficheiro(url: str, destino: Path, progresso: Callable[[int, int], None] | None) -> None:
    pedido = urllib.request.Request(url, headers={"User-Agent": f"Kikoia/{VERSAO}"})
    with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as resposta, open(destino, "wb") as ficheiro:
        total = int(resposta.headers.get("Content-Length") or 0)
        recebido = 0
        while True:
            bloco = resposta.read(TAMANHO_BLOCO)
            if not bloco:
                break
            ficheiro.write(bloco)
            recebido += len(bloco)
            if progresso is not None:
                progresso(recebido, total)


def _extrair_seguro(zip_path: Path, destino: Path) -> None:
    base = destino.resolve()
    with zipfile.ZipFile(zip_path) as zip_:
        for membro in zip_.namelist():
            alvo = (destino / membro).resolve()
            if alvo != base and base not in alvo.parents:
                raise QuadroErro("quadro.ficheiro_invalido")  # caminho que sai da pasta
        zip_.extractall(destino)


def _guardar_atual(pasta: Path, tag: str, exe: Path) -> None:
    temporario = pasta / "atual.json.tmp"
    temporario.write_text(json.dumps({"versao": tag, "exe": str(exe)}, ensure_ascii=False), encoding="utf-8")
    os.replace(temporario, pasta / "atual.json")


def descarregar(
    versao: Versao,
    progresso: Callable[[int, int], None] | None = None,
    pasta: Path | None = None,
    baixar: Callable | None = None,
) -> Path:
    """Transfere, verifica e instala a versao. Devolve o executavel. Nada fica instalado se falhar."""
    pasta = pasta or pasta_quadro()
    baixar = baixar or _baixar_ficheiro
    if not _TAG.fullmatch(versao.tag):
        raise QuadroErro("quadro.ficheiro_invalido")
    pasta.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=pasta, prefix=".descarga-") as tmp_texto:
            tmp = Path(tmp_texto)
            zip_path = tmp / NOME_ARQUIVO
            baixar(versao.ficheiro_url, zip_path, progresso)
            if _sha256(zip_path) != versao.sha256:
                raise QuadroErro("quadro.verificacao_falhou")
            if not zipfile.is_zipfile(zip_path):
                raise QuadroErro("quadro.ficheiro_invalido")
            extraido = tmp / "extraido"
            extraido.mkdir()
            _extrair_seguro(zip_path, extraido)
            if not (extraido / EXECUTAVEL).is_file():
                raise QuadroErro("quadro.ficheiro_invalido")
            destino = pasta / "versoes" / versao.tag
            destino.parent.mkdir(parents=True, exist_ok=True)
            if destino.exists():
                shutil.rmtree(destino)
            shutil.move(str(extraido), str(destino))
    except OSError as erro:
        raise QuadroErro("quadro.sem_rede") from erro
    exe = destino / EXECUTAVEL
    if sys.platform != "win32":
        try:
            exe.chmod(0o755)
        except OSError:
            pass
    _guardar_atual(pasta, versao.tag, exe)
    return exe


def definir_instalacao(caminho: Path, pasta: Path | None = None) -> Path:
    """Indica onde o Quadro ja esta instalado (ex.: Arquivos de Programas ou pasta do projeto).
    Aceita a pasta ou o proprio executavel. A versao fica desconhecida (0.0.0), por isso a proxima
    verificacao oferece a atualizacao."""
    if caminho.is_dir():
        cand_exe = caminho / EXECUTAVEL
        cand_mod = caminho / "quadro" / "__main__.py"
        exe = cand_exe if cand_exe.is_file() else (cand_mod if cand_mod.is_file() else cand_exe)
    else:
        exe = caminho
    eh_modulo_quadro = exe.name == "__main__.py" and exe.parent.name == "quadro" and exe.is_file()
    if not eh_modulo_quadro and (exe.name.lower() != EXECUTAVEL.lower() or not exe.is_file()):
        raise QuadroErro("quadro.exe_invalido")
    pasta = pasta or pasta_quadro()
    pasta.mkdir(parents=True, exist_ok=True)
    _guardar_atual(pasta, "0.0.0", exe)
    return exe


def arrancar(exe: Path) -> None:
    """Abre o Quadro como programa independente (continua depois de o teclado fechar)."""
    if sys.platform == "win32":
        opcoes = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        opcoes = {"start_new_session": True}
    if exe.name == "__main__.py" and exe.parent.name == "quadro":
        subprocess.Popen([sys.executable, "-m", "quadro"], cwd=str(exe.parent.parent), **opcoes)
        return
    subprocess.Popen([str(exe)], cwd=str(exe.parent), **opcoes)
