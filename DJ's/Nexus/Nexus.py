#!/usr/bin/env python3
"""
DJ AI - Live Player  |  python player.py  |  Dale Play. La IA hace todo.
"""
import argparse
import os
import sys, json, time, threading, webbrowser, random, math
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import urllib.parse
from pathlib import Path as _Path

BASE_DIR  = Path(__file__).parent
SRC_DIR   = BASE_DIR / "src"
SONGS_DIR = BASE_DIR / "musica" / "canciones"
JSON_DIR  = BASE_DIR / "musica" / "json"
PORT      = 8765

sys.path.insert(0, str(SRC_DIR))

MODULES_OK    = False
compatibility = None
timing_engine = None
try:
    from compatibility_engine import CompatibilityEngine
    from timing_engine         import TimingDecisionEngine
    compatibility  = CompatibilityEngine()
    timing_engine  = TimingDecisionEngine()
    MODULES_OK     = True
    print("Ô£à  CompatibilityEngine + TimingDecisionEngine cargados")
except ImportError as e:
    print(f"ÔÜá´©Å  src/ no encontrado ({e}) ÔÇö fallback inteligente activo")


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  BIBLIOTECA
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
def load_library():
    tracks, exts = [], {".mp3",".wav",".ogg",".flac",".aac",".m4a"}
    if not SONGS_DIR.exists(): return tracks
    for f in sorted(SONGS_DIR.iterdir()):
        if f.suffix.lower() not in exts: continue
        meta = {}
        jp = JSON_DIR / f"{f.stem}.json"
        if jp.exists():
            try:
                raw  = json.loads(jp.read_text(encoding="utf-8"))
                meta = {k:v for k,v in raw.items() if not k.startswith("_") and v is not None}
            except: pass
        tracks.append({
            "name":                 f.stem,
            "file":                 f.name,
            "bpm":                  meta.get("bpm", 0),
            "energia":              meta.get("energia", 50),
            "key":                  meta.get("key", ""),
            "estilo":               meta.get("estilo", ""),
            "duracion_segundos":    meta.get("duracion_segundos", 0),
            "puede_salir":          meta.get("puede_salir"),
            "puede_empezar_mezcla": meta.get("puede_empezar_mezcla"),
            "debe_sonar_sola":      meta.get("debe_sonar_sola"),
            "intro_fin":            meta.get("intro_fin"),
            "tiene_voz_inicio":     meta.get("tiene_voz_inicio", False),
            "beat_times":           meta.get("beat_times", []),
            "energia_por_segundo":  meta.get("energia_por_segundo", []),
            "start_position":       (lambda pem, intro: float(pem) if pem and float(pem) > 0 else (float(intro) if intro and float(intro) > 0 else 0.0))(meta.get("puede_empezar_mezcla"), meta.get("intro_fin")),
        })
    return tracks


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  RUEDA DE CAMELOT ÔÇö mezcla arm├│nica
#  Un DJ profesional mezcla en tonalidades compatibles.
#  La rueda de Camelot mapea cada key a una posici├│n;
#  las posiciones adyacentes son compatibles.
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
CAMELOT = {
    "Ab":"1A","Eb":"2A","Bb":"3A","F":"4A","C":"5A","G":"6A","D":"7A","A":"8A","E":"9A","B":"10A","F#":"11A","Db":"12A",
    "Abm":"1B","Ebm":"2B","Bbm":"3B","Fm":"4B","Cm":"5B","Gm":"6B","Dm":"7B","Am":"8B","Em":"9B","Bm":"10B","F#m":"11B","C#m":"12B",
    # Nombres alternativos
    "G#":"1A","D#":"2A","A#":"3A","C#":"12A","Gb":"11A",
    "G#m":"1B","D#m":"2B","A#m":"3B","C#m":"12B","Gbm":"11B",
}

def camelot_key(key_str):
    if not key_str: return None
    return CAMELOT.get(key_str.strip(), None)

