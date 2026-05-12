"""
Text injector — injects transcribed text into the currently focused window.
"""

import os
import time
import platform
import pyperclip
from pynput.keyboard import Controller, Key


def inject_text(text: str, method: str = "clipboard") -> None:
    """
    Inject text into the currently focused window.
    
    Args:
        text: The text to inject
        method: "clipboard" (default, most reliable) or "keyboard"
    """
    # Strip whitespace
    text = text.strip()
    
    # Do nothing if empty
    if not text:
        return

    # Don't inject into our own app
    if platform.system() == "Windows":
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == os.getpid():
                    print("[Injector] Skipping injection: our own app is focused.")
                    return
        except Exception:
            pass
            
    # Append space for natural continuation if not present
    if text and not text.endswith(" "):
        text = text + " "
    
    if method == "clipboard":
        _inject_via_clipboard(text)
    else:
        _inject_via_keyboard(text)


def _inject_via_clipboard(text: str) -> None:
    """Inject text by copying to clipboard and pasting."""
    # Save current clipboard content
    old_clipboard = ""
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        pass  # Clipboard may be empty or locked
    
    # Copy new text
    pyperclip.copy(text)
    
    # Verify clipboard updated before pasting
    deadline = time.time() + 0.5  # 500ms max wait
    while pyperclip.paste() != text:
        if time.time() > deadline:
            break  # proceed anyway — best effort
        time.sleep(0.01)
    
    # Send paste command (platform-specific)
    os_name = platform.system()
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    is_wayland = os_name == "Linux" and "wayland" in session
    
    if os_name == "Darwin":  # macOS
        keyboard = Controller()
        keyboard.press(Key.cmd)
        keyboard.press('v')
        keyboard.release('v')
        keyboard.release(Key.cmd)
    
    elif is_wayland:
        # On Wayland, pynput.Controller can't send keys — use wtype/ydotool
        if not _try_paste_wayland():
            print("[Injector] WARNING: Install 'wtype' for auto-paste on Wayland.")
            print("[Injector]          sudo apt-get install wtype")
            print("[Injector]          Text is on clipboard — press Ctrl+V manually.")
    
    else:  # Windows / Linux X11
        keyboard = Controller()
        keyboard.press(Key.ctrl)
        keyboard.press('v')
        keyboard.release('v')
        keyboard.release(Key.ctrl)
    
    # Wait for paste to land
    time.sleep(0.1)
    
    # Restore old clipboard content
    try:
        pyperclip.copy(old_clipboard)
    except Exception:
        pass  # Best effort


def _try_paste_wayland() -> bool:
    """Try to simulate Ctrl+V paste on Wayland using wtype or ydotool."""
    import subprocess
    
    # Try wtype first (sends keys directly on Wayland)
    try:
        subprocess.run(['wtype', '-k', 'ctrl', '-k', 'v'], check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    
    # Try ydotool as fallback
    try:
        subprocess.run(['ydotool', 'key', '29:1', '47:1', '47:0', '29:0'], 
                      check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    
    return False


def _inject_via_keyboard(text: str) -> None:
    """Inject text by simulating keyboard typing."""
    os_name = platform.system()
    
    if os_name == "Linux":
        # Try Linux tools in priority order
        if _try_wtype(text):
            return
        if _try_ydotool(text):
            return
        if _try_xdotool(text):
            return
        # Fall back to pynput
        print("[Injector] Warning: wtype, ydotool, and xdotool not available. Using pynput fallback.")
    
    # Windows/macOS or Linux fallback
    keyboard = Controller()
    keyboard.type(text)


def _try_wtype(text: str) -> bool:
    """Try to inject using wtype (Wayland)."""
    import subprocess
    try:
        # -d 10 = 10ms delay between keystrokes to prevent compositor
        # from misinterpreting fast bursts as system shortcuts
        subprocess.run(['wtype', '-d', '10', text], check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _try_ydotool(text: str) -> bool:
    """Try to inject using ydotool (Wayland kernel-level)."""
    import subprocess
    try:
        subprocess.run(['ydotool', 'type', text], check=True, capture_output=True)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        print("[Injector] Warning: ydotool found but failed. Run: sudo systemctl enable --now ydotool")
        return False


def _try_xdotool(text: str) -> bool:
    """Try to inject using xdotool (X11 only)."""
    import subprocess
    try:
        subprocess.run(['xdotool', 'type', '--', text], check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def delete_text(count: int) -> None:
    """Delete N characters using Backspace.
    
    Sends backspaces in small batches with delays to prevent
    the Wayland compositor from misinterpreting rapid key bursts
    as system shortcuts (which can open random apps/dialogs).
    """
    import os  # Explicit local import to fix NameError
    if count <= 0:
        return
        
    os_name = platform.system()
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    is_wayland = os_name == "Linux" and "wayland" in session
    
    if is_wayland:
        import subprocess
        BATCH = 5  # Send at most 5 backspaces per wtype call
        try:
            remaining = count
            while remaining > 0:
                n = min(remaining, BATCH)
                cmd = ['wtype', '-d', '20']  # 20ms delay between keys
                for _ in range(n):
                    cmd.extend(['-k', 'backspace'])
                subprocess.run(cmd, check=True, capture_output=True)
                remaining -= n
                if remaining > 0:
                    time.sleep(0.03)  # 30ms pause between batches
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    # Fallback to pynput
    keyboard = Controller()
    for _ in range(count):
        keyboard.press(Key.backspace)
        keyboard.release(Key.backspace)
        time.sleep(0.01)

