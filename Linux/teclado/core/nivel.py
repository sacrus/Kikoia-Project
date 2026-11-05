"""Nivel do microfone em decibeis (dBFS), para orientar o utilizador durante o ditado.

A analise usa o sinal ANTES do ganho automatico: o objetivo e dizer ao utilizador
o que realmente chega do microfone (ex.: "Fale mais alto").
"""

from __future__ import annotations

import array
import math
from dataclasses import dataclass

TAXA = 16000
SILENCIO_DB = -120.0
ESCALA = 32768

LIMIAR_FRACO_DB = -40.0       # fala presente, mas fraca (RMS)
RUIDO_MINIMO_FRACO_DB = -55.0 # abaixo disto e silencio, nao fala fraca
LIMIAR_SILENCIO_DB = -60.0    # praticamente nada
LIMIAR_SATURACAO_DB = -1.0    # pico a encostar ao maximo

SEGUNDOS_FRACO = 1.5
SEGUNDOS_SATURACAO = 0.4
SEGUNDOS_SILENCIO = 6.0

MSG_FRACO = "Fale mais alto ou aproxime-se do microfone."
MSG_SATURACAO = "Fale mais baixo ou afaste-se do microfone."
MSG_SILENCIO = "Não se ouve nada. Verifique o microfone."


@dataclass(frozen=True)
class Medicao:
    rms_db: float
    pico_db: float
    mensagem: str | None


def _db(valor: float) -> float:
    return 20.0 * math.log10(valor / ESCALA) if valor > 0 else SILENCIO_DB


def medir(bloco: bytes) -> tuple[float, float, float]:
    """(rms_db, pico_db, duracao_s) de um bloco int16 mono."""
    amostras = array.array("h")
    amostras.frombytes(bloco)
    n = len(amostras)
    if n == 0:
        return SILENCIO_DB, SILENCIO_DB, 0.0
    rms = math.sqrt(sum(v * v for v in amostras) / n)
    pico = max(abs(v) for v in amostras)
    return _db(rms), _db(pico), n / TAXA


def _acumular(tempo: float, duracao: float, condicao: bool) -> float:
    """Soma o tempo com a condicao; sem ela, desconta metade (uma pausa curta nao reinicia)."""
    if condicao:
        return tempo + duracao
    return max(0.0, tempo - duracao * 0.5)


class AnaliseNivel:
    """Acompanha os blocos de audio e devolve uma mensagem quando o nivel nao e adequado.

    As mensagens so aparecem depois de a condicao se manter durante alguns segundos,
    para nao piscarem a cada pausa entre palavras.
    """

    def __init__(self) -> None:
        self._t_fraco = 0.0
        self._t_saturacao = 0.0
        self._t_silencio = 0.0

    def atualizar(self, bloco: bytes) -> Medicao:
        rms, pico, duracao = medir(bloco)
        self._t_silencio = self._t_silencio + duracao if rms < LIMIAR_SILENCIO_DB else 0.0
        # Uma pausa entre palavras nao apaga o tempo acumulado: so o desconta.
        # Assim uma fala fraca com pausas continua a ser detetada.
        self._t_fraco = _acumular(
            self._t_fraco, duracao, RUIDO_MINIMO_FRACO_DB <= rms < LIMIAR_FRACO_DB
        )
        self._t_saturacao = _acumular(self._t_saturacao, duracao, pico >= LIMIAR_SATURACAO_DB)

        mensagem = None
        if self._t_saturacao >= SEGUNDOS_SATURACAO:
            mensagem = MSG_SATURACAO
        elif self._t_fraco >= SEGUNDOS_FRACO:
            mensagem = MSG_FRACO
        elif self._t_silencio >= SEGUNDOS_SILENCIO:
            mensagem = MSG_SILENCIO
        return Medicao(rms, pico, mensagem)
