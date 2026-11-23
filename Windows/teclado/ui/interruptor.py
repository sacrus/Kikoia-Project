"""Interruptor compacto ON/OFF em formato de pilula com icone e indicador de estado.

E um QPushButton marcado como "checkable", por isso o resto do codigo (sinais,
click, isChecked) continua a funcionar sem alteracoes.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QPushButton

COR_ATIVO = QColor("#16A34A")
COR_ATIVO_FUNDO_CLARO = QColor(22, 163, 74, 34)
COR_ATIVO_FUNDO_ESCURO = QColor(34, 197, 94, 48)
COR_INATIVO_PONTO = QColor("#94A3B8")


def _luminosidade(cor: QColor) -> float:
    return (0.299 * cor.red() + 0.587 * cor.green() + 0.114 * cor.blue()) / 255.0


def _desenhar_icone(pintor: QPainter, tipo: str, centro: QPointF, cor: QColor) -> None:
    """Desenha um icone vetorial simples (14x14) sem depender de emojis do sistema."""
    pintor.save()
    caneta = QPen(cor, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    pintor.setPen(caneta)
    pintor.setBrush(Qt.BrushStyle.NoBrush)
    cx, cy = centro.x(), centro.y()

    if tipo == "sugestoes":
        # Balao de dialogo com tres pontinhos
        balao = QRectF(cx - 6.5, cy - 5.5, 13.0, 9.0)
        pintor.drawRoundedRect(balao, 3.0, 3.0)
        cauda = QPainterPath()
        cauda.moveTo(cx - 2.5, cy + 3.5)
        cauda.lineTo(cx - 4.5, cy + 6.2)
        cauda.lineTo(cx + 0.2, cy + 3.5)
        pintor.drawPath(cauda)
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.setBrush(cor)
        for dx in (-3.0, 0.0, 3.0):
            pintor.drawEllipse(QPointF(cx + dx, cy - 1.0), 1.0, 1.0)
    elif tipo == "falar":
        # Altifalante com onda sonora
        cone = QPolygonF([
            QPointF(cx - 6.0, cy - 2.2),
            QPointF(cx - 3.2, cy - 2.2),
            QPointF(cx + 0.2, cy - 5.2),
            QPointF(cx + 0.2, cy + 5.2),
            QPointF(cx - 3.2, cy + 2.2),
            QPointF(cx - 6.0, cy + 2.2),
        ])
        pintor.setBrush(cor)
        pintor.drawPolygon(cone)
        pintor.setBrush(Qt.BrushStyle.NoBrush)
        pintor.drawArc(QRectF(cx - 0.5, cy - 3.5, 4.5, 7.0), -50 * 16, 100 * 16)
        pintor.drawArc(QRectF(cx + 0.5, cy - 5.5, 6.0, 11.0), -50 * 16, 100 * 16)
    elif tipo == "ditar":
        # Microfone classico
        pintor.drawRoundedRect(QRectF(cx - 2.6, cy - 6.0, 5.2, 7.6), 2.5, 2.5)
        pintor.drawArc(QRectF(cx - 5.0, cy - 3.0, 10.0, 7.5), 180 * 16, 180 * 16)
        pintor.drawLine(QPointF(cx, cy + 4.5), QPointF(cx, cy + 6.5))
        pintor.drawLine(QPointF(cx - 2.8, cy + 6.5), QPointF(cx + 2.8, cy + 6.5))

    pintor.restore()


class Interruptor(QPushButton):
    def __init__(self, texto: str, parent=None, *, icone: str | None = None) -> None:
        super().__init__(texto, parent)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icone = icone
        self._cor_fundo = QColor("#FFFFFF")
        self._cor_texto = QColor("#1A1D23")
        self._sob_rato = False
        self.toggled.connect(lambda _=False: self.update())

    def _fonte_rotulo(self) -> QFont:
        fonte = QFont(self.font())
        fonte.setPixelSize(13)
        fonte.setWeight(QFont.Weight.Medium)
        return fonte

    def sizeHint(self) -> QSize:  # noqa: N802 (nome exigido pelo Qt)
        metrica = self.fontMetrics()
        # Usa a metrica da fonte compacta de 13px
        from PySide6.QtGui import QFontMetrics
        metrica = QFontMetrics(self._fonte_rotulo())
        extra_icone = 22 if self._icone else 0
        largura = metrica.horizontalAdvance(self.text()) + extra_icone + 36
        return QSize(max(largura, 86), 34)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (nome exigido pelo Qt)
        return self.sizeHint()

    def definir_cores(self, fundo: str, texto: str) -> None:
        self._cor_fundo = QColor(fundo)
        self._cor_texto = QColor(texto)
        self.update()

    def enterEvent(self, evento) -> None:  # noqa: N802
        self._sob_rato = True
        self.update()
        super().enterEvent(evento)

    def leaveEvent(self, evento) -> None:  # noqa: N802
        self._sob_rato = False
        self.update()
        super().leaveEvent(evento)

    def paintEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            pintor.setOpacity(0.42)

        area = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        raio = area.height() / 2.0
        cy = area.center().y()
        ligado = self.isChecked()
        claro = _luminosidade(self._cor_fundo) > 0.5

        # Fundo da pilula
        if ligado:
            fundo = COR_ATIVO_FUNDO_CLARO if claro else COR_ATIVO_FUNDO_ESCURO
            borda = QColor(22, 163, 74, 150) if claro else QColor(74, 222, 128, 160)
        else:
            fundo = QColor(self._cor_fundo)
            if self._sob_rato and self.isEnabled():
                fundo = fundo.darker(106) if claro else fundo.lighter(115)
            borda = QColor(self._cor_texto)
            borda.setAlpha(35 if claro else 45)

        pintor.setPen(QPen(borda, 1.0))
        pintor.setBrush(fundo)
        pintor.drawRoundedRect(area, raio, raio)

        # Icone (se existir) a esquerda
        x_texto = area.left() + 12.0
        if self._icone:
            cor_ic = COR_ATIVO if ligado else self._cor_texto
            _desenhar_icone(pintor, self._icone, QPointF(area.left() + 17.0, cy), cor_ic)
            x_texto = area.left() + 30.0

        # Ponto indicador de estado a direita
        ponto_x = area.right() - 12.0
        pintor.setPen(Qt.PenStyle.NoPen)
        if ligado:
            pintor.setBrush(QColor(22, 163, 74, 70))
            pintor.drawEllipse(QPointF(ponto_x, cy), 6.0, 6.0)
            pintor.setBrush(COR_ATIVO)
            pintor.drawEllipse(QPointF(ponto_x, cy), 3.6, 3.6)
        else:
            pintor.setBrush(COR_INATIVO_PONTO)
            pintor.drawEllipse(QPointF(ponto_x, cy), 3.2, 3.2)

        # Texto legivel entre o icone e o indicador
        pintor.setFont(self._fonte_rotulo())
        pintor.setPen(self._cor_texto)
        texto_area = QRectF(x_texto, area.top(), ponto_x - 8.0 - x_texto, area.height())
        pintor.drawText(texto_area, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        pintor.end()
