import asyncio
import hashlib
import hmac
import json
import sys

import pytest
from spake2 import SPAKE2_A

from teclado.gateway.confianca import (
    RepositorioConfianca,
    chave_reconhecimento,
    derivar,
    dispositivos_emparelhados_windows,
    pode_ser_emparelhado,
    prova,
)
from teclado.gateway.protocolo import ProtocoloErro, codificar_emparelhamento
from teclado.gateway.servidor import NucleoGateway, SemConfianca, chave_sessao


class Canal:
    """Canal falso: cada passo do telemovel e uma funcao que olha para o que o PC enviou."""

    def __init__(self, passos):
        self.passos = list(passos)
        self.enviadas = []
        self.fechado = None
        self.remote_address = "Telemovel"

    async def recv(self):
        return self.passos.pop(0)(self)

    async def send(self, dados):
        self.enviadas.append(dados)

    async def close(self, code, reason=""):
        self.fechado = code

    def ultima_valor(self):
        return json.loads(self.enviadas[-1])["valor"]


def _hmac(chave, rotulo):
    return hmac.new(chave, rotulo, hashlib.sha256).digest()


def _nucleo(tmp_path, novos=None):
    return NucleoGateway(
        "PC", ao_acao=lambda m: None,
        confianca=RepositorioConfianca(tmp_path),
        ao_emparelhar_novo=(novos.append if novos is not None else None),
    )


def _emparelhar_com_codigo(nucleo, novos_estado):
    """Telemovel que emparelha com o codigo SPAKE2 (como a app Android)."""
    codigo = nucleo.novo_codigo().codigo

    def primeira(_canal):
        spake = SPAKE2_A(codigo.encode("ascii"), idA=b"cliente", idB=b"pc")
        novos_estado["spake"] = spake
        return codificar_emparelhamento("desafio", spake.start().hex())

    def confirma(canal):
        chave = novos_estado["spake"].finish(bytes.fromhex(canal.ultima_valor()))
        novos_estado["chave"] = chave
        return codificar_emparelhamento("confirmacao", _hmac(chave, b"cliente").hex())

    return Canal([primeira, confirma])


def _reconhecer(ident, segredo):
    def resposta(canal):
        nonce = canal.ultima_valor()
        return codificar_emparelhamento("resposta_confianca", prova(segredo, "cliente", nonce))

    return Canal([lambda _c: codificar_emparelhamento("reconhecer", ident), resposta])


def test_derivacao_e_igual_dos_dois_lados():
    chave = b"k" * 32
    assert derivar(chave) == derivar(chave)
    ident, segredo = derivar(chave)
    assert len(ident) == 32 and len(segredo) == 32


def test_emparelhamento_com_codigo_guarda_a_confianca(tmp_path):
    novos = []
    nucleo = _nucleo(tmp_path, novos)
    estado = {}
    canal = _emparelhar_com_codigo(nucleo, estado)
    chave = asyncio.run(nucleo._emparelhar(canal, "Telemovel"))
    ident, segredo = derivar(chave)
    assert chave == estado["chave"]
    assert RepositorioConfianca(tmp_path).segredo(ident) == segredo
    assert novos == ["Telemovel"]


def test_ligacao_de_confianca_nao_precisa_de_codigo(tmp_path):
    nucleo = _nucleo(tmp_path)
    estado = {}
    chave = asyncio.run(nucleo._emparelhar(_emparelhar_com_codigo(nucleo, estado), "Telemovel"))
    ident, segredo = derivar(chave)

    canal = _reconhecer(ident, segredo)
    chave_nova = asyncio.run(nucleo._emparelhar(canal, "Telemovel"))
    nonce = json.loads(canal.enviadas[0])["valor"]
    assert chave_nova == chave_reconhecimento(segredo, nonce)
    assert json.loads(canal.enviadas[1])["valor"] == prova(segredo, "servidor", nonce)
    assert chave_sessao(chave_nova) == chave_sessao(chave_reconhecimento(segredo, nonce))


