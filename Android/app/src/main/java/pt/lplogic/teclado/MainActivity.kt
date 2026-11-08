package pt.lplogic.teclado

import android.Manifest
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import android.bluetooth.BluetoothDevice
import android.content.SharedPreferences
import android.content.res.Configuration
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import android.content.Intent
import android.net.Uri
import pt.lplogic.teclado.rede.Atualizacao
import pt.lplogic.teclado.modelo.Teclado
import pt.lplogic.teclado.rede.Confianca
import pt.lplogic.teclado.rede.Confiancas
import pt.lplogic.teclado.rede.ComputadorEncontrado
import pt.lplogic.teclado.rede.LigacaoGateway
import pt.lplogic.teclado.rede.OuvinteGateway
import pt.lplogic.teclado.rede.TransporteBluetooth
import pt.lplogic.teclado.rede.TransporteWifi
import pt.lplogic.teclado.rede.dispositivosBluetoothEmparelhados
import pt.lplogic.teclado.rede.procurarComputadores

class MainActivity : ComponentActivity() {
    private lateinit var preferencias: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // O teclado e um controlo: o ecra fica sempre ligado enquanto a app esta aberta.
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        preferencias = getSharedPreferences("config", MODE_PRIVATE)
        setContent {
            // Tema: "claro", "escuro" ou "sistema" (segue o aparelho). Guardado no aparelho.
            var tema by remember { mutableStateOf(preferencias.getString("tema", "sistema") ?: "sistema") }
            val escuro = when (tema) {
                "escuro" -> true
                "claro" -> false
                else -> isSystemInDarkTheme()
            }
            MaterialTheme(colorScheme = if (escuro) darkColorScheme() else lightColorScheme()) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AppTeclado(
                        preferencias = preferencias,
                        escuro = escuro,
                        onAlternarTema = {
                            val novo = if (escuro) "claro" else "escuro"
                            preferencias.edit().putString("tema", novo).apply()
                            tema = novo
                        },
                    )
                }
            }
        }
        esconderBarrasDoSistema()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) esconderBarrasDoSistema()
    }

    /** Ecra completo: esconde a barra de estado e a de navegacao (aparecem ao deslizar). */
    private fun esconderBarrasDoSistema() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, window.decorView).apply {
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            hide(WindowInsetsCompat.Type.systemBars())
        }
    }
}

private enum class Tela { PERMISSOES, PROCURAR, CODIGO, TECLADO }

/** Permissoes pedidas na primeira utilizacao: rede local (Android 13+) e Bluetooth (Android 12+). */
private fun permissoesNecessarias(): Array<String> {
    val lista = mutableListOf<String>()
    if (Build.VERSION.SDK_INT >= 33) lista += Manifest.permission.NEARBY_WIFI_DEVICES
    if (Build.VERSION.SDK_INT >= 31) lista += Manifest.permission.BLUETOOTH_CONNECT
    return lista.toTypedArray()
}

/** Um destino de ligacao: nome para mostrar e a forma de arrancar o transporte. */
private class Destino(val nome: String, val endereco: String?, val arrancar: (LigacaoGateway) -> Unit)

/** Reconexao: 2 s, 4 s, 8 s, 16 s e depois 30 s entre tentativas; ao fim de ~10 min desiste. */
private const val MAX_TENTATIVAS_RECONEXAO = 20

private fun atrasoReconexao(tentativa: Int): Long = minOf(30_000L, 2_000L shl (tentativa - 1).coerceAtMost(4))

/** Prefixo da chave de confianca dos computadores ligados por Wi-Fi (o nome identifica o computador). */
private const val PREFIXO_WIFI = "wifi:"

