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
        val cabecalho = DataOutputStream(saida)
        cabecalho.writeInt(dados.size)
        cabecalho.write(dados)
        cabecalho.flush()
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
