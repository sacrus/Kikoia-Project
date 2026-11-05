import sys

import pytest

from teclado.core.aplicacao import Aplicacao
from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.core.teclado_fisico import MAX_PALAVRA, ConstrutorPalavra


class Registo:
    def __init__(self):
        self.envios = []

    def escrever(self, texto):
        self.envios.append(("escrever", texto))

    def tecla(self, nome):
        self.envios.append(("tecla", nome))

    def sequencia(self, acoes):
        self.envios.extend(acoes)

    def atalho(self, nome):
        self.envios.append(("atalho", nome))

    def enviar_atalho(self, passo):
        self.envios.append(("combo", passo))

    def colar_texto(self, texto):
        self.envios.append(("colar", texto))

    def ler_selecao(self):
        return ""


def _letras(editor, texto):
    for c in texto:
        editor.evento_fisico("letra", c)


# --- construtor de palavra ----------------------------------------------------

def test_palavra_acumula_letras_e_termina_com_separador():
    c = ConstrutorPalavra()
    for letra in "casa":
        c.letra(letra)
    assert c.prefixo == "casa"
    assert c.separador() == "casa"


def test_apos_separador_nada_fica_guardado():
    c = ConstrutorPalavra()
    c.letra("a")
    c.separador()
    assert c.prefixo == ""
    assert c.separador() is None


def test_apagar_remove_a_ultima_letra():
    c = ConstrutorPalavra()
    for letra in "casa":
        c.letra(letra)
    c.apagar()
    assert c.prefixo == "cas"


def test_reiniciar_esquece_a_palavra():
    c = ConstrutorPalavra()
    c.letra("x")
    c.reiniciar()
    assert c.prefixo == ""


def test_palavra_demasiado_longa_e_descartada():
    c = ConstrutorPalavra()
    for _ in range(MAX_PALAVRA + 5):
        c.letra("a")
    assert len(c.prefixo) <= MAX_PALAVRA


# --- traducao de teclas (funcao pura) -----------------------------------------------

@pytest.mark.skipif(sys.platform != "win32", reason="modulo do gancho usa a API do Windows")
def test_traducao_de_teclas():
    from teclado.core.captura_teclado import traduzir
    assert traduzir(0x41, "a", False) == ("letra", "a")
    assert traduzir(0x20, None, False) == ("separador", " ")
    assert traduzir(0x08, None, False) == ("apagar",)
    assert traduzir(0x2E, None, False) == ("reiniciar",)       # Delete
    assert traduzir(0x41, "a", True) == ("reiniciar",)         # com Ctrl/Alt
    assert traduzir(0x10, None, False) is None                  # Shift sozinho nao conta
    assert traduzir(0xBE, ".", False) == ("separador", ".")


# --- editor: sugestoes com o teclado fisico -----------------------------------------

def test_teclas_fisicas_geram_sugestoes():
    editor = Editor(Registo(), Dicionario({"casa": 5, "cama": 2}))
    _letras(editor, "ca")
    assert editor.sugestoes[0] == "casa"


def test_teclas_fisicas_nunca_sao_enviadas_a_aplicacao():
    saida = Registo()
    editor = Editor(saida, Dicionario({"casa": 5}))
    _letras(editor, "casa")
    editor.evento_fisico("apagar")
    assert saida.envios == []


def test_escolher_sugestao_fisica_apaga_o_prefixo_e_escreve():
    saida = Registo()
    editor = Editor(saida, Dicionario({"casa": 5}))
    _letras(editor, "ca")
    editor.usar_sugestao(0)
    assert saida.envios[:2] == [("tecla", "backspace"), ("tecla", "backspace")]
    assert saida.envios[2] == ("texto", "casa ")


def test_depois_de_escolher_sugestao_fisica_o_prefixo_recomeca_limpo():
    saida = Registo()
    editor = Editor(saida, Dicionario({"casa": 5}))
    _letras(editor, "ca")
    editor.usar_sugestao(0)
    assert editor.sugestoes == []
    _letras(editor, "x")
    assert editor.sugestoes == []  # nao reaproveita "ca"


def test_separador_fisico_nao_aprende_sem_opcao():
    dic = Dicionario({})
    editor = Editor(Registo(), dic)
    _letras(editor, "zebra")
    editor.evento_fisico("separador", " ")
    assert dic.sugerir("ze", 5) == []


def test_separador_fisico_aprende_quando_ativado(tmp_path):
    dic = Dicionario({}, pessoal_caminho=tmp_path / "uso.sqlite")
    editor = Editor(Registo(), dic)
    editor.aprender_fisico = True
    _letras(editor, "zebra")
    editor.evento_fisico("separador", " ")
    assert dic.sugerir("ze", 5) == ["zebra"]
    dic.fechar()


def test_palavras_muito_curtas_nao_sao_aprendidas(tmp_path):
    dic = Dicionario({}, pessoal_caminho=tmp_path / "uso.sqlite")
    editor = Editor(Registo(), dic)
    editor.aprender_fisico = True
    _letras(editor, "a")
    editor.evento_fisico("separador", " ")
    assert dic.sugerir("a", 5) == []
    dic.fechar()


def test_escrita_virtual_continua_a_enviar_teclas():
    saida = Registo()
    editor = Editor(saida, Dicionario({}))
    editor.texto("ola")
    assert ("escrever", "O") in saida.envios or ("escrever", "o") in saida.envios


def test_evento_fisico_apaga_a_palavra_virtual():
    editor = Editor(Registo(), Dicionario({"casa": 5}))
    editor.texto("ca")
    editor.evento_fisico("letra", "s")
    assert editor.palavra == ""


# --- politica: e uma configuracao --------------------------------------------------

class _Saida:
    def escrever(self, texto):
        pass

    def tecla(self, nome):
        pass


def _app(tmp_path, perfil, pins=()):
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    fila = list(pins)
    return Aplicacao(
        saida=_Saida(), repo=repo, perfil=perfil,
        pedir_pin=lambda: fila.pop(0) if fila else None,
        pastas_layouts=[DADOS_PROJETO / "layouts"],
        pastas_temas=[DADOS_PROJETO / "temas"],
        pasta_temas_utilizador=tmp_path / "temas",
        pasta_layouts_utilizador=tmp_path / "layouts",
    )


def test_teclado_fisico_desligado_por_omissao(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    assert app.preferencias_fisico() == {"ativo": False, "aprender": False}


def test_aprender_so_vale_se_ativo(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    app.definir_teclado_fisico(False, True)
    assert app.preferencias_fisico()["aprender"] is False


def test_ativar_em_perfil_supervisionado_exige_codigo(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="segredo")
    app = _app(tmp_path, perfil, pins=[None, None, None])
    assert app.definir_teclado_fisico(True, False) is False
    assert app.preferencias_fisico()["ativo"] is False


def test_ativar_com_codigo_correto(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="segredo")
    app = _app(tmp_path, perfil, pins=["segredo"])
    assert app.definir_teclado_fisico(True, True) is True
    assert app.preferencias_fisico() == {"ativo": True, "aprender": True}


# --- captura real (Windows): so ciclo de vida, sem teclas reais --------------------

@pytest.mark.skipif(sys.platform != "win32", reason="gancho do Windows")
def test_gancho_liga_e_desliga_sem_erros():
    from teclado.core.captura_teclado import CapturaTeclado
    captura = CapturaTeclado(lambda ev: None)
    captura.ligar()
    assert captura.ativo
    captura.desligar()
    assert not captura.ativo
