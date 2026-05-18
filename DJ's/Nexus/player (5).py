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
<title>DJ AI</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@200;400;700;900&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#050508; --t:#e8eaf0; --dim:#3a3d55;
  /* Genre themes */
  --flamenco-a:#c0392b; --flamenco-b:#e67e22; --flamenco-c:#922b21;
  --urbano-a:#00ffe1;   --urbano-b:#7b2fff;   --urbano-c:#ff00aa;
  --pop-a:#ff79c6;      --pop-b:#bd93f9;       --pop-c:#ffb86c;
  --disco-a:#ffffff;    --disco-b:#ff4081;     --disco-c:#40c4ff;
  /* Active theme vars (default: disco) */
  --th-a:#ffffff; --th-b:#ff4081; --th-c:#40c4ff;
  --th-glow:rgba(255,255,255,.18);
  --th-glow2:rgba(255,64,129,.12);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;cursor:none}
body{background:var(--bg);color:var(--t);
  font-family:'Montserrat',sans-serif;
  display:flex;align-items:center;justify-content:center}

/* ── SCANLINE OVERLAY ───────────────────────────────────────── */
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:9999;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,
    rgba(0,0,0,.04) 2px,rgba(0,0,0,.04) 4px);}

/* ════════════════════════════════════════════════════════════
   IDLE SCREEN
════════════════════════════════════════════════════════════ */
#idle{
  position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:36px;z-index:200;background:var(--bg);
  transition:opacity 1.4s cubic-bezier(.7,0,.3,1),visibility 1.4s}
#idle.off{opacity:0;visibility:hidden;pointer-events:none}

.idle-ring{position:relative;width:160px;height:160px}
.idle-ring svg{position:absolute;inset:0;animation:ringrot 8s linear infinite}
.idle-ring svg circle{fill:none;stroke-width:1;stroke-dasharray:4 8;
  stroke:rgba(255,255,255,.12)}
.idle-ring svg.r2{animation-duration:13s;animation-direction:reverse}
.idle-ring svg.r2 circle{stroke:rgba(255,255,255,.06);stroke-dasharray:2 14}

.play-btn{
  position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:72px;height:72px;border-radius:50%;border:none;cursor:pointer;
  background:rgba(255,255,255,.94);
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 40px rgba(255,255,255,.3),0 0 80px rgba(255,255,255,.1);
  transition:all .3s}
.play-btn:hover{transform:translate(-50%,-50%) scale(1.1);
  box-shadow:0 0 60px rgba(255,255,255,.5),0 0 120px rgba(255,255,255,.2)}
.play-btn:disabled{opacity:.25;cursor:not-allowed;
  box-shadow:none;transform:translate(-50%,-50%)}
.play-btn-tri{
  width:0;height:0;margin-left:6px;
  border-top:16px solid transparent;
  border-bottom:16px solid transparent;
  border-left:26px solid #050508}

.idle-title{
  font-weight:900;font-size:clamp(48px,10vw,96px);
  letter-spacing:16px;text-transform:uppercase;
  color:transparent;
  -webkit-text-stroke:1px rgba(255,255,255,.85);
  animation:titlepulse 4s ease-in-out infinite}
@keyframes titlepulse{
  0%,100%{-webkit-text-stroke-color:rgba(255,255,255,.6)}
  50%{-webkit-text-stroke-color:rgba(255,255,255,.95);
      text-shadow:0 0 80px rgba(255,255,255,.15)}}
@keyframes ringrot{to{transform:rotate(360deg)}}

.idle-sub{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:5px;
  color:var(--dim);text-transform:uppercase}
.idle-count{font-family:'Space Mono',monospace;font-size:11px;
  color:rgba(255,255,255,.35);letter-spacing:2px}
.idle-count b{color:rgba(255,255,255,.7)}

/* ════════════════════════════════════════════════════════════
   APP SHELL
════════════════════════════════════════════════════════════ */
#app{
  position:fixed;inset:0;opacity:0;pointer-events:none;
  transition:opacity 1.6s cubic-bezier(.7,0,.3,1)}
#app.on{opacity:1;pointer-events:none}  /* pointer-events:none = no hay interacción */

/* ── FULL-SCREEN CANVAS ──────────────────────────────────── */
#cvs-bg{position:fixed;inset:0;z-index:1}
#cvs-main{position:fixed;inset:0;z-index:2}
#cvs-particles{position:fixed;inset:0;z-index:3}

/* ── GENRE THEME OVERLAY ─────────────────────────────────── */
#theme-overlay{
  position:fixed;inset:0;z-index:4;pointer-events:none;
  transition:background 4s ease}

/* ── GLASSMORPHISM INFO PANEL ────────────────────────────── */
#panel{
  position:fixed;bottom:40px;left:50%;transform:translateX(-50%);
  z-index:10;
  background:rgba(5,5,8,.55);
  backdrop-filter:blur(24px) saturate(180%);
  -webkit-backdrop-filter:blur(24px) saturate(180%);
  border:1px solid rgba(255,255,255,.08);
  border-radius:20px;
  padding:20px 32px 18px;
  min-width:420px;max-width:640px;
  box-shadow:0 8px 64px rgba(0,0,0,.7),
             inset 0 1px 0 rgba(255,255,255,.08);
  transition:border-color 2s, box-shadow 2s}

.panel-track{
  font-weight:900;font-size:clamp(20px,3.5vw,32px);
  letter-spacing:1px;line-height:1;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  color:#fff;margin-bottom:8px;
  transition:color 2s}
.panel-meta{
  display:flex;align-items:center;gap:14px;
  font-family:'Space Mono',monospace;font-size:10px;
  color:rgba(255,255,255,.45);letter-spacing:2px}
.panel-bpm{color:var(--th-a);font-weight:700;font-size:13px;
  transition:color 2s}
.panel-phase{
  padding:2px 8px;border-radius:6px;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(255,255,255,.04);
  font-size:9px;letter-spacing:3px;text-transform:uppercase;
  transition:border-color 2s}
.panel-key{color:rgba(255,255,255,.3)}

