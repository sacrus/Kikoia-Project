import sys

import pytest

from teclado.core.saida import criar_saida
from teclado.core.saida.nula import SaidaNula


@pytest.mark.skipif(sys.platform != "linux", reason="uinput so existe em Linux")
def test_linux_sem_uinput_usa_saida_sem_injecao(monkeypatch):
    class SemPermissao:
        def __init__(self):
            raise RuntimeError("Sem acesso a /dev/uinput")

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("teclado.core.saida.linux.SaidaLinux", SemPermissao)
    saida = criar_saida()
    assert isinstance(saida, SaidaNula)


def test_saida_sem_injecao_aceita_todas_as_chamadas():
    saida = SaidaNula()
    saida.escrever("olá")
    saida.tecla("enter")
    saida.sequencia([("texto", "a"), ("tecla", "enter")])
    saida.colar_texto("texto ditado")
    saida.atalho("apagar_palavra")
    saida.enviar_atalho("ctrl+c")
    assert saida.janela_ativa("minimizar_janela") is False
    assert saida.ler_selecao() == ""
