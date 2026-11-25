"""Decide se uma acao precisa de aprovacao do adulto.

A supervisao aplica-se apenas a configuracoes (layout, tema, definicoes).
A aprendizagem de palavras nunca e bloqueada.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from .perfil import AMBITOS_VALIDOS, Perfil, Supervisao
from .seguranca import gerar_hash_pin, verificar_pin

ACAO_APRENDER_PALAVRA = "aprender_palavra"


class Decisao(Enum):
    PERMITIR = "permitir"
    PEDIR_APROVACAO = "pedir_aprovacao"


class PedidoAprovacaoNecessario(Exception):
    """Lancada quando a acao so pode avancar com o codigo do adulto."""


def decidir(perfil: Perfil, acao: str) -> Decisao:
    sup = perfil.supervisao
    if sup.ativa and acao in sup.ambito and acao in AMBITOS_VALIDOS:
        return Decisao.PEDIR_APROVACAO
    return Decisao.PERMITIR


def aprovar(perfil: Perfil, pin: str) -> bool:
    return verificar_pin(pin, perfil.supervisao.codigo_hash)


def executar_acao(
    perfil: Perfil,
    acao: str,
    executar: Callable[[], None],
    pin: str | None = None,
) -> None:
    """Executa a acao se estiver permitida ou se o PIN do adulto estiver correto."""
    if decidir(perfil, acao) is Decisao.PERMITIR:
        executar()
        return
    if pin is not None and aprovar(perfil, pin):
        executar()
        return
    raise PedidoAprovacaoNecessario(acao)


def ativar_supervisao(perfil: Perfil, pin: str) -> None:
    """Ativa a supervisao e define o codigo do adulto (sem executar_acao: e a propria definicao)."""
    perfil.supervisao = Supervisao(
        ativa=True,
        codigo_hash=gerar_hash_pin(pin),
        ambito=list(perfil.supervisao.ambito),
    )
