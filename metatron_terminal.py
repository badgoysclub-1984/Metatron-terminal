#!/usr/bin/env python3
import sys
import os
import threading
import time
import re
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLineEdit, QPlainTextEdit, QPushButton, QLabel,
    QSplitter, QFrame, QInputDialog
)
import paramiko

# ANSI Escape sequence filter
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def filter_ansi(text):
    return ANSI_ESCAPE.sub('', text)

class SSHWorker(QObject):
    output_received = pyqtSignal(str, str)  # node_id, text
    status_changed = pyqtSignal(str, str)   # node_id, status

    def __init__(self, node_id, ip, username, password):
        super().__init__()
        self.node_id = node_id
        self.ip = ip
        self.username = username
        self.password = password
        self.client = None
        self.shell = None
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            self.status_changed.emit(self.node_id, "Connecting...")
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.ip, username=self.username, password=self.password, timeout=10)
            
            self.shell = self.client.invoke_shell(term='xterm', width=80, height=24)
            self.status_changed.emit(self.node_id, f"CONNECTED: {self.ip}")
            
            while self.running:
                if self.shell.recv_ready():
                    data = self.shell.recv(4096)
                    if not data:
                        break
                    text = data.decode('utf-8', errors='replace')
                    self.output_received.emit(self.node_id, text)
                else:
                    time.sleep(0.02)
            
            self.status_changed.emit(self.node_id, "Disconnected")
        except Exception as e:
            self.status_changed.emit(self.node_id, f"Error: {str(e)}")
            self.running = False

    def send(self, cmd):
        if self.shell and self.running:
            try:
                self.shell.send(cmd + "\n")
            except Exception:
                pass

    def stop(self):
        self.running = False
        if self.client:
            try:
                self.client.close()
            except:
                pass

