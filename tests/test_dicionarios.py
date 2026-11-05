import pytest

from teclado.core.dicionario import Dicionario
from teclado.core.paths import DADOS_PROJETO

IDIOMAS_COM_LEXICO = ["pt-PT", "en", "es", "fr"]


@pytest.mark.parametrize("codigo", IDIOMAS_COM_LEXICO)
def test_lexico_existe_e_tem_palavras(codigo):
    caminho = DADOS_PROJETO / "languages" / codigo / "lexico.tsv"
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    assert len(linhas) > 20000, codigo


@pytest.mark.parametrize(
    "codigo, prefixo, esperada",
    [
        ("en", "th", "the"),
        ("es", "que", "que"),
        ("fr", "vou", "vous"),
        ("pt-PT", "obri", "obrigado"),
    ],
)
def test_sugestoes_no_idioma_do_lexico(codigo, prefixo, esperada):
    caminho = DADOS_PROJETO / "languages" / codigo / "lexico.tsv"
    dicionario = Dicionario.carregar(caminho)
    sugestoes = dicionario.sugerir(prefixo, 10)
    assert esperada in sugestoes, sugestoes
    assert all(s.startswith(prefixo) for s in sugestoes)
