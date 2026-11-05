import json
import sys

import pytest
from PySide6.QtWidgets import QApplication

from teclado.core import comandos as cmd
from teclado.core.aplicacao import Aplicacao
from teclado.core.comandos import Comando, ComandoErro, carregar, gravar, validar
from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.ia import IAErro, gerar_pacote
from teclado.core.layout import Acao, LayoutInvalido, Tecla, validar_layout
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.core.saida import ACOES
from teclado.gateway.protocolo import ProtocoloErro, codificar
from teclado.ui.editor_layout import simbolos_disponiveis


class _Saida:
    def escrever(self, t):
        pass

    def tecla(self, n):
        pass

    def sequencia(self, a):
        pass

    def atalho(self, n):
        pass

    def enviar_atalho(self, p):
        pass

    def colar_texto(self, t):
        pass

    def ler_selecao(self):
        return ""


# --- validacao e ficheiro -------------------------------------------------------

def test_validar_rejeita_nome_vazio_e_quebra_de_linha():
    with pytest.raises(ValueError):
        validar("  ", "calc")
    with pytest.raises(ValueError):
        validar("Calc", "calc\nrm")


def test_ficheiro_ida_e_volta(tmp_path):
    dados = {"c1": Comando("c1", "Bloco", "notepad")}
    gravar(tmp_path, dados)
    assert carregar(tmp_path) == dados


def test_ficheiro_com_entradas_invalidas_ignora_as_invalidas(tmp_path):
    (tmp_path / "comandos.json").write_text(json.dumps([
        {"id": "c1", "rotulo": "Ok", "comando": "calc"},
        {"id": "../x", "rotulo": "Mau", "comando": "calc"},
        {"id": "c2", "rotulo": "", "comando": "calc"},
    ]), encoding="utf-8")
    assert list(carregar(tmp_path)) == ["c1"]


def test_executar_chama_o_programa(monkeypatch):
    chamadas = []
    monkeypatch.setattr(cmd.subprocess, "Popen", lambda *a, **k: chamadas.append(a))
    cmd.executar("calc")
    assert chamadas and chamadas[0][0] in ("calc", ["calc"])


def test_executar_erro_do_sistema_vira_comando_erro(monkeypatch):
    def falha(*a, **k):
        raise FileNotFoundError("nao existe")
    monkeypatch.setattr(cmd.subprocess, "Popen", falha)
    with pytest.raises(ComandoErro):
        cmd.executar("programa-inexistente")


@pytest.mark.skipif(sys.platform != "win32", reason="abre ficheiros com o Windows")
def test_ficheiro_existente_abre_com_o_sistema(monkeypatch, tmp_path):
    abertos = []
    ficheiro = tmp_path / "nota.txt"
    ficheiro.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cmd.os, "startfile", lambda p: abertos.append(p), raising=False)
    cmd.executar(f'"{ficheiro}"')
    assert abertos == [str(ficheiro)]


# --- teclas tipo comando no layout e no protocolo -------------------------------

def _layout_com(acao):
    return {"nome": "T", "idioma": "pt-PT", "linhas": [[{"rotulo": "X", "acao": acao}]]}


def test_layout_aceita_tecla_de_comando():
    validar_layout(_layout_com({"tipo": "comando", "valor": "c1a2b3c4"}))


def test_layout_recusa_identificador_de_comando_invalido():
    with pytest.raises(LayoutInvalido):
        validar_layout(_layout_com({"tipo": "comando", "valor": "../../x"}))


def test_protocolo_aceita_acao_comando_por_id_apenas():
    codificar(b"k" * 32, "acao", "a", 0, {"acao": {"tipo": "comando", "valor": "c1a2b3c4"}})
    with pytest.raises(ProtocoloErro):
        codificar(b"k" * 32, "acao", "a", 0, {"acao": {"tipo": "comando", "valor": "calc; rm -rf"}})


def test_acoes_de_janela_continuam_fora_de_comandos():
    assert "comando" not in ACOES


def test_palete_do_editor_inclui_teclas_de_comando():
    c = Comando("c1", "Bloco", "notepad")
    itens = simbolos_disponiveis((), [c])
    assert any(i["acao"] == {"tipo": "comando", "valor": "c1"} and i["rotulo"] == "Bloco" for i in itens)


