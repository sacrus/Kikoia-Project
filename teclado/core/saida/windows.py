"""Injecao de teclas no Windows com SendInput.

Texto e enviado com KEYEVENTF_UNICODE, por isso nao depende do layout ativo
do sistema (acentos e simbolos funcionam sempre).
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

from . import ACOES_EDICAO, ACOES_JANELA, TECLAS_ESPECIAIS

# Pausa entre um backspace e o texto seguinte. Sem ela, o Bloco de Notas do
# Windows 11 (e outras aplicações) troca ou perde letras: testado com 0 falhas
# em 12 tentativas com a pausa e 5 a 6 falhas por cada 12 sem ela.
PAUSA_APOS_APAGAR = 0.03

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

_VK = {
    "backspace": 0x08, "tab": 0x09, "enter": 0x0D, "esc": 0x1B, "espaco": 0x20,
    "delete": 0x2E, "seta_esq": 0x25, "seta_cima": 0x26, "seta_dir": 0x27, "seta_baixo": 0x28,
    "home": 0x24, "end": 0x23, "pgup": 0x21, "pgdn": 0x22, "prtsc": 0x2C,
    "insert": 0x2D, "capslock": 0x14,
}
_TECLAS_ESTENDIDAS = frozenset({
    "delete", "seta_esq", "seta_cima", "seta_dir", "seta_baixo",
    "home", "end", "pgup", "pgdn", "insert",
})

# Janelas do sistema que nunca sao alvo de "minimizar/fechar janela ativa".
_CLASSES_PROTEGIDAS = frozenset({"Shell_TrayWnd", "Progman", "WorkerW"})
WM_CLOSE = 0x0010
SW_MINIMIZE = 6
SW_MAXIMIZE = 3

# Teclas usadas nos atalhos de edicao (nomes de MAPA_TECLAS_ATALHO).
_VK_ATALHO = {
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "home": 0x24, "end": 0x23,
    "left": 0x25, "right": 0x27, "c": 0x43,
}
_EXTENDIDAS_ATALHO = frozenset({"home", "end", "left", "right"})

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _UnionEntrada(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _UnionEntrada)]


def _evento_unicode(unidade: int, baixo: bool) -> INPUT:
    evento = INPUT()
    evento.type = INPUT_KEYBOARD
    evento.u.ki.wVk = 0
    evento.u.ki.wScan = unidade
    evento.u.ki.dwFlags = KEYEVENTF_UNICODE | (0 if baixo else KEYEVENTF_KEYUP)
    return evento


def _evento_virtual(vk: int, flags: int) -> INPUT:
    evento = INPUT()
    evento.type = INPUT_KEYBOARD
    evento.u.ki.wVk = vk
    evento.u.ki.wScan = 0
    evento.u.ki.dwFlags = flags
    return evento


def eventos_para_texto(texto: str) -> list[INPUT]:
    """Converte texto em eventos Unicode (pares para caracteres fora do BMP, ex.: emojis)."""
    eventos: list[INPUT] = []
    for caractere in texto:
        codigos = caractere.encode("utf-16-le")
        for i in range(0, len(codigos), 2):
            unidade = codigos[i] | (codigos[i + 1] << 8)
            eventos.append(_evento_unicode(unidade, baixo=True))
            eventos.append(_evento_unicode(unidade, baixo=False))
    return eventos


def eventos_para_tecla(nome: str) -> list[INPUT]:
    if nome not in TECLAS_ESPECIAIS:
        raise ValueError(f"Tecla desconhecida: {nome}")
    flags = KEYEVENTF_EXTENDEDKEY if nome in _TECLAS_ESTENDIDAS else 0
    vk = _VK[nome]
    return [_evento_virtual(vk, flags), _evento_virtual(vk, flags | KEYEVENTF_KEYUP)]


def _vk_e_flags(nome: str) -> tuple[int, int]:
    """Codigo virtual e flags de uma tecla usada num atalho (letra, digito, especial ou modificador)."""
    if nome in _VK_ATALHO:
        vk = _VK_ATALHO[nome]
        return vk, KEYEVENTF_EXTENDEDKEY if nome in _EXTENDIDAS_ATALHO else 0
    if nome in _VK:
        return _VK[nome], KEYEVENTF_EXTENDEDKEY if nome in _TECLAS_ESTENDIDAS else 0
    if len(nome) == 1 and nome.isascii() and nome.isalnum():
        # Letras e digitos: o codigo virtual e o proprio caracter em maiusculas.
        return ord(nome.upper()), 0
    raise ValueError(f"Tecla desconhecida no atalho: {nome}")


def eventos_para_passo(passo: str) -> list[INPUT]:
    """Um passo de atalho, ex.: "ctrl+shift+left" -> prime ctrl, shift, left; liberta ao contrario."""
    partes = passo.split("+")
    modificadores, tecla = partes[:-1], partes[-1]
    eventos: list[INPUT] = []
    for mod in modificadores:
        vk, flags = _vk_e_flags(mod)
        eventos.append(_evento_virtual(vk, flags))
    vk, flags = _vk_e_flags(tecla)
    eventos.append(_evento_virtual(vk, flags))
    eventos.append(_evento_virtual(vk, flags | KEYEVENTF_KEYUP))
    for mod in reversed(modificadores):
        vk, flags = _vk_e_flags(mod)
        eventos.append(_evento_virtual(vk, flags | KEYEVENTF_KEYUP))
    return eventos


# --- area de transferencia (para ler a seleccao) ------------------------------

def _clipboard_api():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = (wintypes.UINT, ctypes.c_void_p)
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = (ctypes.c_void_p,)
    kernel32.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    return user32, kernel32


def _abrir_clipboard(user32) -> bool:
    # A area de transferencia pode estar bloqueada por outra aplicacao: tenta algumas vezes.
    for _ in range(10):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.02)
    return False


def ler_clipboard_texto() -> str | None:
    """Texto da area de transferencia; None se nao houver texto (ou estiver ocupada)."""
    user32, kernel32 = _clipboard_api()
    if not _abrir_clipboard(user32):
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        bloco = kernel32.GlobalLock(handle)
        try:
            return ctypes.wstring_at(bloco)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def escrever_clipboard_texto(texto: str) -> None:
    user32, kernel32 = _clipboard_api()
    dados = (texto + "\0").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(dados))
    bloco = kernel32.GlobalLock(handle)
    ctypes.memmove(bloco, dados, len(dados))
    kernel32.GlobalUnlock(handle)
    if not _abrir_clipboard(user32):
        return
    try:
        user32.EmptyClipboard()
        user32.SetClipboardData(CF_UNICODETEXT, handle)  # a partir daqui o sistema e dono do bloco
    finally:
        user32.CloseClipboard()


def esvaziar_clipboard() -> None:
    user32, _ = _clipboard_api()
    if _abrir_clipboard(user32):
        try:
            user32.EmptyClipboard()
        finally:
            user32.CloseClipboard()


class SaidaWindows:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("SaidaWindows so funciona no Windows.")
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._send_input = self._user32.SendInput
        self._send_input.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
        self._send_input.restype = wintypes.UINT
        self._ultimo_apagar = 0.0
        # Serializa os envios: ditado e teclas virtuais nao se intercalam.
        import threading
        self._lock = threading.RLock()

    def _enviar(self, eventos: list[INPUT]) -> None:
        if not eventos:
            return
        matriz = (INPUT * len(eventos))(*eventos)
        enviados = self._send_input(len(eventos), matriz, ctypes.sizeof(INPUT))
        if enviados != len(eventos):
            raise ctypes.WinError(ctypes.get_last_error())

    def _esperar_apos_apagar(self) -> None:
        decorrido = time.monotonic() - self._ultimo_apagar
        if decorrido < PAUSA_APOS_APAGAR:
            time.sleep(PAUSA_APOS_APAGAR - decorrido)

    def _enviar_texto(self, texto: str) -> None:
        """Envia texto carácter a carácter, com uma pausa curta entre cada um.

        Um bloco grande de eventos Unicode num so SendInput faz aplicacoes como o
        Bloco de Notas substituir o fim do texto por espacos (medido: 18 de 18
        frases ditadas afetadas). Com pausa entre caracteres, o texto chega inteiro.
        """
        if not texto:
            return
        self._esperar_apos_apagar()
        self._enviar(eventos_para_texto(texto))

    def colar_texto(self, texto: str) -> None:
        """Escreve um bloco de texto (ditado) colando-o pela area de transferencia.

        Enviar carácter a carácter ou em lote falhava em aplicacoes como o Bloco de Notas
        (texto substituido por espacos ou teclas repetidas). Colar entra de uma vez.
        O conteudo anterior da area de transferencia e reposto.
        """
        if not texto:
            return
        with self._lock:
            self._esperar_apos_apagar()
            anterior = ler_clipboard_texto()
            escrever_clipboard_texto(texto)
            time.sleep(0.03)  # o clipboard tem de estar pronto antes do Ctrl+V
            self._enviar(eventos_para_passo("ctrl+v"))
            time.sleep(0.15)  # a aplicacao le o clipboard antes de o repor
            if anterior is None:
                esvaziar_clipboard()
            else:
                escrever_clipboard_texto(anterior)

    def _enviar_tecla(self, nome: str) -> None:
        if nome == "backspace":
            self._enviar(eventos_para_tecla(nome))
            self._ultimo_apagar = time.monotonic()
            return
        self._esperar_apos_apagar()
        self._enviar(eventos_para_tecla(nome))

    def escrever(self, texto: str) -> None:
        self._enviar_texto(texto)

    def tecla(self, nome: str) -> None:
        self._enviar_tecla(nome)

    def sequencia(self, acoes: list[tuple[str, str]]) -> None:
        """Envia uma lista de acoes em ordem.

        Cada grupo de backspaces vai num envio; o texto seguinte so sai depois
        da pausa de PAUSA_APOS_APAGAR. Assim o apagar e a escrita de uma
        sugestao nao se misturam na aplicacao de destino.
        """
        for tipo, valor in acoes:
            if tipo == "texto":
                self._enviar_texto(valor)
            elif tipo == "tecla":
                self._enviar_tecla(valor)
            else:
                raise ValueError(f"Tipo de acao desconhecido: {tipo}")

    def atalho(self, nome: str) -> None:
        """Executa uma acao de edicao (apagar/selecionar palavra ou linha)."""
        if nome not in ACOES_EDICAO:
            raise ValueError(f"Acao de edicao desconhecida: {nome}")
        for passo in ACOES_EDICAO[nome]:
            self._esperar_apos_apagar()
            self._enviar(eventos_para_passo(passo))
            if passo.endswith("backspace"):
                self._ultimo_apagar = time.monotonic()

    def enviar_atalho(self, passo: str) -> None:
        """Envia uma combinacao de teclas, ex.: "ctrl+c"."""
        self._esperar_apos_apagar()
        self._enviar(eventos_para_passo(passo))
        if passo.endswith("backspace"):
            self._ultimo_apagar = time.monotonic()

    def janela_ativa(self, acao: str, excluir: int = 0) -> bool:
        """Fecha, minimiza ou maximiza a janela em foco. Devolve False se nao houver alvo valido."""
        if acao not in ACOES_JANELA:
            raise ValueError(f"Acao de janela desconhecida: {acao}")
        user32 = self._user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd or hwnd == excluir:
            return False
        buffer = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, buffer, 64)
        if buffer.value in _CLASSES_PROTEGIDAS:
            return False
        if acao == "fechar_janela":
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)  # a aplicacao pode perguntar se guarda
        elif acao == "minimizar_janela":
            user32.ShowWindow(hwnd, SW_MINIMIZE)
        elif acao == "maximizar_janela":
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
        # "minimizar_teclado" nao e da janela em foco: e tratado pelo proprio teclado.
        return True

    def ler_selecao(self) -> str:
        """Copia a seleccao (Ctrl+C) e devolve o texto, repondo o conteudo anterior da area de transferencia.

        Limitacao: se a area de transferencia tinha imagem ou outro formato (nao texto),
        esse conteudo nao e reposto.
        """
        anterior = ler_clipboard_texto()
        esvaziar_clipboard()
        self._enviar(eventos_para_passo("ctrl+c"))
        texto = ""
        fim = time.monotonic() + 0.6
        while time.monotonic() < fim:
            time.sleep(0.03)
            lido = ler_clipboard_texto()
            if lido:
                texto = lido
                break
        if anterior is not None:
            escrever_clipboard_texto(anterior)
        return texto.strip()
