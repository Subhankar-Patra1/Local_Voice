"""
Voice-to-Text Overlay Window — PyQt6 Modern UI.
"""

import sys
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, pyqtSlot, QTimer, QPropertyAnimation, QEvent, QEasingCurve, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPainterPath, QPen, QIcon

# Colors
BG_COLOR = QColor(24, 24, 27, 240)        # Dark charcoal, slight transparency
ACCENT_COLOR = "#10b981"                  # Emerald green
ACCENT_HOVER = "#059669"
DANGER_COLOR = "#ef4444"                  # Red
DANGER_HOVER = "#dc2626"
WARNING_COLOR = "#f59e0b"                 # Amber
TEXT_COLOR = "#f4f4f5"                    # Very light grey
TEXT_MUTED = "#a1a1aa"                    # Muted grey

FONT_FAMILY = "Segoe UI Variable Display" if sys.platform == "win32" else "SF Pro Display" if sys.platform == "darwin" else "Inter"

WIDTH = 300
HEIGHT_IDLE = 150
HEIGHT_RECORD = 150
FADED_OPACITY = 0.35       # Semi-transparent when not focused
FULL_OPACITY = 1.0
FADE_DURATION_MS = 200     # Smooth fade animation duration

# Create QApplication instance if it doesn't exist
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)
    app.setFont(QFont(FONT_FAMILY, 10))

