"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  AUDIO ANALYZER v4  —  El cerebro que "lee" cada canción antes de mezclarla ║
║                                                                              ║
║  Mejoras v4:                                                                 ║
║   · BPM multi-método con confidence score (3 algoritmos + votación)          ║
║   · Detección de tonalidad (key) con perfiles Krumhansl-Kessler              ║
║   · Energía perceptual (RMS + ponderación espectral)                         ║
║   · Beats interpolados para gaps largos                                      ║
║   · Punto de salida inteligente basado en estructura                         ║
║   · 4.ª capa para detección de intro (onset strength)                        ║
║   · Threshold adaptativo de frases vocales (mediana + factor)                ║
║   · Procesamiento paralelo para análisis sin Demucs (--workers N)            ║
║                                                                              ║
║  Uso:  python audio_analyzer.py musica/canciones musica/json                 ║
║        python src/audio_analyzer.py musica/canciones musica/json --stems-dir musica/stems
║        python audio_analyzer.py musica/canciones musica/json --workers 4     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import concurrent.futures
import logging

import librosa
import numpy as np
import json
import os
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  BLOQUE 1: DEMUCS — SEPARACIÓN DE VOZ E INSTRUMENTAL
# ══════════════════════════════════════════════════════════════════════════════

def check_demucs() -> bool:
    return shutil.which("demucs") is not None or _python_has_demucs()

def _python_has_demucs() -> bool:
    try:
        import demucs  # noqa
        return True
    except ImportError:
        return False

def install_demucs():
    log.info("📦 Instalando demucs (esto solo ocurre la primera vez)...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "demucs"],
        check=True, capture_output=True
    )
    log.info("✅ Demucs instalado")

