"""Arranque: py -m teclado"""

from teclado.core.idiomas import t
import ctypes
import logging
import os
import socket
import subprocess
import threading
import sys
import time
import traceback

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from teclado.core.aplicacao import Aplicacao
from teclado.core.dicionario import Dicionario
from teclado.core.editor import Editor
from teclado.core.paths import DADOS_PROJETO, RAIZ, pasta_dados_utilizador
from teclado.core.reinicio import ARGUMENTO, comando_do_processo
from teclado.core.perfil import RepositorioPerfis, criar_perfil
from teclado.core.captura_teclado import CapturaTeclado
from teclado.core.ia import carregar_config, guardar_config
from teclado.core.layout import NAVEGAR_ANTERIOR, LayoutInvalido
from teclado.core.saida import criar_saida
from teclado.core.voz import (
    Ditado,
    VozIndisponivel,
    criar_sintese,
    escolher_voz_portuguesa,
    vozes_disponiveis,
)
from teclado.ui.definicoes import (
    ACAO_EDITAR,
    ACAO_ATUALIZACOES,
    ACAO_FISICO,
    ACAO_GATEWAY,
    ACAO_IA,
    ACAO_PERSONALIZAR,
    ACAO_SUPERVISAO,
    ACAO_VOZ,
    DialogoDefinicoes,
)
from teclado.ui.ia_teclado import DialogoIATeclado
from teclado.ui.teclado_fisico_opcoes import DialogoTecladoFisico
from teclado.ui.dialogos import ACEITE, escolher_personalizacao, executar_dialogo, pedir_pin
from teclado.ui.editor_layout import DialogoEditorLayout
from teclado.ui.janela import JanelaTeclado
from teclado.ui.supervisao import DialogoSupervisao
from teclado.ui.voz_opcoes import DialogoOpcoesVoz
from teclado.core.comandos import Comando, ComandoErro
from teclado.gateway.acoes import aplicar_acao_remota
from teclado.core import arranque, atualizacao, idiomas
from teclado.ui.atualizacoes import DialogoAtualizacoes
from teclado.ui.instancia import ServidorInstancia, ja_em_execucao
from teclado.gateway.confianca import RepositorioConfianca, dispositivos_emparelhados, pode_ser_emparelhado
from teclado.gateway.controlador import ControladorGateway
from teclado.core.layout_editor import modelo_de, rotular_comandos
from teclado.ui.gateway_opcoes import DialogoGateway


def _registar_erros(pasta):
    """Exceções não tratadas (inclusive em callbacks Qt) ficam num ficheiro de log."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / "erros.log"
    logging.basicConfig(filename=caminho, level=logging.ERROR,
                        format="%(asctime)s %(message)s", encoding="utf-8")

    def gancho(tipo, valor, tb):
        logging.error("".join(traceback.format_exception(tipo, valor, tb)))
        sys.__excepthook__(tipo, valor, tb)

    sys.excepthook = gancho
    return caminho


# Nome do produto nas notificacoes, na janela e no sistema (nao depende do idioma).
NOME_APP = "Kikoia"


def _processo_destacado() -> dict:
    """Opcoes do Popen para o processo novo continuar depois de esta instancia terminar."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _escolher_plataforma_grafica() -> None:
    """No Linux, usa XWayland (xcb) por omissao: o Wayland nao deixa a janela do teclado ficar por cima
    nem sem roubar o foco, e o xcb respeita isso. Se faltarem bibliotecas xcb, fica o Wayland."""
    if not sys.platform.startswith("linux") or "QT_QPA_PLATFORM" in os.environ or not os.environ.get("DISPLAY"):
        return
    for biblioteca in ("libxcb-cursor.so.0", "libxcb-icccm.so.4", "libxcb-keysyms.so.1"):
        try:
            ctypes.CDLL(biblioteca)
        except OSError:
            return
    os.environ["QT_QPA_PLATFORM"] = "xcb"


