"""Touchpad: o telemovel envia os toques; o PC interpreta os gestos e move/clica/desloca o rato.

As definicoes (cliques, sensibilidade) sao do PC, por isso e aqui que os gestos sao reconhecidos.
O telemovel envia a area onde comeca cada toque (esquerda, direita ou barra de deslocamento) e o
tamanho fisico da superficie em milimetros, para que a sensibilidade seja a mesma em qualquer aparelho.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

BOTOES = ("esquerdo", "direito")
OPCOES = (
    "rapido", "duplo_rapido", "duplo_lento",
    "rapido_2", "lento_2", "rapido_3", "lento_3",
    "manter",
)
PREFERENCIAS_POR_OMISSAO: dict = {
    "esquerdo": "rapido",
    "direito": "rapido_2",
    "janela_duplo_ms": 1000,
    "tempo_manter_ms": 1000,
    "sensibilidade": 100,
    "clique_por_area": True,
}
LIMITES = {
    "janela_duplo_ms": (300, 3000),
    "tempo_manter_ms": (500, 3000),
    "sensibilidade": (10, 500),
}
AREAS = ("esquerda", "direita", "barra")
# Toque rapido: ate 300 ms. Lento: de 300 ms a 1500 ms. Acima disto nao e um clique.
TOQUE_RAPIDO_MAX_MS = 300
TOQUE_LENTO_MAX_MS = 1500
JANELA_DUPLO_RAPIDO_S = 0.35
# Deslocamento (fração da superficie) a partir do qual o toque deixa de ser um clique.
DESLOCAMENTO_MAX = 0.02
# Sensibilidade 100: 1 cm de dedo move o cursor 120 px, e 3 entalhes de roda.
PIXEIS_POR_CM = 120
ENTALHES_POR_CM = 3
# Tamanho usado enquanto o telemovel nao envia o seu (aprox. um telemovel).
TAMANHO_PADRAO_MM = (70, 150)
ACOES_TOQUE = ("dimensoes", "down", "move", "up")
# Modos do touchpad. No Quadro Interativo: um dedo arrastado desenha (ferramentas de desenho) ou move
# o cursor (ferramentas de clique); dois dedos movem sempre sem desenhar; toque breve clica o esquerdo.
MODO_NORMAL = "normal"
MODO_QUADRO_DESENHO = "quadro_desenho"
MODO_QUADRO_CLIQUE = "quadro_clique"
MODOS = (MODO_NORMAL, MODO_QUADRO_DESENHO, MODO_QUADRO_CLIQUE)

# opcao -> (dedos, tipo, velocidade). Tipo: simples, duplo ou manter.
_GESTOS = {
    "rapido": (1, "simples", "rapido"),
    "duplo_rapido": (1, "duplo", "rapido"),
    "duplo_lento": (1, "duplo", "lento"),
    "rapido_2": (2, "simples", "rapido"),
    "lento_2": (2, "simples", "lento"),
    "rapido_3": (3, "simples", "rapido"),
    "lento_3": (3, "simples", "lento"),
    "manter": (1, "manter", None),
}


def gesto(opcao: str) -> tuple:
    return _GESTOS[opcao]


def validar_preferencias(prefs: dict) -> dict:
    """Preferencias limpas (com valores por omissao). ValueError se algum valor for invalido."""
    limpas: dict = {}
    for botao in BOTOES:
        valor = prefs.get(botao, PREFERENCIAS_POR_OMISSAO[botao])
        if valor not in OPCOES:
            raise ValueError(f"opcao de clique invalida: {valor!r}")
        limpas[botao] = valor
    for chave, (minimo, maximo) in LIMITES.items():
        valor = prefs.get(chave, PREFERENCIAS_POR_OMISSAO[chave])
        if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
            raise ValueError(f"valor invalido para {chave}")
        limpas[chave] = valor
    area = prefs.get("clique_por_area", PREFERENCIAS_POR_OMISSAO["clique_por_area"])
    if not isinstance(area, bool):
        raise ValueError("clique_por_area tem de ser sim ou nao")
    limpas["clique_por_area"] = area
    gestos = [gesto(limpas[b]) for b in BOTOES if limpas[b] != "manter"]
    if len(gestos) == 2 and (gestos[0][0], gestos[0][2]) == (gestos[1][0], gestos[1][2]):
        raise ValueError("os dois botoes nao podem usar o mesmo gesto")
    return limpas


class RatoNulo:
    """Sem rato disponivel: os toques sao ignorados (o resto do teclado funciona)."""

    def mover(self, dx: int, dy: int) -> None:
        pass

    def clicar(self, botao: str, vezes: int = 1) -> None:
        pass

    def pressionar(self, botao: str) -> None:
        pass

    def soltar(self, botao: str) -> None:
        pass

    def rolar(self, entalhes: int) -> None:
        pass

    def fechar(self) -> None:
        pass


def _agendar_thread(segundos: float, funcao: Callable[[], None]):
    alarme = threading.Timer(segundos, funcao)
    alarme.daemon = True
    alarme.start()
    return alarme


class Interpretador:
    """Transforma toques em cursor, cliques e deslocamento, segundo as preferencias.

    rato: objeto com mover(dx, dy), clicar(botao, vezes) e rolar(entalhes).
    preferencias: funcao sem argumentos que devolve as preferencias atuais.
    relogio e agendar existem para os testes; no uso normal sao o relogio do sistema e um temporizador.
    """

    def __init__(
        self,
        rato,
        preferencias: Callable[[], dict],
        relogio: Callable[[], float] = time.monotonic,
        agendar: Callable | None = None,
        modo: Callable[[], str] | None = None,
    ) -> None:
        self._rato = rato
        self._preferencias = preferencias
        self._modo = modo or (lambda: MODO_NORMAL)
        self._arrastando = False
        self._relogio = relogio
        self._agendar = agendar or _agendar_thread
        self._trava = threading.RLock()
        self._largura_mm, self._altura_mm = TAMANHO_PADRAO_MM
        self._pontos: dict[int, list] = {}  # id -> [x0, y0, px, py, x, y, area]
        self._sessao = 0
        self._inicio = 0.0
        self._area = "esquerda"  # area onde comecou o primeiro dedo da sessao
        self._dedos_max = 0
        self._movido = False
        self._manter_disparado = False
        self._alarme = None
        self._pendente: tuple[str, float] | None = None
        self._resto = [0.0, 0.0]
        self._resto_entalhes = 0.0

    def dimensoes(self, largura_mm: int, altura_mm: int) -> None:
        with self._trava:
            self._largura_mm, self._altura_mm = largura_mm, altura_mm

    def evento(self, acao: str, ident: int, x: int, y: int, area: str | None = None) -> None:
        if acao not in ("down", "move", "up"):
            return
        x, y = x / 10000.0, y / 10000.0
        with self._trava:
            if acao == "down":
                self._baixo(ident, x, y, area if area in AREAS else "esquerda")
            elif acao == "move":
                self._movimento(ident, x, y)
            else:
                self._cima(ident)

    def fechar(self) -> None:
        with self._trava:
            self._cancelar_alarme()

    # --- internos -------------------------------------------------------------

    def _agora(self) -> float:
        return self._relogio()

    def _baixo(self, ident: int, x: float, y: float, area: str) -> None:
        if ident in self._pontos:
            # Um dedo ja registado a começar de novo: o levantamento anterior perdeu-se. Recomeça esse dedo.
            self._pontos[ident] = [x, y, x, y, x, y, area]
            return
        if not self._pontos:
            self._sessao += 1
            self._inicio = self._agora()
            self._area = area
            self._dedos_max = 0
            self._movido = False
            self._manter_disparado = False
            self._arrastando = False
            self._resto = [0.0, 0.0]
            self._resto_entalhes = 0.0
            self._armar_manter()
        self._pontos[ident] = [x, y, x, y, x, y, area]
        self._dedos_max = max(self._dedos_max, len(self._pontos))
        if len(self._pontos) > 1:
            self._cancelar_alarme()  # manter so conta com um dedo
            if self._arrastando:
                # Um segundo dedo para o desenho: solta o botao e passa a mover o cursor.
                self._arrastando = False
                self._rato.soltar("esquerdo")

    def _movimento(self, ident: int, x: float, y: float) -> None:
        p = self._pontos.get(ident)
        if p is None:
            return
        p[2], p[3] = p[4], p[5]
        p[4], p[5] = x, y
        if abs(x - p[0]) > DESLOCAMENTO_MAX or abs(y - p[1]) > DESLOCAMENTO_MAX:
            self._movido = True
            self._cancelar_alarme()
        modo = self._modo()
        if modo == MODO_QUADRO_DESENHO and len(self._pontos) == 1 and self._movido and not self._arrastando:
            # Um dedo que se desloca no desenho: prime o botao, para o movimento desenhar.
            self._arrastando = True
            self._rato.pressionar("esquerdo")
        if len(self._pontos) != 1 and modo == MODO_NORMAL:
            return
        sensibilidade = self._preferencias()["sensibilidade"] / 100
        dx_cm = (x - p[2]) * self._largura_mm / 10
        dy_cm = (y - p[3]) * self._altura_mm / 10
        if p[6] == "barra" and modo == MODO_NORMAL:
            # Arrastar na barra desloca a pagina: dedo para baixo, a pagina desce.
            entalhes = dy_cm * ENTALHES_POR_CM * sensibilidade + self._resto_entalhes
            n = round(entalhes)
            self._resto_entalhes = entalhes - n
            if n:
                self._rato.rolar(-n)
            return
        k = PIXEIS_POR_CM * sensibilidade
        ax = dx_cm * k + self._resto[0]
        ay = dy_cm * k + self._resto[1]
        ix, iy = round(ax), round(ay)
        self._resto = [ax - ix, ay - iy]
        if ix or iy:
            self._rato.mover(ix, iy)

    def _cima(self, ident: int) -> None:
        if self._pontos.pop(ident, None) is None or self._pontos:
            return  # ainda ha dedos no ecra: a sessao continua
        self._fechar_sessao()

    def _armar_manter(self) -> None:
        self._cancelar_alarme()
        if self._modo() != MODO_NORMAL:
            return  # no Quadro nao ha «manter»: o arrastar com um dedo ja desenha
        prefs = self._preferencias()
        botao = next((b for b in BOTOES if prefs[b] == "manter"), None)
        if botao is None:
            return
        sessao = self._sessao
        self._alarme = self._agendar(
            prefs["tempo_manter_ms"] / 1000.0, lambda: self._disparar_manter(sessao, botao),
        )

    def _disparar_manter(self, sessao: int, botao: str) -> None:
        with self._trava:
            if sessao != self._sessao or len(self._pontos) != 1 or self._movido:
                return
            self._alarme = None
            self._manter_disparado = True
            self._rato.clicar(botao, 1)

    def _cancelar_alarme(self) -> None:
        if self._alarme is not None:
            self._alarme.cancel()
            self._alarme = None

    def _fechar_sessao(self) -> None:
        self._cancelar_alarme()
        if self._arrastando:
            self._arrastando = False
            self._rato.soltar("esquerdo")
        if self._movido or self._manter_disparado:
            self._pendente = None
            return
        duracao_ms = (self._agora() - self._inicio) * 1000
        if duracao_ms <= TOQUE_RAPIDO_MAX_MS:
            velocidade = "rapido"
        elif duracao_ms <= TOQUE_LENTO_MAX_MS:
            velocidade = "lento"
        else:
            self._pendente = None
            return
        if self._modo() != MODO_NORMAL:
            # Quadro: so o botao esquerdo, com um dedo e fora da barra (que nao existe no Quadro).
            self._pendente = None
            if self._dedos_max == 1 and self._area != "barra":
                self._rato.clicar("esquerdo", 1)
            return
        prefs = self._preferencias()
        if self._dedos_max == 1:
            if self._area == "barra":
                self._pendente = None  # tocar na barra nao clica
                return
            if prefs["clique_por_area"]:
                # Com o clique por area, um toque na metade esquerda clica o esquerdo, e na direita o direito.
                self._pendente = None
                self._rato.clicar("esquerdo" if self._area == "esquerda" else "direito", 1)
                return
        for botao in BOTOES:
            opcao = prefs[botao]
            if opcao == "manter":
                continue
            dedos, tipo, vel = gesto(opcao)
            if dedos != self._dedos_max or vel != velocidade:
                continue
            if tipo == "simples":
                self._pendente = None
                self._rato.clicar(botao, 1)
                return
            agora = self._agora()
            janela = JANELA_DUPLO_RAPIDO_S if opcao == "duplo_rapido" else prefs["janela_duplo_ms"] / 1000.0
            if self._pendente is not None and self._pendente[0] == botao and agora - self._pendente[1] <= janela:
                self._pendente = None
                self._rato.clicar(botao, 2)  # os dois cliques seguidos: o sistema conta como duplo clique
                return
            self._pendente = (botao, agora)
            return
        self._pendente = None
