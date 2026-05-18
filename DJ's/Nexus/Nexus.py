#!/usr/bin/env python3
"""
DJ AI - Live Player  |  python player.py  |  Dale Play. La IA hace todo.
"""
import sys, json, time, threading, webbrowser, random, math
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import urllib.parse

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
    print("✅  CompatibilityEngine + TimingDecisionEngine cargados")
except ImportError as e:
    print(f"⚠️  src/ no encontrado ({e}) — fallback inteligente activo")


# ══════════════════════════════════════════════════════════════
#  BIBLIOTECA
# ══════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════
#  RUEDA DE CAMELOT — mezcla armónica
#  Un DJ profesional mezcla en tonalidades compatibles.
#  La rueda de Camelot mapea cada key a una posición;
#  las posiciones adyacentes son compatibles.
# ══════════════════════════════════════════════════════════════
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
    """Devuelve bonus 0-15 según compatibilidad armónica."""
    c1, c2 = camelot_key(k1), camelot_key(k2)
    if not c1 or not c2: return 5  # sin info: neutro
    if c1 == c2: return 15         # misma tonalidad: perfecto
    n1, l1 = int(c1[:-1]), c1[-1]
    n2, l2 = int(c2[:-1]), c2[-1]
    # Adyacente en el círculo (±1)
    if l1 == l2 and abs(n1-n2) in (1, 11): return 12
    # Relativo mayor/menor (misma posición, letra distinta)
    if n1 == n2 and l1 != l2: return 10
    # 2 pasos: funciona pero menos ideal
    if l1 == l2 and abs(n1-n2) in (2, 10): return 5
    return 0


