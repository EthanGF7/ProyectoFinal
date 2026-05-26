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


def get_phase(played_count: int, total: int, session_seconds: float = 0.0) -> tuple:
    """Determine current session phase.

    For small libraries (<12 tracks) the ratio-based arc compresses phases to
    ~1 song each, which feels rushed. When the library is small we blend the
    track-ratio with an estimated session-time ratio (assuming ~4 min/track)
    so each phase lasts at least a few songs.

    Args:
        played_count: Number of tracks played so far
        total: Total tracks in library
        session_seconds: Elapsed session time in seconds (optional)

    Returns:
        Phase tuple: (name, ratio, target_energy, fade_base)
    """
    if total < 2:
        return PHASES[0]

    track_ratio = min(1.0, played_count / max(total, 1))

    if total < 12:
        # Estimate a longer session by projecting to a virtual 12-track library
        virtual_total = max(total * 1.5, 12)
        time_ratio = min(1.0, played_count / virtual_total)
        # Weight: 40% real tracks, 60% stretched projection
        ratio = 0.4 * track_ratio + 0.6 * time_ratio
    else:
        ratio = track_ratio

    for phase in PHASES:
        if ratio <= phase[1]:
            return phase

    return PHASES[-1]