def test_dispositivo_desconhecido_e_recusado(tmp_path):
    nucleo = _nucleo(tmp_path)
    with pytest.raises(SemConfianca):
        asyncio.run(nucleo._emparelhar(_reconhecer("0" * 32, b"s" * 32), "Telemovel"))


def test_prova_errada_e_recusada(tmp_path):
    nucleo = _nucleo(tmp_path)
    RepositorioConfianca(tmp_path).guardar("1" * 32, b"s" * 32, "Telemovel")
    canal = _reconhecer("1" * 32, b"outro" * 8)
    with pytest.raises(ProtocoloErro):
        asyncio.run(nucleo._emparelhar(canal, "Telemovel"))


def test_codigo_inativo_nao_aceita_emparelhamento_novo(tmp_path):
    nucleo = _nucleo(tmp_path)
    canal = Canal([lambda _c: codificar_emparelhamento("desafio", "ab" * 8)])
    assert asyncio.run(nucleo._emparelhar(canal, "Telemovel")) is None


def test_repositorio_ignora_ficheiro_invalido(tmp_path):
    (tmp_path / "confianca.json").write_text(
        json.dumps({"../x": {"segredo": "00", "nome": "a"}, "1" * 32: {"segredo": "zz", "nome": "b"}}),
        encoding="utf-8",
    )
    repo = RepositorioConfianca(tmp_path)
    assert repo.nomes() == []
    assert repo.segredo("1" * 32) is None


def test_repositorio_guarda_e_le(tmp_path):
    repo = RepositorioConfianca(tmp_path)
    repo.guardar("a" * 32, b"\x01" * 32, "Telemóvel Ana")
    assert RepositorioConfianca(tmp_path).segredo("a" * 32) == b"\x01" * 32
    assert RepositorioConfianca(tmp_path).nomes() == ["Telemóvel Ana"]


def test_reconexao_atualiza_o_nome_real(tmp_path):
    nucleo = _nucleo(tmp_path)
    estado = {}
    chave = asyncio.run(nucleo._emparelhar(_emparelhar_com_codigo(nucleo, estado), "bluetooth"))
    ident, segredo = derivar(chave)
    assert RepositorioConfianca(tmp_path).nomes() == ["bluetooth"]
    asyncio.run(nucleo._emparelhar(_reconhecer(ident, segredo), "A90 Pro"))
    assert RepositorioConfianca(tmp_path).nomes() == ["A90 Pro"]


def test_nome_generico_nao_substitui_o_nome_guardado(tmp_path):
    repo = RepositorioConfianca(tmp_path)
    repo.guardar("2" * 32, b"s" * 32, "A90 Pro")
    repo.atualizar_nome("2" * 32, "bluetooth")
    assert repo.nomes() == ["A90 Pro"]


def test_emparelhado_pelo_nome_ignora_maiusculas():
    assert pode_ser_emparelhado(["A90 Pro"], {"a90 pro", "mouse"})


def test_emparelhado_pelo_endereco():
    assert pode_ser_emparelhado(["8F:5E:56:20:ED:12"], {"8f5e5620ed12"})


def test_telemovel_nao_emparelhado_nao_e_detetado():
    assert not pode_ser_emparelhado(["A90 Pro"], {"mouse", "tws-mate"})


def test_nome_desconhecido_basta_haver_algum_emparelhado():
    assert pode_ser_emparelhado(["bluetooth"], {"mouse"})
    assert not pode_ser_emparelhado(["bluetooth"], set())


def test_sem_registos_nao_ha_escuta():
    assert not pode_ser_emparelhado([], {"mouse"})


@pytest.mark.skipif(sys.platform != "win32", reason="le o registo do Bluetooth do Windows")
def test_dispositivos_emparelhados_windows_devolve_conjunto():
    assert isinstance(dispositivos_emparelhados_windows(), set)