class OverlayWindow(QWidget):
    """Voice-to-Text overlay with modern PyQt6 UI."""
    
    # Define signals for thread-safe UI updates
    sig_show_idle = pyqtSignal(str, str, bool)
    sig_show_need_download = pyqtSignal(str)
    sig_show_downloading = pyqtSignal(float, str)
    sig_show_recording = pyqtSignal(str)
    sig_update_transcription = pyqtSignal(str)
    sig_set_transcription_text = pyqtSignal(str)
    sig_show_stopping = pyqtSignal()
    sig_show_done = pyqtSignal(str)
    sig_toggle_visibility = pyqtSignal()
    sig_destroy = pyqtSignal()

    def __init__(self, on_start=None, on_stop=None, on_download=None, on_quit=None, on_settings=None):
        super().__init__()
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_download = on_download
        self.on_quit = on_quit
        self.on_settings = on_settings

        # Setup Window Flags for frameless, floating overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._pos_file = Path.home() / ".config" / "voice-to-text" / "overlay_pos.json"
        self._drag_pos = None

        self._dot_count = 0
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._animate_dots)

        # Animations
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(FADE_DURATION_MS)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(600)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutQuint)
        
        self._is_faded = False

        self._build_ui()
        self._connect_signals()
        self._position_window(force_center=True)
        
        # Set Window Icon
        logo_path = str(Path(__file__).parent / "assets" / "logo.svg")
        self.setWindowIcon(QIcon(logo_path))
        
        self.setCursor(Qt.CursorShape.SizeAllCursor) 
        self.show()

        # Windows 11 DWM forces a 1px border on ALL windows.
        # We remove it and apply Acrylic blur (frosted glass).
        if sys.platform == "win32":
            self._apply_windows_11_styles()

    def showEvent(self, event):
        """Play entry animation when window is shown."""
        super().showEvent(event)
        
        # Start position: slightly below final position
        end_pos = self.pos()
        start_pos = QPoint(end_pos.x(), end_pos.y() + 30)
        
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(end_pos)
        
        self.setWindowOpacity(0)
        self._fade_anim.setStartValue(0)
        self._fade_anim.setEndValue(FULL_OPACITY)
        
        self._slide_anim.start()
        self._fade_anim.start()

    def _apply_windows_11_styles(self):
        """Use a small delay to ensure the window is ready for the DWM blur engine."""
        QTimer.singleShot(100, self._force_glass_now)

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
            print(f"[Overlay] Fluent Glass failed: {e}")

    def _build_ui(self):
        self.resize(WIDTH, HEIGHT_IDLE)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Background Frame (Glassmorphism Pill)
        self.bg_frame = QFrame(self)
        self.bg_frame.setObjectName("bgFrame")
        self.bg_frame.setStyleSheet("""
            QFrame#bgFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(0, 0, 0, 0.85), 
                    stop:0.4 rgba(0, 0, 0, 0.6),
                    stop:1 rgba(0, 0, 0, 0.2));
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-top: 1px solid rgba(255, 255, 255, 0.25); /* Glass Edge Highlight */
            }
        """)

        self.bg_layout = QVBoxLayout(self.bg_frame)
        self.bg_layout.setContentsMargins(16, 16, 16, 16)
        self.bg_layout.setSpacing(8)

        # Top Bar Layout (Settings ⚙ + Title + Close ✕)
        self.top_bar_layout = QHBoxLayout()
        self.top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_btn_style = f"""
            QPushButton {{
                color: {TEXT_MUTED};
                background: transparent;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }}
        """

        # Settings Gear Button (left side)
        left_layout = QHBoxLayout()
        self.settings_btn = QPushButton()
        
        # Load SVG icon
        icon_path = str(Path(__file__).parent / "assets" / "settings.svg")
        self.settings_btn.setIcon(QIcon(icon_path))
        self.settings_btn.setIconSize(QSize(16, 16))
        
        self.settings_btn.setFixedSize(24, 24)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settings_btn.setStyleSheet(icon_btn_style)
        self.settings_btn.clicked.connect(self._on_settings_click)
        left_layout.addWidget(self.settings_btn)
        left_layout.addStretch(1)
        self.top_bar_layout.addLayout(left_layout, 1)

        # Title with Logo
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        logo_path = str(Path(__file__).parent / "assets" / "logo.svg")
        self.logo_label = QLabel()
        logo_pixmap = QIcon(logo_path).pixmap(20, 20)
        self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.status_label = QLabel("Local <span style='color: #2ecc71'>Voice</span>")
        font_title = QFont("Segoe UI Variable Display", 13, QFont.Weight.Bold)
        if not font_title.exactMatch():
            font_title = QFont(FONT_FAMILY, 13, QFont.Weight.Bold)
        self.status_label.setFont(font_title)
        self.status_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; border: none; letter-spacing: 0.5px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        title_layout.addStretch()
        title_layout.addWidget(self.logo_label)
        title_layout.addWidget(self.status_label)
        title_layout.addStretch()
        
        self.top_bar_layout.addLayout(title_layout, 2)
        
        # Close Button (right side)
        right_layout = QHBoxLayout()
        right_layout.addStretch(1)
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.setStyleSheet(icon_btn_style)
        self.close_btn.clicked.connect(self._on_close_click)
        right_layout.addWidget(self.close_btn)
        
        self.top_bar_layout.addLayout(right_layout, 1)
        self.bg_layout.addLayout(self.top_bar_layout)

        # Info/Subtitle
        self.info_label = QLabel("Click to start")
        font_info = QFont(FONT_FAMILY, 10)
        self.info_label.setFont(font_info)
        self.info_label.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; border: none;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        self.info_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.bg_layout.addWidget(self.info_label)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #27272a;
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT_COLOR};
                border-radius: 3px;
            }}
        """)
        self.progress_bar.hide()
        self.bg_layout.addWidget(self.progress_bar)

        # Transcription Text
        self.transcription_label = QLabel("")
        font_trans = QFont(FONT_FAMILY, 13)
        self.transcription_label.setFont(font_trans)
        self.transcription_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; border: none;")
        self.transcription_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transcription_label.setWordWrap(True)
        self.transcription_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.transcription_label.hide()
        self.bg_layout.addWidget(self.transcription_label)

        self.bg_layout.addStretch()

        # Action Button
        self.action_btn = QPushButton("Start Listening")
        self.action_btn.setFixedHeight(40)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2ecc71, 
                    stop:1 #1b5e20);
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #34e17e, 
                    stop:1 #237a2a);
            }}
            QPushButton:pressed {{
                background: #1b5e20;
            }}
        """)
        self.action_btn.clicked.connect(self._on_action_click)
        self.bg_layout.addWidget(self.action_btn)

        # Update Badge (Hidden by default)
        self.update_btn = QPushButton("✨ Update Available")
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.update_btn.setStyleSheet("""
            QPushButton {
                color: #5deb8b;
                background-color: transparent;
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding-top: 5px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self.update_btn.hide()
        self.update_btn.clicked.connect(self._on_update_click)
        self.bg_layout.addWidget(self.update_btn)

        self.main_layout.addWidget(self.bg_frame)
        self._style_button("#2ecc71", "#1b5e20", "#34e17e", "#237a2a")
        
    def _on_update_click(self):
        if hasattr(self, '_update_url') and self._update_url:
            from updater import open_url
            open_url(self._update_url)

    def show_update_available(self, version: str, url: str) -> None:
        """Called from the main thread when an update is found."""
        self._update_url = url
        self.update_btn.setText(f"✨ Update {version} Available")
        self.update_btn.show()

    def _style_button(self, color_top, color_bottom, hover_top, hover_bottom):
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {color_top}, 
                    stop:1 {color_bottom});
                color: white;
                border-radius: 20px;
                padding: 0 24px;
                border: none;
                margin: 0 16px;
                font-size: 15px;
                font-weight: 600;
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {hover_top}, 
                    stop:1 {hover_bottom});
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            QPushButton:pressed {{
                background: {color_bottom};
            }}
        """)

    def _connect_signals(self):
        self.sig_show_idle.connect(self._set_idle)
        self.sig_show_need_download.connect(self._set_need_download)
        self.sig_show_downloading.connect(self._set_downloading)
        self.sig_show_recording.connect(self._set_recording)
        self.sig_update_transcription.connect(self._set_transcription_text)
        self.sig_set_transcription_text.connect(self._set_transcription_text)
        self.sig_show_stopping.connect(self._set_stopping)
        self.sig_show_done.connect(self._set_done)
        self.sig_toggle_visibility.connect(self._toggle_visibility)
        self.sig_destroy.connect(self._destroy)

    def _position_window(self, force_center=False):
        x, y = self._load_position()
        if x is None or force_center:
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - WIDTH) // 2
            y = (screen.height() - HEIGHT_IDLE) // 2
        self.move(x, y)

    def _load_position(self):
        try:
            if self._pos_file.exists():
                data = json.loads(self._pos_file.read_text())
                return data.get("x"), data.get("y")
        except Exception:
            pass
        return None, None

    def _save_position(self):
        try:
            self._pos_file.parent.mkdir(parents=True, exist_ok=True)
            self._pos_file.write_text(json.dumps({
                "x": self.x(),
                "y": self.y()
            }))
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Fade in if currently faded
            if self._is_faded:
                self._fade_in()
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def enterEvent(self, event):
        """Mouse entered overlay area — fade in."""
        if self._is_faded:
            self._fade_in()
        super().enterEvent(event)

    def changeEvent(self, event):
        """Detect when overlay loses focus (user clicked another window)."""
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow() and not self._is_faded:
                self._fade_out()
        super().changeEvent(event)

    def _fade_out(self):
        """Smoothly fade overlay to near-invisible."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(FADED_OPACITY)
        self._fade_anim.start()
        self._is_faded = True

    def _fade_in(self):
        """Smoothly fade overlay back to fully visible."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(FULL_OPACITY)
        self._fade_anim.start()
        self._is_faded = False

    def closeEvent(self, event):
        self._save_position()
        event.accept()

    def _on_action_click(self):
        text = self.action_btn.text()
        if text in ("Start Listening", "Start") and self.on_start:
            self.on_start()
        elif text == "Stop Listening" and self.on_stop:
            self.on_stop()
        elif text.startswith("Download") and self.on_download:
            self.on_download()

    def _on_close_click(self):
        """Hide overlay — app stays alive in system tray.
        Use 'Quit Application' from tray menu to fully exit."""
        self.hide()

    def _on_settings_click(self):
        if self.on_settings:
            self.on_settings()
            
    def _animate_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        if self._dot_count == 0:
            self._dot_count = 1
        dots = "." * self._dot_count
        self.transcription_label.setText(dots)

    # Public Methods
    def show_idle(self, message: str = "Click to start", button_text: str = "Start Listening", show_button: bool = True):
        self.sig_show_idle.emit(message, button_text, show_button)

    def show_need_download(self, model_name: str):
        self.sig_show_need_download.emit(model_name)

    def show_downloading(self, percent: float, message: str = ""):
        self.sig_show_downloading.emit(percent, message)

    def show_recording(self, text: str = ""):
        self.sig_show_recording.emit(text)

    def update_transcription(self, text: str):
        self.sig_update_transcription.emit(text)

    def set_transcription_text(self, text: str):
        self.sig_set_transcription_text.emit(text)

    def show_stopping(self):
        self.sig_show_stopping.emit()

    def show_done(self, text: str):
        self.sig_show_done.emit(text)

    def toggle_visibility(self):
        self.sig_toggle_visibility.emit()

    def destroy(self):
        self.sig_destroy.emit()

    # Internal Slots
    @pyqtSlot(str, str, bool)
    def _set_idle(self, message, button_text, show_button):
        self._dot_timer.stop()
        self.status_label.setText("Local <span style='color: #2ecc71'>Voice</span>")
        self.status_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; border: none;")
        self.info_label.setText(message)
        self.info_label.show()

        self.transcription_label.hide()
        self.progress_bar.hide()

        self.action_btn.setText(button_text)
        self._style_button("#2ecc71", "#1b5e20", "#34e17e", "#237a2a")
        self.action_btn.setVisible(show_button)
        
        self.resize(WIDTH, HEIGHT_IDLE)

    @pyqtSlot(str)
    def _set_need_download(self, model_name):
        self.status_label.setText("Model Required")
        self.status_label.setStyleSheet(f"color: {WARNING_COLOR}; background: transparent; border: none;")
        self.info_label.setText(f"Model '{model_name}' not found.")
        self.info_label.show()

        self.transcription_label.hide()
        self.progress_bar.hide()

        self.action_btn.setText(f"Download {model_name}")
        self._style_button(WARNING_COLOR, "#b45309", "#fbbf24", "#d97706")
        self.action_btn.show()
        
        self.resize(WIDTH, HEIGHT_IDLE)

    @pyqtSlot(float, str)
    def _set_downloading(self, percent, message):
        self.status_label.setText("⬇ Downloading Model...")
        self.status_label.setStyleSheet(f"color: {WARNING_COLOR}; background: transparent; border: none;")
        self.info_label.setText(message if message else "Requires internet · ~1.5 GB download")
        self.info_label.show()

        self.transcription_label.hide()
        self.action_btn.hide()

        self.progress_bar.setValue(int(percent))
        self.progress_bar.show()
        
        self.resize(WIDTH, HEIGHT_RECORD)

    @pyqtSlot(str)
    def _set_recording(self, text):
        self.status_label.setText("Listening...")
        self.status_label.setStyleSheet(f"color: {DANGER_COLOR}; background: transparent; border: none;")
        self.info_label.hide()
        self.progress_bar.hide()

        if text:
            self._dot_timer.stop()
            self.transcription_label.setText(text)
        else:
            self._dot_count = 0
            self.transcription_label.setText(".")
            self._dot_timer.start(500)

        self.transcription_label.show()

        self.action_btn.setText("Stop Listening")
        self._style_button("#ef4444", "#7f1d1d", "#f87171", "#991b1b")
        self.action_btn.show()
        
        self.resize(WIDTH, HEIGHT_RECORD)

    @pyqtSlot(str)
    def _set_transcription_text(self, text):
        if text and text != "...":
            self._dot_timer.stop()
            self.transcription_label.setText(text)
        elif text == "...":
            self._dot_count = 0
            self.transcription_label.setText(".")
            self._dot_timer.start(500)

    @pyqtSlot()
    def _set_stopping(self):
        self._dot_timer.stop()
        self.status_label.setText("Stopping...")
        self.status_label.setStyleSheet(f"color: {WARNING_COLOR}; background: transparent; border: none;")
        self.info_label.setText("Please wait...")
        self.info_label.show()

        self.transcription_label.hide()
        self.progress_bar.hide()
        self.action_btn.hide()
        
        self.resize(WIDTH, HEIGHT_IDLE)

    @pyqtSlot(str)
    def _set_done(self, text):
        self._dot_timer.stop()
        self.status_label.setText("Done")
        self.status_label.setStyleSheet(f"color: {ACCENT_COLOR}; background: transparent; border: none;")
        self.info_label.hide()
        self.progress_bar.hide()

        self.transcription_label.setText(text)
        self.transcription_label.show()

        self.action_btn.setText("Start Listening")
        self._style_button("#2ecc71", "#1b5e20", "#34e17e", "#237a2a")
        self.action_btn.show()
        
        self.resize(WIDTH, HEIGHT_RECORD)

    @pyqtSlot()
    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    @pyqtSlot()
    def _destroy(self):
        self.close()
