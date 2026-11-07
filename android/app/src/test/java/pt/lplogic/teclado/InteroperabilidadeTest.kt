package pt.lplogic.teclado

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import pt.lplogic.teclado.crypto.Ed25519
import pt.lplogic.teclado.crypto.Spake2A
import pt.lplogic.teclado.protocolo.Protocolo
import pt.lplogic.teclado.protocolo.ProtocoloErro
import pt.lplogic.teclado.protocolo.Sessao
import java.math.BigInteger

/**
 * Vetores gerados pelo Python (spake2 0.9 e teclado.gateway.protocolo) com:
 *  - SPAKE2_A(pw, entropia=7 repetido) e SPAKE2_B(pw, entropia=9 repetido)
 *  - codificar(b"k"*32, "acao", "id1", 3, {"acao": {"tipo":"texto","valor":"olá"}})
 * Se alguma destas igualdades falhar, o telemovel nao fala com o PC.
 */
class InteroperabilidadeTest {

    private val senha = "123456".toByteArray(Charsets.US_ASCII)
    private val idA = "cliente".toByteArray()
    private val idB = "pc".toByteArray()
    private val escalarA = BigInteger(1, ByteArray(64) { 7 }).mod(Ed25519.L)

    private val mensagemA =
        "41c50df64573bcc193b10780f42a76f3bf73632153800766c65956690d12ea515e"
    private val mensagemB =
        "426801a5885bcef0d6036e8bc216274eac1c976f58f73932357be95c84306ff8c6"
    private val chaveEsperada =
        "356aded8a230e3ad16438ac6e08bd1012d5beace4610a46995c643f749395073"

    @Test
    fun mensagemInicialIgualAoPython() {
        val spake = Spake2A(senha, idA, idB, escalarA)
        assertEquals(mensagemA, spake.iniciar().hex())
    }

    @Test
    fun chaveIgualAoPython() {
        val spake = Spake2A(senha, idA, idB, escalarA)
        spake.iniciar()
        val chave = spake.terminar(mensagemB.hexParaBytes())
        assertEquals(chaveEsperada, chave.hex())
    }

    @Test
    fun codigoErradoGeraChaveDiferente() {
        val spake = Spake2A("000000".toByteArray(), idA, idB, escalarA)
        spake.iniciar()
        val chave = spake.terminar(mensagemB.hexParaBytes())
        assertTrue(chave.hex() != chaveEsperada)
    }

    @Test
    fun mensagemRefletidaERecusada() {
        val spake = Spake2A(senha, idA, idB, escalarA)
        val minha = spake.iniciar()
        val refletida = minha.copyOf().also { it[0] = 'B'.code.toByte() }
        try {
            spake.terminar(refletida)
            fail("devia recusar mensagem refletida")
        } catch (esperado: IllegalArgumentException) {
            assertTrue(esperado.message!!.contains("refletida"))
        }
    }

    @Test
    fun jsonEHmacIgualAoPython() {
        val chave = ByteArray(32) { 'k'.code.toByte() }
        val corpo = mapOf("acao" to mapOf("tipo" to "texto", "valor" to "ol\u00e1"))
        val bytes = Protocolo.codificar(chave, "acao", "id1", 3, corpo)
        val esperado =
            "{\"acao\":{\"tipo\":\"texto\",\"valor\":\"ol\u00e1\"}," +
                "\"hmac\":\"0b0289161e7ea90c7f3c10c0a7cf1ad59b7c3174801f0d19a80cdd35d5d0fa6c\"," +
                "\"id\":\"id1\",\"sequencia\":3,\"tipo\":\"acao\"}"
        assertEquals(esperado, String(bytes, Charsets.UTF_8))
    }

    @Test
    fun sessaoRecusaRepeticao() {
        val chave = ByteArray(32) { 1 }
        val emissor = Sessao(chave)
        val recetor = Sessao(chave)
        val primeira = emissor.enviar("ping", "a")
        recetor.receber(primeira)
        try {
            recetor.receber(primeira)
            fail("devia recusar repeticao")
        } catch (esperado: ProtocoloErro) {
            assertTrue(esperado.message!!.contains("sequencia"))
        }
    }

    @Test
    fun sessaoRecusaMensagemAdulterada() {
        val chave = ByteArray(32) { 1 }
        val bytes = Sessao(chave).enviar("acao", "a", mapOf("acao" to mapOf("tipo" to "texto", "valor" to "x")))
        val adulterada = String(bytes, Charsets.UTF_8).replace("\"valor\":\"x\"", "\"valor\":\"y\"")
        try {
            Sessao(chave).receber(adulterada.toByteArray())
            fail("devia recusar adulteracao")
        } catch (esperado: ProtocoloErro) {
            assertTrue(esperado.message!!.contains("autenticacao"))
        }
    }

    @Test
    fun ligacaoDeConfiancaIgualAoPython() {
        // Vetores de teclado.gateway.confianca (segredo = 01 x32, nonce = ab x16).
        val segredo = ByteArray(32) { 1 }
        val nonce = "ab".repeat(16)
        assertEquals("f8928a3728d7becb90f54007a4ddab3fabe6de73b0d838e067dc724945778575",
            Protocolo.hmacHex(segredo, "cliente:$nonce"))
        assertEquals("476a1a235044727efcb527bfe6da47a4a8bcc7c40ed89b6adff55314db287eba",
            Protocolo.hmacHex(segredo, "servidor:$nonce"))
        assertEquals("a82dc93d05d3294f63feca03435242e9ef51e6f0fad6850036402daece514e28",
            Protocolo.hmacHex(segredo, "reconhecer:$nonce"))
    }

    private fun String.hexParaBytes(): ByteArray =
        ByteArray(length / 2) { substring(it * 2, it * 2 + 2).toInt(16).toByte() }

    private fun ByteArray.hex(): String = joinToString("") { "%02x".format(it) }
}
