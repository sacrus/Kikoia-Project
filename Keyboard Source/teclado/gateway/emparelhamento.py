"""Codigo de emparelhamento de 6 digitos (G1).

Regras:
- Valido 120 s a partir da criacao.
- Ate 3 tentativas erradas; ao fim delas o codigo fica invalido.
- Ao emparelhar com sucesso, o codigo fica usado e nao aceita mais tentativas.

Nota: o codigo e curto, por isso a troca real usa SPAKE2 (G2), que nao permite
testar codigos offline. Esta classe so decide a validade do codigo.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable

VALIDADE_SEGUNDOS = 120.0
MAX_FALHAS = 3
DIGITOS = 6


class EmparelhamentoErro(RuntimeError):
    """Codigo nao pode ser usado. A mensagem e para mostrar ao utilizador."""


class CodigoExpirado(EmparelhamentoErro):
    pass


class CodigoEsgotado(EmparelhamentoErro):
    pass


class CodigoUsado(EmparelhamentoErro):
    pass


def gerar_codigo() -> str:
    """Codigo aleatorio criptograficamente seguro, com zeros a esquerda."""
    return f"{secrets.randbelow(10 ** DIGITOS):0{DIGITOS}d}"


def _so_digitos(texto: str) -> str:
    # Aceita "123 456" ou "123-456", como se escreve normalmente.
    return "".join(c for c in texto if c.isdigit())


class CodigoEmparelhamento:
    def __init__(
        self,
        codigo: str | None = None,
        agora: Callable[[], float] | None = None,
    ) -> None:
        self._agora = agora or time.monotonic
        self.codigo = codigo or gerar_codigo()
        if len(self.codigo) != DIGITOS or not self.codigo.isdigit():
            raise ValueError("o codigo deve ter 6 digitos")
        self._criado = self._agora()
        self._falhas = 0
        self._usado = False

    def segundos_restantes(self) -> float:
        return max(0.0, VALIDADE_SEGUNDOS - (self._agora() - self._criado))

    @property
    def tentativas_restantes(self) -> int:
        return max(0, MAX_FALHAS - self._falhas)

    @property
    def estado(self) -> str:
        if self._usado:
            return "usado"
        if self._falhas >= MAX_FALHAS:
            return "esgotado"
        if self._agora() - self._criado > VALIDADE_SEGUNDOS:
            return "expirado"
        return "ativo"

    def registar_falha(self) -> None:
        """Conta uma falha vinda do protocolo (ex.: confirmacao SPAKE2 errada)."""
        if self.estado == "ativo":
            self._falhas += 1

    def verificar(self, tentativa: str) -> bool:
        """True se o codigo estiver certo. Lanca EmparelhamentoErro se ja nao puder ser usado."""
        estado = self.estado
        if estado == "usado":
            raise CodigoUsado("Este código já foi usado. Gere um novo no computador.")
        if estado == "esgotado":
            raise CodigoEsgotado("Demasiadas tentativas erradas. Gere um novo código no computador.")
        if estado == "expirado":
            raise CodigoExpirado("Este código expirou. Gere um novo no computador.")

        digitos = _so_digitos(tentativa)
        correto = secrets.compare_digest(digitos.encode("utf-8"), self.codigo.encode("utf-8"))
        if not correto:
            self._falhas += 1
            return False
        self._usado = True
        return True
