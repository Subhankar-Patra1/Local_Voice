"""
Configuration settings for Voice-to-Text application.
All user-configurable settings live here.
"""

from pynput import keyboard
import os
import sys
import json
import shutil
import platform
from pathlib import Path

# ---------------------------------------------------------------------------
# Auto-detect CUDA
# ---------------------------------------------------------------------------
# If torch is installed and a GPU is present, default to GPU.
# Otherwise fall back to CPU so the app starts on any machine.

_CUDA_AVAILABLE = False
_DEVICE = "cpu"
_COMPUTE_TYPE = "int8"

try:
    import torch
    if torch.cuda.is_available():
        _CUDA_AVAILABLE = True
        _DEVICE = "cuda"
        _COMPUTE_TYPE = "int8"
except Exception:
    pass  # torch not installed — keep CPU fallback

# Default settings
MODEL = "large-v3-turbo"  # Options: "tiny" | "base" | "small" | "medium" | "large-v2" | "large-v3" | "large-v3-turbo"
LANGUAGE = "en"           # Set to "en" for English to prevent hallucinations (was None for auto-detect)
DEVICE = _DEVICE          # "cuda" or "cpu" — auto-detected above
COMPUTE_TYPE = _COMPUTE_TYPE 
INPUT_DEVICE_INDEX = None # None = system default mic
TOGGLE_KEY_STR = "<f9>"   # pynput format: <ctrl>+<alt>+k or <f9>
AUTO_START = False

SETTINGS_DIR = Path.home() / ".config" / "voice-to-text"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
HISTORY_FILE = SETTINGS_DIR / "history.json"

# Models and Temp Directories
IS_WINDOWS = platform.system() == "Windows"
if getattr(sys, 'frozen', False):
    if IS_WINDOWS:
        USER_CACHE_DIR = Path.home() / "AppData" / "Local" / "voice-to-text"
    else:
        USER_CACHE_DIR = Path.home() / ".cache" / "voice-to-text"
    MODELS_DIR = USER_CACHE_DIR / "models"
    TEMP_DIR = USER_CACHE_DIR / "temp"
else:
    PROJECT_ROOT = Path(__file__).resolve().parent
    D_DRIVE_PATH = Path("D:/Local_Voice")
    if IS_WINDOWS and D_DRIVE_PATH.exists():
        MODELS_DIR = D_DRIVE_PATH / "models"
        TEMP_DIR = D_DRIVE_PATH / "temp"
    else:
        MODELS_DIR = PROJECT_ROOT.parent / "models"
        TEMP_DIR = PROJECT_ROOT.parent / "temp"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

VERSION = "v1.0.0"

def load_settings():
    global MODEL, LANGUAGE, DEVICE, COMPUTE_TYPE, INPUT_DEVICE_INDEX, TOGGLE_KEY_STR, AUTO_START
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                MODEL = data.get("MODEL", MODEL)
                LANGUAGE = data.get("LANGUAGE", LANGUAGE)
                DEVICE = data.get("DEVICE", DEVICE)
                COMPUTE_TYPE = data.get("COMPUTE_TYPE", COMPUTE_TYPE)
                INPUT_DEVICE_INDEX = data.get("INPUT_DEVICE_INDEX", INPUT_DEVICE_INDEX)
                TOGGLE_KEY_STR = data.get("TOGGLE_KEY_STR", TOGGLE_KEY_STR)
                AUTO_START = data.get("AUTO_START", AUTO_START)
        except Exception:
            pass

def save_settings(new_settings):
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(new_settings, f, indent=4)
    
    _manage_autostart(new_settings.get("AUTO_START", False))

def _manage_autostart(enable):
    if platform.system() == "Windows":
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "LocalVoiceToText"
            
            # Determine the command to run
            if getattr(sys, 'frozen', False):
                # Running as .exe (PyInstaller)
                cmd = f'"{sys.executable}"'
            else:
                # Running as script
                python_exe = sys.executable
                script_path = Path(__file__).parent / "main.py"
                cmd = f'"{python_exe}" "{script_path}"'
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[Config] Windows autostart failed: {e}")

    elif platform.system() == "Linux":
        autostart_dir = Path.home() / ".config" / "autostart"
        desktop_file = autostart_dir / "voice-to-text.desktop"
        if enable:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            python_exe = sys.executable
            script_path = Path(__file__).parent / "main.py"
            # Launch in background, no terminal
            content = f"""[Desktop Entry]
Type=Application
Exec={python_exe} "{script_path}"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Voice-to-Text
Comment=AI Dictation Tool
"""
            with open(desktop_file, "w") as f:
                f.write(content)
        else:
            if desktop_file.exists():
                desktop_file.unlink()

def cleanup_temp():
    """Delete all files in the temp directory."""
    if TEMP_DIR.exists():
        try:
            for item in TEMP_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            print(f"[Config] Temp directory cleaned: {TEMP_DIR}")
        except Exception as e:
            print(f"[Config] Temp cleanup failed: {e}")

load_settings()

# Hotkey setup is now handled directly via TOGGLE_KEY_STR in GlobalHotKeys

# ---------------------------------------------------------------------------
# Auto-detect injection method
# ---------------------------------------------------------------------------
# "keyboard" = type directly into focused window (like Windows Win+H)
# "clipboard" = copy text, user pastes manually with Ctrl+V
# On Wayland, keyboard needs wtype/ydotool; clipboard is fallback.

_is_wayland = platform.system() == "Linux" and "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()
_has_wtype = shutil.which("wtype") is not None
_has_ydotool = shutil.which("ydotool") is not None

if _is_wayland and (_has_wtype or _has_ydotool):
    INJECT_METHOD = "keyboard"  # Direct typing — just like Windows dictation
    _inject_tool = "wtype" if _has_wtype else "ydotool"
    print(f"[Config] Wayland detected. Using '{_inject_tool}' for direct text typing.")
elif _is_wayland:
    INJECT_METHOD = "clipboard"  # Fallback — requires manual Ctrl+V
    print("[Config] Wayland detected but wtype/ydotool not found.")
    print("[Config] Install for auto-typing: sudo apt-get install wtype")
    print("[Config] Using clipboard fallback (paste manually with Ctrl+V).")
else:
    if platform.system() == "Windows":
        INJECT_METHOD = "keyboard"  # Direct typing — never touches clipboard
    else:
        INJECT_METHOD = "clipboard"  # X11 / macOS

# VAD
VAD_SENSITIVITY = 0.4       # 0.0–1.0. Higher = ignores more noise
POST_SPEECH_SILENCE = 0.8   # seconds of silence before finalizing

# Debug
DEBUG_PRINT = False  # print transcriptions to terminal (set True for debugging)

AI_PROCESSING = False
