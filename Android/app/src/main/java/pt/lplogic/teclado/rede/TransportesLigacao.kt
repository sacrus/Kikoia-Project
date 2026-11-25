package pt.lplogic.teclado.rede

import pt.lplogic.teclado.R
import pt.lplogic.teclado.TecladoApp
import pt.lplogic.teclado.recurso
import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.net.wifi.WifiManager
import android.os.Build
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.io.IOException
import java.net.InetAddress
import java.net.Socket
import java.util.ArrayDeque
import java.util.LinkedHashMap
import java.util.UUID
import java.util.concurrent.TimeUnit
import javax.net.SocketFactory

/** Tempo maximo para o computador aceitar a ligacao Bluetooth. */
private const val LIMITE_LIGACAO_BT_MS = 15_000L

/** Servico SPP: o mesmo UUID anunciado pelo PC no Bluetooth. */
val UUID_SPP: UUID = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")

/** Dispositivos Bluetooth ja emparelhados nas definicoes do Android. Vazio sem permissao. */
@SuppressLint("MissingPermission")
fun dispositivosBluetoothEmparelhados(contexto: Context): List<BluetoothDevice> = try {
    val adaptador = contexto.getSystemService(BluetoothManager::class.java)?.adapter
    adaptador?.bondedDevices?.sortedBy { it.name ?: "" } ?: emptyList()
} catch (_: SecurityException) {
    emptyList()
}

/** SocketFactory que ativa TCP_NODELAY e IPTOS_LOWDELAY para eliminar atraso de Nagle no Wi-Fi. */
private class FabricaSocketBaixaLatencia : SocketFactory() {
    private val base = getDefault()

    private fun configurar(s: Socket): Socket {
        try {
            s.tcpNoDelay = true
            s.trafficClass = 0x10 // IPTOS_LOWDELAY
        } catch (_: Exception) {
            // Alguns dispositivos ignoram trafficClass; tcpNoDelay e o principal.
        }
        return s
    }

    override fun createSocket(): Socket = configurar(base.createSocket())
    override fun createSocket(host: String, port: Int): Socket = configurar(base.createSocket(host, port))
    override fun createSocket(host: String, port: Int, localHost: InetAddress, localPort: Int): Socket =
        configurar(base.createSocket(host, port, localHost, localPort))
    override fun createSocket(host: InetAddress, port: Int): Socket = configurar(base.createSocket(host, port))
    override fun createSocket(address: InetAddress, port: Int, localAddress: InetAddress, localPort: Int): Socket =
        configurar(base.createSocket(address, port, localAddress, localPort))
}

