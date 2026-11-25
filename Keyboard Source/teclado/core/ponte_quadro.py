"""Cliente da ponte do Quadro Interativo: lê o catálogo de ações e executa-as.

O Quadro grava `ponte.json` (porta, token e PID) quando está aberto e recusa pedidos sem o token.
Este módulo só fala com 127.0.0.1. Se o ficheiro não existir, se a porta não responder ou se o token
não for aceite, o Quadro é tratado como não disponível (não se mostra nada no teclado).
"""

from __future__ import annotations

import base64
import json
import os
import socket
import sys
from pathlib import Path

NOME_FICHEIRO = "ponte.json"
TEMPO_LIMITE_S = 2.0
LIMITE_RESPOSTA = 512 * 1024


class QuadroIndisponivel(RuntimeError):
    """O Quadro não está aberto, ou não aceitou o pedido."""


def pasta_quadro(base: Path | None = None) -> Path:
    if base is not None:
        return base
    if sys.platform == "win32":
        raiz = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        raiz = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("XDG_DATA_HOME")
            or str(Path.home() / ".local" / "share")
        )
    return Path(raiz) / "Kikoia" / "Quadro"


def _ler_ficheiro(base: Path | None) -> dict | None:
    try:
        dados = json.loads((pasta_quadro(base) / NOME_FICHEIRO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("porta"), int) or not isinstance(dados.get("token"), str):
        return None
    return dados


def icones_da_resposta(resposta: dict) -> dict[str, bytes]:
    """PNG de cada icone enviado pelo Quadro (chave: nome do icone). Ignora o que nao for valido."""
    recebidos = resposta.get("icones")
    if not isinstance(recebidos, dict):
        return {}
    imagens: dict[str, bytes] = {}
    for nome, dados in recebidos.items():
        if not isinstance(nome, str) or not isinstance(dados, str):
            continue
        try:
            imagens[nome] = base64.b64decode(dados, validate=True)
        except ValueError:
            continue
    return imagens


def coloridos_da_resposta(resposta: dict) -> set[str]:
    """Nomes dos icones que mantem as suas cores (os restantes sao pintados com a cor do tema)."""
    recebidos = resposta.get("coloridos")
    if not isinstance(recebidos, list):
        return set()
    return {nome for nome in recebidos if isinstance(nome, str)}


class ClienteQuadro:
    def __init__(self, base: Path | None = None, tempo_limite: float = TEMPO_LIMITE_S) -> None:
        self._base = base
        self._tempo_limite = tempo_limite

    def pedir(self, pedido: dict) -> dict:
        """Envia um pedido e devolve a resposta. Levanta QuadroIndisponivel se não for possível falar com o Quadro."""
        ficheiro = _ler_ficheiro(self._base)
        if ficheiro is None:
            raise QuadroIndisponivel("ficheiro da ponte em falta")
        try:
            with socket.create_connection(("127.0.0.1", ficheiro["porta"]), timeout=self._tempo_limite) as ligacao:
                mensagem = {"token": ficheiro["token"], **pedido}
                ligacao.sendall((json.dumps(mensagem, ensure_ascii=False) + "\n").encode("utf-8"))
                recebido = bytearray()
                while b"\n" not in recebido:
                    bloco = ligacao.recv(65536)
                    if not bloco:
                        break
                    recebido.extend(bloco)
                    if len(recebido) > LIMITE_RESPOSTA:
                        raise QuadroIndisponivel("resposta demasiado grande")
        except OSError as erro:
            raise QuadroIndisponivel("o Quadro não está a responder") from erro
        try:
            resposta = json.loads(bytes(recebido).split(b"\n", 1)[0].decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as erro:
            raise QuadroIndisponivel("resposta inválida") from erro
        if not isinstance(resposta, dict):
            raise QuadroIndisponivel("resposta inválida")
        return resposta

    def disponivel(self) -> bool:
        try:
            return bool(self.pedir({"pedido": "estado"}).get("ok"))
        except QuadroIndisponivel:
            return False

    def catalogo(self) -> dict:
        resposta = self.pedir({"pedido": "catalogo"})
        if not resposta.get("ok"):
            raise QuadroIndisponivel(str(resposta.get("erro", "pedido recusado")))
        return resposta

    def pedir_menu(self, visivel: bool) -> dict:
        """Diz ao Quadro se o menu deve estar visivel (o teclado esconde-o enquanto mostra os seus icones)."""
        resposta = self.pedir({"pedido": "menu", "visivel": visivel})
        if not resposta.get("ok"):
            raise QuadroIndisponivel(str(resposta.get("erro", "pedido recusado")))
        return resposta

    def executar(self, identificador: str) -> dict:
        resposta = self.pedir({"pedido": "acao", "id": identificador})
        if not resposta.get("ok"):
            raise QuadroIndisponivel(str(resposta.get("erro", "ação recusada")))
        return resposta
