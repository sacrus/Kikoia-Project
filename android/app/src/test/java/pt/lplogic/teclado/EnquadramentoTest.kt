package pt.lplogic.teclado

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import pt.lplogic.teclado.rede.Enquadramento
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException

/** Mesmo formato que CanalEnquadrado do Python: prefixo de 4 bytes big-endian com o tamanho. */
class EnquadramentoTest {

    @Test
    fun vetorIgualAoPython() {
        val saida = ByteArrayOutputStream()
        Enquadramento.escrever(saida, "ab".toByteArray())
        assertArrayEquals(byteArrayOf(0, 0, 0, 2, 0x61, 0x62), saida.toByteArray())
    }

    @Test
    fun mensagensSeguidasMantemFronteiras() {
        val saida = ByteArrayOutputStream()
        Enquadramento.escrever(saida, "um".toByteArray())
        Enquadramento.escrever(saida, "dois-maior".toByteArray())
        val entrada = ByteArrayInputStream(saida.toByteArray())
        assertEquals("um", String(Enquadramento.ler(entrada)))
        assertEquals("dois-maior", String(Enquadramento.ler(entrada)))
    }

    @Test
    fun tamanhoAcimaDoLimiteERecusado() {
        val entrada = ByteArrayInputStream(byteArrayOf(0x00, 0x10, 0x00, 0x01))
        assertThrows(IOException::class.java) { Enquadramento.ler(entrada) }
    }

    @Test
    fun escreverAcimaDoLimiteERecusado() {
        assertThrows(IllegalArgumentException::class.java) {
            Enquadramento.escrever(ByteArrayOutputStream(), ByteArray(Enquadramento.TAMANHO_MAXIMO + 1))
        }
    }
}
