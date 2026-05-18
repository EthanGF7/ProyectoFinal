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

import argparse
parser = argparse.ArgumentParser(description='Inicia el player local del DJ')
parser.add_argument('--port', type=int, default=8765, help='Puerto HTTP del player')
args = parser.parse_args()
PORT = args.port

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
#  SERVER
# ══════════════════════════════════════════════════════════════
LIBRARY = load_library()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

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

    def ok(self, data, ct):
        self.send_response(200)
        self.send_header("Content-Type", f"{ct}; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
<title>URBANO SESSION</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Space+Grotesk:wght@300;400;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;background:#060606;}
body{font-family:'Space Grotesk',sans-serif;}

/* ── GRAIN TEXTURE ─────────────────────────────────────── */
body::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:9999;
  opacity:0.045;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size:200px 200px;}

/* ── IDLE ─────────────────────────────────────────────── */
#idle{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:28px;z-index:100;background:#060606;
  transition:opacity 1.4s,visibility 1.4s;}
#idle.off{opacity:0;visibility:hidden;pointer-events:none}

.idle-logo{
  font-family:'Anton',sans-serif;
  font-size:clamp(56px,12vw,120px);letter-spacing:8px;text-transform:uppercase;
  color:#e8ff00;
  text-shadow:
    0 0 20px rgba(232,255,0,0.9),
    0 0 60px rgba(232,255,0,0.5),
    0 0 120px rgba(232,255,0,0.2),
    2px 2px 0 rgba(0,0,0,0.9);
  animation:urbanpulse 3s ease-in-out infinite;}
@keyframes urbanpulse{
  0%,100%{text-shadow:0 0 20px rgba(232,255,0,0.9),0 0 60px rgba(232,255,0,0.5),0 0 120px rgba(232,255,0,0.2),2px 2px 0 rgba(0,0,0,0.9);}
  50%{text-shadow:0 0 40px rgba(232,255,0,1),0 0 100px rgba(232,255,0,0.8),0 0 200px rgba(232,255,0,0.4),2px 2px 0 rgba(0,0,0,0.9);}}

.idle-sub{
  font-family:'Space Grotesk',sans-serif;font-weight:300;font-size:10px;letter-spacing:8px;
  color:rgba(232,255,0,0.35);text-transform:uppercase;}

.play-btn{width:90px;height:90px;border-radius:4px;
  background:transparent;border:2px solid rgba(232,255,0,0.5);
  cursor:pointer;font-size:30px;color:#e8ff00;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 30px rgba(232,255,0,0.2),inset 0 0 20px rgba(232,255,0,0.04);
  transition:all .2s;position:relative;clip-path:polygon(0 0,96% 0,100% 4%,100% 100%,4% 100%,0 96%);}
.play-btn:hover{border-color:rgba(232,255,0,0.9);
  box-shadow:0 0 60px rgba(232,255,0,0.6),inset 0 0 30px rgba(232,255,0,0.12);
  transform:scale(1.04);}
.play-btn:disabled{opacity:.15;cursor:not-allowed;}

.idle-info{font-family:'Space Grotesk',sans-serif;font-size:11px;
  color:rgba(255,255,255,0.2);letter-spacing:2px;}
.idle-info b{color:rgba(232,255,0,0.6)}

/* ── STAGE ─────────────────────────────────────────────── */
#stage{position:fixed;inset:0;z-index:1;opacity:0;transition:opacity 1.6s;background:#060606;}
#stage.on{opacity:1;}

#vizMain{position:absolute;inset:0;width:100%;height:100%;}
#particles{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;}

/* ── HUD — cartel urbano ──────────────────────────────── */
#hud{position:absolute;top:0;left:0;right:0;bottom:0;
  pointer-events:none;z-index:10;}

/* Now playing — esquina inferior izquierda, estilo etiqueta industrial */
#nowPlaying{
  position:absolute;bottom:0;left:0;right:0;
  padding:32px 48px 40px;
  background:linear-gradient(to top,rgba(6,6,6,0.96) 0%,rgba(6,6,6,0.5) 60%,transparent 100%);}

.hud-label{
  font-family:'Space Grotesk',sans-serif;font-weight:300;font-size:8px;letter-spacing:7px;
  text-transform:uppercase;color:rgba(232,255,0,0.45);margin-bottom:10px;
  display:flex;align-items:center;gap:10px;}
.hud-label::before{content:'';width:24px;height:1px;background:rgba(232,255,0,0.3);}

#npTitle{
  font-family:'Anton',sans-serif;
  font-size:clamp(24px,4vw,58px);letter-spacing:3px;line-height:1;
  color:#fff;text-transform:uppercase;
  text-shadow:0 0 40px rgba(232,255,0,0.2);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  transition:text-shadow .06s;
  animation:titleSlide .5s cubic-bezier(0.16,1,0.3,1) forwards;}
@keyframes titleSlide{0%{opacity:0;transform:translateX(-12px)}100%{opacity:1;transform:translateX(0)}}
#npTitle.beat-pulse{text-shadow:0 0 60px rgba(232,255,0,0.8),0 0 100px rgba(232,255,0,0.4);}

.hud-meta{display:flex;align-items:center;gap:12px;margin-top:10px;flex-wrap:wrap;}

.hud-bpm{
  font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:11px;letter-spacing:3px;
  color:rgba(232,255,0,0.8);text-transform:uppercase;}

.hud-key{
  font-family:'Space Grotesk',sans-serif;font-size:10px;font-weight:700;
  color:rgba(0,255,136,0.9);
  padding:2px 10px;border:1px solid rgba(0,255,136,0.3);
  background:rgba(0,255,136,0.05);}

.hud-dur{font-family:'Space Grotesk',sans-serif;font-size:10px;color:rgba(255,255,255,0.15);letter-spacing:1px;}

.hud-estilo{
  font-family:'Space Grotesk',sans-serif;font-size:8px;font-weight:700;letter-spacing:3px;text-transform:uppercase;
  color:rgba(255,50,120,0.9);padding:2px 10px;border:1px solid rgba(255,50,120,0.3);
  background:rgba(255,50,120,0.06);}

/* Like buttons */
#likeRow{position:absolute;top:32px;right:48px;display:flex;gap:8px;align-items:center;}
.like-btn{
  background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.1);
  width:34px;height:34px;cursor:pointer;font-size:14px;
  display:flex;align-items:center;justify-content:center;
  transition:all .2s;pointer-events:all;}
.like-btn:hover{border-color:rgba(232,255,0,0.5);background:rgba(232,255,0,0.06);transform:scale(1.1);}
.like-btn.active-like{border-color:rgba(80,220,120,.6);background:rgba(80,220,120,.1);box-shadow:0 0 14px rgba(80,220,120,.3);}
.like-btn.active-dislike{border-color:rgba(255,80,80,.6);background:rgba(255,80,80,.1);box-shadow:0 0 14px rgba(255,80,80,.3);}

