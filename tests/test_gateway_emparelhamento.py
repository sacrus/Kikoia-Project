import pytest

from teclado.gateway.emparelhamento import (
    VALIDADE_SEGUNDOS,
    CodigoEmparelhamento,
    CodigoEsgotado,
    CodigoExpirado,
    CodigoUsado,
    gerar_codigo,
)


class Relogio:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def avancar(self, s):
        self.t += s


def test_codigo_tem_seis_digitos():
    for _ in range(50):
        c = gerar_codigo()
        assert len(c) == 6 and c.isdigit()


def test_codigo_correto_emparelha():
    c = CodigoEmparelhamento("123456", agora=Relogio())
    assert c.verificar("123456") is True
    assert c.estado == "usado"


def test_codigo_com_separadores_aceite():
    c = CodigoEmparelhamento("123456", agora=Relogio())
    assert c.verificar("123 456") is True


def test_codigo_errado_nao_emparelha_e_conta_falha():
    c = CodigoEmparelhamento("123456", agora=Relogio())
    assert c.verificar("000000") is False
    assert c.tentativas_restantes == 2


def test_tres_falhas_esgotam_o_codigo():
    c = CodigoEmparelhamento("123456", agora=Relogio())
    for _ in range(3):
        c.verificar("000000")
    assert c.estado == "esgotado"
    with pytest.raises(CodigoEsgotado):
        c.verificar("123456")  # mesmo o codigo certo ja nao funciona


def test_codigo_expira_ao_fim_de_dois_minutos():
    relogio = Relogio()
    c = CodigoEmparelhamento("123456", agora=relogio)
    relogio.avancar(VALIDADE_SEGUNDOS + 1)
    assert c.estado == "expirado"
    with pytest.raises(CodigoExpirado):
        c.verificar("123456")


def test_codigo_ainda_valido_perto_do_limite():
    relogio = Relogio()
    c = CodigoEmparelhamento("123456", agora=relogio)
    relogio.avancar(VALIDADE_SEGUNDOS - 1)
    assert c.verificar("123456") is True


def test_codigo_usado_nao_aceita_segunda_vez():
    c = CodigoEmparelhamento("123456", agora=Relogio())
    c.verificar("123456")
    with pytest.raises(CodigoUsado):
        c.verificar("123456")


def test_falhas_nao_contam_depois_de_expirar_e_mensagem_e_clara():
    relogio = Relogio()
    c = CodigoEmparelhamento("123456", agora=relogio)
    c.verificar("000000")
    relogio.avancar(VALIDADE_SEGUNDOS + 1)
    with pytest.raises(CodigoExpirado, match="novo"):
        c.verificar("123456")


def test_codigo_mal_formado_na_criacao_recusado():
    with pytest.raises(ValueError):
        CodigoEmparelhamento("12345")
    with pytest.raises(ValueError):
        CodigoEmparelhamento("12a456")
