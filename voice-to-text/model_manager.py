"""
Model Manager — Whisper model registry, download detection, and download logic.

Provides a central source of truth for:
  • Available models and their approximate sizes
  • Whether a specific model is already cached locally
  • Downloading a model on demand with progress callbacks
"""

import os
import threading
import time
import shutil
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Model registry — ordered smallest → largest
# ---------------------------------------------------------------------------
# Each entry: (display_name, approx_size_mb, hf_repo_id)
# hf_repo_id is what faster-whisper actually downloads from HuggingFace.

MODELS = [
    {
        "name": "tiny",
        "size_mb": 75,
        "size_label": "~75 MB",
        "hf_repo": "Systran/faster-whisper-tiny",
        "description": "Fastest · Low accuracy",
        "speed": "★★★★★",
        "accuracy": "★★☆☆☆",
    },
    {
        "name": "base",
        "size_mb": 145,
        "size_label": "~145 MB",
        "hf_repo": "Systran/faster-whisper-base",
        "description": "Fast · Moderate accuracy",
        "speed": "★★★★☆",
        "accuracy": "★★★☆☆",
    },
    {
        "name": "small",
        "size_mb": 465,
        "size_label": "~465 MB",
        "hf_repo": "Systran/faster-whisper-small",
        "description": "Balanced speed & accuracy",
        "speed": "★★★☆☆",
        "accuracy": "★★★★☆",
    },
    {
        "name": "medium",
        "size_mb": 1500,
        "size_label": "~1.5 GB",
        "hf_repo": "Systran/faster-whisper-medium",
        "description": "Slower · High accuracy",
        "speed": "★★☆☆☆",
        "accuracy": "★★★★☆",
    },
    {
        "name": "large-v2",
        "size_mb": 3100,
        "size_label": "~3.1 GB",
        "hf_repo": "Systran/faster-whisper-large-v2",
        "description": "Slow · Very high accuracy",
        "speed": "★☆☆☆☆",
        "accuracy": "★★★★★",
    },
    {
        "name": "large-v3",
        "size_mb": 3100,
        "size_label": "~3.1 GB",
        "hf_repo": "Systran/faster-whisper-large-v3",
        "description": "Slow · Best accuracy (v3)",
        "speed": "★☆☆☆☆",
        "accuracy": "★★★★★",
    },
    {
        "name": "large-v3-turbo",
        "size_mb": 1600,
        "size_label": "~1.6 GB",
        "hf_repo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        "description": "Fast · Near-best accuracy",
        "speed": "★★★★☆",
        "accuracy": "★★★★★",
    },
]

MODEL_NAMES = [m["name"] for m in MODELS]


def get_model_info(model_name: str) -> Optional[dict]:
    """Return metadata dict for a model, or None if unknown."""
    for m in MODELS:
        if m["name"] == model_name:
            return m
    return None


def _get_models_dir() -> Path:
    """Return the HF cache directory where models are stored."""
    return Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface" / "hub"))


def _hf_repo_to_dir_name(hf_repo: str) -> str:
    """Convert 'Systran/faster-whisper-tiny' → 'models--Systran--faster-whisper-tiny'."""
    return "models--" + hf_repo.replace("/", "--")


def is_model_downloaded(model_name: str) -> bool:
    """Check if a model's files exist in the local HF cache.
    
    HuggingFace stores blobs separately and creates symlinks in snapshots/.
    We use f.stat() which follows symlinks to get the real file size.
    """
    info = get_model_info(model_name)
    if not info:
        return False

    models_dir = _get_models_dir()
    model_dir = models_dir / _hf_repo_to_dir_name(info["hf_repo"])
    snapshots_dir = model_dir / "snapshots"

    if not snapshots_dir.exists():
        return False

    # Check that at least one snapshot has actual model files
    for snapshot in snapshots_dir.iterdir():
        if snapshot.is_dir():
            total_size = 0
            for f in snapshot.iterdir():
                try:
                    # .stat() follows symlinks — critical for HF cache layout
                    if f.is_file() or f.is_symlink():
                        total_size += f.stat().st_size
                except OSError:
                    pass
            # A valid model download should be at least 10MB
            if total_size > 10 * 1024 * 1024:
                return True

    return False


