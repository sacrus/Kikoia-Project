import pytest

from teclado.core.perfil import criar_perfil
from teclado.core.politica import (
    ACAO_APRENDER_PALAVRA,
    Decisao,
    PedidoAprovacaoNecessario,
    ativar_supervisao,
    decidir,
    executar_acao,
)


def _supervisionado():
    return criar_perfil("Criança", supervisionado=True, pin="1234")


def test_supervisao_bloqueia_configuracoes():
    perfil = _supervisionado()
    assert decidir(perfil, "alterar_layout") is Decisao.PEDIR_APROVACAO
    assert decidir(perfil, "alterar_tema") is Decisao.PEDIR_APROVACAO
    assert decidir(perfil, "definicoes") is Decisao.PEDIR_APROVACAO


def test_aprender_palavra_nunca_bloqueada():
    assert decidir(_supervisionado(), ACAO_APRENDER_PALAVRA) is Decisao.PERMITIR


def test_perfil_livre_nao_bloqueia():
    perfil = criar_perfil("Adulto", supervisionado=False)
    assert decidir(perfil, "alterar_layout") is Decisao.PERMITIR


def test_executar_bloqueado_sem_pin():
    perfil = _supervisionado()
    feito = []
    with pytest.raises(PedidoAprovacaoNecessario):
        executar_acao(perfil, "alterar_layout", lambda: feito.append(1))
    assert feito == []


def test_executar_com_pin_correto():
    perfil = _supervisionado()
    feito = []
    executar_acao(perfil, "alterar_layout", lambda: feito.append(1), pin="1234")
    assert feito == [1]


def test_executar_com_pin_errado_bloqueado():
    perfil = _supervisionado()
    with pytest.raises(PedidoAprovacaoNecessario):
        executar_acao(perfil, "alterar_layout", lambda: None, pin="0000")


def test_desligar_supervisao_exige_pin_do_adulto():
    perfil = _supervisionado()
    def desligar():
        perfil.supervisao.ativa = False
    with pytest.raises(PedidoAprovacaoNecessario):
        executar_acao(perfil, "definicoes", desligar)
    assert perfil.supervisao.ativa is True
    executar_acao(perfil, "definicoes", desligar, pin="1234")
    assert perfil.supervisao.ativa is False


def test_ativar_supervisao_define_pin():
    perfil = criar_perfil("Adulto", supervisionado=False)
    ativar_supervisao(perfil, "9999")
    assert perfil.supervisao.ativa is True
    assert decidir(perfil, "alterar_tema") is Decisao.PEDIR_APROVACAO
