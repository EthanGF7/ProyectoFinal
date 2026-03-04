"""
Compatibility Engine v2 — Evalúa si dos canciones pueden mezclarse
Mejoras:
  · Soporte de tonalidad (rueda de Camelot) integrado en el score
  · Compatibilidad de tempo por ratios (0.5×, 2×, 1.5×, 0.75×)
  · Score de energía direccional: subidas penalizan menos que bajadas bruscas
  · Confidence de BPM y key usadas para ponderar el score
  · Nuevo método: rank_candidates() para elegir entre múltiples opciones
"""
import numpy as np
from typing import Dict, List, Optional, Tuple


# ── Rueda de Camelot ─────────────────────────────────────────────────────────
CAMELOT: Dict[str, str] = {
    # Mayor (A = inner ring)
    "Ab": "1A", "Eb": "2A", "Bb": "3A", "F": "4A", "C": "5A",
    "G":  "6A", "D":  "7A", "A":  "8A", "E": "9A", "B": "10A",
    "F#": "11A", "Db": "12A",
    # Menor (B = outer ring)
    "Abm": "1B", "Ebm": "2B", "Bbm": "3B", "Fm": "4B", "Cm": "5B",
    "Gm":  "6B", "Dm":  "7B", "Am":  "8B", "Em": "9B", "Bm": "10B",
    "F#m": "11B", "C#m": "12B",
    # Aliases enarmónicos
    "G#": "1A", "D#": "2A", "A#": "3A", "C#": "12A", "Gb": "11A",
    "G#m": "1B", "D#m": "2B", "A#m": "3B", "Gbm": "11B",
}


def _camelot_pos(key_str: str) -> Optional[Tuple[int, str]]:
    """Convierte key → (número, letra) de Camelot. None si no reconocida."""
    if not key_str:
        return None
    c = CAMELOT.get(key_str.strip())
    if not c:
        return None
    return int(c[:-1]), c[-1]


def camelot_compatibility(k1: str, k2: str) -> Tuple[int, str]:
    """
    Devuelve (bonus_pts, descripción) según la rueda de Camelot.
    Escala: 0-15 puntos.
    """
    p1, p2 = _camelot_pos(k1), _camelot_pos(k2)
    if p1 is None or p2 is None:
        return 5, "key desconocida (neutro)"

    n1, l1 = p1
    n2, l2 = p2

    if n1 == n2 and l1 == l2:
        return 15, "misma tonalidad (perfecto)"

    diff = abs(n1 - n2)
    circ = min(diff, 12 - diff)  # distancia circular en el reloj de 12h

    if n1 == n2 and l1 != l2:
        return 10, "relativo mayor/menor"
    if l1 == l2 and circ == 1:
        return 12, "adyacente en el círculo"
    if l1 == l2 and circ == 2:
        return 6, "2 pasos (funciona)"
    if l1 != l2 and circ <= 1:
        return 7, "cambio de modo + adyacente"
    if l1 == l2 and circ == 3:
        return 3, "3 pasos (arriesgado)"

    return 0, "tonalidades incompatibles"


