"""Teclado do Quadro Interativo, gerado a partir do catálogo de ações do Quadro (quadro/acoes.py).

Não é um ficheiro de layout do utilizador: ativa-se sozinho quando o Quadro é a janela em foco
(ver aplicacao.entrar_quadro) e cada tecla envia o identificador da ação ao Quadro.

As teclas mostram ícones (desenhados pelo Quadro e recebidos com o catálogo). O texto fica como
dica ao passar o rato, e é o rótulo usado quando um ícone não existe.

Estrutura:
- teclado principal: ferramentas, desfazer/refazer, apagar, menus, e «Teclado» (volta ao teclado do utilizador);
- um teclado por ferramenta com opções (tamanhos, figuras, formas, efeitos, cores), com «Escolher» e «Voltar».
"""

from __future__ import annotations

from teclado.core.layout import NAVEGAR_BASE, Acao, Layout, Tecla

NOME_RAIZ = "Quadro Interativo"
COLUNAS = 5
FERRAMENTAS_COM_OPCOES = ("caneta", "borracha", "borracha_riscos", "carimbo", "magia", "forma", "texto", "cor")
# Ferramentas em que um dedo arrastado desenha (no touchpad). As restantes so movem e clicam.
FERRAMENTAS_DESENHO = ("caneta", "borracha", "borracha_riscos", "carimbo", "magia", "forma", "texto")
FERRAMENTAS = FERRAMENTAS_DESENHO + ("varinha", "balde", "cor")
ICONE_ESCOLHER = "escolher"
ICONE_VOLTAR = "voltar"
ICONE_TECLADO = "teclado"
ROTULOS = {
    "caneta": "Caneta",
    "borracha": "Borracha",
    "borracha_riscos": "Riscos",
    "varinha": "Varinha",
    "balde": "Balde",
    "carimbo": "Carimbos",
    "magia": "Magia",
    "forma": "Formas",
    "texto": "Texto",
    "cor": "Cor",
    "desfazer": "Desfazer",
    "refazer": "Refazer",
    "apagar_selecao": "Apagar",
    "ocultar_menu": "Ocultar",
    "minimizar": "Minimizar",
    "importar_imagem": "Imagem",
    "pesquisar_imagens": "Pesquisar",
    "jogos": "Jogos",
    "correio": "Correio",
    "definicoes": "Definições",
    "escolher": "Escolher",
    "voltar": "Voltar",
    "teclado": "Teclado",
}


def nome_subteclado(ferramenta: str) -> str:
    return f"{NOME_RAIZ} · {ROTULOS[ferramenta]}"


def _rotulo_opcao(acao: dict) -> str:
    identificador = acao["id"]
    if ".tamanho." in identificador:
        return identificador.rsplit(".", 1)[1]
    nome = acao.get("nome")
    return nome if isinstance(nome, str) and nome else identificador


def _icone(acao: dict | None) -> str | None:
    if acao is None or not isinstance(acao.get("icone"), str):
        return None
    return acao["icone"]


def _tecla(rotulo: str, tipo: str, valor: str, icone: str | None) -> Tecla:
    return Tecla(rotulo=rotulo, acao=Acao(tipo, valor), icone=icone)


def _linhas(teclas: list[Tecla]) -> tuple[tuple[Tecla, ...], ...]:
    return tuple(tuple(teclas[i : i + COLUNAS]) for i in range(0, len(teclas), COLUNAS))


def construir_layouts(catalogo: dict, idioma: str, estado: dict | None = None) -> dict[str, Layout]:
    """Devolve os teclados do Quadro (principal e opcionais) a partir do catálogo recebido do Quadro.

    Com `estado` (ver acoes.estado no Quadro), as teclas que nao estao disponiveis neste momento
    (ex.: desfazer sem nada para desfazer) nao aparecem, para o teclado nao ficar cheio de teclas inuteis."""
    acoes = {a["id"]: a for a in catalogo.get("acoes", []) if isinstance(a, dict) and isinstance(a.get("id"), str)}
    filhos: dict[str, list[dict]] = {}
    for acao in acoes.values():
        if isinstance(acao.get("pai"), str):
            filhos.setdefault(acao["pai"], []).append(acao)

    layouts: dict[str, Layout] = {}
    subteclados: set[str] = set()
    for ferramenta in FERRAMENTAS_COM_OPCOES:
        if ferramenta not in acoes:
            continue
        teclas: list[Tecla] = []
        if ferramenta != "cor":
            teclas.append(_tecla(ROTULOS["escolher"], "quadro", ferramenta, _icone(acoes[ferramenta])))
        for opcao in filhos.get(ferramenta, []):
            teclas.append(_tecla(_rotulo_opcao(opcao), "quadro", opcao["id"], _icone(opcao)))
        teclas.append(_tecla(ROTULOS["voltar"], "navegar", NOME_RAIZ, ICONE_VOLTAR))
        nome = nome_subteclado(ferramenta)
        layouts[nome] = Layout(nome=nome, idioma=idioma, linhas=_linhas(teclas))
        subteclados.add(ferramenta)

    principal: list[Tecla] = []
    for identificador in ("caneta", "borracha", "borracha_riscos", "varinha", "balde",
                          "carimbo", "magia", "forma", "texto", "cor",
                          "desfazer", "refazer", "apagar_selecao",
                          "jogos", "correio", "definicoes", "importar_imagem", "pesquisar_imagens", "minimizar"):
        if identificador not in acoes:
            continue
        if estado is not None and not estado.get(identificador, {}).get("disponivel", True):
            continue
        if identificador in subteclados:
            principal.append(_tecla(ROTULOS[identificador], "navegar", nome_subteclado(identificador), _icone(acoes[identificador])))
        else:
            principal.append(_tecla(ROTULOS[identificador], "quadro", identificador, _icone(acoes[identificador])))
    principal.append(_tecla(ROTULOS["teclado"], "navegar", NAVEGAR_BASE, ICONE_TECLADO))
    layouts[NOME_RAIZ] = Layout(nome=NOME_RAIZ, idioma=idioma, linhas=_linhas(principal))
    return layouts
