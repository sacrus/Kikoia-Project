"""Definicoes do touchpad: o que cada botao faz (clique rapido, duplo, com 2 ou 3 dedos, manter)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from teclado.core.idiomas import t
from teclado.core.toque import BOTOES, LIMITES, OPCOES, validar_preferencias
from teclado.ui.estilo_dialogos import aplicar_estilo_dialogo, criar_cabecalho_dialogo


class DialogoToque(QDialog):
    def __init__(self, parent: QWidget | None, atual: dict) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("toque.titulo"))
        self._combos = {}
        formulario = QFormLayout()
        for botao in BOTOES:
            combo = QComboBox()
            for opcao in OPCOES:
                combo.addItem(t(f"toque.op_{opcao}"), opcao)
            combo.setCurrentIndex(combo.findData(atual[botao]))
            self._combos[botao] = combo
            formulario.addRow(t(f"toque.{botao}"), combo)

        self._area = QCheckBox(t("toque.clique_area"))
        self._area.setChecked(bool(atual.get("clique_por_area", True)))
        formulario.addRow(self._area)

        self._deslizadores: dict[str, QSlider] = {}
        self._rotulos: dict[str, QLabel] = {}
        for chave in ("janela_duplo_ms", "tempo_manter_ms", "sensibilidade"):
            minimo, maximo = LIMITES[chave]
            deslizador = QSlider(Qt.Orientation.Horizontal)
            deslizador.setRange(minimo, maximo)
            deslizador.setValue(atual[chave])
            deslizador.setSingleStep(10 if chave == "sensibilidade" else 100)
            deslizador.setPageStep(50 if chave == "sensibilidade" else 500)
            rotulo = QLabel()
            deslizador.valueChanged.connect(lambda _=0, c=chave: self._atualizar_rotulo(c))
            self._deslizadores[chave] = deslizador
            self._rotulos[chave] = rotulo
            self._atualizar_rotulo(chave)
            formulario.addRow(rotulo, deslizador)

        caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        caixa.accepted.connect(self._confirmar)
        caixa.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        raiz.setSpacing(12)
        raiz.addLayout(criar_cabecalho_dialogo(t("toque.titulo"), icone="touchpad"))
        raiz.addLayout(formulario)
        raiz.addWidget(caixa)
        aplicar_estilo_dialogo(self, cor_destaque="#0284C7")

    def _atualizar_rotulo(self, chave: str) -> None:
        valor = self._deslizadores[chave].value()
        if chave == "sensibilidade":
            self._rotulos[chave].setText(t("toque.sensibilidade", valor=valor))
        elif chave == "janela_duplo_ms":
            self._rotulos[chave].setText(t("toque.janela_duplo", valor=valor))
        else:
            self._rotulos[chave].setText(t("toque.tempo_manter", valor=valor))

    def escolhas(self) -> dict:
        dados = {botao: self._combos[botao].currentData() for botao in BOTOES}
        dados.update({chave: deslizador.value() for chave, deslizador in self._deslizadores.items()})
        dados["clique_por_area"] = self._area.isChecked()
        return dados

    def _confirmar(self) -> None:
        try:
            validar_preferencias(self.escolhas())
        except ValueError:
            QMessageBox.warning(self, t("toque.titulo"), t("toque.conflito"))
            return
        self.accept()
