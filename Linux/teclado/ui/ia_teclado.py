"""Dialogo "Criar teclado com IA": descrever, pre-visualizar e so depois guardar."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teclado.core.ia import (
    MODELO_POR_OMISSAO,
    ClienteOpenAI,
    ConfigIA,
    IAErro,
    gerar_pacote,
)
from teclado.core.idiomas import t
from teclado.ui.icones_menu import desenhar_ilustracao

EXEMPLO = "Um teclado com as vogais do alfabeto português, em letras grandes."


def _estilo_ia(escuro: bool) -> str:
    if escuro:
        fundo = "#16181D"
        cartao = "#1E222A"
        campo = "#262B35"
        texto = "#F1F5F9"
        texto_sec = "#CBD5E1"
        texto_suave = "#94A3B8"
        borda = "#333946"
        ajuda_bg = "#1D263B"
        ajuda_borda = "#2E426B"
        previa_bg = "#191C23"
        primario = "#7C3AED"
        primario_hover = "#6D28D9"
        acao_ok = "#2563EB"
        acao_ok_hover = "#1D4ED8"
        btn_hover = "#2E3544"
    else:
        fundo = "#F1F5F9"
        cartao = "#FFFFFF"
        campo = "#F8FAFC"
        texto = "#0F172A"
        texto_sec = "#1E293B"
        texto_suave = "#64748B"
        borda = "#CBD5E1"
        ajuda_bg = "#EFF6FF"
        ajuda_borda = "#BFDBFE"
        previa_bg = "#F8FAFC"
        primario = "#7C3AED"
        primario_hover = "#6D28D9"
        acao_ok = "#2563EB"
        acao_ok_hover = "#1D4ED8"
        btn_hover = "#F1F5F9"

    return f"""
