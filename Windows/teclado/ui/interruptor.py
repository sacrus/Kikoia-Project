"""Interruptor ON/OFF: deslizador com um LED vermelho quando esta ligado.

E um QPushButton marcado como "checkable", por isso o resto do codigo (sinais,
click, isChecked) continua a funcionar sem alteracoes.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton

COR_TRILHO_LIGADO = QColor("#43A047")
COR_TRILHO_DESLIGADO = QColor("#9E9E9E")
COR_LED = QColor("#E53935")
COR_LED_APAGADO = QColor("#4A1010")
COR_HALO = QColor(229, 57, 53, 80)


class Interruptor(QPushButton):
    def __init__(self, texto: str, parent=None) -> None:
        super().__init__(texto, parent)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cor_fundo = QColor("#FFFFFF")
        self._cor_texto = QColor("#000000")
        self.toggled.connect(lambda _=False: self.update())

    def sizeHint(self) -> QSize:  # noqa: N802 (nome exigido pelo Qt)
        # Largura = texto + LED (34 px) + deslizador (66 px) + margem: o texto nunca e cortado.
        largura = self.fontMetrics().horizontalAdvance(self.text()) + 120
        return QSize(max(largura, 128), 44)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (nome exigido pelo Qt)
        return self.sizeHint()

    def definir_cores(self, fundo: str, texto: str) -> None:
        self._cor_fundo = QColor(fundo)
        self._cor_texto = QColor(texto)
        self.update()

    def paintEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            pintor.setOpacity(0.4)

        area = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        cy = area.center().y()
        ligado = self.isChecked()

        # Caixa do botao
        pintor.setPen(QPen(self._cor_texto, 2))
        pintor.setBrush(self._cor_fundo)
        pintor.drawRoundedRect(area, 10, 10)

        # LED: aceso (com halo) quando ligado, escuro quando desligado
        led = QPointF(area.left() + 18, cy)
        pintor.setPen(Qt.PenStyle.NoPen)
        if ligado:
            pintor.setBrush(COR_HALO)
            pintor.drawEllipse(led, 10, 10)
            pintor.setBrush(COR_LED)
        else:
            pintor.setBrush(COR_LED_APAGADO)
        pintor.drawEllipse(led, 6, 6)

        # Deslizador a direita
        trilho = QRectF(area.right() - 60, cy - 11, 46, 22)
        pintor.setBrush(COR_TRILHO_LIGADO if ligado else COR_TRILHO_DESLIGADO)
        pintor.drawRoundedRect(trilho, 11, 11)
        x = trilho.right() - 19 if ligado else trilho.left() + 3
        pintor.setBrush(QColor("white"))
        pintor.drawEllipse(QRectF(x, cy - 8, 16, 16))

        # Texto entre o LED e o deslizador
        texto_area = QRectF(area.left() + 34, area.top(), area.width() - 34 - 66, area.height())
        pintor.setPen(self._cor_texto)
        pintor.drawText(texto_area, Qt.AlignmentFlag.AlignCenter, self.text())
        pintor.end()
