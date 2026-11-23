"""Dialogo de definicoes: painel visual em grelha de cartoes (roda dentada)."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from teclado.core import idiomas
from teclado.core.atualizacao import VERSAO
from teclado.core.idiomas import t
from teclado.core.paths import DADOS_PROJETO
from teclado.ui.icones_menu import desenhar_ilustracao

ACAO_NENHUMA = ""
ACAO_EDITAR = "editar_teclados"
ACAO_PERSONALIZAR = "personalizar"
ACAO_SUPERVISAO = "supervisao"
ACAO_VOZ = "voz"
ACAO_IA = "ia"
ACAO_FISICO = "fisico"
ACAO_GATEWAY = "gateway"
ACAO_ATUALIZACOES = "atualizacoes"
ACAO_TOQUE = "toque"
ACAO_QUADRO = "quadro"


_CHAVE_TEMA = {
    "Claro": "tema.claro",
    "Escuro": "tema.escuro",
}


def _rotulo_tema(nome: str) -> str:
    """Nome traduzido para os temas de origem (Claro/Escuro); temas do utilizador mantem o nome."""
    return t(_CHAVE_TEMA[nome]) if nome in _CHAVE_TEMA else nome


def _tema_e_escuro(nome: str, cores_temas: dict[str, str] | None) -> bool:
    """Decide se o menu deve usar modo escuro com base na luminosidade do fundo do tema."""
    cor = (cores_temas or {}).get(nome)
    if cor and len(cor) == 7 and cor.startswith("#"):
        r, g, b = int(cor[1:3], 16), int(cor[3:5], 16), int(cor[5:7], 16)
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 <= 0.5
    return nome.strip().lower() == "escuro"


def _estilo_dialogo(escuro: bool) -> str:
    if escuro:
        fundo = "#16181D"
        superficie = "#1E222A"
        campo = "#262B35"
        texto = "#F1F5F9"
        texto_sec = "#CBD5E1"
        texto_suave = "#94A3B8"
        borda = "#333946"
        borda_hover = "#4B5568"
        botao_hover = "#2E3544"
        checked_bg = "#1E3A5F"
        checked_txt = "#93C5FD"
        primario = "#3B82F6"
        primario_hover = "#2563EB"
    else:
        fundo = "#F1F5F9"
        superficie = "#FFFFFF"
        campo = "#F8FAFC"
        texto = "#0F172A"
        texto_sec = "#1E293B"
        texto_suave = "#64748B"
        borda = "#CBD5E1"
        borda_hover = "#94A3B8"
        botao_hover = "#EFF6FF"
        checked_bg = "#DBEAFE"
        checked_txt = "#1D4ED8"
        primario = "#2563EB"
        primario_hover = "#1D4ED8"

    return f"""
