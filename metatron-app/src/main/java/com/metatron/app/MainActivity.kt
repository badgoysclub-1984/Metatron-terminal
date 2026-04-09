package com.metatron.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.jcraft.jsch.ChannelShell
import com.jcraft.jsch.JSch
import com.jcraft.jsch.Session
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.OutputStream
import java.util.regex.Pattern

val NeonBlue = Color(0xFF00FFFF)
val DeepBlack = Color(0xFF000000)
val DarkGrey = Color(0xFF121212)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MetatronZ9Theme {
                Surface(modifier = Modifier.fillMaxSize(), color = DeepBlack) {
                    MetatronTerminalOrchestrator()
                }
            }
        }
    }
}

@Composable
fun MetatronZ9Theme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = NeonBlue,
            background = DeepBlack,
            surface = DarkGrey,
            onPrimary = DeepBlack,
            onBackground = NeonBlue,
            onSurface = NeonBlue
        ),
        typography = Typography(
            bodyLarge = TextStyle(
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Normal,
                fontSize = 11.sp,
                lineHeight = 14.sp
            )
        ),
        content = content
    )
}

class TerminalSessionState(val id: Int, val host: String, val user: String, val pass: String, val port: Int) {
    var terminalText = mutableStateOf("🧿 METATRON v7.0 PRO: INITIALIZING XTERM-256COLOR...\n")
    var isConnected = mutableStateOf(false)
    var outputStream: OutputStream? = null
    var jschSession: Session? = null
    var channel: ChannelShell? = null

    fun disconnect() {
        channel?.disconnect()
        jschSession?.disconnect()
        isConnected.value = false
    }
}

@Composable
fun MetatronTerminalOrchestrator() {
    var screenState by remember { mutableStateOf("setup") }
    var host by remember { mutableStateOf("192.168.1.56") }
    var user by remember { mutableStateOf("badgoysclub") }
    var pass by remember { mutableStateOf("Rebel23!") }
    var port by remember { mutableStateOf("22") }

    val sessions = remember { mutableStateListOf<TerminalSessionState>() }

    if (screenState == "setup") {
        SetupScreen(
            host = host, onHostChange = { host = it },
            user = user, onUserChange = { user = it },
            pass = pass, onPassChange = { pass = it },
            port = port, onPortChange = { port = it },
            onEstablish = { 
                if (sessions.isEmpty()) {
                    sessions.add(TerminalSessionState(0, host, user, pass, port.toIntOrNull() ?: 22))
                }
                screenState = "terminal" 
            }
        )
    } else {
        MultiTerminalInterface(sessions, onExit = { screenState = "setup" }) {
            sessions.add(TerminalSessionState(sessions.size, host, user, pass, port.toIntOrNull() ?: 22))
        }
    }
}

