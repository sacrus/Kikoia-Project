"""Editor visual de teclados.

Ecra dividido em duas partes:
  1. Grelha do teclado: cada linha e uma fila de teclas. Cada linha tem um "+"
     para acrescentar a tecla escolhida na parte 2.
  2. Lista de teclas: todos os simbolos disponiveis. Escolhe-se um e depois
     clica-se num "+" da grelha.
Em cima, modelos rapidos (QWERTY, Numerico, Minimal...) preenchem a grelha.
"""

from __future__ import annotations

from teclado.core.idiomas import t
import copy
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from teclado.core.acentos import ACENTOS
from teclado.core.layout import MODIFICADORES, Layout, LayoutInvalido, validar_tecla
from teclado.core.layout_editor import (
    adicionar_linha,
    adicionar_tecla,
    modelo_de,
    modelo_vazio,
    mover_tecla,
    remover_linha,
    remover_tecla,
    tecla_dict,
)
from teclado.core.rotulos import rotulo_tecla
from teclado.core.saida import ACOES, TECLAS_ESPECIAIS
from teclado.ui.comandos_ui import DialogoComando
from teclado.ui.dialogos import executar_dialogo

def tipos_tecla() -> tuple[tuple[str, str], ...]:
    return (
        ("texto", t("editor.tipo_texto")),
        ("tecla", t("editor.tipo_tecla")),
        ("modificador", t("editor.shift")),
        ("acento", t("editor.tipo_acento")),
        ("multitoque", t("editor.tipo_multitoque")),
        ("acao", t("editor.tipo_acao")),
    )


def rotulo_tipo() -> dict[str, str]:
    return dict(tipos_tecla()) | {"navegar": t("editor.tipo_navegar"), "comando": t("editor.tipo_comando")}


def rotulos_acoes() -> dict[str, tuple[str, float]]:
    return {
        "apagar_palavra": (t("editor.acao_apagar_palavra"), 1.5),
        "apagar_linha": (t("editor.acao_apagar_linha"), 1.5),
        "selecionar_palavra": (t("editor.acao_selecionar_palavra"), 1.5),
        "selecionar_linha": (t("editor.acao_selecionar_linha"), 1.5),
        "ler_selecao": (t("editor.acao_ler_selecao"), 1.5),
        "minimizar_teclado": (t("editor.acao_minimizar_teclado"), 1.5),
        "fechar_janela": (t("editor.acao_fechar_janela"), 1.5),
        "minimizar_janela": (t("editor.acao_minimizar_janela"), 1.5),
        "maximizar_janela": (t("editor.acao_maximizar_janela"), 1.5),
        "navegar_janelas": (t("editor.acao_navegar_janelas"), 1.5),
    }


def rotulo_voltar() -> str:
    return t("editor.voltar")


# Teclas de funcao e de navegacao (tecla especial, rotulo).
TECLAS_FUNCAO = (
    ("Home", "home"), ("End", "end"), ("Pg Up", "pgup"), ("Pg Dn", "pgdn"),
    ("Prt Sc", "prtsc"), ("Insert", "insert"), ("Caps Lock", "capslock"),
    ("Tab", "tab"), ("Esc", "esc"), ("Delete", "delete"),
)
MODELOS_PRONTOS = ("QWERTY", "Numérico", "Minimal", "Abecedário", "Vogais")  # nomes dos layouts (dados)
_CHAVE_MODELO = {
    "QWERTY": "editor.modelo_qwerty",
    "Numérico": "editor.modelo_numerico",
    "Minimal": "editor.modelo_minimal",
    "Abecedário": "editor.modelo_abecedario",
    "Vogais": "editor.modelo_vogais",
}


def rotulo_modelo(nome: str) -> str:
    """Nome do modelo para mostrar (o nome real, usado nos layouts, nao muda)."""
    return t(_CHAVE_MODELO[nome]) if nome in _CHAVE_MODELO else nome
COLUNAS_LISTA = 12
TIPOS_COM_TEXTO = ("texto", "multitoque")


