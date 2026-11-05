import asyncio
import socket
import sys

import pytest

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="BlueZ so existe no Linux")

from teclado.gateway import bluetooth_linux as bl  # noqa: E402


def test_endereco_do_caminho_do_dispositivo():
    caminho = "/org/bluez/hci0/dev_B4_05_A1_1A_79_49"
    assert bl._endereco_do_caminho(caminho) == "B4:05:A1:1A:79:49"


def test_caminho_que_nao_e_dispositivo_fica_igual():
    assert bl._endereco_do_caminho("/org/bluez/hci0") == "/org/bluez/hci0"


def test_disponivel_devolve_none_ou_motivo():
    motivo = bl.disponivel()
    assert motivo is None or isinstance(motivo, str)


def test_ligacao_aceite_chega_ao_nucleo(monkeypatch):
    recebidos = []

    async def tratar(self, canal):
        recebidos.append(canal)

    monkeypatch.setattr(bl.ServidorBluetooth, "_tratar", tratar)
    monkeypatch.setattr(bl, "_nome_do_dispositivo", lambda dispositivo: "Telemovel de teste")

    cliente, servidor = socket.socketpair()
    fd = servidor.detach()
    gateway = bl.ServidorBluetooth("PC-teste", lambda msg: None)

    async def correr():
        await gateway._aceitar_fd(fd, "/org/bluez/hci0/dev_B4_05_A1_1A_79_49")

    asyncio.run(correr())
    cliente.close()

    assert len(recebidos) == 1
    assert recebidos[0].remote_address == "Telemovel de teste"