@Composable
fun AppTeclado(preferencias: SharedPreferences, escuro: Boolean, onAlternarTema: () -> Unit) {
    val contexto = LocalContext.current
    val principal = remember { Handler(Looper.getMainLooper()) }
    val escopo = rememberCoroutineScope()

    var tela by remember {
        mutableStateOf(if (preferencias.getBoolean("permissoes_pedidas", false)) Tela.PROCURAR else Tela.PERMISSOES)
    }
    var computadores by remember { mutableStateOf<List<ComputadorEncontrado>>(emptyList()) }
    var procurou by remember { mutableStateOf(false) }
    var aProcurar by remember { mutableStateOf(false) }
    var destino by remember { mutableStateOf<Destino?>(null) }
    val dispositivosBt = remember { mutableStateListOf<BluetoothDevice>() }
    var codigo by remember { mutableStateOf("") }
    var ligacao by remember { mutableStateOf<LigacaoGateway?>(null) }
    // Reconexao automatica de uma ligacao de confianca que caiu (tentativas com espera crescente).
    var reconectando by remember { mutableStateOf(false) }
    var tentativasReconexao by remember { mutableStateOf(0) }
    var trabalhoReconexao by remember { mutableStateOf<Job?>(null) }
    var estado by remember { mutableStateOf("") }
    var erro by remember { mutableStateOf<String?>(null) }
    // Teclado e sugestoes sao sempre os que o computador envia (nao ha escolha local).
    var teclado by remember { mutableStateOf<Teclado?>(null) }
    var sugestoes by remember { mutableStateOf<List<String>>(emptyList()) }
    // Sugestoes: mostrar ou ocultar a faixa no telemovel (escolha local). Falar e Ditar: estado do PC.
    var sugestoesAtivas by remember { mutableStateOf(preferencias.getBoolean("sugestoes_ativas", true)) }
    var interruptores by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    // Verificacao de atualizacoes: uma vez ao abrir a app, se estiver ativa. So avisa.
    var verificarAtualizacoes by remember { mutableStateOf(preferencias.getBoolean("verificar_atualizacoes", true)) }
    var atualizacao by remember { mutableStateOf<Atualizacao.Nova?>(null) }
    var avisoAtualizacaoFechado by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        if (verificarAtualizacoes) atualizacao = withContext(Dispatchers.IO) { Atualizacao.verificar() }
    }

    val pedirPermissoes = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        preferencias.edit().putBoolean("permissoes_pedidas", true).apply()
        tela = Tela.PROCURAR
    }

    // Reconexao (ver ouvinte): atribuida depois de iniciarLigacao existir.
    var reconectarDestino: (Destino) -> Unit = {}

    fun pararReconexao() {
        trabalhoReconexao?.cancel()
        trabalhoReconexao = null
        reconectando = false
        tentativasReconexao = 0
    }

    fun ouvinte(endereco: String?) = object : OuvinteGateway {
        override fun aoEstado(texto: String) {
            principal.post { estado = texto }
        }

        override fun aoLigar() {
            principal.post {
                erro = null
                reconectando = false
                tentativasReconexao = 0
                tela = Tela.TECLADO
            }
        }

        override fun aoTeclado(teclado_: Teclado) {
            principal.post { teclado = teclado_ }
        }

        override fun aoSugestoes(palavras: List<String>) {
            principal.post { sugestoes = palavras }
        }

        override fun aoInterruptores(estado: Map<String, Any?>) {
            principal.post { interruptores = estado }
        }

        override fun aoFechar(motivo: String?) {
            principal.post {
                val d = destino
                ligacao = null
                estado = ""
                // Ligacao de confianca que estava ativa (ou a reconectar) cai: tenta de novo, sem codigo.
                val deveReconectar = endereco != null && d != null && d.endereco == endereco &&
                    Confiancas.ler(preferencias, endereco) != null &&
                    (tela == Tela.TECLADO || reconectando)
                if (deveReconectar && tentativasReconexao < MAX_TENTATIVAS_RECONEXAO) {
                    reconectando = true
                    tentativasReconexao += 1
                    erro = null
                    trabalhoReconexao?.cancel()
                    trabalhoReconexao = escopo.launch {
                        delay(atrasoReconexao(tentativasReconexao))
                        reconectarDestino(d!!)
                    }
                } else {
                    pararReconexao()
                    erro = motivo
                    if (tela == Tela.TECLADO) tela = Tela.PROCURAR
                }
            }
        }

        override fun aoConfiar(confianca: Confianca) {
            endereco?.let { Confiancas.guardar(preferencias, it, confianca) }
        }

        override fun aoPerderConfianca() {
            endereco?.let { Confiancas.esquecer(preferencias, it) }
            principal.post {
                ligacao = null
                estado = ""
                codigo = ""
                erro = recurso(R.string.and_perdeu_confianca)
                tela = Tela.CODIGO
            }
        }
    }

    // Com confianca liga sem codigo; sem ela usa o codigo de 6 digitos do computador.
    fun iniciarLigacao(d: Destino, digitos: String?, confianca: Confianca?) {
        erro = null
        estado = recurso(R.string.and_ligar)
        val nova = LigacaoGateway(d.nome, digitos, confianca, ouvinte(d.endereco))
        ligacao = nova
        d.arrancar(nova)
    }
    reconectarDestino = { d -> iniciarLigacao(d, null, d.endereco?.let { Confiancas.ler(preferencias, it) }) }

    // Tudo o que se carrega no telemovel vai para o computador, que decide e devolve o estado.
    // Mudar de teclado ("navegar") tambem e feito no computador, que envia o novo teclado.
    fun premirTecla(tipo: String, valor: String) {
        ligacao?.enviarAcao(tipo, valor)
    }

    fun escolherSugestao(indice: Int) {
        ligacao?.escolherSugestao(indice)
    }

    fun ligar() {
        val d = destino ?: return
        val digitos = codigo.filter { it.isDigit() }
        if (digitos.length != 6) {
            erro = recurso(R.string.and_codigo_6)
            return
        }
        iniciarLigacao(d, digitos, null)
    }

    // Ao abrir a app, um computador de confianca liga-se sozinho (sem codigo).
    LaunchedEffect(Unit) {
        val ultimo = Confiancas.ultimo(preferencias) ?: return@LaunchedEffect
        val confianca = Confiancas.ler(preferencias, ultimo) ?: return@LaunchedEffect
        if (tela != Tela.PROCURAR) return@LaunchedEffect
        if (ultimo.startsWith(PREFIXO_WIFI)) {
            val nome = ultimo.removePrefix(PREFIXO_WIFI)
            val computador = procurarComputadores().firstOrNull { it.nome == nome } ?: return@LaunchedEffect
            val d = Destino(computador.nome, ultimo) { lig -> TransporteWifi(computador, lig).ligar() }
            destino = d
            iniciarLigacao(d, null, confianca)
            return@LaunchedEffect
        }
        val dispositivo = dispositivosBluetoothEmparelhados(contexto).firstOrNull { it.address == ultimo }
            ?: return@LaunchedEffect
        val d = Destino(dispositivo.name ?: recurso(R.string.and_computador), ultimo) { lig ->
            TransporteBluetooth(dispositivo, lig).ligar()
        }
        destino = d
        iniciarLigacao(d, null, confianca)
    }

    when (tela) {
        Tela.PERMISSOES -> EcraPermissoes(onContinuar = {
            val pedir = permissoesNecessarias().filter {
                ContextCompat.checkSelfPermission(contexto, it) != android.content.pm.PackageManager.PERMISSION_GRANTED
            }
            if (pedir.isEmpty()) {
                preferencias.edit().putBoolean("permissoes_pedidas", true).apply()
                tela = Tela.PROCURAR
            } else {
                pedirPermissoes.launch(pedir.toTypedArray())
            }
        })

        Tela.PROCURAR -> EcraProcurar(
            computadores = computadores,
            procurou = procurou,
            aProcurar = aProcurar,
            erro = erro,
            dispositivosBt = dispositivosBt,
            onAtualizarBt = {
                dispositivosBt.clear()
                dispositivosBt.addAll(dispositivosBluetoothEmparelhados(contexto))
            },
            onProcurar = {
                aProcurar = true
                escopo.launch {
                    computadores = procurarComputadores()
                    procurou = true
                    aProcurar = false
                }
            },
            onEscolher = {
                val chave = PREFIXO_WIFI + it.nome
                val d = Destino(it.nome, chave) { lig -> TransporteWifi(it, lig).ligar() }
                destino = d
                codigo = ""
                val confianca = Confiancas.ler(preferencias, chave)
                if (confianca != null) {
                    iniciarLigacao(d, null, confianca)
                } else {
                    erro = null
                    tela = Tela.CODIGO
                }
            },
            atualizacao = if (avisoAtualizacaoFechado) null else atualizacao,
            onVerAtualizacao = {
                atualizacao?.pagina?.takeIf { it.isNotEmpty() }?.let { url ->
                    contexto.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                }
            },
            onFecharAtualizacao = { avisoAtualizacaoFechado = true },
            verificarAtualizacoes = verificarAtualizacoes,
            onAlternarVerificacao = {
                verificarAtualizacoes = !verificarAtualizacoes
                preferencias.edit().putBoolean("verificar_atualizacoes", verificarAtualizacoes).apply()
            },
            onEscolherBt = { dispositivo ->
                val d = Destino(dispositivo.name ?: recurso(R.string.and_computador), dispositivo.address) { lig ->
                    TransporteBluetooth(dispositivo, lig).ligar()
                }
                destino = d
                codigo = ""
                val confianca = Confiancas.ler(preferencias, dispositivo.address)
                if (confianca != null) {
                    iniciarLigacao(d, null, confianca)
                } else {
                    erro = null
                    tela = Tela.CODIGO
                }
            },
        )

        Tela.CODIGO -> EcraCodigo(
            nomeDestino = destino?.nome ?: "",
            codigo = codigo,
            onCodigo = { codigo = it.filter { c -> c.isDigit() }.take(6) },
            estado = estado,
            erro = erro,
            aLigar = ligacao != null,
            onEmparelhar = ::ligar,
            onVoltar = { tela = Tela.PROCURAR },
        )

        Tela.TECLADO -> EcraTeclado(
            nomeComputador = (destino?.nome ?: "") +
                if (reconectando) " · " + recurso(R.string.and_reconectando) else "",
            teclado = teclado,
            sugestoes = sugestoes,
            onSugestao = ::escolherSugestao,
            sugestoesAtivas = sugestoesAtivas,
            onAlternarSugestoes = {
                sugestoesAtivas = !sugestoesAtivas
                preferencias.edit().putBoolean("sugestoes_ativas", sugestoesAtivas).apply()
            },
            interruptores = interruptores,
            onAlternarInterruptor = { nome, ligado -> ligacao?.alternarInterruptor(nome, ligado) },
            escuro = escuro,
            onAlternarTema = onAlternarTema,
            onTecla = ::premirTecla,
            onDesligar = {
                pararReconexao()
                ligacao?.fechar()
                ligacao = null
                tela = Tela.PROCURAR
            },
        )
    }
}