QDialog {{
    background-color: {fundo};
    color: {texto};
}}
QLabel {{
    color: {texto_sec};
}}
QLabel#titulo_menu {{
    color: {texto};
    font-size: 21px;
    font-weight: 700;
}}
QLabel#subtitulo_menu {{
    color: {texto_suave};
    font-size: 13px;
}}
QLabel#etiqueta_rapida {{
    color: {texto_sec};
    font-weight: 600;
    font-size: 13px;
}}
QLabel#rodape_menu {{
    color: {texto_suave};
    font-size: 12px;
}}
QCheckBox {{
    color: {texto_sec};
    font-size: 13px;
    spacing: 8px;
}}
QFrame#barra_rapida, QFrame#painel_opcoes {{
    background-color: {superficie};
    border: 1px solid {borda};
    border-radius: 12px;
}}
QComboBox, QSpinBox {{
    background-color: {campo};
    color: {texto};
    border: 1px solid {borda};
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 10pt;
    min-height: 22px;
}}
QComboBox:hover, QSpinBox:hover {{
    border-color: {borda_hover};
}}
QComboBox QAbstractItemView {{
    background-color: {superficie};
    color: {texto};
    font-size: 10pt;
    selection-background-color: {checked_bg};
    selection-color: {checked_txt};
}}
QPushButton#botao_opcoes {{
    background-color: {superficie};
    color: {texto_sec};
    border: 1px solid {borda};
    border-radius: 18px;
    padding: 5px 14px 5px 8px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#botao_opcoes:hover {{
    background-color: {botao_hover};
    border-color: {primario};
}}
QPushButton#botao_opcoes:checked {{
    background-color: {checked_bg};
    border-color: {primario};
    color: {checked_txt};
}}
QPushButton[papel="secundario"] {{
    background-color: {superficie};
    color: {texto_sec};
    border: 1px solid {borda};
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton[papel="secundario"]:hover {{
    background-color: {botao_hover};
    border-color: {primario};
    color: {checked_txt};
}}
QPushButton[papel="secundario"]:pressed {{
    background-color: {checked_bg};
}}
QDialogButtonBox QPushButton {{
    background-color: {superficie};
    color: {texto_sec};
    border: 1px solid {borda};
    border-radius: 8px;
    padding: 6px 18px;
    font-size: 13px;
    font-weight: 600;
    min-width: 78px;
}}
QDialogButtonBox QPushButton:hover {{
    background-color: {botao_hover};
    border-color: {borda_hover};
}}
QDialogButtonBox QPushButton:default {{
    background-color: {primario};
    color: #FFFFFF;
    border: 1px solid {primario};
}}
QDialogButtonBox QPushButton:default:hover {{
    background-color: {primario_hover};
    border-color: {primario_hover};
}}
"""


class _CartaoMenu(QPushButton):
    """Cartao colorido com titulo legivel e ilustracao vetorial num emblema branco."""

    def __init__(
        self,
        titulo: str,
        ilustracao: str,
        cor_inicio: str,
        cor_fim: str,
        *,
        destaque: bool = False,
    ) -> None:
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(210 if destaque else 156, 308 if destaque else 148)
        self.setStyleSheet(f"""
            _CartaoMenu {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {cor_inicio}, stop:1 {cor_fim});
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 16px;
                padding: 12px;
            }}
            _CartaoMenu:hover {{
                border: 2px solid #FFFFFF;
            }}
            _CartaoMenu:pressed {{
                background: {cor_fim};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 14)
        layout.setSpacing(10 if destaque else 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        etiqueta = QLabel(titulo)
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiqueta.setWordWrap(True)
        etiqueta.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        tamanho_texto = 18 if destaque else 14
        etiqueta.setStyleSheet(
            f"color: #FFFFFF; font-size: {tamanho_texto}px; font-weight: 700; background: transparent;"
        )

        lado_icone = 112 if destaque else 56
        emblema = QLabel()
        emblema.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emblema.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        emblema.setPixmap(desenhar_ilustracao(ilustracao, lado_icone))
        emblema.setFixedSize(lado_icone + 24, lado_icone + 16)
        emblema.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.95); border-radius: 16px; padding: 6px;"
        )

        if destaque:
            layout.addStretch(1)
            layout.addWidget(etiqueta)
            layout.addSpacing(10)
            layout.addWidget(emblema, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addStretch(1)
        else:
            layout.addWidget(etiqueta)
            layout.addWidget(emblema, alignment=Qt.AlignmentFlag.AlignCenter)


class DialogoDefinicoes(QDialog):
    """Painel de definicoes em grelha visual + opcoes rapidas e gerais.

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
        cores_temas: dict[str, str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("definicoes.titulo"))
        self.setMinimumWidth(860)
        self._cores_temas = cores_temas or {}
        self._acao = ACAO_NENHUMA

        # --- controlos de preferencias -----------------------------------
        self._layout = QComboBox()
        self._layout.addItems(layouts)
        self._layout.setCurrentText(layout_atual)

        self._tema = QComboBox()
        for nome_tema in temas:
            self._tema.addItem(_rotulo_tema(nome_tema), nome_tema)
        indice_tema = self._tema.findData(tema_atual)
        if indice_tema >= 0:
            self._tema.setCurrentIndex(indice_tema)
        else:
            self._tema.setCurrentText(tema_atual)
        self._tema.currentIndexChanged.connect(lambda _=0: self._aplicar_estilo_tema(self._tema_selecionado()))

        self._idioma = QComboBox()
        for codigo, nome in idiomas.IDIOMAS.items():
            self._idioma.addItem(nome, codigo)
        self._idioma.setCurrentIndex(self._idioma.findData(idioma_atual))
        self._idioma_inicial = idioma_atual
        self._aviso_idioma = QLabel(t("definicoes.idioma_aviso"))
        self._aviso_idioma.setWordWrap(True)
        self._aviso_idioma.setStyleSheet("color: #B45309; font-size: 12px;")
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

        # --- cabecalho + botao azul de opcoes gerais ---------------------
        cabecalho = QHBoxLayout()
        titulo_box = QVBoxLayout()
        titulo_box.setSpacing(2)
        self._logo_titulo = QLabel("Kikoia")
        self._logo_titulo.setObjectName("titulo_menu")
        lbl_sub = QLabel(t("definicoes.titulo"))
        lbl_sub.setObjectName("subtitulo_menu")
        titulo_box.addWidget(self._logo_titulo)
        titulo_box.addWidget(lbl_sub)

        self._botao_opcoes = QPushButton(t("definicoes.titulo"))
        self._botao_opcoes.setObjectName("botao_opcoes")
        self._botao_opcoes.setCheckable(True)
        self._botao_opcoes.setCursor(Qt.CursorShape.PointingHandCursor)
        self._botao_opcoes.setIcon(QIcon(desenhar_ilustracao("opcoes", 28)))
        self._botao_opcoes.setIconSize(QSize(24, 24))
        self._botao_opcoes.toggled.connect(self._alternar_opcoes)

        botao_atualizacoes = QPushButton(t("definicoes.atualizacoes"))
        botao_atualizacoes.setProperty("papel", "secundario")
        botao_atualizacoes.setCursor(Qt.CursorShape.PointingHandCursor)
        botao_atualizacoes.clicked.connect(lambda _=False: self._acionar(ACAO_ATUALIZACOES))

        cabecalho.addLayout(titulo_box)
        cabecalho.addStretch(1)
        cabecalho.addWidget(botao_atualizacoes)
        cabecalho.addWidget(self._botao_opcoes)

        # --- barra rapida (Teclado e Tema sempre a mao) ------------------
        barra_rapida = QFrame()
        barra_rapida.setObjectName("barra_rapida")
        rapida_layout = QHBoxLayout(barra_rapida)
        rapida_layout.setContentsMargins(14, 10, 14, 10)
        rapida_layout.setSpacing(10)
        for texto, combo in ((t("definicoes.teclado"), self._layout), (t("definicoes.tema"), self._tema)):
            lbl = QLabel(texto)
            lbl.setObjectName("etiqueta_rapida")
            rapida_layout.addWidget(lbl)
            rapida_layout.addWidget(combo, 1)

        # --- painel expansivel de opcoes gerais --------------------------
        self._painel_opcoes = QFrame()
        self._painel_opcoes.setObjectName("painel_opcoes")
        self._painel_opcoes.setVisible(False)
        opcoes_layout = QVBoxLayout(self._painel_opcoes)
        opcoes_layout.setContentsMargins(14, 12, 14, 12)
        formulario = QFormLayout()
        formulario.setSpacing(8)
        formulario.addRow(t("definicoes.idioma"), self._idioma)
        formulario.addRow(t("definicoes.sugestoes"), self._max)
        formulario.addRow(t("definicoes.arranque"), self._arranque)
        formulario.addRow(t("definicoes.telemovel"), self._auto)
        formulario.addRow(t("definicoes.atualizacoes_grupo"), self._verificar)
        opcoes_layout.addLayout(formulario)
        opcoes_layout.addWidget(self._aviso_idioma)

        # --- grelha principal de 9 cartoes (estilo Bento) ----------------
        grelha = QGridLayout()
        grelha.setSpacing(12)

        cartao_quadro = _CartaoMenu(
            t("definicoes.abrir_quadro"), "quadro", "#F43F5E", "#E11D48", destaque=True
        )
        cartao_quadro.clicked.connect(lambda _=False: self._acionar(ACAO_QUADRO))

        cartoes_secundarios = (
            # Linha 0
            (0, 1, "definicoes.editar", "editar", "#EC4899", "#DB2777", ACAO_EDITAR),
            (0, 2, "definicoes.personalizar", "personalizar", "#22C55E", "#16A34A", ACAO_PERSONALIZAR),
            (0, 3, "definicoes.telemovel_botao", "telemovel", "#3B82F6", "#2563EB", ACAO_GATEWAY),
            (0, 4, "definicoes.voz", "voz", "#F59E0B", "#D97706", ACAO_VOZ),
            # Linha 1
            (1, 1, "definicoes.ia", "ia", "#8B5CF6", "#7C3AED", ACAO_IA),
            (1, 2, "definicoes.fisico", "sugestoes", "#14B8A6", "#0D9488", ACAO_FISICO),
            (1, 3, "definicoes.toque", "touchpad", "#0EA5E9", "#0284C7", ACAO_TOQUE),
            (1, 4, "definicoes.supervisao", "supervisao", "#6366F1", "#4F46E5", ACAO_SUPERVISAO),
        )

        grelha.addWidget(cartao_quadro, 0, 0, 2, 1)
        for lin, col, chave, icone, c1, c2, acao in cartoes_secundarios:
            cartao = _CartaoMenu(t(chave), icone, c1, c2)
            cartao.clicked.connect(lambda _=False, a=acao: self._acionar(a))
            grelha.addWidget(cartao, lin, col)

        grelha.setColumnStretch(0, 13)
        for col in range(1, 5):
            grelha.setColumnStretch(col, 10)

        # --- rodape e botoes OK / Cancelar -------------------------------
        caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        caixa.accepted.connect(self.accept)
        caixa.rejected.connect(self.reject)

        self._rodape = QLabel()
        self._rodape.setObjectName("rodape_menu")
        self._rodape.setOpenExternalLinks(True)

        linha_rodape = QHBoxLayout()
        linha_rodape.addWidget(self._rodape, 1)
        linha_rodape.addWidget(caixa)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        raiz.setSpacing(12)
        raiz.addLayout(cabecalho)
        raiz.addWidget(barra_rapida)
        raiz.addWidget(self._painel_opcoes)
        raiz.addLayout(grelha)
        raiz.addLayout(linha_rodape)

        self._aplicar_estilo_tema(tema_atual)

    def _aplicar_estilo_tema(self, nome_tema: str) -> None:
        escuro = _tema_e_escuro(nome_tema, self._cores_temas)
        self._escuro = escuro
        self.setStyleSheet(_estilo_dialogo(escuro))
        ficheiro_logo = DADOS_PROJETO / "icone" / ("kikoia_texto_escuro.png" if escuro else "kikoia_texto.png")
        pix = QPixmap(str(ficheiro_logo))
        if not pix.isNull():
            self._logo_titulo.setText("")
            self._logo_titulo.setPixmap(pix.scaledToHeight(28, Qt.TransformationMode.SmoothTransformation))
        else:
            self._logo_titulo.setPixmap(QPixmap())
            self._logo_titulo.setText("Kikoia")
        cor_link = "#60A5FA" if escuro else "#2563EB"
        self._rodape.setText(
            f"Versão {VERSAO} · Projeto Desenvolvido por: Luís Patrício · "
            f'<a href="https://www.lplogic.net" style="color:{cor_link}; text-decoration:none;">www.lplogic.net</a>'
        )

    def _alternar_opcoes(self, visivel: bool) -> None:
        self._painel_opcoes.setVisible(visivel)
        self.adjustSize()

    def _acionar(self, acao: str) -> None:
        self._acao = acao
        self.accept()

    def _tema_selecionado(self) -> str:
        dado = self._tema.currentData()
        return dado if isinstance(dado, str) and dado else self._tema.currentText()

    def escolhas(self) -> dict:
        return {
            "layout": self._layout.currentText(),
            "tema": self._tema_selecionado(),
            "idioma": self._idioma.currentData(),
            "max_sugestoes": self._max.value(),
            "acao": self._acao,
            "auto_iniciar": self._auto.isChecked(),
            "arranque_sistema": self._arranque.isChecked(),
            "verificar_atualizacoes": self._verificar.isChecked(),
        }
