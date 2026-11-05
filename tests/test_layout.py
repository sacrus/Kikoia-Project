import copy
import json

import pytest

from teclado.core.layout import LayoutInvalido, carregar_layout, descobrir_layouts, validar_layout
from teclado.core.paths import DADOS_PROJETO

BASE = {
    "nome": "Teste",
    "idioma": "pt-PT",
    "linhas": [[{"rotulo": "a", "acao": {"tipo": "texto", "valor": "a"}}]],
}


def test_layouts_do_projeto_sao_validos():
    layouts = descobrir_layouts([DADOS_PROJETO / "layouts"])
    assert "Português" in layouts
    assert "Vogais" in layouts


def test_layout_vogais_tem_cinco_vogais():
    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["Vogais"]
    letras = [t.acao.valor for linha in layout.linhas for t in linha if t.acao.tipo == "texto"]
    assert letras == ["a", "e", "i", "o", "u"]


def test_layout_portugues_tem_shift_e_pontuacao():
    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["Português"]
    modificadores = [t.acao.valor for linha in layout.linhas for t in linha if t.acao.tipo == "modificador"]
    pontuacao = {t.acao.valor for linha in layout.linhas for t in linha if t.acao.tipo == "texto"}
    assert modificadores == ["shift"]
    assert {".", ",", "?", "!"} <= pontuacao


def test_layout_valido_minimo():
    layout = validar_layout(copy.deepcopy(BASE))
    assert layout.nome == "Teste"
    assert layout.total_teclas == 1
    assert layout.linhas[0][0].largura == 1.0


@pytest.mark.parametrize(
    "alteracao",
    [
        lambda d: d.pop("nome"),
        lambda d: d.update(linhas=[]),
        lambda d: d["linhas"][0][0]["acao"].update(tipo="script"),
        lambda d: d["linhas"][0][0]["acao"].update(tipo="tecla", valor="inexistente"),
        lambda d: d["linhas"][0][0]["acao"].update(tipo="modificador", valor="alt"),
        lambda d: d["linhas"][0][0].update(largura=0),
        lambda d: d["linhas"][0][0].update(largura=True),
        lambda d: d["linhas"][0][0].update(rotulo=""),
        lambda d: d["linhas"][0][0]["acao"].update(valor="x" * 21),
    ],
)
def test_layout_invalido_rejeitado(alteracao):
    dados = copy.deepcopy(BASE)
    alteracao(dados)
    with pytest.raises(LayoutInvalido):
        validar_layout(dados)


def test_demasiadas_teclas_rejeitadas():
    dados = copy.deepcopy(BASE)
    dados["linhas"] = [[copy.deepcopy(dados["linhas"][0][0]) for _ in range(81)]]
    with pytest.raises(LayoutInvalido):
        validar_layout(dados)


def test_ficheiro_json_invalido(tmp_path):
    ficheiro = tmp_path / "mau.kblayout.json"
    ficheiro.write_text("{ isto nao e json", encoding="utf-8")
    with pytest.raises(LayoutInvalido):
        carregar_layout(ficheiro)


def test_descobrir_ignora_invalidos(tmp_path):
    (tmp_path / "bom.kblayout.json").write_text(json.dumps(BASE), encoding="utf-8")
    (tmp_path / "mau.kblayout.json").write_text("{}", encoding="utf-8")
    encontrados = descobrir_layouts([tmp_path])
    assert list(encontrados) == ["Teste"]
