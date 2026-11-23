"""Deteta se o Quadro Interativo é a janela em foco (só Windows nesta versão)."""

from __future__ import annotations

import ctypes
import sys

TITULO_QUADRO = "Kikoia - Quadro Interativo"


def quadro_em_foco() -> bool:
    if sys.platform != "win32":
        return False
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    janela = user32.GetForegroundWindow()
    if not janela:
        return False
    titulo = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(janela, titulo, len(titulo))
    return titulo.value == TITULO_QUADRO
