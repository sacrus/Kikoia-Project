import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from teclado.core.comandos import Comando
from teclado.core.layout import descobrir_layouts
from teclado.core.paths import DADOS_PROJETO
from teclado.ui.editor_layout import DialogoEditorLayout


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _dialogo(comandos, guardar):
    return DialogoEditorLayout(
        None, descobrir_layouts([DADOS_PROJETO / "layouts"]), None,
        guardar=lambda m: None, apagar=lambda n: False,
        comandos=comandos, guardar_comando=guardar,
    )


def test_teclas_de_programa_existentes_aparecem_na_paleta(app):
    dialogo = _dialogo({"c1": Comando("c1", "Bloco", "notepad")}, lambda *a: None)
    valores = {i["acao"]["valor"] for _, i in dialogo._paleta if i["acao"]["tipo"] == "comando"}
    assert valores == {"c1"}
    dialogo.close()


def test_criar_tecla_de_programa_aparece_logo_na_paleta(app):
    comandos = {}

    def guardar(id_, rotulo, comando):
        novo = Comando("c2", rotulo, comando)
        comandos[novo.id] = novo
        return novo

    dialogo = _dialogo(comandos, guardar)
    # Simula o que o utilizador faz no DialogoComando (sem abrir a janela).
    criada = dialogo._guardar_comando(None, "Word", "winword")
    dialogo._comandos[criada.id] = criada
    dialogo._construir_paleta()
    rotulos = [i["rotulo"] for _, i in dialogo._paleta if i["acao"]["tipo"] == "comando"]
    assert rotulos == ["Word"]
    assert dialogo._paleta and any(b.text() == "Word" for b, _ in dialogo._paleta)
    dialogo.close()


def test_botao_nova_tecla_de_programa_existe(app):
    dialogo = _dialogo({}, lambda *a: None)
    textos = {b.text() for b in dialogo.findChildren(QPushButton)}
    assert "Nova tecla de programa…" in textos
    dialogo.close()