/* Phase + mix — esquina superior izquierda */
#statusBar{position:absolute;top:32px;left:48px;display:flex;flex-direction:column;gap:8px;}

#phasePill{
  font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:8px;letter-spacing:4px;
  text-transform:uppercase;padding:4px 14px;border:1px solid;
  display:inline-flex;align-items:center;gap:6px;width:fit-content;
  transition:all .6s;}
.pill-warm-up{color:rgba(100,200,255,.8);border-color:rgba(100,200,255,.25);background:rgba(100,200,255,.04)}
.pill-first-build{color:rgba(232,255,0,.8);border-color:rgba(232,255,0,.3);background:rgba(232,255,0,.04)}
.pill-first-peak{color:#e8ff00;border-color:rgba(232,255,0,.7);background:rgba(232,255,0,.1);
  animation:peakglow .8s ease-in-out infinite}
.pill-breakdown{color:rgba(0,255,136,.8);border-color:rgba(0,255,136,.25);background:rgba(0,255,136,.04)}
.pill-second-build{color:rgba(232,255,0,.8);border-color:rgba(232,255,0,.3);background:rgba(232,255,0,.05)}
.pill-second-peak{color:#e8ff00;border-color:rgba(232,255,0,.8);background:rgba(232,255,0,.12);
  animation:peakglow .55s ease-in-out infinite}
.pill-outro{color:rgba(255,255,255,.15);border-color:rgba(255,255,255,.08);background:transparent}
@keyframes peakglow{0%,100%{box-shadow:none}50%{box-shadow:0 0 24px rgba(232,255,0,.7),0 0 60px rgba(232,255,0,.2)}}

#mixIndicator{
  font-family:'Space Grotesk',sans-serif;font-size:8px;letter-spacing:4px;
  text-transform:uppercase;padding:4px 14px;
  display:none;align-items:center;gap:8px;
  color:rgba(0,255,136,.9);border:1px solid rgba(0,255,136,.3);background:rgba(0,255,136,.05);}
#mixIndicator.on{display:flex;}
.mix-dot-ind{width:5px;height:5px;background:currentColor;animation:blink .4s step-end infinite;}
@keyframes blink{50%{opacity:0}}

/* Mode tag */
#modeTag{
  position:absolute;top:32px;left:50%;transform:translateX(-50%);
  font-family:'Space Grotesk',sans-serif;font-weight:300;font-size:8px;letter-spacing:6px;text-transform:uppercase;
  color:rgba(255,255,255,0.18);
  pointer-events:none;z-index:10;transition:opacity .8s;}

/* Progress strip — decorativa 2px */
#progressBar{
  position:absolute;bottom:0;left:0;right:0;height:2px;
  background:rgba(255,255,255,0.04);
  pointer-events:none;z-index:20;overflow:hidden;}
#progressFill{
  height:100%;width:0%;
  background:linear-gradient(90deg,rgba(232,255,0,0.6),rgba(0,255,136,0.5));
  transition:width .4s linear;}

/* Invisible compat */
.beat-dot{display:none}
#app,#tlWrap{display:none!important}
#eqRow,#mixRow,#nxtRow,#ww,#wc,#ph,#phHandle{display:none!important}
#viz{position:absolute;left:-9999px;opacity:0;width:1px;height:1px;}
</style>
</head>
<body>

<!-- IDLE -->
<div id="idle">
  <div class="idle-logo">URBANO</div>
  <div class="idle-sub">AI DJ · Sesión autónoma</div>
  <button class="play-btn" id="btnStart" disabled>▶</button>
  <div class="idle-info" id="idleInfo">Cargando biblioteca...</div>
</div>

<!-- STAGE -->
<div id="stage">
  <canvas id="vizMain"></canvas>
  <canvas id="particles"></canvas>
  <div id="hud">
    <div id="statusBar">
      <div id="phasePill" class="pill-warm-up">WARM</div>
      <div id="mixIndicator"><div class="mix-dot-ind"></div><span id="mixLabel">MIX</span></div>
    </div>
    <div id="likeRow">
      <button class="like-btn" id="btnLike" onclick="sendLike('like')" title="Me gusta">👍</button>
      <button class="like-btn" id="btnDislike" onclick="sendLike('dislike')" title="No me gusta">👎</button>
    </div>
    <div id="modeTag">— GLITCH —</div>
    <div id="nowPlaying">
      <div class="hud-label">Ahora Suena</div>
      <div id="npTitle">—</div>
      <div class="hud-meta">
        <span class="hud-bpm" id="npBpm"></span>
        <span class="hud-key" id="npKey" style="display:none"></span>
        <span class="hud-estilo" id="npEstilo" style="display:none"></span>
        <span class="hud-dur" id="npDur"></span>
      </div>
    </div>
  </div>
  <div id="progressBar"><div id="progressFill"></div></div>
</div>

<!-- INVISIBLE COMPAT -->
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
//  DJ AI · Audio Engine (lógica Python intacta)
// ════════════════════════════════════════════════════════════════
const AC = window.AudioContext || window.webkitAudioContext;
let ctx = null;

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
  deck: 'A', startAt: 0, bufs: {},
  decks: { A: {}, B: {} }, modOk: false,
  silenceStart: null, lastRms: 1.0, silenceTriggered: false,
  beatLastTime: 0, beatThresh: 0.15, beatHistory: [], lastBpm: 0,
  sessionTracks: [], sessionStartTime: 0,
  _beatSnapScheduled: false,
  cueing: false, cueSrc: null, cueGain: null,
};

