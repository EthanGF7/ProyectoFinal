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
HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>NEXUS</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=IBM+Plex+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;background:#000;}
body{font-family:'DM Sans',sans-serif;}

/* Scanlines */
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:9998;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.06) 2px,rgba(0,0,0,.06) 3px);}

/* ── IDLE ─────────────────────────────────────────────── */
#idle{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:36px;z-index:100;background:#000;
  transition:opacity 1.4s,visibility 1.4s;}
#idle.off{opacity:0;visibility:hidden;pointer-events:none}

/* Nebula fondo en idle */
#idle::before{content:'';position:absolute;inset:0;
  background:
    radial-gradient(ellipse 80% 60% at 30% 40%, rgba(100,0,200,.18) 0%, transparent 60%),
    radial-gradient(ellipse 60% 80% at 70% 60%, rgba(0,60,180,.15) 0%, transparent 60%),
    radial-gradient(ellipse 40% 40% at 50% 20%, rgba(180,0,255,.1) 0%, transparent 50%);
  pointer-events:none;}

.idle-logo{font-family:'Orbitron',sans-serif;font-weight:900;
  font-size:clamp(64px,14vw,140px);letter-spacing:20px;
  color:#fff;
  text-shadow:
    0 0 40px rgba(140,80,255,.9),
    0 0 80px rgba(140,80,255,.5),
    0 0 160px rgba(80,120,255,.3);
  animation:nexuspulse 4s ease-in-out infinite;}
@keyframes nexuspulse{
  0%,100%{text-shadow:0 0 40px rgba(140,80,255,.9),0 0 80px rgba(140,80,255,.5),0 0 160px rgba(80,120,255,.3);}
  50%{text-shadow:0 0 60px rgba(180,100,255,1),0 0 120px rgba(140,80,255,.8),0 0 240px rgba(80,120,255,.5),0 0 400px rgba(60,80,200,.2);}}

.idle-sub{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:6px;
  color:rgba(160,120,255,.5);text-transform:uppercase;}

.play-btn{width:100px;height:100px;border-radius:50%;
  background:transparent;border:2px solid rgba(140,80,255,.6);
  cursor:pointer;font-size:36px;color:#fff;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 40px rgba(140,80,255,.4),inset 0 0 30px rgba(140,80,255,.1);
  transition:all .3s;position:relative;}
.play-btn::before{content:'';position:absolute;inset:-6px;border-radius:50%;
  border:1px solid rgba(140,80,255,.2);animation:ringgrow 2.5s ease-out infinite;}
.play-btn::after{content:'';position:absolute;inset:-14px;border-radius:50%;
  border:1px solid rgba(80,120,255,.1);animation:ringgrow 2.5s ease-out .6s infinite;}
@keyframes ringgrow{0%{transform:scale(1);opacity:.6}100%{transform:scale(1.6);opacity:0}}
.play-btn:hover{border-color:rgba(180,120,255,.9);
  box-shadow:0 0 80px rgba(140,80,255,.8),inset 0 0 50px rgba(140,80,255,.2);}
.play-btn:disabled{opacity:.2;cursor:not-allowed;}
.play-btn:disabled::before,.play-btn:disabled::after{display:none}
.idle-info{font-family:'IBM Plex Mono',monospace;font-size:11px;color:rgba(140,80,255,.4);}
.idle-info b{color:rgba(180,140,255,.8)}

/* ── STAGE — pantalla completa ────────────────────────── */
#stage{position:fixed;inset:0;z-index:1;opacity:0;transition:opacity 1.6s;background:#000;}
#stage.on{opacity:1;}

#vizMain{position:absolute;inset:0;width:100%;height:100%;}
#particles{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;}

/* ── HUD ─────────────────────────────────────────────── */
#hud{position:absolute;bottom:0;left:0;right:0;
  padding:0 52px 44px;
  display:flex;align-items:flex-end;justify-content:space-between;
  pointer-events:none;z-index:10;}
#hud::before{content:'';position:absolute;inset:0;
  background:linear-gradient(to top,rgba(0,0,0,.92) 0%,rgba(0,0,0,.4) 50%,transparent 100%);
  pointer-events:none;}

.hud-left{position:relative;z-index:1;max-width:75%;}
.hud-label{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:5px;
  text-transform:uppercase;color:rgba(140,80,255,.7);margin-bottom:8px;}

#npTitle{font-family:'Orbitron',sans-serif;font-weight:700;
  font-size:clamp(28px,4.5vw,68px);letter-spacing:2px;line-height:1;
  color:#fff;
  text-shadow:0 0 30px rgba(140,80,255,.5);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  transition:text-shadow .08s;}
#npTitle.beat-pulse{text-shadow:0 0 60px rgba(180,120,255,1),0 0 120px rgba(140,80,255,.7);}

.hud-meta{display:flex;align-items:center;gap:18px;margin-top:10px;}
.hud-bpm{font-family:'IBM Plex Mono',monospace;font-size:12px;
  color:rgba(140,80,255,.9);font-weight:700;}
.hud-key{font-family:'IBM Plex Mono',monospace;font-size:10px;
  color:rgba(100,160,255,.9);
  padding:2px 8px;border:1px solid rgba(100,160,255,.3);border-radius:3px;}
.hud-dur{font-family:'IBM Plex Mono',monospace;font-size:10px;color:rgba(255,255,255,.25);}
.hud-estilo{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;
  color:rgba(255,200,80,.9);padding:2px 8px;border:1px solid rgba(255,200,80,.3);border-radius:3px;}

#likeRow{display:flex;gap:8px;align-items:center;}
.like-btn{background:transparent;border:1px solid rgba(255,255,255,.15);border-radius:50%;
  width:36px;height:36px;cursor:pointer;font-size:16px;
  display:flex;align-items:center;justify-content:center;
  transition:all .2s;pointer-events:all;}
.like-btn:hover{border-color:rgba(255,255,255,.5);background:rgba(255,255,255,.08);transform:scale(1.12);}
.like-btn.active-like{border-color:rgba(80,220,120,.7);background:rgba(80,220,120,.15);
  box-shadow:0 0 16px rgba(80,220,120,.4);}
.like-btn.active-dislike{border-color:rgba(255,80,80,.7);background:rgba(255,80,80,.15);
  box-shadow:0 0 16px rgba(255,80,80,.4);}

.hud-right{position:relative;z-index:1;display:flex;flex-direction:column;align-items:flex-end;gap:10px;}

/* Phase pill */
#phasePill{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
  text-transform:uppercase;padding:5px 14px;border-radius:20px;border:1px solid;transition:all .6s;}
.pill-warm-up{color:rgba(100,160,255,.9);border-color:rgba(100,160,255,.3);background:rgba(100,160,255,.05)}
.pill-first-build{color:rgba(140,80,255,.9);border-color:rgba(140,80,255,.4);background:rgba(140,80,255,.06)}
.pill-first-peak{color:#fff;border-color:rgba(200,120,255,.6);background:rgba(180,80,255,.12);
  animation:peakglow 1s ease-in-out infinite}
.pill-breakdown{color:rgba(100,200,255,.9);border-color:rgba(100,200,255,.3);background:rgba(100,200,255,.05)}
.pill-second-build{color:rgba(140,80,255,.9);border-color:rgba(140,80,255,.4);background:rgba(140,80,255,.06)}
.pill-second-peak{color:#fff;border-color:rgba(220,140,255,.7);background:rgba(180,80,255,.15);
  animation:peakglow .7s ease-in-out infinite}
.pill-outro{color:rgba(255,255,255,.2);border-color:rgba(255,255,255,.1);background:transparent}
@keyframes peakglow{0%,100%{box-shadow:none}50%{box-shadow:0 0 24px rgba(180,80,255,.7)}}

/* Mix indicator */
#mixIndicator{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
  text-transform:uppercase;padding:5px 14px;border-radius:20px;
  display:none;align-items:center;gap:8px;
  color:rgba(100,200,255,.9);border:1px solid rgba(100,200,255,.3);background:rgba(100,200,255,.05);}
#mixIndicator.on{display:flex;}
.mix-dot-ind{width:5px;height:5px;border-radius:50%;background:currentColor;
  animation:blink .5s step-end infinite;}
@keyframes blink{50%{opacity:0}}

/* Elementos invisibles para compat JS */
.beat-dot{display:none}
#app,#tlWrap{display:none!important}
#eqRow,#mixRow,#nxtRow,#ww,#wc,#ph,#phHandle{display:none!important}
#viz{position:absolute;left:-9999px;opacity:0;width:1px;height:1px;}
</style>
</head>
<body>

<!-- IDLE -->
<div id="idle">
  <div class="idle-logo">NEXUS</div>
  <div class="idle-sub">AI DJ · Sesión autónoma</div>
  <button class="play-btn" id="btnStart" disabled>▶</button>
  <div class="idle-info" id="idleInfo">Cargando biblioteca...</div>
</div>

<!-- STAGE -->
<div id="stage">
  <canvas id="vizMain"></canvas>
  <canvas id="particles"></canvas>
  <div id="hud">
    <div class="hud-left">
      <div class="hud-label">Now Playing</div>
      <div id="npTitle">—</div>
      <div class="hud-meta">
        <span class="hud-bpm" id="npBpm"></span>
        <span class="hud-key" id="npKey" style="display:none"></span>
        <span class="hud-estilo" id="npEstilo" style="display:none"></span>
        <span class="hud-dur" id="npDur"></span>
      </div>
    </div>
    <div class="hud-right">
      <div id="phasePill" class="pill-warm-up">WARM</div>
      <div id="mixIndicator"><div class="mix-dot-ind"></div><span id="mixLabel">MIX</span></div>
      <div id="likeRow">
        <button class="like-btn" id="btnLike" onclick="sendLike('like')" title="Me gusta">👍</button>
        <button class="like-btn" id="btnDislike" onclick="sendLike('dislike')" title="No me gusta">👎</button>
      </div>
    </div>
  </div>
