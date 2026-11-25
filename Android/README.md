# Kikoia - app Android (controlo remoto)

Esta app transforma o telemóvel ou o tablet num teclado e num rato para o computador onde corre o Kikoia. Não funciona sozinha: precisa do teclado Kikoia no Windows ou no Linux.

> **Créditos e licenças:** [../CREDITOS.md](../CREDITOS.md) lista as bibliotecas usadas na app (Kotlin, Jetpack Compose, OkHttp, entre outras) e as suas licenças.

## Funcionalidades

- **Teclado remoto:** envia as teclas para o computador, com as teclas do layout ativo.
- **Touchpad:** mover o cursor, clicar por área, barra de deslocamento na direita.
- **Sugestões e voz:** mostrar ou ocultar sugestões de palavras, e ligar a voz de Falar ou Ditar do computador.
- **Poupança de energia:** ao fim de algum tempo sem uso, o ecrã fica preto com um aviso de 20 segundos. Um toque cancela o aviso ou volta a ligar o ecrã. O tempo é configurável.
- **Ligação de confiança:** depois do primeiro emparelhamento, a app liga-se sozinha ao último computador.

## Ligação ao computador

- **Bluetooth (recomendado):** a ligação é cifrada pelo sistema.
- **Wi-Fi (alternativa):** a ligação na rede local não é cifrada. O emparelhamento é protegido e as mensagens são autenticadas, mas o conteúdo circula em texto simples. Usa-o só em redes de confiança.

## Compilar a APK de teste

```powershell
cd android
.\gradlew.bat assembleDebug
```

A APK fica em `app\build\outputs\apk\debug\app-debug.apk`. Para a instalar, ativa a instalação de apps de origem desconhecida no telemóvel.

Testes (protocolo, cifragem e interoperabilidade com o computador):

```powershell
cd android
.\gradlew.bat testDebugUnitTest
```

## Recomendações para pais e educadores

- **Telemóvel do adulto:** o emparelhamento e a confiança ficam guardados no telemóvel. Não emparelhes o telemóvel da criança com o computador do adulto, a menos que queiras que a criança controle o computador.
- **Bloqueio do telemóvel:** ativa o bloqueio de ecrã do telemóvel. A app não substitui o bloqueio do próprio dispositivo.
- **Wi-Fi:** usa-o só em redes de confiança, por causa da ligação não cifrada.
- **Ligação de confiança:** para retirar o acesso ao telemóvel, apaga a confiança no computador (ver o README principal).
