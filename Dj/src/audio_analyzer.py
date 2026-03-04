"""
Audio Analyzer - Detecta BPM, energía, intro y voz para cada canción
"""
import librosa
import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, Optional


class AudioAnalyzer:
    """Analiza archivos de audio y genera metadata para el sistema DJ"""
    
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
    
    def analyze_song(self, audio_path: str) -> Dict:
        print(f"Analizando: {audio_path}")
        
        y, sr = librosa.load(audio_path, sr=self.sample_rate)
        duration = librosa.get_duration(y=y, sr=sr)
        
        bpm          = self._detect_bpm(y, sr)
        energy       = self._calculate_energy(y)
        beat_times   = self._detect_beats(y, sr)
        energy_profile = self._analyze_energy_profile(y, sr)

        # Detectar dónde termina la intro
        intro_fin = self._detect_intro_end(y, sr, energy_profile)

        # Detectar si hay voz en el inicio (antes del drop)
        tiene_voz_inicio = self._detect_vocal_at_start(y, sr, intro_fin)

        metadata = {
            "bpm":                  float(bpm),
            "energia":              float(energy),
            "duracion_segundos":    float(duration),
            "beat_times":           [float(t) for t in beat_times],
            "energia_por_segundo":  [float(e) for e in energy_profile],
            "puede_salir":          float(self._calculate_exit_point(duration)),
            # Auto-detectados (sobreescribibles manualmente en el JSON)
            "intro_fin":            float(intro_fin) if intro_fin is not None else None,
            "tiene_voz_inicio":     bool(tiene_voz_inicio),
            # Manuales opcionales
            "puede_empezar_mezcla": None,
            "debe_sonar_sola":      None
        }
        
        return metadata
    
    # ── Métodos de análisis base ──────────────────────────────────

    def _detect_bpm(self, y: np.ndarray, sr: int) -> float:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, np.ndarray):
            tempo = tempo.item()
        return float(tempo)
    
    def _calculate_energy(self, y: np.ndarray) -> float:
        rms = librosa.feature.rms(y=y)[0]
        energy = np.mean(rms) * 100
        return min(100, max(0, float(energy)))
    
    def _detect_beats(self, y: np.ndarray, sr: int) -> np.ndarray:
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        return librosa.frames_to_time(beat_frames, sr=sr)
    
    def _analyze_energy_profile(self, y: np.ndarray, sr: int) -> list:
        hop_length = sr  # 1 frame = 1 segundo
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        if np.max(rms) > 0:
            energy_profile = (rms / np.max(rms) * 100)
        else:
            energy_profile = rms * 100
        return [float(e) for e in energy_profile]
    
    def _calculate_exit_point(self, duration: float) -> float:
        return round(duration * 0.9, 2)

    # ── Detección de intro ────────────────────────────────────────

    def _detect_intro_end(self, y: np.ndarray, sr: int,
                          energy_profile: list) -> Optional[float]:
        """
        Detecta cuándo termina la intro (primer momento de energía plena).

        Tres capas de análisis en consenso:

        1. Energía RMS por segundo: busca cuándo supera el 40% del máximo
           y se mantiene así ≥ 4 segundos consecutivos.
           → Bueno para canciones que empiezan suaves y explotan.

        2. Onset density: cuenta ataques por segundo y detecta el momento
           donde la densidad sube bruscamente (entrada de batería).
           → Detecta intros instrumentales lentas aunque tengan energía.

        3. Spectral flatness: intro tonal → flatness baja. Con percusión
           completa → flatness sube. Detecta la entrada del kit de batería.

        Resultado: mediana de las tres capas, ajustada a límites razonables.
        """
        ep = np.array(energy_profile)
        n  = len(ep)
        if n < 6:
            return None

        # ── Capa 1: umbral de energía ────────────────────────────
        threshold = np.max(ep) * 0.40
        layer1 = None
        for i in range(n - 3):
            if ep[i] >= threshold and np.mean(ep[i:i+4]) >= threshold * 0.85:
                layer1 = float(i)
                break

        # ── Capa 2: onset density ────────────────────────────────
        hop = 512
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop)
        onset_times  = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop)

        onset_density = np.zeros(n)
        for ot in onset_times:
            idx = int(ot)
            if 0 <= idx < n:
                onset_density[idx] += 1

        density_smooth = np.convolve(onset_density, np.ones(2)/2, mode='same')

        layer2 = None
        if len(density_smooth) > 4:
            thresh_d = np.max(density_smooth) * 0.45
            for i in range(1, n - 2):
                if (density_smooth[i] >= thresh_d and
                        density_smooth[i] > density_smooth[i-1] * 1.4):
                    layer2 = float(i)
                    break

        # ── Capa 3: spectral flatness ────────────────────────────
        flatness = librosa.feature.spectral_flatness(y=y, hop_length=sr)[0]
        layer3   = None
        if len(flatness) > 4:
            flat_smooth = np.convolve(flatness, np.ones(2)/2, mode='same')
            thresh_f = np.max(flat_smooth) * 0.35
            for i in range(1, min(n, len(flat_smooth)) - 1):
                if (flat_smooth[i] >= thresh_f and
                        flat_smooth[i] > flat_smooth[max(0, i-2)] * 1.25):
                    layer3 = float(i)
                    break

        # ── Consenso: mediana de estimaciones ───────────────────
        estimates = [x for x in [layer1, layer2, layer3] if x is not None]
        if not estimates:
            return None

        intro_candidate = float(np.median(estimates))

        # Menos de 3s = no hay intro real
        if intro_candidate < 3.0:
            return None
        # Más del 40% de la canción = no es intro, es estructura
        if intro_candidate > n * 0.40:
            intro_candidate = n * 0.40

        return round(intro_candidate, 2)

    # ── Detección de voz ──────────────────────────────────────────

    def _detect_vocal_at_start(self, y: np.ndarray, sr: int,
                                intro_fin: Optional[float]) -> bool:
        """
        Detecta si hay voz humana en el inicio de la canción.

        Analiza solo hasta intro_fin (o los primeros 10s si no hay intro).
        La voz humana tiene firma espectral característica:
          - Centroid en banda 200–3500 Hz (frecuencias vocales fundamentales)
          - ZCR moderado (0.03–0.18): ni percusión pura ni sintetizador
          - MFCC con varianza temporal alta (la voz cambia continuamente)

        Necesita ≥ 2 de 3 indicadores para confirmar voz.
        """
        ventana = min(int(intro_fin) if intro_fin else 10, 12)
        ventana = max(ventana, 4)
        y_intro = y[:ventana * sr]

        if len(y_intro) < sr:
            return False

        # Silencio: imposible que haya voz
        rms_intro = float(np.mean(librosa.feature.rms(y=y_intro)[0]))
        if rms_intro < 0.005:
            return False

        # Indicador 1: centroid en banda vocal
        centroid = librosa.feature.spectral_centroid(y=y_intro, sr=sr)[0]
        pct_vocal_band = float(np.mean((centroid > 200) & (centroid < 3500)))
        ind1 = pct_vocal_band > 0.60

        # Indicador 2: ZCR en rango vocal
        zcr      = float(np.mean(librosa.feature.zero_crossing_rate(y_intro)[0]))
        ind2     = 0.03 < zcr < 0.18

        # Indicador 3: MFCCs con varianza temporal (voz cambia, beat repite)
        mfcc     = librosa.feature.mfcc(y=y_intro, sr=sr, n_mfcc=8)
        mfcc1_m  = float(np.mean(mfcc[1]))
        mfcc_var = float(np.mean(np.var(mfcc[1:5], axis=1)))
        ind3     = mfcc1_m < -5 and mfcc_var > 20

        return sum([ind1, ind2, ind3]) >= 2

    # ── Guardado y lote ──────────────────────────────────────────

    def save_metadata(self, audio_path: str, output_dir: str):
        
        metadata = self.analyze_song(audio_path)
        
        audio_name = Path(audio_path).stem
        json_path  = os.path.join(output_dir, f"{audio_name}.json")
        
        # Preservar campos manuales si ya existe el JSON
        manual_fields = {}
        if os.path.exists(json_path):
            try:
                existing = json.loads(Path(json_path).read_text(encoding='utf-8'))
                for field in ('puede_empezar_mezcla', 'debe_sonar_sola'):
                    if existing.get(field) is not None:
                        manual_fields[field] = existing[field]
            except: pass
        metadata.update(manual_fields)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        intro_str = f"{metadata['intro_fin']:.1f}s" if metadata['intro_fin'] else "sin intro detectada"
        voz_str   = "⚠ VOZ al inicio" if metadata['tiene_voz_inicio'] else "sin voz"
        print(f"✔ {json_path}")
        print(f"  BPM: {metadata['bpm']:.1f} | Energía: {metadata['energia']:.1f} | "
              f"Intro: {intro_str} | {voz_str}")
    
    def batch_analyze(self, songs_dir: str, json_dir: str):
        os.makedirs(json_dir, exist_ok=True)
        
        extensions = ['.mp3', '.wav']
        songs = []
        for ext in extensions:
            songs.extend(Path(songs_dir).glob(f'*{ext}'))
        
        print(f"\n🎵 {len(songs)} canciones encontradas\n")
        
        for i, song_path in enumerate(songs, 1):
            print(f"[{i}/{len(songs)}]")
            try:
                self.save_metadata(str(song_path), json_dir)
            except Exception as e:
                print(f"✗ Error en {song_path.name}: {e}")
            print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Uso: python audio_analyzer.py <directorio_canciones> <directorio_json>")
        sys.exit(1)
    
    AudioAnalyzer().batch_analyze(sys.argv[1], sys.argv[2])
    
    print("✅ Análisis completado!")
    print("\n💡 intro_fin y tiene_voz_inicio son automáticos.")
    print("   Puedes corregirlos manualmente en cada JSON si la detección falla.")