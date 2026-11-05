import json

import pytest

from teclado.core import idiomas
from teclado.core.idiomas import IDIOMA_PADRAO, IDIOMAS, idioma_valido, t


@pytest.fixture(autouse=True)
def _restaurar_idioma():
    atual = idiomas.atual()
    yield
    idiomas.definir(atual)


def _chaves(codigo):
    caminho = idiomas._pasta / f"{codigo}.json"
    return set(json.loads(caminho.read_text(encoding="utf-8")))


def test_todos_os_idiomas_tem_as_mesmas_chaves():
    referencia = _chaves(IDIOMA_PADRAO)
    for codigo in IDIOMAS:
        assert _chaves(codigo) == referencia, codigo


def test_todas_as_chaves_usadas_no_codigo_existem_em_todos_os_idiomas():
    import re
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1] / "teclado"
    usadas = set()
    for ficheiro in raiz.rglob("*.py"):
        usadas |= set(re.findall(r"\bt\(\s*\"([a-z_.0-9]+)\"", ficheiro.read_text(encoding="utf-8")))
    assert usadas, "nenhuma chave encontrada"
    for codigo in IDIOMAS:
        em_falta = usadas - _chaves(codigo)
        assert not em_falta, f"{codigo}: {sorted(em_falta)}"


def test_idioma_desconhecido_usa_o_padrao():
    assert idioma_valido("xx") == IDIOMA_PADRAO
    assert idioma_valido(None) == IDIOMA_PADRAO
    assert idiomas.definir("xx") == IDIOMA_PADRAO


def test_definir_muda_os_textos():
    idiomas.definir("pt-PT")
    assert t("definicoes.titulo") == "Definições"
    idiomas.definir("en")
    assert t("definicoes.titulo") == "Settings"
    idiomas.definir("fr")
    assert t("definicoes.titulo") == "Paramètres"


def test_chave_em_falta_usa_portugues():
    idiomas.definir("en")
    assert t("chave.que.nao.existe") == "chave.que.nao.existe"


def test_textos_aceitam_campos():
    idiomas.definir("pt-PT")
    assert t("definicoes.titulo", nome="x") == "Definições"


def test_janela_principal_segue_o_idioma(monkeypatch):
    from PySide6.QtWidgets import QApplication

    from teclado.core.dicionario import Dicionario
    from teclado.core.editor import Editor
    from teclado.core.layout import Layout, Tecla, Acao
    from teclado.core.paths import DADOS_PROJETO
    from teclado.core.tema import descobrir_temas
    from teclado.ui.janela import JanelaTeclado

    class Saida:
        def __getattr__(self, nome):
            return lambda *a, **k: None

    app = QApplication.instance() or QApplication([])
    idiomas.definir("en")
    layout = Layout("Teste", "pt-PT", ((Tecla("A", Acao("texto", "a"), 1.0),),))
    tema = descobrir_temas([DADOS_PROJETO / "temas"])["Claro"]
    janela = JanelaTeclado(Editor(Saida(), Dicionario({})), layout, tema, ancorar_fundo=False)
    try:
        assert janela.windowTitle() == "Keyboard - Teste"
        assert janela._botao_falar.text() == "Speak"
        assert janela._botao_ditar.text() == "Dictate"
    finally:
        janela.close()
        idiomas.definir("pt-PT")
    assert app is not None


def test_editor_de_teclados_segue_o_idioma():
    from PySide6.QtWidgets import QApplication, QPushButton

    from teclado.ui.editor_layout import DialogoEditorLayout

    QApplication.instance() or QApplication([])
    idiomas.definir("en")
    dialogo = DialogoEditorLayout(None, {}, None, guardar=lambda m: None, apagar=lambda n: False)
    try:
        assert dialogo.windowTitle() == "Keyboard editor"
        textos = {b.text() for b in dialogo.findChildren(QPushButton)}
        assert "Save" in textos and "Close" in textos
    finally:
        dialogo.close()
        idiomas.definir("pt-PT")
