"""Deteta se o Quadro Interativo é a janela em foco (Windows e Linux X11/XWayland)."""

from __future__ import annotations

import ctypes
import sys

TITULO_QUADRO = "Kikoia - Quadro Interativo"
_USER32 = None
_BUFFER_TITULO = ctypes.create_unicode_buffer(256)
_DISPLAY_X11 = None


def _obter_user32():
    global _USER32
    if _USER32 is None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        _USER32 = user32
    return _USER32


def _titulo_janela_ativa_x11() -> str:
    """Lê o título (`_NET_WM_NAME` ou `WM_NAME`) da janela ativa no servidor X11/XWayland."""
    global _DISPLAY_X11
    try:
        from Xlib import X, display

        if _DISPLAY_X11 is None:
            _DISPLAY_X11 = display.Display()
        d = _DISPLAY_X11
        raiz = d.screen().root
        prop = raiz.get_full_property(d.intern_atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType)
        if prop is None or not prop.value or not prop.value[0]:
            return ""
        wid = int(prop.value[0])
        if wid <= 0:
            return ""
        janela = d.create_resource_object("window", wid)
        net_wm_name = janela.get_full_property(d.intern_atom("_NET_WM_NAME"), X.AnyPropertyType)
        if net_wm_name is not None and net_wm_name.value:
            valor = net_wm_name.value
            if isinstance(valor, bytes):
                return valor.decode("utf-8", "replace")
            if isinstance(valor, str):
                return valor
            return bytes(valor).decode("utf-8", "replace")
        nome = janela.get_wm_name()
        return nome if isinstance(nome, str) else ""
    except Exception:
        if _DISPLAY_X11 is not None:
            try:
                _DISPLAY_X11.close()
            except Exception:
                pass
            _DISPLAY_X11 = None
        return ""


def quadro_em_foco() -> bool:
    if sys.platform == "win32":
        user32 = _obter_user32()
        janela = user32.GetForegroundWindow()
        if not janela:
            return False
        user32.GetWindowTextW(janela, _BUFFER_TITULO, len(_BUFFER_TITULO))
        return _BUFFER_TITULO.value == TITULO_QUADRO
    if sys.platform.startswith("linux"):
        return _titulo_janela_ativa_x11() == TITULO_QUADRO
    return False
