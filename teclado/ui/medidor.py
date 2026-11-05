"""Medidor de barras: anima-se com o nivel do microfone enquanto o ditado esta ativo."""

from __future__ import annotations

import random

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

NUM_BARRAS = 14
PISO_DB = -60.0      # abaixo disto a barra fica no minimo
INTERVALO_MS = 60


class Medidor(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._alvo = 0.0      # nivel da ultima medicao, 0..1
        self._nivel = 0.0     # nivel suavizado
        self._barras = [0.0] * NUM_BARRAS
        self.setFixedSize(NUM_BARRAS * 9, 28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._passo)

    def definir_nivel_db(self, db: float) -> None:
        self._alvo = max(0.0, min(1.0, (db - PISO_DB) / -PISO_DB))

    def showEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        super().showEvent(evento)
        self._timer.start(INTERVALO_MS)

    def hideEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        super().hideEvent(evento)
        self._timer.stop()

    def _passo(self) -> None:
        # Sobe logo com o som e desce devagar; cada barra tem um pouco de variacao.
        self._nivel = max(self._alvo, self._nivel * 0.88)
        for i in range(NUM_BARRAS):
            alvo_barra = self._nivel * (0.55 + 0.45 * random.random())
            self._barras[i] = max(alvo_barra, self._barras[i] * 0.8)
        self.update()

    def paintEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        pintor = QPainter(self)
        pintor.setPen(Qt.PenStyle.NoPen)
        largura = self.width() / NUM_BARRAS
        altura = self.height()
        for i, nivel in enumerate(self._barras):
            h = max(2.0, nivel * altura)
            if nivel < 0.7:
                cor = QColor("#43A047")   # ate ~-18 dB: normal
            elif nivel < 0.9:
                cor = QColor("#FDD835")   # ~-18 a -6 dB: forte
            else:
                cor = QColor("#E53935")   # acima de -6 dB: a saturar
            pintor.setBrush(cor)
            pintor.drawRoundedRect(QRectF(i * largura + 2, altura - h, largura - 4, h), 2, 2)
        pintor.end()