@Composable
private fun AvisoHorizontal(visivel: Boolean, onFechar: () -> Unit) {
    val emPe = LocalConfiguration.current.orientation == Configuration.ORIENTATION_PORTRAIT
    if (!visivel || !emPe) return
    Card(modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp)) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                recurso(R.string.and_dica_horizontal),
                modifier = Modifier.weight(1f),
                fontSize = 15.sp,
            )
            TextButton(onClick = onFechar) { Text("OK") }
        }
    }
}

@Composable
private fun EcraPermissoes(onContinuar: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(recurso(R.string.app_name), fontSize = 30.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(16.dp))
        Text(
            recurso(R.string.and_boas_1) +
                recurso(R.string.and_boas_2),
            fontSize = 18.sp,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            recurso(R.string.and_perm_1) +
                recurso(R.string.and_perm_2),
            fontSize = 18.sp,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            recurso(R.string.and_sugestao),
            fontSize = 18.sp,
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(Modifier.height(24.dp))
        Button(onClick = onContinuar, modifier = Modifier.fillMaxWidth().height(56.dp)) {
            Text(recurso(R.string.and_continuar), fontSize = 20.sp)
        }
    }
}

@Composable
private fun EcraProcurar(
    computadores: List<ComputadorEncontrado>,
    procurou: Boolean,
    aProcurar: Boolean,
    erro: String?,
    dispositivosBt: List<BluetoothDevice>,
    onAtualizarBt: () -> Unit,
    onProcurar: () -> Unit,
    onEscolher: (ComputadorEncontrado) -> Unit,
    onEscolherBt: (BluetoothDevice) -> Unit,
    atualizacao: Atualizacao.Nova?,
    onVerAtualizacao: () -> Unit,
    onFecharAtualizacao: () -> Unit,
    verificarAtualizacoes: Boolean,
    onAlternarVerificacao: () -> Unit,
) {
    var avisoVisto by remember { mutableStateOf(false) }
    var mostrarAvisoWifi by remember { mutableStateOf(false) }
    val contexto = LocalContext.current
    if (mostrarAvisoWifi) {
        AlertDialog(
            onDismissRequest = { mostrarAvisoWifi = false },
            text = { Text(recurso(R.string.and_wifi_aviso), fontSize = 16.sp) },
            confirmButton = {
                TextButton(onClick = { mostrarAvisoWifi = false; onProcurar() }) {
                    Text(recurso(R.string.and_continuar))
                }
            },
            dismissButton = {
                TextButton(onClick = { mostrarAvisoWifi = false }) { Text(recurso(R.string.and_cancelar)) }
            },
        )
    }
    Column(modifier = Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState())) {
        AvisoHorizontal(visivel = !avisoVisto, onFechar = { avisoVisto = true })
        if (atualizacao != null) {
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                Text(
                    recurso(R.string.and_atualizacao_nova, atualizacao.versao),
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                )
                TextButton(onClick = onVerAtualizacao) { Text(recurso(R.string.and_ver_versao), fontSize = 15.sp) }
                TextButton(onClick = onFecharAtualizacao) { Text("✕", fontSize = 15.sp) }
            }
        }
        TextButton(onClick = onAlternarVerificacao) {
            Text(
                recurso(if (verificarAtualizacoes) R.string.and_atualizacoes_on else R.string.and_atualizacoes_off),
                fontSize = 14.sp,
            )
        }
        Text(recurso(R.string.and_escolha), fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(12.dp))
        if (erro != null) {
            Text(erro, color = MaterialTheme.colorScheme.error, fontSize = 16.sp)
            Spacer(Modifier.height(8.dp))
        }

        // Bluetooth primeiro: e o caminho recomendado. Wi-Fi so como alternativa.
        Text(recurso(R.string.and_bt_rotulo), fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(6.dp))
        OutlinedButton(onClick = onAtualizarBt, modifier = Modifier.fillMaxWidth().height(48.dp)) {
            Text(recurso(R.string.and_atualizar_lista), fontSize = 18.sp)
        }
        Spacer(Modifier.height(6.dp))
        if (dispositivosBt.isEmpty()) {
            Text(
                recurso(R.string.and_nenhum_bt_1) +
                    recurso(R.string.and_nenhum_bt_2),
                fontSize = 16.sp,
            )
        }
        dispositivosBt.forEach { dispositivo ->
            OutlinedButton(
                onClick = { onEscolherBt(dispositivo) },
                modifier = Modifier.fillMaxWidth().height(64.dp).padding(vertical = 4.dp),
            ) {
                Text(dispositivo.name ?: recurso(R.string.and_computador), fontSize = 20.sp)
            }
        }

        Spacer(Modifier.height(20.dp))
        Text(recurso(R.string.and_wifi_rotulo), fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(6.dp))
        Button(
            onClick = { mostrarAvisoWifi = true },
            enabled = !aProcurar,
            modifier = Modifier.fillMaxWidth().height(56.dp),
        ) {
            if (aProcurar) {
                CircularProgressIndicator(modifier = Modifier.height(24.dp), strokeWidth = 2.dp)
                Spacer(Modifier.width(12.dp))
            }
            Text(if (aProcurar) recurso(R.string.and_procurando) else recurso(R.string.and_procurar), fontSize = 20.sp)
        }
        Spacer(Modifier.height(8.dp))
        if (procurou && computadores.isEmpty()) {
            Text(
                recurso(R.string.and_nenhum_wifi_1) +
                    recurso(R.string.and_nenhum_wifi_2),
                fontSize = 16.sp,
            )
        }
        computadores.forEach { pc ->
            OutlinedButton(
                onClick = { onEscolher(pc) },
                modifier = Modifier.fillMaxWidth().height(64.dp).padding(vertical = 4.dp),
            ) {
                Text(pc.nome, fontSize = 20.sp)
            }
        }

        Spacer(Modifier.height(24.dp))
        Text(
            "Versão ${Atualizacao.VERSAO} · Projeto Desenvolvido por: Luís Patrício",
            fontSize = 13.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        TextButton(onClick = {
            contexto.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.lplogic.net")))
        }) {
            Text("www.lplogic.net", fontSize = 13.sp)
        }
    }
}

