"""
Audio Analyzer - Detecta BPM, energía, intro y voz para cada canción
"""
import librosa
import numpy as np
import json
import os
from pathlib import Path
from typing import Dict, Optional, List, Union


class AudioAnalyzer:
    """Analiza archivos de audio y genera metadata para el sistema DJ"""
    
    def __init__(self, sample_rate: int = 22050):
        """
        Args:
            sample_rate: Frecuencia de muestreo para análisis (22050 es suficiente para BPM)
        """
        self.sample_rate = sample_rate
    
    def analyze_song(self, audio_path: Union[str, Path]) -> Dict:
        """
        Analiza una canción completa y extrae toda su metadata
        
        Args:
            audio_path: Ruta al archivo de audio (mp3 o wav)
            
        Returns:
            Dict con BPM, energía, duración, beats, intro_fin, tiene_voz_inicio, etc.
        """
        audio_path = Path(audio_path)
        print(f"Analizando: {audio_path.name}")
        
        # Cargar audio
        y, sr = librosa.load(audio_path, sr=self.sample_rate)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Detecciones base
        bpm = self._detect_bpm(y, sr)
        energy = self._calculate_energy(y)
        beat_times = self._detect_beats(y, sr)
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
            # Manuales opcionales (el usuario los completará después)
            "puede_empezar_mezcla": None,
            "debe_sonar_sola":      None
        }
        
        return metadata
    
    # ── Métodos de análisis base ──────────────────────────────────

    def _detect_bpm(self, y: np.ndarray, sr: int) -> float:
        """Detecta el BPM usando análisis temporal"""
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, np.ndarray):
            tempo = tempo.item()
        return float(tempo)
    
    def _calculate_energy(self, y: np.ndarray) -> float:
        """
        Calcula la energía general de la canción (0-100)
        Usa RMS (Root Mean Square) normalizado
        """
        rms = librosa.feature.rms(y=y)[0]
        energy = np.mean(rms) * 100
        return min(100, max(0, float(energy)))
    
    def _detect_beats(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Detecta los tiempos exactos de cada beat"""
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        return beat_times
    
    def _analyze_energy_profile(self, y: np.ndarray, sr: int) -> List[float]:
        """
        Analiza la energía segundo a segundo para detectar momentos
        más estables o intensos
        """
        hop_length = sr  # 1 segundo por frame
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        if np.max(rms) > 0:
            energy_profile = (rms / np.max(rms) * 100)
        else:
            energy_profile = rms * 100
        return [float(e) for e in energy_profile]
    
    def _calculate_exit_point(self, duration: float) -> float:
        """
        Calcula el punto de salida obligatorio (por defecto: 90% de la canción)
        El usuario puede ajustarlo manualmente después
        """
        return round(duration * 0.9, 2)

    # ── Detección de intro ────────────────────────────────────────

    def _detect_intro_end(self, y: np.ndarray, sr: int,
                          energy_profile: List[float]) -> Optional[float]:
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
        if n < 6:  # Muy corto para detectar intro
            return None

        # ── Capa 1: umbral de energía ────────────────────────────
        threshold = np.max(ep) * 0.40
        layer1 = None
        for i in range(n - 3):
            if ep[i] >= threshold and np.mean(ep[i:i+4]) >= threshold * 0.85:
                layer1 = float(i)
                break

        # ── Capa 2: onset density ────────────────────────────────
        hop_onset = 512
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_onset)
        onset_times  = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_onset)

        onset_density = np.zeros(n)
        for ot in onset_times:
            idx = int(ot)
            if 0 <= idx < n:  # Protección contra índices fuera de rango
                onset_density[idx] += 1

        # Suavizado con media móvil de 2 puntos
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
        # Necesitamos al menos 1 segundo de audio para calcular flatness con hop_length=sr
        layer3 = None
        if len(y) >= sr:  # Aseguramos que hay suficiente audio
            flatness = librosa.feature.spectral_flatness(y=y, hop_length=sr)[0]
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
        # Definir ventana de análisis: hasta intro_fin o 10s (máx 12s)
        ventana = min(int(intro_fin) if intro_fin else 10, 12)
        ventana = max(ventana, 4)  # Al menos 4 segundos
        y_intro = y[:ventana * sr]

        if len(y_intro) < sr:  # Muy corto, no podemos determinar
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
        # Tomamos el primer coeficiente MFCC (excluyendo el 0 que es energía)
        mfcc1_m  = float(np.mean(mfcc[1]))
        mfcc_var = float(np.mean(np.var(mfcc[1:5], axis=1)))
        ind3     = mfcc1_m < -5 and mfcc_var > 20

        return sum([ind1, ind2, ind3]) >= 2

    # ── Guardado y lote ──────────────────────────────────────────

    def save_metadata(self, audio_path: Union[str, Path], output_dir: Union[str, Path]):
        """
        Analiza una canción y guarda su JSON en el directorio especificado
        
        Args:
            audio_path: Ruta al archivo de audio
            output_dir: Directorio donde guardar el JSON
        """
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        metadata = self.analyze_song(audio_path)
        
        json_path = output_dir / f"{audio_path.stem}.json"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        intro_str = f"{metadata['intro_fin']:.1f}s" if metadata['intro_fin'] else "sin intro detectada"
        voz_str   = "⚠ CON VOZ al inicio" if metadata['tiene_voz_inicio'] else "sin voz"
        print(f"✔ {json_path.name}")
        print(f"  BPM: {metadata['bpm']:.1f} | Energía: {metadata['energia']:.1f} | "
              f"Intro: {intro_str} | {voz_str}")
    
    def batch_analyze(self, songs_dir: Union[str, Path], json_dir: Union[str, Path]):
        """
        Analiza todas las canciones en un directorio
        
        Args:
            songs_dir: Directorio con archivos mp3/wav
            json_dir: Directorio donde guardar los JSONs
        """
        songs_dir = Path(songs_dir).resolve()
        json_dir = Path(json_dir).resolve()
        
        if not songs_dir.is_dir():
            print(f"❌ El directorio de canciones no existe: {songs_dir}")
            return
        
        json_dir.mkdir(parents=True, exist_ok=True)
        
        # Extensiones soportadas
        extensions = ['.mp3', '.wav', '.flac', '.m4a', '.ogg']  # Añadidas más comunes
        songs = []
        for ext in extensions:
            songs.extend(songs_dir.glob(f'*{ext}'))
            songs.extend(songs_dir.glob(f'*{ext.upper()}'))  # Por si acaso mayúsculas
        
        # Ordenar alfabéticamente
        songs = sorted(songs)
        
        print(f"\n🎵 Encontradas {len(songs)} canciones en {songs_dir}\n")
        
        for i, song_path in enumerate(songs, 1):
            print(f"[{i}/{len(songs)}] {song_path.name}")
            try:
                self.save_metadata(song_path, json_dir)
            except Exception as e:
                print(f"✗ Error: {e}")
                # Opcional: imprimir traceback para depurar
                # import traceback
                # traceback.print_exc()
            print()


def main():
    """Función principal que maneja argumentos de línea de comandos"""
    import sys
    
    # Determinar rutas por defecto relativas a la ubicación del script
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent  # Asumiendo que src está dentro del proyecto
    
    default_songs = project_root / "musica" / "canciones"
    default_json = project_root / "musica" / "json"
    
    if len(sys.argv) >= 3:
        songs_dir = sys.argv[1]
        json_dir = sys.argv[2]
    else:
        print("Usando rutas por defecto:")
        print(f"  Canciones: {default_songs}")
        print(f"  JSON: {default_json}")
        print("(Para especificar otras rutas: python audio_analyzer.py <dir_canciones> <dir_json>)")
        songs_dir = default_songs
        json_dir = default_json
    
    analyzer = AudioAnalyzer()
    analyzer.batch_analyze(songs_dir, json_dir)
    
    print("\n✅ Análisis completado!")
    print("\n💡 Los campos 'intro_fin' y 'tiene_voz_inicio' son automáticos.")
    print("   Puedes corregirlos manualmente en cada JSON si la detección falla.")
    print("   Recuerda completar 'puede_empezar_mezcla' y 'debe_sonar_sola' según tu criterio.")


if __name__ == "__main__":
    main()