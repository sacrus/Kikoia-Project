"""Teclado virtual no Linux (uinput): o sistema recebe as teclas como de um teclado fisico.

Funciona em Wayland e X11, em qualquer aplicacao. Precisa de acesso de escrita a
/dev/uinput: ver tools/configurar_teclado_linux.sh.
"""

from __future__ import annotations

import fcntl
import os
import struct
import time

UINPUT = "/dev/uinput"
EV_SYN = 0x00
EV_KEY = 0x01
SYN_REPORT = 0
TECLA_MAXIMA = 0x2FF  # KEY_MAX do kernel

_UI_DEV_CREATE = 0x5501
_UI_DEV_DESTROY = 0x5502
_UI_SET_EVBIT = 0x40045564
_UI_SET_KEYBIT = 0x40045565
_BUS_USB = 0x03
# struct uinput_user_dev: nome[80], id (4 x u16), ff_effects_max, e os quatro vetores ABS_CNT (64 x 4 bytes).
_DISPOSITIVO = struct.Struct("=80sHHHHI")
_VETORES_ABS = bytes(4 * 64 * 4)
# struct input_event (64 bits): tempo (2 x long), tipo, codigo, valor.
_EVENTO = struct.Struct("@llHHi")
_SINCRONIZAR = _EVENTO.pack(0, 0, EV_SYN, SYN_REPORT, 0)


class TecladoVirtual:
    def __init__(self, nome: str = "Teclado Remoto") -> None:
        try:
            self._fd = os.open(UINPUT, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as erro:
            raise RuntimeError(f"Sem acesso a {UINPUT} ({erro}).") from erro
        try:
            fcntl.ioctl(self._fd, _UI_SET_EVBIT, EV_KEY)
            for codigo in range(TECLA_MAXIMA + 1):
                fcntl.ioctl(self._fd, _UI_SET_KEYBIT, codigo)
            descricao = _DISPOSITIVO.pack(nome.encode("utf-8")[:79], _BUS_USB, 0x1209, 0x7EE1, 1, 0)
            os.write(self._fd, descricao + _VETORES_ABS)  # o kernel exige a estrutura inteira de uma vez
            fcntl.ioctl(self._fd, _UI_DEV_CREATE)
        except OSError as erro:
            os.close(self._fd)
            raise RuntimeError(f"Nao foi possivel criar o teclado virtual ({erro}).") from erro
        # O sistema precisa de ver o dispositivo novo antes da primeira tecla.
        time.sleep(0.5)

    def enviar(self, eventos: list[tuple[int, bool]]) -> None:
        """Pressiona (True) ou liberta (False) cada tecla, por ordem, com uma sincronizacao depois de cada uma."""
        for codigo, pressionada in eventos:
            os.write(self._fd, _EVENTO.pack(0, 0, EV_KEY, codigo, 1 if pressionada else 0))
            os.write(self._fd, _SINCRONIZAR)

    def fechar(self) -> None:
        try:
            fcntl.ioctl(self._fd, _UI_DEV_DESTROY)
        finally:
            os.close(self._fd)
