"""Comandos de voz dentro do ditado: "enter", "muda de linha", "ponto final", etc.

Um comando so e reconhecido quando as palavras correspondem exatamente. Os comandos
ambiguos ("apagar", "espaco", "ponto") so valem quando a frase ditada e so o comando,
para que uma frase como "vou apagar a luz" continue a ser texto.
"""

from __future__ import annotations

import unicodedata

# (palavras normalizadas, acao, so_isolado)
# acao: ("tecla", nome) | ("acao", nome) | ("simbolo", caracter)
COMANDOS: tuple[tuple[tuple[str, ...], tuple[str, str], bool], ...] = (
    (("muda", "de", "linha"), ("tecla", "enter"), False),
    (("nova", "linha"), ("tecla", "enter"), False),
    (("enter",), ("tecla", "enter"), False),
    (("apagar",), ("tecla", "backspace"), True),
    (("apaga",), ("tecla", "backspace"), True),
    (("apaga", "palavra"), ("acao", "apagar_palavra"), True),
    (("apaga", "linha"), ("acao", "apagar_linha"), True),
    (("seleciona", "palavra"), ("acao", "selecionar_palavra"), True),
    (("seleciona", "linha"), ("acao", "selecionar_linha"), True),
    (("ler", "selecao"), ("acao", "ler_selecao"), True),
    (("espaco",), ("tecla", "espaco"), True),
    (("ponto", "final"), ("simbolo", "."), False),
    (("ponto", "de", "interrogacao"), ("simbolo", "?"), False),
    (("ponto", "de", "exclamacao"), ("simbolo", "!"), False),
    (("virgula",), ("simbolo", ","), False),
    (("ponto",), ("simbolo", "."), True),
)
_ORDENADOS = tuple(sorted(COMANDOS, key=lambda c: -len(c[0])))


def normalizar(palavra: str) -> str:
    """minusculas, sem acentos e sem pontuacao: 'Interrogação,' -> 'interrogacao'."""
    decomposta = unicodedata.normalize("NFD", palavra.lower())
    sem_acentos = "".join(c for c in decomposta if unicodedata.category(c) != "Mn")
    return "".join(c for c in sem_acentos if c.isalnum())


def segmentar(texto: str) -> list[tuple[str, str]]:
    """Divide o texto ditado em ("texto", s), ("tecla", n), ("acao", n) e ("simbolo", c)."""
    tokens = texto.split()
    norm = [normalizar(t) for t in tokens]
    total_validos = sum(1 for n in norm if n)
    saida: list[tuple[str, str]] = []
    buffer: list[str] = []

    def fechar(antes_de_comando: bool) -> None:
        if not buffer:
            return
        texto_bloco = " ".join(buffer)
        buffer.clear()
        # Pontuacao colada ao texto anterior; depois de pontuacao, o texto segue com espaco.
        if saida and saida[-1][0] == "simbolo":
            texto_bloco = " " + texto_bloco
        if antes_de_comando:
            texto_bloco = texto_bloco.rstrip()
        if texto_bloco:
            saida.append(("texto", texto_bloco))

    idx = 0
    while idx < len(tokens):
        validos_a_frente = [j for j in range(idx, len(tokens)) if norm[j]]
        encontrado = False
        for padrao, acao, so_isolado in _ORDENADOS:
            k = len(padrao)
            if len(validos_a_frente) < k:
                continue
            if not all(norm[validos_a_frente[q]] == padrao[q] for q in range(k)):
                continue
            if so_isolado and total_validos != k:
                continue
            fechar(antes_de_comando=True)
            saida.append(acao)
            idx = validos_a_frente[k - 1] + 1
            encontrado = True
            break
        if not encontrado:
            buffer.append(tokens[idx])
            idx += 1
    fechar(antes_de_comando=False)
    # O ditado termina com espaco: se o texto final o tinha, mantem-no.
    if texto.endswith((" ", "\t")) and saida and saida[-1][0] == "texto":
        saida[-1] = ("texto", saida[-1][1] + " ")
    return saida
