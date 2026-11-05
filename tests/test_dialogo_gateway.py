import pytest
from PySide6.QtWidgets import QApplication

from teclado.gateway import controlador as mod_controlador
from teclado.gateway.controlador import ControladorGateway
from teclado.gateway.emparelhamento import CodigoEmparelhamento
from teclado.ui.gateway_opcoes import DialogoGateway


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class _ServidorFalso:
    def __init__(self, nome, porta=0, **kwargs):
        self._codigo = None
        self._ativo = False

    def iniciar(self):
        self._ativo = True

    def parar(self):
        self._ativo = False

    def novo_codigo(self):
        self._codigo = CodigoEmparelhamento("123456")
        return self._codigo

    @property
    def ativo(self):
        return self._ativo

    @property
    def codigo(self):
        return self._codigo

    @property
    def dispositivos_ligados(self):
        return 0


def _controlador():
    return ControladorGateway(
        nome="PC", ao_acao=lambda m: None, ao_ligar=lambda e: None,
        ao_desligar=lambda e: None, fornecer_teclado=lambda: None,
    )


def test_dialogo_mostra_codigo_depois_de_ligar(qapp, monkeypatch):
    monkeypatch.setattr(mod_controlador, "ServidorGateway", _ServidorFalso)
    dialogo = DialogoGateway(None, _controlador(), lambda: True, 8765, lambda p: True)
    dialogo._ligar_ou_desligar()
    assert dialogo._codigo.text() == "123 456"
    dialogo._ligar_ou_desligar()
    assert dialogo._codigo.text() == "—"
    dialogo.close()


def test_dialogo_nao_rebenta_ao_atualizar_sem_ligar(qapp):
    dialogo = DialogoGateway(None, _controlador(), lambda: True, 8765, lambda p: True)
    dialogo._atualizar()
    assert dialogo._codigo.text() == "—"
    dialogo.close()
