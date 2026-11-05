import sys

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.layout import (
    MODIFICADORES,
    Acao,
    Layout,
    LayoutInvalido,
    Tecla,
    validar_layout,
)
from teclado.core.saida import ACOES, ACOES_JANELA, TECLAS_ESPECIAIS
from teclado.ui.editor_layout import TECLAS_FUNCAO, simbolos_disponiveis


class SaidaFalsa:
    def __init__(self):
        self.eventos = []

    def escrever(self, texto):
        self.eventos.append(("texto", texto))

    def tecla(self, nome):
        self.eventos.append(("tecla", nome))

    def sequencia(self, acoes):
        self.eventos.extend(acoes)

    def atalho(self, nome):
        self.eventos.append(("atalho", nome))

    def enviar_atalho(self, passo):
        self.eventos.append(("combo", passo))

    def janela_ativa(self, acao, excluir=0):
        self.eventos.append(("janela", acao))
        return True

    def ler_selecao(self):
        return ""


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


# --- teclas e acoes novas -------------------------------------------------

def test_teclas_de_funcao_existem_no_sistema_de_teclas():
    for valor in ("home", "end", "pgup", "pgdn", "prtsc", "insert", "capslock"):
        assert valor in TECLAS_ESPECIAIS


def test_teclas_de_funcao_na_paleta_sao_todas_especiais():
    for _, valor in TECLAS_FUNCAO:
        assert valor in TECLAS_ESPECIAIS


def test_acoes_de_janela_estao_em_acoes():
    assert {"minimizar_teclado", "fechar_janela", "minimizar_janela", "maximizar_janela"} <= ACOES_JANELA
    assert ACOES_JANELA <= ACOES


def test_paleta_tem_ctrl_e_acoes_de_janela():
    itens = simbolos_disponiveis()
    assert ("ctrl" in {i["acao"]["valor"] for i in itens if i["acao"]["tipo"] == "modificador"})
    valores = {i["acao"]["valor"] for i in itens if i["acao"]["tipo"] == "acao"}
    assert ACOES_JANELA <= valores


def test_ctrl_e_modificador_valido_no_layout():
    assert "ctrl" in MODIFICADORES
    dados = {"nome": "T", "idioma": "pt-PT",
             "linhas": [[{"rotulo": "Ctrl", "acao": {"tipo": "modificador", "valor": "ctrl"}}]]}
    assert validar_layout(dados).total_teclas == 1


def test_modificador_inexistente_rejeitado():
    dados = {"nome": "T", "idioma": "pt-PT",
             "linhas": [[{"rotulo": "Alt", "acao": {"tipo": "modificador", "valor": "alt"}}]]}
    with pytest.raises(LayoutInvalido):
        validar_layout(dados)


# --- Ctrl de um toque ---------------------------------------------------------

def test_ctrl_mais_letra_envia_combinacao_e_desliga_ctrl():
    saida = SaidaFalsa()
    editor = Editor(saida, Dicionario({}))
    editor.modificador("ctrl")
    editor.texto("c")
    assert ("combo", "ctrl+c") in saida.eventos
    assert editor.ctrl is False


def test_ctrl_mais_home_envia_combinacao():
    saida = SaidaFalsa()
    editor = Editor(saida, Dicionario({}))
    editor.modificador("ctrl")
    editor.tecla("home")
    assert ("combo", "ctrl+home") in saida.eventos


def test_ctrl_com_simbolo_escreve_o_simbolo():
    saida = SaidaFalsa()
    editor = Editor(saida, Dicionario({}))
    editor.modificador("ctrl")
    editor.texto(".")
    assert ("texto", ".") in saida.eventos
    assert not any(t == "combo" for t, _ in saida.eventos)
    assert editor.ctrl is False


def test_ctrl_nao_afeta_a_tecla_seguinte_sem_ctrl():
    saida = SaidaFalsa()
    editor = Editor(saida, Dicionario({}))
    editor.modificador("ctrl")
    editor.texto("v")
    editor.texto("a")
    assert ("combo", "ctrl+v") in saida.eventos
    # Sem Ctrl, a letra seguinte e escrita como texto (inicio de frase: maiuscula).
    assert ("texto", "A") in saida.eventos
    assert sum(1 for t, _ in saida.eventos if t == "combo") == 1


