import array

from teclado.core.voz import GANHO_ALVO, GANHO_MAXIMO, normalizar_ganho


def _bloco(valor, n=800):
    return array.array("h", [valor] * n).tobytes()


def _pico(bloco):
    return max(abs(v) for v in array.array("h", bloco))


def test_sinal_fraco_e_amplificado_com_o_ganho_maximo():
    estado = {}
    # 400 * 50 passaria o alvo, mas o ganho e limitado a GANHO_MAXIMO (40).
    saida = normalizar_ganho(_bloco(400), estado)
    assert _pico(saida) == int(400 * GANHO_MAXIMO)


def test_sinal_medio_chega_ao_alvo():
    estado = {}
    saida = normalizar_ganho(_bloco(1000), estado)
    assert _pico(saida) == GANHO_ALVO


def test_sinal_forte_nao_e_reduzido():
    estado = {}
    entrada = _bloco(25000)
    assert normalizar_ganho(entrada, estado) == entrada


def test_ruido_de_fundo_nao_e_amplificado_sem_limite():
    estado = {}
    saida = normalizar_ganho(_bloco(5), estado)
    assert _pico(saida) <= 5 * GANHO_MAXIMO + 1


def test_ganho_nao_sobe_de_forma_brusca_apos_sinal_forte():
    estado = {}
    normalizar_ganho(_bloco(20000), estado)
    # O pico de referencia desce devagar: um bloco fraco logo a seguir continua com ganho baixo.
    saida = normalizar_ganho(_bloco(100), estado)
    assert _pico(saida) < GANHO_ALVO


def test_valores_nunca_estouram_int16():
    estado = {}
    saida = normalizar_ganho(_bloco(300), estado)
    assert all(-32768 <= v <= 32767 for v in array.array("h", saida))
