import pytest
from PySide6.QtWidgets import QApplication

from teclado.core.aplicacao import Aplicacao
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.core.politica import Decisao, decidir
from teclado.core.seguranca import verificar_pin
from teclado.ui.supervisao import ACAO_ATIVAR, DialogoSupervisao


class _Saida:
    def escrever(self, texto):
        pass

    def tecla(self, nome):
        pass


def _app(tmp_path, perfil, pins=()):
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    fila = list(pins)

    def pedir():
        return fila.pop(0) if fila else None

    app = Aplicacao(
        saida=_Saida(), repo=repo, perfil=perfil, pedir_pin=pedir,
        pastas_layouts=[DADOS_PROJETO / "layouts"],
        pastas_temas=[DADOS_PROJETO / "temas"],
        pasta_temas_utilizador=tmp_path / "temas",
        pasta_layouts_utilizador=tmp_path / "layouts",
    )
    return app, repo


def test_ativar_grava_codigo_em_hash_e_ambito(tmp_path):
    app, repo = _app(tmp_path, criar_perfil("Criança", supervisionado=False))
    app.ativar_supervisao("1234", ["alterar_tema"])
    guardado = repo.carregar(app.perfil.id).supervisao
    assert guardado.ativa is True
    assert guardado.ambito == ["alterar_tema"]
    assert verificar_pin("1234", guardado.codigo_hash)
    assert "1234" not in (tmp_path / "perfis" / f"{app.perfil.id}.json").read_text(encoding="utf-8")


def test_ativar_com_codigo_curto_nao_altera_nada(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Criança", supervisionado=False))
    with pytest.raises(ValueError):
        app.ativar_supervisao("12", ["alterar_tema"])
    assert app.perfil.supervisao.ativa is False


def test_ativar_ignora_ambito_desconhecido(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Criança", supervisionado=False))
    app.ativar_supervisao("1234", ["alterar_tema", "inventado", "alterar_tema", "aprender_palavra"])
    assert app.perfil.supervisao.ambito == ["alterar_tema"]


def test_ativar_duas_vezes_e_erro(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Criança", supervisionado=False))
    app.ativar_supervisao("1234", ["alterar_tema"])
    with pytest.raises(RuntimeError):
        app.ativar_supervisao("5678", ["alterar_tema"])


def test_alterar_ambito_bloqueado_com_tres_codigos_errados(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Criança", supervisionado=False), pins=["0", "0", "0"])
    app.ativar_supervisao("1234", ["alterar_tema"])
    assert app.atualizar_supervisao(["alterar_layout"]) is False
    assert app.perfil.supervisao.ambito == ["alterar_tema"]


def test_alterar_ambito_aceite_com_codigo_correto(tmp_path):
    app, repo = _app(tmp_path, criar_perfil("Criança", supervisionado=False), pins=["0000", "1234"])
    app.ativar_supervisao("1234", ["alterar_tema"])
    assert app.atualizar_supervisao(["alterar_layout"]) is True  # 2.ª tentativa certa
    assert repo.carregar(app.perfil.id).supervisao.ambito == ["alterar_layout"]


def test_alterar_codigo_novo_so_com_codigo_atual(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Criança", supervisionado=False), pins=["1234"])
    app.ativar_supervisao("1234", ["definicoes"])
    assert app.atualizar_supervisao(["definicoes"], novo_pin="9999") is True
    assert verificar_pin("9999", app.perfil.supervisao.codigo_hash)
    assert not verificar_pin("1234", app.perfil.supervisao.codigo_hash)


def test_desativar_exige_codigo(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Criança", supervisionado=False), pins=[None, None, None])
    app.ativar_supervisao("1234", ["definicoes"])
    assert app.desativar_supervisao() is False
    assert app.perfil.supervisao.ativa is True


def test_desativar_com_codigo_correto_liberta_tudo(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Criança", supervisionado=False), pins=["1234"])
    app.ativar_supervisao("1234", ["alterar_layout", "alterar_tema"])
    assert app.desativar_supervisao() is True
    assert app.perfil.supervisao.ativa is False
    assert decidir(app.perfil, "alterar_layout") is Decisao.PERMITIR


def test_estado_supervisao(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Criança", supervisionado=False))
    assert app.estado_supervisao()[0] is False
    app.ativar_supervisao("1234", ["definicoes"])
    assert app.estado_supervisao() == (True, ["definicoes"])


# --- dialogo -------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_dialogo_ativar_devolve_codigo_e_ambito(qapp):
    dialogo = DialogoSupervisao(None, False, ["alterar_tema", "definicoes"])
    dialogo._pin1.setText("1234")
    dialogo._pin2.setText("1234")
    dialogo._submeter(ACAO_ATIVAR)
    r = dialogo.resultado()
    assert r == {"acao": "ativar", "ambito": ["alterar_tema", "definicoes"], "pin": "1234"}
    dialogo.close()


def test_dialogo_ambito_inicial_reflete_o_perfil(qapp):
    dialogo = DialogoSupervisao(None, True, ["alterar_layout"])
    assert dialogo._checks["alterar_layout"].isChecked()
    assert not dialogo._checks["definicoes"].isChecked()
    dialogo.close()


def test_dialogo_atualizar_sem_codigo_mantem_o_atual(qapp):
    dialogo = DialogoSupervisao(None, True, ["definicoes"])
    dialogo._checks["alterar_tema"].setChecked(True)
    dialogo._submeter("atualizar")
    r = dialogo.resultado()
    assert r["pin"] is None
    assert set(r["ambito"]) == {"definicoes", "alterar_tema"}
    dialogo.close()