</div>

<!-- ELEMENTOS INVISIBLES PARA JS -->
<div id="app" style="display:none">
  <canvas id="viz"></canvas>
  <div class="card">
    <div class="np">
      <div id="vinyl"></div>
      <div class="np-info">
        <div id="npTitleHidden">—</div>
        <div class="np-meta">
          <span id="npBpmHidden">—</span>
          <span id="npEgy">—</span>
          <span id="npKeyHidden">—</span>
          <span id="npDurHidden">—</span>
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
      <div id="nxtNm">—</div>
      <div id="nxtSc">—</div>
      <div id="nxtT">—</div>
      <button id="btnCue" disabled></button>
    </div>
    <div>
      <div><div id="bpmVal">—</div></div>
      <div id="beatDot"></div>
      <div id="modB">—</div>
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
  <div class="lib">
    <span id="libCount">—</span>
    <div id="tlist"></div>
  </div>
</div>
<script>
// ════════════════════════════════════════════════════════════════
//  DJ AI  ·  Audio Engine
//
//  Grafo de audio por deck:
//
//    BufferSource → preGain
//                     → hipass (EQ kick: corta graves pista entrante)
//                       → lopass (EQ high-kill: corta agudos pista saliente)
//                         → masterGain
//                           → compressor
//                             → analyser
//                               → destination
//
//  Durante el crossfade (técnica DJ):
//    OUT: gainA 1→0 (curva cóncava lenta)
//         lopass baja 20kHz→400Hz  (quita agudos/mids)
//
//    IN:  gainB 0→1 (sigmoide TARDÍA: casi nada hasta t=55%, luego aparece)
//         hipass baja 350Hz→20Hz (los graves entran DESPUÉS del resto)
//         = "bass swap": se escuchan los graves de la entrante solo cuando
//           la saliente ya ha desaparecido casi por completo → drop limpio
//
//  EQ visual: 3 barras (lo/mid/hi) muestran lo que está pasando
// ════════════════════════════════════════════════════════════════

const AC = window.AudioContext || window.webkitAudioContext;
let ctx  = null;

const PHASE_ORDER = ['warm-up','first-build','first-peak','breakdown','second-build','second-peak','outro'];
const PHASE_LABELS = {'warm-up':'WARM','first-build':'BUILD','first-peak':'PEAK 1',
  'breakdown':'DOWN','second-build':'BUILD 2','second-peak':'PEAK 2','outro':'OUTRO'};
const STYLE_LABELS = { guetta: '⚡ GUETTA', avicii: '🌅 AVICII', progressive: '〰 PROG', fusion: '✦ FUSION' };
const STYLE_ICONS  = { guetta: '⚡', avicii: '🌅', progressive: '〰' };

const S = {
  lib: [], cur: null, curFile: null,
  nxt: null, nxtPlan: null, nxtScore: 0, nxtPhase: 'warm-up',
  played: [], playedSet: new Set(), count: 0,
  playing: false, mixing: false,
  mixStart: 0, mixDur: 8,
  deck: 'A',
  startAt: 0,
  bufs: {},
  // Deck nodes: S.decks.A = { src, preGain, hipass, lopass, gain, analyser }
  decks: { A: {}, B: {} },
  modOk: false,

  // Silence detection
  silenceStart: null,
  lastRms: 1.0,
  silenceTriggered: false,

  // Beat detection
  beatLastTime: 0,       // ctx.currentTime del último beat detectado
  beatThresh: 0.15,      // umbral dinámico de energía de sub-bass
  beatHistory: [],       // últimas energías para calcular umbral adaptativo
  lastBpm: 0,            // BPM estimado en tiempo real

  // Session timeline
  sessionTracks: [],     // [{track, startCtxTime, color}] orden real de reproducción
  sessionStartTime: 0,   // ctx.currentTime cuando empezó la sesión

  // Mix trigger
  _beatSnapScheduled: false,

  // Cue (preview siguiente)
  cueing: false,
  cueSrc: null,
  cueGain: null,
};

// ── Init ─────────────────────────────────────────────────────
function ic() {
  if (!ctx) {
    ctx  = new AC();
    // Master compressor — limita el volumen total, evita clipping durante el mix
    S.comp = ctx.createDynamicsCompressor();
    S.comp.threshold.value = -14;
    S.comp.knee.value      = 6;
    S.comp.ratio.value     = 4;
    S.comp.attack.value    = 0.003;
    S.comp.release.value   = 0.25;
    // Master analyser (para el visualizador principal)
    S.mAnl = ctx.createAnalyser();
    S.mAnl.fftSize = 1024;
    S.comp.connect(S.mAnl);
    S.mAnl.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();

  // Reverb (ConvolverNode con impulse response sintético)
  if (!S.reverb) {
    S.reverb    = ctx.createConvolver();
    S.reverbGain = ctx.createGain();
    S.reverbGain.gain.value = 0;  // empieza apagado, se activa en el mix

    // Generar impulse response exponencial (sala grande ~2.5s)
    const rate = ctx.sampleRate;
    const len  = Math.floor(rate * 2.5);
    const ir   = ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = ir.getChannelData(ch);
      for (let i = 0; i < len; i++) {
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i/len, 2.5);
      }
    }
    S.reverb.buffer = ir;
    S.comp.connect(S.reverbGain);
    S.reverbGain.connect(S.reverb);
    S.reverb.connect(ctx.destination);
  }

  // Cue output (auriculares DJ — va directo a destination con gain propio)
  if (!S.cueOutGain) {
    S.cueOutGain = ctx.createGain();
    S.cueOutGain.gain.value = 0.85;
    S.cueOutGain.connect(ctx.destination);
  }
}

// ── Boot ─────────────────────────────────────────────────────
async function boot() {
  const [lr, mr] = await Promise.all([fetch('/api/library'), fetch('/api/modules')]);
  S.lib  = await lr.json();
  const m = await mr.json();
  S.modOk = m.ok;
  await loadPrefs();

  const mb = document.getElementById('modB');
  mb.textContent = S.modOk ? 'MÓDULOS OK' : 'FALLBACK';
  mb.className   = 'mod ' + (S.modOk ? 'ok' : 'fb');

  document.getElementById('libCount').textContent = S.lib.length + ' canciones';
  document.getElementById('idleInfo').innerHTML =
    `<b>${S.lib.length}</b> canción${S.lib.length!==1?'es':''} · arco automático`;
  document.getElementById('btnStart').disabled = S.lib.length === 0;
  if (!S.lib.length)
    document.getElementById('idleInfo').textContent = 'Pon MP3/WAV en musica/canciones/';
  renderLib();
}

// ── Scrubbing (arrastrar playhead) ────────────────────────────
{
  const ww      = document.getElementById('ww');
  const ph      = document.getElementById('ph');
  const handle  = document.getElementById('phHandle');
  const tooltip = document.getElementById('wwTooltip');
  let dragging  = false;

  function scrubPos(e) {
    const rect = ww.getBoundingClientRect();
    const pad  = 18; // padding del .ww en px
    const x    = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left - pad;
    const w    = rect.width - pad * 2;
    return Math.max(0, Math.min(1, x / w));
  }

  function seekTo(frac) {
    const dur = S.cur ? (S.cur.duracion_segundos || 0) : 0;
    if (!dur || !S.playing || !ctx) return;
    const newTime = frac * dur;

    const dk  = S.deck;
    const trk = S.cur;
    if (!trk || !S.bufs[trk.file]) return;

    const d = S.decks[dk];
    if (d.src) {
      // Marcar como seek para que onended no dispare doMix
      d.src.onended = null;
      try { d.src.stop(); } catch(e) {}
      d.src = null;
    }

    const src = ctx.createBufferSource();
    src.buffer = S.bufs[trk.file];
    src.playbackRate.value = 1.0;
    src.connect(d.preGain);
    src.start(0, newTime);
    d.src       = src;
    d.startedAt = ctx.currentTime - newTime;
    S.startAt   = d.startedAt;
    S.silenceStart     = null;
    S.silenceTriggered = false;

    src.onended = () => {
      if (S.playing && dk === S.deck && !S.mixing) doMix();
    };
  }

  function onMove(e) {
    if (!S.playing) return;
    e.preventDefault();
    const frac = scrubPos(e);
    const dur  = S.cur ? (S.cur.duracion_segundos || 0) : 0;
    const wc   = document.getElementById('wc');
    const w    = wc.offsetWidth;

    // Mover playhead visualmente
    ph.style.left = (18 + frac * w) + 'px';

    // Tooltip con tiempo
    const t = frac * dur;
    tooltip.textContent = fmt(t);
    tooltip.style.left  = (18 + frac * w) + 'px';
    tooltip.classList.add('show');

    if (dragging) {
      // Actualizar tiempo en pantalla en tiempo real
      document.getElementById('tCur').textContent = fmt(t);
    }
  }

  function onDown(e) {
    if (!S.playing || S.mixing) return;
    dragging = true;
    ph.classList.add('scrubbing');
    handle.classList.add('scrubbing');
    onMove(e);
  }

  function onUp(e) {
    if (!dragging) return;
    dragging = false;
    ph.classList.remove('scrubbing');
    handle.classList.remove('scrubbing');
    tooltip.classList.remove('show');
    const frac = scrubPos(e.changedTouches ? {clientX: e.changedTouches[0].clientX} : e);
    seekTo(frac);
  }

  ww.addEventListener('mousedown',  onDown);
  ww.addEventListener('touchstart', onDown, {passive:false});
  window.addEventListener('mousemove', e => { if (dragging) onMove(e); });
  window.addEventListener('touchmove', e => { if (dragging) onMove(e); }, {passive:false});
  window.addEventListener('mouseup',   onUp);
  window.addEventListener('touchend',  onUp);

  // Hover: mostrar tooltip sin arrastrar
  ww.addEventListener('mousemove', e => { if (!dragging && S.playing) onMove(e); });
  ww.addEventListener('mouseleave', () => { if (!dragging) tooltip.classList.remove('show'); });

  // Guardar referencia para que el loop sepa si está scrubbing
  S._dragging = () => dragging;
}

