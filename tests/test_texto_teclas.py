from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication

from teclado.core import idiomas
from teclado.core.rotulos import rotulo_tecla
from teclado.ui.botao_tecla import TAMANHO_MINIMO, BotaoTecla, _quebrar


def _app():
    return QApplication.instance() or QApplication([])


def _cabe(botao: BotaoTecla) -> bool:
    fonte = QFont(botao.font())
    fonte.setPixelSize(botao._tamanho_atual)
    metrica = QFontMetrics(fonte)
    linhas = botao.text().split("\n")
    largura = botao.width() - 14
    altura = botao.height() - 14
    return all(metrica.horizontalAdvance(linha) <= largura for linha in linhas) and (
        len(linhas) * metrica.height() <= altura
    )


def test_texto_longo_cabe_na_tecla():
    _app()
    botao = BotaoTecla("Navegar entre janelas", 22)
    botao.resize(110, 60)
    botao.ajustar()
    assert _cabe(botao)
    assert botao._tamanho_atual < 22 or "\n" in botao.text()


def test_texto_curto_fica_como_esta():
    _app()
    botao = BotaoTecla("a", 22)
    botao.resize(80, 60)
    botao.ajustar()
    assert botao.text() == "a"
    assert botao._tamanho_atual == 22


def test_palavra_maior_que_a_tecla_nao_rebenta():
    _app()
    botao = BotaoTecla("Supercalifragilisticoexpialidocious", 22)
    botao.resize(30, 30)
    botao.ajustar()
    assert botao._tamanho_atual == TAMANHO_MINIMO


def test_quebrar_respeita_a_largura():
    _app()
    fonte = QFont()
    fonte.setPixelSize(12)
    metrica = QFontMetrics(fonte)
    linhas = _quebrar("uma frase um pouco mais comprida", metrica, 100)
    assert linhas is not None and len(linhas) > 1
    assert all(metrica.horizontalAdvance(linha) <= 100 for linha in linhas)


def test_rotulo_padrao_segue_o_idioma():
    try:
        idiomas.definir("en")
        assert rotulo_tecla("tecla", "espaco", "Espaço") == "Space"
        assert rotulo_tecla("tecla", "backspace", "Apagar") == "Backspace"
    finally:
        idiomas.definir("pt-PT")


def test_rotulo_personalizado_nao_muda():
    assert rotulo_tecla("tecla", "espaco", "Barra") == "Barra"
    assert rotulo_tecla("texto", "a", "Espaço") == "Espaço"