/* MIX INDICATOR */
#mix-indicator{
  position:fixed;top:36px;left:50%;transform:translateX(-50%);
  z-index:10;
  font-family:'Space Mono',monospace;font-size:9px;letter-spacing:4px;
  text-transform:uppercase;color:rgba(255,255,255,.5);
  padding:6px 16px;border-radius:20px;
  background:rgba(5,5,8,.5);
  backdrop-filter:blur(12px);
  border:1px solid rgba(255,255,255,.06);
  opacity:0;transition:opacity .6s}
#mix-indicator.on{opacity:1}
.mix-dot-live{
  display:inline-block;width:5px;height:5px;border-radius:50%;
  background:var(--th-a);margin-right:8px;
  animation:blink .8s step-end infinite;
  transition:background 2s}
@keyframes blink{50%{opacity:0}}

/* BEAT FLASH OVERLAY */
#beat-flash{
  position:fixed;inset:0;z-index:5;pointer-events:none;
  opacity:0;transition:opacity .05s}

/* MODE LABEL (top-right) */
#mode-lbl{
  position:fixed;top:36px;right:36px;z-index:10;
  font-family:'Space Mono',monospace;font-size:8px;letter-spacing:3px;
  text-transform:uppercase;color:rgba(255,255,255,.2);
  transition:opacity .5s}

/* ── GENRE THEMES ─────────────────────────────────────────── */
body.theme-flamenco{
  --th-a:var(--flamenco-a);--th-b:var(--flamenco-b);--th-c:var(--flamenco-c);
  --th-glow:rgba(192,57,43,.2);--th-glow2:rgba(230,126,34,.12)}
body.theme-urbano{
  --th-a:var(--urbano-a);--th-b:var(--urbano-b);--th-c:var(--urbano-c);
  --th-glow:rgba(0,255,225,.15);--th-glow2:rgba(123,47,255,.12)}
body.theme-pop{
  --th-a:var(--pop-a);--th-b:var(--pop-b);--th-c:var(--pop-c);
  --th-glow:rgba(255,121,198,.15);--th-glow2:rgba(189,147,249,.12)}
body.theme-disco{
  --th-a:var(--disco-a);--th-b:var(--disco-b);--th-c:var(--disco-c);
  --th-glow:rgba(255,255,255,.14);--th-glow2:rgba(255,64,129,.1)}

/* ── THEME TRANSITION ─────────────────────────────────────── */
#panel{border-color:var(--th-glow)}
</style>
</head>
<body class="theme-disco">

<!-- IDLE -->
<div id="idle">
  <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:6px;
    color:rgba(255,255,255,.2);text-transform:uppercase;margin-bottom:-20px">
    sesión autónoma · mezcla inteligente
  </div>
  <div class="idle-title">DJ AI</div>
  <div class="idle-ring">
    <svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">
      <circle cx="80" cy="80" r="70" stroke-dasharray="4 8" stroke="rgba(255,255,255,.12)" fill="none" stroke-width="1"/>
    </svg>
    <svg class="r2" viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">
      <circle cx="80" cy="80" r="55" stroke-dasharray="2 14" stroke="rgba(255,255,255,.07)" fill="none" stroke-width="1"/>
    </svg>
    <button class="play-btn" id="btnStart" disabled>
      <div class="play-btn-tri"></div>
    </button>
  </div>
  <div class="idle-count" id="idleInfo">Cargando biblioteca...</div>
  <div class="idle-sub">dale play · la ia hace todo</div>
</div>

<!-- APP -->
<div id="app">
  <canvas id="cvs-bg"></canvas>
  <canvas id="cvs-main"></canvas>
  <canvas id="cvs-particles"></canvas>
  <div id="theme-overlay"></div>
  <div id="beat-flash"></div>

  <!-- Mix indicator (top center) -->
  <div id="mix-indicator">
    <span class="mix-dot-live"></span>
    <span id="mixLabel">mezclando</span>
  </div>

  <!-- Viz mode label (top right) -->
  <div id="mode-lbl">—</div>

  <!-- Main info panel (bottom center) -->
  <div id="panel">
    <div class="panel-track" id="panelTitle">—</div>
    <div class="panel-meta">
      <span class="panel-bpm" id="panelBpm">—</span>
      <span class="panel-phase" id="panelPhase">warm-up</span>
      <span class="panel-key" id="panelKey"></span>
      <span id="panelEgy" style="color:rgba(255,255,255,.25)"></span>
    </div>
  </div>
</div>

<script>
// ════════════════════════════════════════════════════════════════
//  DJ AI  ·  Immersive Visual Engine
//  Audio engine preservado íntegro — solo el frontend es nuevo.
// ════════════════════════════════════════════════════════════════

const AC = window.AudioContext || window.webkitAudioContext;
let ctx = null;

const PHASE_ORDER  = ['warm-up','first-build','first-peak','breakdown','second-build','second-peak','outro'];
const PHASE_LABELS = {'warm-up':'WARM','first-build':'BUILD','first-peak':'PEAK I',
  'breakdown':'DOWN','second-build':'BUILD II','second-peak':'PEAK II','outro':'OUTRO'};
const STYLE_LABELS = {guetta:'⚡ GUETTA', avicii:'🌅 AVICII', progressive:'〰 PROG'};

const S = {
  lib:[], cur:null, curFile:null,
  nxt:null, nxtPlan:null, nxtScore:0, nxtPhase:'warm-up',
  played:[], playedSet:new Set(), count:0,
  playing:false, mixing:false,
  mixStart:0, mixDur:8, mixStyle:'guetta',
  deck:'A',
  startAt:0,
  bufs:{},
  decks:{A:{}, B:{}},
  modOk:false,
  silenceStart:null, lastRms:1.0, silenceTriggered:false,
  beatLastTime:0, beatThresh:0.15, beatHistory:[],
  lastBpm:0, lastBeat:0,
  sessionTracks:[], sessionStartTime:0,
  _beatSnapScheduled:false,
  cueing:false, cueSrc:null, cueGain:null,
};

// ═══════════════════════════════════════════════════════════════
//  VISUAL ENGINE
// ═══════════════════════════════════════════════════════════════

