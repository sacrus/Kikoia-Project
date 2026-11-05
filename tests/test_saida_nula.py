import sys

from teclado.core.saida import criar_saida
from teclado.core.saida.nula import SaidaNula


def test_linux_usa_saida_sem_injecao(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
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
