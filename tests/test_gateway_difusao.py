import asyncio
import hashlib
import hmac
import socket
import time

import pytest
from spake2 import SPAKE2_A
from websockets.asyncio.client import connect

from teclado.gateway.controlador import ControladorGateway
from teclado.gateway.protocolo import Sessao, codificar_emparelhamento, descodificar_emparelhamento
from teclado.gateway.servidor import chave_sessao

MODELO = {"nome": "Vogais", "idioma": "pt-PT",
          "linhas": [[{"rotulo": "A", "acao": {"tipo": "texto", "valor": "a"}}]]}


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _emparelhar(porta, codigo):
    ws = await connect(f"ws://127.0.0.1:{porta}", max_size=16 * 1024)
    spake = SPAKE2_A(codigo.encode("ascii"), idA=b"cliente", idB=b"pc")
    await ws.send(codificar_emparelhamento("desafio", spake.start().hex()))
    resposta = descodificar_emparelhamento(await ws.recv())
    chave = spake.finish(bytes.fromhex(resposta["valor"]))
    await ws.send(codificar_emparelhamento("confirmacao", hmac.new(chave, b"cliente", hashlib.sha256).hexdigest()))
    await ws.recv()  # confirmacao do PC
    return ws, chave


def _ctrl(recebidas, teclado=lambda: None, sugestoes=lambda: []):
    return ControladorGateway(
        nome="PC teste", ao_acao=recebidas.append, ao_ligar=lambda e: None,
        ao_desligar=lambda e: None, fornecer_teclado=teclado, fornecer_sugestoes=sugestoes,
    )


def test_telemovel_recebe_o_teclado_ativo_ao_ligar():
    ctrl = _ctrl([], teclado=lambda: MODELO)
    porta = _porta_livre()
    ctrl.ligar(porta)
    codigo = ctrl.estado()["codigo"]

    async def fluxo():
        ws, chave = await _emparelhar(porta, codigo)
        msg = Sessao(chave_sessao(chave)).receber(await ws.recv())
        await ws.close()
        return msg

    try:
        msg = asyncio.run(fluxo())
    finally:
        ctrl.desligar()
    assert msg["tipo"] == "teclados" and msg["layouts"][0]["nome"] == "Vogais"


def test_atualizar_teclado_chega_em_tempo_real():
    ctrl = _ctrl([])
    porta = _porta_livre()
    ctrl.ligar(porta)
    codigo = ctrl.estado()["codigo"]

    async def fluxo():
        ws, chave = await _emparelhar(porta, codigo)
        sessao = Sessao(chave_sessao(chave))
        await asyncio.to_thread(time.sleep, 0.3)  # o PC regista a sessao depois de confirmar
        ctrl.atualizar_teclado(MODELO | {"nome": "Novo"})
        while True:  # ignora as sugestoes iniciais enviadas ao ligar
            msg = sessao.receber(await asyncio.wait_for(ws.recv(), 5))
            if msg["tipo"] == "teclados":
                break
        await ws.close()
        return msg

    try:
        msg = asyncio.run(fluxo())
    finally:
        ctrl.desligar()
    assert msg["tipo"] == "teclados" and msg["layouts"][0]["nome"] == "Novo"


def test_sugestoes_chegam_ao_telemovel():
    ctrl = _ctrl([], sugestoes=lambda: ["casa", "cama"])
    porta = _porta_livre()
    ctrl.ligar(porta)
    codigo = ctrl.estado()["codigo"]

    async def fluxo():
        ws, chave = await _emparelhar(porta, codigo)
        sessao = Sessao(chave_sessao(chave))
        inicial = sessao.receber(await ws.recv())  # sugestoes atuais ao ligar
        await asyncio.to_thread(time.sleep, 0.3)
        ctrl.atualizar_sugestoes(["bom"])
        seguinte = sessao.receber(await asyncio.wait_for(ws.recv(), 5))
        await ws.close()
        return inicial, seguinte

    try:
        inicial, seguinte = asyncio.run(fluxo())
    finally:
        ctrl.desligar()
    assert inicial["palavras"] == ["casa", "cama"]
    assert seguinte["palavras"] == ["bom"]


def test_escolha_de_sugestao_chega_ao_pc():
    recebidas = []
    ctrl = _ctrl(recebidas)
    porta = _porta_livre()
    ctrl.ligar(porta)
    codigo = ctrl.estado()["codigo"]

    async def fluxo():
        ws, chave = await _emparelhar(porta, codigo)
        sessao = Sessao(chave_sessao(chave))
        await ws.send(sessao.enviar("escolher_sugestao", "e1", {"indice": 2}))
        await asyncio.sleep(0.3)
        await ws.close()

    try:
        asyncio.run(fluxo())
    finally:
        ctrl.desligar()
    assert recebidas and recebidas[0]["tipo"] == "escolher_sugestao" and recebidas[0]["indice"] == 2


def test_indice_de_sugestao_invalido_e_recusado():
    from teclado.gateway.protocolo import ProtocoloErro, codificar
    with pytest.raises(ProtocoloErro):
        codificar(b"c" * 32, "escolher_sugestao", "e", 0, {"indice": 99})
    with pytest.raises(ProtocoloErro):
        codificar(b"c" * 32, "escolher_sugestao", "e", 0, {"indice": True})


def test_atualizar_sem_telemovel_nao_falha():
    ctrl = _ctrl([])
    ctrl.atualizar_teclado(MODELO)
    ctrl.atualizar_sugestoes(["x"])
    assert ctrl.estado() == {"ativo": False}
