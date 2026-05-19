"""HTTP Server - runs DJ player with configurable port and auto-fallback."""
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
                    "application/json"
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
            played_list = [t for t in self.server.library
                           if t["file"] in {x.get("file", "") for x in played_list_raw}]
        except Exception:
            played_list = []

        nxt, score, phase = pick_next(
            self.server.library, current, played_set,
            played_count, played_list, prefs=self.server.prefs
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
            "application/json"
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
            ".flac": "audio/flac", ".aac": "audio/aac", ".m4a": "audio/mp4"
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


def run_dj(name: str, base_dir: Path, port: int = 8765) -> None:
    """Run DJ player server.

    Args:
        name: DJ name (e.g., "Nexus", "Flamenco")
        base_dir: Base directory containing canciones/, json/, preferencias.json, theme.html
        port: Starting port (auto-fallback if occupied)
    """

    songs_dir = base_dir / "canciones"
    json_dir = base_dir / "json"
    prefs_file = base_dir / "preferencias.json"
    theme_file = base_dir / "theme.html"

    songs_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    # Load data
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

    # Load engine.js (shared)
    core_dir = Path(__file__).parent
    engine_js_path = core_dir / "engine.js"
    if engine_js_path.exists():
        engine_js = engine_js_path.read_text(encoding="utf-8")
    else:
        engine_js = ""

    # Try to load shared engine modules (now in core/)
    modules_ok = False
    try:
        sys.path.insert(0, str(core_dir))
        from compatibility_engine import CompatibilityEngine  # noqa: F401
        from timing_engine import TimingDecisionEngine  # noqa: F401
        modules_ok = True
        print("[OK] CompatibilityEngine + TimingDecisionEngine loaded")
    except ImportError as e:
        print(f"[WARN] Engine modules not found ({e}) - fallback active")

    # Find available port
    actual_port = port
    server = None
    for p in range(port, port + 20):
        try:
            server = HTTPServer(("", p), DJHandler)
            actual_port = p
            break
        except OSError:
            continue

    if not server:
        try:
            server = HTTPServer(("127.0.0.1", port), DJHandler)
            actual_port = port
        except OSError:
            server = None

    # Signal to parent processes (Node) about the real port.
    # Must come before any slow operations and with immediate flush.
    print(f"DJ_READY_PORT={actual_port}", flush=True)

    if not server:
        print(f"[WARN] Could not bind to any port, proceeding in degraded mode", flush=True)
        return

    # Attach data to server
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
        print(f"\n[WARN] No songs in {songs_dir}")
        print(f"   Add MP3/WAV files to: {songs_dir}\n")
    else:
        print(f"\n[OK] {len(library)} songs loaded")

    print(f"[DJ] {name} -> {url}\n", flush=True)

    # Open browser
    # threading.Thread(
    #     target=lambda: (time.sleep(1), webbrowser.open(url)),
    #     daemon=True
    # ).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BYE]")
        sys.exit(0)
    except Exception as e:
        print(f"[WARN] Server error: {e}", flush=True)