def separate_stems(audio_path: str, stems_base_dir: str) -> Optional[Dict[str, str]]:
    """
    Separa voz e instrumental con Demucs htdemucs.
    Devuelve {"vocals": path, "no_vocals": path} o None si falla.
    Cachea: si ya existen los stems no vuelve a procesar.
    """
    audio_path     = Path(audio_path)
    stem_name      = audio_path.stem
    song_dir       = Path(stems_base_dir) / stem_name
    vocals_path    = song_dir / "vocals.wav"
    no_vocals_path = song_dir / "no_vocals.wav"

    if vocals_path.exists() and no_vocals_path.exists():
        log.info("  ↩ Stems ya existentes, reutilizando")
        return {"vocals": str(vocals_path), "no_vocals": str(no_vocals_path)}

    Path(stems_base_dir).mkdir(parents=True, exist_ok=True)
    log.info("  🎛  Separando stems con Demucs (htdemucs)...")
    log.info("      Puede tardar 1-3 min la primera vez.")

    try:
        import torch
        import soundfile as sf
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        from demucs.audio import convert_audio

        model = get_model("htdemucs")
        model.eval()

        y_raw, sr_raw = librosa.load(str(audio_path), sr=None, mono=False)
        if y_raw.ndim == 1:
            y_raw = np.stack([y_raw, y_raw])

        wav = torch.tensor(y_raw, dtype=torch.float32).unsqueeze(0)
        wav = convert_audio(wav, sr_raw, model.samplerate, model.audio_channels)

        with torch.no_grad():
            sources = apply_model(model, wav, progress=True)[0]

        voc_idx    = model.sources.index("vocals")
        novoc_idxs = [i for i in range(len(model.sources)) if i != voc_idx]
        vocals     = sources[voc_idx].numpy()
        no_vocals  = sum(sources[i] for i in novoc_idxs).numpy()

        song_dir.mkdir(parents=True, exist_ok=True)
        sf.write(str(vocals_path),    vocals.T,    model.samplerate, subtype="FLOAT")
        sf.write(str(no_vocals_path), no_vocals.T, model.samplerate, subtype="FLOAT")

        log.info(f"  ✅ Stems guardados en {song_dir}")
        return {"vocals": str(vocals_path), "no_vocals": str(no_vocals_path)}

    except ImportError as e:
        log.warning(f"  ⚠ Dependencia faltante: {e}")
    except Exception as e:
        log.warning(f"  ⚠ Error en separación: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  BLOQUE 2: MAPA DE FRASES VOCALES
# ══════════════════════════════════════════════════════════════════════════════

def map_vocal_phrases(
    vocals_path: str,
    duration: float,
    bpm: float,
    min_phrase_sec: float = 2.0,
) -> list:
    """
    Detecta cuándo canta el artista analizando la energía de vocals.wav.
    Devuelve [[inicio, fin], ...] en segundos con snap al beat.

    Mejora v4: threshold adaptativo basado en mediana + factor (más robusto
    que percentil del máximo para canciones con mucha dinámica).
    """
    try:
        y_voc, sr = librosa.load(vocals_path, sr=22050)
    except Exception as e:
        log.warning(f"  ⚠ No se pudo cargar vocals: {e}")
        return []

    hop        = int(sr * 0.08)
    rms        = librosa.feature.rms(y=y_voc, hop_length=hop)[0]
    times      = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    k          = max(1, int(0.4 / 0.08))
    rms_smooth = np.convolve(rms, np.ones(k) / k, mode='same')

    # Threshold: mediana + factor (tolerante con canciones suaves)
    threshold = max(
        float(np.percentile(rms_smooth, 60) * 1.5),
        float(np.max(rms_smooth) * 0.12),
    )

    phrases   = []
    seg_start = None

    def _snap_beat(t):
        if bpm <= 0: return round(t, 2)
        bd = 60.0 / bpm
        return round(round(t / bd) * bd, 2)

    for t, e in zip(times, rms_smooth):
        if e >= threshold:
            if seg_start is None:
                seg_start = float(t)
        else:
            if seg_start is not None:
                seg_end = float(t)
                if seg_end - seg_start >= min_phrase_sec:
                    s, e2 = _snap_beat(seg_start), _snap_beat(seg_end)
                    if e2 - s >= min_phrase_sec:
                        phrases.append([s, e2])
                seg_start = None

    if seg_start is not None:
        seg_end = float(times[-1])
        if seg_end - seg_start >= min_phrase_sec:
            s, e2 = _snap_beat(seg_start), _snap_beat(seg_end)
            phrases.append([s, e2])

    # Fusionar gaps < 1.5s
    merged = []
    for ph in phrases:
        if merged and ph[0] - merged[-1][1] < 1.5:
            merged[-1][1] = ph[1]
        else:
            merged.append(ph)

    log.info(f"  🎤 {len(merged)} frases vocales mapeadas")
    return merged


# ══════════════════════════════════════════════════════════════════════════════
#  BLOQUE 3: DETECCIÓN DE TONALIDAD (KEY)
#  Algoritmo: correlación con perfiles Krumhansl-Kessler (KK)
# ══════════════════════════════════════════════════════════════════════════════

# Perfiles KK clásicos para 12 tonos (empezando en Do/C)
_KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                       2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                       2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

_NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
# Preferir bemoles para evitar confusión con la rueda de Camelot de player.py
_SHARP_TO_FLAT = {
    'C#': 'Db', 'D#': 'Eb', 'F#': 'Gb', 'G#': 'Ab', 'A#': 'Bb'
}


def detect_key(y: np.ndarray, sr: int) -> Tuple[str, float]:
    """
    Detecta la tonalidad de la canción y devuelve (key, confidence).
    Ejemplo: ('Am', 0.87), ('Db', 0.72)

    Usa chroma CQT (mejor resolución armónica que STFT) comparado con
    los perfiles KK rotados para las 24 tonalidades (12 mayor + 12 menor).
    """
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=36)
    except Exception:
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)

    profile = np.mean(chroma, axis=1)
    if np.max(profile) > 0:
        profile = profile / np.max(profile)

    best_score = -np.inf
    best_root  = 'C'
    best_mode  = 'major'

    for i in range(12):
        for mode, template in [('major', _KK_MAJOR), ('minor', _KK_MINOR)]:
            rot   = np.roll(template, i)
            rot_n = rot / np.max(rot)
            score = float(np.corrcoef(profile, rot_n)[0, 1])
            if score > best_score:
                best_score = score
                best_root  = _NOTES[i]
                best_mode  = mode

    # Formatear: C major → "C", A minor → "Am"
    root = _SHARP_TO_FLAT.get(best_root, best_root)
    key_str = root if best_mode == 'major' else root + 'm'

    # Confidence: mapear [-1,1] → [0,1]
    confidence = round((best_score + 1) / 2, 3)
    return key_str, confidence


# ══════════════════════════════════════════════════════════════════════════════
#  BLOQUE 4: CLASE PRINCIPAL — AudioAnalyzer
# ══════════════════════════════════════════════════════════════════════════════

