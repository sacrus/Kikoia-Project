# Kikoia

Teclado virtual para Windows e Linux, pensado para acessibilidade: escrita por clique, sugestões de palavras, voz, teclados configuráveis e controlo remoto a partir de um telemóvel Android.

## Estado atual (versão 0.1.1)

- **Windows:** completo e testado no PC principal.
- **Linux:** funcional em sessões X11 e em Wayland com XWayland. Inclui teclado virtual (`uinput`) com o layout do sistema, Bluetooth (BlueZ), voz de Falar (Piper, uma voz por idioma), ações sobre a janela em foco, leitura da seleção e área de transferência (X11), e reserva da área de trabalho para o teclado (X11/XWayland). Foi testado numa sessão Linux. Limitações desta versão:
  - **Teclado físico com sugestões** ainda não está disponível (só Windows).
  - A reserva da área de trabalho não funciona em aplicações Wayland nativas. As ações sobre a janela (fechar, minimizar, maximizar) e a leitura da seleção também não.
- **Android:** app de controlo remoto, testada por Bluetooth e por Wi-Fi. O Bluetooth é o método recomendado; o Wi-Fi é uma alternativa e pode exigir configurações adicionais na rede (ver abaixo).

## Funcionalidades

- **Teclados em ficheiros JSON** (`data/layouts/`), com ações, modificadores, acentos e toque repetido (multitoque).
- **Editor de teclados visual**, com modelos prontos (QWERTY, numérico, mínimo, vogais, abecedário).
- **Shift como no teclado do sistema:** com Shift ativo, cada tecla escreve o seu símbolo (1 → `!`, ç → `Ç`). Os símbolos vêm de uma tabela por idioma e podem ser definidos tecla a tecla, no campo «Símbolo com Shift» do editor.
- **Modificadores persistentes:** Shift e Ctrl ficam ativos até carregares noutra tecla. Assim, `Shift` → `Ctrl` → `C` envia Ctrl+Shift+C numa só combinação. Shift com setas, Home e End seleciona texto.
- **Teclas de atalho entre teclados:** o QWERTY traz a tecla «Números», que leva ao teclado numérico.
- **Sugestões de palavras** com base num dicionário offline (pt-PT, en, es, fr).
- **Voz:** ditado offline com Vosk (Windows e Linux); síntese de voz (Falar) com SAPI5, só no Windows. O modelo de reconhecimento só é descarregado quando o pedires, em **Definições → Opções de voz**.
- **Temas claro e escuro**, personalizáveis.
- **Teclas personalizadas:** abrem programas ou ficheiros no PC. Criam-se, alteram-se e apagam-se no editor de teclados.
- **Layout «Ações»:** traz as teclas de ação (apagar palavra e linha, selecionar, ler seleção, navegar entre janelas, minimizar, maximizar, fechar janela) e uma tecla para voltar ao QWERTY. Chega-se por ⚡, a tecla ao lado do Ctrl no QWERTY.
- **Janela sem barra de título:** o teclado fica como uma faixa no fundo do ecrã, e as janelas acomodam-se à sua altura (Windows e Linux). Fecha-se pelo botão **Sair** ou pelo ícone da bandeja.
- **Teclado físico com sugestões** (opcional, desligado por omissão; só Windows).
- **Modo supervisão:** um adulto pode proteger layouts, temas e definições com código.
- **Criação de teclados com IA** (requer ligação à internet e chave de API configurada).
- **Controlo remoto a partir do telemóvel**, por Bluetooth ou Wi-Fi.
- **Idiomas da interface:** português (pt-PT), inglês, espanhol e francês.

## Requisitos

- **Windows:** Windows 10 ou 11, Python 3.11 ou superior. Para Bluetooth, o adaptador do PC tem de estar ativo.
- **Linux:** Python 3.11 ou superior, sessão gráfica X11 ou Wayland (com XWayland), BlueZ para Bluetooth, e as bibliotecas `libxcb-cursor0`, `libxcb-icccm4` e `libxcb-keysyms1`. Para o ditado, é preciso a biblioteca PortAudio (`libportaudio2`).
- **Telemóvel:** Android 8.0 (API 26) ou superior.

