# Notas da sessão Linux (para continuar no Windows)

Documento de passagem. Pode apagá-lo depois de ler.

## Ambiente

- Não copiar a pasta `.venv` (é do Linux). No Windows: criar um novo com
  `python -m venv .venv` e `pip install -r requirements.txt`.
- Não copiar `__pycache__` nem `.pytest_cache`.
- `requirements.txt`: não precisa de alterações. `jeepney` só é instalado em Linux
  (marcador `sys_platform == "linux"`); os pacotes `winrt-*` continuam só para Windows.

## Alterações feitas no Linux (verificar também no Windows)

1. **Bluetooth Linux** (`teclado/gateway/bluetooth_linux.py`, novo): perfil SPP no BlueZ via D-Bus
   (`jeepney`). Funciona com o telemóvel Android emparelhado. Testado com telemóvel real.
2. **`teclado/gateway/controlador.py`**: escolhe `bluetooth.py` (Windows) ou `bluetooth_linux.py` (Linux).
3. **`teclado/gateway/confianca.py`**: nova função `dispositivos_emparelhados()`, usada também pela
   escuta automática em `teclado/__main__.py`. No Windows continua a ler o registo, como antes.
4. **Escrita no Linux** (`teclado/core/saida/`): `linux.py`, `uinput.py`, `xkb.py`, `layout.py`.
   Só Linux. Windows continua com `windows.py`.
5. **`tools/configurar_teclado_linux.sh`**: configuração única com `sudo`, só Linux.
6. **`teclado/__main__.py`**:
   - `qt.setQuitOnLastWindowClosed(False)` dentro do bloco do ícone da bandeja. **Aplica-se também ao Windows**:
     confirmar que o teclado continua a fechar pelo menu "Sair" e que não termina sozinho ao esconder-se.
   - `_escolher_plataforma_grafica()`: só Linux (usa xcb quando disponível).
7. **`teclado/ui/janela.py`** (**aplica-se também ao Windows**):
   - Faixa de sugestões reservada enquanto o interruptor "Sugestões" estiver ligado (`ALTURA_FAIXA_SUGESTOES`).
   - Roda dentada desenhada como ícone (`_icone_definicoes`), em vez do caráter ⚙.
     Confirmar que aparece e que abre as definições.
8. **Testes**:
   - `tests/test_saida.py`: o teste do tamanho da estrutura `INPUT` só corre no Windows.
   - `tests/test_saida_nula.py`: ajustado (sem permissão para `uinput`, o Linux usa a saída nula).
   - Novos: `tests/test_gateway_bluetooth_linux.py`, `tests/test_saida_linux.py`.
   - `tests/test_janela.py`: deixou de procurar o botão pelo texto "⚙".
9. **Traduções** (`data/idiomas/*.json`): nova chave `bluetooth.sem_bluez` (pt-PT, en, es, fr).

## Pendente / limitações conhecidas (Linux)

- Fechar/minimizar a janela em foco e ler a seleção ainda não existem no Linux (`linux.py` devolve False/"").
- Caps Lock ativo inverte as maiúsculas no Linux (o estado não é lido).
- Carateres sem tecla no layout (ex.: emojis) não são escritos no Linux.
- Janela do teclado: no Linux usa xcb (XWayland) para ficar por cima e sem roubar foco. No Windows não muda.
- Sem acesso a `/dev/uinput`, o Linux arranca mas não escreve, e mostra a instrução do script.

## Pacotes de sistema instalados no Linux (para outras máquinas)

`libportaudio2 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1` (e `bluez`, que já vem com o Ubuntu).

## Testes

Correr `python -m pytest -q` no Windows. No Linux, último resultado: 520 passed, 14 skipped.
Os testes Linux ficam ignorados no Windows, e vice-versa.

## Ainda por fazer (Android)

- A app Android liga-se ao UUID SPP (`00001101-0000-1000-8000-00805f9b34fb`) e usa o mesmo protocolo
  (emparelhamento SPAKE2 com o código de 6 dígitos, mensagens com prefixo de 4 bytes).
  Não houve alterações à app Android.
