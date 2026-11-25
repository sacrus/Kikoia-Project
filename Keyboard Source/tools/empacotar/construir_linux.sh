#!/usr/bin/env bash
# Gera o executavel do Kikoia para Linux (PyInstaller) e um pacote .tar.gz no ambiente de trabalho.
# Correr numa maquina Linux, a partir da pasta do projeto:
#   pip install -r requirements.txt pyinstaller
#   bash tools/empacotar/construir_linux.sh
# O PyInstaller so gera executaveis para o sistema onde corre: este script nao serve para Windows.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="${TMPDIR:-/tmp}/kikoia_build"
SAIDA="${HOME}/Desktop"
VERSAO="$(python3 -c 'import re,pathlib; print(re.search(r"VERSAO = \"([^\"]+)\"", pathlib.Path("teclado/core/atualizacao.py").read_text(encoding="utf-8")).group(1))')"
ARQUIVO="${SAIDA}/Kikoia-${VERSAO}-Linux-x86_64.tar.gz"

cd "$RAIZ"
rm -rf "$TMP"
PYTHONUTF8=1 python3 -m PyInstaller --noconfirm \
    --distpath "$TMP/dist" --workpath "$TMP/build" \
    tools/empacotar/kikoia.spec

# O script que prepara as permissoes do teclado virtual (uinput) segue junto com o executavel.
cp tools/configurar_teclado_linux.sh "$TMP/dist/Kikoia/"
tar -C "$TMP/dist" -czf "$ARQUIVO" Kikoia
echo "Pacote: $ARQUIVO"
