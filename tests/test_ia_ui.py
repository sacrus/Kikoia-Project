import pytest
from PySide6.QtWidgets import QApplication

from teclado.core.ia import ConfigIA
from teclado.ui.ia_teclado import DialogoIATeclado


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_usar_fica_desativado_ate_gerar(qapp):
    dialogo = DialogoIATeclado(None, ConfigIA())
    assert dialogo._botao_usar.isEnabled() is False
    assert dialogo.resultado() is None
    dialogo.close()


def test_sem_chave_mostra_erro_e_nao_avanca(qapp):
    dialogo = DialogoIATeclado(None, ConfigIA(chave=""))
    dialogo._descricao.setPlainText("vogais")
    dialogo._gerar()
    assert dialogo.resultado() is None
    assert dialogo._botao_usar.isEnabled() is False
    assert "chave" in dialogo._estado.text().lower()
    dialogo.close()


def test_previa_mostra_teclado_gerado(qapp):
    dialogo = DialogoIATeclado(None, ConfigIA(chave="x"))
    modelo = {
        "nome": "Vogais",
        "idioma": "pt-PT",
        "linhas": [[
            {"rotulo": "A", "acao": {"tipo": "texto", "valor": "a"}},
            {"rotulo": "E", "acao": {"tipo": "texto", "valor": "e"}},
        ]],
    }
    dialogo._mostrar(modelo)
    assert "Vogais" in dialogo._previa.text()
    assert "2 teclas" in dialogo._previa.text()
    dialogo.close()


def test_config_alterada_devolve_a_chave_escrita(qapp):
    dialogo = DialogoIATeclado(None, ConfigIA(chave="antiga", modelo="m"))
    dialogo._chave.setText("nova")
    assert dialogo.config_alterada().chave == "nova"
    assert dialogo.config_alterada().modelo == "m"
    dialogo.close()
