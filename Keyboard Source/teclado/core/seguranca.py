"""Codigo do adulto (PIN): guardado apenas como hash PBKDF2 com sal."""

import hashlib
import hmac
import secrets

ALGORITMO = "pbkdf2_sha256"
ITERACOES = 200_000
TAMANHO_MINIMO_PIN = 4


def gerar_hash_pin(pin: str) -> str:
    if not pin or len(pin) < TAMANHO_MINIMO_PIN:
        raise ValueError(f"O codigo deve ter pelo menos {TAMANHO_MINIMO_PIN} caracteres.")
    sal = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), sal, ITERACOES)
    return f"{ALGORITMO}${ITERACOES}${sal.hex()}${digest.hex()}"


def verificar_pin(pin: str, guardado: str | None) -> bool:
    if not pin or not guardado:
        return False
    try:
        algoritmo, iteracoes, sal_hex, digest_hex = guardado.split("$")
        if algoritmo != ALGORITMO:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", pin.encode("utf-8"), bytes.fromhex(sal_hex), int(iteracoes)
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)
