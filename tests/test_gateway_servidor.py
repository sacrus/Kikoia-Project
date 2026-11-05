import asyncio
import json
import socket
import time
import hashlib
import hmac

import pytest
from spake2 import SPAKE2_A
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from teclado.gateway.protocolo import (
    Sessao,
    codificar_emparelhamento,
    descodificar_emparelhamento,
)
from teclado.gateway.servidor import PEDIDO_DESCOBERTA, ServidorGateway, chave_sessao


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Cliente:
    """Cliente de teste: faz o emparelhamento SPAKE2 e depois envia mensagens autenticadas."""

    def __init__(self, ws, chave_spake):
        self.ws = ws
        self.sessao = Sessao(chave_sessao(chave_spake))
        self.chave = chave_spake


async def emparelhar(porta, codigo_tentado):
    ws = await connect(f"ws://127.0.0.1:{porta}", max_size=16 * 1024)
    spake = SPAKE2_A(codigo_tentado.encode("ascii"), idA=b"cliente", idB=b"pc")
    await ws.send(codificar_emparelhamento("desafio", spake.start().hex()))
    resposta = descodificar_emparelhamento(await ws.recv())
    chave = spake.finish(bytes.fromhex(resposta["valor"]))
    prova = hmac.new(chave, b"cliente", hashlib.sha256).hexdigest()
    await ws.send(codificar_emparelhamento("confirmacao", prova))
    return ws, chave


@pytest.fixture
def servidor():
    recebidas = []
    porta = _porta_livre()
    srv = ServidorGateway("Teste", ao_acao=recebidas.append, porta=porta)
    srv.iniciar()
    srv.recebidas = recebidas
    yield srv
    srv.parar()


def _correr(coro):
    return asyncio.run(coro)


async def codigo_de_fecho(porta, codigo_tentado):
    """Tenta emparelhar e devolve o codigo de fecho do servidor (o fecho pode dar-se em qualquer passo)."""
    try:
        ws, _ = await emparelhar(porta, codigo_tentado)
        await ws.recv()
        return None  # emparelhou
    except ConnectionClosed as erro:
        return erro.rcvd.code if erro.rcvd else erro.sent.code


def test_emparelhamento_com_codigo_certo(servidor):
    codigo = servidor.novo_codigo()

    async def fluxo():
        ws, chave = await emparelhar(servidor.porta, codigo.codigo)
        confirmacao = descodificar_emparelhamento(await ws.recv())
        esperado = hmac.new(chave, b"servidor", hashlib.sha256).hexdigest()
        await ws.close()
        return confirmacao["valor"] == esperado

    assert _correr(fluxo()) is True
    assert codigo.estado == "usado"


def test_acao_depois_de_emparelhar_chega_ao_pc(servidor):
    codigo = servidor.novo_codigo()

    async def fluxo():
        ws, chave = await emparelhar(servidor.porta, codigo.codigo)
        await ws.recv()  # confirmacao do PC
        sessao = Sessao(chave_sessao(chave))
        await ws.send(sessao.enviar("acao", "a1", {"acao": {"tipo": "texto", "valor": "olá"}}))
        await asyncio.sleep(0.2)
        await ws.close()

    _correr(fluxo())
    assert len(servidor.recebidas) == 1
    assert servidor.recebidas[0]["acao"]["valor"] == "olá"


def test_ping_recebe_pong_autenticado(servidor):
    codigo = servidor.novo_codigo()

    async def fluxo():
        ws, chave = await emparelhar(servidor.porta, codigo.codigo)
        await ws.recv()
        sessao = Sessao(chave_sessao(chave))
        await ws.send(sessao.enviar("ping", "p1"))
        pong = sessao.receber(await ws.recv())
        await ws.close()
        return pong["tipo"]

    assert _correr(fluxo()) == "pong"


def test_codigo_errado_nao_emparelha(servidor):
    servidor.novo_codigo()

    async def fluxo():
        ws, _ = await emparelhar(servidor.porta, "000000")
        with pytest.raises(ConnectionClosed) as info:
            await ws.recv()
        return info.value.rcvd.code

    assert _correr(fluxo()) == 4003
    assert servidor.codigo.tentativas_restantes == 2


def test_tres_codigos_errados_bloqueiam_o_codigo(servidor):
    codigo = servidor.novo_codigo()

    async def tentar(valor):
        ws, _ = await emparelhar(servidor.porta, valor)
        try:
            await ws.recv()
        except ConnectionClosed:
            pass

    for _ in range(3):
        _correr(tentar("000000" if codigo.codigo != "000000" else "111111"))
    assert codigo.estado == "esgotado"

    # Mesmo o codigo certo ja nao funciona: o codigo esgotou-se.
    assert _correr(codigo_de_fecho(servidor.porta, codigo.codigo)) == 4001


def test_codigo_nao_pode_ser_reutilizado(servidor):
    codigo = servidor.novo_codigo()
    _correr(emparelhar_e_fechar(servidor.porta, codigo.codigo))
    assert _correr(codigo_de_fecho(servidor.porta, codigo.codigo)) == 4001


async def emparelhar_e_fechar(porta, codigo):
    ws, _ = await emparelhar(porta, codigo)
    await ws.recv()
    await ws.close()


def test_sem_codigo_gerado_recusa_ligacao(servidor):
    assert _correr(codigo_de_fecho(servidor.porta, "123456")) == 4001


def test_mensagem_sem_autenticacao_depois_de_emparelhar_fecha(servidor):
    codigo = servidor.novo_codigo()

    async def fluxo():
        ws, _ = await emparelhar(servidor.porta, codigo.codigo)
        await ws.recv()
        await ws.send(json.dumps({"tipo": "acao", "id": "x", "sequencia": 0,
                                  "acao": {"tipo": "texto", "valor": "a"}, "hmac": "00"}))
        with pytest.raises(ConnectionClosed) as info:
            await ws.recv()
        return info.value.rcvd.code

    assert _correr(fluxo()) == 1008
    assert servidor.recebidas == []


def test_descoberta_responde_ao_pedido(servidor):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(3)
        s.sendto(PEDIDO_DESCOBERTA, ("127.0.0.1", servidor.porta))
        dados, _ = s.recvfrom(1024)
    info = json.loads(dados)
    assert info["nome"] == "Teste" and info["porta"] == servidor.porta


def test_descoberta_ignora_outras_mensagens(servidor):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(0.5)
        s.sendto(b"lixo", ("127.0.0.1", servidor.porta))
        with pytest.raises(socket.timeout):
            s.recvfrom(1024)


def test_emparelhamento_mede_tempo_aceitavel(servidor):
    codigo = servidor.novo_codigo()
    inicio = time.perf_counter()
    _correr(emparelhar_e_fechar(servidor.porta, codigo.codigo))
    decorrido = time.perf_counter() - inicio
    # O SPAKE2 custa ~25 ms; o resto e a ligacao local. Limite largo para nao ser instavel.
    assert decorrido < 2.0


def test_parar_fecha_a_porta(servidor):
    porta = servidor.porta
    servidor.parar()
    assert not servidor.ativo
    with socket.socket() as s:
        s.settimeout(1)
        with pytest.raises(OSError):
            s.connect(("127.0.0.1", porta))
    servidor._thread = None  # fixture chama parar de novo: ja esta parado