// ── Start ─────────────────────────────────────────────────────
document.getElementById('btnStart').addEventListener('click', async () => {
  ic();
  document.getElementById('idle').classList.add('off');
  document.getElementById('stage').classList.add('on');
  initClubVisuals();
  const first = chooseFirst();
  await begin(first);
});

function chooseFirst() {
  if (!S.lib.length) return null;
  // Warm-up: energía baja-media, primer cuartil
  const s = [...S.lib].sort((a,b)=>(a.energia||50)-(b.energia||50));
  return s[Math.floor(s.length * 0.18)] || s[0];
}

async function begin(t) {
  S.cur = t; S.curFile = t.file; S.deck = 'A';
  S.playing = true; S.startAt = 0;
  S.played.push(t.file); S.playedSet.add(t.file); S.count = 1;
  S.sessionStartTime = ctx.currentTime;
  S.sessionTracks = [{ track: t, startCtxTime: ctx.currentTime, color: trackColor(0) }];
  updateNP(t, 'warm-up');
  const startPos = t.start_position ?? 0;
  await playDeck('A', t, startPos);
  logMsg(`Iniciando desde ${fmt(startPos)}: ${t.name}`);
  document.getElementById('btnSkip').disabled = false;
  renderLib();
  renderTimeline();
  loop();
  askNext(t, 0);
}

// Botón de skip: salta directamente al mix (para testing)
document.getElementById('btnSkip').addEventListener('click', () => {
  if (!S.mixing && S.playing) doMix();
});

// ── CUE: preview de la siguiente pista ───────────────────────
// Reproduce 5s de la siguiente canción (desde puede_empezar_mezcla)
// en paralelo, en voz baja, para que el DJ pueda oírla.
// Pulsar de nuevo para parar.
document.getElementById('btnCue').addEventListener('click', async () => {
  if (!S.nxt) return;
  const btn = document.getElementById('btnCue');

  if (S.cueing) {
    // Parar cue
    if (S.cueSrc)  { try{S.cueSrc.stop();}catch(e){} S.cueSrc = null; }
    if (S.cueGain) { S.cueGain.gain.setValueAtTime(0, ctx.currentTime); }
    S.cueing = false;
    btn.classList.remove('cueing');
    btn.textContent = '👂 CUE';
    return;
  }

  // Cargar buffer
  try {
    const buf = await loadBuf(S.nxt);
    const enterAt = S.nxtPlan ? (S.nxtPlan.start_next_time || 0) : 0;
    const CUE_DUR = 8; // segundos de preview

    S.cueGain = ctx.createGain();
    S.cueGain.gain.setValueAtTime(0, ctx.currentTime);
    S.cueGain.gain.linearRampToValueAtTime(0.6, ctx.currentTime + 0.3);
    S.cueGain.connect(S.cueOutGain);

    S.cueSrc = ctx.createBufferSource();
    S.cueSrc.buffer = buf;
    S.cueSrc.connect(S.cueGain);
    S.cueSrc.start(0, enterAt);

    // Auto-fade y stop tras CUE_DUR segundos
    S.cueGain.gain.setValueAtTime(0.6, ctx.currentTime + CUE_DUR - 1);
    S.cueGain.gain.linearRampToValueAtTime(0, ctx.currentTime + CUE_DUR);
    S.cueSrc.stop(ctx.currentTime + CUE_DUR);
    S.cueSrc.onended = () => {
      S.cueing = false;
      btn.classList.remove('cueing');
      btn.textContent = '👂 CUE';
      S.cueSrc = null;
    };

    S.cueing = true;
    btn.classList.add('cueing');
    btn.textContent = '■ STOP';
    logMsg(`👂 Preview: ${S.nxt.name}`);
  } catch(e) {
    logMsg('Error cargando preview');
  }
});

// ── Ask server for next track ─────────────────────────────────
async function askNext(t, ct) {
  if (!t) return;
  try {
    const pe  = encodeURIComponent(JSON.stringify([...S.playedSet]));
    // Pasar las últimas 3 canciones con su key para anti-repetición de tonalidad
    const pl  = encodeURIComponent(JSON.stringify(
      S.played.slice(-3).map(f => ({ file: f, key: (S.lib.find(x=>x.file===f)||{}).key||'' }))
    ));
    const url = `/api/next?current=${encodeURIComponent(t.file)}&time=${ct.toFixed(1)}&played=${pe}&count=${S.count}&played_list=${pl}`;
    const d   = await (await fetch(url)).json();
    if (d.error) { S.nxt = null; hideNext(); return; }
    S.nxt = d.track; S.nxtPlan = d.plan; S.nxtScore = d.score; S.nxtPhase = d.phase;
    showNext(d.track, d.plan, d.score, d.phase);
    updateArc(d.phase, d.target_energy);
    preload(d.track);
    renderLib();
  } catch(e) {}
}

// ── Buffer cache ──────────────────────────────────────────────
async function loadBuf(t) {
  if (S.bufs[t.file]) return S.bufs[t.file];
  ic();
  const ab  = await (await fetch('/audio/'+encodeURIComponent(t.file))).arrayBuffer();
  const buf = await ctx.decodeAudioData(ab);
  return S.bufs[t.file] = buf;
}
async function preload(t) {
  if (!t || S.bufs[t.file]) return;
  try { ic(); await loadBuf(t); } catch(e) {}
}

// ── Create / reset deck audio graph ──────────────────────────
function resetGraph(dk) {
  const d = S.decks[dk];
  if (d.src)  { try{d.src.stop();}catch(e){} d.src = null; }

  // Recrear nodos (evita problemas con nodos usados)
  d.preGain  = ctx.createGain();
  d.hipass   = ctx.createBiquadFilter();
  d.lopass   = ctx.createBiquadFilter();
  d.analyser = ctx.createAnalyser();
  d.analyser.fftSize = 256;

  d.hipass.type = 'highpass';  d.hipass.Q.value = 0.71;
  d.lopass.type = 'lowpass';   d.lopass.Q.value = 0.71;

  // Chain: preGain → hipass → lopass → analyser → compressor
  d.preGain.connect(d.hipass);
  d.hipass.connect(d.lopass);
  d.lopass.connect(d.analyser);
  d.analyser.connect(S.comp);

  return d;
}

// ── Play a track on a deck ────────────────────────────────────
async function playDeck(dk, track, offset = 0) {
  const buf = await loadBuf(track);
  // Si la pista no tiene duración en el JSON, usar la del AudioBuffer
  // Esto garantiza que el trigger del mix funcione aunque no haya JSON
  if (!track.duracion_segundos || track.duracion_segundos === 0) {
    track.duracion_segundos = buf.duration;
  }
  const d   = resetGraph(dk);

  const src = ctx.createBufferSource();
  src.buffer = buf;

  // BPM matching: si la entrante tiene BPM distinto, empezar en el ratio
  // que la hace sonar al mismo tempo que la saliente, y programar un ramp
  // gradual a 1.0 para que al terminar el fade suene a su tempo original.
  if (dk !== S.deck && track.bpm && S.cur && S.cur.bpm && track.bpm > 0) {
    const ratio = S.cur.bpm / track.bpm;
    src.playbackRate.setValueAtTime(ratio, ctx.currentTime);
    // Guardar el ramp para cuando se conozca cfDur en doMix
    // (lo haremos desde doMix con d.src ya disponible)
    d._bpmRatio = ratio;
    d._bpmTarget = 1.0;
  } else {
    src.playbackRate.value = 1.0;
    d._bpmRatio  = 1.0;
    d._bpmTarget = 1.0;
  }

  src.connect(d.preGain);
  d.preGain.gain.setValueAtTime(dk === S.deck ? 1 : 0, ctx.currentTime);

  // Deck entrante: graves cortados hasta que la IA los abra (bass swap)
  d.hipass.frequency.setValueAtTime(dk === S.deck ? 20  : 320, ctx.currentTime);
  d.lopass.frequency.setValueAtTime(20000, ctx.currentTime);

  src.start(0, offset);
  d.src = src;

  // Guardar el momento de inicio de ESTE deck para poder calcular su tiempo
  d.startedAt = ctx.currentTime - offset;

  if (dk === S.deck) {
    S.startAt = d.startedAt;
    drawWave(buf, track);
  }

  src.onended = () => {
    if (S.playing && dk === S.deck && !S.mixing) doMix();
  };
}

function getTime() {
  return !S.playing || !ctx ? 0 : Math.max(0, ctx.currentTime - S.startAt);
}