def key_compatibility_bonus(k1, k2):
    """Devuelve bonus 0-15 seg├║n compatibilidad arm├│nica."""
    c1, c2 = camelot_key(k1), camelot_key(k2)
    if not c1 or not c2: return 5  # sin info: neutro
    if c1 == c2: return 15         # misma tonalidad: perfecto
    n1, l1 = int(c1[:-1]), c1[-1]
    n2, l2 = int(c2[:-1]), c2[-1]
    # Adyacente en el c├¡rculo (┬▒1)
    if l1 == l2 and abs(n1-n2) in (1, 11): return 12
    # Relativo mayor/menor (misma posici├│n, letra distinta)
    if n1 == n2 and l1 != l2: return 10
    # 2 pasos: funciona pero menos ideal
    if l1 == l2 and abs(n1-n2) in (2, 10): return 5
    return 0


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  ARCO DE SESI├ôN
#  Un DJ no pone canciones al azar ÔÇö gestiona la energ├¡a de la
#  sala como si fuera una historia con acto 1, cl├¡max y resoluci├│n.
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
# Fases:  nombre, hasta_ratio, energ├¡a_objetivo, fade_base
PHASES = [
    ("warm-up",      0.12, 50,  8),
    ("first-build",  0.30, 68, 10),
    ("first-peak",   0.48, 88,  8),
    ("breakdown",    0.58, 55, 16),
    ("second-build", 0.72, 75, 10),
    ("second-peak",  0.88, 92,  8),
    ("outro",        1.00, 45, 12),
]

def get_phase(played_count, total):
    if total < 2: return PHASES[0]
    ratio = min(1.0, played_count / max(total, 1))
    for phase in PHASES:
        if ratio <= phase[1]: return phase
    return PHASES[-1]


def detect_style(phase, e_current, e_next, bpm_current, bpm_next):
    """
    Detecta qu├® estilo de mezcla usar seg├║n el contexto musical.

    Guetta:      drops duros, bass swap agresivo, sigmoid tard├¡a
                 ÔåÆ BPM alto + energ├¡a alta + fases de peak

    Avicii:      transiciones mel├│dicas, fade sim├®trico largo,
                 graves graduales, reverb pronunciado
                 ÔåÆ BPM medio-bajo, energ├¡a media, breakdown, salto grande de energ├¡a

    Progressive: equal-power puro, EQ neutro, sin trucos ÔÇö mezcla
                 t├®cnica limpia para canciones con BPM muy similar
                 ÔåÆ diff BPM < 3 + energ├¡as similares
    """
    bpm  = bpm_current or bpm_next or 120
    diff = abs(e_next - e_current)
    bpm_diff = abs((bpm_current or 0) - (bpm_next or 0))

    # Fusion: BPM muy parecido + tonalidad compatible + energ├¡as similares
    # Las dos canciones suenan juntas durante mucho tiempo como una sola
    # Se activa con probabilidad ~35% cuando las condiciones son buenas
    bpm  = bpm_current or bpm_next or 120
    if bpm_diff <= 6 and diff <= 15 and bpm >= 110:
        if random.random() < 0.35:
            return "fusion"

    # Progressive: BPM casi id├®ntico + energ├¡a parecida ÔåÆ mezcla t├®cnica perfecta
    if bpm_diff <= 3 and diff <= 12 and bpm >= 115:
        return "progressive"

    # Breakdown ÔåÆ siempre Avicii (momento emocional, no percutivo)
    if phase[0] == "breakdown":
        return "avicii"

    # BPM bajo + energ├¡a baja ÔåÆ Avicii
    if bpm < 110 and e_current < 65:
        return "avicii"

    # Salto grande de energ├¡a ÔåÆ Avicii (transici├│n suave)
    if diff > 22:
        return "avicii"

    # Energ├¡a media con BPM medio ÔåÆ Avicii
    if e_current < 60 and bpm < 125:
        return "avicii"

    # Peak + energ├¡a alta + BPM alto ÔåÆ Guetta
    if phase[0] in ("first-peak", "second-peak") and e_current >= 75 and bpm >= 120:
        return "guetta"

    # BPM alto y energ├¡a alta sostenida ÔåÆ Guetta
    if bpm >= 125 and e_current >= 75:
        return "guetta"

    # Default: Guetta
    return "guetta"


