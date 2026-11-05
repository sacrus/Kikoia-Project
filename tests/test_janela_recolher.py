from PySide6.QtWidgets import QApplication

from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.layout import Acao, Layout, Tecla
from teclado.core.paths import DADOS_PROJETO
from teclado.core.tema import descobrir_temas
from teclado.ui.janela import JanelaTeclado


class _Saida:
    def __getattr__(self, nome):
        return lambda *a, **k: None


def _janela():
    app = QApplication.instance() or QApplication([])
    layout = Layout("T", "pt-PT", ((Tecla("A", Acao("texto", "a"), 1.0),),))
    tema = descobrir_temas([DADOS_PROJETO / "temas"])["Claro"]
    return app, JanelaTeclado(Editor(_Saida(), Dicionario({})), layout, tema, ancorar_fundo=False)


def test_recolhido_durante_um_dialogo_nao_volta_a_aparecer():
    app, janela = _janela()
    janela.show()
    app.processEvents()

    def dialogo():
        janela.recolher_definitivamente()

    janela.sem_sobreposicao(dialogo)
    assert not janela.isVisible()
    janela.close()


def test_sem_recolher_volta_a_aparecer_depois_do_dialogo():
    app, janela = _janela()
    janela.show()
    app.processEvents()
    janela.sem_sobreposicao(lambda: None)
    assert janela.isVisible()
    janela.close()
