"""Operacoes de janela e de area de transferencia em X11 (XWayland incluido).

Usa python-xlib (so Linux). Janelas nativas Wayland, sem XWayland, nao sao visiveis aqui.
"""

from __future__ import annotations

import threading
import time

_NET_ACTIVE_WINDOW = "_NET_ACTIVE_WINDOW"
_NET_CLOSE_WINDOW = "_NET_CLOSE_WINDOW"
_NET_WM_STATE = "_NET_WM_STATE"
_WM_CHANGE_STATE = "WM_CHANGE_STATE"
_MAXIMIZED = ("_NET_WM_STATE_MAXIMIZED_VERT", "_NET_WM_STATE_MAXIMIZED_HORZ")
_ICONIC = 3  # WM_STATE: IconicState
_TEXTO = ("UTF8_STRING", "STRING")


def _abrir():
    from Xlib import display  # importado so em Linux

    return display.Display()


def janela_em_foco_e_acao(acao: str, excluir: int = 0) -> bool:
    """Fecha, minimiza ou maximiza a janela ativa. False se nao houver janela valida.

    'excluir' e a janela do proprio teclado: nunca e alterada.
    """
    from Xlib import X
    from Xlib.protocol import event

    d = _abrir()
    try:
        raiz = d.screen().root
        propriedade = raiz.get_full_property(d.intern_atom(_NET_ACTIVE_WINDOW), X.AnyPropertyType)
        if propriedade is None or not propriedade.value or not propriedade.value[0]:
            return False
        id_janela = int(propriedade.value[0])
        if excluir and id_janela == excluir:
            return False
        janela = d.create_resource_object("window", id_janela)
        mascara = X.SubstructureRedirectMask | X.SubstructureNotifyMask
        if acao == "fechar_janela":
            mensagem = event.ClientMessage(
                window=janela, client_type=d.intern_atom(_NET_CLOSE_WINDOW),
                data=(32, [0, 2, 0, 0, 0]),
            )
        elif acao == "minimizar_janela":
            mensagem = event.ClientMessage(
                window=janela, client_type=d.intern_atom(_WM_CHANGE_STATE),
                data=(32, [_ICONIC, 0, 0, 0, 0]),
            )
        elif acao == "maximizar_janela":
            vertical, horizontal = (d.intern_atom(nome) for nome in _MAXIMIZED)
            mensagem = event.ClientMessage(
                window=janela, client_type=d.intern_atom(_NET_WM_STATE),
                data=(32, [1, vertical, horizontal, 1, 0]),
            )
        else:
            raise ValueError(f"Acao de janela desconhecida: {acao}")
        raiz.send_event(mensagem, event_mask=mascara)
        d.flush()
        return True
    finally:
        d.close()


def ler_selecao_primaria(limite_s: float = 0.6) -> str:
    """Texto selecionado (PRIMARY). Nao altera a area de transferencia nem o teclado."""
    from Xlib import X

    d = _abrir()
    try:
        raiz = d.screen().root
        janela = raiz.create_window(0, 0, 1, 1, 0, d.screen().root_depth)
        propriedade = d.intern_atom("KIKOIA_SELECAO")
        janela.convert_selection(X.PRIMARY, d.intern_atom("UTF8_STRING"), propriedade, X.CurrentTime)
        d.flush()
        fim = time.monotonic() + limite_s
        while time.monotonic() < fim:
            while d.pending_events():
                evento = d.next_event()
                if evento.type == X.SelectionNotify:
                    if not evento.property:
                        return ""
                    dados = janela.get_full_property(propriedade, X.AnyPropertyType)
                    if dados is None or dados.value is None:
                        return ""
                    return bytes(dados.value).decode("utf-8", "replace")
            time.sleep(0.01)
        return ""
    finally:
        d.close()


class DonoClipboard:
    """Diz ao sistema que o clipboard tem um texto, e entrega-o quando alguem o pede (Ctrl+V).

    Corre numa thread propria, com a sua ligacao ao servidor X.
    """

    def __init__(self) -> None:
        self._texto = b""
        self._trava = threading.Lock()
        self._d = _abrir()
        self._janela = self._d.screen().root.create_window(0, 0, 1, 1, 0, self._d.screen().root_depth)
        self._clipboard = self._d.intern_atom("CLIPBOARD")
        self._targets = self._d.intern_atom("TARGETS")
        self._textos = [self._d.intern_atom(nome) for nome in _TEXTO]
        threading.Thread(target=self._servir, daemon=True, name="clipboard-x11").start()

    def definir(self, texto: str) -> None:
        from Xlib import X

        with self._trava:
            self._texto = texto.encode("utf-8")
        self._janela.set_selection_owner(self._clipboard, X.CurrentTime)
        self._d.flush()

    def _servir(self) -> None:
        from Xlib import X
        from Xlib import Xatom
        from Xlib.protocol import event

        while True:
            evento = self._d.next_event()
            if evento.type != X.SelectionRequest:
                continue
            pedido = evento
            resposta = 0  # 0 = None: pedido recusado
            if pedido.target == self._targets:
                alvos = [self._targets] + self._textos
                pedido.requestor.change_property(pedido.property, Xatom.ATOM, 32, alvos)
                resposta = pedido.property
            elif pedido.target in self._textos:
                with self._trava:
                    dados = self._texto
                pedido.requestor.change_property(pedido.property, pedido.target, 8, dados)
                resposta = pedido.property
            notificacao = event.SelectionNotify(
                time=pedido.time, requestor=pedido.requestor, selection=pedido.selection,
                target=pedido.target, property=resposta,
            )
            pedido.requestor.send_event(notificacao, event_mask=0)
            self._d.flush()
