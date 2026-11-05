import copy

import pytest

from teclado.core.acentos import ACENTOS, combinar
from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.layout import LayoutInvalido, descobrir_layouts, validar_layout
from teclado.core.paths import DADOS_PROJETO


class Registo:
    def __init__(self):
        self.eventos = []

    def escrever(self, texto):
        self.eventos.append(("texto", texto))

    def tecla(self, nome):
        self.eventos.append(("tecla", nome))

    def sequencia(self, acoes):
        self.eventos.extend(acoes)

    def escrito(self):
        return "".join(v for t, v in self.eventos if t == "texto")


def _editor(base=None):
    registo = Registo()
    dic = Dicionario(base or {"casa": 10, "cama": 5, "cair": 20})
    return Editor(registo, dic), registo


# --- combinacao -------------------------------------------------------

def test_combinar_vogal_com_acento():
    assert combinar("a", "agudo") == "\u00e1"
    assert combinar("o", "circunflexo") == "\u00f4"
    assert combinar("a", "til") == "\u00e3"
    assert combinar("a", "grave") == "\u00e0"


def test_combinar_sem_resultado_devolve_none():
    assert combinar("k", "agudo") is None
    assert combinar("e", "til") is None
    assert combinar("c", "circunflexo") is None


def test_acentos_definidos_tem_sinal_isolado():
    for nome, (marca, sinal) in ACENTOS.items():
        assert len(marca) == 1 and sinal


# --- editor ------------------------------------------------------------

def test_acento_agudo_combina_com_a_letra_seguinte():
    editor, registo = _editor()
    editor.texto("sim ")
    editor.acento("agudo")
    editor.texto("a")
    assert registo.escrito() == "Sim \u00e1"


def test_acento_com_maiuscula_combina():
    editor, registo = _editor()
    editor.acento("agudo")
    editor.texto("e")
    assert registo.escrito() == "\u00c9"


def test_acento_til_e_circunflexo_em_sequencia():
    editor, registo = _editor()
    editor.texto("x ")
    editor.acento("til")
    editor.texto("a")
    editor.acento("circunflexo")
    editor.texto("o")
    assert registo.escrito() == "X \u00e3\u00f4"


def test_acento_sem_letra_sai_isolado_com_espaco():
    editor, registo = _editor()
    editor.texto("sim")
    editor.acento("agudo")
    editor.tecla("espaco")
    assert registo.escrito() == "Sim\u00b4"


def test_acento_seguido_de_pontuacao_sai_isolado():
    editor, registo = _editor()
    editor.texto("sim")
    editor.acento("grave")
    editor.texto(".")
    assert registo.escrito() == "Sim`."


def test_acento_sem_combinacao_sai_antes_da_letra():
    editor, registo = _editor()
    editor.texto("sim ")
    editor.acento("agudo")
    editor.texto("k")
    assert registo.escrito() == "Sim \u00b4k"


def test_dois_acentos_seguidos_o_primeiro_sai_isolado():
    editor, registo = _editor()
    editor.texto("sim ")
    editor.acento("agudo")
    editor.acento("til")
    editor.texto("a")
    assert registo.escrito() == "Sim \u00b4\u00e3"


def test_backspace_cancela_acento_pendente():
    editor, registo = _editor()
    editor.texto("sim")
    editor.acento("agudo")
    editor.tecla("backspace")
    assert editor.acento_pendente is None
    assert registo.escrito() == "Sim"
    assert ("tecla", "backspace") in registo.eventos


def test_acento_pendente_nao_mostra_sugestoes():
    editor, _ = _editor()
    editor.texto("ca")
    assert editor.sugestoes
    editor.acento("agudo")
    assert editor.sugestoes == []


def test_sugestao_nao_e_usada_com_acento_pendente():
    editor, registo = _editor()
    editor.texto("ca")
    editor.acento("agudo")
    registo.eventos.clear()
    editor.usar_sugestao(0)
    assert registo.eventos == []


def test_palavra_acentuada_fica_no_prefixo_para_sugestoes():
    editor, _ = _editor({"também": 9, "tambor": 1})
    editor.texto("tamb")
    editor.acento("agudo")
    editor.texto("e")
    # A primeira letra da frase sai em maiuscula; o prefixo acompanha o texto.
    assert editor.palavra == "Tamb\u00e9"


def test_acento_desconhecido_rejeitado():
    editor, _ = _editor()
    with pytest.raises(ValueError):
        editor.acento("cedilha_estranha")


# --- layout -------------------------------------------------------------

def test_layout_portugues_tem_teclas_de_acento():
    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["Português"]
    acentos = [t.acao.valor for linha in layout.linhas for t in linha if t.acao.tipo == "acento"]
    assert set(acentos) == {"agudo", "grave", "circunflexo", "til"}


def test_layout_rejeita_acento_desconhecido():
    dados = {
        "nome": "Teste",
        "idioma": "pt-PT",
        "linhas": [[{"rotulo": "x", "acao": {"tipo": "acento", "valor": "inventado"}}]],
    }
    with pytest.raises(LayoutInvalido):
        validar_layout(copy.deepcopy(dados))
