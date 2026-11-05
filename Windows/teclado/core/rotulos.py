"""Rotulos das teclas pre-criadas (Espaco, Apagar, Home...), traduzidos para o idioma atual.

O layout guarda o nome na lingua em que a tecla foi criada. Um rotulo que seja o nome padrao
em qualquer dos idiomas e trocado pela traducao atual; um nome dado pelo utilizador fica igual.
"""

from __future__ import annotations

import json
from functools import lru_cache

from teclado.core.idiomas import t
from teclado.core.paths import DADOS_PROJETO

# (tipo, valor) da acao -> chave de traducao do nome padrao.
CHAVES_TECLAS: dict[tuple[str, str], str] = {
    ("tecla", "backspace"): "tecla.apagar",
    ("tecla", "enter"): "tecla.enter",
    ("tecla", "espaco"): "tecla.espaco",
    ("modificador", "shift"): "tecla.shift",
    ("tecla", "home"): "tecla.home",
    ("tecla", "end"): "tecla.end",
    ("tecla", "pgup"): "tecla.pgup",
    ("tecla", "pgdn"): "tecla.pgdn",
    ("tecla", "prtsc"): "tecla.prtsc",
    ("tecla", "insert"): "tecla.insert",
    ("tecla", "capslock"): "tecla.capslock",
    ("tecla", "tab"): "tecla.tab",
    ("tecla", "esc"): "tecla.esc",
    ("tecla", "delete"): "tecla.delete",
}


@lru_cache(maxsize=None)
def _nomes_padrao(chave: str) -> frozenset[str]:
    """Nome dessa tecla em todos os idiomas disponiveis."""
    nomes = set()
    for ficheiro in (DADOS_PROJETO / "idiomas").glob("*.json"):
        dados = json.loads(ficheiro.read_text(encoding="utf-8"))
        if chave in dados:
            nomes.add(dados[chave])
    return frozenset(nomes)


def rotulo_tecla(tipo: str, valor: str, rotulo: str) -> str:
    """Rotulo a mostrar para uma tecla: o nome traduzido se for um nome padrao, senao o proprio rotulo."""
    chave = CHAVES_TECLAS.get((tipo, valor))
    if chave is not None and rotulo in _nomes_padrao(chave):
        return t(chave)
    return rotulo