// — Theme detection from track name/metadata —
function detectTheme(track) {
  if (!track) return 'disco';
  const n = (track.name||'').toLowerCase();
  const k = (track.key||'').toLowerCase();
  const bpm = track.bpm || 120;
  const e   = track.energia || 50;

  // Flamenco hints: bulería, rumba, sevillana, flamenc, etc.
  if (/flamenco|bulería|rumba|sevillana|tangos|soleá|farruca|copla|guitarra/i.test(n))
    return 'flamenco';
  // Urbano: trap, reggaeton, drill, dembow, perreo, etc.
  if (/reggaeton|trap|drill|dembow|perreo|urban|rap|hip.?hop|freestyle|bachata|salsa/i.test(n))
    return 'urbano';
  // Pop: kpop, pop, indie-pop
  if (/pop|kpop|indie|electropop|synthpop|bubblegum/i.test(n))
    return 'pop';

  // Heurístico por BPM/energía si no hay keywords
  if (bpm < 100 && e < 60) return 'flamenco';
  if (bpm >= 85 && bpm <= 105 && e >= 55) return 'urbano';
  if (bpm >= 100 && bpm <= 130 && e < 70) return 'pop';
  return 'disco';  // alta energía electrónica
}

function applyTheme(theme) {
  document.body.className = 'theme-' + theme;
  V.theme = theme;
  // Update panel glow
  const panel = document.getElementById('panel');
  panel.style.boxShadow =
    '0 8px 64px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.08),' +
    '0 0 40px var(--th-glow)';
}

// — Visualization state —
const V = {
  theme: 'disco',
  mode: 0,         // 0=spectrum, 1=particles, 2=typography, 3=radial
  modeTimer: 0,    // seconds in current mode
  modeDuration: 45,// rotate every 45s
  particles: [],
  frame: 0,
  beatPulse: 0,    // 0-1 decay
  energy: 0,       // smoothed energy
  bass: 0,         // smoothed bass
  bpmInterval: 0.5,// seconds between beats
  lastBeatFlash: 0,
};

const MODES = ['SPECTRUM','PARTICLES','TYPOGRAPHIC','RADIAL'];

// Initialize particles
function initParticles(W, H) {
  V.particles = [];
  const n = 120;
  for (let i = 0; i < n; i++) {
    V.particles.push({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      r: Math.random() * 2 + 0.5,
      alpha: Math.random() * 0.6 + 0.2,
      life: Math.random(),
    });
  }
}

// — Color helpers per theme —
function themeColor(alpha, variant = 0) {
  const t = V.theme;
  if (t === 'flamenco') {
    const cols = [[192,57,43],[230,126,34],[146,43,33]];
    const [r,g,b] = cols[variant % 3];
    return `rgba(${r},${g},${b},${alpha})`;
  }
  if (t === 'urbano') {
    const cols = [[0,255,225],[123,47,255],[255,0,170]];
    const [r,g,b] = cols[variant % 3];
    return `rgba(${r},${g},${b},${alpha})`;
  }
  if (t === 'pop') {
    const cols = [[255,121,198],[189,147,249],[255,184,108]];
    const [r,g,b] = cols[variant % 3];
    return `rgba(${r},${g},${b},${alpha})`;
  }
  // disco
  const cols = [[255,255,255],[255,64,129],[64,196,255]];
  const [r,g,b] = cols[variant % 3];
  return `rgba(${r},${g},${b},${alpha})`;
}

// — Canvas references —
let cvsBg, cvsMn, cvsPt, gBg, gMn, gPt;

function setupCanvases() {
  cvsBg = document.getElementById('cvs-bg');
  cvsMn = document.getElementById('cvs-main');
  cvsPt = document.getElementById('cvs-particles');
  gBg   = cvsBg.getContext('2d');
  gMn   = cvsMn.getContext('2d');
  gPt   = cvsPt.getContext('2d');
  resizeCanvases();
}

function resizeCanvases() {
  const W = window.innerWidth, H = window.innerHeight, dpr = devicePixelRatio || 1;
  [cvsBg, cvsMn, cvsPt].forEach(c => {
    c.width  = W * dpr; c.height = H * dpr;
    c.style.width  = W + 'px'; c.style.height = H + 'px';
    c.getContext('2d').setTransform(dpr,0,0,dpr,0,0);
  });
  initParticles(W, H);
}
window.addEventListener('resize', resizeCanvases);

// ═══ DRAW BACKGROUND ════════════════════════════════════════════
function drawBackground() {
  const W = cvsBg.offsetWidth, H = cvsBg.offsetHeight;
  const t = V.theme, e = V.energy, bass = V.bass;

  // Base fill with trail
  gBg.fillStyle = `rgba(5,5,8,${0.12 + (1-e)*0.05})`;
  gBg.fillRect(0, 0, W, H);

  if (t === 'flamenco') {
    // Warm vignette center glow
    const r = gBg.createRadialGradient(W/2, H/2, 0, W/2, H/2, W*0.7);
    r.addColorStop(0, `rgba(192,57,43,${0.06 + bass*0.12})`);
    r.addColorStop(0.4, `rgba(146,43,33,${0.03 + bass*0.05})`);
    r.addColorStop(1, 'transparent');
    gBg.fillStyle = r; gBg.fillRect(0,0,W,H);

    // Rhythmic "palma" flashes at beat
    if (V.beatPulse > 0.1) {
      gBg.fillStyle = `rgba(230,126,34,${V.beatPulse * 0.08})`;
      gBg.fillRect(0,0,W,H);
    }

  } else if (t === 'urbano') {
    // Dark with neon edge glows
    const gl = gBg.createLinearGradient(0, 0, W, H);
    gl.addColorStop(0, `rgba(0,255,225,${0.03 + bass*0.06})`);
    gl.addColorStop(0.5, 'transparent');
    gl.addColorStop(1, `rgba(123,47,255,${0.03 + e*0.05})`);
    gBg.fillStyle = gl; gBg.fillRect(0,0,W,H);

    // Bass vibration lines
    if (V.beatPulse > 0.3) {
      const lc = Math.floor(V.beatPulse * 6);
      for (let i = 0; i < lc; i++) {
        const y = H * (0.3 + Math.random() * 0.4);
        gBg.strokeStyle = `rgba(255,0,170,${V.beatPulse * 0.15})`;
        gBg.lineWidth = Math.random() * 1;
        gBg.beginPath(); gBg.moveTo(0,y); gBg.lineTo(W,y); gBg.stroke();
      }
    }

  } else if (t === 'pop') {
    // Soft pastel nebula
    const r1 = gBg.createRadialGradient(W*0.3, H*0.4, 0, W*0.3, H*0.4, W*0.5);
    r1.addColorStop(0, `rgba(255,121,198,${0.04 + e*0.04})`);
    r1.addColorStop(1, 'transparent');
    gBg.fillStyle = r1; gBg.fillRect(0,0,W,H);
    const r2 = gBg.createRadialGradient(W*0.7, H*0.6, 0, W*0.7, H*0.6, W*0.4);
    r2.addColorStop(0, `rgba(189,147,249,${0.04 + bass*0.04})`);
    r2.addColorStop(1, 'transparent');
    gBg.fillStyle = r2; gBg.fillRect(0,0,W,H);

  } else {
    // disco — strobo
    if (V.beatPulse > 0.6 && Math.random() > 0.4) {
      gBg.fillStyle = `rgba(255,255,255,${V.beatPulse * 0.05})`;
      gBg.fillRect(0,0,W,H);
    }
    // Laser beams
    if (V.beatPulse > 0.4) {
      const cx = W/2, cy = H*0.15;
      for (let i = 0; i < 5; i++) {
        const angle = (-Math.PI*0.4) + (i/4)*Math.PI*0.8;
        const colors = ['rgba(255,64,129','rgba(64,196,255','rgba(255,255,255',
                        'rgba(255,64,129','rgba(64,196,255'];
        gBg.strokeStyle = colors[i] + `,${ V.beatPulse * 0.18})`;
        gBg.lineWidth = 1;
        gBg.beginPath();
        gBg.moveTo(cx, cy);
        gBg.lineTo(cx + Math.cos(angle)*W, cy + Math.sin(angle)*H*1.2);
        gBg.stroke();
      }
    }
  }
}

