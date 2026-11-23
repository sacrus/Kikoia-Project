# Créditos e licenças

O Kikoia usa componentes de terceiros. Cada um mantém a sua própria licença. Este ficheiro indica quem fez cada componente, para que fique claro o que é de quem e quais são as obrigações ao distribuir. O texto completo de cada licença está nas fontes indicadas.

**Licença do código do Kikoia:** *a definir pelo autor antes da publicação.* Ver a secção «Pontos em aberto» no fim deste ficheiro.

Onde se lê **Aplica-se a**, indica-se a plataforma em que o componente é usado: Windows, Linux ou Android.

---

## 1. Teclado (Python)

Bibliotecas que vão no pacote ou são instaladas com `requirements.txt`.

| Componente | Para que serve | Licença | Aplica-se a | Fonte |
|---|---|---|---|---|
| Python (interpretador) | Corre o programa; vai dentro do executável Windows | PSF-2.0 | Windows | python.org |
| PySide6 e shiboken6 (Qt for Python) | Interface gráfica | LGPL-3.0 (também disponível em GPL-2.0 ou GPL-3.0; usamos LGPL-3.0) | Windows, Linux | pypi.org/project/PySide6 · qt.io |
| Vosk (API) | Ditado offline | Apache-2.0 | Windows, Linux | alphacephei.com/vosk |
| sounddevice | Captura do áudio para o ditado | MIT | Windows, Linux | pypi.org/project/sounddevice |
| spake2 | Emparelhamento seguro (SPAKE2) com o telemóvel | MIT | Windows, Linux | pypi.org/project/spake2 |
| websockets | Transporte Wi-Fi com o telemóvel | BSD-3-Clause | Windows, Linux | pypi.org/project/websockets |
| jeepney | Bluetooth no Linux (D-Bus, BlueZ) | MIT | Linux | pypi.org/project/jeepney |
| python-xlib | Janela em foco, seleção e área de transferência (X11) | LGPL-2.1-or-later | Linux | pypi.org/project/python-xlib |
| piper-tts | Voz de Falar no Linux | GPL-3.0-or-later | Linux | pypi.org/project/piper-tts |
| winrt-runtime e winrt-Windows.\* | Bluetooth no Windows (Windows Runtime) | MIT | Windows | github.com/pywinrt/pywinrt |

**Ferramentas de construção (não vão no programa, exceto como indicado):**

| Componente | Para que serve | Licença | Aplica-se a |
|---|---|---|---|
| PyInstaller | Gera o executável Windows. Tem uma exceção que permite distribuir programas com qualquer licença | GPL-2.0-or-later, com exceção | Windows |
| Inno Setup | Gera o instalador Windows | Licença própria do Inno Setup, gratuita | Windows |
| pytest | Testes | MIT | Desenvolvimento |
| spylls | Gera o léxico a partir dos dicionários (`tools/gerar_lexico.py`) | MIT | Desenvolvimento |

---

## 2. Vozes e dados linguísticos

**Vozes Piper (Linux).** Descarregadas só quando o utilizador as pede. Não vêm no pacote.

| Voz | Idioma | Licença | Atribuição |
|---|---|---|---|
| `pt_PT-tugao-medium` | Português (Portugal) | CC0 | Conjunto de dados OHF-Voice |
| `en_US-amy-medium` | Inglês (EUA) | Ver a fonte (MycroftAI mimic3-voices) | *Verificar antes de publicar* |
| `es_ES-sharvard-medium` | Espanhol (Espanha) | CC BY 3.0 | Conjunto Sharvard, Universidade de Edimburgo (datashare.ed.ac.uk/handle/10283/574) |
| `fr_FR-siwis-medium` | Francês (França) | CC BY 4.0 | Base SIWIS, Universidade de Edimburgo (datashare.is.ed.ac.uk/handle/10283/2353) |

Todas as vozes são afinadas a partir do modelo base `hifi_tts_92` (conjunto HiFi-TTS). *Verificar a licença do conjunto HiFi-TTS antes de publicar.*

**Modelos de ditado (Vosk).** Descarregados só quando o utilizador os pede. Licença Apache-2.0, do autor Alpha Cephei.

**Dicionários e listas de frequência** (usados para as sugestões de palavras). Os detalhes, as obrigações e as limitações de cada fonte estão em `data/languages/LICENCAS.md`:
- FrequencyWords (listas de frequência): CC-BY-SA-4.0.
- Hunspell pt_PT, en_US (SCOWL), es_ES e fr_FR (Grammalecte): usados só como filtro de validade. Licenças GPL, LGPL, MPL ou permissivas, conforme a fonte.

---

## 3. Android

Aplica-se a: **Android**. As bibliotecas abaixo vão na APK, exceto os testes.

| Componente | Para que serve | Licença |
|---|---|---|
| Kotlin | Linguagem | Apache-2.0 |
| Jetpack Compose, Material 3, AndroidX (activity, core-ktx) | Interface e ciclo de vida | Apache-2.0 |
| OkHttp 4.12.0 | Ligação Wi-Fi ao computador | Apache-2.0 |
| Gradle (wrapper) | Compilação | Apache-2.0 |
| JUnit 4.13.2 | Testes (não vai na APK) | EPL-1.0 |
| org.json 20240303 | Testes (não vai na APK) | Licença JSON |

---

## 4. Quadro Interativo

Aplica-se a: **Windows** (o Quadro só existe para Windows nesta versão).

| Componente | Para que serve | Licença | Como é usado |
|---|---|---|---|
| PySide6 | Interface gráfica | LGPL-3.0 (ver secção 1) | Incluído |
| GCompris | Jogo educativo para crianças. Autores: Timothée Giet e outros | AGPL-3.0 | Não incluído: descarregado do site oficial (gcompris.net), com verificação SHA-256 |
| Solo, de Simon Tatham's Portable Puzzle Collection | Jogo de lógica (Sudoku). Copyright Simon Tatham e outros contribuidores | MIT | Não incluído: descarregado do site oficial (chiark.greenend.org.uk/~sgtatham/puzzles), com verificação SHA-256 |
| Imagem `thumb.png` do Solo | Miniatura no catálogo | Copyright Simon Tatham (coleção MIT) | Incluída, copiada do site oficial |

---

## 5. Obrigações ao distribuir

- Incluir este ficheiro em qualquer pacote distribuído (Windows, Linux, Android e repositórios).
- **LGPL (PySide6, python-xlib):** manter os avisos de copyright e disponibilizar o texto da licença. No instalador Windows, é preciso também indicar como obter o código-fonte do PySide6 e permitir a substituição da biblioteca. *Confirmar o texto exato antes da primeira publicação do instalador.*
- **GPL (piper-tts):** ver os pontos em aberto.
- **CC BY (vozes Sharvard e SIWIS):** dar crédito aos autores, indicar que a voz foi afinada (Piper) e manter a ligação à licença.
- **Dicionários e léxico:** ver `data/languages/LICENCAS.md`.

---

## Pontos em aberto

1. **Licença do Kikoia.** O repositório ainda não tem licença própria. Convém decidir antes da publicação, porque o `piper-tts` (GPL-3.0-or-later) e as regras da LGPL condicionam a escolha.
2. **Voz `amy` e conjunto HiFi-TTS.** A licença não está confirmada nas fontes consultadas. Confirmar antes de publicar.
3. **Textos completos das licenças.** Não estão incluídos. Ao publicar, convém juntar os textos das licenças usadas nos pacotes (LGPL, GPL, Apache-2.0, MIT, CC BY).