// ════════════════════════════════════════════════════════════
//  D O M I X — Triple style: Guetta / Avicii / Progressive
//
//  GUETTA:
//    OUT: gain cóncava suavizada (pow 0.9)
//         lopass 20kHz→400Hz (mata agudos progresivamente)
//    IN:  sigmoide TARDÍA (aparece de golpe en el 65%)
//         hipass 320Hz→20Hz con bass swap abrupto en el 60%
//         → Drop percibido físicamente
//
//  AVICII:
//    OUT: gain coseno suave (sale en arco simétrico)
//         hipass 20Hz→800Hz (pierde graves gradualmente = "se va")
//    IN:  sigmoide TEMPRANA (empieza a oírse desde el 20%)
//         graves abiertos desde el principio
//         → La melodía de la entrante llega ANTES que el beat
//    Reverb: más pronunciado (0.35 vs 0.18)
//
//  PROGRESSIVE:
//    Equal-power puro: vOut=cos(f·π/2), vIn=sin(f·π/2)
//    → En cualquier punto del fade: vOut²+vIn²=1 (sin bajón matemático)
//    EQ neutro — sin highpass/lowpass agresivo
//    BPM casi idéntico → sin pitch shifting apreciable
//    Reverb mínimo (0.10)
//
//  FUSION:
//    Blend largo (32-38s): ambas canciones suenan juntas al ~80% vol
//    durante el 60% central del fade → se fusionan en una textura.
//    EQ complementario: saliente cede agudos, entrante cede graves.
//    Se activa ~35% de las veces cuando BPM diff ≤ 6.
//    Reverb medio (0.22)
// ════════════════════════════════════════════════════════════
async function doMix() {
  if (S.mixing || !S.playing) return;
  const nxt = S.nxt;
  if (!nxt) {
    askNext(S.cur, getTime());
    setTimeout(() => { if (!S.mixing && S.nxt) doMix(); }, 1200);
    return;
  }

  const plan    = S.nxtPlan;
  const cfDur   = plan ? (plan.mix_duration || 8) : 8;
  const enterAt = plan ? (plan.start_next_time || 0) : 0;
  const style   = plan ? (plan.style || 'guetta') : 'guetta';

  // Detener CUE si está activo antes de empezar la mezcla
  if (S.cueing && S.cueSrc) {
    try { S.cueSrc.stop(); } catch(e) {}
    S.cueSrc = null;
    S.cueing = false;
    document.getElementById('btnCue').classList.remove('cueing');
    document.getElementById('btnCue').textContent = '👂 CUE';
  }

  S.mixing   = true;
  S.mixStart = ctx.currentTime;
  S.mixDur   = cfDur;
  S.mixStyle = style;

  showMixing(nxt.name, cfDur, style);
  logMsg(`${STYLE_LABELS[style]||style} · ⇄ ${nxt.name} · ${cfDur.toFixed(0)}s`);

  // Reverb — Progressive casi nada, Avicii mucho, Guetta moderado
  if (S.reverb && S.reverbGain) {
    const reverbPeak = style === 'avicii' ? 0.35 : style === 'progressive' ? 0.10 : style === 'fusion' ? 0.22 : 0.18;
    const rg = S.reverbGain.gain;
    rg.cancelScheduledValues(ctx.currentTime);
    rg.setValueAtTime(0, ctx.currentTime);
    rg.linearRampToValueAtTime(reverbPeak,     ctx.currentTime + cfDur * 0.25);
    rg.linearRampToValueAtTime(reverbPeak*0.5, ctx.currentTime + cfDur * 0.75);
    rg.linearRampToValueAtTime(0,              ctx.currentTime + cfDur * 1.0);
  }

  const out = S.deck;
  const inp = out === 'A' ? 'B' : 'A';

  await playDeck(inp, nxt, enterAt);
  const inpStartedAt = ctx.currentTime - enterAt;

  const t0    = ctx.currentTime;
  const dOut  = S.decks[out];
  const dIn   = S.decks[inp];
  const steps = Math.round(cfDur * 30);

  // Anclar estado inicial
  dOut.preGain.gain.cancelScheduledValues(t0);
  dIn.preGain.gain.cancelScheduledValues(t0);
  dOut.hipass.frequency.cancelScheduledValues(t0);
  dOut.lopass.frequency.cancelScheduledValues(t0);
  dIn.hipass.frequency.cancelScheduledValues(t0);
  dIn.lopass.frequency.cancelScheduledValues(t0);

  dOut.preGain.gain.setValueAtTime(1,     t0);
  dIn.preGain.gain.setValueAtTime(0,      t0);
  dOut.lopass.frequency.setValueAtTime(20000, t0);
  dOut.hipass.frequency.setValueAtTime(20,    t0);
  dIn.lopass.frequency.setValueAtTime(20000, t0);

  if (style === 'progressive') {
    // EQ completamente neutro — las pistas suenan completas
    dIn.hipass.frequency.setValueAtTime(20, t0);
  } else if (style === 'avicii') {
    // Entrante empieza con graves abiertos — melodía llega primero
    dIn.hipass.frequency.setValueAtTime(20, t0);
  } else if (style === 'fusion') {
    // Fusion: ambas pistas suenan abiertas y equilibradas desde el inicio
    dIn.hipass.frequency.setValueAtTime(20, t0);
    dOut.hipass.frequency.setValueAtTime(20, t0);
  } else {
    // Guetta: graves de la entrante cortados hasta el bass swap
    dIn.hipass.frequency.setValueAtTime(320, t0);
  }

  // BPM ramp (solo Guetta/Avicii — Progressive tiene BPM casi igual)
  if (style !== 'progressive' && dIn.src && dIn._bpmRatio && dIn._bpmRatio !== 1.0) {
    dIn.src.playbackRate.cancelScheduledValues(t0);
    dIn.src.playbackRate.setValueAtTime(dIn._bpmRatio, t0);
    dIn.src.playbackRate.exponentialRampToValueAtTime(1.0, t0 + cfDur);
  }

  // ── Nodo de compensación de volumen (anti-bajón) ─────────────
  // Guetta/Avicii: las curvas no son equal-power → puede haber hueco.
  // Progressive: equal-power puro → sin hueco (pero lo dejamos activo
  // para uniformidad y por si el compresor pump).
  if (!S.compGain) {
    S.compGain = ctx.createGain();
    S.compGain.gain.value = 1;
    S.comp.disconnect(S.mAnl);
    S.comp.connect(S.compGain);
    S.compGain.connect(S.mAnl);
  }
  S.compGain.gain.cancelScheduledValues(t0);
  S.compGain.gain.setValueAtTime(1, t0);

  for (let i = 0; i <= steps; i++) {
    const f   = i / steps;
    const tAt = t0 + f * cfDur;

    let vOut, vIn;

    if (style === 'progressive') {
      // ── PROGRESSIVE: equal-power puro ──────────────────────
      // Garantía matemática: vOut²+vIn²=1 en todo momento.
      // No hay bajón posible — es la base del DJ mixing técnico.
      vOut = Math.cos(f * Math.PI / 2);
      vIn  = Math.sin(f * Math.PI / 2);

    } else if (style === 'fusion') {
      // ── FUSION: ambas pistas suenan casi al mismo volumen durante
      // la mayor parte del blend. Curva en forma de meseta:
      //   - Los primeros 20%: la entrante sube suavemente
      //   - Del 20% al 80%: las dos conviven casi al mismo nivel (~0.85)
      //     aplicando equal-power en esa zona para mantener energía
      //   - El último 20%: la saliente baja suavemente
      // El resultado es una superposición larga donde ambas canciones
      // se fusionan en una sola textura.
      if (f < 0.20) {
        vOut = 1.0;
        vIn  = Math.sin((f / 0.20) * Math.PI / 2);
      } else if (f < 0.80) {
        const mid = (f - 0.20) / 0.60;  // 0..1 en zona central
        vOut = Math.cos(mid * Math.PI / 2) * 0.3 + 0.7;   // 1.0 → 0.7
        vIn  = Math.sin(mid * Math.PI / 2) * 0.3 + 0.7;   // 0.7 → 1.0
      } else {
        const tail = (f - 0.80) / 0.20;
        vOut = Math.cos(tail * Math.PI / 2) * 0.7;
        vIn  = 1.0;
      }

    } else if (style === 'avicii') {
      // ── AVICII: fade simétrico tipo coseno con sigmoide temprana
      vOut = Math.pow(Math.cos(f * Math.PI / 2), 1.2);
      vIn  = 1 / (1 + Math.exp(-10 * (f - 0.35)));

    } else {
      // ── GUETTA: asimétrico, drop abrupto ───────────────────
      // OUT: cóncava suavizada — pow(0.9) mantiene volumen en la primera mitad
      vOut = Math.pow(1 - f, 0.9);
      // IN: sigmoide TARDÍA — aparece de golpe en el 65%
      vIn  = 1 / (1 + Math.exp(-16 * (f - 0.65)));
    }

    dOut.preGain.gain.setValueAtTime(Math.max(0, vOut), tAt);
    dIn.preGain.gain.setValueAtTime(Math.min(1, vIn),   tAt);

    // Gain de compensación: normaliza la potencia combinada a ≥ 1.
    // Progressive: power=1 siempre (sin ajuste necesario).
    // Guetta/Avicii: puede bajar — este nodo lo compensa.
    const power = Math.sqrt(vOut * vOut + vIn * vIn);
    const cGain = power > 0.01 ? Math.min(1.35, 1 / power) : 1;
    S.compGain.gain.setValueAtTime(cGain, tAt);

    if (style === 'progressive') {
      // EQ neutro: solo un leve lowpass a la saliente en la segunda mitad
      // para que no haya superposición de frecuencias altas que cause comb filtering
      const loFreq = f > 0.5 ? (20000 * Math.pow(8000/20000, (f-0.5)*2)) : 20000;
      dOut.lopass.frequency.setValueAtTime(Math.max(8000, loFreq), tAt);
      // Entrante: sin tocar nada — suena completa y limpia
      dIn.hipass.frequency.setValueAtTime(20, tAt);

    } else if (style === 'fusion') {
      // ── FUSION EQ: las dos pistas se complementan por frecuencias
      // En la zona central (20%-80%) se hace EQ complementario:
      //   - Saliente: graves plenos, agudos ligeramente reducidos
      //   - Entrante: agudos plenos, graves ligeramente reducidos
      // Esto evita acumulación de bajos y crea una mezcla más limpia
      // mientras las dos canciones suenan juntas.
      if (f < 0.20) {
        // Entrada: la entrante llega desde abajo, EQ neutro
        dOut.lopass.frequency.setValueAtTime(20000, tAt);
        dIn.hipass.frequency.setValueAtTime(20, tAt);
      } else if (f < 0.80) {
        // Zona de fusión: EQ complementario suave
        const mid = (f - 0.20) / 0.60;
        // Saliente: agudos se van reduciendo levemente
        const outLoFreq = 20000 * Math.pow(5000/20000, mid * 0.6);
        dOut.lopass.frequency.setValueAtTime(Math.max(5000, outLoFreq), tAt);
        // Entrante: hipass que desaparece rápido para dejar bajos limpios
        const inHpFreq = 80 * Math.pow(20/80, Math.min(1, mid * 2));
        dIn.hipass.frequency.setValueAtTime(Math.max(20, inHpFreq), tAt);
      } else {
        // Salida: saliente pierde agudos completamente
        const tail = (f - 0.80) / 0.20;
        const outLoFreq = 5000 * Math.pow(400/5000, tail);
        dOut.lopass.frequency.setValueAtTime(Math.max(400, outLoFreq), tAt);
        dIn.hipass.frequency.setValueAtTime(20, tAt);
      }

    } else if (style === 'avicii') {
      // OUT lopass: mantiene cuerpo hasta el final
      const loFreq = 20000 * Math.pow(800/20000, Math.pow(f, 1.4));
      dOut.lopass.frequency.setValueAtTime(Math.max(700, loFreq), tAt);
      // OUT hipass: pierde graves gradualmente ("se va")
      const outHpFreq = 20 * Math.pow(600/20, Math.pow(f, 1.8));
      dOut.hipass.frequency.setValueAtTime(Math.min(600, outHpFreq), tAt);
      // IN hipass: ya abierto, desaparece rápido
      const inHpFreq = 80 * Math.pow(20/80, Math.pow(f * 2, 1.5));
      dIn.hipass.frequency.setValueAtTime(Math.max(20, inHpFreq), tAt);

    } else {
      // GUETTA EQ
      // OUT lopass: agudos mueren progresivamente
      const loFreq = 20000 * Math.pow(500/20000, Math.pow(f, 0.7));
      dOut.lopass.frequency.setValueAtTime(Math.max(400, loFreq), tAt);
      // IN hipass: bass swap abrupto en el 60%
      let hpFreq;
      if (f < 0.60) {
        hpFreq = 320 * Math.pow(200/320, f/0.60);
      } else {
        const bassF = (f - 0.60) / 0.40;
        hpFreq = 200 * Math.pow(20/200, Math.pow(bassF, 1.5));
      }
      dIn.hipass.frequency.setValueAtTime(Math.max(20, hpFreq), tAt);
    }
  }

  // A mitad del fade: actualizar UI
  setTimeout(async () => {
    updateNP(nxt, S.nxtPhase);
    if (S.bufs[nxt.file]) drawWave(S.bufs[nxt.file], nxt);
  }, cfDur * 500);

  // Al final del fade: cambiar deck activo
  setTimeout(async () => {
    S.deck    = inp;
    S.startAt = inpStartedAt;
    S.cur  = nxt; S.curFile = nxt.file;
    S.played.push(nxt.file); S.playedSet.add(nxt.file); S.count++;
    S.nxt  = null; S.nxtPlan = null;
    S.sessionTracks.push({
      track: nxt,
      startCtxTime: inpStartedAt,
      color: trackColor(S.sessionTracks.length)
    });
    document.getElementById('btnCue').disabled = true;
    await askNext(nxt, getTime());
    renderLib();
    renderTimeline();
  }, cfDur * 950);

  // Fin: apagar deck saliente limpiamente
  setTimeout(() => {
    const dO = S.decks[out];
    if (dO.preGain) {
      dO.preGain.gain.cancelScheduledValues(ctx.currentTime);
      dO.preGain.gain.setValueAtTime(0, ctx.currentTime);
    }
    if (dO.src) { try{dO.src.stop();}catch(e){} dO.src = null; }
    if (dO.hipass) dO.hipass.frequency.setValueAtTime(20,    ctx.currentTime);
    if (dO.lopass) dO.lopass.frequency.setValueAtTime(20000, ctx.currentTime);

    // Volver el gain de compensación a 1 limpiamente
    if (S.compGain) {
      S.compGain.gain.cancelScheduledValues(ctx.currentTime);
      S.compGain.gain.linearRampToValueAtTime(1, ctx.currentTime + 0.3);
    }

    S.mixing           = false;
    S.silenceStart     = null;
    S.silenceTriggered = false;
    hideMixing();
    hideEQ();
    logMsg(`Reproduciendo: ${S.cur.name}`);
  }, cfDur * 1000 + 250);
}

