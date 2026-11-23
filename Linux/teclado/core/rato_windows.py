"""Rato virtual no Windows: SendInput com movimento relativo e botoes do rato."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _UniaoRato(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class ENTRADA_RATO(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _UniaoRato)]


_BOTOES = {
    "esquerdo": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "direito": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
}


class RatoWindows:
    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._enviar_entrada = self._user32.SendInput
        self._enviar_entrada.argtypes = (wintypes.UINT, ctypes.POINTER(ENTRADA_RATO), ctypes.c_int)
        self._enviar_entrada.restype = wintypes.UINT

    def _enviar(self, entradas: list[ENTRADA_RATO]) -> None:
        arranjo = (ENTRADA_RATO * len(entradas))(*entradas)
        self._enviar_entrada(len(arranjo), arranjo, ctypes.sizeof(ENTRADA_RATO))

    @staticmethod
    def _entrada(flags: int, dx: int = 0, dy: int = 0) -> ENTRADA_RATO:
        entrada = ENTRADA_RATO()
        entrada.type = INPUT_MOUSE
        entrada.u.mi.dx = dx
        entrada.u.mi.dy = dy
        entrada.u.mi.dwFlags = flags
        return entrada

    def mover(self, dx: int, dy: int) -> None:
        self._enviar([self._entrada(MOUSEEVENTF_MOVE, dx, dy)])

    def clicar(self, botao: str, vezes: int = 1) -> None:
        baixo, cima = _BOTOES[botao]
        entradas = []
        for _ in range(vezes):
            entradas.append(self._entrada(baixo))
            entradas.append(self._entrada(cima))
        self._enviar(entradas)

    def pressionar(self, botao: str) -> None:
        self._enviar([self._entrada(_BOTOES[botao][0])])

    def soltar(self, botao: str) -> None:
        self._enviar([self._entrada(_BOTOES[botao][1])])

    def rolar(self, entalhes: int) -> None:
        """Roda do rato: positivo sobe, negativo desce (um entalhe = WHEEL_DELTA)."""
        entrada = self._entrada(MOUSEEVENTF_WHEEL)
        entrada.u.mi.mouseData = (entalhes * WHEEL_DELTA) & 0xFFFFFFFF
        self._enviar([entrada])

    def fechar(self) -> None:
        pass
