"""
First-run Model Selector — Fullscreen-style model picker shown on first launch.

Displays all available Whisper models with sizes, speed/accuracy ratings,
and download status. User picks one, and it is downloaded before proceeding.
"""

import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen

import model_manager

# Design tokens
ACCENT_COLOR = "#10b981"
ACCENT_HOVER = "#059669"
BG_DARK = "#18181b"
BG_MID = "#27272a"
BG_CARD = "#1f1f23"
BG_CARD_HOVER = "#2a2a2f"
BG_CARD_SELECTED = "#0d3320"
BORDER_COLOR = "#3f3f46"
BORDER_SELECTED = "#10b981"
TEXT_COLOR = "#f4f4f5"
TEXT_MUTED = "#a1a1aa"
TEXT_DIM = "#71717a"
SUCCESS_COLOR = "#22c55e"
WARNING_COLOR = "#f59e0b"
DANGER_COLOR = "#ef4444"

FONT_FAMILY = "Segoe UI Variable Display" if sys.platform == "win32" else "SF Pro Display" if sys.platform == "darwin" else "Inter"


class ModelCard(QFrame):
    """A single model card in the selector grid."""
    
    clicked = pyqtSignal(str)  # emits model name
    
    def __init__(self, model_info: dict, is_downloaded: bool, parent=None):
        super().__init__(parent)
        self.model_name = model_info["name"]
        self.is_downloaded = is_downloaded
        self._selected = False
        
        self.setFixedHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Left: Model name + description
        left = QVBoxLayout()
        left.setSpacing(2)
        
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        
        name_label = QLabel(model_info["name"])
        name_label.setFont(QFont(FONT_FAMILY, 13, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; border: none;")
        name_row.addWidget(name_label)
        
        size_label = QLabel(model_info["size_label"])
        size_label.setFont(QFont(FONT_FAMILY, 10))
        size_label.setStyleSheet(f"color: {TEXT_DIM}; background: transparent; border: none;")
        name_row.addWidget(size_label)
        
        if is_downloaded:
            dl_badge = QLabel("✓ Downloaded")
            dl_badge.setFont(QFont(FONT_FAMILY, 9))
            dl_badge.setStyleSheet(f"color: {SUCCESS_COLOR}; background: transparent; border: none;")
            name_row.addWidget(dl_badge)
        
        name_row.addStretch()
        left.addLayout(name_row)
        
        desc_label = QLabel(model_info["description"])
        desc_label.setFont(QFont(FONT_FAMILY, 10))
        desc_label.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; border: none;")
        left.addWidget(desc_label)
        
        layout.addLayout(left, 1)
        
        # Right: Speed + Accuracy ratings
        right = QVBoxLayout()
        right.setSpacing(2)
        
        speed_label = QLabel(f"Speed: {model_info['speed']}")
        speed_label.setFont(QFont(FONT_FAMILY, 9))
        speed_label.setStyleSheet(f"color: {TEXT_DIM}; background: transparent; border: none;")
        speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(speed_label)
        
        acc_label = QLabel(f"Accuracy: {model_info['accuracy']}")
        acc_label.setFont(QFont(FONT_FAMILY, 9))
        acc_label.setStyleSheet(f"color: {TEXT_DIM}; background: transparent; border: none;")
        acc_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(acc_label)
        
        layout.addLayout(right)
    
    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style(selected)
    
    def _apply_style(self, selected: bool):
        if selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_CARD_SELECTED};
                    border: 2px solid {BORDER_SELECTED};
                    border-radius: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_CARD};
                    border: 1px solid {BORDER_COLOR};
                    border-radius: 12px;
                }}
                QFrame:hover {{
                    background-color: {BG_CARD_HOVER};
                    border: 1px solid {TEXT_DIM};
                }}
            """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.model_name)
        super().mousePressEvent(event)


class ModelSelectorDialog(QDialog):
    """First-run model selection dialog."""
    
    # Signal emitted when a model is selected and ready (name: str)
    model_ready = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose AI Model")
        self.setFixedSize(520, 640)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._selected_model = None
        self._cards: dict[str, ModelCard] = {}
        self._downloading = False
        self._drag_pos = None
        
        self._setup_ui()
        self._dwm_applied = False
    
    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32" and not self._dwm_applied:
            self._dwm_applied = True
            self._remove_dwm_border()
    
    def _remove_dwm_border(self):
        try:
            import ctypes
            hwnd = int(self.winId())
            DWMWA_BORDER_COLOR = 34
            DWMWA_COLOR_NONE = 0xFFFFFFFE
            color = ctypes.c_uint(DWMWA_COLOR_NONE)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_BORDER_COLOR,
                ctypes.byref(color), ctypes.sizeof(color)
            )
            DWMWA_NCRENDERING_POLICY = 2
            DWMNCRP_DISABLED = 1
            policy = ctypes.c_int(DWMNCRP_DISABLED)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_NCRENDERING_POLICY,
                ctypes.byref(policy), ctypes.sizeof(policy)
            )
        except Exception:
            pass
    
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        # Glass container
        self.container = QFrame()
        self.container.setObjectName("glass")
        self.container.setStyleSheet("""
            QFrame#glass {
                background-color: rgba(24, 24, 27, 245);
                border: none;
                border-radius: 16px;
            }
        """)
        
        inner = QVBoxLayout(self.container)
        inner.setContentsMargins(28, 24, 28, 24)
        inner.setSpacing(16)
        
        # Header
        header = QLabel("Choose Your AI Model")
        header.setFont(QFont(FONT_FAMILY, 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; border: none;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(header)
        
        subtitle = QLabel("Select a speech recognition model. Smaller models are faster\nbut less accurate. You can change this later in Settings.")
        subtitle.setFont(QFont(FONT_FAMILY, 11))
        subtitle.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; border: none;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        inner.addWidget(subtitle)
        
        # Scroll area for model cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {BG_DARK};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {BORDER_COLOR};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        cards_widget = QWidget()
        cards_widget.setStyleSheet("background: transparent;")
        cards_layout = QVBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 4, 0)
        cards_layout.setSpacing(8)
        
        downloaded = model_manager.get_downloaded_models()
        
        for model_info in model_manager.MODELS:
            is_dl = model_info["name"] in downloaded
            card = ModelCard(model_info, is_dl)
            card.clicked.connect(self._on_card_clicked)
            cards_layout.addWidget(card)
            self._cards[model_info["name"]] = card
        
        cards_layout.addStretch()
        scroll.setWidget(cards_widget)
        inner.addWidget(scroll, 1)
        
        # Progress area (hidden initially)
        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_MID};
                border-radius: 10px;
                border: none;
            }}
        """)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(16, 12, 16, 12)
        progress_layout.setSpacing(6)
        
        self.progress_label = QLabel("Downloading...")
        self.progress_label.setFont(QFont(FONT_FAMILY, 11))
        self.progress_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; border: none;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BG_DARK};
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT_COLOR};
                border-radius: 3px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_frame.hide()
        inner.addWidget(self.progress_frame)
        
        # Footer buttons
        footer = QHBoxLayout()
        footer.setSpacing(12)
        
        self.continue_btn = QPushButton("Select a model above")
        self.continue_btn.setFont(QFont(FONT_FAMILY, 12, QFont.Weight.Bold))
        self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.continue_btn.setFixedHeight(44)
        self.continue_btn.setEnabled(False)
        self._style_continue_btn(False)
        self.continue_btn.clicked.connect(self._on_continue)
        
        footer.addWidget(self.continue_btn)
        inner.addLayout(footer)
        
        root.addWidget(self.container)
    
    def _style_continue_btn(self, enabled: bool):
        if enabled:
            self.continue_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT_COLOR};
                    color: white;
                    border-radius: 12px;
                    border: none;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {ACCENT_HOVER};
                }}
            """)
        else:
            self.continue_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_MID};
                    color: {TEXT_DIM};
                    border-radius: 12px;
                    border: 1px solid {BORDER_COLOR};
                    font-size: 13px;
                }}
            """)
    
    def _on_card_clicked(self, model_name: str):
        if self._downloading:
            return
        
        self._selected_model = model_name
        
        # Update card visuals
        for name, card in self._cards.items():
            card.set_selected(name == model_name)
        
        # Update button
        is_dl = model_manager.is_model_downloaded(model_name)
        info = model_manager.get_model_info(model_name)
        
        if is_dl:
            self.continue_btn.setText(f"Use {model_name}")
        else:
            self.continue_btn.setText(f"Download & Use {model_name}  ({info['size_label']})")
        
        self.continue_btn.setEnabled(True)
        self._style_continue_btn(True)
    
    def _on_continue(self):
        if not self._selected_model or self._downloading:
            return
        
        model_name = self._selected_model
        
        if model_manager.is_model_downloaded(model_name):
            # Already downloaded — emit and close
            self.model_ready.emit(model_name)
            self.accept()
        else:
            # Need to download first
            self._start_download(model_name)
    
    def _start_download(self, model_name: str):
        self._downloading = True
        self.continue_btn.setEnabled(False)
        self.continue_btn.setText("Downloading...")
        self._style_continue_btn(False)
        
        self.progress_frame.show()
        self.progress_label.setText(f"Downloading {model_name}...")
        self.progress_bar.setValue(0)
        
        def on_progress(pct, msg):
            # Thread-safe UI update via QTimer
            QTimer.singleShot(0, lambda: self._update_progress(pct, msg))
        
        def on_done(success, msg):
            QTimer.singleShot(0, lambda: self._download_finished(success, msg, model_name))
        
        model_manager.download_model(model_name, on_progress, on_done)
    
    def _update_progress(self, pct: float, msg: str):
        self.progress_bar.setValue(int(pct))
        self.progress_label.setText(msg)
    
    def _download_finished(self, success: bool, msg: str, model_name: str):
        self._downloading = False
        
        if success:
            self.progress_label.setText("✓ Download complete!")
            self.progress_label.setStyleSheet(f"color: {SUCCESS_COLOR}; background: transparent; border: none;")
            self.progress_bar.setValue(100)
            
            # Update the card to show downloaded status
            if model_name in self._cards:
                # Rebuild the card would be complex, just proceed
                pass
            
            # Short delay then emit ready
            QTimer.singleShot(800, lambda: self._finalize(model_name))
        else:
            self.progress_label.setText(f"✗ Download failed: {msg}")
            self.progress_label.setStyleSheet(f"color: {DANGER_COLOR}; background: transparent; border: none;")
            self.continue_btn.setText("Retry Download")
            self.continue_btn.setEnabled(True)
            self._style_continue_btn(True)
    
    def _finalize(self, model_name: str):
        self.model_ready.emit(model_name)
        self.accept()
    
    # --- Dragging ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