def fade_duration(phase, e_current, e_next, style="guetta"):
    """
    Duraci├│n del crossfade seg├║n estilo y contexto.
    Progressive: el m├ís largo (los dos sonar├ín perfectamente juntos)
    Avicii: largos y sim├®tricos
    Guetta: cortos y agresivos
    """
    _, _, _, base = phase
    diff = e_next - e_current

    if style == "fusion":
        # Las dos canciones conviven mucho tiempo ÔÇö blend largo y equilibrado
        return 38.0 if abs(diff) <= 10 else 32.0

    if style == "progressive":
        # Mezcla t├®cnica: larga y gradual ÔÇö los BPMs son casi iguales
        # as├¡ que pueden convivir mucho tiempo sin problema
        if abs(diff) <= 8:  return 20.0  # energ├¡as similares: fade largo y suave
        if diff > 8:        return 18.0  # subida: un poco m├ís corto
        return 16.0                      # bajada

    if style == "avicii":
        if phase[0] == "breakdown":   return 22.0  # cinematogr├ífico largo
        if diff < -15:                return 18.0  # bajada muy suave
        if diff > 15:                 return 16.0  # subida progresiva
        if abs(diff) <= 8:            return 14.0  # energ├¡as similares
        return 15.0
    else:  # guetta
        if phase[0] == "breakdown":   return 18.0
        if phase[0] in ("first-peak","second-peak") and diff > 10: return 9.0
        if diff < -15:                return 14.0
        if diff > 15:                 return 11.0
        if abs(diff) <= 8:            return float(base) - 1
        return float(base)


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  SCORING ÔÇö c├│mo elige el DJ la siguiente canci├│n
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
def score_track(candidate, current, phase, played_set, played_list=None):
    if candidate["file"] in played_set: return -1

    _, _, target_e, _ = phase
    cur_bpm = current.get("bpm", 0) or 0
    cnd_bpm = candidate.get("bpm", 0) or 0
    cur_e   = current.get("energia", 50) or 50
    cnd_e   = candidate.get("energia", 50) or 50

    score = 0.0

    # 1. BPM ÔÇö lo m├ís importante para una mezcla limpia (0-35 pts)
    if cur_bpm and cnd_bpm:
        diff = abs(cur_bpm - cnd_bpm)
        if diff <= 3:
            # BPM casi id├®ntico: progressive mix posible ÔåÆ bonus extra
            score += 35
        elif diff <= 14:
            score += max(0.0, 35 - diff * 2.5)
        else:
            # BPM muy diferente: penalizar pero no descartar
            score += max(0.0, 5 - (diff - 14) * 0.5)
    else:
        score += 10  # sin BPM: neutro

    # 2. Energ├¡a objetivo de la fase (0-30 pts)
    e_dist = abs(cnd_e - target_e)
    score += max(0.0, 30 - e_dist * 1.1)

    # 3. Coherencia de transici├│n ÔÇö no saltar de 90 a 30 de golpe (0-15 pts)
    jump = abs(cnd_e - cur_e)
    if jump > 35: score -= 5   # penalizar saltos brutales
    else: score += max(0.0, 15 - jump * 0.43)

    # 4. Compatibilidad arm├│nica ÔÇö rueda de Camelot (0-15 pts)
    score += key_compatibility_bonus(
        current.get("key",""), candidate.get("key","")
    )

    # 5. Anti-repetici├│n de tonalidad: si las ├║ltimas 2 canciones tuvieron
    #    la misma key que la candidata, penalizar (evita que suene todo en Am)
    if played_list and len(played_list) >= 2:
        cnd_key = candidate.get("key", "")
        recent_keys = [t.get("key","") for t in played_list[-2:] if isinstance(t, dict)]
        if cnd_key and recent_keys.count(cnd_key) >= 2:
            score -= 8

    # 6. Bonus por calidad del JSON (mejor mezcla si hay beat_times)
    if candidate.get("beat_times"):           score += 6
    if candidate.get("puede_salir"):          score += 3
    if candidate.get("puede_empezar_mezcla"): score += 3

    # 7. Factor humano ÔÇö un DJ no es un algoritmo puro
    score += random.gauss(0, 4)

    # 8. Preferencias del usuario (like/dislike)
    pref = PREFS.get(candidate["file"], 0)
    if pref == 1:   score += 18   # like: grande boost
    elif pref == -1: score -= 50  # dislike: pr├ícticamente descartada

    return max(0.0, score)


