"""Editor de texto: envia teclas para a aplicacao e acompanha a palavra em curso.

Responsabilidades:
- Maiusculas automaticas no inicio de frase (depois de . ! ? e Enter).
- Tecla Shift de um toque: a proxima letra sai em maiuscula.
- Teclas de acento (tecla morta): o acento espera pela letra seguinte e
  combina-se com ela. Sem letra, sai o sinal isolado.
- Sugestoes da palavra em curso; ao escolher uma, apaga o prefixo e escreve a palavra.
- Aprender a palavra quando esta termina (espaco, pontuacao, Enter, sugestao).

Limitacao: so conhece o texto escrito pelo proprio teclado. Se o utilizador
escrever com o teclado fisico, o editor nao sabe o que foi escrito (fase 7).
"""

from __future__ import annotations

import time
from collections.abc import Callable

from .acentos import ACENTOS, combinar
from .comandos_voz import segmentar
from .teclado_fisico import ConstrutorPalavra
from .saida import ACOES, ACOES_JANELA
from .dicionario import Dicionario
from .saida import Saida

MAX_SUGESTOES = 10
FIM_DE_FRASE = ".!?"
PONTUACAO = frozenset(".,;:!?")
TECLAS_QUE_FECHAM_PALAVRA = frozenset({"espaco", "enter", "tab"})
# Tempo maximo entre dois toques na mesma tecla de toque repetido (segundos).
MULTITOQUE_INTERVALO = 1.2


