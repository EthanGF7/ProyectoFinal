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
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Bebas+Neue&family=DM+Sans:wght@300;400;600&display=swap');
:root{
  --bg:#07080f; --s1:#0d0f1c; --s2:#12152a; --b:#1c2040;
  --g:#c8ff00;  --c:#00f0ff;  --r:#ff3b5c; --o:#ff9500; --p:#b060ff;
  --t:#dde2ff;  --dim:#3d4466;
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;
  display:flex;align-items:center;justify-content:center;}
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:9999;
  background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,.035) 3px,rgba(0,0,0,.035) 4px);}

/* ── IDLE ──────────────────────────────────────────────────── */
#idle{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:28px;z-index:100;background:var(--bg);
  transition:opacity .9s,visibility .9s;}
#idle.off{opacity:0;visibility:hidden;pointer-events:none}

.idle-logo{font-family:'Bebas Neue',sans-serif;
  font-size:clamp(72px,15vw,140px);letter-spacing:12px;
  background:linear-gradient(135deg,var(--g) 30%,var(--c));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  animation:logopulse 3s ease-in-out infinite;}
@keyframes logopulse{
  0%,100%{filter:drop-shadow(0 0 20px rgba(200,255,0,.3))}
  50%    {filter:drop-shadow(0 0 60px rgba(200,255,0,.7)) drop-shadow(0 0 120px rgba(0,240,255,.3))}}

.idle-sub{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:4px;
  color:var(--dim);text-transform:uppercase;}

.play-btn{width:100px;height:100px;border-radius:50%;background:var(--g);border:none;
  cursor:pointer;font-size:38px;color:#000;font-weight:900;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 0 50px rgba(200,255,0,.4),0 0 100px rgba(200,255,0,.15);
  transition:all .25s;position:relative;}
.play-btn::before{content:'';position:absolute;inset:-4px;border-radius:50%;
  border:1px solid rgba(200,255,0,.2);animation:ringgrow 2s ease-out infinite;}
@keyframes ringgrow{0%{transform:scale(1);opacity:.6}100%{transform:scale(1.4);opacity:0}}
.play-btn:hover{transform:scale(1.09);box-shadow:0 0 80px rgba(200,255,0,.7),0 0 160px rgba(200,255,0,.25)}
.play-btn:disabled{opacity:.3;cursor:not-allowed;transform:none;animation:none}
.play-btn:disabled::before{display:none}
.idle-info{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--dim);}
.idle-info b{color:var(--g)}

/* ── APP ───────────────────────────────────────────────────── */
#app{width:100%;max-width:860px;padding:12px;opacity:0;transition:opacity 1s;
  pointer-events:none;display:flex;flex-direction:column;gap:8px;height:100vh;max-height:100vh;}
#app.on{opacity:1;pointer-events:all}

/* MAIN CARD */
.card{background:var(--s1);border:1px solid var(--b);border-radius:16px;overflow:hidden;flex-shrink:0}

/* ── VIZ (spectrum arriba) ─────────────────────────────────── */
#viz{width:100%;height:52px;display:block;border-radius:10px 10px 0 0;
  background:var(--bg);border:1px solid var(--b);border-bottom:none;flex-shrink:0}

/* ── NOW PLAYING ───────────────────────────────────────────── */
.np{padding:12px 18px 10px;border-bottom:1px solid var(--b);
  display:flex;align-items:center;gap:14px}

/* Vinyl animado */
.vinyl{width:52px;height:52px;border-radius:50%;flex-shrink:0;position:relative;
  background:
    radial-gradient(circle at 50% 50%,
      #333 0%,#333 16%,transparent 17%,
      rgba(255,255,255,.04) 35%,transparent 36%,
      rgba(255,255,255,.02) 55%,transparent 56%,
      #1a1a1a 80%
    );
  border:1px solid #2a2a2a;}
.vinyl.spin{animation:vspin 1.8s linear infinite}
@keyframes vspin{to{transform:rotate(360deg)}}
.vinyl-dot{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:10px;height:10px;border-radius:50%;
  background:radial-gradient(var(--g),rgba(200,255,0,.4));
  box-shadow:0 0 8px var(--g)}
.vinyl-groove{position:absolute;inset:6px;border-radius:50%;
  border:1px solid rgba(255,255,255,.04)}
.vinyl-groove2{position:absolute;inset:14px;border-radius:50%;
  border:1px solid rgba(255,255,255,.03)}

.np-info{flex:1;min-width:0}
.np-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
  color:var(--dim);text-transform:uppercase;margin-bottom:2px}
