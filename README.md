# 🎙️ Voice-to-Text — Fully Local Real-Time Speech-to-Text

A fully local, system-wide, real-time voice-to-text desktop application for Windows, macOS, and Linux. Speak naturally and your words are transcribed by a local AI model and automatically typed into whatever application is currently focused.

**No cloud. No API keys. Everything runs on your machine.**

## What It Does

When you press F9 (or click the system tray icon), the app starts listening. As you speak, a floating overlay appears at the bottom of your screen showing live partial transcription updating in real-time. When you pause, the overlay disappears and the finalized text is automatically pasted into whatever window was focused before the overlay appeared.

## Requirements

- **Python**: 3.11 (exactly)
- **GPU**: NVIDIA GPU with CUDA 12.1 support (6GB+ VRAM recommended)
  - RTX 3050 (6GB) or better
  - Can run on CPU but will be slower
- **OS**: Windows, macOS, or Linux
- **Disk Space**: ~3GB for the large-v3-turbo model

## Installation

### Step 1: Install PyTorch with CUDA Support

**IMPORTANT**: PyTorch must be installed FIRST with the correct CUDA version.

#### Windows

Run the provided installer script:

```bash
install.bat
```

Or manually:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

#### macOS / Linux

Run the provided installer script:

```bash
chmod +x install.sh
./install.sh
```

Or manually:

**Linux (with CUDA):**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

**macOS:**
```bash
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

### Step 2: Platform-Specific Setup

#### macOS

**Accessibility Permission Required** for global hotkeys to work:

1. Go to **System Settings** → **Privacy & Security** → **Accessibility**
2. Click the **+** button
3. Add **Terminal** (or your Python IDE)
4. Restart the app

#### Linux

**Text Injection Tools** (for best Wayland support):

```bash
# Install text injection tools
sudo apt-get install xdotool wtype ydotool

# Enable ydotool daemon (for Wayland)
sudo systemctl enable --now ydotool

# Add your user to input group (required for ydotool)
sudo usermod -aG input $USER
```

Then **log out and log back in** for the group change to take effect.

## Running

```bash
python main.py
```

The app will:
1. Load the AI model (takes ~10-30 seconds on first run)
2. Show a microphone icon in your system tray
3. Wait for you to press F9 or click the tray icon

## Usage

### Starting/Stopping

- **Press F9** (or click the tray icon) to start listening
- The tray icon turns **green** when listening
- **Press F9 again** to stop listening

### Speaking

1. Press F9 to start
2. Speak naturally
3. A **floating overlay** appears at the bottom of your screen showing live transcription
4. When you pause, the overlay disappears and text is pasted into your focused window
5. Continue speaking for more transcriptions

### System Tray Menu

Right-click the tray icon to see:
- **Start/Stop Listening** (with hotkey)
- **Model info** (which model is loaded)
- **Device info** (CUDA or CPU)
- **Quit**

## Configuration

All settings are in `config.py`. Edit this file to customize behavior.

| Setting | Default | Options | Description |
|---------|---------|---------|-------------|
| `MODEL` | `"large-v3-turbo"` | `"tiny"`, `"base"`, `"small"`, `"medium"`, `"large-v2"`, `"large-v3"`, `"large-v3-turbo"` | Whisper model size. Larger = more accurate but slower and more VRAM. |
| `LANGUAGE` | `"en"` | `"en"`, `"es"`, `"fr"`, `"de"`, `None`, etc. | Language code or `None` for auto-detect. |
| `DEVICE` | `"cuda"` | `"cuda"`, `"cpu"` | Use GPU (cuda) or CPU. |
| `COMPUTE_TYPE` | `"int8_float16"` | `"int8_float16"`, `"float16"`, `"int8"`, `"float32"` | Precision mode. `int8_float16` recommended for 6GB VRAM (low memory, near-zero accuracy loss). |
| `INPUT_DEVICE_INDEX` | `None` | `None`, `0`, `1`, `2`, ... | Microphone to use. `None` = system default. See below for how to find your mic index. |
| `TOGGLE_KEY` | `keyboard.Key.f9` | Any `pynput` key | Hotkey to start/stop listening. |
| `INJECT_METHOD` | `"clipboard"` | `"clipboard"`, `"keyboard"` | How to inject text. `"clipboard"` is most reliable. |
| `VAD_SENSITIVITY` | `0.4` | `0.0` – `1.0` | Voice activity detection sensitivity. Higher = ignores more noise. |
| `POST_SPEECH_SILENCE` | `0.8` | seconds (float) | How long to wait after you stop speaking before finalizing. |
| `DEBUG_PRINT` | `True` | `True`, `False` | Print transcriptions to terminal. |

### Finding Your Microphone Index

If the app isn't picking up your microphone, or you want to use a specific mic:

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

This will print a list like:

```
  0 Built-in Microphone, Core Audio (2 in, 0 out)
  1 External USB Mic, Core Audio (1 in, 0 out)
