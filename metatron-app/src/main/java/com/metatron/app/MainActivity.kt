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
                    SSHMetatronTerminal()
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
fun SSHMetatronTerminal() {
    val coroutineScope = rememberCoroutineScope()
    var prompt by remember { mutableStateOf("") }
    val terminalLines = remember { mutableStateListOf<String>("ℤ₉ METATRON TERMINAL v2.0 READY...", "Waiting for SSH connection to 192.168.1.56...") }
    
    // SSH State
    var session by remember { mutableStateOf<Session?>(null) }
    var outputStream by remember { mutableStateOf<OutputStream?>(null) }
    var channel by remember { mutableStateOf<ChannelShell?>(null) }

    // Auto-connect to Pi (hardcoded for now to facilitate fast deployment)
    LaunchedEffect(Unit) {
        coroutineScope.launch(Dispatchers.IO) {
            try {
                val jsch = JSch()
                val newSession = jsch.getSession("badgoysclub", "192.168.1.56", 22)
                newSession.setPassword("Rebel23!")
                newSession.setConfig("StrictHostKeyChecking", "no")
                newSession.connect(10000)
                
                val newChannel = newSession.openChannel("shell") as ChannelShell
                newChannel.connect()
                
                session = newSession
                channel = newChannel
                outputStream = newChannel.outputStream
                val inputStream = newChannel.inputStream

                withContext(Dispatchers.Main) {
                    terminalLines.add("--- CONNECTED TO ℤ₉ BACKEND ---")
                }

                // Listener for incoming shell data
                val buffer = ByteArray(4096)
                while (newChannel.isConnected) {
                    if (inputStream.available() > 0) {
                        val i = inputStream.read(buffer, 0, 4096)
                        if (i < 0) break
                        val response = String(buffer, 0, i)
                        withContext(Dispatchers.Main) {
                            terminalLines.add(response.trim())
                        }
                    }
                    delay(50)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    terminalLines.add("CONNECTION ERROR: ${e.message}")
                }
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // Header
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "ℤ₉ AGENTIC OS",
                color = NeonBlue,
                style = MaterialTheme.typography.headlineSmall.copy(
                    fontWeight = FontWeight.ExtraBold,
                    letterSpacing = 4.sp
                )
            )
        }

        // Terminal Window
        TerminalOutputWindow(terminalLines)

        // Prompt Bar (Chatbot style)
        PromptBar(
            value = prompt,
            onValueChange = { prompt = it },
            onSend = {
                if (prompt.isNotBlank()) {
                    val cmd = prompt
                    coroutineScope.launch(Dispatchers.IO) {
                        try {
                            outputStream?.write((cmd + "\n").toByteArray())
                            outputStream?.flush()
                        } catch (e: Exception) {
                            withContext(Dispatchers.Main) {
                                terminalLines.add("SEND ERROR: ${e.message}")
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
fun ColumnScope.TerminalOutputWindow(lines: List<String>) {
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
            .padding(8.dp)
            .border(1.dp, NeonBlue.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
            .background(DarkGrey, RoundedCornerShape(8.dp))
            .padding(12.dp)
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
                    fontSize = 12.sp,
                    modifier = Modifier.padding(vertical = 1.dp)
                )
            }
        }
    }
}

@Composable
fun PromptBar(
    value: String,
    onValueChange: (String) -> Unit,
    onSend: () -> Unit
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
                .height(56.dp)
                .border(1.dp, NeonBlue, RoundedCornerShape(28.dp))
                .background(DarkGrey, RoundedCornerShape(28.dp))
                .padding(horizontal = 20.dp),
            contentAlignment = Alignment.CenterStart
        ) {
            if (value.isEmpty()) {
                Text(
                    text = "Execute Z9 command...",
                    color = NeonBlue.copy(alpha = 0.5f),
                    fontFamily = FontFamily.Monospace
                )
            }
            BasicTextField(
                value = value,
                onValueChange = onValueChange,
                textStyle = TextStyle(
                    color = NeonBlue,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 16.sp
                ),
                cursorBrush = SolidColor(NeonBlue),
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send)
            )
        }

        Spacer(modifier = Modifier.width(8.dp))

        IconButton(
            onClick = onSend,
            modifier = Modifier
                .size(56.dp)
                .background(NeonBlue, RoundedCornerShape(28.dp))
        ) {
            Icon(
                imageVector = Icons.Default.Send,
                contentDescription = "Send",
                tint = DeepBlack
            )
        }
    }
}