def simbolos_disponiveis(atalhos: list[tuple[str, str]] = (), comandos=()) -> list[dict]:
    """Teclas que o utilizador pode escolher, por ordem de uso.

    atalhos: (rotulo, nome do teclado) dos teclados disponibilizados como atalho.
    """
    itens: list[dict] = []
    # Teclas de atalho para outros teclados (criadas pelo utilizador).
    itens += [tecla_dict(rotulo, "navegar", nome, 1.5) for rotulo, nome in atalhos]
    itens += [tecla_dict(rotulo_voltar(), "navegar", "__anterior__", 1.5)]
    # Acoes de edicao.
    itens += [tecla_dict(rotulo, "acao", acao, largura) for acao, (rotulo, largura) in rotulos_acoes().items()]
    # Modificador Ctrl (de um toque) e teclas de funcao/navegacao.
    itens += [tecla_dict("Ctrl", "modificador", "ctrl", 1.5)]
    itens += [tecla_dict(rotulo_tecla("tecla", valor, rotulo), "tecla", valor) for rotulo, valor in TECLAS_FUNCAO]
    itens += [tecla_dict(letra, "texto", letra) for letra in "abcdefghijklmnopqrstuvwxyzç"]
    itens += [tecla_dict(letra, "texto", letra) for letra in "àáâãéêíóôõú"]
    itens += [tecla_dict(letra, "texto", letra) for letra in "ÀÁÂÃÉÊÍÓÔÕÚÇ"]
    itens += [tecla_dict(d, "texto", d) for d in "0123456789"]
    itens += [tecla_dict(p, "texto", p) for p in ".,;:?!-'\"()/@"]
    itens += [tecla_dict(sinal, "acento", nome) for nome, (_, sinal) in ACENTOS.items()]
    itens += [
        tecla_dict(t("editor.shift"), "modificador", "shift", 1.5),
        tecla_dict(t("editor.espaco"), "tecla", "espaco", 3.0),
        tecla_dict(t("editor.apagar_tecla_especial"), "tecla", "backspace", 2.0),
        tecla_dict("Enter", "tecla", "enter", 2.0),
        tecla_dict("←", "tecla", "seta_esq"),
        tecla_dict("→", "tecla", "seta_dir"),
        tecla_dict("↑", "tecla", "seta_cima"),
        tecla_dict("↓", "tecla", "seta_baixo"),
    ]
    # Teclas personalizadas (programas do PC), criadas em "Teclas personalizadas".
    itens += [tecla_dict(c.rotulo, "comando", c.id, 1.5) for c in comandos]
    # Garante que so aparecem teclas especiais que existem no sistema.
    for item in itens:
        if item["acao"]["tipo"] == "tecla":
            assert item["acao"]["valor"] in TECLAS_ESPECIAIS
    return itens


def atalhos_de(layouts: dict[str, Layout], excluir: str | None = None) -> list[tuple[str, str]]:
    """(rotulo, nome) dos teclados que se disponibilizaram como atalho."""
    return [
        (layout.atalho, nome)
        for nome, layout in layouts.items()
        if layout.atalho and nome != excluir
    ]


