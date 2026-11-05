package pt.lplogic.teclado.modelo

/** Acoes da janela do PC. Nao sao permitidas remotamente, por isso nao sao mostradas no telemovel. */
val ACOES_DE_JANELA = setOf("minimizar_teclado", "fechar_janela", "minimizar_janela", "maximizar_janela")

data class Tecla(
    val rotulo: String,
    val tipo: String,
    val valor: String,
    val largura: Double,
)

data class Teclado(
    val nome: String,
    val linhas: List<List<Tecla>>,
)

/** Converte o mapa recebido do PC num teclado utilizavel no telemovel. */
fun teclado(dados: Map<*, *>): Teclado {
    val nome = dados["nome"] as? String ?: "Teclado"
    val linhasBrutas = dados["linhas"] as? List<*> ?: emptyList<Any>()
    val linhas = linhasBrutas.mapNotNull { linha ->
        val teclas = (linha as? List<*>)?.mapNotNull { tecla -> tecla as? Map<*, *> }?.mapNotNull(::tecla)
        teclas?.takeIf { it.isNotEmpty() }
    }
    return Teclado(nome, linhas)
}

private fun tecla(dados: Map<*, *>): Tecla? {
    val rotulo = dados["rotulo"] as? String ?: return null
    val acao = dados["acao"] as? Map<*, *> ?: return null
    val tipo = acao["tipo"] as? String ?: return null
    val valor = acao["valor"] as? String ?: return null
    if (tipo == "acao" && valor in ACOES_DE_JANELA) return null
    val largura = (dados["largura"] as? Number)?.toDouble() ?: 1.0
    return Tecla(rotulo, tipo, valor, largura)
}
