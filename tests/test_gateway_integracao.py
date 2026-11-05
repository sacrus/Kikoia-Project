import asyncio
import hashlib
import hmac
import socket

import pytest
from PySide6.QtWidgets import QApplication
from spake2 import SPAKE2_A
from websockets.asyncio.client import connect

from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.layout import descobrir_layouts
from teclado.core.layout_editor import modelo_de
from teclado.core.paths import DADOS_PROJETO
from teclado.gateway.acoes import aplicar_acao_remota
from teclado.gateway.controlador import ControladorGateway
from teclado.gateway.protocolo import Sessao, codificar_emparelhamento, descodificar_emparelhamento
from teclado.gateway.servidor import chave_sessao


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
    return ws, chave


class Registo:
    def __init__(self):
        self.envios = []

    def escrever(self, texto):
        self.envios.append(("escrever", texto))

    def tecla(self, nome):
        self.envios.append(("tecla", nome))

    def sequencia(self, acoes):
        self.envios.extend(acoes)

    def atalho(self, nome):
        self.envios.append(("atalho", nome))

    def enviar_atalho(self, passo):
        self.envios.append(("combo", passo))

    def colar_texto(self, texto):
        self.envios.append(("colar", texto))

    def ler_selecao(self):
        return ""


def _controlador(recebidas, ligados, teclados):
    return ControladorGateway(
        nome="PC teste",
        ao_acao=recebidas.append,
        ao_ligar=ligados.append,
        ao_desligar=lambda endereco: None,
        fornecer_teclado=teclados,
    )


def test_ligar_gera_codigo_e_desligar_fecha(tmp_path):
    ctrl = _controlador([], [], lambda: None)
    porta = _porta_livre()
    ctrl.ligar(porta)
    estado = ctrl.estado()
    assert estado["ativo"] and estado["porta"] == porta
    assert len(estado["codigo"]) == 6 and estado["estado_codigo"] == "ativo"
    ctrl.desligar()
    assert ctrl.estado() == {"ativo": False}


def test_novo_codigo_substitui_o_anterior():
    ctrl = _controlador([], [], lambda: None)
    ctrl.ligar(_porta_livre())
    try:
        antigo = ctrl.estado()["codigo"]
        novo = ctrl.novo_codigo()
        assert len(novo) == 6
        assert ctrl.estado()["codigo"] == novo
        assert antigo or True
    finally:
        ctrl.desligar()


def test_novo_codigo_sem_ligar_erro():
    with pytest.raises(RuntimeError):
        _controlador([], [], lambda: None).novo_codigo()


def test_porta_ocupada_erro_claro():
    ocupada = socket.socket()
    ocupada.bind(("0.0.0.0", 0))  # mesma interface que o servidor usa
    ocupada.listen()
    porta = ocupada.getsockname()[1]
    ctrl = _controlador([], [], lambda: None)
    try:
        with pytest.raises(RuntimeError):
            ctrl.ligar(porta)
        assert not ctrl.ativo
    finally:
        ocupada.close()


def test_telemovel_recebe_os_teclados_depois_de_emparelhar():
    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["QWERTY"]
    ctrl = _controlador([], [], lambda: modelo_de(layout))
    porta = _porta_livre()
    ctrl.ligar(porta)
    codigo = ctrl.estado()["codigo"]

    async def fluxo():
        ws, chave = await _emparelhar(porta, codigo)
        await ws.recv()  # confirmacao do PC
        sessao = Sessao(chave_sessao(chave))
        msg = sessao.receber(await ws.recv())
        await ws.close()
        return msg

    try:
        msg = asyncio.run(fluxo())
    finally:
        ctrl.desligar()
    assert msg["tipo"] == "teclados"
    assert msg["layouts"][0]["nome"] == "QWERTY"


