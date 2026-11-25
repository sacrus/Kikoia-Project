"""Localizacao das pastas de dados do projeto e do utilizador."""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DADOS_PROJETO = RAIZ / "data"


def pasta_dados_utilizador() -> Path:
    """Perfis, layouts e temas criados pelo utilizador (fora do projeto)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "teclado"
