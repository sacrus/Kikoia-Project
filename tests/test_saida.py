import ctypes
import sys

import pytest

from teclado.core.saida import TECLAS_ESPECIAIS
from teclado.core.saida.windows import (
    INPUT,
    KEYEVENTF_KEYUP,
    KEYEVENTF_UNICODE,
    eventos_para_texto,
    eventos_para_tecla,
)


def test_tamanho_struct_input_correto():
    esperado = 40 if sys.maxsize > 2**32 else 28
    assert ctypes.sizeof(INPUT) == esperado


def test_texto_gera_par_down_up_por_caracter():
    eventos = eventos_para_texto("ã")
    assert len(eventos) == 2
    assert eventos[0].u.ki.wScan == ord("ã")
    assert eventos[0].u.ki.dwFlags & KEYEVENTF_UNICODE
    assert eventos[1].u.ki.dwFlags & KEYEVENTF_KEYUP


def test_caracter_fora_do_bmp_usa_par_de_surrogates():
    eventos = eventos_para_texto("😀")
    # 1 caracter -> 2 unidades UTF-16 -> 2 pares down/up = 4 eventos
    assert len(eventos) == 4
    assert eventos[0].u.ki.wScan == 0xD83D
    assert eventos[2].u.ki.wScan == 0xDE00


def test_tecla_especial_valida():
    for nome in TECLAS_ESPECIAIS:
        eventos = eventos_para_tecla(nome)
        assert len(eventos) == 2


def test_tecla_desconhecida_rejeitada():
    with pytest.raises(ValueError):
        eventos_para_tecla("nao_existe")

def test_sequencia_envia_acoes_em_ordem_com_pausa_apos_apagar(monkeypatch):
    from teclado.core.saida import windows as W
    if sys.platform != "win32":
        pytest.skip("Windows apenas")
    chamadas = []
    pausas = []
    monkeypatch.setattr(W.time, "sleep", lambda s: pausas.append(s))
    saida = W.SaidaWindows.__new__(W.SaidaWindows)
    saida._ultimo_apagar = 0.0
    saida._enviar = lambda eventos: chamadas.append(len(eventos))
    saida.sequencia([("tecla", "backspace"), ("tecla", "backspace"), ("texto", "é")])
    # 2 backspaces (2 eventos cada) e depois o texto (1 caracter = 2 eventos).
    assert chamadas == [2, 2, 2]
    # O texto so sai depois de uma pausa, porque um backspace acabou de ser enviado.
    assert pausas and pausas[-1] > 0


def test_sequencia_rejeita_tipo_desconhecido():
    from teclado.core.saida import windows as W
    if sys.platform != "win32":
        pytest.skip("Windows apenas")
    saida = W.SaidaWindows.__new__(W.SaidaWindows)
    saida._enviar = lambda eventos: None
    with pytest.raises(ValueError):
        saida.sequencia([("abrir", "x")])
