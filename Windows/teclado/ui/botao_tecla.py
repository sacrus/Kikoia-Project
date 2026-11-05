"""Tecla do teclado com texto que cabe sempre: reduz a letra e, se preciso, parte o texto em linhas."""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QPushButton

TAMANHO_MINIMO = 7  # pixeis: abaixo disto o texto ja nao se le
MARGEM = 14  # pixeis reservados para borda e padding (folha de estilo)


def _quebrar(texto: str, metrica: QFontMetrics, largura: int) -> list[str] | None:
    """Parte o texto em linhas que cabem na largura. None se alguma palavra nao couber."""
    linhas: list[str] = []
    atual = ""
    for palavra in texto.split():
        if metrica.horizontalAdvance(palavra) > largura:
            return None
        candidata = f"{atual} {palavra}" if atual else palavra
        if metrica.horizontalAdvance(candidata) <= largura:
            atual = candidata
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas or [texto]


class BotaoTecla(QPushButton):
    def __init__(self, texto: str, tamanho_base: int) -> None:
        super().__init__(texto)
        self._texto = texto
        self._base = tamanho_base
        self._tamanho_atual = tamanho_base

    def definir_tamanho_base(self, tamanho: int) -> None:
        self._base = tamanho
        self.ajustar()

    def resizeEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        super().resizeEvent(evento)
        self.ajustar()

    def ajustar(self) -> None:
        """Escolhe o maior tamanho (do base ate ao minimo) em que o texto cabe no botao."""
        largura = self.width() - MARGEM
        altura = self.height() - MARGEM
        if largura <= 0 or altura <= 0 or not self._texto:
            return
        escolhido, linhas = TAMANHO_MINIMO, None
        for tamanho in range(self._base, TAMANHO_MINIMO - 1, -1):
            fonte = QFont(self.font())
            fonte.setPixelSize(tamanho)
            metrica = QFontMetrics(fonte)
            quebrado = _quebrar(self._texto, metrica, largura)
            if quebrado is not None and len(quebrado) * metrica.height() <= altura:
                escolhido, linhas = tamanho, quebrado
                break
        if linhas is None:
            # Nem o minimo cabe inteiro: fica o minimo, com as linhas que couberem.
            fonte = QFont(self.font())
            fonte.setPixelSize(TAMANHO_MINIMO)
            linhas = _quebrar(self._texto, QFontMetrics(fonte), largura) or [self._texto]
        self._aplicar(escolhido, "\n".join(linhas) if len(linhas) > 1 else self._texto)

    def _aplicar(self, tamanho: int, texto: str) -> None:
        if tamanho != self._tamanho_atual:
            # So ha folha propria quando o tamanho difere do da tema (evita repintar a toa).
            self.setStyleSheet("" if tamanho == self._base else f"font-size: {tamanho}px;")
            self._tamanho_atual = tamanho
        if self.text() != texto:
            self.setText(texto)