// ── Animation loop ────────────────────────────────────────────
function loop() {
  requestAnimationFrame(loop);
  if (!S.playing || !ctx) return;

  const t   = getTime();
  const dur = S.cur ? (S.cur.duracion_segundos || 0) : 0;

  // Mix progress bar (oculto, solo para compat)
  if (S.mixing) {
    const pct = Math.min(100, ((ctx.currentTime - S.mixStart) / S.mixDur) * 100);
    const mf = document.getElementById('mixFill');
    if(mf) mf.style.width = pct + '%';
    updateEQVisual(pct / 100);
  }

  // ── Trigger del mix ─────────────────────────────────────────
  // No disparar mientras el usuario está arrastrando el playhead
  if (!S.mixing && S.nxt && dur > 0 && !(S._dragging && S._dragging())) {
    const cf         = S.nxtPlan ? (S.nxtPlan.mix_duration || 8) : 8;
    const puedeSalir = S.cur ? (parseFloat(S.cur.puede_salir) || 0) : 0;
    const planExit   = S.nxtPlan ? (parseFloat(S.nxtPlan.exit_at) || 0) : 0;

    let trig;
    if (puedeSalir > 0) {
      trig = puedeSalir - cf;
    } else if (planExit > 0) {
      trig = planExit - cf;
    } else {
      trig = dur - cf - 2;
    }
    trig = Math.max(trig, dur * 0.73);

    // Beat-snapping: si el trigger está a menos de 1 beat de distancia,
    // esperar al beat más cercano para arrancar alineado con el ritmo.
    // Usa los beat_times del JSON si están disponibles.
    if (t >= trig - 0.5 && t < trig + 2.5 && !S._beatSnapScheduled) {
      S._beatSnapScheduled = true;
      const beatTimes = S.cur ? (S.cur.beat_times || []) : [];
      let snapTarget = trig;

      if (beatTimes.length > 0) {
        // Encontrar el beat más próximo dentro de ±1.5s del trigger ideal
        let bestDist = 9999, bestBeat = trig;
        for (const bt of beatTimes) {
          const dist = Math.abs(bt - trig);
          if (dist < bestDist && dist < 1.5) { bestDist = dist; bestBeat = bt; }
        }
        snapTarget = bestBeat;
      }

      const delay = Math.max(0, (snapTarget - t) * 1000);
      setTimeout(() => {
        S._beatSnapScheduled = false;
        if (!S.mixing && S.nxt) doMix();
      }, delay);
    }
  }

  // Refrescar plan cada 20s para mantenerlo actualizado
  if (!S.mixing && S.cur && S.nxt && Math.round(t) % 20 === 0 && t > 8) {
    askNext(S.cur, t);
  }

  // ── Update timeline playhead ─────────────────────────────────
  if (S.playing && S.sessionTracks.length > 0) {
    const elapsed = ctx.currentTime - S.sessionStartTime;
    const totalEst = S.sessionTracks.reduce((acc, st) => {
      return acc + (st.track.duracion_segundos || 180);
    }, 0);
    const pct = Math.min(99, (elapsed / Math.max(totalEst, 1)) * 100);
    const tlHead = document.getElementById('tlHead');
    if (tlHead) tlHead.style.left = pct + '%';
  }

  // ── Detección de silencio / caída de canción ─────────────────
  if (!S.mixing && S.playing && t > 5 && !(S._dragging && S._dragging())) {
    const dk = S.decks[S.deck];
    if (dk && dk.analyser) {
      const buf = new Uint8Array(dk.analyser.frequencyBinCount);
      dk.analyser.getByteFrequencyData(buf);
      // RMS normalizado 0-1
      let sum = 0;
      for (let i = 0; i < buf.length; i++) sum += (buf[i]/255) * (buf[i]/255);
      const rms = Math.sqrt(sum / buf.length);

      const SILENCE_THRESHOLD = 0.03;   // por debajo de esto = silencio percibido
      const SILENCE_MS        = 1800;   // debe durar 1.8s para confirmar
      const MIN_PROGRESS      = 0.30;   // ignorar antes del 30% de la canción

      const progress = dur > 0 ? t / dur : 0;

      if (rms < SILENCE_THRESHOLD && progress > MIN_PROGRESS && !S.silenceTriggered) {
        if (S.silenceStart === null) {
          S.silenceStart = ctx.currentTime;
        } else if ((ctx.currentTime - S.silenceStart) * 1000 > SILENCE_MS) {
          // ¡Silencio confirmado! Saltar al siguiente
          S.silenceTriggered = true;
          S.silenceStart     = null;
          logMsg('⚡ Silencio detectado — saltando');
          doMix();
        }
      } else if (rms >= SILENCE_THRESHOLD) {
        // Señal volvió — resetear contador
        S.silenceStart     = null;
        S.silenceTriggered = false;
      }
    }
  }

  drawViz();
}

