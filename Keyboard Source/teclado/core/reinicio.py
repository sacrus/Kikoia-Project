"""Reinicio do Kikoia: abre outra instancia com o mesmo programa (ex.: ao mudar o idioma)."""

from __future__ import annotations

import sys

# A nova instancia espera que a anterior liberte o servidor e as portas antes de arrancar.
ARGUMENTO = "--reiniciar"


def comando_reinicio(congelado: bool, executavel: str) -> list[str]:
    """Argumentos para arrancar de novo: o executavel (empacotado) ou 'python -m teclado'."""
    base = [executavel] if congelado else [executavel, "-m", "teclado"]
    return [*base, ARGUMENTO]


def comando_do_processo() -> list[str]:
    return comando_reinicio(bool(getattr(sys, "frozen", False)), sys.executable)
