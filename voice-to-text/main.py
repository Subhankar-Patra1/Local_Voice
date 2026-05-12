"""
Voice-to-Text — Fully Local Real-Time Speech-to-Text
Entry point — wires everything together.
"""

import os
import sys
import signal
import threading
import platform
from pathlib import Path
import config

# Fix for PyInstaller console=False and multiprocessing
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

if platform.system() == "Linux":
    os.environ["QT_QPA_PLATFORM"] = "xcb"

# ---------------------------------------------------------------------------
# Cross-platform paths
# ---------------------------------------------------------------------------
# On Windows, prefer D:\Local_Voice if it exists (legacy / disk-space setup).
# On macOS/Linux, use the project directory or ~/.cache/voice-to-text.

IS_WINDOWS = platform.system() == "Windows"

MODELS_DIR = config.MODELS_DIR
TEMP_DIR = config.TEMP_DIR

# Point Hugging Face cache here
os.environ["HF_HOME"] = str(MODELS_DIR)
os.environ["HUGGINGFACE_HUB_CACHE"] = str(MODELS_DIR)

# Temp files
os.environ["TEMP"] = str(TEMP_DIR)
os.environ["TMP"] = str(TEMP_DIR)
os.environ["TMPDIR"] = str(TEMP_DIR)


import config
import model_manager
from overlay import OverlayWindow
from tray import TrayApp
from injector import inject_text, delete_text
from recorder import VoiceRecorder

try:
    from pynput import keyboard
except ImportError:
    print("[App] ERROR: pynput not installed.")
    print("[App] Install with: pip install pynput>=1.7.6")
    sys.exit(1)


# Global instances
overlay = None
recorder = None
tray = None
model_loaded = False
_is_stopping = False


def _log(msg: str) -> None:
    """Print to console."""
    print(msg)

def print_banner() -> None:
    """Print startup banner."""
    os_name = platform.system()
    _log("=" * 50)
    _log("  Local Voice    |  Fully Local")
    _log(f"  Model  : {config.MODEL}")
    _log(f"  Device : {config.DEVICE.upper()}")
    if os_name == "Linux" and "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower():
        _log("  Control: Click the toggle button (Wayland)")
    else:
        _log(f"  Hotkey : {config.TOGGLE_KEY_STR}")
    _log(f"  Inject : {config.INJECT_METHOD}")
    _log("=" * 50)
    _log("")


def load_model() -> None:
    """Load the AI model (first time). Called when user clicks 'Start'."""
    global recorder, overlay, tray, model_loaded
    try:
        _log("[App] Loading model...")
        overlay.show_idle("Loading model... Please wait", show_button=False)
        recorder.start()
        # Model loading happens inside recorder.start()
        # on_loading callback will handle UI updates
    except Exception as e:
        _log(f"[App] ERROR loading model: {e}")
        import traceback
        _log(traceback.format_exc())
        overlay.show_idle("Error loading model. Click to retry.", button_text="Start")


def start_recording() -> None:
    """Start recording (after model is loaded)."""
    global recorder, overlay, tray, model_loaded
    try:
        if not model_loaded:
            _log("[App] Model not loaded yet. Loading first...")
            load_model()
            return
        _log("[App] Recording started.")
        recorder.start()
        overlay.show_recording("")
        if tray:
            tray.set_active(True)
    except Exception as e:
        _log(f"[App] ERROR during start: {e}")
        import traceback
        _log(traceback.format_exc())


def stop_recording() -> None:
    """Stop recording."""
    global recorder, overlay, tray, _is_stopping
    
    if _is_stopping:
        return
        
    try:
        _is_stopping = True
        _log("[App] Stopping recording...")
        overlay.show_stopping()

        def _stop_task():
            global _is_stopping
            try:
                recorder.stop()
            finally:
                _log("[App] Recording stopped.")
                overlay.show_idle("Click to start", button_text="Start Listening")
                if tray:
                    tray.set_active(False)
                _is_stopping = False

        threading.Thread(target=_stop_task, daemon=True).start()

    except Exception as e:
        _log(f"[App] ERROR during stop: {e}")
        import traceback
        _log(traceback.format_exc())


def toggle_recording() -> None:
    """Toggle recording on/off (for hotkey/tray)."""
    global recorder, model_loaded
    if not model_loaded:
        _log("[App] Model not loaded yet. Ignoring toggle.")
        # If they press hotkey before loading, we could start load, but
        # clicking overlay is safer.
        load_model()
        return
    if recorder.is_running():
        stop_recording()
    else:
        start_recording()


def toggle_overlay() -> None:
    """Show or hide the overlay window."""
    global overlay
    if overlay:
        overlay.toggle_visibility()


def on_quit() -> None:
    """Handle quit request."""
    _log("[App] Shutting down...")
    _shutdown()


def open_settings() -> None:
    """Open the settings GUI dialog."""
    from settings_ui import SettingsDialog
    from PyQt6.QtCore import Qt
    dialog = SettingsDialog()
    dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    dialog.exec()


