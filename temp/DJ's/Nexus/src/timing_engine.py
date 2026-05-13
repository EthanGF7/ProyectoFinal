"""
Timing Decision Engine - Decide CUÁNDO y CÓMO mezclar exactamente
"""
import numpy as np
from typing import Dict, Optional, Tuple


class TimingDecisionEngine:
    """
    Decide el momento exacto y la duración de la mezcla
    Respeta las ventanas definidas en el JSON
    """
    
    def __init__(self, default_mix_duration: float = 8.0):
        """
        Args:
            default_mix_duration: Duración por defecto de mezcla en segundos
        """
        self.default_mix_duration = default_mix_duration
    
    def find_mix_point(self, 
                      current_song: Dict,
                      next_song: Dict,
                      current_time: float) -> Optional[Dict]:
        """
        Encuentra el momento exacto para empezar la mezcla
        
        Args:
            current_song: Metadata de canción actual
            next_song: Metadata de canción siguiente
            current_time: Tiempo actual de reproducción
            
        Returns:
            Dict con timing de mezcla o None si no es posible aún
        """
        # Verificar si ya pasamos el punto de salida obligatorio
        max_exit = current_song.get('puede_salir')
        if max_exit is not None and isinstance(max_exit, (int, float)) and current_time >= max_exit:
            # Mezcla urgente, tenemos que salir YA
            return self._create_urgent_mix(current_time, next_song)
        
        # Verificar si la siguiente canción tiene ventana definida
        puede_empezar = next_song.get('puede_empezar_mezcla')
        debe_sonar_sola = next_song.get('debe_sonar_sola')
        
        if puede_empezar is not None and debe_sonar_sola is not None:
            # Canción con ventana específica - buscar mejor momento
            return self._find_optimal_in_window(
                current_song,
                next_song,
                current_time,
                puede_empezar,
                debe_sonar_sola
            )
        else:
            # Canción sin ventana - comportamiento simple
            return self._find_standard_mix_point(
                current_song,
                next_song,
                current_time
            )
    
    def _create_urgent_mix(self, current_time: float, next_song: Dict) -> Dict:
        """
        Crea una mezcla rápida cuando ya pasamos el punto de salida
        """
        # Mezcla más corta para salir rápido
        mix_duration = min(4.0, self.default_mix_duration)
        
        return {
            'start_current_time': current_time,
            'start_next_time': next_song.get('puede_empezar_mezcla', 0),
            'mix_duration': mix_duration,
            'fade_type': 'quick',  # Crossfade rápido
            'reason': 'Salida obligatoria alcanzada'
        }
    
    def _find_optimal_in_window(self,
                                current_song: Dict,
                                next_song: Dict,
                                current_time: float,
                                puede_empezar: float,
                                debe_sonar_sola: float) -> Optional[Dict]:
        """
        Busca el mejor momento dentro de la ventana definida
        """
        # Calcular ventana disponible
        window_duration = debe_sonar_sola - puede_empezar
        
        if window_duration <= 0:
            print("⚠️ Ventana inválida en metadata")
            return None
        
        # Analizar beats de la canción actual
        beat_times = np.array(current_song.get('beat_times', []))
        
        if len(beat_times) == 0:
            # Sin beats detectados, usar ventana completa
            mix_start = puede_empezar + (window_duration * 0.5)
        else:
            # Encontrar el beat más cercano al centro de la ventana
            window_center = puede_empezar + (window_duration * 0.5)
            closest_beat_idx = np.argmin(np.abs(beat_times - window_center))
            mix_start = beat_times[closest_beat_idx]
            
            # Asegurar que está dentro de la ventana
            mix_start = max(puede_empezar, min(debe_sonar_sola - 1, mix_start))
        
        # Calcular duración de mezcla
        mix_duration = self._calculate_optimal_mix_duration(
            current_song,
            next_song,
            mix_start,
            window_duration
        )
        
        return {
            'start_current_time': current_time,
            'start_next_time': mix_start,
            'mix_duration': mix_duration,
            'fade_type': 'smooth',  # Crossfade suave
            'reason': f'Ventana óptima ({puede_empezar:.1f}s - {debe_sonar_sola:.1f}s)',
            'window_start': puede_empezar,
            'window_end': debe_sonar_sola
        }
    
    def _find_standard_mix_point(self,
                                 current_song: Dict,
                                 next_song: Dict,
                                 current_time: float) -> Dict:
        """
        Encuentra punto de mezcla para canciones sin ventana definida
        """
        # Buscar el siguiente beat fuerte para empezar mezcla
        beat_times = np.array(current_song.get('beat_times', []))
        
        if len(beat_times) > 0:
            # Encontrar beats después del tiempo actual
            future_beats = beat_times[beat_times > current_time]
            
            if len(future_beats) > 0:
                # Usar el siguiente beat (o el segundo siguiente para más margen)
                beats_ahead = min(2, len(future_beats))
                mix_start_current = future_beats[beats_ahead - 1]
            else:
                mix_start_current = current_time + 2.0
        else:
            # Sin beats, simplemente esperar 2 segundos
            mix_start_current = current_time + 2.0
        
        return {
            'start_current_time': mix_start_current,
            'start_next_time': 0,  # Empezar desde el inicio
            'mix_duration': self.default_mix_duration,
            'fade_type': 'smooth',
            'reason': 'Mezcla estándar en siguiente beat'
        }
    
    def _calculate_optimal_mix_duration(self,
                                       current_song: Dict,
                                       next_song: Dict,
                                       mix_start: float,
                                       window_duration: float) -> float:
        """
        Calcula la duración óptima de mezcla
        """
        # Duración base
        duration = self.default_mix_duration
        
        # Ajustar según BPM
        bpm_avg = (current_song['bpm'] + next_song['bpm']) / 2
        
        # A mayor BPM, mezclas más cortas (más beats por segundo)
        if bpm_avg > 140:
            duration = 6.0
        elif bpm_avg < 100:
            duration = 10.0
        
        # Ajustar según diferencia de energía
        energy_diff = abs(current_song['energia'] - next_song['energia'])
        if energy_diff > 20:
            # Gran diferencia de energía = mezcla más larga para suavizar
            duration += 2.0
        
        # No exceder la ventana disponible
        max_duration = min(window_duration * 0.8, 16.0)
        duration = min(duration, max_duration)
        
        return duration
    
    def should_start_mixing_now(self,
                                current_song: Dict,
                                current_time: float,
                                next_song_ready: bool) -> Tuple[bool, str]:
        """
        Decide si es el momento de empezar a mezclar AHORA
        
        Returns:
            (should_mix: bool, reason: str)
        """
        if not next_song_ready:
            return False, "Siguiente canción no preparada"
        
        # Verificar punto de salida obligatorio
        max_exit = current_song.get('puede_salir')
        
        # Empezar mezcla antes del punto de salida
        # (para que termine justo en el punto de salida)
        time_until_exit = max_exit - current_time
        
        if time_until_exit <= self.default_mix_duration:
            return True, f"Cerca del punto de salida ({time_until_exit:.1f}s restantes)"
        
        # Si aún hay tiempo, esperar
        return False, f"Aún hay {time_until_exit:.1f}s hasta punto de salida"


# Test
if __name__ == "__main__":
    engine = TimingDecisionEngine()
    
    current = {
        "bpm": 128.0,
        "energia": 75.0,
        "puede_salir": 180.0,
        "beat_times": [0, 0.47, 0.94, 1.41, 1.88, 2.35]
    }
    
    next_song = {
        "bpm": 130.0,
        "energia": 80.0,
        "puede_empezar_mezcla": 16.0,
        "debe_sonar_sola": 32.0
    }
    
    # Simular a 170 segundos de la canción actual
    result = engine.find_mix_point(current, next_song, 170.0)
    
    if result:
        print("🎚️ Plan de mezcla:")
        print(f"  Empezar en: {result['start_current_time']:.1f}s (canción actual)")
        print(f"  Desde: {result['start_next_time']:.1f}s (siguiente canción)")
        print(f"  Duración: {result['mix_duration']:.1f}s")
        print(f"  Tipo: {result['fade_type']}")
        print(f"  Razón: {result['reason']}")
