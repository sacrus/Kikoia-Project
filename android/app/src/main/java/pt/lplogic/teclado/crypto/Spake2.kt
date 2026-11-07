package pt.lplogic.teclado.crypto

import java.math.BigInteger
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/** Ponto em coordenadas estendidas: [X, Y, Z, T]. */
typealias Ponto = Array<BigInteger>

/**
 * SPAKE2 (lado A) com Ed25519, igual a biblioteca Python `spake2` 0.9 usada pelo PC.
 *
 * Os parametros (M, N, derivacao da palavra-passe) seguem o codigo fonte dessa biblioteca,
 * e os vetores de teste em Spake2Test garantem que os dois lados chegam a mesma chave.
 *
 * Nota: a aritmetica usa BigInteger e nao e de tempo constante. Aceitavel para um codigo
 * de emparelhamento de uso unico; reavaliar se o protocolo for alargado.
 */
object Ed25519 {
    private val DOIS = BigInteger.valueOf(2)
    private val UM = BigInteger.ONE
    val P: BigInteger = DOIS.pow(255).subtract(BigInteger.valueOf(19))
    val L: BigInteger = DOIS.pow(252).add(BigInteger("27742317777372353535851937790883648493"))
    private val QUATRO = BigInteger.valueOf(4)
    private val OITO = BigInteger.valueOf(8)

    private fun m(a: BigInteger): BigInteger = a.mod(P)
    private fun inv(x: BigInteger): BigInteger = x.modPow(P.subtract(DOIS), P)

    val D: BigInteger = m(BigInteger.valueOf(-121665).multiply(inv(BigInteger.valueOf(121666))))
    private val I: BigInteger = DOIS.modPow(P.subtract(UM).divide(QUATRO), P)

    private fun xrecover(y: BigInteger): BigInteger {
        val yy = y.multiply(y)
        val xx = m(yy.subtract(UM)).multiply(inv(m(D.multiply(yy).add(UM))))
        var x = xx.modPow(P.add(BigInteger.valueOf(3)).divide(OITO), P)
        if (m(x.multiply(x).subtract(xx)).signum() != 0) x = m(x.multiply(I))
        if (x.testBit(0)) x = P.subtract(x)
        return x
    }

    private val BY: BigInteger = m(QUATRO.multiply(inv(BigInteger.valueOf(5))))
    private val BX: BigInteger = xrecover(BY)

    val IDENTIDADE: Ponto = arrayOf(BigInteger.ZERO, UM, UM, BigInteger.ZERO)
    val BASE: Ponto = afim(BX, BY)

    private fun afim(x: BigInteger, y: BigInteger): Ponto =
        arrayOf(m(x), m(y), UM, m(x.multiply(y)))

    fun soma(p1: Ponto, p2: Ponto): Ponto {
        val a = m(p1[1].subtract(p1[0]).multiply(p2[1].subtract(p2[0])))
        val b = m(p1[1].add(p1[0]).multiply(p2[1].add(p2[0])))
        val c = m(p1[3].multiply(DOIS).multiply(D).multiply(p2[3]))
        val d = m(p1[2].multiply(DOIS).multiply(p2[2]))
        val e = m(b.subtract(a))
        val f = m(d.subtract(c))
        val g = m(d.add(c))
        val h = m(b.add(a))
        return arrayOf(m(e.multiply(f)), m(g.multiply(h)), m(f.multiply(g)), m(e.multiply(h)))
    }

    fun mul(p: Ponto, escalar: BigInteger): Ponto {
        require(escalar.signum() >= 0) { "escalar negativo" }
        var resultado = IDENTIDADE
        var base = p
        for (i in 0 until escalar.bitLength()) {
            if (escalar.testBit(i)) resultado = soma(resultado, base)
            base = soma(base, base)
        }
        return resultado
    }

    private fun afimDe(p: Ponto): Pair<BigInteger, BigInteger> {
        val zInv = inv(p[2])
        return Pair(m(p[0].multiply(zInv)), m(p[1].multiply(zInv)))
    }

    fun codificar(p: Ponto): ByteArray {
        val (x, y) = afimDe(p)
        val valor = if (x.testBit(0)) y.add(DOIS.pow(255)) else y
        val bruto = valor.toByteArray()
        val le = ByteArray(32)
        for (i in 0 until minOf(32, bruto.size)) le[i] = bruto[bruto.size - 1 - i]
        return le
    }

    fun decodificar(bytes: ByteArray): Ponto {
        require(bytes.size == 32) { "elemento com tamanho errado" }
        val be = ByteArray(32) { bytes[31 - it] }
        val sem = BigInteger(1, be)
        val y = sem.and(DOIS.pow(255).subtract(UM))
        var x = xrecover(y)
        if (x.testBit(0) != sem.testBit(255)) x = P.subtract(x)
        if (!naCurva(x, y)) throw IllegalArgumentException("ponto fora da curva")
        return afim(x, y)
    }

