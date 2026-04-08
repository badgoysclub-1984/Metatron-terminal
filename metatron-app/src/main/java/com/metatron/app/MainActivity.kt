package com.metatron.app

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Send
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
                    MetatronAppOrchestrator()
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
                fontSize = 13.sp,
                lineHeight = 18.sp,
                letterSpacing = 0.5.sp
            )
        ),
        content = content
    )
}

@Composable
fun MetatronAppOrchestrator() {
    var screenState by remember { mutableStateOf("connect") } // "connect" or "terminal"
    var host by remember { mutableStateOf("192.168.1.56") }
    var user by remember { mutableStateOf("badgoysclub") }
    var password by remember { mutableStateOf("Rebel23!") }
    var port by remember { mutableStateOf("22") }

    if (screenState == "connect") {
        ConnectionScreen(
            host = host, onHostChange = { host = it },
            user = user, onUserChange = { user = it },
            password = password, onPasswordChange = { password = it },
            port = port, onPortChange = { port = it },
            onConnect = { screenState = "terminal" }
        )
    } else {
        TerminalScreen(host, user, password, port.toIntOrNull() ?: 22) {
            screenState = "connect"
        }
    }
}

@Composable
fun ConnectionScreen(
    host: String, onHostChange: (String) -> Unit,
    user: String, onUserChange: (String) -> Unit,
    password: String, onPasswordChange: (String) -> Unit,
    port: String, onPortChange: (String) -> Unit,
    onConnect: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("ℤ₉ NODE SETUP", color = NeonBlue, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(32.dp))
        
        OutlinedTextField(value = host, onValueChange = onHostChange, label = { Text("Host IP") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(value = port, onValueChange = onPortChange, label = { Text("Port") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(value = user, onValueChange = onUserChange, label = { Text("Username") }, modifier = Modifier.fillMaxWidth())
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = password, onValueChange = onPasswordChange, label = { Text("Password") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth()
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        Button(
            onClick = onConnect,
            modifier = Modifier.fillMaxWidth().height(56.dp),
            colors = ButtonDefaults.buttonColors(containerColor = NeonBlue, contentColor = DeepBlack)
        ) {
            Text("ESTABLISH QUANTUM LINK", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
fun TerminalScreen(host: String, user: String, pass: String, port: Int, onDisconnect: () -> Unit) {
    val coroutineScope = rememberCoroutineScope()
    val terminalLines = remember { mutableStateListOf<String>("[SYSTEM] Initializing SSH...") }
    var prompt by remember { mutableStateOf("") }
    var outputStream by remember { mutableStateOf<OutputStream?>(null) }
    var isConnected by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        coroutineScope.launch(Dispatchers.IO) {
            try {
                val jsch = JSch()
                val session = jsch.getSession(user, host, port)
                session.setPassword(pass)
                session.setConfig("StrictHostKeyChecking", "no")
                session.connect(15000)
                
                val channel = session.openChannel("shell") as ChannelShell
                channel.setPty(true)
                channel.connect()
                
                outputStream = channel.outputStream
                val inputStream = channel.inputStream
                isConnected = true

                withContext(Dispatchers.Main) { terminalLines.add("[SUCCESS] Connected to $user@$host") }

                val buffer = ByteArray(8192)
                while (channel.isConnected) {
                    if (inputStream.available() > 0) {
                        val length = inputStream.read(buffer)
                        if (length > 0) {
                            val chunk = String(buffer, 0, length).replace("\r", "")
                            withContext(Dispatchers.Main) {
                                // Add lines individually for better LazyColumn performance
                                chunk.split("\n").forEach { line ->
                                    if (line.isNotEmpty()) terminalLines.add(line)
                                }
                            }
                        }
                    }
                    delay(50)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { terminalLines.add("[ERROR] ${e.message}") }
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("ℤ₉ GEMINI TERMINAL", color = NeonBlue, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
            IconButton(onClick = onDisconnect) {
                Icon(Icons.Default.Settings, contentDescription = "Settings", tint = NeonBlue)
            }
        }

        // SelectionContainer allows users to copy text!
        SelectionContainer(modifier = Modifier.weight(1f).fillMaxWidth()) {
            TerminalOutputWindow(terminalLines)
        }

        PromptBar(
            value = prompt,
            onValueChange = { prompt = it },
            enabled = isConnected,
            onSend = {
                if (prompt.isNotBlank()) {
                    val cmd = prompt
                    coroutineScope.launch(Dispatchers.IO) {
                        outputStream?.write((cmd + "\n").toByteArray())
                        outputStream?.flush()
                    }
                    prompt = ""
                }
            }
        )
    }
}

@Composable
fun TerminalOutputWindow(lines: List<String>) {
    val listState = rememberLazyListState()
    LaunchedEffect(lines.size) {
        if (lines.isNotEmpty()) listState.animateScrollToItem(lines.size - 1)
    }

    LazyColumn(
        state = listState,
        modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp).background(DeepBlack)
    ) {
        items(lines) { line ->
            Text(
                text = line,
                color = NeonBlue,
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
                modifier = Modifier.padding(vertical = 1.dp)
            )
        }
    }
}

@Composable
fun PromptBar(value: String, onValueChange: (String) -> Unit, onSend: () -> Unit, enabled: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(16.dp).navigationBarsPadding().imePadding(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier.weight(1f).height(52.dp).border(1.dp, NeonBlue, RoundedCornerShape(26.dp)).background(DarkGrey).padding(horizontal = 20.dp),
            contentAlignment = Alignment.CenterStart
        ) {
            if (value.isEmpty()) Text("Message Gemini CLI...", color = NeonBlue.copy(alpha = 0.4f), fontSize = 14.sp)
            BasicTextField(
                value = value, onValueChange = onValueChange, enabled = enabled,
                textStyle = TextStyle(color = NeonBlue, fontFamily = FontFamily.Monospace, fontSize = 15.sp),
                cursorBrush = SolidColor(NeonBlue), modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send)
            )
        }
        Spacer(modifier = Modifier.width(10.dp))
        IconButton(
            onClick = onSend, enabled = enabled,
            modifier = Modifier.size(52.dp).background(if (enabled) NeonBlue else Color.Gray, RoundedCornerShape(26.dp))
        ) {
            Icon(Icons.Default.Send, contentDescription = "Send", tint = DeepBlack)
        }
    }
}
