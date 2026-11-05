package pt.lplogic.teclado.rede

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.SocketTimeoutException

data class ComputadorEncontrado(val nome: String, val ip: String, val porta: Int)

const val PORTA_POR_OMISSAO = 47800
private const val PEDIDO = "TECLADO-GW?"

/**
 * Procura computadores com o teclado na rede local: envia um pedido por broadcast UDP
 * e recolhe as respostas durante alguns segundos. Nao precisa de IP nem de configuracao.
 */
suspend fun procurarComputadores(tempoMs: Long = 3000L): List<ComputadorEncontrado> =
    withContext(Dispatchers.IO) {
        val encontrados = LinkedHashMap<String, ComputadorEncontrado>()
        DatagramSocket().use { socket ->
            socket.broadcast = true
            socket.soTimeout = 300
            val pedido = PEDIDO.toByteArray(Charsets.UTF_8)
            socket.send(DatagramPacket(pedido, pedido.size, InetAddress.getByName("255.255.255.255"), PORTA_POR_OMISSAO))
            val fim = System.currentTimeMillis() + tempoMs
            val buffer = ByteArray(1024)
            while (System.currentTimeMillis() < fim) {
                val pacote = DatagramPacket(buffer, buffer.size)
                try {
                    socket.receive(pacote)
                } catch (_: SocketTimeoutException) {
                    continue
                }
                val texto = String(pacote.data, 0, pacote.length, Charsets.UTF_8)
                try {
                    val json = JSONObject(texto)
                    if (json.optInt("gw") != 1) continue
                    val ip = pacote.address.hostAddress ?: continue
                    val porta = json.getInt("porta")
                    val chave = "$ip:$porta"
                    encontrados[chave] = ComputadorEncontrado(json.getString("nome"), ip, porta)
                } catch (_: Exception) {
                    // resposta de outra aplicacao na rede: ignorar
                }
            }
        }
        encontrados.values.toList()
    }