.np-title{font-family:'Bebas Neue',sans-serif;font-size:clamp(22px,3.8vw,34px);
  letter-spacing:1px;line-height:1;margin-bottom:3px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.np-meta{display:flex;gap:8px;font-family:'IBM Plex Mono',monospace;font-size:10px;
  flex-wrap:wrap;align-items:center}
.np-meta .bpm{color:var(--g);font-weight:700}
.np-meta .egy{color:var(--c)}
.np-meta .key{color:var(--p);font-size:9px;
  padding:1px 5px;border-radius:5px;border:1px solid rgba(176,96,255,.25)}
.np-meta .dm{color:var(--dim)}

/* Phase pill */
.pill{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:1px;
  text-transform:uppercase;padding:2px 8px;border-radius:8px;flex-shrink:0;
  border:1px solid}
.pill-warm-up     {color:var(--c);border-color:rgba(0,240,255,.25);background:rgba(0,240,255,.06)}
.pill-first-build {color:var(--g);border-color:rgba(200,255,0,.2);background:rgba(200,255,0,.05)}
.pill-first-peak  {color:var(--g);border-color:rgba(200,255,0,.4);background:rgba(200,255,0,.1);
  animation:peakpulse 1.2s ease-in-out infinite}
.pill-breakdown   {color:var(--o);border-color:rgba(255,149,0,.3);background:rgba(255,149,0,.07)}
.pill-second-build{color:var(--g);border-color:rgba(200,255,0,.25);background:rgba(200,255,0,.06)}
.pill-second-peak {color:var(--g);border-color:rgba(200,255,0,.5);background:rgba(200,255,0,.12);
  animation:peakpulse .9s ease-in-out infinite}
.pill-outro       {color:var(--dim);border-color:rgba(61,68,102,.4);background:rgba(61,68,102,.1)}
@keyframes peakpulse{
  0%,100%{box-shadow:none}50%{box-shadow:0 0 10px rgba(200,255,0,.35)}}

/* ── WAVEFORM + PLAYHEAD ───────────────────────────────────── */
.ww{padding:6px 18px;position:relative;border-bottom:1px solid var(--b);
  user-select:none;-webkit-user-select:none}
#wc{width:100%;height:42px;display:block;border-radius:5px;background:var(--s2);
  cursor:col-resize}
.ph{position:absolute;top:6px;bottom:6px;width:2px;
  background:var(--g);box-shadow:0 0 8px var(--g);
  pointer-events:none;border-radius:1px}
.ph.scrubbing{background:white;box-shadow:0 0 12px white}
.ph-handle{position:absolute;top:50%;transform:translate(-50%,-50%);
  width:12px;height:12px;border-radius:50%;
  background:var(--g);box-shadow:0 0 8px var(--g);
  pointer-events:none;transition:transform .1s}
.ph-handle.scrubbing{transform:translate(-50%,-50%) scale(1.5);background:white;box-shadow:0 0 12px white}
.ww-tooltip{position:absolute;top:-22px;transform:translateX(-50%);
  font-family:'IBM Plex Mono',monospace;font-size:9px;
  background:rgba(0,0,0,.8);color:var(--t);padding:2px 6px;border-radius:4px;
  pointer-events:none;opacity:0;transition:opacity .15s;white-space:nowrap}
.ww-tooltip.show{opacity:1}
.times{display:flex;justify-content:space-between;
  font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--dim);margin-top:3px}
.times .cur{color:var(--t)}

/* ── EQ METERS (visual de lo que hace el EQ durante el mix) ── */
.eq-row{padding:5px 18px;border-bottom:1px solid var(--b);
  display:flex;gap:8px;align-items:center;opacity:0;transition:opacity .4s}
.eq-row.on{opacity:1}
.eq-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);
  letter-spacing:1px;text-transform:uppercase;width:18px;flex-shrink:0}