def test_ctrl_nao_e_ligado_por_tecla_de_janela():
    saida = SaidaFalsa()
    chamadas = []
    editor = Editor(saida, Dicionario({}))
    editor.ligar_acoes_janela(chamadas.append)
    editor.modificador("ctrl")
    editor.acao("fechar_janela")
    assert chamadas == ["fechar_janela"]
    assert editor.ctrl is True  # continua a aguardar a tecla


# --- acoes de janela ---------------------------------------------------------

@pytest.mark.parametrize("acao", sorted(ACOES_JANELA))
def test_acao_de_janela_vai_ao_controlo_do_ecra(acao):
    saida = SaidaFalsa()
    chamadas = []
    editor = Editor(saida, Dicionario({}))
    editor.ligar_acoes_janela(chamadas.append)
    editor.texto("ola")
    editor.acao(acao)
    assert chamadas == [acao]
    assert ("atalho", acao) not in saida.eventos
    assert editor.palavra == "Ola"  # o texto em curso nao e mexido


# --- tamanho das teclas (regressao do bug visual) ---------------------------------

def _layout_de_teste():
    return Layout(
        nome="Teste",
        idioma="pt-PT",
        linhas=((
            Tecla("a", Acao("texto", "a"), 1.0),
            Tecla("Espaço", Acao("tecla", "espaco"), 4.0),
        ),),
    )


def test_largura_da_tecla_e_respeitada_na_janela(qapp):
    from teclado.core.tema import Tema
    from teclado.ui.janela import JanelaTeclado

    tema = Tema(nome="T", cor_fundo="#FFFFFF", cor_tecla="#EEEEEE", cor_texto="#000000",
                cor_tecla_premida="#FFD54F", cor_texto_premido="#000000")
    janela = JanelaTeclado(Editor(SaidaFalsa(), Dicionario({})), _layout_de_teste(), tema,
                           ancorar_fundo=False)
    janela.resize(1000, 300)
    janela.show()
    qapp.processEvents()
    botoes = {b.text(): b for b in janela.findChildren(QPushButton)}
    try:
        # "Espaço" tem largura 4 e "a" tem largura 1: a tecla grande deve ser claramente maior.
        assert botoes["Espaço"].width() >= 3 * botoes["a"].width()
    finally:
        janela.close()


def test_teclas_nao_tem_tamanho_minimo_grande(qapp):
    from teclado.core.tema import Tema
    from teclado.ui.janela import JanelaTeclado

    tema = Tema(nome="T", cor_fundo="#FFFFFF", cor_tecla="#EEEEEE", cor_texto="#000000",
                cor_tecla_premida="#FFD54F", cor_texto_premido="#000000")
    janela = JanelaTeclado(Editor(SaidaFalsa(), Dicionario({})), _layout_de_teste(), tema,
                           ancorar_fundo=False)
    botao = next(b for b in janela.findChildren(QPushButton) if b.text() == "a")
    assert botao.minimumWidth() <= 24
    janela.close()


# --- reserva da parte inferior do ecra (Windows) --------------------------------

@pytest.mark.skipif(sys.platform != "win32", reason="AppBar do Windows")
def test_teclado_reserva_o_fundo_do_ecra(qapp):
    from teclado.core.tema import Tema
    from teclado.ui.appbar import BarraInferior
    from teclado.ui.janela import JanelaTeclado

    barra = BarraInferior()
    antes = barra.area_de_trabalho()
    tema = Tema(nome="T", cor_fundo="#FFFFFF", cor_tecla="#EEEEEE", cor_texto="#000000",
                cor_tecla_premida="#FFD54F", cor_texto_premido="#000000")
    janela = JanelaTeclado(Editor(SaidaFalsa(), Dicionario({})), _layout_de_teste(), tema)
    janela.show()
    qapp.processEvents()
    try:
        ratio = qapp.primaryScreen().devicePixelRatio() or 1.0
        topo_fisico = round(janela.geometry().top() * ratio)
        area = barra.area_de_trabalho()
        # A area util termina onde comeca o teclado.
        assert abs(area[3] - topo_fisico) <= 2
        assert area[3] < antes[3]
    finally:
        janela.close()
        qapp.processEvents()
    assert barra.area_de_trabalho() == antes
