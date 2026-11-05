"""Criacao de teclados por pedido escrito (IA).

Fluxo: o adulto descreve o teclado em texto -> um modelo de linguagem devolve JSON
no formato de layout -> o JSON passa pela mesma validacao de qualquer teclado ->
o utilizador ve a pre-visualizacao e so depois guarda (com a politica de supervisao).

Privacidade: so o pedido do adulto e enviado. Nunca perfis, palavras aprendidas,
historico de uso ou o conteudo do teclado atual.

Fornecedor por omissao: Groq (plano gratuito, API compativel com OpenAI).
Os nomes dos modelos mudam com frequencia; por isso o modelo e configuravel.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .acentos import ACENTOS
from .comandos import novo_id, validar as validar_comando
from .layout_editor import validar_modelo
from .saida import ACOES, TECLAS_ESPECIAIS

ENDPOINT_POR_OMISSAO = "https://api.groq.com/openai/v1/chat/completions"
MODELO_POR_OMISSAO = "openai/gpt-oss-20b"
TIMEOUT_SEGUNDOS = 45
MAX_TOKENS = 2048  # modelos de raciocinio gastam tokens antes da resposta
MAX_DESCRICAO = 500
MAX_TECLAS_PEDIDAS = 80
FICHEIRO_CONFIG = "ia.json"


class IAErro(RuntimeError):
    """Falha ao obter ou interpretar a resposta da IA. A mensagem e para o utilizador."""


class ClienteIA(Protocol):
    def completar(self, sistema: str, pedido: str) -> str: ...


@dataclass(frozen=True)
class ConfigIA:
    chave: str = ""
    modelo: str = MODELO_POR_OMISSAO
    endpoint: str = ENDPOINT_POR_OMISSAO

    @property
    def configurada(self) -> bool:
        return bool(self.chave.strip())


# --- configuracao local (fora do projeto e fora do perfil) ----------------------

def carregar_config(pasta: Path) -> ConfigIA:
    caminho = Path(pasta) / FICHEIRO_CONFIG
    if not caminho.is_file():
        return ConfigIA()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ConfigIA()
    return ConfigIA(
        chave=str(dados.get("chave", "")),
        modelo=str(dados.get("modelo") or MODELO_POR_OMISSAO),
        endpoint=str(dados.get("endpoint") or ENDPOINT_POR_OMISSAO),
    )


def guardar_config(pasta: Path, config: ConfigIA) -> None:
    """Grava a configuracao. A chave fica so neste computador, num ficheiro do utilizador."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    dados = {"chave": config.chave.strip(), "modelo": config.modelo, "endpoint": config.endpoint}
    destino = pasta / FICHEIRO_CONFIG
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


# --- prompt -----------------------------------------------------------------------

def _lista(itens) -> str:
    return ", ".join(sorted(itens))


def prompt_sistema() -> str:
    """Instrucoes ao modelo: formato exato, valores permitidos e regras de seguranca."""
    return f"""Respondes APENAS com um objeto JSON valido, sem texto antes ou depois.

Formato:
{{"nome": "texto curto (1 a 40 caracteres)",
  "idioma": "pt-PT",
  "linhas": [ [tecla, tecla, ...], [tecla, ...] ],
  "comandos": [ {{"id": "c1", "rotulo": "nome da tecla (ate 30)", "comando": "caminho completo do programa ou comando (ate 300)"}} ] (opcional)}}

Cada tecla e um objeto:
{{"rotulo": "o que aparece (ate 30 caracteres)",
  "acao": {{"tipo": "...", "valor": "..."}},
  "largura": numero entre 0.5 e 6 (opcional, 1 por omissao)}}

Tipos de acao permitidos:
- "texto": valor = a letra, acento ou simbolo a escrever (ex.: "a", "é", "7", ".")
- "tecla": valor = uma de [{_lista(TECLAS_ESPECIAIS)}]
- "acento": valor = uma de [{_lista(ACENTOS)}]
- "modificador": valor = "shift" ou "ctrl"
- "acao": valor = uma de [{_lista(ACOES)}]
- "multitoque": valor = 2 a 12 letras por ordem (ex.: "abc"), tipo telefone
- "navegar": valor = nome de outro teclado; "__anterior__" volta ao anterior
- "comando": valor = o id de uma entrada da lista "comandos" (ex.: "c1"). Use-o so quando
  o pedido indicar um programa ou comando concreto a executar no computador.

Regras:
- No maximo {MAX_TECLAS_PEDIDAS} teclas no total.
- Usa apenas os tipos e valores listados. Nao inventes outros.
- Para letras acentuadas, usa "texto" com a letra ja acentuada.
- Mantem o teclado simples e grande para uma crianca ou um adulto com dificuldades motoras:
  poucas teclas por linha quando o pedido for simples.
"""


def prompt_utilizador(descricao: str) -> str:
    texto = descricao.strip()[:MAX_DESCRICAO]
    return f"Cria um teclado com esta descricao:\n{texto}"


# --- interpretacao da resposta -----------------------------------------------------