.eq-band{flex:1;height:3px;border-radius:2px;background:var(--s2);overflow:hidden;position:relative}
.eq-fill{height:100%;border-radius:2px;transition:width .15s linear}
.eq-fill.lo{background:linear-gradient(90deg,#ff3b5c,#ff6b35)}
.eq-fill.mid{background:linear-gradient(90deg,#ff9500,var(--g))}
.eq-fill.hi{background:linear-gradient(90deg,var(--g),var(--c))}
.eq-sep{width:1px;background:var(--b);height:14px;flex-shrink:0}

/* ── SESSION ARC ───────────────────────────────────────────── */
.arc{padding:6px 18px;border-bottom:1px solid var(--b);
  display:flex;align-items:center;gap:10px}
.arc-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);
  letter-spacing:1px;text-transform:uppercase;width:32px;flex-shrink:0}
.arc-track{flex:1;height:18px;background:var(--s2);border-radius:4px;
  position:relative;overflow:hidden}
/* Curva de energía de la sesión dibujada como fondo */
.arc-track::before{content:'';position:absolute;inset:0;
  background:linear-gradient(90deg,
    rgba(0,240,255,.15) 0%,
    rgba(200,255,0,.25) 30%,
    rgba(200,255,0,.4)  48%,
    rgba(255,149,0,.2)  58%,
    rgba(200,255,0,.35) 72%,
    rgba(200,255,0,.45) 88%,
    rgba(0,240,255,.1)  100%
  );}
.arc-cursor{position:absolute;top:0;bottom:0;width:3px;
  background:white;box-shadow:0 0 8px white;
  transition:left .9s cubic-bezier(.22,1,.36,1);border-radius:2px}
.arc-phase{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);
  flex-shrink:0;min-width:60px;text-align:right}

/* ── MIX IN PROGRESS ───────────────────────────────────────── */
.mix-row{padding:6px 18px;
  border-bottom:1px solid rgba(200,255,0,.06);
  font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:1px;
  display:none;align-items:center;gap:8px;
  transition:background .4s,color .4s,border-color .4s}
.mix-row.on{display:flex}
/* Guetta: verde lima agresivo */
.mix-row.style-guetta{
  background:rgba(200,255,0,.03);color:var(--g);
  border-bottom-color:rgba(200,255,0,.08)}
/* Avicii: naranja cálido suave */
.mix-row.style-avicii{
  background:rgba(255,149,0,.03);color:var(--o);
  border-bottom-color:rgba(255,149,0,.08)}
/* Progressive: cyan técnico */
.mix-row.style-progressive{
  background:rgba(0,240,255,.03);color:var(--c);
  border-bottom-color:rgba(0,240,255,.08)}
.mix-dot{width:5px;height:5px;border-radius:50%;
  animation:blink .5s step-end infinite;flex-shrink:0}
.style-guetta .mix-dot{background:var(--g)}
.style-avicii .mix-dot{background:var(--o)}
.style-progressive .mix-dot{background:var(--c)}
@keyframes blink{50%{opacity:0}}
.mix-prog{flex:1;height:3px;background:var(--b);border-radius:2px;overflow:hidden}
.mix-fill{height:100%;border-radius:2px;width:0%;transition:width .2s linear}
.style-guetta .mix-fill{background:linear-gradient(90deg,var(--c),var(--g))}
.style-avicii .mix-fill{background:linear-gradient(90deg,#ff6b35,var(--o))}
.mix-label{font-size:8px;flex-shrink:0;opacity:.7;font-weight:700;letter-spacing:2px}
.mix-info{color:var(--dim);flex-shrink:0;font-size:8px}

/* ── NEXT UP ───────────────────────────────────────────────── */
.nxt{padding:7px 18px;background:rgba(0,240,255,.018);
  border-bottom:1px solid rgba(0,240,255,.05);
  display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.nxt-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:2px;
  color:var(--c);text-transform:uppercase;flex-shrink:0}
.nxt-nm{font-size:12px;font-weight:600;flex:1;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nxt-sc{font-family:'IBM Plex Mono',monospace;font-size:8px;
  padding:2px 6px;border-radius:7px;border:1px solid rgba(0,240,255,.18);
  color:var(--c);flex-shrink:0}
.nxt-t{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);flex-shrink:0}

/* ── STATUS ────────────────────────────────────────────────── */
.st{padding:7px 18px;display:flex;align-items:center;
  justify-content:space-between;flex-wrap:wrap;gap:6px}
.st-l{display:flex;align-items:center;gap:7px}
.bx{background:var(--s2);border:1px solid var(--b);border-radius:7px;
  padding:4px 11px;text-align:center;font-family:'IBM Plex Mono',monospace}
.bx .v{font-size:17px;color:var(--g);font-weight:700;line-height:1}
.bx .l{font-size:7px;color:var(--dim);letter-spacing:2px}
.live{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:2px;
  text-transform:uppercase;padding:2px 8px;border-radius:10px;
  border:1px solid var(--g);color:var(--g);animation:blink 1.4s step-end infinite}
.mod{font-family:'IBM Plex Mono',monospace;font-size:8px;padding:2px 8px;
  border-radius:10px;border:1px solid}
.mod.ok{border-color:rgba(0,240,255,.3);color:var(--c)}
.mod.fb{border-color:var(--dim);color:var(--dim)}
.skip-btn{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:1px;
  padding:3px 10px;border-radius:8px;border:1px solid rgba(200,255,0,.3);
  background:rgba(200,255,0,.06);color:var(--g);cursor:pointer;transition:all .15s;}
.skip-btn:hover{background:rgba(200,255,0,.15);border-color:var(--g)}
.skip-btn:disabled{opacity:.3;cursor:not-allowed}
#log{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--dim);
  max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ── LIBRARY ───────────────────────────────────────────────── */
.lib{background:var(--s1);border:1px solid var(--b);border-radius:14px;
  overflow:hidden;flex:1;min-height:0;display:flex;flex-direction:column}
.lib-h{padding:7px 14px;border-bottom:1px solid var(--b);
  display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.lib-h h2{font-family:'IBM Plex Mono',monospace;font-size:8px;
  letter-spacing:2px;text-transform:uppercase;color:var(--dim)}
.lib-h .cnt{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--g)}
.tlist{overflow-y:auto;flex:1}
.tlist::-webkit-scrollbar{width:2px}
.tlist::-webkit-scrollbar-thumb{background:var(--b);border-radius:2px}
.tk{display:grid;grid-template-columns:18px 1fr 32px 44px 28px 32px;
  align-items:center;gap:5px;padding:5px 14px;
  border-bottom:1px solid rgba(28,32,64,.5);transition:background .1s}
.tk:hover{background:var(--s2)}
.tk.cur{background:rgba(200,255,0,.045);border-left:2px solid var(--g)}
.tk.nxt{background:rgba(0,240,255,.02);border-left:2px solid rgba(0,240,255,.35)}
.tk.done{opacity:.28}
.tn{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);text-align:center}
.tt{font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.te{height:2px;border-radius:2px;background:var(--b);overflow:hidden}
.tef{height:100%;background:linear-gradient(90deg,var(--c),var(--g));border-radius:2px}
.tb{font-family:'IBM Plex Mono',monospace;font-size:8px;text-align:right}
.tb.ok{color:var(--g)}.tb.no{color:var(--dim)}
.ts{font-family:'IBM Plex Mono',monospace;font-size:8px;text-align:right}
.ts.hi{color:var(--g)}.ts.mi{color:var(--c)}.ts.lo{color:var(--dim)}
.td{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);text-align:right}
.empty{padding:28px;text-align:center;color:var(--dim)}
.empty code{font-family:'IBM Plex Mono',monospace;color:var(--g);font-size:9px}

/* ── TIMELINE DE SESIÓN ─────────────────────────────────────── */
.timeline{background:var(--s1);border:1px solid var(--b);border-radius:14px;
  overflow:hidden;flex-shrink:0;padding:8px 14px}
.tl-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.tl-h span{font-family:'IBM Plex Mono',monospace;font-size:8px;
  letter-spacing:2px;text-transform:uppercase;color:var(--dim)}
.tl-track{position:relative;height:28px;background:var(--s2);border-radius:5px;overflow:hidden}
/* Curva de energía de sesión como fondo */
.tl-energy-curve{position:absolute;inset:0;opacity:.25}
.tl-blocks{position:absolute;inset:0;display:flex}
.tl-block{height:100%;position:relative;border-right:1px solid var(--bg);
  cursor:pointer;transition:filter .15s;flex-shrink:0}
.tl-block:hover{filter:brightness(1.4)}
.tl-block.playing{box-shadow:inset 0 0 0 1px white}
.tl-block.done{opacity:.5}
.tl-block.future{opacity:.3}
.tl-head{position:absolute;top:0;bottom:0;width:2px;background:white;
  box-shadow:0 0 6px white;pointer-events:none;transition:left .1s linear}
.tl-labels{display:flex;margin-top:3px;position:relative;height:14px}
.tl-lbl{position:absolute;font-family:'IBM Plex Mono',monospace;font-size:7px;
  color:var(--dim);transform:translateX(-50%);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;max-width:80px}
.tl-lbl.cur{color:var(--g)}

/* ── CUE / PREVIEW ──────────────────────────────────────────── */
.cue-btn{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:1px;
  padding:3px 9px;border-radius:8px;
  border:1px solid rgba(176,96,255,.35);
  background:rgba(176,96,255,.08);color:var(--p);
  cursor:pointer;transition:all .15s;flex-shrink:0}
.cue-btn:hover{background:rgba(176,96,255,.2);border-color:var(--p)}
.cue-btn.cueing{background:rgba(176,96,255,.25);border-color:var(--p);
  animation:peakpulse .8s ease-in-out infinite}
.cue-btn:disabled{opacity:.3;cursor:not-allowed}

/* ── BEAT indicator ─────────────────────────────────────────── */
.beat-dot{width:6px;height:6px;border-radius:50%;background:var(--g);
  opacity:0;transition:opacity .05s;flex-shrink:0}
.beat-dot.flash{opacity:1}
</style>
</head>
<body>

<!-- IDLE -->
<div id="idle">
  <div class="idle-logo">DJ AI</div>
  <div class="idle-sub">Sesión autónoma · mezcla inteligente en vivo</div>
  <button class="play-btn" id="btnStart" disabled>▶</button>
  <div class="idle-info" id="idleInfo">Cargando biblioteca...</div>
</div>

<!-- PLAYER -->
<div id="app">

  <canvas id="viz"></canvas>

  <div class="card">

    <!-- NOW PLAYING -->
    <div class="np">
      <div class="vinyl" id="vinyl">
        <div class="vinyl-groove"></div>
        <div class="vinyl-groove2"></div>
        <div class="vinyl-dot"></div>
      </div>
      <div class="np-info">
        <div class="np-lbl">Now playing</div>
        <div class="np-title" id="npTitle">—</div>
        <div class="np-meta">
          <span class="bpm" id="npBpm">—</span>
          <span class="egy" id="npEgy">—</span>
          <span class="key" id="npKey" style="display:none">—</span>
          <span class="dm"  id="npDur">—</span>
          <span class="pill" id="phasePill">warm-up</span>
        </div>
      </div>
    </div>

    <!-- WAVEFORM -->
    <div class="ww" id="ww">
      <canvas id="wc"></canvas>
      <div class="ph" id="ph" style="left:18px">
        <div class="ph-handle" id="phHandle"></div>
      </div>
      <div class="ww-tooltip" id="wwTooltip">0:00</div>
      <div class="times">
        <span class="cur" id="tCur">0:00</span>
        <span id="tTot">0:00</span>
      </div>
    </div>

    <!-- EQ BANDS (visible durante el mix) -->
    <div class="eq-row" id="eqRow">
      <div class="eq-lbl">LO</div>
      <div class="eq-band"><div class="eq-fill lo" id="eqLo" style="width:100%"></div></div>
      <div class="eq-sep"></div>
      <div class="eq-lbl" style="width:24px">MID</div>
      <div class="eq-band"><div class="eq-fill mid" id="eqMid" style="width:100%"></div></div>
      <div class="eq-sep"></div>
      <div class="eq-lbl">HI</div>
      <div class="eq-band"><div class="eq-fill hi" id="eqHi" style="width:100%"></div></div>
    </div>

    <!-- SESSION ARC -->
    <div class="arc">
      <div class="arc-lbl">Arco</div>
      <div class="arc-track">
        <div class="arc-cursor" id="arcCursor" style="left:0%"></div>
      </div>
      <div class="arc-phase" id="arcPhase">warm-up</div>
    </div>

    <!-- MIX IN PROGRESS -->
    <div class="mix-row" id="mixRow">
      <div class="mix-dot"></div>
      <div class="mix-label" id="mixStyleLabel">⚡</div>
      <div class="mix-prog"><div class="mix-fill" id="mixFill"></div></div>
      <div class="mix-info" id="mixInfo">mezclando...</div>
    </div>

    <!-- NEXT UP -->
    <div class="nxt" id="nxtRow" style="display:none">
      <div class="nxt-lbl">IA Next</div>
      <div class="nxt-nm" id="nxtNm">—</div>
      <div class="nxt-sc" id="nxtSc">—</div>
      <div class="nxt-t"  id="nxtT">—</div>
      <button class="cue-btn" id="btnCue" disabled title="Preview 5s de la siguiente">👂 CUE</button>
    </div>

    <!-- STATUS -->
    <div class="st">
      <div class="st-l">
        <div class="bx"><div class="v" id="bpmVal">—</div><div class="l">BPM</div></div>
        <div class="live">● LIVE</div>
        <div class="beat-dot" id="beatDot"></div>
        <div class="mod" id="modB">—</div>
        <button class="skip-btn" id="btnSkip" disabled title="Saltar al mix ahora">⏭ MIX NOW</button>
      </div>
      <div id="log">—</div>
    </div>

  </div><!-- .card -->

  <!-- TIMELINE DE SESIÓN -->
  <div class="timeline" id="tlWrap" style="display:none">
    <div class="tl-h">
      <span>Timeline · sesión</span>
      <span id="tlDur">—</span>
    </div>
    <div class="tl-track" id="tlTrack">
      <canvas class="tl-energy-curve" id="tlCurve"></canvas>
      <div class="tl-blocks" id="tlBlocks"></div>
      <div class="tl-head"   id="tlHead"  style="left:0%"></div>
    </div>
    <div class="tl-labels" id="tlLabels"></div>
  </div>

  <!-- LIBRARY -->
  <div class="lib">
    <div class="lib-h">
      <h2>🎵 Biblioteca</h2>
      <span class="cnt" id="libCount">—</span>
    </div>
    <div class="tlist" id="tlist">
      <div class="empty"><p>Cargando...</p></div>
    </div>
  </div>

</div><!-- #app -->

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
const STYLE_LABELS = { guetta: '⚡ GUETTA', avicii: '🌅 AVICII', progressive: '〰 PROG' };
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
  document.getElementById('app').classList.add('on');
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
    const reverbPeak = style === 'avicii' ? 0.35 : style === 'progressive' ? 0.10 : 0.18;
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

  // Playhead — no mover mientras el usuario arrastra
  const wW = document.getElementById('wc').offsetWidth;
  if (!S._dragging || !S._dragging()) {
    const pad = 18;
    document.getElementById('ph').style.left   = (pad + (dur > 0 ? (t/dur)*wW : 0)) + 'px';
    document.getElementById('tCur').textContent = fmt(t);
  }
  document.getElementById('tTot').textContent  = fmt(dur);

  // Vinyl spin
  document.getElementById('vinyl').classList.toggle('spin', S.playing && !S.mixing);

  // Mix progress bar
  if (S.mixing) {
    const pct = Math.min(100, ((ctx.currentTime - S.mixStart) / S.mixDur) * 100);
    document.getElementById('mixFill').style.width = pct + '%';
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

  // ── Detección de beat en tiempo real ───────────────────────
  // Analiza la energía de sub-bass (bins 0-4 ≈ 20-80Hz) cada frame.
  // Si supera el umbral adaptativo → beat detectado → flash visual.
  // El umbral se adapta al nivel medio de los últimos 30 beats.
  if (!S.mixing && S.playing && t > 2) {
    const dk = S.decks[S.deck];
    if (dk && dk.analyser) {
      const fdata = new Uint8Array(dk.analyser.frequencyBinCount);
      dk.analyser.getByteFrequencyData(fdata);
      // Sub-bass energy (primeros 4 bins)
      const subE = (fdata[0] + fdata[1] + fdata[2] + fdata[3]) / (4 * 255);
      S.beatHistory.push(subE);
      if (S.beatHistory.length > 60) S.beatHistory.shift();
      const avg = S.beatHistory.reduce((a,b)=>a+b,0) / S.beatHistory.length;
      S.beatThresh = avg * 1.5;

      const now = ctx.currentTime;
      const minInterval = S.cur && S.cur.bpm ? 60/S.cur.bpm * 0.7 : 0.25;
      if (subE > S.beatThresh && subE > 0.1 && (now - S.beatLastTime) > minInterval) {
        S.beatLastTime = now;
        // Flash visual del beat dot
        const dot = document.getElementById('beatDot');
        dot.classList.add('flash');
        setTimeout(() => dot.classList.remove('flash'), 80);
      }
    }
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
  document.getElementById('npTitle').textContent = t.name;
  document.getElementById('npBpm').textContent   = t.bpm  ? t.bpm.toFixed(1)+' BPM' : '—';
  document.getElementById('npEgy').textContent   = t.energia ? 'E'+t.energia : '';
  document.getElementById('npDur').textContent   = t.duracion_segundos ? fmt(t.duracion_segundos) : '';
  document.getElementById('bpmVal').textContent  = t.bpm ? Math.round(t.bpm) : '—';

  const keyEl = document.getElementById('npKey');
  if (t.key) { keyEl.textContent = t.key; keyEl.style.display = 'inline'; }
  else keyEl.style.display = 'none';

  const pill = document.getElementById('phasePill');
  const p = phase || S.nxtPhase || 'warm-up';
  pill.textContent = PHASE_LABELS[p] || p;
  pill.setAttribute('class', 'pill pill-' + p);
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
  const row   = document.getElementById('mixRow');
  const label = document.getElementById('mixStyleLabel');
  row.classList.add('on');
  row.classList.remove('style-guetta', 'style-avicii', 'style-progressive');
  row.classList.add('style-' + (style || 'guetta'));
  label.textContent = STYLE_LABELS[style] || '⚡ GUETTA';
  document.getElementById('mixInfo').textContent = `→ ${name} · ${dur.toFixed(0)}s`;
  document.getElementById('mixFill').style.width = '0%';
  document.getElementById('eqRow').classList.add('on');
}
function hideMixing() { document.getElementById('mixRow').classList.remove('on'); }

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
      <div class="tt">${t.name}</div>
      <div class="te"><div class="tef" style="width:${t.energia||50}%"></div></div>
      <div class="tb ${bOk?'ok':'no'}">${t.bpm?t.bpm.toFixed(0)+'bpm':'—'}</div>
      <div class="ts ${sC}">${sc!==null?sc:'—'}</div>
      <div class="td">${t.duracion_segundos?fmt(t.duracion_segundos):'—'}</div>
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

// ── Spectrum visualizer ───────────────────────────────────────
function drawViz() {
  const c = document.getElementById('viz'), dpr = devicePixelRatio||1;
  if(c.width!==c.offsetWidth*dpr){c.width=c.offsetWidth*dpr;c.height=c.offsetHeight*dpr;}
  const g = c.getContext('2d'), W=c.offsetWidth, H=c.offsetHeight;
  g.setTransform(dpr,0,0,dpr,0,0);

  // Fade out fondo (efecto de cola)
  g.fillStyle = 'rgba(7,8,15,.55)';
  g.fillRect(0,0,W,H);

  // Dibuja ambos decks durante el crossfade (superpuestos)
  const drawDeck = (dkId, colorFn) => {
    const dk = S.decks[dkId];
    if (!dk || !dk.analyser) return;
    const d = new Uint8Array(dk.analyser.frequencyBinCount);
    dk.analyser.getByteFrequencyData(d);
    const bw = (W / d.length) * 1.2;
    for(let i=0;i<d.length;i++){
      const v=d[i]/255, bh=v*H*0.96;
      if(bh < 1) continue;
      const col = colorFn(i/d.length, v);
      g.fillStyle = col;
      // Barra + reflejo especular
      g.fillRect(i*bw, H-bh, bw-0.5, bh);
      g.globalAlpha = 0.12;
      g.fillRect(i*bw, H, bw-0.5, -bh*0.25);
      g.globalAlpha = 1;
    }
  };

  const colorOut = (x, v) => `rgba(200,255,0,${(0.25+v*0.75).toFixed(2)})`;
  const colorIn  = (x, v) => `rgba(0,240,255,${(0.2+v*0.7).toFixed(2)})`;

  if (S.mixing) {
    const other = S.deck === 'A' ? 'B' : 'A';
    drawDeck(other, colorIn);
    drawDeck(S.deck, colorOut);
  } else {
    drawDeck(S.deck, colorOut);
  }
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