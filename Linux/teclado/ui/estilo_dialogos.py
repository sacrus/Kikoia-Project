"""Folha de estilo unificada (Claro/Escuro) e cabecalho padrao para todos os dialogos."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from teclado.ui.icones_menu import desenhar_ilustracao

_MODO_ESCURO = False


def definir_modo_escuro(escuro: bool) -> None:
    """Atualiza o modo claro/escuro global dos dialogos conforme o tema ativo do teclado."""
    global _MODO_ESCURO
    _MODO_ESCURO = bool(escuro)


def modo_escuro() -> bool:
    return _MODO_ESCURO


def estilo_dialogo_base(escuro: bool, cor_destaque: str = "#2563EB") -> str:
    """QSS moderno em modo Claro ou Escuro, coerente com o menu e a janela de IA."""
    if escuro:
        fundo = "#16181D"
        cartao = "#1E222A"
        campo = "#262B35"
        texto = "#F1F5F9"
        texto_sec = "#CBD5E1"
        texto_suave = "#94A3B8"
        borda = "#333946"
        borda_hover = "#4B5568"
        btn_hover = "#2E3544"
        checked_bg = "#1E3A5F"
        checked_txt = "#93C5FD"
        destaque_hover = "#1D4ED8" if cor_destaque == "#2563EB" else cor_destaque
    else:
        fundo = "#F1F5F9"
        cartao = "#FFFFFF"
        campo = "#F8FAFC"
        texto = "#0F172A"
        texto_sec = "#1E293B"
        texto_suave = "#64748B"
        borda = "#CBD5E1"
        borda_hover = "#94A3B8"
        btn_hover = "#EFF6FF"
        checked_bg = "#DBEAFE"
        checked_txt = "#1D4ED8"
        destaque_hover = "#1D4ED8" if cor_destaque == "#2563EB" else cor_destaque

    return f"""
QDialog {{
    background-color: {fundo};
    color: {texto};
}}
QLabel {{
    color: {texto_sec};
}}
QLabel#titulo_dialogo {{
    color: {texto};
    font-size: 18px;
    font-weight: 700;
}}
QLabel#subtitulo_dialogo {{
    color: {texto_suave};
    font-size: 12px;
}}
QGroupBox {{
    background-color: {cartao};
    border: 1px solid {borda};
    border-radius: 12px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
    color: {texto};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {texto};
}}
QFrame#cartao_dialogo {{
    background-color: {cartao};
    border: 1px solid {borda};
    border-radius: 12px;
}}
QScrollArea {{
    background-color: {cartao};
    border: 1px solid {borda};
    border-radius: 10px;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {cartao};
}}
QCheckBox, QRadioButton {{
    color: {texto_sec};
    font-size: 13px;
    spacing: 8px;
}}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {campo};
    color: {texto};
    border: 1px solid {borda};
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 10pt;
    min-height: 22px;
}}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1.5px solid {cor_destaque};
}}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {borda_hover};
}}
QComboBox QAbstractItemView {{
    background-color: {cartao};
    color: {texto};
    font-size: 10pt;
    selection-background-color: {checked_bg};
    selection-color: {checked_txt};
}}
QListWidget {{
    background-color: {cartao};
    color: {texto};
    border: 1px solid {borda};
    border-radius: 10px;
    padding: 4px;
    font-size: 10pt;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background-color: {checked_bg};
    color: {checked_txt};
}}
QTableWidget {{
    background-color: {cartao};
    color: {texto};
    border: 1px solid {borda};
    border-radius: 10px;
    gridline-color: {borda};
}}
QHeaderView::section {{
    background-color: {campo};
    color: {texto};
    border: none;
    border-bottom: 1px solid {borda};
    padding: 6px 8px;
    font-weight: 600;
}}
QPushButton {{
    background-color: {cartao};
    color: {texto_sec};
    border: 1px solid {borda};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {btn_hover};
    border-color: {borda_hover};
}}
QPushButton:checked {{
    background-color: {checked_bg};
    border-color: {cor_destaque};
    color: {checked_txt};
}}
QPushButton:disabled {{
    opacity: 0.45;
}}
QPushButton[papel="primario"], QDialogButtonBox QPushButton:default {{
    background-color: {cor_destaque};
    color: #FFFFFF;
    border: 1px solid {cor_destaque};
}}
QPushButton[papel="primario"]:hover, QDialogButtonBox QPushButton:default:hover {{
    background-color: {destaque_hover};
    border-color: {destaque_hover};
}}
QProgressBar {{
    background-color: {campo};
    border: 1px solid {borda};
    border-radius: 6px;
    text-align: center;
    color: {texto};
    height: 16px;
}}
QProgressBar::chunk {{
    background-color: {cor_destaque};
    border-radius: 5px;
}}
"""


def aplicar_estilo_dialogo(
    dialogo: QDialog,
    *,
    escuro: bool | None = None,
    cor_destaque: str = "#2563EB",
) -> None:
    """Aplica o estilo unificado ao dialogo (usa o modo global se escuro=None)."""
    usar_escuro = _MODO_ESCURO if escuro is None else escuro
    dialogo.setStyleSheet(estilo_dialogo_base(usar_escuro, cor_destaque=cor_destaque))


def criar_cabecalho_dialogo(
    titulo: str,
    subtitulo: str | None = None,
    icone: str | None = None,
) -> QHBoxLayout:
    """Cabecalho visual uniforme com emblema vetorial opcional, titulo e subtitulo."""
    cabecalho = QHBoxLayout()
    cabecalho.setSpacing(12)
    if icone:
        emblema = QLabel()
        emblema.setPixmap(desenhar_ilustracao(icone, 40))
        emblema.setFixedSize(52, 52)
        emblema.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emblema.setStyleSheet("background-color: #FFFFFF; border-radius: 13px; border: 1px solid #E2E8F0;")
        cabecalho.addWidget(emblema)

    textos = QVBoxLayout()
    textos.setSpacing(2)
    lbl_titulo = QLabel(titulo)
    lbl_titulo.setObjectName("titulo_dialogo")
    textos.addWidget(lbl_titulo)
    if subtitulo:
        lbl_sub = QLabel(subtitulo)
        lbl_sub.setObjectName("subtitulo_dialogo")
        lbl_sub.setWordWrap(True)
        textos.addWidget(lbl_sub)
    cabecalho.addLayout(textos, 1)
    return cabecalho
