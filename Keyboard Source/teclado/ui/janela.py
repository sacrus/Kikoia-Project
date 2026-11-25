"""Janela do teclado: sempre por cima, sem roubar o foco, no fundo do ecra.

Se o foco mudasse para esta janela, a aplicacao de destino deixaria de receber
as teclas. Por isso usa-se WindowDoesNotAcceptFocus (no Windows aplica
WS_EX_NOACTIVATE) e nenhum botao aceita foco de teclado.

A janela e um complemento: so mostra o teclado, as sugestoes e uma barra
minima (Sugestoes, Voz, roda dentada). Tudo o resto esta nas Definicoes.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Callable

from PySide6.QtCore import QPointF, QRect, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from teclado.core.editor import Editor
from teclado.core import idiomas
from teclado.core.idiomas import t
from teclado.core.layout import Layout, Tecla
from teclado.core.paths import DADOS_PROJETO
from teclado.core.tema import Tema
from teclado.core.rotulos import rotulo_tecla
if sys.platform.startswith("linux"):
    from teclado.ui.appbar_x11 import BarraInferiorX11 as BarraInferior
else:
    from teclado.ui.appbar import BarraInferior
from teclado.ui.botao_tecla import BotaoTecla, colorir
from teclado.ui.estilo_dialogos import definir_modo_escuro
from teclado.ui.interruptor import Interruptor
from teclado.ui.medidor import Medidor

Callback = Callable[[], object]

# Imagens maiores do que isto sao reduzidas uma vez ao carregar (memoria e velocidade).
LADO_MAXIMO_IMAGEM = 1600
# Altura do teclado: parte do ecra, com um minimo para as teclas continuarem legiveis.
ALTURA_RELATIVA = 0.42
ALTURA_MINIMA = 260
# Faixa superior (controlos + sugestoes): altura fixa para as teclas nunca mudarem de sitio.
ALTURA_FAIXA_SUGESTOES = 36


def _misturar(cor_a: str, cor_b: str, fator: float) -> str:
    """Mistura duas cores hex (#RRGGBB). fator=0 devolve cor_a; fator=1 devolve cor_b."""
    a, b = QColor(cor_a), QColor(cor_b)
    r = round(a.red() * (1 - fator) + b.red() * fator)
    g = round(a.green() * (1 - fator) + b.green() * fator)
    bl = round(a.blue() * (1 - fator) + b.blue() * fator)
    return f"#{r:02X}{g:02X}{bl:02X}"


def _luminosidade(cor: str) -> float:
    c = QColor(cor)
    return (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0


def _derivar_paleta(tema: Tema) -> dict[str, str]:
    """Deriva tons secundarios, relevo e hover a partir das cores do tema."""
    claro = _luminosidade(tema.cor_fundo) > 0.5
    if claro:
        especial = _misturar(tema.cor_fundo, tema.cor_texto, 0.11)
        tecla_hover = _misturar(tema.cor_tecla, tema.cor_texto, 0.05)
        especial_hover = _misturar(especial, tema.cor_texto, 0.08)
        borda = _misturar(tema.cor_fundo, tema.cor_texto, 0.16)
        relevo = _misturar(tema.cor_fundo, "#000000", 0.27)
        sugestao = _misturar(tema.cor_fundo, tema.cor_texto, 0.12)
        sugestao_hover = _misturar(sugestao, tema.cor_texto, 0.09)
        barra_topo = _misturar(tema.cor_fundo, "#FFFFFF", 0.30)
        util_fundo = _misturar(tema.cor_fundo, "#FFFFFF", 0.55)
        util_hover = _misturar(util_fundo, tema.cor_texto, 0.07)
        texto_suave = _misturar(tema.cor_texto, tema.cor_fundo, 0.42)
    else:
        especial = _misturar(tema.cor_fundo, tema.cor_tecla, 0.48)
        tecla_hover = _misturar(tema.cor_tecla, "#FFFFFF", 0.09)
        especial_hover = _misturar(especial, "#FFFFFF", 0.09)
        borda = _misturar(tema.cor_tecla, "#FFFFFF", 0.10)
        relevo = _misturar(tema.cor_fundo, "#000000", 0.55)
        sugestao = _misturar(tema.cor_fundo, tema.cor_tecla, 0.65)
        sugestao_hover = _misturar(sugestao, "#FFFFFF", 0.10)
        barra_topo = _misturar(tema.cor_fundo, "#FFFFFF", 0.04)
        util_fundo = _misturar(tema.cor_fundo, tema.cor_tecla, 0.55)
        util_hover = _misturar(util_fundo, "#FFFFFF", 0.10)
        texto_suave = _misturar(tema.cor_texto, tema.cor_fundo, 0.40)

    return {
        "especial": especial,
        "tecla_hover": tecla_hover,
        "especial_hover": especial_hover,
        "borda": borda,
        "relevo": relevo,
        "sugestao": sugestao,
        "sugestao_hover": sugestao_hover,
        "barra_topo": barra_topo,
        "util_fundo": util_fundo,
        "util_hover": util_hover,
        "texto_suave": texto_suave,
    }


def carregar_imagem_fundo(caminho) -> QImage | None:
    imagem = QImage(str(caminho))
    if imagem.isNull():
        return None
    if max(imagem.width(), imagem.height()) > LADO_MAXIMO_IMAGEM:
        imagem = imagem.scaled(
            LADO_MAXIMO_IMAGEM,
            LADO_MAXIMO_IMAGEM,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return imagem


def folha_de_estilo(tema: Tema) -> str:
    p = _derivar_paleta(tema)
    return f"""
    QWidget#barra_topo {{
        background-color: {p['barra_topo']};
        border-bottom: 1px solid {p['borda']};
        border-radius: 10px;
    }}
    QPushButton {{
        background-color: {tema.cor_tecla};
        color: {tema.cor_texto};
        font-size: {tema.tamanho_fonte}px;
        font-weight: 500;
        border: 1px solid {p['borda']};
        border-bottom: 2px solid {p['relevo']};
        border-radius: 9px;
        padding: 4px 6px;
    }}
    QPushButton:hover {{
        background-color: {p['tecla_hover']};
    }}
    QPushButton[papel="especial"] {{
        background-color: {p['especial']};
        font-weight: 500;
    }}
    QPushButton[papel="especial"]:hover {{
        background-color: {p['especial_hover']};
    }}
    QPushButton[papel="sugestao"] {{
        background-color: {p['sugestao']};
        color: {tema.cor_texto};
        font-size: 15px;
        font-weight: 500;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 2px 14px;
    }}
    QPushButton[papel="sugestao"]:hover {{
        background-color: {p['sugestao_hover']};
    }}
    QPushButton[papel="util"] {{
        background-color: {p['util_fundo']};
        color: {tema.cor_texto};
        font-size: 13px;
        font-weight: 500;
        border: 1px solid {p['borda']};
        border-radius: 10px;
        padding: 4px 12px;
    }}
    QPushButton[papel="util"]:hover {{
        background-color: {p['util_hover']};
    }}
    QPushButton:pressed, QPushButton:checked {{
        background-color: {tema.cor_tecla_premida};
        color: {tema.cor_texto_premido};
        border: 1px solid {tema.cor_tecla_premida};
        border-bottom: 1px solid {tema.cor_tecla_premida};
    }}
    QPushButton:disabled {{
        opacity: 0.4;
    }}
    """


def _papel_da_tecla(tecla: Tecla) -> str:
    """Classifica visualmente a tecla: 'tecla' (escrita/espaco) ou 'especial' (controlo/acao)."""
    if tecla.acao.tipo in ("texto", "multitoque", "acento"):
        return "tecla"
    if tecla.acao.tipo == "tecla" and tecla.acao.valor == "espaco":
        return "tecla"
    return "especial"


def _botao_sem_foco(texto: str) -> QPushButton:
    botao = QPushButton(texto)
    botao.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return botao


def _icone_definicoes(cor: str, tamanho: int = 64) -> QIcon:
    """Roda dentada desenhada, sem depender de um tipo de letra com o simbolo (⚙ falta em varios sistemas)."""
    pixmap = QPixmap(tamanho, tamanho)
    pixmap.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(pixmap)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    centro = tamanho / 2
    raio_externo, raio_dente, raio_furo = tamanho * 0.46, tamanho * 0.34, tamanho * 0.16
    pontos = []
    for dente in range(8):
        angulo = 2 * math.pi * dente / 8
        for deslocamento, raio in ((-0.16, raio_dente), (-0.09, raio_externo), (0.09, raio_externo), (0.16, raio_dente)):
            a = angulo + deslocamento
            pontos.append(QPointF(centro + raio * math.cos(a), centro + raio * math.sin(a)))
    caminho = QPainterPath()
    caminho.setFillRule(Qt.FillRule.OddEvenFill)  # o furo central fica vazio
    caminho.addPolygon(QPolygonF(pontos))
    caminho.addEllipse(QPointF(centro, centro), raio_furo, raio_furo)
    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(QColor(cor))
    pintor.drawPath(caminho)
    pintor.end()
    return QIcon(pixmap)


class JanelaTeclado(QWidget):
    def __init__(
        self,
        editor: Editor,
        layout: Layout,
        tema: Tema,
        *,
        ao_definicoes: Callback | None = None,
        ao_navegar: Callable[[str], object] | None = None,
        ancorar_fundo: bool = True,
        ao_comando: Callable[[str], object] | None = None,
        ao_fechar: Callable[[], object] | None = None,
        ao_quadro: Callable[[str], object] | None = None,
    ) -> None:
        # Sem barra de titulo (igual em Windows e Linux): o teclado e a faixa do fundo do ecra,
        # e a barra sobrepunha-se as janelas. Fechar faz-se pelo botao Sair.
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._editor = editor
        editor.ao_atualizar = self._atualizar_sugestoes
        self._ao_definicoes = ao_definicoes or (lambda: None)
        self._ao_navegar = ao_navegar or (lambda nome: None)
        self._ao_comando = ao_comando or (lambda id_: None)
        self._ao_quadro = ao_quadro or (lambda id_: None)
        self._icones: dict[str, QPixmap] = {}
        self._coloridos: set[str] = set()
        self._botoes_icone: list[tuple[BotaoTecla, str]] = []
        self._tema_atual = tema
        self.em_dialogo_aberto = False
        self._ao_fechar = ao_fechar or (lambda: None)
        self._ancorar_fundo = ancorar_fundo
        self._barra = BarraInferior()
        if not sys.platform.startswith("linux") or QGuiApplication.platformName() == "xcb":
            self._barra.preparar(int(self.winId()))  # antes de mostrar: o gestor de janelas le o tipo ao mapear
        self._ao_falar_toggle: Callable[[bool], None] = lambda ativo: None
        self._ao_ditar_toggle: Callable[[bool], None] = lambda ativo: None
        self._modelo_layout: Layout | None = None
        self._botoes_modificador: dict[str, QPushButton] = {}
        self._botoes_sugestao: list[QPushButton] = []
        self._sugestoes_ativas = True
        self._cor_fundo = QColor("#FFFFFF")
        self._imagem: QImage | None = None  # original, ja reduzida ao carregar
        self._imagem_escalada: QPixmap | None = None  # cache para o tamanho atual
        self._opacidade = 1.0
        self._tamanho_fonte = tema.tamanho_fonte
        self._botoes_teclas: list[BotaoTecla] = []
        self._teclas_texto: list[tuple[BotaoTecla, Tecla]] = []

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(10, 8, 10, 10)
        raiz.setSpacing(8)

        self._barra_topo = self._construir_barra_topo()
        raiz.addWidget(self._barra_topo)

        self._area_teclas = QVBoxLayout()
        self._area_teclas.setSpacing(7)
        raiz.addLayout(self._area_teclas, 1)

        self.aplicar_tema(tema)
        self.montar(layout)
        self._atualizar_sugestoes()

    # --- barra superior integrada (controlos + sugestoes) ----------------

    def _construir_barra_topo(self) -> QWidget:
        barra_widget = QWidget()
        barra_widget.setObjectName("barra_topo")
        barra_widget.setFixedHeight(46)
        barra = QHBoxLayout(barra_widget)
        barra.setContentsMargins(8, 5, 8, 5)
        barra.setSpacing(6)

        self._botao_sugestoes = Interruptor(t("janela.sugestoes"), icone="sugestoes")
        self._botao_sugestoes.setCheckable(True)
        self._botao_sugestoes.setChecked(True)
        self._botao_sugestoes.setToolTip(t("janela.sugestoes_dica"))
        self._botao_sugestoes.toggled.connect(self._alternar_sugestoes)

        # Voz: dois interruptores. O estado real vem de configurar_voz().
        self._botao_falar = Interruptor(t("janela.falar"), icone="falar")
        self._botao_falar.setCheckable(True)
        self._botao_falar.setEnabled(False)
        self._botao_falar.toggled.connect(lambda ativo: self._ao_falar_toggle(ativo))

        self._botao_ditar = Interruptor(t("janela.ditar"), icone="ditar")
        self._botao_ditar.setCheckable(True)
        self._botao_ditar.setEnabled(False)
        self._botao_ditar.toggled.connect(lambda ativo: self._ao_ditar_toggle(ativo))

        self._botao_definicoes = _botao_sem_foco("")
        self._botao_definicoes.setProperty("papel", "util")
        self._botao_definicoes.setIconSize(QSize(18, 18))
        self._botao_definicoes.setFixedSize(34, 34)
        self._botao_definicoes.setCursor(Qt.CursorShape.PointingHandCursor)
        # Sem barra de titulo (o teclado e reservado como faixa do ecra), este botao fecha o Kikoia.
        self._botao_sair = _botao_sem_foco(t("tray.sair"))
        self._botao_sair.setProperty("papel", "util")
        self._botao_sair.setFixedHeight(34)
        self._botao_sair.setCursor(Qt.CursorShape.PointingHandCursor)
        self._botao_sair.clicked.connect(lambda _=False: self.close())
        self._botao_definicoes.setToolTip(t("janela.definicoes_dica"))
        self._botao_definicoes.clicked.connect(lambda _=False: self._pedir_definicoes())

        # Medidor e mensagem so aparecem com o Ditar ligado.
        self._medidor = Medidor()
        self._medidor.setVisible(False)
        self._aviso = QLabel()
        self._aviso.setStyleSheet(
            "background:#263238; color:#FFEB3B; font-size:12px; font-weight:bold; border-radius:6px; padding:3px 8px;"
        )
        self._aviso.setVisible(False)

        # Indicador do teclado fisico: visivel sempre que as teclas estao a ser observadas.
        # Nome do teclado ativo (o titulo da janela deixou de se ver sem a barra de titulo).
        self._etiqueta_layout = QLabel()
        self._indicador_fisico = QLabel(t("janela.teclado_fisico"))
        self._indicador_fisico.setStyleSheet(
            "color:#DC2626; font-size:12px; font-weight:bold; padding:3px 6px; border:1px solid #DC2626; border-radius:6px;"
        )
        self._indicador_fisico.setToolTip(t("janela.teclado_fisico_dica"))
        self._indicador_fisico.setVisible(False)

        # Zona central de sugestoes (mantem os botoes da direita alinhados mesmo quando oculta).
        zona_centro = QWidget()
        zona_centro_layout = QHBoxLayout(zona_centro)
        zona_centro_layout.setContentsMargins(6, 0, 6, 0)
        zona_centro_layout.setSpacing(0)
        self._faixa_sugestoes = QWidget()
        self._sugestoes_layout = QHBoxLayout(self._faixa_sugestoes)
        self._sugestoes_layout.setContentsMargins(0, 0, 0, 0)
        self._sugestoes_layout.setSpacing(6)
        self._faixa_sugestoes.setFixedHeight(ALTURA_FAIXA_SUGESTOES)
        zona_centro_layout.addWidget(self._faixa_sugestoes, 1)

        self._logo_marca = QLabel()
        self._logo_marca.setStyleSheet("padding: 0 6px 0 2px; background: transparent;")
        self._logo_marca.setToolTip("Kikoia")

        self._interruptores = [self._botao_sugestoes, self._botao_falar, self._botao_ditar]
        barra.addWidget(self._logo_marca)
        barra.addWidget(self._botao_sugestoes)
        barra.addWidget(self._botao_falar)
        barra.addWidget(self._botao_ditar)
        barra.addWidget(self._medidor)
        barra.addWidget(self._aviso)
        barra.addWidget(self._indicador_fisico)
        barra.addWidget(zona_centro, 1)
        barra.addWidget(self._etiqueta_layout)
        barra.addWidget(self._botao_sair)
        barra.addWidget(self._botao_definicoes)
        return barra_widget

    def mostrar_indicador_fisico(self, visivel: bool) -> None:
        self._indicador_fisico.setVisible(visivel)

    def mostrar_nivel(self, visivel: bool) -> None:
        """Mostra o medidor de barras (so faz sentido com o Ditar ligado)."""
        self._medidor.setVisible(visivel)
        if not visivel:
            self._aviso.setVisible(False)
            self._aviso.setText("")

    def atualizar_nivel(self, medicao) -> None:
        """Recebe uma Medicao do microfone: atualiza as barras e a mensagem, se houver."""
        self._medidor.definir_nivel_db(medicao.rms_db)
        if medicao.mensagem:
            self._aviso.setText(medicao.mensagem)
            self._aviso.setVisible(True)
        else:
            self._aviso.setVisible(False)

    def configurar_voz(
        self,
        *,
        falar_ligado: bool,
        falar_motivo: str | None,
        ditar_ligado: bool,
        ditar_motivo: str | None,
        ao_falar: Callable[[bool], None],
        ao_ditar: Callable[[bool], None],
    ) -> None:
        """Estado dos botoes de voz. Motivo preenchido = botao desativado, com explicacao."""
        self._ao_falar_toggle = ao_falar
        self._ao_ditar_toggle = ao_ditar
        for botao, ligado, motivo, nome in (
            (self._botao_falar, falar_ligado, falar_motivo, t("janela.falar")),
            (self._botao_ditar, ditar_ligado, ditar_motivo, t("janela.ditar")),
        ):
            botao.blockSignals(True)
            botao.setChecked(ligado and motivo is None)
            botao.blockSignals(False)
            botao.setEnabled(motivo is None)
            botao.setToolTip(motivo or t("janela.alternar_dica", nome=nome))
        self.mostrar_nivel(ditar_ligado and ditar_motivo is None)

    def _alternar_sugestoes(self, ativo: bool) -> None:
        self._sugestoes_ativas = ativo
        self._atualizar_sugestoes()

    def _pedir_definicoes(self) -> None:
        # Adiado: as definicoes abrem so depois de o clique terminar.
        QTimer.singleShot(0, lambda: self._ao_definicoes())

    # --- construcao ------------------------------------------------------

    def _botao(self, texto: str, ao_premir: Callback) -> QPushButton:
        botao = _botao_sem_foco(texto)
        botao.setMinimumSize(60, 56)
        botao.clicked.connect(lambda _=False: ao_premir())
        return botao

    def _botao_tecla(self, texto: str, ao_premir: Callback) -> QPushButton:
        """Tecla do teclado: cresce com a largura pedida (o stretch) e nao tem tamanho minimo grande.

        Antes, o tamanho minimo fixo e a politica por omissao impediam que a
        largura da tecla fosse respeitada.
        """
        botao = BotaoTecla(texto, self._tamanho_fonte)
        botao.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        botao.setMinimumSize(24, 24)
        botao.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        botao.clicked.connect(lambda _=False: ao_premir())
        self._botoes_teclas.append(botao)
        return botao

    def definir_icones(self, imagens: dict[str, bytes], coloridos: set[str] | None = None) -> None:
        """Imagens (PNG) dos icones que as teclas podem mostrar. Aplicam-se na proxima montagem.
        Os monocromaticos tomam a cor do texto do tema; os coloridos mantem as suas cores."""
        self._coloridos = set(coloridos or ())
        for nome, dados in imagens.items():
            pixmap = QPixmap()
            if pixmap.loadFromData(dados, "PNG"):
                self._icones[nome] = pixmap

    def _imagem_da_tecla(self, nome: str) -> QPixmap:
        original = self._icones[nome]
        if nome in self._coloridos:
            return original
        return colorir(original, self._tema_atual.cor_texto)

    def montar(self, layout: Layout) -> None:
        """Reconstroi as teclas a partir do layout, so com as teclas da lingua selecionada."""
        layout = layout.para_idioma(idiomas.atual())
        while self._area_teclas.count():
            item = self._area_teclas.takeAt(0)
            antiga = item.widget()
            if antiga is not None:
                antiga.hide()
                antiga.setParent(None)  # sai da arvore ja; apaga-se no proximo ciclo
                antiga.deleteLater()
        self._botoes_modificador.clear()
        self._botoes_teclas.clear()
        self._botoes_icone.clear()
        self._teclas_texto = []

        for linha in layout.linhas:
            fila = QWidget()
            horizontal = QHBoxLayout(fila)
            horizontal.setContentsMargins(0, 0, 0, 0)
            horizontal.setSpacing(7)
            for tecla in linha:
                rotulo = rotulo_tecla(tecla.acao.tipo, tecla.acao.valor, tecla.rotulo)
                botao = self._botao_tecla(rotulo, lambda t=tecla: self._premir(t))
                botao.setProperty("papel", _papel_da_tecla(tecla))
                if tecla.icone and tecla.icone in self._icones:
                    botao.definir_icone(self._imagem_da_tecla(tecla.icone))
                    botao.setToolTip(rotulo)
                    self._botoes_icone.append((botao, tecla.icone))
                if tecla.acao.tipo == "texto":
                    self._teclas_texto.append((botao, tecla))
                if tecla.acao.tipo == "modificador":
                    botao.setCheckable(True)
                    self._botoes_modificador[tecla.acao.valor] = botao
                horizontal.addWidget(botao, max(1, round(tecla.largura * 10)))
            self._area_teclas.addWidget(fila, 1)

        self._modelo_layout = layout
        self.setWindowTitle(t("janela.titulo", nome=layout.nome))
        self._etiqueta_layout.setText(layout.nome)
        self._atualizar_simbolos_shift()

    def _atualizar_sugestoes(self) -> None:
        palavras = self._editor.sugestoes
        while len(self._botoes_sugestao) < len(palavras):
            indice = len(self._botoes_sugestao)
            botao = _botao_sem_foco("")
            botao.setProperty("papel", "sugestao")
            botao.setFixedHeight(32)
            botao.setCursor(Qt.CursorShape.PointingHandCursor)
            botao.clicked.connect(lambda _=False, i=indice: self._editor.usar_sugestao(i))
            self._sugestoes_layout.addWidget(botao, 1)
            self._botoes_sugestao.append(botao)
        for indice, botao in enumerate(self._botoes_sugestao):
            if indice < len(palavras):
                botao.setText(palavras[indice])
                botao.show()
            else:
                botao.hide()
        self._faixa_sugestoes.setVisible(self._sugestoes_ativas)
        self._sincronizar_modificadores()

    def _sincronizar_modificadores(self) -> None:
        # Cada modificador (shift, ctrl) reflete o estado do editor com o mesmo nome.
        for nome, botao in self._botoes_modificador.items():
            botao.setChecked(bool(getattr(self._editor, nome, False)))
        self._atualizar_simbolos_shift()

    def _atualizar_simbolos_shift(self) -> None:
        """Com Shift ativo, cada tecla de texto mostra o simbolo que escreve com Shift."""
        for botao, tecla in self._teclas_texto:
            novo = tecla.rotulo
            if self._editor.shift:
                simbolo = tecla.shift or self._editor.simbolo_shift(tecla.acao.valor)
                valor = tecla.acao.valor
                if simbolo:
                    novo = simbolo
                elif len(valor) == 1 and valor.isalpha():
                    novo = valor.upper()  # letras: com Shift mostram a maiuscula, como no teclado fisico
            botao.definir_texto(novo)

    def aplicar_tema(self, tema: Tema) -> None:
        self._tema_atual = tema
        self._cor_fundo = QColor(tema.cor_fundo)
        definir_modo_escuro(_luminosidade(tema.cor_fundo) <= 0.5)
        paleta = _derivar_paleta(tema)
        self._cor_borda_topo = QColor(paleta["borda"])
        for botao, nome in self._botoes_icone:
            botao.definir_icone(self._imagem_da_tecla(nome))
        self._etiqueta_layout.setStyleSheet(
            f"color:{paleta['texto_suave']}; font-size:12px; font-weight:600; padding:2px 8px;"
        )
        self._tamanho_fonte = tema.tamanho_fonte
        for botao in self._botoes_teclas:
            botao.definir_tamanho_base(tema.tamanho_fonte)
        self._imagem = carregar_imagem_fundo(tema.imagem_fundo) if tema.imagem_fundo else None
        self._opacidade = tema.opacidade_imagem / 100
        self.setStyleSheet(folha_de_estilo(tema))
        for interruptor in self._interruptores:
            interruptor.definir_cores(paleta["util_fundo"], tema.cor_texto)
        self._botao_definicoes.setIcon(_icone_definicoes(tema.cor_texto))
        self._atualizar_logo_marca(tema)
        self._atualizar_cache_imagem()
        self.update()

    def _atualizar_logo_marca(self, tema: Tema) -> None:
        claro = _luminosidade(tema.cor_fundo) > 0.5
        ficheiro = DADOS_PROJETO / "icone" / ("kikoia_texto.png" if claro else "kikoia_texto_escuro.png")
        pix = QPixmap(str(ficheiro))
        if not pix.isNull():
            self._logo_marca.setPixmap(pix.scaledToHeight(20, Qt.TransformationMode.SmoothTransformation))
            self._logo_marca.setVisible(True)
        else:
            self._logo_marca.setVisible(False)

    def _ancorar(self) -> None:
        """Ocupa a largura toda, na parte inferior do ecra, e reserva essa area ao Windows.

        Com a reserva, as janelas maximizadas ficam acima do teclado.
        """
        ecra = QGuiApplication.primaryScreen()
        area = ecra.availableGeometry()
        ratio = ecra.devicePixelRatio() or 1.0
        # Com X11, a altura vem da area util sem o proprio teclado (a reserva demora a ser atualizada pelo gestor).
        base = self._barra.area_base()
        altura_de_referencia = base[3] / ratio if base is not None else area.height()
        altura = max(ALTURA_MINIMA, int(altura_de_referencia * ALTURA_RELATIVA))
        self._barra.remover()  # se ja estava registada (ex.: reaberta), refaz de forma limpa
        pode_reservar = not sys.platform.startswith("linux") or QGuiApplication.platformName() == "xcb"
        if self._ancorar_fundo and pode_reservar and self._barra.registar(int(self.winId())):
            posicao = self._barra.posicionar(round(altura * ratio))
            if posicao is not None:
                x, y, w, h = posicao
                self.setGeometry(QRect(round(x / ratio), round(y / ratio),
                                       round(w / ratio), round(h / ratio)))
                return
        # Sem reserva (outro sistema ou desligada): so posiciona no fundo.
        self.setGeometry(area.x(), area.y() + area.height() - altura, area.width(), altura)

    def posicionar_no_fundo(self) -> None:
        self._ancorar()

    def showEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        super().showEvent(evento)
        self._ancorar()

    def hideEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        super().hideEvent(evento)
        self._barra.remover()  # sem teclado visivel, a area volta a ser toda das janelas

    def _atualizar_cache_imagem(self) -> None:
        """Escala a imagem para o tamanho da janela uma so vez (nao em cada repaint)."""
        if self._imagem is None or self.width() <= 0 or self.height() <= 0:
            self._imagem_escalada = None
            return
        self._imagem_escalada = QPixmap.fromImage(
            self._imagem.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        super().resizeEvent(evento)
        self._atualizar_cache_imagem()

    # --- acoes -----------------------------------------------------------

    def _premir(self, tecla: Tecla) -> None:
        if tecla.acao.tipo == "texto":
            # Com Shift ativo, a tecla escreve o seu simbolo proprio (se o tiver).
            valor = tecla.shift if (tecla.shift and self._editor.shift) else tecla.acao.valor
            self._editor.texto(valor)
        elif tecla.acao.tipo == "modificador":
            self._editor.modificador(tecla.acao.valor)
        elif tecla.acao.tipo == "acento":
            self._editor.acento(tecla.acao.valor)
        elif tecla.acao.tipo == "multitoque":
            self._editor.multitoque(id(tecla), tecla.acao.valor)
        elif tecla.acao.tipo == "acao":
            self._editor.acao(tecla.acao.valor)
        elif tecla.acao.tipo == "navegar":
            self._ao_navegar(tecla.acao.valor)
        elif tecla.acao.tipo == "comando":
            self._ao_comando(tecla.acao.valor)
        elif tecla.acao.tipo == "quadro":
            self._ao_quadro(tecla.acao.valor)
        else:
            self._editor.tecla(tecla.acao.valor)
        # Uma tecla pode consumir um modificador (Shift, Ctrl): o botao tem de refletir isso.
        self._sincronizar_modificadores()

    def sem_sobreposicao(self, funcao: Callback):
        """Executa uma janela de dialogo com o teclado recolhido.

        O teclado esta sempre por cima; sem recolher, taparia o dialogo.
        """
        estava_visivel = self.isVisible()
        self._recolher_no_fim = False
        self.hide()
        self.em_dialogo_aberto = True
        try:
            return funcao()
        finally:
            self.em_dialogo_aberto = False
            if estava_visivel and not self._recolher_no_fim:
                self.show()

    def closeEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        # O X fecha o Kikoia por completo. Sem isto, so a janela saia e o processo ficava a correr.
        self._ao_fechar()
        super().closeEvent(evento)

    def recolher_definitivamente(self) -> None:
        """Esconde o teclado mesmo que um dialogo o tenha recolhido (ex.: o telemovel ligou-se)."""
        self._recolher_no_fim = True
        self.hide()

    # --- desenho ---------------------------------------------------------

    def paintEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        pintor = QPainter(self)
        pintor.fillRect(self.rect(), self._cor_fundo)
        if self._imagem_escalada is not None:
            escalada = self._imagem_escalada
            x = (self.width() - escalada.width()) // 2
            y = (self.height() - escalada.height()) // 2
            pintor.setOpacity(self._opacidade)
            pintor.drawPixmap(x, y, escalada)
            pintor.setOpacity(1.0)
        if hasattr(self, "_cor_borda_topo"):
            pintor.fillRect(0, 0, self.width(), 1, self._cor_borda_topo)
        pintor.end()
