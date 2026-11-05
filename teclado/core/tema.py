"""Temas visuais: cores, tamanho de letra e imagem de fundo (*.kbtheme.json)."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

EXTENSAO = ".kbtheme.json"
CAMPOS_COR = ("cor_fundo", "cor_tecla", "cor_texto", "cor_tecla_premida", "cor_texto_premido")
_HEX = re.compile(r"#[0-9a-fA-F]{6}")

log = logging.getLogger(__name__)


class TemaInvalido(ValueError):
    """Os dados nao respeitam o formato de tema."""


@dataclass(frozen=True)
class Tema:
    nome: str
    cor_fundo: str
    cor_tecla: str
    cor_texto: str
    cor_tecla_premida: str
    cor_texto_premido: str
    tamanho_fonte: int = 22
    imagem_fundo: Path | None = None
    opacidade_imagem: int = 50  # 0 = invisivel, 100 = totalmente visivel


def cor_texto_para(fundo: str) -> str:
    """Preto ou branco, conforme a luminosidade da cor de fundo (contraste)."""
    r, g, b = (int(fundo[i:i + 2], 16) for i in (1, 3, 5))
    luminosidade = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminosidade > 0.5 else "#FFFFFF"


def validar_tema(dados: object, base: Path = Path(".")) -> Tema:
    if not isinstance(dados, dict):
        raise TemaInvalido("O tema deve ser um objeto JSON.")

    nome = dados.get("nome")
    if not isinstance(nome, str) or not nome.strip() or len(nome) > 40:
        raise TemaInvalido("Tema: 'nome' deve ter 1 a 40 caracteres.")

    cores = {}
    for campo in CAMPOS_COR:
        valor = dados.get(campo)
        if not isinstance(valor, str) or not _HEX.fullmatch(valor):
            raise TemaInvalido(f"Tema '{nome}': '{campo}' deve ser uma cor #RRGGBB.")
        cores[campo] = valor

    tamanho = dados.get("tamanho_fonte", 22)
    if isinstance(tamanho, bool) or not isinstance(tamanho, int) or not 10 <= tamanho <= 72:
        raise TemaInvalido(f"Tema '{nome}': 'tamanho_fonte' deve ser um inteiro entre 10 e 72.")

    opacidade = dados.get("opacidade_imagem", 50)
    if isinstance(opacidade, bool) or not isinstance(opacidade, int) or not 0 <= opacidade <= 100:
        raise TemaInvalido(f"Tema '{nome}': 'opacidade_imagem' deve estar entre 0 e 100.")

    imagem = None
    caminho_imagem = dados.get("imagem_fundo")
    if caminho_imagem:
        if not isinstance(caminho_imagem, str):
            raise TemaInvalido(f"Tema '{nome}': 'imagem_fundo' deve ser um caminho.")
        imagem = Path(base) / caminho_imagem
        if not imagem.is_file():
            raise TemaInvalido(f"Tema '{nome}': imagem não encontrada ({caminho_imagem}).")

    return Tema(
        nome=nome.strip(),
        tamanho_fonte=tamanho,
        imagem_fundo=imagem,
        opacidade_imagem=opacidade,
        **cores,
    )


def carregar_tema(caminho: Path) -> Tema:
    caminho = Path(caminho)
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise TemaInvalido(f"{caminho.name}: {erro}") from erro
    return validar_tema(dados, base=caminho.parent)


def tema_para_dicionario(tema: Tema) -> dict:
    return {
        "nome": tema.nome,
        "cor_fundo": tema.cor_fundo,
        "cor_tecla": tema.cor_tecla,
        "cor_texto": tema.cor_texto,
        "cor_tecla_premida": tema.cor_tecla_premida,
        "cor_texto_premido": tema.cor_texto_premido,
        "tamanho_fonte": tema.tamanho_fonte,
        "imagem_fundo": str(tema.imagem_fundo) if tema.imagem_fundo else None,
        "opacidade_imagem": tema.opacidade_imagem,
    }


def guardar_tema(tema: Tema, caminho: Path) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = json.dumps(tema_para_dicionario(tema), ensure_ascii=False, indent=2)
    caminho.write_text(conteudo, encoding="utf-8")


def descobrir_temas(pastas: Iterable[Path]) -> dict[str, Tema]:
    encontrados: dict[str, Tema] = {}
    for pasta in pastas:
        pasta = Path(pasta)
        if not pasta.is_dir():
            continue
        for ficheiro in sorted(pasta.glob(f"*{EXTENSAO}")):
            try:
                tema = carregar_tema(ficheiro)
            except TemaInvalido as erro:
                log.warning("Tema ignorado: %s", erro)
                continue
            encontrados[tema.nome] = tema
    return encontrados
