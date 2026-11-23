package pt.lplogic.teclado

import android.graphics.BitmapFactory
import android.os.Handler
import android.os.Looper
import android.util.Base64
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap

/**
 * Icones das teclas, recebidos do computador em partes (mensagem "icones").
 * Os icones monocromaticos tomam a cor do texto da tecla; os coloridos mantem as suas cores.
 */
object IconesTeclado {
    private val pngs = HashMap<String, String>()
    private val coloridos = HashSet<String>()
    private val bitmaps = HashMap<String, ImageBitmap?>()
    private val principal = Handler(Looper.getMainLooper())

    /** Muda quando chegam icones: as teclas que os mostram voltam a desenhar-se. */
    var versao by mutableIntStateOf(0)
        private set

    @Synchronized
    fun receber(mensagem: Map<String, Any?>) {
        val imagens = mensagem["imagens"] as? Map<*, *> ?: return
        for ((nome, dados) in imagens) {
            if (nome is String && dados is String) {
                pngs[nome] = dados
                bitmaps.remove(nome)
            }
        }
        (mensagem["coloridos"] as? List<*>)?.filterIsInstance<String>()?.let { coloridos.addAll(it) }
        principal.post { versao++ }
    }

    @Synchronized
    fun bitmap(nome: String): ImageBitmap? {
        if (bitmaps.containsKey(nome)) return bitmaps[nome]
        val imagem = pngs[nome]?.let { codigo ->
            try {
                val bytes = Base64.decode(codigo, Base64.DEFAULT)
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
            } catch (erro: IllegalArgumentException) {
                null
            }
        }
        bitmaps[nome] = imagem
        return imagem
    }

    @Synchronized
    fun colorido(nome: String): Boolean = nome in coloridos
}
