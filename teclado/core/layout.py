"""Layouts de teclado: ficheiros *.kblayout.json, validados antes de usar.

Formato:
{
  "nome": "Vogais",
  "idioma": "pt-PT",
  "linhas": [
    [ {"rotulo": "a", "acao": {"tipo": "texto", "valor": "a"}, "largura": 2} ],
    [ {"rotulo": "Apagar", "acao": {"tipo": "tecla", "valor": "backspace"}} ]
  ]
}
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from teclado.core.acentos import ACENTOS
from teclado.core.comandos import ID_RE as ID_COMANDO
from teclado.core.saida import ACOES, TECLAS_ESPECIAIS

EXTENSAO = ".kblayout.json"
# "texto": escreve caracteres; "tecla": tecla especial (ver TECLAS_ESPECIAIS);
# "modificador": altera o comportamento da proxima tecla (ex.: shift).
TIPOS_ACAO = frozenset({"texto", "tecla", "modificador", "acento", "multitoque", "navegar", "acao", "comando"})
# "navegar": valor = nome do teclado de destino (ou NAVEGAR_ANTERIOR).
# "acao": acao de edicao (ver ACOES em teclado/core/saida).
NAVEGAR_ANTERIOR = "__anterior__"
MAX_NOME_TECLADO = 40
MAX_ROTULO_ATALHO = 20
MODIFICADORES = frozenset({"shift", "ctrl"})
# Toque repetido: as letras da tecla, por ordem (ex.: "abc").
MULTITOQUE_MAX = 12
MAX_TECLAS = 80
MAX_TEXTO = 20
MAX_ROTULO = 30  # o que aparece na tecla pode ser mais longo do que o valor da acao

log = logging.getLogger(__name__)


class LayoutInvalido(ValueError):
    """O ficheiro ou os dados nao respeitam o formato de layout."""


@dataclass(frozen=True)
class Acao:
    tipo: str
    valor: str


@dataclass(frozen=True)
class Tecla:
    rotulo: str
    acao: Acao
    largura: float = 1.0


@dataclass(frozen=True)
class Layout:
    nome: str
    idioma: str
    linhas: tuple[tuple[Tecla, ...], ...]
    # Rotulo da tecla que leva a este teclado noutros teclados (None = nao disponibilizado).
    atalho: str | None = None

    @property
    def total_teclas(self) -> int:
        return sum(len(linha) for linha in self.linhas)


def _texto(dados: dict, campo: str, maximo: int, contexto: str) -> str:
    valor = dados.get(campo)
    if not isinstance(valor, str) or not valor.strip() or len(valor) > maximo:
        raise LayoutInvalido(f"{contexto}: '{campo}' deve ser texto com 1 a {maximo} caracteres.")
    return valor


def _tecla(dados: object, contexto: str) -> Tecla:
    if not isinstance(dados, dict):
        raise LayoutInvalido(f"{contexto}: a tecla deve ser um objeto.")
    rotulo = _texto(dados, "rotulo", MAX_ROTULO, contexto)

    acao_dados = dados.get("acao")
    if not isinstance(acao_dados, dict):
        raise LayoutInvalido(f"{contexto}: falta 'acao'.")
    tipo = acao_dados.get("tipo")
    if tipo not in TIPOS_ACAO:
        raise LayoutInvalido(f"{contexto}: tipo de acao invalido ({tipo!r}).")
    limite_valor = MAX_NOME_TECLADO if tipo in ("navegar", "comando") else MAX_TEXTO
    valor = _texto(acao_dados, "valor", limite_valor, contexto)
    if tipo == "tecla" and valor not in TECLAS_ESPECIAIS:
        raise LayoutInvalido(f"{contexto}: tecla especial desconhecida ({valor!r}).")
    if tipo == "modificador" and valor not in MODIFICADORES:
        raise LayoutInvalido(f"{contexto}: modificador desconhecido ({valor!r}).")
    if tipo == "acento" and valor not in ACENTOS:
        raise LayoutInvalido(f"{contexto}: acento desconhecido ({valor!r}).")
    if tipo == "comando" and not ID_COMANDO.fullmatch(valor):
        raise LayoutInvalido(f"{contexto}: identificador de comando invalido ({valor!r}).")
    if tipo == "acao" and valor not in ACOES:
        raise LayoutInvalido(f"{contexto}: ação desconhecida ({valor!r}).")
    if tipo == "multitoque" and not 2 <= len(valor) <= MULTITOQUE_MAX:
        raise LayoutInvalido(
            f"{contexto}: toque repetido deve ter entre 2 e {MULTITOQUE_MAX} caracteres."
        )

    largura = dados.get("largura", 1)
    if isinstance(largura, bool) or not isinstance(largura, (int, float)) or not 0.5 <= largura <= 6:
        raise LayoutInvalido(f"{contexto}: 'largura' deve estar entre 0.5 e 6.")

    return Tecla(rotulo=rotulo, acao=Acao(tipo, valor), largura=float(largura))


def validar_tecla(dados: object, contexto: str = "Tecla") -> Tecla:
    """Valida uma tecla isolada (usado pelo editor de layouts)."""
    return _tecla(dados, contexto)


def _atalho(dados: object) -> str | None:
    if dados is None:
        return None
    if not isinstance(dados, dict):
        raise LayoutInvalido("'atalho' deve ser um objeto com 'rotulo'.")
    return _texto(dados, "rotulo", MAX_ROTULO_ATALHO, "Atalho")


def validar_layout(dados: object) -> Layout:
    if not isinstance(dados, dict):
        raise LayoutInvalido("O layout deve ser um objeto JSON.")
    nome = _texto(dados, "nome", 40, "Layout")
    idioma = _texto(dados, "idioma", 16, "Layout")

    linhas_dados = dados.get("linhas")
    if not isinstance(linhas_dados, list) or not linhas_dados:
        raise LayoutInvalido("Layout: 'linhas' deve ser uma lista não vazia.")

    linhas = []
    for i, linha_dados in enumerate(linhas_dados, start=1):
        if not isinstance(linha_dados, list) or not linha_dados:
            raise LayoutInvalido(f"Linha {i}: deve ser uma lista não vazia de teclas.")
        linhas.append(tuple(_tecla(t, f"Linha {i}, tecla {j}") for j, t in enumerate(linha_dados, 1)))

    layout = Layout(nome=nome, idioma=idioma, linhas=tuple(linhas), atalho=_atalho(dados.get("atalho")))
    if layout.total_teclas > MAX_TECLAS:
        raise LayoutInvalido(f"Layout '{nome}': máximo de {MAX_TECLAS} teclas.")
    return layout


def carregar_layout(caminho: Path) -> Layout:
    caminho = Path(caminho)
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise LayoutInvalido(f"{caminho.name}: {erro}") from erro
    return validar_layout(dados)


def descobrir_layouts(pastas: Iterable[Path]) -> dict[str, Layout]:
    """Lê todos os layouts válidos das pastas indicadas. Os inválidos são ignorados com aviso."""
    encontrados: dict[str, Layout] = {}
    for pasta in pastas:
        pasta = Path(pasta)
        if not pasta.is_dir():
            continue
        for ficheiro in sorted(pasta.glob(f"*{EXTENSAO}")):
            try:
                layout = carregar_layout(ficheiro)
            except LayoutInvalido as erro:
                log.warning("Layout ignorado: %s", erro)
                continue
            encontrados[layout.nome] = layout
    return encontrados
