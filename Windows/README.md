# Kikoia

Teclado virtual para Windows e Linux, pensado para acessibilidade: escrita por clique, sugestões de palavras, voz, teclados configuráveis e controlo remoto a partir de um telemóvel Android.

Estado atual:
- **Windows:** completo e testado no PC principal.
- **Linux:** parcial e não testado (a injeção de teclas por `uinput` não está implementada).
- **Android:** app de controlo remoto, testada por Bluetooth. A ligação Wi-Fi está implementada mas ainda não foi testada em rede real.

## Funcionalidades

- Teclados em ficheiros JSON (`data/layouts/`), com ações, modificadores, acentos e multitoque.
- Editor de teclados visual, com modelos prontos (QWERTY, numérico, mínimo, vogais, abecedário).
- Sugestões de palavras com base num dicionário pt-PT offline.
- Voz: síntese com SAPI5 (Windows) e reconhecimento com Vosk (offline). O modelo de reconhecimento (ditar) só é descarregado quando o pedes: ⚙ → **Opções de voz** → **Descarregar modelo** (cerca de 32 a 42 MB, conforme o idioma). Pode ser removido no mesmo ecrã.
- Temas claro e escuro, personalizáveis.
- Teclas personalizadas que abrem programas ou ficheiros no PC.
- Teclado físico com sugestões (opcional, desligado por omissão).
- Modo supervisão: um adulto pode proteger layout, tema e definições com código.
- Criação de teclados com IA (requer ligação à internet e chave de API configurada).
- Controlo remoto a partir do telemóvel, por Bluetooth ou Wi-Fi.

## Requisitos

- Python 3.11 ou superior.
- Windows 10/11 (para voz SAPI5 e Bluetooth). Para Bluetooth, o adaptador do PC tem de estar ativo.
- Para o telemóvel: Android 8.0 (API 26) ou superior.

## Instalação e execução (desenvolvimento)

```powershell
cd C:\caminho\para\KeyBoard
py -m pip install -r requirements.txt
py -m teclado
```

O teclado abre no ecrã. Para voltar a mostrá-lo depois de escondido, usa o ícone na área de notificações → «Mostrar teclado».

Só pode correr uma instância. Se abrires o programa outra vez, a segunda instância mostra a primeira e fecha-se.

## Controlo remoto com o telemóvel

### Primeiro emparelhamento

1. No PC, emparelha o telemóvel nas definições do Windows (Bluetooth) e na mesma rede Wi-Fi, se fores usar Wi-Fi.
2. No teclado: ⚙ → **Telemóvel** → escolhe o transporte e carrega em **Ligar ao telemóvel**. Aparece um código de 6 dígitos, válido durante 2 minutos.
3. Na app Android, escolhe o computador e escreve o código.

Depois de emparelhado, o PC e o telemóvel guardam uma ligação de confiança e **não pedem mais código**. A app liga-se sozinha ao último computador usado, e o teclado do PC esconde-se para a bandeja quando o telemóvel se liga.

### Arranque automático da escuta

Com **Ligar ao telemóvel automaticamente ao iniciar** ativo (vem ativo por omissão), o PC espera 5 minutos pelo telemóvel ao arrancar:
- Por Bluetooth, se o telemóvel de confiança estiver emparelhado no Windows.
- Caso contrário, por Wi-Fi.

Se nenhum telemóvel se ligar nesses 5 minutos, o PC deixa de escutar.

### Arranque com o sistema

⚙ → **Iniciar o teclado com o computador** cria uma entrada no arranque do Windows (registo da conta do utilizador, sem administrador). No Linux, cria um ficheiro `.desktop` em `~/.config/autostart`.

## Onde ficam os dados

| O quê | Onde (Windows) |
|---|---|
| Perfis e preferências | `%APPDATA%\teclado\perfis\` |
| Teclados e temas criados por ti | `%APPDATA%\teclado\layouts\`, `%APPDATA%\teclado\temas\` |
| Teclas personalizadas | `%APPDATA%\teclado\comandos.json` |
| Ligações de confiança com telemóveis | `%APPDATA%\teclado\confianca.json` |
| Registo de erros | `%APPDATA%\teclado\erros.log` |

No Linux, os dados ficam em `~/.local/share/teclado/`.

## Segurança e privacidade

- **Confiança com telemóveis:** o ficheiro `confianca.json` contém segredos que permitem ligar um telemóvel sem código. Não o partilhes. Para retirar a confiança a todos os telemóveis, fecha o teclado e apaga esse ficheiro: os telemóveis terão de emparelhar outra vez com o código.
- **Teclas personalizadas:** o telemóvel só envia o identificador de uma tecla. Nunca envia texto de comando, e o PC só executa os comandos guardados nas suas definições.
- **Supervisão:** o código do adulto protege apenas configurações (layout, tema, definições, teclas personalizadas, arranque e supervisão). A aprendizagem de palavras nunca é bloqueada.
- **Dados de voz e dicionário:** são processados localmente. A criação de teclados com IA é o único recurso que usa a internet. Os modelos de voz são descarregados só quando os pedes.

## Atualizações

- Ao arrancar, o teclado verifica (em segundo plano) se há versões novas do próprio teclado e das dependências Python. Se houver, mostra um aviso na área de notificações. Nunca instala nada sem confirmação.
- ⚙ → **Atualizações…** mostra as versões instaladas e as mais recentes, atualiza as dependências depois de confirmares, e abre a página da versão nova do teclado para transferir.
- A verificação ao arrancar pode ser desligada em ⚙ → **Verificar atualizações ao iniciar**.
- A verificação do teclado usa as GitHub Releases. Enquanto `REPOSITORIO` em `teclado/core/atualizacao.py` estiver por definir, só as dependências são verificadas. Ao publicar uma versão, atualiza `VERSAO` nesse mesmo ficheiro.

## Android

A app fica em `android/`. Para gerar a APK de teste:

```powershell
cd android
.\gradlew.bat assembleDebug
```

A APK fica em `android\app\build\outputs\apk\debug\app-debug.apk`. Para instalar, ativa a instalação de apps de origem desconhecida no telemóvel.

## Testes

```powershell
py -m pytest
```

Para os testes Android (protocolo, cifragem e interoperabilidade com o PC):

```powershell
cd android
.\gradlew.bat testDebugUnitTest
```

## Estrutura

```
teclado/        código Python (core, ui, gateway)
  core/         editor, dicionário, layouts, voz, arranque, supervisão
  gateway/      protocolo, emparelhamento, confiança, Wi-Fi e Bluetooth
  ui/           janela, editor de teclados, diálogos
data/           layouts, temas, dicionário pt-PT
android/        app Android (Kotlin / Compose)
tests/          testes Python
tools/          scripts de geração de dados
```

## Licenças

- O código do projeto tem a sua própria licença.
- O dicionário `data/languages/pt-PT/lexico.tsv` é derivado de FrequencyWords (CC-BY-SA-4.0) e Hunspell pt_PT. Ver `data/languages/LICENCAS.md`.