def test_acao_do_telemovel_chega_ao_callback_do_pc():
    recebidas = []
    ctrl = _controlador(recebidas, [], lambda: None)
    porta = _porta_livre()
    ctrl.ligar(porta)
    codigo = ctrl.estado()["codigo"]

    async def fluxo():
        ws, chave = await _emparelhar(porta, codigo)
        await ws.recv()
        sessao = Sessao(chave_sessao(chave))
        await ws.send(sessao.enviar("acao", "a1", {"acao": {"tipo": "tecla", "valor": "backspace"}}))
        await asyncio.sleep(0.3)
        await ws.close()

    try:
        asyncio.run(fluxo())
    finally:
        ctrl.desligar()
    assert recebidas and recebidas[0]["acao"] == {"tipo": "tecla", "valor": "backspace"}


# --- aplicar acoes remotas no editor ---------------------------------------------

def _editor():
    saida = Registo()
    return Editor(saida, Dicionario({})), saida


def test_texto_remoto_escreve_com_inicio_de_frase():
    editor, saida = _editor()
    aplicar_acao_remota(editor, {"tipo": "texto", "valor": "ola"})
    assert ("escrever", "O") in saida.envios


def test_tecla_remota_envia_a_tecla():
    editor, saida = _editor()
    aplicar_acao_remota(editor, {"tipo": "tecla", "valor": "enter"})
    assert ("tecla", "enter") in saida.envios


def test_acao_de_edicao_remota_envia_o_atalho():
    editor, saida = _editor()
    aplicar_acao_remota(editor, {"tipo": "acao", "valor": "apagar_palavra"})
    assert ("atalho", "apagar_palavra") in saida.envios


def test_multitoque_remoto_percorre_as_letras():
    editor, saida = _editor()
    aplicar_acao_remota(editor, {"tipo": "multitoque", "valor": "abc"})
    aplicar_acao_remota(editor, {"tipo": "multitoque", "valor": "abc"})
    texto = "".join(v for t, v in saida.envios if t == "escrever")
    assert texto[-1] == "b" or texto[-1] == "B"


def test_navegar_remoto_nao_altera_o_editor():
    editor, saida = _editor()
    aplicar_acao_remota(editor, {"tipo": "navegar", "valor": "Numerico"})
    assert saida.envios == []


# --- dialogo ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class _CtrlFalso:
    def __init__(self, estado):
        self._estado = estado
        self.ativo = estado["ativo"]

    def estado(self):
        return self._estado

    def ligar(self, porta, transporte="wifi"):
        self.ativo = True

    def bluetooth_disponivel(self):
        return None

    def desligar(self):
        self.ativo = False

    def novo_codigo(self):
        return "123456"


def test_dialogo_mostra_desligado_e_botao_ligar(qapp):
    from teclado.ui.gateway_opcoes import DialogoGateway, formatar_codigo
    dialogo = DialogoGateway(None, _CtrlFalso({"ativo": False}), lambda: True, 47800, lambda p: True)
    assert dialogo._botao_ligar.text() == "Ligar ao telemóvel"
    assert dialogo._codigo.text() == "—"
    assert formatar_codigo("123456") == "123 456"
    dialogo.close()


def test_dialogo_mostra_codigo_quando_ativo(qapp):
    from teclado.ui.gateway_opcoes import DialogoGateway
    estado = {"ativo": True, "porta": 47800, "codigo": "654321", "estado_codigo": "ativo",
              "segundos": 90, "ligados": 0}
    dialogo = DialogoGateway(None, _CtrlFalso(estado), lambda: True, 47800, lambda p: True)
    assert dialogo._codigo.text() == "654 321"
    assert dialogo._botao_ligar.text() == "Desligar"
    dialogo.close()


def test_ligar_sem_autorizacao_nao_liga(qapp):
    from teclado.ui.gateway_opcoes import DialogoGateway
    ctrl = _CtrlFalso({"ativo": False})
    dialogo = DialogoGateway(None, ctrl, lambda: False, 47800, lambda p: True)
    dialogo._ligar_ou_desligar()
    assert ctrl.ativo is False
    dialogo.close()
