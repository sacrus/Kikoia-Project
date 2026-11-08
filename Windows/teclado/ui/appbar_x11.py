"""Reserva da area de trabalho em X11 (Linux): o teclado anuncia a faixa do fundo ao gestor de janelas.

Equivale ao AppBar do Windows. O teclado fica como janela do tipo "dock" com _NET_WM_STRUT_PARTIAL:
o gestor de janelas (GNOME/Mutter, KDE, ...) nao deixa as janelas maximizadas ocupar essa faixa.
Funciona em X11 e em XWayland (o teclado corre em xcb). Em Wayland nativo nao faz nada.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_TIPO_JANELA = "_NET_WM_WINDOW_TYPE"
_DOCK = "_NET_WM_WINDOW_TYPE_DOCK"
_STRUT = "_NET_WM_STRUT"
_STRUT_PARCIAL = "_NET_WM_STRUT_PARTIAL"
_AREA_UTIL = "_NET_WORKAREA"


class BarraInferiorX11:
    """Regista uma janela X como faixa no fundo do ecra. Coordenadas em pixeis fisicos."""

    def __init__(self) -> None:
        self._display = None
        self._wid = 0
        self._ativa = False
        # Area util sem a reserva do teclado (lida antes de qualquer reserva; o gestor atualiza-a com atraso).
        self._area_base: tuple[int, int, int, int] | None = None

    @property
    def registada(self) -> bool:
        return self._ativa

    def _abrir(self) -> bool:
        if self._display is not None:
            return True
        try:
            from Xlib import display

            self._display = display.Display()
        except Exception:  # sem X (Wayland nativo) ou sem DISPLAY
            log.info("Sem X disponivel: a area de trabalho nao e reservada ao teclado.")
            return False
        return True

    def _janela(self):
        return self._display.create_resource_object("window", self._wid)

    def preparar(self, wid: int) -> None:
        """Marca a janela como 'dock' antes de ser mostrada: o gestor le o tipo ao mapear a janela."""
        from Xlib import Xatom

        if not self._abrir():
            return
        self._wid = wid
        if self._area_base is None:
            self._area_base = self._ler_area_util()
        atomo = self._display.intern_atom(_TIPO_JANELA)
        self._janela().change_property(atomo, Xatom.ATOM, 32, [self._display.intern_atom(_DOCK)])
        self._display.sync()

    def registar(self, wid: int) -> bool:
        if not self._abrir():
            return False
        if wid != self._wid:
            self.preparar(wid)
        self._ativa = True
        return True

    def _ler_area_util(self) -> tuple[int, int, int, int] | None:
        from Xlib import Xatom

        raiz = self._display.screen().root
        area = raiz.get_full_property(self._display.intern_atom(_AREA_UTIL), Xatom.CARDINAL)
        if area is None or len(area.value) < 4:
            return None
        return tuple(int(v) for v in area.value[:4])

    def area_base(self) -> tuple[int, int, int, int] | None:
        """Area util do ecra sem o teclado (x, y, w, h em pixeis fisicos); None se nao houver X."""
        return self._area_base

    def _limite_inferior_util(self, altura_ecra: int) -> int:
        """Fundo da area util (acima de um painel do sistema, se existir), em pixeis."""
        base = self._area_base or self._ler_area_util()
        if base is None:
            return altura_ecra
        return min(altura_ecra, base[1] + base[3])

    def posicionar(self, altura: int) -> tuple[int, int, int, int] | None:
        """Coloca o teclado no fundo da area util e reserva exatamente essa faixa.

        A reserva tem de comecar onde comeca o teclado; senao as janelas maximizadas
        ficam por baixo dele (ou sobram faixas vazias). Devolve (x, y, w, h) em pixeis fisicos.
        """
        from Xlib import Xatom

        if not self._ativa:
            return None
        ecra = self._display.screen()
        largura, altura_ecra = ecra.width_in_pixels, ecra.height_in_pixels
        topo = self._limite_inferior_util(altura_ecra) - altura
        valores = [0, 0, 0, altura_ecra - topo, 0, 0, 0, 0, 0, 0, 0, largura - 1]
        janela = self._janela()
        janela.change_property(self._display.intern_atom(_STRUT_PARCIAL), Xatom.CARDINAL, 32, valores)
        janela.change_property(self._display.intern_atom(_STRUT), Xatom.CARDINAL, 32, valores[:4])
        self._display.sync()
        return 0, topo, largura, altura

    def remover(self) -> None:
        if not self._ativa:
            return
        janela = self._janela()
        janela.delete_property(self._display.intern_atom(_STRUT_PARCIAL))
        janela.delete_property(self._display.intern_atom(_STRUT))
        self._display.sync()
        self._ativa = False