@Composable
fun SetupScreen(
    host: String, onHostChange: (String) -> Unit,
    user: String, onUserChange: (String) -> Unit,
    pass: String, onPassChange: (String) -> Unit,
    port: String, onPortChange: (String) -> Unit,
    onEstablish: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("ℤ₉ TERMINAL v7.0 SETUP", color = NeonBlue, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold)
        Spacer(modifier = Modifier.height(32.dp))
        OutlinedTextField(value = host, onValueChange = onHostChange, label = { Text("HOST IP") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(value = port, onValueChange = onPortChange, label = { Text("PORT") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(value = user, onValueChange = onUserChange, label = { Text("USER") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = pass, onValueChange = onPassChange, label = { Text("PASS") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(40.dp))
        Button(
            onClick = onEstablish,
            modifier = Modifier.fillMaxWidth().height(56.dp),
            colors = ButtonDefaults.buttonColors(containerColor = NeonBlue, contentColor = DeepBlack)
        ) {
            Text("ESTABLISH MULTI-NODE LINK", fontWeight = FontWeight.Bold)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun MultiTerminalInterface(
    sessions: MutableList<TerminalSessionState>, 
    onExit: () -> Unit,
    onAddTerminal: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var prompt by remember { mutableStateOf("") }
    val pagerState = rememberPagerState(pageCount = { sessions.size })
    val ansiPattern = Pattern.compile("\\x1B\\[[0-9;]*[a-zA-Z]")

    // Connect all unconnected sessions
    LaunchedEffect(sessions.size) {
        sessions.filter { !it.isConnected.value && it.channel == null }.forEach { sessionState ->
            coroutineScope.launch(Dispatchers.IO) {
                try {
                    val jsch = JSch()
                    val session = jsch.getSession(sessionState.user, sessionState.host, sessionState.port)
                    session.setPassword(sessionState.pass)
                    session.setConfig("StrictHostKeyChecking", "no")
                    session.connect(30000)
                    
                    val channel = session.openChannel("shell") as ChannelShell
                    channel.setPty(true)
                    // CRITICAL: Request xterm-256color to bypass Gemini CLI warnings
                    channel.setEnv("TERM", "xterm-256color")
                    channel.setPtyType("xterm-256color", 120, 40, 0, 0)
                    channel.connect()
                    
                    sessionState.jschSession = session
                    sessionState.channel = channel
                    sessionState.outputStream = channel.outputStream
                    val inputStream = channel.inputStream
                    sessionState.isConnected.value = true

                    withContext(Dispatchers.Main) { 
                        sessionState.terminalText.value += "--- NODE ${sessionState.id} LINK ACTIVE ---\n" 
                    }

                    val buffer = ByteArray(16384)
                    while (channel.isConnected) {
                        if (inputStream.available() > 0) {
                            val read = inputStream.read(buffer)
                            if (read > 0) {
                                val raw = String(buffer, 0, read)
                                val clean = ansiPattern.matcher(raw).replaceAll("")
                                    .replace("\r\n", "\n")
                                    .replace("\r", "")
                                
                                withContext(Dispatchers.Main) {
                                    val newText = sessionState.terminalText.value + clean
                                    sessionState.terminalText.value = if (newText.length > 100000) newText.takeLast(80000) else newText
                                }
                            }
                        }
                        delay(20)
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) { 
                        sessionState.terminalText.value += "\n[SYSTEM ERROR] NODE ${sessionState.id}: ${e.message}\n" 
                    }
                }
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("ℤ₉ MULTI-NODE TERMINAL (${pagerState.currentPage + 1}/${sessions.size})", color = NeonBlue, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold) },
            actions = {
                IconButton(onClick = onAddTerminal) {
                    Icon(Icons.Default.Add, contentDescription = "Add Node", tint = NeonBlue)
                }
                IconButton(onClick = onExit) {
                    Icon(Icons.Default.Settings, contentDescription = "Config", tint = NeonBlue)
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = DeepBlack)
        )

        // Pager for Multiple Terminal Windows
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.weight(1f).fillMaxWidth()
        ) { page ->
            val sessionState = sessions[page]
            val scrollState = rememberScrollState()
            
            LaunchedEffect(sessionState.terminalText.value) {
                scrollState.animateScrollTo(scrollState.maxValue)
            }

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 8.dp)
                    .border(1.dp, NeonBlue.copy(alpha = 0.3f), RoundedCornerShape(4.dp))
                    .background(Color.Black)
            ) {
                // EDITABLE TEXTFIELD: Allows direct typing, copy, and paste into the terminal
                BasicTextField(
                    value = sessionState.terminalText.value,
                    onValueChange = { newText ->
                        // Detect appended text (simulating typing/pasting directly into terminal)
                        if (newText.length > sessionState.terminalText.value.length) {
                            val diff = newText.substring(sessionState.terminalText.value.length)
                            coroutineScope.launch(Dispatchers.IO) {
                                sessionState.outputStream?.write(diff.toByteArray())
                                sessionState.outputStream?.flush()
                            }
                        }
                        sessionState.terminalText.value = newText
                    },
                    textStyle = TextStyle(
                        color = NeonBlue,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                        lineHeight = 14.sp
                    ),
                    cursorBrush = SolidColor(NeonBlue),
                    modifier = Modifier.fillMaxSize().padding(8.dp).verticalScroll(scrollState)
                )
            }
        }

        // Shared Prompt Bar & Tools
        val activeSession = sessions.getOrNull(pagerState.currentPage)
        val isConnected = activeSession?.isConnected?.value == true

        Row(
            modifier = Modifier.fillMaxWidth().padding(8.dp).navigationBarsPadding().imePadding(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Tool Icons (Upload / Screenshot stubs)
            IconButton(onClick = { /* Upload Logic Stub */ }) {
                Icon(Icons.Default.Add, contentDescription = "Upload File", tint = NeonBlue)
            }
            IconButton(onClick = { /* Screenshot Logic Stub */ }) {
                Icon(Icons.Default.Add, contentDescription = "Take Screenshot", tint = NeonBlue)
            }

            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(48.dp)
                    .border(1.dp, if (isConnected) NeonBlue else Color.Gray, RoundedCornerShape(24.dp))
                    .background(DarkGrey)
                    .padding(horizontal = 16.dp),
                contentAlignment = Alignment.CenterStart
            ) {
                if (prompt.isEmpty()) Text(if (isConnected) "Global command..." else "Connecting...", color = NeonBlue.copy(alpha = 0.3f), fontSize = 13.sp)
                BasicTextField(
                    value = prompt, onValueChange = { prompt = it }, enabled = isConnected,
                    textStyle = TextStyle(color = NeonBlue, fontFamily = FontFamily.Monospace, fontSize = 14.sp),
                    cursorBrush = SolidColor(NeonBlue), modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send)
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
            IconButton(
                onClick = {
                    if (prompt.isNotBlank() && activeSession != null) {
                        val cmd = prompt
                        coroutineScope.launch(Dispatchers.IO) {
                            activeSession.outputStream?.write((cmd + "\n").toByteArray())
                            activeSession.outputStream?.flush()
                        }
                        prompt = ""
                    }
                },
                enabled = isConnected,
                modifier = Modifier.size(48.dp).background(if (isConnected) NeonBlue else Color.Gray, RoundedCornerShape(24.dp))
            ) {
                Icon(Icons.Default.Send, contentDescription = "Send", tint = DeepBlack)
            }
        }
    }
}
