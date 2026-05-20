"""Session arc - manage energy curve across DJ set."""

# Session phases: (name, ratio_cutoff, target_energy, fade_base)
PHASES = [
    ("warm-up", 0.12, 50, 8),
    ("first-build", 0.30, 68, 10),
    ("first-peak", 0.48, 88, 8),
    ("breakdown", 0.58, 55, 16),
    ("second-build", 0.72, 75, 10),
    ("second-peak", 0.88, 92, 8),
    ("outro", 1.00, 45, 12),
]


def get_phase(played_count: int, total: int) -> tuple:
    """Determine current session phase.
    
    Args:
        played_count: Number of tracks played so far
        total: Total tracks in library
        
    Returns:
        Phase tuple: (name, ratio, target_energy, fade_base)
    """
    if total < 2:
        return PHASES[0]
    
    ratio = min(1.0, played_count / max(total, 1))
    for phase in PHASES:
        if ratio <= phase[1]:
            return phase
    
    return PHASES[-1]