// ═══ DRAW SPECTRUM (mode 0) ═══════════════════════════════════
function drawSpectrum(freqData) {
  const W = cvsMn.offsetWidth, H = cvsMn.offsetHeight;
  gMn.clearRect(0, 0, W, H);

  const n = freqData.length;
  const bw = (W / n) * 1.3;

  for (let i = 0; i < n; i++) {
    const v = freqData[i] / 255;
    if (v < 0.02) continue;
    const bh = v * H * 0.75;
    const x = i * bw;
    const frac = i / n;

    let col;
    if (V.theme === 'flamenco') {
      const r = Math.floor(192 + 38*v), g = Math.floor(57 + 69*v * (1-frac)), b = Math.floor(43);
      col = `rgba(${r},${g},${b},${0.5+v*0.5})`;
    } else if (V.theme === 'urbano') {
      const hue = frac < 0.4 ? 174 : (frac < 0.7 ? 270 : 315);
      col = `hsla(${hue},100%,${50+v*30}%,${0.4+v*0.6})`;
    } else if (V.theme === 'pop') {
      const hue = 300 + frac * 80;
      col = `hsla(${hue},80%,${65+v*20}%,${0.4+v*0.55})`;
    } else {
      // disco: white + pink mirror
      col = frac < 0.5
        ? `rgba(${Math.floor(200+55*v)},${Math.floor(200+55*v)},255,${0.4+v*0.5})`
        : `rgba(255,${Math.floor(64+v*100)},${Math.floor(129+v*80)},${0.4+v*0.5})`;
    }

    gMn.fillStyle = col;
    gMn.fillRect(x, H - bh, bw - 0.8, bh);
    // Mirror reflection
    gMn.globalAlpha = 0.12;
    gMn.fillRect(x, H, bw - 0.8, bh * 0.2);
    gMn.globalAlpha = 1;
  }
}

// ═══ DRAW RADIAL (mode 3) ═════════════════════════════════════
function drawRadial(freqData) {
  const W = cvsMn.offsetWidth, H = cvsMn.offsetHeight;
  const cx = W/2, cy = H/2;
  const baseR = Math.min(W,H) * 0.18;

  gMn.clearRect(0,0,W,H);

  const n = Math.min(freqData.length, 180);
  for (let i = 0; i < n; i++) {
    const v = freqData[i] / 255;
    if (v < 0.02) continue;
    const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
    const r1 = baseR + V.beatPulse * 20;
    const r2 = r1 + v * Math.min(W,H) * 0.28;
    const x1 = cx + Math.cos(angle) * r1;
    const y1 = cy + Math.sin(angle) * r1;
    const x2 = cx + Math.cos(angle) * r2;
    const y2 = cy + Math.sin(angle) * r2;

    gMn.strokeStyle = themeColor(0.4 + v * 0.6, Math.floor(i / (n/3)));
    gMn.lineWidth = 1.5 + v * 2;
    gMn.beginPath(); gMn.moveTo(x1,y1); gMn.lineTo(x2,y2); gMn.stroke();
  }

  // Center circle
  gMn.beginPath();
  gMn.arc(cx, cy, baseR + V.beatPulse * 15, 0, Math.PI*2);
  gMn.strokeStyle = themeColor(0.25 + V.beatPulse * 0.3, 0);
  gMn.lineWidth = 1;
  gMn.stroke();
}

// ═══ DRAW PARTICLES (mode 1) ══════════════════════════════════
function drawParticlesViz(freqData) {
  const W = cvsMn.offsetWidth, H = cvsMn.offsetHeight;
  gMn.clearRect(0,0,W,H);

  const e = V.energy, bp = V.beatPulse;

  V.particles.forEach((p, i) => {
    // Influence by audio
    const fi = Math.floor((i / V.particles.length) * freqData.length);
    const fv = (freqData[fi] || 0) / 255;
    p.vx += (Math.random()-0.5) * 0.06 * (1 + fv * 3);
    p.vy += (Math.random()-0.5) * 0.06 * (1 + fv * 3);
    p.vx *= 0.97; p.vy *= 0.97;

    // Beat impulse
    if (bp > 0.5) {
      const dx = p.x - W/2, dy = p.y - H/2;
      const dist = Math.sqrt(dx*dx+dy*dy) || 1;
      p.vx += (dx/dist) * bp * 0.8;
      p.vy += (dy/dist) * bp * 0.8;
    }

    p.x += p.vx; p.y += p.vy;
    // Wrap
    if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
    if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;

    const alpha = p.alpha * (0.3 + fv * 0.7);
    const r = p.r * (1 + fv * 2 + bp * 1.5);

    gMn.beginPath();
    gMn.arc(p.x, p.y, r, 0, Math.PI*2);
    gMn.fillStyle = themeColor(alpha, i % 3);
    gMn.fill();
  });
}

