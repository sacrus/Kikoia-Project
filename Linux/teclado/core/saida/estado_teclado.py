"""Estado do teclado no Linux: Caps Lock, lido do LED do teclado em /sys/class/leds."""

from __future__ import annotations

from pathlib import Path

RAIZ_LEDS = Path("/sys/class/leds")


def caps_lock_ativo(raiz: Path = RAIZ_LEDS) -> bool:
    """True se algum LED de Caps Lock estiver aceso. Sem LED (ou sem leitura), False."""
    for brilho in raiz.glob("*capslock/brightness"):
        try:
            if brilho.read_text().strip() not in ("", "0"):
                return True
        except OSError:
            continue
    return False
