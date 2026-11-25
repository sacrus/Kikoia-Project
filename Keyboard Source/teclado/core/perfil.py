"""Perfis de utilizador e respetivo armazenamento em JSON local."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .seguranca import gerar_hash_pin

# Acoes que o modo de supervisao pode proteger (apenas configuracoes).
AMBITO_POR_OMISSAO = ["alterar_layout", "alterar_tema", "definicoes"]
AMBITOS_VALIDOS = frozenset(AMBITO_POR_OMISSAO)

_ID_VALIDO = re.compile(r"[0-9a-f]{32}")


@dataclass
class Supervisao:
    ativa: bool = False
    codigo_hash: str | None = None
    ambito: list[str] = field(default_factory=lambda: list(AMBITO_POR_OMISSAO))


@dataclass
class Perfil:
    id: str
    nome: str
    supervisao: Supervisao = field(default_factory=Supervisao)
    preferencias: dict = field(default_factory=dict)

    def para_dicionario(self) -> dict:
        dados = asdict(self)
        sup = dados.pop("supervisao")
        dados["supervisao"] = {
            "ativa": sup["ativa"],
            "codigo_adulto_hash": sup["codigo_hash"],
            "ambito": sup["ambito"],
        }
        return dados

    @classmethod
    def de_dicionario(cls, dados: dict) -> "Perfil":
        sup = dados.get("supervisao", {})
        ambito = [a for a in sup.get("ambito", AMBITO_POR_OMISSAO) if a in AMBITOS_VALIDOS]
        return cls(
            id=dados["id"],
            nome=dados["nome"],
            supervisao=Supervisao(
                ativa=bool(sup.get("ativa", False)),
                codigo_hash=sup.get("codigo_adulto_hash"),
                ambito=ambito,
            ),
            preferencias=dict(dados.get("preferencias", {})),
        )


def criar_perfil(nome: str, supervisionado: bool, pin: str | None = None) -> Perfil:
    """Cria um perfil. Um perfil supervisionado exige um codigo do adulto."""
    nome = nome.strip()
    if not nome:
        raise ValueError("O perfil precisa de um nome.")
    if supervisionado:
        supervisao = Supervisao(ativa=True, codigo_hash=gerar_hash_pin(pin or ""))
    else:
        supervisao = Supervisao(ativa=False)
    return Perfil(id=uuid.uuid4().hex, nome=nome, supervisao=supervisao)


class RepositorioPerfis:
    """Guarda cada perfil num ficheiro JSON separado dentro de uma pasta."""

    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)

    def _caminho(self, perfil_id: str) -> Path:
        if not _ID_VALIDO.fullmatch(perfil_id):
            raise ValueError("Identificador de perfil invalido.")
        return self.pasta / f"{perfil_id}.json"

    def guardar(self, perfil: Perfil) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        destino = self._caminho(perfil.id)
        temporario = destino.with_suffix(".json.tmp")
        conteudo = json.dumps(perfil.para_dicionario(), ensure_ascii=False, indent=2)
        temporario.write_text(conteudo, encoding="utf-8")
        os.replace(temporario, destino)

    def carregar(self, perfil_id: str) -> Perfil:
        caminho = self._caminho(perfil_id)
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return Perfil.de_dicionario(dados)

    def listar(self) -> list[Perfil]:
        if not self.pasta.exists():
            return []
        perfis = []
        for ficheiro in sorted(self.pasta.glob("*.json")):
            if _ID_VALIDO.fullmatch(ficheiro.stem):
                perfis.append(self.carregar(ficheiro.stem))
        return perfis
