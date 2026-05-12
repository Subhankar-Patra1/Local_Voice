# Technical Documentation: HOW_IT_WORKS.md

This document provides a ground-truth technical analysis of the **Local Voice** application architecture based on the current implementation.

---

## 1. System Architecture
The application operates as a multi-threaded system where the UI, Audio Capture, and Text Injection are decoupled to prevent deadlocks and ensure low-latency feedback.

### 🧩 Data Flow: Mic to Text
1.  **Mic Input**: Audio is captured via `sounddevice` (inside `RealtimeSTT`).
2.  **VAD Gate**: `Silero VAD` filters silence; only speech audio enters the buffer.
3.  **Inference**: `faster-whisper` processes the buffer into text hypotheses.
4.  **Callback**: `recorder.py` receives partial and stabilized text via callbacks.
5.  **Commitment Logic**: `_get_new_content` calculates the delta (new text only).
6.  **Injection**: `injector.py` pushes text into the system clipboard and simulates a paste command.

### 📊 ASCII Diagram
```text
[ Microphone ] 
      |
      v
[ RealtimeSTT ] -> (Thread A) -> [ VAD Filter ] -> [ Faster-Whisper ]
      |                                                 |
      v                                                 v
[ main.py ] <---- (Callback) ------------------ [ recorder.py ]
      |                                         (Commitment Logic)
      v
[ injector.py ] -> (System Clipboard) -> [ Target App ]
```

---

## 2. STT Pipeline
The project utilizes `RealtimeSTT` to wrap `faster-whisper` for efficient local inference.

*   **Model**: Defaults to `large-v3-turbo` for high accuracy with low latency.
*   **Device**: Auto-detects `cuda` (NVIDIA) or `cpu`. For CUDA, it uses `int8_float16` quantization to save VRAM.
*   **RealtimeSTT Wrapper**: Manages the `audio_queue` and the `_recording_worker` thread. It performs constant decoding on partial audio buffers.
*   **VAD**: Controlled by `VAD_SENSITIVITY` (0.4) and `POST_SPEECH_SILENCE` (0.8s) in `config.py`.

---

## 3. Duplicate Prevention (Honest Analysis)
The "Incremental Commitment Engine" is a custom string-comparison mechanism designed to prevent the AI from double-typing when it updates its hypothesis.

### 📝 The Core Logic (`recorder.py`):
```python
def _get_new_content(self, text: str) -> str:
    def normalize(s):
        return "".join(c for c in s if c.isalnum()).lower()
        
    norm_full = normalize(text)
    if norm_full.startswith(self._injected_norm):
        # Calculate exactly where the new part starts in the original string
        match_idx = 0
        norm_ptr = 0
        for i, char in enumerate(text):
            if normalize(char):
                norm_ptr += 1
            if norm_ptr == len(self._injected_norm):
                match_idx = i + 1
                break
        
        new_part = text[match_idx:]
        self._injected_norm = norm_full
        return new_part
```
**Mechanism**: It is a **prefix-match guard**. It keeps a normalized version of everything already typed. When a new transcription update arrives, it checks if the update starts with what was already sent. If it does, it only types the "tail" (new characters).

---

## 4. Text Injection
The application uses a hybrid approach to "type" into other windows.

### 📋 The Verification Loop (`injector.py`):
To ensure text isn't lost during rapid typing, we use a verification loop when using the clipboard method:
```python
pyperclip.copy(text)
deadline = time.time() + 0.5
while pyperclip.paste() != text:
    if time.time() > deadline: break
    time.sleep(0.01)
```

### ⚡ Fallback Chain:
1.  **Wayland**: Attempts `wtype` (direct keys) -> `ydotool` -> Clipboard.
2.  **X11/Windows**: Defaults to the **Clipboard Method** (Copy + Ctrl+V) for maximum reliability across complex character sets (like Bengali/Hindi).

---

## 5. UI Architecture
Contrary to common lightweight tools using Tkinter, this project is built on **PyQt6** for high-performance rendering and alpha-transparency.

*   **Frameless Design**: The overlay (`overlay.py`) is a `QWidget` with `Qt.WindowType.FramelessWindowHint`.
*   **Threading**: The AI runs in a native Python thread (`threading.Thread`). Updates to the UI are handled via regular attribute setting and repaint events, as `PyQt6` is generally safe for non-blocking attribute updates if triggered by the main loop.
*   **Glassmorphism**: It is **simulated**. We use `rgba` backgrounds with 0.98 opacity and `QGraphicsDropShadowEffect`. Real OS-level blur (Mica/Acrylic) is not natively supported by PyQt6 on Linux without compositor extensions.

---

## 6. Settings & Persistence
*   **Location**: `~/.config/voice-to-text/settings.json`
*   **Saved**: Model name, device (CPU/GPU), language, shortcut key, and autostart state.
*   **Reset**: The internal `_injected_norm` buffer (duplicate prevention) resets every time you stop recording or finalize a sentence.

---

## 7. Known Limitations
1.  **RAM/VRAM**: `large-v3-turbo` requires ~4GB VRAM. CPU mode requires ~6GB RAM and is significantly slower.
2.  **Hallucinations**: During long silences, the model may hallucinate "dots" or "thank you." We have a regex filter in `main.py` to strip these.
3.  **Non-English Accuracy**: While Whisper supports 99 languages, accuracy drops significantly for languages like **Bengali** compared to English, especially with background noise.
4.  **Wayland Hotkeys**: Global hotkeys (F9) are unreliable on Wayland due to protocol security; users should rely on the UI toggle button.

---

## 8. Privacy
*   **No Cloud Calls**: Transcription is 100% local. No audio or text is sent to external servers.
*   **One-Time Download**: On first launch, the app connects to **HuggingFace** to download the chosen model (~1.5GB). After that, the internet is not required.