@Composable
private fun EcraCodigo(
    nomeDestino: String,
    codigo: String,
    onCodigo: (String) -> Unit,
    estado: String,
    erro: String?,
    aLigar: Boolean,
    onEmparelhar: () -> Unit,
    onVoltar: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState())) {
        Text(
            recurso(R.string.and_emparelhar_com, nomeDestino.ifEmpty { recurso(R.string.and_o_computador) }),
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            recurso(R.string.and_escreva_1) +
                recurso(R.string.and_escreva_2),
            fontSize = 17.sp,
        )
        Spacer(Modifier.height(16.dp))
        OutlinedTextField(
            value = codigo,
            onValueChange = onCodigo,
            label = { Text(recurso(R.string.and_codigo_rotulo)) },
            singleLine = true,
            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 28.sp, fontWeight = FontWeight.Bold),
        )
        Spacer(Modifier.height(16.dp))
        if (erro != null) {
            Text(erro, color = MaterialTheme.colorScheme.error, fontSize = 17.sp)
            Spacer(Modifier.height(8.dp))
        }
        if (estado.isNotEmpty()) {
            Text(estado, fontSize = 17.sp)
            Spacer(Modifier.height(8.dp))
        }
        Button(
            onClick = onEmparelhar,
            enabled = !aLigar && codigo.length == 6,
            modifier = Modifier.fillMaxWidth().height(56.dp),
        ) {
            Text(recurso(R.string.and_emparelhar), fontSize = 20.sp)
        }
        Spacer(Modifier.height(8.dp))
        TextButton(onClick = onVoltar) { Text(recurso(R.string.and_voltar), fontSize = 18.sp) }
    }
}

