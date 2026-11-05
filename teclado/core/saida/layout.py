"""Layout de teclado configurado no sistema (Linux).

Pergunta ao ambiente grafico (GNOME) e, se nao houver resposta, ao sistema (localectl
ou /etc/default/keyboard). Assim o teclado escreve as teclas que o utilizador ve,
seja qual for o layout e a lingua da instalacao.
"""

from __future__ import annotations

import ast
import logging
import re
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

PADRAO = ("us", "", "")  # layout, variante, opcoes XKB


def _executar(*argumentos: str) -> str | None:
    try:
        resultado = subprocess.run(argumentos, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return resultado.stdout if resultado.returncode == 0 else None


def _separar_xkb(identificador: str) -> tuple[str, str]:
    """'pt+nodeadkeys' -> ('pt', 'nodeadkeys')."""
    layout, _, variante = identificador.partition("+")
    return layout.strip(), variante.strip()


def _gnome() -> tuple[str, str, str] | None:
    fontes = _executar("gsettings", "get", "org.gnome.desktop.input-sources", "sources")
    if not fontes:
        return None
    try:
        lista = ast.literal_eval(fontes.strip())
    except (ValueError, SyntaxError):
        return None
    indice_atual = 0
    texto_atual = _executar("gsettings", "get", "org.gnome.desktop.input-sources", "current")
    if texto_atual:
        try:
            indice_atual = int(texto_atual.split()[-1])
        except ValueError:
            pass
    xkb = [fonte for fonte in lista if isinstance(fonte, tuple) and len(fonte) == 2 and fonte[0] == "xkb"]
    if not xkb:
        return None
    escolhida = lista[indice_atual] if indice_atual < len(lista) and lista[indice_atual] in xkb else xkb[0]
    layout, variante = _separar_xkb(escolhida[1])
    opcoes = ""
    texto_opcoes = _executar("gsettings", "get", "org.gnome.desktop.input-sources", "xkb-options")
    if texto_opcoes:
        try:
            opcoes = ",".join(ast.literal_eval(texto_opcoes.strip()))
        except (ValueError, SyntaxError):
            opcoes = ""
    return layout, variante, opcoes


def _localectl() -> tuple[str, str, str] | None:
    estado = _executar("localectl", "status")
    if not estado:
        return None
    campos = {}
    for linha in estado.splitlines():
        chave, _, valor = linha.partition(":")
        campos[chave.strip()] = valor.strip()
    layout = campos.get("X11 Layout", "")
    if not layout:
        return None
    return layout, campos.get("X11 Variant", ""), campos.get("X11 Options", "")


def _etc_default_keyboard() -> tuple[str, str, str] | None:
    try:
        texto = Path("/etc/default/keyboard").read_text(encoding="utf-8")
    except OSError:
        return None

    def valor(nome: str) -> str:
        encontrado = re.search(rf'^{nome}="?([^"\n]*)"?', texto, re.MULTILINE)
        return encontrado.group(1).strip() if encontrado else ""

    layout = valor("XKBLAYOUT").split(",")[0]
    if not layout:
        return None
    return layout, valor("XKBVARIANT").split(",")[0], valor("XKBOPTIONS")


def layout_do_sistema() -> tuple[str, str, str]:
    """(layout, variante, opcoes) XKB do teclado que o sistema esta a usar."""
    for origem in (_gnome, _localectl, _etc_default_keyboard):
        resultado = origem()
        if resultado:
            log.info("Layout do teclado: %s %s %s (%s)", *resultado, origem.__name__)
            return resultado
    log.warning("Layout do teclado nao encontrado; a usar %s", PADRAO[0])
    return PADRAO
