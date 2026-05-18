"""User preferences - like/dislike management."""
import json
from pathlib import Path


def load_prefs(prefs_file: Path) -> dict:
    """Load user preferences: {file: 1 (like) | -1 (dislike)}.
    
    Args:
        prefs_file: Path to preferencias.json
        
    Returns:
        Dict mapping filenames to preference values
    """
    if prefs_file.exists():
        try:
            return json.loads(prefs_file.read_text(encoding="utf-8"))
        except:
            pass
    return {}


def save_prefs(prefs_file: Path, prefs: dict) -> None:
    """Save user preferences to disk.
    
    Args:
        prefs_file: Path to preferencias.json
        prefs: Dict to save
    """
    prefs_file.parent.mkdir(parents=True, exist_ok=True)
    prefs_file.write_text(
        json.dumps(prefs, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
