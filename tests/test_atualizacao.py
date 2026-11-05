import sys

import pytest
from PySide6.QtWidgets import QApplication

from teclado.core import atualizacao
from teclado.core.atualizacao import Dependencia, verificar_dependencias, verificar_teclado, versao_tupla


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_epoca_pep440_nao_conta_na_comparacao():
    assert versao_tupla("4!10.0.28000.2957") == versao_tupla("10.0.28000.2957")
    assert not Dependencia("x", "4!10.0.1", "10.0.1").desatualizada


def test_versoes_comparam_numericamente():
    assert versao_tupla("1.10.0") > versao_tupla("1.9.0")
    assert versao_tupla("v0.2") > versao_tupla("0.1.9")
    assert versao_tupla("0.1.0") == versao_tupla("0.1.0")


def test_dependencia_desatualizada_so_com_versao_mais_recente_maior():
    assert Dependencia("x", "1.0.0", "1.1.0").desatualizada
    assert not Dependencia("x", "1.1.0", "1.1.0").desatualizada
    assert not Dependencia("x", "2.0.0", "1.9.0").desatualizada
    assert not Dependencia("x", None, "1.0.0").desatualizada


def test_requisitos_ignoram_pacotes_de_outro_sistema(tmp_path, monkeypatch):
    ficheiro = tmp_path / "requirements.txt"
    ficheiro.write_text(
        "PySide6-Essentials>=6.7\n"
        "# comentario\n"
        "winrt-runtime>=3.0; sys_platform == \"win32\"\n"
        "spake2>=0.9\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "platform", "linux")
    assert atualizacao.nomes_dependencias(ficheiro) == ["PySide6-Essentials", "spake2"]
    monkeypatch.setattr(sys, "platform", "win32")
    assert atualizacao.nomes_dependencias(ficheiro) == ["PySide6-Essentials", "winrt-runtime", "spake2"]


def test_verificar_dependencias_usa_o_pypi():
    respostas = {"https://pypi.org/pypi/spake2/json": {"info": {"version": "9.9.9"}}}

    resultados = verificar_dependencias(["spake2"], buscar=lambda url: respostas[url])

    assert resultados[0].mais_recente == "9.9.9"
    assert resultados[0].nome == "spake2"


def test_sem_rede_nao_marca_como_desatualizada():
    def sem_rede(url):
        raise OSError("sem ligacao")

    resultados = verificar_dependencias(["spake2"], buscar=sem_rede)

    assert resultados[0].mais_recente is None
    assert not resultados[0].desatualizada


def test_teclado_sem_repositorio_nao_faz_pedidos(monkeypatch):
    monkeypatch.setattr(atualizacao, "REPOSITORIO", None)

    def nao_deve_ser_chamado(url):
        raise AssertionError("nao devia haver pedidos")

    assert verificar_teclado(buscar=nao_deve_ser_chamado) is None


def test_teclado_com_versao_nova_devolve_atualizacao(monkeypatch):
    monkeypatch.setattr(atualizacao, "REPOSITORIO", "dono/teclado")
    dados = {"tag_name": "v9.0.0", "html_url": "https://github.com/dono/teclado/releases/tag/v9.0.0"}

    nova = verificar_teclado(buscar=lambda url: dados)

    assert nova.versao == "9.0.0"
    assert nova.pagina.endswith("v9.0.0")


def test_teclado_na_mesma_versao_nao_avisa(monkeypatch):
    monkeypatch.setattr(atualizacao, "REPOSITORIO", "dono/teclado")
    assert verificar_teclado(buscar=lambda url: {"tag_name": "v" + atualizacao.VERSAO}) is None


def test_comando_atualizar_usa_o_python_do_teclado():
    comando = atualizacao.comando_atualizar(["spake2"])
    assert comando[0] == sys.executable
    assert comando[1:] == ["-m", "pip", "install", "--upgrade", "spake2"]


def test_dialogo_abre_sem_rede(qapp, monkeypatch):
    from teclado.ui.atualizacoes import DialogoAtualizacoes

    monkeypatch.setattr(atualizacao, "REPOSITORIO", None)
    dialogo = DialogoAtualizacoes(None)
    assert atualizacao.VERSAO in dialogo._estado_teclado.text()
    dialogo.close()