// ═══ DRAW TYPOGRAPHY (mode 2) ════════════════════════════════
let typoTimer = 0;
function drawTypography(freqData) {
  const W = cvsMn.offsetWidth, H = cvsMn.offsetHeight;
  gMn.clearRect(0,0,W,H);
  typoTimer += 1/60;

  if (!S.cur) return;

  const bpm = S.cur.bpm || 120;
  const phase = S.nxtPhase || 'warm-up';
  const e = V.energy;

  // Pulsing BPM display
  const bpmSize = 120 + V.beatPulse * 60;
  gMn.font = `900 ${bpmSize}px 'Montserrat', sans-serif`;
  gMn.textAlign = 'center';
  gMn.textBaseline = 'middle';
  gMn.fillStyle = themeColor(0.04 + V.beatPulse * 0.06, 0);
  gMn.fillText(Math.round(bpm), W/2, H/2 - 20);

  // BPM label outline
  gMn.font = `900 ${80 + V.beatPulse*30}px 'Montserrat', sans-serif`;
  gMn.fillStyle = themeColor(0.12 + V.beatPulse * 0.18, 0);
  gMn.fillText(Math.round(bpm), W/2 + 1, H/2 - 20 + 1);

  // Phase label
  const phaseLabel = PHASE_LABELS[phase] || phase.toUpperCase();
  gMn.font = `200 ${18 + e*8}px 'Montserrat', sans-serif`;
  gMn.fillStyle = themeColor(0.3 + e*0.3, 1);
  gMn.letterSpacing = '12px';
  gMn.fillText(phaseLabel, W/2, H/2 + 70);
  gMn.letterSpacing = '0px';

  // Track name — scrolling
  const titleSize = Math.min(28 + e*10, 42);
  gMn.font = `700 ${titleSize}px 'Montserrat', sans-serif`;
  gMn.fillStyle = themeColor(0.15 + e*0.15, 2);
  const name = S.cur.name.toUpperCase();
  const tw = gMn.measureText(name).width;
  const tx = (W/2 - tw/2 - (typoTimer * 30) % (tw + W)) + W/2;
  gMn.fillText(name, tx % (W + tw) - tw/2, H * 0.82);
}

// ═══ MAIN VISUAL LOOP ════════════════════════════════════════
function vizLoop() {
  requestAnimationFrame(vizLoop);
  V.frame++;

  // Get audio data
  let freqData = new Uint8Array(64);
  let hasAudio = false;
  if (ctx && S.playing) {
    const dk = S.decks[S.deck];
    if (dk && dk.analyser) {
      const fd = new Uint8Array(dk.analyser.frequencyBinCount);
      dk.analyser.getByteFrequencyData(fd);
      freqData = fd;
      hasAudio = true;
    }
    // During mix, blend both decks
    if (S.mixing) {
      const other = S.deck === 'A' ? 'B' : 'A';
      const dkO = S.decks[other];
      if (dkO && dkO.analyser) {
        const fd2 = new Uint8Array(dkO.analyser.frequencyBinCount);
        dkO.analyser.getByteFrequencyData(fd2);
        for (let i = 0; i < freqData.length && i < fd2.length; i++) {
          freqData[i] = Math.max(freqData[i], fd2[i]);
        }
      }
    }
  }

  // Compute energy & bass
  let sumAll = 0, sumBass = 0;
  const bassN = Math.floor(freqData.length * 0.08);
  for (let i = 0; i < freqData.length; i++) {
    sumAll += freqData[i];
    if (i < bassN) sumBass += freqData[i];
  }
  const rawE    = sumAll / (freqData.length * 255);
  const rawBass = sumBass / (bassN * 255);
  V.energy = V.energy * 0.88 + rawE * 0.12;
  V.bass   = V.bass   * 0.85 + rawBass * 0.15;

  // Beat pulse decay
  V.beatPulse = Math.max(0, V.beatPulse - 0.04);

  // Mode rotation
  if (S.playing) {
    V.modeTimer += 1/60;
    if (V.modeTimer > V.modeDuration) {
      V.modeTimer = 0;
      V.mode = (V.mode + 1) % MODES.length;
      // Vary duration 30-60s
      V.modeDuration = 30 + Math.random() * 30;
      document.getElementById('mode-lbl').textContent = MODES[V.mode];
    }
  }

  drawBackground();

  // Draw main viz based on mode
  if (hasAudio || V.frame % 3 === 0) {
    if (V.mode === 0) drawSpectrum(freqData);
    else if (V.mode === 1) drawParticlesViz(freqData);
    else if (V.mode === 2) drawTypography(freqData);
    else drawRadial(freqData);
  }

  // Particles overlay (always subtle in all modes)
  if (V.mode !== 1) drawParticlesSubtle();
}

function drawParticlesSubtle() {
  const W = cvsPt.offsetWidth, H = cvsPt.offsetHeight;
  gPt.clearRect(0,0,W,H);
  const n = Math.floor(V.particles.length * 0.3);
  for (let i = 0; i < n; i++) {
    const p = V.particles[i];
    p.x += p.vx * 0.3; p.y += p.vy * 0.3;
    if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
    if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
    gPt.beginPath();
    gPt.arc(p.x, p.y, p.r * 0.6, 0, Math.PI*2);
    gPt.fillStyle = themeColor(p.alpha * 0.15, i%3);
    gPt.fill();
  }
}

// ═══════════════════════════════════════════════════════════════
//  AUDIO ENGINE (preservado íntegro)
// ═══════════════════════════════════════════════════════════════

