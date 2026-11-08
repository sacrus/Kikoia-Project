"""Gateway no PC: nucleo comum (emparelhamento, sessao, acoes, difusao) e transporte Wi-Fi.

Emparelhamento (SPAKE2 com o codigo de 6 digitos):
  1. Telemovel -> PC: emparelhar/desafio  (mensagem SPAKE2 do lado A)
  2. PC -> Telemovel: emparelhar/resposta (mensagem SPAKE2 do lado B)
  3. Telemovel -> PC: emparelhar/confirmacao = HMAC(K, "cliente")
  4. PC -> Telemovel: emparelhar/confirmacao = HMAC(K, "servidor")
Depois de confirmado, cada mensagem e autenticada com a chave de sessao.

O PC e a fonte de verdade: envia o teclado ativo e as sugestoes em tempo real
(atualizar_teclado / atualizar_sugestoes), chamaveis de qualquer thread.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from collections.abc import Callable
from typing import Any

from spake2 import SPAKE2_B
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from teclado.core.idiomas import t
from teclado.gateway.confianca import RepositorioConfianca, chave_reconhecimento, derivar, prova
from teclado.gateway.emparelhamento import CodigoEmparelhamento
from teclado.gateway.protocolo import (
    MAX_PALAVRA,
    MAX_SUGESTOES,
    TAMANHO_MAXIMO,
    ProtocoloErro,
    Sessao,
    codificar_emparelhamento,
    descodificar_emparelhamento,
)

PORTA_POR_OMISSAO = 47800
# Heartbeat de aplicacao (Bluetooth nao tem o do WebSocket): ping a cada 15 s;
# 45 s sem nenhuma mensagem do telemovel = ligacao perdida.
INTERVALO_PING_S = 15.0
TEMPO_SEM_SINAL_S = 45.0
PEDIDO_DESCOBERTA = b"TECLADO-GW?"
VERSAO = 1
ID_CLIENTE = b"cliente"
ID_PC = b"pc"

log = logging.getLogger(__name__)


def _hmac(chave: bytes, rotulo: bytes) -> bytes:
    return hmac.new(chave, rotulo, hashlib.sha256).digest()


def chave_sessao(chave_spake: bytes) -> bytes:
    """Chave de sessao derivada da chave SPAKE2 (separada da confirmacao)."""
    return _hmac(chave_spake, b"gateway-sessao")


class SemConfianca(Exception):
    """O telemovel pediu ligacao sem codigo, mas o PC nao o conhece."""


class NucleoGateway:
    """Emparelhamento, troca de mensagens e difusao, independentes do transporte."""

    def __init__(
        self,
        nome: str,
        ao_acao: Callable[[dict[str, Any]], None],
        ao_emparelhar: Callable[[str], None] | None = None,
        ao_desligar: Callable[[str], None] | None = None,
        fornecer_teclado: Callable[[], dict[str, Any] | None] | None = None,
        fornecer_sugestoes: Callable[[], list[str]] | None = None,
        confianca: RepositorioConfianca | None = None,
        ao_emparelhar_novo: Callable[[str], None] | None = None,
        fornecer_interruptores: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.nome = nome
        self._ao_acao = ao_acao
        self._fornecer_interruptores = fornecer_interruptores
        self._ao_emparelhar = ao_emparelhar or (lambda endereco: None)
        self._ao_emparelhar_novo = ao_emparelhar_novo or (lambda endereco: None)
        self._confianca = confianca
        self._ao_desligar = ao_desligar or (lambda endereco: None)
        self._fornecer_teclado = fornecer_teclado
        self._fornecer_sugestoes = fornecer_sugestoes
        self._codigo: CodigoEmparelhamento | None = None
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._parar: asyncio.Event | None = None
        self._pronto = threading.Event()
        self._erro: str | None = None
        self._dispositivos: set[str] = set()
        # id(canal) -> (canal, sessao) dos telemoveis com sessao ativa.
        self._sessoes: dict[int, tuple[Any, Sessao]] = {}
        self._ultimo_sinal: dict[int, float] = {}

    # --- estado -------------------------------------------------------------

    @property
    def ativo(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def dispositivos_ligados(self) -> int:
        return len(self._dispositivos)

    @property
    def codigo(self) -> CodigoEmparelhamento | None:
        return self._codigo

    def novo_codigo(self) -> CodigoEmparelhamento:
        """Gera um codigo novo (o anterior deixa de valer)."""
        self._codigo = CodigoEmparelhamento()
        return self._codigo

    # --- difusao (chamavel de qualquer thread) -------------------------------

    def atualizar_teclado(self, modelo: dict[str, Any]) -> None:
        """Envia o teclado ativo a todos os telemoveis ligados."""
        self._difundir(lambda sessao: self._mensagem_teclado(sessao, modelo))

    def atualizar_sugestoes(self, palavras: list[str]) -> None:
        """Envia as sugestoes atuais a todos os telemoveis ligados."""
        limpas = [p for p in palavras if 1 <= len(p) <= MAX_PALAVRA][:MAX_SUGESTOES]
        self._difundir(lambda sessao: sessao.enviar("sugestoes", "s", {"palavras": limpas}))

    def atualizar_interruptores(self, estado: dict[str, Any]) -> None:
        """Envia o estado dos interruptores Falar e Ditar a todos os telemoveis ligados."""
        self._difundir(lambda sessao: sessao.enviar("interruptores", "i", estado))

    def _difundir(self, fabrica: Callable[[Sessao], bytes | None]) -> None:
        loop = self._loop
        if loop is None or not self._sessoes:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._enviar_a_todos(fabrica), loop)
        except RuntimeError:
            pass  # loop ja fechado: o gateway esta a desligar

    async def _enviar_a_todos(self, fabrica: Callable[[Sessao], bytes | None]) -> None:
        for canal, sessao in list(self._sessoes.values()):
            # Cada telemovel e tratado a parte: um erro num nao pode impedir os outros de receber.
            try:
                dados = fabrica(sessao)
                if dados is None:
                    continue
                await canal.send(dados)
            except (ConnectionError, OSError, ConnectionClosed):
                log.info("Telemovel desligado durante a difusao")
            except Exception:
                # Sem isto, o erro ficava guardado na tarefa e ninguem o via.
                log.error("Falha ao enviar mensagem a um telemovel", exc_info=True)

    def _mensagem_teclado(self, sessao: Sessao, modelo: dict[str, Any]) -> bytes | None:
        try:
            return sessao.enviar("teclados", "t", {"layouts": [modelo]})
        except ProtocoloErro:
            log.warning("Teclado '%s' nao cabe no protocolo; ignorado", modelo.get("nome"))
            return None

    # --- ciclo de vida -------------------------------------------------------

    def iniciar(self) -> None:
        if self.ativo:
            return
        self._pronto.clear()
        self._erro = None
        self._thread = threading.Thread(target=self._correr, daemon=True, name="gateway")
        self._thread.start()
        self._pronto.wait(10.0)
        if self._erro:
            raise RuntimeError(self._erro)

    def parar(self) -> None:
        if not self.ativo or self._loop is None or self._parar is None:
            return
        self._loop.call_soon_threadsafe(self._parar.set)
        self._thread.join(5.0)
        self._thread = None

    def _correr(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._principal_seguro())
        finally:
            self._loop.close()

    async def _principal_seguro(self) -> None:
        self._parar = asyncio.Event()
        try:
            await self._principal()
        except OSError as erro:
            self._erro = t("servidor.transporte", erro=erro)
            self._pronto.set()

    async def _principal(self) -> None:
        raise NotImplementedError

    # --- ligacao de um dispositivo -----------------------------------------------

    async def _tratar(self, canal) -> None:
        endereco = str(canal.remote_address)
        log.info("Ligacao recebida de %s", endereco)
        try:
            chave_spake = await self._emparelhar(canal, endereco)
        except SemConfianca:
            log.info("Telemovel sem confianca guardada (%s)", endereco)
            await canal.send(codificar_emparelhamento("sem_confianca", "0"))
            await canal.close(code=4004, reason="sem confianca")
            return
        except ProtocoloErro as erro:
            log.info("Emparelhamento recusado (%s): %s", endereco, erro)
            await canal.close(code=4003, reason="emparelhamento recusado")
            return
        except ConnectionClosed:
            log.info("Telemovel desligou durante o emparelhamento (%s)", endereco)
            return
        except Exception:
            log.error("Erro no emparelhamento (%s)", endereco, exc_info=True)
            await canal.close(code=1011, reason="erro interno")
            return
        if chave_spake is None:
            await canal.close(code=4001, reason="sem codigo ativo")
            return

        sessao = Sessao(chave_sessao(chave_spake))
        self._dispositivos.add(endereco)
        self._sessoes[id(canal)] = (canal, sessao)
        self._ultimo_sinal[id(canal)] = time.monotonic()
        self._ao_emparelhar(endereco)
        vigia = None
        try:
            await self._estado_inicial(canal, sessao)
            vigia = asyncio.create_task(self._vigiar(canal, sessao, endereco))
            async for dados in canal:
                self._ultimo_sinal[id(canal)] = time.monotonic()
                try:
                    msg = sessao.receber(dados if isinstance(dados, bytes) else dados.encode("utf-8"))
                except ProtocoloErro as erro:
                    log.warning("Mensagem recusada de %s: %s", endereco, erro)
                    await canal.close(code=1008, reason="mensagem recusada")
                    return
                await self._processar(canal, sessao, msg)
        except (ConnectionError, OSError):
            pass  # ligacao perdida: tratada no finally
        finally:
            if vigia is not None:
                vigia.cancel()
            # getattr: o canal Bluetooth nao tem close_code (so o WebSocket tem).
            log.info("Ligacao de %s terminada (codigo %s)", endereco, getattr(canal, "close_code", "-"))
            self._sessoes.pop(id(canal), None)
            self._ultimo_sinal.pop(id(canal), None)
            self._dispositivos.discard(endereco)
            self._ao_desligar(endereco)

    async def _vigiar(self, canal, sessao: Sessao, endereco: str) -> None:
        """Ping de aplicacao a cada INTERVALO_PING_S. Sem sinal do telemovel durante
        TEMPO_SEM_SINAL_S, a ligacao e dada como perdida (ex.: Bluetooth que caiu sem aviso)."""
        while True:
            await asyncio.sleep(INTERVALO_PING_S)
            silencio = time.monotonic() - self._ultimo_sinal.get(id(canal), 0.0)
            if silencio > TEMPO_SEM_SINAL_S:
                log.info("Telemovel %s sem sinal ha %.0f s: ligacao dada como perdida", endereco, silencio)
                try:
                    await canal.close(code=1001, reason="sem sinal")
                except Exception:
                    pass
                return
            try:
                await canal.send(sessao.enviar("ping", secrets.token_hex(4)))
            except Exception:
                return  # a ligacao ja caiu: o ciclo de receção trata do resto

    async def _estado_inicial(self, canal, sessao: Sessao) -> None:
        """Teclado ativo e sugestoes atuais, logo apos o emparelhamento."""
        if self._fornecer_teclado is not None:
            modelo = self._fornecer_teclado()
            if modelo is not None:
                dados = self._mensagem_teclado(sessao, modelo)
                if dados is not None:
                    await canal.send(dados)
        if self._fornecer_sugestoes is not None:
            palavras = self._fornecer_sugestoes()
            limpas = [p for p in palavras if 1 <= len(p) <= MAX_PALAVRA][:MAX_SUGESTOES]
            await canal.send(sessao.enviar("sugestoes", "s", {"palavras": limpas}))
        if self._fornecer_interruptores is not None:
            await canal.send(sessao.enviar("interruptores", "i", self._fornecer_interruptores()))

    async def _processar(self, canal, sessao: Sessao, msg: dict[str, Any]) -> None:
        tipo = msg["tipo"]
        if tipo == "ping":
            await canal.send(sessao.enviar("pong", msg["id"]))
        elif tipo in ("acao", "escolher_sugestao", "interruptor"):
            self._ao_acao(msg)
        # Outros tipos sao do PC para o telemovel: ignorados aqui.

    async def _emparelhar(self, canal, endereco: str) -> bytes | None:
        """Devolve a chave de ligacao se for bem-sucedida; None se nao houver codigo ativo.

        Primeira mensagem do telemovel: 'reconhecer' (ligacao de confianca, sem codigo)
        ou 'desafio' (emparelhamento SPAKE2 com o codigo de 6 digitos).
        """
        primeira = descodificar_emparelhamento(await canal.recv())
        if primeira["passo"] == "reconhecer":
            return await self._reconhecer(canal, primeira["valor"], endereco)
        return await self._emparelhar_codigo(canal, endereco, primeira)

    async def _reconhecer(self, canal, ident: str, endereco: str) -> bytes:
        segredo = self._confianca.segredo(ident) if self._confianca is not None else None
        if segredo is None:
            raise SemConfianca()
        nonce = secrets.token_hex(16)
        await canal.send(codificar_emparelhamento("desafio_confianca", nonce))
        resposta = descodificar_emparelhamento(await canal.recv())
        if resposta["passo"] != "resposta_confianca":
            raise ProtocoloErro("passo inesperado")
        if not hmac.compare_digest(resposta["valor"], prova(segredo, "cliente", nonce)):
            raise ProtocoloErro("confianca recusada")
        await canal.send(codificar_emparelhamento("confirmacao_confianca", prova(segredo, "servidor", nonce)))
        self._confianca.atualizar_nome(ident, endereco)
        return chave_reconhecimento(segredo, nonce)

    async def _emparelhar_codigo(self, canal, endereco: str, desafio: dict[str, Any]) -> bytes | None:
        codigo = self._codigo
        if codigo is None or codigo.estado != "ativo":
            return None

        if desafio["passo"] != "desafio":
            raise ProtocoloErro("passo inesperado")

        spake = SPAKE2_B(codigo.codigo.encode("ascii"), idA=ID_CLIENTE, idB=ID_PC)
        mensagem_pc = spake.start()
        await canal.send(codificar_emparelhamento("resposta", mensagem_pc.hex()))
        try:
            chave = spake.finish(bytes.fromhex(desafio["valor"]))
        except Exception as erro:
            raise ProtocoloErro("mensagem SPAKE2 invalida") from erro

        confirmacao = descodificar_emparelhamento(await canal.recv())
        if confirmacao["passo"] != "confirmacao":
            raise ProtocoloErro("passo inesperado")
        esperado = _hmac(chave, b"cliente").hex()
        if not hmac.compare_digest(confirmacao["valor"], esperado):
            codigo.registar_falha()  # codigo errado: as chaves nao coincidem
            raise ProtocoloErro("codigo errado")

        codigo.verificar(codigo.codigo)  # confirmado: o codigo fica usado
        await canal.send(codificar_emparelhamento("confirmacao", _hmac(chave, b"servidor").hex()))
        ident, segredo = derivar(chave)
        if self._confianca is not None:
            self._confianca.guardar(ident, segredo, endereco)
        self._ao_emparelhar_novo(endereco)
        return chave


class ProtocoloDescoberta(asyncio.DatagramProtocol):
    """Responde a 'TECLADO-GW?' com o nome e a porta. Ignora qualquer outra mensagem."""

    def __init__(self, nome: str, porta: int) -> None:
        self._nome = nome
        self._porta = porta
        self._transporte = None

    def connection_made(self, transporte) -> None:
        self._transporte = transporte

    def datagram_received(self, dados: bytes, endereco) -> None:
        if dados != PEDIDO_DESCOBERTA or self._transporte is None:
            return
        resposta = json.dumps({"gw": VERSAO, "nome": self._nome, "porta": self._porta}).encode("utf-8")
        self._transporte.sendto(resposta, endereco)


class ServidorGateway(NucleoGateway):
    """Transporte Wi-Fi: WebSocket na porta configurada e descoberta UDP."""

    def __init__(self, nome: str, ao_acao, porta: int = PORTA_POR_OMISSAO, **kwargs) -> None:
        super().__init__(nome, ao_acao, **kwargs)
        self.porta = porta

    async def _principal(self) -> None:
        loop = asyncio.get_running_loop()
        udp, _ = await loop.create_datagram_endpoint(
            lambda: ProtocoloDescoberta(self.nome, self.porta),
            local_addr=("0.0.0.0", self.porta),
        )
        try:
            async with serve(self._tratar, "0.0.0.0", self.porta, max_size=TAMANHO_MAXIMO):
                self._pronto.set()
                await self._parar.wait()
        finally:
            udp.close()