def delete_model(model_name: str) -> bool:
    """Delete a model's files from the local HF cache.
    Returns True if successful, False if model not found or deletion failed.
    """
    info = get_model_info(model_name)
    if not info:
        return False

    try:
        models_dir = _get_models_dir()
        model_dir = models_dir / _hf_repo_to_dir_name(info["hf_repo"])
        
        if model_dir.exists():
            shutil.rmtree(model_dir)
            
            # Also clean up the 'locks' directory if it exists
            locks_dir = models_dir / ".locks" / _hf_repo_to_dir_name(info["hf_repo"])
            if locks_dir.exists():
                shutil.rmtree(locks_dir)
                
            return True
    except Exception as e:
        print(f"[ModelManager] Error deleting model {model_name}: {e}")
        
    return False


def get_downloaded_models() -> list[str]:
    """Return list of model names that are already downloaded."""
    return [m["name"] for m in MODELS if is_model_downloaded(m["name"])]


def download_model(
    model_name: str,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    done_callback: Optional[Callable[[bool, str], None]] = None,
) -> threading.Thread:
    """Download a model in a background thread.
    
    Args:
        model_name: Name of the model to download (e.g. 'small')
        progress_callback: Called with (percent: float, message: str)
        done_callback: Called with (success: bool, message: str) when finished
    
    Returns:
        The background thread (already started).
    """
    info = get_model_info(model_name)
    if not info:
        if done_callback:
            done_callback(False, f"Unknown model: {model_name}")
        return threading.current_thread()

    def _download():
        try:
            if progress_callback:
                progress_callback(0, f"Preparing to download {model_name}...")

            # Use huggingface_hub to download the model
            from huggingface_hub import snapshot_download

            models_dir = _get_models_dir()

            # Start a size monitor in a sub-thread for progress updates
            target_mb = info["size_mb"]
            model_dir = models_dir / _hf_repo_to_dir_name(info["hf_repo"])
            stop_monitor = threading.Event()

            def _monitor():
                start_time = time.time()
                while not stop_monitor.is_set():
                    time.sleep(1)
                    try:
                        current_size = 0
                        if model_dir.exists():
                            for f in model_dir.rglob("*"):
                                if f.is_file():
                                    try:
                                        current_size += f.stat().st_size
                                    except OSError:
                                        pass
                        mb = current_size / (1024 * 1024)
                        pct = min(95, int(mb / target_mb * 100))
                        elapsed = int(time.time() - start_time)

                        if mb < 1:
                            msg = f"Connecting... ({elapsed}s)"
                        else:
                            speed = mb / max(elapsed, 1)
                            remaining = target_mb - mb
                            eta = int(remaining / speed) if speed > 0.1 else 0
                            if eta > 60:
                                eta_str = f"~{eta // 60}m {eta % 60}s left"
                            elif eta > 0:
                                eta_str = f"~{eta}s left"
                            else:
                                eta_str = "Almost done..."
                            msg = f"{mb:.0f} MB / {target_mb} MB · {eta_str}"

                        if progress_callback:
                            progress_callback(pct, msg)
                    except Exception:
                        pass

            monitor_thread = threading.Thread(target=_monitor, daemon=True)
            monitor_thread.start()

            # Actually download the model
            snapshot_download(
                repo_id=info["hf_repo"],
                cache_dir=str(models_dir),
            )

            stop_monitor.set()
            monitor_thread.join(timeout=2)

            if progress_callback:
                progress_callback(100, "Download complete!")

            if done_callback:
                done_callback(True, f"Model '{model_name}' downloaded successfully!")

        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {e}")
            if done_callback:
                done_callback(False, str(e))

    t = threading.Thread(target=_download, daemon=True)
    t.start()
    return t
