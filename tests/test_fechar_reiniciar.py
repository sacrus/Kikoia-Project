import sys

import pytest
from PySide6.QtWidgets import QApplication

from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.layout import Acao, Layout, Tecla
from teclado.core.paths import DADOS_PROJETO
from teclado.core.reinicio import ARGUMENTO, comando_reinicio
from teclado.core.saida import ACOES, ACOES_EDICAO
from teclado.core.tema import descobrir_temas
from teclado.ui.janela import JanelaTeclado


class _Saida:
    def __getattr__(self, nome):
        return lambda *a, **k: None


def _janela(**kwargs):
    app = QApplication.instance() or QApplication([])
    layout = Layout("T", "pt-PT", ((Tecla("A", Acao("texto", "a"), 1.0),),))
    tema = descobrir_temas([DADOS_PROJETO / "temas"])["Claro"]
    return app, JanelaTeclado(Editor(_Saida(), Dicionario({})), layout, tema, ancorar_fundo=False, **kwargs)


def test_fechar_a_janela_chama_ao_fechar_para_sair_da_aplicacao():
    chamadas = []
    app, janela = _janela(ao_fechar=lambda: chamadas.append("sair"))
    janela.show()
    app.processEvents()
    janela.close()
    assert chamadas == ["sair"]


def test_reinicio_a_partir_do_codigo_fonte():
    assert comando_reinicio(False, "python") == ["python", "-m", "teclado", ARGUMENTO]


def test_reinicio_a_partir_do_executavel():
    assert comando_reinicio(True, "Kikoia.exe") == ["Kikoia.exe", ARGUMENTO]


def test_navegar_entre_janelas_e_um_atalho_alt_tab():
    assert ACOES_EDICAO["navegar_janelas"] == ("alt+tab",)
    assert "navegar_janelas" in ACOES


@pytest.mark.skipif(sys.platform != "win32", reason="SendInput so existe no Windows")
def test_alt_tab_envia_alt_tab_e_libertaos_pela_ordem_certa():
    from teclado.core.saida.windows import eventos_para_passo

    # alt para baixo, tab para baixo e para cima, alt para cima.
    assert len(eventos_para_passo("alt+tab")) == 4
