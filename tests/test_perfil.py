import json

import pytest

from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.core.seguranca import verificar_pin


def test_perfil_supervisionado_guarda_hash_e_nao_o_pin(tmp_path):
    # PIN com letras que nao existem em hexadecimal, para nunca coincidir com o id do perfil.
    perfil = criar_perfil("Criança", supervisionado=True, pin="segredo")
    repo = RepositorioPerfis(tmp_path)
    repo.guardar(perfil)

    conteudo = (tmp_path / f"{perfil.id}.json").read_text(encoding="utf-8")
    assert "segredo" not in conteudo
    assert "codigo_adulto_hash" in conteudo

    carregado = repo.carregar(perfil.id)
    assert carregado.supervisao.ativa is True
    assert verificar_pin("segredo", carregado.supervisao.codigo_hash)


def test_perfil_livre_sem_pin(tmp_path):
    perfil = criar_perfil("Adulto", supervisionado=False)
    repo = RepositorioPerfis(tmp_path)
    repo.guardar(perfil)
    carregado = repo.carregar(perfil.id)
    assert carregado.supervisao.ativa is False
    assert carregado.supervisao.codigo_hash is None


def test_supervisionado_exige_pin():
    with pytest.raises(ValueError):
        criar_perfil("Criança", supervisionado=True, pin="12")


def test_nome_vazio_rejeitado():
    with pytest.raises(ValueError):
        criar_perfil("   ", supervisionado=False)


def test_id_com_caminhos_invalidos_rejeitado(tmp_path):
    repo = RepositorioPerfis(tmp_path)
    with pytest.raises(ValueError):
        repo.carregar("../segredo")


def test_listar_ignora_ficheiros_estranhos(tmp_path):
    repo = RepositorioPerfis(tmp_path)
    perfil = criar_perfil("Adulto", supervisionado=False)
    repo.guardar(perfil)
    (tmp_path / "lixo.json").write_text("{}", encoding="utf-8")
    assert [p.id for p in repo.listar()] == [perfil.id]


def test_ficheiro_json_legivel(tmp_path):
    perfil = criar_perfil("Adulto", supervisionado=False)
    RepositorioPerfis(tmp_path).guardar(perfil)
    dados = json.loads((tmp_path / f"{perfil.id}.json").read_text(encoding="utf-8"))
    assert dados["nome"] == "Adulto"
    assert dados["supervisao"]["ambito"] == ["alterar_layout", "alterar_tema", "definicoes"]
