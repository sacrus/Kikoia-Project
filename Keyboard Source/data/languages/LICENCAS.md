# Licencas dos dados linguisticos

## pt-PT (`pt-PT/lexico.tsv`)

Ficheiro derivado, gerado por `tools/gerar_lexico.py`, a partir de duas fontes:

| Fonte | Uso | Licenca |
|---|---|---|
| FrequencyWords, `content/2018/pt/pt_50k.txt` (https://github.com/hermitdave/FrequencyWords) | Palavras e contagens de frequencia | CC-BY-SA-4.0 (conteudo) |
| Hunspell pt_PT, `pt_PT.dic` e `pt_PT.aff` (https://github.com/LibreOffice/dictionaries/tree/master/pt_PT) | Apenas filtro de validade (nenhum texto do dicionario e copiado) | GPL 2 / LGPL 2.1 / MPL 1.1, a escolha |

**Obrigacoes ao distribuir `lexico.tsv`:**
- Dar credito a FrequencyWords (Hermit Dave e contribuidores) e indicar a licenca CC-BY-SA-4.0.
- Distribuir o ficheiro derivado sob CC-BY-SA-4.0 (ou compativel).
- Esta licenca aplica-se ao ficheiro de dados. O codigo do projeto mantem a sua propria licenca.

**Limitacoes conhecidas:**
- O filtro Hunspell nao separa pt-PT de pt-BR. Formas como "voce", "voces" e "caminhao" passam.
- A lista de origem vem de legendas (OpenSubtitles); pode conter registos coloquiais.
- Nomes proprios so entram se existirem no Hunspell em minusculas; os restantes sao aprendidos pelo uso.

## en (`en/lexico.tsv`)

Ficheiro derivado, gerado com `tools/gerar_lexico.py`, a partir de:

| Fonte | Uso | Licenca |
|---|---|---|
| FrequencyWords, `content/2018/en/en_50k.txt` (https://github.com/hermitdave/FrequencyWords) | Palavras e contagens de frequencia | CC-BY-SA-4.0 (conteudo) |
| Hunspell en_US, `en_US.dic` e `en_US.aff` (https://github.com/LibreOffice/dictionaries/tree/master/en), versao 2020.12.07, derivado de SCOWL | Apenas filtro de validade | Licenca permissiva de Kevin Atkinson (SCOWL): uso, copia e distribuicao sem custo, desde que o aviso de copyright seja mantido. O ficheiro .aff baseia-se no Ispell (licenca BSD). |

**Obrigacoes ao distribuir `en/lexico.tsv`:**
- Dar credito a FrequencyWords e indicar a licenca CC-BY-SA-4.0.
- Manter o aviso de copyright do SCOWL (Kevin Atkinson) e do Ispell (Geoff Kuenning), disponivel no README do dicionario.

**Limitacoes conhecidas:**
- A lista de origem vem de legendas (OpenSubtitles); pode conter registos coloquiais.
- Mantem-se so o dicionario en_US (ortografia americana). A ortografia britanica nao e filtrada.

## es (`es/lexico.tsv`)

Ficheiro derivado, gerado com `tools/gerar_lexico.py`, a partir de:

| Fonte | Uso | Licenca |
|---|---|---|
| FrequencyWords, `content/2018/es/es_50k.txt` (https://github.com/hermitdave/FrequencyWords) | Palavras e contagens de frequencia | CC-BY-SA-4.0 (conteudo) |
| Hunspell es_ES, `es_ES.dic` e `es_ES.aff` (https://github.com/LibreOffice/dictionaries/tree/master/es) | Apenas filtro de validade | Tripla licenca, a escolha: GPL 3, LGPL 3 ou MPL 1.1 (ficheiro `es/LICENSE.md`) |

**Obrigacoes ao distribuir `es/lexico.tsv`:**
- Dar credito a FrequencyWords e indicar a licenca CC-BY-SA-4.0.
- Indicar a licenca escolhida do dicionario Hunspell es_ES, conforme a tripla licenca acima.

**Limitacoes conhecidas:**
- A lista de origem vem de legendas (OpenSubtitles); mistura formas de Espanha e da America Latina.
- O filtro Hunspell es_ES nao separa variantes regionais.

## fr (`fr/lexico.tsv`)

Ficheiro derivado, gerado com `tools/gerar_lexico.py`, a partir de:

| Fonte | Uso | Licenca |
|---|---|---|
| FrequencyWords, `content/2018/fr/fr_50k.txt` (https://github.com/hermitdave/FrequencyWords) | Palavras e contagens de frequencia | CC-BY-SA-4.0 (conteudo) |
| Hunspell fr_FR, dicionario Grammalecte v7.5 (Olivier R., https://grammalecte.net/), copia de https://github.com/wooorm/dictionaries/tree/main/dictionaries/fr | Apenas filtro de validade | MPL 2.0 (ficheiro `license` do dicionario) |

**Obrigacoes ao distribuir `fr/lexico.tsv`:**
- Dar credito a FrequencyWords e indicar a licenca CC-BY-SA-4.0.
- Dar credito a Olivier R. (Grammalecte) e manter a licenca MPL 2.0 do dicionario Hunspell.

**Limitacoes conhecidas:**
- A lista de origem vem de legendas (OpenSubtitles); pode conter registos coloquiais.
- Nao filtra as diferencas entre francês de França e de outros paises francofonos.

## Modelos de voz (Vosk, descarregados a pedido)

Nao vem nada disto com o teclado. Um modelo so e transferido quando o utilizador o pede
em Opcoes de voz (para ditar). Fonte: https://alphacephei.com/vosk/models

| Idioma | Modelo | Tamanho aprox. | Licenca |
|---|---|---|---|
| Portugues | vosk-model-small-pt-0.3 | 32 MB | Apache 2.0 |
| Ingles | vosk-model-small-en-us-0.15 | 41 MB | Apache 2.0 |
| Espanhol | vosk-model-small-es-0.42 | 40 MB | Apache 2.0 |
| Frances | vosk-model-small-fr-0.22 | 42 MB | Apache 2.0 |

Os modelos mantem a licenca Apache 2.0 do autor (Alpha Cephei). Ao distribuir o teclado,
manter o aviso de licenca dos modelos se os incluir.

## Regras para novos idiomas

Cada idioma novo entra so depois de a sua fonte e licenca estarem registadas aqui.
