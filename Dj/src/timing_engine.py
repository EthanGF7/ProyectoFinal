"""
Timing Decision Engine v2 — Decide CUÁNDO y CÓMO mezclar exactamente
Mejoras:
  · Snap a barras de 4/8/16 beats (no solo al beat individual)
  · Niveles de urgencia: normal / urgente / crítico con cf diferente
  · Análisis de energía local para elegir el mejor momento dentro la ventana
  · Detección de frases vocales activas en el punto de salida
  · mix_preview(): descripción legible del plan de mezcla
"""
import numpy as np
from typing import Dict, Optional, Tuple


class TimingDecisionEngine:

    def __init__(self, default_mix_duration: float = 8.0):
        """
        default_mix_duration: duración base del crossfade en segundos.
        """
        self.default_mix_duration = default_mix_duration

    # ── API principal ─────────────────────────────────────────────────────────

    def find_mix_point(
        self,
        current_song: Dict,
        next_song: Dict,
        current_time: float,
    ) -> Optional[Dict]:
        """
        Calcula el plan de mezcla óptimo.
        Retorna un dict con el timing o None si no es posible aún.
        """
        max_exit = current_song.get("puede_salir")
        if not max_exit:
            max_exit = current_song.get("duracion_segundos", current_time + 180) * 0.90

        urgency = self._urgency_level(current_time, float(max_exit))

        if urgency == "critical":
            return self._emergency_mix(current_time, next_song, max_exit)

        puede_empezar = next_song.get("puede_empezar_mezcla")
        debe_sonar    = next_song.get("debe_sonar_sola")

        if puede_empezar is not None and debe_sonar is not None:
            return self._windowed_mix(
                current_song, next_song, current_time,
                float(puede_empezar), float(debe_sonar), urgency,
            )

        return self._standard_mix(current_song, next_song, current_time, urgency)

    def should_start_mixing_now(
        self,
        current_song: Dict,
        current_time: float,
        next_song_ready: bool,
        mix_duration_estimate: float = 8.0,
    ) -> Tuple[bool, str]:
        """
        Decide si hay que empezar el crossfade AHORA.
        Considera el tiempo hasta el punto de salida y si hay frases vocales.
        """
        if not next_song_ready:
            return False, "Siguiente canción no preparada"

        max_exit = current_song.get("puede_salir")
        if not max_exit:
            return False, "Sin punto de salida definido"

        time_until_exit = float(max_exit) - current_time

        # Urgencias
        if time_until_exit <= 0:
            return True, "⚠ Ya pasamos el punto de salida — mix inmediato"
        if time_until_exit <= mix_duration_estimate * 0.5:
            return True, f"🔴 Solo {time_until_exit:.1f}s hasta salida obligatoria"
        if time_until_exit <= mix_duration_estimate:
            # Verificar si estamos en mitad de una frase vocal
            if self._in_vocal_phrase(current_song, current_time):
                return False, "Frase vocal activa — esperar fin de frase"
            return True, f"Cerca del punto de salida ({time_until_exit:.1f}s)"

        return False, f"{time_until_exit:.1f}s hasta punto de salida"

    def mix_preview(self, plan: Dict) -> str:
        """
        Genera una descripción legible del plan de mezcla.
        Útil para logging y debugging.
        """
        if not plan:
            return "Sin plan de mezcla"
        lines = [
            f"🎚️  Plan de mezcla ({plan.get('urgency', 'normal')})",
            f"   Canción actual: fade-out en {plan['start_current_time']:.1f}s",
            f"   Siguiente entra: desde {plan['start_next_time']:.1f}s",
            f"   Duración crossfade: {plan['mix_duration']:.1f}s",
            f"   Tipo: {plan['fade_type']}",
            f"   Razón: {plan['reason']}",
        ]
        if plan.get("snap_bars"):
            lines.append(f"   Snap a: {plan['snap_bars']} compases")
        if plan.get("has_vocal_warning"):
            lines.append("   ⚠ Puede haber voz durante el crossfade")
        return "\n".join(lines)

    # ── Helpers de mezcla ─────────────────────────────────────────────────────

    def _urgency_level(self, current_time: float, max_exit: float) -> str:
        """
        Clasifica la urgencia del mix según tiempo restante.
          critical: ya pasamos o < 4s → mezcla de emergencia
          high:     < default_mix_duration/2 → mezcla rápida
          normal:   tiempo suficiente
        """
        remaining = max_exit - current_time
        if remaining <= 4.0:
            return "critical"
        if remaining <= self.default_mix_duration * 0.75:
            return "high"
        return "normal"

    def _emergency_mix(
        self, current_time: float, next_song: Dict, max_exit: float
    ) -> Dict:
        """Mezcla de emergencia: crossfade mínimo, salir ya."""
        duration = min(4.0, self.default_mix_duration)
        enter_at = next_song.get("puede_empezar_mezcla", 0) or 0
        return {
            "start_current_time": current_time,
            "start_next_time":    float(enter_at),
            "mix_duration":       duration,
            "fade_type":          "cut",
            "urgency":            "critical",
            "reason":             "Salida obligatoria superada — mezcla de emergencia",
            "snap_bars":          None,
            "has_vocal_warning":  False,
        }

    def _windowed_mix(
        self,
        current_song: Dict,
        next_song: Dict,
        current_time: float,
        puede_empezar: float,
        debe_sonar: float,
        urgency: str,
    ) -> Optional[Dict]:
        """
        Mezcla dentro de una ventana explícita del JSON.
        Busca el punto de menor varianza de energía dentro de la ventana
        (el momento más estable = mejor para mezclar).
        """
        window_dur = debe_sonar - puede_empezar
        if window_dur <= 0:
            return None

        # Mejor punto de salida dentro de la ventana
        mix_start = self._best_exit_in_window(
            current_song, puede_empezar, debe_sonar
        )

        # Advertencia de voz
        has_vocal = self._in_vocal_phrase(current_song, mix_start)

        duration = self._optimal_duration(
            current_song, next_song, window_dur, urgency
        )

        fade_type = "quick" if urgency == "high" else "smooth"

        return {
            "start_current_time": round(mix_start, 2),
            "start_next_time":    float(puede_empezar),
            "mix_duration":       round(duration, 2),
            "fade_type":          fade_type,
            "urgency":            urgency,
            "reason":             (
                f"Ventana óptima ({puede_empezar:.1f}s–{debe_sonar:.1f}s)"
            ),
            "window_start":       puede_empezar,
            "window_end":         debe_sonar,
            "snap_bars":          None,
            "has_vocal_warning":  has_vocal,
        }

    def _standard_mix(
        self,
        current_song: Dict,
        next_song: Dict,
        current_time: float,
        urgency: str,
    ) -> Dict:
        """
        Mezcla estándar sin ventana definida.
        Snappea al próximo bar de 4/8/16 beats en la canción actual.
        """
        bpm1 = current_song.get("bpm") or 120.0
        bpm2 = next_song.get("bpm") or bpm1

        # Elegir número de barras según urgencia
        bars = 1 if urgency == "high" else 2

        mix_start = self._next_bar(
            current_song.get("beat_times", []),
            current_time, bpm1, bars=bars,
        )

        enter_at = self._choose_enter_point(next_song)
        duration = self._optimal_duration(
            current_song, next_song,
            window_dur=self.default_mix_duration * 2,
            urgency=urgency,
        )
        has_vocal = self._in_vocal_phrase(current_song, mix_start)

        return {
            "start_current_time": round(mix_start, 2),
            "start_next_time":    round(enter_at, 2),
            "mix_duration":       round(duration, 2),
            "fade_type":          "quick" if urgency == "high" else "smooth",
            "urgency":            urgency,
            "reason":             f"Mix estándar — siguiente bar ({bars} compases)",
            "snap_bars":          bars,
            "has_vocal_warning":  has_vocal,
        }

    # ── Utilidades internas ───────────────────────────────────────────────────

    def _next_bar(
        self,
        beat_times: list,
        current_time: float,
        bpm: float,
        bars: int = 2,
    ) -> float:
        """
        Encuentra el próximo inicio de compás (bars × 4 beats) después de current_time.
        Si no hay beat_times, calcula a partir del BPM.
        """
        beat_dur = 60.0 / max(bpm, 1.0)
        bar_dur  = beat_dur * 4 * bars

        if beat_times:
            bt = np.array(beat_times)
            future = bt[bt > current_time + 0.5]  # al menos 0.5s en el futuro
            if len(future) > 0:
                # Encontrar el primer beat que es inicio de compás (múltiplo de 4*bars)
                for t in future:
                    beat_idx = np.searchsorted(bt, t)
                    if beat_idx % (4 * bars) == 0:
                        return float(t)
                # Fallback: primer beat futuro
                return float(future[0])

        # Sin beats: calcular siguiente bar a partir del BPM
        elapsed_bars = (current_time + 0.5) / bar_dur
        next_bar_n   = int(elapsed_bars) + 1
        return round(next_bar_n * bar_dur, 2)

    def _best_exit_in_window(
        self,
        song: Dict,
        window_start: float,
        window_end: float,
    ) -> float:
        """
        Dentro de una ventana, elige el segundo con menor varianza
        de energía en ±2s (el momento más tranquilo = mejor para mezclar).
        """
        ep  = song.get("energia_por_segundo", [])
        bts = np.array(song.get("beat_times", []))

        if not ep:
            # Sin perfil de energía: usar centro de la ventana
            center = (window_start + window_end) / 2
            if len(bts) > 0:
                future = bts[(bts >= window_start) & (bts <= window_end)]
                if len(future) > 0:
                    mid = (window_start + window_end) / 2
                    return float(bts[np.argmin(np.abs(future - mid))])
            return round(center, 2)

        # Buscar segundo con menor varianza local
        best_t   = (window_start + window_end) / 2
        best_var = np.inf

        start_i = int(window_start)
        end_i   = int(window_end)

        for i in range(start_i, min(end_i, len(ep))):
            w   = ep[max(0, i - 2): min(len(ep), i + 3)]
            var = float(np.std(w)) if len(w) > 1 else 0.0
            if var < best_var:
                best_var = var
                best_t   = float(i)

        # Snap al beat más cercano
        if len(bts) > 0:
            candidates = bts[(bts >= window_start) & (bts <= window_end)]
            if len(candidates) > 0:
                best_t = float(candidates[np.argmin(np.abs(candidates - best_t))])

        return round(best_t, 2)

    def _choose_enter_point(self, next_song: Dict) -> float:
        """
        Punto de entrada de la canción siguiente:
          1. puede_empezar_mezcla manual
          2. intro_fin (saltar la intro)
          3. 0 (desde el principio)
        """
        pem       = next_song.get("puede_empezar_mezcla")
        intro_fin = next_song.get("intro_fin")
        tiene_voz = next_song.get("tiene_voz_inicio", False)

        if pem is not None:
            return float(pem)

        if intro_fin and float(intro_fin) >= 3.0:
            bpm2 = next_song.get("bpm") or 0
            if bpm2 > 0:
                beat_dur = 60.0 / bpm2
                return max(0.0, float(intro_fin) - beat_dur * 4)
            return max(0.0, float(intro_fin) - 4.0)

        if tiene_voz:
            return 4.0

        return 0.0

    def _optimal_duration(
        self,
        current_song: Dict,
        next_song: Dict,
        window_dur: float,
        urgency: str,
    ) -> float:
        """
        Duración del crossfade ajustada a BPM, diferencia de energía y urgencia.
        """
        if urgency == "critical":
            return min(4.0, self.default_mix_duration)
        if urgency == "high":
            duration = self.default_mix_duration * 0.75
        else:
            duration = self.default_mix_duration

        bpm1 = current_song.get("bpm") or 120.0
        bpm2 = next_song.get("bpm") or bpm1
        bpm_avg = (bpm1 + bpm2) / 2

        # BPM alto → mezclas más cortas (más beats por segundo)
        if bpm_avg > 150:
            duration = min(duration, 6.0)
        elif bpm_avg > 130:
            duration = min(duration, 8.0)
        elif bpm_avg < 100:
            duration = max(duration, 10.0)

        # Diferencia grande de energía → más larga para suavizar
        diff = abs(
            (current_song.get("energia") or 50) -
            (next_song.get("energia") or 50)
        )
        if diff > 20:
            duration += 2.0

        # No exceder la ventana disponible
        max_duration = min(window_dur * 0.80, 20.0)
        return max(2.0, min(duration, max_duration))

    def _in_vocal_phrase(self, song: Dict, time_point: float) -> bool:
        """
        Comprueba si el tiempo dado cae dentro de una frase vocal.
        Útil para evitar cortar la voz en el punto de salida.
        """
        phrases = song.get("vocal_phrases", [])
        if not phrases:
            return False
        for start, end in phrases:
            if start <= time_point <= end:
                return True
        return False


# ── Test ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = TimingDecisionEngine()

    current = {
        "bpm": 128.0, "energia": 75.0,
        "puede_salir": 180.0,
        "beat_times": [0, 0.47, 0.94, 1.41, 1.88, 2.35, 2.82, 3.29,
                        3.76, 4.23, 4.70, 5.17, 5.64, 6.11, 6.58, 7.05],
        "vocal_phrases": [[60.0, 75.0], [120.0, 135.0]],
        "energia_por_segundo": [70, 72, 74, 76, 75, 73, 71, 70] * 30,
    }
    nxt = {
        "bpm": 130.0, "energia": 80.0,
        "puede_empezar_mezcla": 16.0, "debe_sonar_sola": 32.0,
        "intro_fin": 12.0, "tiene_voz_inicio": False,
    }

    for t, label in [(170.0, "Normal"), (177.0, "High urgency"), (182.0, "Critical")]:
        print(f"\n{'='*50}")
        print(f"Tiempo actual: {t}s — {label}")
        plan = engine.find_mix_point(current, nxt, t)
        print(engine.mix_preview(plan))

        should, reason = engine.should_start_mixing_now(current, t, True)
        print(f"¿Mezclar ahora? {should} — {reason}")