class DialogoTecla(QDialog):
    """Cria ou altera uma tecla em detalhe (usado para casos avancados)."""

    def __init__(self, parent: QWidget | None, inicial: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("editor.tecla_titulo"))
        self._rotulo = QLineEdit()
        self._rotulo.setMaxLength(20)
        self._tipo = QComboBox()
        for tipo, descricao in tipos_tecla():
            self._tipo.addItem(descricao, tipo)
        self._valor_texto = QLineEdit()
        self._valor_texto.setMaxLength(20)
        self._valor_lista = QComboBox()
        self._dica = QLabel(t("editor.tecla_dica"))
        self._dica.setWordWrap(True)
        self._largura = QDoubleSpinBox()
        self._largura.setRange(0.5, 6.0)
        self._largura.setSingleStep(0.5)
        self._largura.setValue(1.0)

        contentor_valor = QWidget()
        valor_layout = QVBoxLayout(contentor_valor)
        valor_layout.setContentsMargins(0, 0, 0, 0)
        valor_layout.addWidget(self._valor_texto)
        valor_layout.addWidget(self._valor_lista)
        valor_layout.addWidget(self._dica)

        formulario = QFormLayout(self)
        formulario.addRow(t("editor.tecla_rotulo"), self._rotulo)
        formulario.addRow(t("geral.tipo"), self._tipo)
        formulario.addRow(t("geral.valor"), contentor_valor)
        formulario.addRow(t("geral.largura"), self._largura)
        caixa = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        caixa.accepted.connect(self.accept)
        caixa.rejected.connect(self.reject)
        formulario.addRow(caixa)

        self._tipo.currentIndexChanged.connect(self._atualizar_valor)
        if inicial is not None:
            self._preencher(inicial)
        self._atualizar_valor()

    def _atualizar_valor(self) -> None:
        tipo = self._tipo.currentData()
        self._valor_texto.setVisible(tipo in TIPOS_COM_TEXTO)
        self._dica.setVisible(tipo == "multitoque")
        self._valor_lista.setVisible(tipo not in TIPOS_COM_TEXTO)
        self._valor_lista.clear()
        if tipo == "tecla":
            opcoes = sorted(TECLAS_ESPECIAIS)
        elif tipo == "modificador":
            opcoes = sorted(MODIFICADORES)
        elif tipo == "acento":
            opcoes = list(ACENTOS)
        elif tipo == "acao":
            opcoes = sorted(ACOES)
        else:
            opcoes = []
        for opcao in opcoes:
            self._valor_lista.addItem(opcao, opcao)

    def _preencher(self, tecla: dict) -> None:
        self._rotulo.setText(tecla["rotulo"])
        self._tipo.setCurrentIndex(self._tipo.findData(tecla["acao"]["tipo"]))
        valor = tecla["acao"]["valor"]
        if tecla["acao"]["tipo"] in TIPOS_COM_TEXTO:
            self._valor_texto.setText(valor)
        else:
            self._valor_lista.setCurrentIndex(self._valor_lista.findData(valor))
        self._largura.setValue(float(tecla.get("largura", 1.0)))

    def resultado(self) -> dict:
        tipo = self._tipo.currentData()
        valor = self._valor_texto.text() if tipo in TIPOS_COM_TEXTO else self._valor_lista.currentData()
        rotulo = self._rotulo.text().strip() or str(valor)
        return tecla_dict(rotulo, tipo, valor, float(self._largura.value()))

    def accept(self) -> None:  # noqa: D401 (nome do Qt)
        try:
            validar_tecla(self.resultado())
        except LayoutInvalido as erro:
            QMessageBox.warning(self, t("geral.tecla_invalida"), str(erro))
            return
        super().accept()


