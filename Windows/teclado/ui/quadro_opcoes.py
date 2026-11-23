"""Botao «Abrir Quadro Interativo»: verifica, pergunta, transfere (se preciso) e abre o Quadro."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teclado.core import quadro
from teclado.core.idiomas import t
from teclado.ui.estilo_dialogos import aplicar_estilo_dialogo, criar_cabecalho_dialogo


class _Sinal(QObject):
    progresso = Signal(int, int)
    resultado = Signal(object)  # (tipo, dados): "versao", "ok", "erro"


def _mensagem(erro: object) -> str:
    chave = str(erro)
    return t(chave) if chave.startswith("quadro.") else chave


class DialogoQuadro(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("quadro.titulo"))
        self.resize(480, 200)
        self._ocupado = False
        self._versao: quadro.Versao | None = None

        self._estado = QLabel()
        self._estado.setWordWrap(True)
        self._barra = QProgressBar()
        self._barra.setVisible(False)
        self._botao = QPushButton(t("quadro.abrir"))
        self._botao.setProperty("papel", "primario")
        self._botao.clicked.connect(self._iniciar)
        fechar = QPushButton(t("geral.fechar"))
        fechar.clicked.connect(self.reject)

        botoes = QHBoxLayout()
        botoes.addWidget(self._botao)
        botoes.addStretch(1)
        botoes.addWidget(fechar)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        raiz.setSpacing(12)
        raiz.addLayout(criar_cabecalho_dialogo(t("quadro.titulo"), icone="quadro"))
        raiz.addWidget(self._estado)
        raiz.addWidget(self._barra)
        raiz.addLayout(botoes)
        aplicar_estilo_dialogo(self, cor_destaque="#E11D48")

        self._sinal = _Sinal()
        self._sinal.progresso.connect(self._mostrar_progresso, Qt.ConnectionType.QueuedConnection)
        self._sinal.resultado.connect(self._recebido, Qt.ConnectionType.QueuedConnection)

        if not quadro.suportado():
            self._estado.setText(t("quadro.so_windows"))
            self._botao.setEnabled(False)
        else:
            self._estado.setText(t("quadro.descricao"))

    # --- verificacao (segundo plano) ----------------------------------------------

    def _iniciar(self) -> None:
        if self._ocupado:
            return
        self._ocupado = True
        self._botao.setEnabled(False)
        self._estado.setText(t("quadro.a_verificar"))
        threading.Thread(target=self._trabalhar_verificacao, daemon=True, name="quadro-verificar").start()

    def _trabalhar_verificacao(self) -> None:
        try:
            versao = quadro.ultima_versao()
        except (quadro.QuadroErro, OSError) as erro:
            self._sinal.resultado.emit(("erro", _erro_de_rede(erro)))
            return
        self._sinal.resultado.emit(("versao", versao))

    # --- decisao (thread principal) -------------------------------------------------

    def _recebido(self, mensagem: object) -> None:
        tipo, dados = mensagem
        if tipo == "erro":
            self._falhou(_mensagem(dados))
        elif tipo == "versao":
            self._decidir(dados)
        elif tipo == "ok":
            self._abrir(dados)

    def _decidir(self, versao: quadro.Versao | None) -> None:
        if versao is None:
            self._falhou(t("quadro.sem_versao"))
            return
        self._versao = versao
        mb = round(versao.tamanho / 1_000_000, 1)
        instalada = quadro.versao_instalada()
        if instalada is not None and not quadro.precisa_atualizar(instalada, versao):
            exe = quadro.exe_instalado()
            if exe is not None:
                self._abrir(exe)
                return
        if instalada is None:
            pergunta = t("quadro.confirmar_descarga", mb=mb)
        else:
            pergunta = t("quadro.confirmar_atualizacao", versao=versao.tag, mb=mb)
        caixa = QMessageBox(self)
        caixa.setWindowTitle(t("quadro.titulo"))
        caixa.setText(pergunta)
        transferir = caixa.addButton(t("quadro.transferir"), QMessageBox.ButtonRole.AcceptRole)
        indicar = caixa.addButton(t("quadro.ja_tenho"), QMessageBox.ButtonRole.ActionRole)
        caixa.addButton(t("quadro.cancelar"), QMessageBox.ButtonRole.RejectRole)
        caixa.setDefaultButton(transferir)
        caixa.exec()
        escolha = caixa.clickedButton()
        if escolha is indicar:
            self._indicar_caminho()
            return
        if escolha is not transferir:
            self._repor()
            return
        self._barra.setVisible(True)
        self._barra.setRange(0, 100)
        self._barra.setValue(0)
        self._estado.setText(t("quadro.a_descarregar", percentagem=0))
        threading.Thread(target=self._trabalhar_descarga, daemon=True, name="quadro-descarregar").start()

    def _trabalhar_descarga(self) -> None:
        def progresso(recebido: int, total: int) -> None:
            self._sinal.progresso.emit(recebido, total)

        try:
            exe = quadro.descarregar(self._versao, progresso=progresso)
        except (quadro.QuadroErro, OSError) as erro:
            self._sinal.resultado.emit(("erro", _erro_de_rede(erro)))
            return
        self._sinal.resultado.emit(("ok", exe))

    def _indicar_caminho(self) -> None:
        """O Quadro ja esta instalado noutro sitio: o utilizador aponta o executavel e o teclado passa a usá-lo."""
        caminho, _ = QFileDialog.getOpenFileName(
            self, t("quadro.escolher_titulo"), "", f"{quadro.EXECUTAVEL} (KikoiaQuadro.exe);;{t('quadro.todos')} (*)"
        )
        if not caminho:
            self._repor()
            return
        try:
            exe = quadro.definir_instalacao(Path(caminho))
        except quadro.QuadroErro as erro:
            self._falhou(_mensagem(erro))
            return
        self._abrir(exe)

    def _mostrar_progresso(self, recebido: int, total: int) -> None:
        percentagem = int(recebido * 100 / total) if total else 0
        self._barra.setValue(percentagem)
        self._estado.setText(t("quadro.a_descarregar", percentagem=percentagem))

    def _abrir(self, exe: object) -> None:
        try:
            quadro.arrancar(exe)  # type: ignore[arg-type]
        except OSError as erro:
            self._falhou(t("quadro.abrir_falhou", erro=erro))
            return
        self.accept()

    def _falhou(self, mensagem: str) -> None:
        QMessageBox.warning(self, t("quadro.titulo"), mensagem)
        self._repor()

    def _repor(self) -> None:
        self._ocupado = False
        self._barra.setVisible(False)
        self._botao.setEnabled(quadro.suportado())
        self._estado.setText(t("quadro.descricao"))


def _erro_de_rede(erro: BaseException) -> str:
    if isinstance(erro, quadro.QuadroErro):
        return str(erro)
    return "quadro.sem_rede"