// ── EQ visual durante el mix ──────────────────────────────────
function updateEQVisual(frac) {
  // frac 0→1 durante el crossfade
  // Muestra lo que el EQ está haciendo a la pista saliente
  const hiPct  = Math.max(0, (1 - Math.pow(frac / 0.8, 0.6)) * 100);
  const midPct = Math.max(0, (1 - Math.pow(frac / 0.9, 0.8)) * 100);
  const loPct  = Math.max(0, (1 - Math.pow(frac / 1.0, 1.2)) * 100);
  document.getElementById('eqHi').style.width  = hiPct + '%';
  document.getElementById('eqMid').style.width = midPct + '%';
  document.getElementById('eqLo').style.width  = loPct + '%';
}

function hideEQ() {
  document.getElementById('eqRow').classList.remove('on');
  document.getElementById('eqHi').style.width  = '100%';
  document.getElementById('eqMid').style.width = '100%';
  document.getElementById('eqLo').style.width  = '100%';
}

// ── UI helpers ────────────────────────────────────────────────
function updateNP(t, phase) {
  // HUD visible
  const titleEl = document.getElementById('npTitle');
  if(titleEl) titleEl.textContent = t.name;
  const bpmEl = document.getElementById('npBpm');
  if(bpmEl) bpmEl.textContent = t.bpm ? t.bpm.toFixed(1)+' BPM' : '';
  const durEl = document.getElementById('npDur');
  if(durEl) durEl.textContent = t.duracion_segundos ? fmt(t.duracion_segundos) : '';
  const keyEl = document.getElementById('npKey');
  if(keyEl){ if(t.key){keyEl.textContent=t.key;keyEl.style.display='inline';}else keyEl.style.display='none'; }
  const estiloEl = document.getElementById('npEstilo');
  if(estiloEl){ if(t.estilo){estiloEl.textContent=t.estilo;estiloEl.style.display='inline';}else estiloEl.style.display='none'; }

  // BPM box (oculto, compat)
  const bv = document.getElementById('bpmVal');
  if(bv) bv.textContent = t.bpm ? Math.round(t.bpm) : '—';

  // Phase pill HUD
  const pill = document.getElementById('phasePill');
  const p = phase || S.nxtPhase || 'warm-up';
  if(pill){ pill.textContent = PHASE_LABELS[p]||p; pill.setAttribute('class','pill-'+p); }

  // EQ visual reset
  const egyEl = document.getElementById('npEgy');
  if(egyEl) egyEl.textContent = t.energia ? 'E'+t.energia : '';

  // Like/dislike state
  updateLikeUI(t.file);
}

function updateArc(phase, targetE) {
  const idx = PHASE_ORDER.indexOf(phase);
  const pct = idx < 0 ? 0 : (idx / (PHASE_ORDER.length-1)) * 100;
  document.getElementById('arcCursor').style.left  = pct + '%';
  document.getElementById('arcPhase').textContent  = (PHASE_LABELS[phase]||phase) + ' · E→' + Math.round(targetE);
}

function showNext(t, plan, score, phase) {
  document.getElementById('nxtRow').style.display = 'flex';
  document.getElementById('nxtNm').textContent    = t.name;
  document.getElementById('nxtSc').textContent    = 'Score ' + Math.round(score);
  const style  = plan ? (plan.style || 'guetta') : 'guetta';
  const sLabel = STYLE_ICONS[style] || '⚡';
  const timing = plan
    ? `${sLabel} ${style.toUpperCase()} · ${(plan.mix_duration||8).toFixed(0)}s fade`
    : '';
  document.getElementById('nxtT').textContent = timing;
  document.getElementById('btnCue').disabled = false;
}
function hideNext() { document.getElementById('nxtRow').style.display = 'none'; }

function showMixing(name, dur, style) {
  // Panel oculto (compat JS)
  const row = document.getElementById('mixRow');
  if(row){ row.classList.add('on'); row.classList.remove('style-guetta','style-avicii','style-progressive','style-fusion'); row.classList.add('style-'+(style||'guetta')); }
  const lbl = document.getElementById('mixStyleLabel');
  if(lbl) lbl.textContent = STYLE_LABELS[style]||'⚡';
  const mi = document.getElementById('mixInfo');
  if(mi) mi.textContent = `→ ${name} · ${dur.toFixed(0)}s`;
  const mf = document.getElementById('mixFill');
  if(mf) mf.style.width = '0%';
  const eq = document.getElementById('eqRow');
  if(eq) eq.classList.add('on');

  // HUD visible
  const ind = document.getElementById('mixIndicator');
  const mlb = document.getElementById('mixLabel');
  if(ind && mlb){
    ind.className = 'on style-'+(style||'guetta');
    mlb.textContent = (STYLE_LABELS[style]||'MIX').replace(/^.+\s/,''); // solo la palabra
  }
}
function hideMixing() {
  const row = document.getElementById('mixRow');
  if(row) row.classList.remove('on');
  const ind = document.getElementById('mixIndicator');
  if(ind) ind.className = '';
}

// ── Like / Dislike ────────────────────────────────────────────
// S.prefs: {filename: 1||-1}  cargado al arrancar y actualizado en vivo
S.prefs = {};

async function loadPrefs() {
  try {
    const r = await fetch('/api/prefs');
    S.prefs = await r.json();
  } catch(e) {}
}

async function sendLike(action) {
  if (!S.cur) return;
  const file = S.cur.file;
  // Toggle: si ya tiene esa acción, la borra (clear)
  const current = S.prefs[file];
  const sendAction = (action === 'like' && current === 1) || (action === 'dislike' && current === -1)
    ? 'clear' : action;

  try {
    await fetch('/api/like', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ file, action: sendAction })
    });
    if (sendAction === 'like')    S.prefs[file] = 1;
    else if (sendAction === 'dislike') S.prefs[file] = -1;
    else delete S.prefs[file];
    updateLikeUI(file);
    // Feedback visual breve en el título
    const titleEl = document.getElementById('npTitle');
    if (titleEl) {
      const orig = titleEl.textContent;
      titleEl.textContent = sendAction === 'like' ? '👍 ¡Guardado!' : sendAction === 'dislike' ? '👎 Anotado' : '✓ Borrado';
      setTimeout(() => { titleEl.textContent = orig; }, 1400);
    }
  } catch(e) {}
}

function updateLikeUI(file) {
  const pref = S.prefs[file] || 0;
  const bl = document.getElementById('btnLike');
  const bd = document.getElementById('btnDislike');
  if (bl) { bl.classList.toggle('active-like', pref === 1); }
  if (bd) { bd.classList.toggle('active-dislike', pref === -1); }
}

function renderLib() {
  const list = document.getElementById('tlist');
  if (!S.lib.length) {
    list.innerHTML = '<div class="empty"><p>Pon MP3/WAV en <code>musica/canciones/</code></p></div>';
    return;
  }
  const cBpm = S.cur ? (S.cur.bpm||0) : 0;
  list.innerHTML = S.lib.map((t,i) => {
    const iC   = t.file === S.curFile;
    const iN   = S.nxt && t.file === S.nxt.file;
    const done = !iC && S.playedSet.has(t.file);
    const bOk  = !cBpm || !t.bpm || Math.abs(t.bpm-cBpm) <= 10;
    const sc   = iN ? Math.round(S.nxtScore) : null;
    const sC   = sc===null ? '' : sc>70?'hi':sc>40?'mi':'lo';
    return `<div class="tk ${iC?'cur':''} ${iN?'nxt':''} ${done?'done':''}">
      <div class="tn">${iC?'▶':iN?'→':done?'✓':i+1}</div>
      <div class="tt">${t.name}${t.estilo?` <span class="tk-estilo">${t.estilo}</span>`:''}</div>
      <div class="te"><div class="tef" style="width:${t.energia||50}%"></div></div>
      <div class="tb ${bOk?'ok':'no'}">${t.bpm?t.bpm.toFixed(0)+'bpm':'—'}</div>
      <div class="ts ${sC}">${sc!==null?sc:'—'}</div>
      <div class="td">${t.duracion_segundos?fmt(t.duracion_segundos):'—'}</div>
      <div class="tpref">${(S.prefs[t.file]===1)?'👍':(S.prefs[t.file]===-1)?'👎':''}</div>
    </div>`;
  }).join('');
}

