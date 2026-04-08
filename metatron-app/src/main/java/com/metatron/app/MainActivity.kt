package com.metatron.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
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
import java.util.*

// Neon Palette
val NeonBlue = Color(0xFF00FFFF)
val DeepBlack = Color(0xFF000000)
val DarkGrey = Color(0xFF121212)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MetatronZ9Theme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = DeepBlack
                ) {
                    GeminiTerminalApp()
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
                fontSize = 14.sp,
                lineHeight = 20.sp,
                letterSpacing = 0.5.sp
            )
        ),
        content = content
    )
}

@Composable
fun GeminiTerminalApp() {
    val coroutineScope = rememberCoroutineScope()
    var prompt by remember { mutableStateOf("") }
    val terminalLines = remember { mutableStateListOf<String>("🧿 METATRON Z9: INITIALIZING QUANTUM LINK...") }
    
    // SSH State
    var session by remember { mutableStateOf<Session?>(null) }
    var outputStream by remember { mutableStateOf<OutputStream?>(null) }
    var isConnected by remember { mutableStateOf(false) }

    // Persistent SSH Connection
    LaunchedEffect(Unit) {
        coroutineScope.launch(Dispatchers.IO) {
            try {
                val jsch = JSch()
                val newSession = jsch.getSession("badgoysclub", "192.168.1.56", 22)
                newSession.setPassword("Rebel23!")
                newSession.setConfig("StrictHostKeyChecking", "no")
                newSession.connect(15000)
                
                val channel = newSession.openChannel("shell") as ChannelShell
                channel.setPty(true)
                channel.connect()
                
                session = newSession
                outputStream = channel.outputStream
                val inputStream = channel.inputStream
                isConnected = true

                withContext(Dispatchers.Main) {
                    terminalLines.add("--- LINK ESTABLISHED: badgoysclub@192.168.1.56 ---")
                }

                val buffer = ByteArray(8192)
                while (channel.isConnected) {
                    if (inputStream.available() > 0) {
                        val length = inputStream.read(buffer)
                        if (length > 0) {
                            val cleanResponse = String(buffer, 0, length)
                                .replace("\r\n", "\n")
                                .replace("\r", "\n")
                            
                            withContext(Dispatchers.Main) {
                                // Simple logic to avoid flooding the UI with identical lines or echoes
                                if (cleanResponse.isNotBlank()) {
                                    terminalLines.add(cleanResponse.trimEnd())
                                }
                            }
                        }
                    }
                    delay(30)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    terminalLines.add("CONNECTION FAILED: ${e.message}")
                }
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // App Title
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 12.dp, bottom = 8.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "ℤ₉ GEMINI TERMINAL",
                color = NeonBlue,
                style = MaterialTheme.typography.titleMedium.copy(
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = 2.sp
                )
            )
        }

        // Terminal Window (Output)
        TerminalWindow(terminalLines)

        // Prompt Bar (Input)
        ChatbotPromptBar(
            value = prompt,
            onValueChange = { prompt = it },
            enabled = isConnected,
            onSend = {
                if (prompt.isNotBlank()) {
                    val cmd = prompt
                    coroutineScope.launch(Dispatchers.IO) {
                        try {
                            outputStream?.write((cmd + "\n").toByteArray())
                            outputStream?.flush()
                        } catch (e: Exception) {
                            withContext(Dispatchers.Main) {
                                terminalLines.add("SYSTEM ERROR: ${e.message}")
                            }
                        }
                    }
                    prompt = ""
                }
            }
        )
    }
}

@Composable
fun ColumnScope.TerminalWindow(lines: List<String>) {
    val listState = rememberLazyListState()
    
    LaunchedEffect(lines.size) {
        if (lines.isNotEmpty()) {
            listState.animateScrollToItem(lines.size - 1)
        }
    }

    Box(
        modifier = Modifier
            .weight(1f)
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp)
            .border(1.dp, NeonBlue.copy(alpha = 0.3f), RoundedCornerShape(4.dp))
            .background(DarkGrey.copy(alpha = 0.5f))
            .padding(8.dp)
    ) {
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize()
        ) {
            items(lines) { line ->
                Text(
                    text = line,
                    color = NeonBlue,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    lineHeight = 14.sp
                )
            }
        }
    }
}

@Composable
fun ChatbotPromptBar(
    value: String,
    onValueChange: (String) -> Unit,
    onSend: () -> Unit,
    enabled: Boolean
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .navigationBarsPadding()
            .imePadding(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .weight(1f)
                .height(52.dp)
                .border(1.dp, if (enabled) NeonBlue else Color.Gray, RoundedCornerShape(26.dp))
                .background(DarkGrey, RoundedCornerShape(26.dp))
                .padding(horizontal = 20.dp),
            contentAlignment = Alignment.CenterStart
        ) {
            if (value.isEmpty()) {
                Text(
                    text = if (enabled) "Message Gemini CLI..." else "Connecting...",
                    color = NeonBlue.copy(alpha = 0.4f),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 14.sp
                )
            }
            BasicTextField(
                value = value,
                onValueChange = onValueChange,
                enabled = enabled,
                textStyle = TextStyle(
                    color = NeonBlue,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 15.sp
                ),
                cursorBrush = SolidColor(NeonBlue),
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send)
            )
        }

        Spacer(modifier = Modifier.width(10.dp))

        IconButton(
            onClick = onSend,
            enabled = enabled,
            modifier = Modifier
                .size(52.dp)
                .background(if (enabled) NeonBlue else Color.Gray, RoundedCornerShape(26.dp))
        ) {
            Icon(
                imageVector = Icons.Default.Send,
                contentDescription = "Send",
                tint = DeepBlack
            )
        }
    }
}
