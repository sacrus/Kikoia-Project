"""Opcoes do teclado fisico: explica o que e observado e pede confirmacao ao ligar."""

from __future__ import annotations

from teclado.core.idiomas import t
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

def texto_explicacao() -> str:
    return (
        t("tecladofisico.explicacao_1")
        + t("tecladofisico.explicacao_2")
        + t("tecladofisico.explicacao_3")
        + t("tecladofisico.explicacao_4")
        + t("tecladofisico.explicacao_5")
        + t("tecladofisico.explicacao_6")
        + t("tecladofisico.explicacao_7")
    )


class DialogoTecladoFisico(QDialog):
    def __init__(self, parent: QWidget | None, ativo: bool, aprender: bool,
                 motivo_indisponivel: str | None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("tecladofisico.titulo"))
        self._ativo_inicial = ativo
        self._ativar = QCheckBox(t("tecladofisico.mostrar"))
        self._aprender = QCheckBox(t("tecladofisico.aprender"))
        self._ativar.setChecked(ativo and motivo_indisponivel is None)
        self._aprender.setChecked(aprender)
        self._ativar.toggled.connect(self._aprender.setEnabled)
        self._aprender.setEnabled(self._ativar.isChecked())

        explicacao = QLabel(texto_explicacao())
        explicacao.setWordWrap(True)
        caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        caixa.accepted.connect(self._confirmar)
        caixa.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.addWidget(explicacao)
        raiz.addWidget(self._ativar)
        raiz.addWidget(self._aprender)
        if motivo_indisponivel:
            aviso = QLabel(motivo_indisponivel)
            aviso.setWordWrap(True)
            self._ativar.setEnabled(False)
            self._aprender.setEnabled(False)
            raiz.addWidget(aviso)
        raiz.addWidget(caixa)

    def _confirmar(self) -> None:
        # Ligar pela primeira vez pede confirmacao explicita: e uma funcao sensivel.
        if self._ativar.isChecked() and not self._ativo_inicial:
            resposta = QMessageBox.question(
                self, t("geral.confirmar"),
                t("tecladofisico.confirmar_1")
                + t("tecladofisico.confirmar_2"),
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
        self.accept()

    def escolhas(self) -> dict:
        return {"ativo": self._ativar.isChecked(), "aprender": self._aprender.isChecked()}