class DialogoEditorLayout(QDialog):
    """Editor visual: grelha do teclado em cima, lista de teclas em baixo.

    guardar(modelo) -> Layout | None   (None = nao aprovado; LayoutInvalido se mal formado)
    apagar(nome) -> bool
    """

    def __init__(
        self,
        parent: QWidget | None,
        layouts: dict[str, Layout],
        atual: Layout | None,
        guardar: Callable[[dict], Layout | None],
        apagar: Callable[[str], bool],
        comandos: dict | None = None,
        guardar_comando: Callable[[str | None, str, str], object] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("editor.titulo"))
        self.resize(820, 760)  # tamanho ao restaurar a janela
        # Abre maximizado: o teclado completo fica visivel sem puxar as bordas.
        self.estado_inicial = Qt.WindowState.WindowMaximized
        self._layouts = layouts
        self._guardar_fn = guardar
        self._apagar_fn = apagar
        self.guardado: Layout | None = None
        self.apagado = False
        self._modelo = modelo_de(atual) if atual is not None else modelo_vazio("Novo teclado")

        self._cel: tuple[int, int] | None = None   # tecla selecionada na grelha
        self._escolhida: dict | None = None         # tecla escolhida na lista de baixo
        self._celulas: dict[tuple[int, int], QPushButton] = {}
        self._paleta: list[tuple[QPushButton, dict]] = []
        self._a_atualizar = False

        # --- nome e modelos rapidos ----------------------------------------
        self._nome = QLineEdit(self._modelo["nome"])
        self._nome.setMaxLength(40)
        self._nome.setPlaceholderText(t("editor.nome_placeholder"))

        # Atalho: esta tecla leva a este teclado a partir de qualquer outro teclado.
        atalho_atual = self._modelo.get("atalho")
        self._atalho_ativo = QCheckBox(t("editor.atalho"))
        self._atalho_ativo.setChecked(atalho_atual is not None)
        self._atalho_rotulo = QLineEdit(atalho_atual["rotulo"] if atalho_atual else self._modelo["nome"][:20])
        self._atalho_rotulo.setMaxLength(20)
        self._atalho_rotulo.setPlaceholderText(t("editor.atalho_placeholder"))
        self._atalho_rotulo.setEnabled(self._atalho_ativo.isChecked())
        self._atalho_ativo.toggled.connect(self._atalho_rotulo.setEnabled)
        linha_atalho = QHBoxLayout()
        linha_atalho.addWidget(self._atalho_ativo, 1)
        linha_atalho.addWidget(QLabel(t("editor.rotulo")))
        linha_atalho.addWidget(self._atalho_rotulo)

        modelos = QHBoxLayout()
        modelos.addWidget(QLabel(t("editor.comecar_com")))
        for nome in MODELOS_PRONTOS:
            botao = QPushButton(rotulo_modelo(nome))
            botao.setEnabled(nome in layouts)
            botao.clicked.connect(lambda _=False, n=nome: self._aplicar_pronto(n))
            modelos.addWidget(botao)
        modelos.addStretch(1)

        # --- 1. grelha do teclado ----------------------------------------
        self._grelha_conteudo = QWidget()
        self._grelha = QVBoxLayout(self._grelha_conteudo)
        self._grelha.setContentsMargins(4, 4, 4, 4)
        self._grelha.setSpacing(6)
        area_grelha = QScrollArea()
        area_grelha.setWidgetResizable(True)
        area_grelha.setWidget(self._grelha_conteudo)
        area_grelha.setMinimumHeight(190)

        botao_nova_linha = QPushButton(t("editor.nova_linha"))
        botao_nova_linha.clicked.connect(self._nova_linha)

        # Propriedades da tecla selecionada
        self._info = QLabel()
        self._spin_largura = QDoubleSpinBox()
        self._spin_largura.setRange(0.5, 6.0)
        self._spin_largura.setSingleStep(0.5)
        self._spin_largura.setValue(1.0)
        self._spin_largura.setPrefix(t("editor.largura_prefixo"))
        self._spin_largura.valueChanged.connect(self._alterar_largura)
        self._botao_editar = QPushButton(t("geral.editar"))
        self._botao_editar.clicked.connect(self._editar_selecionada)
        self._botao_apagar_tecla = QPushButton(t("editor.apagar_tecla"))
        self._botao_apagar_tecla.clicked.connect(self._apagar_selecionada)
        self._botao_esq = QPushButton(t("editor.mover_esquerda"))
        self._botao_esq.clicked.connect(lambda: self._mover_selecionada(-1))
        self._botao_dir = QPushButton(t("editor.mover_direita"))
        self._botao_dir.clicked.connect(lambda: self._mover_selecionada(1))
        propriedades = QHBoxLayout()
        propriedades.addWidget(self._info, 1)
        for widget in (self._spin_largura, self._botao_editar, self._botao_apagar_tecla,
                       self._botao_esq, self._botao_dir):
            propriedades.addWidget(widget)

        # --- 2. lista de teclas -----------------------------------------
        conteudo_lista = QWidget()
        self._grade_paleta = QGridLayout(conteudo_lista)
        self._grade_paleta.setSpacing(4)
        self._comandos = comandos if comandos is not None else {}
        self._guardar_comando = guardar_comando
        self._atalhos = atalhos_de(layouts, excluir=self._modelo["nome"])
        self._construir_paleta()
        area_lista = QScrollArea()
        area_lista.setWidgetResizable(True)
        area_lista.setWidget(conteudo_lista)
        area_lista.setMinimumHeight(200)

        botao_outro = QPushButton(t("editor.outro_simbolo"))
        botao_outro.clicked.connect(self._outro_simbolo)
        botao_avancada = QPushButton(t("editor.tecla_avancada"))
        botao_avancada.clicked.connect(self._tecla_avancada)
        botao_programa = QPushButton(t("editor.tecla_programa"))
        botao_programa.setToolTip(t("editor.tecla_programa_dica"))
        botao_programa.clicked.connect(self._nova_tecla_programa)
        extras = QHBoxLayout()
        extras.addWidget(botao_outro)
        extras.addWidget(botao_avancada)
        extras.addWidget(botao_programa)
        extras.addStretch(1)

        # --- estado e rodape ----------------------------------------------
        self._estado = QLabel()
        self._estado.setWordWrap(True)
        self._estado.setStyleSheet("font-weight: bold;")

        botao_apagar = QPushButton(t("editor.apagar_teclado"))
        botao_apagar.clicked.connect(self._apagar_teclado)
        botao_guardar = QPushButton(t("geral.guardar"))
        botao_guardar.clicked.connect(self._guardar)
        botao_fechar = QPushButton(t("geral.fechar"))
        botao_fechar.clicked.connect(self.reject)
        rodape = QHBoxLayout()
        rodape.addWidget(botao_apagar)
        rodape.addStretch(1)
        rodape.addWidget(botao_guardar)
        rodape.addWidget(botao_fechar)

        raiz = QVBoxLayout(self)
        nome_linha = QHBoxLayout()
        nome_linha.addWidget(QLabel(t("editor.nome")))
        nome_linha.addWidget(self._nome, 1)
        raiz.addLayout(nome_linha)
        raiz.addLayout(linha_atalho)
        raiz.addLayout(modelos)
        raiz.addWidget(QLabel(t("editor.passo_1_a")
                              + t("editor.passo_1_b")))
        raiz.addWidget(area_grelha, 1)
        linha_botoes_grelha = QHBoxLayout()
        linha_botoes_grelha.addWidget(botao_nova_linha)
        linha_botoes_grelha.addStretch(1)
        raiz.addLayout(linha_botoes_grelha)
        raiz.addLayout(propriedades)
        raiz.addWidget(QLabel(t("editor.passo_2")))
        raiz.addWidget(area_lista, 1)
        raiz.addLayout(extras)
        raiz.addWidget(self._estado)
        raiz.addLayout(rodape)

        self._refrescar()

    # --- desenho ---------------------------------------------------------

    def _limpar_grelha(self) -> None:
        while self._grelha.count():
            item = self._grelha.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _construir_linha(self, r: int, linha: list[dict]) -> QWidget:
        fila = QWidget()
        horizontal = QHBoxLayout(fila)
        horizontal.setContentsMargins(0, 0, 0, 0)
        horizontal.setSpacing(4)

        etiqueta = QLabel(f"{r + 1}")
        etiqueta.setFixedWidth(22)
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        horizontal.addWidget(etiqueta)

        for p, tecla in enumerate(linha):
            botao = QPushButton(tecla["rotulo"])
            botao.setCheckable(True)
            botao.setChecked(self._cel == (r, p))
            botao.setMinimumHeight(52)
            botao.setToolTip(f"{rotulo_tipo()[tecla['acao']['tipo']]}: {tecla['acao']['valor']}")
            botao.clicked.connect(lambda _=False, r=r, p=p: self._selecionar(r, p))
            fator = max(1, round(float(tecla.get("largura", 1.0)) * 10))
            horizontal.addWidget(botao, fator)
            self._celulas[(r, p)] = botao

        mais = QPushButton("+")
        mais.setMinimumHeight(52)
        mais.setToolTip(t("editor.acrescentar_dica"))
        mais.clicked.connect(lambda _=False, r=r: self._colocar(r))
        horizontal.addWidget(mais, 10)

        apagar_linha = QPushButton("✕")
        apagar_linha.setFixedWidth(34)
        apagar_linha.setToolTip(t("editor.apagar_linha_dica"))
        apagar_linha.clicked.connect(lambda _=False, r=r: self._apagar_linha(r))
        horizontal.addWidget(apagar_linha)
        return fila

    def _refrescar(self) -> None:
        self._limpar_grelha()
        self._celulas = {}
        if not self._modelo["linhas"]:
            self._grelha.addWidget(QLabel(
                t("editor.vazio")
            ))
        for r, linha in enumerate(self._modelo["linhas"]):
            self._grelha.addWidget(self._construir_linha(r, linha))
        self._grelha.addStretch(1)
        self._atualizar_propriedades()
        self._destacar_lista()

    def _destacar_lista(self) -> None:
        for botao, item in self._paleta:
            botao.setChecked(item is self._escolhida)

    def _tecla_selecionada(self) -> dict | None:
        if self._cel is None:
            return None
        r, p = self._cel
        linhas = self._modelo["linhas"]
        if r < len(linhas) and p < len(linhas[r]):
            return linhas[r][p]
        self._cel = None
        return None

    def _atualizar_propriedades(self) -> None:
        tecla = self._tecla_selecionada()
        ativo = tecla is not None
        for widget in (self._spin_largura, self._botao_editar, self._botao_apagar_tecla,
                       self._botao_esq, self._botao_dir):
            widget.setEnabled(ativo)
        if tecla is None:
            self._info.setText(t("editor.nenhuma"))
            return
        self._info.setText(t("editor.selecionada", rotulo=tecla["rotulo"], tipo=rotulo_tipo()[tecla["acao"]["tipo"]]))
        self._a_atualizar = True
        self._spin_largura.setValue(float(tecla.get("largura", 1.0)))
        self._a_atualizar = False

    def _dizer(self, mensagem: str) -> None:
        self._estado.setText(mensagem)

    # --- grelha ----------------------------------------------------------

    def _selecionar(self, r: int, p: int) -> None:
        self._cel = (r, p)
        self._refrescar()

    def _colocar(self, r: int) -> None:
        if self._escolhida is None:
            self._dizer(t("editor.primeiro_escolha"))
            return
        nova = copy.deepcopy(self._escolhida)
        _, posicao = adicionar_tecla(self._modelo, r, nova)
        self._cel = (r, posicao)
        self._refrescar()
        self._dizer(t("editor.acrescentada", rotulo=nova["rotulo"], linha=r + 1))

    def _nova_linha(self) -> None:
        adicionar_linha(self._modelo)
        self._refrescar()
        self._dizer(t("editor.linha_criada", n=len(self._modelo["linhas"])))

    def _apagar_linha(self, r: int) -> None:
        if self._modelo["linhas"][r]:
            resposta = QMessageBox.question(
                self, t("editor.apagar_linha_titulo"), t("editor.apagar_linha_pergunta", n=r + 1)
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
        remover_linha(self._modelo, r)
        if self._cel is not None:
            cr, cp = self._cel
            if cr == r:
                self._cel = None
            elif cr > r:
                self._cel = (cr - 1, cp)
        self._refrescar()

    def _alterar_largura(self, valor: float) -> None:
        if self._a_atualizar or self._cel is None:
            return
        tecla = self._tecla_selecionada()
        if tecla is None:
            return
        tecla["largura"] = float(valor)
        self._refrescar()

    def _editar_selecionada(self) -> None:
        tecla = self._tecla_selecionada()
        if tecla is None:
            return
        dialogo = DialogoTecla(self, tecla)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        r, p = self._cel
        self._modelo["linhas"][r][p] = dialogo.resultado()
        self._refrescar()

    def _apagar_selecionada(self) -> None:
        if self._cel is None:
            return
        r, p = self._cel
        remover_tecla(self._modelo, r, p)
        self._cel = None
        self._refrescar()

    def _mover_selecionada(self, direcao: int) -> None:
        if self._cel is None:
            return
        r, p = self._cel
        novo = mover_tecla(self._modelo, r, p, direcao)
        self._cel = (r, novo)
        self._refrescar()

    # --- lista de teclas -------------------------------------------------

    def _escolher(self, item: dict) -> None:
        self._escolhida = item
        self._destacar_lista()
        self._dizer(t("editor.escolhida", rotulo=item["rotulo"]))

    def _outro_simbolo(self) -> None:
        texto, ok = QInputDialog.getText(
            self, t("editor.outro_simbolo_titulo"), t("editor.escreva_simbolo")
        )
        if not ok or not texto.strip():
            return
        item = tecla_dict(texto.strip(), "texto", texto.strip())
        try:
            validar_tecla(item)
        except LayoutInvalido as erro:
            QMessageBox.warning(self, t("editor.simbolo_invalido"), str(erro))
            return
        self._escolhida = item
        self._destacar_lista()
        self._dizer(t("editor.escolhida", rotulo=item["rotulo"]))

    def _construir_paleta(self) -> None:
        """(Re)constroi a lista de teclas, incluindo as teclas de programa existentes."""
        while self._grade_paleta.count():
            item = self._grade_paleta.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._paleta = []
        for indice, item in enumerate(simbolos_disponiveis(self._atalhos, list(self._comandos.values()))):
            botao = QPushButton(item["rotulo"])
            botao.setCheckable(True)
            botao.setMinimumSize(46, 40)
            botao.setToolTip(rotulo_tipo()[item["acao"]["tipo"]])
            botao.clicked.connect(lambda _=False, it=item: self._escolher(it))
            self._grade_paleta.addWidget(botao, indice // COLUNAS_LISTA, indice % COLUNAS_LISTA)
            self._paleta.append((botao, item))

    def _nova_tecla_programa(self) -> None:
        """Cria uma tecla que executa um programa/comando no PC e a deixa escolhida para colocar."""
        if self._guardar_comando is None:
            QMessageBox.information(self, t("geral.indisponivel"), t("editor.programa_nao_configurado"))
            return
        dialogo = DialogoComando(self)
        if executar_dialogo(dialogo) != QDialog.DialogCode.Accepted:
            return
        rotulo, comando = dialogo.resultado()
        criada = self._guardar_comando(None, rotulo, comando)
        if criada is None:
            QMessageBox.information(
                self, t("geral.nao_guardado"),
                t("geral.nao_aprovado"),
            )
            return
        self._comandos[criada.id] = criada
        self._construir_paleta()
        self._escolhida = next(
            (item for _, item in self._paleta if item["acao"] == {"tipo": "comando", "valor": criada.id}), None,
        )
        self._destacar_lista()
        self._dizer(t("editor.tecla_criada", rotulo=criada.rotulo))

    def _tecla_avancada(self) -> None:
        dialogo = DialogoTecla(self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        self._escolhida = dialogo.resultado()
        self._destacar_lista()
        self._dizer(t("editor.escolhida", rotulo=self._escolhida["rotulo"]))

    # --- modelos rapidos e rodape -----------------------------------------

    def _aplicar_pronto(self, nome: str) -> None:
        if nome not in self._layouts:
            return
        if any(self._modelo["linhas"]):
            resposta = QMessageBox.question(
                self, t("editor.substituir_titulo"),
                t("editor.substituir_pergunta", nome=nome),
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return
        self._modelo = modelo_de(self._layouts[nome])
        # Uma copia nao herda o atalho do modelo de origem (evita duas teclas iguais).
        self._modelo.pop("atalho", None)
        self._atalho_ativo.setChecked(False)
        self._nome.setText(t("editor.copia", nome=nome))
        self._cel = None
        self._refrescar()
        self._dizer(t("editor.modelo_carregado", nome=nome))

    def _guardar(self) -> None:
        self._modelo["nome"] = self._nome.text().strip()
        if self._atalho_ativo.isChecked():
            rotulo = self._atalho_rotulo.text().strip() or self._modelo["nome"][:20]
            self._modelo["atalho"] = {"rotulo": rotulo}
        else:
            self._modelo.pop("atalho", None)
        try:
            resultado = self._guardar_fn(self._modelo)
        except LayoutInvalido as erro:
            QMessageBox.warning(self, t("geral.teclado_invalido"), str(erro))
            return
        if resultado is None:
            QMessageBox.information(
                self, t("geral.nao_guardado"),
                t("geral.nao_aprovado"),
            )
            return
        self.guardado = resultado
        self.accept()

    def _apagar_teclado(self) -> None:
        nome = self._nome.text().strip()
        resposta = QMessageBox.question(self, t("editor.apagar_teclado_titulo"), t("editor.apagar_teclado_pergunta", nome=nome))
        if resposta != QMessageBox.StandardButton.Yes:
            return
        if self._apagar_fn(nome):
            self.apagado = True
            self.accept()
        else:
            QMessageBox.information(
                self, t("editor.nao_apagado"),
                t("editor.so_apagar_1")
                + t("editor.so_apagar_2"),
            )
