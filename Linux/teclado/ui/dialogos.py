"""Dialogos: codigo do adulto e personalizacao (cores e imagem num so ecra)."""

from __future__ import annotations

from pathlib import Path

from teclado.core.idiomas import t
from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teclado.core.tema import Tema, cor_texto_para

# Diálogos Qt próprios (não nativos): comportamento previsível no Windows
# e funcionam dentro de uma janela que não aceita foco.
_NAO_NATIVO_COR = QColorDialog.ColorDialogOption.DontUseNativeDialog
_NAO_NATIVO_FICHEIRO = QFileDialog.Option.DontUseNativeDialog
def filtro_imagens() -> str:
    return f"{t('dialogos.filtro_imagens')} (*.png *.jpg *.jpeg *.bmp)"
TAMANHO_PREVIA = (360, 180)
ACEITE = int(QDialog.DialogCode.Accepted)


def _estado_desejado(dialogo: QDialog) -> Qt.WindowState:
    """Estado com que o diálogo deve abrir (normal, salvo se o diálogo pedir outro)."""
    return getattr(dialogo, "estado_inicial", Qt.WindowState.WindowNoState)


def _trazer_para_frente(dialogo: QDialog) -> None:
    if dialogo.isVisible():
        dialogo.setWindowState(_estado_desejado(dialogo))  # tira o estado minimizado
        dialogo.raise_()
        dialogo.activateWindow()


def executar_dialogo(dialogo: QDialog) -> int:
    """Mostra um diálogo modal e garante que fica visível e com foco.

    Depois de o teclado ser recolhido, nenhuma janela está ativa. Sem isto, o
    Windows pode abrir o diálogo minimizado (só aparece na barra de tarefas).
    Um diálogo pode definir `estado_inicial` (ex.: maximizado) e é esse o estado
    usado.
    """
    dialogo.setWindowState(_estado_desejado(dialogo))
    dialogo.show()
    dialogo.raise_()
    dialogo.activateWindow()
    # Repete depois de o ciclo de eventos arrancar, quando o Windows ja processou a janela.
    QTimer.singleShot(0, lambda: _trazer_para_frente(dialogo))
    return dialogo.exec()


def pedir_pin(parent: QWidget | None) -> str | None:
    caixa = QInputDialog(parent)
    caixa.setWindowTitle(t("dialogos.codigo_adulto"))
    caixa.setLabelText(t("dialogos.codigo_adulto_texto"))
    caixa.setTextEchoMode(QLineEdit.EchoMode.Password)
    if executar_dialogo(caixa) != ACEITE:
        return None
    return caixa.textValue()


def imagem_valida(caminho: Path) -> bool:
    return not QImage(str(caminho)).isNull()


class DialogoPersonalizacao(QDialog):
    """Escolha de cor de fundo, cor das teclas e imagem, com pré-visualização.

    Tudo acontece dentro deste diálogo: não há diálogos encadeados.
    """

    def __init__(self, parent: QWidget | None, tema_atual: Tema) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("dialogos.personalizar"))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._fundo = QColor(tema_atual.cor_fundo)
        self._tecla = QColor(tema_atual.cor_tecla)
        self._imagem: Path | None = tema_atual.imagem_fundo

        self._previa = QLabel()
        self._previa.setFixedSize(*TAMANHO_PREVIA)
        self._etiqueta_imagem = QLabel()
        self._atualizar_previa()

        botao_fundo = QPushButton(t("dialogos.cor_fundo"))
        botao_fundo.clicked.connect(self._escolher_fundo)
        botao_tecla = QPushButton(t("dialogos.cor_teclas"))
        botao_tecla.clicked.connect(self._escolher_tecla)
        botao_imagem = QPushButton(t("dialogos.escolher_imagem"))
        botao_imagem.clicked.connect(self._escolher_imagem)
        botao_sem_imagem = QPushButton(t("dialogos.remover_imagem"))
        botao_sem_imagem.clicked.connect(self._remover_imagem)

        linha_cores = QHBoxLayout()
        linha_cores.addWidget(botao_fundo)
        linha_cores.addWidget(botao_tecla)
        linha_imagem = QHBoxLayout()
        linha_imagem.addWidget(botao_imagem)
        linha_imagem.addWidget(botao_sem_imagem)

        caixa = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        caixa.accepted.connect(self.accept)
        caixa.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.addWidget(self._previa)
        raiz.addWidget(self._etiqueta_imagem)
        raiz.addLayout(linha_cores)
        raiz.addLayout(linha_imagem)
        raiz.addWidget(caixa)

    # --- pre-visualizacao -----------------------------------------------

    def _atualizar_previa(self) -> None:
        largura, altura = TAMANHO_PREVIA
        tela = QPixmap(largura, altura)
        tela.fill(self._fundo)
        pintor = QPainter(tela)
        if self._imagem is not None:
            imagem = QImage(str(self._imagem))
            if not imagem.isNull():
                escalada = imagem.scaled(
                    largura, altura,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                pintor.setOpacity(0.5)
                pintor.drawImage(
                    (largura - escalada.width()) // 2,
                    (altura - escalada.height()) // 2,
                    escalada,
                )
                pintor.setOpacity(1.0)
        tecla = QRect(largura // 2 - 40, altura // 2 - 30, 80, 60)
        pintor.setBrush(self._tecla)
        pintor.setPen(QColor(cor_texto_para(self._tecla.name())))
        pintor.drawRoundedRect(tecla, 8, 8)
        pintor.drawText(tecla, Qt.AlignmentFlag.AlignCenter, "A")
        pintor.end()
        self._previa.setPixmap(tela)
        self._etiqueta_imagem.setText(
            t("dialogos.imagem_atual", nome=self._imagem.name) if self._imagem else t("dialogos.sem_imagem")
        )

    # --- acoes -----------------------------------------------------------

    def _escolher_fundo(self) -> None:
        cor = QColorDialog.getColor(self._fundo, self, t("dialogos.cor_fundo_titulo"), _NAO_NATIVO_COR)
        if cor.isValid():
            self._fundo = cor
            self._atualizar_previa()

    def _escolher_tecla(self) -> None:
        cor = QColorDialog.getColor(self._tecla, self, t("dialogos.cor_teclas_titulo"), _NAO_NATIVO_COR)
        if cor.isValid():
            self._tecla = cor
            self._atualizar_previa()

    def _escolher_imagem(self) -> None:
        ficheiro, _ = QFileDialog.getOpenFileName(
            self, t("dialogos.imagem_fundo_titulo"), "", filtro_imagens(), "", _NAO_NATIVO_FICHEIRO
        )
        if not ficheiro:
            return
        caminho = Path(ficheiro)
        if not imagem_valida(caminho):
            QMessageBox.warning(self, t("dialogos.imagem_invalida"), t("dialogos.imagem_erro"))
            return
        self._imagem = caminho
        self._atualizar_previa()

    def _remover_imagem(self) -> None:
        self._imagem = None
        self._atualizar_previa()

    # --- resultado -------------------------------------------------------

    def escolhas(self) -> dict:
        return {
            "cor_fundo": self._fundo.name(),
            "cor_tecla": self._tecla.name(),
            "imagem": self._imagem,
        }


def escolher_personalizacao(parent: QWidget | None, tema_atual: Tema) -> dict | None:
    """Mostra o diálogo. Devolve as escolhas se confirmado, ou None se cancelado."""
    dialogo = DialogoPersonalizacao(parent, tema_atual)
    if executar_dialogo(dialogo) != ACEITE:
        return None
    return dialogo.escolhas()
