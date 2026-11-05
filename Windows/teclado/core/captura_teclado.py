"""Captura global das teclas fisicas no Windows (gancho WH_KEYBOARD_LL).

Envia eventos simplificados ao chamador: ("letra", c), ("separador", c),
("apagar",), ("reiniciar",). Nunca envia o codigo bruto de cada tecla.

- Teclas injetadas pelo proprio software (o teclado virtual, o ditado) sao ignoradas,
  para nao serem contadas duas vezes.
- O gancho corre numa thread propria com ciclo de mensagens. Deve ser rapido: nenhuma
  exceção pode sair do callback (o Windows desligaria o gancho).
"""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
from collections.abc import Callable
from ctypes import wintypes

log = logging.getLogger(__name__)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012
HC_ACTION = 0
LLKHF_INJECTED = 0x10

VK_BACK, VK_TAB, VK_RETURN, VK_SPACE = 0x08, 0x09, 0x0D, 0x20
VK_SHIFT, VK_CONTROL, VK_MENU, VK_CAPITAL = 0x10, 0x11, 0x12, 0x14
VK_LWIN, VK_RWIN = 0x5B, 0x5C
VK_NAVEGACAO = frozenset({0x1B, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E})
VK_MODIFICADORES = frozenset({VK_SHIFT, VK_CAPITAL, 0xA0, 0xA1})  # shifts; nao alteram a palavra


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


# WINFUNCTYPE so existe no Windows: fora dele o modulo importa (para os testes das funcoes puras)
# mas nao cria o gancho.
HOOKPROC = (
    ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    if sys.platform == "win32"
    else None
)


def traduzir(vk: int, caractere: str | None, atalho_ativo: bool) -> tuple | None:
    """Converte uma tecla no evento simplificado. Funcao pura, testavel sem Windows."""
    if vk in VK_MODIFICADORES:
        return None
    if atalho_ativo:
        return ("reiniciar",)           # Ctrl/Alt/Win: pode mudar o texto, nao e palavra
    if vk == VK_BACK:
        return ("apagar",)
    if vk in (VK_TAB, VK_RETURN):
        return ("separador", "\n")
    if vk == VK_SPACE:
        return ("separador", " ")
    if vk in VK_NAVEGACAO:
        return ("reiniciar",)
    if not caractere:
        return None
    if caractere.isalpha():
        return ("letra", caractere)
    if caractere.isprintable():
        return ("separador", caractere)  # pontuacao, simbolos
    return None


class CapturaTeclado:
    def __init__(self, ao_evento: Callable[[tuple], None]) -> None:
        if sys.platform != "win32":
            raise RuntimeError("A captura de teclas fisicas so existe no Windows nesta versao.")
        self._ao_evento = ao_evento
        self._thread: threading.Thread | None = None
        self._tid = 0
        self._pronto = threading.Event()
        self._erro: str | None = None
        self._proc = None  # referencia viva ao callback (senao o Python recolhe-o)

    @property
    def ativo(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def ligar(self) -> None:
        if self.ativo:
            return
        self._pronto.clear()
        self._erro = None
        self._thread = threading.Thread(target=self._correr, daemon=True, name="captura-teclado")
        self._thread.start()
        self._pronto.wait(5.0)
        if self._erro:
            raise RuntimeError(self._erro)

    def desligar(self) -> None:
        if not self.ativo:
            return
        ctypes.WinDLL("user32").PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        self._thread.join(2.0)
        self._thread = None

    # --- thread do gancho ---------------------------------------------------

    def _correr(self) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._user32 = user32
        user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD)
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.CallNextHookEx.argtypes = (ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        user32.GetAsyncKeyState.restype = ctypes.c_short
        user32.GetKeyState.argtypes = (ctypes.c_int,)
        user32.GetKeyState.restype = ctypes.c_short
        user32.ToUnicodeEx.argtypes = (
            wintypes.UINT, wintypes.UINT, ctypes.c_void_p,
            wintypes.LPWSTR, ctypes.c_int, wintypes.UINT, ctypes.c_void_p,
        )
        user32.ToUnicodeEx.restype = ctypes.c_int
        # Handles sao ponteiros: sem isto o ctypes trunca-os em 64 bits.
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        user32.GetKeyboardLayout.argtypes = (wintypes.DWORD,)
        user32.GetKeyboardLayout.restype = ctypes.c_void_p
        user32.GetWindowThreadProcessId.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        kernel32.GetModuleHandleW.restype = ctypes.c_void_p

        self._proc = HOOKPROC(self._gancho)
        gancho = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0,
        )
        if not gancho:
            self._erro = f"Não foi possível ligar a captura de teclas (erro {ctypes.get_last_error()})."
            self._pronto.set()
            return
        self._tid = kernel32.GetCurrentThreadId()
        self._pronto.set()

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        user32.UnhookWindowsHookEx(gancho)

    def _gancho(self, codigo, wparam, lparam):
        try:
            if codigo == HC_ACTION and wparam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                info = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if not info.flags & LLKHF_INJECTED:
                    evento = self._evento(info.vkCode, info.scanCode)
                    if evento is not None:
                        self._ao_evento(evento)
        except Exception:
            log.error("Erro na captura de teclas", exc_info=True)
        return self._user32.CallNextHookEx(None, codigo, wparam, lparam)

    def _evento(self, vk: int, scan: int) -> tuple | None:
        user32 = self._user32
        atalho = any(
            user32.GetAsyncKeyState(tecla) & 0x8000
            for tecla in (VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN)
        )
        caractere = None if atalho or vk in (VK_BACK, VK_TAB, VK_RETURN) else self._caractere(vk, scan)
        return traduzir(vk, caractere, atalho)

    def _caractere(self, vk: int, scan: int) -> str | None:
        """Caracter produzido pela tecla no layout atual (inclui acentos e shift)."""
        user32 = self._user32
        estado = (ctypes.c_ubyte * 256)()
        if user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
            estado[VK_SHIFT] = 0x80
        if user32.GetKeyState(VK_CAPITAL) & 0x0001:
            estado[VK_CAPITAL] = 0x01
        janela = user32.GetForegroundWindow()
        thread = user32.GetWindowThreadProcessId(janela, None) if janela else 0
        layout = user32.GetKeyboardLayout(thread)
        buffer = ctypes.create_unicode_buffer(8)
        # Flag 4: nao altera o estado de teclas mortas (ex.: acento antes de uma letra).
        n = user32.ToUnicodeEx(vk, scan, estado, buffer, 8, 0x4, layout)
        if n <= 0:
            return None  # <0 = tecla morta (acento): ignorada, nao e palavra ainda
        return buffer.value[:n] or None
