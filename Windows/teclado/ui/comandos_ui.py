"""Gestao das teclas personalizadas (programas e comandos do PC)."""

from __future__ import annotations

from teclado.core.idiomas import t
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teclado.core.comandos import MAX_COMANDO, MAX_ROTULO, Comando, validar
from teclado.ui.dialogos import ACEITE, executar_dialogo

def texto_ajuda() -> str:
    return (
        t("cmd.ajuda_1")
        + t("cmd.ajuda_2")
        + t("cmd.ajuda_3")
        + t("cmd.ajuda_4")
    )


class DialogoComando(QDialog):
    def __init__(self, parent: QWidget | None, inicial: Comando | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("cmd.titulo_tecla"))
        self._rotulo = QLineEdit(inicial.rotulo if inicial else "")
        self._rotulo.setMaxLength(MAX_ROTULO)
        self._rotulo.setPlaceholderText(t("cmd.exemplo"))
        self._comando = QLineEdit(inicial.comando if inicial else "")
        self._comando.setMaxLength(MAX_COMANDO)

        procurar = QPushButton(t("cmd.escolher"))
        procurar.clicked.connect(self._procurar)
        ajuda = QLabel(texto_ajuda())
        ajuda.setWordWrap(True)

        formulario = QFormLayout()
        formulario.addRow(t("cmd.nome_tecla"), self._rotulo)
        formulario.addRow(t("cmd.programa_comando"), self._comando)

        caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        caixa.accepted.connect(self._confirmar)
        caixa.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.addLayout(formulario)
        raiz.addWidget(procurar)
        raiz.addWidget(ajuda)
        raiz.addWidget(caixa)

    def _procurar(self) -> None:
        ficheiro, _ = QFileDialog.getOpenFileName(
            self, t("cmd.titulo_ficheiro"), "", t("cmd.todos_ficheiros"), "",
            QFileDialog.Option.DontUseNativeDialog,
        )
        if ficheiro:
            self._comando.setText(f'"{ficheiro}"' if " " in ficheiro else ficheiro)

    def _confirmar(self) -> None:
        try:
            validar(self._rotulo.text(), self._comando.text())
        except ValueError as erro:
            QMessageBox.warning(self, t("geral.tecla_invalida"), str(erro))
            return
        self.accept()

    def resultado(self) -> tuple[str, str]:
        return validar(self._rotulo.text(), self._comando.text())


class DialogoComandos(QDialog):
    """Lista as teclas personalizadas e permite criar, alterar e apagar.

    guardar(id|None, rotulo, comando) -> Comando | None  (None = nao aprovado)
    apagar(id) -> bool
    """

    def __init__(
        self,
        parent: QWidget | None,
        comandos: dict[str, Comando],
        guardar: Callable[[str | None, str, str], Comando | None],
        apagar: Callable[[str], bool],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("cmd.titulo_lista"))
        self.resize(620, 420)
        self._comandos = comandos
        self._guardar = guardar
        self._apagar = apagar

        self._lista = QListWidget()
        explicacao = QLabel(
            t("cmd.explica_1")
            + t("cmd.explica_2")
        )
        explicacao.setWordWrap(True)

        novo = QPushButton(t("cmd.nova"))
        novo.clicked.connect(self._novo)
        editar = QPushButton(t("cmd.alterar"))
        editar.clicked.connect(self._editar)
        apagar_btn = QPushButton(t("geral.apagar"))
        apagar_btn.clicked.connect(self._apagar_selecionado)
        botoes = QHBoxLayout()
        for botao in (novo, editar, apagar_btn):
            botoes.addWidget(botao)
        botoes.addStretch(1)

        fechar = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        fechar.rejected.connect(self.reject)
        fechar.accepted.connect(self.accept)

        raiz = QVBoxLayout(self)
        raiz.addWidget(explicacao)
        raiz.addWidget(self._lista, 1)
        raiz.addLayout(botoes)
        raiz.addWidget(fechar)
        self._recarregar()

    def _recarregar(self) -> None:
        self._lista.clear()
        for c in self._comandos.values():
            item = QListWidgetItem(f"{c.rotulo}   →   {c.comando}")
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self._lista.addItem(item)

    def _selecionado(self) -> Comando | None:
        item = self._lista.currentItem()
        if item is None:
            return None
        return self._comandos.get(item.data(Qt.ItemDataRole.UserRole))

    def _nao_aprovado(self) -> None:
        QMessageBox.information(
            self, t("geral.nao_guardado"),
            t("geral.nao_aprovado"),
        )

    def _novo(self) -> None:
        dialogo = DialogoComando(self)
        if executar_dialogo(dialogo) != ACEITE:
            return
        rotulo, comando = dialogo.resultado()
        if self._guardar(None, rotulo, comando) is None:
            self._nao_aprovado()
        self._recarregar()

    def _editar(self) -> None:
        atual = self._selecionado()
        if atual is None:
            return
        dialogo = DialogoComando(self, atual)
        if executar_dialogo(dialogo) != ACEITE:
            return
        rotulo, comando = dialogo.resultado()
        if self._guardar(atual.id, rotulo, comando) is None:
            self._nao_aprovado()
        self._recarregar()

    def _apagar_selecionado(self) -> None:
        atual = self._selecionado()
        if atual is None:
            return
        resposta = QMessageBox.question(self, t("geral.apagar"), t("cmd.apagar_pergunta", rotulo=atual.rotulo))
        if resposta != QMessageBox.StandardButton.Yes:
            return
        if not self._apagar(atual.id):
            self._nao_aprovado()
        self._recarregar()
