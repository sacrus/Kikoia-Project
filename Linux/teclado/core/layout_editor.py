"""Edicao de layouts como dicionarios simples (o modelo que a interface altera).

Um modelo tem o mesmo formato do ficheiro JSON, mas pode estar incompleto
(linhas vazias, sem teclas). So e validado ao guardar.
"""

from __future__ import annotations

import copy
import json
import os
import re
import unicodedata
from dataclasses import replace
from pathlib import Path

from .layout import EXTENSAO, Layout, LayoutInvalido, Tecla, carregar_layout, validar_layout


def tecla_dict(rotulo: str, tipo: str, valor: str, largura: float = 1.0) -> dict:
    return {"rotulo": rotulo, "acao": {"tipo": tipo, "valor": valor}, "largura": largura}


def modelo_vazio(nome: str, idioma: str = "pt-PT") -> dict:
    return {"nome": nome, "idioma": idioma, "linhas": []}


def _dict_de_tecla(tecla: Tecla) -> dict:
    dados = tecla_dict(tecla.rotulo, tecla.acao.tipo, tecla.acao.valor, tecla.largura)
    if tecla.shift is not None:
        dados["shift"] = tecla.shift
    if tecla.idiomas is not None:
        dados["idiomas"] = sorted(tecla.idiomas)
    return dados


def modelo_de(layout: Layout) -> dict:
    """Copia editavel de um layout existente."""
    modelo = {
        "nome": layout.nome,
        "idioma": layout.idioma,
        "linhas": [[_dict_de_tecla(t) for t in linha] for linha in layout.linhas],
    }
    if layout.atalho is not None:
        modelo["atalho"] = {"rotulo": layout.atalho}
    return modelo


def adicionar_linha(modelo: dict) -> int:
    modelo["linhas"].append([])
    return len(modelo["linhas"]) - 1


def remover_linha(modelo: dict, linha: int) -> None:
    del modelo["linhas"][linha]


def adicionar_tecla(modelo: dict, linha: int | None, tecla: dict) -> tuple[int, int]:
    """Acrescenta a tecla no fim da linha indicada (ou na ultima, se nao houver indicacao).

    Devolve (linha, posicao) onde a tecla ficou.
    """
    if not modelo["linhas"]:
        adicionar_linha(modelo)
    if linha is None:
        linha = len(modelo["linhas"]) - 1
    modelo["linhas"][linha].append(tecla)
    return linha, len(modelo["linhas"][linha]) - 1


def remover_tecla(modelo: dict, linha: int, posicao: int) -> None:
    del modelo["linhas"][linha][posicao]


def mover_tecla(modelo: dict, linha: int, posicao: int, direcao: int) -> int:
    """Troca a tecla com a vizinha da mesma linha (direcao -1 ou +1). Devolve a nova posicao."""
    fila = modelo["linhas"][linha]
    destino = posicao + direcao
    if not 0 <= destino < len(fila):
        return posicao
    fila[posicao], fila[destino] = fila[destino], fila[posicao]
    return destino


def _limpo(modelo: dict) -> dict:
    copia = copy.deepcopy(modelo)
    copia["linhas"] = [linha for linha in copia.get("linhas", []) if linha]
    return copia


def validar_modelo(modelo: dict) -> Layout:
    """Valida o modelo como layout (ignora linhas vazias). Lanca LayoutInvalido."""
    return validar_layout(_limpo(modelo))


def nome_de_ficheiro(nome: str) -> str:
    base = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii").lower()
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    if not base:
        raise LayoutInvalido("O nome do teclado precisa de pelo menos uma letra ou número.")
    return base


def guardar_layout_em_pasta(modelo: dict, pasta: Path) -> Layout:
    """Valida e grava o modelo como ficheiro .kblayout.json na pasta do utilizador."""
    limpo = _limpo(modelo)
    layout = validar_layout(limpo)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / (nome_de_ficheiro(layout.nome) + EXTENSAO)
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(json.dumps(limpo, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, destino)
    return layout


def gravar_modelo_em_ficheiro(modelo: dict, destino: Path) -> Layout:
    """Valida e grava o modelo no ficheiro indicado (mantem o nome do ficheiro)."""
    limpo = _limpo(modelo)
    layout = validar_layout(limpo)
    destino = Path(destino)
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(json.dumps(limpo, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, destino)
    return layout


def rotular_comandos(layout: Layout, comandos: dict) -> Layout:
    """Layout com o nome atual de cada tecla de comando: o nome vem do comando, nao da tecla.

    Assim, renomear um comando atualiza todas as teclas que o usam, sem reescrever os layouts.
    Um comando que ja nao existe mantem o nome guardado na tecla.
    """
    def atual(tecla: Tecla) -> Tecla:
        if tecla.acao.tipo != "comando":
            return tecla
        comando = comandos.get(tecla.acao.valor)
        if comando is None or comando.rotulo == tecla.rotulo:
            return tecla
        return replace(tecla, rotulo=comando.rotulo)

    return replace(layout, linhas=tuple(tuple(atual(tecla) for tecla in linha) for linha in layout.linhas))


def usa_comando(layout: Layout, id_: str) -> bool:
    return any(
        tecla.acao.tipo == "comando" and tecla.acao.valor == id_
        for linha in layout.linhas for tecla in linha
    )


def remover_teclas_de_comando(modelo: dict, id_: str) -> int:
    """Tira do modelo as teclas deste comando. Devolve quantas foram removidas."""
    removidas = 0
    for linha in modelo["linhas"]:
        antes = len(linha)
        linha[:] = [t for t in linha if not (t["acao"]["tipo"] == "comando" and t["acao"]["valor"] == id_)]
        removidas += antes - len(linha)
    return removidas


def apagar_layout_em_pasta(nome: str, pasta: Path) -> bool:
    """Apaga o teclado com esse nome, se existir nesta pasta. Modelos do projeto nao sao tocados."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        return False
    for ficheiro in pasta.glob(f"*{EXTENSAO}"):
        try:
            layout = carregar_layout(ficheiro)
        except LayoutInvalido:
            continue
        if layout.nome == nome:
            ficheiro.unlink()
            return True
    return False
