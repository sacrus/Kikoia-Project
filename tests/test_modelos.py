import io
import urllib.request
import zipfile

import pytest

from teclado.core import modelos


def _zip_modelo(nome_pasta="vosk-model-small-pt-0.3"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_:
        zip_.writestr(f"{nome_pasta}/am/final.mdl", b"x" * 1000)
        zip_.writestr(f"{nome_pasta}/conf/model.conf", b"y")
    return buffer.getvalue()


class _Resposta:
    def __init__(self, dados: bytes, enviar_tamanho: bool = True) -> None:
        self._dados = io.BytesIO(dados)
        self.headers = {"Content-Length": str(len(dados))} if enviar_tamanho else {}

    def read(self, n: int = -1) -> bytes:
        return self._dados.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def servidor(monkeypatch):
    estado = {"dados": _zip_modelo(), "pedidos": []}

    def fake_urlopen(pedido, timeout=None):
        estado["pedidos"].append(pedido.full_url)
        return _Resposta(estado["dados"])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return estado


def test_nada_esta_instalado_no_inicio(tmp_path):
    for idioma in modelos.MODELOS_VOZ:
        assert modelos.instalado(tmp_path, idioma) is None


def test_descarregar_instala_o_modelo_na_pasta_do_idioma(tmp_path, servidor):
    destino = modelos.descarregar(tmp_path, "pt-PT")
    assert destino == tmp_path / "modelos" / "vosk-pt"
    assert (destino / "am" / "final.mdl").is_file()
    assert modelos.instalado(tmp_path, "pt-PT") == destino
    assert servidor["pedidos"] == [f"{modelos.URL_BASE}/vosk-model-small-pt-0.3.zip"]


def test_progresso_e_reportado(tmp_path, servidor):
    recebidos = []
    modelos.descarregar(tmp_path, "en", progresso=lambda r, t: recebidos.append((r, t)))
    assert recebidos and recebidos[-1][0] == recebidos[-1][1] > 0


def test_ficheiro_que_nao_e_modelo_nao_fica_instalado(tmp_path, servidor):
    servidor["dados"] = b"isto nao e um zip"
    with pytest.raises(modelos.ModeloErro):
        modelos.descarregar(tmp_path, "fr")
    assert modelos.instalado(tmp_path, "fr") is None
    assert not any(p.name.startswith(".descarga-") for p in (tmp_path / "modelos").iterdir())


def test_estrutura_errada_nao_fica_instalada(tmp_path, servidor):
    servidor["dados"] = _zip_modelo_sem_am()
    with pytest.raises(modelos.ModeloErro):
        modelos.descarregar(tmp_path, "es")
    assert modelos.instalado(tmp_path, "es") is None


def test_cancelar_nao_deixa_nada_instalado(tmp_path, servidor):
    with pytest.raises(modelos.DescargaCancelada):
        modelos.descarregar(tmp_path, "en", cancelar=lambda: True)
    assert modelos.instalado(tmp_path, "en") is None


def test_sem_ligacao_da_erro_claro(tmp_path, monkeypatch):
    def sem_rede(pedido, timeout=None):
        raise OSError("sem ligacao")

    monkeypatch.setattr(urllib.request, "urlopen", sem_rede)
    with pytest.raises(modelos.ModeloErro, match="Sem ligacao"):
        modelos.descarregar(tmp_path, "pt-PT")


def test_remover_apaga_o_modelo(tmp_path, servidor):
    modelos.descarregar(tmp_path, "pt-PT")
    modelos.remover(tmp_path, "pt-PT")
    assert modelos.instalado(tmp_path, "pt-PT") is None
    modelos.remover(tmp_path, "pt-PT")  # repetir nao falha


def test_idioma_sem_modelo_nao_transfere_nada(tmp_path, servidor):
    with pytest.raises(modelos.ModeloErro):
        modelos.descarregar(tmp_path, "de")
    assert servidor["pedidos"] == []


def test_modelos_pequenos_para_os_quatro_idiomas():
    assert set(modelos.MODELOS_VOZ) == {"pt-PT", "en", "es", "fr"}
    assert all(m.nome.startswith("vosk-model-small-") for m in modelos.MODELOS_VOZ.values())


def _zip_modelo_sem_am():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_:
        zip_.writestr("pasta/outra/ficheiro.txt", b"x")
    return buffer.getvalue()
