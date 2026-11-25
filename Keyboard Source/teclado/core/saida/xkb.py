"""Mapa de teclas do layout do sistema, com libxkbcommon.

O uinput envia codigos de tecla fisicos (evdev). Para escrever um caracter, pergunta-se
ao libxkbcommon que tecla, e com que modificadores, o produz no layout ativo. Assim o
texto sai como o utilizador o ve no teclado, qualquer que seja o layout.

Acentos que nao tem tecla propria (ex.: a tilde em portugues) sao escritos como a tecla
morta seguida da letra: o ambiente grafico junta os dois, como faria o teclado fisico.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import functools
import unicodedata

# Codigos XKB = codigos evdev + 8.
DESLOCAMENTO_XKB = 8
SEM_INDICE = 0xFFFFFFFF

_MARCAS_MORTAS = {
    "dead_grave": "\u0300", "dead_acute": "\u0301", "dead_circumflex": "\u0302",
    "dead_tilde": "\u0303", "dead_macron": "\u0304", "dead_breve": "\u0306",
    "dead_abovedot": "\u0307", "dead_diaeresis": "\u0308", "dead_abovering": "\u030a",
    "dead_doubleacute": "\u030b", "dead_caron": "\u030c", "dead_cedilla": "\u0327",
    "dead_ogonek": "\u0328",
}
# Nome XKB do modificador -> papel usado nos atalhos.
_MODIFICADORES_XKB = {"Shift": "shift", "Control": "ctrl", "Mod1": "alt", "Mod5": "altgr"}
# Tecla que dá cada papel, pelo keysym do nível base.
_KEYSYM_MODIFICADORES = {"shift": "Shift_L", "ctrl": "Control_L", "alt": "Alt_L", "altgr": "ISO_Level3_Shift"}
# Codigos evdev convencionais (KEY_LEFTSHIFT, KEY_LEFTCTRL, KEY_LEFTALT, KEY_RIGHTALT).
_TECLAS_CONVENCIONAIS = {"shift": 42, "ctrl": 29, "alt": 56, "altgr": 100}


class _NomesRegras(ctypes.Structure):
    _fields_ = [
        ("rules", ctypes.c_char_p),
        ("model", ctypes.c_char_p),
        ("layout", ctypes.c_char_p),
        ("variant", ctypes.c_char_p),
        ("options", ctypes.c_char_p),
    ]


@functools.lru_cache(maxsize=1)
def _biblioteca() -> ctypes.CDLL:
    lib = ctypes.CDLL(ctypes.util.find_library("xkbcommon") or "libxkbcommon.so.0")
    c_p, u32, c_int = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
    lib.xkb_context_new.argtypes, lib.xkb_context_new.restype = [c_int], c_p
    lib.xkb_keymap_new_from_names.argtypes = [c_p, ctypes.POINTER(_NomesRegras), c_int]
    lib.xkb_keymap_new_from_names.restype = c_p
    lib.xkb_keymap_min_keycode.argtypes, lib.xkb_keymap_min_keycode.restype = [c_p], u32
    lib.xkb_keymap_max_keycode.argtypes, lib.xkb_keymap_max_keycode.restype = [c_p], u32
    lib.xkb_keymap_num_levels_for_key.argtypes = [c_p, u32, u32]
    lib.xkb_keymap_num_levels_for_key.restype = u32
    lib.xkb_keymap_key_get_syms_by_level.argtypes = [c_p, u32, u32, u32, ctypes.POINTER(ctypes.POINTER(u32))]
    lib.xkb_keymap_key_get_syms_by_level.restype = c_int
    lib.xkb_keymap_key_get_mods_for_level.argtypes = [c_p, u32, u32, u32, ctypes.POINTER(u32), ctypes.c_size_t]
    lib.xkb_keymap_key_get_mods_for_level.restype = ctypes.c_size_t
    lib.xkb_keysym_to_utf32.argtypes, lib.xkb_keysym_to_utf32.restype = [u32], u32
    lib.xkb_keysym_from_name.argtypes, lib.xkb_keysym_from_name.restype = [ctypes.c_char_p, c_int], u32
    lib.xkb_keymap_mod_get_index.argtypes = [c_p, ctypes.c_char_p]
    lib.xkb_keymap_mod_get_index.restype = u32
    return lib


class MapaTeclas:
    """Caracteres e atalhos -> (codigo evdev da tecla, codigos evdev dos modificadores)."""

    def __init__(self, layout: str, variante: str = "", opcoes: str = "") -> None:
        try:
            self._lib = _biblioteca()
        except OSError as erro:
            raise RuntimeError("libxkbcommon nao encontrada: instale a biblioteca xkbcommon.") from erro
        contexto = self._lib.xkb_context_new(0)
        nomes = _NomesRegras(None, None, layout.encode(), variante.encode() or None, opcoes.encode() or None)
        self._keymap = self._lib.xkb_keymap_new_from_names(contexto, ctypes.byref(nomes), 0)
        if not self._keymap:
            raise RuntimeError(f"Layout de teclado nao suportado: {layout} {variante}".strip())
        self._mascaras: dict[int, str] = {}
        self._mascara_lock = 0
        self._teclas_modificadores: dict[str, int] = {}
        self._por_keysym: dict[int, tuple[int, tuple[int, ...]]] = {}
        self._por_caracter: dict[str, tuple[int, tuple[int, ...]]] = {}
        self._marcas: dict[str, tuple[int, tuple[int, ...]]] = {}
        self._carregar()

    def passos_para_caracter(self, caracter: str) -> list[tuple[int, tuple[int, ...]]] | None:
        """Teclas a premir para escrever o caracter; None se o layout nao o tiver."""
        if caracter in self._por_caracter:
            return [self._por_caracter[caracter]]
        decomposto = unicodedata.normalize("NFD", caracter)
        if len(decomposto) == 2 and decomposto[1] in self._marcas and decomposto[0] in self._por_caracter:
            return [self._marcas[decomposto[1]], self._por_caracter[decomposto[0]]]
        return None

    def tecla_base(self, nome: str) -> int | None:
        """Codigo evdev da tecla que produz o nome (ex.: "c") sem modificadores."""
        entrada = self._por_keysym.get(self._lib.xkb_keysym_from_name(nome.encode(), 0))
        if entrada and entrada[1] == ():
            return entrada[0]
        return None

    def tecla_modificador(self, papel: str) -> int | None:
        """Codigo evdev da tecla de modificador: "shift", "ctrl", "alt" ou "altgr"."""
        return self._teclas_modificadores.get(papel)

    def _carregar(self) -> None:
        lib, mapa = self._lib, self._keymap
        for nome, papel in _MODIFICADORES_XKB.items():
            indice = lib.xkb_keymap_mod_get_index(mapa, nome.encode())
            if indice != SEM_INDICE:
                self._mascaras[1 << indice] = papel
        indice_lock = lib.xkb_keymap_mod_get_index(mapa, b"Lock")
        if indice_lock != SEM_INDICE:
            self._mascara_lock = 1 << indice_lock

        self._localizar_modificadores()
        for codigo_xkb in self._codigos_xkb():
            for nivel in range(lib.xkb_keymap_num_levels_for_key(mapa, codigo_xkb, 0)):
                simbolos = self._simbolos(codigo_xkb, nivel)
                if not simbolos:
                    continue
                mods = self._modificadores_do_nivel(codigo_xkb, nivel)
                if mods is None:
                    continue
                for keysym in simbolos:
                    self._registar(keysym, codigo_xkb - DESLOCAMENTO_XKB, mods)

        for nome, marca in _MARCAS_MORTAS.items():
            entrada = self._por_keysym.get(lib.xkb_keysym_from_name(nome.encode(), 0))
            if entrada:
                self._marcas[marca] = entrada

    def _codigos_xkb(self) -> range:
        lib, mapa = self._lib, self._keymap
        return range(max(lib.xkb_keymap_min_keycode(mapa), DESLOCAMENTO_XKB), lib.xkb_keymap_max_keycode(mapa) + 1)

    def _simbolos(self, codigo_xkb: int, nivel: int) -> list[int]:
        simbolos = ctypes.POINTER(ctypes.c_uint32)()
        quantos = self._lib.xkb_keymap_key_get_syms_by_level(
            self._keymap, codigo_xkb, 0, nivel, ctypes.byref(simbolos),
        )
        return [simbolos[i] for i in range(max(quantos, 0))]

    def _modificadores_do_nivel(self, codigo_xkb: int, nivel: int) -> tuple[int, ...] | None:
        mascaras = (ctypes.c_uint32 * 16)()
        total = self._lib.xkb_keymap_key_get_mods_for_level(self._keymap, codigo_xkb, 0, nivel, mascaras, 16)
        return self._modificadores_para(list(mascaras)[:min(total, 16)])

    def _localizar_modificadores(self) -> None:
        """Acha as teclas de Shift, Ctrl, Alt e AltGr antes de mapear o resto.

        Quando mais do que uma tecla da o mesmo modificador, usa a convencional (ex.: AltGr = 100).
        """
        procurados = {
            self._lib.xkb_keysym_from_name(nome.encode(), 0): papel
            for papel, nome in _KEYSYM_MODIFICADORES.items()
        }
        candidatas: dict[str, list[int]] = {}
        for codigo_xkb in self._codigos_xkb():
            for keysym in self._simbolos(codigo_xkb, 0):
                if keysym in procurados:
                    candidatas.setdefault(procurados[keysym], []).append(codigo_xkb - DESLOCAMENTO_XKB)
        for papel, codigos in candidatas.items():
            self._teclas_modificadores[papel] = _TECLAS_CONVENCIONAIS.get(papel) if (
                _TECLAS_CONVENCIONAIS.get(papel) in codigos
            ) else codigos[0]

    def _modificadores_para(self, mascaras: list[int]) -> tuple[int, ...] | None:
        """Menor combinacao de modificadores (codigos evdev) que produz o nivel; None se nao houver."""
        if not mascaras:
            return ()
        melhor: tuple[int, ...] | None = None
        for mascara in mascaras:
            # Caps Lock so afeta letras, e para elas produz o mesmo que Shift: usa-se Shift.
            if mascara & self._mascara_lock:
                mascara = (mascara & ~self._mascara_lock) | self._mascara_shift()
            papeis = [papel for bit, papel in self._mascaras.items() if mascara & bit]
            conhecidas = sum(bit for bit in self._mascaras if mascara & bit)
            if mascara & ~conhecidas or any(p not in self._teclas_modificadores for p in papeis):
                continue
            combinacao = tuple(self._teclas_modificadores[p] for p in papeis)
            if melhor is None or len(combinacao) < len(melhor):
                melhor = combinacao
        return melhor

    def _mascara_shift(self) -> int:
        for bit, papel in self._mascaras.items():
            if papel == "shift":
                return bit
        return 0

    def _registar(self, keysym: int, evdev: int, mods: tuple[int, ...]) -> None:
        atual = self._por_keysym.get(keysym)
        if atual is None or len(mods) < len(atual[1]):
            self._por_keysym[keysym] = (evdev, mods)
        caracter = self._lib.xkb_keysym_to_utf32(keysym)
        if caracter:
            letra = chr(caracter)
            atual_letra = self._por_caracter.get(letra)
            if atual_letra is None or len(mods) < len(atual_letra[1]):
                self._por_caracter[letra] = (evdev, mods)
