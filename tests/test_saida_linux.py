import ctypes
import sys

import pytest

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="uinput so existe no Linux")

from teclado.core.saida import linux as saida_linux  # noqa: E402
from teclado.core.saida.xkb import DESLOCAMENTO_XKB, MapaTeclas, _biblioteca  # noqa: E402

LAYOUT = ("pt", "", "")


@pytest.fixture(scope="module")
def mapa():
    try:
        return MapaTeclas(*LAYOUT)
    except (RuntimeError, OSError) as erro:
        pytest.skip(f"libxkbcommon ou layout 'pt' indisponivel: {erro}")


def _texto_no_xkb(mapa: MapaTeclas, eventos: list[tuple[int, bool]]) -> str:
    """Reproduz os eventos no motor XKB (mesmo layout) e devolve o texto produzido."""
    lib = _biblioteca()
    estado = lib.xkb_state_new(mapa._keymap)
    atualizar = lib.xkb_state_update_key
    atualizar.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int]
    atualizar.restype = ctypes.c_int
    lib.xkb_state_key_get_utf8.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
    lib.xkb_state_key_get_utf8.restype = ctypes.c_int
    texto = ""
    for codigo, pressionada in eventos:
        xkb = codigo + DESLOCAMENTO_XKB
        if pressionada:
            buffer = ctypes.create_string_buffer(16)
            lib.xkb_state_key_get_utf8(estado, xkb, buffer, 16)
            texto += buffer.value.decode("utf-8")
        atualizar(estado, xkb, 1 if pressionada else 0)
    return texto


class _SaidaSemDispositivo(saida_linux.SaidaLinux):
    """Guarda os eventos em vez de os enviar ao kernel."""

    def __init__(self, mapa: MapaTeclas) -> None:
        self._mapa = mapa
        self._lock = saida_linux.threading.RLock()
        self._ultimo_apagar = 0.0
        self._avisados = set()
        self._dono_clipboard = None
        self.eventos: list[tuple[int, bool]] = []

        class _Captura:
            def enviar(captura, eventos):
                self.eventos.extend(eventos)

        self._teclado = _Captura()


def test_caracteres_com_tecla_propria(mapa):
    assert mapa.passos_para_caracter("a") == [(30, ())]
    assert mapa.passos_para_caracter("ç") == [(39, ())]


def test_maiuscula_usa_shift(mapa):
    (tecla, modificadores), = mapa.passos_para_caracter("A")
    assert tecla == 30
    assert modificadores == (mapa.tecla_modificador("shift"),)


def test_acento_sem_tecla_propria_e_tecla_morta_mais_letra(mapa):
    passos = mapa.passos_para_caracter("ã")
    assert passos is not None and len(passos) == 2
    assert passos[1] == (30, ())  # a letra base


def test_arroba_usa_altgr(mapa):
    (tecla, modificadores), = mapa.passos_para_caracter("@")
    assert modificadores == (mapa.tecla_modificador("altgr"),)


def test_teclas_de_atalho_do_layout(mapa):
    assert mapa.tecla_base("c") is not None
    assert mapa.tecla_modificador("ctrl") is not None


def test_texto_reproduzido_no_xkb_e_o_esperado(mapa):
    saida = _SaidaSemDispositivo(mapa)
    # Sem acentos com tecla morta: o estado XKB simples nao faz a composicao que o compositor faz.
    saida._enviar_texto("Ç ç @ A z ?!")
    assert _texto_no_xkb(mapa, saida.eventos) == "Ç ç @ A z ?!"


def test_enter_e_tab_nao_passam_pelo_mapa(mapa):
    saida = _SaidaSemDispositivo(mapa)
    saida._enviar_texto("\n")
    assert saida.eventos[:2] == [(28, True), (28, False)]


def test_carater_sem_tecla_cola_pela_area_de_transferencia(mapa, monkeypatch):
    colados = []

    class DonoFalso:
        def definir(self, texto):
            colados.append(texto)

    monkeypatch.setattr(saida_linux.x11, "DonoClipboard", DonoFalso)
    saida = _SaidaSemDispositivo(mapa)
    saida._enviar_texto("😀")
    assert colados == ["😀"]
    ctrl, v = mapa.tecla_modificador("ctrl"), mapa.tecla_base("v")
    assert saida.eventos == [(ctrl, True), (v, True), (v, False), (ctrl, False)]


def test_caps_lock_inverte_o_shift_das_letras(mapa, monkeypatch):
    monkeypatch.setattr(saida_linux, "caps_lock_ativo", lambda: True)
    saida = _SaidaSemDispositivo(mapa)
    saida._enviar_texto("a")
    shift = mapa.tecla_modificador("shift")
    assert saida.eventos == [(shift, True), (30, True), (30, False), (shift, False)]


def test_caps_lock_nao_muda_digitos_nem_sinais(mapa, monkeypatch):
    monkeypatch.setattr(saida_linux, "caps_lock_ativo", lambda: True)
    saida = _SaidaSemDispositivo(mapa)
    saida._enviar_texto("1")
    assert saida.eventos == [(mapa.tecla_base("1"), True), (mapa.tecla_base("1"), False)]


def test_inverter_shift_adiciona_e_retira_o_shift():
    assert saida_linux.inverter_shift([(30, ())], 42) == [(30, (42,))]
    assert saida_linux.inverter_shift([(30, (42,))], 42) == [(30, ())]
    assert saida_linux.inverter_shift([(30, ())], None) == [(30, ())]


def test_caps_lock_le_o_led_do_teclado(tmp_path):
    from teclado.core.saida.estado_teclado import caps_lock_ativo

    assert caps_lock_ativo(tmp_path) is False
    led = tmp_path / "input3::capslock"
    led.mkdir()
    (led / "brightness").write_text("0\n")
    assert caps_lock_ativo(tmp_path) is False
    (led / "brightness").write_text("1\n")
    assert caps_lock_ativo(tmp_path) is True
