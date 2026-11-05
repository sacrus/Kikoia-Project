import sys

import pytest

from teclado.core.aplicacao import Aplicacao
from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.layout import LayoutInvalido, NAVEGAR_ANTERIOR, validar_layout
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.core.saida import ACOES, ACOES_EDICAO
from teclado.core.layout import descobrir_layouts
from teclado.ui.editor_layout import atalhos_de, simbolos_disponiveis


class SaidaFalsa:
    def __init__(self, selecao=""):
        self.eventos = []
        self.selecao = selecao

    def escrever(self, texto):
        self.eventos.append(("texto", texto))

    def tecla(self, nome):
        self.eventos.append(("tecla", nome))

    def sequencia(self, acoes):
        self.eventos.extend(acoes)

    def atalho(self, nome):
        self.eventos.append(("atalho", nome))

    def ler_selecao(self):
        return self.selecao


# --- validacao ---------------------------------------------------------------

def _layout(acao, atalho=None):
    dados = {
        "nome": "Teste", "idioma": "pt-PT",
        "linhas": [[{"rotulo": "x", "acao": acao}]],
    }
    if atalho is not None:
        dados["atalho"] = atalho
    return dados


def test_acao_de_edicao_valida():
    layout = validar_layout(_layout({"tipo": "acao", "valor": "apagar_palavra"}))
    assert layout.linhas[0][0].acao.tipo == "acao"


def test_acao_de_edicao_desconhecida_rejeitada():
    with pytest.raises(LayoutInvalido):
        validar_layout(_layout({"tipo": "acao", "valor": "formatar_disco"}))


def test_navegar_aceita_nome_de_teclado_longo():
    layout = validar_layout(_layout({"tipo": "navegar", "valor": "Numérico"}))
    assert layout.linhas[0][0].acao.valor == "Numérico"


def test_navegar_para_anterior_valido():
    validar_layout(_layout({"tipo": "navegar", "valor": NAVEGAR_ANTERIOR}))


def test_atalho_do_teclado_e_lido():
    layout = validar_layout(_layout({"tipo": "texto", "valor": "a"}, atalho={"rotulo": "Números"}))
    assert layout.atalho == "Números"


def test_teclado_sem_atalho_tem_none():
    layout = validar_layout(_layout({"tipo": "texto", "valor": "a"}))
    assert layout.atalho is None


def test_todas_as_acoes_de_edicao_tem_sequencia():
    for nome in ACOES_EDICAO:
        assert ACOES_EDICAO[nome]
    assert "ler_selecao" in ACOES


# --- sequencias de teclas (Windows) -----------------------------------------

@pytest.mark.skipif(sys.platform != "win32", reason="SendInput e so Windows")
def test_passo_com_modificadores_prime_e_liberta_por_ordem():
    from teclado.core.saida.windows import eventos_para_passo
    eventos = eventos_para_passo("ctrl+shift+left")
    # 3 primeiros (ctrl, shift, left) a premir e depois a libertar left, shift, ctrl.
    assert len(eventos) == 6
    assert eventos[0].u.ki.wVk == 0x11 and eventos[1].u.ki.wVk == 0x10
    assert eventos[-1].u.ki.wVk == 0x11


@pytest.mark.skipif(sys.platform != "win32", reason="SendInput e so Windows")
def test_tecla_desconhecida_num_atalho_rejeitada():
    from teclado.core.saida.windows import eventos_para_passo
    with pytest.raises(ValueError):
        eventos_para_passo("ctrl+xyz")


# --- editor -----------------------------------------------------------------

def test_apagar_palavra_envia_a_acao_e_limpa_prefixo():
    saida = SaidaFalsa()
    editor = Editor(saida, Dicionario({"casa": 1}))
    editor.texto("ca")
    editor.acao("apagar_palavra")
    assert ("atalho", "apagar_palavra") in saida.eventos
    assert editor.palavra == ""
    assert editor.sugestoes == []