function ic() {
  if (!ctx) {
    ctx = new AC();
    S.comp = ctx.createDynamicsCompressor();
    S.comp.threshold.value = -14;
    S.comp.knee.value      = 6;
    S.comp.ratio.value     = 4;
    S.comp.attack.value    = 0.003;
    S.comp.release.value   = 0.25;
    S.mAnl = ctx.createAnalyser();
    S.mAnl.fftSize = 1024;
    S.comp.connect(S.mAnl);
    S.mAnl.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();

  if (!S.reverb) {
    S.reverb    = ctx.createConvolver();
    S.reverbGain = ctx.createGain();
    S.reverbGain.gain.value = 0;
    const rate = ctx.sampleRate;
    const len  = Math.floor(rate * 2.5);
    const ir   = ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = ir.getChannelData(ch);
      for (let i = 0; i < len; i++)
        d[i] = (Math.random()*2-1) * Math.pow(1-i/len, 2.5);
    }
    S.reverb.buffer = ir;
    S.comp.connect(S.reverbGain);
    S.reverbGain.connect(S.reverb);
    S.reverb.connect(ctx.destination);
  }
  if (!S.cueOutGain) {
    S.cueOutGain = ctx.createGain();
    S.cueOutGain.gain.value = 0.85;
    S.cueOutGain.connect(ctx.destination);
  }
}

async function boot() {
  const [lr, mr] = await Promise.all([fetch('/api/library'), fetch('/api/modules')]);
  S.lib  = await lr.json();
  const m = await mr.json();
  S.modOk = m.ok;
  const info = document.getElementById('idleInfo');
  info.innerHTML = `<b>${S.lib.length}</b> canción${S.lib.length!==1?'es':''} · arco automático`;
  document.getElementById('btnStart').disabled = S.lib.length === 0;
  if (!S.lib.length) info.textContent = 'Pon MP3/WAV en musica/canciones/';
}

document.getElementById('btnStart').addEventListener('click', async () => {
  ic();
  document.getElementById('idle').classList.add('off');
  document.getElementById('app').classList.add('on');
  setupCanvases();
  initParticles(window.innerWidth, window.innerHeight);
  vizLoop();
  const first = chooseFirst();
  await begin(first);
});

function chooseFirst() {
  if (!S.lib.length) return null;
  const s = [...S.lib].sort((a,b)=>(a.energia||50)-(b.energia||50));
  return s[Math.floor(s.length * 0.18)] || s[0];
}

async function begin(t) {
  S.cur = t; S.curFile = t.file; S.deck = 'A';
  S.playing = true; S.startAt = 0;
  S.played.push(t.file); S.playedSet.add(t.file); S.count = 1;
  S.sessionStartTime = ctx.currentTime;
  S.sessionTracks = [{track:t, startCtxTime:ctx.currentTime}];
  updateNP(t, 'warm-up');
  const startPos = t.start_position ?? 0;
  await playDeck('A', t, startPos);
  loop();
  askNext(t, 0);
  // Apply initial theme
  const theme = detectTheme(t);
  applyTheme(theme);
}

async function askNext(t, ct) {
  if (!t) return;
  try {
    const pe  = encodeURIComponent(JSON.stringify([...S.playedSet]));
    const pl  = encodeURIComponent(JSON.stringify(
      S.played.slice(-3).map(f=>({file:f, key:(S.lib.find(x=>x.file===f)||{}).key||''}))
    ));
    const url = `/api/next?current=${encodeURIComponent(t.file)}&time=${ct.toFixed(1)}&played=${pe}&count=${S.count}&played_list=${pl}`;
    const d   = await (await fetch(url)).json();
    if (d.error) { S.nxt=null; return; }
    S.nxt=d.track; S.nxtPlan=d.plan; S.nxtScore=d.score; S.nxtPhase=d.phase;
    updateArc(d.phase, d.target_energy);
  } catch(e) {}
}

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

function resetGraph(dk) {
  const d = S.decks[dk];
  if (d.src) { try{d.src.stop();}catch(e){} d.src = null; }
  d.preGain  = ctx.createGain();
  d.hipass   = ctx.createBiquadFilter();
  d.lopass   = ctx.createBiquadFilter();
  d.analyser = ctx.createAnalyser();
  d.analyser.fftSize = 256;
  d.hipass.type = 'highpass'; d.hipass.Q.value = 0.71;
  d.lopass.type = 'lowpass';  d.lopass.Q.value = 0.71;
  d.preGain.connect(d.hipass);
  d.hipass.connect(d.lopass);
  d.lopass.connect(d.analyser);
  d.analyser.connect(S.comp);
  return d;
}

async function playDeck(dk, track, offset=0) {
  const buf = await loadBuf(track);
  if (!track.duracion_segundos || track.duracion_segundos === 0)
    track.duracion_segundos = buf.duration;
  const d = resetGraph(dk);
  const src = ctx.createBufferSource();
  src.buffer = buf;
  if (dk !== S.deck && track.bpm && S.cur && S.cur.bpm && track.bpm > 0) {
    const ratio = S.cur.bpm / track.bpm;
    src.playbackRate.setValueAtTime(ratio, ctx.currentTime);
    d._bpmRatio = ratio; d._bpmTarget = 1.0;
  } else {
    src.playbackRate.value = 1.0;
    d._bpmRatio = 1.0; d._bpmTarget = 1.0;
  }
  src.connect(d.preGain);
  d.preGain.gain.setValueAtTime(dk === S.deck ? 1 : 0, ctx.currentTime);
  d.hipass.frequency.setValueAtTime(dk === S.deck ? 20 : 320, ctx.currentTime);
  d.lopass.frequency.setValueAtTime(20000, ctx.currentTime);
  src.start(0, offset);
  d.src = src;
  d.startedAt = ctx.currentTime - offset;
  if (dk === S.deck) S.startAt = d.startedAt;
  src.onended = () => {
    if (S.playing && dk === S.deck && !S.mixing) doMix();
  };
}

function getTime() {
  return !S.playing || !ctx ? 0 : Math.max(0, ctx.currentTime - S.startAt);
}

