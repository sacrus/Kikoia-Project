"""Estado do teclado no Linux: Caps Lock lido do LED em /sys/class/leds com fallback X11 (`LockMask`)."""

from __future__ import annotations

from pathlib import Path

RAIZ_LEDS = Path("/sys/class/leds")


def _caps_lock_x11() -> bool:
    try:
        from Xlib import X, display

        d = display.Display()
        try:
            ptr = d.screen().root.query_pointer()
            return bool(ptr.mask & X.LockMask)
        finally:
            d.close()
    except Exception:
        return False


def caps_lock_ativo(raiz: Path = RAIZ_LEDS) -> bool:
    """True se algum LED de Caps Lock estiver aceso (ou se `LockMask` estiver ativo no X11)."""
    encontrou_led = False
    for brilho in raiz.glob("*capslock/brightness"):
        encontrou_led = True
        try:
            if brilho.read_text().strip() not in ("", "0"):
                return True
        except OSError:
            continue
    if not encontrou_led and raiz == RAIZ_LEDS:
        return _caps_lock_x11()
    return False
