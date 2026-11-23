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
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.foundation.Canvas
import android.app.Activity
import android.view.WindowManager
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntSize
import androidx.compose.foundation.layout.Box
import androidx.compose.ui.input.pointer.changedToDown
import androidx.compose.ui.input.pointer.changedToUp
import androidx.compose.ui.input.pointer.positionChanged
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.semantics.Role
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.LocalContentColor
import androidx.compose.foundation.Image
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.layout.size
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
import pt.lplogic.teclado.modelo.Tecla
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
            val esquema = if (escuro) {
                darkColorScheme(
                    primary = Color(0xFF3B82F6),
                    onPrimary = Color.White,
                    background = Color(0xFF16181D),
                    surface = Color(0xFF1E222A),
                    onSurface = Color(0xFFF1F5F9),
                )
            } else {
                lightColorScheme(
                    primary = Color(0xFF2563EB),
                    onPrimary = Color.White,
                    background = Color(0xFFF1F4F8),
                    surface = Color(0xFFFFFFFF),
                    onSurface = Color(0xFF1A1D23),
                )
            }
            MaterialTheme(colorScheme = esquema) {
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

private enum class Tela { PERMISSOES, PROCURAR, CODIGO, TECLADO, TOUCHPAD }

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
    // Poupanca de energia: depois de X minutos sem toques, aviso com contagem e ecra preto (ver PoupancaEcra).
    var poupancaMinutos by remember { mutableStateOf(preferencias.getInt("poupanca_minutos", 5)) }
    var ultimaAtividade by remember { mutableStateOf(System.currentTimeMillis()) }
    var poupancaFase by remember { mutableStateOf(0) } // 0 normal, 1 aviso, 2 ecra apagado
    var segundosPoupanca by remember { mutableStateOf(POUPANCA_SEGUNDOS) }
    val ligadoRemoto = ligacao != null && tela != Tela.PROCURAR
    LaunchedEffect(ultimaAtividade, poupancaMinutos, ligadoRemoto) {
        poupancaFase = 0
        if (!ligadoRemoto || poupancaMinutos == 0) return@LaunchedEffect
        delay(poupancaMinutos * 60_000L)
        poupancaFase = 1
        for (s in POUPANCA_SEGUNDOS downTo 1) {
            segundosPoupanca = s
            delay(1_000L)
        }
        poupancaFase = 2
    }
    // Enquanto o teclado remoto esta ligado, o ecra nao adormece sozinho (a poupanca e feita pela app).
    // Com o ecra apagado por poupanca, o brilho fica no minimo.
    LaunchedEffect(ligadoRemoto, poupancaFase) {
        val janela = (contexto as? Activity)?.window ?: return@LaunchedEffect
        if (ligadoRemoto) {
            janela.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            janela.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
        janela.attributes = janela.attributes.also {
            it.screenBrightness = if (poupancaFase == 2) 0.01f else WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE
        }
    }
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
                    (tela == Tela.TECLADO || tela == Tela.TOUCHPAD || reconectando)
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
                    if (tela == Tela.TECLADO || tela == Tela.TOUCHPAD) tela = Tela.PROCURAR
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

    Box(
        modifier = Modifier
            .fillMaxSize()
            // Regista qualquer toque como atividade, sem consumir o evento (o toque continua para o ecra).
            .pointerInput(Unit) {
                awaitPointerEventScope {
                    while (true) {
                        awaitPointerEvent(PointerEventPass.Initial)
                        ultimaAtividade = System.currentTimeMillis()
                    }
                }
            },
    ) {
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
            poupancaMinutos = poupancaMinutos,
            onAlternarPoupanca = {
                val opcoes = listOf(0, 1, 2, 5, 10, 15, 30)
                poupancaMinutos = opcoes[(opcoes.indexOf(poupancaMinutos) + 1) % opcoes.size]
                preferencias.edit().putInt("poupanca_minutos", poupancaMinutos).apply()
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

        Tela.TOUCHPAD -> EcraTouchpad(
            onEvento = { acao, id, x, y, area -> ligacao?.enviarToque(acao, id, x, y, area) },
            onDimensoes = { largura, altura -> ligacao?.enviarDimensoes(largura, altura) },
            onVoltar = { tela = Tela.TECLADO },
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
            onTouchpad = { tela = Tela.TOUCHPAD },
            onDesligar = {
                pararReconexao()
                ligacao?.fechar()
                ligacao = null
                tela = Tela.PROCURAR
            },
        )
    }
    PoupancaEcra(fase = poupancaFase, segundos = segundosPoupanca)
    }
}

/** Modo de poupanca: aviso com contagem e, depois, ecra preto. Um toque cancela o aviso ou repoe a sessao. */
@Composable
private fun PoupancaEcra(fase: Int, segundos: Int) {
    if (fase == 0) return
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            // Bloqueia os toques enquanto o aviso ou o ecra preto estao visiveis (o toque ja foi registado).
            .pointerInput(Unit) {
                awaitPointerEventScope {
                    while (true) {
                        awaitPointerEvent().changes.forEach { it.consume() }
                    }
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        if (fase == 1) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(24.dp)) {
                Text(recurso(R.string.and_poupanca_aviso), color = Color.White, fontSize = 20.sp, textAlign = TextAlign.Center)
                Spacer(Modifier.height(16.dp))
                Text(recurso(R.string.and_poupanca_contagem, segundos), color = Color.White, fontSize = 28.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

/** Segundos de aviso antes de o ecra ficar preto na poupanca de energia. */
private const val POUPANCA_SEGUNDOS = 20

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
    poupancaMinutos: Int,
    onAlternarPoupanca: () -> Unit,
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
        TextButton(onClick = onAlternarPoupanca) {
            Text(
                if (poupancaMinutos == 0) recurso(R.string.and_poupanca_desligada)
                else recurso(R.string.and_poupanca_valor, poupancaMinutos),
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
/**
 * Touchpad: a superficie do ecra envia os toques ao PC, que move e clica o rato
 * (ver teclado/core/toque.py). Posicoes normalizadas entre 0 e 10000.
 */
@Composable
private fun EcraTouchpad(
    onEvento: (acao: String, id: Int, x: Int, y: Int, area: String?) -> Unit,
    onDimensoes: (larguraMm: Int, alturaMm: Int) -> Unit,
    onVoltar: () -> Unit,
) {
    val contexto = LocalContext.current
    val xdpi = contexto.resources.displayMetrics.xdpi
    val ydpi = contexto.resources.displayMetrics.ydpi
    // Barra de deslocamento: 1,2 cm no lado direito, qualquer que seja o aparelho.
    val barraPx = BARRA_DESLOCAMENTO_MM / 25.4f * xdpi
    var tamanho by remember { mutableStateOf(IntSize.Zero) }
    val dedosAtivos = remember { HashSet<Int>() }
    // No Quadro Interativo o touchpad tem uma so area e explica o uso de 1 e 2 dedos.
    val noQuadro = ModoTouchpad.noQuadro()
    LaunchedEffect(tamanho) {
        if (tamanho.width > 0 && tamanho.height > 0) {
            onDimensoes((tamanho.width / xdpi * 25.4f).toInt(), (tamanho.height / ydpi * 25.4f).toInt())
        }
    }
    // Ao sair do touchpad, os dedos que ainda estejam no ecra sao levantados no PC.
    DisposableEffect(Unit) {
        onDispose { for (id in dedosAtivos.toList()) onEvento("up", id, 0, 0, null) }
    }
    Box(
        modifier = Modifier
            .fillMaxSize()
            .onSizeChanged { tamanho = it }
            .pointerInput(onEvento, barraPx) {
                awaitPointerEventScope {
                    while (true) {
                        val evento = awaitPointerEvent()
                        val largura = size.width.toFloat().coerceAtLeast(1f)
                        val altura = size.height.toFloat().coerceAtLeast(1f)
                        val quadro = ModoTouchpad.noQuadro()
                        val presentes = HashSet<Int>()
                        for (mudanca in evento.changes) {
                            val id = (mudanca.id.value % 32).toInt()
                            presentes.add(id)
                            val x = (mudanca.position.x / largura * 10000f).toInt().coerceIn(0, 10000)
                            val y = (mudanca.position.y / altura * 10000f).toInt().coerceIn(0, 10000)
                            // Cada evento lista todos os dedos: um dedo que ja nao esta premido fica levantado,
                            // mesmo que o levantamento anterior se tenha perdido (ex.: gesto de 3 dedos cancelado pelo sistema).
                            if (!mudanca.pressed) {
                                if (dedosAtivos.remove(id)) onEvento("up", id, x, y, null)
                            } else if (dedosAtivos.add(id)) {
                                // A area e decidida no inicio do toque: barra, esquerda ou direita.
                                // No Quadro nao ha barra nem lados: toda a superficie e a mesma area.
                                val area = when {
                                    quadro -> "esquerda"
                                    mudanca.position.x >= largura - barraPx -> "barra"
                                    mudanca.position.x < (largura - barraPx) / 2f -> "esquerda"
                                    else -> "direita"
                                }
                                onEvento("down", id, x, y, area)
                            } else if (mudanca.positionChanged()) {
                                onEvento("move", id, x, y, null)
                            }
                            mudanca.consume()
                        }
                        // Dedos que desapareceram do evento (gesto cancelado pelo sistema) contam como levantados.
                        for (id in dedosAtivos.filter { it !in presentes }) {
                            dedosAtivos.remove(id)
                            onEvento("up", id, 0, 0, null)
                        }
                    }
                }
            },
    ) {
        if (noQuadro) {
            Box(
                modifier = Modifier.fillMaxSize()
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.06f)),
            )
            InstrucoesQuadro(modifier = Modifier.align(Alignment.Center))
        } else {
            Row(modifier = Modifier.fillMaxSize()) {
                Box(
                    modifier = Modifier.weight(1f).fillMaxHeight()
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.06f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(recurso(R.string.and_touchpad_esquerdo), fontSize = 20.sp)
                }
                Box(
                    modifier = Modifier.weight(1f).fillMaxHeight()
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(recurso(R.string.and_touchpad_direito), fontSize = 20.sp)
                }
                Box(
                    modifier = Modifier
                        .width(with(LocalDensity.current) { barraPx.toDp() })
                        .fillMaxHeight()
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.3f)),
                    contentAlignment = Alignment.Center,
                ) {
                    // Riscos horizontais, como a roda do rato, com setas discretas no topo e na base.
                    Canvas(modifier = Modifier.fillMaxSize()) {
                        val espaco = 14.dp.toPx()
                        val cor = Color.Gray.copy(alpha = 0.5f)
                        var y = size.height * 0.2f
                        while (y < size.height * 0.8f) {
                            drawLine(
                                color = cor,
                                start = Offset(size.width * 0.2f, y),
                                end = Offset(size.width * 0.8f, y),
                                strokeWidth = 2.dp.toPx(),
                            )
                            y += espaco
                        }
                    }
                    Text(
                        "",
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        modifier = Modifier.align(Alignment.TopCenter).padding(top = 8.dp),
                    )
                    Text(
                        "",
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp),
                    )
                }
            }
        }
        TextButton(onClick = onVoltar, modifier = Modifier.align(Alignment.TopStart).padding(8.dp)) {
            Text(recurso(R.string.and_voltar_teclado), fontSize = 16.sp)
        }
        if (!noQuadro) {
            Text(
                recurso(R.string.and_touchpad_dica),
                fontSize = 14.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.align(Alignment.TopCenter).padding(top = 56.dp, start = 24.dp, end = 24.dp),
            )
        }
    }
}

/** Tres cartoes com desenhos (sem texto): desenhar com 1 dedo, mover com 2 dedos, clicar com um toque. */
@Composable
private fun InstrucoesQuadro(modifier: Modifier = Modifier) {
    val cor = MaterialTheme.colorScheme.onSurface
    val fundo = MaterialTheme.colorScheme.surface
    Row(
        modifier = modifier.fillMaxWidth().padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
        CartaoInstrucao(fundo) { desenharUmDedo(cor) }
        CartaoInstrucao(fundo) { desenharDoisDedos(cor) }
        CartaoInstrucao(fundo) { desenharToque(cor) }
    }
}

@Composable
private fun CartaoInstrucao(fundo: Color, desenho: DrawScope.() -> Unit) {
    Canvas(
        modifier = Modifier.size(104.dp).clip(RoundedCornerShape(16.dp)).background(fundo.copy(alpha = 0.9f)),
    ) { desenho() }
}

/** 1 dedo a arrastar: um traco ondulado (desenhar). */
private fun DrawScope.desenharUmDedo(cor: Color) {
    val s = size.minDimension
    drawCircle(cor, radius = s * 0.09f, center = Offset(s * 0.26f, s * 0.5f))
    val traco = Path().apply {
        moveTo(s * 0.4f, s * 0.5f)
        cubicTo(s * 0.52f, s * 0.26f, s * 0.68f, s * 0.74f, s * 0.86f, s * 0.5f)
    }
    drawPath(traco, cor, style = Stroke(width = s * 0.07f, cap = StrokeCap.Round))
}

/** 2 dedos: o cursor move-se numa seta, sem traco (mover). */
private fun DrawScope.desenharDoisDedos(cor: Color) {
    val s = size.minDimension
    drawCircle(cor, radius = s * 0.08f, center = Offset(s * 0.2f, s * 0.46f))
    drawCircle(cor, radius = s * 0.08f, center = Offset(s * 0.2f, s * 0.6f))
    drawLine(cor, Offset(s * 0.42f, s * 0.53f), Offset(s * 0.86f, s * 0.53f), strokeWidth = s * 0.06f, cap = StrokeCap.Round)
    drawLine(cor, Offset(s * 0.86f, s * 0.53f), Offset(s * 0.74f, s * 0.41f), strokeWidth = s * 0.06f, cap = StrokeCap.Round)
    drawLine(cor, Offset(s * 0.86f, s * 0.53f), Offset(s * 0.74f, s * 0.65f), strokeWidth = s * 0.06f, cap = StrokeCap.Round)
}

/** Toque breve: um ponto com um anel a pulsar (clicar). */
private fun DrawScope.desenharToque(cor: Color) {
    val s = size.minDimension
    drawCircle(cor, radius = s * 0.11f, center = Offset(s * 0.5f, s * 0.5f))
    drawCircle(cor, radius = s * 0.28f, center = Offset(s * 0.5f, s * 0.5f), style = Stroke(width = s * 0.05f))
}

/** Largura da barra de deslocamento do touchpad, em milimetros. */
private const val BARRA_DESLOCAMENTO_MM = 12f

/** Paleta visual do teclado no telemovel, alinhada com os temas Claro e Escuro do PC. */
private data class PaletaTeclado(
    val fundo: Color,
    val barraTopo: Color,
    val tecla: Color,
    val teclaEspecial: Color,
    val texto: Color,
    val textoSuave: Color,
    val borda: Color,
    val relevo: Color,
    val sugestao: Color,
    val utilFundo: Color,
    val ativoFundo: Color,
    val ativoBorda: Color,
    val ativoCor: Color,
    val premida: Color,
    val textoPremido: Color,
)

private val PALETA_CLARA = PaletaTeclado(
    fundo = Color(0xFFD5DBE3),
    barraTopo = Color(0xFFE2E6EC),
    tecla = Color(0xFFFFFFFF),
    teclaEspecial = Color(0xFFBEC6D1),
    texto = Color(0xFF1A1D23),
    textoSuave = Color(0xFF5A6270),
    borda = Color(0xFFB7BFC9),
    relevo = Color(0xFF9EA6B2),
    sugestao = Color(0xFFBEC6D1),
    utilFundo = Color(0xFFEBEEF3),
    ativoFundo = Color(0x2416A34A),
    ativoBorda = Color(0x9916A34A),
    ativoCor = Color(0xFF16A34A),
    premida = Color(0xFF2563EB),
    textoPremido = Color(0xFFFFFFFF),
)

private val PALETA_ESCURA = PaletaTeclado(
    fundo = Color(0xFF16181D),
    barraTopo = Color(0xFF1D2027),
    tecla = Color(0xFF2B2F38),
    teclaEspecial = Color(0xFF20242C),
    texto = Color(0xFFF1F5F9),
    textoSuave = Color(0xFF94A3B8),
    borda = Color(0xFF3A3F4B),
    relevo = Color(0xFF0A0C0F),
    sugestao = Color(0xFF252932),
    utilFundo = Color(0xFF22262E),
    ativoFundo = Color(0x3222C55E),
    ativoBorda = Color(0xA04ADE80),
    ativoCor = Color(0xFF22C55E),
    premida = Color(0xFF3B82F6),
    textoPremido = Color(0xFFFFFFFF),
)

private fun ehTeclaDeEscrita(tecla: Tecla): Boolean {
    if (tecla.tipo == "texto" || tecla.tipo == "multitoque" || tecla.tipo == "acento") return true
    if (tecla.tipo == "tecla" && tecla.valor == "espaco") return true
    return false
}

/** Pilula compacta na barra superior: discreta quando desligada, verde suave quando ativa. */
@Composable
private fun PilulaTopo(
    simbolo: String,
    ativo: Boolean,
    habilitado: Boolean,
    descricao: String,
    paleta: PaletaTeclado,
    onClick: () -> Unit,
) {
    val forma = RoundedCornerShape(50)
    val fundo = if (ativo) paleta.ativoFundo else paleta.utilFundo
    val borda = if (ativo) paleta.ativoBorda else paleta.borda.copy(alpha = 0.7f)
    val alfa = if (habilitado) 1f else 0.38f
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier
            .height(30.dp)
            .clip(forma)
            .background(fundo.copy(alpha = fundo.alpha * alfa))
            .border(1.dp, borda.copy(alpha = borda.alpha * alfa), forma)
            .clickable(enabled = habilitado, role = Role.Button, onClick = onClick)
            .padding(horizontal = 9.dp)
            .semantics { contentDescription = descricao },
    ) {
        Text(
            simbolo,
            fontSize = 14.sp,
            color = (if (ativo) paleta.ativoCor else paleta.texto).copy(alpha = alfa),
        )
        Box(
            modifier = Modifier
                .size(6.dp)
                .clip(forma)
                .background((if (ativo) paleta.ativoCor else paleta.textoSuave.copy(alpha = 0.45f)).copy(alpha = alfa)),
        )
    }
}

/** Botao de utilidade compacto na barra superior (Touchpad, Tema, Desligar). */
@Composable
private fun BotaoUtilTopo(
    rotulo: String,
    descricao: String,
    paleta: PaletaTeclado,
    onClick: () -> Unit,
) {
    val forma = RoundedCornerShape(9.dp)
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .height(30.dp)
            .clip(forma)
            .background(paleta.utilFundo)
            .border(1.dp, paleta.borda.copy(alpha = 0.7f), forma)
            .clickable(role = Role.Button, onClick = onClick)
            .padding(horizontal = 10.dp)
            .semantics { contentDescription = descricao },
    ) {
        Text(rotulo, fontSize = 13.sp, fontWeight = FontWeight.Medium, color = paleta.texto)
    }
}

