import asyncio
import sys

import pytest

from teclado.gateway.bluetooth import SPP_UUID, canal_de_socket, disponivel
from teclado.gateway.canal import CanalFechado, canal_de_streams
from teclado.gateway.protocolo import ProtocoloErro


class _Socket:
    """Imita um StreamSocket: entrada e saida ligadas a mesma memoria."""

    def __init__(self, ms):
        self.input_stream = ms.get_input_stream_at(0)
        self.output_stream = ms.get_output_stream_at(0)
        self.fechado = False

    def close(self):
        self.fechado = True


def _par_de_canais():
    """Dois canais: o que envia escreve numa memoria que o outro le."""
    if sys.platform != "win32":
        pytest.skip("WinRT so existe no Windows")
    from winrt.windows.storage.streams import InMemoryRandomAccessStream
    ms = InMemoryRandomAccessStream()
    emissor = canal_de_socket(_Socket(ms), "par")
    recetor = canal_de_socket(_Socket(ms), "par")
    return emissor, recetor


def test_servico_usa_o_uuid_spp():
    assert str(SPP_UUID) == "00001101-0000-1000-8000-00805f9b34fb"


def test_disponibilidade_no_windows_e_none():
    if sys.platform == "win32":
        assert disponivel() is None


def test_mensagem_enquadrada_chega_inteira_no_windows():
    emissor, recetor = _par_de_canais()

    async def fluxo():
        await emissor.send(b"ola mundo")
        return await recetor.recv()

    assert asyncio.run(fluxo()) == b"ola mundo"


def test_duas_mensagens_seguidas_mantem_as_fronteiras():
    emissor, recetor = _par_de_canais()

    async def fluxo():
        await emissor.send(b"um")
        await emissor.send(b"dois-maior")
        return [await recetor.recv(), await recetor.recv()]

    assert asyncio.run(fluxo()) == [b"um", b"dois-maior"]


# --- camada enquadrada, testada sobre asyncio streams (qualquer SO) -----------

def test_canal_enquadrado_sobre_streams_ida_e_volta():
    async def fluxo():
        recebidas = []

        async def servidor(reader, writer):
            canal = canal_de_streams(reader, writer, "local")
            async for msg in canal:
                recebidas.append(msg)
                await canal.send(b"eco:" + msg)
            writer.close()

        srv = await asyncio.start_server(servidor, "127.0.0.1", 0)
        porta = srv.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", porta)
        canal = canal_de_streams(reader, writer, "cliente")
        await canal.send(b"a")
        resposta = await canal.recv()
        writer.close()
        srv.close()
        await srv.wait_closed()
        return recebidas, resposta

    recebidas, resposta = asyncio.run(fluxo())
    assert recebidas == [b"a"]
    assert resposta == b"eco:a"


def test_mensagem_acima_do_limite_recusada_ao_enviar():
    async def fluxo():
        class Falso:
            def write(self, d):
                pass

            async def drain(self):
                pass

            def close(self):
                pass

        canal = canal_de_streams(None, Falso(), "x")
        with pytest.raises(ProtocoloErro):
            await canal.send(b"x" * (16 * 1024 + 1))

    asyncio.run(fluxo())


def test_fluxo_fechado_levanta_canal_fechado():
    async def fluxo():
        async def servidor(reader, writer):
            writer.close()

        srv = await asyncio.start_server(servidor, "127.0.0.1", 0)
        porta = srv.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", porta)
        canal = canal_de_streams(reader, writer, "x")
        try:
            with pytest.raises(CanalFechado):
                await canal.recv()
        finally:
            writer.close()
            srv.close()
            await srv.wait_closed()

    asyncio.run(fluxo())
