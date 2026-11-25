package pt.lplogic.teclado.rede

import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream

/** Canal de bytes para a ligacao (Wi-Fi ou Bluetooth). Mensagens ja vem separadas. */
interface Transporte {
    /** Envia uma mensagem. Devolve false se a ligacao ja nao estiver disponivel. */
    fun enviar(dados: ByteArray): Boolean
    /** Envia uma mensagem de estado continuo (ex.: movimento do touchpad) que pode substituir a anterior pendente. */
    fun enviarSubstituivel(chave: String, dados: ByteArray): Boolean = enviar(dados)
    fun fechar()
}

/**
 * Enquadramento de mensagens sobre um fluxo de bytes (Bluetooth RFCOMM).
 * Cada mensagem leva um prefixo de 4 bytes com o tamanho, em big-endian,
 * igual ao CanalEnquadrado do Python.
 */
object Enquadramento {
    const val TAMANHO_MAXIMO = 16 * 1024

    fun escrever(saida: OutputStream, dados: ByteArray) {
        require(dados.size <= TAMANHO_MAXIMO) { "mensagem demasiado grande" }
        // Envia cabecalho (4 bytes big-endian) + corpo numa unica escrita para evitar fragmentacao RFCOMM.
        val pacote = ByteArray(4 + dados.size)
        val tam = dados.size
        pacote[0] = (tam ushr 24).toByte()
        pacote[1] = (tam ushr 16).toByte()
        pacote[2] = (tam ushr 8).toByte()
        pacote[3] = tam.toByte()
        System.arraycopy(dados, 0, pacote, 4, tam)
        saida.write(pacote)
        saida.flush()
    }

    fun ler(entrada: InputStream): ByteArray {
        val dados = DataInputStream(entrada)
        val tamanho = dados.readInt()
        if (tamanho < 0 || tamanho > TAMANHO_MAXIMO) throw IOException("mensagem demasiado grande")
        val corpo = ByteArray(tamanho)
        dados.readFully(corpo)
        return corpo
    }
}
