package pt.lplogic.teclado.rede

import pt.lplogic.teclado.R
import pt.lplogic.teclado.recurso
import pt.lplogic.teclado.crypto.Spake2A
import pt.lplogic.teclado.modelo.Teclado
import pt.lplogic.teclado.modelo.teclado
import pt.lplogic.teclado.protocolo.Protocolo
import pt.lplogic.teclado.protocolo.Sessao

/** Eventos da ligacao. Chamados numa thread de rede: quem os usa deve mudar para a thread principal. */
interface OuvinteGateway {
    fun aoEstado(texto: String)
    /** Teclado ativo no computador (substitui sempre o anterior). */
    fun aoTeclado(teclado: Teclado)
    /** Sugestoes de palavras atuais no computador. */
    fun aoSugestoes(palavras: List<String>)
    fun aoFechar(motivo: String?)
    /** A ligacao esta ativa e autenticada: mostrar o teclado. */
    fun aoLigar() {}
    /** Estado de Falar e Ditar no computador (e se cada um esta disponivel). */
    fun aoInterruptores(estado: Map<String, Any?>) {}
    /** Emparelhamento com codigo concluido: guardar para ligar sem codigo da proxima vez. */
    fun aoConfiar(confianca: Confianca) {}
    /** O computador ja nao reconhece este telemovel: e preciso o codigo outra vez. */
    fun aoPerderConfianca() {}
}

private enum class Passo { DESAFIO, CONFIANCA, CONFIRMACAO, CONFIRMACAO_CONFIANCA, ATIVO }

/** O computador ja nao conhece este telemovel (ex.: foi reinstalado). */
private class PerdeuConfianca : Exception("sem confianca")

/**
 * Estado do emparelhamento e da sessao, independente do transporte (Wi-Fi ou Bluetooth).
 * Com [confianca] liga sem codigo; sem ela, emparelha com o codigo de 6 digitos.
 * O computador e a fonte de verdade: o telemovel mostra o teclado ativo e envia acoes.
 */
