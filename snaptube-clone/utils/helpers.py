import re
import os
import json
from pathlib import Path
from typing import Optional


# Path for storing settings
CONFIG_DIR = Path.home() / ".snaptube-clone"
CONFIG_FILE = CONFIG_DIR / "settings.json"


def ensure_config_dir():
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    """Load saved settings from config file."""
    ensure_config_dir()
    defaults = {
        "download_path": str(Path.home() / "Downloads" / "Snaptube-Clone"),
        "theme": "Dark",
        "max_playlist_items": 10,
        "auto_open_folder": False,
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
                defaults.update(saved)
        except (json.JSONDecodeError, IOError):
            pass
    return defaults


def save_settings(settings: dict):
    """Save settings to config file."""
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except IOError:
        pass


def extract_domain(url: str) -> str:
    """Extract domain name from URL."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        return match.group(1)
    return ""


def is_valid_url(url: str) -> bool:
    """Basic URL validation - just check it starts with http:// or https:// and has a domain."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    # Simple check: starts with http:// or https:// and has at least one dot after the protocol
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    # Must have at least a domain (something after protocol)
    rest = url.split("://", 1)[1] if "://" in url else url
    if not rest or len(rest) < 3:
        return False
    # Must contain at least one dot or be localhost
    if "." not in rest and "localhost" not in rest.lower():
        return False
    return True


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""
    invalid_chars = r'[<>:"/\\|?*]'
    return re.sub(invalid_chars, "_", filename)


def open_download_folder(path: str):
    """Open the download folder in file explorer."""
    try:
        os.startfile(path)
    except AttributeError:
        # Fallback for non-Windows
        import subprocess
        subprocess.Popen(["xdg-open", path])


def get_icon_path() -> str:
    """Return path to app icon."""
    return str(Path(__file__).parent.parent / "assets" / "icon.png")