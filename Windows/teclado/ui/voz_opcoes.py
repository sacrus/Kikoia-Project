"""Opcoes de voz: o que e lido em voz alta, com que voz, e o modelo de reconhecimento (ditar)."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teclado.core import modelos, voz_piper
from teclado.core.idiomas import t


class _Sinal(QObject):
    progresso = Signal(int, int)
    concluido = Signal(object)  # None se instalado; senao, a mensagem (ou CANCELADA)


CANCELADA = "cancelada"


class DialogoOpcoesVoz(QDialog):
    """Leitura em voz alta e escolha da voz. Com pasta_dados, tambem gere o modelo de ditar.

    O modelo so e descarregado quando o utilizador carrega no botao (com confirmacao).
    """

    def __init__(
        self,
        parent: QWidget | None,
        preferencias: dict,
        vozes: list[tuple[str, str]],
        pasta_dados: Path | None = None,
        idioma: str = "pt-PT",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("voz.titulo"))
        self._ler_palavra = QCheckBox(t("voz.ler_palavra"))
        self._ler_frase = QCheckBox(t("voz.ler_frase"))
        self._ler_sugestao = QCheckBox(t("voz.ler_sugestao"))
        self._ler_palavra.setChecked(bool(preferencias.get("ler_palavra")))
        self._ler_frase.setChecked(bool(preferencias.get("ler_frase")))
        self._ler_sugestao.setChecked(bool(preferencias.get("ler_sugestao")))

        self._voz = QComboBox()
        self._ids: list[str | None] = [None]
        self._voz.addItem(t("voz.predefinida"))
        for id_, nome in vozes:
            self._voz.addItem(nome)
            self._ids.append(id_)
        if preferencias.get("voz_id") in self._ids:
            self._voz.setCurrentIndex(self._ids.index(preferencias.get("voz_id")))

        aviso = QLabel()
        aviso.setWordWrap(True)
        if not vozes:
            aviso.setText(
                t("voz.sem_vozes_1")
                + t("voz.sem_vozes_2")
            )

        caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        caixa.accepted.connect(self.accept)
        caixa.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.addWidget(QLabel(t("voz.o_que_e_lido")))
        raiz.addWidget(self._ler_palavra)
        raiz.addWidget(self._ler_frase)
        raiz.addWidget(self._ler_sugestao)
        raiz.addWidget(QLabel(t("voz.voz")))
        raiz.addWidget(self._voz)
        raiz.addWidget(aviso)

        self._pasta_dados = pasta_dados
        self._idioma = idioma
        self._a_descarregar = False
        self._cancelar = False
        self._sinal = _Sinal()
        self._sinal.progresso.connect(self._mostrar_progresso, Qt.ConnectionType.QueuedConnection)
        self._sinal.concluido.connect(self._descarga_concluida, Qt.ConnectionType.QueuedConnection)
        if pasta_dados is not None:
            raiz.addWidget(QLabel(f"<b>{t('voz.secao')}</b>"))
            self._estado_modelo = QLabel()
            self._estado_modelo.setWordWrap(True)
            self._botao_descarregar = QPushButton()
            self._botao_descarregar.clicked.connect(self._descarregar_ou_cancelar)
            self._botao_remover = QPushButton(t("voz.remover"))
            self._botao_remover.clicked.connect(self._remover)
            raiz.addWidget(self._estado_modelo)
            raiz.addWidget(self._botao_descarregar)
            raiz.addWidget(self._botao_remover)
            self._atualizar_modelo()

        if pasta_dados is not None and sys.platform.startswith("linux"):
            # No Linux, a voz de Falar (Piper) tambem e descarregada a pedido.
            raiz.addWidget(QLabel(f"<b>{t('voz.piper_secao')}</b>"))
            self._estado_piper = QLabel()
            self._estado_piper.setWordWrap(True)
            self._botao_piper = QPushButton()
            self._botao_piper.clicked.connect(self._piper_descarregar_ou_cancelar)
            self._botao_piper_remover = QPushButton(t("voz.remover"))
            self._botao_piper_remover.clicked.connect(self._piper_remover)
            raiz.addWidget(self._estado_piper)
            raiz.addWidget(self._botao_piper)
            raiz.addWidget(self._botao_piper_remover)
            self._a_descarregar_piper = False
            self._cancelar_piper = False
            self._sinal_piper = _Sinal()
            self._sinal_piper.progresso.connect(self._piper_progresso, Qt.ConnectionType.QueuedConnection)
            self._sinal_piper.concluido.connect(self._piper_concluido, Qt.ConnectionType.QueuedConnection)
            self._atualizar_piper()

        raiz.addWidget(caixa)

    def escolhas(self) -> dict:
        return {
            "ler_palavra": self._ler_palavra.isChecked(),
            "ler_frase": self._ler_frase.isChecked(),
            "ler_sugestao": self._ler_sugestao.isChecked(),
            "voz_id": self._ids[self._voz.currentIndex()],
        }

    # --- modelo de ditar ----------------------------------------------------------

    def _modelo(self) -> modelos.ModeloVoz | None:
        return modelos.modelo_do_idioma(self._idioma)

    def _atualizar_modelo(self) -> None:
        modelo = self._modelo()
        if modelo is None:
            self._estado_modelo.setText(t("voz.sem_modelo_idioma"))
            self._botao_descarregar.setEnabled(False)
            self._botao_remover.setEnabled(False)
            return
        instalado = modelos.instalado(self._pasta_dados, self._idioma) is not None
        self._estado_modelo.setText(t("voz.modelo_instalado") if instalado else t("voz.modelo_nao_instalado"))
        self._botao_descarregar.setText(t("voz.descarregar", mb=modelo.tamanho_mb))
        self._botao_descarregar.setEnabled(not instalado and not self._a_descarregar)
        self._botao_remover.setEnabled(instalado and not self._a_descarregar)

    def _descarregar_ou_cancelar(self) -> None:
        if self._a_descarregar:
            self._cancelar = True
            return
        modelo = self._modelo()
        if modelo is None:
            return
        resposta = QMessageBox.question(
            self, t("voz.titulo"), t("voz.confirmar_descarga", mb=modelo.tamanho_mb),
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        self._a_descarregar = True
        self._cancelar = False
        self._botao_descarregar.setText(t("voz.cancelar"))
        self._botao_remover.setEnabled(False)
        self._estado_modelo.setText(t("voz.a_descarregar", percentagem=0))
        threading.Thread(target=self._trabalhar_descarga, daemon=True, name="modelo-voz").start()

    def _trabalhar_descarga(self) -> None:
        def progresso(recebido: int, total: int) -> None:
            self._sinal.progresso.emit(recebido, total)

        try:
            modelos.descarregar(
                self._pasta_dados, self._idioma,
                progresso=progresso, cancelar=lambda: self._cancelar,
            )
            self._sinal.concluido.emit(None)
        except modelos.DescargaCancelada:
            self._sinal.concluido.emit(CANCELADA)
        except modelos.ModeloErro as erro:
            self._sinal.concluido.emit(str(erro))

    def _mostrar_progresso(self, recebido: int, total: int) -> None:
        percentagem = int(recebido * 100 / total) if total else 0
        self._estado_modelo.setText(t("voz.a_descarregar", percentagem=percentagem))

    def _descarga_concluida(self, resultado: object) -> None:
        self._a_descarregar = False
        self._cancelar = False
        if resultado is None:
            self._estado_modelo.setText(t("voz.modelo_instalado_ok"))
        elif resultado != CANCELADA:
            QMessageBox.warning(self, t("voz.titulo"), t("voz.descarga_falhou", erro=resultado))
        self._atualizar_modelo()

    def _remover(self) -> None:
        modelos.remover(self._pasta_dados, self._idioma)
        self._atualizar_modelo()

    # --- voz de Falar (Piper, Linux) -----------------------------------------------

    def _voz_piper(self):
        """Voz de Falar da lingua deste dialogo (None se a lingua nao tiver voz)."""
        return voz_piper.voz_do_idioma(self._idioma)

    def _atualizar_piper(self) -> None:
        voz = self._voz_piper()
        if voz is None:
            self._estado_piper.setText(t("voz.piper_sem_idioma"))
            self._botao_piper.setEnabled(False)
            self._botao_piper_remover.setEnabled(False)
            return
        instalada = voz_piper.instalada(self._pasta_dados, self._idioma)
        self._estado_piper.setText(t("voz.piper_instalada") if instalada else t("voz.piper_nao_instalada"))
        self._botao_piper.setText(t("voz.piper_descarregar", mb=voz.tamanho_mb))
        self._botao_piper.setEnabled(not instalada and not self._a_descarregar_piper)
        self._botao_piper_remover.setEnabled(instalada and not self._a_descarregar_piper)

    def _piper_descarregar_ou_cancelar(self) -> None:
        if self._a_descarregar_piper:
            self._cancelar_piper = True
            return
        resposta = QMessageBox.question(
            self, t("voz.titulo"), t("voz.piper_confirmar", mb=self._voz_piper().tamanho_mb),
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        self._a_descarregar_piper = True
        self._cancelar_piper = False
        self._botao_piper.setText(t("voz.cancelar"))
        self._botao_piper_remover.setEnabled(False)
        self._estado_piper.setText(t("voz.a_descarregar", percentagem=0))
        threading.Thread(target=self._piper_trabalhar, daemon=True, name="voz-piper").start()

    def _piper_trabalhar(self) -> None:
        def progresso(recebido: int, total: int) -> None:
            self._sinal_piper.progresso.emit(recebido, total)

        try:
            voz_piper.descarregar(
                self._pasta_dados, self._idioma, progresso=progresso, cancelar=lambda: self._cancelar_piper,
            )
            self._sinal_piper.concluido.emit(None)
        except modelos.DescargaCancelada:
            self._sinal_piper.concluido.emit(CANCELADA)
        except modelos.ModeloErro as erro:
            self._sinal_piper.concluido.emit(str(erro))

    def _piper_progresso(self, recebido: int, total: int) -> None:
        percentagem = int(recebido * 100 / total) if total else 0
        self._estado_piper.setText(t("voz.a_descarregar", percentagem=percentagem))

    def _piper_concluido(self, resultado: object) -> None:
        self._a_descarregar_piper = False
        self._cancelar_piper = False
        if resultado is None:
            # A voz passa a estar na lista, selecionada. Ativa-se com OK.
            voz = self._voz_piper()
            if voz.id not in self._ids:
                self._voz.addItem(voz.nome)
                self._ids.append(voz.id)
            self._voz.setCurrentIndex(self._ids.index(voz.id))
            self._estado_piper.setText(t("voz.piper_ativar"))
        elif resultado != CANCELADA:
            QMessageBox.warning(self, t("voz.titulo"), t("voz.descarga_falhou", erro=resultado))
        self._atualizar_piper()

    def _piper_remover(self) -> None:
        voz = self._voz_piper()
        voz_piper.remover(self._pasta_dados, self._idioma)
        if voz is not None and voz.id in self._ids:
            indice = self._ids.index(voz.id)
            self._voz.removeItem(indice)
            self._ids.pop(indice)
        self._atualizar_piper()

    def reject(self) -> None:  # fechar a meio de uma descarga cancela-a
        if self._a_descarregar:
            self._cancelar = True
        if getattr(self, "_a_descarregar_piper", False):
            self._cancelar_piper = True
        super().reject()
