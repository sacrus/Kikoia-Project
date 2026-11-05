import json
import urllib.error

import pytest

from teclado.core.ia import (
    ConfigIA,
    ClienteOpenAI,
    IAErro,
    carregar_config,
    extrair_json,
    gerar_teclado,
    guardar_config,
    prompt_sistema,
    prompt_utilizador,
)

TECLADO_VOGAIS = {
    "nome": "Vogais",
    "idioma": "pt-PT",
    "linhas": [[
        {"rotulo": "A", "acao": {"tipo": "texto", "valor": "a"}},
        {"rotulo": "E", "acao": {"tipo": "texto", "valor": "e"}},
    ]],
}


class ClienteFalso:
    def __init__(self, resposta):
        self.resposta = resposta
        self.pedidos = []

    def completar(self, sistema, pedido):
        self.pedidos.append((sistema, pedido))
        return self.resposta


# --- extracao da resposta -------------------------------------------------------

def test_json_puro_e_aceite():
    assert extrair_json(json.dumps(TECLADO_VOGAIS))["nome"] == "Vogais"


def test_json_dentro_de_bloco_de_codigo_e_aceite():
    texto = "Aqui está:\n```json\n" + json.dumps(TECLADO_VOGAIS) + "\n```"
    assert extrair_json(texto)["nome"] == "Vogais"


def test_json_com_texto_a_volta_e_aceite():
    texto = "Claro! " + json.dumps(TECLADO_VOGAIS) + " Espero que ajude."
    assert extrair_json(texto)["nome"] == "Vogais"


def test_resposta_vazia_da_erro_legivel():
    with pytest.raises(IAErro, match="não devolveu"):
        extrair_json("   ")


def test_resposta_sem_json_da_erro_legivel():
    with pytest.raises(IAErro, match="formato de teclado"):
        extrair_json("não consigo fazer isso")


# --- geracao validada -----------------------------------------------------------------

def test_gerar_teclado_devolve_modelo_validado():
    cliente = ClienteFalso(json.dumps(TECLADO_VOGAIS))
    modelo = gerar_teclado("um teclado com as vogais", cliente)
    assert modelo["nome"] == "Vogais"
    assert [t["rotulo"] for t in modelo["linhas"][0]] == ["A", "E"]


def test_teclado_com_acao_inventada_e_rejeitado():
    mau = json.loads(json.dumps(TECLADO_VOGAIS))
    mau["linhas"][0][0]["acao"] = {"tipo": "executar", "valor": "rm -rf"}
    with pytest.raises(IAErro, match="não é válido"):
        gerar_teclado("x", ClienteFalso(json.dumps(mau)))


def test_tecla_especial_inexistente_e_rejeitada():
    mau = json.loads(json.dumps(TECLADO_VOGAIS))
    mau["linhas"][0][0]["acao"] = {"tipo": "tecla", "valor": "formatar"}
    with pytest.raises(IAErro):
        gerar_teclado("x", ClienteFalso(json.dumps(mau)))


def test_nome_em_falta_recebe_nome_por_omissao():
    sem_nome = {"linhas": TECLADO_VOGAIS["linhas"]}
    modelo = gerar_teclado("x", ClienteFalso(json.dumps(sem_nome)), nome_por_omissao="Criado")
    assert modelo["nome"] == "Criado"


def test_pedido_vazio_nao_chama_a_ia():
    cliente = ClienteFalso("{}")
    with pytest.raises(IAErro):
        gerar_teclado("   ", cliente)
    assert cliente.pedidos == []


def test_descricao_muito_longa_e_cortada_no_pedido():
    cliente = ClienteFalso(json.dumps(TECLADO_VOGAIS))
    gerar_teclado("a" * 5000, cliente)
    _, pedido = cliente.pedidos[0]
    assert len(pedido) < 1000


# --- privacidade: so o pedido vai para a IA ----------------------------------------------

def test_prompt_nao_contem_dados_de_perfil_nem_palavras_aprendidas():
    cliente = ClienteFalso(json.dumps(TECLADO_VOGAIS))
    gerar_teclado("vogais", cliente)
    sistema, pedido = cliente.pedidos[0]
    assert "perfil" not in pedido.lower()
    assert "dicionario" not in pedido.lower() and "dicionário" not in pedido.lower()
    assert "perfil" not in sistema.lower()
    assert pedido == prompt_utilizador("vogais")


def test_prompt_de_sistema_lista_as_acoes_permitidas():
    texto = prompt_sistema()
    for acao in ("apagar_palavra", "minimizar_teclado", "ctrl", "multitoque", "navegar"):
        assert acao in texto


# --- configuracao local -------------------------------------------------------------------

def test_config_ausente_nao_tem_chave(tmp_path):
    assert carregar_config(tmp_path).configurada is False


def test_config_guardada_e_lida(tmp_path):
    guardar_config(tmp_path, ConfigIA(chave="  gsk_teste  ", modelo="m1"))
    lida = carregar_config(tmp_path)
    assert lida.chave == "gsk_teste"
    assert lida.modelo == "m1"
    assert lida.configurada


def test_config_corrompida_nao_rebenta(tmp_path):
    (tmp_path / "ia.json").write_text("{ isto nao e json", encoding="utf-8")
    assert carregar_config(tmp_path).configurada is False


def test_cliente_sem_chave_recusa_arrancar():
    with pytest.raises(IAErro, match="chave"):
        ClienteOpenAI(ConfigIA(chave=""))


# --- cliente HTTP (sem rede: urlopen substituido) --------------------------------------------

class _Resposta:
    def __init__(self, corpo):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_cliente_envia_pedido_compativel_com_openai(monkeypatch):
    enviado = {}

    def falso(pedido, timeout):
        enviado["url"] = pedido.full_url
        enviado["cabecalhos"] = dict(pedido.headers)
        enviado["corpo"] = json.loads(pedido.data.decode("utf-8"))
        resposta = {"choices": [{"message": {"content": "{}"}}]}
        return _Resposta(json.dumps(resposta).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", falso)
    cliente = ClienteOpenAI(ConfigIA(chave="gsk_x", modelo="modelo-teste"))
    assert cliente.completar("sistema", "pedido") == "{}"
    assert enviado["url"].endswith("/chat/completions")
    assert enviado["cabecalhos"]["Authorization"] == "Bearer gsk_x"
    assert enviado["corpo"]["model"] == "modelo-teste"
    assert enviado["corpo"]["messages"][1]["content"] == "pedido"


def test_erro_401_mostra_mensagem_sobre_a_chave(monkeypatch):
    def falso(pedido, timeout):
        raise urllib.error.HTTPError(pedido.full_url, 401, "x", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", falso)
    with pytest.raises(IAErro, match="chave"):
        ClienteOpenAI(ConfigIA(chave="x")).completar("s", "p")


def test_sem_ligacao_mostra_mensagem_legivel(monkeypatch):
    def falso(pedido, timeout):
        raise urllib.error.URLError("sem rede")

    monkeypatch.setattr("urllib.request.urlopen", falso)
    with pytest.raises(IAErro, match="ligar"):
        ClienteOpenAI(ConfigIA(chave="x")).completar("s", "p")
