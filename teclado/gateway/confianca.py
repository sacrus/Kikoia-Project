"""Confianca entre o PC e um telemovel ja emparelhado: ligacao automatica sem codigo.

Depois de um emparelhamento SPAKE2 bem-sucedido, PC e telemovel derivam do mesmo
segredo da troca um identificador e um segredo partilhado. Nas ligacoes seguintes
o telemovel apresenta o identificador, o PC envia um desafio (nonce novo) e os dois
provam que conhecem o segredo. Nenhum codigo e necessario.

O segredo fica guardado no PC (ficheiro confianca.json na pasta do utilizador) e no
telemovel. Quem o tiver pode ligar-se: por isso o ficheiro nao deve ser partilhado.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
import threading
from pathlib import Path

FICHEIRO = "confianca.json"
ID_RE = re.compile(r"[0-9a-f]{32}")
SEGREDO_RE = re.compile(r"[0-9a-f]{64}")
# Nome usado quando o Windows nao diz qual e o telemovel.
NOME_DESCONHECIDO = "bluetooth"


def _hmac(chave: bytes, rotulo: bytes) -> bytes:
    return hmac.new(chave, rotulo, hashlib.sha256).digest()


def derivar(chave_spake: bytes) -> tuple[str, bytes]:
    """Identificador (32 hex) e segredo de confianca a partir da chave SPAKE2 do emparelhamento."""
    ident = _hmac(chave_spake, b"gateway-id").hex()[:32]
    return ident, _hmac(chave_spake, b"gateway-confianca")


def prova(segredo: bytes, papel: str, nonce: str) -> str:
    """Prova de conhecer o segredo ('cliente' ou 'servidor') para este nonce."""
    return hmac.new(segredo, f"{papel}:{nonce}".encode("utf-8"), hashlib.sha256).hexdigest()


def chave_reconhecimento(segredo: bytes, nonce: str) -> bytes:
    """Chave SPAKE2 equivalente de uma ligacao reconhecida (a chave de sessao deriva dela)."""
    return hmac.new(segredo, f"reconhecer:{nonce}".encode("utf-8"), hashlib.sha256).digest()


class RepositorioConfianca:
    """Telemoveis de confianca guardados. Thread-safe: escritas vem da thread do gateway."""

    def __init__(self, pasta: Path) -> None:
        self._caminho = Path(pasta) / FICHEIRO
        self._trava = threading.Lock()

    def _ler(self) -> dict[str, dict]:
        try:
            dados = json.loads(self._caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(dados, dict):
            return {}
        return {
            k: v for k, v in dados.items()
            if ID_RE.fullmatch(k) and isinstance(v, dict)
            and isinstance(v.get("segredo"), str) and SEGREDO_RE.fullmatch(v["segredo"])
        }

    def _gravar(self, dados: dict[str, dict]) -> None:
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self._caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporario, self._caminho)

    def segredo(self, ident: str) -> bytes | None:
        with self._trava:
            entrada = self._ler().get(ident)
        return bytes.fromhex(entrada["segredo"]) if entrada else None

    def guardar(self, ident: str, segredo: bytes, nome: str) -> None:
        with self._trava:
            dados = self._ler()
            dados[ident] = {"segredo": segredo.hex(), "nome": str(nome)[:60]}
            self._gravar(dados)

    def nomes(self) -> list[str]:
        """Nomes e enderecos dos telemoveis de confianca (ver pode_ser_emparelhado)."""
        with self._trava:
            return [str(v.get("nome", "")) for v in self._ler().values()]

    def atualizar_nome(self, ident: str, nome: str) -> None:
        """Guarda o nome real do telemovel quando ele se liga (o nome anterior pode ser generico)."""
        if not nome or nome == NOME_DESCONHECIDO:
            return
        with self._trava:
            dados = self._ler()
            if ident in dados and dados[ident].get("nome") != nome:
                dados[ident]["nome"] = nome[:60]
                self._gravar(dados)


def _normalizar(texto: str) -> str:
    """Compara nomes sem maiusculas nem espacos, e enderecos sem separadores (AA:BB:.. ou aabb..)."""
    limpo = texto.strip().lower()
    sem_separadores = re.sub(r"[:\-]", "", limpo)
    if re.fullmatch(r"[0-9a-f]{12}", sem_separadores):
        return sem_separadores
    return limpo


def dispositivos_emparelhados_windows() -> set[str] | None:
    """Nomes e enderecos dos dispositivos Bluetooth emparelhados no Windows. None fora do Windows."""
    if sys.platform != "win32":
        return None
    import winreg

    try:
        chave = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices",
        )
    except OSError:
        return set()
    encontrados: set[str] = set()
    with chave:
        indice = 0
        while True:
            try:
                sub = winreg.EnumKey(chave, indice)
            except OSError:
                break
            indice += 1
            encontrados.add(_normalizar(sub))
            try:
                with winreg.OpenKey(chave, sub) as dispositivo:
                    bruto, _ = winreg.QueryValueEx(dispositivo, "Name")
            except OSError:
                continue
            if isinstance(bruto, bytes):
                encontrados.add(_normalizar(bruto.rstrip(b"\x00").decode("utf-8", "replace")))
            else:
                encontrados.add(_normalizar(str(bruto)))
    return encontrados


def pode_ser_emparelhado(nomes_guardados: list[str], emparelhados: set[str] | None) -> bool:
    """True se algum telemovel de confianca estiver emparelhado no Windows.

    Se o nome do telemovel nao for conhecido (o Windows nao o indicou), basta haver algum
    dispositivo Bluetooth emparelhado: nao ha forma segura de o identificar.
    """
    if not emparelhados:
        return False
    conhecidos = [_normalizar(n) for n in nomes_guardados if n and n != NOME_DESCONHECIDO]
    if not conhecidos:
        return bool(nomes_guardados)
    return any(nome in emparelhados for nome in conhecidos)
