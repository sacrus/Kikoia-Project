import json

import pytest

from teclado.core.aplicacao import Aplicacao
from teclado.core.layout import LayoutInvalido, descobrir_layouts
from teclado.core.layout_editor import (
    adicionar_linha,
    adicionar_tecla,
    apagar_layout_em_pasta,
    guardar_layout_em_pasta,
    modelo_de,
    modelo_vazio,
    mover_tecla,
    nome_de_ficheiro,
    remover_linha,
    remover_tecla,
    tecla_dict,
    validar_modelo,
)
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil


def _tecla(letra):
    return tecla_dict(letra, "texto", letra)


# --- modelos prontos -----------------------------------------------------

@pytest.mark.parametrize("nome", ["QWERTY", "QWERTY com acentos", "Numérico", "Abecedário", "Vogais"])
def test_modelos_prontos_existem_e_sao_validos(nome):
    assert nome in descobrir_layouts([DADOS_PROJETO / "layouts"])


def test_qwerty_tem_as_letras_do_teclado_portugues():
    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["QWERTY"]
    letras = {t.acao.valor for linha in layout.linhas for t in linha if t.acao.tipo == "texto"}
    assert set("qwertyuiopasdfghjklçzxcvbnm") <= letras


def test_qwerty_com_acentos_tem_a_grave_a_agudo_e_e_agudo():
    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["QWERTY com acentos"]
    valores = {t.acao.valor for linha in layout.linhas for t in linha}
    assert {"à", "á", "é"} <= valores


# --- operacoes sobre o modelo -------------------------------------------

def test_modelo_de_layout_existente_e_editavel():
    layout = descobrir_layouts([DADOS_PROJETO / "layouts"])["Vogais"]
    modelo = modelo_de(layout)
    assert modelo["nome"] == "Vogais"
    assert validar_modelo(modelo).total_teclas == layout.total_teclas


def test_adicionar_tecla_sem_linhas_cria_a_primeira():
    modelo = modelo_vazio("Teste")
    linha, posicao = adicionar_tecla(modelo, None, _tecla("a"))
    assert (linha, posicao) == (0, 0)
    assert modelo["linhas"] == [[_tecla("a")]]


def test_adicionar_tecla_a_linha_indicada():
    modelo = modelo_vazio("Teste")
    adicionar_linha(modelo)
    adicionar_linha(modelo)
    adicionar_tecla(modelo, 0, _tecla("a"))
    adicionar_tecla(modelo, 1, _tecla("b"))
    assert modelo["linhas"][0][0]["rotulo"] == "a"
    assert modelo["linhas"][1][0]["rotulo"] == "b"


def test_mover_tecla_troca_com_vizinha_e_respeita_limites():
    modelo = modelo_vazio("Teste")
    for letra in "abc":
        adicionar_tecla(modelo, None, _tecla(letra))
    nova = mover_tecla(modelo, 0, 0, 1)
    assert nova == 1
    assert [t["rotulo"] for t in modelo["linhas"][0]] == ["b", "a", "c"]
    assert mover_tecla(modelo, 0, 0, -1) == 0  # ja e a primeira


def test_remover_tecla_e_linha():
    modelo = modelo_vazio("Teste")
    adicionar_tecla(modelo, None, _tecla("a"))
    adicionar_tecla(modelo, None, _tecla("b"))
    remover_tecla(modelo, 0, 0)
    assert [t["rotulo"] for t in modelo["linhas"][0]] == ["b"]
    remover_linha(modelo, 0)
    assert modelo["linhas"] == []


def test_validar_ignora_linhas_vazias():
    modelo = modelo_vazio("Teste")
    adicionar_linha(modelo)
    adicionar_tecla(modelo, None, _tecla("a"))
    adicionar_linha(modelo)
    assert validar_modelo(modelo).total_teclas == 1


def test_validar_rejeita_teclado_sem_teclas():
    with pytest.raises(LayoutInvalido):
        validar_modelo(modelo_vazio("Vazio"))


def test_validar_rejeita_nome_vazio():
    modelo = modelo_vazio("   ")
    adicionar_tecla(modelo, None, _tecla("a"))
    with pytest.raises(LayoutInvalido):
        validar_modelo(modelo)


def test_validar_rejeita_tecla_com_acento_desconhecido():
    modelo = modelo_vazio("Teste")
    adicionar_tecla(modelo, None, tecla_dict("x", "acento", "inventado"))
    with pytest.raises(LayoutInvalido):
        validar_modelo(modelo)


# --- ficheiros -------------------------------------------------------------

def test_nome_de_ficheiro_sem_acentos_nem_simbolos():
    assert nome_de_ficheiro("Teclado das Vogais!") == "teclado_das_vogais"
    assert nome_de_ficheiro("Numérico") == "numerico"


def test_nome_de_ficheiro_sem_letras_rejeitado():
    with pytest.raises(LayoutInvalido):
        nome_de_ficheiro("?!  ")