/** Tecla do teclado com hierarquia visual (escrita vs especial) e relevo inferior subtil. */
@Composable
private fun TeclaVisual(
    tecla: Tecla,
    paleta: PaletaTeclado,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    val interacao = remember { MutableInteractionSource() }
    val premida by interacao.collectIsPressedAsState()
    val forma = RoundedCornerShape(9.dp)
    val escrita = ehTeclaDeEscrita(tecla)
    val corFundo = when {
        premida -> paleta.premida
        escrita -> paleta.tecla
        else -> paleta.teclaEspecial
    }
    val corTexto = if (premida) paleta.textoPremido else paleta.texto
    val corBorda = if (premida) paleta.premida else paleta.borda

    Box(
        modifier = modifier
            .clip(forma)
            .background(if (premida) paleta.premida else paleta.relevo)
            .clickable(interactionSource = interacao, indication = null, role = Role.Button, onClick = onClick)
            .padding(bottom = if (premida) 0.dp else 2.dp),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .fillMaxSize()
                .clip(forma)
                .background(corFundo)
                .border(1.dp, corBorda, forma)
                .padding(horizontal = 4.dp, vertical = 2.dp),
        ) {
            CompositionLocalProvider(LocalContentColor provides corTexto) {
                // Ler a versao dos icones: quando chegam, a tecla desenha-se de novo.
                IconesTeclado.versao
                val nome = tecla.icone
                val imagem = nome?.let { IconesTeclado.bitmap(it) }
                if (nome != null && imagem != null) {
                    // Monocromaticos tomam a cor do texto da tecla; os coloridos mantem as suas cores.
                    val tinta = if (IconesTeclado.colorido(nome)) null else LocalContentColor.current
                    Image(
                        bitmap = imagem,
                        contentDescription = tecla.rotulo,
                        modifier = Modifier.fillMaxHeight(0.74f).aspectRatio(1f),
                        colorFilter = tinta?.let { ColorFilter.tint(it) },
                    )
                } else {
                    TextoAdaptavel(
                        texto = tecla.rotulo,
                        tamanhoMaximo = 22.sp,
                        tamanhoMinimo = 9.sp,
                        cor = corTexto,
                    )
                }
            }
        }
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
    onTouchpad: () -> Unit,
    onDesligar: () -> Unit,
    escuro: Boolean,
    onAlternarTema: () -> Unit,
) {
    val paleta = if (escuro) PALETA_ESCURA else PALETA_CLARA
    val falar = interruptores["falar"] == true
    val falarDisponivel = interruptores["falar_disponivel"] == true
    val ditar = interruptores["ditar"] == true
    val ditarDisponivel = interruptores["ditar_disponivel"] == true

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(paleta.fundo)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        // Barra superior integrada com marca Kikoia, estado da ligacao, interruptores e utilidades
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier
                .fillMaxWidth()
                .height(42.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(paleta.barraTopo)
                .border(1.dp, paleta.borda.copy(alpha = 0.65f), RoundedCornerShape(10.dp))
                .padding(horizontal = 8.dp),
        ) {
            Image(
                painter = painterResource(if (escuro) R.drawable.logo_kikoia_escuro else R.drawable.logo_kikoia_claro),
                contentDescription = "Kikoia",
                contentScale = ContentScale.FillHeight,
                modifier = Modifier.height(17.dp),
            )
            Box(
                modifier = Modifier
                    .width(1.dp)
                    .height(16.dp)
                    .background(paleta.borda.copy(alpha = 0.7f)),
            )
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(RoundedCornerShape(50))
                    .background(paleta.ativoCor),
            )
            Text(
                nomeComputador,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                color = paleta.texto,
                maxLines = 1,
                modifier = Modifier.weight(1f),
            )
            BotaoUtilTopo(
                rotulo = "🖱",
                descricao = recurso(R.string.and_touchpad),
                paleta = paleta,
                onClick = onTouchpad,
            )
            PilulaTopo(
                simbolo = "💬",
                ativo = sugestoesAtivas,
                habilitado = true,
                descricao = recurso(R.string.and_sugestoes),
                paleta = paleta,
                onClick = onAlternarSugestoes,
            )
            PilulaTopo(
                simbolo = "🔊",
                ativo = falar,
                habilitado = falarDisponivel,
                descricao = recurso(R.string.and_falar),
                paleta = paleta,
            ) {
                onAlternarInterruptor("falar", !falar)
            }
            PilulaTopo(
                simbolo = "🎤",
                ativo = ditar,
                habilitado = ditarDisponivel,
                descricao = recurso(R.string.and_ditar),
                paleta = paleta,
            ) {
                onAlternarInterruptor("ditar", !ditar)
            }
            BotaoUtilTopo(
                rotulo = if (escuro) "☀" else "☾",
                descricao = if (escuro) "Tema claro" else "Tema escuro",
                paleta = paleta,
                onClick = onAlternarTema,
            )
            BotaoUtilTopo(
                rotulo = recurso(R.string.and_desligar),
                descricao = recurso(R.string.and_desligar),
                paleta = paleta,
                onClick = onDesligar,
            )
        }

        // A faixa ocupa sempre o mesmo espaco enquanto as sugestoes estiverem ativas, mesmo sem palavras:
        // assim o teclado nao sobe nem desce quando as sugestoes aparecem ou desaparecem.
        if (sugestoesAtivas) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(42.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                sugestoes.forEachIndexed { i, palavra ->
                    val formaSug = RoundedCornerShape(8.dp)
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .clip(formaSug)
                            .background(paleta.sugestao)
                            .clickable(role = Role.Button) { onSugestao(i) }
                            .padding(horizontal = 8.dp, vertical = 2.dp),
                    ) {
                        TextoAdaptavel(
                            texto = palavra,
                            tamanhoMaximo = 16.sp,
                            tamanhoMinimo = 10.sp,
                            cor = paleta.texto,
                        )
                    }
                }
            }
        }

        if (teclado == null) {
            Box(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                contentAlignment = Alignment.Center,
            ) {
                Text(recurso(R.string.and_aguardar), fontSize = 18.sp, color = paleta.textoSuave)
            }
            return@Column
        }

        Column(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            teclado.linhas.forEach { linha ->
                Row(
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(5.dp),
                ) {
                    linha.forEach { tecla ->
                        TeclaVisual(
                            tecla = tecla,
                            paleta = paleta,
                            modifier = Modifier.weight(tecla.largura.toFloat()).fillMaxHeight(),
                            onClick = { onTecla(tecla.tipo, tecla.valor) },
                        )
                    }
                }
            }
        }
    }
}
