from teclado.core.aplicacao import Aplicacao
from teclado.core.comandos import Comando
from teclado.core.layout import Acao, Layout, Tecla
from teclado.core.layout_editor import remover_teclas_de_comando, rotular_comandos, usa_comando
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil


def _layout(*teclas):
    return Layout("T", "pt-PT", (tuple(teclas),))


def test_rotular_comandos_usa_o_nome_atual_do_comando():
    tecla = Tecla("Antigo", Acao("comando", "c1"), 1.0)
    atual = rotular_comandos(_layout(tecla), {"c1": Comando("c1", "Novo", "notepad")})
    assert atual.linhas[0][0].rotulo == "Novo"
    assert tecla.rotulo == "Antigo"


def test_rotular_comandos_mantem_comando_apagado_e_outras_teclas():
    comando = Tecla("Antigo", Acao("comando", "c9"), 1.0)
    letra = Tecla("a", Acao("texto", "a"), 1.0)
    atual = rotular_comandos(_layout(comando, letra), {})
    assert [t.rotulo for t in atual.linhas[0]] == ["Antigo", "a"]


def test_remover_teclas_de_comando_do_modelo():
    modelo = {"nome": "T", "idioma": "pt-PT", "linhas": [[
        {"rotulo": "x", "acao": {"tipo": "comando", "valor": "c1"}, "largura": 1.0},
        {"rotulo": "a", "acao": {"tipo": "texto", "valor": "a"}, "largura": 1.0},
    ]]}
    assert remover_teclas_de_comando(modelo, "c1") == 1
    assert [t["rotulo"] for t in modelo["linhas"][0]] == ["a"]


def test_usa_comando():
    assert usa_comando(_layout(Tecla("x", Acao("comando", "c1"), 1.0)), "c1")
    assert not usa_comando(_layout(Tecla("a", Acao("texto", "a"), 1.0)), "c1")


class _Saida:
    def __getattr__(self, nome):
        return lambda *a, **k: None


def _app(tmp_path):
    perfil = criar_perfil("Adulto", supervisionado=False)
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    return Aplicacao(
        saida=_Saida(), repo=repo, perfil=perfil, pedir_pin=lambda: None,
        pastas_layouts=[DADOS_PROJETO / "layouts", tmp_path / "layouts"],
        pastas_temas=[DADOS_PROJETO / "temas"], pasta_temas_utilizador=tmp_path / "temas",
        pasta_layouts_utilizador=tmp_path / "layouts", pasta_comandos=tmp_path,
    )


def _teclado_com_comando(app, id_):
    return {
        "nome": "Meu", "idioma": "pt-PT", "linhas": [[
            {"rotulo": "Bloco", "acao": {"tipo": "comando", "valor": id_}, "largura": 1.0},
            {"rotulo": "a", "acao": {"tipo": "texto", "valor": "a"}, "largura": 1.0},
        ]],
    }


def test_apagar_comando_com_remover_tira_as_teclas_dos_teclados(tmp_path):
    app = _app(tmp_path)
    comando = app.guardar_comando(None, "Bloco", "notepad")
    app.guardar_layout(_teclado_com_comando(app, comando.id))
    assert app.teclados_com_comando(comando.id) == ["Meu"]
    assert app.apagar_comando(comando.id, remover_teclas=True)
    assert app.teclados_com_comando(comando.id) == []
    assert [t.rotulo for t in app.layouts["Meu"].linhas[0]] == ["a"]


def test_editor_mostra_o_nome_atual_da_tecla_de_comando():
    from PySide6.QtWidgets import QApplication

    from teclado.ui.editor_layout import DialogoEditorLayout

    QApplication.instance() or QApplication([])
    comandos = {"c1": Comando("c1", "Novo", "notepad")}
    dialogo = DialogoEditorLayout(
        None, {}, None, guardar=lambda modelo: None, apagar=lambda nome: False, comandos=comandos,
    )
    tecla = {"rotulo": "Antigo", "acao": {"tipo": "comando", "valor": "c1"}, "largura": 1.0}
    assert dialogo._rotulo_visivel(tecla) == "Novo"
    assert dialogo._comando_da_tecla(tecla) == "c1"
    dialogo.close()


def test_apagar_comando_sem_remover_mantem_as_teclas(tmp_path):
    app = _app(tmp_path)
    comando = app.guardar_comando(None, "Bloco", "notepad")
    app.guardar_layout(_teclado_com_comando(app, comando.id))
    assert app.apagar_comando(comando.id)
    assert app.teclados_com_comando(comando.id) == ["Meu"]
