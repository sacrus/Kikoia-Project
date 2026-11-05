import asyncio
import hashlib
import hmac as hm

from spake2 import SPAKE2_A

from teclado.gateway.canal import canal_de_streams
from teclado.gateway.protocolo import Sessao, codificar_emparelhamento, descodificar_emparelhamento
from teclado.gateway.servidor import NucleoGateway, chave_sessao


class NucleoTCP(NucleoGateway):
    """O mesmo nucleo que o Bluetooth usa, sobre TCP com enquadramento."""

    async def _principal(self):
        async def tratar(reader, writer):
            await self._tratar(canal_de_streams(reader, writer, "tcp"))

        srv = await asyncio.start_server(tratar, "127.0.0.1", 0)
        self.porta_real = srv.sockets[0].getsockname()[1]
        self._pronto.set()
        await self._parar.wait()
        srv.close()


def test_emparelhamento_e_acao_pelo_transporte_enquadrado():
    recebidas = []
    nucleo = NucleoTCP("Teste", ao_acao=recebidas.append)
    nucleo.iniciar()
    codigo = nucleo.novo_codigo().codigo

    async def cliente():
        reader, writer = await asyncio.open_connection("127.0.0.1", nucleo.porta_real)
        canal = canal_de_streams(reader, writer, "cli")
        spake = SPAKE2_A(codigo.encode("ascii"), idA=b"cliente", idB=b"pc")
        await canal.send(codificar_emparelhamento("desafio", spake.start().hex()))
        resposta = descodificar_emparelhamento(await canal.recv())
        chave = spake.finish(bytes.fromhex(resposta["valor"]))
        prova = hm.new(chave, b"cliente", hashlib.sha256).hexdigest()
        await canal.send(codificar_emparelhamento("confirmacao", prova))
        await canal.recv()  # confirmacao do PC
        sessao = Sessao(chave_sessao(chave))
        await canal.send(sessao.enviar("acao", "a1", {"acao": {"tipo": "texto", "valor": "ola"}}))
        await asyncio.sleep(0.3)
        writer.close()

    try:
        asyncio.run(cliente())
    finally:
        nucleo.parar()
    assert recebidas and recebidas[0]["acao"]["valor"] == "ola"
    assert nucleo.codigo.estado == "usado"
