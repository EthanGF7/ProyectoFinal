"""Track scoring and selection - AI DJ decision logic."""
import random
from .harmony import key_compatibility_bonus


def score_track(candidate: dict, current: dict, phase: tuple, 
               played_set: set, played_list: list = None, prefs: dict = None) -> float:
    """Score a candidate track for next selection.
    
    Args:
        candidate: Track to evaluate
        current: Currently playing track
        phase: Current session phase
        played_set: Set of filenames already played
        played_list: Recent tracks for anti-repetition
        prefs: User preferences {file: 1/-1}
        
    Returns:
        Score 0-100+ (higher=better)
    """
    if not prefs:
        prefs = {}
    if not played_list:
        played_list = []
    
    if candidate["file"] in played_set:
        return -1
    
    _, _, target_e, _ = phase
    cur_bpm = current.get("bpm", 0) or 0
    cnd_bpm = candidate.get("bpm", 0) or 0
    cur_e = current.get("energia", 50) or 50
    cnd_e = candidate.get("energia", 50) or 50
    
    score = 0.0
    
    # 1. BPM matching (0-35 pts)
    if cur_bpm and cnd_bpm:
        diff = abs(cur_bpm - cnd_bpm)
        if diff <= 3:
            score += 35  # Progressive mix possible
        elif diff <= 14:
            score += max(0.0, 35 - diff * 2.5)
        else:
            score += max(0.0, 5 - (diff - 14) * 0.5)
    else:
        score += 10
    
    # 2. Energy target of phase (0-30 pts)
    e_dist = abs(cnd_e - target_e)
    score += max(0.0, 30 - e_dist * 1.1)
    
    # 3. Transition coherence (0-15 pts)
    jump = abs(cnd_e - cur_e)
    if jump > 35:
        score -= 5
    else:
        score += max(0.0, 15 - jump * 0.43)
    
    # 4. Harmonic compatibility (0-15 pts)
    score += key_compatibility_bonus(
        current.get("key", ""), candidate.get("key", "")
    )
    
    # 5. Anti-key-repetition
    if len(played_list) >= 2:
        cnd_key = candidate.get("key", "")
        recent_keys = [t.get("key", "") for t in played_list[-2:] if isinstance(t, dict)]
        if cnd_key and recent_keys.count(cnd_key) >= 2:
            score -= 8
    
    # 6. JSON quality bonus
    if candidate.get("beat_times"):
        score += 6
    if candidate.get("puede_salir"):
        score += 3
    if candidate.get("puede_empezar_mezcla"):
        score += 3
    
    # 7. Human factor randomness
    score += random.gauss(0, 4)
    
    # 8. User preferences
    pref = prefs.get(candidate["file"], 0)
    if pref == 1:
        score += 18
    elif pref == -1:
        score -= 50
    
    return max(0.0, score)


def pick_next(library: list, current: dict, played_set: set, 
             played_count: int, played_list: list = None, 
             phase: tuple = None, prefs: dict = None) -> tuple:
    """Select next track using weighted selection from top candidates.
    
    Args:
        library: All available tracks
        current: Currently playing track
        played_set: Set of played filenames
        played_count: Number of tracks played
        played_list: Recent tracks
        phase: Session phase
        prefs: User preferences
        
    Returns:
        (selected_track, best_score, phase) or (None, 0, phase) if exhausted
    """
    if not phase:
        from .arc import get_phase
        phase = get_phase(played_count, len(library))
    if not prefs:
        prefs = {}
    if not played_list:
        played_list = []
    
    # Score all candidates
    scored = [
        (t, score_track(t, current, phase, played_set, played_list, prefs))
        for t in library
    ]
    candidates = [(t, s) for t, s in scored if s >= 0]
    
    # If all played, reset
    if not candidates:
        new_ps = {current["file"]}
        candidates = [
            (t, score_track(t, current, phase, new_ps, played_list, prefs))
            for t in library if t["file"] != current["file"]
        ]
        candidates = [(t, s) for t, s in candidates if s >= 0]
    
    if not candidates:
        return None, 0, phase
    
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    # Weighted selection from top-3 (human, not always #1)
    top = candidates[:min(3, len(candidates))]
    total_w = sum(s for _, s in top) or 1
    r, acc = random.random() * total_w, 0
    chosen = top[0][0]
    
    for t, s in top:
        acc += s
        if r <= acc:
            chosen = t
            break
    
    return chosen, candidates[0][1], phase
