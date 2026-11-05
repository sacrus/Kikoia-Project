package pt.lplogic.teclado.rede

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Verifica se ha uma versao nova da app no GitHub. So avisa: o utilizador abre a pagina da versao
 * e transfere a APK. Sem rede, ou sem versao publicada, devolve null sem erro.
 */
object Atualizacao {
    const val REPOSITORIO = "sacrus/Kikoia-Project"
    const val VERSAO = "0.1.0"
    private const val TIMEOUT_MS = 8000

    data class Nova(val versao: String, val pagina: String)

    /** "v1.10.0" -> [1, 10, 0]. Compara numericamente, por isso 1.10 e mais recente que 1.9. */
    fun versaoTupla(texto: String): List<Int> =
        Regex("\\d+").findAll(texto).take(4).map { it.value.toInt() }.toList().ifEmpty { listOf(0) }

    fun e_mais_recente(etiqueta: String, atual: String = VERSAO): Boolean {
        val a = versaoTupla(etiqueta)
        val b = versaoTupla(atual)
        for (i in 0 until maxOf(a.size, b.size)) {
            val x = a.getOrElse(i) { 0 }
            val y = b.getOrElse(i) { 0 }
            if (x != y) return x > y
        }
        return false
    }

    /** Chamar fora da thread principal. Nunca lanca excecoes. */
    fun verificar(): Nova? = try {
        val ligacao = URL("https://api.github.com/repos/$REPOSITORIO/releases/latest")
            .openConnection() as HttpURLConnection
        try {
            ligacao.connectTimeout = TIMEOUT_MS
            ligacao.readTimeout = TIMEOUT_MS
            ligacao.setRequestProperty("Accept", "application/vnd.github+json")
            ligacao.setRequestProperty("User-Agent", "Kikoia/$VERSAO")
            if (ligacao.responseCode != HttpURLConnection.HTTP_OK) {
                null
            } else {
                val dados = JSONObject(ligacao.inputStream.bufferedReader().use { it.readText() })
                val etiqueta = dados.optString("tag_name")
                if (etiqueta.isNotEmpty() && e_mais_recente(etiqueta)) {
                    Nova(etiqueta.trimStart('v', 'V'), dados.optString("html_url"))
                } else {
                    null
                }
            }
        } finally {
            ligacao.disconnect()
        }
    } catch (erro: Exception) {
        null
    }
}
