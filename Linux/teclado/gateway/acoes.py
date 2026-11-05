"""Aplica no editor do PC uma acao recebida do telemovel (ja validada pelo protocolo)."""

from __future__ import annotations

import zlib
from typing import Any


def aplicar_acao_remota(editor: Any, acao: dict[str, Any]) -> None:
    """Executa a acao no editor, exatamente como se a tecla tivesse sido carregada no PC.

    'navegar' nao e aplicado: o telemovel muda de teclado por si e so envia a acao
    para o PC quando e uma tecla de escrita.
    """
    tipo = acao["tipo"]
    valor = acao["valor"]
    if tipo == "texto":
        editor.texto(valor)
    elif tipo == "tecla":
        editor.tecla(valor)
    elif tipo == "acento":
        editor.acento(valor)
    elif tipo == "modificador":
        editor.modificador(valor)
    elif tipo == "multitoque":
        # Chave estavel para o mesmo botao, para que toques seguidos percorram as letras.
        editor.multitoque(zlib.crc32(valor.encode("utf-8")), valor)
    elif tipo == "acao":
        editor.acao(valor)
    # "navegar": ignorado (ver docstring)