# --- controlador: politica e execucao ---------------------------------------------

class _Prompt:
    def __init__(self, pins=()):
        self.pins = list(pins)

    def __call__(self):
        return self.pins.pop(0) if self.pins else None


def _app(tmp_path, perfil, pins=()):
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    return Aplicacao(
        saida=_Saida(), repo=repo, perfil=perfil, pedir_pin=_Prompt(pins),
        pastas_layouts=[DADOS_PROJETO / "layouts"], pastas_temas=[DADOS_PROJETO / "temas"],
        pasta_temas_utilizador=tmp_path / "temas", pasta_layouts_utilizador=tmp_path / "layouts",
        pasta_comandos=tmp_path,
    )


def test_guardar_comando_em_perfil_livre(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    novo = app.guardar_comando(None, "Bloco", "notepad")
    assert novo is not None and novo.id.startswith("c")
    assert carregar(tmp_path)[novo.id].comando == "notepad"


def test_guardar_comando_supervisionado_sem_codigo_nao_grava(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="segredo")
    app = _app(tmp_path, perfil, pins=[None])
    assert app.guardar_comando(None, "Bloco", "notepad") is None
    assert carregar(tmp_path) == {}


def test_executar_comando_desconhecido_erro(tmp_path):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    with pytest.raises(ComandoErro):
        app.executar_comando("c00000000")


def test_executar_comando_guardado_chama_o_programa(tmp_path, monkeypatch):
    app = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    novo = app.guardar_comando(None, "Calc", "calc")
    chamados = []
    monkeypatch.setattr("teclado.core.aplicacao.executar", chamados.append)
    app.executar_comando(novo.id)
    assert chamados == ["calc"]


# --- IA: comandos propostos ----------------------------------------------------------

class _Cliente:
    def __init__(self, resposta):
        self.resposta = resposta

    def completar(self, s, p):
        return self.resposta


def _resposta(comandos, tecla_id):
    return json.dumps({
        "nome": "Escritorio",
        "linhas": [[
            {"rotulo": "Bloco", "acao": {"tipo": "comando", "valor": tecla_id}},
            {"rotulo": "A", "acao": {"tipo": "texto", "valor": "a"}},
        ]],
        "comandos": comandos,
    })


def test_ia_reapontar_comandos_para_ids_novos():
    modelo, comandos = gerar_pacote(
        "tecla para o bloco de notas",
        _Cliente(_resposta([{"id": "c1", "rotulo": "Bloco", "comando": "notepad"}], "c1")),
    )
    assert len(comandos) == 1
    novo_id = comandos[0]["id"]
    assert novo_id != "c1"
    assert modelo["linhas"][0][0]["acao"]["valor"] == novo_id


def test_ia_tecla_sem_comando_definido_e_recusada():
    with pytest.raises(IAErro):
        gerar_pacote("x", _Cliente(_resposta([], "c9")))


def test_ia_comando_perigoso_demasiado_longo_e_recusado():
    with pytest.raises(IAErro):
        gerar_pacote("x", _Cliente(_resposta([{"id": "c1", "rotulo": "x", "comando": "a" * 400}], "c1")))


# --- janela: tecla de comando chama o callback ---------------------------------------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_tecla_de_comando_na_janela_chama_o_callback(qapp):
    from teclado.core.layout import Layout
    from teclado.core.tema import descobrir_temas
    from teclado.ui.janela import JanelaTeclado
    from PySide6.QtWidgets import QPushButton

    layout = Layout("T", "pt-PT", ((Tecla("Bloco", Acao("comando", "c1"), 1.0),),))
    tema = descobrir_temas([DADOS_PROJETO / "temas"])["Claro"]
    chamadas = []
    janela = JanelaTeclado(Editor(_Saida(), Dicionario({})), layout, tema,
                           ancorar_fundo=False, ao_comando=chamadas.append)
    botao = next(b for b in janela.findChildren(QPushButton) if b.text() == "Bloco")
    botao.click()
    assert chamadas == ["c1"]
    janela.close()