QDialog {{
    background-color: {fundo};
    color: {texto};
}}
QLabel {{
    color: {texto_sec};
}}
QLabel#titulo_ia {{
    color: {texto};
    font-size: 19px;
    font-weight: 700;
}}
QLabel#subtitulo_ia {{
    color: {texto_suave};
    font-size: 12px;
}}
QFrame#cartao_ia {{
    background-color: {cartao};
    border: 1px solid {borda};
    border-radius: 12px;
}}
QFrame#cartao_ajuda {{
    background-color: {ajuda_bg};
    border: 1px solid {ajuda_borda};
    border-radius: 10px;
}}
QLineEdit, QPlainTextEdit {{
    background-color: {campo};
    color: {texto};
    border: 1px solid {borda};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 10pt;
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {primario};
}}
QPushButton#botao_gerar {{
    background-color: {primario};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#botao_gerar:hover {{
    background-color: {primario_hover};
}}
QPushButton#botao_ajuda {{
    background-color: transparent;
    color: #3B82F6;
    border: none;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 0;
}}
QPushButton#botao_ajuda:hover {{
    text-decoration: underline;
}}
QPushButton#botao_mostrar {{
    background-color: {campo};
    color: {texto_sec};
    border: 1px solid {borda};
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#botao_mostrar:hover {{
    background-color: {btn_hover};
}}
QLabel#previa_ia {{
    background-color: {previa_bg};
    color: {texto};
    font-size: 15px;
    padding: 12px;
    border: 1px solid {borda};
    border-radius: 10px;
}}
QLabel#estado_ia {{
    color: {texto_suave};
    font-size: 12px;
    font-weight: 600;
}}
QDialogButtonBox QPushButton {{
    background-color: {cartao};
    color: {texto_sec};
    border: 1px solid {borda};
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 600;
    min-width: 84px;
}}
QDialogButtonBox QPushButton:hover {{
    background-color: {btn_hover};
}}
QPushButton#botao_usar {{
    background-color: {acao_ok};
    color: #FFFFFF;
    border: 1px solid {acao_ok};
}}
QPushButton#botao_usar:hover {{
    background-color: {acao_ok_hover};
}}
QPushButton#botao_usar:disabled {{
    background-color: {borda};
    color: {texto_suave};
    border: 1px solid {borda};
}}
"""


class DialogoIATeclado(QDialog):
    """Pede um teclado a IA. Resultado: o modelo validado (dict), ou None se cancelado.

    Guardar o teclado e feito por quem chama (para aplicar a politica de supervisao).
    A chave e o modelo, se alterados, sao devolvidos em config_alterada().
    """

    def __init__(self, parent: QWidget | None, config: ConfigIA, *, escuro: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("ia.titulo"))
        self.resize(680, 640)
        self.estado_inicial = Qt.WindowState.WindowNoState
        self.setStyleSheet(_estilo_ia(escuro))
        self._config = config
        self._modelo: dict | None = None
        self._comandos: list[dict] = []

        # --- cabecalho com ilustracao vetorial ---------------------------
        cabecalho = QHBoxLayout()
        cabecalho.setSpacing(12)
        emblema = QLabel()
        emblema.setPixmap(desenhar_ilustracao("ia", 44))
        emblema.setFixedSize(56, 56)
        emblema.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emblema.setStyleSheet("background-color: #FFFFFF; border-radius: 14px; border: 1px solid #E2E8F0;")
        titulo_box = QVBoxLayout()
        titulo_box.setSpacing(2)
        lbl_titulo = QLabel(t("ia.titulo"))
        lbl_titulo.setObjectName("titulo_ia")
        lbl_sub = QLabel(t("ia.descreva"))
        lbl_sub.setObjectName("subtitulo_ia")
        lbl_sub.setWordWrap(True)
        titulo_box.addWidget(lbl_titulo)
        titulo_box.addWidget(lbl_sub)
        cabecalho.addWidget(emblema)
        cabecalho.addLayout(titulo_box, 1)

        # --- cartao de configuracao + guia OpenAI ------------------------
        cartao_cfg = QFrame()
        cartao_cfg.setObjectName("cartao_ia")
        cfg_layout = QVBoxLayout(cartao_cfg)
        cfg_layout.setContentsMargins(14, 12, 14, 12)
        cfg_layout.setSpacing(8)

        self._chave = QLineEdit(config.chave)
        self._chave.setEchoMode(QLineEdit.EchoMode.Password)
        self._chave.setPlaceholderText(t("ia.chave_placeholder"))
        botao_mostrar = QPushButton(t("ia.mostrar_chave"))
        botao_mostrar.setObjectName("botao_mostrar")
        botao_mostrar.setCheckable(True)
        botao_mostrar.setCursor(Qt.CursorShape.PointingHandCursor)
        botao_mostrar.toggled.connect(
            lambda visivel: self._chave.setEchoMode(
                QLineEdit.EchoMode.Normal if visivel else QLineEdit.EchoMode.Password
            )
        )
        linha_chave = QHBoxLayout()
        linha_chave.setSpacing(6)
        linha_chave.addWidget(self._chave, 1)
        linha_chave.addWidget(botao_mostrar)

        self._modelo_ia = QLineEdit(config.modelo or MODELO_POR_OMISSAO)

        formulario = QFormLayout()
        formulario.setSpacing(8)
        formulario.addRow(t("ia.chave"), linha_chave)
        formulario.addRow(t("ia.modelo"), self._modelo_ia)
        cfg_layout.addLayout(formulario)

        # Guia passo a passo (aberto por omissao quando ainda nao ha chave)
        sem_chave = not bool(config.chave.strip())
        self._botao_ajuda = QPushButton(f"▸ {t('ia.ajuda_titulo')}" if not sem_chave else f"▾ {t('ia.ajuda_titulo')}")
        self._botao_ajuda.setObjectName("botao_ajuda")
        self._botao_ajuda.setCheckable(True)
        self._botao_ajuda.setChecked(sem_chave)
        self._botao_ajuda.setCursor(Qt.CursorShape.PointingHandCursor)

        self._cartao_ajuda = QFrame()
        self._cartao_ajuda.setObjectName("cartao_ajuda")
        self._cartao_ajuda.setVisible(sem_chave)
        ajuda_layout = QVBoxLayout(self._cartao_ajuda)
        ajuda_layout.setContentsMargins(12, 10, 12, 10)
        cor_link = "#60A5FA" if escuro else "#2563EB"
        lbl_ajuda = QLabel(f"<style>a {{ color: {cor_link}; text-decoration: none; font-weight: 600; }}</style>{t('ia.ajuda_texto')}")
        lbl_ajuda.setWordWrap(True)
        lbl_ajuda.setOpenExternalLinks(True)
        lbl_ajuda.setStyleSheet("font-size: 12px; line-height: 1.4;")
        ajuda_layout.addWidget(lbl_ajuda)

        self._botao_ajuda.toggled.connect(self._alternar_ajuda)
        cfg_layout.addWidget(self._botao_ajuda)
        cfg_layout.addWidget(self._cartao_ajuda)

        # --- cartao de pedido e previa -----------------------------------
        cartao_pedido = QFrame()
        cartao_pedido.setObjectName("cartao_ia")
        pedido_layout = QVBoxLayout(cartao_pedido)
        pedido_layout.setContentsMargins(14, 12, 14, 12)
        pedido_layout.setSpacing(8)

        self._descricao = QPlainTextEdit()
        self._descricao.setPlaceholderText(t("ia.exemplo"))
        self._descricao.setMaximumHeight(86)

        botao_gerar = QPushButton(t("ia.gerar"))
        botao_gerar.setObjectName("botao_gerar")
        botao_gerar.setCursor(Qt.CursorShape.PointingHandCursor)
        botao_gerar.clicked.connect(self._gerar)

        self._estado = QLabel(t("ia.descreva"))
        self._estado.setObjectName("estado_ia")
        self._estado.setWordWrap(True)

        self._previa = QLabel()
        self._previa.setObjectName("previa_ia")
        self._previa.setWordWrap(True)
        self._previa.setMinimumHeight(140)
        self._previa.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        pedido_layout.addWidget(QLabel(t("ia.o_que")))
        pedido_layout.addWidget(self._descricao)
        pedido_layout.addWidget(botao_gerar)
        pedido_layout.addWidget(self._estado)
        pedido_layout.addWidget(QLabel(t("ia.previa")))
        pedido_layout.addWidget(self._previa, 1)

        # --- rodape ------------------------------------------------------
        self._caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._botao_usar = QPushButton(t("ia.usar"))
        self._botao_usar.setObjectName("botao_usar")
        self._botao_usar.setEnabled(False)
        self._botao_usar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._botao_usar.clicked.connect(self._usar)
        self._caixa.addButton(self._botao_usar, QDialogButtonBox.ButtonRole.ActionRole)
        self._caixa.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        raiz.setSpacing(12)
        raiz.addLayout(cabecalho)
        raiz.addWidget(cartao_cfg)
        raiz.addWidget(cartao_pedido, 1)
        raiz.addWidget(self._caixa)

    def _alternar_ajuda(self, visivel: bool) -> None:
        self._cartao_ajuda.setVisible(visivel)
        prefixo = "▾" if visivel else "▸"
        self._botao_ajuda.setText(f"{prefixo} {t('ia.ajuda_titulo')}")

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
        self._mostrar(modelo, comandos)
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
