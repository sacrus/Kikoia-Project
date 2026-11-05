package pt.lplogic.teclado.rede

import android.content.SharedPreferences

/** Segredo partilhado com um computador emparelhado: permite ligar sem codigo. */
data class Confianca(val id: String, val segredoHex: String)

/**
 * Computadores de confianca, guardados por endereco Bluetooth. Ficam so na app (preferencias privadas).
 * Quem tiver este segredo pode ligar-se ao computador: nao o partilhe.
 */
object Confiancas {
    private const val PREFIXO = "confianca_bt_"
    private const val ULTIMO = "ultimo_bt"

    fun guardar(prefs: SharedPreferences, endereco: String, confianca: Confianca) {
        prefs.edit()
            .putString(PREFIXO + endereco, "${confianca.id}:${confianca.segredoHex}")
            .putString(ULTIMO, endereco)
            .apply()
    }

    fun ler(prefs: SharedPreferences, endereco: String): Confianca? {
        val valor = prefs.getString(PREFIXO + endereco, null) ?: return null
        val partes = valor.split(":")
        return if (partes.size == 2) Confianca(partes[0], partes[1]) else null
    }

    fun esquecer(prefs: SharedPreferences, endereco: String) {
        prefs.edit().remove(PREFIXO + endereco).apply()
    }

    /** Endereco Bluetooth do computador usado da ultima vez, se houver. */
    fun ultimo(prefs: SharedPreferences): String? = prefs.getString(ULTIMO, null)
}
