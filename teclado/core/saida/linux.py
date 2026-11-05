"""Injecao de teclas no Linux: teclado virtual (uinput) com o layout do sistema.

Funciona em Wayland e X11, em qualquer aplicacao (incluindo terminais).

Limitacoes: a janela em foco e a area de transferencia nao sao geridas, porque
dependem do ambiente grafico. O texto (incluindo o ditado) escreve-se carater a carater.
"""

from __future__ import annotations

import logging
import threading
import time

from . import ACOES_EDICAO
from .layout import layout_do_sistema
from .uinput import TecladoVirtual
from .xkb import MapaTeclas

log = logging.getLogger(__name__)

PAUSA_APOS_APAGAR = 0.03
PAUSA_ENTRE_TECLAS = 0.004
PAUSA_ENTRE_MARCA_E_LETRA = 0.01

# Codigos evdev das teclas de navegacao e edicao (independentes do layout).
_TECLAS = {
    "backspace": 14, "tab": 15, "enter": 28, "esc": 1, "espaco": 57, "delete": 111,
    "seta_esq": 105, "seta_dir": 106, "seta_cima": 103, "seta_baixo": 108,
    "home": 102, "end": 107, "pgup": 104, "pgdn": 109, "prtsc": 99, "insert": 110, "capslock": 58,
    "left": 105, "right": 106,
}
_MODIFICADORES = {"ctrl": "ctrl", "shift": "shift", "alt": "alt"}


class SaidaLinux:
    def __init__(self) -> None:
        self._mapa = MapaTeclas(*layout_do_sistema())
        self._teclado = TecladoVirtual()
        self._lock = threading.RLock()
        self._ultimo_apagar = 0.0
        self._avisados: set[str] = set()

    # --- envio -----------------------------------------------------------------

    def _combinacao(self, modificadores: tuple[int, ...], tecla: int) -> list[tuple[int, bool]]:
        """Prime os modificadores, a tecla, liberta a tecla e depois os modificadores (ao contrario)."""
        return (
            [(codigo, True) for codigo in modificadores]
            + [(tecla, True), (tecla, False)]
            + [(codigo, False) for codigo in reversed(modificadores)]
        )

    def _enviar_passos(self, passos: list[tuple[int, tuple[int, ...]]]) -> None:
        for indice, (tecla, modificadores) in enumerate(passos):
            if indice:
                time.sleep(PAUSA_ENTRE_MARCA_E_LETRA)
            self._teclado.enviar(self._combinacao(modificadores, tecla))

    def _enviar_carater(self, carater: str) -> None:
        if carater == "\n":
            self._teclado.enviar(self._combinacao((), _TECLAS["enter"]))
            return
        if carater == "\t":
            self._teclado.enviar(self._combinacao((), _TECLAS["tab"]))
            return
        passos = self._mapa.passos_para_caracter(carater)
        if passos is None:
            self._avisar_uma_vez(f"Caracter sem tecla neste teclado: {carater!r}")
            return
        self._enviar_passos(passos)

    def _esperar_apos_apagar(self) -> None:
        decorrido = time.monotonic() - self._ultimo_apagar
        if decorrido < PAUSA_APOS_APAGAR:
            time.sleep(PAUSA_APOS_APAGAR - decorrido)

    def _enviar_texto(self, texto: str) -> None:
        if not texto:
            return
        with self._lock:
            self._esperar_apos_apagar()
            for carater in texto:
                self._enviar_carater(carater)
                time.sleep(PAUSA_ENTRE_TECLAS)

    def _enviar_tecla(self, nome: str) -> None:
        codigo = self._codigo_tecla(nome)
        with self._lock:
            if nome == "backspace":
                self._teclado.enviar(self._combinacao((), codigo))
                self._ultimo_apagar = time.monotonic()
                return
            self._esperar_apos_apagar()
            self._teclado.enviar(self._combinacao((), codigo))

    def _enviar_passo(self, passo: str) -> None:
        """Um passo de atalho, ex.: "ctrl+shift+left"."""
        *nomes_modificadores, nome_tecla = passo.split("+")
        modificadores = tuple(self._codigo_modificador(nome) for nome in nomes_modificadores)
        tecla = self._codigo_tecla(nome_tecla)
        self._teclado.enviar(self._combinacao(modificadores, tecla))
        if nome_tecla == "backspace":
            self._ultimo_apagar = time.monotonic()

    def _codigo_modificador(self, nome: str) -> int:
        papel = _MODIFICADORES.get(nome)
        codigo = self._mapa.tecla_modificador(papel) if papel else None
        if codigo is None:
            raise ValueError(f"Modificador desconhecido no atalho: {nome}")
        return codigo

    def _codigo_tecla(self, nome: str) -> int:
        if nome in _TECLAS:
            return _TECLAS[nome]
        if len(nome) == 1:
            codigo = self._mapa.tecla_base(nome)
            if codigo is not None:
                return codigo
        raise ValueError(f"Tecla desconhecida no atalho: {nome}")

    def _avisar_uma_vez(self, mensagem: str) -> None:
        if mensagem not in self._avisados:
            self._avisados.add(mensagem)
            log.warning(mensagem)

    # --- interface (ver saida/__init__.py) ---------------------------------------

    def escrever(self, texto: str) -> None:
        self._enviar_texto(texto)

    def tecla(self, nome: str) -> None:
        self._enviar_tecla(nome)

    def sequencia(self, acoes: list[tuple[str, str]]) -> None:
        for tipo, valor in acoes:
            if tipo == "texto":
                self._enviar_texto(valor)
            elif tipo == "tecla":
                self._enviar_tecla(valor)
            else:
                raise ValueError(f"Tipo de acao desconhecido: {tipo}")

    def colar_texto(self, texto: str) -> None:
        """Escreve o texto carater a carater (a area de transferencia nao e gerida no Linux)."""
        self._enviar_texto(texto)

    def atalho(self, nome: str) -> None:
        if nome not in ACOES_EDICAO:
            raise ValueError(f"Acao de edicao desconhecida: {nome}")
        with self._lock:
            for passo in ACOES_EDICAO[nome]:
                self._esperar_apos_apagar()
                self._enviar_passo(passo)

    def enviar_atalho(self, passo: str) -> None:
        with self._lock:
            self._esperar_apos_apagar()
            self._enviar_passo(passo)

    def janela_ativa(self, acao: str, excluir: int = 0) -> bool:
        self._avisar_uma_vez("Fechar, minimizar e maximizar a janela em foco ainda nao esta disponivel no Linux.")
        return False

    def ler_selecao(self) -> str:
        self._avisar_uma_vez("Ler a selecao ainda nao esta disponivel no Linux.")
        return ""