// ── Waveform ──────────────────────────────────────────────────
function drawWave(buf, track) {
  const c = document.getElementById('wc'), dpr = devicePixelRatio||1;
  c.width = c.offsetWidth*dpr; c.height = c.offsetHeight*dpr;
  const g = c.getContext('2d'); g.scale(dpr,dpr);
  const W=c.offsetWidth, H=c.offsetHeight, mid=H/2;
  const data=buf.getChannelData(0), step=Math.ceil(data.length/W);
  g.clearRect(0,0,W,H);

  // Gradiente que refleja la energía de la canción
  const gr = g.createLinearGradient(0,0,W,0);
  gr.addColorStop(0,  'rgba(200,255,0,.08)');
  gr.addColorStop(.4, 'rgba(200,255,0,.65)');
  gr.addColorStop(.6, 'rgba(0,240,255,.55)');
  gr.addColorStop(1,  'rgba(200,255,0,.08)');
  g.strokeStyle = gr; g.lineWidth = 1; g.beginPath();
  for(let i=0;i<W;i++){
    let mn=1,mx=-1;
    for(let j=0;j<step;j++){const v=data[i*step+j]||0;if(v<mn)mn=v;if(v>mx)mx=v;}
    g.moveTo(i,mid+mn*mid); g.lineTo(i,mid+mx*mid);
  }
  g.stroke();

  if(!track) return;
  const dur = track.duracion_segundos || buf.duration;

  // Zona de entrada permitida (azul)
  if(track.puede_empezar_mezcla) {
    const x1=(track.puede_empezar_mezcla/dur)*W;
    const x2=track.debe_sonar_sola?(track.debe_sonar_sola/dur)*W:W;
    g.fillStyle='rgba(0,240,255,.04)'; g.fillRect(x1,0,x2-x1,H);
    g.strokeStyle='rgba(0,240,255,.18)'; g.lineWidth=1;
    g.beginPath();g.moveTo(x1,0);g.lineTo(x1,H);g.stroke();
    if(track.debe_sonar_sola){g.beginPath();g.moveTo(x2,0);g.lineTo(x2,H);g.stroke();}
  }
  // Punto de salida (rojo)
  if(track.puede_salir){
    const xo=(track.puede_salir/dur)*W;
    g.strokeStyle='rgba(255,59,92,.35)'; g.lineWidth=1;
    g.beginPath();g.moveTo(xo,0);g.lineTo(xo,H);g.stroke();
    // Pequeño triángulo marcador
    g.fillStyle='rgba(255,59,92,.5)';
    g.beginPath();g.moveTo(xo-3,0);g.lineTo(xo+3,0);g.lineTo(xo,5);g.fill();
  }
}

// ══════════════════════════════════════════════════════════════
//  NEXUS VISUALS — visualizador galáctico
// ══════════════════════════════════════════════════════════════
const CV = {
  particles: [], stars: [],
  beatEnergy: 0, smoothEnergy: 0,
  hue: 270, targetHue: 270,
  rotation: 0, lastBeat: 0, beamAngle: 0, nebulaPulse: 0,
};

function initClubVisuals() {
  const pm = document.getElementById('vizMain');
  const pp = document.getElementById('particles');
  function resize() {
    pm.width = pp.width = window.innerWidth*(devicePixelRatio||1);
    pm.height= pp.height= window.innerHeight*(devicePixelRatio||1);
    pm.style.width = pp.style.width = window.innerWidth+'px';
    pm.style.height= pp.style.height= window.innerHeight+'px';
  }
  window.addEventListener('resize', resize); resize();
  for(let i=0;i<220;i++) CV.stars.push(mkStar());
  for(let i=0;i<60;i++) CV.particles.push(mkParticle(false));
}

function mkStar(){
  const W=window.innerWidth, H=window.innerHeight;
  return{x:Math.random()*W,y:Math.random()*H,size:Math.pow(Math.random(),3)*2.5+0.3,
    brightness:Math.random(),twinkle:Math.random()*Math.PI*2,
    twinkleSpeed:0.02+Math.random()*0.04,hue:220+Math.random()*120};
}

function mkParticle(fromBeat){
  const W=window.innerWidth, H=window.innerHeight;
  const angle=Math.random()*Math.PI*2;
  const speed=fromBeat?3+Math.random()*5:0.2+Math.random()*0.6;
  return{x:fromBeat?W/2+(Math.random()-.5)*120:Math.random()*W,
    y:fromBeat?H*.5+(Math.random()-.5)*120:Math.random()*H,
    vx:Math.cos(angle)*speed*(fromBeat?1:.3),
    vy:Math.sin(angle)*speed*(fromBeat?1:.3)-(fromBeat?1:.1),
    life:1,decay:fromBeat?.015+Math.random()*.015:.002+Math.random()*.003,
    size:fromBeat?Math.random()*5+2:Math.random()*1.8+.4,
    hue:250+Math.random()*80,sat:fromBeat?100:60+Math.random()*40,beat:!!fromBeat};
}

function drawViz(){
  if(!S.playing||!ctx) return;
  const pm=document.getElementById('vizMain');
  const pp=document.getElementById('particles');
  if(!pm||!pp) return;
  const dpr=devicePixelRatio||1;
  const W=pm.width/dpr, H=pm.height/dpr;
  const gm=pm.getContext('2d'), gp=pp.getContext('2d');
  gm.setTransform(dpr,0,0,dpr,0,0);
  gp.setTransform(dpr,0,0,dpr,0,0);

  const dk=S.decks[S.deck];
  let freqData=null,subE=0,midE=0,hiE=0,avgE=0;
  if(dk&&dk.analyser){
    freqData=new Uint8Array(dk.analyser.frequencyBinCount);
    dk.analyser.getByteFrequencyData(freqData);
    const n=freqData.length;
    for(let i=0;i<n;i++){
      const v=freqData[i]/255; avgE+=v;
      if(i<n*.08) subE+=v; else if(i<n*.35) midE+=v; else hiE+=v;
    }
    avgE/=n; subE/=n*.08; midE/=n*.27; hiE/=n*.65;
  }
  CV.smoothEnergy+=(avgE-CV.smoothEnergy)*.10;
  CV.beatEnergy+=(subE-CV.beatEnergy)*.20;
  CV.nebulaPulse+=.008;

  S.beatHistory.push(subE);
  if(S.beatHistory.length>25) S.beatHistory.shift();
  const avgHist=S.beatHistory.reduce((a,b)=>a+b,0)/S.beatHistory.length;
  const now=ctx.currentTime;
  const isBeat=subE>avgHist*1.5&&subE>.18&&(now-S.beatLastTime)>.18&&S.playing;
  if(isBeat){
    S.beatLastTime=now; CV.lastBeat=now;
    for(let i=0;i<28;i++) CV.particles.push(mkParticle(true));
    const title=document.getElementById('npTitle');
    if(title){title.classList.add('beat-pulse');setTimeout(()=>title.classList.remove('beat-pulse'),130);}
    const bd=document.getElementById('beatDot');
    if(bd){bd.classList.add('flash');setTimeout(()=>bd.classList.remove('flash'),80);}
  }

  const phaseHues={'warm-up':220,'first-build':260,'first-peak':285,
    'breakdown':190,'second-build':265,'second-peak':295,'outro':240};
  CV.targetHue=phaseHues[S.nxtPhase||'warm-up']||270;
  CV.hue+=(CV.targetHue-CV.hue)*.008;

  const cx=W/2, cy=H/2;
  const beatAge=now-CV.lastBeat;

  // Fondo espacio
  gm.fillStyle=`rgba(0,0,${Math.round(3+CV.smoothEnergy*6)},${.18+CV.smoothEnergy*.05})`;
  gm.fillRect(0,0,W,H);

  // Nebula
  const np=CV.nebulaPulse;
  const nr1=gm.createRadialGradient(cx+Math.sin(np*.7)*W*.15,cy+Math.cos(np*.5)*H*.15,0,cx+Math.sin(np*.7)*W*.15,cy+Math.cos(np*.5)*H*.15,Math.min(W,H)*.55);
  nr1.addColorStop(0,`hsla(${CV.hue},80%,22%,${.06+CV.smoothEnergy*.08})`);
  nr1.addColorStop(1,'transparent');
  gm.fillStyle=nr1; gm.fillRect(0,0,W,H);
  const nr2=gm.createRadialGradient(cx+Math.cos(np*.4)*W*.2,cy+Math.sin(np*.6)*H*.2,0,cx+Math.cos(np*.4)*W*.2,cy+Math.sin(np*.6)*H*.2,Math.min(W,H)*.38);
  nr2.addColorStop(0,`hsla(${CV.hue+45},90%,18%,${.05+CV.smoothEnergy*.05})`);
  nr2.addColorStop(1,'transparent');
  gm.fillStyle=nr2; gm.fillRect(0,0,W,H);

  // Estrellas
  for(const s of CV.stars){
    s.twinkle+=s.twinkleSpeed+CV.smoothEnergy*.02;
    const b=s.brightness*(.5+.5*Math.sin(s.twinkle));
    const g2=b*(.4+CV.beatEnergy*.6);
    gm.fillStyle=`hsla(${s.hue},60%,${85+b*15}%,${b*.9})`;
    gm.beginPath(); gm.arc(s.x,s.y,s.size*(.8+g2*.5),0,Math.PI*2); gm.fill();
    if(b>.7&&s.size>1){
      gm.fillStyle=`hsla(${s.hue},80%,90%,${b*.18})`;
      gm.beginPath(); gm.arc(s.x,s.y,s.size*2.8,0,Math.PI*2); gm.fill();
    }
  }

  // Visualizador
  if(freqData){
    const isPeak=S.nxtPhase==='first-peak'||S.nxtPhase==='second-peak';
    CV.rotation+=.003+CV.smoothEnergy*.012;
    if(isPeak){
      // Corona orbital
      const bins=freqData.length, step=Math.PI*2/bins;
      const baseR=Math.min(W,H)*.18*(1+CV.smoothEnergy*.2);
      gm.save(); gm.translate(cx,cy);
      gm.strokeStyle=`hsla(${CV.hue},80%,60%,${.08+CV.beatEnergy*.12})`; gm.lineWidth=1;
      gm.beginPath(); gm.arc(0,0,baseR,0,Math.PI*2); gm.stroke();
      for(let i=0;i<bins;i++){
        const v=freqData[i]/255; if(v<.04) continue;
        const ang=step*i+CV.rotation;
        const r0=baseR, r1=r0+v*Math.min(W,H)*.3*(1+CV.smoothEnergy*.3);
        const h=CV.hue+(i/bins)*60-30;
        gm.strokeStyle=`hsla(${h},100%,${50+v*35}%,${.5+v*.5})`;
        gm.lineWidth=1+v*2.5;
        gm.beginPath();
        gm.moveTo(Math.cos(ang)*r0,Math.sin(ang)*r0);
        gm.lineTo(Math.cos(ang)*r1,Math.sin(ang)*r1);
        gm.stroke();
      }
      const core=gm.createRadialGradient(0,0,0,0,0,baseR*.55);
      core.addColorStop(0,`hsla(${CV.hue},100%,88%,${.1+CV.beatEnergy*.22})`);
      core.addColorStop(1,'transparent');
      gm.fillStyle=core; gm.beginPath(); gm.arc(0,0,baseR*.55,0,Math.PI*2); gm.fill();
      gm.restore();
    } else {
      // Barras espectrales simétricas
      const bins=freqData.length, bw=W/bins*1.5, mirror=W/2;
      for(let i=0;i<bins;i++){
        const v=freqData[i]/255;
        const bh=v*H*.55*(1+CV.smoothEnergy*.35);
        if(bh<1) continue;
        const xL=mirror-i*bw-bw, xR=mirror+i*bw;
        const h=CV.hue+(i/bins)*50;
        const l=40+v*45, a=.25+v*.75;
        const grad=gm.createLinearGradient(0,H,0,H-bh);
        grad.addColorStop(0,`hsla(${h},80%,${l*.6}%,${a*.3})`);
        grad.addColorStop(.65,`hsla(${h},100%,${l}%,${a})`);
        grad.addColorStop(1,`hsla(${h+20},100%,${l+20}%,${Math.min(1,a*1.3)})`);
        gm.fillStyle=grad;
        gm.fillRect(xL,H-bh,bw-.5,bh); gm.fillRect(xR,H-bh,bw-.5,bh);
        if(v>.45){
          const tp=(v-.45)*1.8;
          gm.fillStyle=`rgba(255,255,255,${tp*.7})`;
          gm.fillRect(xL,H-bh-2,bw-.5,3); gm.fillRect(xR,H-bh-2,bw-.5,3);
        }
        gm.fillStyle=`hsla(${h},80%,${l}%,${a*.055})`;
        gm.fillRect(xL,H,bw-.5,-bh*.22); gm.fillRect(xR,H,bw-.5,-bh*.22);
      }
    }
  }

  // Haces de luz
  CV.beamAngle+=.005+CV.smoothEnergy*.018;
  for(let b=0;b<4;b++){
    const ang=CV.beamAngle+b*Math.PI*.5;
    const h=CV.hue+b*35;
    const beam=gm.createLinearGradient(cx,cy,cx+Math.cos(ang)*W,cy+Math.sin(ang)*H);
    beam.addColorStop(0,`hsla(${h},100%,70%,${.05+CV.smoothEnergy*.07})`);
    beam.addColorStop(.5,`hsla(${h},90%,55%,${.02+CV.smoothEnergy*.03})`);
    beam.addColorStop(1,'transparent');
    gm.fillStyle=beam;
    const w2=.03+CV.smoothEnergy*.02;
    gm.beginPath(); gm.moveTo(cx,cy);
    gm.lineTo(cx+Math.cos(ang-w2)*W*1.3,cy+Math.sin(ang-w2)*H*1.3);
    gm.lineTo(cx+Math.cos(ang+w2)*W*1.3,cy+Math.sin(ang+w2)*H*1.3);
    gm.closePath(); gm.fill();
  }

  // Ondas beat
  if(beatAge<1.4){
    const t2=beatAge/1.4;
    for(let r=0;r<3;r++){
      const td=Math.max(0,t2-r*.08);
      gm.strokeStyle=`hsla(${CV.hue+r*25},100%,78%,${(1-td)*.4})`;
      gm.lineWidth=(1-td)*3;
      gm.beginPath(); gm.arc(cx,cy,td*Math.min(W,H)*.6,0,Math.PI*2); gm.stroke();
    }
  }

  // Glow central beat
  if(beatAge<.35){
    const bf=1-beatAge/.35;
    const bgr=gm.createRadialGradient(cx,cy,0,cx,cy,Math.min(W,H)*.42);
    bgr.addColorStop(0,`hsla(${CV.hue},100%,85%,${bf*.28})`);
    bgr.addColorStop(.5,`hsla(${CV.hue+20},90%,60%,${bf*.09})`);
    bgr.addColorStop(1,'transparent');
    gm.fillStyle=bgr; gm.fillRect(0,0,W,H);
  }

  // Partículas
  gp.clearRect(0,0,W,H);
  CV.particles=CV.particles.filter(p=>p.life>0);
  for(const p of CV.particles){
    p.x+=p.vx; p.y+=p.vy;
    p.vy+=p.beat?-.03:.012; p.vx*=.98; p.vy*=.99;
    p.life-=p.decay;
    const a=p.life*(p.beat?.92:.38);
    if(p.beat&&p.size>2){
      gp.fillStyle=`hsla(${p.hue},${p.sat}%,82%,${a*.18})`;
      gp.beginPath(); gp.arc(p.x,p.y,p.size*p.life*2.8,0,Math.PI*2); gp.fill();
    }
    gp.fillStyle=`hsla(${p.hue},${p.sat}%,75%,${a})`;
    gp.beginPath(); gp.arc(p.x,p.y,p.size*p.life,0,Math.PI*2); gp.fill();
  }
  while(CV.particles.length<80) CV.particles.push(mkParticle(false));
}
function logMsg(m) { document.getElementById('log').textContent = m; }

