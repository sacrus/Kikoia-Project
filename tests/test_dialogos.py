import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from teclado.core.tema import Tema
from teclado.ui.dialogos import DialogoPersonalizacao, imagem_valida


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _tema(imagem=None):
    return Tema(
        nome="Teste", cor_fundo="#112233", cor_tecla="#445566", cor_texto="#FFFFFF",
        cor_tecla_premida="#FFD54F", cor_texto_premido="#000000",
        imagem_fundo=imagem, opacidade_imagem=50,
    )


def test_dialogo_parte_das_cores_do_tema(app):
    dialogo = DialogoPersonalizacao(None, _tema())
    escolhas = dialogo.escolhas()
    assert escolhas["cor_fundo"] == "#112233"
    assert escolhas["cor_tecla"] == "#445566"
    assert escolhas["imagem"] is None
    dialogo.close()


def test_dialogo_mantem_imagem_do_tema(app, tmp_path):
    caminho = tmp_path / "f.png"
    QImage(64, 64, QImage.Format.Format_RGB32).save(str(caminho))
    dialogo = DialogoPersonalizacao(None, _tema(caminho))
    assert dialogo.escolhas()["imagem"] == caminho
    dialogo._remover_imagem()
    assert dialogo.escolhas()["imagem"] is None
    dialogo.close()


def test_imagem_valida_aceita_png_real(tmp_path):
    caminho = tmp_path / "ok.png"
    QImage(10, 10, QImage.Format.Format_RGB32).save(str(caminho))
    assert imagem_valida(caminho)


def test_imagem_valida_rejeita_ficheiro_falso(tmp_path):
    caminho = tmp_path / "falso.png"
    caminho.write_bytes(b"nao e imagem")
    assert not imagem_valida(caminho)