class AudioAnalyzer:

    def __init__(self, sample_rate: int = 22050, use_demucs: bool = True):
        self.sample_rate = sample_rate
        self.use_demucs  = use_demucs

    # ── Análisis principal ────────────────────────────────────────────────────
    def analyze_song(self, audio_path: str, stems_dir: Optional[str] = None) -> Dict:
        log.info(f"Analizando: {Path(audio_path).name}")

        y, sr  = librosa.load(audio_path, sr=self.sample_rate)
        dur    = float(librosa.get_duration(y=y, sr=sr))

        bpm, bpm_conf = self._detect_bpm(y, sr)
        energy        = self._calculate_energy(y, sr)
        beats         = self._detect_beats(y, sr)
        ep            = self._analyze_energy_profile(y, sr)
        key, key_conf = detect_key(y, sr)

        intro_fin        = self._detect_intro_end(y, sr, ep)
        tiene_voz_inicio = self._detect_vocal_at_start(y, sr, intro_fin)
        structure_pts    = self._detect_structure_points(y, sr, dur, bpm)

        # Punto de salida: último punto estructural en 75-92% de la duración
        ps = self._calculate_exit_point(dur, structure_pts)

        vocal_phrases = []
        has_stems     = False
        if self.use_demucs and stems_dir:
            stems = separate_stems(audio_path, stems_dir)
            if stems:
                has_stems     = True
                vocal_phrases = map_vocal_phrases(stems["vocals"], dur, bpm)

        log.info(
            f"  BPM: {bpm:.1f} ({bpm_conf:.0%}) | E: {energy:.1f} | "
            f"Key: {key} ({key_conf:.0%}) | Intro: "
            f"{'%.1fs' % intro_fin if intro_fin else '—'} | "
            f"Voz: {'⚠' if tiene_voz_inicio else 'ok'} | "
            f"{'✅ %d frases' % len(vocal_phrases) if has_stems else 'sin stems'} | "
            f"Estructura: {len(structure_pts)} pts"
        )

        return {
            # ── Generados automáticamente ──────────────────────────────────
            "bpm":                  round(float(bpm), 2),
            "bpm_confidence":       bpm_conf,
            "energia":              round(float(energy), 2),
            "duracion_segundos":    round(float(dur), 3),
            "key":                  key,
            "key_confidence":       key_conf,
            "beat_times":           [round(float(t), 3) for t in beats],
            "energia_por_segundo":  [round(float(e), 2) for e in ep],
            "puede_salir":          round(float(ps), 2),
            "intro_fin":            round(float(intro_fin), 2) if intro_fin else None,
            "tiene_voz_inicio":     bool(tiene_voz_inicio),
            "has_stems":            has_stems,
            "vocal_phrases":        vocal_phrases,
            "structure_points":     structure_pts,

            # (sin campos manuales — todo se calcula automáticamente)
        }

    # ── BPM multi-método ──────────────────────────────────────────────────────
    def _detect_bpm(self, y: np.ndarray, sr: int) -> Tuple[float, float]:
        """
        3 algoritmos independientes + votación por mediana.
          1. beat_track estándar (percusión global)
          2. beat_track en banda de bajos (bombo — más estable en EDM)
          3. Tempogram de onset strength global

        Resuelve conflictos de doble/mitad tempo antes de hacer la mediana.
        Confidence = acuerdo entre los 3 métodos (más acuerdo → más confidence).
        """
        # Método 1
        t1, _ = librosa.beat.beat_track(y=y, sr=sr)
        t1 = float(t1.item() if isinstance(t1, np.ndarray) else t1)

        # Método 2: enfatizar bajos
        try:
            y_low = librosa.effects.preemphasis(y, coef=-0.97)
            t2, _ = librosa.beat.beat_track(y=y_low, sr=sr, start_bpm=t1)
            t2 = float(t2.item() if isinstance(t2, np.ndarray) else t2)
        except Exception:
            t2 = t1

        # Método 3: tempogram
        try:
            onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
            tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
            ac        = np.mean(tempogram, axis=1)
            freqs     = librosa.tempo_frequencies(len(ac), sr=sr)
            mask      = (freqs >= 60) & (freqs <= 200)
            t3 = float(freqs[mask][np.argmax(ac[mask])]) if mask.any() else t1
        except Exception:
            t3 = t1

        # Resolver doble/mitad
        def resolve(t, ref, tol=6.0):
            if abs(t - ref) <= tol:        return t
            if abs(t * 2 - ref) <= tol:    return t * 2
            if abs(t / 2 - ref) <= tol:    return t / 2
            return t

        resolved = [t1, resolve(t2, t1), resolve(t3, t1)]
        bpm      = float(np.median(resolved))

        avg_diff   = float(np.mean([abs(t - bpm) for t in resolved]))
        confidence = round(max(0.0, min(1.0, 1.0 - avg_diff / 10.0)), 3)

        return round(bpm, 2), confidence

    # ── Energía perceptual ────────────────────────────────────────────────────
    def _calculate_energy(self, y: np.ndarray, sr: int) -> float:
        """
        80% RMS + 20% ponderación espectral.
        Las frecuencias altas (hi-hat, synths agudos) aumentan la percepción
        de energía aunque el RMS absoluto no cambie mucho.
        """
        rms = float(np.mean(librosa.feature.rms(y=y)[0]))
        try:
            centroid      = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            centroid_norm = float(np.mean(np.clip(centroid / 5000, 0, 1)))
        except Exception:
            centroid_norm = 0.5
        energy_raw = rms * 0.80 + rms * centroid_norm * 0.20
        return float(min(100, max(0, energy_raw * 100)))

    # ── Beats con interpolación ───────────────────────────────────────────────
    def _detect_beats(self, y: np.ndarray, sr: int) -> np.ndarray:
        """
        beat_track + post-procesado:
          - Elimina duplicados (gap < 0.1s)
          - Interpola beats perdidos en gaps > 2.5× el periodo mediano
        """
        _, frames = librosa.beat.beat_track(y=y, sr=sr)
        times     = librosa.frames_to_time(frames, sr=sr)

        if len(times) < 2:
            return times

        # Eliminar duplicados
        cleaned = [times[0]]
        for t in times[1:]:
            if t - cleaned[-1] > 0.1:
                cleaned.append(t)
        times = np.array(cleaned)

        # Interpolar gaps
        if len(times) > 2:
            diffs  = np.diff(times)
            median = np.median(diffs)
            filled = [times[0]]
            for i, d in enumerate(diffs):
                t_prev = times[i]
                t_next = times[i + 1]
                if d > median * 2.5:
                    n_missing = round(d / median) - 1
                    for k in range(1, n_missing + 1):
                        filled.append(t_prev + k * median)
                filled.append(t_next)
            times = np.array(filled)

        return times

    # ── Perfil de energía ─────────────────────────────────────────────────────
    def _analyze_energy_profile(self, y: np.ndarray, sr: int) -> List[float]:
        """RMS por segundo normalizado a 0-100, con suavizado de 3s."""
        rms = librosa.feature.rms(y=y, hop_length=sr)[0]
        if np.max(rms) > 0:
            ep = rms / np.max(rms) * 100
        else:
            ep = rms * 100
        if len(ep) > 3:
            ep = np.convolve(ep, np.ones(3) / 3, mode='same')
        return [round(float(e), 2) for e in ep]

    # ── Punto de salida inteligente ───────────────────────────────────────────
    def _calculate_exit_point(
        self, duration: float, structure_points: List[float]
    ) -> float:
        """
        Usa el último punto estructural entre 75-92% de la duración
        (salida del último drop/chorus). Fallback: 90%.
        """
        fallback = round(duration * 0.90, 2)
        if not structure_points:
            return fallback
        candidates = [p for p in structure_points
                      if duration * 0.75 <= p <= duration * 0.92]
        return round(max(candidates), 2) if candidates else fallback

    # ── Detección de intro ────────────────────────────────────────────────────
    def _detect_intro_end(
        self, y: np.ndarray, sr: int, ep: List[float]
    ) -> Optional[float]:
        """
        4 capas independientes en consenso (mediana):
          1. Salto de energía RMS
          2. Densidad de onsets
          3. Spectral flatness
          4. Onset strength global (kicks)  ← nuevo en v4
        """
        n = len(ep)
        if n < 4:
            return None

        ep_arr = np.array(ep)

        # Capa 1
        layer1 = None
        thr1   = np.max(ep_arr) * 0.50
        for i in range(1, min(n, 45)):
            if ep_arr[i] >= thr1 and ep_arr[i] > ep_arr[i - 1] * 1.25:
                layer1 = float(i); break

        # Capa 2: densidad de onsets
        try:
            ot  = librosa.frames_to_time(
                librosa.onset.onset_detect(y=y, sr=sr, hop_length=sr),
                sr=sr, hop_length=sr)
            od  = np.zeros(n)
            for t in ot:
                idx = int(t)
                if 0 <= idx < n: od[idx] += 1
            od_s = np.convolve(od, np.ones(2) / 2, mode='same')
        except Exception:
            od_s = np.zeros(n)

        layer2 = None
        td = np.max(od_s) * 0.45
        for i in range(1, n - 2):
            if od_s[i] >= td and od_s[i] > od_s[i - 1] * 1.35:
                layer2 = float(i); break

        # Capa 3: spectral flatness
        layer3 = None
        try:
            fl   = librosa.feature.spectral_flatness(y=y, hop_length=sr)[0]
            fl_s = np.convolve(fl, np.ones(2) / 2, mode='same')
            tf   = np.max(fl_s) * 0.35
            for i in range(1, min(n, len(fl_s)) - 1):
                if fl_s[i] >= tf and fl_s[i] > fl_s[max(0, i - 2)] * 1.20:
                    layer3 = float(i); break
        except Exception:
            pass

        # Capa 4: onset strength por segundo
        layer4 = None
        try:
            env   = librosa.onset.onset_strength(y=y, sr=sr)
            t_env = librosa.frames_to_time(np.arange(len(env)), sr=sr)
            os_s  = np.zeros(n)
            for t, v in zip(t_env, env):
                idx = int(t)
                if 0 <= idx < n: os_s[idx] += v
            os_sm = np.convolve(os_s, np.ones(3) / 3, mode='same')
            thr4  = np.max(os_sm) * 0.50
            for i in range(1, min(n, 40)):
                if os_sm[i] >= thr4 and os_sm[i] > os_sm[max(0, i - 2)] * 1.30:
                    layer4 = float(i); break
        except Exception:
            pass

        estimates = [x for x in [layer1, layer2, layer3, layer4] if x is not None]
        if not estimates:
            return None

        c = float(np.median(estimates))
        if c < 3.0: return None
        if c > n * 0.40: c = n * 0.40
        return round(c, 2)

    # ── Voz al inicio ──────────────────────────────────────────────────────────
    def _detect_vocal_at_start(
        self, y: np.ndarray, sr: int, intro_fin: Optional[float]
    ) -> bool:
        """3 indicadores acústicos de voz; requiere ≥2/3 para True."""
        ventana = min(int(intro_fin) if intro_fin else 10, 12)
        ventana = max(ventana, 4)
        y_i     = y[:ventana * sr]

        if len(y_i) < sr: return False
        if float(np.mean(librosa.feature.rms(y=y_i)[0])) < 0.005: return False

        c  = librosa.feature.spectral_centroid(y=y_i, sr=sr)[0]
        i1 = float(np.mean((c > 200) & (c < 3500))) > 0.60

        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y_i)[0]))
        i2  = 0.03 < zcr < 0.18

        try:
            mfc = librosa.feature.mfcc(y=y_i, sr=sr, n_mfcc=8)
            i3  = float(np.mean(mfc[1])) < -5 and \
                  float(np.mean(np.var(mfc[1:5], axis=1))) > 20
        except Exception:
            i3 = False

        return sum([i1, i2, i3]) >= 2

    # ── Estructura musical ────────────────────────────────────────────────────
    def _detect_structure_points(
        self, y: np.ndarray, sr: int, duration: float, bpm: float
    ) -> List[float]:
        """
        3 novelty curves ponderadas (spectral contrast 40% + RMS 35% + chroma 25%).
        Picos ajustados al bar (4 beats) más cercano. Mín 8s entre puntos.
        """
        hop = 512

        try:
            sc   = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=hop)
            sc_n = np.abs(np.diff(np.mean(sc, axis=0), prepend=0))
        except Exception:
            sc_n = np.zeros(len(y) // hop + 1)

        rms   = librosa.feature.rms(y=y, hop_length=hop)[0]
        rms_n = np.abs(np.diff(rms, prepend=rms[0]))

        try:
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
            ch_n   = np.sqrt(np.sum(
                np.diff(chroma, axis=1, prepend=chroma[:, :1]) ** 2, axis=0))
        except Exception:
            ch_n = np.zeros_like(rms_n)

        def norm(x):
            m = np.max(x)
            return x / m if m > 0 else x

        n       = min(len(sc_n), len(rms_n), len(ch_n))
        novelty = norm(sc_n[:n]) * 0.40 + norm(rms_n[:n]) * 0.35 + norm(ch_n[:n]) * 0.25
        kw      = max(1, int(2.0 * sr / hop))
        novelty = np.convolve(novelty, np.ones(kw) / kw, mode='same')

        times    = librosa.frames_to_time(np.arange(n), sr=sr, hop_length=hop)
        thr      = np.percentile(novelty, 75)
        min_dist = max(1, int(8.0 * sr / hop))

        peaks, last = [], -min_dist
        for i in range(1, n - 1):
            if (novelty[i] > thr and
                    novelty[i] > novelty[i - 1] and
                    novelty[i] > novelty[i + 1] and
                    i - last >= min_dist):
                peaks.append(float(times[i]))
                last = i

        if bpm > 0:
            bar     = 4 * 60.0 / bpm
            snapped = []
            for t in peaks:
                st = round(round(t / bar) * bar, 2)
                if not snapped or abs(st - snapped[-1]) > bar * 0.5:
                    snapped.append(st)
            peaks = snapped

        return sorted(t for t in peaks if 8.0 <= t <= duration * 0.95)

    # ── Guardar JSON ──────────────────────────────────────────────────────────
    def save_metadata(
        self, audio_path: str, json_dir: str, stems_dir: Optional[str] = None
    ):
        meta = self.analyze_song(audio_path, stems_dir)
        out  = Path(json_dir) / f"{Path(audio_path).stem}.json"
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        log.info(f"  💾 {out.name}")

    # ── Análisis en lote ──────────────────────────────────────────────────────
    def batch_analyze(
        self,
        songs_dir: str,
        json_dir: str,
        stems_dir: Optional[str] = None,
        workers: int = 1,
    ):
        """
        Analiza todas las canciones de una carpeta.
        Con workers > 1 usa ProcessPoolExecutor (solo sin Demucs — GPU no es thread-safe).
        """
        os.makedirs(json_dir, exist_ok=True)
        if stems_dir:
            os.makedirs(stems_dir, exist_ok=True)

        exts  = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}
        songs = sorted(p for p in Path(songs_dir).iterdir()
                       if p.suffix.lower() in exts)

        log.info(f"\n🎵 {len(songs)} canciones encontradas")
        if self.use_demucs and stems_dir:
            log.info("🎛  Demucs activo — separación de voz automática")
        else:
            log.info("⚠  Sin Demucs — acappella no disponible")

        # Demucs no es thread-safe → forzar secuencial
        effective_workers = 1 if (self.use_demucs and stems_dir) else max(1, workers)

        def _process(path):
            log.info(f"\n[{songs.index(path)+1}/{len(songs)}] {path.name}")
            try:
                self.save_metadata(str(path), json_dir, stems_dir)
                return True
            except Exception as e:
                log.error(f"  ✗ Error: {e}")
                return False

        if effective_workers == 1:
            results = [_process(p) for p in songs]
        else:
            log.info(f"⚡ Procesamiento paralelo — {effective_workers} workers")
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=effective_workers
            ) as ex:
                results = list(ex.map(_process, songs))

        ok = sum(results)
        log.info(f"\n✅ Completado — {ok}/{len(results)} canciones OK")
        log.info("💡 Edita 'structure_points' o 'puede_salir' en el JSON si es necesario.")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="DJ AI — Audio Analyzer v4")
    p.add_argument("songs_dir",  help="Carpeta con MP3/WAV")
    p.add_argument("json_dir",   help="Carpeta donde guardar los JSONs")
    p.add_argument("--stems-dir", default=None,
                   help="Carpeta para guardar stems (activa Demucs). Ej: musica/stems")
    p.add_argument("--no-demucs", action="store_true",
                   help="Desactivar Demucs aunque esté instalado")
    p.add_argument("--workers", type=int, default=1,
                   help="Workers paralelos (solo sin Demucs). Default: 1")
    args = p.parse_args()

    use_demucs = not args.no_demucs and args.stems_dir is not None

    if use_demucs and not check_demucs():
        try:
            install_demucs()
        except Exception as e:
            log.warning(f"⚠ No se pudo instalar demucs: {e}")
            log.warning("  pip install demucs — continuando sin stems...\n")
            use_demucs = False

    AudioAnalyzer(use_demucs=use_demucs).batch_analyze(
        songs_dir = args.songs_dir,
        json_dir  = args.json_dir,
        stems_dir = args.stems_dir if use_demucs else None,
        workers   = args.workers,
    )