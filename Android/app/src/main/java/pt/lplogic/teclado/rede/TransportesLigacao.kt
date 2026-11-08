package pt.lplogic.teclado.rede

import pt.lplogic.teclado.R
import pt.lplogic.teclado.recurso
import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.Context
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.io.IOException
import java.util.UUID
import java.util.concurrent.TimeUnit

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

/** Wi-Fi: WebSocket para o computador na mesma rede. */
class TransporteWifi(
    private val computador: ComputadorEncontrado,
    private val ligacao: LigacaoGateway,
) : Transporte {
    private val cliente = OkHttpClient.Builder().pingInterval(20, TimeUnit.SECONDS).build()
    private var ws: WebSocket? = null

    fun ligar() {
        val pedido = Request.Builder().url("ws://${computador.ip}:${computador.porta}").build()
        ws = cliente.newWebSocket(pedido, ouvinte)
    }

    override fun enviar(dados: ByteArray): Boolean = ws?.send(ByteString.of(*dados)) ?: false

    override fun fechar() {
        ws?.close(1000, "fim")
    }

    private val ouvinte = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            ligacao.aoAbrir(this@TransporteWifi)
        }

        override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
            ligacao.aoReceber(bytes.toByteArray())
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            ligacao.aoFechar("${motivoDoFecho(code)} [codigo $code${if (reason.isNotEmpty()) ": $reason" else ""}]")
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
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
    private val escrita = Any()
    @Volatile private var ligado = false

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

    override fun enviar(dados: ByteArray): Boolean {
        val s = socket ?: return false
        return try {
            synchronized(escrita) { Enquadramento.escrever(s.outputStream, dados) }
            true
        } catch (erro: IOException) {
            false
        }
    }

    override fun fechar() {
        fecharSocket()
    }

    private fun fecharSocket() {
        try {
            socket?.close()
        } catch (_: IOException) {
            // ja estava fechado
        }
        socket = null
    }
}
