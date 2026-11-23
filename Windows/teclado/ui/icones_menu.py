"""Ilustracoes vetoriais originais (QPainter) para o painel de definicoes.

Desenhadas em codigo sem imagens externas: nitidas em qualquer resolucao e sem
dependencias de licencas de terceiros.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


def desenhar_ilustracao(nome: str, tamanho: int = 96) -> QPixmap:
    """Devolve um QPixmap transparente com uma ilustracao vetorial original."""
    pix = QPixmap(tamanho, tamanho)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Coordenadas normalizadas 0..100 para escalar perfeitamente a qualquer tamanho.
    escala = tamanho / 100.0
    p.scale(escala, escala)

    if nome == "quadro":
        _desenhar_quadro(p)
    elif nome == "editar":
        _desenhar_editar(p)
    elif nome == "personalizar":
        _desenhar_personalizar(p)
    elif nome == "telemovel":
        _desenhar_telemovel(p)
    elif nome == "voz":
        _desenhar_voz(p)
    elif nome == "ia":
        _desenhar_ia(p)
    elif nome == "sugestoes":
        _desenhar_sugestoes(p)
    elif nome == "touchpad":
        _desenhar_touchpad(p)
    elif nome == "supervisao":
        _desenhar_supervisao(p)
    elif nome == "opcoes":
        _desenhar_opcoes(p)
    p.end()
    return pix


def _desenhar_quadro(p: QPainter) -> None:
    """Quadro interativo com elementos coloridos e mao estilizada a tocar."""
    # Moldura do quadro
    p.setPen(QPen(QColor("#334155"), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#F8FAFC"))
    p.drawRoundedRect(QRectF(10, 12, 80, 56), 8, 8)

    # Barra inferior do quadro
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#64748B"))
    p.drawRoundedRect(QRectF(12, 60, 76, 6), 3, 3)

    # Elementos no quadro (blocos coloridos e circulo)
    p.setBrush(QColor("#10B981"))
    p.drawRoundedRect(QRectF(20, 22, 16, 11), 3, 3)
    p.setBrush(QColor("#F59E0B"))
    p.drawRoundedRect(QRectF(20, 38, 14, 11), 3, 3)
    p.setBrush(QColor("#38BDF8"))
    p.drawEllipse(QPointF(68, 32), 10, 10)
    p.setBrush(QColor("#E0F2FE"))
    p.drawEllipse(QPointF(68, 32), 4.5, 4.5)

    # Traco de desenho suave
    p.setPen(QPen(QColor("#94A3B8"), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(42, 26), QPointF(54, 26))

    # Mao estilizada a tocar no quadro
    p.setPen(QPen(QColor("#334155"), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#FDBA74"))
    # Dedo indicador
    p.drawRoundedRect(QRectF(49, 36, 9, 24), 4.5, 4.5)
    # Palma
    p.drawRoundedRect(QRectF(44, 52, 24, 22), 7, 7)
    # Punho
    p.setBrush(QColor("#475569"))
    p.drawRoundedRect(QRectF(47, 74, 18, 12), 3, 3)


def _desenhar_editar(p: QPainter) -> None:
    """Teclado com distintivo de chave inglesa (edicao)."""
    # Corpo do teclado
    p.setPen(QPen(QColor("#1E293B"), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#F8FAFC"))
    p.drawRoundedRect(QRectF(10, 22, 74, 46), 8, 8)

    # Pequeno cabo no topo
    p.drawLine(QPointF(47, 22), QPointF(47, 14))
    p.drawLine(QPointF(47, 14), QPointF(56, 14))

    # Teclas
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#38BDF8"))
    for linha in range(2):
        for col in range(5):
            p.drawRoundedRect(QRectF(17 + col * 12.2, 30 + linha * 11, 9, 7.5), 2, 2)
    # Barra de espaco
    p.setBrush(QColor("#64748B"))
    p.drawRoundedRect(QRectF(24, 54, 34, 7.5), 2.5, 2.5)

    # Distintivo circular dourado com ferramenta
    p.setPen(QPen(QColor("#1E293B"), 3.4))
    p.setBrush(QColor("#FBBF24"))
    p.drawEllipse(QPointF(74, 68), 18, 18)

    # Chave inglesa simples no centro do distintivo
    p.setPen(QPen(QColor("#1E293B"), 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(68, 74), QPointF(79, 63))
    p.setBrush(QColor("#FBBF24"))
    p.drawArc(QRectF(74, 56, 10, 10), 40 * 16, 260 * 16)


def _desenhar_personalizar(p: QPainter) -> None:
    """Paleta de artista com cores vivas e pincel."""
    p.setPen(QPen(QColor("#1E293B"), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#F8FAFC"))

    # Forma da paleta
    paleta = QPainterPath()
    paleta.addEllipse(QRectF(12, 16, 72, 66))
    p.drawPath(paleta)

    # Furo do polegar
    p.setBrush(QColor("#DCFCE7"))
    p.drawEllipse(QPointF(64, 62), 7.5, 7.5)

    # Pingos de tinta coloridos
    p.setPen(Qt.PenStyle.NoPen)
    cores = (
        (QPointF(30, 36), "#EF4444"),
        (QPointF(48, 28), "#F59E0B"),
        (QPointF(66, 36), "#3B82F6"),
        (QPointF(28, 56), "#10B981"),
        (QPointF(44, 66), "#A855F7"),
    )
    for centro, cor in cores:
        p.setBrush(QColor(cor))
        p.drawEllipse(centro, 6.5, 6.5)

    # Pincel diagonal
    p.setPen(QPen(QColor("#1E293B"), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(60, 76), QPointF(86, 24))
    p.setBrush(QColor("#F59E0B"))
    p.drawEllipse(QPointF(58, 78), 5.5, 5.5)


def _desenhar_telemovel(p: QPainter) -> None:
    """Telemovel com teclado e ondas sem fios."""
    # Corpo do telemovel
    p.setPen(QPen(QColor("#1E293B"), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#F8FAFC"))
    p.drawRoundedRect(QRectF(20, 14, 46, 74), 9, 9)

    # Ecra interno
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#DBEAFE"))
    p.drawRoundedRect(QRectF(26, 23, 34, 48), 4, 4)

    # Mini teclas no ecra do telemovel
    p.setBrush(QColor("#2563EB"))
    for linha in range(2):
        for col in range(3):
            p.drawRoundedRect(QRectF(29 + col * 9.8, 46 + linha * 8, 7.6, 5.5), 1.5, 1.5)
    p.setBrush(QColor("#60A5FA"))
    p.drawRoundedRect(QRectF(33, 62, 20, 5.5), 2, 2)

    # Botao home discreto
    p.setBrush(QColor("#94A3B8"))
    p.drawEllipse(QPointF(43, 79), 3.0, 3.0)

    # Ondas Wi-Fi / Bluetooth a direita
    p.setBrush(Qt.BrushStyle.NoBrush)
    for raio, cor in ((10, "#38BDF8"), (18, "#2563EB"), (26, "#1D4ED8")):
        p.setPen(QPen(QColor(cor), 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(66 - raio, 34 - raio, raio * 2, raio * 2), -45 * 16, 90 * 16)


def _desenhar_voz(p: QPainter) -> None:
    """Microfone com ondas sonoras."""
    # Capsula do microfone
    p.setPen(QPen(QColor("#1E293B"), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#FEF3C7"))
    p.drawRoundedRect(QRectF(38, 16, 24, 38), 12, 12)

    # Grelha do microfone
    p.setPen(QPen(QColor("#D97706"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(44, 28), QPointF(56, 28))
    p.drawLine(QPointF(44, 36), QPointF(56, 36))

    # Suporte curvo e base
    p.setPen(QPen(QColor("#1E293B"), 3.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRectF(28, 30, 44, 36), 180 * 16, 180 * 16)
    p.drawLine(QPointF(50, 66), QPointF(50, 82))
    p.drawLine(QPointF(36, 82), QPointF(64, 82))

    # Ondas sonoras laterais
    p.setPen(QPen(QColor("#F59E0B"), 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawArc(QRectF(64, 26, 18, 28), -50 * 16, 100 * 16)
    p.drawArc(QRectF(18, 26, 18, 28), 130 * 16, 100 * 16)


def _estrela_4(p: QPainter, cx: float, cy: float, r_ext: float, r_int: float, cor: str) -> None:
    pontos = []
    for i in range(8):
        ang = math.pi * i / 4.0
        r = r_ext if i % 2 == 0 else r_int
        pontos.append(QPointF(cx + r * math.cos(ang), cy + r * math.sin(ang)))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(cor))
    p.drawPolygon(QPolygonF(pontos))


def _desenhar_ia(p: QPainter) -> None:
    """Mini teclado com brilhos de inteligencia artificial."""
    # Teclado estilizado na metade inferior
    p.setPen(QPen(QColor("#1E293B"), 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#F8FAFC"))
    p.drawRoundedRect(QRectF(12, 46, 76, 40), 8, 8)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#8B5CF6"))
    for col in range(5):
        p.drawRoundedRect(QRectF(19 + col * 12.6, 54, 9.2, 7.5), 2, 2)
    p.setBrush(QColor("#C4B5FD"))
    p.drawRoundedRect(QRectF(26, 68, 48, 8), 3, 3)

    # Estrelas brilhantes (IA) no topo
    _estrela_4(p, 50, 26, 17, 5.5, "#7C3AED")
    _estrela_4(p, 26, 28, 9.5, 3.2, "#F59E0B")
    _estrela_4(p, 74, 24, 10.5, 3.5, "#EC4899")


def _desenhar_sugestoes(p: QPainter) -> None:
    """Pilulas de sugestao de palavras acima de uma barra de teclado."""
    # Balao principal com tres linhas/pilulas de sugestao
    p.setPen(QPen(QColor("#1E293B"), 3.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#F0FDFA"))
    p.drawRoundedRect(QRectF(12, 16, 76, 40), 10, 10)

    # Tres pilulas de palavras sugeridas
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#0D9488"))
    p.drawRoundedRect(QRectF(18, 25, 20, 10), 5, 5)
    p.setBrush(QColor("#14B8A6"))
    p.drawRoundedRect(QRectF(42, 25, 20, 10), 5, 5)
    p.setBrush(QColor("#5EEAD4"))
    p.drawRoundedRect(QRectF(66, 25, 16, 10), 5, 5)
    p.setBrush(QColor("#99F6E4"))
    p.drawRoundedRect(QRectF(26, 40, 48, 8), 4, 4)

    # Teclas sugeridas em baixo
    p.setPen(QPen(QColor("#1E293B"), 3.2))
    p.setBrush(QColor("#FFFFFF"))
    for i in range(3):
        p.drawRoundedRect(QRectF(16 + i * 24, 65, 20, 18), 5, 5)


def _desenhar_touchpad(p: QPainter) -> None:
    """Superficie de touchpad com zonas de clique e cursor."""
    p.setPen(QPen(QColor("#1E293B"), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#F8FAFC"))
    p.drawRoundedRect(QRectF(12, 14, 76, 72), 10, 10)

    # Linha divisoria dos botoes inferiores
    p.setPen(QPen(QColor("#94A3B8"), 2.8))
    p.drawLine(QPointF(14, 64), QPointF(86, 64))
    p.drawLine(QPointF(50, 64), QPointF(50, 84))

    # Anel de toque suave
    p.setPen(QPen(QColor("#38BDF8"), 2.8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(42, 36), 12, 12)

    # Seta de cursor
    seta = QPolygonF([
        QPointF(42, 34),
        QPointF(42, 56),
        QPointF(49, 50),
        QPointF(54, 58),
        QPointF(59, 55),
        QPointF(54, 47),
        QPointF(62, 47),
    ])
    p.setPen(QPen(QColor("#1E293B"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#0284C7"))
    p.drawPolygon(seta)


def _desenhar_supervisao(p: QPainter) -> None:
    """Escudo protetor com cadeado ao centro."""
    escudo = QPainterPath()
    escudo.moveTo(50, 12)
    escudo.lineTo(82, 24)
    escudo.lineTo(82, 50)
    escudo.cubicTo(82, 70, 66, 82, 50, 88)
    escudo.cubicTo(34, 82, 18, 70, 18, 50)
    escudo.lineTo(18, 24)
    escudo.closeSubpath()

    p.setPen(QPen(QColor("#1E293B"), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(QColor("#E0E7FF"))
    p.drawPath(escudo)

    # Arco do cadeado
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor("#312E81"), 4.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawArc(QRectF(40, 32, 20, 22), 0, 180 * 16)

    # Corpo do cadeado
    p.setPen(QPen(QColor("#1E293B"), 3.0))
    p.setBrush(QColor("#FBBF24"))
    p.drawRoundedRect(QRectF(36, 44, 28, 22), 5, 5)

    # Fechadura
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#1E293B"))
    p.drawEllipse(QPointF(50, 53), 3.2, 3.2)
    p.drawRoundedRect(QRectF(48.3, 54, 3.4, 6.5), 1.5, 1.5)


def _desenhar_opcoes(p: QPainter) -> None:
    """Icone azul circular de definicoes/reguladores (sliders)."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#2563EB"))
    p.drawEllipse(QPointF(50, 50), 44, 44)

    p.setPen(QPen(QColor("#FFFFFF"), 5.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for y, x_bola in ((33, 38), (50, 62), (67, 44)):
        p.drawLine(QPointF(24, y), QPointF(76, y))
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(x_bola, y), 6.5, 6.5)
