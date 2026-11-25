"""Rato virtual: move o cursor e envia cliques ao sistema (usado pelo touchpad do telemovel).

Cada sistema tem a sua implementacao. Sem permissao ou sem suporte, usa-se RatoNulo:
o teclado continua a funcionar, so o touchpad fica sem efeito (com aviso no registo).
"""

from __future__ import annotations

import logging
import sys

from teclado.core.toque import RatoNulo

log = logging.getLogger(__name__)


def criar_rato():
    if sys.platform == "win32":
        from teclado.core.rato_windows import RatoWindows

        return RatoWindows()
    if sys.platform.startswith("linux"):
        try:
            from teclado.core.rato_linux import RatoLinux

            return RatoLinux()
        except RuntimeError as erro:
            log.error("Rato virtual indisponivel: %s", erro)
    return RatoNulo()
