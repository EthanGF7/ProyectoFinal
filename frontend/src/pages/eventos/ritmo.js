import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import BarraNavegacion from '../../components/BarraNavegacion';
import { callAuthedApi } from '../../utils/apiClient';

const GAME_DURATION = 45000;
const SONGS = [
  {
    title: 'Gasolina Mashup',
    artist: 'DJ Nexus',
    bpm: 96,
    firstBeat: 900,
    url: `/api/djs/nexus/audio?file=${encodeURIComponent('Eoo x Gasolina.wav')}`,
  },
  {
    title: 'Rehuso',
    artist: 'DJ Nexus',
    bpm: 104,
    firstBeat: 720,
    url: `/api/djs/nexus/audio?file=${encodeURIComponent('Rehuso.mp3')}`,
  },
  {
    title: 'Motinha',
    artist: 'DJ Nexus',
    bpm: 128,
    firstBeat: 520,
    url: `/api/djs/nexus/audio?file=${encodeURIComponent('MOTINHA.wav')}`,
  },
];
const DIFFICULTY_OPTIONS = {
  suave: { label: 'Suave', score: 1 },
  medio: { label: 'Medio', score: 1.35 },
  intenso: { label: 'Intenso', score: 1.75 },
};

function getNearestBeat(song, elapsed, calibration) {
  const beatMs = 60000 / song.bpm;
  const firstBeat = song.firstBeat + calibration;
  if (elapsed < firstBeat) return firstBeat;
  const beatIndex = Math.round((elapsed - firstBeat) / beatMs);
  return firstBeat + beatIndex * beatMs;
}

function getJudgement(delta) {
  const abs = Math.abs(delta);
  if (abs <= 90) return { label: 'Perfect', points: 1000, className: 'perfect' };
  if (abs <= 170) return { label: 'Good', points: 550, className: 'good' };
  if (abs <= 260) return { label: 'Late', points: 180, className: 'late' };
  return null;
}

