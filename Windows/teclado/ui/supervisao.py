"""Dialogo de supervisao do adulto: ativar, alterar o ambito e o codigo, desativar."""

from __future__ import annotations

from teclado.core.idiomas import t
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teclado.core.seguranca import TAMANHO_MINIMO_PIN

def rotulos_ambito() -> dict[str, str]:
    return {
        "alterar_layout": t("sup.criar_alterar"),
        "alterar_tema": t("sup.mudar_tema"),
        "definicoes": t("sup.alterar_definicoes"),
    }

ACAO_ATIVAR = "ativar"
ACAO_ATUALIZAR = "atualizar"
ACAO_DESATIVAR = "desativar"


class DialogoSupervisao(QDialog):
    """Escolhe o que fica protegido pelo codigo do adulto.

    Nao valida o codigo atual: quem chama (Aplicacao) pede-o quando e preciso.
    resultado() devolve {"acao", "ambito", "pin"} ou None se cancelado.
    """

    def __init__(self, parent: QWidget | None, ativa: bool, ambito: list[str]) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("sup.titulo"))
        self._ativa = ativa
        self._resultado: dict | None = None

        titulo = QLabel(
            t("sup.ativa")
            if ativa else
            t("sup.desligada_1")
            + t("sup.desligada_2")
        )
        titulo.setWordWrap(True)

        self._checks: dict[str, QCheckBox] = {}
        caixa_ambito = QVBoxLayout()
        caixa_ambito.addWidget(QLabel(t("sup.protegido")))
        for chave, rotulo in rotulos_ambito().items():
            cb = QCheckBox(rotulo)
            cb.setChecked(chave in ambito)
            self._checks[chave] = cb
            caixa_ambito.addWidget(cb)

        self._pin1 = QLineEdit()
        self._pin2 = QLineEdit()
        for campo in (self._pin1, self._pin2):
            campo.setEchoMode(QLineEdit.EchoMode.Password)
            campo.setMaxLength(32)
        if ativa:
            self._pin1.setPlaceholderText(t("sup.novo_codigo"))
            self._pin2.setPlaceholderText(t("sup.repita_novo"))
        else:
            self._pin1.setPlaceholderText(t("sup.codigo_minimo", n=TAMANHO_MINIMO_PIN))
            self._pin2.setPlaceholderText(t("sup.repita"))

        caixa_pin = QVBoxLayout()
        caixa_pin.addWidget(QLabel(t("sup.codigo_rotulo")))
        caixa_pin.addWidget(self._pin1)
        caixa_pin.addWidget(self._pin2)

        botoes = QHBoxLayout()
        if ativa:
            botao_guardar = QPushButton(t("sup.guardar"))
            botao_guardar.clicked.connect(lambda _=False: self._submeter(ACAO_ATUALIZAR))
            botao_desativar = QPushButton(t("sup.desativar"))
            botao_desativar.clicked.connect(lambda _=False: self._submeter(ACAO_DESATIVAR))
            botoes.addWidget(botao_desativar)
            botoes.addStretch(1)
            botoes.addWidget(botao_guardar)
        else:
            botao_ativar = QPushButton(t("sup.ativar"))
            botao_ativar.clicked.connect(lambda _=False: self._submeter(ACAO_ATIVAR))
            botoes.addStretch(1)
            botoes.addWidget(botao_ativar)
        botao_fechar = QPushButton("Fechar")
        botao_fechar.clicked.connect(self.reject)
        botoes.addWidget(botao_fechar)

        raiz = QVBoxLayout(self)
        raiz.addWidget(titulo)
        raiz.addLayout(caixa_ambito)
        raiz.addLayout(caixa_pin)
        raiz.addLayout(botoes)

    def _ambito_escolhido(self) -> list[str]:
        return [chave for chave, cb in self._checks.items() if cb.isChecked()]

    def _submeter(self, acao: str) -> None:
        pin = self._pin1.text()
        if acao == ACAO_DESATIVAR:
            resposta = QMessageBox.question(
                self, t("sup.desativar"),
                t("sup.desativar_pergunta"),
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
        else:
            if acao == ACAO_ATIVAR or pin:
                if len(pin) < TAMANHO_MINIMO_PIN:
                    QMessageBox.warning(
                        self, t("sup.codigo_curto"),
                        t("sup.codigo_pelo_menos", n=TAMANHO_MINIMO_PIN),
                    )
                    return
                if pin != self._pin2.text():
                    QMessageBox.warning(self, t("sup.codigos_diferentes"), t("sup.nao_coincidem"))
                    return
        self._resultado = {
            "acao": acao,
            "ambito": self._ambito_escolhido(),
            "pin": pin or None,
        }
        self.accept()

    def resultado(self) -> dict | None:
        return self._resultado