class LigacaoGateway(
    private val nomeComputador: String,
    private val codigo: String?,
    private val confianca: Confianca?,
    private val ouvinte: OuvinteGateway,
) {
    private var transporte: Transporte? = null
    private var spake: Spake2A? = null
    private var chave: ByteArray? = null
    private var nonce: String? = null
    private var sessao: Sessao? = null
    private var passo = Passo.DESAFIO
    private var fechada = false

    val ativa: Boolean
        get() = synchronized(this) { sessao != null && !fechada }

    /** O transporte ficou pronto: comeca a ligacao (de confianca ou com codigo). */
    @Synchronized
    fun aoAbrir(t: Transporte) {
        if (fechada) return
        transporte = t
        val c = confianca
        if (c != null) {
            passo = Passo.CONFIANCA
            ouvinte.aoEstado(recurso(R.string.and_ligar))
            t.enviar(Protocolo.codificarEmparelhamento("reconhecer", c.id))
            return
        }
        val s = Spake2A((codigo ?: "").toByteArray(Charsets.US_ASCII), "cliente".toByteArray(), "pc".toByteArray())
        spake = s
        ouvinte.aoEstado(recurso(R.string.and_emparelhar_estado))
        t.enviar(Protocolo.codificarEmparelhamento("desafio", s.iniciar().hex()))
    }

    /** Chegou uma mensagem do computador. Qualquer erro fecha a ligacao. */
    @Synchronized
    fun aoReceber(bytes: ByteArray) {
        if (fechada) return
        try {
            tratar(bytes)
        } catch (erro: PerdeuConfianca) {
            fechada = true
            transporte?.fechar()
            ouvinte.aoPerderConfianca()
        } catch (erro: Exception) {
            fechada = true
            transporte?.fechar()
            ouvinte.aoFechar(recurso(R.string.and_ligacao_recusada, erro.message ?: recurso(R.string.and_erro_protocolo)))
        }
    }

    /** O transporte fechou (pelo computador, por rede ou por erro). */
    @Synchronized
    fun aoFechar(motivo: String) {
        if (fechada) return
        fechada = true
        ouvinte.aoFechar(if (sessao == null) motivo else recurso(R.string.and_ligacao_perdida))
    }

    /** Envia uma tecla ou acao do teclado. Devolve false se ainda nao estiver autenticada. */
    @Synchronized
    fun enviarAcao(tipo: String, valor: String): Boolean =
        enviarMensagem("acao", mapOf("acao" to mapOf("tipo" to tipo, "valor" to valor)))

    /** Pede ao computador para ligar ou desligar Falar ("falar") ou Ditar ("ditar"). */
    @Synchronized
    fun alternarInterruptor(nome: String, ligado: Boolean): Boolean =
        enviarMensagem("interruptor", mapOf("nome" to nome, "ligado" to ligado))

    /** Escolhe a sugestao com este indice (0 a 9) na lista atual do computador. */
    @Synchronized
    fun escolherSugestao(indice: Int): Boolean = enviarMensagem("escolher_sugestao", mapOf("indice" to indice))

    @Synchronized
    fun fechar() {
        fechada = true
        transporte?.fechar()
    }

    @Synchronized
    private fun enviarMensagem(tipo: String, corpo: Map<String, Any?>): Boolean {
        val s = sessao ?: return false
        val t = transporte ?: return false
        return t.enviar(s.enviar(tipo, Protocolo.novoId(), corpo))
    }

    private fun tratar(bytes: ByteArray) {
        val t = transporte ?: return
        when (passo) {
            Passo.CONFIANCA -> {
                val mensagem = Protocolo.descodificarMapa(bytes)
                if (mensagem["passo"] == "sem_confianca") throw PerdeuConfianca()
                require(mensagem["passo"] == "desafio_confianca") { "passo inesperado" }
                val c = confianca!!
                val segredo = c.segredoHex.hexParaBytes()
                val valorNonce = mensagem["valor"] as String
                nonce = valorNonce
                t.enviar(
                    Protocolo.codificarEmparelhamento(
                        "resposta_confianca",
                        Protocolo.hmacHex(segredo, "cliente:$valorNonce"),
                    ),
                )
                chave = Protocolo.hmacHex(segredo, "reconhecer:$valorNonce").hexParaBytes()
                passo = Passo.CONFIRMACAO_CONFIANCA
            }
            Passo.CONFIRMACAO_CONFIANCA -> {
                val mensagem = Protocolo.descodificarMapa(bytes)
                require(mensagem["passo"] == "confirmacao_confianca") { "passo inesperado" }
                val segredo = confianca!!.segredoHex.hexParaBytes()
                require(mensagem["valor"] == Protocolo.hmacHex(segredo, "servidor:${nonce!!}")) { "computador não confirmado" }
                sessao = Sessao(Protocolo.chaveSessao(chave!!))
                passo = Passo.ATIVO
                ouvinte.aoEstado(recurso(R.string.and_ligado_a, nomeComputador))
                ouvinte.aoLigar()
            }
            Passo.DESAFIO -> {
                val mensagem = Protocolo.descodificarMapa(bytes)
                require(mensagem["passo"] == "resposta") { "passo inesperado" }
                val resposta = (mensagem["valor"] as String).hexParaBytes()
                val chaveSpake = spake!!.terminar(resposta)
                chave = chaveSpake
                t.enviar(Protocolo.codificarEmparelhamento("confirmacao", Protocolo.hmacHex(chaveSpake, "cliente")))
                passo = Passo.CONFIRMACAO
                ouvinte.aoEstado(recurso(R.string.and_confirmar_codigo))
            }
            Passo.CONFIRMACAO -> {
                val mensagem = Protocolo.descodificarMapa(bytes)
                require(mensagem["passo"] == "confirmacao") { "passo inesperado" }
                val chaveSpake = chave!!
                require(mensagem["valor"] == Protocolo.hmacHex(chaveSpake, "servidor")) { "código errado" }
                sessao = Sessao(Protocolo.chaveSessao(chaveSpake))
                passo = Passo.ATIVO
                ouvinte.aoConfiar(
                    Confianca(
                        id = Protocolo.hmacHex(chaveSpake, "gateway-id").take(32),
                        segredoHex = Protocolo.hmacHex(chaveSpake, "gateway-confianca"),
                    ),
                )
                ouvinte.aoEstado(recurso(R.string.and_ligado_a, nomeComputador))
                ouvinte.aoLigar()
            }
            Passo.ATIVO -> {
                val mensagem = sessao!!.receber(bytes)
                when (mensagem["tipo"]) {
                    "teclados" -> {
                        val lista = mensagem["layouts"] as? List<*> ?: return
                        lista.filterIsInstance<Map<*, *>>().firstOrNull()?.let { ouvinte.aoTeclado(teclado(it)) }
                    }
                    "sugestoes" -> {
                        val palavras = (mensagem["palavras"] as? List<*>)?.filterIsInstance<String>() ?: emptyList()
                        ouvinte.aoSugestoes(palavras)
                    }
                    "interruptores" -> ouvinte.aoInterruptores(mensagem)
                }
            }
        }
    }
}

/** Motivo legivel quando o computador fecha a ligacao com um codigo conhecido. */
fun motivoDoFecho(code: Int): String = when (code) {
    4001 -> recurso(R.string.and_fecho_4001)
    4003 -> recurso(R.string.and_fecho_4003)
    4004 -> recurso(R.string.and_fecho_4004)
    1008 -> recurso(R.string.and_fecho_1008)
    else -> recurso(R.string.and_fecho_outro)
}

fun ByteArray.hex(): String = joinToString("") { "%02x".format(it) }

fun String.hexParaBytes(): ByteArray {
    require(length % 2 == 0) { "hexadecimal invalido" }
    return ByteArray(length / 2) { substring(it * 2, it * 2 + 2).toInt(16).toByte() }
}