async function doMix() {
  if (S.mixing || !S.playing) return;
  const nxt = S.nxt;
  if (!nxt) {
    askNext(S.cur, getTime());
    setTimeout(()=>{ if(!S.mixing && S.nxt) doMix(); }, 1200);
    return;
  }
  const plan   = S.nxtPlan;
  const cfDur  = plan ? (plan.mix_duration||8) : 8;
  const enterAt= plan ? (plan.start_next_time||0) : 0;
  const style  = plan ? (plan.style||'guetta') : 'guetta';

  S.mixing   = true;
  S.mixStart = ctx.currentTime;
  S.mixDur   = cfDur;
  S.mixStyle = style;

  // Show mix indicator
  const mi = document.getElementById('mix-indicator');
  mi.classList.add('on');
  document.getElementById('mixLabel').textContent = (STYLE_LABELS[style]||style).replace(/^[^ ]+ /,'').toLowerCase();

  if (S.reverb && S.reverbGain) {
    const reverbPeak = style==='avicii' ? 0.35 : style==='progressive' ? 0.10 : 0.18;
    const rg = S.reverbGain.gain;
    rg.cancelScheduledValues(ctx.currentTime);
    rg.setValueAtTime(0, ctx.currentTime);
    rg.linearRampToValueAtTime(reverbPeak,     ctx.currentTime + cfDur*0.25);
    rg.linearRampToValueAtTime(reverbPeak*0.5, ctx.currentTime + cfDur*0.75);
    rg.linearRampToValueAtTime(0,              ctx.currentTime + cfDur*1.0);
  }

  const out = S.deck;
  const inp = out === 'A' ? 'B' : 'A';
  await playDeck(inp, nxt, enterAt);
  const inpStartedAt = ctx.currentTime - enterAt;

  const t0   = ctx.currentTime;
  const dOut = S.decks[out];
  const dIn  = S.decks[inp];
  const steps= Math.round(cfDur * 30);

  dOut.preGain.gain.cancelScheduledValues(t0);
  dIn.preGain.gain.cancelScheduledValues(t0);
  dOut.hipass.frequency.cancelScheduledValues(t0);
  dOut.lopass.frequency.cancelScheduledValues(t0);
  dIn.hipass.frequency.cancelScheduledValues(t0);
  dIn.lopass.frequency.cancelScheduledValues(t0);

  dOut.preGain.gain.setValueAtTime(1, t0);
  dIn.preGain.gain.setValueAtTime(0,  t0);
  dOut.lopass.frequency.setValueAtTime(20000, t0);
  dOut.hipass.frequency.setValueAtTime(20, t0);
  dIn.lopass.frequency.setValueAtTime(20000, t0);

  if (style === 'progressive' || style === 'avicii') {
    dIn.hipass.frequency.setValueAtTime(20, t0);
  } else {
    dIn.hipass.frequency.setValueAtTime(320, t0);
  }

  if (style !== 'progressive' && dIn.src && dIn._bpmRatio && dIn._bpmRatio !== 1.0) {
    dIn.src.playbackRate.cancelScheduledValues(t0);
    dIn.src.playbackRate.setValueAtTime(dIn._bpmRatio, t0);
    dIn.src.playbackRate.exponentialRampToValueAtTime(1.0, t0 + cfDur);
  }

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
    const f = i / steps;
    const tAt = t0 + f * cfDur;
    let vOut, vIn;

    if (style === 'progressive') {
      vOut = Math.cos(f * Math.PI/2);
      vIn  = Math.sin(f * Math.PI/2);
    } else if (style === 'avicii') {
      vOut = Math.pow(Math.cos(f * Math.PI/2), 1.2);
      vIn  = 1/(1+Math.exp(-10*(f-0.35)));
    } else {
      vOut = Math.pow(1-f, 0.9);
      vIn  = 1/(1+Math.exp(-16*(f-0.65)));
    }

    dOut.preGain.gain.setValueAtTime(Math.max(0,vOut), tAt);
    dIn.preGain.gain.setValueAtTime(Math.min(1,vIn),   tAt);

    const power = Math.sqrt(vOut*vOut + vIn*vIn);
    const cGain = power > 0.01 ? Math.min(1.35, 1/power) : 1;
    S.compGain.gain.setValueAtTime(cGain, tAt);

    if (style === 'progressive') {
      const loFreq = f > 0.5 ? (20000 * Math.pow(8000/20000,(f-0.5)*2)) : 20000;
      dOut.lopass.frequency.setValueAtTime(Math.max(8000,loFreq), tAt);
      dIn.hipass.frequency.setValueAtTime(20, tAt);
    } else if (style === 'avicii') {
      const loFreq = 20000 * Math.pow(800/20000, Math.pow(f,1.4));
      dOut.lopass.frequency.setValueAtTime(Math.max(700,loFreq), tAt);
      const outHpFreq = 20 * Math.pow(600/20, Math.pow(f,1.8));
      dOut.hipass.frequency.setValueAtTime(Math.min(600,outHpFreq), tAt);
      const inHpFreq  = 80 * Math.pow(20/80, Math.pow(f*2,1.5));
      dIn.hipass.frequency.setValueAtTime(Math.max(20,inHpFreq), tAt);
    } else {
      const loFreq = 20000 * Math.pow(500/20000, Math.pow(f,0.7));
      dOut.lopass.frequency.setValueAtTime(Math.max(400,loFreq), tAt);
      let hpFreq;
      if (f < 0.60) {
        hpFreq = 320 * Math.pow(200/320, f/0.60);
      } else {
        const bassF = (f-0.60)/0.40;
        hpFreq = 200 * Math.pow(20/200, Math.pow(bassF,1.5));
      }
      dIn.hipass.frequency.setValueAtTime(Math.max(20,hpFreq), tAt);
    }
  }

  // Midpoint UI update
  setTimeout(async () => {
    updateNP(nxt, S.nxtPhase);
    // Theme transition
    const newTheme = detectTheme(nxt);
    applyTheme(newTheme);
  }, cfDur * 500);

  // Handoff
  setTimeout(async () => {
    S.deck   = inp;
    S.startAt = inpStartedAt;
    S.cur  = nxt; S.curFile = nxt.file;
    S.played.push(nxt.file); S.playedSet.add(nxt.file); S.count++;
    S.nxt  = null; S.nxtPlan = null;
    S.sessionTracks.push({track:nxt, startCtxTime:inpStartedAt});
    await askNext(nxt, getTime());
    if (S.nxt) preload(S.nxt);
  }, cfDur * 950);

  // End
  setTimeout(() => {
    const dO = S.decks[out];
    if (dO.preGain) {
      dO.preGain.gain.cancelScheduledValues(ctx.currentTime);
      dO.preGain.gain.setValueAtTime(0, ctx.currentTime);
    }
    if (dO.src) { try{dO.src.stop();}catch(e){} dO.src = null; }
    if (dO.hipass) dO.hipass.frequency.setValueAtTime(20, ctx.currentTime);
    if (dO.lopass) dO.lopass.frequency.setValueAtTime(20000, ctx.currentTime);
    if (S.compGain) {
      S.compGain.gain.cancelScheduledValues(ctx.currentTime);
      S.compGain.gain.linearRampToValueAtTime(1, ctx.currentTime+0.3);
    }
    S.mixing           = false;
    S.silenceStart     = null;
    S.silenceTriggered = false;
    document.getElementById('mix-indicator').classList.remove('on');
  }, cfDur * 1000 + 250);
}

