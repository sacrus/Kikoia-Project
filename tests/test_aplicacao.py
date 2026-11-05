from teclado.core.aplicacao import Aplicacao
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.core.politica import ativar_supervisao


class _Saida:
    def escrever(self, texto):
        pass

    def tecla(self, nome):
        pass


def _app(tmp_path, perfil, pin=lambda: None):
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    return Aplicacao(
        saida=_Saida(),
        repo=repo,
        perfil=perfil,
        pedir_pin=pin,
        pastas_layouts=[DADOS_PROJETO / "layouts"],
        pastas_temas=[DADOS_PROJETO / "temas", tmp_path / "temas"],
        pasta_temas_utilizador=tmp_path / "temas",
    ), repo


def test_valores_por_omissao(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    assert app.layout.nome == "QWERTY"
    assert app.tema.nome == "Claro"


def test_adulto_sem_supervisao_muda_sem_pin(tmp_path):
    chamadas = []
    app, repo = _app(tmp_path, criar_perfil("Adulto", supervisionado=False),
                     pin=lambda: chamadas.append(1) or None)
    novo = app.mudar_layout("Vogais")
    assert novo is not None and app.layout.nome == "Vogais"
    assert chamadas == []
    assert repo.carregar(app.perfil.id).preferencias["layout"] == "Vogais"


def test_supervisionado_bloqueado_sem_pin(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    app, _ = _app(tmp_path, perfil, pin=lambda: None)
    assert app.mudar_layout("Vogais") is None
    assert app.layout.nome == "QWERTY"


def test_supervisionado_com_pin_correto(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    pins = iter(["1234"])
    app, _ = _app(tmp_path, perfil, pin=lambda: next(pins))
    assert app.mudar_layout("Vogais") is not None
    assert app.layout.nome == "Vogais"


def test_supervisionado_pin_errado_tres_vezes(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    tentativas = []

    def pin():
        tentativas.append(1)
        return "0000"

    app, _ = _app(tmp_path, perfil, pin=pin)
    assert app.mudar_tema("Escuro") is None
    assert len(tentativas) == 3
    assert app.tema.nome == "Claro"


def test_proximo_layout_cicla(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    primeiro = app.layout.nome
    segundo = app.proximo_layout().nome
    assert segundo != primeiro
    for _ in range(len(app.layouts) - 1):
        app.proximo_layout()
    assert app.layout.nome == primeiro


def test_personalizar_cria_tema_e_guarda(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    tema = app.personalizar("#101010", "#FFFFFF", None)
    assert tema is not None
    assert tema.cor_texto == "#000000"
    assert (tmp_path / "temas" / "personalizado.kbtheme.json").exists()
    assert app.tema.nome == "Personalizado"


def test_ativar_supervisao_bloqueia_troca_de_tema(tmp_path):
    perfil = criar_perfil("Adulto", supervisionado=False)
    ativar_supervisao(perfil, "9999")
    app, _ = _app(tmp_path, perfil, pin=lambda: None)
    assert app.mudar_tema("Escuro") is None
