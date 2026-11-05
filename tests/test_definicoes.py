import pytest
from PySide6.QtWidgets import QApplication

from teclado.core.aplicacao import Aplicacao
from teclado.core.dicionario import Dicionario
from teclado.core.editor import MAX_SUGESTOES, Editor
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.ui.definicoes import ACAO_EDITAR, ACAO_PERSONALIZAR, DialogoDefinicoes


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _Saida:
    def escrever(self, texto):
        pass

    def tecla(self, nome):
        pass


def _dialogo(max_sugestoes=5, auto_iniciar=False):
    return DialogoDefinicoes(
        None,
        ["QWERTY", "Vogais"], "QWERTY",
        ["Claro", "Escuro"], "Claro",
        max_sugestoes,
        auto_iniciar=auto_iniciar,
    )


def test_dialogo_devolve_valores_atuais(app):
    dialogo = _dialogo(7)
    assert dialogo.escolhas() == {"layout": "QWERTY", "tema": "Claro", "idioma": "pt-PT", "max_sugestoes": 7,
                                  "acao": "", "auto_iniciar": False, "arranque_sistema": False,
                                  "verificar_atualizacoes": True}


def test_dialogo_mostra_a_opcao_telemovel_guardada(app):
    dialogo = _dialogo(auto_iniciar=True)
    assert dialogo.escolhas()["auto_iniciar"] is True
    dialogo.close()
    dialogo.close()


def test_dialogo_muda_teclado_e_tema(app):
    dialogo = _dialogo()
    dialogo._layout.setCurrentText("Vogais")
    dialogo._tema.setCurrentText("Escuro")
    escolhas = dialogo.escolhas()
    assert escolhas["layout"] == "Vogais" and escolhas["tema"] == "Escuro"
    dialogo.close()


def test_atalho_editar_marca_acao(app):
    dialogo = _dialogo()
    dialogo._acionar(ACAO_EDITAR)
    assert dialogo.escolhas()["acao"] == ACAO_EDITAR


def test_atalho_personalizar_marca_acao(app):
    dialogo = _dialogo()
    dialogo._acionar(ACAO_PERSONALIZAR)
    assert dialogo.escolhas()["acao"] == ACAO_PERSONALIZAR


def test_numero_de_sugestoes_limitado_a_1_e_10(app):
    dialogo = _dialogo()
    dialogo._max.setValue(10)
    assert dialogo.escolhas()["max_sugestoes"] == 10
    assert dialogo._max.maximum() == MAX_SUGESTOES
    assert dialogo._max.minimum() == 1
    dialogo.close()


def test_editor_altera_numero_de_sugestoes():
    editor = Editor(_Saida(), Dicionario({"casa": 1, "cama": 1, "cair": 1, "caso": 1}), max_sugestoes=5)
    editor.definir_max_sugestoes(2)
    editor.texto("ca")
    assert len(editor.sugestoes) == 2
    assert editor.max_sugestoes == 2


def _app_com_perfil(tmp_path, perfil):
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    return Aplicacao(
        saida=_Saida(),
        repo=repo,
        perfil=perfil,
        pedir_pin=lambda: None,
        pastas_layouts=[DADOS_PROJETO / "layouts"],
        pastas_temas=[DADOS_PROJETO / "temas"],
        pasta_temas_utilizador=tmp_path / "temas",
        pasta_layouts_utilizador=tmp_path / "layouts",
    ), repo


def test_definir_max_sugestoes_guarda_no_perfil(tmp_path):
    app, repo = _app_com_perfil(tmp_path, criar_perfil("Adulto", supervisionado=False))
    assert app.definir_max_sugestoes(8) is True
    assert repo.carregar(app.perfil.id).preferencias["max_sugestoes"] == 8


def test_definir_max_sugestoes_bloqueado_em_perfil_supervisionado(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    app, repo = _app_com_perfil(tmp_path, perfil)
    assert app.definir_max_sugestoes(8) is False
    assert "max_sugestoes" not in repo.carregar(app.perfil.id).preferencias


def test_definir_max_sugestoes_com_limite(tmp_path):
    app, _ = _app_com_perfil(tmp_path, criar_perfil("Adulto", supervisionado=False))
    app.definir_max_sugestoes(99)
    assert app.perfil.preferencias["max_sugestoes"] == 10
