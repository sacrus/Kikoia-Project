"""Injecao de teclas noutras aplicacoes. Uma implementacao por sistema operativo."""

from __future__ import annotations

import logging
import sys
from typing import Protocol

log = logging.getLogger(__name__)

# Nomes de teclas especiais independentes do sistema operativo.
TECLAS_ESPECIAIS = frozenset(
    {"backspace", "tab", "enter", "esc", "espaco", "delete",
     "seta_esq", "seta_dir", "seta_cima", "seta_baixo",
     "home", "end", "pgup", "pgdn", "prtsc", "insert", "capslock"}
)

# Acoes de edicao: cada uma e uma sequencia de atalhos de teclado.
# Formato de cada passo: "tecla" ou "modificador+...+tecla" (nomes em MAPA_TECLAS_ATALHO).
ACOES_EDICAO: dict[str, tuple[str, ...]] = {
    "apagar_palavra": ("ctrl+backspace",),
    "apagar_linha": ("home", "shift+end", "backspace"),
    "selecionar_palavra": ("ctrl+left", "ctrl+shift+right"),
    "selecionar_linha": ("home", "shift+end"),
}
# Acoes sobre a janela da aplicacao em foco. Nao sao atalhos: tratadas pelo controlador do ecra.
ACOES_JANELA = frozenset({"minimizar_teclado", "fechar_janela", "minimizar_janela", "maximizar_janela"})
# "ler_selecao" nao e um atalho: copia a seleccao e devolve o texto (ver Saida.ler_selecao).
ACOES = frozenset(ACOES_EDICAO) | {"ler_selecao"} | ACOES_JANELA

# Nomes usados nos atalhos (alem de TECLAS_ESPECIAIS e das letras e digitos).
MAPA_TECLAS_ATALHO = frozenset({"ctrl", "shift", "home", "end", "left", "right", "c"})


class Saida(Protocol):
    def escrever(self, texto: str) -> None:
        """Escreve texto (letras, acentos, simbolos) na aplicacao com foco."""

    def tecla(self, nome: str) -> None:
        """Pressiona e liberta uma tecla especial (ver TECLAS_ESPECIAIS)."""

    def sequencia(self, acoes: list[tuple[str, str]]) -> None:
        """Envia uma lista de ("texto", valor) / ("tecla", nome) em ordem, com pausas seguras."""

    def colar_texto(self, texto: str) -> None:
        """Escreve um bloco de texto de uma vez (ditado), pela area de transferencia."""

    def atalho(self, nome: str) -> None:
        """Executa uma acao de edicao (ver ACOES_EDICAO)."""

    def enviar_atalho(self, passo: str) -> None:
        """Envia uma combinacao, ex.: "ctrl+c" ou "ctrl+home"."""

    def janela_ativa(self, acao: str, excluir: int = 0) -> bool:
        """Fecha, minimiza ou maximiza a janela em foco (ver ACOES_JANELA). Ignora 'excluir'."""

    def ler_selecao(self) -> str:
        """Devolve o texto selecionado na aplicacao com foco ("" se nada estiver selecionado)."""


def criar_saida() -> Saida:
    if sys.platform == "win32":
        from .windows import SaidaWindows

        return SaidaWindows()
    from .nula import SaidaNula

    try:
        from .linux import SaidaLinux

        return SaidaLinux()
    except RuntimeError as erro:
        # Sem permissao para /dev/uinput: a interface funciona, sem escrever noutras apps.
        log.error("Injecao de teclas indisponivel: %s Execute tools/configurar_teclado_linux.sh.", erro)
        return SaidaNula()
