"""Dialogo "Telemovel": liga o gateway, mostra o codigo de emparelhamento e o estado."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from teclado.core.idiomas import t

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
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("telemovel.titulo"))
        self.resize(520, 420)
        self.estado_inicial = Qt.WindowState.WindowNoState
        self._controlador = controlador
        self._autorizar = autorizar
        self._guardar_porta = guardar_porta

        # Ler valores atuais do controlador para inicializar o UI

        self._estado = QLabel()
        self._estado.setWordWrap(True)
        self._estado.setStyleSheet("font-size: 16px; font-weight: bold;")

        self._codigo = QLabel("—")
        self._codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._codigo.setStyleSheet("font-size: 46px; font-weight: bold; letter-spacing: 6px; padding: 8px;")

        self._tempo = QLabel()
        self._tempo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._botao_ligar = QPushButton()
        self._botao_ligar.clicked.connect(self._ligar_ou_desligar)
        self._botao_codigo = QPushButton(t("gateway.gerar_codigo"))
        self._botao_codigo.clicked.connect(self._novo_codigo)

        self._transporte = QComboBox()
        self._transporte.addItem(t("gateway.wifi"), "wifi")
        motivo_bt = controlador.bluetooth_disponivel()
        self._transporte.addItem(t("gateway.bluetooth"), "bluetooth")
        if motivo_bt:
            self._transporte.setItemData(1, motivo_bt, Qt.ItemDataRole.ToolTipRole)
            self._transporte.model().item(1).setEnabled(False)
        self._transporte.currentIndexChanged.connect(lambda _=0: self._atualizar())

        self._porta = QSpinBox()
        self._porta.setRange(1024, 65535)
        self._porta.setValue(porta_atual)
        botao_porta = QPushButton(t("gateway.guardar_porta"))
        botao_porta.clicked.connect(self._guardar_porta_clicado)
        linha_porta = QHBoxLayout()
        linha_porta.addWidget(QLabel(t("gateway.ligacao")))
        linha_porta.addWidget(self._transporte)
        linha_porta.addWidget(QLabel(t("gateway.porta")))
        linha_porta.addWidget(self._porta)
        linha_porta.addWidget(botao_porta)
        linha_porta.addStretch(1)

        ajuda = QLabel(
            t("gateway.ajuda_1")
            + t("gateway.ajuda_2")
            + t("gateway.ajuda_3")
        )
        ajuda.setWordWrap(True)

        botoes = QHBoxLayout()
        botoes.addWidget(self._botao_ligar)
        botoes.addWidget(self._botao_codigo)
        fechar = QPushButton(t("geral.fechar"))
        fechar.clicked.connect(self.accept)
        botoes.addWidget(fechar)

        raiz = QVBoxLayout(self)
        raiz.addWidget(self._estado)
        raiz.addWidget(self._codigo)
        raiz.addWidget(self._tempo)
        raiz.addLayout(botoes)
        raiz.addLayout(linha_porta)
        raiz.addWidget(ajuda)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._atualizar)
        self._timer.start(1000)
        self._atualizar()

    # --- acoes ---------------------------------------------------------------

    def _get_ativo(self) -> bool:
        """Obter status ativo do controlador, compatível com ambos os tipos."""
        controlador = self._controlador
        if hasattr(controlador, "estado") and callable(controlador.estado):
            # ControladorGateway: estado() ja cobre o ativo
            try:
                e = controlador.estado()
                return e.get("ativo", False)
            except Exception:
                pass
        # Fallback para Aplicacao
        return getattr(controlador, "ativo", False)

    def _ligar_ou_desligar(self) -> None:
        ativo = self._get_ativo()
        if ativo:
            # Se for ControladorGateway, chamar desligar
            if hasattr(self._controlador, "desligar") and callable(self._controlador.desligar):
                self._controlador.desligar()
        else:
            if not self._autorizar():
                return
            # Se for ControladorGateway, chamar ligar
            if hasattr(self._controlador, "ligar") and callable(self._controlador.ligar):
                try:
                    self._controlador.ligar(self._porta.value(), self._transporte.currentData())
                except RuntimeError as erro:
                    QMessageBox.warning(self, t("telemovel.titulo"), str(erro))
            # Se for Aplicacao, nao tem ligao gateway; apenas informar
        self._atualizar()

    def _novo_codigo(self) -> None:
        ativo = self._get_ativo()
        if not ativo or not self._autorizar():
            return
        # Se for ControladorGateway, chamar novo_codigo
        if hasattr(self._controlador, "novo_codigo") and callable(self._controlador.novo_codigo):
            self._controlador.novo_codigo()
        # Se for Aplicacao, nao tem novo_codigo gateway; informar
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
        # Try ControladorGateway.estado() first
        if hasattr(controlador, "estado") and callable(controlador.estado):
            try:
                return controlador.estado()
            except Exception:
                pass
        # Fallback para Aplicacao: usar ativo property e valores padrões
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
        self._porta.setEnabled(wifi and not e["ativo"])
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