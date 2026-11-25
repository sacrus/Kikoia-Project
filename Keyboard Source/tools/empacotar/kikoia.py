"""Ponto de entrada do executavel (PyInstaller). Ver kikoia.spec."""

import sys

from teclado.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
