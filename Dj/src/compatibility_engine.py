"""
Compatibility Engine - Evalúa si dos canciones pueden mezclarse
"""
import numpy as np
from typing import Dict, Tuple, Optional


class CompatibilityEngine:
    """Decide si dos canciones son compatibles para mezclar"""
    
    def __init__(self, 
                 max_bpm_diff: float = 8.0,
                 max_energy_diff: float = 30.0,
                 min_energy_stability: float = 10.0):
        """
        Args:
            max_bpm_diff: Diferencia máxima de BPM permitida (default: 8)
            max_energy_diff: Diferencia máxima de energía permitida (default: 30)
            min_energy_stability: Variación mínima de energía para considerar estable (default: 10)
        """
        self.max_bpm_diff = max_bpm_diff
        self.max_energy_diff = max_energy_diff
        self.min_energy_stability = min_energy_stability
    
    def are_compatible(self, 
                      current_song: Dict, 
                      next_song: Dict,
                      current_time: float) -> Tuple[bool, str]:
        """
        Evalúa si dos canciones son compatibles en un momento dado
        
        Args:
            current_song: Metadata de la canción actual
            next_song: Metadata de la canción siguiente
            current_time: Segundo actual de la canción en curso
            
        Returns:
            (compatible: bool, razón: str)
        """
        # 1. Verificar diferencia de BPM
        bpm_compatible, bpm_reason = self._check_bpm_compatibility(
            current_song['bpm'], 
            next_song['bpm']
        )
        if not bpm_compatible:
            return False, bpm_reason
        
        # 2. Verificar diferencia de energía
        energy_compatible, energy_reason = self._check_energy_compatibility(
            current_song['energia'], 
            next_song['energia']
        )
        if not energy_compatible:
            return False, energy_reason
        
        # 3. Verificar estabilidad del momento actual
        stable, stability_reason = self._check_moment_stability(
            current_song, 
            current_time
        )
        if not stable:
            return False, stability_reason
        
        return True, "Canciones compatibles"
    
    def _check_bpm_compatibility(self, current_bpm: float, next_bpm: float) -> Tuple[bool, str]:
        """
        Verifica si los BPMs son compatibles
        Permite diferencias razonables que un DJ puede cuadrar
        """
        diff = abs(current_bpm - next_bpm)
        
        # Permitir BPMs que sean múltiplos cercanos (doble tempo, mitad)
        if self._are_bpm_multiples(current_bpm, next_bpm):
            return True, "BPMs compatibles (múltiplos)"
        
        if diff <= self.max_bpm_diff:
            return True, f"BPMs compatibles (diff: {diff:.1f})"
        
        return False, f"Diferencia de BPM muy grande ({diff:.1f})"
    
    def _are_bpm_multiples(self, bpm1: float, bpm2: float, tolerance: float = 5.0) -> bool:
        """
        Verifica si dos BPMs son múltiplos cercanos
        Por ejemplo: 130 BPM y 65 BPM (doble/mitad)
        """
        ratios = [0.5, 2.0]  # mitad y doble
        
        for ratio in ratios:
            expected = bpm1 * ratio
            if abs(expected - bpm2) <= tolerance:
                return True
        
        return False
    
    def _check_energy_compatibility(self, current_energy: float, next_energy: float) -> Tuple[bool, str]:
        """
        Verifica si las energías son compatibles
        Permite transiciones naturales (gradual up/down)
        """
        diff = abs(current_energy - next_energy)
        
        if diff <= self.max_energy_diff:
            if next_energy > current_energy:
                return True, f"Subida gradual de energía (+{diff:.1f})"
            elif next_energy < current_energy:
                return True, f"Bajada gradual de energía (-{diff:.1f})"
            else:
                return True, "Energías similares"
        
        return False, f"Salto de energía muy brusco ({diff:.1f})"
    
    def _check_moment_stability(self, song: Dict, current_time: float) -> Tuple[bool, str]:
        """
        Verifica si el momento actual de la canción es estable para mezclar
        Evita mezclar en momentos caóticos o con cambios bruscos
        """
        # Obtener perfil de energía
        energy_profile = song.get('energia_por_segundo', [])
        
        if not energy_profile:
            return True, "Sin datos de estabilidad (asumido estable)"
        
        # Encontrar el segundo correspondiente
        current_second = int(current_time)
        
        if current_second >= len(energy_profile):
            return True, "Final de canción (asumido estable)"
        
        # Analizar ventana de ±2 segundos
        window_start = max(0, current_second - 2)
        window_end = min(len(energy_profile), current_second + 3)
        window = energy_profile[window_start:window_end]
        
        # Calcular variación en la ventana
        if len(window) > 1:
            variation = np.std(window)
            
            if variation > self.min_energy_stability * 2:
                return False, f"Momento muy inestable (variación: {variation:.1f})"
        
        return True, "Momento estable para mezclar"
    
    def calculate_compatibility_score(self, 
                                     current_song: Dict, 
                                     next_song: Dict,
                                     current_time: float) -> float:
        """
        Calcula un score de compatibilidad (0-100)
        Útil para elegir entre varias canciones compatibles
        
        Returns:
            Score 0-100 (mayor = mejor compatibilidad)
        """
        score = 100.0
        
        # Penalizar por diferencia de BPM (0-30 puntos)
        bpm_diff = abs(current_song['bpm'] - next_song['bpm'])
        bpm_penalty = min(30, (bpm_diff / self.max_bpm_diff) * 30)
        score -= bpm_penalty
        
        # Penalizar por diferencia de energía (0-30 puntos)
        energy_diff = abs(current_song['energia'] - next_song['energia'])
        energy_penalty = min(30, (energy_diff / self.max_energy_diff) * 30)
        score -= energy_penalty
        
        # Bonificar estabilidad del momento (0-20 puntos)
        energy_profile = current_song.get('energia_por_segundo', [])
        if energy_profile:
            current_second = int(current_time)
            if current_second < len(energy_profile):
                window_start = max(0, current_second - 2)
                window_end = min(len(energy_profile), current_second + 3)
                window = energy_profile[window_start:window_end]
                
                if len(window) > 1:
                    stability = max(0, 20 - np.std(window))
                    score += stability
        
        # Bonificar transiciones naturales de energía (0-20 puntos)
        if next_song['energia'] > current_song['energia']:
            # Subida gradual de energía
            if energy_diff <= 15:
                score += 15
        elif next_song['energia'] == current_song['energia']:
            # Mantener energía
            score += 20
        else:
            # Bajada gradual
            if energy_diff <= 20:
                score += 10
        
        return max(0, min(100, score))


# Test
if __name__ == "__main__":
    # Ejemplo de uso
    engine = CompatibilityEngine()
    
    song1 = {
        "bpm": 128.0,
        "energia": 75.0,
        "energia_por_segundo": [70, 72, 75, 76, 78, 75, 73]
    }
    
    song2 = {
        "bpm": 130.0,
        "energia": 80.0,
        "energia_por_segundo": [78, 80, 82, 81, 79]
    }
    
    compatible, reason = engine.are_compatible(song1, song2, 5.0)
    score = engine.calculate_compatibility_score(song1, song2, 5.0)
    
    print(f"Compatible: {compatible}")
    print(f"Razón: {reason}")
    print(f"Score: {score:.1f}/100")
