"""Transporte Bluetooth (RFCOMM/SPP) no Linux, via BlueZ no barramento D-Bus.

O PC regista o perfil SPP (o mesmo UUID do Windows) no BlueZ, que anuncia o servico
e entrega cada ligacao ja aberta (com um descritor de ficheiro). O emparelhamento e
feito uma vez, nas definicoes do Linux e do Android. Depois, o protocolo e o mesmo do
Wi-Fi e do Windows.

A passagem de descritores de ficheiro so existe na API bloqueante do jeepney: o
registo e a receção dos pedidos do BlueZ correm numa thread propria, e cada ligacao
e entregue ao loop asyncio do gateway.

Requer o BlueZ (bluetoothd) a correr e um adaptador Bluetooth.
"""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import threading

from jeepney import DBusAddress, new_error, new_method_return
from jeepney.bus_messages import message_bus
from jeepney.io.blocking import Proxy, open_dbus_connection
from jeepney.low_level import HeaderFields, MessageType
from jeepney.wrappers import DBusErrorResponse, new_method_call, unwrap_msg

from teclado.core.idiomas import t
from teclado.gateway.bluetooth import SPP_UUID
from teclado.gateway.canal import canal_de_streams
from teclado.gateway.confianca import _normalizar
from teclado.gateway.servidor import NucleoGateway

BLUEZ = "org.bluez"
CAMINHO_BLUEZ = "/org/bluez"
CAMINHO_PERFIL = "/teclado/gateway/spp"
IFACE_GESTOR_PERFIS = "org.bluez.ProfileManager1"
IFACE_DISPOSITIVO = "org.bluez.Device1"
IFACE_PROPRIEDADES = "org.freedesktop.DBus.Properties"
IFACE_GESTOR_OBJETOS = "org.freedesktop.DBus.ObjectManager"
NOME_PERFIL = "Teclado Remoto"

log = logging.getLogger(__name__)
_CAMINHO_DISPOSITIVO = re.compile(r"/org/bluez/hci\d+/dev_((?:[0-9A-F]{2}_){5}[0-9A-F]{2})$")


def _endereco_do_caminho(caminho: str) -> str:
    """'/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF' -> 'AA:BB:CC:DD:EE:FF'."""
    encontrado = _CAMINHO_DISPOSITIVO.search(caminho)
    return encontrado.group(1).replace("_", ":") if encontrado else caminho


def _chamar_bloqueante(conexao, destino: DBusAddress, metodo: str, assinatura=None, corpo=()):
    try:
        return unwrap_msg(conexao.send_and_get_reply(new_method_call(destino, metodo, assinatura, corpo)))
    except DBusErrorResponse as erro:
        raise OSError(f"BlueZ recusou o pedido: {erro.name}") from erro


def disponivel() -> str | None:
    """None se o BlueZ estiver a correr; senao, o motivo."""
    try:
        conexao = open_dbus_connection(bus="SYSTEM")
    except OSError:
        return t("bluetooth.sem_bluez")
    try:
        (ativo,) = Proxy(message_bus, conexao).NameHasOwner(BLUEZ)
    except OSError:
        return t("bluetooth.sem_bluez")
    finally:
        conexao.close()
    return None if ativo else t("bluetooth.sem_bluez")


def dispositivos_emparelhados() -> set[str]:
    """Nomes e enderecos dos dispositivos Bluetooth emparelhados no BlueZ."""
    try:
        conexao = open_dbus_connection(bus="SYSTEM")
    except OSError:
        return set()
    try:
        destino = DBusAddress("/", bus_name=BLUEZ, interface=IFACE_GESTOR_OBJETOS)
        (objetos,) = _chamar_bloqueante(conexao, destino, "GetManagedObjects")
    except OSError:
        return set()
    finally:
        conexao.close()
    encontrados: set[str] = set()
    for interfaces in objetos.values():
        dispositivo = interfaces.get(IFACE_DISPOSITIVO)
        if not dispositivo or not dispositivo.get("Paired", ("b", False))[1]:
            continue
        for campo in ("Alias", "Address"):
            valor = dispositivo.get(campo)
            if valor and valor[1]:
                encontrados.add(_normalizar(str(valor[1])))
    return encontrados


def _nome_do_dispositivo(dispositivo: str) -> str:
    """Nome que o telemovel tem no BlueZ; se nao for possivel ler, o endereco."""
    endereco = _endereco_do_caminho(dispositivo)
    try:
        conexao = open_dbus_connection(bus="SYSTEM")
    except OSError:
        return endereco
    try:
        destino = DBusAddress(dispositivo, bus_name=BLUEZ, interface=IFACE_PROPRIEDADES)
        (valor,) = _chamar_bloqueante(conexao, destino, "Get", "ss", (IFACE_DISPOSITIVO, "Alias"))
        return str(valor[1]).strip() or endereco
    except OSError:
        return endereco
    finally:
        conexao.close()


