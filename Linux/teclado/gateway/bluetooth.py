"""Transporte Bluetooth (RFCOMM/SPP) no Windows, via WinRT.

O PC anuncia o servico com o UUID SPP (00001101-...). O telemovel liga-se por
Bluetooth emparelhado (o emparelhamento do sistema e feito uma vez, nas definicoes
do Windows e do Android). Depois, o mesmo emparelhamento SPAKE2 com o codigo de 6
digitos e o mesmo protocolo usados no Wi-Fi.

Limitacoes conhecidas:
- So funciona no Windows (WinRT) e com um adaptador Bluetooth ativo.
- Requer o pacote winrt-Windows.Devices.Bluetooth.Rfcomm e afins.
"""

from __future__ import annotations

from teclado.core.idiomas import t
import asyncio
import logging
import uuid

from teclado.gateway.canal import CanalEnquadrado, CanalFechado
from teclado.gateway.confianca import NOME_DESCONHECIDO
from teclado.gateway.servidor import NucleoGateway

SPP_UUID = uuid.UUID("00001101-0000-1000-8000-00805f9b34fb")
log = logging.getLogger(__name__)


def disponivel() -> str | None:
    """None se o Bluetooth do Windows esta disponivel; senao, o motivo."""
    try:
        import winrt.windows.devices.bluetooth.rfcomm  # noqa: F401
        import winrt.windows.networking.sockets  # noqa: F401
        import winrt.windows.storage.streams  # noqa: F401
    except ImportError:
        return t("bluetooth.instalar")
    return None


def canal_de_socket(sock, endereco: str) -> CanalEnquadrado:
    """Canal enquadrado sobre um StreamSocket do WinRT."""
    from winrt.windows.storage.streams import DataReader, DataWriter

    leitor = DataReader(sock.input_stream)
    escritor = DataWriter(sock.output_stream)

    async def ler(n: int) -> bytes:
        try:
            carregados = await leitor.load_async(n)
        except OSError as erro:
            raise CanalFechado("ligacao Bluetooth perdida") from erro
        if carregados < n:
            raise CanalFechado("ligacao Bluetooth fechada")
        buffer = bytearray(n)
        leitor.read_bytes(buffer)
        return bytes(buffer)

    async def escrever(dados: bytes) -> None:
        try:
            escritor.write_bytes(dados)
            await escritor.store_async()
        except OSError as erro:
            raise CanalFechado("ligacao Bluetooth perdida") from erro

    async def fechar() -> None:
        sock.close()

    return CanalEnquadrado(ler, escrever, fechar, endereco)


class ServidorBluetooth(NucleoGateway):
    """Mesmo nucleo do Wi-Fi, com ligacoes RFCOMM em vez de WebSocket."""

    def __init__(self, nome: str, ao_acao, **kwargs) -> None:
        super().__init__(nome, ao_acao, **kwargs)
        self._anuncio = None
        self._lista = None

    async def _principal(self) -> None:
        from winrt.windows.devices.bluetooth.rfcomm import RfcommServiceId, RfcommServiceProvider
        from winrt.windows.networking.sockets import StreamSocketListener

        identificador = RfcommServiceId.from_uuid(SPP_UUID)
        self._anuncio = await RfcommServiceProvider.create_async(identificador)
        self._lista = StreamSocketListener()
        loop = asyncio.get_running_loop()

        def ao_receber(_remetente, argumentos) -> None:
            # Evento chega numa thread do WinRT: entrega ao loop do gateway.
            asyncio.run_coroutine_threadsafe(self._aceitar(argumentos.socket), loop)

        self._lista.add_connection_received(ao_receber)
        await self._lista.bind_service_name_async(identificador.as_string())
        self._anuncio.start_advertising(self._lista)
        self._pronto.set()
        try:
            await self._parar.wait()
        finally:
            self._anuncio.stop_advertising()
            self._lista.close()

    async def _aceitar(self, sock) -> None:
        try:
            endereco = _nome_remoto(sock)
            await self._tratar(canal_de_socket(sock, endereco))
        except Exception:
            log.error("Erro numa ligacao Bluetooth", exc_info=True)
        finally:
            sock.close()


def _nome_remoto(sock) -> str:
    """Nome ou endereco do telemovel, tentando os varios campos que o Windows devolve."""
    try:
        host = sock.information.remote_host_name
    except Exception:
        return NOME_DESCONHECIDO
    for campo in ("display_name", "canonical_name", "raw_name"):
        try:
            valor = str(getattr(host, campo) or "").strip()
        except Exception:
            valor = ""
        if valor:
            return valor
    log.info("O Windows nao indicou o nome do telemovel Bluetooth")
    return NOME_DESCONHECIDO
