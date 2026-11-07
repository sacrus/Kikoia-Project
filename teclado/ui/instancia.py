"""Apenas uma instancia do teclado a correr.

A primeira instancia abre um servidor local (QLocalServer). Uma segunda instancia liga-se a
esse servidor, pede que o teclado seja mostrado, e termina.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

NOME = "teclado-remoto-instancia"
PEDIDO_MOSTRAR = b"mostrar"
TIMEOUT_MS = 500


# Ligacoes ao servidor de outra instancia. Ficam abertas ate o servidor ler o pedido:
# se fossem fechadas logo, o pedido podia perder-se antes de ser lido.
_ligacoes: list[QLocalSocket] = []


def ja_em_execucao(nome: str = NOME) -> bool:
    """True se outra instancia ja estiver a correr (e recebe o pedido para se mostrar)."""
    socket = QLocalSocket()
    socket.connectToServer(nome)
    if not socket.waitForConnected(TIMEOUT_MS):
        return False
    socket.write(PEDIDO_MOSTRAR)
    socket.flush()
    socket.waitForDisconnected(TIMEOUT_MS)  # o servidor fecha a ligacao depois de ler
    _ligacoes.append(socket)
    return True


class ServidorInstancia(QObject):
    """Recebe os pedidos das outras instancias. Chamar so depois de ja_em_execucao() ser False."""

    pedido_mostrar = Signal()

    def __init__(self, nome: str = NOME, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Restos de uma execucao que terminou sem fechar o servidor (ex.: crash).
        QLocalServer.removeServer(nome)
        self._servidor = QLocalServer(self)
        self._servidor.newConnection.connect(self._nova_ligacao)
        self._servidor.listen(nome)

    @property
    def ativo(self) -> bool:
        return self._servidor.isListening()

    def fechar(self) -> None:
        """Deixa de aceitar pedidos (antes de uma nova instancia arrancar)."""
        self._servidor.close()

    def _nova_ligacao(self) -> None:
        ligacao = self._servidor.nextPendingConnection()
        if ligacao is None:
            return
        # O cliente pode fechar a ligacao logo apos escrever: lemos tambem ao desligar.
        ligacao.readyRead.connect(lambda: self._ler(ligacao))
        ligacao.disconnected.connect(lambda: self._ler(ligacao))

    def _ler(self, ligacao: QLocalSocket) -> None:
        if bytes(ligacao.readAll()) == PEDIDO_MOSTRAR:
            self.pedido_mostrar.emit()
        ligacao.disconnectFromServer()
