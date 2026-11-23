package pt.lplogic.teclado

import android.os.Handler
import android.os.Looper
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/**
 * Modo do touchpad indicado pelo computador: "normal", ou no Quadro "quadro_desenho" / "quadro_clique".
 * No Quadro o touchpad mostra uma so area, com desenhos que explicam o uso de 1 e 2 dedos.
 */
object ModoTouchpad {
    private val principal = Handler(Looper.getMainLooper())

    var modo by mutableStateOf("normal")
        private set

    fun receber(mensagem: Map<String, Any?>) {
        val valor = mensagem["modo"] as? String ?: return
        principal.post { modo = valor }
    }

    /** True quando o touchpad controla o Quadro Interativo (uma so area, sem barra de deslocamento). */
    fun noQuadro(): Boolean = modo != "normal"
}
