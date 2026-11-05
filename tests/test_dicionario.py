from teclado.core.dicionario import Dicionario
from teclado.core.paths import DADOS_PROJETO

BASE = {"casa": 10, "cama": 5, "cair": 20, "mais": 50, "gato": 3}


def test_base_ordenada_por_frequencia():
    dic = Dicionario(BASE)
    assert dic.sugerir("ca", 5) == ["cair", "casa", "cama"]


def test_prefixo_vazio_sem_sugestoes():
    assert Dicionario(BASE).sugerir("", 5) == []


def test_maximo_respeitado():
    assert len(Dicionario(BASE).sugerir("c", 2)) == 2


def test_prefixo_sem_correspondencia():
    assert Dicionario(BASE).sugerir("xyz", 5) == []


def test_pesquisa_ignora_maiusculas_no_prefixo():
    assert Dicionario(BASE).sugerir("CA", 5)[0] == "cair"


def test_palavras_usadas_aparecem_primeiro(tmp_path):
    dic = Dicionario(BASE, pessoal_caminho=tmp_path / "uso.sqlite")
    dic.aprender("cama")
    dic.aprender("cama")
    assert dic.sugerir("ca", 5)[0] == "cama"
    dic.fechar()


def test_nome_proprio_guardado_com_maiuscula(tmp_path):
    dic = Dicionario(BASE, pessoal_caminho=tmp_path / "uso.sqlite")
    dic.aprender("Maria", inicio_frase=False)
    assert dic.sugerir("ma", 5)[0] == "Maria"
    dic.fechar()


def test_maiuscula_de_inicio_de_frase_nao_e_guardada(tmp_path):
    dic = Dicionario(BASE, pessoal_caminho=tmp_path / "uso.sqlite")
    dic.aprender("Casa", inicio_frase=True)
    assert dic.sugerir("ca", 5)[0] == "casa"
    dic.fechar()


def test_aprendizagem_persiste_entre_sessoes(tmp_path):
    caminho = tmp_path / "uso.sqlite"
    dic = Dicionario(BASE, pessoal_caminho=caminho)
    dic.aprender("gato")
    dic.fechar()
    nova = Dicionario(BASE, pessoal_caminho=caminho)
    assert nova.sugerir("ga", 5)[0] == "gato"
    nova.fechar()


def test_palavras_sem_letras_nao_sao_aprendidas(tmp_path):
    dic = Dicionario(BASE, pessoal_caminho=tmp_path / "uso.sqlite")
    dic.aprender("12ab")
    dic.aprender("")
    assert dic.sugerir("12", 5) == []
    dic.fechar()


def test_aprender_sem_perfil_nao_altera_base():
    dic = Dicionario(BASE)
    dic.aprender("zebra")
    assert dic.sugerir("ze", 5) == []


def test_lexico_pt_pt_carrega_e_tem_palavras_comuns():
    dic = Dicionario.carregar(DADOS_PROJETO / "languages" / "pt-PT" / "lexico.tsv")
    assert dic.sugerir("ca", 10)
    assert "casa" in dic.sugerir("cas", 10)


def test_lexico_excluiu_erros_de_ocr_e_formas_inexistentes():
    # Estas formas nao existem no Hunspell pt_PT (erros de OCR ou pt pre-AO90).
    dic = Dicionario.carregar(DADOS_PROJETO / "languages" / "pt-PT" / "lexico.tsv")
    assert "näo" not in dic.sugerir("nã", 10)
    assert "óptimo" not in dic.sugerir("óp", 10)