/** Wi-Fi: WebSocket de baixa latencia com TCP_NODELAY, WifiLock e coalescencia de movimentos. */
class TransporteWifi(
    private val computador: ComputadorEncontrado,
    private val ligacao: LigacaoGateway,
) : Transporte {
    private val cliente = OkHttpClient.Builder()
        .socketFactory(FabricaSocketBaixaLatencia())
        .pingInterval(20, TimeUnit.SECONDS)
        .build()
    private var ws: WebSocket? = null
    private var wifiLock: WifiManager.WifiLock? = null
    private val travaFila = Object()
    private val filaFiavel = ArrayDeque<ByteArray>()
    private val pendentesSubstituiveis = LinkedHashMap<String, ByteArray>()
    private var threadEnvio: Thread? = null
    @Volatile private var fechado = false

    fun ligar() {
        adquirirWifiLock()
        val pedido = Request.Builder().url("ws://${computador.ip}:${computador.porta}").build()
        ws = cliente.newWebSocket(pedido, ouvinte)
    }

    private fun adquirirWifiLock() {
        try {
            val wm = TecladoApp.instancia.applicationContext.getSystemService(WifiManager::class.java) ?: return
            @Suppress("DEPRECATION")
            val modo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                WifiManager.WIFI_MODE_FULL_LOW_LATENCY
            } else {
                WifiManager.WIFI_MODE_FULL_HIGH_PERF
            }
            val lock = wm.createWifiLock(modo, "Kikoia:WifiBaixaLatencia")
            lock.setReferenceCounted(false)
            lock.acquire()
            wifiLock = lock
        } catch (_: Exception) {
            // Ignorado se o ambiente (ex.: teste unitario) nao tiver WifiManager.
        }
    }

    private fun libertarWifiLock() {
        try {
            if (wifiLock?.isHeld == true) wifiLock?.release()
        } catch (_: Exception) {
        }
        wifiLock = null
    }

    private fun iniciarThreadEnvio(webSocket: WebSocket) {
        val t = Thread {
            try {
                while (!fechado) {
                    var ehSubstituivel = false
                    val dados: ByteArray? = synchronized(travaFila) {
                        while (!fechado && filaFiavel.isEmpty() && pendentesSubstituiveis.isEmpty()) {
                            travaFila.wait()
                        }
                        if (fechado) {
                            null
                        } else if (filaFiavel.isNotEmpty()) {
                            filaFiavel.removeFirst()
                        } else {
                            // Se a fila interna do OkHttp ainda esta a escoar um pacote anterior,
                            // aguarda brevemente para coalescer novos movimentos em vez de acumular atraso.
                            if (webSocket.queueSize() > 0L) {
                                travaFila.wait(4L)
                            }
                            if (fechado) {
                                null
                            } else if (filaFiavel.isNotEmpty()) {
                                filaFiavel.removeFirst()
                            } else if (pendentesSubstituiveis.isNotEmpty()) {
                                ehSubstituivel = true
                                val it = pendentesSubstituiveis.entries.iterator()
                                val primeiro = it.next().value
                                it.remove()
                                primeiro
                            } else {
                                null
                            }
                        }
                    }
                    if (dados == null) {
                        if (fechado) break
                        continue
                    }
                    if (!webSocket.send(ByteString.of(*dados)) && !ehSubstituivel) {
                        break
                    }
                }
            } catch (_: InterruptedException) {
                // encerramento normal
            }
        }.apply { isDaemon = true; name = "wifi-envio" }
        threadEnvio = t
        t.start()
    }

    override fun enviar(dados: ByteArray): Boolean {
        if (fechado || ws == null) return false
        synchronized(travaFila) {
            if (fechado) return false
            if (pendentesSubstituiveis.isNotEmpty()) {
                for (pendente in pendentesSubstituiveis.values) {
                    filaFiavel.addLast(pendente)
                }
                pendentesSubstituiveis.clear()
            }
            filaFiavel.addLast(dados)
            travaFila.notifyAll()
        }
        return true
    }

    override fun enviarSubstituivel(chave: String, dados: ByteArray): Boolean {
        if (fechado || ws == null) return false
        synchronized(travaFila) {
            if (fechado) return false
            pendentesSubstituiveis[chave] = dados
            travaFila.notifyAll()
        }
        return true
    }

    override fun fechar() {
        encerrarInterno()
        ws?.close(1000, "fim")
    }

    private fun encerrarInterno() {
        fechado = true
        synchronized(travaFila) {
            filaFiavel.clear()
            pendentesSubstituiveis.clear()
            travaFila.notifyAll()
        }
        threadEnvio?.interrupt()
        threadEnvio = null
        libertarWifiLock()
    }

    private val ouvinte = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            iniciarThreadEnvio(webSocket)
            ligacao.aoAbrir(this@TransporteWifi)
        }

        override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
            ligacao.aoReceber(bytes.toByteArray())
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            encerrarInterno()
            ligacao.aoFechar("${motivoDoFecho(code)} [codigo $code${if (reason.isNotEmpty()) ": $reason" else ""}]")
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            encerrarInterno()
            // Detalhe tecnico para diagnostico (tipo de erro, mensagem e resposta HTTP, se houver).
            val http = response?.let { " HTTP ${it.code}" } ?: ""
            ligacao.aoFechar(
                recurso(R.string.and_wifi_falhou) + " [${t.javaClass.simpleName}: ${t.message ?: "sem mensagem"}$http]",
            )
        }
    }
}

/**
 * Bluetooth (RFCOMM/SPP) para um computador ja emparelhado nas definicoes do Android.
 * A ligacao e feita numa thread propria; as mensagens sao enquadradas (ver Enquadramento).
 */