    private fun naCurva(x: BigInteger, y: BigInteger): Boolean {
        val xx = x.multiply(x)
        val yy = y.multiply(y)
        val r = yy.subtract(xx).subtract(UM).subtract(D.multiply(xx).multiply(yy))
        return m(r).signum() == 0
    }

    fun ehIdentidade(p: Ponto): Boolean =
        codificar(p).contentEquals(codificar(IDENTIDADE))

    /** Elemento do grupo principal (ordem L), como bytes_to_element() do Python. */
    fun elementoValido(bytes: ByteArray): Ponto {
        val p = decodificar(bytes)
        require(!ehIdentidade(p)) { "elemento zero" }
        require(ehIdentidade(mul(p, L))) { "elemento fora do grupo" }
        return p
    }

    /** Elemento arbitrario sem logaritmo conhecido, como arbitrary_element() do Python. */
    fun elementoArbitrario(semente: ByteArray): Ponto {
        val hseed = hkdf(semente, "SPAKE2 arbitrary element".toByteArray(Charsets.UTF_8), 48)
        val y = BigInteger(1, hseed).mod(P)
        var mais = 0
        while (true) {
            val yp = m(y.add(BigInteger.valueOf(mais.toLong())))
            mais++
            val x = xrecover(yp)
            if (!naCurva(x, yp)) continue
            val p8 = mul(afim(x, yp), OITO)
            if (ehIdentidade(p8)) continue
            return p8
        }
    }

    /** Escalar a partir da palavra-passe, como password_to_scalar() do Python. */
    fun escalarDaSenha(senha: ByteArray): BigInteger {
        val sobredimensionado = hkdf(senha, "SPAKE2 pw".toByteArray(Charsets.UTF_8), 48)
        return BigInteger(1, sobredimensionado).mod(L)
    }

    fun escalarAleatorio(random: SecureRandom = SecureRandom()): BigInteger {
        val bytes = ByteArray(64)
        random.nextBytes(bytes)
        return BigInteger(1, bytes).mod(L)
    }

    private fun hmac(chave: ByteArray, dados: ByteArray): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(if (chave.isEmpty()) ByteArray(32) else chave, "HmacSHA256"))
        return mac.doFinal(dados)
    }

    /** HKDF-SHA256 com sal vazio, como cryptography.hazmat HKDF no Python. */
    fun hkdf(ikm: ByteArray, info: ByteArray, tamanho: Int): ByteArray {
        val prk = hmac(ByteArray(32), ikm)
        val saida = ByteArray(tamanho)
        var anterior = ByteArray(0)
        var pos = 0
        var contador = 1
        while (pos < tamanho) {
            anterior = hmac(prk, anterior + info + byteArrayOf(contador.toByte()))
            val copia = minOf(anterior.size, tamanho - pos)
            System.arraycopy(anterior, 0, saida, pos, copia)
            pos += copia
            contador++
        }
        return saida
    }

    fun sha256(vararg partes: ByteArray): ByteArray {
        val md = MessageDigest.getInstance("SHA-256")
        partes.forEach { md.update(it) }
        return md.digest()
    }

    /** Parametros fixos do protocolo (sementes publicas, como em params.py). */
    val M: Ponto by lazy { elementoArbitrario("M".toByteArray()) }
    val N: Ponto by lazy { elementoArbitrario("N".toByteArray()) }
}

/** Lado A do SPAKE2. O lado PC e o B. */
class Spake2A(
    private val senha: ByteArray,
    private val idA: ByteArray,
    private val idB: ByteArray,
    private val xy: BigInteger = Ed25519.escalarAleatorio(),
) {
    private val escalarSenha = Ed25519.escalarDaSenha(senha)
    private val mensagemSaida: ByteArray =
        Ed25519.codificar(Ed25519.soma(Ed25519.mul(Ed25519.BASE, xy), Ed25519.mul(Ed25519.M, escalarSenha)))

    /** Primeira mensagem, com o byte de lado 'A' a frente (como no Python). */
    fun iniciar(): ByteArray = byteArrayOf('A'.code.toByte()) + mensagemSaida

    /** Recebe a resposta do PC ('B' + mensagem) e devolve a chave partilhada de 32 bytes. */
    fun terminar(mensagemComLado: ByteArray): ByteArray {
        require(mensagemComLado.isNotEmpty() && mensagemComLado[0] == 'B'.code.toByte()) { "lado inesperado" }
        val mensagem = mensagemComLado.copyOfRange(1, mensagemComLado.size)
        require(!mensagem.contentEquals(mensagemSaida)) { "mensagem refletida" }
        val y = Ed25519.elementoValido(mensagem)
        val desbloqueio = Ed25519.mul(Ed25519.N, Ed25519.L.subtract(escalarSenha).mod(Ed25519.L))
        val kElem = Ed25519.mul(Ed25519.soma(y, desbloqueio), xy)
        val k = Ed25519.codificar(kElem)
        return Ed25519.sha256(
            Ed25519.sha256(senha),
            Ed25519.sha256(idA),
            Ed25519.sha256(idB),
            mensagemSaida,
            mensagem,
            k,
        )
    }
}
