package pt.lplogic.teclado.protocolo

import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

class ProtocoloErro(mensagem: String) : Exception(mensagem)

/**
 * JSON canonico igual ao json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=False)
 * do Python: e sobre estes bytes que o HMAC e calculado.
 */
object JsonCanonico {
    fun codificar(valor: Any?): String = when (valor) {
        null -> "null"
        is String -> citar(valor)
        is Boolean -> valor.toString()
        is Int, is Long -> valor.toString()
        is Double -> valor.toString()
        is Map<*, *> -> valor.entries
            .sortedBy { it.key as String }
            .joinToString(",", "{", "}") { citar(it.key as String) + ":" + codificar(it.value) }
        is List<*> -> valor.joinToString(",", "[", "]") { codificar(it) }
        else -> throw IllegalArgumentException("tipo nao suportado: ${valor::class}")
    }

    private fun citar(texto: String): String {
        val sb = StringBuilder("\"")
        for (c in texto) {
            when {
                c == '"' -> sb.append("\\\"")
                c == '\\' -> sb.append("\\\\")
                c == '\n' -> sb.append("\\n")
                c == '\r' -> sb.append("\\r")
                c == '\t' -> sb.append("\\t")
                c == '\b' -> sb.append("\\b")
                c == '\u000c' -> sb.append("\\f")
                c < ' ' -> sb.append(String.format("\\u%04x", c.code))
                else -> sb.append(c)
            }
        }
        return sb.append('"').toString()
    }

    /** Converte um JSONObject em Map/List/valores simples, para validar e reencodificar. */
    fun paraMapa(objeto: JSONObject): Map<String, Any?> {
        val mapa = LinkedHashMap<String, Any?>()
        for (chave in objeto.keys()) mapa[chave] = paraValor(objeto.get(chave))
        return mapa
    }

    private fun paraValor(valor: Any?): Any? = when (valor) {
        JSONObject.NULL -> null
        is JSONObject -> paraMapa(valor)
        is JSONArray -> (0 until valor.length()).map { paraValor(valor.get(it)) }
        else -> valor
    }
}

object Protocolo {
    const val TAMANHO_MAXIMO = 16 * 1024
    private const val ALGORITMO = "HmacSHA256"

    private fun hmacBytes(chave: ByteArray, dados: ByteArray): ByteArray {
        val mac = Mac.getInstance(ALGORITMO)
        mac.init(SecretKeySpec(chave, ALGORITMO))
        return mac.doFinal(dados)
    }

    fun hmacHex(chave: ByteArray, texto: String): String =
        hmacBytes(chave, texto.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }

    private fun assinar(chave: ByteArray, mensagem: Map<String, Any?>): String {
        val semAssinatura = mensagem.filterKeys { it != "hmac" }
        return hmacHex(chave, JsonCanonico.codificar(semAssinatura))
    }

    /** Mensagem autenticada (tipo, id, sequencia + campos), como codificar() no Python. */
    fun codificar(chave: ByteArray, tipo: String, id: String, sequencia: Int, corpo: Map<String, Any?> = emptyMap()): ByteArray {
        val mensagem = LinkedHashMap<String, Any?>(corpo)
        mensagem["tipo"] = tipo
        mensagem["id"] = id
        mensagem["sequencia"] = sequencia
        mensagem["hmac"] = assinar(chave, mensagem)
        val bytes = JsonCanonico.codificar(mensagem).toByteArray(Charsets.UTF_8)
        if (bytes.size > TAMANHO_MAXIMO) throw ProtocoloErro("mensagem demasiado grande")
        return bytes
    }

    /** Mensagem de emparelhamento SPAKE2 (sem HMAC: ainda nao ha chave partilhada). */
    fun codificarEmparelhamento(passo: String, valor: String): ByteArray =
        JsonCanonico.codificar(mapOf("tipo" to "emparelhar", "passo" to passo, "valor" to valor))
            .toByteArray(Charsets.UTF_8)

    fun descodificarMapa(bytes: ByteArray): Map<String, Any?> {
        if (bytes.size > TAMANHO_MAXIMO) throw ProtocoloErro("mensagem demasiado grande")
        return try {
            JSONObject(String(bytes, Charsets.UTF_8)).let { JsonCanonico.paraMapa(it) }
        } catch (erro: Exception) {
            throw ProtocoloErro("mensagem mal formada")
        }
    }

    /** Chave de sessao derivada da chave SPAKE2 (igual a chave_sessao() no PC). */
    fun chaveSessao(chaveSpake: ByteArray): ByteArray = hmacBytes(chaveSpake, "gateway-sessao".toByteArray())

    fun novoId(): String = UUID.randomUUID().toString().take(12)
}

/** Sessao autenticada: envia com sequencia crescente e recebe verificando HMAC e sequencia. */
class Sessao(private val chave: ByteArray) {
    private var sequenciaEnvio = 0
    private var sequenciaMinima = 0

    fun enviar(tipo: String, id: String, corpo: Map<String, Any?> = emptyMap()): ByteArray {
        val bytes = Protocolo.codificar(chave, tipo, id, sequenciaEnvio, corpo)
        sequenciaEnvio++
        return bytes
    }

    fun receber(bytes: ByteArray): Map<String, Any?> {
        val mensagem = Protocolo.descodificarMapa(bytes)
        val tipo = mensagem["tipo"] as? String ?: throw ProtocoloErro("mensagem mal formada")
        if (tipo !in setOf("emparelhar", "teclados", "acao", "sugestoes", "ping", "pong")) {
            throw ProtocoloErro("tipo de mensagem desconhecido")
        }
        val recebido = mensagem["hmac"] as? String ?: throw ProtocoloErro("autenticacao falhou")
        val esperado = Protocolo.hmacHex(chave, JsonCanonico.codificar(mensagem.filterKeys { it != "hmac" }))
        if (!java.security.MessageDigest.isEqual(recebido.toByteArray(), esperado.toByteArray())) {
            throw ProtocoloErro("autenticacao falhou")
        }
        val sequencia = mensagem["sequencia"] as? Int ?: throw ProtocoloErro("sequencia invalida")
        if (sequencia < sequenciaMinima) throw ProtocoloErro("sequencia repetida ou fora de ordem")
        sequenciaMinima = sequencia + 1
        return mensagem
    }
}
