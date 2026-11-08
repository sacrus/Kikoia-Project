"""Barra de ancoragem no fundo do ecra (Windows: AppBar do shell).

Com a barra registada, o Windows reserva a parte inferior do ecra: as janelas
maximizadas (Word, browser, Bloco de Notas) passam a ocupar so a area acima do
teclado. Em outros sistemas esta classe nao faz nada e o teclado fica so posicionado.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

WM_APPBAR_CALLBACK = 0x0400 + 100  # mensagem que o shell envia a janela (nao tratada aqui)
ABM_NEW, ABM_REMOVE, ABM_QUERYPOS, ABM_SETPOS = 0x0, 0x1, 0x2, 0x3
ABE_BOTTOM = 3
SPI_GETWORKAREA = 0x0030
SM_CXSCREEN, SM_CYSCREEN = 0, 1


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class _APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", _RECT),
        ("lParam", wintypes.LPARAM),
    ]


class BarraInferior:
    """Regista uma janela como barra no fundo. Coordenadas em pixeis fisicos."""

    def __init__(self) -> None:
        self._disponivel = sys.platform == "win32"
        self._ativa = False
        self._hwnd = 0
        if self._disponivel:
            self._shell = ctypes.WinDLL("shell32")
            self._user32 = ctypes.WinDLL("user32")
            self._shell.SHAppBarMessage.restype = ctypes.c_size_t
            self._shell.SHAppBarMessage.argtypes = (wintypes.DWORD, ctypes.POINTER(_APPBARDATA))
            self._user32.SystemParametersInfoW.argtypes = (
                wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT,
            )
            self._user32.SystemParametersInfoW.restype = wintypes.BOOL
            self._user32.GetSystemMetrics.argtypes = (ctypes.c_int,)
            self._user32.GetSystemMetrics.restype = ctypes.c_int

    @property
    def registada(self) -> bool:
        return self._ativa

    def preparar(self, wid: int) -> None:
        """Nada a fazer no Windows (so existe em X11)."""

    def area_base(self) -> None:
        """So existe em X11: no Windows a area util e lida com area_de_trabalho()."""
        return None

    def _dados(self, rc: _RECT | None = None) -> _APPBARDATA:
        dados = _APPBARDATA()
        dados.cbSize = ctypes.sizeof(_APPBARDATA)
        dados.hWnd = self._hwnd
        dados.uCallbackMessage = WM_APPBAR_CALLBACK
        dados.uEdge = ABE_BOTTOM
        if rc is not None:
            dados.rc = rc
        return dados

    def registar(self, hwnd: int) -> bool:
        if not self._disponivel or not hwnd:
            return False
        if self._ativa:
            return True
        self._hwnd = hwnd
        dados = self._dados()
        if not self._shell.SHAppBarMessage(ABM_NEW, ctypes.byref(dados)):
            self._hwnd = 0
            return False
        self._ativa = True
        return True

    def posicionar(self, altura: int) -> tuple[int, int, int, int] | None:
        """Reserva 'altura' pixeis no fundo (ajustado ao que o shell permitir). Devolve (x, y, w, h)."""
        if not self._ativa:
            return None
        ecra = _RECT(0, 0, self._user32.GetSystemMetrics(SM_CXSCREEN),
                     self._user32.GetSystemMetrics(SM_CYSCREEN))
        dados = self._dados(ecra)
        # O shell devolve a area livre (descontando a barra de tarefas); so se fixa a altura.
        self._shell.SHAppBarMessage(ABM_QUERYPOS, ctypes.byref(dados))
        dados.rc.top = dados.rc.bottom - altura
        self._shell.SHAppBarMessage(ABM_SETPOS, ctypes.byref(dados))
        r = dados.rc
        return r.left, r.top, r.right - r.left, r.bottom - r.top

    def remover(self) -> None:
        if not self._ativa:
            return
        self._shell.SHAppBarMessage(ABM_REMOVE, ctypes.byref(self._dados()))
        self._ativa = False
        self._hwnd = 0

    def area_de_trabalho(self) -> tuple[int, int, int, int] | None:
        """Area util do ecra (left, top, right, bottom). Util para verificar a reserva."""
        if not self._disponivel:
            return None
        area = _RECT()
        self._user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(area), 0)
        return area.left, area.top, area.right, area.bottom