function ic() {
  if (!ctx) {
    ctx = new AC();
    S.comp = ctx.createDynamicsCompressor();
    S.comp.threshold.value = -14; S.comp.knee.value = 6;
    S.comp.ratio.value = 4; S.comp.attack.value = 0.003; S.comp.release.value = 0.25;
    S.mAnl = ctx.createAnalyser(); S.mAnl.fftSize = 1024;
    S.comp.connect(S.mAnl); S.mAnl.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  if (!S.reverb) {
    S.reverb = ctx.createConvolver(); S.reverbGain = ctx.createGain(); S.reverbGain.gain.value = 0;
    const rate=ctx.sampleRate, len=Math.floor(rate*2.5), ir=ctx.createBuffer(2,len,rate);
    for(let ch=0;ch<2;ch++){const d=ir.getChannelData(ch);for(let i=0;i<len;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/len,2.5);}
    S.reverb.buffer=ir; S.comp.connect(S.reverbGain); S.reverbGain.connect(S.reverb); S.reverb.connect(ctx.destination);
  }
  if (!S.cueOutGain) { S.cueOutGain=ctx.createGain(); S.cueOutGain.gain.value=0.85; S.cueOutGain.connect(ctx.destination); }
}

async function boot() {
  const [lr,mr] = await Promise.all([fetch('/api/library'),fetch('/api/modules')]);
  S.lib = await lr.json(); const m=await mr.json(); S.modOk=m.ok;
  await loadPrefs();
  document.getElementById('modB').textContent = S.modOk?'MÓDULOS OK':'FALLBACK';
  document.getElementById('libCount').textContent = S.lib.length+' canciones';
  document.getElementById('idleInfo').innerHTML=`<b>${S.lib.length}</b> canción${S.lib.length!==1?'es':''}`;
  document.getElementById('btnStart').disabled = S.lib.length===0;
  if(!S.lib.length) document.getElementById('idleInfo').textContent='Pon MP3/WAV en musica/canciones/';
  renderLib();
}

{
  const ww=document.getElementById('ww'),ph=document.getElementById('ph'),
    handle=document.getElementById('phHandle'),tooltip=document.getElementById('wwTooltip');
  let dragging=false;
  function scrubPos(e){const rect=ww.getBoundingClientRect(),pad=18,
    x=(e.touches?e.touches[0].clientX:e.clientX)-rect.left-pad,w=rect.width-pad*2;
    return Math.max(0,Math.min(1,x/w));}
  function seekTo(frac){const dur=S.cur?(S.cur.duracion_segundos||0):0;
    if(!dur||!S.playing||!ctx)return;const newTime=frac*dur,dk=S.deck,trk=S.cur;
    if(!trk||!S.bufs[trk.file])return;const d=S.decks[dk];
    if(d.src){d.src.onended=null;try{d.src.stop();}catch(e){}}
    const src=ctx.createBufferSource();src.buffer=S.bufs[trk.file];src.playbackRate.value=1.0;
    src.connect(d.preGain);src.start(0,newTime);d.src=src;d.startedAt=ctx.currentTime-newTime;
    S.startAt=d.startedAt;S.silenceStart=null;S.silenceTriggered=false;
    src.onended=()=>{if(S.playing&&dk===S.deck&&!S.mixing)doMix();};}
  function onMove(e){if(!S.playing)return;e.preventDefault();const frac=scrubPos(e),
    dur=S.cur?(S.cur.duracion_segundos||0):0,wc=document.getElementById('wc'),w=wc.offsetWidth;
    ph.style.left=(18+frac*w)+'px';tooltip.textContent=fmt(frac*dur);
    tooltip.style.left=(18+frac*w)+'px';tooltip.classList.add('show');
    if(dragging)document.getElementById('tCur').textContent=fmt(frac*dur);}
  function onDown(e){if(!S.playing||S.mixing)return;dragging=true;ph.classList.add('scrubbing');onMove(e);}
  function onUp(e){if(!dragging)return;dragging=false;ph.classList.remove('scrubbing');
    tooltip.classList.remove('show');seekTo(scrubPos(e.changedTouches?{clientX:e.changedTouches[0].clientX}:e));}
  ww.addEventListener('mousedown',onDown);ww.addEventListener('touchstart',onDown,{passive:false});
  window.addEventListener('mousemove',e=>{if(dragging)onMove(e);});
  window.addEventListener('touchmove',e=>{if(dragging)onMove(e);},{passive:false});
  window.addEventListener('mouseup',onUp);window.addEventListener('touchend',onUp);
  ww.addEventListener('mousemove',e=>{if(!dragging&&S.playing)onMove(e);});
  ww.addEventListener('mouseleave',()=>{if(!dragging)tooltip.classList.remove('show');});
  S._dragging=()=>dragging;
}

document.getElementById('btnStart').addEventListener('click', async () => {
  ic();
  document.getElementById('idle').classList.add('off');
  document.getElementById('stage').classList.add('on');
  initUrbanoVisuals();
  const first=chooseFirst();
  await begin(first);
});

function chooseFirst(){if(!S.lib.length)return null;const s=[...S.lib].sort((a,b)=>(a.energia||50)-(b.energia||50));return s[Math.floor(s.length*0.18)]||s[0];}

async function begin(t){
  S.cur=t;S.curFile=t.file;S.deck='A';S.playing=true;S.startAt=0;
  S.played.push(t.file);S.playedSet.add(t.file);S.count=1;
  S.sessionStartTime=ctx.currentTime;
  S.sessionTracks=[{track:t,startCtxTime:ctx.currentTime,color:trackColor(0)}];
  updateNP(t,'warm-up');const startPos=t.start_position??0;
  await playDeck('A',t,startPos);logMsg(`Iniciando: ${t.name}`);
  document.getElementById('btnSkip').disabled=false;
  renderLib();renderTimeline();loop();askNext(t,0);
}

document.getElementById('btnSkip').addEventListener('click',()=>{if(!S.mixing&&S.playing)doMix();});

document.getElementById('btnCue').addEventListener('click',async()=>{
  if(!S.nxt)return;const btn=document.getElementById('btnCue');
  if(S.cueing){if(S.cueSrc){try{S.cueSrc.stop();}catch(e){}}if(S.cueGain)S.cueGain.gain.setValueAtTime(0,ctx.currentTime);
    S.cueing=false;btn.classList.remove('cueing');btn.textContent='👂 CUE';return;}
  try{const buf=await loadBuf(S.nxt),enterAt=S.nxtPlan?(S.nxtPlan.start_next_time||0):0,CUE_DUR=8;
    S.cueGain=ctx.createGain();S.cueGain.gain.setValueAtTime(0,ctx.currentTime);
    S.cueGain.gain.linearRampToValueAtTime(0.6,ctx.currentTime+0.3);S.cueGain.connect(S.cueOutGain);
    S.cueSrc=ctx.createBufferSource();S.cueSrc.buffer=buf;S.cueSrc.connect(S.cueGain);S.cueSrc.start(0,enterAt);
    S.cueGain.gain.setValueAtTime(0.6,ctx.currentTime+CUE_DUR-1);
    S.cueGain.gain.linearRampToValueAtTime(0,ctx.currentTime+CUE_DUR);S.cueSrc.stop(ctx.currentTime+CUE_DUR);
    S.cueSrc.onended=()=>{S.cueing=false;btn.classList.remove('cueing');btn.textContent='👂 CUE';S.cueSrc=null;};
    S.cueing=true;btn.classList.add('cueing');btn.textContent='■ STOP';}catch(e){}
});

async function askNext(t,ct){
  if(!t)return;
  try{const pe=encodeURIComponent(JSON.stringify([...S.playedSet]));
    const pl=encodeURIComponent(JSON.stringify(S.played.slice(-3).map(f=>({file:f,key:(S.lib.find(x=>x.file===f)||{}).key||''}))));
    const url=`/api/next?current=${encodeURIComponent(t.file)}&time=${ct.toFixed(1)}&played=${pe}&count=${S.count}&played_list=${pl}`;
    const d=await(await fetch(url)).json();
    if(d.error){S.nxt=null;hideNext();return;}
    S.nxt=d.track;S.nxtPlan=d.plan;S.nxtScore=d.score;S.nxtPhase=d.phase;
    showNext(d.track,d.plan,d.score,d.phase);updateArc(d.phase,d.target_energy);preload(d.track);renderLib();}catch(e){}
}

async function loadBuf(t){
  if(S.bufs[t.file])return S.bufs[t.file];ic();
  const ab=await(await fetch('/audio/'+encodeURIComponent(t.file))).arrayBuffer();
  const buf=await ctx.decodeAudioData(ab);return S.bufs[t.file]=buf;
}
async function preload(t){if(!t||S.bufs[t.file])return;try{ic();await loadBuf(t);}catch(e){}}

function resetGraph(dk){
  const d=S.decks[dk];if(d.src){try{d.src.stop();}catch(e){}}
  d.preGain=ctx.createGain();d.hipass=ctx.createBiquadFilter();d.lopass=ctx.createBiquadFilter();
  d.analyser=ctx.createAnalyser();d.analyser.fftSize=256;
  d.hipass.type='highpass';d.hipass.Q.value=0.71;d.lopass.type='lowpass';d.lopass.Q.value=0.71;
  d.preGain.connect(d.hipass);d.hipass.connect(d.lopass);d.lopass.connect(d.analyser);d.analyser.connect(S.comp);
  return d;
}

async function playDeck(dk,track,offset=0){
  const buf=await loadBuf(track);
  if(!track.duracion_segundos||track.duracion_segundos===0)track.duracion_segundos=buf.duration;
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
  src.onended=()=>{if(S.playing&&dk===S.deck&&!S.mixing)doMix();};
}

function getTime(){return !S.playing||!ctx?0:Math.max(0,ctx.currentTime-S.startAt);}

async function doMix(){
  if(S.mixing||!S.playing)return;const nxt=S.nxt;
  if(!nxt){askNext(S.cur,getTime());setTimeout(()=>{if(!S.mixing&&S.nxt)doMix();},1200);return;}
  const plan=S.nxtPlan,cfDur=plan?(plan.mix_duration||8):8,enterAt=plan?(plan.start_next_time||0):0,
    style=plan?(plan.style||'guetta'):'guetta';
  if(S.cueing&&S.cueSrc){try{S.cueSrc.stop();}catch(e){}S.cueSrc=null;S.cueing=false;
    document.getElementById('btnCue').classList.remove('cueing');document.getElementById('btnCue').textContent='👂 CUE';}
  S.mixing=true;S.mixStart=ctx.currentTime;S.mixDur=cfDur;S.mixStyle=style;
  showMixing(nxt.name,cfDur,style);logMsg(`${STYLE_LABELS[style]||style} · ⇄ ${nxt.name} · ${cfDur.toFixed(0)}s`);
  if(S.reverb&&S.reverbGain){
    const rp=style==='avicii'?.35:style==='progressive'?.10:style==='fusion'?.22:.18;
    const rg=S.reverbGain.gain;rg.cancelScheduledValues(ctx.currentTime);rg.setValueAtTime(0,ctx.currentTime);
    rg.linearRampToValueAtTime(rp,ctx.currentTime+cfDur*0.25);
    rg.linearRampToValueAtTime(rp*0.5,ctx.currentTime+cfDur*0.75);
    rg.linearRampToValueAtTime(0,ctx.currentTime+cfDur);}
  const out=S.deck,inp=out==='A'?'B':'A';
  await playDeck(inp,nxt,enterAt);
  const t0=ctx.currentTime,dOut=S.decks[out],dIn=S.decks[inp],steps=Math.round(cfDur*30);
  dOut.preGain.gain.cancelScheduledValues(t0);dIn.preGain.gain.cancelScheduledValues(t0);
  [dOut,dIn].forEach(d=>{d.hipass.frequency.cancelScheduledValues(t0);d.lopass.frequency.cancelScheduledValues(t0);});
  dOut.preGain.gain.setValueAtTime(1,t0);dIn.preGain.gain.setValueAtTime(0,t0);
  dOut.lopass.frequency.setValueAtTime(20000,t0);dOut.hipass.frequency.setValueAtTime(20,t0);
  dIn.lopass.frequency.setValueAtTime(20000,t0);
  if(style==='progressive'||style==='avicii'||style==='fusion')dIn.hipass.frequency.setValueAtTime(20,t0);
  else dIn.hipass.frequency.setValueAtTime(320,t0);
  if(style!=='progressive'&&dIn.src&&dIn._bpmRatio&&dIn._bpmRatio!==1.0){
    dIn.src.playbackRate.cancelScheduledValues(t0);dIn.src.playbackRate.setValueAtTime(dIn._bpmRatio,t0);
    dIn.src.playbackRate.exponentialRampToValueAtTime(1.0,t0+cfDur);}
  if(!S.compGain){S.compGain=ctx.createGain();S.compGain.gain.value=1;
    S.comp.disconnect(S.mAnl);S.comp.connect(S.compGain);S.compGain.connect(S.mAnl);}
  S.compGain.gain.cancelScheduledValues(t0);S.compGain.gain.setValueAtTime(1,t0);
  for(let i=0;i<=steps;i++){
    const f=i/steps,tAt=t0+f*cfDur;
    let vOut,vIn;
    if(style==='progressive'){vOut=Math.cos(f*Math.PI/2);vIn=Math.sin(f*Math.PI/2);}
    else if(style==='fusion'){
      if(f<0.20){vOut=1;vIn=Math.sin((f/0.20)*Math.PI/2);}
      else if(f<0.80){const mid=(f-0.20)/0.60;vOut=Math.cos(mid*Math.PI/2)*0.3+0.7;vIn=Math.sin(mid*Math.PI/2)*0.3+0.7;}
      else{const tail=(f-0.80)/0.20;vOut=Math.cos(tail*Math.PI/2)*0.7;vIn=1.0;}
    }else if(style==='avicii'){
      vOut=Math.cos(f*Math.PI/2);vIn=f<0.20?Math.sin((f/0.20)*0.52):Math.sin(((f-0.20)/0.80)*Math.PI/2+0.52);vIn=Math.min(1,vIn);
    }else{
      vOut=f<0.30?1:Math.cos(((f-0.30)/0.70)*Math.PI/2);vIn=1/(1+Math.exp(-12*(f-0.65)));
    }
    dOut.preGain.gain.setValueAtTime(Math.max(0,vOut),tAt);dIn.preGain.gain.setValueAtTime(Math.max(0,vIn),tAt);
    if(style==='guetta'){
      if(f<0.60)dIn.hipass.frequency.setValueAtTime(320,tAt);
      else dIn.hipass.frequency.exponentialRampToValueAtTime(20,tAt);
      dOut.lopass.frequency.setValueAtTime(Math.max(400,20000*(1-f*1.2)),tAt);
    }else if(style==='avicii'){dOut.hipass.frequency.setValueAtTime(20+f*780,tAt);
    }else if(style==='fusion'){dOut.lopass.frequency.setValueAtTime(Math.max(2000,20000*(1-f*.5)),tAt);}
    S.compGain.gain.setValueAtTime(style==='progressive'?1:1+Math.sin(f*Math.PI)*0.06,tAt);
  }
  dOut.preGain.gain.setValueAtTime(0,t0+cfDur);dIn.preGain.gain.setValueAtTime(1,t0+cfDur);
  setTimeout(async()=>{
    const d2=S.decks[out];if(d2.src){d2.src.onended=null;try{d2.src.stop();}catch(e){}}
    S.deck=inp;S.cur=nxt;S.curFile=nxt.file;S.startAt=S.decks[inp].startedAt;
    S.mixing=false;S.mixStyle=null;
    S.played.push(nxt.file);S.playedSet.add(nxt.file);S.count++;
    S.sessionTracks.push({track:nxt,startCtxTime:ctx.currentTime,color:trackColor(S.sessionTracks.length)});
    S.silenceStart=null;S.silenceTriggered=false;
    hideMixing();updateNP(nxt,'');renderLib();renderTimeline();askNext(nxt,0);
  },cfDur*1000+200);
}

function loop(){
  if(!S.playing)return;requestAnimationFrame(loop);
  const t=getTime(),dur=S.cur?(S.cur.duracion_segundos||0):0;
  if(dur>0){const pf=document.getElementById('progressFill');if(pf)pf.style.width=Math.min(100,(t/dur)*100)+'%';}
  document.getElementById('tCur').textContent=fmt(t);
  if(dur)document.getElementById('tTot').textContent=fmt(dur);
  if(S.mAnl){
    const fbuf=new Uint8Array(S.mAnl.frequencyBinCount);S.mAnl.getByteFrequencyData(fbuf);
    const subEnd=Math.floor(fbuf.length*0.05);let subE=0;
    for(let i=0;i<subEnd;i++)subE+=fbuf[i]/255;subE/=Math.max(subEnd,1);
    S.beatHistory.push(subE);if(S.beatHistory.length>30)S.beatHistory.shift();
    const avg=S.beatHistory.reduce((a,b)=>a+b,0)/S.beatHistory.length;
    S.beatThresh=avg*1.35+0.05;
    const now=ctx.currentTime;
    if(subE>S.beatThresh&&(now-S.beatLastTime)>0.25){
      S.beatLastTime=now;UV.lastBeat=now;
      const tt=document.getElementById('npTitle');
      if(tt){tt.classList.add('beat-pulse');setTimeout(()=>tt.classList.remove('beat-pulse'),120);}
    }
    let total=0;for(let i=0;i<fbuf.length;i++)total+=fbuf[i]/255;
    UV.smoothEnergy+=(total/fbuf.length-UV.smoothEnergy)*0.12;UV.rawFreq=fbuf;
  }
  if(S.mixing){const elapsed=ctx.currentTime-S.mixStart,frac=Math.min(1,elapsed/Math.max(S.mixDur,1));
    document.getElementById('mixFill').style.width=(frac*100)+'%';updateEQVisual(frac);}
  if(!S.mixing&&S.playing&&!S._beatSnapScheduled&&S.nxt&&S.nxtPlan&&dur>0){
    const startMix=S.nxtPlan.start_current_time||(dur-(S.nxtPlan.mix_duration||8));
    if(t>=startMix-0.3&&t<startMix+3){S._beatSnapScheduled=true;
      setTimeout(()=>{if(!S.mixing&&S.playing)doMix();S._beatSnapScheduled=false;},Math.max(0,(startMix-t)*1000));}}
  if(!S.mixing&&S.playing&&dur>0&&t>=dur-0.5&&!S._beatSnapScheduled){
    S._beatSnapScheduled=true;setTimeout(()=>{if(!S.mixing&&S.playing)doMix();S._beatSnapScheduled=false;},Math.max(0,(dur-t)*1000));}
  if(S.count===1&&!S.mixing&&S.nxt&&!S._beatSnapScheduled)askNext(S.cur,t);
  if(S.playing&&S.sessionTracks.length>0){
    const elapsed=ctx.currentTime-S.sessionStartTime;
    const totalEst=S.sessionTracks.reduce((acc,st)=>acc+(st.track.duracion_segundos||180),0);
    const pct=Math.min(99,(elapsed/Math.max(totalEst,1))*100);
    const tlHead=document.getElementById('tlHead');if(tlHead)tlHead.style.left=pct+'%';}
  if(!S.mixing&&S.playing&&t>5&&!(S._dragging&&S._dragging())){
    const dk=S.decks[S.deck];
    if(dk&&dk.analyser){
      const buf2=new Uint8Array(dk.analyser.frequencyBinCount);dk.analyser.getByteFrequencyData(buf2);
      let sum=0;for(let i=0;i<buf2.length;i++)sum+=(buf2[i]/255)*(buf2[i]/255);
      const rms=Math.sqrt(sum/buf2.length),progress=dur>0?t/dur:0;
      if(rms<0.03&&progress>0.30&&!S.silenceTriggered){
        if(S.silenceStart===null)S.silenceStart=ctx.currentTime;
        else if((ctx.currentTime-S.silenceStart)*1000>1800){S.silenceTriggered=true;S.silenceStart=null;doMix();}
      }else if(rms>=0.03){S.silenceStart=null;S.silenceTriggered=false;}}}
  drawUrbanoViz();
}

function updateEQVisual(frac){
  document.getElementById('eqHi').style.width=Math.max(0,(1-Math.pow(frac/0.8,0.6))*100)+'%';
  document.getElementById('eqMid').style.width=Math.max(0,(1-Math.pow(frac/0.9,0.8))*100)+'%';
  document.getElementById('eqLo').style.width=Math.max(0,(1-Math.pow(frac/1.0,1.2))*100)+'%';
}
function updateNP(t,phase){
  const titleEl=document.getElementById('npTitle');
  if(titleEl){titleEl.style.animation='none';void titleEl.offsetWidth;titleEl.style.animation='';titleEl.textContent=t.name;}
  const bpmEl=document.getElementById('npBpm');if(bpmEl)bpmEl.textContent=t.bpm?t.bpm.toFixed(1)+' BPM':'';
  const durEl=document.getElementById('npDur');if(durEl)durEl.textContent=t.duracion_segundos?fmt(t.duracion_segundos):'';
  const keyEl=document.getElementById('npKey');if(keyEl){if(t.key){keyEl.textContent=t.key;keyEl.style.display='inline';}else keyEl.style.display='none';}
  const estiloEl=document.getElementById('npEstilo');if(estiloEl){if(t.estilo){estiloEl.textContent=t.estilo;estiloEl.style.display='inline';}else estiloEl.style.display='none';}
  const bv=document.getElementById('bpmVal');if(bv)bv.textContent=t.bpm?Math.round(t.bpm):'—';
  const pill=document.getElementById('phasePill');const p=phase||S.nxtPhase||'warm-up';
  if(pill){pill.textContent=PHASE_LABELS[p]||p;pill.setAttribute('class','pill-'+p);}
  const egyEl=document.getElementById('npEgy');if(egyEl)egyEl.textContent=t.energia?'E'+t.energia:'';
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
  document.getElementById('nxtT').textContent=(STYLE_ICONS[style]||'⚡')+' '+style.toUpperCase()+' · '+((plan&&plan.mix_duration)||8).toFixed(0)+'s fade';
  document.getElementById('btnCue').disabled=false;
}
function hideNext(){document.getElementById('nxtRow').style.display='none';}
function showMixing(name,dur,style){
  const row=document.getElementById('mixRow');if(row){row.classList.add('on');}
  const lbl=document.getElementById('mixStyleLabel');if(lbl)lbl.textContent=STYLE_LABELS[style]||'⚡';
  const mi=document.getElementById('mixInfo');if(mi)mi.textContent=`→ ${name} · ${dur.toFixed(0)}s`;
  const mf=document.getElementById('mixFill');if(mf)mf.style.width='0%';
  const eq=document.getElementById('eqRow');if(eq)eq.classList.add('on');
  const ind=document.getElementById('mixIndicator');const mlb=document.getElementById('mixLabel');
  if(ind&&mlb){ind.className='on';mlb.textContent=(STYLE_LABELS[style]||'MIX').replace(/^.+\s/,'');}
}
function hideMixing(){
  const row=document.getElementById('mixRow');if(row)row.classList.remove('on');
  const ind=document.getElementById('mixIndicator');if(ind)ind.className='';
}
S.prefs={};
async function loadPrefs(){try{const r=await fetch('/api/prefs');S.prefs=await r.json();}catch(e){}}
async function sendLike(action){
  if(!S.cur)return;const file=S.cur.file;const current=S.prefs[file];
  const sendAction=(action==='like'&&current===1)||(action==='dislike'&&current===-1)?'clear':action;
  try{await fetch('/api/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({file,action:sendAction})});
    if(sendAction==='like')S.prefs[file]=1;else if(sendAction==='dislike')S.prefs[file]=-1;else delete S.prefs[file];
    updateLikeUI(file);const titleEl=document.getElementById('npTitle');
    if(titleEl){const orig=titleEl.textContent;
      titleEl.textContent=sendAction==='like'?'👍 ¡Guardado!':sendAction==='dislike'?'👎 Anotado':'✓ Borrado';
      setTimeout(()=>{titleEl.textContent=orig;},1400);}
  }catch(e){}
}
function updateLikeUI(file){
  const pref=S.prefs[file]||0;
  const bl=document.getElementById('btnLike');const bd=document.getElementById('btnDislike');
  if(bl)bl.classList.toggle('active-like',pref===1);if(bd)bd.classList.toggle('active-dislike',pref===-1);
}
function renderLib(){
  const list=document.getElementById('tlist');
  if(!S.lib.length){list.innerHTML='<div>Pon MP3/WAV en musica/canciones/</div>';return;}
  list.innerHTML=S.lib.map((t,i)=>{
    const iC=t.file===S.curFile,iN=S.nxt&&t.file===S.nxt.file,done=!iC&&S.playedSet.has(t.file);
    return `<div class="tk ${iC?'cur':''} ${iN?'nxt':''} ${done?'done':''}"><div class="tn">${iC?'▶':iN?'→':done?'✓':i+1}</div><div class="tt">${t.name}</div></div>`;
  }).join('');
}
function drawWave(buf,track){
  const c=document.getElementById('wc'),dpr=devicePixelRatio||1;
  c.width=c.offsetWidth*dpr;c.height=c.offsetHeight*dpr;
  const g=c.getContext('2d');g.scale(dpr,dpr);
  const W=c.offsetWidth,H=c.offsetHeight,mid=H/2;
  const data=buf.getChannelData(0),step=Math.ceil(data.length/W);
  g.clearRect(0,0,W,H);
  const gr=g.createLinearGradient(0,0,W,0);
  gr.addColorStop(0,'rgba(232,255,0,.06)');gr.addColorStop(.4,'rgba(232,255,0,.6)');
  gr.addColorStop(.6,'rgba(0,255,136,.5)');gr.addColorStop(1,'rgba(232,255,0,.06)');
  g.strokeStyle=gr;g.lineWidth=1;g.beginPath();
  for(let i=0;i<W;i++){let mn=1,mx=-1;
    for(let j=0;j<step;j++){const v=data[i*step+j]||0;if(v<mn)mn=v;if(v>mx)mx=v;}
    g.moveTo(i,mid+mn*mid);g.lineTo(i,mid+mx*mid);}
  g.stroke();
}
function trackColor(idx){
  const p=['rgba(232,255,0','rgba(0,255,136','rgba(255,50,120','rgba(0,200,255','rgba(255,100,0','rgba(200,50,255','rgba(255,220,0','rgba(0,180,255'];
  return p[idx%p.length];
}
function renderTimeline(){
  const wrap=document.getElementById('tlWrap');if(!wrap||!S.sessionTracks.length)return;
  wrap.style.display='block';
  const blocks=document.getElementById('tlBlocks'),labels=document.getElementById('tlLabels'),tlDur=document.getElementById('tlDur');
  const durations=S.sessionTracks.map(st=>st.track.duracion_segundos||180);
  const total=durations.reduce((a,b)=>a+b,0);
  blocks.innerHTML=S.sessionTracks.map((st,i)=>{
    const dur=st.track.duracion_segundos||180,pct=(dur/total*100).toFixed(2);
    const isCur=st.track.file===S.curFile,isDone=!isCur&&i<S.sessionTracks.length-1;
    return `<div class="tl-block ${isCur?'playing':''} ${isDone?'done':'future'}" style="width:${pct}%;background:${st.color},.08)" title="${st.track.name}"><div style="position:absolute;bottom:0;left:0;right:0;height:${30+(st.track.energia||50)*0.7}%;background:${st.color},.4);border-radius:2px 2px 0 0"></div></div>`;
  }).join('');
  let leftPct=0;
  labels.innerHTML=S.sessionTracks.map((st,i)=>{
    const dur=st.track.duracion_segundos||180,pct=dur/total*100,mid=leftPct+pct/2;leftPct+=pct;
    const isCur=st.track.file===S.curFile;
    const name=st.track.name.length>12?st.track.name.slice(0,11)+'…':st.track.name;
    return `<span class="tl-lbl ${isCur?'cur':''}" style="left:${mid.toFixed(1)}%">${name}</span>`;
  }).join('');
  tlDur.textContent=`~${Math.floor(total/60)} min`;
}
function logMsg(m){document.getElementById('log').textContent=m;}
function fmt(s){s=Math.max(0,Math.floor(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');}
function resize(){['viz','wc'].forEach(id=>{const c=document.getElementById(id);c.width=c.offsetWidth*(devicePixelRatio||1);c.height=c.offsetHeight*(devicePixelRatio||1);});}
window.addEventListener('resize',resize);resize();

// ════════════════════════════════════════════════════════════════
//  URBANO VISUALS — Dark Neon Industrial
//  3 modos rotativos: Glitch · Radar EQ · Partículas Humo
// ════════════════════════════════════════════════════════════════
const UV = {
  smoothEnergy: 0,
  rawFreq: null,
  lastBeat: 0,
  mode: 0,           // 0=glitch, 1=radar, 2=smoke
  modeTimer: 0,
  MODE_DURATION: 40, // segundos
  t: 0,
  // Glitch state
  glitchTimer: 0,
  glitchActive: false,
  glitchIntensity: 0,
  // Radar state
  radarAngle: 0,
  // Smoke particles
  smoke: [],
};

const MODE_NAMES_U = ['GLITCH','RADAR','SMOKE'];

function initUrbanoVisuals(){
  const pm=document.getElementById('vizMain'),pp=document.getElementById('particles');
  function resizeViz(){
    pm.width=pp.width=window.innerWidth*(devicePixelRatio||1);
    pm.height=pp.height=window.innerHeight*(devicePixelRatio||1);
    pm.style.width=pp.style.width=window.innerWidth+'px';
    pm.style.height=pp.style.height=window.innerHeight+'px';
  }
  window.addEventListener('resize',resizeViz);resizeViz();
  for(let i=0;i<120;i++) UV.smoke.push(mkSmoke());
  UV.modeTimer=performance.now();
  document.getElementById('modeTag').textContent='— '+MODE_NAMES_U[0]+' —';
}

function mkSmoke(){
  const W=window.innerWidth;
  return{
    x:Math.random()*W, y:Math.random()*window.innerHeight*0.2,
    vx:(Math.random()-0.5)*0.8, vy:1.2+Math.random()*1.8,
    size:8+Math.random()*40, opacity:0.05+Math.random()*0.2,
    decay:0.003+Math.random()*0.005,
    hue:Math.random()<0.6?75:Math.random()<0.5?150:330, // volt/green/magenta
    life:1.0,
  };
}

function resetSmoke(p){
  const W=window.innerWidth;
  p.x=Math.random()*W; p.y=-20;
  p.vx=(Math.random()-0.5)*0.8; p.vy=1.2+Math.random()*2;
  p.size=10+Math.random()*50; p.opacity=0.04+Math.random()*0.18;
  p.decay=0.003+Math.random()*0.005; p.life=1.0;
  p.hue=Math.random()<0.55?75:Math.random()<0.5?150:330;
}

function drawUrbanoViz(){
  const pm=document.getElementById('vizMain');if(!pm)return;
  const gm=pm.getContext('2d');
  const W=pm.width,H=pm.height,cx=W/2,cy=H/2;
  const dpr=devicePixelRatio||1;
  const now=performance.now();
  UV.t+=0.016;

  // Mode rotation
  const elapsed=(now-UV.modeTimer)/1000;
  if(elapsed>UV.MODE_DURATION){
    UV.mode=(UV.mode+1)%3;UV.modeTimer=now;
    const lbl=document.getElementById('modeTag');
    if(lbl){lbl.style.opacity=0;setTimeout(()=>{lbl.textContent='— '+MODE_NAMES_U[UV.mode]+' —';lbl.style.opacity=1;},600);}
  }

  const beatAge=ctx?(ctx.currentTime-UV.lastBeat):99;
  const beatFlash=Math.max(0,1-beatAge*5);
  const energy=UV.smoothEnergy;
  const freq=UV.rawFreq;

  gm.clearRect(0,0,W,H);

  // Dark background (near-black with subtle grain feel)
  gm.fillStyle='rgba(6,6,6,0.85)';
  gm.fillRect(0,0,W,H);

  // ── MODE 0: GLITCH + CHROMATIC ABERRATION ──────────────────
  if(UV.mode===0){
    let subE=0;
    if(freq){const subEnd=Math.floor(freq.length*0.05);for(let i=0;i<subEnd;i++)subE+=freq[i]/255;subE/=Math.max(subEnd,1);}

    // Trigger glitch on beat
    if(beatFlash>0.7&&subE>0.25){UV.glitchActive=true;UV.glitchIntensity=subE;UV.glitchTimer=now;}
    if(UV.glitchActive&&(now-UV.glitchTimer)>120){UV.glitchActive=false;}

    // Base waveform — compact horizontal strips
    if(freq){
      const slices=80;
      for(let s=0;s<slices;s++){
        const si=Math.floor((s/slices)*freq.length);
        const v=freq[si]/255;
        const y=H*(s/slices);
        const lineH=H/slices;
        const barW=(W/2)*v*(1+energy);
        // Chromatic: R/G/B slightly offset
        const offX=UV.glitchActive?UV.glitchIntensity*30*(Math.random()-0.5):0;
        const offY=UV.glitchActive?UV.glitchIntensity*4*(Math.random()-0.5):0;
        gm.fillStyle=`rgba(232,255,0,${v*0.7+energy*0.3})`;
        gm.fillRect(cx+offX, y+offY, barW*(0.5+Math.random()*0.5), lineH*0.7);
        gm.fillStyle=`rgba(0,255,136,${v*0.5})`;
        gm.fillRect(cx+offX+barW*0.1, y+offY+lineH*0.15, barW*0.8, lineH*0.5);
        // Mirror left
        gm.fillStyle=`rgba(232,255,0,${v*0.5})`;
        gm.fillRect(cx-offX-barW*(0.5+Math.random()*0.5), y+offY, barW*(0.5+Math.random()*0.5), lineH*0.7);
      }
    }

    // Glitch scanlines
    if(UV.glitchActive){
      const numGlitch=Math.floor(UV.glitchIntensity*12)+2;
      for(let g=0;g<numGlitch;g++){
        const gy=Math.random()*H;const gh=2+Math.random()*12;
        const shift=(Math.random()-0.5)*UV.glitchIntensity*60;
        // Slice + shift effect
        gm.save();gm.beginPath();gm.rect(0,gy,W,gh);gm.clip();
        gm.translate(shift,0);
        // Colored glitch bar
        gm.fillStyle=`rgba(255,50,120,${0.3+Math.random()*0.5})`;
        gm.fillRect(0,gy,W,gh);gm.restore();
      }
      // Chromatic split flash
      gm.fillStyle=`rgba(232,255,0,${UV.glitchIntensity*0.04})`;gm.fillRect(3,0,W,H);
      gm.fillStyle=`rgba(255,0,80,${UV.glitchIntensity*0.03})`;gm.fillRect(-3,0,W,H);
    }

    // Beat ring
    if(beatFlash>0.05){
      for(let r=0;r<3;r++){
        const td=Math.max(0,beatFlash-r*0.12);
        gm.strokeStyle=`rgba(232,255,0,${td*0.6})`;
        gm.lineWidth=(1-td)*4*dpr;
        gm.beginPath();gm.arc(cx,cy,td*Math.min(W,H)*0.5,0,Math.PI*2);gm.stroke();
      }
    }
  }

  // ── MODE 1: RADIAL EQ RADAR ────────────────────────────────
  else if(UV.mode===1){
    UV.radarAngle+=0.008+energy*0.03;

    // Radar sweep glow
    const sweepEnd={x:cx+Math.cos(UV.radarAngle)*Math.min(W,H)*0.6,y:cy+Math.sin(UV.radarAngle)*Math.min(W,H)*0.6};
    const sweep=gm.createLinearGradient(cx,cy,sweepEnd.x,sweepEnd.y);
    sweep.addColorStop(0,`rgba(232,255,0,${0.04+energy*0.08})`);
    sweep.addColorStop(0.6,`rgba(232,255,0,${0.02+energy*0.04})`);
    sweep.addColorStop(1,'transparent');
    gm.beginPath();const sweepW=0.25+energy*0.15;
    gm.moveTo(cx,cy);
    gm.arc(cx,cy,Math.min(W,H)*0.6,UV.radarAngle-sweepW,UV.radarAngle);
    gm.closePath();gm.fillStyle=sweep;gm.fill();

    // Concentric grid circles
    for(let r=1;r<=4;r++){
      const rr=Math.min(W,H)*0.15*r*dpr;
      gm.strokeStyle=`rgba(232,255,0,${0.06+r*0.02})`;
      gm.lineWidth=0.5*dpr;gm.beginPath();gm.arc(cx,cy,rr,0,Math.PI*2);gm.stroke();
    }

    // EQ spikes
    if(freq){
      const numBars=128;const maxR=Math.min(W,H)*0.52;
      gm.save();
      for(let i=0;i<numBars;i++){
        const ang=(i/numBars)*Math.PI*2;
        const fi=Math.floor((i/numBars)*freq.length*0.75);
        const v=freq[fi]/255;
        const barLen=v*maxR*(0.4+energy*0.6)*dpr;
        const innerR=maxR*0.18*dpr;
        const x1=cx+Math.cos(ang)*innerR,y1=cy+Math.sin(ang)*innerR;
        const x2=cx+Math.cos(ang)*(innerR+barLen),y2=cy+Math.sin(ang)*(innerR+barLen);
        // Neon line with glow
        const hue2=v>0.7?75:v>0.4?150:180; // volt/green/cyan
        gm.strokeStyle=`hsla(${hue2},100%,${55+v*35}%,${0.5+v*0.5})`;
        gm.lineWidth=(0.8+v*2.5)*dpr;
        gm.beginPath();gm.moveTo(x1,y1);gm.lineTo(x2,y2);gm.stroke();
        // Tip dot
        if(v>0.45){gm.fillStyle=`hsla(${hue2},100%,90%,${v*0.8})`;
          gm.beginPath();gm.arc(x2,y2,1.5*dpr,0,Math.PI*2);gm.fill();}
      }
      gm.restore();
    }

    // Central subwoofer circle
    const subE2 = freq ? (()=>{let s=0;const e=Math.floor(freq.length*0.04);for(let i=0;i<e;i++)s+=freq[i]/255;return s/Math.max(e,1);})() : 0;
    const cR=(40+subE2*100)*dpr*(1+beatFlash*0.4);
    const cg=gm.createRadialGradient(cx,cy,0,cx,cy,cR);
    cg.addColorStop(0,`rgba(232,255,0,${0.15+subE2*0.3})`);
    cg.addColorStop(0.5,`rgba(232,255,0,${0.05+subE2*0.1})`);
    cg.addColorStop(1,'transparent');
    gm.fillStyle=cg;gm.beginPath();gm.arc(cx,cy,cR,0,Math.PI*2);gm.fill();
  }

  // ── MODE 2: SMOKE PARTICLES ────────────────────────────────
  else{
    let subE3=0,hiE=0;
    if(freq){
      const subEnd=Math.floor(freq.length*0.05);for(let i=0;i<subEnd;i++)subE3+=freq[i]/255;subE3/=Math.max(subEnd,1);
      const hiS=Math.floor(freq.length*0.6);for(let i=hiS;i<freq.length;i++)hiE+=freq[i]/255;hiE/=(freq.length-hiS)||1;
    }

    const pp=document.getElementById('particles');const gp=pp.getContext('2d');
    gp.clearRect(0,0,W,H);

    for(const p of UV.smoke){
      p.y+=p.vy*(1+subE3*4+hiE*2);
      p.x+=p.vx*(1+energy)+(Math.random()-0.5)*0.4;
      p.vy*=0.998; p.vx*=0.995;
      p.size*=1.008;
      p.life-=p.decay*(1+energy);
      if(p.life<=0||p.y>H/dpr+50) resetSmoke(p);
      const alpha=p.life*p.opacity*(0.7+energy*0.4);
      const sz=p.size*p.life*dpr;
      const sg=gp.createRadialGradient(p.x*dpr,p.y*dpr,0,p.x*dpr,p.y*dpr,sz);
      sg.addColorStop(0,`hsla(${p.hue},100%,60%,${alpha})`);
      sg.addColorStop(0.5,`hsla(${p.hue},90%,40%,${alpha*0.4})`);
      sg.addColorStop(1,'transparent');
      gp.fillStyle=sg;gp.beginPath();gp.arc(p.x*dpr,p.y*dpr,sz,0,Math.PI*2);gp.fill();
    }

    // Beat shockwave
    if(beatFlash>0.1){
      const sw=gm.createRadialGradient(cx,cy,0,cx,cy,Math.min(W,H)*0.5);
      sw.addColorStop(0,`rgba(232,255,0,${beatFlash*0.08})`);
      sw.addColorStop(0.4,`rgba(0,255,136,${beatFlash*0.04})`);
      sw.addColorStop(1,'transparent');
      gm.fillStyle=sw;gm.fillRect(0,0,W,H);
    }

    // Floor line
    gm.strokeStyle=`rgba(232,255,0,${0.08+energy*0.15})`;
    gm.lineWidth=1*dpr;gm.beginPath();gm.moveTo(0,H*0.96);gm.lineTo(W,H*0.96);gm.stroke();
  }
}

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