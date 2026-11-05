package pt.lplogic.teclado

import android.app.Application

/** Guarda o contexto da app para textos usados fora das telas (ligacoes, erros). */
class TecladoApp : Application() {
    override fun onCreate() {
        super.onCreate()
        instancia = this
    }

    companion object {
        lateinit var instancia: TecladoApp
            private set
    }
}

/** Texto de recurso no idioma do telemovel (values, values-en, values-es, values-fr). */
fun recurso(id: Int, vararg argumentos: Any): String = TecladoApp.instancia.getString(id, *argumentos)
