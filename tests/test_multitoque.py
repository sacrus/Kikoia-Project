from teclado.core.dicionario import Dicionario
from teclado.core.editor import MULTITOQUE_INTERVALO, Editor
from teclado.core.layout import LayoutInvalido, validar_layout


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
        """Texto final simulando backspaces."""
        saida = []
        for tipo, valor in self.eventos:
            if tipo == "texto":
                saida.append(valor)
            elif tipo == "tecla" and valor == "backspace" and saida:
                ultimo = saida.pop()
                if len(ultimo) > 1:
                    saida.append(ultimo[:-1])
        return "".join(saida)


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def avancar(self, s):
        self.t += s


def _editor():
    registo = Registo()
    relogio = Relogio()
    editor = Editor(registo, Dicionario({}), relogio=relogio)
    return editor, registo, relogio


def test_um_toque_escreve_a_primeira_letra():
    editor, registo, _ = _editor()
    editor.multitoque(1, "abc")
    assert registo.escrito() == "A"


def test_toques_seguidos_percorrem_as_letras():
    editor, registo, relogio = _editor()
    editor.multitoque(1, "abc")
    relogio.avancar(0.3)
    editor.multitoque(1, "abc")
    assert registo.escrito() == "B"
    relogio.avancar(0.3)
    editor.multitoque(1, "abc")
    assert registo.escrito() == "C"
    relogio.avancar(0.3)
    editor.multitoque(1, "abc")
    assert registo.escrito() == "A"  # volta ao inicio


def test_pausa_longa_comeca_nova_letra():
    editor, registo, relogio = _editor()
    editor.multitoque(1, "abc")
    relogio.avancar(MULTITOQUE_INTERVALO + 0.5)
    editor.multitoque(1, "abc")
    # Segunda palavra da frase: a letra nao sai em maiuscula.
    assert registo.escrito() == "Aa"


def test_tecla_diferente_comeca_nova_letra():
    editor, registo, relogio = _editor()
    editor.multitoque(1, "abc")
    relogio.avancar(0.2)
    editor.multitoque(2, "def")
    assert registo.escrito() == "Ad"


def test_outra_tecla_pelo_meio_interrompe_o_ciclo():
    editor, registo, relogio = _editor()
    editor.multitoque(1, "abc")
    relogio.avancar(0.2)
    editor.texto("x")
    relogio.avancar(0.2)
    editor.multitoque(1, "abc")
    assert registo.escrito() == "Axa"


def test_inicio_de_frase_mantem_maiuscula_no_ciclo():
    editor, registo, relogio = _editor()
    editor.multitoque(1, "abc")
    relogio.avancar(0.2)
    editor.multitoque(1, "abc")
    # Primeira letra do texto: "B" (de "b") ja sai em maiuscula.
    assert registo.escrito() == "B"


def test_palavra_em_curso_acompanha_o_ciclo():
    editor, _, relogio = _editor()
    editor.texto("ca")
    editor.multitoque(2, "abc")
    relogio.avancar(0.2)
    editor.multitoque(2, "abc")
    # "Ca" escrito; o toque repetido de "abc" acrescenta "a" e depois troca para "b".
    assert editor.palavra == "Cab"


def test_multitoque_com_acento_pendente_escoa_o_acento():
    editor, registo, _ = _editor()
    editor.acento("agudo")
    editor.multitoque(1, "abc")
    assert registo.escrito().startswith("\u00b4")


def test_layout_rejeita_multitoque_com_uma_so_letra():
    dados = {
        "nome": "Teste", "idioma": "pt-PT",
        "linhas": [[{"rotulo": "1", "acao": {"tipo": "multitoque", "valor": "a"}}]],
    }
    try:
        validar_layout(dados)
    except LayoutInvalido:
        return
    raise AssertionError("devia rejeitar")


def test_layout_minimal_valida():
    from teclado.core.layout import descobrir_layouts
    from teclado.core.paths import DADOS_PROJETO
    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["Minimal"]
    assert layout.total_teclas >= 12
