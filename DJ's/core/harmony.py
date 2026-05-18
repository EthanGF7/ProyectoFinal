"""Harmonic mixing - Camelot wheel and key compatibility."""

# Camelot wheel: maps musical keys to positions
CAMELOT = {
    "Ab": "1A", "Eb": "2A", "Bb": "3A", "F": "4A", "C": "5A", "G": "6A",
    "D": "7A", "A": "8A", "E": "9A", "B": "10A", "F#": "11A", "Db": "12A",
    "Abm": "1B", "Ebm": "2B", "Bbm": "3B", "Fm": "4B", "Cm": "5B", "Gm": "6B",
    "Dm": "7B", "Am": "8B", "Em": "9B", "Bm": "10B", "F#m": "11B", "C#m": "12B",
    # Aliases
    "G#": "1A", "D#": "2A", "A#": "3A", "C#": "12A", "Gb": "11A",
    "G#m": "1B", "D#m": "2B", "A#m": "3B", "C#m": "12B", "Gbm": "11B",
}


def camelot_key(key_str: str) -> str | None:
    """Map key string to Camelot position."""
    if not key_str:
        return None
    return CAMELOT.get(key_str.strip())


def key_compatibility_bonus(k1: str, k2: str) -> int:
    """Score harmonic compatibility 0-15 using Camelot wheel.
    
    Args:
        k1: First key (current track)
        k2: Second key (next track)
        
    Returns:
        Bonus points: 15=perfect, 12=adjacent, 10=relative, 5=compatible, 0=poor
    """
    c1, c2 = camelot_key(k1), camelot_key(k2)
    
    if not c1 or not c2:
        return 5  # No info: neutral
    if c1 == c2:
        return 15  # Same key: perfect
    
    n1, l1 = int(c1[:-1]), c1[-1]
    n2, l2 = int(c2[:-1]), c2[-1]
    
    # Adjacent on wheel (±1 position)
    if l1 == l2 and abs(n1 - n2) in (1, 11):
        return 12
    
    # Relative major/minor (same position, different mode)
    if n1 == n2 and l1 != l2:
        return 10
    
    # Two steps: works but less ideal
    if l1 == l2 and abs(n1 - n2) in (2, 10):
        return 5
    
    return 0
