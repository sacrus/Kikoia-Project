"""Dialogo de atualizacoes: estado do teclado e das dependencias. Nunca instala sem confirmacao."""

from __future__ import annotations

import logging
import threading
import webbrowser

from PySide6.QtCore import QObject, QProcess, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from teclado.core import atualizacao
from teclado.core.atualizacao import Atualizacao, Dependencia
from teclado.core.idiomas import t


class _Resultado(QObject):
    concluido = Signal(object)


class DialogoAtualizacoes(QDialog):
    """Mostra as versoes e deixa atualizar. Verificar corre em segundo plano (pode demorar)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("atualizacoes.titulo"))
        self.resize(560, 420)
        self._atualizacao: Atualizacao | None = None
        self._pacotes_desatualizados: list[str] = []
        self._resultado = _Resultado()
        self._resultado.concluido.connect(self._mostrar_verificacao, Qt.ConnectionType.QueuedConnection)
        self._processo: QProcess | None = None

        self._estado_teclado = QLabel()
        self._estado_teclado.setWordWrap(True)
        self._abrir = QPushButton(t("atualizacoes.abrir_pagina"))
        self._abrir.setVisible(False)
        self._abrir.clicked.connect(self._abrir_pagina)

        self._tabela = QTableWidget(0, 3)
        self._tabela.setHorizontalHeaderLabels([
            t("atualizacoes.pacote"), t("atualizacoes.instalada"), t("atualizacoes.recente"),
        ])
        self._tabela.verticalHeader().setVisible(False)
        self._tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._verificar = QPushButton(t("atualizacoes.verificar"))
        self._verificar.clicked.connect(self._iniciar_verificacao)
        self._atualizar_deps = QPushButton(t("atualizacoes.atualizar_deps"))
        self._atualizar_deps.setEnabled(False)
        self._atualizar_deps.clicked.connect(self._confirmar_atualizacao)
        self._estado = QLabel("")

        botoes = QHBoxLayout()
        botoes.addWidget(self._verificar)
        botoes.addWidget(self._atualizar_deps)
        botoes.addStretch(1)

        raiz = QVBoxLayout(self)
        raiz.addWidget(QLabel(f"<b>{t('atualizacoes.teclado')}</b>"))
        raiz.addWidget(self._estado_teclado)
        raiz.addWidget(self._abrir)
        # No executavel nao ha dependencias a atualizar: so se mostra a versao do teclado.
        self._dependencias = QLabel(f"<b>{t('atualizacoes.dependencias')}</b>")
        raiz.addWidget(self._dependencias)
        raiz.addWidget(self._tabela, 1)
        raiz.addLayout(botoes)
        raiz.addWidget(self._estado)
        if atualizacao.empacotado():
            for widget in (self._dependencias, self._tabela, self._atualizar_deps):
                widget.setVisible(False)

        self._mostrar_teclado_atual()

    # --- teclado -----------------------------------------------------------------

    def _mostrar_teclado_atual(self, nova: Atualizacao | None = None, consultado: bool = False) -> None:
        if not atualizacao.teclado_configurado():
            self._estado_teclado.setText(
                f"{t('atualizacoes.versao_atual', versao=atualizacao.VERSAO)}<br>"
                f"{t('atualizacoes.nao_configurado')}"
            )
            return
        if nova is not None:
            self._atualizacao = nova
            self._estado_teclado.setText(
                f"{t('atualizacoes.versao_atual', versao=atualizacao.VERSAO)}<br>"
                f"<b>{t('atualizacoes.nova', versao=nova.versao)}</b>"
            )
            self._abrir.setVisible(bool(nova.pagina))
            return
        texto = t("atualizacoes.versao_atual", versao=atualizacao.VERSAO)
        if consultado:
            texto += f"<br>{t('atualizacoes.ao_dia')}"
        self._estado_teclado.setText(texto)

    def _abrir_pagina(self) -> None:
        if self._atualizacao is not None and self._atualizacao.pagina:
            webbrowser.open(self._atualizacao.pagina)

    # --- verificacao (segundo plano) -----------------------------------------------

    def _iniciar_verificacao(self) -> None:
        self._verificar.setEnabled(False)
        self._estado.setText(t("atualizacoes.a_verificar"))

        def trabalhar() -> None:
            try:
                nova = atualizacao.verificar_teclado() if atualizacao.teclado_configurado() else None
                dependencias = atualizacao.verificar_dependencias()
                erro = None
            except (OSError, ValueError):
                nova, dependencias, erro = None, [], t("atualizacoes.sem_rede")
            self._resultado.concluido.emit((nova, dependencias, erro))

        threading.Thread(target=trabalhar, daemon=True, name="verificar-atualizacoes").start()

    def _mostrar_verificacao(self, resultado: tuple) -> None:
        nova, dependencias, erro = resultado
        self._verificar.setEnabled(True)
        self._mostrar_teclado_atual(nova, consultado=erro is None and nova is None)
        self._preencher_tabela(dependencias)
        self._pacotes_desatualizados = [d.nome for d in dependencias if d.desatualizada]
        self._atualizar_deps.setEnabled(bool(self._pacotes_desatualizados))
        self._estado.setText(erro or "")

    def _preencher_tabela(self, dependencias: list[Dependencia]) -> None:
        self._tabela.setRowCount(len(dependencias))
        for linha, dep in enumerate(dependencias):
            valores = [dep.nome, dep.instalada or "—", dep.mais_recente or "—"]
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if coluna == 2 and dep.desatualizada:
                    item.setForeground(Qt.GlobalColor.darkYellow)
                self._tabela.setItem(linha, coluna, item)
        self._tabela.resizeColumnsToContents()

    # --- atualizacao das dependencias (so com confirmacao) ----------------------------

    def _confirmar_atualizacao(self) -> None:
        if not self._pacotes_desatualizados or self._processo is not None:
            return
        resposta = QMessageBox.question(
            self, t("atualizacoes.titulo"),
            t("atualizacoes.confirmar", quantidade=len(self._pacotes_desatualizados)),
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        self._atualizar_deps.setEnabled(False)
        self._estado.setText(t("atualizacoes.a_atualizar"))
        self._processo = QProcess(self)
        self._processo.finished.connect(self._atualizacao_terminada)
        args = atualizacao.comando_atualizar(self._pacotes_desatualizados)
        self._processo.start(args[0], args[1:])

    def _atualizacao_terminada(self, codigo: int, _estado) -> None:
        processo, self._processo = self._processo, None
        if codigo == 0:
            self._estado.setText(t("atualizacoes.atualizado"))
            self._iniciar_verificacao()
            return
        logging.error("Atualizacao das dependencias falhou: %s", bytes(processo.readAllStandardError()).decode(errors="replace"))
        self._estado.setText(t("atualizacoes.falhou"))
        self._atualizar_deps.setEnabled(True)
