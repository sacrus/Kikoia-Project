"""Voz: sintese (texto para fala) e reconhecimento (fala para texto), ambos opcionais.

- Sintese: SAPI5 do Windows, chamado diretamente (comtypes). Corre numa thread
  propria, com fila, para nunca bloquear as teclas.
  Nota: o pyttsx3 deixava de falar depois da primeira frase no SAPI5; por isso
  nao e usado.
- Reconhecimento: Vosk, offline, com um modelo guardado numa pasta local.
  Sem modelo ou sem dependencias, o botao fica desativado com o motivo.

Nada disto e obrigatorio: se o motor nao existir, o teclado funciona igual.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from teclado.core import modelos
from teclado.core.idiomas import t
from teclado.core.nivel import AnaliseNivel

log = logging.getLogger(__name__)


class VozIndisponivel(RuntimeError):
    """O motor de voz pedido nao esta instalado ou nao tem vozes."""


class Sintese(Protocol):
    def falar(self, texto: str) -> None: ...
    def parar(self) -> None: ...
    def fechar(self) -> None: ...


def _inicializar_com() -> None:
    """COM tem de ser inicializado em cada thread que use o SAPI5 (Windows)."""
    if sys.platform != "win32":
        return
    import comtypes  # type: ignore

    comtypes.CoInitialize()


class MotorSapi:
    """Interface minima de um motor: setProperty / say / runAndWait.

    runAndWait() bloqueia ate a frase terminar (SPVoice.Speak e sincrono),
    por isso a thread de SinteseFalada espera pela frase seguinte.
    """

    def __init__(self) -> None:
        import comtypes.client  # type: ignore

        self._sp = comtypes.client.CreateObject("SAPI.SPVoice")
        self._pendente: str | None = None

    def setProperty(self, nome: str, valor: str) -> None:
        if nome != "voice":
            return
        for token in self._sp.GetVoices():
            if token.Id == valor:
                self._sp.Voice = token
                return

    def say(self, texto: str) -> None:
        self._pendente = texto

    def runAndWait(self) -> None:
        if self._pendente is not None:
            self._sp.Speak(self._pendente)
            self._pendente = None


class SinteseFalada:
    """Fala numa thread de fundo. Os pedidos entram numa fila e saem por ordem.

    O motor e criado dentro da thread (o COM e por thread).
    aguardar_pronto() diz se o motor arrancou; um erro fica em `erro`.
    """

    def __init__(self, motor: Callable[[], object], voz_id: str | None = None) -> None:
        self._motor_fabrica = motor
        self._voz_id = voz_id
        self._fila: queue.Queue[str | None] = queue.Queue(maxsize=50)
        self._pronto = threading.Event()
        self.erro: Exception | None = None
        self._thread = threading.Thread(target=self._correr, daemon=True, name="sintese")
        self._thread.start()

    def aguardar_pronto(self, limite: float = 5.0) -> bool:
        """True se o motor arrancou. False se falhou (ver self.erro) ou se demorou demasiado."""
        self._pronto.wait(limite)
        return self._pronto.is_set() and self.erro is None

    def falar(self, texto: str) -> None:
        texto = (texto or "").strip()
        if not texto:
            return
        try:
            self._fila.put_nowait(texto)
        except queue.Full:
            pass  # demasiados pedidos: descarta em vez de atrasar o teclado

    def parar(self) -> None:
        while True:
            try:
                self._fila.get_nowait()
            except queue.Empty:
                break

    def fechar(self) -> None:
        self.parar()
        self._fila.put(None)

    def _correr(self) -> None:
        try:
            _inicializar_com()
            motor = self._motor_fabrica()
            if self._voz_id:
                motor.setProperty("voice", self._voz_id)
        except Exception as erro:
            self.erro = erro
            log.error("Motor de voz nao arrancou: %s", erro, exc_info=True)
            self._pronto.set()
            return
        self._pronto.set()
        while True:
            texto = self._fila.get()
            if texto is None:
                break
            try:
                motor.say(texto)
                motor.runAndWait()
            except Exception:  # um erro do motor nao pode matar a thread nem o teclado
                log.error("Falha ao falar: %r", texto, exc_info=True)


def vozes_disponiveis() -> list[tuple[str, str]]:
    """Lista (id, nome) das vozes SAPI instaladas. Vazia se nao houver motor."""
    if sys.platform != "win32":
        return []
    try:
        _inicializar_com()
        import comtypes.client  # type: ignore

        sp = comtypes.client.CreateObject("SAPI.SPVoice")
        return [(t.Id, t.GetDescription()) for t in sp.GetVoices()]
    except Exception:
        log.warning("Nao foi possivel listar as vozes SAPI", exc_info=True)
        return []


def escolher_voz_portuguesa(vozes: list[tuple[str, str]]) -> str | None:
    """Prefere pt-PT, depois qualquer portugues, e nunca devolve uma voz que nao seja portuguesa."""
    for id_, nome in vozes:
        if "PT-PT" in id_.upper() or "PORTUGAL" in nome.upper():
            return id_
    for id_, nome in vozes:
        if "PT-" in id_.upper() or "PORTUGUESE" in nome.upper() or "PORTUGUÊS" in nome.upper():
            return id_
    return None


def criar_sintese(voz_id: str | None = None) -> Sintese:
    """Cria o motor de fala do sistema. Lanca VozIndisponivel se nao existir."""
    if sys.platform != "win32":
        raise VozIndisponivel("Síntese de voz ainda não disponível neste sistema.")
    sintese = SinteseFalada(MotorSapi, voz_id=voz_id)
    if not sintese.aguardar_pronto():
        motivo = f" ({sintese.erro})" if sintese.erro else ""
        raise VozIndisponivel(f"Não foi possível iniciar o motor de voz do Windows{motivo}.")
    return sintese


# --- reconhecimento (Vosk, offline) -----------------------------------------

def modelo_vosk_presente(pasta_dados: Path, idioma: str = "pt-PT") -> Path | None:
    """Pasta do modelo Vosk do idioma, se estiver instalado (descarregado a pedido)."""
    return modelos.instalado(pasta_dados, idioma)


def verificar_reconhecimento(pasta_dados: Path, idioma: str = "pt-PT") -> str | None:
    """None se o reconhecimento de voz esta pronto a usar; senao, o motivo."""
    try:
        import vosk  # noqa: F401  type: ignore
        import sounddevice  # noqa: F401  type: ignore
    except ImportError:
        return "Instale vosk e sounddevice para ditar por voz."
    if modelos.modelo_do_idioma(idioma) is None:
        return t("voz.sem_modelo_idioma")
    if modelo_vosk_presente(pasta_dados, idioma) is None:
        return t("voz.modelo_em_falta")
    return None


# Ganho automatico do microfone. Microfones baixos (pico de ~400 em 32767) fazem o
# reconhecedor falhar palavras; medido: a 2 % do volume original o modelo perde o texto,
# e com ganho normalizado a frase volta a sair certa.
GANHO_ALVO = 20000      # pico desejado (em 32767)
GANHO_MAXIMO = 40.0     # limite: nao amplifica so ruido de fundo
PICO_MINIMO = 300       # abaixo disto e silencio/ruido, nao fala
DECAIMENTO_PICO = 0.99  # o pico de referencia desce devagar entre blocos (blocos de 0,1 s)


def normalizar_ganho(bloco: bytes, estado: dict) -> bytes:
    """Aplica ganho a um bloco de audio int16 mono. 'estado' guarda o pico entre blocos."""
    import array

    amostras = array.array("h")
    amostras.frombytes(bloco)
    if not amostras:
        return bloco
    pico_bloco = max(abs(v) for v in amostras)
    estado["pico"] = max(pico_bloco, estado.get("pico", 0.0) * DECAIMENTO_PICO)
    referencia = max(estado["pico"], PICO_MINIMO)
    ganho = min(GANHO_MAXIMO, GANHO_ALVO / referencia)
    if ganho <= 1.0:
        return bloco
    for i, v in enumerate(amostras):
        amostras[i] = max(-32768, min(32767, int(v * ganho)))
    return amostras.tobytes()


class Ditado:
    """Recebe texto reconhecido (frases finais) e entrega-o ao editor."""

    def __init__(
        self,
        pasta_dados: Path,
        ao_texto: Callable[[str], None],
        ao_nivel: Callable[[object], None] | None = None,
        idioma: str = "pt-PT",
    ) -> None:
        motivo = verificar_reconhecimento(pasta_dados, idioma)
        if motivo is not None:
            raise VozIndisponivel(motivo)
        import json

        import sounddevice  # type: ignore
        import vosk  # type: ignore

        vosk.SetLogLevel(-1)
        modelo = vosk.Model(str(modelo_vosk_presente(pasta_dados, idioma)))
        self._reconhecedor = vosk.KaldiRecognizer(modelo, 16000)
        self._json = json
        self._ao_texto = ao_texto
        self._stream = sounddevice.RawInputStream(
            samplerate=16000, blocksize=1600, dtype="int16", channels=1,
            callback=self._recebe,
        )
        self._ativo = False
        self._ganho: dict = {}
        self._analise = AnaliseNivel()
        self._ao_nivel = ao_nivel

    def _recebe(self, dados, frames, tempo, estado) -> None:  # callback de audio
        if not self._ativo:
            return
        bruto = bytes(dados)
        if self._ao_nivel is not None:
            # Analisa o sinal do microfone antes do ganho: e isso que o utilizador deve ajustar.
            self._ao_nivel(self._analise.atualizar(bruto))
        bloco = normalizar_ganho(bruto, self._ganho)
        if self._reconhecedor.AcceptWaveform(bloco):
            texto = self._json.loads(self._reconhecedor.Result()).get("text", "").strip()
            if texto:
                self._ao_texto(texto)

    @property
    def ativo(self) -> bool:
        return self._ativo

    def ligar(self) -> None:
        if not self._ativo:
            self._analise = AnaliseNivel()  # comeca a medir do zero
            self._stream.start()
            self._ativo = True

    def desligar(self) -> None:
        if self._ativo:
            self._ativo = False
            self._stream.stop()
