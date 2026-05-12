"""
Modern Settings UI for Voice-to-Text with model download management.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QFormLayout, QMessageBox,
    QFrame, QGraphicsDropShadowEffect, QMenu, QWidgetAction,
    QProgressBar
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QColor, QFont, QKeySequence, QPainter, QPen, QBrush, QAction
import config
import model_manager
try:
    import pyaudio
except ImportError:
    pyaudio = None

# Design tokens
ACCENT_COLOR = "#10b981"
ACCENT_HOVER = "#059669"
BG_DARK = "#18181b"
BG_MID = "#27272a"
BORDER_COLOR = "#3f3f46"
TEXT_COLOR = "#f4f4f5"
TEXT_MUTED = "#a1a1aa"
SUCCESS_COLOR = "#22c55e"
WARNING_COLOR = "#f59e0b"
DANGER_COLOR = "#ef4444"

FONT_FAMILY = "Segoe UI Variable Display" if sys.platform == "win32" else "Inter"


class CustomDropdown(QPushButton):
    """A fully custom dropdown selector with no system popup decorations."""
    valueChanged = pyqtSignal(str)

    def __init__(self, items, current="", parent=None):
        super().__init__(parent)
        self.items = items
        self.current_value = current if current in items else (items[0] if items else "")
        self.setText("")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self._apply_style()
        self.clicked.connect(self._show_menu)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_MID};
                color: white;
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 13px;
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{
                border: 1px solid {ACCENT_COLOR};
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(TEXT_COLOR))
        p.setFont(QFont(FONT_FAMILY, 13))
        text_rect = self.rect().adjusted(18, 0, -40, 0)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.current_value)
        p.setPen(QColor(TEXT_MUTED))
        chevron_rect = self.rect().adjusted(0, 0, -14, 0)
        p.drawText(chevron_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "▾")
        p.end()

    def _show_menu(self):
        self.menu = QMenu(self)
        self.menu.setMinimumWidth(self.width())
        self.menu.setWindowFlags(self.menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.menu.setStyleSheet(f"""
            QMenu {{
                background-color: {BG_DARK};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 10px 20px;
                border-radius: 8px;
                color: {TEXT_COLOR};
                font-family: '{FONT_FAMILY}';
                font-size: 13px;
                margin: 1px 0px;
            }}
            QMenu::item:selected {{
                background-color: {ACCENT_COLOR};
                color: white;
            }}
        """)
        
        for item in self.items:
            action = self.menu.addAction(item)
            action.triggered.connect(lambda checked, i=item: self._on_item_selected(i))
            
        self.menu.exec(self.mapToGlobal(QPoint(0, self.height() + 5)))

    def _on_item_selected(self, item):
        self.current_value = item
        self.update()
        self.valueChanged.emit(self.current_value)

    def currentText(self):
        return self.current_value


class ToggleSwitch(QPushButton):
    """A modern iOS-style toggle switch drawn with QPainter."""
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_color = QColor(ACCENT_COLOR) if self.isChecked() else QColor(BORDER_COLOR)
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        p.setBrush(QBrush(QColor("white")))
        knob_x = self.width() - 24 if self.isChecked() else 4
        p.drawEllipse(knob_x, 4, 20, 20)
        p.end()


class HotkeyButton(QPushButton):
    """A button that records key combinations."""
    def __init__(self, current_hotkey, parent=None):
        super().__init__(current_hotkey, parent)
        self.recording = False
        self.current_hotkey = current_hotkey
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setStyleSheet(self._get_style(False))
        self.clicked.connect(self._toggle)

    def _get_style(self, recording):
        bg = BG_MID if not recording else "#065f46"
        border = f"1px solid {ACCENT_COLOR}" if recording else f"1px solid {BORDER_COLOR}"
        return f"""
            QPushButton {{
                background-color: {bg}; color: white; border: {border};
                border-radius: 8px; padding: 10px; font-weight: bold; font-size: 13px;
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{ border: 1px solid {ACCENT_COLOR}; }}
        """

    def _toggle(self):
        if self.isChecked():
            self.setText("Press your keys...")
            self.setStyleSheet(self._get_style(True))
            self.recording = True
        else:
            self.recording = False
            self.setText(self.current_hotkey)
            self.setStyleSheet(self._get_style(False))

    def keyPressEvent(self, event):
        if not self.recording:
            super().keyPressEvent(event)
            return
        key = event.key()
        modifiers = event.modifiers()
        is_modifier = key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta)
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier: parts.append("<ctrl>")
        if modifiers & Qt.KeyboardModifier.AltModifier: parts.append("<alt>")
        if modifiers & Qt.KeyboardModifier.ShiftModifier: parts.append("<shift>")
        if modifiers & Qt.KeyboardModifier.MetaModifier: parts.append("<cmd>")
        if not is_modifier:
            if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
                parts.append(f"<f{key - Qt.Key.Key_F1 + 1}>")
            elif key == Qt.Key.Key_Space: parts.append("<space>")
            elif key == Qt.Key.Key_Tab: parts.append("<tab>")
            elif key in (Qt.Key.Key_Enter, Qt.Key.Key_Return): parts.append("<enter>")
            elif key == Qt.Key.Key_Escape:
                self.setChecked(False); self._toggle(); return
            else:
                char = event.text().lower()
                if char and char.isalnum(): parts.append(char)
                else:
                    key_text = QKeySequence(key).toString().lower()
                    if key_text: parts.append(key_text)
            self.current_hotkey = "+".join(parts)
            self.setText(self.current_hotkey)
            self.recording = False
            self.setChecked(False)
            self.setStyleSheet(self._get_style(False))
        else:
            self.setText("+".join(parts) + " + ..." if parts else "Press your keys...")


class ModelDropdown(QPushButton):
    """Custom dropdown for model selection with download status indicators."""
    valueChanged = pyqtSignal(str)

    def __init__(self, current="", parent=None):
        super().__init__(parent)
        self.current_value = current
        self.setText("")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self._apply_style()
        self.clicked.connect(self._show_menu)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_MID}; color: white;
                border: 1px solid {BORDER_COLOR}; border-radius: 8px;
                padding: 8px 15px; font-size: 13px;
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{ border: 1px solid {ACCENT_COLOR}; }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(TEXT_COLOR))
        p.setFont(QFont(FONT_FAMILY, 13))
        text_rect = self.rect().adjusted(18, 0, -40, 0)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.current_value)
        p.setPen(QColor(TEXT_MUTED))
        chevron_rect = self.rect().adjusted(0, 0, -14, 0)
        p.drawText(chevron_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "▾")
        p.end()

    def _show_menu(self):
        self.menu = QMenu(self)
        self.menu.setMinimumWidth(self.width())
        self.menu.setWindowFlags(self.menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.menu.setStyleSheet(f"""
            QMenu {{
                background-color: {BG_DARK};
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 10px 20px;
                border-radius: 8px;
                color: {TEXT_COLOR};
                font-family: '{FONT_FAMILY}';
                font-size: 13px;
                margin: 1px 0px;
            }}
            QMenu::item:selected {{
                background-color: {ACCENT_COLOR};
                color: white;
            }}
        """)
        
        downloaded = model_manager.get_downloaded_models()
        for m in model_manager.MODELS:
            name = m["name"]
            is_dl = name in downloaded
            prefix = "✓ " if name == self.current_value else "   "
            suffix = f"  ({m['size_label']})"
            if not is_dl:
                suffix += "  ⬇"
            action = self.menu.addAction(f"{prefix}{name}{suffix}")
            action.setData(name)
            if name == self.current_value:
                font = action.font(); font.setBold(True); action.setFont(font)
        chosen = self.menu.exec(self.mapToGlobal(self.rect().bottomLeft()))
        if chosen:
            val = chosen.data()
            if val:
                self.current_value = val
                self.update()
                self.valueChanged.emit(self.current_value)

    def currentText(self):
        return self.current_value


def get_audio_devices():
    """Return list of (index, name) for all input devices."""
    if not pyaudio:
        return [(None, "Default Microphone")]
    
    devices = [(None, "Default Microphone")]
    try:
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                name = info.get('name')
                # Clean up Windows-specific naming if needed
                devices.append((i, name))
        p.terminate()
    except Exception as e:
        print(f"[Settings] Error listing audio devices: {e}")
    return devices


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice-to-Text Settings")
        self.setFixedSize(480, 580)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._downloading = False
        
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

        self._setup_ui()
        self._dwm_applied = False

    def showEvent(self, event):
        super().showEvent(event)
        
        # Play entry animation
        end_pos = self.pos()
        start_pos = QPoint(end_pos.x(), end_pos.y() + 50)
        
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(end_pos)
        
        self.setWindowOpacity(0)
        self._fade_anim.setStartValue(0)
        self._fade_anim.setEndValue(1.0)
        
        self._slide_anim.start()
        self._fade_anim.start()

        if sys.platform == "win32" and not self._dwm_applied:
            self._dwm_applied = True
            # Use a tiny delay (5ms) for the glass effect so it feels instant
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
            print(f"[Settings] Fluent Glass failed: {e}")

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("glass")
        container.setStyleSheet("""
            QFrame#glass {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.08), 
                    stop:1 rgba(255, 255, 255, 0.03));
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-top: 1px solid rgba(255, 255, 255, 0.25); /* Glass Edge Highlight */
                border-radius: 12px;
            }
        """)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(30, 28, 30, 28)
        inner.setSpacing(18)
        root.addWidget(container)

        # Header
        header = QLabel("Settings")
        header.setStyleSheet(f"color: white; font-size: 22px; font-weight: bold; background: transparent; border: none; font-family: '{FONT_FAMILY}';")
        inner.addWidget(header)

        label_style = f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; background: transparent; border: none; font-family: '{FONT_FAMILY}';"

        # 1. Model dropdown
        row1 = QHBoxLayout()
        l1 = QLabel("Whisper Model")
        l1.setStyleSheet(label_style)
        l1.setFixedWidth(130)
        self.model_dropdown = ModelDropdown(current=config.MODEL)
        self.model_dropdown.valueChanged.connect(self._on_model_changed)
        row1.addWidget(l1)
        row1.addWidget(self.model_dropdown, 1)
        inner.addLayout(row1)

        # Model status + download area
        self.model_status_frame = QFrame()
        self.model_status_frame.setObjectName("StatusFrame")
        self.model_status_frame.setStyleSheet(f"""
            #StatusFrame {{ 
                background-color: rgba(255, 255, 255, 0.03); 
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px; 
            }}
        """)
        ms_layout = QVBoxLayout(self.model_status_frame)
        ms_layout.setContentsMargins(14, 10, 14, 10)
        ms_layout.setSpacing(6)

        self.model_status_label = QLabel("")
        self.model_status_label.setFont(QFont(FONT_FAMILY, 11))
        self.model_status_label.setWordWrap(True)
        self.model_status_label.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; border: none;")
        ms_layout.addWidget(self.model_status_label)

        self.download_btn = QPushButton("Download Model")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setFixedHeight(34)
        self.download_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {WARNING_COLOR}; color: white;
                border-radius: 8px; font-weight: bold; font-size: 12px; border: none;
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{ background-color: #d97706; }}
        """)
        self.download_btn.clicked.connect(self._on_download_click)
        self.download_btn.hide()
        ms_layout.addWidget(self.download_btn)

        self.delete_btn = QPushButton("Delete Model Files")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setFixedHeight(34)
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {DANGER_COLOR};
                border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px;
                font-weight: bold; font-size: 11px;
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{ background-color: {DANGER_COLOR}; color: white; border: 1px solid {DANGER_COLOR}; }}
        """)
        self.delete_btn.clicked.connect(self._on_delete_click)
        self.delete_btn.hide()
        ms_layout.addWidget(self.delete_btn)

        self.dl_progress = QProgressBar()
        self.dl_progress.setFixedHeight(6)
        self.dl_progress.setTextVisible(False)
        self.dl_progress.setStyleSheet(f"""
            QProgressBar {{ background-color: {BG_DARK}; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background-color: {ACCENT_COLOR}; border-radius: 3px; }}
        """)
        self.dl_progress.hide()
        ms_layout.addWidget(self.dl_progress)

        self.model_status_frame.hide()
        inner.addWidget(self.model_status_frame)

        self._update_model_status(config.MODEL)

        # 2. Device
        row2 = QHBoxLayout()
        l2 = QLabel("Processor")
        l2.setStyleSheet(label_style)
        l2.setFixedWidth(130)
        self.device_dropdown = CustomDropdown(["cuda", "cpu"], current=config.DEVICE)
        row2.addWidget(l2)
        row2.addWidget(self.device_dropdown, 1)
        inner.addLayout(row2)

        # 2.5 Microphone dropdown
        row_mic = QHBoxLayout()
        l_mic = QLabel("Microphone")
        l_mic.setStyleSheet(label_style)
        l_mic.setFixedWidth(130)
        
        self.audio_devices = get_audio_devices()
        device_names = [d[1] for d in self.audio_devices]
        
        # Find current device index in the list
        current_name = "Default Microphone"
        for idx, name in self.audio_devices:
            if idx == config.INPUT_DEVICE_INDEX:
                current_name = name
                break
        
        self.mic_dropdown = CustomDropdown(device_names, current=current_name)
        row_mic.addWidget(l_mic)
        row_mic.addWidget(self.mic_dropdown, 1)
        inner.addLayout(row_mic)

        # 3. Language
        row_lang = QHBoxLayout()
        l_lang = QLabel("Language")
        l_lang.setStyleSheet(label_style)
        l_lang.setFixedWidth(130)
        lang_display_map = {None: "Auto-detect", "en": "English", "es": "Spanish", "fr": "French",
                           "de": "German", "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "hi": "Hindi"}
        current_lang_display = lang_display_map.get(config.LANGUAGE, "Auto-detect")
        self.language_dropdown = CustomDropdown(
            ["Auto-detect", "English", "Spanish", "French", "German", "Chinese", "Japanese", "Korean", "Hindi"],
            current=current_lang_display
        )
        row_lang.addWidget(l_lang)
        row_lang.addWidget(self.language_dropdown, 1)
        inner.addLayout(row_lang)

        # 4. Hotkey
        row3 = QHBoxLayout()
        l3 = QLabel("Shortcut Key")
        l3.setStyleSheet(label_style)
        l3.setFixedWidth(130)
        self.hotkey_btn = HotkeyButton(config.TOGGLE_KEY_STR)
        row3.addWidget(l3)
        row3.addWidget(self.hotkey_btn, 1)
        inner.addLayout(row3)

        # 5. Autostart toggle
        row4 = QHBoxLayout()
        al = QLabel("Start at Login")
        al.setStyleSheet(f"color: {TEXT_COLOR}; font-size: 14px; background: transparent; border: none; font-family: '{FONT_FAMILY}';")
        self.autostart_toggle = ToggleSwitch(checked=config.AUTO_START)
        row4.addWidget(al)
        row4.addStretch()
        row4.addWidget(self.autostart_toggle)
        inner.addLayout(row4)

        inner.addStretch()

        # Footer
        footer = QHBoxLayout()
        footer.setSpacing(12)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedSize(110, 38)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {TEXT_MUTED};
                border: 1px solid {BORDER_COLOR}; border-radius: 10px;
                font-weight: bold; font-size: 13px;
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{ background-color: {BG_MID}; color: white; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save and Restart")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedSize(170, 38)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_COLOR}; color: white;
                border-radius: 10px; font-weight: bold; font-size: 13px; border: none;
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
        """)
        save_btn.clicked.connect(self._save)

        footer.addStretch()
        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)
        inner.addLayout(footer)

    def _on_model_changed(self, model_name):
        self._update_model_status(model_name)

    def _update_model_status(self, model_name):
        """Show download status for the selected model."""
        info = model_manager.get_model_info(model_name)
        if not info:
            self.model_status_frame.hide()
            return

        is_dl = model_manager.is_model_downloaded(model_name)
        self.model_status_frame.show()

        if not is_dl:
            self.model_status_label.setText(
                f"⚠ {model_name} is not downloaded.\nYou need to download it before you can use it.  ({info['size_label']})"
            )
            self.model_status_label.setStyleSheet(f"color: {WARNING_COLOR}; background: transparent; border: none;")
            self.download_btn.setText(f"Download {model_name}  ({info['size_label']})")
            self.download_btn.show()
            self.delete_btn.hide()
            self.dl_progress.hide()
        else:
            # Model is downloaded
            self.model_status_label.setText(f"✓ {model_name} is downloaded and ready  ({info['size_label']})")
            self.model_status_label.setStyleSheet(f"color: {SUCCESS_COLOR}; background: transparent; border: none;")
            self.download_btn.hide()
            self.delete_btn.show()
            self.dl_progress.hide()

    def _on_delete_click(self):
        model_name = self.model_dropdown.currentText()
        reply = QMessageBox.question(self, "Delete Model", 
                                   f"Are you sure you want to delete all files for '{model_name}'?\nThis will free up disk space.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if model_manager.delete_model(model_name):
                QMessageBox.information(self, "Deleted", f"Model '{model_name}' has been deleted.")
                self._update_model_status(model_name)
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete model '{model_name}'.")

    def _on_download_click(self):
        if self._downloading:
            return
        model_name = self.model_dropdown.currentText()
        self._downloading = True
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.dl_progress.setValue(0)
        self.dl_progress.show()

        def on_progress(pct, msg):
            QTimer.singleShot(0, lambda: self._dl_progress_update(pct, msg))

        def on_done(success, msg):
            QTimer.singleShot(0, lambda: self._dl_done(success, msg, model_name))

        model_manager.download_model(model_name, on_progress, on_done)

    def _dl_progress_update(self, pct, msg):
        self.dl_progress.setValue(int(pct))
        self.model_status_label.setText(msg)
        self.model_status_label.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; border: none;")

    def _dl_done(self, success, msg, model_name):
        self._downloading = False
        if success:
            self._update_model_status(model_name)
        else:
            self.model_status_label.setText(f"✗ Download failed: {msg}")
            self.model_status_label.setStyleSheet(f"color: {DANGER_COLOR}; background: transparent; border: none;")
            self.download_btn.setText("Retry Download")
            self.download_btn.setEnabled(True)

    def _save(self):
        selected_model = self.model_dropdown.currentText()

        # Block save if model not downloaded
        if not model_manager.is_model_downloaded(selected_model):
            QMessageBox.warning(self, "Model Not Downloaded",
                f"The model '{selected_model}' is not downloaded yet.\n"
                "Please download it first using the Download button, or select a different model.")
            return

        lang_map = {"Auto-detect": None, "English": "en", "Spanish": "es", "French": "fr",
                     "German": "de", "Chinese": "zh", "Japanese": "ja", "Korean": "ko", "Hindi": "hi"}
        # Find selected mic index
        mic_name = self.mic_dropdown.currentText()
        selected_mic_index = None
        for idx, name in self.audio_devices:
            if name == mic_name:
                selected_mic_index = idx
                break

        new_settings = {
            "MODEL": selected_model,
            "DEVICE": self.device_dropdown.currentText(),
            "INPUT_DEVICE_INDEX": selected_mic_index,
            "LANGUAGE": lang_map.get(self.language_dropdown.currentText()),
            "COMPUTE_TYPE": "int8",
            "TOGGLE_KEY_STR": self.hotkey_btn.current_hotkey,
            "AUTO_START": self.autostart_toggle.isChecked()
        }
        config.save_settings(new_settings)
        QMessageBox.information(self, "Restarting", "Settings saved. The app will now restart.")
        self.accept()
        # Restart the app
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