## Instalação e execução (desenvolvimento)

### Windows

```powershell
cd C:\caminho\para\Kikoia
py -m pip install -r requirements.txt
py -m teclado
```

### Linux

```bash
cd /caminho/para/Kikoia
python3 -m pip install -r requirements.txt
sudo tools/configurar_teclado_linux.sh   # uma vez: permite criar o teclado virtual
python3 -m teclado
```

O script `tools/configurar_teclado_linux.sh` dá acesso a `/dev/uinput` apenas à sessão gráfica ativa, sem juntar o utilizador a nenhum grupo. Se o teclado ainda não escrever depois de o executares, termina a sessão e volta a entrar.

Para voltar a mostrar o teclado depois de escondido, usa o ícone na área de notificações: **Mostrar teclado**.

Só pode correr uma instância. Se abrires o programa outra vez, a segunda mostra a primeira e fecha-se.

## Controlo remoto com o telemóvel

### Primeiro emparelhamento

1. Emparelha o telemóvel no sistema (Bluetooth). Para Wi-Fi, liga-o à mesma rede.
2. No teclado: **Definições → Telemóvel**, escolhe o transporte e carrega em **Ligar ao telemóvel**. Aparece um código de 6 dígitos, válido durante 2 minutos.
3. Na app Android, escolhe o computador e escreve o código.

O transporte recomendado é o **Bluetooth**. O Wi-Fi é uma alternativa: quando o escolhes, o teclado mostra que pode ser preciso configurar o reencaminhamento de portas no router.

Depois de emparelhado, o PC e o telemóvel guardam uma ligação de confiança e **não pedem mais código**. A app liga-se sozinha ao último computador usado, e o teclado do PC esconde-se na bandeja quando o telemóvel se liga.

Enquanto a ligação está ativa, o PC e o telemóvel trocam um sinal de vida (ping) a cada 15 segundos. Se não houver nenhuma mensagem durante 45 segundos (por exemplo, o Bluetooth caiu sem aviso), a ligação é dada como perdida: o teclado volta a aparecer no PC, e o telemóvel tenta voltar a ligar-se sozinho, com esperas crescentes, durante cerca de 10 minutos. Para parar as tentativas, carrega em **Desligar**.

Os ícones do cabeçalho da app Android permitem mostrar ou ocultar as sugestões (💬), e ligar ou desligar a voz do PC (🔊 Falar e 🎤 Ditar).

### Arranque automático da escuta

Com **Ligar ao telemóvel automaticamente ao iniciar** ativo (ativo por omissão), o PC espera 5 minutos pelo telemóvel ao arrancar:
- por Bluetooth, se o telemóvel de confiança estiver emparelhado no sistema;
- caso contrário, por Wi-Fi.

Se nenhum telemóvel se ligar nesses 5 minutos, o PC deixa de escutar.

### Arranque com o sistema

**Definições → Iniciar o teclado com o computador** cria uma entrada de arranque para a conta do utilizador, sem administrador. No Windows, é uma entrada do registo; no Linux, um ficheiro `.desktop` em `~/.config/autostart`.

## Voz

- **Ditar** (reconhecimento): offline, com Vosk. Funciona em Windows e Linux. O modelo do idioma escolhido é descarregado a pedido (cerca de 31 a 42 MB, conforme o idioma), e pode ser removido no mesmo ecrã.
- **Falar** (síntese): no Windows, com as vozes SAPI5 instaladas. No Linux, com a voz Piper do idioma (pt-PT, en, es, fr), descarregada a pedido em **Opções de voz → Voz de Falar (Linux)**.

## Onde ficam os dados

