"""Palavra em curso no teclado fisico (fase 7).

Guarda apenas a palavra que esta a ser escrita, nunca o historico de teclas.
Quando a palavra termina (espaco, pontuacao, Enter, Tab), devolve-a e esquece-a.

Privacidade:
- Nao ha registo de teclas: so o fragmento da palavra atual existe em memoria.
- Uma palavra muito longa e descartada (provavelmente nao e texto normal).
- Teclas de atalho (Ctrl, Alt, Win) e de navegacao reiniciam a palavra.
"""

from __future__ import annotations

MAX_PALAVRA = 40


class ConstrutorPalavra:
    def __init__(self) -> None:
        self._palavra = ""

    @property
    def prefixo(self) -> str:
        return self._palavra

    def letra(self, caractere: str) -> None:
        if len(self._palavra) >= MAX_PALAVRA:
            self._palavra = ""  # demasiado longa para ser palavra: descarta
        self._palavra += caractere

    def apagar(self) -> None:
        self._palavra = self._palavra[:-1]

    def reiniciar(self) -> None:
        self._palavra = ""

    def separador(self) -> str | None:
        """Termina a palavra. Devolve-a (ou None se estava vazia) e esquece-a."""
        palavra = self._palavra
        self._palavra = ""
        return palavra or None
