import pytest

from teclado.gateway.protocolo import ProtocoloErro, codificar, descodificar

CHAVE = b"k" * 32


def test_pedido_de_interruptor_valido():
    dados = codificar(CHAVE, "interruptor", "i1", 0, {"nome": "falar", "ligado": True})
    msg = descodificar(CHAVE, dados, 0)
    assert msg["nome"] == "falar" and msg["ligado"] is True


@pytest.mark.parametrize("corpo", [
    {"nome": "outro", "ligado": True},
    {"nome": "ditar", "ligado": "sim"},
    {"nome": "ditar"},
])
def test_pedido_de_interruptor_invalido_e_recusado(corpo):
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "interruptor", "i1", 0, corpo)


def test_estado_dos_interruptores_valido():
    estado = {"falar": False, "falar_disponivel": True, "ditar": True, "ditar_disponivel": False}
    dados = codificar(CHAVE, "interruptores", "i2", 0, estado)
    assert descodificar(CHAVE, dados, 0)["ditar_disponivel"] is False


def test_estado_dos_interruptores_incompleto_e_recusado():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "interruptores", "i2", 0, {"falar": True})
