import copy
import json

import pytest

from teclado.gateway.protocolo import (
    TAMANHO_MAXIMO,
    ProtocoloErro,
    Sessao,
    assinar,
    codificar,
    descodificar,
)

CHAVE = b"c" * 32
LAYOUT = {
    "nome": "Vogais",
    "idioma": "pt-PT",
    "linhas": [[{"rotulo": "A", "acao": {"tipo": "texto", "valor": "a"}}]],
}


def _dados(tipo="ping", corpo=None, seq=0):
    return codificar(CHAVE, tipo, "m1", seq, corpo)


def _alterar(dados, **campos):
    msg = json.loads(dados.decode("utf-8"))
    msg.update(campos)
    return json.dumps(msg).encode("utf-8")


# --- ida e volta ----------------------------------------------------------------

def test_ping_ida_e_volta():
    msg = descodificar(CHAVE, _dados("ping"), 0)
    assert msg["tipo"] == "ping" and msg["sequencia"] == 0


def test_acao_texto_ida_e_volta():
    dados = _dados("acao", {"acao": {"tipo": "texto", "valor": "olá"}})
    assert descodificar(CHAVE, dados, 0)["acao"]["valor"] == "olá"


def test_teclados_validados_ida_e_volta():
    msg = descodificar(CHAVE, _dados("teclados", {"layouts": [LAYOUT]}), 0)
    assert msg["layouts"][0]["nome"] == "Vogais"


def test_sugestoes_ida_e_volta():
    msg = descodificar(CHAVE, _dados("sugestoes", {"palavras": ["casa", "cama"]}), 0)
    assert msg["palavras"] == ["casa", "cama"]


def test_json_canonico_e_estavel():
    a = codificar(CHAVE, "ping", "m1", 0)
    assert assinar(CHAVE, json.loads(a)) == json.loads(a)["hmac"]


# --- autenticacao ----------------------------------------------------------------

def test_chave_errada_e_recusada():
    with pytest.raises(ProtocoloErro, match="autenticacao"):
        descodificar(b"x" * 32, _dados(), 0)


def test_campo_adulterado_e_recusado():
    dados = _dados("acao", {"acao": {"tipo": "texto", "valor": "a"}})
    adulterado = _alterar(dados, acao={"tipo": "texto", "valor": "b"})
    with pytest.raises(ProtocoloErro, match="autenticacao"):
        descodificar(CHAVE, adulterado, 0)


def test_hmac_em_falta_e_recusado():
    msg = json.loads(_dados().decode("utf-8"))
    del msg["hmac"]
    with pytest.raises(ProtocoloErro):
        descodificar(CHAVE, json.dumps(msg).encode("utf-8"), 0)


def test_hmac_de_outra_mensagem_nao_serve():
    outra = json.loads(_dados("ping", seq=5).decode("utf-8"))
    original = json.loads(_dados("pong", seq=5).decode("utf-8"))
    original["hmac"] = outra["hmac"]
    with pytest.raises(ProtocoloErro):
        descodificar(CHAVE, json.dumps(original).encode("utf-8"), 0)


# --- sequencia --------------------------------------------------------------------

def test_repeticao_e_recusada():
    sessao = Sessao(CHAVE)
    dados = sessao.enviar("ping", "m1")
    receptor = Sessao(CHAVE)
    receptor.receber(dados)
    with pytest.raises(ProtocoloErro, match="sequencia"):
        receptor.receber(dados)


def test_sequencia_fora_de_ordem_e_recusada():
    sessao = Sessao(CHAVE)
    primeira = sessao.enviar("ping", "a")
    segunda = sessao.enviar("ping", "b")
    receptor = Sessao(CHAVE)
    receptor.receber(segunda)
    with pytest.raises(ProtocoloErro, match="sequencia"):
        receptor.receber(primeira)


def test_sequencia_cresce_no_envio():
    sessao = Sessao(CHAVE)
    seqs = [json.loads(sessao.enviar("ping", str(i)))["sequencia"] for i in range(3)]
    assert seqs == [0, 1, 2]


def test_sequencia_negativa_ou_booleana_recusada():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "ping", "m1", -1)
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "ping", "m1", True)


# --- limites -----------------------------------------------------------------------

def test_mensagem_acima_de_16kb_e_recusada_ao_receber():
    grande = b"{" + b" " * (TAMANHO_MAXIMO + 10) + b"}"
    with pytest.raises(ProtocoloErro, match="demasiado grande"):
        descodificar(CHAVE, grande, 0)


def test_mensagem_acima_de_16kb_e_recusada_ao_enviar():
    palavras = ["x" * 40] * 10
    corpo = {"palavras": palavras, "extra": "y" * (TAMANHO_MAXIMO)}
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "sugestoes", "m1", 0, corpo)


def test_json_mal_formado_e_recusado():
    with pytest.raises(ProtocoloErro, match="mal formada"):
        descodificar(CHAVE, b"{ isto nao e json", 0)


def test_tipo_desconhecido_e_recusado():
    with pytest.raises(ProtocoloErro, match="tipo"):
        codificar(CHAVE, "executar", "m1", 0)


def test_chave_curta_e_recusada():
    with pytest.raises(ProtocoloErro):
        Sessao(b"curta")


# --- conteudo validado -----------------------------------------------------------------

def test_acao_inventada_e_recusada():
    with pytest.raises(ProtocoloErro, match="acao"):
        codificar(CHAVE, "acao", "m1", 0, {"acao": {"tipo": "executar", "valor": "rm"}})


def test_tecla_especial_inexistente_e_recusada():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "acao", "m1", 0, {"acao": {"tipo": "tecla", "valor": "formatar"}})


def test_acao_de_janela_remota_nao_e_aceite():
    # Acoes de janela ficam fora do controlo remoto nesta fase.
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "acao", "m1", 0, {"acao": {"tipo": "acao", "valor": "minimizar_janela"}})


def test_teclado_invalido_e_recusado():
    mau = copy.deepcopy(LAYOUT)
    mau["linhas"][0][0]["acao"] = {"tipo": "script", "valor": "x"}
    with pytest.raises(ProtocoloErro, match="teclado"):
        codificar(CHAVE, "teclados", "m1", 0, {"layouts": [mau]})


def test_mais_de_50_teclados_recusados():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "teclados", "m1", 0, {"layouts": [LAYOUT] * 51})


def test_sugestoes_demasiadas_recusadas():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "sugestoes", "m1", 0, {"palavras": ["a"] * 11})


def test_sugestao_vazia_recusada():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "sugestoes", "m1", 0, {"palavras": [""]})


def test_emparelhar_so_aceita_passos_conhecidos():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "emparelhar", "m1", 0, {"passo": "roubar", "valor": "ab"})


def test_emparelhar_valor_tem_de_ser_hexadecimal():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "emparelhar", "m1", 0, {"passo": "desafio", "valor": "xyz!"})


def test_id_vazio_ou_longo_recusado():
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "ping", "", 0)
    with pytest.raises(ProtocoloErro):
        codificar(CHAVE, "ping", "x" * 65, 0)
