package com.metatron.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
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
import java.io.InputStream
import java.io.OutputStream
import java.util.regex.Pattern

// Neon Palette
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
                fontWeight = FontWeight.Medium,
                fontSize = 12.sp,
                lineHeight = 16.sp
            )
        ),
        content = content
    )
}

@Composable
fun MetatronTerminalOrchestrator() {
    var screenState by remember { mutableStateOf("setup") }
    var host by remember { mutableStateOf("192.168.1.56") }
    var user by remember { mutableStateOf("badgoysclub") }
    var pass by remember { mutableStateOf("Rebel23!") }
    var port by remember { mutableStateOf("22") }

    if (screenState == "setup") {
        SetupScreen(
            host = host, onHostChange = { host = it },
            user = user, onUserChange = { user = it },
            pass = pass, onPassChange = { pass = it },
            port = port, onPortChange = { port = it },
            onEstablish = { screenState = "terminal" }
        )
    } else {
        TerminalInterface(host, user, pass, port.toIntOrNull() ?: 22) {
            screenState = "setup"
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
        Text("ℤ₉ NODE CONFIGURATION", color = NeonBlue, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold)
        Spacer(modifier = Modifier.height(40.dp))
        
        OutlinedTextField(value = host, onValueChange = onHostChange, label = { Text("HOST IP") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(value = port, onValueChange = onPortChange, label = { Text("PORT") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(value = user, onValueChange = onUserChange, label = { Text("USER") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(
            value = pass, onValueChange = onPassChange, label = { Text("CREDENTIAL") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth()
        )
        
        Spacer(modifier = Modifier.height(48.dp))
        Button(
            onClick = onEstablish,
            modifier = Modifier.fillMaxWidth().height(60.dp),
            shape = RoundedCornerShape(8.dp),
            colors = ButtonDefaults.buttonColors(containerColor = NeonBlue, contentColor = DeepBlack)
        ) {
            Text("INITIATE SECURE LINK", fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TerminalInterface(host: String, user: String, pass: String, port: Int, onExit: () -> Unit) {
    val coroutineScope = rememberCoroutineScope()
    val clipboardManager = LocalClipboardManager.current
    var terminalText by remember { mutableStateOf("🧿 METATRON v4.0: CONNECTING...\n") }
    var prompt by remember { mutableStateOf("") }
    var isConnected by remember { mutableStateOf(false) }
    var outputStream by remember { mutableStateOf<OutputStream?>(null) }
    
    val ansiPattern = Pattern.compile("\\x1B\\[[0-9;]*[a-zA-Z]")

    LaunchedEffect(Unit) {
        coroutineScope.launch(Dispatchers.IO) {
            try {
                val jsch = JSch()
                val session = jsch.getSession(user, host, port)
                session.setPassword(pass)
                session.setConfig("StrictHostKeyChecking", "no")
                session.connect(20000)
                
                val channel = session.openChannel("shell") as ChannelShell
                channel.setPty(true)
                channel.setEnv("TERM", "xterm")
                channel.connect()
                
                outputStream = channel.outputStream
                val inputStream = channel.inputStream
                isConnected = true

                withContext(Dispatchers.Main) { terminalText += "--- SECURE LINK ACTIVE ---\n" }

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
                                terminalText += clean
                                if (terminalText.length > 50000) {
                                    terminalText = terminalText.takeLast(30000)
                                }
                            }
                        }
                    }
                    delay(40)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { terminalText += "\n[ERROR] CONNECTION TERMINATED: ${e.message}\n" }
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("ℤ₉ GEMINI TERMINAL", color = NeonBlue, fontSize = 16.sp, fontWeight = FontWeight.Bold) },
            actions = {
                IconButton(onClick = { clipboardManager.setText(AnnotatedString(terminalText)) }) {
                    Icon(Icons.Default.Share, contentDescription = "Copy All", tint = NeonBlue)
                }
                IconButton(onClick = onExit) {
                    Icon(Icons.Default.Settings, contentDescription = "Setup", tint = NeonBlue)
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = DeepBlack)
        )

        val scrollState = rememberScrollState()
        LaunchedEffect(terminalText) {
            scrollState.animateScrollTo(scrollState.maxValue)
        }

        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 8.dp)
                .border(1.dp, NeonBlue.copy(alpha = 0.2f), RoundedCornerShape(4.dp))
                .background(Color.Black)
        ) {
            SelectionContainer {
                Text(
                    text = terminalText,
                    color = NeonBlue,
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(12.dp)
                        .verticalScroll(scrollState)
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp).navigationBarsPadding().imePadding(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(52.dp)
                    .border(1.dp, if (isConnected) NeonBlue else Color.DarkGray, RoundedCornerShape(26.dp))
                    .background(DarkGrey)
                    .padding(horizontal = 20.dp),
                contentAlignment = Alignment.CenterStart
            ) {
                if (prompt.isEmpty()) Text(if (isConnected) "Enter command..." else "Reconnecting...", color = NeonBlue.copy(alpha = 0.3f))
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
                    if (prompt.isNotBlank()) {
                        val cmd = prompt
                        coroutineScope.launch(Dispatchers.IO) {
                            outputStream?.write((cmd + "\n").toByteArray())
                            outputStream?.flush()
                        }
                        prompt = ""
                    }
                },
                enabled = isConnected,
                modifier = Modifier.size(52.dp).background(if (isConnected) NeonBlue else Color.DarkGray, RoundedCornerShape(26.dp))
            ) {
                Icon(Icons.Default.Send, contentDescription = "Send", tint = DeepBlack)
            }
        }
    }
}
