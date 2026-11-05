import array

import pytest
from PySide6.QtWidgets import QApplication

from teclado.core.nivel import (
    MSG_FRACO,
    MSG_SATURACAO,
    MSG_SILENCIO,
    AnaliseNivel,
    medir,
)
from teclado.ui.interruptor import Interruptor
from teclado.ui.medidor import PISO_DB, Medidor


def _bloco(valor, segundos=0.1):
    n = int(16000 * segundos)
    return array.array("h", [valor] * n).tobytes()


# --- medicao em decibeis ----------------------------------------------------

def test_sinal_maximo_da_zero_dbfs():
    rms, pico, dur = medir(_bloco(32767))
    assert pico == pytest.approx(0.0, abs=0.01)
    assert rms == pytest.approx(0.0, abs=0.01)
    assert dur == pytest.approx(0.1)


def test_sinal_a_metade_da_cerca_de_menos_6_db():
    rms, pico, _ = medir(_bloco(16384))
    assert -6.1 < pico < -5.9


def test_silencio_da_piso():
    rms, pico, _ = medir(_bloco(0))
    assert rms < -100 and pico < -100


def test_bloco_vazio_nao_falha():
    assert medir(b"")[2] == 0.0


# --- mensagens ------------------------------------------------------------------

def test_fala_fraca_sustentada_pede_para_falar_mais_alto():
    analise = AnaliseNivel()
    mensagens = [analise.atualizar(_bloco(300)).mensagem for _ in range(20)]  # ~-41 dB RMS
    assert mensagens[-1] == MSG_FRACO
    assert mensagens[0] is None  # nao aparece logo no primeiro bloco


def test_fala_normal_nao_gera_mensagem():
    analise = AnaliseNivel()
    mensagens = [analise.atualizar(_bloco(3000)).mensagem for _ in range(30)]
    assert all(m is None for m in mensagens)


def test_saturacao_sustentada_pede_para_afastar():
    analise = AnaliseNivel()
    mensagens = [analise.atualizar(_bloco(32000)).mensagem for _ in range(10)]
    assert mensagens[-1] == MSG_SATURACAO


def test_pico_isolado_nao_basta_para_a_mensagem():
    analise = AnaliseNivel()
    analise.atualizar(_bloco(32000, 0.1))
    assert analise.atualizar(_bloco(3000)).mensagem is None


def test_silencio_prolongado_pede_para_verificar_o_microfone():
    analise = AnaliseNivel()
    mensagens = [analise.atualizar(_bloco(0)).mensagem for _ in range(70)]  # 7 s
    assert mensagens[-1] == MSG_SILENCIO


def test_pausa_curta_entre_palavras_nao_zera_a_fala_fraca():
    analise = AnaliseNivel()
    for _ in range(10):
        analise.atualizar(_bloco(300))          # 1,0 s de fala fraca
    analise.atualizar(_bloco(0, 0.2))           # pausa curta
    mensagens = [analise.atualizar(_bloco(300)).mensagem for _ in range(8)]
    assert mensagens[-1] == MSG_FRACO


# --- widgets --------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_interruptor_alterna_com_o_clique(qapp):
    botao = Interruptor("Ditar")
    recebidos = []
    botao.toggled.connect(recebidos.append)
    botao.click()
    botao.click()
    assert recebidos == [True, False]
    assert botao.isCheckable()


def test_interruptor_continua_a_ser_botao_com_texto(qapp):
    botao = Interruptor("Falar")
    assert botao.text() == "Falar"


def test_medidor_limita_o_nivel_entre_zero_e_um(qapp):
    medidor = Medidor()
    medidor.definir_nivel_db(20.0)
    assert medidor._alvo == 1.0
    medidor.definir_nivel_db(PISO_DB - 50)
    assert medidor._alvo == 0.0
    medidor.close()
