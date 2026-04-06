#!/usr/bin/env python3
import sys
import os
from PyQt5.QtCore import QUrl, Qt, QPoint
from PyQt5.QtGui import QColor, QMouseEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView

class OverlayApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Make the window frameless, stay on top, and behave like an overlay
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.X11BypassWindowManagerHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Position at the bottom right initially
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        w, h = 1000, 600
        x = screen_geometry.width() - w - 20
        y = screen_geometry.height() - h - 20
        self.setGeometry(x, y, w, h)

        # Central widget with transparent background
        central_widget = QWidget()
        central_widget.setStyleSheet("background: transparent;")
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Add a custom draggable title bar for the overlay
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(24)
        self.title_bar.setStyleSheet("background: rgba(0, 240, 255, 0.2); border-radius: 4px 4px 0 0;")
        
        tb_layout = QVBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("color: white; background: transparent; border: none; font-weight: bold;")
        self.close_btn.clicked.connect(self.close)
        tb_layout.addWidget(self.close_btn, alignment=Qt.AlignRight)
        
        layout.addWidget(self.title_bar)
        
        # Web View
        self.browser = QWebEngineView()
        self.browser.page().setBackgroundColor(Qt.transparent)
        self.browser.load(QUrl("http://127.0.0.1:5000"))
        
        layout.addWidget(self.browser)
        
        # Drag state
        self.dragging = False
        self.drag_position = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.title_bar.geometry().contains(event.pos()):
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging = False

if __name__ == "__main__":
    # Ensure High DPI scaling is supported
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # Optional: ensure we can load localhost immediately
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-web-security"
    
    window = OverlayApp()
    window.show()
    sys.exit(app.exec_())