def main() -> int:
    _escolher_plataforma_grafica()
    qt = QApplication(sys.argv)
    qt.setApplicationName(NOME_APP)
    if sys.platform == "win32":
        # Sem isto, as notificacoes do Windows mostram o nome do interprete ("Python").
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(NOME_APP)
    # Reinicio pedido pela instancia anterior (ex.: mudanca de idioma): espera que ela liberte o servidor.
    if ARGUMENTO in sys.argv:
        for _ in range(60):
            if not ja_em_execucao():
                break
            time.sleep(0.25)
        time.sleep(1.0)
    # Uma so instancia: a segunda pede a primeira para se mostrar e termina.
    if ja_em_execucao():
        return 0
    instancia = ServidorInstancia()
    # Se o arranque com o sistema estiver ativo, a entrada aponta sempre para este executavel.
    if arranque.ativado():
        try:
            arranque.definir(True)
        except OSError as erro:
            logging.error("Arranque com o sistema nao atualizado: %s", erro)

    pasta = pasta_dados_utilizador()
    _registar_erros(pasta)
    repo = RepositorioPerfis(pasta / "perfis")
    perfis = repo.listar()
    if perfis:
        perfil = perfis[0]
    else:
        perfil = criar_perfil("Predefinido", supervisionado=False)
        repo.guardar(perfil)

    janela = None  # atribuida abaixo; os callbacks so correm depois de a janela existir

    def com_dialogo(funcao):
        return janela.sem_sobreposicao(funcao)

    controlador = Aplicacao(
        saida=criar_saida(),
        repo=repo,
        perfil=perfil,
        pedir_pin=lambda: com_dialogo(lambda: pedir_pin(None)),
        pastas_layouts=[DADOS_PROJETO / "layouts", pasta / "layouts"],
        pastas_temas=[DADOS_PROJETO / "temas", pasta / "temas"],
        pasta_temas_utilizador=pasta / "temas",
        pasta_layouts_utilizador=pasta / "layouts",
        pasta_comandos=pasta,
    )
    idiomas.definir(controlador.idioma)

    # Dicionario do idioma escolhido (sem lexico instalado, usa o portugues). Cada idioma aprende
    # as suas palavras em separado; o portugues mantem o ficheiro que ja existia.
    lingua = idiomas.atual()
    lexico = DADOS_PROJETO / "languages" / lingua / "lexico.tsv"
    if not lexico.is_file():
        lingua = idiomas.IDIOMA_PADRAO
        lexico = DADOS_PROJETO / "languages" / lingua / "lexico.tsv"
    sufixo = "" if lingua == idiomas.IDIOMA_PADRAO else f"-{lingua}"
    dicionario = Dicionario.carregar(
        lexico,
        pessoal=pasta / "dicionario" / f"{perfil.id}{sufixo}.sqlite",
    )
    editor = Editor(
        controlador.saida,
        dicionario,
        max_sugestoes=int(perfil.preferencias.get("max_sugestoes", 5)),
    )

    # --- voz -----------------------------------------------------------------
    # Sintese e reconhecimento sao opcionais: sem eles, os botoes ficam desativados
    # com o motivo, e o teclado funciona igual.

    sintese = None
    motivo_falar = None
    try:
        # Sem voz escolhida, usa a portuguesa instalada (senao a do sistema, que pode ser inglesa).
        voz_inicial = controlador.preferencias_voz()["voz_id"] or escolher_voz_portuguesa(vozes_disponiveis())
        sintese = criar_sintese(voz_inicial)
    except VozIndisponivel as erro:
        motivo_falar = str(erro)

    class PonteVoz(QObject):
        texto_ditado = Signal(str)
        nivel = Signal(object)  # Medicao do microfone (thread de audio -> Qt)

    ponte = PonteVoz()
    ponte.nivel.connect(lambda medicao: janela.atualizar_nivel(medicao))
    ponte.texto_ditado.connect(lambda texto: editor.ditar(texto + " "))  # regressa a thread do Qt

    ditado = None
    motivo_ditar = None

    def criar_ditado() -> None:
        # O modelo de ditar e descarregado a pedido: recria-se o ditado quando o modelo muda.
        nonlocal ditado, motivo_ditar
        if ditado is not None:
            ditado.desligar()
        ditado = None
        motivo_ditar = None
        try:
            ditado = Ditado(pasta, ao_texto=ponte.texto_ditado.emit, ao_nivel=ponte.nivel.emit,
                            idioma=idiomas.atual())
        except VozIndisponivel as erro:
            motivo_ditar = str(erro)

    criar_ditado()

    def falar_se_ligado(texto: str) -> None:
        if sintese is not None and controlador.preferencias_voz()["falar"]:
            sintese.falar(texto)

    def estado_interruptores() -> dict:
        # Falar e Ditar tambem se mostram no telemovel (ver interruptores no protocolo).
        prefs = controlador.preferencias_voz()
        return {
            "falar": bool(prefs["falar"]) and motivo_falar is None,
            "falar_disponivel": motivo_falar is None,
            "ditar": bool(ditado and ditado.ativo),
            "ditar_disponivel": motivo_ditar is None,
        }

    def sincronizar_voz() -> None:
        prefs = controlador.preferencias_voz()
        editor.falar_palavra = prefs["ler_palavra"]
        editor.falar_frase = prefs["ler_frase"]
        editor.falar_sugestao = prefs["ler_sugestao"]
        janela.configurar_voz(
            falar_ligado=prefs["falar"],
            falar_motivo=motivo_falar,
            ditar_ligado=bool(ditado and ditado.ativo),
            ditar_motivo=motivo_ditar,
            ao_falar=alternar_falar,
            ao_ditar=alternar_ditar,
        )
        gateway.atualizar_interruptores(estado_interruptores())

    def alternar_interruptor(nome: str, ligado: bool) -> None:
        # Pedido do telemovel: so muda se o recurso estiver disponivel no PC.
        if nome == "falar" and motivo_falar is None:
            alternar_falar(ligado)
        elif nome == "ditar" and motivo_ditar is None and ditado is not None:
            alternar_ditar(ligado)

    def alternar_falar(ligado: bool) -> None:
        controlador.alternar_falar(ligado)
        sincronizar_voz()

    def alternar_ditar(ligado: bool) -> None:
        if ditado is None:
            return
        ditado.ligar() if ligado else ditado.desligar()
        sincronizar_voz()

    editor.ligar_voz(falar_se_ligado)

    def ler_selecao(texto: str) -> None:
        # Pedido explicito do utilizador: le sempre, mesmo com o botao Falar desligado.
        if sintese is not None:
            sintese.falar(texto)

    editor.ligar_leitura_selecao(ler_selecao)

    def com_nomes_atuais(layout):
        # Nome de cada tecla de comando vem do comando (ver rotular_comandos).
        return rotular_comandos(layout, controlador.comandos)

    def sincronizar_telemovel() -> None:
        # O telemovel mostra sempre o teclado ativo no PC.
        gateway.atualizar_teclado(modelo_de(com_nomes_atuais(controlador.layout)))

    def navegar(nome: str) -> None:
        novo = controlador.voltar_teclado() if nome == NAVEGAR_ANTERIOR else controlador.navegar_para(nome)
        if novo is not None:
            janela.montar(com_nomes_atuais(novo))
            sincronizar_telemovel()

    # --- acoes das definicoes (correm com o teclado recolhido) -----------

    def opcoes_voz() -> None:
        nonlocal sintese, motivo_falar
        dialogo = DialogoOpcoesVoz(
            None, controlador.preferencias_voz(), vozes_disponiveis(),
            pasta_dados=pasta, idioma=idiomas.atual(),
        )
        resultado = executar_dialogo(dialogo)
        # O modelo de ditar pode ter sido descarregado ou removido dentro do dialogo.
        criar_ditado()
        if resultado != ACEITE:
            sincronizar_voz()
            return
        escolhas = dialogo.escolhas()
        if not controlador.definir_opcoes_voz(**escolhas):
            return
        # Trocar de voz exige um motor novo; o anterior e fechado.
        if sintese is not None:
            sintese.fechar()
        sintese, motivo_falar = None, None
        try:
            sintese = criar_sintese(escolhas["voz_id"] or escolher_voz_portuguesa(vozes_disponiveis()))
        except VozIndisponivel as erro:
            motivo_falar = str(erro)
        sincronizar_voz()

    # --- acoes das definicoes (correm com o teclado recolhido) -----------

    def editar_teclados() -> None:
        dialogo = DialogoEditorLayout(
            None,
            controlador.layouts,
            controlador.layout,
            guardar=controlador.guardar_layout,
            apagar=controlador.apagar_layout,
            comandos=controlador.comandos,
            guardar_comando=controlador.guardar_comando,
            apagar_comando=controlador.apagar_comando,
            teclados_com_comando=controlador.teclados_com_comando,
        )
        executar_dialogo(dialogo)
        janela.montar(com_nomes_atuais(controlador.layout))
        sincronizar_telemovel()

    def personalizar_tema() -> None:
        escolhas = escolher_personalizacao(None, controlador.tema)
        if escolhas is None:
            return
        novo = controlador.personalizar(**escolhas)
        if novo is not None:
            janela.aplicar_tema(novo)

    def gerir_supervisao() -> None:
        ativa, ambito = controlador.estado_supervisao()
        dialogo = DialogoSupervisao(None, ativa, ambito)
        if executar_dialogo(dialogo) != ACEITE:
            return
        r = dialogo.resultado()
        try:
            if r["acao"] == "ativar":
                controlador.ativar_supervisao(r["pin"], r["ambito"])
            elif r["acao"] == "atualizar":
                controlador.atualizar_supervisao(r["ambito"], r["pin"])
            elif r["acao"] == "desativar":
                controlador.desativar_supervisao()
        except ValueError as erro:
            QMessageBox.warning(None, t("geral.supervisao"), str(erro))

    def aplicar_definicoes(escolhas: dict) -> None:
        if escolhas["layout"] != controlador.layout.nome:
            novo = controlador.mudar_layout(escolhas["layout"])
            if novo is not None:
                janela.montar(com_nomes_atuais(novo))
                sincronizar_telemovel()
        if escolhas["tema"] != controlador.tema.nome:
            novo = controlador.mudar_tema(escolhas["tema"])
            if novo is not None:
                janela.aplicar_tema(novo)
        if escolhas["max_sugestoes"] != editor.max_sugestoes:
            if controlador.definir_max_sugestoes(escolhas["max_sugestoes"]):
                editor.definir_max_sugestoes(escolhas["max_sugestoes"])
        if escolhas["verificar_atualizacoes"] != controlador.verificar_atualizacoes:
            controlador.definir_verificar_atualizacoes(escolhas["verificar_atualizacoes"])
        if escolhas["idioma"] != controlador.idioma:
            if controlador.definir_idioma(escolhas["idioma"]):
                pergunta = QMessageBox.question(
                    None, idiomas.t("geral.idioma"), idiomas.t("definicoes.idioma_reiniciar"),
                )
                if pergunta == QMessageBox.StandardButton.Yes:
                    reiniciar_aplicacao()
        if escolhas["auto_iniciar"] != controlador._auto_iniciar:
            controlador.definir_auto_iniciar(escolhas["auto_iniciar"])
        if escolhas["arranque_sistema"] != arranque.ativado():
            try:
                controlador.definir_arranque_sistema(escolhas["arranque_sistema"])
            except OSError as erro:
                logging.error("Arranque com o sistema nao alterado: %s", erro)
                QMessageBox.warning(None, idiomas.t("geral.arranque"), idiomas.t("geral.arranque_falhou", erro=erro))
        if escolhas["acao"] == ACAO_EDITAR:
            editar_teclados()
        elif escolhas["acao"] == ACAO_PERSONALIZAR:
            personalizar_tema()
        elif escolhas["acao"] == ACAO_SUPERVISAO:
            gerir_supervisao()
        elif escolhas["acao"] == ACAO_VOZ:
            opcoes_voz()
        elif escolhas["acao"] == ACAO_IA:
            criar_com_ia()
        elif escolhas["acao"] == ACAO_FISICO:
            opcoes_fisico()
        elif escolhas["acao"] == ACAO_GATEWAY:
            abrir_gateway()
        elif escolhas["acao"] == ACAO_ATUALIZACOES:
            executar_dialogo(DialogoAtualizacoes(None))

    def opcoes_fisico() -> None:
        prefs = controlador.preferencias_fisico()
        dialogo = DialogoTecladoFisico(None, prefs["ativo"], prefs["aprender"], motivo_fisico)
        if executar_dialogo(dialogo) != ACEITE:
            return
        escolhas_f = dialogo.escolhas()
        if controlador.definir_teclado_fisico(escolhas_f["ativo"], escolhas_f["aprender"]):
            sincronizar_fisico()

    def criar_com_ia() -> None:
        """Pede um teclado a IA, pre-visualiza e so guarda se o utilizador confirmar.

        A gravacao usa controlador.guardar_layout: passa pela mesma politica de supervisao.
        """
        dialogo = DialogoIATeclado(None, carregar_config(pasta))
        if executar_dialogo(dialogo) != ACEITE:
            return
        nova = dialogo.config_alterada()
        if nova.configurada:
            guardar_config(pasta, nova)
        modelo = dialogo.resultado()
        if modelo is None:
            return
        # Os programas propostos so ficam guardados se o utilizador confirmou (Usar este teclado).
        comandos_ia = [Comando(c["id"], c["rotulo"], c["comando"]) for c in dialogo.comandos()]
        if comandos_ia and not controlador.guardar_comandos_em_lote(comandos_ia):
            QMessageBox.information(
                None, idiomas.t("geral.nao_guardado"),
                idiomas.t("geral.nao_aprovado"),
            )
            return
        try:
            guardado = controlador.guardar_layout(modelo)
        except LayoutInvalido as erro:
            QMessageBox.warning(None, "Teclado inválido", str(erro))
            return
        if guardado is None:
            QMessageBox.information(
                None, idiomas.t("geral.nao_guardado"),
                idiomas.t("geral.nao_aprovado"),
            )
            return
        janela.montar(com_nomes_atuais(guardado))
        sincronizar_telemovel()

    def abrir_definicoes() -> None:
        def fluxo() -> None:
            dialogo = DialogoDefinicoes(
                None,
                list(controlador.layouts),
                controlador.layout.nome,
                list(controlador.temas),
                controlador.tema.nome,
                editor.max_sugestoes,
                auto_iniciar=controlador._auto_iniciar,
                idioma_atual=controlador.idioma,
                arranque_sistema=arranque.ativado(),
                verificar_atualizacoes=controlador.verificar_atualizacoes,
            )
            if executar_dialogo(dialogo) != ACEITE:
                return
            aplicar_definicoes(dialogo.escolhas())

        # Tudo corre dentro de sem_sobreposicao: o teclado fica recolhido ate o fim.
        janela.sem_sobreposicao(fluxo)

    def sair() -> None:
        # Fechar o teclado (X) termina a aplicacao por completo: nada fica em segundo plano.
        qt.quit()

    def reiniciar_aplicacao() -> None:
        # A nova instancia so arranca depois de esta libertar o servidor (ver ARGUMENTO).
        instancia.fechar()
        subprocess.Popen(comando_do_processo(), cwd=str(RAIZ), **_processo_destacado())
        qt.quit()

    janela = JanelaTeclado(
        editor,
        controlador.layout,
        controlador.tema,
        ao_definicoes=abrir_definicoes,
        ao_navegar=navegar,
        ao_comando=lambda id_: executar_por_id(id_),  # resolvido ao premir, nao na criacao
        ao_fechar=sair,
    )
    # Ao mostrar, a janela ancora-se no fundo do ecra e reserva essa area (ver ui/appbar.py).

    def mostrar_teclado() -> None:
        janela.show()
        janela.raise_()

    # Icone na area de notificacao: e a forma de voltar a mostrar o teclado depois de minimizado.
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(qt.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), qt)
        menu = QMenu()
        menu.addAction(idiomas.t("tray.mostrar"), mostrar_teclado)
        menu.addAction(idiomas.t("tray.sair"), qt.quit)
        tray.setContextMenu(menu)
        tray.setToolTip(idiomas.t("app.nome"))
        tray.activated.connect(
            lambda motivo: mostrar_teclado()
            if motivo == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        tray.show()
        # Com o teclado escondido (ligado ao telemovel), so o icone fica visivel: nao e para terminar.
        qt.setQuitOnLastWindowClosed(False)

    instancia.pedido_mostrar.connect(mostrar_teclado)

    def acao_sistema(nome: str) -> None:
        if nome == "minimizar_teclado":
            # Sem icone na bandeja nao ha forma de o voltar a mostrar: nao se minimiza.
            if tray is not None:
                janela.hide()
            return
        fazer = getattr(controlador.saida, "janela_ativa", None)
        if fazer is not None:
            fazer(nome, excluir=int(janela.winId()))

    editor.ligar_acoes_janela(acao_sistema)

    # --- gateway (telemovel) ------------------------------------------------------
    # Os eventos chegam da thread de rede por sinais Qt (entrega na thread principal).
    class PonteGateway(QObject):
        acao = Signal(object)
        ligado = Signal(str)
        emparelhado = Signal(str)
        desligado = Signal(str)

    ponte_gw = PonteGateway()

    def notificar(texto: str) -> None:
        if tray is not None:
            tray.showMessage(NOME_APP, texto)

    def executar_por_id(id_: str) -> None:
        # So executa teclas guardadas no PC: o telemovel nunca envia texto de comando.
        try:
            controlador.executar_comando(id_)
        except ComandoErro as erro:
            logging.error("Tecla personalizada falhou: %s", erro)
            notificar(str(erro))

    def tratar_remoto(msg: dict) -> None:
        # Chega ja na thread do Qt (sinal). Navegacao e sugestoes mudam o estado do PC.
        if msg["tipo"] == "interruptor":
            alternar_interruptor(msg["nome"], msg["ligado"])
            return
        if msg["tipo"] == "escolher_sugestao":
            editor.usar_sugestao(msg["indice"])
            return
        acao = msg["acao"]
        if acao["tipo"] == "comando":
            executar_por_id(acao["valor"])
            return
        if acao["tipo"] == "navegar":
            navegar(acao["valor"])
            return
        aplicar_acao_remota(editor, acao)

    ponte_gw.acao.connect(tratar_remoto)
    ponte_gw.ligado.connect(lambda endereco: notificar(idiomas.t("telemovel.ligado", endereco=endereco)))
    ponte_gw.desligado.connect(lambda endereco: notificar(idiomas.t("telemovel.desligado")))

    confianca = RepositorioConfianca(pasta)
    gateway = ControladorGateway(
        nome=socket.gethostname(),
        ao_acao=ponte_gw.acao.emit,
        ao_ligar=ponte_gw.ligado.emit,
        ao_desligar=ponte_gw.desligado.emit,
        fornecer_teclado=lambda: modelo_de(com_nomes_atuais(controlador.layout)),
        fornecer_sugestoes=lambda: list(editor.sugestoes),
        fornecer_interruptores=lambda: estado_interruptores(),
        confianca=confianca,
        ao_emparelhar_novo=ponte_gw.emparelhado.emit,
    )

    # --- ligacao automatica ao telemovel de confianca ---
    # Um telemovel ja emparelhado liga-se sem codigo (ver teclado/gateway/confianca.py).
    # Com "Iniciar com PC" ativo, o PC so escuta durante 5 minutos ao arrancar: por Bluetooth
    # se o telemovel guardado estiver emparelhado no Windows, senao por Wi-Fi.
    # Sem telemovel de confianca guardado, nao faz nada.
    tempo_escuta = QTimer()
    tempo_escuta.setSingleShot(True)
    TEMPO_ESCUTA_MS = 5 * 60 * 1000

    def terminar_escuta() -> None:
        if gateway.ativo and gateway.estado()["ligados"] == 0:
            gateway.desligar()
            notificar(idiomas.t("telemovel.tempo_esgotado"))

    tempo_escuta.timeout.connect(terminar_escuta)

    def arrancar_escuta() -> None:
        # Bluetooth se o telemovel de confianca estiver emparelhado no sistema; senao, Wi-Fi.
        if not controlador._auto_iniciar or gateway.ativo:
            return
        guardados = confianca.nomes()
        if not guardados:
            return
        porta = controlador.preferencias_gateway()["porta"]
        if pode_ser_emparelhado(guardados, dispositivos_emparelhados()):
            try:
                gateway.ligar(porta=porta, transporte="bluetooth")
            except RuntimeError as erro:
                logging.error("Escuta Bluetooth automatica nao iniciou: %s", erro)
            else:
                tempo_escuta.start(TEMPO_ESCUTA_MS)
                notificar(idiomas.t("telemovel.escuta_bluetooth"))
                return
        try:
            gateway.ligar(porta=porta, transporte="wifi")
        except RuntimeError as erro:
            logging.error("Escuta Wi-Fi automatica nao iniciou: %s", erro)
            return
        tempo_escuta.start(TEMPO_ESCUTA_MS)
        notificar(idiomas.t("telemovel.escuta_wifi"))

    # Ligado ao telemovel, a janela de emparelhamento fecha e o teclado sai do ecra
    # (fica no icone da bandeja). Os sinais chegam da thread de rede: entrega na thread principal.
    dialogos_gateway = []

    def esconder_teclado() -> None:
        if tray is None:
            return  # sem icone na bandeja nao ha forma de o voltar a mostrar
        for dialogo in dialogos_gateway:
            dialogo.accept()
        janela.recolher_definitivamente()

    def ao_telemovel_ligado(endereco: str) -> None:
        esconder_teclado()

    def ao_telemovel_emparelhado(endereco: str) -> None:
        notificar(idiomas.t("telemovel.emparelhado", endereco=endereco))
        esconder_teclado()

    def ao_telemovel_desligado(endereco: str) -> None:
        # Sem telemovel ligado, o teclado volta ao ecra do PC.
        if gateway.estado().get("ligados", 0) == 0:
            mostrar_teclado()

    ponte_gw.ligado.connect(ao_telemovel_ligado, Qt.ConnectionType.QueuedConnection)
    ponte_gw.emparelhado.connect(ao_telemovel_emparelhado, Qt.ConnectionType.QueuedConnection)
    ponte_gw.desligado.connect(ao_telemovel_desligado, Qt.ConnectionType.QueuedConnection)

    # As sugestoes mudam a cada tecla: o telemovel recebe sempre a lista atual.
    atualizar_ecra_sugestoes = editor.ao_atualizar

    def ao_mudar_sugestoes() -> None:
        atualizar_ecra_sugestoes()
        gateway.atualizar_sugestoes(list(editor.sugestoes))

    editor.ao_atualizar = ao_mudar_sugestoes

    def abrir_gateway() -> None:
        dialogo = DialogoGateway(
            None,
            gateway,
            controlador.pedir_aprovacao_definicoes,
            controlador.preferencias_gateway()["porta"],
            lambda porta: controlador.definir_porta_gateway(porta),
        )
        dialogos_gateway.append(dialogo)
        try:
            executar_dialogo(dialogo)
        finally:
            dialogos_gateway.remove(dialogo)

    QTimer.singleShot(2000, arrancar_escuta)

    # Atualizacoes: verificadas em segundo plano; so avisam na bandeja. Instalar e sempre uma escolha do utilizador.
    class PonteAtualizacao(QObject):
        disponivel = Signal(bool)

    ponte_atualizacao = PonteAtualizacao()

    def aviso_atualizacao(ha: bool) -> None:
        if ha and tray is not None:
            tray.showMessage(NOME_APP, idiomas.t("atualizacoes.aviso_bandeja"))

    ponte_atualizacao.disponivel.connect(aviso_atualizacao, Qt.ConnectionType.QueuedConnection)

    def verificar_atualizacoes_em_fundo() -> None:
        def trabalhar() -> None:
            try:
                nova = atualizacao.verificar_teclado()
                dependencias = atualizacao.verificar_dependencias()
            except (OSError, ValueError):
                return  # sem rede ou resposta invalida: tenta de novo no proximo arranque
            ponte_atualizacao.disponivel.emit(nova is not None or any(d.desatualizada for d in dependencias))

        threading.Thread(target=trabalhar, daemon=True, name="atualizacoes").start()

    if controlador.verificar_atualizacoes:
        QTimer.singleShot(20000, verificar_atualizacoes_em_fundo)

    sincronizar_voz()

    # --- teclado fisico (fase 7) ------------------------------------------------
    # Desligado por omissao. Os eventos chegam da thread do gancho por sinal Qt,
    # para serem tratados na thread principal.
    class PonteFisico(QObject):
        evento = Signal(object)

        def __init__(self, tratar) -> None:
            super().__init__()
            self._tratar = tratar
            self.evento.connect(self._recebe, Qt.ConnectionType.QueuedConnection)

        def _recebe(self, ev) -> None:
            self._tratar(ev)

    def tratar_fisico(ev) -> None:
        editor.evento_fisico(ev[0], ev[1] if len(ev) > 1 else None)

    ponte_fisico = PonteFisico(tratar_fisico)
    captura = None
    motivo_fisico = None
    try:
        captura = CapturaTeclado(ponte_fisico.evento.emit)
    except RuntimeError as erro:
        motivo_fisico = str(erro)

    def sincronizar_fisico() -> None:
        prefs = controlador.preferencias_fisico()
        editor.aprender_fisico = prefs["aprender"]
        ativo = False
        if captura is not None:
            if prefs["ativo"] and not captura.ativo:
                try:
                    captura.ligar()
                except RuntimeError as erro:
                    logging.error("Teclado fisico nao ligou: %s", erro)
            elif not prefs["ativo"] and captura.ativo:
                captura.desligar()
            ativo = captura.ativo
        janela.mostrar_indicador_fisico(ativo)

    sincronizar_fisico()
    janela.show()
    try:
        return qt.exec()
    finally:
        if tray is not None:
            tray.hide()  # o icone some logo, sem esperar que o Windows o limpe
        if ditado is not None:
            ditado.desligar()
        if sintese is not None:
            sintese.fechar()
        gateway.desligar()
        if captura is not None:
            captura.desligar()
        dicionario.fechar()


if __name__ == "__main__":
    sys.exit(main())
