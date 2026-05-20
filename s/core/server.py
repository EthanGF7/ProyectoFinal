"""HTTP Server - runs DJ player with configurable port and auto-fallback.

Importante: el bind del puerto y el print de DJ_READY_PORT ocurren ANTES
de cargar la librería de audio (load_library) para que el proceso padre
(Node) reciba la señal de "listo" en <500ms aunque librosa tarde 10s.
"""
import sys
import json
import time
import threading
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from .library import load_library
from .arc import get_phase
from .mixing import detect_style, fade_duration
from .scoring import pick_next
from .prefs import load_prefs, save_prefs


class DJHandler(BaseHTTPRequestHandler):
    """HTTP request handler for DJ player."""

    def log_message(self, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        p = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(p.query)

        if p.path in ("/", "/index.html"):
            self.ok(self.server.html.encode("utf-8"), "text/html")

        elif p.path == "/api/library":
            self.ok(json.dumps(self.server.library).encode(), "application/json")

        elif p.path == "/api/modules":
            self.ok(json.dumps({"ok": self.server.modules_ok}).encode(), "application/json")

        elif p.path == "/api/next":
            self._handle_next(qs)

        elif p.path == "/api/prefs":
            self.ok(json.dumps(self.server.prefs).encode(), "application/json")

        elif p.path.startswith("/audio/"):
            self._handle_audio(p.path)

        elif p.path == "/engine.js":
            self.ok(self.server.engine_js.encode("utf-8"), "application/javascript")

        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests."""
        p = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if p.path == "/api/like":
            file = data.get("file", "")
            action = data.get("action", "")

            if file and action in ("like", "dislike", "clear"):
                if action == "like":
                    self.server.prefs[file] = 1
                elif action == "dislike":
                    self.server.prefs[file] = -1
                else:
                    self.server.prefs.pop(file, None)

                save_prefs(self.server.prefs_file, self.server.prefs)
                self.ok(
                    json.dumps({"ok": True, "file": file, "action": action}).encode(),
                    "application/json",
                )
            else:
                self.ok(b'{"error":"invalid"}', "application/json")
        else:
            self.send_error(404)

    def _handle_next(self, qs):
        """Handle /api/next request."""
        cur_file = qs.get("current", [None])[0]
        cur_time = float(qs.get("time", [0])[0])
        played_count = int(qs.get("count", [0])[0])

        try:
            played_set = set(json.loads(urllib.parse.unquote(qs.get("played", ["[]"])[0])))
        except Exception:
            played_set = set()

        current = next((t for t in self.server.library if t["file"] == cur_file), None)
        if not current:
            self.ok(b'{"error":"not found"}', "application/json")
            return

        try:
            played_list_raw = json.loads(urllib.parse.unquote(qs.get("played_list", ["[]"])[0]))
            played_list = [
                t for t in self.server.library
                if t["file"] in {x.get("file", "") for x in played_list_raw}
            ]
        except Exception:
            played_list = []

        nxt, score, phase = pick_next(
            self.server.library, current, played_set,
            played_count, played_list, prefs=self.server.prefs,
        )

        if not nxt:
            self.ok(b'{"error":"no tracks"}', "application/json")
            return

        plan = self._build_plan(current, nxt, cur_time, phase)
        _, _, target_e, _ = phase

        self.ok(
            json.dumps({
                "track": nxt, "plan": plan,
                "score": round(score, 1),
                "phase": phase[0],
                "target_energy": round(target_e, 1),
            }, default=str).encode(),
            "application/json",
        )

    def _build_plan(self, current, nxt, current_time, phase):
        """Build mixing plan."""
        dur = float(current.get("duracion_segundos") or 0)
        ps = current.get("puede_salir")
        e1 = current.get("energia", 50) or 50
        e2 = nxt.get("energia", 50) or 50
        bpm1 = current.get("bpm", 0) or 0
        bpm2 = nxt.get("bpm", 0) or 0

        style = detect_style(phase, e1, e2, bpm1, bpm2)
        cf = fade_duration(phase, e1, e2, style)

        exit_at = float(ps) if ps else (dur - 2.0 if dur else current_time + 90)
        start_mix = exit_at - cf
        min_start = dur * 0.73 if dur else current_time + 10
        start_mix = max(start_mix, min_start, current_time + 8)

        # Entry point logic
        pem = nxt.get("puede_empezar_mezcla")
        intro_fin = nxt.get("intro_fin")
        tiene_voz = nxt.get("tiene_voz_inicio", False)

        if pem is not None:
            enter_at = float(pem)
        elif intro_fin is not None and intro_fin >= 3.0:
            bpm2 = nxt.get("bpm", 0) or 0
            if bpm2 > 0:
                beat_dur = 60.0 / bpm2
                enter_at = max(0.0, intro_fin - beat_dur * 4)
            else:
                enter_at = max(0.0, intro_fin - 4.0)
        elif tiene_voz:
            enter_at = 4.0
        else:
            enter_at = 0.0

        return {
            "start_current_time": round(start_mix, 2),
            "start_next_time": round(enter_at, 2),
            "mix_duration": cf,
            "exit_at": round(exit_at, 2),
            "phase": phase[0],
            "has_entry_point": pem is not None,
            "style": style,
        }

    def _handle_audio(self, path):
        """Serve audio files."""
        fname = urllib.parse.unquote(path[7:])
        fp = self.server.songs_dir / fname

        if not fp.exists():
            self.send_error(404)
            return

        mime = {
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
            ".flac": "audio/flac", ".aac": "audio/aac", ".m4a": "audio/mp4",
        }.get(fp.suffix.lower(), "audio/mpeg")

        data = fp.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def ok(self, data, ct):
        """Send 200 OK response."""
        self.send_response(200)
        self.send_header("Content-Type", f"{ct}; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)


def _bind_server(start_port: int):
    """Intenta bindear el primer puerto libre desde start_port.
    Si start_port es 0, deja que el SO asigne uno."""
    if start_port == 0:
        try:
            srv = HTTPServer(("", 0), DJHandler)
            return srv, srv.server_address[1]
        except OSError:
            return None, 0

    for p in range(start_port, start_port + 20):
        try:
            srv = HTTPServer(("", p), DJHandler)
            return srv, p
        except OSError:
            continue

    # Último intento en localhost
    try:
        srv = HTTPServer(("127.0.0.1", 0), DJHandler)
        return srv, srv.server_address[1]
    except OSError:
        return None, 0


def run_dj(name: str, base_dir: Path, port: int = 0) -> None:
    """Run DJ player server.

    Args:
        name: DJ name (e.g., "Nexus", "Flamenco")
        base_dir: Base directory containing canciones/, json/, preferencias.json, theme.html
        port: Starting port (0 = let OS pick; auto-fallback if occupied)
    """
    songs_dir = base_dir / "canciones"
    json_dir = base_dir / "json"
    prefs_file = base_dir / "preferencias.json"
    theme_file = base_dir / "theme.html"

    songs_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # PASO 1: BIND DEL PUERTO + AVISO A NODE — antes de nada pesado.
    # Esto garantiza que el padre reciba DJ_READY_PORT en <500ms.
    # ---------------------------------------------------------------
    server, actual_port = _bind_server(port)
    if not server or actual_port <= 0:
        print("DJ_READY_PORT=0", flush=True)
        print(f"[FATAL] No se pudo abrir ningún puerto desde {port}", flush=True)
        return

    print(f"DJ_READY_PORT={actual_port}", flush=True)
    print(f"[BOOT] {name} bound on port {actual_port}, loading data...", flush=True)

    # ---------------------------------------------------------------
    # PASO 2: Carga pesada (librería, prefs, módulos opcionales).
    # ---------------------------------------------------------------
    try:
        library = load_library(songs_dir, json_dir)
    except Exception as e:
        print(f"[WARN] Error loading library: {e}", flush=True)
        library = []

    try:
        prefs = load_prefs(prefs_file)
    except Exception as e:
        print(f"[WARN] Error loading preferences: {e}", flush=True)
        prefs = {}

    if not theme_file.exists():
        theme_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{name} DJ Player</title>
            <style>
                body {{ font-family: Arial; background: #222; color: #fff; padding: 20px; }}
                h1 {{ color: #0f0; }}
            </style>
        </head>
        <body>
            <h1>{name} DJ Player</h1>
            <p>Add MP3 files to: {songs_dir}</p>
            <div id="app"></div>
        </body>
        </html>
        """
    else:
        theme_html = theme_file.read_text(encoding="utf-8")

    # engine.js compartido
    core_dir = Path(__file__).parent
    engine_js_path = core_dir / "engine.js"
    engine_js = engine_js_path.read_text(encoding="utf-8") if engine_js_path.exists() else ""

    # Módulos opcionales (compatibility/timing)
    modules_ok = False
    try:
        sys.path.insert(0, str(core_dir))
        from compatibility_engine import CompatibilityEngine  # noqa: F401
        from timing_engine import TimingDecisionEngine  # noqa: F401
        modules_ok = True
        print("[OK] CompatibilityEngine + TimingDecisionEngine loaded", flush=True)
    except ImportError as e:
        print(f"[WARN] Engine modules not found ({e}) - fallback active", flush=True)

    # ---------------------------------------------------------------
    # PASO 3: Asignar datos al server y arrancar serve_forever.
    # ---------------------------------------------------------------
    server.library = library
    server.prefs = prefs
    server.prefs_file = prefs_file
    server.songs_dir = songs_dir
    server.json_dir = json_dir
    server.modules_ok = modules_ok
    server.html = theme_html
    server.engine_js = engine_js
    server.base_dir = base_dir

    url = f"http://localhost:{actual_port}"

    if not library:
        print(f"[WARN] No songs in {songs_dir}", flush=True)
        print(f"   Add MP3/WAV files to: {songs_dir}", flush=True)
    else:
        print(f"[OK] {len(library)} songs loaded", flush=True)

    print(f"[DJ] {name} -> {url}", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[BYE]", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[WARN] Server error: {e}", flush=True)