def open_history() -> None:
    """Open the transcription history GUI dialog."""
    from history_ui import HistoryDialog
    dialog = HistoryDialog()
    dialog.exec()


def _shutdown(signum=None, frame=None) -> None:
    """Clean shutdown."""
    global recorder, overlay, tray
    
    if recorder and recorder.is_running():
        recorder.stop()
    
    if overlay:
        overlay.destroy()
    
    if tray:
        tray.stop()
    
    import time
    time.sleep(0.1)
    
    # Auto-cleanup temp files
    config.cleanup_temp()
    
    sys.exit(0)


from PyQt6.QtCore import QObject, pyqtSignal

class HotkeyBridge(QObject):
    """Thread-safe bridge between pynput background thread and Qt main thread."""
    triggered = pyqtSignal()

# Global bridge instance
_hotkey_bridge = None

def on_hotkey_triggered() -> None:
    """Handle global hotkey trigger from the pynput background thread."""
    try:
        _log(f"[App] Hotkey pressed: {config.TOGGLE_KEY_STR}")
        if _hotkey_bridge:
            _hotkey_bridge.triggered.emit()
    except Exception as e:
        print(f"[App] Hotkey error: {e}")


def _hotkey_action() -> None:
    """Actual hotkey logic — runs safely on the Qt main thread."""
    try:
        # If overlay was hidden (user clicked ✕), just bring it back to its previous state
        if overlay and not overlay.isVisible():
            overlay.show()
            _log("[App] Restored overlay from tray.")
            return  # Do not toggle recording, just restore the UI
            
        # If overlay is already visible, toggle the recording/loading state
        toggle_recording()
    except Exception as e:
        print(f"[App] Hotkey action error: {e}")

def check_platform_requirements() -> bool:
    """Check platform-specific requirements and print warnings.
    Returns True if a fallback UI (toggle button) is needed (Linux Wayland)."""
    os_name = platform.system()
    
    if os_name == "Windows":
        _log("[App] Windows detected.")
        _log("[App] INFO: Press F9 to toggle recording.")
        _log("[App] INFO: Right-click tray icon for menu.")
        _log("")
    
    elif os_name == "Darwin":
        _log("[App] macOS detected.")
        _log("[App] NOTE: Accessibility permission required for global hotkeys.")
        _log("[App]       If F9 doesn't work, go to:")
        _log("[App]       System Settings → Privacy & Security → Accessibility → Add Terminal")
        _log("")
    
    elif os_name == "Linux":
        session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        is_wayland = "wayland" in session
        if is_wayland:
            _log("[App] Linux Wayland detected.")
            _log("[App] WARNING: Global hotkeys (F9) and tray clicks may not work on Wayland.")
            _log("[App]          A toggle button + status window will appear as fallback.")
            _log("[App]          For text injection: sudo apt-get install wtype ydotool")
            _log("")
            return True
        else:
            _log("[App] Linux X11 detected.")
            _log("[App] INFO: Press F9 to toggle recording.")
            _log("[App] INFO: For Wayland support: sudo apt-get install wtype ydotool")
            _log("")
    return False




def _show_first_run_selector() -> str | None:
    """Show model selector dialog on first run. Returns selected model name or None."""
    from model_selector import ModelSelectorDialog
    selected = [None]
    
    def on_model_ready(name):
        selected[0] = name
    
    dialog = ModelSelectorDialog()
    dialog.model_ready.connect(on_model_ready)
    dialog.exec()
    return selected[0]


def _is_first_run() -> bool:
    """Check if this is the first run (no model configured or settings file missing)."""
    return not config.SETTINGS_FILE.exists()


