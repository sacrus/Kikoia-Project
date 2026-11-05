import uuid

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from teclado.ui.instancia import ServidorInstancia, ja_em_execucao


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _nome():
    return "teclado-teste-" + uuid.uuid4().hex[:8]


def test_sem_instancia_nao_ha_outra_a_correr(qapp):
    assert not ja_em_execucao(_nome())


def test_segunda_instancia_pede_para_mostrar(qapp):
    nome = _nome()
    servidor = ServidorInstancia(nome)
    assert servidor.ativo
    recebidos = []
    servidor.pedido_mostrar.connect(lambda: recebidos.append(True))

    assert ja_em_execucao(nome)

    espera = QEventLoop()
    QTimer.singleShot(300, espera.quit)
    espera.exec()
    assert recebidos == [True]
