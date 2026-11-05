from teclado.core.comandos_voz import segmentar
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


# --- segmentacao -----------------------------------------------------------

def test_enter_sozinho_e_comando():
    assert segmentar("enter") == [("tecla", "enter")]


def test_muda_de_linha_e_comando():
    assert segmentar("muda de linha") == [("tecla", "enter")]


def test_muda_de_linha_com_pontuacao_do_reconhecedor():
    assert segmentar("Muda de linha.") == [("tecla", "enter")]


def test_comando_no_meio_da_frase():
    assert segmentar("olá tudo bem muda de linha obrigado") == [
        ("texto", "olá tudo bem"), ("tecla", "enter"), ("texto", "obrigado"),
    ]


def test_ponto_final_vira_simbolo_com_espaco_depois():
    assert segmentar("ola ponto final tudo bem") == [
        ("texto", "ola"), ("simbolo", "."), ("texto", " tudo bem"),
    ]


def test_ponto_de_interrogacao_sem_acento():
    assert segmentar("queres ir ponto de interrogacao") == [
        ("texto", "queres ir"), ("simbolo", "?"),
    ]


def test_ponto_de_interrogacao_com_acento_do_reconhecedor():
    assert segmentar("queres ir ponto de interrogação") == [
        ("texto", "queres ir"), ("simbolo", "?"),
    ]


def test_apagar_so_e_comando_quando_isolado():
    assert segmentar("apagar") == [("tecla", "backspace")]
    assert segmentar("vou apagar a luz") == [("texto", "vou apagar a luz")]


def test_apaga_palavra_isolado():
    assert segmentar("apaga palavra") == [("acao", "apagar_palavra")]


def test_ler_selecao_com_acento():
    assert segmentar("ler seleção") == [("acao", "ler_selecao")]


def test_frase_normal_fica_como_texto():
    assert segmentar("hoje vou ao mercado") == [("texto", "hoje vou ao mercado")]


def test_texto_vazio():
    assert segmentar("") == []


# --- editor -----------------------------------------------------------------

def test_ditado_com_enter_envia_tecla_de_enter():
    saida = Registo()
    editor = Editor(saida, Dicionario({}))
    editor.ditar("bom dia enter ")
    assert ("colar", "Bom dia") in saida.eventos
    assert ("tecla", "enter") in saida.eventos
    assert saida.eventos.index(("colar", "Bom dia")) < saida.eventos.index(("tecla", "enter"))


def test_ditado_so_enter_nao_cola_nada():
    saida = Registo()
    editor = Editor(saida, Dicionario({}))
    editor.ditar("enter")
    assert saida.eventos == [("tecla", "enter")]


def test_ponto_final_depois_de_texto_nao_tem_espaco_antes():
    saida = Registo()
    editor = Editor(saida, Dicionario({}))
    editor.ditar("ola ponto final tudo bem ")
    # Ordem real de envio: texto colado, pontuacao escrita, texto colado.
    sequencia = [v for t, v in saida.eventos if t in ("colar", "escrever")]
    assert "".join(sequencia) == "Ola. Tudo bem "
