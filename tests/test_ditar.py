from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor


class Registo:
    def __init__(self):
        self.eventos = []

    def escrever(self, texto):
        self.eventos.append(("escrever", texto))

    def tecla(self, nome):
        self.eventos.append(("tecla", nome))

    def sequencia(self, acoes):
        self.eventos.extend(acoes)

    def atalho(self, nome):
        self.eventos.append(("atalho", nome))

    def enviar_atalho(self, passo):
        self.eventos.append(("combo", passo))

    def colar_texto(self, texto):
        self.eventos.append(("colar", texto))

    def ler_selecao(self):
        return ""


def test_ditado_envia_um_unico_bloco_colado():
    saida = Registo()
    editor = Editor(saida, Dicionario({}))
    editor.ditar("bom dia a todos ")
    colados = [v for t, v in saida.eventos if t == "colar"]
    assert colados == ["Bom dia a todos "]
    assert not any(t == "escrever" for t, _ in saida.eventos)


def test_ditado_mantem_maiuscula_de_inicio_de_frase_e_pontuacao():
    saida = Registo()
    editor = Editor(saida, Dicionario({}))
    editor.ditar("ola. tudo bem? ")
    colados = "".join(v for t, v in saida.eventos if t == "colar")
    assert colados == "Ola. Tudo bem? "


def test_ditado_com_tecla_pelo_meio_envia_o_texto_antes():
    saida = Registo()
    editor = Editor(saida, Dicionario({}))
    editor.ditar("ola ")
    editor.tecla("enter")
    ordem = [t for t, _ in saida.eventos]
    assert ordem.index("colar") < ordem.index("tecla")


def test_ditado_atualiza_o_estado_da_frase():
    saida = Registo()
    lidos = []
    editor = Editor(saida, Dicionario({}))
    editor.falar_frase = True
    editor.ligar_voz(lidos.append)
    editor.ditar("sim. ")
    assert lidos == ["Sim."]


def test_ditado_depois_de_escrita_normal_continua_bem():
    saida = Registo()
    editor = Editor(saida, Dicionario({}))
    editor.texto("ola")
    editor.ditar(" tudo ")
    assert saida.eventos[-1][0] == "colar"
    assert editor._saida is saida  # a saida real foi reposta
