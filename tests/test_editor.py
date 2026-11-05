from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor


class Registo:
    """Saida falsa: guarda tudo o que seria enviado para a aplicacao."""

    def __init__(self):
        self.eventos = []

    def escrever(self, texto):
        self.eventos.append(("texto", texto))

    def tecla(self, nome):
        self.eventos.append(("tecla", nome))

    def sequencia(self, acoes):
        for tipo, valor in acoes:
            self.eventos.append((tipo, valor))

    def escrito(self):
        return "".join(v for t, v in self.eventos if t == "texto")


def _editor(base=None, pessoal=None, maximo=5):
    registo = Registo()
    dic = Dicionario(base or {"casa": 10, "cama": 5, "cair": 20, "mais": 50, "gato": 3}, pessoal)
    return Editor(registo, dic, max_sugestoes=maximo), registo


def test_primeira_letra_do_texto_e_maiuscula():
    editor, registo = _editor()
    editor.texto("ola")
    assert registo.escrito() == "Ola"


def test_maiuscula_depois_de_ponto_e_espaco():
    editor, registo = _editor()
    editor.texto("ola. ")
    editor.texto("tudo")
    assert registo.escrito() == "Ola. Tudo"


def test_maiuscula_depois_de_exclamacao_e_interrogacao():
    editor, registo = _editor()
    editor.texto("sim! ")
    editor.texto("nao? ")
    editor.texto("quero")
    assert registo.escrito() == "Sim! Nao? Quero"


def test_enter_inicia_nova_frase():
    editor, registo = _editor()
    editor.texto("ola")
    editor.tecla("enter")
    editor.texto("bom")
    assert registo.escrito() == "Ola" + "Bom"


def test_virgula_nao_inicia_frase():
    editor, registo = _editor()
    editor.texto("sim, ")
    editor.texto("eu")
    assert registo.escrito() == "Sim, eu"


def test_shift_de_um_toque_so_afeta_a_proxima_letra():
    editor, registo = _editor()
    editor.texto("sim ")
    editor.modificador("shift")
    editor.texto("j")
    editor.texto("oao")
    assert registo.escrito() == "Sim Joao"


def test_shift_ativo_fica_marcado_ate_a_letra_seguinte():
    editor, _ = _editor()
    editor.texto("sim ")
    editor.modificador("shift")
    assert editor.shift is True
    editor.texto("a")
    assert editor.shift is False


def test_backspace_apaga_no_editor_e_na_aplicacao():
    editor, registo = _editor()
    editor.texto("ca")
    editor.tecla("backspace")
    assert editor.palavra == "C"
    assert ("tecla", "backspace") in registo.eventos


def test_sugestoes_aparecem_com_o_prefixo():
    editor, _ = _editor()
    editor.texto("ca")
    assert editor.sugestoes[0] == "cair"


def test_sem_prefixo_nao_ha_sugestoes():
    editor, _ = _editor()
    editor.texto("sim ")
    assert editor.sugestoes == []


def test_maximo_de_sugestoes_respeitado():
    editor, _ = _editor(maximo=1)
    editor.texto("c")
    assert len(editor.sugestoes) == 1


def test_usar_sugestao_apaga_prefixo_e_escreve_palavra():
    editor, registo = _editor()
    editor.texto("sim ")
    editor.texto("ca")
    registo.eventos.clear()
    editor.usar_sugestao(1)  # casa
    assert registo.eventos == [("tecla", "backspace"), ("tecla", "backspace"), ("texto", "casa ")]


def test_usar_sugestao_respeita_maiuscula_do_prefixo():
    editor, registo = _editor()
    editor.texto("Ca")
    registo.eventos.clear()
    editor.usar_sugestao(1)  # casa -> Casa
    assert ("texto", "Casa ") in registo.eventos


def test_usar_sugestao_inexistente_nao_faz_nada():
    editor, registo = _editor()
    editor.texto("ca")
    registo.eventos.clear()
    editor.usar_sugestao(9)
    assert registo.eventos == []


def test_palavra_escrita_fica_aprendida(tmp_path):
    dic = Dicionario({"casa": 10}, pessoal_caminho=tmp_path / "uso.sqlite")
    registo = Registo()
    editor = Editor(registo, dic)
    editor.texto("gato ")
    assert dic.sugerir("ga", 5) == ["gato"]
    dic.fechar()


def test_nome_proprio_escrito_a_meio_de_frase_fica_com_maiuscula(tmp_path):
    dic = Dicionario({"mais": 50}, pessoal_caminho=tmp_path / "uso.sqlite")
    registo = Registo()
    editor = Editor(registo, dic)
    editor.texto("ola ")
    editor.modificador("shift")
    editor.texto("maria ")
    assert dic.sugerir("ma", 5)[0] == "Maria"
    dic.fechar()


def test_tecla_de_navegacao_limpa_o_prefixo():
    editor, _ = _editor()
    editor.texto("ca")
    editor.tecla("seta_esq")
    assert editor.palavra == ""
    assert editor.sugestoes == []


def test_espaco_fecha_palavra_e_limpa_sugestoes():
    editor, _ = _editor()
    editor.texto("ca")
    editor.tecla("espaco")
    assert editor.palavra == ""
    assert editor.sugestoes == []

def test_pontuacao_apos_sugestao_apaga_o_espaco_automatico():
    editor, registo = _editor()
    editor.texto("sim ")
    editor.texto("ca")
    editor.usar_sugestao(1)  # casa
    registo.eventos.clear()
    editor.texto(".")
    assert registo.eventos == [("tecla", "backspace"), ("texto", ".")]


def test_espaco_apos_sugestao_nao_duplica():
    editor, registo = _editor()
    editor.texto("sim ")
    editor.texto("ca")
    editor.usar_sugestao(1)
    registo.eventos.clear()
    editor.texto(" ")
    assert registo.eventos == []


def test_letra_apos_sugestao_nao_apaga_espaco():
    editor, registo = _editor()
    editor.texto("sim ")
    editor.texto("ca")
    editor.usar_sugestao(1)
    registo.eventos.clear()
    editor.texto("m")
    assert registo.eventos == [("texto", "m")]

def test_sugestao_usa_sequencia_de_apagar_e_escrever():
    class SaidaAtomica:
        def __init__(self):
            self.envios = []
        def escrever(self, texto):
            self.envios.append(("escrever", texto))
        def tecla(self, nome):
            self.envios.append(("tecla", nome))
        def sequencia(self, acoes):
            self.envios.append(("sequencia", list(acoes)))

    saida = SaidaAtomica()
    editor = Editor(saida, Dicionario({"também": 9, "tambor": 1}))
    editor.texto("tamb")
    saida.envios.clear()
    editor.usar_sugestao(0)
    assert saida.envios == [("sequencia", [
        ("tecla", "backspace"), ("tecla", "backspace"),
        ("tecla", "backspace"), ("tecla", "backspace"),
        ("texto", "Também "),
    ])]


def test_palavra_acentuada_inteira_no_mesmo_lote():
    from teclado.core.saida.windows import eventos_para_texto
    eventos = eventos_para_texto("Também ")
    # Cada caracter gera um par down/up; o acento nao pode ficar separado.
    assert len(eventos) == 2 * len("Também ")
