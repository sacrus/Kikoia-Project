"""Dialogo de definicoes: tudo o que nao e uso diario fica aqui (roda dentada)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from teclado.core import idiomas
from teclado.core.atualizacao import VERSAO
from teclado.core.idiomas import t

ACAO_NENHUMA = ""
ACAO_EDITAR = "editar_teclados"
ACAO_PERSONALIZAR = "personalizar"
ACAO_SUPERVISAO = "supervisao"
ACAO_VOZ = "voz"
ACAO_IA = "ia"
ACAO_FISICO = "fisico"
ACAO_GATEWAY = "gateway"
ACAO_COMANDOS = "comandos"
ACAO_ATUALIZACOES = "atualizacoes"


class DialogoDefinicoes(QDialog):
    """Escolha de teclado, tema, idioma e numero de sugestoes, mais atalhos.

    Depois de fechar com OK (ou com um dos atalhos), escolhas() devolve o que o
    utilizador pediu. Cancelar devolve None (quem chama nao aplica nada).
    """

    def __init__(
        self,
        parent: QWidget | None,
        layouts: list[str],
        layout_atual: str,
        temas: list[str],
        tema_atual: str,
        max_sugestoes: int,
        auto_iniciar: bool = False,
        arranque_sistema: bool = False,
        idioma_atual: str = idiomas.IDIOMA_PADRAO,
        verificar_atualizacoes: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("definicoes.titulo"))
        self._acao = ACAO_NENHUMA

        self._layout = QComboBox()
        self._layout.addItems(layouts)
        self._layout.setCurrentText(layout_atual)

        self._tema = QComboBox()
        self._tema.addItems(temas)
        self._tema.setCurrentText(tema_atual)

        self._idioma = QComboBox()
        for codigo, nome in idiomas.IDIOMAS.items():
            self._idioma.addItem(nome, codigo)
        self._idioma.setCurrentIndex(self._idioma.findData(idioma_atual))
        self._idioma_inicial = idioma_atual
        self._aviso_idioma = QLabel(t("definicoes.idioma_aviso"))
        self._aviso_idioma.setWordWrap(True)
        self._aviso_idioma.setVisible(False)
        self._idioma.currentIndexChanged.connect(
            lambda _=0: self._aviso_idioma.setVisible(self._idioma.currentData() != self._idioma_inicial)
        )

        self._max = QSpinBox()
        self._max.setRange(1, 10)
        self._max.setValue(max_sugestoes)

        self._arranque = QCheckBox(t("definicoes.arranque_opcao"))
        self._arranque.setChecked(arranque_sistema)
        self._arranque.setToolTip(t("definicoes.arranque_dica"))

        self._auto = QCheckBox(t("definicoes.telemovel_opcao"))
        self._auto.setChecked(auto_iniciar)
        self._auto.setToolTip(t("definicoes.telemovel_dica"))

        self._verificar = QCheckBox(t("definicoes.verificar_atualizacoes"))
        self._verificar.setChecked(verificar_atualizacoes)

        formulario = QFormLayout()
        formulario.addRow(t("definicoes.teclado"), self._layout)
        formulario.addRow(t("definicoes.tema"), self._tema)
        formulario.addRow(t("definicoes.idioma"), self._idioma)
        formulario.addRow(t("definicoes.sugestoes"), self._max)
        formulario.addRow(t("definicoes.arranque"), self._arranque)
        formulario.addRow(t("definicoes.telemovel"), self._auto)
        formulario.addRow(t("definicoes.atualizacoes_grupo"), self._verificar)

        botao_editar = QPushButton(t("definicoes.editar"))
        botao_editar.clicked.connect(lambda _=False: self._acionar(ACAO_EDITAR))
        botao_personalizar = QPushButton(t("definicoes.personalizar"))
        botao_personalizar.clicked.connect(lambda _=False: self._acionar(ACAO_PERSONALIZAR))
        botao_supervisao = QPushButton(t("definicoes.supervisao"))
        botao_supervisao.clicked.connect(lambda _=False: self._acionar(ACAO_SUPERVISAO))
        botao_voz = QPushButton(t("definicoes.voz"))
        botao_voz.clicked.connect(lambda _=False: self._acionar(ACAO_VOZ))
        botao_ia = QPushButton(t("definicoes.ia"))
        botao_ia.clicked.connect(lambda _=False: self._acionar(ACAO_IA))
        botao_fisico = QPushButton(t("definicoes.fisico"))
        botao_fisico.clicked.connect(lambda _=False: self._acionar(ACAO_FISICO))

        caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        caixa.accepted.connect(self.accept)
        caixa.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.addLayout(formulario)
        raiz.addWidget(self._aviso_idioma)
        raiz.addWidget(botao_editar)
        raiz.addWidget(botao_personalizar)
        raiz.addWidget(botao_voz)
        raiz.addWidget(botao_ia)
        raiz.addWidget(botao_fisico)
        botao_gateway = QPushButton(t("definicoes.telemovel_botao"))
        botao_gateway.clicked.connect(lambda _=False: self._acionar(ACAO_GATEWAY))
        raiz.addWidget(botao_gateway)
        botao_comandos = QPushButton(t("definicoes.comandos"))
        botao_comandos.clicked.connect(lambda _=False: self._acionar(ACAO_COMANDOS))
        raiz.addWidget(botao_comandos)
        botao_atualizacoes = QPushButton(t("definicoes.atualizacoes"))
        botao_atualizacoes.clicked.connect(lambda _=False: self._acionar(ACAO_ATUALIZACOES))
        raiz.addWidget(botao_atualizacoes)
        raiz.addWidget(botao_supervisao)
        raiz.addWidget(caixa)
        rodape = QLabel(
            f"Versão {VERSAO} · Projeto Desenvolvido por: Luís Patrício<br>"
            '<a href="https://www.lplogic.net">www.lplogic.net</a>'
        )
        rodape.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rodape.setOpenExternalLinks(True)
        raiz.addWidget(rodape)

    def _acionar(self, acao: str) -> None:
        self._acao = acao
        self.accept()

    def escolhas(self) -> dict:
        return {
            "layout": self._layout.currentText(),
            "tema": self._tema.currentText(),
            "idioma": self._idioma.currentData(),
            "max_sugestoes": self._max.value(),
            "acao": self._acao,
            "auto_iniciar": self._auto.isChecked(),
            "arranque_sistema": self._arranque.isChecked(),
            "verificar_atualizacoes": self._verificar.isChecked(),
        }
