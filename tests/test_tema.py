import json

import pytest

from teclado.core.paths import DADOS_PROJETO
from teclado.core.tema import (
    Tema,
    TemaInvalido,
    carregar_tema,
    cor_texto_para,
    descobrir_temas,
    guardar_tema,
    validar_tema,
)

BASE = {
    "nome": "Teste",
    "cor_fundo": "#000000",
    "cor_tecla": "#111111",
    "cor_texto": "#FFFFFF",
    "cor_tecla_premida": "#FFD54F",
    "cor_texto_premido": "#000000",
}


def test_temas_do_projeto_validos():
    temas = descobrir_temas([DADOS_PROJETO / "temas"])
    assert {"Claro", "Escuro"} <= set(temas)


def test_tema_com_imagem_existente(tmp_path):
    imagem = tmp_path / "fundo.png"
    imagem.write_bytes(b"x")
    dados = dict(BASE, imagem_fundo="fundo.png")
    tema = validar_tema(dados, base=tmp_path)
    assert tema.imagem_fundo == tmp_path / "fundo.png"


def test_imagem_inexistente_rejeitada(tmp_path):
    with pytest.raises(TemaInvalido):
        validar_tema(dict(BASE, imagem_fundo="nao_existe.png"), base=tmp_path)


@pytest.mark.parametrize(
    "alteracao",
    [
        {"cor_fundo": "azul"},
        {"cor_tecla": "#GGGGGG"},
        {"cor_texto": "#FFF"},
        {"tamanho_fonte": 5},
        {"tamanho_fonte": True},
        {"opacidade_imagem": 101},
        {"nome": ""},
    ],
)
def test_tema_invalido_rejeitado(alteracao):
    with pytest.raises(TemaInvalido):
        validar_tema(dict(BASE, **alteracao))


def test_cor_texto_para_contraste():
    assert cor_texto_para("#FFFFFF") == "#000000"
    assert cor_texto_para("#000000") == "#FFFFFF"


def test_guardar_e_carregar_ida_e_volta(tmp_path):
    imagem = tmp_path / "f.png"
    imagem.write_bytes(b"x")
    tema = Tema(
        nome="Personalizado",
        cor_fundo="#112233",
        cor_tecla="#445566",
        cor_texto="#FFFFFF",
        cor_tecla_premida="#FFD54F",
        cor_texto_premido="#000000",
        tamanho_fonte=30,
        imagem_fundo=imagem,
        opacidade_imagem=70,
    )
    caminho = tmp_path / "p.kbtheme.json"
    guardar_tema(tema, caminho)
    assert carregar_tema(caminho) == tema
    assert json.loads(caminho.read_text(encoding="utf-8"))["nome"] == "Personalizado"
