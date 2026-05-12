"""
Voice recorder — wraps RealtimeSTT for speech-to-text.
"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

# Suppress ALSA/JACK warnings from PortAudio
# ALSA writes directly to OS file descriptor 2, so we use os.dup2()
def _suppress_stderr_fd():
    """Redirect OS-level stderr (fd 2) to /dev/null."""
    _devnull = os.open(os.devnull, os.O_WRONLY)
    _saved_stderr = os.dup(2)
    os.dup2(_devnull, 2)
    return _saved_stderr, _devnull

def _restore_stderr_fd(_saved_stderr, _devnull):
    """Restore OS-level stderr."""
    os.dup2(_saved_stderr, 2)
    os.close(_devnull)
    os.close(_saved_stderr)

try:
    from RealtimeSTT import AudioToTextRecorder
except ImportError:
    print("[Recorder] ERROR: RealtimeSTT not installed.")
    print("[Recorder] Install with: pip install RealtimeSTT>=0.3.0")
    sys.exit(1)


# Global flag for download monitor to stop when model is loaded
_download_done = threading.Event()

def _monitor_download(progress_callback=None):
    """Background thread: monitor download progress by tracking NEW files.
    
    Args:
        progress_callback: Optional callable(percent: float, message: str)
                          Called every second with download progress for the overlay UI.
    """
    # HF_HOME is set by main.py before this import
    models_dir = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface" / "hub"))
    torch_hub = Path.home() / ".cache" / "torch" / "hub"
    
    # Target sizes for large-v3-turbo + Silero VAD
    TARGET_MB = 1550
    
    print("[Download] Monitoring download progress...")
    print("[Download] Note: File size may stay at 0 for 30-60s while buffering.")
    print()
    
    # Baseline: what exists BEFORE we start downloading
    def _get_size(dirs):
        total = 0
        for d in dirs:
            if d.exists():
                try:
                    for f in d.rglob("*"):
                        if f.is_file():
                            try:
                                total += f.stat().st_size
                            except OSError:
                                pass # File might have been moved/deleted by the downloader
                except OSError:
                    pass
        return total
    
    dirs = [models_dir, torch_hub]
    baseline = _get_size(dirs)
    last_mb = -1
    start_time = time.time()
    spin_chars = ["|", "/", "-", "\\"]
    spin_idx = 0
    
    for _ in range(600):  # 10 minutes max (600 * 1s)
        # Check if loading is done
        if _download_done.is_set():
            break
        
        time.sleep(1)
        
        # Only count NEW bytes added since baseline
        current = _get_size(dirs)
        delta = max(0, current - baseline)
        mb = delta / (1024 * 1024)
        elapsed = int(time.time() - start_time)
        pct = min(100, int(mb / TARGET_MB * 100))
        
        # Always update every 2 seconds with spinner, even if size hasn't changed
        if mb != last_mb or elapsed % 2 == 0:
            bar_len = 30
            filled = int(min(mb, TARGET_MB) / TARGET_MB * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            spin = spin_chars[spin_idx % 4]
            spin_idx += 1
            
            if mb < 1:
                # Still buffering — show spinner only
                print(f"\r[Download] {spin}  Waiting for download to start...  ({elapsed}s elapsed)  ", end="", flush=True)
                if progress_callback:
                    progress_callback(0, f"Connecting... ({elapsed}s)\nRequires internet · ~1.5 GB download")
            else:
                print(f"\r[Download] {bar}  {mb:6.1f}MB / ~{TARGET_MB}MB  ({pct}%)  ", end="", flush=True)
                # Estimate time remaining
                speed = mb / max(elapsed, 1)  # MB/s
                remaining_mb = TARGET_MB - mb
                eta_sec = int(remaining_mb / speed) if speed > 0.1 else 0
                if eta_sec > 60:
                    eta_str = f"~{eta_sec // 60}m {eta_sec % 60}s left"
                elif eta_sec > 0:
                    eta_str = f"~{eta_sec}s left"
                else:
                    eta_str = "Almost done..."
                if progress_callback:
                    progress_callback(pct, f"{mb:.0f} MB / {TARGET_MB} MB · {eta_str}")
            last_mb = mb
        
        if mb > TARGET_MB * 0.95:
            if progress_callback:
                progress_callback(99, "Finalizing model load...")
            break
    
    # Clear the line and print done
    print(f"\r{' '*70}\r[Download] Done.")

import config
from injector import inject_text


class VoiceRecorder:
    """Voice recorder with real-time transcription."""
    
    def __init__(
        self,
        on_text: Optional[Callable[[str], None]] = None,
        on_partial: Optional[Callable[[str], None]] = None,
        on_loading: Optional[Callable[[str], None]] = None,
        on_download_progress: Optional[Callable[[float, str], None]] = None
    ):
        """
        Initialize voice recorder.
        
        Args:
            on_text: Callback for finalized or stabilized transcription
            on_partial: Callback for partial (live) transcription
            on_loading: Callback for loading status messages
            on_download_progress: Callback(percent, message) for download progress
        """
        self.on_text = on_text or self._default_on_text
        self.on_partial = on_partial or self._default_on_partial
        self.on_loading = on_loading
        self.on_download_progress = on_download_progress
        
        self.recorder = None
        self._running = False
        self._thread = None
        self._model_loaded = False
        self._injected_norm = "" # Track normalized text already emitted to prevent duplicates
        self._inject_lock = threading.RLock() # Use RLock to prevent deadlock since _get_new_content and callers use it
        self._last_final_text = ""
        self._last_stabilized_text = ""
        self._last_stabilized_len = 0
    
    def start(self) -> None:
        """Start recording in background thread."""
        if self._running:
            return
        
        self._running = True
        self._injected_norm = ""
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop recording."""
        self._running = False
        
        # Stop the internal AudioToTextRecorder to shut down its threads
        if self.recorder is not None:
            try:
                self.recorder.stop()
            except Exception:
                pass  # Already stopped or not initialized
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
    
    def is_running(self) -> bool:
        """Check if recorder is running."""
        return self._running
    
    def _record_loop(self) -> None:
        """Main recording loop (runs in background thread)."""
        try:
            # Create recorder if not exists
            if self.recorder is None:
                self._create_recorder()
            else:
                # If reusing the recorder, we must explicitly start it again
                # so it doesn't instantly return cached text in an infinite loop.
                try:
                    self.recorder.abort() # clear old buffers
                except Exception:
                    pass
                self.recorder.start()
            
            print("[Recorder] Waiting for speech...")
            
            # Process speech in loop
            while self._running:
                try:
                    # This blocks until a sentence is finalized
                    text = self.recorder.text()
                    
                    if not self._running:
                        break
                    
                    # Print final transcription
                    if config.DEBUG_PRINT and text.strip():
                        print(f"\n[Final]   {text}")
                    
                    if not text.strip():
                        continue
                    
                    # Exact duplicate guard — RealtimeSTT upstream bug fires same sentence twice
                    if text.strip() == self._last_final_text:
                        continue
                    
                    self._last_final_text = text.strip()
                    
                    # Zone 2 is display-only, so inject the full final text here
                    self.on_text(text.strip())
                
                except Exception as e:
                    if self._running:
                        print(f"[Recorder] Error in recording loop: {e}")
                        break
        
        except Exception as e:
            print(f"[Recorder] Fatal error: {e}")
            self._running = False
    
    def _get_new_content(self, text: str) -> str:
        """Calculate the part of 'text' that hasn't been injected yet."""
        with self._inject_lock:
            def normalize(s):
                return "".join(c for c in s if c.isalnum()).lower()
                
            norm_full = normalize(text)
            if not norm_full:
                return ""
                
            if not self._injected_norm:
                self._injected_norm = norm_full
                return text
                
            if norm_full.startswith(self._injected_norm):
                # Find the split point in the original string
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
                
            # If the new text is completely different (shouldn't happen in a segment), reset
            self._injected_norm = norm_full
            return text

    def _create_recorder(self) -> None:
        """Create and configure the AudioToTextRecorder."""
        # Check if model is already cached (skip download UI on subsequent runs)
        models_dir = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface" / "hub"))
        cached_size_mb = 0
        if models_dir.exists():
            for f in models_dir.rglob("*"):
                if f.is_file():
                    cached_size_mb += f.stat().st_size
            cached_size_mb /= (1024 * 1024)
        
        model_is_cached = cached_size_mb > 500  # Model is ~1.5GB, so >500MB means it's there
        
        if model_is_cached:
            print(f"\n{'='*50}")
            print(f"  Loading AI model: {config.MODEL} (cached)")
            print(f"  Device: {config.DEVICE.upper()}")
            print(f"{'='*50}\n")
            
            if self.on_loading:
                self.on_loading("loading")
        else:
            print(f"\n{'='*50}")
            print(f"  Loading AI model: {config.MODEL}")
            print(f"  Device: {config.DEVICE.upper()}")
            print(f"  Step 1/2: Downloading Silero VAD (~50MB)  —  ~10-30s")
            print(f"  Step 2/2: Downloading Whisper model (~1.5GB)  —  ~2-5min")
            print(f"{'='*50}\n")
            
            if self.on_loading:
                self.on_loading("downloading")
            
            # Start download monitor thread (only needed for first-time download)
            monitor = threading.Thread(
                target=_monitor_download,
                args=(self.on_download_progress,),
                daemon=True
            )
            monitor.start()
        
        # Suppress ALSA/JACK stderr noise at OS level
        _saved_stderr, _devnull = _suppress_stderr_fd()
        try:
            self.recorder = AudioToTextRecorder(
                model=config.MODEL,
                language=config.LANGUAGE,
                device=config.DEVICE,
                compute_type=config.COMPUTE_TYPE,
                input_device_index=config.INPUT_DEVICE_INDEX,
                silero_sensitivity=config.VAD_SENSITIVITY,
                post_speech_silence_duration=config.POST_SPEECH_SILENCE,
                enable_realtime_transcription=True,
                realtime_processing_pause=0.1,
                spinner=False,  # Disable built-in terminal spinner — we use overlay UI
                on_realtime_transcription_update=self._on_realtime_update,
                on_realtime_transcription_stabilized=self._on_realtime_stabilized
            )
            
            self._model_loaded = True
            _download_done.set()  # Stop the download monitor
            print(f"\n{'='*50}")
            print(f"  Model '{config.MODEL}' loaded successfully!")
            print(f"  Press F9 again or start speaking to stop.")
            print(f"{'='*50}\n")
            
            if self.on_loading:
                self.on_loading(None)  # Clear loading message
        
        except Exception as e:
            print(f"[Recorder] ERROR: Failed to load model: {e}")
            
            # Build a user-friendly error message
            if "CUDA" in str(e) or "out of memory" in str(e).lower():
                error_msg = "GPU out of memory"
                print("[Recorder] HINT: GPU out of memory. Try:")
                print("  1. Use a smaller model in Settings")
                print("  2. Set Processor to 'cpu' in Settings")
            elif "INPUT_DEVICE_INDEX" in str(e) or "device" in str(e).lower():
                error_msg = "Invalid audio device"
                print("[Recorder] HINT: Invalid audio device.")
            else:
                error_msg = str(e)[:80]
            
            self._running = False
            if self.on_loading:
                self.on_loading(f"error: {error_msg}")
            return  # Don't sys.exit — let user fix via Settings
        
        finally:
            _download_done.set()  # Always stop the download monitor
            _restore_stderr_fd(_saved_stderr, _devnull)
    
    def _on_realtime_update(self, text: str) -> None:
        """Called when partial transcription updates."""
        if not self._running:
            return  # Ignore callbacks after stop
        
        if config.DEBUG_PRINT and text.strip():
            # Print inline (overwrite same line)
            print(f"\r[Partial] {text:<60}", end='', flush=True)
        
        # Call partial callback
        self.on_partial(text)
    
    def _on_realtime_stabilized(self, text: str) -> None:
        """Called when partial transcription stabilizes (Zone 2).
        
        Display-only — shows stable preview in overlay.
        Injection happens only in Zone 3 (recorder.text()) after silence,
        because inject_text transforms text (strip + trailing space) making
        character-count-based backspace correction unreliable.
        """
        if not self._running or not text.strip():
            return

        # Show stabilized text in overlay for better preview
        # (more stable than Zone 1's raw guesses)
        self.on_partial(text)
    
    def _default_on_text(self, text: str) -> None:
        """Default final callback: inject text."""
        # Import here to avoid circular dependency
        from overlay import OverlayWindow
        
        # Hide overlay (if exists)
        # Note: This is handled in main.py, but kept here as fallback
        
        # Inject text
        inject_text(text, method=config.INJECT_METHOD)
        
        if config.DEBUG_PRINT:
            print(f"[Injector] Injected {len(text)} chars via {config.INJECT_METHOD}.")
    
    def _default_on_partial(self, text: str) -> None:
        """Default partial callback: do nothing."""
        pass
