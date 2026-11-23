"""Rato virtual no Linux (uinput): dispositivo separado do teclado, com movimento relativo e botoes.

Usa o mesmo acesso a /dev/uinput que o teclado (ver tools/configurar_teclado_linux.sh).
"""

from __future__ import annotations

import fcntl
import os
import time

from teclado.core.saida.uinput import (
    _BUS_USB,
    _DISPOSITIVO,
    _EVENTO,
    _SINCRONIZAR,
    _UI_DEV_CREATE,
    _UI_DEV_DESTROY,
    _UI_SET_EVBIT,
    _UI_SET_KEYBIT,
    _VETORES_ABS,
    EV_KEY,
    EV_SYN,
    UINPUT,
)

EV_REL = 0x02
REL_X = 0x00
REL_Y = 0x01
REL_WHEEL = 0x08
_UI_SET_RELBIT = 0x40045566
BTN_LEFT = 0x110
BTN_RIGHT = 0x111
_BOTAO = {"esquerdo": BTN_LEFT, "direito": BTN_RIGHT}


class RatoLinux:
    def __init__(self, nome: str = "Kikoia Rato") -> None:
        try:
            self._fd = os.open(UINPUT, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as erro:
            raise RuntimeError(f"Sem acesso a {UINPUT} ({erro}).") from erro
        try:
            fcntl.ioctl(self._fd, _UI_SET_EVBIT, EV_KEY)
            fcntl.ioctl(self._fd, _UI_SET_EVBIT, EV_REL)
            fcntl.ioctl(self._fd, _UI_SET_EVBIT, EV_SYN)
            for codigo in _BOTAO.values():
                fcntl.ioctl(self._fd, _UI_SET_KEYBIT, codigo)
            for codigo in (REL_X, REL_Y, REL_WHEEL):
                fcntl.ioctl(self._fd, _UI_SET_RELBIT, codigo)
            descricao = _DISPOSITIVO.pack(nome.encode("utf-8")[:79], _BUS_USB, 0x1209, 0x7EE2, 1, 0)
            os.write(self._fd, descricao + _VETORES_ABS)
            fcntl.ioctl(self._fd, _UI_DEV_CREATE)
        except OSError as erro:
            os.close(self._fd)
            raise RuntimeError(f"Nao foi possivel criar o rato virtual ({erro}).") from erro
        time.sleep(0.5)  # o sistema precisa de ver o dispositivo novo antes do primeiro movimento

    def _evento(self, tipo: int, codigo: int, valor: int) -> None:
        os.write(self._fd, _EVENTO.pack(0, 0, tipo, codigo, valor))
        os.write(self._fd, _SINCRONIZAR)

    def mover(self, dx: int, dy: int) -> None:
        if dx:
            self._evento(EV_REL, REL_X, dx)
        if dy:
            self._evento(EV_REL, REL_Y, dy)

    def pressionar(self, botao: str) -> None:
        self._evento(EV_KEY, _BOTAO[botao], 1)

    def soltar(self, botao: str) -> None:
        self._evento(EV_KEY, _BOTAO[botao], 0)

    def rolar(self, entalhes: int) -> None:
        if entalhes:
            self._evento(EV_REL, REL_WHEEL, entalhes)

    def clicar(self, botao: str, vezes: int = 1) -> None:
        codigo = _BOTAO[botao]
        for _ in range(vezes):
            self._evento(EV_KEY, codigo, 1)
            self._evento(EV_KEY, codigo, 0)

    def fechar(self) -> None:
        try:
            fcntl.ioctl(self._fd, _UI_DEV_DESTROY)
        finally:
            os.close(self._fd)
