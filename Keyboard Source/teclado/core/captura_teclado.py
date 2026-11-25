"""Captura global das teclas fisicas (Windows: WH_KEYBOARD_LL; Linux X11/XWayland: XRecord + XKB).

Envia eventos simplificados ao chamador: ("letra", c), ("separador", c),
("apagar",), ("reiniciar",). Nunca envia o codigo bruto de cada tecla.

- Teclas injetadas pelo proprio software (o teclado virtual, o ditado) sao ignoradas,
  para nao serem contadas duas vezes.
- O gancho corre numa thread propria. Deve ser rapido: nenhuma exceção pode sair do callback.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time
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

# Códigos evdev (Linux: keycode X11 - 8)
EV_BACK, EV_TAB, EV_RETURN, EV_KPENTER, EV_SPACE = 14, 15, 28, 96, 57
EV_MODIFICADORES = frozenset({42, 54, 58, 100})  # Shift Esq/Dir, CapsLock, AltGr
EV_ATALHOS = frozenset({29, 97, 56, 125, 126})   # Ctrl Esq/Dir, Alt Esq, Super Esq/Dir
EV_NAVEGACAO = frozenset({1, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111})


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


# WINFUNCTYPE so existe no Windows: fora dele o modulo importa (para os testes das funcoes puras)
# mas usa XRecord no Linux.
HOOKPROC = (
    ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    if sys.platform == "win32"
    else None
)


def traduzir(vk: int, caractere: str | None, atalho_ativo: bool) -> tuple | None:
    """Converte uma tecla Windows no evento simplificado. Funcao pura, testavel sem Windows."""
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


def traduzir_evdev(evdev: int, caractere: str | None, atalho_ativo: bool) -> tuple | None:
    """Converte um código evdev Linux no mesmo evento simplificado."""
    if evdev in EV_MODIFICADORES:
        return None
    if atalho_ativo or evdev in EV_ATALHOS:
        return ("reiniciar",)
    if evdev == EV_BACK:
        return ("apagar",)
    if evdev in (EV_TAB, EV_RETURN, EV_KPENTER):
        return ("separador", "\n")
    if evdev == EV_SPACE:
        return ("separador", " ")
    if evdev in EV_NAVEGACAO:
        return ("reiniciar",)
    return traduzir(0, caractere, False)


class CapturaTeclado:
    def __init__(self, ao_evento: Callable[[tuple], None]) -> None:
        if sys.platform != "win32" and not sys.platform.startswith("linux"):
            raise RuntimeError("A captura de teclas fisicas nao esta disponivel neste sistema.")
        if sys.platform.startswith("linux"):
            self._validar_linux()
        self._ao_evento = ao_evento
        self._thread: threading.Thread | None = None
        self._tid = 0
        self._pronto = threading.Event()
        self._erro: str | None = None
        self._proc = None  # referencia viva ao callback (senao o Python recolhe-o)
        self._ctx_xrecord = None
        self._disp_ctrl = None

    @staticmethod
    def _validar_linux() -> None:
        if not os.environ.get("DISPLAY"):
            raise RuntimeError("A captura de teclas fisicas requer uma sessao grafica X11/XWayland.")
        try:
            from Xlib import display

            d = display.Display()
            tem_rec = bool(d.has_extension("RECORD"))
            d.close()
        except Exception as erro:
            raise RuntimeError(f"Sem acesso ao servidor X11 para observar teclas ({erro}).") from erro
        if not tem_rec:
            raise RuntimeError("A extensao XRecord nao esta disponivel neste servidor X11.")

    @property
    def ativo(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def ligar(self) -> None:
        if self.ativo:
            return
        self._pronto.clear()
        self._erro = None
        alvo = self._correr if sys.platform == "win32" else self._correr_linux
        self._thread = threading.Thread(target=alvo, daemon=True, name="captura-teclado")
        self._thread.start()
        self._pronto.wait(5.0)
        if self._erro:
            raise RuntimeError(self._erro)

    def desligar(self) -> None:
        if not self.ativo:
            return
        if sys.platform == "win32":
            ctypes.WinDLL("user32").PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        else:
            disp = self._disp_ctrl
            ctx = self._ctx_xrecord
            if disp is not None and ctx is not None:
                try:
                    disp.record_disable_context(ctx)
                    disp.flush()
                except Exception:
                    pass
        if self._thread is not None:
            self._thread.join(2.0)
        self._thread = None

    # --- thread do gancho Linux (XRecord + libxkbcommon) --------------------

    def _correr_linux(self) -> None:
        from Xlib import X, display
        from Xlib.ext import record
        from Xlib.protocol import rq

        from teclado.core.saida import uinput
        from teclado.core.saida.layout import layout_do_sistema
        from teclado.core.saida.xkb import DESLOCAMENTO_XKB, MapaTeclas, _biblioteca

        d_dados = None
        d_ctrl = None
        ctx = None
        lib = None
        estado_xkb = None
        compose_state = None
        compose_table = None
        try:
            mapa = MapaTeclas(*layout_do_sistema())
            lib = _biblioteca()
            lib.xkb_state_new.argtypes, lib.xkb_state_new.restype = [ctypes.c_void_p], ctypes.c_void_p
            lib.xkb_state_unref.argtypes, lib.xkb_state_unref.restype = [ctypes.c_void_p], None
            lib.xkb_state_update_key.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int]
            lib.xkb_state_update_key.restype = ctypes.c_int
            lib.xkb_state_key_get_one_sym.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            lib.xkb_state_key_get_one_sym.restype = ctypes.c_uint32
            lib.xkb_state_key_get_utf8.argtypes = [
                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t,
            ]
            lib.xkb_state_key_get_utf8.restype = ctypes.c_int
            estado_xkb = lib.xkb_state_new(mapa._keymap)

            # Suporte opcional a teclas mortas (ex.: ~ + a -> ã) via xkb_compose
            try:
                c_p, u32, c_int = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
                lib.xkb_compose_table_new_from_locale.argtypes = [c_p, ctypes.c_char_p, c_int]
                lib.xkb_compose_table_new_from_locale.restype = c_p
                lib.xkb_compose_state_new.argtypes, lib.xkb_compose_state_new.restype = [c_p, c_int], c_p
                lib.xkb_compose_state_feed.argtypes, lib.xkb_compose_state_feed.restype = [c_p, u32], c_int
                lib.xkb_compose_state_get_status.argtypes, lib.xkb_compose_state_get_status.restype = [c_p], c_int
                lib.xkb_compose_state_get_utf8.argtypes = [c_p, ctypes.c_char_p, ctypes.c_size_t]
                lib.xkb_compose_state_get_utf8.restype = c_int
                lib.xkb_compose_state_reset.argtypes, lib.xkb_compose_state_reset.restype = [c_p], None
                ctx_xkb = lib.xkb_context_new(0)
                loc = (os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE") or os.environ.get("LANG") or "C").encode()
                compose_table = lib.xkb_compose_table_new_from_locale(ctx_xkb, loc, 0)
                if compose_table:
                    compose_state = lib.xkb_compose_state_new(compose_table, 0)
            except Exception:
                compose_state = None

            d_dados = display.Display()
            d_ctrl = display.Display()
            ctx = d_dados.record_create_context(
                0,
                [record.AllClients],
                [{
                    "core_requests": (0, 0),
                    "core_replies": (0, 0),
                    "ext_requests": (0, 0, 0, 0),
                    "ext_replies": (0, 0, 0, 0),
                    "delivered_events": (0, 0),
                    "device_events": (X.KeyPress, X.KeyRelease),
                    "errors": (0, 0),
                    "client_started": False,
                    "client_died": False,
                }],
            )
            self._disp_ctrl = d_ctrl
            self._ctx_xrecord = ctx
        except Exception as erro:
            self._erro = f"Não foi possível ligar a captura de teclas no Linux ({erro})."
            self._pronto.set()
            for obj in (d_dados, d_ctrl):
                if obj is not None:
                    try:
                        obj.close()
                    except Exception:
                        pass
            return

        teclas_atalho_ativas: set[int] = set()
        campo_evento = rq.EventField(None)

        def _processar_resposta(reply) -> None:
            if reply.category != record.FromServer or reply.client_swapped or not len(reply.data):
                return
            dados = reply.data
            while len(dados):
                try:
                    ev, dados = campo_evento.parse_binary_value(dados, d_dados.display, None, None)
                    kc = int(ev.detail)
                    evdev = kc - DESLOCAMENTO_XKB
                    if evdev < 0:
                        continue
                    pressionada = ev.type == X.KeyPress
                    if evdev in EV_ATALHOS:
                        if pressionada:
                            teclas_atalho_ativas.add(evdev)
                        else:
                            teclas_atalho_ativas.discard(evdev)

                    # Ignora teclas injetadas pelo próprio teclado virtual Kikoia
                    if (time.monotonic() - uinput.ultima_injecao()) < 0.06:
                        lib.xkb_state_update_key(estado_xkb, kc, 1 if pressionada else 0)
                        continue

                    if not pressionada:
                        lib.xkb_state_update_key(estado_xkb, kc, 0)
                        continue

                    atalho = bool(teclas_atalho_ativas) or bool(ev.state & (X.ControlMask | X.Mod1Mask | X.Mod4Mask))
                    caractere = None
                    if not atalho and evdev not in (EV_BACK, EV_TAB, EV_RETURN, EV_KPENTER, EV_SPACE) and evdev not in EV_MODIFICADORES and evdev not in EV_NAVEGACAO:
                        buf = ctypes.create_string_buffer(16)
                        if compose_state is not None:
                            sym = lib.xkb_state_key_get_one_sym(estado_xkb, kc)
                            lib.xkb_compose_state_feed(compose_state, sym)
                            status = lib.xkb_compose_state_get_status(compose_state)
                            if status == 1:  # XKB_COMPOSE_COMPOSING (tecla morta premida)
                                lib.xkb_state_update_key(estado_xkb, kc, 1)
                                continue
                            if status == 2:  # XKB_COMPOSE_COMPOSED
                                n = lib.xkb_compose_state_get_utf8(compose_state, buf, 16)
                                lib.xkb_compose_state_reset(compose_state)
                                if n > 0:
                                    caractere = buf.value[:n].decode("utf-8", "replace")
                            elif status == 3:  # XKB_COMPOSE_CANCELLED
                                lib.xkb_compose_state_reset(compose_state)
                        if caractere is None:
                            n = lib.xkb_state_key_get_utf8(estado_xkb, kc, buf, 16)
                            if n > 0:
                                caractere = buf.value[:n].decode("utf-8", "replace")

                    lib.xkb_state_update_key(estado_xkb, kc, 1)
                    evento = traduzir_evdev(evdev, caractere, atalho)
                    if evento is not None:
                        self._ao_evento(evento)
                except Exception:
                    log.error("Erro na captura de teclas Linux", exc_info=True)
                    break

        self._pronto.set()
        try:
            d_dados.record_enable_context(ctx, _processar_resposta)
        except Exception:
            pass
        finally:
            self._ctx_xrecord = None
            self._disp_ctrl = None
            try:
                if ctx is not None and d_ctrl is not None:
                    d_ctrl.record_free_context(ctx)
            except Exception:
                pass
            for obj in (d_dados, d_ctrl):
                if obj is not None:
                    try:
                        obj.close()
                    except Exception:
                        pass
            if estado_xkb is not None and lib is not None:
                try:
                    lib.xkb_state_unref(estado_xkb)
                except Exception:
                    pass

    # --- thread do gancho Windows -------------------------------------------

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
        user32.GetWindowThreadProcessId.argtypes = (wintypes.DWORD,) if False else (ctypes.c_void_p, ctypes.c_void_p)
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