| O quê | Windows | Linux |
|---|---|---|
| Perfis e preferências | `%APPDATA%\teclado\perfis\` | `~/.local/share/teclado/perfis/` |
| Teclados e temas criados por ti | `%APPDATA%\teclado\layouts\`, `…\temas\` | `~/.local/share/teclado/layouts/`, `…/temas/` |
| Teclas personalizadas | `%APPDATA%\teclado\comandos.json` | `~/.local/share/teclado/comandos.json` |
| Ligações de confiança com telemóveis | `%APPDATA%\teclado\confianca.json` | `~/.local/share/teclado/confianca.json` |
| Registo de erros | `%APPDATA%\teclado\erros.log` | `~/.local/share/teclado/erros.log` |

## Segurança e privacidade

- **Confiança com telemóveis:** o ficheiro `confianca.json` contém segredos que permitem ligar um telemóvel sem código. Não o partilhes. Para retirar a confiança a todos os telemóveis, fecha o teclado e apaga esse ficheiro: os telemóveis terão de emparelhar outra vez com o código.
- **Teclas personalizadas:** o telemóvel só envia o identificador de uma tecla. Nunca envia texto de comando, e o PC só executa os comandos guardados nas suas definições.
- **Wi-Fi sem encriptação:** a ligação Wi-Fi entre o telemóvel e o PC é em texto simples na rede local (o emparelhamento é protegido e as mensagens são autenticadas). Por isso, o Wi-Fi é a alternativa; o Bluetooth, cifrado pelo sistema, é o recomendado.
- **Instalador Windows:** a opção «Permitir a ligação Wi-Fi do telemóvel na Firewall do Windows» cria a regra para o Kikoia. Pede autorização de administrador; se a recusares, o Windows volta a perguntar quando o Wi-Fi for usado.
- **Supervisão:** o código do adulto protege apenas configurações (layout, tema, definições, teclas personalizadas, arranque e supervisão). A aprendizagem de palavras nunca é bloqueada.
- **Dados de voz e dicionário:** são processados localmente. A criação de teclados com IA é o único recurso que usa a internet. Os modelos de voz são descarregados só quando os pedes.

## Atualizações

- Ao arrancar, o teclado verifica em segundo plano se há versões novas do próprio teclado e das dependências Python, e mostra um aviso na área de notificações. Nunca instala nada sem confirmação.
- **Definições → Atualizações** mostra as versões instaladas e as mais recentes, atualiza as dependências depois de confirmares, e abre a página da versão nova para transferir.
- A verificação ao arrancar pode ser desligada em **Verificar atualizações ao iniciar**.
- A verificação do teclado usa as GitHub Releases do repositório indicado em `REPOSITORIO` (`teclado/core/atualizacao.py`). Ao publicar uma versão, atualiza `VERSAO` nesse mesmo ficheiro.

## Android

A app fica em `android/`. Para gerar a APK de teste:

```powershell
cd android
.\gradlew.bat assembleDebug
```

A APK fica em `android\app\build\outputs\apk\debug\app-debug.apk`. Para a instalar, ativa a instalação de apps de origem desconhecida no telemóvel.

## Testes

```bash
python3 -m pytest
```

Testes da app Android (protocolo, cifragem e interoperabilidade com o PC):

```powershell
cd android
.\gradlew.bat testDebugUnitTest
```

Os testes específicos do Linux (`tests/test_saida_linux.py`) só correm numa sessão Linux. Os específicos do Windows são ignorados no Linux, e vice-versa.

## Estrutura

```
teclado/        código Python (core, ui, gateway)
  core/         editor, dicionário, layouts, símbolos com Shift, voz, arranque, supervisão
  gateway/      protocolo, emparelhamento, confiança, Wi-Fi e Bluetooth
  ui/           janela, editor de teclados, diálogos
data/           layouts, temas, dicionários, idiomas
android/        app Android (Kotlin / Compose)
tests/          testes Python
tools/          scripts de configuração, empacotamento e geração de dados
```

## Licenças

- O código do projeto tem a sua própria licença.
- O dicionário `data/languages/pt-PT/lexico.tsv` é derivado de FrequencyWords (CC-BY-SA-4.0) e Hunspell pt_PT. Ver `data/languages/LICENCAS.md`.