# ══════════════════════════════════════════════════════════════
#  ARCO DE SESIÓN
#  Un DJ no pone canciones al azar — gestiona la energía de la
#  sala como si fuera una historia con acto 1, clímax y resolución.
# ══════════════════════════════════════════════════════════════
# Fases:  nombre, hasta_ratio, energía_objetivo, fade_base
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
    Detecta qué estilo de mezcla usar según el contexto musical.

    Guetta:      drops duros, bass swap agresivo, sigmoid tardía
                 → BPM alto + energía alta + fases de peak

    Avicii:      transiciones melódicas, fade simétrico largo,
                 graves graduales, reverb pronunciado
                 → BPM medio-bajo, energía media, breakdown, salto grande de energía

    Progressive: equal-power puro, EQ neutro, sin trucos — mezcla
                 técnica limpia para canciones con BPM muy similar
                 → diff BPM < 3 + energías similares
    """
    bpm  = bpm_current or bpm_next or 120
    diff = abs(e_next - e_current)
    bpm_diff = abs((bpm_current or 0) - (bpm_next or 0))

    # Fusion: BPM muy parecido + tonalidad compatible + energías similares
    # Las dos canciones suenan juntas durante mucho tiempo como una sola
    # Se activa con probabilidad ~35% cuando las condiciones son buenas
    bpm  = bpm_current or bpm_next or 120
    if bpm_diff <= 6 and diff <= 15 and bpm >= 110:
        if random.random() < 0.35:
            return "fusion"

    # Progressive: BPM casi idéntico + energía parecida → mezcla técnica perfecta
    if bpm_diff <= 3 and diff <= 12 and bpm >= 115:
        return "progressive"

    # Breakdown → siempre Avicii (momento emocional, no percutivo)
    if phase[0] == "breakdown":
        return "avicii"

    # BPM bajo + energía baja → Avicii
    if bpm < 110 and e_current < 65:
        return "avicii"

    # Salto grande de energía → Avicii (transición suave)
    if diff > 22:
        return "avicii"

    # Energía media con BPM medio → Avicii
    if e_current < 60 and bpm < 125:
        return "avicii"

    # Peak + energía alta + BPM alto → Guetta
    if phase[0] in ("first-peak", "second-peak") and e_current >= 75 and bpm >= 120:
        return "guetta"

    # BPM alto y energía alta sostenida → Guetta
    if bpm >= 125 and e_current >= 75:
        return "guetta"

    # Default: Guetta
    return "guetta"


def fade_duration(phase, e_current, e_next, style="guetta"):
    """
    Duración del crossfade según estilo y contexto.
    Progressive: el más largo (los dos sonarán perfectamente juntos)
    Avicii: largos y simétricos
    Guetta: cortos y agresivos
    """
    _, _, _, base = phase
    diff = e_next - e_current

    if style == "fusion":
        # Las dos canciones conviven mucho tiempo — blend largo y equilibrado
        return 38.0 if abs(diff) <= 10 else 32.0

    if style == "progressive":
        # Mezcla técnica: larga y gradual — los BPMs son casi iguales
        # así que pueden convivir mucho tiempo sin problema
        if abs(diff) <= 8:  return 20.0  # energías similares: fade largo y suave
        if diff > 8:        return 18.0  # subida: un poco más corto
        return 16.0                      # bajada

    if style == "avicii":
        if phase[0] == "breakdown":   return 22.0  # cinematográfico largo
        if diff < -15:                return 18.0  # bajada muy suave
        if diff > 15:                 return 16.0  # subida progresiva
        if abs(diff) <= 8:            return 14.0  # energías similares
        return 15.0
    else:  # guetta
        if phase[0] == "breakdown":   return 18.0
        if phase[0] in ("first-peak","second-peak") and diff > 10: return 9.0
        if diff < -15:                return 14.0
        if diff > 15:                 return 11.0
        if abs(diff) <= 8:            return float(base) - 1
        return float(base)


# ══════════════════════════════════════════════════════════════
#  SCORING — cómo elige el DJ la siguiente canción
# ══════════════════════════════════════════════════════════════
def score_track(candidate, current, phase, played_set, played_list=None):
    if candidate["file"] in played_set: return -1

    _, _, target_e, _ = phase
    cur_bpm = current.get("bpm", 0) or 0
    cnd_bpm = candidate.get("bpm", 0) or 0
    cur_e   = current.get("energia", 50) or 50
    cnd_e   = candidate.get("energia", 50) or 50

    score = 0.0

    # 1. BPM — lo más importante para una mezcla limpia (0-35 pts)
    if cur_bpm and cnd_bpm:
        diff = abs(cur_bpm - cnd_bpm)
        if diff <= 3:
            # BPM casi idéntico: progressive mix posible → bonus extra
            score += 35
        elif diff <= 14:
            score += max(0.0, 35 - diff * 2.5)
        else:
            # BPM muy diferente: penalizar pero no descartar
            score += max(0.0, 5 - (diff - 14) * 0.5)
    else:
        score += 10  # sin BPM: neutro

    # 2. Energía objetivo de la fase (0-30 pts)
    e_dist = abs(cnd_e - target_e)
    score += max(0.0, 30 - e_dist * 1.1)

    # 3. Coherencia de transición — no saltar de 90 a 30 de golpe (0-15 pts)
    jump = abs(cnd_e - cur_e)
    if jump > 35: score -= 5   # penalizar saltos brutales
    else: score += max(0.0, 15 - jump * 0.43)

    # 4. Compatibilidad armónica — rueda de Camelot (0-15 pts)
    score += key_compatibility_bonus(
        current.get("key",""), candidate.get("key","")
    )

    # 5. Anti-repetición de tonalidad: si las últimas 2 canciones tuvieron
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

    # 7. Factor humano — un DJ no es un algoritmo puro
    score += random.gauss(0, 4)

    # 8. Preferencias del usuario (like/dislike)
    pref = PREFS.get(candidate["file"], 0)
    if pref == 1:   score += 18   # like: grande boost
    elif pref == -1: score -= 50  # dislike: prácticamente descartada

    return max(0.0, score)


def pick_next(library, current, played_set, played_count, played_list=None):
    total = len(library)
    phase = get_phase(played_count, total)

    scored = [(t, score_track(t, current, phase, played_set, played_list))
              for t in library]
    candidates = [(t, s) for t, s in scored if s >= 0]

    if not candidates:
        # Todas sonaron — reiniciar historial (sesión continua)
        new_ps = {current["file"]}
        candidates = [(t, score_track(t, current, phase, new_ps, played_list))
                      for t in library if t["file"] != current["file"]]
        candidates = [(t,s) for t,s in candidates if s >= 0]

    if not candidates:
        return None, 0, phase

    candidates.sort(key=lambda x: x[1], reverse=True)

    # Selección ponderada top-3: humano, no siempre el #1
    top     = candidates[:min(3, len(candidates))]
    total_w = sum(s for _, s in top) or 1
    r, acc  = random.random() * total_w, 0
    chosen  = top[0][0]
    for t, s in top:
        acc += s
        if r <= acc: chosen = t; break

    return chosen, candidates[0][1], phase


# ══════════════════════════════════════════════════════════════
#  PLAN DE MEZCLA
# ══════════════════════════════════════════════════════════════
def build_plan(current, nxt, current_time, phase):
    dur  = float(current.get("duracion_segundos") or 0)
    ps   = current.get("puede_salir")
    e1   = current.get("energia", 50) or 50
    e2   = nxt.get("energia", 50) or 50
    bpm1 = current.get("bpm", 0) or 0
    bpm2 = nxt.get("bpm", 0) or 0

    style = detect_style(phase, e1, e2, bpm1, bpm2)
    cf    = fade_duration(phase, e1, e2, style)

    # Punto de salida ideal: puede_salir del JSON, o últimos 3s de la canción
    exit_at = float(ps) if ps else (dur - 2.0 if dur else current_time + 90)

    # Comenzar el fade exactamente cf segundos antes de la salida
    start_mix = exit_at - cf

    # Nunca antes del 73% de la canción  
    min_start = dur * 0.73 if dur else current_time + 10
    start_mix = max(start_mix, min_start, current_time + 8)

    # ── Punto de entrada de la pista ENTRANTE ──────────────────
    # Prioridad:
    #   1. puede_empezar_mezcla manual (el usuario lo sabe mejor que nadie)
    #   2. intro_fin auto-detectado (saltar la intro instrumental larga)
    #   3. Si tiene_voz_inicio=True, también usar intro_fin para no entrar
    #      con voz cantando encima de la pista saliente
    #   4. Fallback: 0 (desde el principio)
    pem       = nxt.get("puede_empezar_mezcla")
    intro_fin = nxt.get("intro_fin")
    tiene_voz = nxt.get("tiene_voz_inicio", False)

    if pem is not None:
        # Manual tiene prioridad absoluta
        enter_at = float(pem)
    elif intro_fin is not None and intro_fin >= 3.0:
        # Hay intro detectada — entrar al acabar la intro
        # Ajustar al beat más próximo (4 beats antes del fin de intro)
        # para que el drop de la entrante caiga alineado
        bpm2 = nxt.get("bpm", 0) or 0
        if bpm2 > 0:
            beat_dur = 60.0 / bpm2
            # Entrar 4 beats antes del fin de intro para que el drop
            # caiga dentro del crossfade, no después
            enter_at = max(0.0, intro_fin - beat_dur * 4)
        else:
            enter_at = max(0.0, intro_fin - 4.0)
    elif tiene_voz:
        # Tiene voz desde el principio pero no intro larga detectada.
        # Entrar en el segundo 4 como mínimo para evitar la voz del inicio.
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

    # TimingDecisionEngine — respetar si no corta demasiado pronto
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


# ══════════════════════════════════════════════════════════════
#  PREFERENCIAS DE USUARIO (like/dislike)
# ══════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════
#  SERVER
# ══════════════════════════════════════════════════════════════
LIBRARY = load_library()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        p  = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(p.query)

        if p.path in ("/", "/index.html"):
            self.ok(HTML.encode("utf-8"), "text/html")

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


# ══════════════════════════════════════════════════════════════
#  FRONTEND
# ══════════════════════════════════════════════════════════════
#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════
#  NUEVO BLOQUE HTML  —  NEXUS · Club Underground Futurista
#  Reemplaza completamente la variable HTML = r""" ... """
#  La lógica Python / audio engine no ha sido modificada.
# ══════════════════════════════════════════════════════════════

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>NEXUS · AI DJ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Space+Grotesk:wght@300;400;500&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════════════════
   RESET & ROOT VARS
═══════════════════════════════════════════════════════════ */
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;background:#000;cursor:none}
body{font-family:'Space Grotesk',sans-serif;}

:root{
  --cobalt:   #0047ff;
  --violet:   #8b2fff;
  --cyan:     #00f0ff;
  --laser:    #00ff88;
  --white:    #ffffff;
  --dim:      rgba(255,255,255,0.04);
}

/* ═══════════════════════════════════════════════════════════
   SCANLINES  —  textura CRT de baja opacidad
═══════════════════════════════════════════════════════════ */
body::after{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:9000;
  background:repeating-linear-gradient(
    0deg,transparent,transparent 2px,
    rgba(0,0,0,0.055) 2px,rgba(0,0,0,0.055) 3px
  );
}

/* ═══════════════════════════════════════════════════════════
   IDLE SCREEN
═══════════════════════════════════════════════════════════ */
#idle{
  position:fixed;inset:0;z-index:500;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:32px;
  background:#000;
  transition:opacity 1.8s ease,visibility 1.8s ease;
}
#idle.off{opacity:0;visibility:hidden;pointer-events:none;}

/* Grid líneas de fondo en idle */
#idle::before{
  content:'';position:absolute;inset:0;pointer-events:none;
  background-image:
    linear-gradient(rgba(0,71,255,0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,71,255,0.07) 1px, transparent 1px);
  background-size:60px 60px;
  mask-image:radial-gradient(ellipse 80% 70% at 50% 50%, black 20%, transparent 80%);
}
#idle::after{
  content:'';position:absolute;inset:0;pointer-events:none;
  background:
    radial-gradient(ellipse 70% 60% at 30% 40%, rgba(139,47,255,0.15) 0%, transparent 60%),
    radial-gradient(ellipse 55% 70% at 70% 55%, rgba(0,71,255,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 40% 40% at 50% 15%, rgba(0,240,255,0.09) 0%, transparent 55%);
}

.idle-tagline{
  font-family:'Share Tech Mono',monospace;
  font-size:10px;letter-spacing:8px;text-transform:uppercase;
  color:rgba(0,240,255,0.45);
  position:relative;z-index:1;
}

.idle-logo{
  font-family:'Orbitron',sans-serif;font-weight:900;
  font-size:clamp(72px,15vw,160px);
  letter-spacing:clamp(12px,2.5vw,30px);
  color:#fff;line-height:1;
  position:relative;z-index:1;
  animation:logo-pulse 5s ease-in-out infinite;
}
@keyframes logo-pulse{
  0%,100%{
    text-shadow:
      0 0 30px rgba(0,71,255,0.9),
      0 0 70px rgba(139,47,255,0.6),
      0 0 140px rgba(0,71,255,0.3);
  }
  33%{
    text-shadow:
      0 0 40px rgba(0,240,255,1),
      0 0 90px rgba(0,240,255,0.7),
      0 0 200px rgba(0,71,255,0.4),
      0 0 400px rgba(139,47,255,0.15);
  }
  66%{
    text-shadow:
      0 0 35px rgba(0,255,136,0.9),
      0 0 80px rgba(0,255,136,0.5),
      0 0 160px rgba(0,71,255,0.3);
  }
}

/* Glitch effect en idle logo */
.idle-logo::before,.idle-logo::after{
  content:'NEXUS';
  position:absolute;top:0;left:0;right:0;
  font-family:'Orbitron',sans-serif;font-weight:900;
  font-size:inherit;letter-spacing:inherit;
}
.idle-logo::before{
  color:rgba(0,240,255,0.25);
  animation:glitch-a 4s infinite;
  clip-path:polygon(0 20%,100% 20%,100% 40%,0 40%);
}
.idle-logo::after{
  color:rgba(139,47,255,0.25);
  animation:glitch-b 4s infinite;
  clip-path:polygon(0 65%,100% 65%,100% 80%,0 80%);
}
@keyframes glitch-a{
  0%,94%,100%{transform:translate(0);}
  95%{transform:translate(-3px,1px);}
  97%{transform:translate(3px,-1px);}
}
@keyframes glitch-b{
  0%,96%,100%{transform:translate(0);}
  97%{transform:translate(3px,2px);}
  99%{transform:translate(-3px,-2px);}
}

.idle-sub{
  font-family:'Share Tech Mono',monospace;font-size:11px;letter-spacing:5px;
  color:rgba(139,47,255,0.5);text-transform:uppercase;
  position:relative;z-index:1;
}

/* Botón Play */
.play-btn{
  width:100px;height:100px;border-radius:50%;
  background:rgba(0,71,255,0.06);
  border:1px solid rgba(0,71,255,0.5);
  cursor:pointer;color:#fff;
  display:flex;align-items:center;justify-content:center;
  position:relative;z-index:1;
  box-shadow:0 0 40px rgba(0,71,255,0.35),inset 0 0 30px rgba(0,71,255,0.08);
  transition:all 0.3s ease;
}
.play-btn::before{
  content:'';position:absolute;inset:-8px;border-radius:50%;
  border:1px solid rgba(0,240,255,0.2);
  animation:ring-out 2.6s ease-out infinite;
}
.play-btn::after{
  content:'';position:absolute;inset:-18px;border-radius:50%;
  border:1px solid rgba(139,47,255,0.12);
  animation:ring-out 2.6s ease-out 0.65s infinite;
}
@keyframes ring-out{0%{transform:scale(1);opacity:0.7}100%{transform:scale(1.75);opacity:0}}
.play-icon{
  width:0;height:0;
  border-top:13px solid transparent;
  border-bottom:13px solid transparent;
  border-left:21px solid rgba(255,255,255,0.9);
  margin-left:5px;
}
.play-btn:hover{
  border-color:rgba(0,240,255,0.8);
  box-shadow:0 0 70px rgba(0,240,255,0.5),inset 0 0 40px rgba(0,240,255,0.1);
  transform:scale(1.06);
}
.play-btn:disabled{opacity:0.15;cursor:not-allowed;}
.play-btn:disabled::before,.play-btn:disabled::after{display:none;}

.idle-info{
  font-family:'Share Tech Mono',monospace;font-size:11px;
  color:rgba(0,71,255,0.5);letter-spacing:2px;
  position:relative;z-index:1;
}
.idle-info b{color:rgba(0,240,255,0.8);}

/* ═══════════════════════════════════════════════════════════
   STAGE
═══════════════════════════════════════════════════════════ */
#stage{
  position:fixed;inset:0;z-index:1;
  opacity:0;transition:opacity 2s ease;
  background:#000;
}
#stage.on{opacity:1;}

/* Tres canvases apilados */
#cvBg,#cvViz,#cvPart{
  position:absolute;inset:0;width:100%;height:100%;
}
#cvBg{z-index:1;}
#cvViz{z-index:2;}
#cvPart{z-index:3;pointer-events:none;}

/* ═══════════════════════════════════════════════════════════
   STROBE OVERLAY — activo en drops
═══════════════════════════════════════════════════════════ */
#strobeOverlay{
  position:fixed;inset:0;z-index:50;
  pointer-events:none;
  background:#fff;
  opacity:0;
  transition:opacity 0.04s linear;
}

/* ═══════════════════════════════════════════════════════════
   MODE BADGE — nombre del modo visual
═══════════════════════════════════════════════════════════ */
#modeBadge{
  position:fixed;top:32px;left:50%;transform:translateX(-50%);
  z-index:100;pointer-events:none;
  font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:7px;
  text-transform:uppercase;
  color:rgba(0,240,255,0.6);
  opacity:0;transition:opacity 1s ease;
}
#modeBadge.show{opacity:1;}

/* ═══════════════════════════════════════════════════════════
   HUD  —  Holographic heads-up display
═══════════════════════════════════════════════════════════ */
#hud{
  position:fixed;bottom:0;left:0;right:0;z-index:80;
  padding:0 48px 44px;
  display:flex;align-items:flex-end;justify-content:space-between;
  pointer-events:none;
}
/* Gradiente inferior profundo */
#hud::before{
  content:'';position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(
    to top,
    rgba(0,0,0,0.96) 0%,
    rgba(0,0,0,0.55) 45%,
    transparent 100%
  );
}

/* ── HUD Left ── */
.hud-left{position:relative;z-index:1;max-width:72%;}

/* Micro lineas decorativas tipo HUD */
.hud-coords{
  font-family:'Share Tech Mono',monospace;font-size:8px;letter-spacing:4px;
  color:rgba(0,240,255,0.3);margin-bottom:10px;
  animation:coords-blink 3.5s ease-in-out infinite;
}
@keyframes coords-blink{
  0%,100%{color:rgba(0,240,255,0.3);}
  50%{color:rgba(0,240,255,0.55);}
}

.hud-label{
  font-family:'Share Tech Mono',monospace;font-size:8px;letter-spacing:6px;
  text-transform:uppercase;color:rgba(0,71,255,0.7);margin-bottom:7px;
}

#npTitle{
  font-family:'Orbitron',sans-serif;font-weight:700;
  font-size:clamp(24px,4vw,60px);letter-spacing:2px;line-height:1;
  color:#fff;
  text-shadow:0 0 25px rgba(0,71,255,0.5);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  transition:text-shadow 0.07s ease;
  opacity:0;
  animation:hud-appear 1s ease 0.2s forwards;
}
#npTitle.beat-pulse{
  text-shadow:
    0 0 50px rgba(0,240,255,1),
    0 0 100px rgba(0,71,255,0.8),
    0 0 200px rgba(139,47,255,0.4);
}
@keyframes hud-appear{
  from{opacity:0;transform:translateX(-8px);}
  to{opacity:1;transform:translateX(0);}
}

.hud-meta{
  display:flex;align-items:center;gap:14px;margin-top:9px;
  opacity:0;animation:hud-appear 1s ease 0.5s forwards;
}
.hud-bpm{
  font-family:'Share Tech Mono',monospace;font-size:12px;
  color:rgba(0,240,255,0.9);font-weight:400;letter-spacing:1px;
}
.hud-key{
  font-family:'Share Tech Mono',monospace;font-size:10px;
  color:rgba(0,255,136,0.85);
  padding:2px 8px;border:1px solid rgba(0,255,136,0.25);border-radius:2px;
  letter-spacing:1px;
}
.hud-estilo{
  font-family:'Share Tech Mono',monospace;font-size:9px;letter-spacing:3px;
  text-transform:uppercase;
  color:rgba(255,200,80,0.85);
  padding:2px 8px;border:1px solid rgba(255,200,80,0.2);border-radius:2px;
}
.hud-dur{
  font-family:'Share Tech Mono',monospace;font-size:10px;
  color:rgba(255,255,255,0.2);letter-spacing:1px;
}

/* Micro progreso bar — 1px, solo visual */
#progressTrack{
  position:fixed;bottom:0;left:0;right:0;
  height:1px;z-index:90;pointer-events:none!important;
  background:rgba(255,255,255,0.04);
}
#progressFill{
  height:1px;width:0%;
  background:linear-gradient(to right,
    rgba(0,71,255,0.6),
    rgba(0,240,255,0.8),
    rgba(139,47,255,0.6)
  );
  transition:width 1s linear;
  pointer-events:none!important;
  box-shadow:0 0 6px rgba(0,240,255,0.5);
}

/* ── HUD Right ── */
.hud-right{
  position:relative;z-index:1;
  display:flex;flex-direction:column;align-items:flex-end;gap:10px;
  opacity:0;animation:hud-appear 1s ease 0.8s forwards;
}

/* Phase pill */
#phasePill{
  font-family:'Share Tech Mono',monospace;font-size:8px;letter-spacing:4px;
  text-transform:uppercase;padding:5px 14px;border-radius:20px;border:1px solid;
  transition:all 0.7s ease;
}
.pill-warm-up{color:rgba(0,71,255,0.85);border-color:rgba(0,71,255,0.3);background:rgba(0,71,255,0.05);}
.pill-first-build{color:rgba(139,47,255,0.9);border-color:rgba(139,47,255,0.35);background:rgba(139,47,255,0.07);}
.pill-first-peak{
  color:#fff;border-color:rgba(0,240,255,0.6);background:rgba(0,71,255,0.12);
  animation:pill-peak 0.9s ease-in-out infinite;
}
.pill-breakdown{color:rgba(0,255,136,0.7);border-color:rgba(0,255,136,0.25);background:rgba(0,255,136,0.04);}
.pill-second-build{color:rgba(139,47,255,0.9);border-color:rgba(139,47,255,0.35);background:rgba(139,47,255,0.07);}
.pill-second-peak{
  color:#fff;border-color:rgba(0,240,255,0.7);background:rgba(139,47,255,0.14);
  animation:pill-peak 0.65s ease-in-out infinite;
}
.pill-outro{color:rgba(255,255,255,0.18);border-color:rgba(255,255,255,0.08);background:transparent;}
@keyframes pill-peak{
  0%,100%{box-shadow:none;}
  50%{box-shadow:0 0 20px rgba(0,240,255,0.55),0 0 40px rgba(139,47,255,0.25);}
}

/* Mix indicator */
#mixIndicator{
  font-family:'Share Tech Mono',monospace;font-size:8px;letter-spacing:3px;
  text-transform:uppercase;padding:5px 14px;border-radius:20px;
  display:none;align-items:center;gap:8px;
  color:rgba(0,255,136,0.85);border:1px solid rgba(0,255,136,0.25);background:rgba(0,255,136,0.04);
}
#mixIndicator.on{display:flex;}
.mix-dot-ind{
  width:5px;height:5px;border-radius:50%;background:currentColor;
  animation:blink-dot 0.5s step-end infinite;
}
@keyframes blink-dot{50%{opacity:0;}}

/* Like / dislike */
#likeRow{display:flex;gap:8px;align-items:center;pointer-events:all;}
.like-btn{
  background:transparent;border:1px solid rgba(255,255,255,0.12);
  border-radius:50%;width:36px;height:36px;
  cursor:pointer;font-size:15px;
  display:flex;align-items:center;justify-content:center;
  transition:all 0.2s ease;color:rgba(255,255,255,0.5);
}
.like-btn:hover{
  border-color:rgba(255,255,255,0.4);background:rgba(255,255,255,0.07);
  transform:scale(1.12);
}
.like-btn.active-like{
  border-color:rgba(0,255,136,0.7);background:rgba(0,255,136,0.12);
  box-shadow:0 0 14px rgba(0,255,136,0.35);color:rgba(0,255,136,1);
}
.like-btn.active-dislike{
  border-color:rgba(255,60,80,0.7);background:rgba(255,60,80,0.12);
  box-shadow:0 0 14px rgba(255,60,80,0.35);color:rgba(255,60,80,1);
}

/* ═══════════════════════════════════════════════════════════
   CORNER DECORATION — líneas HUD decorativas
═══════════════════════════════════════════════════════════ */
.hud-corner{
  position:fixed;z-index:79;pointer-events:none;
  width:40px;height:40px;
  opacity:0.35;
}
.hud-corner.tl{top:28px;left:28px;border-top:1px solid rgba(0,240,255,0.6);border-left:1px solid rgba(0,240,255,0.6);}
.hud-corner.tr{top:28px;right:28px;border-top:1px solid rgba(0,240,255,0.6);border-right:1px solid rgba(0,240,255,0.6);}
.hud-corner.bl{bottom:28px;left:28px;border-bottom:1px solid rgba(0,240,255,0.6);border-left:1px solid rgba(0,240,255,0.6);}
.hud-corner.br{bottom:28px;right:28px;border-bottom:1px solid rgba(0,240,255,0.6);border-right:1px solid rgba(0,240,255,0.6);}

/* ═══════════════════════════════════════════════════════════
   ELEMENTOS INVISIBLES — compatibilidad JS
═══════════════════════════════════════════════════════════ */
.beat-dot{display:none!important;}
#app,#tlWrap{display:none!important;}
#eqRow,#mixRow,#nxtRow,#ww,#wc,#ph,#phHandle{display:none!important;}
#viz{position:absolute;left:-9999px;opacity:0;width:1px;height:1px;}
</style>
</head>
<body>

<!-- ═══════════════ IDLE ══════════════════════════════════ -->
<div id="idle">
  <div class="idle-tagline">AI DJ · Autonomous Session · Club Mode</div>
  <div class="idle-logo">NEXUS</div>
  <div class="idle-sub">Sistema de Mezcla Autónomo · v3.0</div>
  <button class="play-btn" id="btnStart" disabled>
    <div class="play-icon"></div>
  </button>
  <div class="idle-info" id="idleInfo">Cargando biblioteca...</div>
</div>

<!-- ═══════════════ STAGE ═════════════════════════════════ -->
<div id="stage">
  <canvas id="cvBg"></canvas>
  <canvas id="cvViz"></canvas>
  <canvas id="cvPart"></canvas>
</div>

<!-- Strobe -->
<div id="strobeOverlay"></div>

<!-- Corners HUD -->
<div class="hud-corner tl"></div>
<div class="hud-corner tr"></div>
<div class="hud-corner bl"></div>
<div class="hud-corner br"></div>

<!-- Mode badge -->
<div id="modeBadge">TUNNEL MODE</div>

<!-- HUD -->
<div id="hud">
  <div class="hud-left">
    <div class="hud-coords" id="hudCoords">SYS:// 00.00.00 · NEXUS_NODE_ACTIVE</div>
    <div class="hud-label">Now Playing</div>
    <div id="npTitle">—</div>
    <div class="hud-meta">
      <span class="hud-bpm"   id="npBpm"></span>
      <span class="hud-key"   id="npKey"    style="display:none"></span>
      <span class="hud-estilo" id="npEstilo" style="display:none"></span>
      <span class="hud-dur"   id="npDur"></span>
    </div>
  </div>
  <div class="hud-right">
    <div id="phasePill" class="pill-warm-up">WARM</div>
    <div id="mixIndicator"><div class="mix-dot-ind"></div><span id="mixLabel">MIX</span></div>
    <div id="likeRow">
      <button class="like-btn" id="btnLike"    onclick="sendLike('like')"    title="Like">▲</button>
      <button class="like-btn" id="btnDislike" onclick="sendLike('dislike')" title="Dislike">▼</button>
    </div>
  </div>
</div>

<!-- Progress line (1px, no interaction) -->
<div id="progressTrack"><div id="progressFill"></div></div>

<!-- ═══════════════ COMPAT ELEMENTS (hidden) ══════════════ -->
<div id="app" style="display:none">
  <canvas id="viz"></canvas>
  <div class="card">
    <div class="np">
      <div id="vinyl"></div>
      <div class="np-info">
        <div id="npTitleHidden">—</div>
        <div class="np-meta">
          <span id="npBpmHidden">—</span><span id="npEgy">—</span>
          <span id="npKeyHidden">—</span><span id="npDurHidden">—</span>
          <span id="phasePillHidden">warm-up</span>
        </div>
      </div>
    </div>
    <div id="ww" style="display:none">
      <canvas id="wc"></canvas>
      <div id="ph"><div id="phHandle"></div></div>
      <div id="wwTooltip">0:00</div>
      <div class="times"><span id="tCur">0:00</span><span id="tTot">0:00</span></div>
    </div>
    <div id="eqRow">
      <div><div id="eqLo" style="width:100%"></div></div>
      <div><div id="eqMid" style="width:100%"></div></div>
      <div><div id="eqHi" style="width:100%"></div></div>
    </div>
    <div class="arc">
      <div><div id="arcCursor" style="left:0%"></div></div>
      <div id="arcPhase">warm-up</div>
    </div>
    <div id="mixRow">
      <div id="mixStyleLabel">⚡</div>
      <div><div id="mixFill"></div></div>
      <div id="mixInfo">mezclando...</div>
    </div>
    <div id="nxtRow">
      <div id="nxtNm">—</div><div id="nxtSc">—</div>
      <div id="nxtT">—</div>
      <button id="btnCue" disabled></button>
    </div>
    <div>
      <div><div id="bpmVal">—</div></div>
      <div id="beatDot"></div><div id="modB">—</div>
      <button id="btnSkip" disabled></button>
      <div id="log">—</div>
    </div>
  </div>
  <div id="tlWrap">
    <canvas id="tlCurve"></canvas>
    <div id="tlBlocks"></div>
    <div id="tlHead" style="left:0%"></div>
    <div id="tlLabels"></div>
    <span id="tlDur">—</span>
  </div>
  <div class="lib"><span id="libCount">—</span><div id="tlist"></div></div>
</div>

<script>
// ════════════════════════════════════════════════════════════════
//  NEXUS · DJ AI  Audio Engine + Club Visual System
//  Audio engine idéntico al original.
//  Visual system 100% nuevo: 3 modos que rotan cada 45s.
// ════════════════════════════════════════════════════════════════

const AC = window.AudioContext || window.webkitAudioContext;
let ctx = null;

const PHASE_ORDER  = ['warm-up','first-build','first-peak','breakdown','second-build','second-peak','outro'];
const PHASE_LABELS = {'warm-up':'WARM','first-build':'BUILD','first-peak':'PEAK 1',
  'breakdown':'DOWN','second-build':'BUILD 2','second-peak':'PEAK 2','outro':'OUTRO'};
const STYLE_LABELS = {guetta:'⚡ GUETTA',avicii:'🌅 AVICII',progressive:'〰 PROG',fusion:'✦ FUSION'};
const STYLE_ICONS  = {guetta:'⚡',avicii:'🌅',progressive:'〰'};

const S = {
  lib:[], cur:null, curFile:null,
  nxt:null, nxtPlan:null, nxtScore:0, nxtPhase:'warm-up',
  played:[], playedSet:new Set(), count:0,
  playing:false, mixing:false,
  mixStart:0, mixDur:8,
  deck:'A', startAt:0, bufs:{},
  decks:{A:{},B:{}}, modOk:false,
  silenceStart:null, lastRms:1.0, silenceTriggered:false,
  beatLastTime:0, beatThresh:0.15, beatHistory:[], lastBpm:0,
  sessionTracks:[], sessionStartTime:0,
  _beatSnapScheduled:false,
  cueing:false, cueSrc:null, cueGain:null,
};

// ── Init AudioContext ─────────────────────────────────────────
function ic() {
  if (!ctx) {
    ctx = new AC();
    S.comp = ctx.createDynamicsCompressor();
    S.comp.threshold.value=-14; S.comp.knee.value=6;
    S.comp.ratio.value=4; S.comp.attack.value=0.003; S.comp.release.value=0.25;
    S.mAnl = ctx.createAnalyser(); S.mAnl.fftSize=1024;
    S.comp.connect(S.mAnl); S.mAnl.connect(ctx.destination);
  }
  if (ctx.state==='suspended') ctx.resume();
  if (!S.reverb) {
    S.reverb=ctx.createConvolver(); S.reverbGain=ctx.createGain();
    S.reverbGain.gain.value=0;
    const rate=ctx.sampleRate, len=Math.floor(rate*2.5);
    const ir=ctx.createBuffer(2,len,rate);
    for(let ch=0;ch<2;ch++){const d=ir.getChannelData(ch);for(let i=0;i<len;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/len,2.5);}
    S.reverb.buffer=ir;
    S.comp.connect(S.reverbGain); S.reverbGain.connect(S.reverb); S.reverb.connect(ctx.destination);
  }
  if (!S.cueOutGain){S.cueOutGain=ctx.createGain();S.cueOutGain.gain.value=0.85;S.cueOutGain.connect(ctx.destination);}
}

// ── Boot ─────────────────────────────────────────────────────
async function boot() {
  const [lr,mr]=await Promise.all([fetch('/api/library'),fetch('/api/modules')]);
  S.lib=await lr.json(); const m=await mr.json(); S.modOk=m.ok;
  await loadPrefs();
  document.getElementById('modB').textContent=S.modOk?'MÓDULOS OK':'FALLBACK';
  document.getElementById('libCount').textContent=S.lib.length+' canciones';
  document.getElementById('idleInfo').innerHTML=`<b>${S.lib.length}</b> canción${S.lib.length!==1?'es':''} · arco automático`;
  document.getElementById('btnStart').disabled=S.lib.length===0;
  if(!S.lib.length) document.getElementById('idleInfo').textContent='Pon MP3/WAV en musica/canciones/';
  renderLib();
}

// ── Scrubbing DESACTIVADO — experiencia blindada ──────────────
{
  S._dragging=()=>false; // siempre false: no hay scrubbing
}

// Bloquear TODOS los controles de teclado y media
window.addEventListener('keydown',e=>{
  const bl=['Space','ArrowLeft','ArrowRight','ArrowUp','ArrowDown',
    'MediaPlayPause','MediaStop','MediaTrackNext','MediaTrackPrevious'];
  if(bl.includes(e.code)){e.preventDefault();e.stopPropagation();}
},{capture:true});
window.addEventListener('touchmove',e=>e.preventDefault(),{passive:false});

// ── Start ─────────────────────────────────────────────────────
document.getElementById('btnStart').addEventListener('click',async()=>{
  ic();
  document.getElementById('idle').classList.add('off');
  document.getElementById('stage').classList.add('on');
  initClubVisuals();
  const first=chooseFirst();
  await begin(first);
});

function chooseFirst(){
  if(!S.lib.length) return null;
  const s=[...S.lib].sort((a,b)=>(a.energia||50)-(b.energia||50));
  return s[Math.floor(s.length*0.18)]||s[0];
}

async function begin(t){
  S.cur=t;S.curFile=t.file;S.deck='A';
  S.playing=true;S.startAt=0;
  S.played.push(t.file);S.playedSet.add(t.file);S.count=1;
  S.sessionStartTime=ctx.currentTime;
  S.sessionTracks=[{track:t,startCtxTime:ctx.currentTime,color:trackColor(0)}];
  updateNP(t,'warm-up');
  const startPos=t.start_position??0;
  await playDeck('A',t,startPos);
  logMsg(`Iniciando desde ${fmt(startPos)}: ${t.name}`);
  document.getElementById('btnSkip').disabled=false;
  renderLib(); renderTimeline(); loop(); askNext(t,0);
}

document.getElementById('btnSkip').addEventListener('click',()=>{if(!S.mixing&&S.playing) doMix();});

document.getElementById('btnCue').addEventListener('click',async()=>{
  if(!S.nxt) return; const btn=document.getElementById('btnCue');
  if(S.cueing){
    if(S.cueSrc){try{S.cueSrc.stop();}catch(e){}S.cueSrc=null;}
    if(S.cueGain) S.cueGain.gain.setValueAtTime(0,ctx.currentTime);
    S.cueing=false;btn.classList.remove('cueing');btn.textContent='👂 CUE';return;
  }
  try{
    const buf=await loadBuf(S.nxt),enterAt=S.nxtPlan?(S.nxtPlan.start_next_time||0):0,CUE_DUR=8;
    S.cueGain=ctx.createGain();S.cueGain.gain.setValueAtTime(0,ctx.currentTime);
    S.cueGain.gain.linearRampToValueAtTime(0.6,ctx.currentTime+0.3);S.cueGain.connect(S.cueOutGain);
    S.cueSrc=ctx.createBufferSource();S.cueSrc.buffer=buf;S.cueSrc.connect(S.cueGain);S.cueSrc.start(0,enterAt);
    S.cueGain.gain.setValueAtTime(0.6,ctx.currentTime+CUE_DUR-1);
    S.cueGain.gain.linearRampToValueAtTime(0,ctx.currentTime+CUE_DUR);
    S.cueSrc.stop(ctx.currentTime+CUE_DUR);
    S.cueSrc.onended=()=>{S.cueing=false;btn.classList.remove('cueing');btn.textContent='👂 CUE';S.cueSrc=null;};
    S.cueing=true;btn.classList.add('cueing');btn.textContent='■ STOP';
    logMsg(`👂 Preview: ${S.nxt.name}`);
  }catch(e){logMsg('Error cargando preview');}
});

async function askNext(t,ct){
  if(!t) return;
  try{
    const pe=encodeURIComponent(JSON.stringify([...S.playedSet]));
    const pl=encodeURIComponent(JSON.stringify(S.played.slice(-3).map(f=>({file:f,key:(S.lib.find(x=>x.file===f)||{}).key||''}))));
    const url=`/api/next?current=${encodeURIComponent(t.file)}&time=${ct.toFixed(1)}&played=${pe}&count=${S.count}&played_list=${pl}`;
    const d=await (await fetch(url)).json();
    if(d.error){S.nxt=null;hideNext();return;}
    S.nxt=d.track;S.nxtPlan=d.plan;S.nxtScore=d.score;S.nxtPhase=d.phase;
    showNext(d.track,d.plan,d.score,d.phase);updateArc(d.phase,d.target_energy);preload(d.track);renderLib();
  }catch(e){}
}

async function loadBuf(t){
  if(S.bufs[t.file]) return S.bufs[t.file];
  ic();const ab=await(await fetch('/audio/'+encodeURIComponent(t.file))).arrayBuffer();
  const buf=await ctx.decodeAudioData(ab);return S.bufs[t.file]=buf;
}
async function preload(t){if(!t||S.bufs[t.file]) return;try{ic();await loadBuf(t);}catch(e){}}

function resetGraph(dk){
  const d=S.decks[dk];
  if(d.src){try{d.src.stop();}catch(e){}d.src=null;}
  d.preGain=ctx.createGain();d.hipass=ctx.createBiquadFilter();
  d.lopass=ctx.createBiquadFilter();d.analyser=ctx.createAnalyser();d.analyser.fftSize=256;
  d.hipass.type='highpass';d.hipass.Q.value=0.71;
  d.lopass.type='lowpass';d.lopass.Q.value=0.71;
  d.preGain.connect(d.hipass);d.hipass.connect(d.lopass);d.lopass.connect(d.analyser);d.analyser.connect(S.comp);
  return d;
}

async function playDeck(dk,track,offset=0){
  const buf=await loadBuf(track);
  if(!track.duracion_segundos||track.duracion_segundos===0) track.duracion_segundos=buf.duration;
  const d=resetGraph(dk);const src=ctx.createBufferSource();src.buffer=buf;
  if(dk!==S.deck&&track.bpm&&S.cur&&S.cur.bpm&&track.bpm>0){
    const ratio=S.cur.bpm/track.bpm;src.playbackRate.setValueAtTime(ratio,ctx.currentTime);
    d._bpmRatio=ratio;d._bpmTarget=1.0;
  }else{src.playbackRate.value=1.0;d._bpmRatio=1.0;d._bpmTarget=1.0;}
  src.connect(d.preGain);d.preGain.gain.setValueAtTime(dk===S.deck?1:0,ctx.currentTime);
  d.hipass.frequency.setValueAtTime(dk===S.deck?20:320,ctx.currentTime);
  d.lopass.frequency.setValueAtTime(20000,ctx.currentTime);
  src.start(0,offset);d.src=src;d.startedAt=ctx.currentTime-offset;
  if(dk===S.deck){S.startAt=d.startedAt;drawWave(buf,track);}
  src.onended=()=>{if(S.playing&&dk===S.deck&&!S.mixing) doMix();};
}

function getTime(){return!S.playing||!ctx?0:Math.max(0,ctx.currentTime-S.startAt);}

async function doMix(){
  if(S.mixing||!S.playing) return;
  const nxt=S.nxt;
  if(!nxt){askNext(S.cur,getTime());setTimeout(()=>{if(!S.mixing&&S.nxt)doMix();},1200);return;}
  const plan=S.nxtPlan,cfDur=plan?(plan.mix_duration||8):8,enterAt=plan?(plan.start_next_time||0):0,style=plan?(plan.style||'guetta'):'guetta';
  if(S.cueing&&S.cueSrc){try{S.cueSrc.stop();}catch(e){}S.cueSrc=null;S.cueing=false;document.getElementById('btnCue').classList.remove('cueing');document.getElementById('btnCue').textContent='👂 CUE';}
  S.mixing=true;S.mixStart=ctx.currentTime;S.mixDur=cfDur;S.mixStyle=style;
  showMixing(nxt.name,cfDur,style);logMsg(`${STYLE_LABELS[style]||style} · ⇄ ${nxt.name} · ${cfDur.toFixed(0)}s`);
  if(S.reverb&&S.reverbGain){
    const rp=style==='avicii'?0.35:style==='progressive'?0.10:style==='fusion'?0.22:0.18;
    const rg=S.reverbGain.gain;rg.cancelScheduledValues(ctx.currentTime);rg.setValueAtTime(0,ctx.currentTime);
    rg.linearRampToValueAtTime(rp,ctx.currentTime+cfDur*0.35);rg.linearRampToValueAtTime(rp*0.5,ctx.currentTime+cfDur*0.75);rg.linearRampToValueAtTime(0,ctx.currentTime+cfDur);
  }
  const out=S.deck,inp=out==='A'?'B':'A';
  await playDeck(inp,nxt,enterAt);const inpStartedAt=ctx.currentTime-enterAt;
  const t0=ctx.currentTime,dOut=S.decks[out],dIn=S.decks[inp],steps=Math.round(cfDur*30);
  dOut.preGain.gain.cancelScheduledValues(t0);dIn.preGain.gain.cancelScheduledValues(t0);
  dOut.hipass.frequency.cancelScheduledValues(t0);dOut.lopass.frequency.cancelScheduledValues(t0);
  dIn.hipass.frequency.cancelScheduledValues(t0);dIn.lopass.frequency.cancelScheduledValues(t0);
  dOut.preGain.gain.setValueAtTime(1,t0);dIn.preGain.gain.setValueAtTime(0,t0);
  dOut.lopass.frequency.setValueAtTime(20000,t0);dOut.hipass.frequency.setValueAtTime(20,t0);dIn.lopass.frequency.setValueAtTime(20000,t0);
  if(style==='progressive'||style==='avicii'||style==='fusion') dIn.hipass.frequency.setValueAtTime(20,t0);
  else dIn.hipass.frequency.setValueAtTime(320,t0);
  if(style==='fusion') dOut.hipass.frequency.setValueAtTime(20,t0);
  if(style!=='progressive'&&dIn.src&&dIn._bpmRatio&&dIn._bpmRatio!==1.0){dIn.src.playbackRate.cancelScheduledValues(t0);dIn.src.playbackRate.setValueAtTime(dIn._bpmRatio,t0);dIn.src.playbackRate.exponentialRampToValueAtTime(1.0,t0+cfDur);}
  if(!S.compGain){S.compGain=ctx.createGain();S.compGain.gain.value=1;S.comp.disconnect(S.mAnl);S.comp.connect(S.compGain);S.compGain.connect(S.mAnl);}
  S.compGain.gain.cancelScheduledValues(t0);S.compGain.gain.setValueAtTime(1,t0);
  for(let i=0;i<=steps;i++){
    const f=i/steps,tAt=t0+f*cfDur;let vOut,vIn;
    if(style==='progressive'){vOut=Math.cos(f*Math.PI/2);vIn=Math.sin(f*Math.PI/2);}
    else if(style==='fusion'){if(f<0.20){vOut=1.0;vIn=Math.sin((f/0.20)*Math.PI/2);}else if(f<0.80){const mid=(f-0.20)/0.60;vOut=Math.cos(mid*Math.PI/2)*0.3+0.7;vIn=Math.sin(mid*Math.PI/2)*0.3+0.7;}else{const tail=(f-0.80)/0.20;vOut=Math.cos(tail*Math.PI/2)*0.7;vIn=1.0;}}
    else if(style==='avicii'){vOut=Math.pow(Math.cos(f*Math.PI/2),1.2);vIn=1/(1+Math.exp(-10*(f-0.35)));}
    else{vOut=Math.pow(1-f,0.9);vIn=1/(1+Math.exp(-16*(f-0.65)));}
    dOut.preGain.gain.setValueAtTime(Math.max(0,vOut),tAt);dIn.preGain.gain.setValueAtTime(Math.min(1,vIn),tAt);
    const power=Math.sqrt(vOut*vOut+vIn*vIn),cGain=power>0.01?Math.min(1.35,1/power):1;S.compGain.gain.setValueAtTime(cGain,tAt);
    if(style==='progressive'){const lf=f>0.5?(20000*Math.pow(8000/20000,(f-0.5)*2)):20000;dOut.lopass.frequency.setValueAtTime(Math.max(8000,lf),tAt);dIn.hipass.frequency.setValueAtTime(20,tAt);}
    else if(style==='fusion'){if(f<0.20){dOut.lopass.frequency.setValueAtTime(20000,tAt);dIn.hipass.frequency.setValueAtTime(20,tAt);}else if(f<0.80){const mid=(f-0.20)/0.60;const olf=20000*Math.pow(5000/20000,mid*0.6);dOut.lopass.frequency.setValueAtTime(Math.max(5000,olf),tAt);const ihf=80*Math.pow(20/80,Math.min(1,mid*2));dIn.hipass.frequency.setValueAtTime(Math.max(20,ihf),tAt);}else{const tail=(f-0.80)/0.20;const olf=5000*Math.pow(400/5000,tail);dOut.lopass.frequency.setValueAtTime(Math.max(400,olf),tAt);dIn.hipass.frequency.setValueAtTime(20,tAt);}}
    else if(style==='avicii'){const lf=20000*Math.pow(800/20000,Math.pow(f,1.4));dOut.lopass.frequency.setValueAtTime(Math.max(700,lf),tAt);const ohf=20*Math.pow(600/20,Math.pow(f,1.8));dOut.hipass.frequency.setValueAtTime(Math.min(600,ohf),tAt);const ihf=80*Math.pow(20/80,Math.pow(f*2,1.5));dIn.hipass.frequency.setValueAtTime(Math.max(20,ihf),tAt);}
    else{const lf=20000*Math.pow(500/20000,Math.pow(f,0.7));dOut.lopass.frequency.setValueAtTime(Math.max(400,lf),tAt);let hpf;if(f<0.60){hpf=320*Math.pow(200/320,f/0.60);}else{const bf=(f-0.60)/0.40;hpf=200*Math.pow(20/200,Math.pow(bf,1.5));}dIn.hipass.frequency.setValueAtTime(Math.max(20,hpf),tAt);}
  }
  setTimeout(async()=>{updateNP(nxt,S.nxtPhase);if(S.bufs[nxt.file])drawWave(S.bufs[nxt.file],nxt);},cfDur*500);
  setTimeout(async()=>{
    S.deck=inp;S.startAt=inpStartedAt;S.cur=nxt;S.curFile=nxt.file;
    S.played.push(nxt.file);S.playedSet.add(nxt.file);S.count++;S.nxt=null;S.nxtPlan=null;
    S.sessionTracks.push({track:nxt,startCtxTime:inpStartedAt,color:trackColor(S.sessionTracks.length)});
    document.getElementById('btnCue').disabled=true;
    await askNext(nxt,getTime());renderLib();renderTimeline();
  },cfDur*950);
  setTimeout(()=>{
    const dO=S.decks[out];
    if(dO.preGain){dO.preGain.gain.cancelScheduledValues(ctx.currentTime);dO.preGain.gain.setValueAtTime(0,ctx.currentTime);}
    if(dO.src){try{dO.src.stop();}catch(e){}dO.src=null;}
    if(dO.hipass) dO.hipass.frequency.setValueAtTime(20,ctx.currentTime);
    if(dO.lopass) dO.lopass.frequency.setValueAtTime(20000,ctx.currentTime);
    if(S.compGain){S.compGain.gain.cancelScheduledValues(ctx.currentTime);S.compGain.gain.linearRampToValueAtTime(1,ctx.currentTime+0.3);}
    S.mixing=false;S.silenceStart=null;S.silenceTriggered=false;hideMixing();hideEQ();logMsg(`Reproduciendo: ${S.cur.name}`);
  },cfDur*1000+250);
}

// ── Animation loop ────────────────────────────────────────────
function loop(){
  requestAnimationFrame(loop);
  if(!S.playing||!ctx) return;
  const t=getTime(),dur=S.cur?(S.cur.duracion_segundos||0):0;
  if(S.mixing){
    const pct=Math.min(100,((ctx.currentTime-S.mixStart)/S.mixDur)*100);
    const mf=document.getElementById('mixFill');if(mf) mf.style.width=pct+'%';
    updateEQVisual(pct/100);
  }
  // Progress bar blindado
  if(dur>0){const pct=Math.min(99.8,(t/dur)*100);document.getElementById('progressFill').style.width=pct+'%';}
  // HUD coords animado
  if(S.playing){
    const bpm=S.cur?(S.cur.bpm||0):0;
    const e=S.cur?(S.cur.energia||50):50;
    document.getElementById('hudCoords').textContent=
      `SYS:// BPM_${bpm?bpm.toFixed(0):'--'} · E_${e} · ${PHASE_LABELS[S.nxtPhase||'warm-up']||'WARM'}`;
  }
  // Beat detection for timeline head
  if(!S.mixing&&S.nxt&&dur>0){
    const cf=S.nxtPlan?(S.nxtPlan.mix_duration||8):8;
    const ps=S.cur?(parseFloat(S.cur.puede_salir)||0):0;
    const pe=S.nxtPlan?(parseFloat(S.nxtPlan.exit_at)||0):0;
    let trig;
    if(ps>0) trig=ps-cf; else if(pe>0) trig=pe-cf; else trig=dur-cf-2;
    trig=Math.max(trig,dur*0.73);
    if(t>=trig-0.5&&t<trig+2.5&&!S._beatSnapScheduled){
      S._beatSnapScheduled=true;
      const bt=S.cur?(S.cur.beat_times||[]):[];let snap=trig;
      if(bt.length>0){let bd=9999,bb=trig;for(const b of bt){const d=Math.abs(b-trig);if(d<bd&&d<1.5){bd=d;bb=b;}}snap=bb;}
      const delay=Math.max(0,(snap-t)*1000);
      setTimeout(()=>{S._beatSnapScheduled=false;if(!S.mixing&&S.nxt)doMix();},delay);
    }
  }
  if(!S.mixing&&S.cur&&S.nxt&&Math.round(t)%20===0&&t>8) askNext(S.cur,t);
  if(S.playing&&S.sessionTracks.length>0){
    const el=ctx.currentTime-S.sessionStartTime;
    const tot=S.sessionTracks.reduce((a,s)=>a+(s.track.duracion_segundos||180),0);
    const pct=Math.min(99,(el/Math.max(tot,1))*100);
    const th=document.getElementById('tlHead');if(th) th.style.left=pct+'%';
  }
  if(!S.mixing&&S.playing&&t>5){
    const dk=S.decks[S.deck];
    if(dk&&dk.analyser){
      const b2=new Uint8Array(dk.analyser.frequencyBinCount);dk.analyser.getByteFrequencyData(b2);
      let sum=0;for(let i=0;i<b2.length;i++) sum+=(b2[i]/255)*(b2[i]/255);
      const rms=Math.sqrt(sum/b2.length);
      if(rms<0.03&&(dur>0?t/dur:0)>0.30&&!S.silenceTriggered){
        if(S.silenceStart===null) S.silenceStart=ctx.currentTime;
        else if((ctx.currentTime-S.silenceStart)*1000>1800){S.silenceTriggered=true;S.silenceStart=null;doMix();}
      }else if(rms>=0.03){S.silenceStart=null;S.silenceTriggered=false;}
    }
  }
  drawNexusViz();
}

// ── EQ visual ─────────────────────────────────────────────────
function updateEQVisual(f){
  document.getElementById('eqHi').style.width=Math.max(0,(1-Math.pow(f/0.8,0.6))*100)+'%';
  document.getElementById('eqMid').style.width=Math.max(0,(1-Math.pow(f/0.9,0.8))*100)+'%';
  document.getElementById('eqLo').style.width=Math.max(0,(1-Math.pow(f/1.0,1.2))*100)+'%';
}
function hideEQ(){
  document.getElementById('eqRow').classList.remove('on');
  ['eqHi','eqMid','eqLo'].forEach(id=>document.getElementById(id).style.width='100%');
}

// ── UI helpers ─────────────────────────────────────────────────
function updateNP(t,phase){
  const tEl=document.getElementById('npTitle');
  if(tEl){tEl.style.animation='none';tEl.offsetHeight;tEl.style.animation='hud-appear 1s ease 0.2s forwards';tEl.textContent=t.name;}
  const bEl=document.getElementById('npBpm');if(bEl) bEl.textContent=t.bpm?t.bpm.toFixed(1)+' BPM':'';
  const dEl=document.getElementById('npDur');if(dEl) dEl.textContent=t.duracion_segundos?fmt(t.duracion_segundos):'';
  const kEl=document.getElementById('npKey');if(kEl){if(t.key){kEl.textContent=t.key;kEl.style.display='inline';}else kEl.style.display='none';}
  const eEl=document.getElementById('npEstilo');if(eEl){if(t.estilo){eEl.textContent=t.estilo;eEl.style.display='inline';}else eEl.style.display='none';}
  const bv=document.getElementById('bpmVal');if(bv) bv.textContent=t.bpm?Math.round(t.bpm):'—';
  const pill=document.getElementById('phasePill');const p=phase||S.nxtPhase||'warm-up';
  if(pill){pill.textContent=PHASE_LABELS[p]||p;pill.setAttribute('class','pill-'+p);}
  const egy=document.getElementById('npEgy');if(egy) egy.textContent=t.energia?'E'+t.energia:'';
  updateLikeUI(t.file);
}
function updateArc(phase,targetE){
  const idx=PHASE_ORDER.indexOf(phase),pct=idx<0?0:(idx/(PHASE_ORDER.length-1))*100;
  document.getElementById('arcCursor').style.left=pct+'%';
  document.getElementById('arcPhase').textContent=(PHASE_LABELS[phase]||phase)+' · E→'+Math.round(targetE);
}
function showNext(t,plan,score,phase){
  document.getElementById('nxtRow').style.display='flex';
  document.getElementById('nxtNm').textContent=t.name;
  document.getElementById('nxtSc').textContent='Score '+Math.round(score);
  const style=plan?(plan.style||'guetta'):'guetta';
  const sLbl=STYLE_ICONS[style]||'⚡';
  document.getElementById('nxtT').textContent=plan?`${sLbl} ${style.toUpperCase()} · ${(plan.mix_duration||8).toFixed(0)}s fade`:'';
  document.getElementById('btnCue').disabled=false;
}
function hideNext(){document.getElementById('nxtRow').style.display='none';}
function showMixing(name,dur,style){
  const row=document.getElementById('mixRow');
  if(row){row.classList.add('on');row.classList.remove('style-guetta','style-avicii','style-progressive','style-fusion');row.classList.add('style-'+(style||'guetta'));}
  const lbl=document.getElementById('mixStyleLabel');if(lbl) lbl.textContent=STYLE_LABELS[style]||'⚡';
  const mi=document.getElementById('mixInfo');if(mi) mi.textContent=`→ ${name} · ${dur.toFixed(0)}s`;
  const mf=document.getElementById('mixFill');if(mf) mf.style.width='0%';
  const eq=document.getElementById('eqRow');if(eq) eq.classList.add('on');
  const ind=document.getElementById('mixIndicator'),mlb=document.getElementById('mixLabel');
  if(ind&&mlb){ind.className='on style-'+(style||'guetta');mlb.textContent=(STYLE_LABELS[style]||'MIX').replace(/^.+\s/,'');}
}
function hideMixing(){
  const row=document.getElementById('mixRow');if(row) row.classList.remove('on');
  const ind=document.getElementById('mixIndicator');if(ind) ind.className='';
}
S.prefs={};
async function loadPrefs(){try{const r=await fetch('/api/prefs');S.prefs=await r.json();}catch(e){}}
async function sendLike(action){
  if(!S.cur) return;const file=S.cur.file;const current=S.prefs[file];
  const sa=(action==='like'&&current===1)||(action==='dislike'&&current===-1)?'clear':action;
  try{
    await fetch('/api/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({file,action:sa})});
    if(sa==='like') S.prefs[file]=1;else if(sa==='dislike') S.prefs[file]=-1;else delete S.prefs[file];
    updateLikeUI(file);
    const tEl=document.getElementById('npTitle');
    if(tEl){const orig=tEl.textContent;tEl.textContent=sa==='like'?'▲ LIKED':sa==='dislike'?'▼ SKIP':'— RESET';setTimeout(()=>{tEl.textContent=orig;},1400);}
  }catch(e){}
}
function updateLikeUI(file){
  const p=S.prefs[file]||0;
  const bl=document.getElementById('btnLike'),bd=document.getElementById('btnDislike');
  if(bl) bl.classList.toggle('active-like',p===1);
  if(bd) bd.classList.toggle('active-dislike',p===-1);
}
function renderLib(){
  const list=document.getElementById('tlist');if(!S.lib.length){list.innerHTML='<div class="empty"><p>Pon MP3/WAV en musica/canciones/</p></div>';return;}
  const cBpm=S.cur?(S.cur.bpm||0):0;
  list.innerHTML=S.lib.map((t,i)=>{
    const iC=t.file===S.curFile,iN=S.nxt&&t.file===S.nxt.file,done=!iC&&S.playedSet.has(t.file);
    const bOk=!cBpm||!t.bpm||Math.abs(t.bpm-cBpm)<=10,sc=iN?Math.round(S.nxtScore):null,sC=sc===null?'':sc>70?'hi':sc>40?'mi':'lo';
    return `<div class="tk ${iC?'cur':''} ${iN?'nxt':''} ${done?'done':''}">
      <div class="tn">${iC?'▶':iN?'→':done?'✓':i+1}</div><div class="tt">${t.name}${t.estilo?` <span class="tk-estilo">${t.estilo}</span>`:''}</div>
      <div class="te"><div class="tef" style="width:${t.energia||50}%"></div></div>
      <div class="tb ${bOk?'ok':'no'}">${t.bpm?t.bpm.toFixed(0)+'bpm':'—'}</div>
      <div class="ts ${sC}">${sc!==null?sc:'—'}</div><div class="td">${t.duracion_segundos?fmt(t.duracion_segundos):'—'}</div>
      <div class="tpref">${(S.prefs[t.file]===1)?'▲':(S.prefs[t.file]===-1)?'▼':''}</div></div>`;
  }).join('');
}
function drawWave(buf,track){
  const c=document.getElementById('wc'),dpr=devicePixelRatio||1;
  c.width=c.offsetWidth*dpr;c.height=c.offsetHeight*dpr;
  const g=c.getContext('2d');g.scale(dpr,dpr);
  const W=c.offsetWidth,H=c.offsetHeight,mid=H/2,data=buf.getChannelData(0),step=Math.ceil(data.length/W);
  g.clearRect(0,0,W,H);
  const gr=g.createLinearGradient(0,0,W,0);
  gr.addColorStop(0,'rgba(0,71,255,.06)');gr.addColorStop(.4,'rgba(0,240,255,.6)');gr.addColorStop(.6,'rgba(139,47,255,.5)');gr.addColorStop(1,'rgba(0,71,255,.06)');
  g.strokeStyle=gr;g.lineWidth=1;g.beginPath();
  for(let i=0;i<W;i++){let mn=1,mx=-1;for(let j=0;j<step;j++){const v=data[i*step+j]||0;if(v<mn)mn=v;if(v>mx)mx=v;}g.moveTo(i,mid+mn*mid);g.lineTo(i,mid+mx*mid);}
  g.stroke();
  if(!track) return;const dur=track.duracion_segundos||buf.duration;
  if(track.puede_empezar_mezcla){const x1=(track.puede_empezar_mezcla/dur)*W,x2=track.debe_sonar_sola?(track.debe_sonar_sola/dur)*W:W;g.fillStyle='rgba(0,240,255,.04)';g.fillRect(x1,0,x2-x1,H);g.strokeStyle='rgba(0,240,255,.18)';g.lineWidth=1;g.beginPath();g.moveTo(x1,0);g.lineTo(x1,H);g.stroke();}
  if(track.puede_salir){const xo=(track.puede_salir/dur)*W;g.strokeStyle='rgba(0,255,136,.35)';g.lineWidth=1;g.beginPath();g.moveTo(xo,0);g.lineTo(xo,H);g.stroke();g.fillStyle='rgba(0,255,136,.5)';g.beginPath();g.moveTo(xo-3,0);g.lineTo(xo+3,0);g.lineTo(xo,5);g.fill();}
}
function trackColor(idx){
  const p=['rgba(0,71,255','rgba(0,240,255','rgba(139,47,255','rgba(0,255,136','rgba(255,60,80','rgba(255,200,0','rgba(0,180,255','rgba(200,80,255'];
  return p[idx%p.length];
}
function renderTimeline(){
  const wrap=document.getElementById('tlWrap');if(!wrap||!S.sessionTracks.length) return;
  wrap.style.display='block';
  const blocks=document.getElementById('tlBlocks'),labels=document.getElementById('tlLabels'),tlDur=document.getElementById('tlDur');
  const durations=S.sessionTracks.map(st=>st.track.duracion_segundos||180),total=durations.reduce((a,b)=>a+b,0);
  blocks.innerHTML=S.sessionTracks.map((st,i)=>{
    const dur=st.track.duracion_segundos||180,pct=(dur/total*100).toFixed(2),isCur=st.track.file===S.curFile,isDone=!isCur&&i<S.sessionTracks.length-1,e=st.track.energia||50,col=st.color,hPct=30+e*0.7;
    return `<div class="tl-block ${isCur?'playing':''} ${isDone?'done':'future'}" style="width:${pct}%;background:${col},.08)" title="${st.track.name}"><div style="position:absolute;bottom:0;left:0;right:0;height:${hPct}%;background:${col},.4);border-radius:2px 2px 0 0;pointer-events:none"></div></div>`;
  }).join('');
  let leftPct=0;
  labels.innerHTML=S.sessionTracks.map((st,i)=>{
    const dur=st.track.duracion_segundos||180,pct=dur/total*100,mid=leftPct+pct/2;leftPct+=pct;
    const isCur=st.track.file===S.curFile,name=st.track.name.length>12?st.track.name.slice(0,11)+'…':st.track.name;
    return `<span class="tl-lbl ${isCur?'cur':''}" style="left:${mid.toFixed(1)}%">${name}</span>`;
  }).join('');
  tlDur.textContent=`~${Math.floor(total/60)} min`;
}
function logMsg(m){document.getElementById('log').textContent=m;}
function fmt(s){s=Math.max(0,Math.floor(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');}
function resize(){['viz','wc'].forEach(id=>{const c=document.getElementById(id);c.width=c.offsetWidth*(devicePixelRatio||1);c.height=c.offsetHeight*(devicePixelRatio||1);});}
window.addEventListener('resize',resize);resize();


// ════════════════════════════════════════════════════════════════
//  ✦  NEXUS VISUAL ENGINE  ✦
//
//  Tres modos — rotación cada 45 segundos:
//    0 · TUNNEL      — túnel fractal hacia el espectador
//    1 · LASERS      — haces vectoriales neon que cruzan la pantalla
//    2 · SHOCKWAVE   — ondas de choque estroboscópicas + drops
//
//  Colores mutantes: cobalt → violet → cyan → laser green
//  Fondo: negro absoluto, sin concesiones
// ════════════════════════════════════════════════════════════════

const NX = {
  // Global timing
  mode:         0,
  modeNames:    ['TUNNEL MODE', 'LASER MODE', 'SHOCKWAVE MODE'],
  modeSwitchAt: 0,
  MODE_DUR:     45,
  frameN:       0,
  t:            0,

  // Audio state
  smoothE:  0,
  beatE:    0,
  subE:     0,
  midE:     0,
  hiE:      0,

  // Beat
  beatHistory: [],
  lastBeatCtx: 0,
  isBeat:      false,

  // Color rotation (hue)
  hue:        220,
  targetHue:  220,

  // ── MODE 0: TUNNEL ──────────────────────────────────────
  tunnel:{
    rings:   [],        // anillos del túnel
    angle:   0,
    zSpeed:  0,         // velocidad Z base
    agitate: 0,         // sacudida en beat
  },

  // ── MODE 1: LASERS ──────────────────────────────────────
  laser:{
    beams:   [],
    spawnT:  0,
  },

  // ── MODE 2: SHOCKWAVE ───────────────────────────────────
  shock:{
    rings:    [],       // ondas expansivas
    strobeOn: false,
    strobeT:  0,
    particles:[],
  },

  // Canvas refs (set in init)
  W:0, H:0,
};

// ─────────────────────────────────────────────────────────────
//  Init
// ─────────────────────────────────────────────────────────────
function initClubVisuals(){
  const cvBg  = document.getElementById('cvBg');
  const cvViz = document.getElementById('cvViz');
  const cvPart= document.getElementById('cvPart');

  function doResize(){
    const dpr=devicePixelRatio||1, w=window.innerWidth, h=window.innerHeight;
    [cvBg,cvViz,cvPart].forEach(c=>{
      c.width=w*dpr; c.height=h*dpr;
      c.style.width=w+'px'; c.style.height=h+'px';
    });
    NX.W=w; NX.H=h;
  }
  window.addEventListener('resize',doResize); doResize();

  // Pre-seed tunnel rings
  for(let i=0;i<40;i++) NX.tunnel.rings.push(makeTunnelRing(i/40));

  // Pre-seed lasers
  for(let i=0;i<12;i++) NX.laser.beams.push(makeLaser());

  // Pre-seed shock particles
  for(let i=0;i<80;i++) NX.shock.particles.push(makeShockParticle());
}

// ─────────────────────────────────────────────────────────────
//  TUNNEL ring factory
// ─────────────────────────────────────────────────────────────
function makeTunnelRing(z){
  return{
    z:       z,             // 0 (far) → 1 (near)
    rotOff:  Math.random()*Math.PI*2,
    sides:   4+Math.floor(Math.random()*5)*2,  // 4,6,8,10,12
    twist:   (Math.random()-0.5)*0.4,
    hueOff:  Math.random()*60-30,
    thick:   0.5+Math.random()*1.5,
  };
}

// ─────────────────────────────────────────────────────────────
//  LASER beam factory
// ─────────────────────────────────────────────────────────────
function makeLaser(){
  const W=NX.W||window.innerWidth, H=NX.H||window.innerHeight;
  const fromEdge=Math.random()<0.5;
  let x1,y1,x2,y2;
  if(fromEdge){
    // Horizontal-ish beams
    const y=Math.random()*H;
    x1=-20; y1=y+(Math.random()-0.5)*H*0.3;
    x2=W+20; y2=y+(Math.random()-0.5)*H*0.3;
  }else{
    // Diagonal beams
    const side=Math.floor(Math.random()*4);
    if(side===0){x1=Math.random()*W;y1=-20;x2=Math.random()*W;y2=H+20;}
    else if(side===1){x1=Math.random()*W;y1=H+20;x2=Math.random()*W;y2=-20;}
    else if(side===2){x1=-20;y1=Math.random()*H;x2=W+20;y2=Math.random()*H;}
    else{x1=W+20;y1=Math.random()*H;x2=-20;y2=Math.random()*H;}
  }
  const hues=[220,260,180,120,300];
  return{
    x1,y1,x2,y2,
    hue:  hues[Math.floor(Math.random()*hues.length)],
    width:0.4+Math.random()*2.5,
    alpha:0.4+Math.random()*0.6,
    life: 1,
    decay:0.004+Math.random()*0.012,
    glow: Math.random()<0.4,
    dash: Math.random()<0.25,
    dashOffset: Math.random()*40,
    dashSpeed: (Math.random()-0.5)*0.8,
    split: Math.random()<0.2,  // doubles with offset
  };
}

// ─────────────────────────────────────────────────────────────
//  SHOCKWAVE particle factory
// ─────────────────────────────────────────────────────────────
function makeShockParticle(){
  const W=NX.W||window.innerWidth, H=NX.H||window.innerHeight;
  const angle=Math.random()*Math.PI*2;
  const speed=2+Math.random()*5;
  return{
    x: W/2+(Math.random()-0.5)*100,
    y: H/2+(Math.random()-0.5)*100,
    vx: Math.cos(angle)*speed,
    vy: Math.sin(angle)*speed,
    life: 1,
    decay: 0.01+Math.random()*0.02,
    size:  1+Math.random()*3,
    hue:   180+Math.random()*160,
    trail: [],
  };
}

// ─────────────────────────────────────────────────────────────
//  Shared color scheme — rotates with phase
// ─────────────────────────────────────────────────────────────
const PHASE_HUES = {
  'warm-up':220,'first-build':240,'first-peak':260,
  'breakdown':180,'second-build':255,'second-peak':280,'outro':200
};

function getColorSet(){
  const h=NX.hue;
  return{
    primary: `hsl(${h},100%,60%)`,
    secondary:`hsl(${(h+50)%360},100%,55%)`,
    accent:  `hsl(${(h+120)%360},100%,65%)`,
    dim:     `hsl(${h},80%,20%)`,
  };
}

// ─────────────────────────────────────────────────────────────
//  Mode switch logic
// ─────────────────────────────────────────────────────────────
function checkModeSwitch(nowCtx){
  if(NX.modeSwitchAt===0){NX.modeSwitchAt=nowCtx;return;}
  if(nowCtx-NX.modeSwitchAt<NX.MODE_DUR) return;

  NX.mode=(NX.mode+1)%3;
  NX.modeSwitchAt=nowCtx;

  const badge=document.getElementById('modeBadge');
  if(badge){
    badge.textContent=NX.modeNames[NX.mode];
    badge.classList.add('show');
    setTimeout(()=>badge.classList.remove('show'),3200);
  }

  // Re-seed data for new mode
  if(NX.mode===0){
    NX.tunnel.rings=[];
    for(let i=0;i<40;i++) NX.tunnel.rings.push(makeTunnelRing(i/40));
  }else if(NX.mode===1){
    NX.laser.beams=[];
    for(let i=0;i<12;i++) NX.laser.beams.push(makeLaser());
  }else{
    NX.shock.rings=[];
    NX.shock.particles=[];
    for(let i=0;i<80;i++) NX.shock.particles.push(makeShockParticle());
  }
}

// ─────────────────────────────────────────────────────────────
//  Audio analysis helpers
// ─────────────────────────────────────────────────────────────
function analyzeAudio(){
  const dk=S.decks[S.deck];
  let subE=0,midE=0,hiE=0,avgE=0;
  if(dk&&dk.analyser){
    const fd=new Uint8Array(dk.analyser.frequencyBinCount);
    dk.analyser.getByteFrequencyData(fd);
    const n=fd.length;
    for(let i=0;i<n;i++){
      const v=fd[i]/255; avgE+=v;
      if(i<n*0.08) subE+=v; else if(i<n*0.35) midE+=v; else hiE+=v;
    }
    avgE/=n; subE/=n*0.08; midE/=(n*0.27)||1; hiE/=(n*0.65)||1;
  }
  NX.smoothE+=(avgE-NX.smoothE)*0.10;
  NX.beatE  +=(subE-NX.beatE)  *0.22;
  NX.subE=subE; NX.midE=midE; NX.hiE=hiE;

  // Beat detection
  NX.beatHistory.push(subE);
  if(NX.beatHistory.length>28) NX.beatHistory.shift();
  const avgH=NX.beatHistory.reduce((a,b)=>a+b,0)/NX.beatHistory.length;
  const nowCtx=ctx?ctx.currentTime:0;
  NX.isBeat=subE>avgH*1.45&&subE>0.16&&(nowCtx-NX.lastBeatCtx)>0.17&&S.playing;
  if(NX.isBeat){
    NX.lastBeatCtx=nowCtx;
    // Beat pulse on title
    const tEl=document.getElementById('npTitle');
    if(tEl){tEl.classList.add('beat-pulse');setTimeout(()=>tEl.classList.remove('beat-pulse'),130);}
    const bd=document.getElementById('beatDot');
    if(bd){bd.classList.add('flash');setTimeout(()=>bd.classList.remove('flash'),80);}
  }

  // Hue tracking
  NX.targetHue=PHASE_HUES[S.nxtPhase||'warm-up']||220;
  NX.hue+=(NX.targetHue-NX.hue)*0.006;
}

// ─────────────────────────────────────────────────────────────
//  ██  MODE 0 — TUNNEL FRACTAL  ██
//
//  Anillos poligonales que viajan hacia el espectador.
//  Velocidad ligada al BPM estimado.
//  Beat → sacudida + aceleración.
// ─────────────────────────────────────────────────────────────
function drawTunnel(g, W, H){
  g.clearRect(0,0,W,H);
  const cx=W/2, cy=H/2;
  const bpm=S.cur?(S.cur.bpm||128):128;
  const bpmSpeed=bpm/128;  // normalizado a 1.0 a 128BPM

  // Sacudida en beat
  if(NX.isBeat) NX.tunnel.agitate=1.0;
  NX.tunnel.agitate*=0.88;

  // Avance Z global
  const baseSpeed=0.004*bpmSpeed;
  const burstSpeed=NX.tunnel.agitate*0.025;
  NX.tunnel.zSpeed=baseSpeed+burstSpeed+NX.smoothE*0.006;
  NX.tunnel.angle+=0.003+NX.smoothE*0.008;

  // Avanzar y reciclar rings
  for(const ring of NX.tunnel.rings){
    ring.z+=NX.tunnel.zSpeed;
    if(ring.z>=1) ring.z-=1;
  }

  // Ordenar por z (más lejos primero para dibujar encima los cercanos)
  NX.tunnel.rings.sort((a,b)=>a.z-b.z);

  for(const ring of NX.tunnel.rings){
    const z=ring.z;
    if(z<0.01) continue;

    // Perspectiva: 1/z
    const scale=Math.pow(z,1.8);
    const maxR=Math.min(W,H)*0.7;
    const r=scale*maxR*(0.5+NX.smoothE*0.2);

    const alpha=Math.min(1, z*1.5) * (0.25 + z*0.55);
    const hue=NX.hue+ring.hueOff+(ring.z*90);
    const lum=40+z*45;
    const width=ring.thick*(0.5+z*2)*(1+NX.beatE*0.5);

    g.save();
    g.translate(
      cx + Math.sin(NX.tunnel.angle*0.7+ring.rotOff)*NX.tunnel.agitate*30*z,
      cy + Math.cos(NX.tunnel.angle*0.5+ring.rotOff)*NX.tunnel.agitate*20*z
    );

    // Glow exterior
    if(z>0.4){
      g.shadowColor=`hsl(${hue},100%,70%)`;
      g.shadowBlur=8+z*20;
    }else{
      g.shadowBlur=0;
    }

    g.strokeStyle=`hsla(${hue},100%,${lum}%,${alpha})`;
    g.lineWidth=width;

    // Polígono retorcido
    const sides=ring.sides;
    const angleStep=Math.PI*2/sides;
    const rot=NX.tunnel.angle*ring.twist+ring.rotOff;
    g.beginPath();
    for(let s=0;s<=sides;s++){
      const a=angleStep*s+rot;
      // Distorsión reactiva a frecuencias
      const distort=1+NX.hiE*0.15*Math.sin(a*3+NX.tunnel.angle*2);
      const px=Math.cos(a)*r*distort;
      const py=Math.sin(a)*r*distort;
      if(s===0) g.moveTo(px,py); else g.lineTo(px,py);
    }
    g.closePath();
    g.stroke();

    // En los rings más cercanos, añadir diagonal interior
    if(z>0.75 && ring.sides<=8){
      g.globalAlpha=alpha*0.25;
      g.strokeStyle=`hsl(${hue+40},100%,80%)`;
      g.lineWidth=0.5;
      g.beginPath();
      const a0=rot, a1=rot+Math.PI;
      g.moveTo(Math.cos(a0)*r*0.15,Math.sin(a0)*r*0.15);
      g.lineTo(Math.cos(a0)*r*0.9, Math.sin(a0)*r*0.9);
      g.moveTo(Math.cos(a1)*r*0.15,Math.sin(a1)*r*0.15);
      g.lineTo(Math.cos(a1)*r*0.9, Math.sin(a1)*r*0.9);
      g.stroke();
      g.globalAlpha=1;
    }

    g.restore();
  }

  // Core glow central
  const coreAge=ctx?(ctx.currentTime-NX.lastBeatCtx):9;
  const cf=coreAge<0.4?(1-coreAge/0.4):0;
  if(cf>0||NX.smoothE>0.1){
    const coreR=g.createRadialGradient(cx,cy,0,cx,cy,Math.min(W,H)*0.15);
    coreR.addColorStop(0,`hsla(${NX.hue},100%,90%,${cf*0.5+NX.smoothE*0.15})`);
    coreR.addColorStop(0.5,`hsla(${NX.hue+30},100%,60%,${cf*0.2+NX.smoothE*0.06})`);
    coreR.addColorStop(1,'transparent');
    g.fillStyle=coreR;
    g.beginPath();g.arc(cx,cy,Math.min(W,H)*0.15,0,Math.PI*2);g.fill();
  }

  g.shadowBlur=0;
}

// ─────────────────────────────────────────────────────────────
//  ██  MODE 1 — LASER BEAMS  ██
//
//  Líneas vectoriales neon que cruzan el espacio negro.
//  Reaccionan a hi/mid frequencies.
//  Beat → spawn masivo + shake.
// ─────────────────────────────────────────────────────────────
function drawLasers(g, W, H){
  // Fondo negro puro con muy poca persistencia para que los láseres
  // dejen una estela breve
  g.fillStyle='rgba(0,0,0,0.18)';
  g.fillRect(0,0,W,H);

  // Spawn nuevos beams
  const spawnRate=2+Math.floor(NX.hiE*8+NX.midE*4);
  for(let i=0;i<spawnRate;i++) NX.laser.beams.push(makeLaser());
  if(NX.isBeat) for(let i=0;i<15;i++) NX.laser.beams.push(makeLaser());

  // Cap
  while(NX.laser.beams.length>180) NX.laser.beams.shift();

  // Renderizar
  NX.laser.beams=NX.laser.beams.filter(b=>b.life>0);
  for(const beam of NX.laser.beams){
    beam.life-=beam.decay*(0.7+NX.smoothE*1.5);
    beam.dashOffset+=beam.dashSpeed;

    const a=beam.life*beam.alpha;
    const hue=beam.hue+(NX.hue-220); // shift con la fase

    if(beam.glow){
      g.shadowColor=`hsl(${hue},100%,70%)`;
      g.shadowBlur=12+NX.hiE*20;
    }else{
      g.shadowBlur=0;
    }

    g.globalAlpha=a;
    g.strokeStyle=`hsl(${hue},100%,65%)`;
    g.lineWidth=beam.width*(0.5+beam.life*0.5)*(1+NX.hiE*0.6);

    if(beam.dash){
      g.setLineDash([8,12]);
      g.lineDashOffset=beam.dashOffset;
    }else{
      g.setLineDash([]);
    }

    g.beginPath();
    g.moveTo(beam.x1,beam.y1);
    g.lineTo(beam.x2,beam.y2);
    g.stroke();

    // Split double beam
    if(beam.split){
      const off=4+NX.midE*8;
      const dx=beam.y2-beam.y1,dy=beam.x1-beam.x2;
      const len=Math.sqrt(dx*dx+dy*dy)||1;
      const nx=dx/len*off,ny=dy/len*off;
      g.globalAlpha=a*0.4;
      g.lineWidth=beam.width*0.5;
      g.beginPath();g.moveTo(beam.x1+nx,beam.y1+ny);g.lineTo(beam.x2+nx,beam.y2+ny);g.stroke();
      g.beginPath();g.moveTo(beam.x1-nx,beam.y1-ny);g.lineTo(beam.x2-nx,beam.y2-ny);g.stroke();
    }
  }

  g.globalAlpha=1; g.shadowBlur=0; g.setLineDash([]);

  // Grid de puntos intersección (sutil)
  if(NX.smoothE>0.15){
    const gridA=NX.smoothE*0.04;
    g.fillStyle=`hsla(${NX.hue},100%,70%,${gridA})`;
    const step=Math.max(20,120-NX.smoothE*80);
    for(let x=0;x<W;x+=step) for(let y=0;y<H;y+=step){
      g.beginPath();g.arc(x,y,1,0,Math.PI*2);g.fill();
    }
  }
}

// ─────────────────────────────────────────────────────────────
//  ██  MODE 2 — SHOCKWAVE ESTROBOSCÓPICA  ██
//
//  Anillos concéntricos expansivos distorsionados.
//  En drops/peaks: flicker estroboscópico controlado.
// ─────────────────────────────────────────────────────────────
function drawShockwave(g, gPart, W, H){
  g.clearRect(0,0,W,H);
  gPart.clearRect(0,0,W,H);

  const cx=W/2, cy=H/2;
  const nowCtx=ctx?ctx.currentTime:0;

  // ── Strobe en drops/peaks ──
  const isPeak=S.nxtPhase==='first-peak'||S.nxtPhase==='second-peak';
  const strobeEl=document.getElementById('strobeOverlay');
  if(isPeak&&NX.isBeat&&strobeEl){
    // Flicker controlado: máx 3 flashes por beat, baja opacidad
    NX.shock.strobeT=nowCtx;
    strobeEl.style.opacity='0.06';
    setTimeout(()=>{strobeEl.style.opacity='0';},35);
    setTimeout(()=>{strobeEl.style.opacity='0.04';},70);
    setTimeout(()=>{strobeEl.style.opacity='0';},100);
  }

  // ── Spawn anillos expansivos en beat ──
  if(NX.isBeat){
    for(let i=0;i<3;i++){
      const distort=[];
      const pts=128;
      for(let j=0;j<pts;j++){
        distort.push({
          dr: (Math.random()-0.5)*60*(1+NX.subE),
          da: (Math.random()-0.5)*0.12,
        });
      }
      NX.shock.rings.push({
        r:      5,
        maxR:   Math.min(W,H)*0.9*(0.6+Math.random()*0.4),
        speed:  8+NX.smoothE*12+i*3,
        life:   1,
        decay:  0.006+i*0.003,
        hue:    NX.hue+(i*40),
        width:  3-i*0.5,
        distort,
      });
    }
    // Re-burst particles
    for(const p of NX.shock.particles){
      const angle=Math.random()*Math.PI*2,speed=3+Math.random()*8+NX.subE*10;
      p.x=cx+(Math.random()-0.5)*80;p.y=cy+(Math.random()-0.5)*80;
      p.vx=Math.cos(angle)*speed;p.vy=Math.sin(angle)*speed;
      p.life=1;p.trail=[];
    }
  }

  // ── Fondo pulsante ──
  const bgGlow=g.createRadialGradient(cx,cy,0,cx,cy,Math.min(W,H)*0.7);
  bgGlow.addColorStop(0,`hsla(${NX.hue},80%,8%,${0.04+NX.smoothE*0.12})`);
  bgGlow.addColorStop(0.6,`hsla(${NX.hue+60},70%,4%,${0.03+NX.smoothE*0.06})`);
  bgGlow.addColorStop(1,'transparent');
  g.fillStyle=bgGlow;g.fillRect(0,0,W,H);

  // ── Anillos expansivos distorsionados ──
  NX.shock.rings=NX.shock.rings.filter(r=>r.life>0);
  for(const ring of NX.shock.rings){
    ring.r+=ring.speed;
    ring.life-=ring.decay;
    if(ring.r>ring.maxR) ring.life=0;

    const alpha=ring.life*(0.4+NX.smoothE*0.3);
    const pts=ring.distort.length;
    const angleStep=Math.PI*2/pts;

    g.save();
    g.translate(cx,cy);
    g.strokeStyle=`hsla(${ring.hue},100%,65%,${alpha})`;
    g.lineWidth=ring.width*ring.life;
    g.shadowColor=`hsl(${ring.hue},100%,70%)`;
    g.shadowBlur=8+ring.life*15;

    g.beginPath();
    for(let i=0;i<=pts;i++){
      const d=ring.distort[i%pts];
      const angle=angleStep*i+d.da;
      const r=ring.r+d.dr*ring.life;
      const x=Math.cos(angle)*r, y=Math.sin(angle)*r;
      if(i===0) g.moveTo(x,y); else g.lineTo(x,y);
    }
    g.closePath();g.stroke();
    g.shadowBlur=0;
    g.restore();
  }

  // ── Freq spectrum radial (siempre activo) ──
  const dk=S.decks[S.deck];
  if(dk&&dk.analyser){
    const fd=new Uint8Array(dk.analyser.frequencyBinCount);
    dk.analyser.getByteFrequencyData(fd);
    const n=fd.length,step2=Math.PI*2/n;
    const baseR=Math.min(W,H)*0.12*(1+NX.smoothE*0.3);
    g.save();g.translate(cx,cy);
    for(let i=0;i<n;i++){
      const v=fd[i]/255;if(v<0.03) continue;
      const ang=step2*i+NX.shock.rings.length*0.01;
      const r0=baseR,r1=r0+v*Math.min(W,H)*0.35*(1+NX.smoothE*0.4);
      const h=NX.hue+(i/n)*60;
      g.strokeStyle=`hsla(${h},100%,${45+v*40}%,${0.4+v*0.55})`;
      g.lineWidth=1.2+v*2.5;
      g.shadowColor=`hsl(${h},100%,70%)`;g.shadowBlur=v>0.5?12:0;
      g.beginPath();g.moveTo(Math.cos(ang)*r0,Math.sin(ang)*r0);g.lineTo(Math.cos(ang)*r1,Math.sin(ang)*r1);g.stroke();
    }
    g.shadowBlur=0;g.restore();
  }

  // ── Partículas de shockwave ──
  NX.shock.particles=NX.shock.particles.filter(p=>p.life>0);
  for(const p of NX.shock.particles){
    p.trail.push({x:p.x,y:p.y});
    if(p.trail.length>8) p.trail.shift();
    p.x+=p.vx;p.y+=p.vy;p.vx*=0.97;p.vy*=0.97;
    p.life-=0.012+NX.smoothE*0.008;
    const a=p.life*0.85;
    // Trail
    if(p.trail.length>1){
      gPart.strokeStyle=`hsla(${p.hue},100%,70%,${a*0.35})`;
      gPart.lineWidth=p.size*p.life;
      gPart.beginPath();
      gPart.moveTo(p.trail[0].x,p.trail[0].y);
      for(let i=1;i<p.trail.length;i++) gPart.lineTo(p.trail[i].x,p.trail[i].y);
      gPart.stroke();
    }
    gPart.fillStyle=`hsla(${p.hue},100%,80%,${a})`;
    gPart.beginPath();gPart.arc(p.x,p.y,p.size*p.life,0,Math.PI*2);gPart.fill();
  }
  // Refill
  while(NX.shock.particles.length<80) NX.shock.particles.push(makeShockParticle());
}

// ─────────────────────────────────────────────────────────────
//  Background — negro absoluto con nebula de color
// ─────────────────────────────────────────────────────────────
function drawBackground(g,W,H){
  // Base totalmente negra
  g.fillStyle='rgba(0,0,0,0.82)';
  g.fillRect(0,0,W,H);

  // Nebula de color sutil — se mueve lentamente
  NX.t+=0.005;
  const cx=W/2,cy=H/2;
  const nx1=cx+Math.sin(NX.t*0.8)*W*0.18;
  const ny1=cy+Math.cos(NX.t*0.6)*H*0.12;
  const neR=Math.min(W,H)*(0.4+NX.smoothE*0.15);
  const ng=g.createRadialGradient(nx1,ny1,0,nx1,ny1,neR);
  ng.addColorStop(0,`hsla(${NX.hue},80%,20%,${0.04+NX.smoothE*0.06})`);
  ng.addColorStop(1,'transparent');
  g.fillStyle=ng;g.fillRect(0,0,W,H);

  const nx2=cx+Math.cos(NX.t*0.5)*W*0.22;
  const ny2=cy+Math.sin(NX.t*0.7)*H*0.16;
  const ng2=g.createRadialGradient(nx2,ny2,0,nx2,ny2,Math.min(W,H)*0.32);
  ng2.addColorStop(0,`hsla(${(NX.hue+80)%360},90%,15%,${0.03+NX.smoothE*0.04})`);
  ng2.addColorStop(1,'transparent');
  g.fillStyle=ng2;g.fillRect(0,0,W,H);
}

// ─────────────────────────────────────────────────────────────
//  MAIN DRAW — llamado desde loop()
// ─────────────────────────────────────────────────────────────
function drawNexusViz(){
  if(!S.playing||!ctx) return;
  const cvBg =document.getElementById('cvBg');
  const cvViz=document.getElementById('cvViz');
  const cvPart=document.getElementById('cvPart');
  if(!cvBg||!cvViz||!cvPart) return;

  const dpr=devicePixelRatio||1;
  const W=cvBg.width/dpr, H=cvBg.height/dpr;
  NX.W=W; NX.H=H; NX.frameN++;

  const gBg  =cvBg.getContext('2d');
  const gViz =cvViz.getContext('2d');
  const gPart=cvPart.getContext('2d');
  gBg.setTransform(dpr,0,0,dpr,0,0);
  gViz.setTransform(dpr,0,0,dpr,0,0);
  gPart.setTransform(dpr,0,0,dpr,0,0);

  // Analizar audio
  analyzeAudio();

  // Comprobar cambio de modo
  const nowCtx=ctx?ctx.currentTime:0;
  checkModeSwitch(nowCtx);

  // Fondo
  drawBackground(gBg,W,H);

  // Limpieza básica del canvas de particulas si no es shockwave
  if(NX.mode!==2) gPart.clearRect(0,0,W,H);

  // Modo visual principal
  if(NX.mode===0){
    gViz.clearRect(0,0,W,H);
    drawTunnel(gViz,W,H);
  }else if(NX.mode===1){
    drawLasers(gViz,W,H);
  }else{
    drawShockwave(gViz,gPart,W,H);
  }

  // ── Espectro horizontal en la base (siempre, cualquier modo) ──
  const dk=S.decks[S.deck];
  if(dk&&dk.analyser&&NX.mode!==2){
    const fd=new Uint8Array(dk.analyser.frequencyBinCount);
    dk.analyser.getByteFrequencyData(fd);
    const n=fd.length, bw=W/n, mirror=W/2;
    for(let i=0;i<n;i++){
      const v=fd[i]/255, bh=v*H*0.18*(1+NX.smoothE*0.4);
      if(bh<1) continue;
      const xL=mirror-i*bw-bw, xR=mirror+i*bw;
      const h=NX.hue+(i/n)*50;
      const grad=gViz.createLinearGradient(0,H,0,H-bh);
      grad.addColorStop(0,`hsla(${h},90%,25%,0.3)`);
      grad.addColorStop(0.7,`hsla(${h},100%,55%,${0.3+v*0.5})`);
      grad.addColorStop(1,`hsla(${h+20},100%,80%,${Math.min(1,0.5+v*0.6)})`);
      gViz.fillStyle=grad;
      if(xL>0) gViz.fillRect(xL,H-bh,bw-0.5,bh);
      if(xR<W) gViz.fillRect(xR,H-bh,bw-0.5,bh);
    }
  }

  // ── Beat rings (todos los modos) ──
  const beatAge=ctx?(ctx.currentTime-NX.lastBeatCtx):9;
  if(beatAge<1.8&&NX.mode!==2){
    const cx=W/2, cy=H/2;
    for(let r=0;r<4;r++){
      const td=Math.max(0,beatAge/1.8-r*0.07);
      const a=(1-td)*0.3;
      gViz.strokeStyle=`hsla(${NX.hue+r*30},100%,75%,${a})`;
      gViz.lineWidth=(1-td)*2.5;
      gViz.beginPath();gViz.arc(cx,cy,td*Math.min(W,H)*0.65,0,Math.PI*2);gViz.stroke();
    }
  }
}

// ─────────────────────────────────────────────────────────────
//  Arranque
// ─────────────────────────────────────────────────────────────
boot();
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
def main():
    SONGS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    if not LIBRARY:
        print(f"\n⚠️  Sin canciones en {SONGS_DIR}")
        print(f"   Pon tus MP3/WAV ahí y ejecuta de nuevo.\n")
    else:
        print(f"\n✅  {len(LIBRARY)} canciones")
        no_json = [t for t in LIBRARY if not t["bpm"]]
        if no_json:
            print(f"⚠️  {len(no_json)} sin JSON — la mezcla usará BPM fallback:")
            for t in no_json: print(f"   • {t['name']}")
        else:
            print(f"✅  Todas las canciones tienen JSON completo")

    url = f"http://localhost:{PORT}"
    print(f"\n🎧  {url}  —  abre el navegador, dale Play\n")

    threading.Thread(target=lambda:(time.sleep(1), webbrowser.open(url)), daemon=True).start()
    server = HTTPServer(("", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋")

if __name__ == "__main__":
    main()