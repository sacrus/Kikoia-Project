"""Dialogo "Criar teclado com IA": descrever, pre-visualizar e so depois guardar."""

from __future__ import annotations

from teclado.core.idiomas import t
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teclado.core.ia import (
    MODELO_POR_OMISSAO,
    ConfigIA,
    ClienteOpenAI,
    IAErro,
    gerar_pacote,
)

EXEMPLO = "Um teclado com as vogais do alfabeto português, em letras grandes."


class DialogoIATeclado(QDialog):
    """Pede um teclado a IA. Resultado: o modelo validado (dict), ou None se cancelado.

    Guardar o teclado e feito por quem chama (para aplicar a politica de supervisao).
    A chave e o modelo, se alterados, sao devolvidos em config_alterada().
    """

    def __init__(self, parent: QWidget | None, config: ConfigIA) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("ia.titulo"))
        self.resize(640, 560)
        self.estado_inicial = Qt.WindowState.WindowNoState
        self._config = config
        self._modelo: dict | None = None
        self._comandos: list[dict] = []

        self._chave = QLineEdit(config.chave)
        self._chave.setEchoMode(QLineEdit.EchoMode.Password)
        self._chave.setPlaceholderText(t("ia.chave_placeholder"))
        self._modelo_ia = QLineEdit(config.modelo or MODELO_POR_OMISSAO)

        formulario = QFormLayout()
        formulario.addRow(t("ia.chave"), self._chave)
        formulario.addRow(t("ia.modelo"), self._modelo_ia)

        self._descricao = QPlainTextEdit()
        self._descricao.setPlaceholderText(EXEMPLO)
        self._descricao.setMaximumHeight(90)

        botao_gerar = QPushButton(t("ia.gerar"))
        botao_gerar.clicked.connect(self._gerar)
        self._estado = QLabel(t("ia.descreva"))
        self._estado.setWordWrap(True)

        self._previa = QLabel()
        self._previa.setWordWrap(True)
        self._previa.setStyleSheet("font-size: 16px; padding: 8px; border: 1px solid #888;")
        self._previa.setMinimumHeight(160)
        self._previa.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._botao_usar = QPushButton(t("ia.usar"))
        self._botao_usar.setEnabled(False)
        self._botao_usar.clicked.connect(self._usar)
        self._caixa.addButton(self._botao_usar, QDialogButtonBox.ButtonRole.ActionRole)
        self._caixa.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.addLayout(formulario)
        raiz.addWidget(QLabel(t("ia.o_que")))
        raiz.addWidget(self._descricao)
        raiz.addWidget(botao_gerar)
        raiz.addWidget(self._estado)
        raiz.addWidget(QLabel(t("ia.previa")))
        raiz.addWidget(self._previa, 1)
        raiz.addWidget(self._caixa)

    # --- acoes -------------------------------------------------------------

    def _config_atual(self) -> ConfigIA:
        return ConfigIA(
            chave=self._chave.text(),
            modelo=self._modelo_ia.text().strip() or MODELO_POR_OMISSAO,
            endpoint=self._config.endpoint,
        )

    def config_alterada(self) -> ConfigIA:
        return self._config_atual()

    def _gerar(self) -> None:
        self._modelo = None
        self._comandos = []
        self._botao_usar.setEnabled(False)
        self._estado.setText(t("ia.a_pedir"))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            modelo, comandos = gerar_pacote(self._descricao.toPlainText(), ClienteOpenAI(self._config_atual()))
        except IAErro as erro:
            self._estado.setText(str(erro))
            self._previa.setText("")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._modelo = modelo
        self._comandos = comandos
        self._mostrar(modelo)
        self._estado.setText(t("ia.verifique"))
        self._botao_usar.setEnabled(True)

    def comandos(self) -> list[dict]:
        """Programas que o teclado propõe executar no PC (confirmados ao carregar em «Usar»)."""
        return list(self._comandos)

    def _mostrar(self, modelo: dict, comandos: list[dict] | None = None) -> None:
        linhas = ["   ".join(t["rotulo"] for t in linha) for linha in modelo["linhas"] if linha]
        total = sum(len(linha) for linha in modelo["linhas"])
        cabecalho = t("ia.cabecalho", nome=modelo["nome"], total=total)
        texto = cabecalho + "<br>".join(linhas)
        if comandos:
            texto += t("ia.executa")
            texto += "<br>".join(f"{c['rotulo']} → {c['comando']}" for c in comandos)
        self._previa.setText(texto)

    def _usar(self) -> None:
        if self._modelo is None:
            return
        self.accept()

    def resultado(self) -> dict | None:
        return self._modelo
