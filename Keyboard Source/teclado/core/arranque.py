"""Arranque do teclado com o sistema (Windows: registo do utilizador; Linux: autostart XDG).

So mexe na entrada do proprio utilizador (sem administrador). O estado real e a propria
entrada do sistema: nao e guardado no perfil.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .paths import RAIZ

NOME = "Kikoia"
NOME_ANTIGO = "TecladoRemoto"  # entrada criada por versoes anteriores; removida ao gravar a nova
CHAVE_WINDOWS = r"Software\Microsoft\Windows\CurrentVersion\Run"
FICHEIRO_LINUX = "teclado-remoto.desktop"


def _interprete() -> str:
    """No Windows, pythonw.exe nao abre janela de consola ao arrancar."""
    executavel = Path(sys.executable)
    if sys.platform == "win32":
        pythonw = executavel.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return str(executavel)


def comando_arranque(raiz: Path = RAIZ) -> str:
    """Linha de comando que arranca o teclado (o executavel empacotado, ou a pasta do projeto)."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    raiz_txt = str(raiz)
    codigo = (
        f"import os,sys; os.chdir(r'{raiz_txt}'); sys.path.insert(0, r'{raiz_txt}'); "
        "import teclado.__main__ as m; sys.exit(m.main())"
    )
    return f'"{_interprete()}" -c "{codigo}"'


def ativado() -> bool:
    if sys.platform == "win32":
        return _win_existe(NOME)
    return linux_ativado()


def definir(ativo: bool, raiz: Path = RAIZ) -> None:
    """Liga ou desliga o arranque com o sistema. Lanca OSError se o sistema recusar."""
    if sys.platform == "win32":
        _win_apagar(NOME_ANTIGO)
        if ativo:
            _win_gravar(NOME, comando_arranque(raiz))
        else:
            _win_apagar(NOME)
        return
    linux_definir(ativo, comando_arranque(raiz))


def linux_ativado(base: Path | None = None) -> bool:
    return _caminho_linux(base).exists()


def linux_definir(ativo: bool, comando: str, base: Path | None = None) -> None:
    caminho = _caminho_linux(base)
    if ativo:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(_entrada_desktop(comando), encoding="utf-8")
    elif caminho.exists():
        caminho.unlink()


def _caminho_linux(base: Path | None) -> Path:
    pasta = base or (Path.home() / ".config")
    return pasta / "autostart" / FICHEIRO_LINUX


def _entrada_desktop(comando: str) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Kikoia\n"
        f"Exec={comando}\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def _win_existe(nome: str) -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_WINDOWS) as chave:
            winreg.QueryValueEx(chave, nome)
        return True
    except OSError:
        return False


def _win_gravar(nome: str, comando: str) -> None:
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, CHAVE_WINDOWS, 0, winreg.KEY_SET_VALUE) as chave:
        winreg.SetValueEx(chave, nome, 0, winreg.REG_SZ, comando)


def _win_apagar(nome: str) -> None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_WINDOWS, 0, winreg.KEY_SET_VALUE) as chave:
            winreg.DeleteValue(chave, nome)
    except FileNotFoundError:
        pass
