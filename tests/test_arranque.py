import sys
import uuid

import pytest

from teclado.core import arranque


def test_comando_aponta_para_a_pasta_do_projeto(tmp_path):
    comando = arranque.comando_arranque(tmp_path)
    assert str(tmp_path) in comando
    assert "teclado.__main__" in comando and "m.main()" in comando


def test_linux_liga_e_desliga_a_entrada_autostart(tmp_path):
    assert not arranque.linux_ativado(base=tmp_path)
    arranque.linux_definir(True, "python -c teste", base=tmp_path)
    ficheiro = tmp_path / "autostart" / "teclado-remoto.desktop"
    assert ficheiro.is_file()
    texto = ficheiro.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in texto and "Exec=python -c teste" in texto
    assert arranque.linux_ativado(base=tmp_path)
    arranque.linux_definir(False, "", base=tmp_path)
    assert not ficheiro.exists()
    arranque.linux_definir(False, "", base=tmp_path)  # desligar duas vezes nao falha


@pytest.mark.skipif(sys.platform != "win32", reason="usa o registo do Windows")
def test_windows_grava_e_apaga_a_entrada_de_arranque():
    nome = "TecladoRemotoTeste-" + uuid.uuid4().hex[:8]
    try:
        arranque._win_gravar(nome, arranque.comando_arranque())
        assert arranque._win_existe(nome)
    finally:
        arranque._win_apagar(nome)
    assert not arranque._win_existe(nome)