// ═══ MAIN GAME LOOP ══════════════════════════════════════════
function loop() {
  requestAnimationFrame(loop);
  if (!S.playing || !ctx) return;

  const t   = getTime();
  const dur = S.cur ? (S.cur.duracion_segundos||0) : 0;

  // Mix progress
  if (S.mixing) {
    const pct = Math.min(1, (ctx.currentTime - S.mixStart) / S.mixDur);
    // (no UI bar needed)
  }

  // Mix trigger
  if (!S.mixing && S.nxt && dur > 0) {
    const cf       = S.nxtPlan ? (S.nxtPlan.mix_duration||8) : 8;
    const puedeSalir = S.cur ? (parseFloat(S.cur.puede_salir)||0) : 0;
    const planExit   = S.nxtPlan ? (parseFloat(S.nxtPlan.exit_at)||0) : 0;
    let trig;
    if (puedeSalir > 0) trig = puedeSalir - cf;
    else if (planExit > 0) trig = planExit - cf;
    else trig = dur - cf - 2;
    trig = Math.max(trig, dur * 0.73);

    if (t >= trig - 0.5 && t < trig + 2.5 && !S._beatSnapScheduled) {
      S._beatSnapScheduled = true;
      const beatTimes = S.cur ? (S.cur.beat_times||[]) : [];
      let snapTarget = trig;
      if (beatTimes.length > 0) {
        let bestDist=9999, bestBeat=trig;
        for (const bt of beatTimes) {
          const dist=Math.abs(bt-trig);
          if (dist<bestDist && dist<1.5){bestDist=dist;bestBeat=bt;}
        }
        snapTarget=bestBeat;
      }
      const delay = Math.max(0,(snapTarget-t)*1000);
      setTimeout(()=>{ S._beatSnapScheduled=false; if(!S.mixing && S.nxt) doMix(); }, delay);
    }
  }

  // Refresh plan
  if (!S.mixing && S.cur && S.nxt && Math.round(t)%20===0 && t>8)
    askNext(S.cur, t);

  // Beat detection — visual beat pulse
  if (S.playing && t > 2) {
    const dk = S.decks[S.deck];
    if (dk && dk.analyser) {
      const fdata = new Uint8Array(dk.analyser.frequencyBinCount);
      dk.analyser.getByteFrequencyData(fdata);
      const subE = (fdata[0]+fdata[1]+fdata[2]+fdata[3]) / (4*255);
      S.beatHistory.push(subE);
      if (S.beatHistory.length > 60) S.beatHistory.shift();
      const avg = S.beatHistory.reduce((a,b)=>a+b,0) / S.beatHistory.length;
      S.beatThresh = avg * 1.5;
      const now = ctx.currentTime;
      const minInt = S.cur && S.cur.bpm ? 60/S.cur.bpm*0.7 : 0.25;
      if (subE > S.beatThresh && subE > 0.1 && (now-S.beatLastTime) > minInt) {
        S.beatLastTime = now;
        V.beatPulse = 1.0;  // trigger visual beat
        // Beat flash overlay
        const flash = document.getElementById('beat-flash');
        const tc = getComputedStyle(document.documentElement).getPropertyValue('--th-glow').trim();
        flash.style.background = tc || 'rgba(255,255,255,.04)';
        flash.style.opacity = '1';
        setTimeout(()=>{ flash.style.opacity='0'; }, 80);
      }
    }
  }

  // Silence detection
  if (!S.mixing && S.playing && t > 5) {
    const dk = S.decks[S.deck];
    if (dk && dk.analyser) {
      const buf = new Uint8Array(dk.analyser.frequencyBinCount);
      dk.analyser.getByteFrequencyData(buf);
      let sum=0;
      for (let i=0;i<buf.length;i++) sum+=(buf[i]/255)*(buf[i]/255);
      const rms = Math.sqrt(sum/buf.length);
      const SILENCE_THRESHOLD=0.03, SILENCE_MS=1800, MIN_PROGRESS=0.30;
      const progress = dur>0 ? t/dur : 0;
      if (rms<SILENCE_THRESHOLD && progress>MIN_PROGRESS && !S.silenceTriggered) {
        if (S.silenceStart===null) S.silenceStart=ctx.currentTime;
        else if ((ctx.currentTime-S.silenceStart)*1000 > SILENCE_MS) {
          S.silenceTriggered=true; S.silenceStart=null; doMix();
        }
      } else if (rms>=SILENCE_THRESHOLD) {
        S.silenceStart=null; S.silenceTriggered=false;
      }
    }
  }
}

// ═══ UI UPDATE HELPERS ══════════════════════════════════════
function updateNP(t, phase) {
  document.getElementById('panelTitle').textContent = t.name;
  document.getElementById('panelBpm').textContent   = t.bpm ? Math.round(t.bpm)+' BPM' : '—';
  document.getElementById('panelPhase').textContent = PHASE_LABELS[phase||'warm-up']||phase;
  const ke = document.getElementById('panelKey');
  ke.textContent = t.key ? t.key : '';
  document.getElementById('panelEgy').textContent = t.energia ? 'E'+t.energia : '';
}

function updateArc(phase, targetE) {
  // No arc visual — just update phase pill in panel
  document.getElementById('panelPhase').textContent = PHASE_LABELS[phase]||phase;
}

function fmt(s){s=Math.max(0,Math.floor(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')}

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