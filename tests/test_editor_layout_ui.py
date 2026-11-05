import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from teclado.core.layout import descobrir_layouts
from teclado.core.layout_editor import validar_modelo
from teclado.core.paths import DADOS_PROJETO
from teclado.ui.editor_layout import DialogoEditorLayout, DialogoTecla, simbolos_disponiveis


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _layouts():
    return descobrir_layouts([DADOS_PROJETO / "layouts"])


def _dialogo(atual=None, guardar=lambda m: None):
    return DialogoEditorLayout(None, _layouts(), atual, guardar=guardar, apagar=lambda n: False)


def _botao(dialogo, texto):
    return next(b for b in dialogo.findChildren(QPushButton) if b.text() == texto)


def _escolher_e_colocar(dialogo, rotulo, linha):
    """Simula o utilizador: escolhe uma tecla da lista e clica no + da linha."""
    botao = next(b for b, item in dialogo._paleta if item["rotulo"] == rotulo)
    botao.click()
    dialogo._grelha_conteudo.findChildren(QPushButton)  # garante a grelha construida
    mais = [b for b in dialogo._grelha_conteudo.findChildren(QPushButton) if b.text() == "+"]
    mais[linha].click()


def test_editor_abre_maximizado(app):
    from teclado.ui.dialogos import _estado_desejado
    from PySide6.QtCore import Qt

    dialogo = _dialogo()
    assert _estado_desejado(dialogo) == Qt.WindowState.WindowMaximized
    dialogo.close()


def test_grelha_carrega_o_teclado_atual(app):
    atual = _layouts()["Vogais"]
    dialogo = _dialogo(atual)
    assert dialogo._nome.text() == "Vogais"
    assert len(dialogo._celulas) == atual.total_teclas
    dialogo.close()


def test_paleta_tem_letras_acentos_e_especiais(app):
    dialogo = _dialogo()
    valores = {(i["acao"]["tipo"], i["acao"]["valor"]) for _, i in dialogo._paleta}
    assert ("texto", "a") in valores
    assert ("texto", "é") in valores
    assert ("acento", "agudo") in valores
    assert ("tecla", "espaco") in valores
    dialogo.close()


def test_escolher_e_colocar_tecla_na_linha(app):
    dialogo = _dialogo()
    _botao(dialogo, "+ Nova linha").click()
    _escolher_e_colocar(dialogo, "á", 0)
    assert [t["rotulo"] for t in dialogo._modelo["linhas"][0]] == ["á"]
    dialogo.close()


def test_sem_escolha_nao_coloca_nada(app):
    dialogo = _dialogo()
    _botao(dialogo, "+ Nova linha").click()
    mais = [b for b in dialogo._grelha_conteudo.findChildren(QPushButton) if b.text() == "+"]
    mais[0].click()
    assert dialogo._modelo["linhas"][0] == []
    dialogo.close()


def test_modelo_rapido_preenche_a_grelha(app):
    dialogo = _dialogo()
    dialogo._aplicar_pronto("Numérico")
    assert dialogo._nome.text() == "Numérico (cópia)"
    assert len(dialogo._celulas) == _layouts()["Numérico"].total_teclas
    dialogo.close()


def test_minimal_existe_e_tem_toque_repetido(app):
    dialogo = _dialogo()
    dialogo._aplicar_pronto("Minimal")
    tipos = {t["acao"]["tipo"] for linha in dialogo._modelo["linhas"] for t in linha}
    assert "multitoque" in tipos
    dialogo.close()


def test_guardar_envia_modelo_ao_controlador(app):
    recebidos = []

    def guardar(modelo):
        recebidos.append(modelo)
        return validar_modelo(modelo)

    dialogo = _dialogo(guardar=guardar)
    dialogo._nome.setText("Só A e C")
    _botao(dialogo, "+ Nova linha").click()
    _escolher_e_colocar(dialogo, "a", 0)
    _escolher_e_colocar(dialogo, "c", 0)
    dialogo._guardar()
    assert recebidos[0]["nome"] == "Só A e C"
    assert dialogo.guardado is not None and dialogo.guardado.nome == "Só A e C"


def test_simbolos_disponiveis_sao_todos_validos():
    from teclado.core.layout import validar_tecla
    for item in simbolos_disponiveis():
        validar_tecla(item)


def test_dialogo_tecla_multitoque_valida(app):
    dialogo = DialogoTecla(None)
    dialogo._tipo.setCurrentIndex(dialogo._tipo.findData("multitoque"))
    dialogo._valor_texto.setText("abc")
    dialogo._rotulo.setText("2 ABC")
    resultado = dialogo.resultado()
    assert resultado["acao"] == {"tipo": "multitoque", "valor": "abc"}
    dialogo.close()