class TerminalPane(QFrame):
    def __init__(self, node_id, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        # NEON BLUE BORDER
        self.setStyleSheet("background: #000; border: 1px solid #00f0ff; border-radius: 4px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # NEON PURPLE STATUS
        self.status_label = QLabel(f"Node {node_id}: Offline")
        self.status_label.setStyleSheet("color: #bc13fe; font-weight: bold; font-size: 11px; font-family: 'Courier New';")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        self.clear_btn = QPushButton("CLR")
        self.clear_btn.setFixedSize(40, 18)
        # NEON ORANGE BUTTONS
        self.clear_btn.setStyleSheet("font-size: 8px; background: #222; color: #ff6700; border: 1px solid #ff6700;")
        self.clear_btn.clicked.connect(lambda: self.output.clear())
        header_layout.addWidget(self.clear_btn)
        
        layout.addWidget(self.header)
        
        # Terminal Output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Monospace", 10))
        # WHITE TEXT
        self.output.setStyleSheet("background: #000; color: #ffffff; border: none;")
        # Prevent scroll bars from inheriting weird styles
        self.output.verticalScrollBar().setStyleSheet("background: #111;")
        layout.addWidget(self.output)
        
        # Input Area
        self.input_area = QWidget()
        input_layout = QHBoxLayout(self.input_area)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input = QLineEdit()
        # WHITE TEXT, NEON BLUE BORDER
        self.input.setStyleSheet("background: #111; color: #ffffff; border: 1px solid #00f0ff; padding: 4px;")
        self.input.setPlaceholderText("Command...")
        self.input.returnPressed.connect(self.send_command)
        input_layout.addWidget(self.input)

        # SEND BUTTON (NEON ORANGE)
        self.send_btn = QPushButton("SEND")
        self.send_btn.setFixedWidth(60)
        self.send_btn.setStyleSheet("background: #ff6700; color: #000; font-weight: bold; padding: 4px;")
        self.send_btn.clicked.connect(self.send_command)
        input_layout.addWidget(self.send_btn)
        
        self.connect_btn = QPushButton("CONNECT")
        self.connect_btn.setFixedWidth(100)
        # NEON ORANGE BUTTON
        self.connect_btn.setStyleSheet("background: #ff6700; color: #000; font-weight: bold; padding: 4px;")
        self.connect_btn.clicked.connect(self.show_connect_dialog)
        input_layout.addWidget(self.connect_btn)
        
        layout.addWidget(self.input_area)
        
        self.worker = None

    def styled_input(self, title, label, echo=QLineEdit.Normal, default=""):
        dlg = QInputDialog(self)
        dlg.setWindowTitle(title)
        dlg.setLabelText(label)
        dlg.setTextValue(default)
        dlg.setTextEchoMode(echo)
        # Force visibility for dark theme
        dlg.setStyleSheet("QWidget { background-color: #111; color: #00f0ff; } QLineEdit { background-color: #222; color: #fff; border: 1px solid #00f0ff; } QPushButton { background-color: #00f0ff; color: #000; }")
        if dlg.exec_() == QInputDialog.Accepted:
            return dlg.textValue(), True
        return "", False

    def show_connect_dialog(self):
        ip, ok = self.styled_input("Connect Node", "IP Address:", QLineEdit.Normal, "192.168.1.56")
        if ok and ip:
            user, ok = self.styled_input("Connect Node", "Username:", QLineEdit.Normal, "pi")
            if ok and user:
                password, ok = self.styled_input("Connect Node", "Password:", QLineEdit.Password, "Rebel23!")
                if ok:
                    self.start_ssh(ip, user, password)

    def start_ssh(self, ip, username, password):
        if self.worker:
            self.worker.stop()
        
        self.output.appendPlainText(f"--- INITIALIZING SESSION TO {ip} ---")
        self.worker = SSHWorker(self.node_id, ip, username, password)
        self.worker.output_received.connect(self.append_output)
        self.worker.status_changed.connect(self.update_status)
        self.worker.start()
        
        # UI Update
        self.connect_btn.setText("DISCONNECT")
        self.connect_btn.setStyleSheet("background: #f00; color: #fff; font-weight: bold; padding: 4px;")
        try: self.connect_btn.clicked.disconnect()
        except: pass
        self.connect_btn.clicked.connect(self.stop_ssh)

    def stop_ssh(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.update_status(self.node_id, "Offline")
        self.connect_btn.setText("CONNECT")
        self.connect_btn.setStyleSheet("background: #00f0ff; color: #000; font-weight: bold; padding: 4px;")
        try: self.connect_btn.clicked.disconnect()
        except: pass
        self.connect_btn.clicked.connect(self.show_connect_dialog)
        self.output.appendPlainText("\n--- SESSION TERMINATED ---")

    def append_output(self, node_id, text):
        # Basic terminal handling: normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Filter ANSI codes for clean QPlainTextEdit display
        clean_text = filter_ansi(text)
        if clean_text:
            self.output.insertPlainText(clean_text)
            self.output.moveCursor(QTextCursor.End)

    def update_status(self, node_id, status):
        self.status_label.setText(f"Node {node_id}: {status}")

    def send_command(self):
        cmd = self.input.text()
        if self.worker:
            self.worker.send(cmd)
        else:
            self.output.appendPlainText("Error: Node not connected.")
        self.input.clear()

class MetatronTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧿 METATRON TERMINAL v3.1")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background: rgba(1, 4, 9, 0.95);")
        
        # Position and Size
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width()//8, screen.height()//8, 1200, 800)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(2, 2, 2, 2)
        
        # Custom Title Bar
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(35)
        self.title_bar.setStyleSheet("background: #000; border-bottom: 2px solid #00f0ff;")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(15, 0, 15, 0)
        
        self.title_label = QLabel("🧿 METATRON MULTI-NODE HIVE TERMINAL")
        self.title_label.setStyleSheet("color: #00f0ff; font-weight: 900; letter-spacing: 3px; font-size: 14px;")
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        self.layout_btn = QPushButton("GRID LAYOUT")
        self.layout_btn.setStyleSheet("color: #00f0ff; background: #111; border: 1px solid #00f0ff; padding: 4px 15px; font-weight: bold;")
        self.layout_btn.clicked.connect(self.toggle_layout)
        title_layout.addWidget(self.layout_btn)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setStyleSheet("color: #f00; background: transparent; border: none; font-size: 20px; font-weight: bold;")
        self.close_btn.clicked.connect(self.close)
        title_layout.addWidget(self.close_btn)
        
        self.layout.addWidget(self.title_bar)
        
        # Terminal Grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(8)
        self.layout.addWidget(self.grid_container)
        
        self.panes = []
        for i in range(4):
            pane = TerminalPane(str(i+1))
            self.panes.append(pane)
        
        self.current_layout = 4
        self.update_layout()

        # Draggable
        self.dragging = False
        self.drag_position = None

    def toggle_layout(self):
        if self.current_layout == 4:
            self.current_layout = 1
        elif self.current_layout == 1:
            self.current_layout = 2
        else:
            self.current_layout = 4
        self.update_layout()

    def update_layout(self):
        # Clear current grid
        for i in reversed(range(self.grid_layout.count())): 
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
            
        if self.current_layout == 1:
            self.grid_layout.addWidget(self.panes[0], 0, 0)
            for i in range(1, 4): self.panes[i].hide()
            self.panes[0].show()
        elif self.current_layout == 2:
            self.grid_layout.addWidget(self.panes[0], 0, 0)
            self.grid_layout.addWidget(self.panes[1], 0, 1)
            for i in range(2, 4): self.panes[i].hide()
            self.panes[0].show()
            self.panes[1].show()
        else:
            self.grid_layout.addWidget(self.panes[0], 0, 0)
            self.grid_layout.addWidget(self.panes[1], 0, 1)
            self.grid_layout.addWidget(self.panes[2], 1, 0)
            self.grid_layout.addWidget(self.panes[3], 1, 1)
            for i in range(4): self.panes[i].show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.geometry().contains(event.pos()):
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Ensure tooltips/dialogs don't look weird
    app.setStyle("Fusion")
    window = MetatronTerminal()
    window.show()
    sys.exit(app.exec_())
