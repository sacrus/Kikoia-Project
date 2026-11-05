# -*- mode: python ; coding: utf-8 -*-
# Gerar o executavel do Windows: ver tools/empacotar/construir_windows.ps1

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

RAIZ = Path(SPECPATH).resolve().parents[1]

datas = [(str(RAIZ / "data"), "data")]
binaries = []
hiddenimports = []
pacotes = ["vosk", "sounddevice"]
if sys.platform == "win32":
    # Bluetooth no Windows: os modulos winrt sao carregados dinamicamente e o PyInstaller nao os ve.
    pacotes.append("winrt")
for pacote in pacotes:
    dados, libs, ocultos = collect_all(pacote)
    datas += dados
    binaries += libs
    hiddenimports += ocultos

a = Analysis(
    [str(Path(SPECPATH) / "kikoia.py")],
    pathex=[str(RAIZ)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Kikoia",
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="Kikoia",
)
