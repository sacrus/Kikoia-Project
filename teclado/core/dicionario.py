"""Dicionario de sugestoes: lexico base por frequencia + palavras usadas pelo perfil.

- Base: ficheiro TSV "palavra<TAB>contagem", ordenado por frequencia (ver tools/gerar_lexico.py).
  Carregado uma vez em memoria; a pesquisa por prefixo usa bisect (rapida).
- Pessoal: SQLite local por perfil. Guarda contagem, ultima utilizacao e a forma
  com maiusculas (nomes proprios) quando a palavra foi escrita a meio de frase.

Ordem das sugestoes: primeiro as palavras usadas pelo perfil (mais usadas e
mais recentes), depois o lexico base por frequencia.
"""

from __future__ import annotations

import bisect
import sqlite3
import time
from pathlib import Path

FIM_DE_PREFIXO = "\U0010ffff"


class Dicionario:
    def __init__(
        self,
        base: dict[str, int] | None = None,
        pessoal_caminho: Path | None = None,
    ) -> None:
        self._freq: dict[str, int] = dict(base or {})
        self._chaves: list[str] = sorted(self._freq)
        self._bd: sqlite3.Connection | None = None
        if pessoal_caminho is not None:
            pessoal_caminho.parent.mkdir(parents=True, exist_ok=True)
            self._bd = sqlite3.connect(pessoal_caminho)
            self._bd.execute(
                """CREATE TABLE IF NOT EXISTS uso (
                       palavra TEXT PRIMARY KEY,
                       forma TEXT,
                       contagem INTEGER NOT NULL,
                       ultima INTEGER NOT NULL)"""
            )
            self._bd.commit()

    @classmethod
    def carregar(cls, lexico: Path, pessoal: Path | None = None) -> "Dicionario":
        base: dict[str, int] = {}
        for linha in Path(lexico).read_text(encoding="utf-8").splitlines():
            partes = linha.split("\t")
            if len(partes) == 2 and partes[1].isdigit():
                base[partes[0]] = int(partes[1])
        return cls(base, pessoal)

    def fechar(self) -> None:
        if self._bd is not None:
            self._bd.close()
            self._bd = None

    # --- pesquisa --------------------------------------------------------

    def _base_com_prefixo(self, prefixo: str) -> list[str]:
        inicio = bisect.bisect_left(self._chaves, prefixo)
        fim = bisect.bisect_left(self._chaves, prefixo + FIM_DE_PREFIXO)
        candidatas = self._chaves[inicio:fim]
        candidatas.sort(key=lambda p: -self._freq[p])
        return candidatas

    def _pessoais_com_prefixo(self, prefixo: str, limite: int) -> list[str]:
        if self._bd is None or limite <= 0:
            return []
        cursor = self._bd.execute(
            """SELECT COALESCE(forma, palavra) FROM uso
               WHERE palavra >= ? AND palavra < ?
               ORDER BY contagem DESC, ultima DESC
               LIMIT ?""",
            (prefixo, prefixo + FIM_DE_PREFIXO, limite),
        )
        return [linha[0] for linha in cursor.fetchall()]

    def sugerir(self, prefixo: str, maximo: int = 5) -> list[str]:
        """Sugestoes para o prefixo (sem maiusculas automaticas; isso e papel do Editor)."""
        chave = prefixo.lower()
        if not chave or maximo <= 0:
            return []
        resultado: list[str] = []
        vistas: set[str] = set()
        for forma in self._pessoais_com_prefixo(chave, maximo):
            if forma.lower() not in vistas:
                vistas.add(forma.lower())
                resultado.append(forma)
        for palavra in self._base_com_prefixo(chave):
            if len(resultado) >= maximo:
                break
            if palavra not in vistas:
                vistas.add(palavra)
                resultado.append(palavra)
        return resultado[:maximo]

    # --- aprendizagem ----------------------------------------------------

    def aprender(self, palavra: str, inicio_frase: bool = False) -> None:
        """Regista uma palavra escrita.

        inicio_frase: se True, a maiuscula inicial veio da regra de frase e nao do
        utilizador, por isso nao e guardada como nome proprio.
        """
        chave = palavra.lower()
        if not chave or not chave.isalpha():
            return
        # O lexico base nunca muda; a aprendizagem fica so na tabela pessoal.
        if self._bd is None:
            return
        preferida = palavra if (not inicio_frase and palavra[:1].isupper()) else None
        self._bd.execute(
            """INSERT INTO uso (palavra, forma, contagem, ultima) VALUES (?, ?, 1, ?)
               ON CONFLICT(palavra) DO UPDATE SET
                   contagem = contagem + 1,
                   ultima = excluded.ultima,
                   forma = COALESCE(excluded.forma, uso.forma)""",
            (chave, preferida, int(time.time())),
        )
        self._bd.commit()