def test_guardar_grava_ficheiro_e_pode_ser_redescoberto(tmp_path):
    modelo = modelo_vazio("Só A e C")
    adicionar_tecla(modelo, None, _tecla("a"))
    adicionar_tecla(modelo, None, _tecla("c"))
    layout = guardar_layout_em_pasta(modelo, tmp_path)
    ficheiro = tmp_path / "so_a_e_c.kblayout.json"
    assert ficheiro.exists()
    dados = json.loads(ficheiro.read_text(encoding="utf-8"))
    assert dados["nome"] == "Só A e C"
    assert descobrir_layouts([tmp_path])["Só A e C"] == layout


def test_guardar_invalido_nao_cria_ficheiro(tmp_path):
    with pytest.raises(LayoutInvalido):
        guardar_layout_em_pasta(modelo_vazio("Vazio"), tmp_path)
    assert list(tmp_path.glob("*.kblayout.json")) == []


def test_apagar_remove_so_o_teclado_indicado(tmp_path):
    for nome in ["Um", "Dois"]:
        modelo = modelo_vazio(nome)
        adicionar_tecla(modelo, None, _tecla("a"))
        guardar_layout_em_pasta(modelo, tmp_path)
    assert apagar_layout_em_pasta("Um", tmp_path) is True
    assert list(descobrir_layouts([tmp_path])) == ["Dois"]


def test_apagar_inexistente_devolve_falso(tmp_path):
    assert apagar_layout_em_pasta("Nao existe", tmp_path) is False


# --- controlador -----------------------------------------------------------

class _Saida:
    def escrever(self, texto):
        pass

    def tecla(self, nome):
        pass


def _aplicacao(tmp_path, perfil, pin=lambda: None):
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    pasta_utilizador = tmp_path / "layouts"
    from teclado.core.paths import DADOS_PROJETO as D
    app = Aplicacao(
        saida=_Saida(),
        repo=repo,
        perfil=perfil,
        pedir_pin=pin,
        pastas_layouts=[D / "layouts", pasta_utilizador],
        pastas_temas=[D / "temas"],
        pasta_temas_utilizador=tmp_path / "temas",
        pasta_layouts_utilizador=pasta_utilizador,
    )
    return app, repo, pasta_utilizador


def _modelo_teste(nome="Meu teclado"):
    modelo = modelo_vazio(nome)
    adicionar_tecla(modelo, None, _tecla("a"))
    return modelo


def test_predefinido_e_qwerty(tmp_path):
    app, _, _ = _aplicacao(tmp_path, criar_perfil("Adulto", supervisionado=False))
    assert app.layout.nome == "QWERTY"


def test_guardar_teclado_novo_passa_a_ser_o_ativo(tmp_path):
    app, repo, pasta = _aplicacao(tmp_path, criar_perfil("Adulto", supervisionado=False))
    guardado = app.guardar_layout(_modelo_teste())
    assert guardado is not None and app.layout.nome == "Meu teclado"
    assert (pasta / "meu_teclado.kblayout.json").exists()
    assert repo.carregar(app.perfil.id).preferencias["layout"] == "Meu teclado"
    assert "Meu teclado" in app.layouts


def test_guardar_invalido_lanca_erro_sem_alterar_nada(tmp_path):
    app, _, pasta = _aplicacao(tmp_path, criar_perfil("Adulto", supervisionado=False))
    with pytest.raises(LayoutInvalido):
        app.guardar_layout(modelo_vazio("Vazio"))
    assert app.layout.nome == "QWERTY"
    assert not pasta.exists() or not any(pasta.iterdir())


def test_guardar_bloqueado_em_perfil_supervisionado_sem_pin(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    app, _, pasta = _aplicacao(tmp_path, perfil, pin=lambda: None)
    assert app.guardar_layout(_modelo_teste()) is None
    assert app.layout.nome == "QWERTY"
    assert not pasta.exists() or not any(pasta.iterdir())


def test_guardar_com_pin_correto_em_perfil_supervisionado(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    pins = iter(["1234"])
    app, _, _ = _aplicacao(tmp_path, perfil, pin=lambda: next(pins))
    assert app.guardar_layout(_modelo_teste()) is not None
    assert app.layout.nome == "Meu teclado"


def test_apagar_teclado_ativo_volta_ao_predefinido(tmp_path):
    app, _, _ = _aplicacao(tmp_path, criar_perfil("Adulto", supervisionado=False))
    app.guardar_layout(_modelo_teste())
    assert app.apagar_layout("Meu teclado") is True
    assert "Meu teclado" not in app.layouts
    assert app.layout.nome == "QWERTY"


def test_nao_apaga_modelo_do_projeto(tmp_path):
    app, _, _ = _aplicacao(tmp_path, criar_perfil("Adulto", supervisionado=False))
    assert app.apagar_layout("QWERTY") is False
    assert "QWERTY" in app.layouts
