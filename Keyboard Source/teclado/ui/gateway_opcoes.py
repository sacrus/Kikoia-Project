"""Diálogo «Aplicação Android»: configura a ligação remota, mostra o código e o estado."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from teclado.core.idiomas import t
from teclado.ui.estilo_dialogos import aplicar_estilo_dialogo, criar_cabecalho_dialogo

ROTULO_CODIGO_EXPIRADO = "—"


def formatar_codigo(codigo: str) -> str:
    return f"{codigo[:3]} {codigo[3:]}"


class DialogoGateway(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        controlador: Any,
        autorizar: Callable[[], bool],
        porta_atual: int,
        guardar_porta: Callable[[int], bool],
        ao_alterar_estado: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("telemovel.titulo"))
        self.resize(560, 500)
        self.estado_inicial = Qt.WindowState.WindowNoState
        self._controlador = controlador
        self._autorizar = autorizar
        self._guardar_porta = guardar_porta
        self._ao_alterar_estado = ao_alterar_estado

        # --- Cartão 1: Estado + Código de emparelhamento ---
        cartao_codigo = QFrame()
        cartao_codigo.setProperty("cartao", True)
        lay_cod = QVBoxLayout(cartao_codigo)
        lay_cod.setContentsMargins(16, 14, 16, 14)
        lay_cod.setSpacing(6)

        self._estado = QLabel()
        self._estado.setWordWrap(True)
        self._estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._estado.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")

        self._codigo = QLabel("—")
        self._codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._codigo.setStyleSheet(
            "font-size: 44px; font-weight: 800; letter-spacing: 8px; padding: 6px 0; background: transparent;"
        )

        self._tempo = QLabel()
        self._tempo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tempo.setProperty("secundario", True)
        self._tempo.setStyleSheet("font-size: 12px; background: transparent;")

        self._botao_ligar = QPushButton()
        self._botao_ligar.setProperty("papel", "primario")
        self._botao_ligar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._botao_ligar.clicked.connect(self._ligar_ou_desligar)

        self._botao_codigo = QPushButton(t("gateway.gerar_codigo"))
        self._botao_codigo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._botao_codigo.clicked.connect(self._novo_codigo)

        botoes_acao = QHBoxLayout()
        botoes_acao.setSpacing(10)
        botoes_acao.addStretch(1)
        botoes_acao.addWidget(self._botao_ligar)
        botoes_acao.addWidget(self._botao_codigo)
        botoes_acao.addStretch(1)

        lay_cod.addWidget(self._estado)
        lay_cod.addWidget(self._codigo)
        lay_cod.addWidget(self._tempo)
        lay_cod.addSpacing(4)
        lay_cod.addLayout(botoes_acao)

        # --- Cartão 2: Tipo de ligação (+ Porta só visível em Wi-Fi) ---
        cartao_lig = QFrame()
        cartao_lig.setProperty("cartao", True)
        lay_lig = QVBoxLayout(cartao_lig)
        lay_lig.setContentsMargins(16, 12, 16, 12)
        lay_lig.setSpacing(10)

        self._transporte = QComboBox()
        motivo_bt = controlador.bluetooth_disponivel()
        self._transporte.addItem(t("gateway.bluetooth_recomendado"), "bluetooth")
        self._transporte.addItem(t("gateway.wifi"), "wifi")
        if motivo_bt:
            self._transporte.setItemData(0, motivo_bt, Qt.ItemDataRole.ToolTipRole)
            self._transporte.model().item(0).setEnabled(False)
            self._transporte.setCurrentIndex(1)
        self._transporte.currentIndexChanged.connect(lambda _=0: self._atualizar())

        linha_transporte = QHBoxLayout()
        linha_transporte.setSpacing(10)
        lbl_lig = QLabel(t("gateway.ligacao"))
        lbl_lig.setStyleSheet("font-weight: 600; background: transparent;")
        linha_transporte.addWidget(lbl_lig)
        linha_transporte.addWidget(self._transporte, 1)
        lay_lig.addLayout(linha_transporte)

        # Bloco Wi-Fi (Porta + Guardar porta + aviso): oculto quando está em Bluetooth!
        self._bloco_wifi = QWidget()
        lay_wifi = QVBoxLayout(self._bloco_wifi)
        lay_wifi.setContentsMargins(0, 2, 0, 0)
        lay_wifi.setSpacing(6)

        self._porta = QSpinBox()
        self._porta.setRange(1024, 65535)
        self._porta.setValue(porta_atual)
        self._botao_porta = QPushButton(t("gateway.guardar_porta"))
        self._botao_porta.setCursor(Qt.CursorShape.PointingHandCursor)
        self._botao_porta.clicked.connect(self._guardar_porta_clicado)

        linha_porta = QHBoxLayout()
        linha_porta.setSpacing(8)
        lbl_porta = QLabel(t("gateway.porta"))
        lbl_porta.setStyleSheet("font-weight: 600; background: transparent;")
        linha_porta.addWidget(lbl_porta)
        linha_porta.addWidget(self._porta)
        linha_porta.addWidget(self._botao_porta)
        linha_porta.addStretch(1)

        self._aviso_wifi = QLabel(t("gateway.aviso_wifi"))
        self._aviso_wifi.setWordWrap(True)
        self._aviso_wifi.setProperty("secundario", True)
        self._aviso_wifi.setStyleSheet("font-size: 12px; background: transparent;")

        lay_wifi.addLayout(linha_porta)
        lay_wifi.addWidget(self._aviso_wifi)
        lay_lig.addWidget(self._bloco_wifi)

        # --- Cartão 3: Instruções claras para a Aplicação Android ---
        cartao_ajuda = QFrame()
        cartao_ajuda.setProperty("cartao", True)
        lay_ajuda = QVBoxLayout(cartao_ajuda)
        lay_ajuda.setContentsMargins(16, 12, 16, 12)
        lay_ajuda.setSpacing(4)

        ajuda = QLabel(
            t("gateway.ajuda_1")
            + t("gateway.ajuda_2")
            + t("gateway.ajuda_3")
        )
        ajuda.setWordWrap(True)
        ajuda.setProperty("secundario", True)
        ajuda.setStyleSheet("font-size: 12.5px; line-height: 1.4; background: transparent;")
        lay_ajuda.addWidget(ajuda)

        # --- Rodapé com Fechar ---
        fechar = QPushButton(t("geral.fechar"))
        fechar.setCursor(Qt.CursorShape.PointingHandCursor)
        fechar.clicked.connect(self.accept)
        rodape = QHBoxLayout()
        rodape.addStretch(1)
        rodape.addWidget(fechar)

        conteudo = QWidget()
        lay_conteudo = QVBoxLayout(conteudo)
        lay_conteudo.setContentsMargins(0, 0, 0, 0)
        lay_conteudo.setSpacing(12)
        lay_conteudo.addWidget(cartao_codigo)
        lay_conteudo.addWidget(cartao_lig)
        lay_conteudo.addWidget(cartao_ajuda)
        lay_conteudo.addStretch(1)

        scroll = QScrollArea()
        scroll.setProperty("sem_borda", True)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(conteudo)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(20, 16, 20, 16)
        raiz.setSpacing(12)
        raiz.addLayout(criar_cabecalho_dialogo(t("telemovel.titulo"), icone="telemovel"))
        raiz.addWidget(scroll, 1)
        raiz.addLayout(rodape)

        aplicar_estilo_dialogo(self, cor_destaque="#2563EB")

        ecra = self.screen() or QGuiApplication.primaryScreen()
        if ecra is not None:
            area = ecra.availableGeometry()
            larg = min(560, max(380, area.width() - 40))
            alt = min(580, max(360, area.height() - 60))
            self.resize(larg, alt)
        else:
            self.resize(560, 580)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._atualizar)
        self._timer.start(1000)
        self._atualizar()

    # --- acoes ---------------------------------------------------------------

    def _get_ativo(self) -> bool:
        """Obter status ativo do controlador, compatível com ambos os tipos."""
        controlador = self._controlador
        if hasattr(controlador, "estado") and callable(controlador.estado):
            try:
                e = controlador.estado()
                return e.get("ativo", False)
            except Exception:
                pass
        return getattr(controlador, "ativo", False)

    def _ligar_ou_desligar(self) -> None:
        ativo = self._get_ativo()
        if ativo:
            if hasattr(self._controlador, "desligar") and callable(self._controlador.desligar):
                self._controlador.desligar()
            if self._ao_alterar_estado is not None:
                self._ao_alterar_estado(False)
        else:
            if not self._autorizar():
                return
            if hasattr(self._controlador, "ligar") and callable(self._controlador.ligar):
                try:
                    self._controlador.ligar(self._porta.value(), self._transporte.currentData())
                except RuntimeError as erro:
                    QMessageBox.warning(self, t("telemovel.titulo"), str(erro))
                else:
                    if self._ao_alterar_estado is not None:
                        self._ao_alterar_estado(True)
        self._atualizar()

    def _novo_codigo(self) -> None:
        ativo = self._get_ativo()
        if not ativo or not self._autorizar():
            return
        if hasattr(self._controlador, "novo_codigo") and callable(self._controlador.novo_codigo):
            self._controlador.novo_codigo()
        self._atualizar()

    def _guardar_porta_clicado(self) -> None:
        if self._controlador.ativo:
            QMessageBox.information(self, t("telemovel.titulo"), t("gateway.desligue_primeiro"))
            return
        if not self._guardar_porta(self._porta.value()):
            QMessageBox.information(
                self, "Não guardado",
                "A alteração não foi aprovada. É preciso o código do adulto quando a supervisão está ativa.",
            )

    # --- estado ----------------------------------------------------------------

    def _obter_estado(self) -> dict[str, Any]:
        """Obter estado do controlador, compatível com ambos ControladorGateway e Aplicacao."""
        controlador = self._controlador
        if hasattr(controlador, "estado") and callable(controlador.estado):
            try:
                return controlador.estado()
            except Exception:
                pass
        ativo = getattr(controlador, "ativo", False)
        return {
            "ativo": ativo,
            "transporte": getattr(controlador, "_transporte", None) or "unknown",
            "porta": getattr(controlador, "porta", None),
            "codigo": getattr(controlador, "codigo", None),
            "estado_codigo": getattr(controlador, "codigo", None).estado if hasattr(getattr(controlador, "codigo", None), "estado") else None,
            "segundos": int(getattr(getattr(controlador, "codigo", None), "segundos_restantes", lambda: 0)()),
            "ligados": getattr(controlador, "dispositivos_ligados", 0) if hasattr(controlador, "dispositivos_ligados") else 0,
        }

    def _atualizar(self) -> None:
        e = self._obter_estado()
        wifi = self._transporte.currentData() == "wifi"
        self._bloco_wifi.setVisible(wifi)
        self._porta.setEnabled(wifi and not e["ativo"])
        self._botao_porta.setEnabled(wifi and not e["ativo"])
        self._transporte.setEnabled(not e["ativo"])
        if not e["ativo"]:
            self._estado.setText(t("gateway.desligado"))
            self._codigo.setText("—")
            self._tempo.setText("")
            self._botao_ligar.setText(t("gateway.ligar"))
            self._botao_codigo.setEnabled(False)
            return

        self._botao_ligar.setText(t("geral.desligar"))
        self._botao_codigo.setEnabled(True)
        if e.get("transporte") == "bluetooth":
            self._tempo.setToolTip(t("gateway.dica_bluetooth"))
        if e["ligados"] > 0:
            self._estado.setText(t("gateway.ligados", n=e["ligados"]))
        else:
            self._estado.setText(t("gateway.a_espera"))

        if e["estado_codigo"] == "ativo":
            self._codigo.setText(formatar_codigo(e["codigo"]))
            via = f"porta {e['porta']}" if e.get("porta") else t("gateway.via_bluetooth")
            self._tempo.setText(t("gateway.valido", segundos=e["segundos"], via=via))
        elif e["estado_codigo"] == "usado":
            self._codigo.setText(ROTULO_CODIGO_EXPIRADO)
            self._tempo.setText(t("gateway.usado"))
        else:
            self._codigo.setText(ROTULO_CODIGO_EXPIRADO)
            self._tempo.setText(t("gateway.expirado"))

    def closeEvent(self, evento) -> None:  # noqa: N802 (nome exigido pelo Qt)
        self._timer.stop()
        super().closeEvent(evento)
