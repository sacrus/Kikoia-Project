# Teclado Remoto: teste em Linux

Esta pasta é para testar o teclado numa máquina Linux (versão de teste, ainda sem fase 8).

## O que funciona e o que não funciona

**Funciona (para testar):**
- Interface do teclado: teclados, temas, layouts, editor de teclados.
- Definições, supervisão do adulto, teclas personalizadas, idioma (português, inglês, espanhol, francês).
- Sugestões de palavras (dicionário de cada idioma).
- Telemóvel por **Bluetooth** (emparelhado no sistema) e por **Wi-Fi**: emparelhamento com código, ligação de confiança e escuta de 5 minutos.
- Arranque com o sistema (cria `~/.config/autostart/teclado-remoto.desktop`).
- Instância única, verificação de atualizações (sem repositório configurado, só verifica as dependências).

**Não funciona ainda:**
- **Teclado físico (observar teclas):** só existe no Windows.
- **Janela em foco e área de transferência:** fechar/minimizar a janela em foco, e ler a seleção, não estão disponíveis no Linux. O texto (incluindo o ditado) escreve-se normalmente.
- **Voz:** a síntese depende das vozes do sistema (Linux), e o ditar precisa do modelo Vosk (descarregado em Opções de voz).

## Instalação

Precisa de Python 3.11 ou superior.

Em Debian/Ubuntu:

```bash
sudo apt install python3 python3-venv libportaudio2 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1
cd TecladoRemoto-Linux
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

(Em outras distribuições, instale os equivalentes: Python 3.11+, venv, PortAudio, e as bibliotecas XCB que o Qt pedir.)

## Permitir escrever noutras aplicações (uma vez)

O teclado escreve através de um teclado virtual do kernel (`/dev/uinput`). Para isso, execute uma vez:

```bash
sudo tools/configurar_teclado_linux.sh
```

Depois, termine a sessão e volte a entrar. O script não junta o utilizador a nenhum grupo: a permissão só existe enquanto a sessão gráfica estiver ativa. O layout de teclado é lido do próprio sistema (GNOME ou `localectl`), por isso funciona com qualquer teclado configurado.

Se o teclado não escrever, confirme com `ls -l /dev/uinput` (deve mostrar acesso ao seu utilizador) e volte a executar o script.

## Executar

```bash
. .venv/bin/activate
python -m teclado
```

O teclado abre no ecrã. Os dados ficam em `~/.local/share/teclado/` (perfis, layouts, dicionário pessoal, registo de erros em `erros.log`).

## Testes automáticos

```bash
. .venv/bin/activate
python -m pytest -q
```

Alguns testes são específicos do Windows e ficam ignorados (`skipped`). Se algum falhar, envie-me o resultado (o texto do erro).

## O que me pode enviar para eu corrigir

1. O resultado de `python -m pytest -q` (últimas 30 linhas).
2. O ficheiro `~/.local/share/teclado/erros.log`.
3. Se algo não aparecer bem no ecrã: uma captura de ecrã, e o nome da distribuição e do ambiente gráfico (GNOME, KDE, etc.).

## Telemóvel por Bluetooth

1. Emparelhe o telemóvel com o computador nas definições Bluetooth do Linux (uma vez só).
2. No teclado: ⚙ → Telemóvel → escolha **Bluetooth (emparelhado)** → **Ligar ao telemóvel**.
3. Na app do telemóvel, escolha o computador e escreva o código de 6 dígitos.

Requer o serviço BlueZ (`bluetoothd`) a correr e um adaptador Bluetooth. O código expira ao fim de 2 minutos; se expirar, gere outro.

## Telemóvel por Wi-Fi

1. No teclado: ⚙ → Telemóvel → escolha **Wi-Fi (mesma rede)** → **Ligar ao telemóvel**.
2. No telemóvel, na mesma rede Wi-Fi, abra a app e escolha o computador. Escreva o código de 6 dígitos.
3. A firewall do Linux pode bloquear a porta (por omissão 47800). Se não aparecer o computador, confirme a firewall.