def pick_next(library, current, played_set, played_count, played_list=None):
    total = len(library)
    phase = get_phase(played_count, total)

    scored = [(t, score_track(t, current, phase, played_set, played_list))
              for t in library]
    candidates = [(t, s) for t, s in scored if s >= 0]

    if not candidates:
        # Todas sonaron ÔÇö reiniciar historial (sesi├│n continua)
        new_ps = {current["file"]}
        candidates = [(t, score_track(t, current, phase, new_ps, played_list))
                      for t in library if t["file"] != current["file"]]
        candidates = [(t,s) for t,s in candidates if s >= 0]

    if not candidates:
        return None, 0, phase

    candidates.sort(key=lambda x: x[1], reverse=True)

    # Selecci├│n ponderada top-3: humano, no siempre el #1
    top     = candidates[:min(3, len(candidates))]
    total_w = sum(s for _, s in top) or 1
    r, acc  = random.random() * total_w, 0
    chosen  = top[0][0]
    for t, s in top:
        acc += s
        if r <= acc: chosen = t; break

    return chosen, candidates[0][1], phase


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  PLAN DE MEZCLA
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
def build_plan(current, nxt, current_time, phase):
    dur  = float(current.get("duracion_segundos") or 0)
    ps   = current.get("puede_salir")
    e1   = current.get("energia", 50) or 50
    e2   = nxt.get("energia", 50) or 50
    bpm1 = current.get("bpm", 0) or 0
    bpm2 = nxt.get("bpm", 0) or 0

    style = detect_style(phase, e1, e2, bpm1, bpm2)
    cf    = fade_duration(phase, e1, e2, style)

    # Punto de salida ideal: puede_salir del JSON, o ├║ltimos 3s de la canci├│n
    exit_at = float(ps) if ps else (dur - 2.0 if dur else current_time + 90)

    # Comenzar el fade exactamente cf segundos antes de la salida
    start_mix = exit_at - cf

    # Nunca antes del 73% de la canci├│n  
    min_start = dur * 0.73 if dur else current_time + 10
    start_mix = max(start_mix, min_start, current_time + 8)

    # ÔöÇÔöÇ Punto de entrada de la pista ENTRANTE ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    # Prioridad:
    #   1. puede_empezar_mezcla manual (el usuario lo sabe mejor que nadie)
    #   2. intro_fin auto-detectado (saltar la intro instrumental larga)
    #   3. Si tiene_voz_inicio=True, tambi├®n usar intro_fin para no entrar
    #      con voz cantando encima de la pista saliente
    #   4. Fallback: 0 (desde el principio)
    pem       = nxt.get("puede_empezar_mezcla")
    intro_fin = nxt.get("intro_fin")
    tiene_voz = nxt.get("tiene_voz_inicio", False)

    if pem is not None:
        # Manual tiene prioridad absoluta
        enter_at = float(pem)
    elif intro_fin is not None and intro_fin >= 3.0:
        # Hay intro detectada ÔÇö entrar al acabar la intro
        # Ajustar al beat m├ís pr├│ximo (4 beats antes del fin de intro)
        # para que el drop de la entrante caiga alineado
        bpm2 = nxt.get("bpm", 0) or 0
        if bpm2 > 0:
            beat_dur = 60.0 / bpm2
            # Entrar 4 beats antes del fin de intro para que el drop
            # caiga dentro del crossfade, no despu├®s
            enter_at = max(0.0, intro_fin - beat_dur * 4)
        else:
            enter_at = max(0.0, intro_fin - 4.0)
    elif tiene_voz:
        # Tiene voz desde el principio pero no intro larga detectada.
        # Entrar en el segundo 4 como m├¡nimo para evitar la voz del inicio.
        enter_at = 4.0
    else:
        enter_at = 0.0

    plan = {
        "start_current_time": round(start_mix, 2),
        "start_next_time":    round(enter_at, 2),
        "mix_duration":       cf,
        "exit_at":            round(exit_at, 2),
        "phase":              phase[0],
        "has_entry_point":    pem is not None,
        "style":              style,
    }

    # TimingDecisionEngine ÔÇö respetar si no corta demasiado pronto
    if MODULES_OK and timing_engine:
        try:
            tp = timing_engine.find_mix_point(current, nxt, current_time)
            if tp and isinstance(tp, dict):
                sct = tp.get("start_current_time")
                if sct and float(sct) >= min_start:
                    tp.setdefault("exit_at",      plan["exit_at"])
                    tp.setdefault("mix_duration",  cf)
                    tp.setdefault("phase",         phase[0])
                    return tp
                tp["start_current_time"] = plan["start_current_time"]
                tp.setdefault("exit_at",     plan["exit_at"])
                tp.setdefault("mix_duration", cf)
                tp.setdefault("phase",        phase[0])
                return tp
        except: pass

    return plan


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  PREFERENCIAS DE USUARIO (like/dislike)
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
PREFS_FILE = BASE_DIR / "musica" / "preferencias.json"

def load_prefs() -> dict:
    """Carga preferencias: {file: 1 (like) | -1 (dislike)}"""
    if PREFS_FILE.exists():
        try:
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except: pass
    return {}

def save_prefs(prefs: dict):
    PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PREFS_FILE.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")