class Editor:
    def __init__(
        self,
        saida: Saida,
        dicionario: Dicionario,
        max_sugestoes: int = 5,
        ao_atualizar: Callable[[], None] | None = None,
        relogio: Callable[[], float] | None = None,
        ao_falar: Callable[[str], None] | None = None,
    ) -> None:
        self._saida = saida
        self._dicionario = dicionario
        self._max = max(1, min(max_sugestoes, MAX_SUGESTOES))
        self.ao_atualizar = ao_atualizar or (lambda: None)
        # Voz: recebe o texto a ler. As opcoes decidem quando e chamado.
        self._ao_falar = ao_falar or (lambda texto: None)
        self._ao_ler: Callable[[str], None] = lambda texto: None
        self.falar_palavra = False      # ler cada palavra ao completa-la
        self.falar_frase = False        # ler a frase ao terminar (. ! ? ou Enter)
        self.falar_sugestao = False     # ler a sugestao escolhida
        self._frase = ""                # texto da frase em curso, para a leitura

        self.palavra = ""                 # prefixo da palavra em curso, tal como esta no texto
        self._palavra_no_inicio = False   # a palavra comecou no inicio de frase?
        self.inicio_frase = True          # a proxima letra deve sair em maiuscula
        self.shift = False                # shift de um toque, ativo para a proxima letra
        self._espaco_automatico = False   # o ultimo espaco foi escrito por uma sugestao
        self._acento: str | None = None   # acento de tecla morta a aguardar letra
        self._sugestoes: list[str] = []
        self._relogio = relogio or time.monotonic
        # Teclado fisico: palavra escrita fora do teclado virtual (ver teclado_fisico.py)
        self._fisico = ConstrutorPalavra()
        self.aprender_fisico = False
        # (chave, indice, instante, inicio_de_frase_antes) do ultimo toque repetido
        self._ultimo_multi: tuple[int, int, float, bool] | None = None
        self.ctrl = False                 # Ctrl de um toque: combina com a proxima tecla
        self._ao_sistema: Callable[[str], None] = lambda nome: None

    # --- propriedades ----------------------------------------------------

    @property
    def sugestoes(self) -> list[str]:
        return list(self._sugestoes)

    @property
    def acento_pendente(self) -> str | None:
        return self._acento

    @property
    def max_sugestoes(self) -> int:
        return self._max

    def ligar_voz(self, ao_falar: Callable[[str], None]) -> None:
        """Define quem recebe o texto a ler (ex.: a sintese de voz)."""
        self._ao_falar = ao_falar

    def ligar_leitura_selecao(self, ao_ler: Callable[[str], None]) -> None:
        """Define quem recebe o texto selecionado quando se carrega em "Ler seleção"."""
        self._ao_ler = ao_ler

    def ligar_acoes_janela(self, ao_sistema: Callable[[str], None]) -> None:
        """Define quem executa as acoes de janela (minimizar teclado, fechar/maximizar janela ativa)."""
        self._ao_sistema = ao_sistema

    def acao(self, nome: str) -> None:
        """Acoes de edicao, de janela e leitura da seleccao."""
        self._ultimo_multi = None
        if nome not in ACOES:
            raise ValueError(f"Ação desconhecida: {nome}")
        if nome in ACOES_JANELA:
            # Nao alteram o texto: nao mexem na palavra em curso nem nas sugestoes.
            self._ao_sistema(nome)
            return
        if nome == "ler_selecao":
            texto = self._saida.ler_selecao()
            if texto:
                self._ao_ler(texto)
            return
        self._escoar_acento()
        # A palavra em curso deixa de corresponder ao texto: nao se aprende nem se sugere.
        self.palavra = ""
        self._frase = ""
        self._espaco_automatico = False
        self._saida.atalho(nome)
        self._atualizar()

    def definir_max_sugestoes(self, n: int) -> None:
        self._max = max(1, min(int(n), MAX_SUGESTOES))
        self._atualizar()

    # --- entrada ---------------------------------------------------------

    def texto(self, valor: str) -> None:
        self._ultimo_multi = None
        for caractere in valor:
            if self.ctrl and caractere.isascii() and caractere.isalnum():
                self._combinacao(caractere.lower())
            else:
                self.ctrl = False  # Ctrl com um simbolo nao combina: escreve o simbolo
                self._caractere(caractere)
        self._atualizar()

    def ditar(self, valor: str) -> None:
        """Texto ditado: comandos de voz (enter, muda de linha, ponto final...) viram teclas;
        o resto e escrito como texto colado.
        """
        for tipo, valor_segmento in segmentar(valor):
            if tipo == "texto":
                self._ditar_texto(valor_segmento)
            elif tipo == "tecla":
                self.tecla(valor_segmento)
            elif tipo == "acao":
                self.acao(valor_segmento)
            elif tipo == "simbolo":
                self.texto(valor_segmento)

    def _ditar_texto(self, valor: str) -> None:
        """Texto ditado por voz: o estado do editor e atualizado como em texto(), mas o
        texto e enviado de uma vez (colado), em vez de tecla a tecla.
        """
        capturado: list[str] = []
        original = self._saida

        class _Captura:
            def escrever(self, texto: str) -> None:
                capturado.append(texto)

            def _descarregar(self) -> None:
                # Antes de qualquer tecla ou atalho, o texto ja capturado tem de sair primeiro.
                if capturado:
                    original.colar_texto("".join(capturado))
                    capturado.clear()

            def tecla(self, nome: str) -> None:
                self._descarregar()
                original.tecla(nome)

            def sequencia(self, acoes) -> None:
                self._descarregar()
                original.sequencia(acoes)

            def atalho(self, nome: str) -> None:
                self._descarregar()
                original.atalho(nome)

            def enviar_atalho(self, passo: str) -> None:
                self._descarregar()
                original.enviar_atalho(passo)

            def ler_selecao(self) -> str:
                self._descarregar()
                return original.ler_selecao()

        self._saida = _Captura()
        try:
            self.texto(valor)
        finally:
            self._saida = original
        if capturado:
            original.colar_texto("".join(capturado))
            capturado.clear()

    def modificador(self, nome: str) -> None:
        if nome == "shift":
            self.shift = not self.shift
        elif nome == "ctrl":
            self.ctrl = not self.ctrl

    def _combinacao(self, tecla: str) -> None:
        """Envia Ctrl+tecla. Uma combinacao pode mudar o texto, por isso a palavra em curso e descartada."""
        self.ctrl = False
        self._ultimo_multi = None
        self._acento = None
        self.palavra = ""
        self._frase = ""
        self._espaco_automatico = False
        self._saida.enviar_atalho(f"ctrl+{tecla}")
        self._atualizar()

    def acento(self, nome: str) -> None:
        if nome not in ACENTOS:
            raise ValueError(f"Acento desconhecido: {nome}")
        self.ctrl = False
        self._ultimo_multi = None
        # Dois acentos seguidos: o primeiro sai isolado.
        self._escoar_acento()
        self._acento = nome
        self._espaco_automatico = False
        self._atualizar()

    def multitoque(self, chave: int, caracteres: str) -> None:
        """Tecla de toque repetido (ex.: "abc" no teclado tipo telefone).

        Um toque escreve a primeira letra. Toques seguidos na mesma tecla, dentro
        de MULTITOQUE_INTERVALO, trocam a letra anterior pela seguinte.
        """
        if len(caracteres) < 2:
            raise ValueError("Toque repetido precisa de pelo menos 2 caracteres.")
        self.ctrl = False
        agora = self._relogio()
        anterior = self._ultimo_multi
        self._escoar_acento()
        if (
            anterior is not None
            and anterior[0] == chave
            and agora - anterior[2] <= MULTITOQUE_INTERVALO
        ):
            indice = (anterior[1] + 1) % len(caracteres)
            inicio = anterior[3]
            self._apagar_ultimo()
            self.inicio_frase = inicio
        else:
            indice = 0
            inicio = self.inicio_frase
        self._ultimo_multi = None
        self._caractere(caracteres[indice])
        self._ultimo_multi = (chave, indice, agora, inicio)
        self._atualizar()

    def tecla(self, nome: str) -> None:
        self._ultimo_multi = None
        if self.ctrl:
            self._combinacao(nome)  # ex.: Ctrl + Home, Ctrl + Backspace
            return
        if nome == "backspace":
            # O acento pendente ainda nao foi escrito: apagar atinge o caracter anterior.
            self._acento = None
            if self.palavra:
                self.palavra = self.palavra[:-1]
            self._frase = self._frase[:-1]
            self._espaco_automatico = False
            self._saida.tecla("backspace")
            self._atualizar()
            return

        self._escoar_acento()
        if nome in TECLAS_QUE_FECHAM_PALAVRA:
            self._fechar_palavra()
            if nome == "espaco" and self._espaco_automatico:
                self._espaco_automatico = False
                self._atualizar()
                return
            self._espaco_automatico = False
            self._saida.tecla(nome)
            if nome == "enter":
                self.inicio_frase = True
                self._fechar_frase()
            self._atualizar()
            return
        # Teclas de navegacao mudam a posicao do cursor: o prefixo deixa de ser valido.
        self.palavra = ""
        self._espaco_automatico = False
        self._saida.tecla(nome)
        self._atualizar()

    def usar_sugestao(self, indice: int) -> None:
        self._ultimo_multi = None
        prefixo = self.palavra or self._fisico.prefixo
        if self._acento is not None or not prefixo:
            return
        if not 0 <= indice < len(self._sugestoes):
            return
        escolhida = self._ajustar_ao_prefixo(self._sugestoes[indice], prefixo)
        # Apagar o prefixo e escrever a palavra (pausa segura tratada em saida/windows.py).
        acoes = [("tecla", "backspace")] * len(prefixo) + [("texto", escolhida + " ")]
        self._saida.sequencia(acoes)
        self._frase = self._frase[: len(self._frase) - len(prefixo)] + escolhida + " "
        inicio = self._palavra_no_inicio if self.palavra else False
        self._dicionario.aprender(escolhida, inicio_frase=inicio)
        self._fisico.reiniciar()
        if self.falar_sugestao:
            self._ao_falar(escolhida)
        self.palavra = ""
        self.inicio_frase = False
        self.shift = False
        self._espaco_automatico = True
        self._atualizar()

    def evento_fisico(self, tipo: str, valor: str | None = None) -> None:
        """Eventos do teclado fisico (ver core/captura_teclado.py).

        Nao envia nada a aplicacao: so acompanha a palavra que o utilizador escreve,
        para oferecer sugestoes.
        """
        # O texto escrito fisicamente nao continua a palavra do teclado virtual.
        self.palavra = ""
        if tipo == "letra":
            self._fisico.letra(valor)
        elif tipo == "apagar":
            self._fisico.apagar()
        elif tipo == "reiniciar":
            self._fisico.reiniciar()
        elif tipo == "separador":
            palavra = self._fisico.separador()
            if palavra and self.aprender_fisico and len(palavra) >= 2:
                self._dicionario.aprender(palavra)
        self._atualizar()

    # --- internos --------------------------------------------------------

    def _caractere(self, caractere: str) -> None:
        if caractere.isalpha():
            if not self.palavra:
                self._palavra_no_inicio = self.inicio_frase
            maiuscula = self.shift or self.inicio_frase
            base = caractere.upper() if maiuscula else caractere
            acento = self._acento
            self._acento = None

            if acento is None:
                saida = base
            else:
                combinada = combinar(base, acento)
                if combinada is None:
                    # Sem letra acentuada possivel: o sinal sai isolado e a letra começa palavra nova.
                    self._fechar_palavra()
                    self._saida.escrever(ACENTOS[acento][1])
                    saida = base
                else:
                    saida = combinada

            self.shift = False
            self.inicio_frase = False
            self._espaco_automatico = False
            self.palavra += saida
            self._frase += saida
            self._saida.escrever(saida)
            return

        self._escoar_acento()
        self._fechar_palavra()
        if caractere == " " and self._espaco_automatico:
            # A sugestao ja escreveu o espaco: nao o duplicar.
            self._espaco_automatico = False
            self._frase += " "
            return
        if caractere in PONTUACAO and self._espaco_automatico:
            # Sem espaco antes da pontuacao ("Casa." e nao "Casa .").
            self._saida.tecla("backspace")
            self._frase = self._frase[:-1]
        self._espaco_automatico = False
        self._frase += caractere
        if caractere in FIM_DE_FRASE:
            self.inicio_frase = True
        self._saida.escrever(caractere)
        if caractere in FIM_DE_FRASE:
            self._fechar_frase()

    def _apagar_ultimo(self) -> None:
        """Apaga o caracter escrito pelo toque anterior (no texto e na palavra em curso)."""
        if self.palavra:
            self.palavra = self.palavra[:-1]
        self._espaco_automatico = False
        self._saida.tecla("backspace")

    def _escoar_acento(self) -> None:
        """Escreve o sinal isolado de um acento que nao foi seguido de letra."""
        if self._acento is not None:
            sinal = ACENTOS[self._acento][1]
            self._acento = None
            self._fechar_palavra()
            self._saida.escrever(sinal)

    def _fechar_palavra(self) -> None:
        if self.palavra:
            self._dicionario.aprender(self.palavra, inicio_frase=self._palavra_no_inicio)
            if self.falar_palavra:
                self._ao_falar(self.palavra)
        self.palavra = ""

    def _fechar_frase(self) -> None:
        """Le a frase acumulada (se a opcao estiver ativa) e recomeca a acumular."""
        frase = self._frase.strip()
        self._frase = ""
        if frase and self.falar_frase:
            self._ao_falar(frase)

    def _atualizar(self) -> None:
        # Com um acento pendente, o prefixo nao corresponde ao texto: sem sugestoes.
        prefixo = self.palavra or self._fisico.prefixo
        if prefixo and self._acento is None:
            self._sugestoes = self._dicionario.sugerir(prefixo, self._max)
        else:
            self._sugestoes = []
        self.ao_atualizar()

    @staticmethod
    def _ajustar_ao_prefixo(sugestao: str, prefixo: str) -> str:
        """Se o utilizador comecou com maiuscula, a sugestao tambem comeca."""
        if prefixo[:1].isupper() and sugestao:
            return sugestao[0].upper() + sugestao[1:]
        return sugestao
