"""Canal de mensagens sobre um fluxo de bytes (usado pelo Bluetooth RFCOMM).

RFCOMM e um fluxo sem fronteiras de mensagem. Cada mensagem e enviada com um
prefixo de 4 bytes (tamanho, big-endian). O Wi-Fi usa WebSocket, que ja tem
fronteiras; ambos expõem a mesma interface (send, recv, close, remote_address)
para que o emparelhamento e o protocolo sejam os mesmos.
"""

from __future__ import annotations

import asyncio
import struct
from collections.abc import Awaitable, Callable

from teclado.gateway.protocolo import TAMANHO_MAXIMO, ProtocoloErro

CABECALHO = struct.Struct(">I")


class CanalFechado(ConnectionError):
    """O outro lado fechou o fluxo (ou houve erro de transporte)."""


class CanalEnquadrado:
    def __init__(
        self,
        ler_exato: Callable[[int], Awaitable[bytes]],
        escrever: Callable[[bytes], Awaitable[None]],
        fechar: Callable[[], Awaitable[None]],
        endereco: str,
    ) -> None:
        self._ler_exato = ler_exato
        self._escrever = escrever
        self._fechar = fechar
        self._endereco = endereco

    @property
    def remote_address(self) -> str:
        return self._endereco

    async def send(self, dados: bytes) -> None:
        if len(dados) > TAMANHO_MAXIMO:
            raise ProtocoloErro("mensagem demasiado grande")
        await self._escrever(CABECALHO.pack(len(dados)) + dados)

    async def recv(self) -> bytes:
        cabecalho = await self._ler_exato(CABECALHO.size)
        (tamanho,) = CABECALHO.unpack(cabecalho)
        if tamanho > TAMANHO_MAXIMO:
            raise ProtocoloErro("mensagem demasiado grande")
        return await self._ler_exato(tamanho) if tamanho else b""

    async def close(self, code: int = 1000, reason: str = "") -> None:
        await self._fechar()

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return await self.recv()
        except (CanalFechado, ProtocoloErro):
            raise StopAsyncIteration


def canal_de_streams(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, endereco: str) -> CanalEnquadrado:
    """Canal sobre asyncio streams (TCP ou outro fluxo)."""

    async def ler(n: int) -> bytes:
        try:
            return await reader.readexactly(n)
        except (asyncio.IncompleteReadError, OSError) as erro:
            raise CanalFechado("fluxo fechado") from erro

    async def escrever(dados: bytes) -> None:
        try:
            writer.write(dados)
            await writer.drain()
        except OSError as erro:
            raise CanalFechado("fluxo fechado") from erro

    async def fechar() -> None:
        writer.close()

    return CanalEnquadrado(ler, escrever, fechar, endereco)