_BLOCO_CODIGO = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extrair_json(texto: str) -> dict:
    """Aceita JSON puro ou dentro de um bloco de codigo. Devolve o objeto."""
    if not texto or not texto.strip():
        raise IAErro("A IA não devolveu nenhum teclado. Tente descrever de outra forma.")
    candidatos = [texto.strip()]
    candidatos += [m.group(1).strip() for m in _BLOCO_CODIGO.finditer(texto)]
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio != -1 and fim > inicio:
        candidatos.append(texto[inicio:fim + 1])
    for candidato in candidatos:
        try:
            dados = json.loads(candidato)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict):
            return dados
    raise IAErro("A resposta da IA não estava em formato de teclado. Tente de novo.")


MAX_COMANDOS_IA = 10


def gerar_pacote(
    descricao: str, cliente: ClienteIA, nome_por_omissao: str = "Teclado IA",
) -> tuple[dict, list[dict]]:
    """Pede um teclado e os comandos que ele usa. Devolve (modelo, comandos), ja validados.

    Os comandos recebem identificadores novos (nunca substituem os existentes) e as teclas
    que os usam sao reapontadas para esses identificadores. Nada e gravado aqui: quem chama
    mostra a pre-visualizacao e so guarda depois de confirmacao.
    """
    if not descricao.strip():
        raise IAErro("Descreva o teclado que pretende.")
    bruto = cliente.completar(prompt_sistema(), prompt_utilizador(descricao))
    dados = extrair_json(bruto)

    brutos = dados.pop("comandos", None) or []
    if not isinstance(brutos, list) or len(brutos) > MAX_COMANDOS_IA:
        raise IAErro("A IA propôs comandos em formato inválido.")
    mapa: dict[str, str] = {}
    comandos: list[dict] = []
    for item in brutos:
        if not isinstance(item, dict):
            raise IAErro("A IA propôs um comando em formato inválido.")
        try:
            rotulo, comando = validar_comando(item.get("rotulo"), item.get("comando"))
        except ValueError as erro:
            raise IAErro(f"Comando proposto inválido: {erro}") from erro
        ident = novo_id()
        mapa[str(item.get("id"))] = ident
        comandos.append({"id": ident, "rotulo": rotulo, "comando": comando})
    _reapontar_comandos(dados, mapa)

    if not isinstance(dados.get("nome"), str) or not dados["nome"].strip():
        dados["nome"] = nome_por_omissao
    dados.setdefault("idioma", "pt-PT")
    dados["nome"] = dados["nome"].strip()[:40]
    try:
        validar_modelo(dados)
    except Exception as erro:  # LayoutInvalido: a mensagem ja e legivel
        raise IAErro(f"O teclado proposto não é válido: {erro}") from erro
    return dados, comandos


def _reapontar_comandos(modelo: dict, mapa: dict[str, str]) -> None:
    for linha in modelo.get("linhas") or []:
        if not isinstance(linha, list):
            continue
        for tecla in linha:
            acao = tecla.get("acao") if isinstance(tecla, dict) else None
            if isinstance(acao, dict) and acao.get("tipo") == "comando":
                if acao.get("valor") not in mapa:
                    raise IAErro("Uma tecla usa um comando que a IA não definiu.")
                acao["valor"] = mapa[acao["valor"]]


def gerar_teclado(descricao: str, cliente: ClienteIA, nome_por_omissao: str = "Teclado IA") -> dict:
    """Como gerar_pacote, mas devolve so o modelo (sem comandos)."""
    modelo, _ = gerar_pacote(descricao, cliente, nome_por_omissao)
    return modelo


# --- cliente HTTP ------------------------------------------------------------------

class ClienteOpenAI:
    """Cliente minimo para a API de chat compativel com OpenAI (sem dependencias extra)."""

    def __init__(self, config: ConfigIA, timeout: float = TIMEOUT_SEGUNDOS) -> None:
        if not config.configurada:
            raise IAErro("Falta a chave da IA. Configure-a em Definições > Criar com IA.")
        self._config = config
        self._timeout = timeout

    def completar(self, sistema: str, pedido: str) -> str:
        corpo = json.dumps({
            "model": self._config.modelo,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": pedido},
            ],
            "temperature": 0.2,
            "max_tokens": MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        pedido_http = urllib.request.Request(
            self._config.endpoint,
            data=corpo,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._config.chave.strip()}",
                "User-Agent": "teclado-adaptativo/0.1",
            },
        )
        try:
            with urllib.request.urlopen(pedido_http, timeout=self._timeout) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            raise IAErro(_mensagem_http(erro.code)) from erro
        except (urllib.error.URLError, TimeoutError, OSError) as erro:
            raise IAErro("Não foi possível ligar à IA. Verifique a ligação à internet.") from erro
        except json.JSONDecodeError as erro:
            raise IAErro("A IA devolveu uma resposta inesperada.") from erro
        try:
            return dados["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as erro:
            raise IAErro("A IA devolveu uma resposta inesperada.") from erro


def _mensagem_http(codigo: int) -> str:
    if codigo in (401, 403):
        return "A chave da IA não é aceite. Verifique-a nas definições."
    if codigo == 429:
        return "Limite de pedidos da IA atingido. Tente daqui a um minuto."
    if codigo >= 500:
        return "O serviço de IA está indisponível de momento."
    return f"A IA recusou o pedido (erro {codigo})."
