import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QApplication, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QFont, QPainter, QCursor

import history
import sys

class HistoryItemWidget(QFrame):
    """Custom widget for a single history item."""
    def __init__(self, text: str, timestamp: float, parent=None):
        super().__init__(parent)
        self.text_content = text
        self.setObjectName("HistoryItem")
        self.setStyleSheet("""
            #HistoryItem {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(35, 35, 35, 0.5), 
                    stop:1 rgba(15, 15, 15, 0.7));
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                margin-bottom: 6px;
            }
            #HistoryItem:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        # Header (Time + Copy button)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%I:%M %p")
        if dt.date() != datetime.now().date():
            time_str = dt.strftime("%b %d, %I:%M %p")
            
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #888888; font-size: 11px;")
        
        copy_btn = QPushButton("Copy")
        copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #48C774;
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                color: #5deb8b;
            }
        """)
        copy_btn.clicked.connect(self._copy_text)
        self.copy_btn = copy_btn
        
        header_layout.addWidget(time_label)
        header_layout.addStretch()
        header_layout.addWidget(copy_btn)
        
        # Text content
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("color: white; font-size: 13px; line-height: 1.4;")
        
        layout.addLayout(header_layout)
        layout.addWidget(text_label)

    def _copy_text(self):
        cb = QApplication.clipboard()
        cb.setText(self.text_content)
        self.copy_btn.setText("Copied!")
        self.copy_btn.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, self._reset_copy_btn)
        
    def _reset_copy_btn(self):
        self.copy_btn.setText("Copy")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #48C774;
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                color: #5deb8b;
            }
        """)

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transcription History")
        self.setFixedSize(380, 500)
        
        # Frameless window styling like settings
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint
        # Animations
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(600)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutQuint)
        
        # 1. Apply Dark Mode IMMEDIATELY to prevent white flash
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
            except: pass

        self.setup_ui()
        self.load_history()
        
        # For dragging
        self.dragPos = None

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Background frame
        self.bg_frame = QFrame(self)
        self.bg_frame.setObjectName("bgFrame")
        self.bg_frame.setStyleSheet("""
            #bgFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.08), 
                    stop:1 rgba(255, 255, 255, 0.03));
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-top: 1px solid rgba(255, 255, 255, 0.25); /* Glass Edge Highlight */
            }
        """)
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 15, 0)
        
        title = QLabel("Transcription History")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                color: white;
                background-color: #e81123;
                border-radius: 15px;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
                outline: none;
            }
            QListWidget::item {
                background: transparent;
            }
            QListWidget::item:selected {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                min-height: 40px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #10b981; /* Emerald Green */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        
        bg_layout.addWidget(header)
        bg_layout.addWidget(self.list_widget)
        
        main_layout.addWidget(self.bg_frame)
        
        # DWM fix for Windows 11 borders and Acrylic Blur
        import platform
        if platform.system() == "Windows":
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._apply_windows_11_styles)

    def showEvent(self, event):
        super().showEvent(event)
        
        # Play entry animation
        from PyQt6.QtCore import QPoint
        end_pos = self.pos()
        start_pos = QPoint(end_pos.x(), end_pos.y() + 50)
        
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(end_pos)
        
        self.setWindowOpacity(0)
        self._fade_anim.setStartValue(0)
        self._fade_anim.setEndValue(1.0)
        
        self._slide_anim.start()
        self._fade_anim.start()

    def _apply_windows_11_styles(self):
        """Use a tiny delay to ensure the window is ready for the DWM blur engine."""
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(5, self._force_glass_now)

    def _force_glass_now(self):
        try:
            import ctypes
            hwnd = int(self.winId())
            
            # Force Immersive Dark Mode
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), 4)

            # Use Original Mica (Value 2) - The smoothest, most elegant material
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(ctypes.c_int(2)), 4)
            
            # Native Rounding
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)

        except Exception as e:
            print(f"[History] Fluent Glass failed: {e}")

    def load_history(self):
        entries = history.get_history()
        self.list_widget.clear()
        
        if not entries:
            item = QListWidgetItem(self.list_widget)
            label = QLabel("No transcriptions yet.")
            label.setStyleSheet("color: #888888; font-size: 13px; text-align: center; margin-top: 20px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(label.sizeHint())
            self.list_widget.setItemWidget(item, label)
            return
            
        for entry in entries:
            # We add them as widgets to the list
            widget = HistoryItemWidget(entry["text"], entry["timestamp"])
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.setItemWidget(item, widget)

    # Window dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() < 60:
            self.dragPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.dragPos is not None:
            delta = event.globalPosition().toPoint() - self.dragPos
            self.move(self.pos() + delta)
            self.dragPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.dragPos = None
