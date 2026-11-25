"""Gera o lexico base de um idioma (ferramenta de desenvolvimento, nao corre no teclado).

Fontes:
  - Lista de frequencia FrequencyWords (CC-BY-SA-4.0), ficheiro "palavra contagem".
  - Dicionario Hunspell pt_PT (GPL/LGPL/MPL), usado so como filtro de validade.

Regras:
  - So entram formas em minusculas que o Hunspell aceita (remove erros de OCR,
    pt pre-AO90 e nomes proprios sem entrada no dicionario).
  - Nao separa pt-PT de pt-BR: o Hunspell pt_PT aceita formas como "voce" e "voces".

Uso (a partir da raiz do projeto):
  py tools\\gerar_lexico.py --freq tools\\fontes\\pt_50k.txt ^
      --hunspell tools\\fontes\\pt_PT --saida data\\languages\\pt-PT\\lexico.tsv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from spylls.hunspell import Dictionary


def gerar(freq: Path, hunspell: Path, saida: Path, limite: int) -> tuple[int, int]:
    dicionario = Dictionary.from_files(str(hunspell))
    vistas: set[str] = set()
    aceites: list[tuple[str, int]] = []
    total = 0

    for linha in freq.read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if len(partes) != 2 or not partes[1].isdigit():
            continue
        total += 1
        palavra = partes[0].lower()
        if palavra in vistas or not palavra.isalpha():
            continue
        vistas.add(palavra)
        if not dicionario.lookup(palavra):
            continue
        aceites.append((palavra, int(partes[1])))
        if len(aceites) >= limite:
            break

    aceites.sort(key=lambda par: -par[1])
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8", newline="\n") as ficheiro:
        for palavra, contagem in aceites:
            ficheiro.write(f"{palavra}\t{contagem}\n")
    return total, len(aceites)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--freq", type=Path, required=True)
    parser.add_argument("--hunspell", type=Path, required=True, help="Caminho sem extensao (ex.: pt_PT)")
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--limite", type=int, default=50000)
    args = parser.parse_args()
    total, aceites = gerar(args.freq, args.hunspell, args.saida, args.limite)
    print(f"Linhas lidas: {total} | palavras aceites: {aceites} | ficheiro: {args.saida}")


if __name__ == "__main__":
    main()
