import time

import pytest

from teclado.core.aplicacao import Aplicacao
from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.paths import DADOS_PROJETO
from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.core.voz import (
    SinteseFalada,
    VozIndisponivel,
    escolher_voz_portuguesa,
    modelo_vosk_presente,
    verificar_reconhecimento,
)


class Registo:
    def __init__(self):
        self.eventos = []

    def escrever(self, texto):
        self.eventos.append(("texto", texto))

    def tecla(self, nome):
        self.eventos.append(("tecla", nome))

    def sequencia(self, acoes):
        self.eventos.extend(acoes)


class FalaFalsa:
    def __init__(self):
        self.ditas = []
        self.voz = None

    def setProperty(self, nome, valor):
        if nome == "voice":
            self.voz = valor

    def say(self, texto):
        self.ditas.append(texto)

    def runAndWait(self):
        pass


def _editor(voz=None, base=None):
    ditas = []
    registo = Registo()
    editor = Editor(registo, Dicionario(base or {"casa": 5, "cama": 2}), ao_falar=ditas.append)
    return editor, registo, ditas


# --- editor: leitura -------------------------------------------------------

def test_sem_opcoes_nada_e_lido():
    editor, _, ditas = _editor()
    editor.texto("ola ")
    assert ditas == []


def test_ler_palavra_ao_completar_com_espaco():
    editor, _, ditas = _editor()
    editor.falar_palavra = True
    editor.texto("ola ")
    assert ditas == ["Ola"]


def test_ler_palavra_nao_le_palavra_incompleta():
    editor, _, ditas = _editor()
    editor.falar_palavra = True
    editor.texto("ol")
    assert ditas == []


def test_ler_frase_ao_terminar_com_ponto():
    editor, _, ditas = _editor()
    editor.falar_frase = True
    editor.texto("ola amigo.")
    assert ditas == ["Ola amigo."]


def test_ler_frase_ao_terminar_com_enter():
    editor, _, ditas = _editor()
    editor.falar_frase = True
    editor.texto("bom dia")
    editor.tecla("enter")
    assert ditas == ["Bom dia"]


def test_backspace_retira_do_texto_lido():
    editor, _, ditas = _editor()
    editor.falar_frase = True
    editor.texto("olaa")
    editor.tecla("backspace")
    editor.texto(".")
    assert ditas == ["Ola."]


def test_ler_sugestao_escolhida():
    editor, _, ditas = _editor()
    editor.falar_sugestao = True
    editor.texto("ca")
    editor.usar_sugestao(0)
    # Inicio de frase: a sugestao sai com maiuscula, e e isso que e lido.
    assert ditas == ["Casa"]


def test_sugestao_sem_opcao_nao_le():
    editor, _, ditas = _editor()
    editor.texto("ca")
    editor.usar_sugestao(0)
    assert ditas == []


def test_frase_acumulada_com_sugestao_fica_completa():
    editor, _, ditas = _editor()
    editor.falar_frase = True
    editor.texto("vou ")
    editor.texto("ca")
    editor.usar_sugestao(0)
    editor.texto(".")
    # A sugestao deixa o espaco automatico; o ponto cola-se a palavra.
    assert ditas == ["Vou casa."]


def test_motor_que_falha_ao_arrancar_e_reportado():
    def fabrica():
        raise OSError("motor ausente")

    sintese = SinteseFalada(fabrica)
    assert sintese.aguardar_pronto() is False
    assert isinstance(sintese.erro, OSError)
    sintese.fechar()


