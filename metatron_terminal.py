#!/usr/bin/env python3
import sys
import os
import threading
import queue
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QFont, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLineEdit, QPlainTextEdit, QPushButton, QLabel,
    QSplitter, QFrame
)
import paramiko

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
            self.status_changed.emit(self.node_id, f"Connected to {self.ip}")
            
            while self.running:
                if self.shell.recv_ready():
                    data = self.shell.recv(1024).decode('utf-8', errors='replace')
                    if data:
                        self.output_received.emit(self.node_id, data)
                else:
                    threading.Event().wait(0.01)
        except Exception as e:
            self.status_changed.emit(self.node_id, f"Error: {str(e)}")
            self.running = False

    def send(self, cmd):
        if self.shell and self.running:
            self.shell.send(cmd + "\n")

    def stop(self):
        self.running = False
        if self.client:
            self.client.close()

class TerminalPane(QFrame):
    def __init__(self, node_id, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setStyleSheet("background: #000; border: 1px solid #00f0ff; border-radius: 4px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel(f"Node {node_id}: Offline")
        self.status_label.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 10px;")
        header_layout.addWidget(self.status_label)
        
        layout.addWidget(self.header)
        
        # Terminal Output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Monospace", 10))
        self.output.setStyleSheet("background: #000; color: #00f0ff; border: none;")
        layout.addWidget(self.output)
        
        # Input Area
        self.input_area = QWidget()
        input_layout = QHBoxLayout(self.input_area)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input = QLineEdit()
        self.input.setStyleSheet("background: #111; color: #fff; border: 1px solid #333;")
        self.input.setPlaceholderText("Enter command...")
        self.input.returnPressed.connect(self.send_command)
        input_layout.addWidget(self.input)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("background: #00f0ff; color: #000; font-weight: bold;")
        self.connect_btn.clicked.connect(self.show_connect_dialog)
        input_layout.addWidget(self.connect_btn)
        
        layout.addWidget(self.input_area)
        
        self.worker = None

    def show_connect_dialog(self):
        # For simplicity, we'll just hardcode or use a simple prompt
        # In a real app, this would be a dialog
        from PyQt5.QtWidgets import QInputDialog
        ip, ok = QInputDialog.getText(self, "Connect Node", "IP Address:", QLineEdit.Normal, "192.168.1.56")
        if ok and ip:
            password, ok = QInputDialog.getText(self, "Connect Node", "Password:", QLineEdit.Password, "Rebel23!")
            if ok:
                self.start_ssh(ip, "pi", password)

    def start_ssh(self, ip, username, password):
        if self.worker:
            self.worker.stop()
        
        self.worker = SSHWorker(self.node_id, ip, username, password)
        self.worker.output_received.connect(self.append_output)
        self.worker.status_changed.connect(self.update_status)
        self.worker.start()
        self.connect_btn.setText("Disconnect")
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.stop_ssh)

    def stop_ssh(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.update_status(self.node_id, "Offline")
        self.connect_btn.setText("Connect")
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.show_connect_dialog)

    def append_output(self, node_id, text):
        self.output.insertPlainText(text)
        self.output.moveCursor(QTextCursor.End)

    def update_status(self, node_id, status):
        self.status_label.setText(f"Node {node_id}: {status}")

    def send_command(self):
        cmd = self.input.text()
        if self.worker:
            self.worker.send(cmd)
        self.input.clear()

class MetatronTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧿 METATRON TERMINAL v3.1")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background: rgba(1, 4, 9, 0.9);")
        
        # Position and Size
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width()//4, screen.height()//4, 1200, 800)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Custom Title Bar
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet("background: #000; border-bottom: 1px solid #00f0ff;")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        
        self.title_label = QLabel("METATRON MULTI-NODE TERMINAL")
        self.title_label.setStyleSheet("color: #00f0ff; font-weight: 900; letter-spacing: 2px;")
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        self.layout_btn = QPushButton("LAYOUT")
        self.layout_btn.setStyleSheet("color: #00f0ff; background: transparent; border: 1px solid #00f0ff; padding: 2px 10px;")
        self.layout_btn.clicked.connect(self.toggle_layout)
        title_layout.addWidget(self.layout_btn)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setStyleSheet("color: #f00; background: transparent; border: none; font-size: 16px;")
        self.close_btn.clicked.connect(self.close)
        title_layout.addWidget(self.close_btn)
        
        self.layout.addWidget(self.title_bar)
        
        # Terminal Grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
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
            self.grid_layout.itemAt(i).widget().setParent(None)
            
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
    window = MetatronTerminal()
    window.show()
    sys.exit(app.exec_())