def _resolver(registo: asyncio.Future, erro: BaseException | None) -> None:
    if registo.done():
        return
    if erro is None:
        registo.set_result(None)
    else:
        registo.set_exception(erro)


class ServidorBluetooth(NucleoGateway):
    """Mesmo nucleo do Wi-Fi, com ligacoes RFCOMM geridas pelo BlueZ."""

    def __init__(self, nome: str, ao_acao, **kwargs) -> None:
        super().__init__(nome, ao_acao, **kwargs)
        self._ligacoes: set[asyncio.Task] = set()

    async def _principal(self) -> None:
        loop = asyncio.get_running_loop()
        registo = loop.create_future()
        parada = threading.Event()
        bluez = threading.Thread(
            target=self._correr_bluez, args=(loop, registo, parada), daemon=True, name="bluez",
        )
        bluez.start()
        try:
            await registo
            self._pronto.set()
            await self._parar.wait()
        finally:
            parada.set()
            await loop.run_in_executor(None, bluez.join, 5.0)
            for ligacao in list(self._ligacoes):
                ligacao.cancel()

    def _correr_bluez(self, loop: asyncio.AbstractEventLoop, registo: asyncio.Future, parada: threading.Event) -> None:
        try:
            conexao = open_dbus_connection(bus="SYSTEM", enable_fds=True)
        except OSError as erro:
            loop.call_soon_threadsafe(_resolver, registo, OSError(f"D-Bus indisponivel: {erro}"))
            return
        registado = False
        try:
            destino = DBusAddress(CAMINHO_BLUEZ, bus_name=BLUEZ, interface=IFACE_GESTOR_PERFIS)
            opcoes = {
                "Name": ("s", NOME_PERFIL),
                "Role": ("s", "server"),
                "RequireAuthentication": ("b", True),
                "RequireAuthorization": ("b", False),
            }
            _chamar_bloqueante(conexao, destino, "RegisterProfile", "osa{sv}", (CAMINHO_PERFIL, str(SPP_UUID), opcoes))
            registado = True
            loop.call_soon_threadsafe(_resolver, registo, None)
            while not parada.is_set():
                try:
                    msg = conexao.receive(timeout=0.5)
                except TimeoutError:
                    continue
                self._tratar_pedido(conexao, msg, loop)
        except OSError as erro:
            loop.call_soon_threadsafe(_resolver, registo, erro)
        finally:
            if registado:
                try:
                    _chamar_bloqueante(conexao, destino, "UnregisterProfile", "o", (CAMINHO_PERFIL,))
                except OSError:
                    log.info("Perfil Bluetooth nao foi removido do BlueZ", exc_info=True)
            conexao.close()

    def _tratar_pedido(self, conexao, msg, loop: asyncio.AbstractEventLoop) -> None:
        """Responde, na thread do BlueZ, aos metodos do perfil que o BlueZ chama."""
        if msg.header.message_type is not MessageType.method_call:
            return
        if msg.header.fields.get(HeaderFields.path) != CAMINHO_PERFIL:
            return
        membro = msg.header.fields.get(HeaderFields.member)
        if membro == "NewConnection":
            dispositivo, fd, _propriedades = msg.body
            conexao.send_message(new_method_return(msg))
            loop.call_soon_threadsafe(self._lancar, fd.to_raw_fd(), dispositivo)
        elif membro in ("Release", "RequestDisconnection"):
            conexao.send_message(new_method_return(msg))
        else:
            conexao.send_message(new_error(msg, "org.bluez.Error.Rejected", "s", (f"metodo desconhecido: {membro}",)))

    def _lancar(self, fd: int, dispositivo: str) -> None:
        tarefa = asyncio.get_running_loop().create_task(self._aceitar_fd(fd, dispositivo))
        self._ligacoes.add(tarefa)
        tarefa.add_done_callback(self._ligacoes.discard)

    async def _aceitar_fd(self, fd: int, dispositivo: str) -> None:
        sock = socket.socket(fileno=fd)
        try:
            sock.setblocking(False)
            endereco = await asyncio.get_running_loop().run_in_executor(None, _nome_do_dispositivo, dispositivo)
            leitor, escritor = await asyncio.open_connection(sock=sock)
            await self._tratar(canal_de_streams(leitor, escritor, endereco))
        except Exception:
            log.error("Erro numa ligacao Bluetooth", exc_info=True)
        finally:
            sock.close()