export default function JuegoRitmoEvento() {
  const [selectedSongIndex, setSelectedSongIndex] = useState(0);
  const [difficulty, setDifficulty] = useState('medio');
  const [calibration, setCalibration] = useState(0);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [score, setScore] = useState(0);
  const [combo, setCombo] = useState(0);
  const [maxCombo, setMaxCombo] = useState(0);
  const [judgement, setJudgement] = useState('Pulsa cuando el aro esté verde');
  const [ranking, setRanking] = useState([]);
  const [rankingMessage, setRankingMessage] = useState('');
  const [saved, setSaved] = useState(false);
  const frameRef = useRef(null);
  const audioRef = useRef(null);
  const selectedSong = SONGS[selectedSongIndex];
  const bpm = selectedSong.bpm;
  const nearestBeat = getNearestBeat(selectedSong, elapsed, calibration);
  const beatDelta = Math.abs(elapsed - nearestBeat);
  const beatMs = 60000 / bpm;
  const beatProgress = running ? Math.min(1, beatDelta / (beatMs / 2)) : 1;
  const ringScale = 0.55 + beatProgress * 1.55;
  const onBeat = running && beatDelta < 140;

  const progress = Math.min((elapsed / GAME_DURATION) * 100, 100);

  const loadRanking = useCallback(async () => {
    try {
      const response = await fetch('/api/eventos/ritmo/ranking');
      const payload = await response.json();
      setRanking(payload.ranking || []);
      setRankingMessage(payload.setupRequired ? 'Falta crear la tabla rhythm_game_scores en Supabase.' : '');
    } catch {
      setRankingMessage('No se pudo cargar el ranking.');
    }
  }, []);

  const startGame = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.pause();
    audio.currentTime = 0;

    try {
      await audio.play();
    } catch {
      setJudgement('Activa el audio');
      return;
    }

    setScore(0);
    setCombo(0);
    setMaxCombo(0);
    setSaved(false);
    setJudgement('Espera al verde');
    setElapsed(0);
    setRunning(true);
  }, []);

  const saveScore = useCallback(async () => {
    if (saved || score <= 0) return;
    try {
      const payload = await callAuthedApi('/api/eventos/ritmo/ranking', {
        method: 'POST',
        body: {
          score,
          maxCombo,
          songTitle: selectedSong.title,
          difficulty,
        },
      });
      setRanking(payload.ranking || []);
      setRankingMessage('Puntuación guardada.');
      setSaved(true);
    } catch (err) {
      setRankingMessage(err.message || 'Inicia sesión para guardar tu puntuación.');
    }
  }, [difficulty, maxCombo, saved, score, selectedSong.title]);

  const stopGame = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setRunning(false);
    setJudgement('Evento terminado');
    if (frameRef.current) cancelAnimationFrame(frameRef.current);
  }, []);

  const hitBeat = useCallback(() => {
    if (!running) return;
    const result = getJudgement(elapsed - nearestBeat);
    if (!result) {
      setCombo(0);
      setJudgement('Miss');
      return;
    }
    setCombo((current) => {
      const next = current + 1;
      setMaxCombo((previous) => Math.max(previous, next));
      setScore((value) => value + Math.round((result.points + next * 12) * DIFFICULTY_OPTIONS[difficulty].score));
      return next;
    });
    setJudgement(result.label);
  }, [difficulty, elapsed, nearestBeat, running]);

  useEffect(() => {
    if (!running) return undefined;

    function tick() {
      const nextElapsed = audioRef.current ? audioRef.current.currentTime * 1000 : 0;
      setElapsed(nextElapsed);

      if (nextElapsed >= GAME_DURATION) {
        stopGame();
        return;
      }

      frameRef.current = requestAnimationFrame(tick);
    }

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [running, stopGame]);

  useEffect(() => {
    if (!running) return undefined;

    function onKeyDown(event) {
      if (event.code === 'Space') {
        event.preventDefault();
        hitBeat();
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [hitBeat, running]);

  useEffect(() => {
    loadRanking();
  }, [loadRanking]);

  return (
    <div className="page-container rhythm-page">
      <BarraNavegacion />
      <main className="neon-main rhythm-main">
        <section className="rhythm-hero">
          <div className="rhythm-orbit" aria-hidden="true"></div>
          <div className="rhythm-header">
            <span className="section-tag">Evento juego</span>
            <h1>Beat Battle</h1>
            <p>Juego simplificado: escucha la canción y pulsa el botón central cuando el aro se cierre y se ponga verde.</p>
          </div>

          <div className="rhythm-layout">
            <aside className="rhythm-panel">
              <div>
                <span className="rhythm-label">Canción</span>
                <div className="rhythm-song-list">
                  {SONGS.map((song, index) => (
                    <button
                      key={song.url}
                      type="button"
                      className={selectedSongIndex === index ? 'active' : ''}
                      onClick={() => {
                        setSelectedSongIndex(index);
                        setCalibration(0);
                      }}
                      disabled={running}
                    >
                      <strong>{song.title}</strong>
                      <span>{song.artist} · {song.bpm} BPM</span>
                    </button>
                  ))}
                </div>
              </div>

              <audio
                ref={audioRef}
                className="rhythm-audio"
                controls
                src={selectedSong.url}
                onEnded={stopGame}
              />

              <div>
                <span className="rhythm-label">Ajuste de ritmo</span>
                <div className="rhythm-calibration">
                  <button type="button" onClick={() => setCalibration((value) => value - 50)} disabled={running}>
                    -50 ms
                  </button>
                  <strong>{calibration > 0 ? `+${calibration}` : calibration} ms</strong>
                  <button type="button" onClick={() => setCalibration((value) => value + 50)} disabled={running}>
                    +50 ms
                  </button>
                </div>
              </div>

              <div>
                <span className="rhythm-label">Dificultad</span>
                <div className="rhythm-options rhythm-options-wide">
                  {Object.keys(DIFFICULTY_OPTIONS).map((option) => (
                    <button
                      key={option}
                      type="button"
                      className={difficulty === option ? 'active' : ''}
                      onClick={() => setDifficulty(option)}
                      disabled={running}
                    >
                      {DIFFICULTY_OPTIONS[option].label}
                    </button>
                  ))}
                </div>
              </div>

              <button type="button" className="rhythm-start" onClick={running ? stopGame : startGame}>
                {running ? 'Terminar evento' : 'Empezar juego'}
              </button>

              <Link href="/eventos" className="rhythm-back">Volver a eventos</Link>
            </aside>

            <button type="button" className={`rhythm-stage rhythm-stage-simple ${onBeat ? 'on-beat' : ''}`} onClick={hitBeat} disabled={!running}>
              <div className="rhythm-progress"><span style={{ width: `${progress}%` }}></span></div>
              <div className="rhythm-scoreboard">
                <div><span>Puntos</span><strong>{score}</strong></div>
                <div><span>Combo</span><strong>x{combo}</strong></div>
                <div><span>Máx.</span><strong>x{maxCombo}</strong></div>
              </div>
              <div className="rhythm-simple-target">
                <div className="rhythm-safe-zone">
                  <span>{onBeat ? '¡Ahora!' : 'Pulsa'}</span>
                  <small>cuando el aro toque el centro</small>
                </div>
                <div
                  className="rhythm-shrink-ring"
                  style={{
                    transform: `translate(-50%, -50%) scale(${ringScale})`,
                  }}
                ></div>
              </div>
              <div className={`rhythm-judgement rhythm-judgement-simple ${judgement.toLowerCase()}`}>{judgement}</div>
            </button>
          </div>

          <section className="rhythm-ranking">
            <div className="rhythm-ranking-header">
              <div>
                <span className="section-tag tag-purple">Ranking</span>
                <h2>Top 3 jugadores</h2>
              </div>
              {!running && score > 0 && (
                <button type="button" className="rhythm-start" onClick={saveScore} disabled={saved}>
                  {saved ? 'Guardado' : 'Guardar puntuación'}
                </button>
              )}
            </div>
            {rankingMessage && <p className="rhythm-ranking-message">{rankingMessage}</p>}
            <div className="rhythm-ranking-list">
              {ranking.length === 0 ? (
                <p>Aún no hay puntuaciones guardadas.</p>
              ) : (
                ranking.map((entry, index) => (
                  <div className="rhythm-ranking-row" key={entry.id}>
                    <strong>#{index + 1}</strong>
                    <span>{entry.username}</span>
                    <b>{entry.score}</b>
                  </div>
                ))
              )}
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}
