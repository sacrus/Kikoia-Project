"""Vozes para Falar no Linux: Piper (sintese neural, offline).

Cada lingua tem a sua voz: portugues de Portugal (tugao), ingles (Amy), espanhol (Sharvard) e
frances (Siwis). Nenhuma vem com o teclado: so e descarregada quando o utilizador carrega em
«Descarregar a voz» em Opcoes de voz, e fica em vozes/<pasta da lingua> dentro dos dados.
Cada ficheiro e verificado com SHA-256 antes de ser instalado.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from teclado.core import modelos

# Duracao relativa das frases (1.0 = velocidade normal da voz; acima de 1.0 fala mais devagar).
FATOR_DURACAO = 1.6
# Variacao do ritmo e da aspereza da voz (o valor por omissao, 0.667, soa rouco nesta voz).
RUIDO_SINTESE = 0.4
# Silencio antes e depois de cada frase (segundos).
MARGEM_SILENCIO_S = 0.4

_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"


@dataclass(frozen=True)
class VozPiper:
    id: str
    nome: str
    pasta: str  # pasta local dentro de vozes/
    url_base: str
    modelo: str  # nome local do .onnx
    config: str  # nome local do .json
    ficheiros: dict[str, tuple[str, str]]  # nome local -> (nome no servidor, SHA-256 esperado)
    tamanho_mb: int


VOZES: dict[str, VozPiper] = {
    "pt-PT": VozPiper(
        id="pt_PT-tugao-medium",
        nome="Português (Portugal), tugão (Piper)",
        pasta="piper-pt_PT",
        url_base=_BASE + "pt/pt_PT/tug%C3%A3o/medium/",
        modelo="pt_PT-tugao-medium.onnx",
        config="pt_PT-tugao-medium.onnx.json",
        ficheiros={
            "pt_PT-tugao-medium.onnx": (
                "pt_PT-tug%C3%A3o-medium.onnx",
                "223a7aaca69a155c61897e8ada7c3b13bc306e16c72dbb9c2fed733e2b0927d4",
            ),
            "pt_PT-tugao-medium.onnx.json": (
                "pt_PT-tug%C3%A3o-medium.onnx.json",
                "fe0918dfc0f1a89264a6eea4afe8e95d8e9fed3cc6c81b5c2f87fcb2b50c7320",
            ),
        },
        tamanho_mb=63,
    ),
    "en": VozPiper(
        id="en_US-amy-medium",
        nome="English (US), Amy (Piper)",
        pasta="piper-en",
        url_base=_BASE + "en/en_US/amy/medium/",
        modelo="en_US-amy-medium.onnx",
        config="en_US-amy-medium.onnx.json",
        ficheiros={
            "en_US-amy-medium.onnx": (
                "en_US-amy-medium.onnx",
                "b3a6e47b57b8c7fbe6a0ce2518161a50f59a9cdd8a50835c02cb02bdd6206c18",
            ),
            "en_US-amy-medium.onnx.json": (
                "en_US-amy-medium.onnx.json",
                "95a23eb4d42909d38df73bb9ac7f45f597dbfcde2d1bf9526fdeaf5466977d77",
            ),
        },
        tamanho_mb=63,
    ),
    "es": VozPiper(
        id="es_ES-sharvard-medium",
        nome="Español (España), Sharvard (Piper)",
        pasta="piper-es",
        url_base=_BASE + "es/es_ES/sharvard/medium/",
        modelo="es_ES-sharvard-medium.onnx",
        config="es_ES-sharvard-medium.onnx.json",
        ficheiros={
            "es_ES-sharvard-medium.onnx": (
                "es_ES-sharvard-medium.onnx",
                "40febfb1679c69a4505ff311dc136e121e3419a13a290ef264fdf43ddedd0fb1",
            ),
            "es_ES-sharvard-medium.onnx.json": (
                "es_ES-sharvard-medium.onnx.json",
                "7438c9b699c72b0c3388dae1b68d3f364dc66a2150fe554a1c11f03372957b2c",
            ),
        },
        tamanho_mb=77,
    ),
    "fr": VozPiper(
        id="fr_FR-siwis-medium",
        nome="Français (France), Siwis (Piper)",
        pasta="piper-fr",
        url_base=_BASE + "fr/fr_FR/siwis/medium/",
        modelo="fr_FR-siwis-medium.onnx",
        config="fr_FR-siwis-medium.onnx.json",
        ficheiros={
            "fr_FR-siwis-medium.onnx": (
                "fr_FR-siwis-medium.onnx",
                "641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99",
            ),
            "fr_FR-siwis-medium.onnx.json": (
                "fr_FR-siwis-medium.onnx.json",
                "39479916c2db192b5ac9764daddd0c744d83e023ad890c6976c0633ae4df8959",
            ),
        },
        tamanho_mb=63,
    ),
}

# Nomes do portugues (mantidos para o codigo e os testes existentes).
_PT = VOZES["pt-PT"]
ID_VOZ = _PT.id
NOME_VOZ = _PT.nome
TAMANHO_MB = _PT.tamanho_mb
URL_BASE = _PT.url_base
MODELO = _PT.modelo
CONFIG = _PT.config
FICHEIROS: dict[str, tuple[str, str]] = _PT.ficheiros


def voz_do_idioma(idioma: str) -> VozPiper | None:
    return VOZES.get(idioma)


def _ficheiros(idioma: str) -> dict[str, tuple[str, str]]:
    return FICHEIROS if idioma == "pt-PT" else VOZES[idioma].ficheiros


def _url_base(idioma: str) -> str:
    return URL_BASE if idioma == "pt-PT" else VOZES[idioma].url_base


def pasta_voz(pasta_dados: Path, idioma: str = "pt-PT") -> Path:
    return Path(pasta_dados) / "vozes" / VOZES[idioma].pasta


def instalada(pasta_dados: Path, idioma: str = "pt-PT") -> bool:
    if idioma not in VOZES:
        return False
    pasta = pasta_voz(pasta_dados, idioma)
    return all((pasta / ficheiro).is_file() for ficheiro in _ficheiros(idioma))


def remover(pasta_dados: Path, idioma: str = "pt-PT") -> None:
    pasta = pasta_voz(pasta_dados, idioma)
    if pasta.exists():
        shutil.rmtree(pasta)


def _sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with open(caminho, "rb") as ficheiro:
        for bloco in iter(lambda: ficheiro.read(64 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def descarregar(
    pasta_dados: Path,
    idioma: str = "pt-PT",
    progresso: Callable[[int, int], None] | None = None,
    cancelar: Callable[[], bool] | None = None,
) -> Path:
    """Transfere e verifica os ficheiros da voz da lingua. Nada fica instalado se alguma etapa falhar."""
    if idioma not in VOZES:
        raise modelos.ModeloErro("Ainda nao ha voz de Falar para este idioma.")
    destino = pasta_voz(pasta_dados, idioma)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent, prefix=".descarga-") as tmp_texto:
        tmp = Path(tmp_texto)
        for local, (servidor, sha_esperado) in _ficheiros(idioma).items():
            modelos._transferir(_url_base(idioma) + servidor, tmp / local, progresso, cancelar)
            if _sha256(tmp / local) != sha_esperado:
                raise modelos.ModeloErro("A verificação da voz falhou (ficheiro corrompido ou alterado).")
        if destino.exists():
            shutil.rmtree(destino)
        destino.mkdir(parents=True)
        for local in _ficheiros(idioma):
            shutil.move(str(tmp / local), str(destino / local))
    return destino


class MotorPiper:
    """Mesma interface do motor SAPI (setProperty / say / runAndWait), usada pela SinteseFalada.

    runAndWait() sintetiza a frase e espera que o audio acabe, por isso a fila da
    SinteseFalada espera pela frase seguinte.
    """

    def __init__(self, modelo: Path, config: Path) -> None:
        from piper import PiperVoice  # importado so quando a voz existe

        self._voz = PiperVoice.load(str(modelo), str(config))
        self._pendente: str | None = None

    def setProperty(self, nome: str, valor: str) -> None:
        pass  # uma voz por motor

    def say(self, texto: str) -> None:
        self._pendente = texto

    def runAndWait(self) -> None:
        if self._pendente is None:
            return
        texto, self._pendente = self._pendente, None
        import numpy as np
        import sounddevice as sd

        from piper import SynthesisConfig

        blocos: list[np.ndarray] = []
        taxa = 22050
        configuracao = SynthesisConfig(length_scale=FATOR_DURACAO, noise_scale=RUIDO_SINTESE)
        for bloco in self._voz.synthesize(texto, syn_config=configuracao):
            taxa = bloco.sample_rate
            blocos.append(bloco.audio_float_array)
        if blocos:
            # Silencio antes e depois: sem ele, o inicio e o fim das palavras curtas perdem-se na placa de som.
            silencio = np.zeros(int(taxa * MARGEM_SILENCIO_S), dtype=np.float32)
            sd.play(np.concatenate([silencio, *blocos, silencio]), taxa)
            sd.wait()
