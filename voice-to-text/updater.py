import threading
import urllib.request
import json
import webbrowser
from PyQt6.QtCore import QObject, pyqtSignal

import config

class UpdateChecker(QObject):
    update_available = pyqtSignal(str, str) # version, url
    
    def __init__(self):
        super().__init__()
        self.repo_url = "https://api.github.com/repos/subhankar-patra/LocalVoice/releases/latest"
        self.releases_page = "https://github.com/subhankar-patra/LocalVoice/releases/latest"
        
    def check_for_updates(self):
        """Run the update check in a background thread."""
        def _check():
            try:
                # Add a timeout so it doesn't hang startup
                req = urllib.request.Request(
                    self.repo_url, 
                    headers={'User-Agent': 'LocalVoice-App'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    latest_version = data.get("tag_name", "")
                    html_url = data.get("html_url", self.releases_page)
                    
                    if latest_version and self._is_newer(config.VERSION, latest_version):
                        # Use QTimer or just emit signal (pyqtSignals are thread-safe if connected across threads)
                        self.update_available.emit(latest_version, html_url)
            except Exception as e:
                # Silently fail on network issues (we don't want to bother the user)
                print(f"[Updater] Update check failed: {e}")
                
        threading.Thread(target=_check, daemon=True).start()
        
    def _is_newer(self, current: str, latest: str) -> bool:
        """Compare versions like 'v1.0.0' vs 'v1.1.0'"""
        try:
            curr_parts = [int(x) for x in current.strip('v').split('.')]
            latest_parts = [int(x) for x in latest.strip('v').split('.')]
            
            # Pad with zeros if different lengths
            while len(curr_parts) < len(latest_parts): curr_parts.append(0)
            while len(latest_parts) < len(curr_parts): latest_parts.append(0)
            
            for c, l in zip(curr_parts, latest_parts):
                if l > c:
                    return True
                elif l < c:
                    return False
            return False
        except Exception:
            # If parsing fails, just do simple string comparison fallback
            return latest != current

def open_url(url: str):
    webbrowser.open(url)
