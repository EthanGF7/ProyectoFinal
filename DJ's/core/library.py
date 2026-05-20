"""Library loader - read songs and metadata from directories."""
import json
from pathlib import Path


def load_library(songs_dir: Path, json_dir: Path) -> list[dict]:
    """Load music library from songs_dir and metadata from json_dir.
    
    Args:
        songs_dir: Path to folder containing MP3/WAV files
        json_dir: Path to folder containing .json metadata files
        
    Returns:
        List of track dicts with metadata
    """
    tracks = []
    exts = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"}
    
    if not songs_dir.exists():
        return tracks
    
    for f in sorted(songs_dir.iterdir()):
        if f.suffix.lower() not in exts:
            continue
        
        meta = {}
        jp = json_dir / f"{f.stem}.json"
        if jp.exists():
            try:
                raw = json.loads(jp.read_text(encoding="utf-8"))
                meta = {k: v for k, v in raw.items() if not k.startswith("_") and v is not None}
            except:
                pass
        
        # Determine start_position: prefer puede_empezar_mezcla, fallback to intro_fin
        pem = meta.get("puede_empezar_mezcla")
        intro_fin = meta.get("intro_fin")
        if pem and float(pem) > 0:
            start_position = float(pem)
        elif intro_fin and float(intro_fin) > 0:
            start_position = float(intro_fin)
        else:
            start_position = 0.0
        
        tracks.append({
            "name": f.stem,
            "file": f.name,
            "bpm": meta.get("bpm", 0),
            "energia": meta.get("energia", 50),
            "key": meta.get("key", ""),
            "estilo": meta.get("estilo", ""),
            "duracion_segundos": meta.get("duracion_segundos", 0),
            "puede_salir": meta.get("puede_salir"),
            "puede_empezar_mezcla": meta.get("puede_empezar_mezcla"),
            "debe_sonar_sola": meta.get("debe_sonar_sola"),
            "intro_fin": meta.get("intro_fin"),
            "tiene_voz_inicio": meta.get("tiene_voz_inicio", False),
            "beat_times": meta.get("beat_times", []),
            "energia_por_segundo": meta.get("energia_por_segundo", []),
            "start_position": start_position,
        })
    
    return tracks