class TransporteBluetooth(
    private val dispositivo: BluetoothDevice,
    private val ligacao: LigacaoGateway,
) : Transporte {
    private var socket: BluetoothSocket? = null
    private val travaFila = Object()
    private val filaFiavel = ArrayDeque<ByteArray>()
    private val pendentesSubstituiveis = LinkedHashMap<String, ByteArray>()
    private var threadEnvio: Thread? = null
    @Volatile private var ligado = false
    @Volatile private var fechado = false

    @SuppressLint("MissingPermission")
    fun ligar() {
        // Sem resposta do computador, a tentativa e cancelada (fecha o socket e o connect() falha).
        Thread {
            try {
                Thread.sleep(LIMITE_LIGACAO_BT_MS)
            } catch (_: InterruptedException) {
                return@Thread
            }
            if (!ligado) fecharSocket()
        }.apply { isDaemon = true; name = "bluetooth-limite" }.start()
        Thread {
            try {
                val s = dispositivo.createRfcommSocketToServiceRecord(UUID_SPP)
                socket = s
                s.connect()
                ligado = true
                iniciarThreadEnvio(s)
                ligacao.aoAbrir(this)
                val entrada = s.inputStream
                while (true) {
                    ligacao.aoReceber(Enquadramento.ler(entrada))
                }
            } catch (erro: SecurityException) {
                ligacao.aoFechar(recurso(R.string.and_bt_permissao))
            } catch (erro: IOException) {
                ligacao.aoFechar(
                    recurso(R.string.and_bt_falhou_1) +
                        recurso(R.string.and_bt_falhou_2),
                )
            } finally {
                fecharSocket()
            }
        }.apply { isDaemon = true; name = "bluetooth-gateway" }.start()
    }

    private fun iniciarThreadEnvio(s: BluetoothSocket) {
        val t = Thread {
            val saida = s.outputStream
            try {
                while (!fechado) {
                    val dados: ByteArray? = synchronized(travaFila) {
                        while (!fechado && filaFiavel.isEmpty() && pendentesSubstituiveis.isEmpty()) {
                            travaFila.wait()
                        }
                        if (fechado) {
                            null
                        } else if (filaFiavel.isNotEmpty()) {
                            filaFiavel.removeFirst()
                        } else {
                            val it = pendentesSubstituiveis.entries.iterator()
                            val primeiro = it.next().value
                            it.remove()
                            primeiro
                        }
                    }
                    if (dados == null || fechado) break
                    Enquadramento.escrever(saida, dados)
                }
            } catch (_: InterruptedException) {
                // encerramento normal
            } catch (_: IOException) {
                fecharSocket()
            }
        }.apply { isDaemon = true; name = "bluetooth-envio" }
        threadEnvio = t
        t.start()
    }

    override fun enviar(dados: ByteArray): Boolean {
        if (fechado || socket == null) return false
        synchronized(travaFila) {
            if (fechado) return false
            // Descarrega qualquer movimento pendente (sequencia anterior) antes do evento fiavel
            // para garantir ordem estrita de sequencia no protocolo.
            if (pendentesSubstituiveis.isNotEmpty()) {
                for (pendente in pendentesSubstituiveis.values) {
                    filaFiavel.addLast(pendente)
                }
                pendentesSubstituiveis.clear()
            }
            filaFiavel.addLast(dados)
            travaFila.notifyAll()
        }
        return true
    }

    override fun enviarSubstituivel(chave: String, dados: ByteArray): Boolean {
        if (fechado || socket == null) return false
        synchronized(travaFila) {
            if (fechado) return false
            // Guarda apenas a posicao mais recente para esta chave: zero acumulacao de delay no Bluetooth!
            pendentesSubstituiveis[chave] = dados
            travaFila.notifyAll()
        }
        return true
    }

    override fun fechar() {
        fecharSocket()
    }

    private fun fecharSocket() {
        fechado = true
        synchronized(travaFila) {
            filaFiavel.clear()
            pendentesSubstituiveis.clear()
            travaFila.notifyAll()
        }
        threadEnvio?.interrupt()
        threadEnvio = null
        try {
            socket?.close()
        } catch (_: IOException) {
            // ja estava fechado
        }
        socket = null
    }
}
