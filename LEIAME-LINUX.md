# Teclado Remoto: teste em Linux

Esta pasta é para testar o teclado numa máquina Linux (versão de teste, ainda sem fase 8).

## O que funciona e o que não funciona

**Funciona (para testar):**
- Interface do teclado: teclados, temas, layouts, editor de teclados.
- Definições, supervisão do adulto, teclas personalizadas, idioma (português, inglês, espanhol, francês).
- Sugestões de palavras (dicionário de cada idioma).
- Telemóvel por **Wi-Fi**: emparelhamento com código, ligação de confiança e escuta de 5 minutos.
- Arranque com o sistema (cria `~/.config/autostart/teclado-remoto.desktop`).
- Instância única, verificação de atualizações (sem repositório configurado, só verifica as dependências).

**Não funciona ainda:**
- **Escrever noutras aplicações.** Neste sistema o teclado não envia teclas para outras janelas: a fase 8 (uinput) ainda não está feita. Vês o teclado e as sugestões, mas o texto não chega ao editor, ao navegador, etc.
- **Bluetooth:** só existe no Windows. No Linux, use Wi-Fi.
- **Teclado físico (observar teclas):** só existe no Windows.
- **Voz:** a síntese depende das vozes do sistema (Linux), e o ditar precisa do modelo Vosk (descarregado em Opções de voz).

## Instalação

Precisa de Python 3.11 ou superior.

Em Debian/Ubuntu:

```bash
sudo apt install python3 python3-venv libportaudio2 libxcb-cursor0
cd TecladoRemoto-Linux
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

(Em outras distribuições, instale os equivalentes: Python 3.11+, venv, PortAudio, e as bibliotecas XCB que o Qt pedir.)

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

## Telemóvel por Wi-Fi

1. No teclado: ⚙ → Telemóvel → escolha **Wi-Fi (mesma rede)** → **Ligar ao telemóvel**.
2. No telemóvel, na mesma rede Wi-Fi, abra a app e escolha o computador. Escreva o código de 6 dígitos.
3. A firewall do Linux pode bloquear a porta (por omissão 47800). Se não aparecer o computador, confirme a firewall.
