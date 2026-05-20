"""Mixing styles - detect and calculate fade parameters."""
import random


def detect_style(phase: tuple, e_current: int, e_next: int, 
                bpm_current: int, bpm_next: int) -> str:
    """Detect mixing style based on context.
    
    Returns:
        "guetta": aggressive bass swaps, hard drops
        "avicii": melodic, symmetric fades, reverb-heavy
        "progressive": technical, long blends, similar BPM
        "fusion": hybrid blend, balanced overlap
    """
    bpm = bpm_current or bpm_next or 120
    diff = abs(e_next - e_current)
    bpm_diff = abs((bpm_current or 0) - (bpm_next or 0))
    
    # Fusion: very similar BPM + compatible energies
    if bpm_diff <= 6 and diff <= 15 and bpm >= 110:
        if random.random() < 0.35:
            return "fusion"
    
    # Progressive: nearly identical BPM
    if bpm_diff <= 3 and diff <= 12 and bpm >= 115:
        return "progressive"
    
    # Breakdown: always emotional
    if phase[0] == "breakdown":
        return "avicii"
    
    # Low energy/BPM: smooth transition
    if bpm < 110 and e_current < 65:
        return "avicii"
    
    # Large energy jump: smooth ramp
    if diff > 22:
        return "avicii"
    
    # Medium energy with medium BPM
    if e_current < 60 and bpm < 125:
        return "avicii"
    
    # Peak + high energy: aggressive
    if phase[0] in ("first-peak", "second-peak") and e_current >= 75 and bpm >= 120:
        return "guetta"
    
    # High BPM + sustained energy: aggressive
    if bpm >= 125 and e_current >= 75:
        return "guetta"
    
    return "guetta"


def fade_duration(phase: tuple, e_current: int, e_next: int, 
                 style: str = "guetta") -> float:
    """Calculate crossfade duration based on style.
    
    Args:
        phase: Current session phase
        e_current: Energy of current track
        e_next: Energy of next track
        style: Mixing style (guetta/avicii/progressive/fusion)
        
    Returns:
        Fade duration in seconds
    """
    _, _, _, base = phase
    diff = e_next - e_current
    
    if style == "fusion":
        # Long coexistence
        return 38.0 if abs(diff) <= 10 else 32.0
    
    if style == "progressive":
        # Technical, gradual
        if abs(diff) <= 8:
            return 20.0
        if diff > 8:
            return 18.0
        return 16.0
    
    if style == "avicii":
        if phase[0] == "breakdown":
            return 22.0
        if diff < -15:
            return 18.0
        if diff > 15:
            return 16.0
        if abs(diff) <= 8:
            return 14.0
        return 15.0
    
    # guetta
    if phase[0] == "breakdown":
        return 18.0
    if phase[0] in ("first-peak", "second-peak") and diff > 10:
        return 9.0
    if diff < -15:
        return 14.0
    if diff > 15:
        return 11.0
    if abs(diff) <= 8:
        return float(base) - 1
    
    return float(base)