def test_ligar_falar_ativa_leitura_de_palavra_e_frase(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    app.alternar_falar(True)
    prefs = app.preferencias_voz()
    assert prefs["falar"] is True and prefs["ler_palavra"] is True and prefs["ler_frase"] is True
    app.alternar_falar(False)
    assert app.preferencias_voz()["falar"] is False


def test_ligar_voz_troca_o_destino():
    editor, _, ditas = _editor()
    outras = []
    editor.ligar_voz(outras.append)
    editor.falar_palavra = True
    editor.texto("ola ")
    assert ditas == [] and outras == ["Ola"]


# --- sintese (motor falso, sem audio) --------------------------------------

def _esperar(condicao, limite=2.0):
    fim = time.time() + limite
    while time.time() < fim:
        if condicao():
            return True
        time.sleep(0.01)
    return False


def test_sintese_fala_por_ordem_numa_thread():
    motor = FalaFalsa()
    sintese = SinteseFalada(lambda: motor)
    sintese.falar("um")
    sintese.falar("dois")
    assert _esperar(lambda: motor.ditas == ["um", "dois"])
    sintese.fechar()


def test_sintese_usa_a_voz_escolhida():
    motor = FalaFalsa()
    sintese = SinteseFalada(lambda: motor, voz_id="VOZ-X")
    sintese.falar("ola")
    assert _esperar(lambda: motor.ditas == ["ola"])
    assert motor.voz == "VOZ-X"
    sintese.fechar()


def test_sintese_ignora_texto_vazio():
    motor = FalaFalsa()
    sintese = SinteseFalada(lambda: motor)
    sintese.falar("   ")
    sintese.falar("")
    sintese.falar("ok")
    assert _esperar(lambda: motor.ditas == ["ok"])
    sintese.fechar()


def test_erro_do_motor_nao_mata_a_fila():
    class Partido(FalaFalsa):
        def say(self, texto):
            if texto == "mau":
                raise RuntimeError("falha do motor")
            super().say(texto)

    motor = Partido()
    sintese = SinteseFalada(lambda: motor)
    sintese.falar("mau")
    sintese.falar("bom")
    assert _esperar(lambda: motor.ditas == ["bom"])
    sintese.fechar()


# --- vozes e reconhecimento --------------------------------------------------

def test_escolhe_voz_portuguesa_de_portugal_primeiro():
    vozes = [("TTS_MS_EN-US", "Zira"), ("TTS_MS_PT-BR_MARIA", "Maria pt-BR"), ("TTS_MS_PT-PT_HELENA", "Helena")]
    assert escolher_voz_portuguesa(vozes) == "TTS_MS_PT-PT_HELENA"


def test_sem_voz_portuguesa_nao_escolhe_ingles():
    vozes = [("TTS_MS_EN-US", "Zira")]
    assert escolher_voz_portuguesa(vozes) is None


def test_reconhecimento_sem_dependencias_explica_o_motivo(tmp_path):
    motivo = verificar_reconhecimento(tmp_path)
    assert motivo is not None
    assert "vosk" in motivo.lower() or "modelo" in motivo.lower()


def test_modelo_vosk_ausente(tmp_path):
    assert modelo_vosk_presente(tmp_path) is None


def test_modelo_vosk_presente_quando_existe_pasta_com_ficheiros(tmp_path):
    pasta = tmp_path / "modelos" / "vosk-pt"
    pasta.mkdir(parents=True)
    (pasta / "am").write_text("x", encoding="utf-8")
    assert modelo_vosk_presente(tmp_path) == pasta


def test_ditado_recusa_arranque_sem_dependencias(tmp_path):
    from teclado.core.voz import Ditado
    with pytest.raises(VozIndisponivel):
        Ditado(tmp_path, ao_texto=lambda t: None)


# --- controlador: preferencias e politica -------------------------------------

class _Saida:
    def escrever(self, texto):
        pass

    def tecla(self, nome):
        pass


def _app(tmp_path, perfil, pins=()):
    repo = RepositorioPerfis(tmp_path / "perfis")
    repo.guardar(perfil)
    fila = list(pins)
    app = Aplicacao(
        saida=_Saida(), repo=repo, perfil=perfil,
        pedir_pin=lambda: fila.pop(0) if fila else None,
        pastas_layouts=[DADOS_PROJETO / "layouts"],
        pastas_temas=[DADOS_PROJETO / "temas"],
        pasta_temas_utilizador=tmp_path / "temas",
        pasta_layouts_utilizador=tmp_path / "layouts",
    )
    return app, repo


def test_falar_nao_pede_codigo_mesmo_supervisionado(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    app, repo = _app(tmp_path, perfil)
    app.alternar_falar(True)
    assert repo.carregar(app.perfil.id).preferencias["voz"]["falar"] is True


def test_preferencias_voz_padrao_desligadas(tmp_path):
    app, _ = _app(tmp_path, criar_perfil("Adulto", supervisionado=False))
    prefs = app.preferencias_voz()
    assert prefs["falar"] is False and prefs["ler_palavra"] is False


def test_opcoes_de_voz_bloqueadas_em_supervisionado_sem_codigo(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    app, repo = _app(tmp_path, perfil, pins=[None])
    assert app.definir_opcoes_voz(True, True, True, None) is False
    assert "voz" not in repo.carregar(app.perfil.id).preferencias


def test_opcoes_de_voz_com_codigo_correto(tmp_path):
    perfil = criar_perfil("Criança", supervisionado=True, pin="1234")
    app, repo = _app(tmp_path, perfil, pins=["1234"])
    assert app.definir_opcoes_voz(True, False, True, "VOZ-1") is True
    prefs = repo.carregar(app.perfil.id).preferencias["voz"]
    assert prefs["ler_palavra"] is True and prefs["ler_sugestao"] is True and prefs["voz_id"] == "VOZ-1"


# --- janela: estado dos botoes -----------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_botoes_de_voz_desativados_com_motivo(qapp):
    from teclado.core.layout import descobrir_layouts
    from teclado.core.tema import descobrir_temas
    from teclado.ui.janela import JanelaTeclado

    janela = JanelaTeclado(
        Editor(_Saida(), Dicionario({})),
        descobrir_layouts([DADOS_PROJETO / "layouts"])["QWERTY"],
        descobrir_temas([DADOS_PROJETO / "temas"])["Claro"],
    )
    janela.configurar_voz(falar_ligado=False, falar_motivo="Sem motor", ditar_ligado=False,
                          ditar_motivo="Falta o modelo", ao_falar=lambda a: None, ao_ditar=lambda a: None)
    assert janela._botao_falar.isEnabled() is False
    assert "Sem motor" in janela._botao_falar.toolTip()
    assert janela._botao_ditar.isEnabled() is False
    janela.close()


def test_botao_falar_ativo_chama_callback(qapp):
    from teclado.core.layout import descobrir_layouts
    from teclado.core.tema import descobrir_temas
    from teclado.ui.janela import JanelaTeclado

    recebidos = []
    janela = JanelaTeclado(
        Editor(_Saida(), Dicionario({})),
        descobrir_layouts([DADOS_PROJETO / "layouts"])["QWERTY"],
        descobrir_temas([DADOS_PROJETO / "temas"])["Claro"],
    )
    janela.configurar_voz(falar_ligado=False, falar_motivo=None, ditar_ligado=False,
                          ditar_motivo="x", ao_falar=recebidos.append, ao_ditar=lambda a: None)
    janela._botao_falar.click()
    assert recebidos == [True]
    janela.close()
