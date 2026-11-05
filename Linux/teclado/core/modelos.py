"""Modelos de voz (Vosk) descarregados so a pedido do utilizador.

Nada disto vem com o teclado. Um modelo so e transferido quando o utilizador carrega em
«Descarregar modelo» em Opcoes de voz (para ditar). Fica em modelos/<pasta> dentro dos dados
do utilizador, e pode ser removido a qualquer momento.
"""

from __future__ import annotations

import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

URL_BASE = "https://alphacephei.com/vosk/models"
TAMANHO_BLOCO = 64 * 1024
TIMEOUT_S = 30


class ModeloErro(RuntimeError):
    """Nao foi possivel descarregar ou instalar o modelo. A mensagem e para o utilizador."""


class DescargaCancelada(ModeloErro):
    pass


@dataclass(frozen=True)
class ModeloVoz:
    idioma: str
    nome: str  # nome do ficheiro no site (sem .zip)
    pasta: str  # pasta local dentro de modelos/
    tamanho_mb: int  # tamanho aproximado do ficheiro transferido


# Modelos pequenos (Apache 2.0), os que correm bem num PC normal. Os grandes nao sao oferecidos.
MODELOS_VOZ: dict[str, ModeloVoz] = {
    "pt-PT": ModeloVoz("pt-PT", "vosk-model-small-pt-0.3", "vosk-pt", 32),
    "en": ModeloVoz("en", "vosk-model-small-en-us-0.15", "vosk-en", 41),
    "es": ModeloVoz("es", "vosk-model-small-es-0.42", "vosk-es", 40),
    "fr": ModeloVoz("fr", "vosk-model-small-fr-0.22", "vosk-fr", 42),
}


def modelo_do_idioma(idioma: str) -> ModeloVoz | None:
    return MODELOS_VOZ.get(idioma)


def pasta_do_modelo(pasta_dados: Path, idioma: str) -> Path | None:
    modelo = modelo_do_idioma(idioma)
    if modelo is None:
        return None
    return Path(pasta_dados) / "modelos" / modelo.pasta


def instalado(pasta_dados: Path, idioma: str) -> Path | None:
    """Pasta do modelo se estiver instalado (com ficheiros dentro); senao None."""
    pasta = pasta_do_modelo(pasta_dados, idioma)
    if pasta is None or not pasta.is_dir() or not any(pasta.iterdir()):
        return None
    return pasta


def url_do_modelo(modelo: ModeloVoz) -> str:
    return f"{URL_BASE}/{modelo.nome}.zip"


def descarregar(
    pasta_dados: Path,
    idioma: str,
    progresso: Callable[[int, int], None] | None = None,
    cancelar: Callable[[], bool] | None = None,
) -> Path:
    """Transfere, verifica e instala o modelo do idioma. Devolve a pasta instalada.

    progresso(recebido, total) e chamado a cada bloco (total 0 se o servidor nao disser).
    Se a transferencia falhar ou for cancelada, nada fica instalado a meio.
    """
    modelo = modelo_do_idioma(idioma)
    if modelo is None:
        raise ModeloErro("Ainda nao ha modelo de voz para este idioma.")
    destino = pasta_do_modelo(pasta_dados, idioma)
    assert destino is not None
    pasta_modelos = Path(pasta_dados) / "modelos"
    pasta_modelos.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=pasta_modelos, prefix=".descarga-") as tmp_texto:
        tmp = Path(tmp_texto)
        zip_transferido = tmp / "modelo.zip"
        _transferir(url_do_modelo(modelo), zip_transferido, progresso, cancelar)
        if not zipfile.is_zipfile(zip_transferido):
            raise ModeloErro("O ficheiro transferido nao e um modelo valido.")
        extraido = tmp / "extraido"
        with zipfile.ZipFile(zip_transferido) as zip_:
            zip_.extractall(extraido)
        pastas = [p for p in extraido.iterdir() if p.is_dir()]
        origem = pastas[0] if len(pastas) == 1 else extraido
        if not (origem / "am").is_dir():
            raise ModeloErro("O modelo transferido nao tem a estrutura esperada.")
        if destino.exists():
            shutil.rmtree(destino)
        shutil.move(str(origem), str(destino))
    return destino


def remover(pasta_dados: Path, idioma: str) -> None:
    pasta = pasta_do_modelo(pasta_dados, idioma)
    if pasta is not None and pasta.exists():
        shutil.rmtree(pasta)


def _transferir(
    url: str,
    destino: Path,
    progresso: Callable[[int, int], None] | None,
    cancelar: Callable[[], bool] | None,
) -> None:
    pedido = urllib.request.Request(url, headers={"User-Agent": "TecladoRemoto"})
    try:
        resposta = urllib.request.urlopen(pedido, timeout=TIMEOUT_S)
    except OSError as erro:
        raise ModeloErro(f"Sem ligacao para descarregar o modelo ({erro}).") from erro
    with resposta, open(destino, "wb") as ficheiro:
        total = int(resposta.headers.get("Content-Length") or 0)
        recebido = 0
        while True:
            if cancelar is not None and cancelar():
                raise DescargaCancelada("Descarga cancelada.")
            bloco = resposta.read(TAMANHO_BLOCO)
            if not bloco:
                break
            ficheiro.write(bloco)
            recebido += len(bloco)
            if progresso is not None:
                progresso(recebido, total)
    if total and recebido != total:
        raise ModeloErro("A transferencia ficou incompleta. Tente de novo.")