/**
 * Ecra do teclado: so o teclado ativo do computador, em quase todo o ecra.
 * Cabecalho minimo, faixa de sugestoes (quando houver) e teclas que ocupam todo o espaco.
 */
/** Interruptor pequeno do cabecalho: cinzento quando desligado, colorido quando ligado. */
@Composable
private fun IconeAlternar(
    simbolo: String,
    ativo: Boolean,
    habilitado: Boolean,
    descricao: String,
    onClick: () -> Unit,
) {
    TextButton(
        onClick = onClick,
        enabled = habilitado,
        contentPadding = PaddingValues(horizontal = 6.dp),
        modifier = Modifier.semantics { contentDescription = descricao },
    ) {
        Text(
            simbolo,
            fontSize = 16.sp,
            color = if (ativo) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
        )
    }
}

@Composable
private fun EcraTeclado(
    nomeComputador: String,
    teclado: Teclado?,
    sugestoes: List<String>,
    onSugestao: (Int) -> Unit,
    sugestoesAtivas: Boolean,
    onAlternarSugestoes: () -> Unit,
    interruptores: Map<String, Any?>,
    onAlternarInterruptor: (nome: String, ligado: Boolean) -> Unit,
    onTecla: (tipo: String, valor: String) -> Unit,
    onDesligar: () -> Unit,
    escuro: Boolean,
    onAlternarTema: () -> Unit,
) {
    val falar = interruptores["falar"] == true
    val falarDisponivel = interruptores["falar_disponivel"] == true
    val ditar = interruptores["ditar"] == true
    val ditarDisponivel = interruptores["ditar_disponivel"] == true
    Column(
        modifier = Modifier.fillMaxSize().padding(4.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth().height(36.dp),
        ) {
            Text(
                "● $nomeComputador",
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                modifier = Modifier.weight(1f),
            )
            // Interruptores pequenos: sugestoes (local), falar e ditar (no computador).
            IconeAlternar("💬", ativo = sugestoesAtivas, habilitado = true, descricao = recurso(R.string.and_sugestoes), onClick = onAlternarSugestoes)
            IconeAlternar("🔊", ativo = falar, habilitado = falarDisponivel, descricao = recurso(R.string.and_falar)) {
                onAlternarInterruptor("falar", !falar)
            }
            IconeAlternar("🎤", ativo = ditar, habilitado = ditarDisponivel, descricao = recurso(R.string.and_ditar)) {
                onAlternarInterruptor("ditar", !ditar)
            }
            // Sol/lua: alterna o tema, discreto no cabecalho.
            TextButton(onClick = onAlternarTema) {
                Text(if (escuro) "☀" else "☾", fontSize = 18.sp)
            }
            TextButton(onClick = onDesligar) { Text(recurso(R.string.and_desligar), fontSize = 13.sp) }
        }

        // A faixa ocupa sempre o mesmo espaco enquanto as sugestoes estiverem ativas, mesmo sem palavras:
        // assim o teclado nao sobe nem desce quando as sugestoes aparecem ou desaparecem.
        if (sugestoesAtivas) {
            Row(
                modifier = Modifier.fillMaxWidth().height(56.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                sugestoes.forEachIndexed { i, palavra ->
                    OutlinedButton(
                        onClick = { onSugestao(i) },
                        modifier = Modifier.weight(1f).fillMaxHeight(),
                        contentPadding = PaddingValues(2.dp),
                    ) {
                        TextoAdaptavel(palavra, tamanhoMaximo = 18.sp, tamanhoMinimo = 9.sp)
                    }
                }
            }
        }

        if (teclado == null) {
            Text(recurso(R.string.and_aguardar), fontSize = 18.sp)
            return@Column
        }

        Column(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            teclado.linhas.forEach { linha ->
                Row(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    linha.forEach { tecla ->
                        Button(
                            onClick = { onTecla(tecla.tipo, tecla.valor) },
                            modifier = Modifier.weight(tecla.largura.toFloat()).fillMaxHeight(),
                            contentPadding = PaddingValues(2.dp),
                        ) {
                            TextoAdaptavel(tecla.rotulo, tamanhoMaximo = 22.sp, tamanhoMinimo = 9.sp)
                        }
                    }
                }
            }
        }
    }
}
