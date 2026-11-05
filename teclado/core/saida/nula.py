"""Saida sem injecao de teclas: usada em Linux ate a fase 8 (uinput).

A interface, as definicoes, o telemovel, as sugestoes e os teclados funcionam normalmente.
O que se escreve no teclado nao chega a outras aplicacoes.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)
AVISO = "Injecao de teclas ainda nao disponivel neste sistema: o texto nao chega as aplicacoes."


class SaidaNula:
    def __init__(self) -> None:
        log.warning(AVISO)

    def escrever(self, texto: str) -> None:
        pass

    def tecla(self, nome: str) -> None:
        pass

    def sequencia(self, acoes: list[tuple[str, str]]) -> None:
        pass

    def colar_texto(self, texto: str) -> None:
        pass

    def atalho(self, nome: str) -> None:
        pass

    def enviar_atalho(self, passo: str) -> None:
        pass

    def janela_ativa(self, acao: str, excluir: int = 0) -> bool:
        return False

    def ler_selecao(self) -> str:
        return ""
