import pytest
from PySide6.QtWidgets import QApplication

from teclado.core import modelos
from teclado.ui.voz_opcoes import DialogoOpcoesVoz


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_sem_modelo_so_o_botao_de_descarregar_esta_ativo(qapp, tmp_path):
    dialogo = DialogoOpcoesVoz(None, {}, [], pasta_dados=tmp_path, idioma="pt-PT")
    assert dialogo._botao_descarregar.isEnabled()
    assert not dialogo._botao_remover.isEnabled()
    dialogo.close()


def test_com_modelo_instalado_so_o_botao_de_remover_esta_ativo(qapp, tmp_path):
    pasta = tmp_path / "modelos" / modelos.MODELOS_VOZ["en"].pasta
    (pasta / "am").mkdir(parents=True)
    (pasta / "am" / "final.mdl").write_bytes(b"x")
    dialogo = DialogoOpcoesVoz(None, {}, [], pasta_dados=tmp_path, idioma="en")
    assert not dialogo._botao_descarregar.isEnabled()
    assert dialogo._botao_remover.isEnabled()
    dialogo.close()


def test_sem_pasta_nao_mostra_a_secao_do_modelo(qapp):
    dialogo = DialogoOpcoesVoz(None, {}, [])
    assert not hasattr(dialogo, "_botao_descarregar")
    dialogo.close()


def test_idioma_sem_modelo_desativa_os_botoes(qapp, tmp_path):
    dialogo = DialogoOpcoesVoz(None, {}, [], pasta_dados=tmp_path, idioma="de")
    assert not dialogo._botao_descarregar.isEnabled()
    assert not dialogo._botao_remover.isEnabled()
    dialogo.close()