def test_selecionar_linha_nao_aprende_palavra_parcial(tmp_path):
    from teclado.core.dicionario import Dicionario as D
    dic = D({}, pessoal_caminho=tmp_path / "uso.sqlite")
    editor = Editor(SaidaFalsa(), dic)
    editor.texto("pal")
    editor.acao("selecionar_linha")
    assert dic.sugerir("pa", 5) == []
    dic.fechar()


def test_ler_selecao_le_o_texto_selecionado():
    lidos = []
    editor = Editor(SaidaFalsa(selecao="bom dia"), Dicionario({}))
    editor.ligar_leitura_selecao(lidos.append)
    editor.acao("ler_selecao")
    assert lidos == ["bom dia"]


def test_ler_selecao_sem_texto_nao_le_nada():
    lidos = []
    editor = Editor(SaidaFalsa(selecao=""), Dicionario({}))
    editor.ligar_leitura_selecao(lidos.append)
    editor.acao("ler_selecao")
    assert lidos == []


def test_acao_desconhecida_no_editor_rejeitada():
    editor = Editor(SaidaFalsa(), Dicionario({}))
    with pytest.raises(ValueError):
        editor.acao("formatar_disco")


# --- navegacao entre teclados -------------------------------------------------

def _app(tmp_path, perfil):
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    return Aplicacao(
        saida=SaidaFalsa(), repo=repo, perfil=perfil,
        pedir_pin=lambda: None,
        pastas_layouts=[DADOS_PROJETO / "layouts"],
        pastas_temas=[DADOS_PROJETO / "temas"],
        pasta_temas_utilizador=tmp_path / "temas",
        pasta_layouts_utilizador=tmp_path / "layouts",
    )


def test_navegar_para_outro_teclado(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    assert app.navegar_para("Numérico").nome == "Numérico"
    assert app.layout.nome == "Numérico"


def test_navegar_nao_guarda_no_perfil(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    app.navegar_para("Numérico")
    assert app.perfil.preferencias.get("layout") is None


def test_voltar_regressa_ao_teclado_anterior(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    inicial = app.layout.nome
    app.navegar_para("Numérico")
    app.navegar_para("Vogais")
    assert app.voltar_teclado().nome == "Numérico"
    assert app.voltar_teclado().nome == inicial


def test_voltar_sem_historico_nao_faz_nada(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    inicial = app.layout.nome
    assert app.voltar_teclado() is None
    assert app.layout.nome == inicial


def test_navegar_nao_pede_codigo_em_perfil_supervisionado(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    app = _app(tmp_path, perfil)
    assert app.navegar_para("Numérico") is not None
    assert app.layout.nome == "Numérico"


def test_navegar_para_teclado_inexistente_nao_faz_nada(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    inicial = app.layout.nome
    assert app.navegar_para("Nao existe") is None
    assert app.layout.nome == inicial


# --- editor visual: paleta e atalhos ---------------------------------------------

def test_paleta_inclui_acoes_de_edicao():
    itens = simbolos_disponiveis()
    acoes = {i["acao"]["valor"] for i in itens if i["acao"]["tipo"] == "acao"}
    assert {"apagar_palavra", "apagar_linha", "selecionar_palavra", "selecionar_linha", "ler_selecao"} <= acoes


def test_paleta_inclui_voltar_e_atalhos_de_outros_teclados():
    itens = simbolos_disponiveis([("Números", "Numérico")])
    navegar = [i for i in itens if i["acao"]["tipo"] == "navegar"]
    assert {i["rotulo"] for i in navegar} == {"Números", "← Voltar"}
    assert {i["acao"]["valor"] for i in navegar} == {"Numérico", NAVEGAR_ANTERIOR}


def test_atalhos_de_nao_inclui_o_proprio_teclado():
    layouts = descobrir_layouts([DADOS_PROJETO / "layouts"])
    layouts["Numérico"] = layouts["Numérico"].__class__(
        nome="Numérico", idioma="pt-PT", linhas=layouts["Numérico"].linhas, atalho="Números"
    )
    assert atalhos_de(layouts, excluir="Numérico") == []
    assert atalhos_de(layouts, excluir="QWERTY") == [("Números", "Numérico")]
