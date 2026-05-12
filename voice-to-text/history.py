import json
import time
from collections import deque
from pathlib import Path
from typing import List, Dict

import config

MAX_HISTORY_ITEMS = 20

# In-memory history queue
_history = deque(maxlen=MAX_HISTORY_ITEMS)

def load_history() -> None:
    """Load history from disk."""
    if not config.HISTORY_FILE.parent.exists():
        config.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        
    if config.HISTORY_FILE.exists():
        try:
            with open(config.HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _history.clear()
                for item in data:
                    _history.append(item)
        except Exception as e:
            print(f"[History] Failed to load history: {e}")

def save_history() -> None:
    """Save history to disk."""
    try:
        with open(config.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(_history), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[History] Failed to save history: {e}")

def add_entry(text: str) -> None:
    """Add a new transcription entry to history."""
    if not text.strip():
        return
        
    entry = {
        "timestamp": time.time(),
        "text": text.strip()
    }
    _history.appendleft(entry)  # Newest first
    save_history()

def get_history() -> List[Dict]:
    """Get the current history list."""
    return list(_history)

# Load history on module import
load_history()
