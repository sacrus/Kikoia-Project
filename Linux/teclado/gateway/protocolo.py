"""Protocolo do gateway: mensagens JSON autenticadas por HMAC e com sequencia crescente.

Formato de cada mensagem (JSON, UTF-8):
  {"tipo": ..., "id": ..., "sequencia": n, <campos do tipo>, "hmac": "<hex>"}

- O HMAC-SHA256 cobre o JSON canonico (chaves ordenadas, sem espacos) de tudo
  exceto o proprio campo "hmac".
- A sequencia tem de ser estritamente crescente por sessao: repeticoes e mensagens
  fora de ordem sao recusadas (protecao contra repeticao).
- Cada campo e validado antes de qualquer acao chegar ao editor. Os validadores
  sao os mesmos do resto do teclado (layouts e teclas).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any

from teclado.core.layout import LayoutInvalido, validar_layout, validar_tecla
from teclado.core.saida import ACOES_EDICAO

TAMANHO_MAXIMO = 16 * 1024
TIPOS = frozenset({
    "emparelhar", "teclados", "acao", "sugestoes", "escolher_sugestao", "ping", "pong",
    # Interruptores Falar e Ditar: o telemovel pede (interruptor) e o PC devolve o estado (interruptores).
    "interruptor", "interruptores",
})
INTERRUPTORES = frozenset({"falar", "ditar"})
TIPOS_ACAO_REMOTA = frozenset({"texto", "tecla", "acento", "multitoque", "modificador", "acao", "navegar", "comando"})
MAX_LAYOUTS = 50
MAX_SUGESTOES = 10
MAX_PALAVRA = 40
MAX_HEX = 256
# Acoes remotas: so edicao de texto e leitura. Fechar/minimizar janelas fica so no PC.
ACOES_REMOTAS = frozenset(ACOES_EDICAO) | {"ler_selecao"}
PASSOS_EMPARELHAR = frozenset({
    "desafio", "resposta", "confirmacao",
    # Ligacao a um telemovel de confianca (sem codigo).
    "reconhecer", "desafio_confianca", "resposta_confianca", "confirmacao_confianca", "sem_confianca",
})
_HEX = re.compile(r"[0-9a-f]+")


class ProtocoloErro(ValueError):
    """Mensagem recusada. A mensagem de erro nao contem dados do utilizador."""


def _canonico(dados: dict[str, Any]) -> bytes:
    return json.dumps(dados, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def assinar(chave: bytes, dados: dict[str, Any]) -> str:
    """HMAC-SHA256 do JSON canonico de 'dados' (sem o campo 'hmac')."""
    semf = {k: v for k, v in dados.items() if k != "hmac"}
    return hmac.new(chave, _canonico(semf), hashlib.sha256).hexdigest()


# --- validacao de cada tipo ---------------------------------------------------

def _validar_corpo(tipo: str, msg: dict[str, Any]) -> None:
    if tipo in ("ping", "pong"):
        return

    if tipo == "emparelhar":
        passo = msg.get("passo")
        valor = msg.get("valor")
        if passo not in PASSOS_EMPARELHAR:
            raise ProtocoloErro("passo de emparelhamento invalido")
        if not isinstance(valor, str) or len(valor) > MAX_HEX or not _HEX.fullmatch(valor):
            raise ProtocoloErro("valor de emparelhamento invalido")
        return

    if tipo == "teclados":
        layouts = msg.get("layouts")
        if not isinstance(layouts, list) or not layouts or len(layouts) > MAX_LAYOUTS:
            raise ProtocoloErro("lista de teclados invalida")
        for dados in layouts:
            try:
                validar_layout(dados)
            except LayoutInvalido as erro:
                raise ProtocoloErro(f"teclado invalido: {erro}") from None
        return

    if tipo == "acao":
        acao = msg.get("acao")
        if not isinstance(acao, dict) or acao.get("tipo") not in TIPOS_ACAO_REMOTA:
            raise ProtocoloErro("acao desconhecida")
        if acao["tipo"] == "acao" and acao.get("valor") not in ACOES_REMOTAS:
            raise ProtocoloErro("acao nao permitida remotamente")
        try:
            validar_tecla({"rotulo": "x", "acao": acao})
        except LayoutInvalido as erro:
            raise ProtocoloErro(f"acao invalida: {erro}") from None
        return

    if tipo == "escolher_sugestao":
        indice = msg.get("indice")
        if not isinstance(indice, int) or isinstance(indice, bool) or not 0 <= indice < MAX_SUGESTOES:
            raise ProtocoloErro("indice de sugestao invalido")
        return

    if tipo == "interruptor":
        if msg.get("nome") not in INTERRUPTORES or not isinstance(msg.get("ligado"), bool):
            raise ProtocoloErro("interruptor invalido")
        return

    if tipo == "interruptores":
        for chave in ("falar", "falar_disponivel", "ditar", "ditar_disponivel"):
            if not isinstance(msg.get(chave), bool):
                raise ProtocoloErro("estado de interruptores invalido")
        return

    if tipo == "sugestoes":
        palavras = msg.get("palavras")
        if not isinstance(palavras, list) or len(palavras) > MAX_SUGESTOES:
            raise ProtocoloErro("lista de sugestoes invalida")
        for p in palavras:
            if not isinstance(p, str) or not 1 <= len(p) <= MAX_PALAVRA:
                raise ProtocoloErro("sugestao invalida")
        return


# --- codificacao --------------------------------------------------------------

def codificar(chave: bytes, tipo: str, id_: str, sequencia: int, corpo: dict[str, Any] | None = None) -> bytes:
    """Gera os bytes de uma mensagem autenticada. Valida antes de enviar."""
    if tipo not in TIPOS:
        raise ProtocoloErro("tipo de mensagem desconhecido")
    if not isinstance(id_, str) or not 1 <= len(id_) <= 64:
        raise ProtocoloErro("identificador invalido")
    if not isinstance(sequencia, int) or isinstance(sequencia, bool) or sequencia < 0:
        raise ProtocoloErro("sequencia invalida")
    msg: dict[str, Any] = {"tipo": tipo, "id": id_, "sequencia": sequencia, **(corpo or {})}
    _validar_corpo(tipo, msg)
    msg["hmac"] = assinar(chave, msg)
    dados = _canonico(msg)
    if len(dados) > TAMANHO_MAXIMO:
        raise ProtocoloErro("mensagem demasiado grande")
    return dados


def descodificar(chave: bytes, dados: bytes, sequencia_minima: int) -> dict[str, Any]:
    """Valida uma mensagem recebida. 'sequencia_minima' = ultima sequencia aceite + 1.

    Ordem de verificacao: tamanho, JSON, tipo, HMAC, sequencia, campos.
    Assim um atacante sem a chave nao chega a ver os campos validados.
    """
    if len(dados) > TAMANHO_MAXIMO:
        raise ProtocoloErro("mensagem demasiado grande")
    try:
        msg = json.loads(dados.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProtocoloErro("mensagem mal formada") from None
    if not isinstance(msg, dict):
        raise ProtocoloErro("mensagem mal formada")
    tipo = msg.get("tipo")
    if tipo not in TIPOS:
        raise ProtocoloErro("tipo de mensagem desconhecido")
    recebido = msg.get("hmac")
    if not isinstance(recebido, str) or not hmac.compare_digest(recebido, assinar(chave, msg)):
        raise ProtocoloErro("autenticacao falhou")
    seq = msg.get("sequencia")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < sequencia_minima:
        raise ProtocoloErro("sequencia repetida ou fora de ordem")
    id_ = msg.get("id")
    if not isinstance(id_, str) or not 1 <= len(id_) <= 64:
        raise ProtocoloErro("identificador invalido")
    _validar_corpo(tipo, msg)
    return msg


def codificar_emparelhamento(passo: str, valor: str) -> bytes:
    """Mensagem de emparelhamento SPAKE2. Nao tem HMAC: ainda nao existe chave partilhada.

    Os valores transportados sao mensagens SPAKE2 (publicas por desenho) ou
    confirmacoes HMAC calculadas com a chave SPAKE2.
    """
    msg = {"tipo": "emparelhar", "passo": passo, "valor": valor}
    _validar_corpo("emparelhar", msg)
    dados = _canonico(msg)
    if len(dados) > TAMANHO_MAXIMO:
        raise ProtocoloErro("mensagem demasiado grande")
    return dados


def descodificar_emparelhamento(dados: bytes) -> dict[str, Any]:
    if len(dados) > TAMANHO_MAXIMO:
        raise ProtocoloErro("mensagem demasiado grande")
    try:
        msg = json.loads(dados.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProtocoloErro("mensagem mal formada") from None
    if not isinstance(msg, dict) or msg.get("tipo") != "emparelhar":
        raise ProtocoloErro("esperada mensagem de emparelhamento")
    _validar_corpo("emparelhar", msg)
    return msg


class Sessao:
    """Estado de uma ligacao: chave, sequencia de envio e sequencia minima de receção."""

    def __init__(self, chave: bytes) -> None:
        if len(chave) < 16:
            raise ProtocoloErro("chave de sessao demasiado curta")
        self._chave = chave
        self._seq_envio = 0
        self._seq_minima = 0

    def enviar(self, tipo: str, id_: str, corpo: dict[str, Any] | None = None) -> bytes:
        dados = codificar(self._chave, tipo, id_, self._seq_envio, corpo)
        self._seq_envio += 1
        return dados

    def receber(self, dados: bytes) -> dict[str, Any]:
        msg = descodificar(self._chave, dados, self._seq_minima)
        self._seq_minima = msg["sequencia"] + 1
        return msg