// ── Track color palette ───────────────────────────────────────
function trackColor(idx) {
  const palette = [
    'rgba(200,255,0',    // verde lima
    'rgba(0,240,255',    // cyan
    'rgba(176,96,255',   // violeta
    'rgba(255,149,0',    // naranja
    'rgba(255,59,92',    // rojo
    'rgba(0,255,180',    // verde agua
    'rgba(255,220,0',    // amarillo
    'rgba(80,160,255',   // azul
  ];
  return palette[idx % palette.length];
}

// ── Timeline de sesión ────────────────────────────────────────
function renderTimeline() {
  const wrap = document.getElementById('tlWrap');
  if (!wrap || !S.sessionTracks.length) return;
  wrap.style.display = 'block';

  const blocks  = document.getElementById('tlBlocks');
  const labels  = document.getElementById('tlLabels');
  const tlDur   = document.getElementById('tlDur');

  // Calcular duración total estimada de la sesión
  const durations = S.sessionTracks.map(st => st.track.duracion_segundos || 180);
  const total     = durations.reduce((a,b)=>a+b, 0);

  // Render bloques
  blocks.innerHTML = S.sessionTracks.map((st, i) => {
    const dur  = st.track.duracion_segundos || 180;
    const pct  = (dur / total * 100).toFixed(2);
    const isCur = st.track.file === S.curFile;
    const isDone = !isCur && i < S.sessionTracks.length - 1;
    const e    = st.track.energia || 50;
    const col  = st.color;
    // Altura de la barra proporcional a la energía
    const hPct = 30 + e * 0.7;
    return `<div class="tl-block ${isCur?'playing':''} ${isDone?'done':'future'}"
      style="width:${pct}%;background:${col},.08)"
      title="${st.track.name}"
      onclick="tlSeek(${i})">
      <div style="position:absolute;bottom:0;left:0;right:0;height:${hPct}%;
        background:${col},.4);border-radius:2px 2px 0 0;pointer-events:none"></div>
    </div>`;
  }).join('');

  // Labels debajo (nombre truncado, solo algunas)
  let leftPct = 0;
  labels.innerHTML = S.sessionTracks.map((st, i) => {
    const dur = st.track.duracion_segundos || 180;
    const pct = dur / total * 100;
    const mid = leftPct + pct / 2;
    leftPct  += pct;
    const isCur = st.track.file === S.curFile;
    const name  = st.track.name.length > 12 ? st.track.name.slice(0,11)+'…' : st.track.name;
    return `<span class="tl-lbl ${isCur?'cur':''}" style="left:${mid.toFixed(1)}%">${name}</span>`;
  }).join('');

  // Duración total
  const totalMins = Math.floor(total / 60);
  tlDur.textContent = `~${totalMins} min`;
}

// Seek directo a una canción del timeline (click en bloque)
function tlSeek(idx) {
  if (S.mixing) return;  // no permitir seek durante mezcla
  const st = S.sessionTracks[idx];
  if (!st) return;
  // Si es la pista actual, solo saltar al principio
  if (st.track.file === S.curFile) {
    const d = S.decks[S.deck];
    if (d && d.src) {
      d.src.onended = null;
      try { d.src.stop(); } catch(e) {}
    }
    const buf = S.bufs[st.track.file];
    if (!buf) return;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = 1.0;
    src.connect(d.preGain);
    src.start(0, 0);
    d.src = src;
    d.startedAt = ctx.currentTime;
    S.startAt = d.startedAt;
    S.silenceStart = null; S.silenceTriggered = false;
    src.onended = () => { if (S.playing && !S.mixing) doMix(); };
    logMsg(`↩ Reiniciando: ${st.track.name}`);
  }
  // (Para canciones pasadas/futuras no hacemos nada — solo informativo)
}
function fmt(s) { s=Math.max(0,Math.floor(s)); return Math.floor(s/60)+':'+String(s%60).padStart(2,'0'); }
function resize() {
  ['viz','wc'].forEach(id=>{
    const c=document.getElementById(id);
    c.width=c.offsetWidth*(devicePixelRatio||1);
    c.height=c.offsetHeight*(devicePixelRatio||1);
  });
}
window.addEventListener('resize', resize); resize();
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