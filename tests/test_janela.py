import ctypes
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton

from teclado.core.layout import descobrir_layouts
from teclado.core.paths import DADOS_PROJETO
from teclado.core.tema import descobrir_temas

WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
GWL_EXSTYLE = -20


class _Saida:
    def __init__(self):
        self.textos = []
        self.teclas = []

    def escrever(self, texto):
        self.textos.append(texto)

    def tecla(self, nome):
        self.teclas.append(nome)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _janela(saida, layout_nome="Português", tema_nome="Claro", **kwargs):
    from teclado.core.dicionario import Dicionario
    from teclado.core.editor import Editor
    from teclado.ui.janela import JanelaTeclado

    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])[layout_nome]
    tema = descobrir_temas([DADOS_PROJETO / "temas"])[tema_nome]
    return JanelaTeclado(Editor(saida, Dicionario()), layout, tema, **kwargs)


def _botao(janela, texto):
    return next(b for b in janela.findChildren(QPushButton) if b.text() == texto)


@pytest.mark.skipif(sys.platform != "win32", reason="Verificacao Win32")
def test_janela_nao_aceita_foco_e_fica_no_topo(app):
    janela = _janela(_Saida())
    janela.show()
    app.processEvents()
    try:
        user32 = ctypes.WinDLL("user32")
        user32.GetWindowLongPtrW.argtypes = (ctypes.c_void_p, ctypes.c_int)
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        estilo = user32.GetWindowLongPtrW(int(janela.winId()), GWL_EXSTYLE)
        assert estilo & WS_EX_NOACTIVATE, "Janela pode roubar o foco"
        assert estilo & WS_EX_TOPMOST, "Janela nao esta sempre por cima"
    finally:
        janela.close()


def test_botoes_nao_recebem_foco(app):
    janela = _janela(_Saida())
    for botao in janela.findChildren(QPushButton):
        assert botao.focusPolicy() == Qt.FocusPolicy.NoFocus
    janela.close()


def test_tecla_envia_texto_do_layout(app):
    saida = _Saida()
    janela = _janela(saida)
    _botao(janela, "a").click()
    # Inicio de frase: a primeira letra sai em maiuscula.
    assert saida.textos == ["A"]
    janela.close()


def test_tecla_a_meio_de_frase_sai_minuscula(app):
    saida = _Saida()
    janela = _janela(saida)
    _botao(janela, "a").click()
    _botao(janela, "b").click()
    assert saida.textos == ["A", "b"]
    janela.close()


def test_tecla_especial_envia_comando(app):
    saida = _Saida()
    janela = _janela(saida)
    _botao(janela, "Apagar").click()
    assert saida.teclas == ["backspace"]
    janela.close()


def test_montar_outro_layout_reconstroi_teclas(app):
    janela = _janela(_Saida())
    janela.montar(descobrir_layouts([DADOS_PROJETO / "layouts"])["Vogais"])
    rotulos = [b.text() for b in janela.findChildren(QPushButton)]
    assert "A" in rotulos and "ç" not in rotulos
    janela.close()


def test_barra_minima_so_tem_sugestoes_voz_e_definicoes(app):
    janela = _janela(_Saida())
    textos = {b.text() for b in janela.findChildren(QPushButton)}
    assert janela._botao_definicoes in janela.findChildren(QPushButton)
    assert "Sugestões" in textos and "Falar" in textos and "Ditar" in textos
    assert "Layout" not in textos and "Tema" not in textos and "Personalizar" not in textos
    janela.close()


def test_voz_desativada_por_omissao(app):
    janela = _janela(_Saida())
    assert _botao(janela, "Falar").isEnabled() is False
    assert _botao(janela, "Ditar").isEnabled() is False
    janela.close()


def test_engrenagem_pede_definicoes(app):
    chamadas = []
    from teclado.core.dicionario import Dicionario
    from teclado.core.editor import Editor
    from teclado.ui.janela import JanelaTeclado

    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["QWERTY"]
    tema = descobrir_temas([DADOS_PROJETO / "temas"])["Claro"]
    janela = JanelaTeclado(Editor(_Saida(), Dicionario()), layout, tema,
                           ao_definicoes=lambda: chamadas.append(1))
    janela._botao_definicoes.click()
    app.processEvents()
    assert chamadas == [1]
    janela.close()


def test_desligar_sugestoes_oculta_a_faixa(app):
    janela = _janela(_Saida())
    janela.show()
    _botao(janela, "Sugestões").click()
    assert janela._faixa_sugestoes.isVisibleTo(janela) is False
    _botao(janela, "Sugestões").click()
    janela.close()

def test_sem_sobreposicao_recolhe_e_repoe(app):
    janela = _janela(_Saida())
    janela.show()
    app.processEvents()
    visto_durante = []
    janela.sem_sobreposicao(lambda: visto_durante.append(janela.isVisible()))
    assert visto_durante == [False]
    assert janela.isVisible()
    janela.close()


def test_sem_sobreposicao_repoe_mesmo_com_erro(app):
    janela = _janela(_Saida())
    janela.show()
    app.processEvents()
    def falha():
        raise RuntimeError("erro no dialogo")
    try:
        janela.sem_sobreposicao(falha)
    except RuntimeError:
        pass
    assert janela.isVisible()
    janela.close()

def test_imagem_grande_e_reduzida_ao_carregar(tmp_path):
    from PySide6.QtGui import QImage

    from teclado.ui.janela import LADO_MAXIMO_IMAGEM, carregar_imagem_fundo

    caminho = tmp_path / "grande.png"
    QImage(4000, 3000, QImage.Format.Format_RGB32).save(str(caminho))
    imagem = carregar_imagem_fundo(caminho)
    assert max(imagem.width(), imagem.height()) == LADO_MAXIMO_IMAGEM


def test_imagem_invalida_nao_rebenta(tmp_path):
    from teclado.ui.janela import carregar_imagem_fundo

    ficheiro = tmp_path / "falso.png"
    ficheiro.write_bytes(b"isto nao e uma imagem")
    assert carregar_imagem_fundo(ficheiro) is None


def test_cache_da_imagem_e_criado_e_acompanha_o_tamanho(app, tmp_path):
    from PySide6.QtGui import QImage

    from teclado.core.tema import Tema
    from teclado.ui.janela import JanelaTeclado

    caminho = tmp_path / "fundo.png"
    QImage(800, 600, QImage.Format.Format_RGB32).save(str(caminho))
    base = _janela(_Saida())
    tema = Tema(
        nome="Img", cor_fundo="#000000", cor_tecla="#111111", cor_texto="#FFFFFF",
        cor_tecla_premida="#FFD54F", cor_texto_premido="#000000",
        imagem_fundo=caminho, opacidade_imagem=50,
    )
    from teclado.core.dicionario import Dicionario
    from teclado.core.editor import Editor

    janela = JanelaTeclado(Editor(_Saida(), Dicionario()), base._modelo_layout, tema)
    janela.resize(500, 400)
    janela.show()
    app.processEvents()
    assert janela._imagem_escalada is not None
    assert janela._imagem_escalada.width() >= 500 or janela._imagem_escalada.height() >= 400
    janela.close()
    base.close()
