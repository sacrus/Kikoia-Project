"""Controlador: liga perfil, layouts, temas e saida de teclas.

Toda a alteracao de configuracao passa por _com_aprovacao, que aplica a
politica de supervisao e, se necessario, pede o codigo do adulto.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..gateway.servidor import PORTA_POR_OMISSAO
from . import arranque, idiomas
from .comandos import Comando, ComandoErro, carregar, executar, gravar, novo_id, validar
from .layout import EXTENSAO, Layout, LayoutInvalido, carregar_layout, descobrir_layouts
from .layout_editor import (
    apagar_layout_em_pasta,
    gravar_modelo_em_ficheiro,
    guardar_layout_em_pasta,
    modelo_de,
    remover_teclas_de_comando,
    usa_comando,
    validar_modelo,
)
from .perfil import AMBITO_POR_OMISSAO, AMBITOS_VALIDOS, Perfil, RepositorioPerfis, Supervisao
from .politica import PedidoAprovacaoNecessario, aprovar, executar_acao
from .seguranca import gerar_hash_pin
from .saida import Saida
from .tema import Tema, cor_texto_para, descobrir_temas, guardar_tema

TENTATIVAS_PIN = 3
LAYOUT_POR_OMISSAO = "QWERTY"
TEMA_POR_OMISSAO = "Claro"
NOME_TEMA_PERSONALIZADO = "Personalizado"


def _ambito_valido(ambito: list[str]) -> list[str]:
    """So aceita acoes conhecidas, sem repetidos e na ordem recebida."""
    limpo: list[str] = []
    for item in ambito:
        if item in AMBITOS_VALIDOS and item not in limpo:
            limpo.append(item)
    return limpo


class Aplicacao:
    def __init__(
        self,
        saida: Saida,
        repo: RepositorioPerfis,
        perfil: Perfil,
        pedir_pin: Callable[[], str | None],
        pastas_layouts: list[Path],
        pastas_temas: list[Path],
        pasta_temas_utilizador: Path,
        pasta_layouts_utilizador: Path | None = None,
        pasta_comandos: Path | None = None,
    ) -> None:
        self.saida = saida
        self.repo = repo
        self.perfil = perfil
        self._pedir_pin = pedir_pin
        self._pasta_temas_utilizador = Path(pasta_temas_utilizador)
        # Pasta onde os teclados criados pelo utilizador sao gravados. Deve estar
        # tambem em pastas_layouts, para serem carregados no arranque.
        self._pasta_layouts_utilizador = Path(pasta_layouts_utilizador) if pasta_layouts_utilizador else None
        self._pastas_layouts = [Path(p) for p in pastas_layouts]
        # Teclas personalizadas (programas do PC), guardadas na pasta do utilizador.
        self._pasta_comandos = Path(pasta_comandos) if pasta_comandos else None
        self.comandos: dict[str, Comando] = carregar(self._pasta_comandos) if self._pasta_comandos else {}

        self._historico: list[str] = []
        self.layouts: dict[str, Layout] = descobrir_layouts(pastas_layouts)
        self.temas: dict[str, Tema] = descobrir_temas(pastas_temas)
        if not self.layouts or not self.temas:
            raise RuntimeError("Não foram encontrados layouts ou temas válidos.")

        self.layout = self.layouts.get(
            perfil.preferencias.get("layout", ""),
            self.layouts.get(LAYOUT_POR_OMISSAO, next(iter(self.layouts.values()))),
        )
        self.tema = self.temas.get(
            perfil.preferencias.get("tema", ""),
            self.temas.get(TEMA_POR_OMISSAO, next(iter(self.temas.values()))),
        )

        # Novas preferencias: auto-iniciar e tempo de auto-reconexao Bluetooth
        # Ligado por omissao: o PC escuta o telemovel de confianca ao arrancar (ver __main__).
        self._auto_iniciar = bool(perfil.preferencias.get("auto_iniciar", True))
        self._idioma = idiomas.idioma_valido(perfil.preferencias.get("idioma"))
        self._verificar_atualizacoes = bool(perfil.preferencias.get("verificar_atualizacoes", True))
        self._endereco_bluetooth_ultimo = perfil.preferencias.get("endereco_bluetooth_ultimo")
        self._timer_auto_conexao = None

    # --- aprovacao -------------------------------------------------------

    def _com_aprovacao(self, acao: str, alteracao: Callable[[], None]) -> bool:
        try:
            executar_acao(self.perfil, acao, alteracao)
            return True
        except PedidoAprovacaoNecessario:
            pass
        for _ in range(TENTATIVAS_PIN):
            pin = self._pedir_pin()
            if pin is None:
                return False
            try:
                executar_acao(self.perfil, acao, alteracao, pin=pin)
                return True
            except PedidoAprovacaoNecessario:
                continue
        return False

    # --- layouts ---------------------------------------------------------

    def mudar_layout(self, nome: str) -> Layout | None:
        novo = self.layouts[nome]

        def aplicar() -> None:
            self.layout = novo
            self.perfil.preferencias["layout"] = nome
            self.repo.guardar(self.perfil)

        return novo if self._com_aprovacao("alterar_layout", aplicar) else None

    def proximo_layout(self) -> Layout | None:
        nomes = list(self.layouts)
        indice = nomes.index(self.layout.nome)
        return self.mudar_layout(nomes[(indice + 1) % len(nomes)])

    def navegar_para(self, nome: str) -> Layout | None:
        """Muda de teclado a partir de uma tecla de atalho.

        E uso diario, nao configuracao: nao pede codigo e nao fica guardado
        (ao reiniciar volta ao teclado predefinido do perfil).
        """
        if nome not in self.layouts:
            return None
        if nome != self.layout.nome:
            self._historico.append(self.layout.nome)
            self.layout = self.layouts[nome]
        return self.layout

    def voltar_teclado(self) -> Layout | None:
        """Volta ao teclado anterior, se houver (tecla "Voltar")."""
        while self._historico:
            nome = self._historico.pop()
            if nome in self.layouts:
                self.layout = self.layouts[nome]
                return self.layout
        return None

    def guardar_layout(self, modelo: dict) -> Layout | None:
        """Grava um teclado criado/alterado pelo utilizador e passa a usa-lo.

        Erros de formato lancam LayoutInvalido antes de pedir qualquer codigo.
        Devolve None se a alteracao nao foi aprovada pelo adulto.
        """
        if self._pasta_layouts_utilizador is None:
            raise RuntimeError("Pasta de teclados do utilizador nao configurada.")
        validar_modelo(modelo)
        resultado: dict[str, Layout] = {}

        def aplicar() -> None:
            guardado = guardar_layout_em_pasta(modelo, self._pasta_layouts_utilizador)
            self.layouts = descobrir_layouts(self._pastas_layouts)
            self.layout = self.layouts[guardado.nome]
            self.perfil.preferencias["layout"] = guardado.nome
            self.repo.guardar(self.perfil)
            resultado["layout"] = self.layout

        return resultado["layout"] if self._com_aprovacao("alterar_layout", aplicar) else None

    def apagar_layout(self, nome: str) -> bool:
        """Apaga um teclado criado pelo utilizador. Modelos do projeto nao se apagam."""
        if self._pasta_layouts_utilizador is None:
            return False
        apagado = {"ok": False}

        def aplicar() -> None:
            apagado["ok"] = apagar_layout_em_pasta(nome, self._pasta_layouts_utilizador)
            if not apagado["ok"]:
                return
            self.layouts = descobrir_layouts(self._pastas_layouts)
            if self.layout.nome == nome:
                # Se existir um modelo do projeto com o mesmo nome, volta a ele; senao usa o predefinido.
                if nome in self.layouts:
                    self.layout = self.layouts[nome]
                else:
                    self.layout = self.layouts.get(LAYOUT_POR_OMISSAO, next(iter(self.layouts.values())))
                self.perfil.preferencias["layout"] = self.layout.nome
                self.repo.guardar(self.perfil)

        return self._com_aprovacao("alterar_layout", aplicar) and apagado["ok"]

    # --- temas -----------------------------------------------------------

    def mudar_tema(self, nome: str) -> Tema | None:
        novo = self.temas[nome]

        def aplicar() -> None:
            self.tema = novo
            self.perfil.preferencias["tema"] = nome
            self.repo.guardar(self.perfil)

        return novo if self._com_aprovacao("alterar_tema", aplicar) else None

    def proximo_tema(self) -> Tema | None:
        nomes = list(self.temas)
        indice = nomes.index(self.tema.nome)
        return self.mudar_tema(nomes[(indice + 1) % len(nomes)])

    # --- supervisao do adulto ---------------------------------------------
    # Ativar nao pede codigo (e uma restricao). Qualquer alteracao ou
    # desativacao, com supervisao ativa, pede sempre o codigo do adulto.

    def estado_supervisao(self) -> tuple[bool, list[str]]:
        sup = self.perfil.supervisao
        return sup.ativa, list(sup.ambito)

    def _exigir_pin_adulto(self) -> bool:
        for _ in range(TENTATIVAS_PIN):
            pin = self._pedir_pin()
            if pin is None:
                return False
            if aprovar(self.perfil, pin):
                return True
        return False

    def _gravar_supervisao(self, sup: Supervisao) -> None:
        self.perfil.supervisao = sup
        self.repo.guardar(self.perfil)

    def ativar_supervisao(self, pin: str, ambito: list[str]) -> None:
        """Liga a supervisao. O codigo deve ter pelo menos 4 caracteres (ValueError)."""
        if self.perfil.supervisao.ativa:
            raise RuntimeError("A supervisão já está ativa.")
        novo_hash = gerar_hash_pin(pin)  # valida o codigo antes de alterar seja o que for
        self._gravar_supervisao(Supervisao(ativa=True, codigo_hash=novo_hash, ambito=_ambito_valido(ambito)))

    def atualizar_supervisao(self, ambito: list[str], novo_pin: str | None = None) -> bool:
        """Altera o que fica protegido e, opcionalmente, o codigo. Pede o codigo atual."""
        sup = self.perfil.supervisao
        if not sup.ativa:
            raise RuntimeError("A supervisão não está ativa.")
        novo_hash = gerar_hash_pin(novo_pin) if novo_pin else sup.codigo_hash
        if not self._exigir_pin_adulto():
            return False
        self._gravar_supervisao(Supervisao(ativa=True, codigo_hash=novo_hash, ambito=_ambito_valido(ambito)))
        return True

    def desativar_supervisao(self) -> bool:
        if not self.perfil.supervisao.ativa:
            return False
        if not self._exigir_pin_adulto():
            return False
        self._gravar_supervisao(Supervisao(ativa=False, ambito=list(AMBITO_POR_OMISSAO)))
        return True

    # --- voz -------------------------------------------------------------
    # Os interruptores Falar/Ditar sao uso diario: nao pedem codigo.
    # As opcoes de leitura e a escolha da voz sao configuracoes: pedem codigo.

    def preferencias_voz(self) -> dict:
        padrao = {"falar": False, "ler_palavra": False, "ler_frase": False,
                  "ler_sugestao": False, "voz_id": None}
        return {**padrao, **self.perfil.preferencias.get("voz", {})}

    def alternar_falar(self, ligado: bool) -> None:
        """Liga ou desliga a leitura em voz alta (guardado no perfil).

        Ligar o botao Falar le cada palavra e cada frase. As opcoes detalhadas
        (sugestoes, desligar uma delas) continuam nas Opcoes de voz.
        """
        voz = self.preferencias_voz()
        voz["falar"] = bool(ligado)
        if ligado:
            voz["ler_palavra"] = True
            voz["ler_frase"] = True
        self.perfil.preferencias["voz"] = voz
        self.repo.guardar(self.perfil)

    def definir_opcoes_voz(self, ler_palavra: bool, ler_frase: bool, ler_sugestao: bool,
                           voz_id: str | None) -> bool:
        voz = self.preferencias_voz()
        voz.update(ler_palavra=bool(ler_palavra), ler_frase=bool(ler_frase),
                   ler_sugestao=bool(ler_sugestao), voz_id=voz_id)

        def aplicar() -> None:
            self.perfil.preferencias["voz"] = voz
            self.repo.guardar(self.perfil)

        return self._com_aprovacao("definicoes", aplicar)

    # --- teclas personalizadas (programas do PC) ----------------------------------
    # Criar, alterar e apagar e configuracao (supervisionada). Executar nao pede codigo:
    # e o uso diario, e so executa comandos ja guardados.

    def _exigir_pasta_comandos(self) -> Path:
        if self._pasta_comandos is None:
            raise RuntimeError("Pasta das teclas personalizadas nao configurada.")
        return self._pasta_comandos

    def guardar_comando(self, id_: str | None, rotulo: str, comando: str) -> Comando | None:
        pasta = self._exigir_pasta_comandos()
        rotulo, comando = validar(rotulo, comando)
        ident = id_ or novo_id()
        novo = Comando(ident, rotulo, comando)

        def aplicar() -> None:
            self.comandos[ident] = novo
            gravar(pasta, self.comandos)

        return novo if self._com_aprovacao("definicoes", aplicar) else None

    def apagar_comando(self, id_: str, remover_teclas: bool = False) -> bool:
        """Apaga o comando. Com remover_teclas, tira tambem as teclas que o usam nos teclados guardados."""
        pasta = self._exigir_pasta_comandos()
        if id_ not in self.comandos:
            return False

        def aplicar() -> None:
            self.comandos.pop(id_, None)
            gravar(pasta, self.comandos)
            if remover_teclas:
                self._remover_teclas_de_comando(id_)

        return self._com_aprovacao("definicoes", aplicar)

    def teclados_com_comando(self, id_: str) -> list[str]:
        """Nomes dos teclados guardados pelo utilizador que usam esta tecla de comando."""
        return [layout.nome for _, layout in self._ficheiros_do_utilizador() if usa_comando(layout, id_)]

    def _ficheiros_do_utilizador(self) -> list[tuple[Path, Layout]]:
        pasta = self._pasta_layouts_utilizador
        if pasta is None or not Path(pasta).is_dir():
            return []
        resultado = []
        for ficheiro in Path(pasta).glob(f"*{EXTENSAO}"):
            try:
                resultado.append((ficheiro, carregar_layout(ficheiro)))
            except LayoutInvalido:
                continue
        return resultado

    def _remover_teclas_de_comando(self, id_: str) -> None:
        for ficheiro, layout in self._ficheiros_do_utilizador():
            if not usa_comando(layout, id_):
                continue
            modelo = modelo_de(layout)
            remover_teclas_de_comando(modelo, id_)
            gravar_modelo_em_ficheiro(modelo, ficheiro)
        self.layouts = descobrir_layouts(self._pastas_layouts)
        if self.layout.nome in self.layouts:
            self.layout = self.layouts[self.layout.nome]

    def guardar_comandos_em_lote(self, lista: list[Comando]) -> bool:
        pasta = self._exigir_pasta_comandos()

        def aplicar() -> None:
            for c in lista:
                self.comandos[c.id] = c
            gravar(pasta, self.comandos)

        return self._com_aprovacao("definicoes", aplicar)

    def executar_comando(self, id_: str) -> None:
        """Executa a tecla personalizada pelo identificador. Lanca ComandoErro se falhar."""
        comando = self.comandos.get(id_)
        if comando is None:
            raise ComandoErro("Esta tecla já não existe. Atualize o teclado no computador.")
        executar(comando.comando)

    # --- gateway (telemovel) ----------------------------------------------------
    # Abrir o gateway a emparelhamento, gerar codigos e mudar a porta sao definicoes:
    # num perfil supervisionado pedem o codigo do adulto.

    def pedir_aprovacao_definicoes(self) -> bool:
        return self._com_aprovacao("definicoes", lambda: None)

    def preferencias_gateway(self) -> dict:
        return {"porta": int(self.perfil.preferencias.get("gateway", {}).get("porta", PORTA_POR_OMISSAO))}

    def definir_porta_gateway(self, porta: int) -> bool:
        if not 1024 <= int(porta) <= 65535:
            raise ValueError("A porta tem de estar entre 1024 e 65535.")
        porta = int(porta)

        def aplicar() -> None:
            self.perfil.preferencias["gateway"] = {"porta": porta}
            self.repo.guardar(self.perfil)

        return self._com_aprovacao("definicoes", aplicar)

    @property
    def idioma(self) -> str:
        """Idioma guardado no perfil (aplicado ao arrancar o teclado)."""
        return self._idioma

    @property
    def verificar_atualizacoes(self) -> bool:
        return self._verificar_atualizacoes

    def definir_verificar_atualizacoes(self, ativo: bool) -> bool:
        def aplicar() -> None:
            self.perfil.preferencias["verificar_atualizacoes"] = bool(ativo)
            self.repo.guardar(self.perfil)
            self._verificar_atualizacoes = bool(ativo)

        return self._com_aprovacao("definicoes", aplicar)

    def definir_idioma(self, codigo: str) -> bool:
        codigo = idiomas.idioma_valido(codigo)

        def aplicar() -> None:
            self.perfil.preferencias["idioma"] = codigo
            self.repo.guardar(self.perfil)
            self._idioma = codigo

        return self._com_aprovacao("definicoes", aplicar)

    def definir_arranque_sistema(self, ativo: bool) -> bool:
        """Arranque com o Windows/Linux. Guardado no sistema, nao no perfil."""
        def aplicar() -> None:
            arranque.definir(ativo)

        return self._com_aprovacao("definicoes", aplicar)

    def definir_auto_iniciar(self, iniciar: bool) -> bool:
        def aplicar() -> None:
            self.perfil.preferencias["auto_iniciar"] = bool(iniciar)
            self.repo.guardar(self.perfil)
            self._auto_iniciar = bool(iniciar)

        return self._com_aprovacao("definicoes", aplicar)

    # --- teclado fisico (fase 7) ----------------------------------------------
    # Observar teclas e uma capacidade sensivel: desligada por omissao e sempre
    # tratada como configuracao (pede o codigo do adulto em perfis supervisionados).

    def preferencias_fisico(self) -> dict:
        padrao = {"ativo": False, "aprender": False}
        return {**padrao, **self.perfil.preferencias.get("teclado_fisico", {})}

    def definir_teclado_fisico(self, ativo: bool, aprender: bool) -> bool:
        valor = {"ativo": bool(ativo), "aprender": bool(ativo and aprender)}

        def aplicar() -> None:
            self.perfil.preferencias["teclado_fisico"] = valor
            self.repo.guardar(self.perfil)

        return self._com_aprovacao("definicoes", aplicar)

    def definir_max_sugestoes(self, n: int) -> bool:
        """Numero de sugestoes (1 a 10). E uma definicao: segue a politica de supervisao."""
        n = max(1, min(int(n), 10))

        def aplicar() -> None:
            self.perfil.preferencias["max_sugestoes"] = n
            self.repo.guardar(self.perfil)

        return self._com_aprovacao("definicoes", aplicar)

    def personalizar(
        self,
        cor_fundo: str,
        cor_tecla: str,
        imagem: Path | None,
    ) -> Tema | None:
        tema = Tema(
            nome=NOME_TEMA_PERSONALIZADO,
            cor_fundo=cor_fundo,
            cor_tecla=cor_tecla,
            cor_texto=cor_texto_para(cor_tecla),
            cor_tecla_premida="#FFD54F",
            cor_texto_premido="#000000",
            tamanho_fonte=self.tema.tamanho_fonte,
            imagem_fundo=imagem,
            opacidade_imagem=self.tema.opacidade_imagem,
        )
        caminho = self._pasta_temas_utilizador / "personalizado.kbtheme.json"

        def aplicar() -> None:
            guardar_tema(tema, caminho)
            self.temas[tema.nome] = tema
            self.tema = tema
            self.perfil.preferencias["tema"] = tema.nome
            self.repo.guardar(self.perfil)

        return tema if self._com_aprovacao("alterar_tema", aplicar) else None
