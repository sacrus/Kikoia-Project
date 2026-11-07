package pt.lplogic.teclado

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import pt.lplogic.teclado.rede.Atualizacao

class AtualizacaoTest {

    @Test
    fun versaoTuplaIgnoraPrefixoEComparaNumericamente() {
        assertEquals(listOf(1, 10, 0), Atualizacao.versaoTupla("v1.10.0"))
        assertEquals(listOf(0), Atualizacao.versaoTupla("sem-numeros"))
    }

    @Test
    fun versaoMaisRecenteEDetetada() {
        assertTrue(Atualizacao.e_mais_recente("v0.2.0", atual = "0.1.0"))
        assertTrue(Atualizacao.e_mais_recente("1.10.0", atual = "1.9.0"))
        assertTrue(Atualizacao.e_mais_recente("1.0", atual = "0.1.0"))
    }

    @Test
    fun mesmaVersaoOuAnteriorNaoAvisa() {
        assertFalse(Atualizacao.e_mais_recente("v0.1.0", atual = "0.1.0"))
        assertFalse(Atualizacao.e_mais_recente("0.0.9", atual = "0.1.0"))
        assertFalse(Atualizacao.e_mais_recente("1.9.0", atual = "1.10.0"))
    }
}
