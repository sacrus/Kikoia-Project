"""Janela do teclado: sempre por cima, sem roubar o foco, no fundo do ecra.

Se o foco mudasse para esta janela, a aplicacao de destino deixaria de receber
as teclas. Por isso usa-se WindowDoesNotAcceptFocus (no Windows aplica
WS_EX_NOACTIVATE) e nenhum botao aceita foco de teclado.

A janela e um complemento: so mostra o teclado, as sugestoes e uma barra
minima (Sugestoes, Voz, roda dentada). Tudo o resto esta nas Definicoes.
"""

from __future__ import annotations

import math
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
from teclado.core.idiomas import t
from teclado.core.layout import Layout, Tecla
from teclado.core.tema import Tema
from teclado.ui.appbar import BarraInferior
from teclado.ui.interruptor import Interruptor
from teclado.ui.medidor import Medidor

Callback = Callable[[], object]

# Imagens maiores do que isto sao reduzidas uma vez ao carregar (memoria e velocidade).
LADO_MAXIMO_IMAGEM = 1600
# Altura do teclado: parte do ecra, com um minimo para as teclas continuarem legiveis.
ALTURA_RELATIVA = 0.42
ALTURA_MINIMA = 260
# Faixa das sugestoes: reservada enquanto as sugestoes estiverem ativas, mesmo sem palavras,
# para que as teclas nao mudem de posicao quando aparecem ou desaparecem sugestoes.
ALTURA_FAIXA_SUGESTOES = 44


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
    return f"""
    QPushButton {{
        background-color: {tema.cor_tecla};
        color: {tema.cor_texto};
        font-size: {tema.tamanho_fonte}px;
        border: 2px solid {tema.cor_texto};
        border-radius: 8px;
        padding: 4px;
    }}
    QPushButton:pressed, QPushButton:checked {{
        background-color: {tema.cor_tecla_premida};
        color: {tema.cor_texto_premido};
    }}
    QPushButton:disabled {{
        opacity: 0.4;
    }}
    """


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
    ) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
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
        self._ancorar_fundo = ancorar_fundo
        self._barra = BarraInferior()
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

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(6, 6, 6, 6)

        self._faixa_sugestoes = QWidget()
        self._sugestoes_layout = QHBoxLayout(self._faixa_sugestoes)
        self._sugestoes_layout.setContentsMargins(0, 0, 0, 0)
        self._faixa_sugestoes.setFixedHeight(ALTURA_FAIXA_SUGESTOES)
        raiz.addWidget(self._faixa_sugestoes)

        self._area_teclas = QVBoxLayout()
        raiz.addLayout(self._area_teclas, 1)

        raiz.addLayout(self._construir_barra())

        self.aplicar_tema(tema)
        self.montar(layout)
        self._atualizar_sugestoes()

    # --- barra minima ----------------------------------------------------

    def _construir_barra(self) -> QHBoxLayout:
        barra = QHBoxLayout()

        self._botao_sugestoes = Interruptor(t("janela.sugestoes"))
        self._botao_sugestoes.setCheckable(True)
        self._botao_sugestoes.setChecked(True)
        self._botao_sugestoes.setToolTip(t("janela.sugestoes_dica"))
        self._botao_sugestoes.toggled.connect(self._alternar_sugestoes)

        # Voz: dois interruptores. O estado real vem de configurar_voz().
        self._botao_falar = Interruptor(t("janela.falar"))
        self._botao_falar.setCheckable(True)
        self._botao_falar.setEnabled(False)
        self._botao_falar.toggled.connect(lambda ativo: self._ao_falar_toggle(ativo))

        self._botao_ditar = Interruptor(t("janela.ditar"))
        self._botao_ditar.setCheckable(True)
        self._botao_ditar.setEnabled(False)
        self._botao_ditar.toggled.connect(lambda ativo: self._ao_ditar_toggle(ativo))

        self._botao_definicoes = _botao_sem_foco("")
        self._botao_definicoes.setIconSize(QSize(26, 26))
        self._botao_definicoes.setFixedSize(40, 40)
        self._botao_definicoes.setToolTip(t("janela.definicoes_dica"))
        self._botao_definicoes.clicked.connect(lambda _=False: self._pedir_definicoes())

        # Medidor e mensagem so aparecem com o Ditar ligado.
        self._medidor = Medidor()
        self._medidor.setVisible(False)
        self._aviso = QLabel()
        self._aviso.setStyleSheet(
            "background:#263238; color:#FFEB3B; font-weight:bold; border-radius:6px; padding:4px 8px;"
        )
        self._aviso.setVisible(False)

        # Indicador do teclado fisico: visivel sempre que as teclas estao a ser observadas.
        self._indicador_fisico = QLabel(t("janela.teclado_fisico"))
        self._indicador_fisico.setStyleSheet(
            "color:#E53935; font-weight:bold; padding:4px 6px; border:1px solid #E53935; border-radius:6px;"
        )
        self._indicador_fisico.setToolTip(t("janela.teclado_fisico_dica"))
        self._indicador_fisico.setVisible(False)

        self._interruptores = [self._botao_sugestoes, self._botao_falar, self._botao_ditar]
        barra.addWidget(self._botao_sugestoes)
        barra.addWidget(self._botao_falar)
        barra.addWidget(self._botao_ditar)
        barra.addWidget(self._medidor)
        barra.addWidget(self._aviso)
        barra.addWidget(self._indicador_fisico)
        barra.addStretch(1)
        barra.addWidget(self._botao_definicoes)
        return barra

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
        botao = _botao_sem_foco(texto)
        botao.setMinimumSize(24, 24)
        botao.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        botao.clicked.connect(lambda _=False: ao_premir())
        return botao

    def montar(self, layout: Layout) -> None:
        """Reconstroi as teclas a partir do layout."""
        while self._area_teclas.count():
            item = self._area_teclas.takeAt(0)
            antiga = item.widget()
            if antiga is not None:
                antiga.hide()
                antiga.setParent(None)  # sai da arvore ja; apaga-se no proximo ciclo
                antiga.deleteLater()
        self._botoes_modificador.clear()

        for linha in layout.linhas:
            fila = QWidget()
            horizontal = QHBoxLayout(fila)
            horizontal.setContentsMargins(0, 0, 0, 0)
            horizontal.setSpacing(6)
            for tecla in linha:
                botao = self._botao_tecla(tecla.rotulo, lambda t=tecla: self._premir(t))
                if tecla.acao.tipo == "modificador":
                    botao.setCheckable(True)
                    self._botoes_modificador[tecla.acao.valor] = botao
                horizontal.addWidget(botao, max(1, round(tecla.largura * 10)))
            self._area_teclas.addWidget(fila, 1)

        self._modelo_layout = layout
        self.setWindowTitle(t("janela.titulo", nome=layout.nome))

    def _atualizar_sugestoes(self) -> None:
        palavras = self._editor.sugestoes
        while len(self._botoes_sugestao) < len(palavras):
            indice = len(self._botoes_sugestao)
            botao = _botao_sem_foco("")
            botao.setMinimumHeight(44)
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

    def aplicar_tema(self, tema: Tema) -> None:
        self._cor_fundo = QColor(tema.cor_fundo)
        self._imagem = carregar_imagem_fundo(tema.imagem_fundo) if tema.imagem_fundo else None
        self._opacidade = tema.opacidade_imagem / 100
        self.setStyleSheet(folha_de_estilo(tema))
        for interruptor in self._interruptores:
            interruptor.definir_cores(tema.cor_tecla, tema.cor_texto)
        self._botao_definicoes.setIcon(_icone_definicoes(tema.cor_texto))
        self._atualizar_cache_imagem()
        self.update()

    def _ancorar(self) -> None:
        """Ocupa a largura toda, na parte inferior do ecra, e reserva essa area ao Windows.

        Com a reserva, as janelas maximizadas ficam acima do teclado.
        """
        ecra = QGuiApplication.primaryScreen()
        area = ecra.availableGeometry()
        ratio = ecra.devicePixelRatio() or 1.0
        altura = max(ALTURA_MINIMA, int(area.height() * ALTURA_RELATIVA))
        self._barra.remover()  # se ja estava registada (ex.: reaberta), refaz de forma limpa
        if self._ancorar_fundo and self._barra.registar(int(self.winId())):
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
            self._editor.texto(tecla.acao.valor)
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
        try:
            return funcao()
        finally:
            if estava_visivel and not self._recolher_no_fim:
                self.show()

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
        pintor.end()