def main() -> None:
    """Main entry point."""
    global overlay, recorder, tray, _hotkey_bridge
    
    # Print banner
    print_banner()
    
    # Check platform requirements
    check_platform_requirements()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    
    # Initialize the global QApplication first!
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Initialize hotkey bridge for thread-safe UI updates
    _hotkey_bridge = HotkeyBridge()
    _hotkey_bridge.triggered.connect(_hotkey_action)
    
    # First-run: show model selector if no settings exist yet
    if _is_first_run():
        _log("[App] First run detected — showing model selector...")
        chosen_model = _show_first_run_selector()
        if chosen_model:
            _log(f"[App] User chose model: {chosen_model}")
            config.save_settings({
                "MODEL": chosen_model,
                "DEVICE": config.DEVICE,
                "LANGUAGE": config.LANGUAGE,
                "COMPUTE_TYPE": config.COMPUTE_TYPE,
                "TOGGLE_KEY_STR": config.TOGGLE_KEY_STR,
                "AUTO_START": config.AUTO_START,
            })
            config.MODEL = chosen_model
        else:
            _log("[App] User closed model selector without choosing. Exiting.")
            sys.exit(0)
    
    # Create overlay window (visible on startup)
    _log("[App] Creating overlay window...")

    def on_overlay_start():
        """Called when user clicks 'Start' or 'Start Listening' in overlay."""
        global model_loaded
        if not model_loaded:
            load_model()
        else:
            start_recording()

    def on_overlay_stop():
        """Called when user clicks 'Stop Listening' in overlay."""
        stop_recording()

    overlay = OverlayWindow(on_start=on_overlay_start, on_stop=on_overlay_stop, on_quit=on_quit, on_settings=open_settings)
    overlay.show_idle("Click Start to load model", button_text="Start")
    _log("[App] Overlay ready.")

    # Start update checker in background
    from updater import UpdateChecker
    global _updater
    _updater = UpdateChecker()
    _updater.update_available.connect(overlay.show_update_available)
    _updater.check_for_updates()

    def on_text(text: str) -> None:
        import re
        
        # 1. Basic cleanup
        cleaned = text.strip()
        
        # 2. Remove AI hallucinations (repeating characters/dots)
        # Often Whisper outputs "...." or "  . . ." when there is silence
        cleaned = re.sub(r'[\.]{2,}', '', cleaned)
        cleaned = re.sub(r'\s*\.\s*', ' ', cleaned).strip()
        
        # 3. Filter common "Silence Hallucinations" 
        # (Whisper often outputs these when nothing is said)
        hallucinations = [
            "Thank you.", "Thanks for watching.", "Please like and subscribe.",
            "I'll see you in the next one.", "subtitle by", "translated by",
            "you", "i", "it", "the" # Single-word junk often fired by small models
        ]
        
        # Case-insensitive check for full phrase hallucinations
        lower_cleaned = cleaned.lower().strip(" .!,")
        for h in hallucinations:
            if h.lower() in lower_cleaned:
                # If the entire transcription is just a hallucination, ignore it
                if len(lower_cleaned) <= len(h) + 2:
                    return

        if not cleaned or len(cleaned) < 2:
            return

        # Optional AI post-processing through Claude (removes filler words, fixes grammar)
        if config.AI_PROCESSING:
            from processor import process
            cleaned = process(cleaned)
            if config.DEBUG_PRINT:
                print(f"[AI]       {cleaned}")

        import history
        history.add_entry(cleaned)

        inject_text(cleaned, method=config.INJECT_METHOD)

        if config.DEBUG_PRINT:
            print(f"[Injected] {cleaned}")

    def on_partial(text: str) -> None:
        """Handle partial transcription: show live preview ONLY."""
        overlay.show_recording(text)

    def on_loading(status: str | None) -> None:
        """Show loading/downloading status in overlay."""
        global model_loaded
        if status == "downloading":
            info = model_manager.get_model_info(config.MODEL)
            size_label = info["size_label"] if info else "~1.5 GB"
            overlay.show_downloading(0, f"Preparing to download AI model...\nRequires internet · {size_label} download")
        elif status == "loading":
            # Model is cached — just loading from disk (fast, ~2-5s)
            overlay.show_idle("Loading AI model...", show_button=False)
        elif status and status.startswith("error:"):
            # Model loading failed — show error in overlay
            error_msg = status[6:].strip()
            _log(f"[App] Model load error: {error_msg}")
            overlay.show_idle(f"Error: {error_msg}\nTry a smaller model in Settings.", button_text="Start")
        elif status:
            overlay.show_idle(status, show_button=False)
        else:
            # Loading done - immediately transition to recording state
            model_loaded = True
            _log("[App] Recording started.")
            overlay.show_recording("")
            if tray:
                tray.set_active(True)

    def on_download_progress(percent: float, message: str) -> None:
        """Show download progress in overlay (called from download monitor thread)."""
        overlay.show_downloading(percent, message)
    
    _log("[App] Creating voice recorder...")
    recorder = VoiceRecorder(
        on_text=on_text, 
        on_partial=on_partial, 
        on_loading=on_loading,
        on_download_progress=on_download_progress
    )
    
    # Start global hotkey listener
    _log(f"[App] Hotkey active: {config.TOGGLE_KEY_STR}")
    hotkey_map = {config.TOGGLE_KEY_STR: on_hotkey_triggered}
    listener = keyboard.GlobalHotKeys(hotkey_map)
    listener.start()
    
    # Create tray app
    _log("[App] Starting system tray... (check your taskbar)")
    hotkey_label = config.TOGGLE_KEY_STR.replace("<", "").replace(">", "").upper()
    tray = TrayApp(
        on_toggle=toggle_recording,
        on_toggle_overlay=toggle_overlay,
        on_quit=on_quit,
        on_settings=open_settings,
        on_history=open_history,
        hotkey_label=hotkey_label
    )
    
    _log("[App] Ready. Press F9 or click the overlay to begin.")
    _log("")
    
    # Run tray in main thread
    tray.run()
    
    # Run PyQt6 event loop on main thread (drives overlay updates)
    try:
        if app:
            app.exec()
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
