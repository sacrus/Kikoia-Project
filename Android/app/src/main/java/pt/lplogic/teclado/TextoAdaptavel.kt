package pt.lplogic.teclado

import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Constraints
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text

/**
 * Texto que diminui (ate tamanhoMinimo) para caber na tecla, sem mudar o tamanho da tecla.
 * Tenta primeiro uma linha; se nem no tamanho minimo couber, usa duas linhas e reticencias.
 */
@Composable
fun TextoAdaptavel(
    texto: String,
    tamanhoMaximo: TextUnit,
    tamanhoMinimo: TextUnit,
    modifier: Modifier = Modifier.fillMaxSize(),
    cor: Color = Color.Unspecified,
) {
    val medidor = rememberTextMeasurer()
    BoxWithConstraints(modifier = modifier, contentAlignment = Alignment.Center) {
        val largura = constraints.maxWidth
        val altura = constraints.maxHeight
        val ajuste = remember(texto, largura, altura, tamanhoMaximo, tamanhoMinimo) {
            ajustar(texto, medidor, largura, altura, tamanhoMaximo, tamanhoMinimo)
        }
        Text(
            text = texto,
            fontSize = ajuste.tamanho,
            maxLines = ajuste.linhas,
            softWrap = ajuste.linhas > 1,
            overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.Center,
            color = cor,
        )
    }
}

private class Ajuste(val tamanho: TextUnit, val linhas: Int)

private fun ajustar(
    texto: String,
    medidor: TextMeasurer,
    largura: Int,
    altura: Int,
    maximo: TextUnit,
    minimo: TextUnit,
): Ajuste {
    if (largura == Constraints.Infinity || altura == Constraints.Infinity) return Ajuste(maximo, 1)
    var tamanho = maximo.value
    while (tamanho >= minimo.value) {
        val medido: TextLayoutResult = medidor.measure(
            text = texto,
            style = TextStyle(fontSize = tamanho.sp),
            maxLines = 1,
        )
        if (medido.size.width <= largura && medido.size.height <= altura) {
            return Ajuste(tamanho.sp, 1)
        }
        tamanho -= 1f
    }
    return Ajuste(minimo, 2)
}