* 2 Built-in Output, Core Audio (0 in, 2 out)
```

The number on the left is the index. Set `INPUT_DEVICE_INDEX = 1` in `config.py` to use "External USB Mic".

### Why `int8_float16` for `COMPUTE_TYPE`?

The `large-v3-turbo` model in full `float16` precision uses ~3GB VRAM. Under real workloads (browser, IDE, etc. open), this can cause out-of-memory errors on a 6GB card like the RTX 3050.

`int8_float16` reduces VRAM usage to ~1.8GB with **negligible accuracy difference** (typically <1% word error rate increase). This is the recommended default.

If you have more VRAM (8GB+), you can use `float16` for slightly better accuracy.

## Model Selection Guide

| Model | VRAM (int8_float16) | VRAM (float16) | Speed | Accuracy |
|-------|---------------------|----------------|-------|----------|
| `tiny` | ~400MB | ~800MB | Very Fast | Low |
| `base` | ~500MB | ~1GB | Fast | Medium |
| `small` | ~800MB | ~1.5GB | Medium | Good |
| `medium` | ~1.2GB | ~2.5GB | Slow | Very Good |
| `large-v2` | ~2GB | ~4GB | Slower | Excellent |
| `large-v3` | ~2GB | ~4GB | Slower | Excellent |
| `large-v3-turbo` | ~1.8GB | ~3GB | Medium | Excellent |

**Recommended**: `large-v3-turbo` with `int8_float16` for best balance of speed, accuracy, and VRAM usage.

## Troubleshooting

### "CUDA not available" or "out of memory"

**Solution 1**: Use `int8_float16` compute type (default)

```python
COMPUTE_TYPE = "int8_float16"
```

**Solution 2**: Use a smaller model

```python
MODEL = "base"  # or "small"
```

**Solution 3**: Fall back to CPU

```python
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
```

### "No module named 'RealtimeSTT'"

You didn't install dependencies. Run:

```bash
pip install -r requirements.txt
```

### Hotkey (F9) doesn't work on macOS

You need to grant Accessibility permission. See **Platform-Specific Setup** above.

### Text injection doesn't work on Linux (Wayland)

Install text injection tools:

```bash
sudo apt-get install wtype ydotool
sudo systemctl enable --now ydotool
sudo usermod -aG input $USER
```

Then **log out and log back in**.

### "Invalid INPUT_DEVICE_INDEX"

List available microphones:

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

Set `INPUT_DEVICE_INDEX` in `config.py` to the correct index.

### Clipboard gets overwritten

This is expected behavior when using `INJECT_METHOD = "clipboard"`. The app saves your clipboard, pastes the transcription, then restores your clipboard.

If this is problematic, try:

```python
INJECT_METHOD = "keyboard"
```

Note: `"keyboard"` method is less reliable on some systems.

### Model download fails

The model downloads automatically on first run from Hugging Face. If download fails:

1. Check your internet connection
2. Try again (downloads resume automatically)
3. Manually download from: https://huggingface.co/Systran/faster-whisper-large-v3-turbo

### Transcription is slow

**Solution 1**: Use a smaller model

```python
MODEL = "base"  # Much faster, less accurate
```

**Solution 2**: Check you're using GPU

```python
DEVICE = "cuda"  # Not "cpu"
```

**Solution 3**: Close other GPU-heavy apps (games, video editors, etc.)

### Transcription is inaccurate

**Solution 1**: Use a larger model

```python
MODEL = "large-v3"  # More accurate, slower
```

**Solution 2**: Adjust VAD sensitivity

```python
VAD_SENSITIVITY = 0.5  # Higher = less background noise picked up
```

**Solution 3**: Use a better microphone or reduce background noise

## How It Works

1. **Audio Capture**: Uses `sounddevice` to capture audio from your microphone
2. **Voice Activity Detection**: Silero VAD detects when you're speaking vs. silence
3. **Speech-to-Text**: faster-whisper (local Whisper model) transcribes your speech
4. **Real-Time Updates**: Partial transcriptions stream to the overlay as you speak
5. **Text Injection**: On silence, finalized text is pasted into your focused window

All processing happens **locally on your machine**. No data is sent to the cloud.

## 🚀 Roadmap

### Phase 1: Core Engine (Completed)
- [x] Real-time local transcription
- [x] Floating glassmorphism overlay
- [x] Global hotkey support
- [x] Multi-model support (Tiny to Large)

### Phase 2: Professional Polish (Completed)
- [x] **Settings GUI**: Full glassmorphism interface for easy configuration
- [x] **Microphone Selector**: Switch inputs directly from the UI
- [x] **Model Management**: Download and delete models to save disk space
- [x] **Standalone Executable**: Professional Windows installer (.exe)
- [x] **Hallucination Filter**: Clean, professional-grade transcriptions

### Phase 3: Future Enhancements (Coming Soon)
- [ ] **Real-time Waveform**: Animated audio visualizer in the overlay
- [ ] **LocalVoice Lite**: A lightweight, CPU-optimized version (<200MB)
- [ ] **Auto-Updater**: One-click updates from the cloud
- [ ] **Global Push-to-Talk**: Hold a key to record instead of toggle
- [ ] **Auto-start on login**

## License

MIT License — see LICENSE file for details.

## Credits

Built with:
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — Fast Whisper inference
- [RealtimeSTT](https://github.com/KoljaB/RealtimeSTT) — Real-time speech-to-text pipeline
- [pynput](https://github.com/moses-palmer/pynput) — Global hotkeys and text injection
- [pystray](https://github.com/moses-palmer/pystray) — System tray icon
