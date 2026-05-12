"""
System tray icon and menu using PyQt6.
"""

from typing import Callable
from pathlib import Path
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot

class TrayApp(QObject):
    """System tray application with microphone icon."""
    
    sig_set_active = pyqtSignal(bool)
    sig_stop = pyqtSignal()
    
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_toggle_overlay: Callable[[], None],
        on_quit: Callable[[], None],
        on_settings: Callable[[], None],
        on_history: Callable[[], None],
        hotkey_label: str = "F9"
    ):
        """
        Initialize tray app.
        """
        super().__init__()
        self.on_toggle = on_toggle
        self.on_toggle_overlay = on_toggle_overlay
        self.on_quit = on_quit
        self.on_settings = on_settings
        self.on_history = on_history
        self.hotkey_label = hotkey_label
        self.is_active = False
        
        import config
        self.model_name = config.MODEL
        self.device_name = config.DEVICE.upper()
        
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._create_icon(False))
        self.tray.setToolTip("Local Voice")
        
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self._update_menu()
        
        self.tray.activated.connect(self._on_activated)
        
        self.sig_set_active.connect(self._do_set_active)
        self.sig_stop.connect(self._do_stop)
    


    def run(self) -> None:
        """Show the tray icon."""
        self.tray.show()
    
    def set_active(self, active: bool) -> None:
        """Update icon color and menu label (thread-safe)."""
        self.sig_set_active.emit(active)
        
    @pyqtSlot(bool)
    def _do_set_active(self, active: bool) -> None:
        self.is_active = active
        self.tray.setIcon(self._create_icon(active))
        self.tray.setToolTip("Listening..." if active else "Local Voice")
        self._update_menu()
    
    def stop(self) -> None:
        """Hide the tray icon (thread-safe)."""
        self.sig_stop.emit()
        
    @pyqtSlot()
    def _do_stop(self) -> None:
        self.tray.hide()
    
    def _create_icon(self, active: bool) -> QIcon:
        """Load professional SVG icon from assets."""
        asset_name = "logo_active.svg" if active else "logo.svg"
        icon_path = str(Path(__file__).parent / "assets" / asset_name)
        return QIcon(icon_path)
    
    def _update_menu(self) -> None:
        """Rebuild the tray menu."""
        self.menu.clear()
        
        toggle_label = f"Stop Listening ({self.hotkey_label})" if self.is_active else f"Start Listening ({self.hotkey_label})"
        
        action_toggle = QAction(toggle_label, self.menu)
        action_toggle.triggered.connect(self.on_toggle)
        self.menu.addAction(action_toggle)
        
        action_overlay = QAction("Show/Hide Overlay", self.menu)
        action_overlay.triggered.connect(self.on_toggle_overlay)
        self.menu.addAction(action_overlay)
        
        self.menu.addSeparator()
        
        action_history = QAction("Transcription History", self.menu)
        action_history.triggered.connect(self.on_history)
        self.menu.addAction(action_history)
        
        action_settings = QAction("Settings...", self.menu)
        action_settings.triggered.connect(self.on_settings)
        self.menu.addAction(action_settings)
        
        self.menu.addSeparator()
        
        action_model = QAction(f"Model: {self.model_name}", self.menu)
        action_model.setEnabled(False)
        self.menu.addAction(action_model)
        
        action_device = QAction(f"Device: {self.device_name}", self.menu)
        action_device.setEnabled(False)
        self.menu.addAction(action_device)
        
        self.menu.addSeparator()
        
        action_quit = QAction("Quit Application", self.menu)
        action_quit.triggered.connect(self.on_quit)
        self.menu.addAction(action_quit)

    def _on_activated(self, reason) -> None:
        """Handle click events on the tray icon."""
        # Convert int to enum if needed, or just check value
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left click
            self.on_toggle()