class CompatibilityEngine:
    """
    Evalúa y puntúa la compatibilidad entre canciones.
    Devuelve booleano (compatible/no) y score continuo 0-100.
    """

    def __init__(
        self,
        max_bpm_diff: float = 8.0,
        max_energy_diff: float = 30.0,
        min_energy_stability: float = 10.0,
    ):
        self.max_bpm_diff        = max_bpm_diff
        self.max_energy_diff     = max_energy_diff
        self.min_energy_stability = min_energy_stability

    # ── API principal ─────────────────────────────────────────────────────────

    def are_compatible(
        self,
        current_song: Dict,
        next_song: Dict,
        current_time: float,
    ) -> Tuple[bool, str]:
        """
        Evaluación binaria de compatibilidad.
        Retorna (compatible, razón).
        """
        ok, reason = self._check_bpm(current_song["bpm"], next_song["bpm"])
        if not ok:
            return False, reason

        ok, reason = self._check_energy(current_song["energia"], next_song["energia"])
        if not ok:
            return False, reason

        ok, reason = self._check_stability(current_song, current_time)
        if not ok:
            return False, reason

        return True, "Canciones compatibles"

    def compatibility_score(
        self,
        current_song: Dict,
        next_song: Dict,
        current_time: float,
    ) -> float:
        """
        Score continuo 0-100. Combina:
          · Cercanía de BPM (0-30)
          · Compatibilidad de energía con dirección (0-25)
          · Rueda de Camelot — tonalidad (0-15)
          · Estabilidad del momento de salida (0-15)
          · Calidad de metadata de la entrante (0-15)
        """
        score = 0.0

        # 1. BPM (0-30)
        score += self._score_bpm(current_song["bpm"], next_song["bpm"])

        # 2. Energía con dirección (0-25)
        score += self._score_energy(current_song["energia"], next_song["energia"])

        # 3. Tonalidad / Camelot (0-15), ponderado por confidence
        k1 = current_song.get("key", "")
        k2 = next_song.get("key", "")
        key_pts, _ = camelot_compatibility(k1, k2)
        # Ponderar por key_confidence si existe (si baja, penalizar menos)
        kc1 = current_song.get("key_confidence", 1.0) or 1.0
        kc2 = next_song.get("key_confidence", 1.0) or 1.0
        key_weight = (kc1 + kc2) / 2
        score += key_pts * key_weight

        # 4. Estabilidad del momento (0-15)
        score += self._score_stability(current_song, current_time)

        # 5. Calidad de metadata de la entrante (0-15)
        score += self._score_metadata_quality(next_song)

        return round(max(0.0, min(100.0, score)), 2)

    def rank_candidates(
        self,
        current_song: Dict,
        candidates: List[Dict],
        current_time: float,
        top_n: int = 5,
    ) -> List[Tuple[Dict, float, str]]:
        """
        Clasifica una lista de candidatas de mayor a menor compatibilidad.
        Retorna [(track, score, reason), ...].
        Filtra incompatibles (score < 20) si hay candidatas compatibles.
        """
        results = []
        for c in candidates:
            ok, reason = self.are_compatible(current_song, c, current_time)
            if not ok:
                continue
            s = self.compatibility_score(current_song, c, current_time)
            _, key_reason = camelot_compatibility(
                current_song.get("key", ""), c.get("key", "")
            )
            full_reason = f"{reason} | {key_reason}"
            results.append((c, s, full_reason))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]

    # ── Comprobaciones binarias ───────────────────────────────────────────────

    def _check_bpm(self, bpm1: float, bpm2: float) -> Tuple[bool, str]:
        if not bpm1 or not bpm2:
            return True, "BPM desconocido (asumido compatible)"

        diff = abs(bpm1 - bpm2)
        if diff <= self.max_bpm_diff:
            return True, f"BPMs compatibles (Δ{diff:.1f})"

        # Ratios musicales: ×2, ×0.5, ×1.5, ×0.75
        for ratio in (2.0, 0.5, 1.5, 0.75):
            if abs(bpm1 * ratio - bpm2) <= self.max_bpm_diff:
                return True, f"BPMs compatibles (ratio {ratio}×)"

        return False, f"Diferencia de BPM muy grande (Δ{diff:.1f})"

    def _check_energy(self, e1: float, e2: float) -> Tuple[bool, str]:
        diff = abs(e1 - e2)
        if diff <= self.max_energy_diff:
            direction = "↑" if e2 > e1 else ("↓" if e2 < e1 else "→")
            return True, f"Energía compatible {direction} (Δ{diff:.1f})"
        return False, f"Salto de energía muy brusco (Δ{diff:.1f})"

    def _check_stability(
        self, song: Dict, current_time: float
    ) -> Tuple[bool, str]:
        ep = song.get("energia_por_segundo", [])
        if not ep:
            return True, "Sin datos de estabilidad (asumido estable)"

        idx = int(current_time)
        if idx >= len(ep):
            return True, "Final de canción (asumido estable)"

        window = ep[max(0, idx - 2): min(len(ep), idx + 3)]
        if len(window) > 1:
            var = float(np.std(window))
            if var > self.min_energy_stability * 2:
                return False, f"Momento muy inestable (σ={var:.1f})"

        return True, "Momento estable"

    # ── Sub-scores continuos ──────────────────────────────────────────────────

    def _score_bpm(self, bpm1: float, bpm2: float) -> float:
        """0-30 puntos según cercanía de BPM."""
        if not bpm1 or not bpm2:
            return 10.0  # neutro

        diff = abs(bpm1 - bpm2)

        # Diferencia directa
        if diff <= 3:
            return 30.0
        if diff <= self.max_bpm_diff:
            return max(0.0, 30.0 - diff * 3.0)

        # Ratios
        best_ratio_diff = min(
            abs(bpm1 * r - bpm2)
            for r in (2.0, 0.5, 1.5, 0.75)
        )
        if best_ratio_diff <= self.max_bpm_diff:
            return max(0.0, 20.0 - best_ratio_diff * 2.5)

        return max(0.0, 5.0 - (diff - self.max_bpm_diff) * 0.3)

    def _score_energy(self, e_cur: float, e_nxt: float) -> float:
        """
        0-25 puntos.
        Subidas suaves de energía son más valoradas que bajadas.
        Penalización asimétrica: bajar mucho de golpe es peor que subir.
        """
        diff = e_nxt - e_cur  # positivo = sube, negativo = baja

        if abs(diff) <= 8:
            return 25.0  # transición muy suave

        if diff > 0:
            # Subida: hasta +25 puntos, se va reduciendo
            return max(0.0, 25.0 - diff * 0.6)
        else:
            # Bajada: penalización más agresiva
            return max(0.0, 20.0 - abs(diff) * 0.8)

    def _score_stability(self, song: Dict, current_time: float) -> float:
        """0-15 puntos según varianza de energía en el punto de salida."""
        ep = song.get("energia_por_segundo", [])
        if not ep:
            return 7.5  # neutro

        idx    = int(current_time)
        window = ep[max(0, idx - 2): min(len(ep), idx + 3)]
        if len(window) < 2:
            return 10.0

        var = float(np.std(window))
        return max(0.0, 15.0 - var * 0.5)

    def _score_metadata_quality(self, song: Dict) -> float:
        """
        0-15 puntos según riqueza de los datos de análisis de la entrante.
        Más datos → mejores decisiones de mezcla → bonus.
        """
        pts = 0.0
        if song.get("beat_times"):      pts += 4.0
        if song.get("puede_salir"):     pts += 2.0
        if song.get("structure_points"): pts += 5.0
        if song.get("has_stems"):       pts += 3.0
        if song.get("key"):             pts += 1.0
        return min(pts, 15.0)


# ── Test ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = CompatibilityEngine()

    song1 = {
        "bpm": 128.0, "energia": 75.0, "key": "Am",
        "key_confidence": 0.88,
        "energia_por_segundo": [70, 72, 75, 76, 78, 75, 73],
    }
    song2 = {
        "bpm": 130.0, "energia": 80.0, "key": "Em",
        "key_confidence": 0.80,
        "beat_times": [0, 0.46, 0.92], "structure_points": [32.0, 64.0],
    }
    song3 = {
        "bpm": 100.0, "energia": 40.0, "key": "F#",
        "key_confidence": 0.55,
    }

    for candidate, name in [(song2, "song2"), (song3, "song3")]:
        ok, reason = engine.are_compatible(song1, candidate, 5.0)
        score = engine.compatibility_score(song1, candidate, 5.0)
        key_bonus, key_reason = camelot_compatibility(
            song1.get("key", ""), candidate.get("key", "")
        )
        print(f"\n{name}:")
        print(f"  Compatible: {ok} — {reason}")
        print(f"  Score: {score:.1f}/100")
        print(f"  Camelot: +{key_bonus} pts — {key_reason}")