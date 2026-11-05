"""Ciclo de vida do gateway dentro da aplicacao: ligar, desligar, codigo, estado e difusao.

Transportes: "wifi" (WebSocket + UDP, porta configuravel) e "bluetooth" (RFCOMM, Windows).
O servidor cria-se de cada vez que se liga. Os callbacks chegam da thread do gateway:
quem os usa deve reencaminhar para a thread do Qt.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from teclado.gateway.bluetooth import ServidorBluetooth, disponivel as bluetooth_disponivel
from teclado.gateway.confianca import RepositorioConfianca
from teclado.gateway.servidor import PORTA_POR_OMISSAO, NucleoGateway, ServidorGateway

TRANSPORTE_WIFI = "wifi"
TRANSPORTE_BLUETOOTH = "bluetooth"
TRANSPORTES = (TRANSPORTE_WIFI, TRANSPORTE_BLUETOOTH)


class ControladorGateway:
    def __init__(
        self,
        nome: str,
        ao_acao: Callable[[dict[str, Any]], None],
        ao_ligar: Callable[[str], None],
        ao_desligar: Callable[[str], None],
        fornecer_teclado: Callable[[], dict[str, Any] | None],
        fornecer_sugestoes: Callable[[], list[str]] | None = None,
        confianca: RepositorioConfianca | None = None,
        ao_emparelhar_novo: Callable[[str], None] | None = None,
    ) -> None:
        self._nome = nome
        self._ao_acao = ao_acao
        self._ao_ligar = ao_ligar
        self._ao_desligar = ao_desligar
        self._fornecer_teclado = fornecer_teclado
        self._fornecer_sugestoes = fornecer_sugestoes
        self._confianca = confianca
        self._ao_emparelhar_novo = ao_emparelhar_novo
        self._servidor: NucleoGateway | None = None
        self._transporte: str | None = None
        self._porta: int | None = None

    @property
    def ativo(self) -> bool:
        return self._servidor is not None and self._servidor.ativo

    @staticmethod
    def bluetooth_disponivel() -> str | None:
        return bluetooth_disponivel()

    def ligar(self, porta: int = PORTA_POR_OMISSAO, transporte: str = TRANSPORTE_WIFI) -> None:
        """Liga o transporte e gera um codigo. Lanca RuntimeError se nao for possivel."""
        if transporte not in TRANSPORTES:
            raise ValueError("transporte desconhecido")
        if self.ativo:
            return
        kwargs = dict(
            ao_acao=self._ao_acao,
            ao_emparelhar=self._ao_ligar,
            ao_desligar=self._ao_desligar,
            fornecer_teclado=self._fornecer_teclado,
            fornecer_sugestoes=self._fornecer_sugestoes,
            confianca=self._confianca,
            ao_emparelhar_novo=self._ao_emparelhar_novo,
        )
        if transporte == TRANSPORTE_BLUETOOTH:
            motivo = bluetooth_disponivel()
            if motivo:
                raise RuntimeError(motivo)
            servidor = ServidorBluetooth(self._nome, **kwargs)
            porta_usada = None
        else:
            servidor = ServidorGateway(self._nome, porta=porta, **kwargs)
            porta_usada = porta
        servidor.iniciar()
        servidor.novo_codigo()
        self._servidor = servidor
        self._transporte = transporte
        self._porta = porta_usada

    def desligar(self) -> None:
        if self._servidor is not None:
            self._servidor.parar()
            self._servidor = None

    def novo_codigo(self) -> str:
        if not self.ativo:
            raise RuntimeError("O telemóvel não está ligado ao gateway.")
        return self._servidor.novo_codigo().codigo

    def atualizar_teclado(self, modelo: dict[str, Any]) -> None:
        if self.ativo:
            self._servidor.atualizar_teclado(modelo)

    def atualizar_sugestoes(self, palavras: list[str]) -> None:
        if self.ativo:
            self._servidor.atualizar_sugestoes(palavras)

    def estado(self) -> dict[str, Any]:
        if not self.ativo:
            return {"ativo": False}
        codigo = self._servidor.codigo
        return {
            "ativo": True,
            "transporte": self._transporte,
            "porta": self._porta,
            "codigo": codigo.codigo,
            "estado_codigo": codigo.estado,
            "segundos": int(codigo.segundos_restantes()),
            "ligados": self._servidor.dispositivos_ligados,
        }