PREFS = load_prefs()


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  SERVER
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
LIBRARY = load_library()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        p  = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(p.query)

        if p.path in ("/", "/index.html"):
            self.ok(_load_html(), "text/html")

        elif p.path == "/api/library":
            self.ok(json.dumps(LIBRARY).encode(), "application/json")

        elif p.path == "/api/modules":
            self.ok(json.dumps({"ok": MODULES_OK}).encode(), "application/json")

        elif p.path == "/api/next":
            cur_file     = qs.get("current", [None])[0]
            cur_time     = float(qs.get("time", [0])[0])
            played_count = int(qs.get("count", [0])[0])
            try:
                played_set = set(json.loads(urllib.parse.unquote(qs.get("played",["[]"])[0])))
            except: played_set = set()

            current = next((t for t in LIBRARY if t["file"] == cur_file), None)
            if not current: self.ok(b'{"error":"not found"}', "application/json"); return

            try:
                played_list_raw = json.loads(urllib.parse.unquote(qs.get("played_list",["[]"])[0]))
                # played_list is a list of track objects [{file, key, ...}]
                played_list = [t for t in LIBRARY if t["file"] in {x.get("file","") for x in played_list_raw}]
            except:
                played_list = []

            nxt, score, phase = pick_next(LIBRARY, current, played_set, played_count, played_list)
            if not nxt:      self.ok(b'{"error":"no tracks"}', "application/json"); return

            plan = build_plan(current, nxt, cur_time, phase)
            _, _, target_e, _ = phase

            self.ok(json.dumps({
                "track": nxt, "plan": plan,
                "score": round(score, 1),
                "phase": phase[0],
                "target_energy": round(target_e, 1),
            }, default=str).encode(), "application/json")

        elif p.path == "/api/prefs":
            # Devuelve todas las preferencias actuales
            self.ok(json.dumps(PREFS).encode(), "application/json")

        elif p.path.startswith("/audio/"):
            fname = urllib.parse.unquote(p.path[7:])
            fp    = SONGS_DIR / fname
            if not fp.exists(): self.send_error(404); return
            mime = {".mp3":"audio/mpeg",".wav":"audio/wav",".ogg":"audio/ogg",
                    ".flac":"audio/flac",".aac":"audio/aac",".m4a":"audio/mp4"
                   }.get(fp.suffix.lower(), "audio/mpeg")
            data = fp.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except:
            data = {}

        if p.path == "/api/like":
            file   = data.get("file", "")
            action = data.get("action", "")  # "like", "dislike", "clear"
            if file and action in ("like", "dislike", "clear"):
                if action == "like":
                    PREFS[file] = 1
                elif action == "dislike":
                    PREFS[file] = -1
                else:
                    PREFS.pop(file, None)
                save_prefs(PREFS)
                self.ok(json.dumps({"ok": True, "file": file, "action": action}).encode(), "application/json")
            else:
                self.ok(b'{"error":"invalid"}', "application/json")
        else:
            self.send_error(404)

    def ok(self, data, ct):
        self.send_response(200)
        self.send_header("Content-Type", f"{ct}; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  FRONTEND
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#!/usr/bin/env python3
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  NUEVO BLOQUE HTML  ÔÇö  NEXUS ┬À Club Underground Futurista
#  Reemplaza completamente la variable HTML = r""" ... """
#  La l├│gica Python / audio engine no ha sido modificada.
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ

_HTML_PATH = _Path(__file__).parent / "index.html"

def _load_html() -> bytes:
    """Load index.html as UTF-8 bytes (cached on first call)."""
    global _HTML_CACHE
    if _HTML_CACHE is None:
        _HTML_CACHE = _HTML_PATH.read_bytes()
    return _HTML_CACHE

_HTML_CACHE: "bytes | None" = None
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
#  MAIN
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
def main():
    SONGS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    if not LIBRARY:
        print(f"\nÔÜá´©Å  Sin canciones en {SONGS_DIR}")
        print(f"   Pon tus MP3/WAV ah├¡ y ejecuta de nuevo.\n")
    else:
        print(f"\nÔ£à  {len(LIBRARY)} canciones")
        no_json = [t for t in LIBRARY if not t["bpm"]]
        if no_json:
            print(f"ÔÜá´©Å  {len(no_json)} sin JSON ÔÇö la mezcla usar├í BPM fallback:")
            for t in no_json: print(f"   ÔÇó {t['name']}")
        else:
            print(f"Ô£à  Todas las canciones tienen JSON completo")

    url = f"http://localhost:{PORT}"
    print(f"\n­ƒÄº  {url}  ÔÇö  abre el navegador, dale Play\n")

    threading.Thread(target=lambda:(time.sleep(1), webbrowser.open(url)), daemon=True).start()
    server = HTTPServer(("", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n­ƒæï")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus AI DJ Player")
    parser.add_argument("--port", type=int, default=None,
                        help="Port (default: auto-fallback from 8765)")
    args = parser.parse_args()

    PORT = args.port or int(os.environ.get("DJ_PORT", PORT))
    main()
