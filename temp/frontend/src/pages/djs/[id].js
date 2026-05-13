// Ficha pública de un DJ con sus playlists
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import BarraNavegacion from '../../components/BarraNavegacion';
import { useNeonCardEffects } from '../../hooks/useNeonCardEffects';

const formatDate = (value) => {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
  });
};

export default function FichaDj() {
  const router = useRouter();
  const { id } = router.query;
  const [dj, setDj] = useState(null);
  const [playlists, setPlaylists] = useState([]);
  const [audioFiles, setAudioFiles] = useState([]);
  const [currentTrack, setCurrentTrack] = useState(null);
  const [playerVisible, setPlayerVisible] = useState(false);
  const [launchingPlayer, setLaunchingPlayer] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const {
    handleCardMouseEnter,
    handleCardMouseLeave,
    handleCardMouseMove,
    handleCardClick,
  } = useNeonCardEffects();

  useEffect(() => {
    if (!id) return;

    const loadData = async () => {
      try {
        setLoading(true);
        setError('');
        const response = await fetch(`/api/djs/${id}`);
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload.error || 'No se pudo cargar el DJ');
        }
        const payload = await response.json();
        setDj(payload.dj || null);
        setPlaylists(payload.playlists || []);
        setAudioFiles(payload.audioFiles || []);
        setCurrentTrack((payload.audioFiles || [])[0] || null);
      } catch (err) {
        console.error('[djs/:id] Error cargando DJ:', err);
        setError(err.message || 'No se pudo cargar la ficha del DJ');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id]);

  const headline = useMemo(() => {
    if (!dj) return '';
    const segments = [dj.estilo_musical, dj.estilo_visual].filter((value) => value);
    return segments.join(' · ');
  }, [dj]);

  const handleLaunchPlayer = async () => {
    if (!dj?.isLocal || !id) return;

    setLaunchingPlayer(true);
    try {
      const response = await fetch(`/api/djs/${id}/launch`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || 'No se pudo arrancar el player local');
      }
      const payload = await response.json();
      const port = payload.port || 8765;

      const tryOpen = async () => {
        const maxAttempts = 10;
        const url = `http://localhost:${port}`;
        for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
          try {
            const response = await fetch(url);
            if (response.ok) {
              window.open(url, '_blank');
              return;
            }
          } catch (err) {
            // Ignorar errores de conexión
          }
          await new Promise((resolve) => setTimeout(resolve, 500));
        }
        // Abrir de todas formas después de los intentos
        window.open(url, '_blank');
      };

      await tryOpen();
    } catch (err) {
      console.error('[djs/:id] Error arrancando player:', err);
      alert(err.message || 'No se pudo arrancar el player local');
    } finally {
      setLaunchingPlayer(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <BarraNavegacion />
        <div className="profile-loading">
          <div className="loading-spinner"></div>
          <p>Encendiendo cabina...</p>
        </div>
      </div>
    );
  }

  if (error || !dj) {
    return (
      <div className="page-container">
        <BarraNavegacion />
        <main className="neon-main">
          <section className="neon-section">
            <div className="error-message" style={{ marginBottom: '24px' }}>
              {error || 'No encontramos a este DJ.'}
            </div>
            <Link href="/djs" className="btn-secondary">
              Volver a todos los DJs
            </Link>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="neon-main">
        <section className="neon-section dj-profile-detail">
          <header className="section-header">
            <span className="section-tag tag-purple">DJ destacado</span>
            <h1>{dj.nombre_artistico}</h1>
            {headline && <p>{headline}</p>}
            {dj.bio && <p className="dj-bio">{dj.bio}</p>}
            <div className="dj-meta">
              {dj.username && <span>@{dj.username}</span>}
              {dj.email && <span>{dj.email}</span>}
              {dj.created_at && <span>En cabina desde {formatDate(dj.created_at)}</span>}
            </div>
            <Link href="/djs" className="back-link">
              ← Volver al catálogo de DJs
            </Link>
          </header>

          <section className="dj-player-section">
            <header className="dj-subheader player-header">
              <div>
                <h2>Player del DJ</h2>
                <p>Escucha la sesión del DJ seleccionado.</p>
              </div>
              <div className="player-actions">
                {dj.isLocal && (
                  <button
                    type="button"
                    className="player-open-link"
                    onClick={handleLaunchPlayer}
                    disabled={launchingPlayer}
                  >
                    {launchingPlayer ? 'Arrancando player...' : 'Abrir player local'}
                  </button>
                )}
                {audioFiles.length > 0 && (
                  <button
                    type="button"
                    className="player-toggle-button"
                    onClick={() => setPlayerVisible((visible) => !visible)}
                  >
                    {playerVisible ? 'Cerrar player' : 'Abrir player'}
                  </button>
                )}
              </div>
            </header>

            {audioFiles.length > 0 ? (
              playerVisible ? (
                <div className="dj-audio-panel">
                  <div className="dj-audio-player">
                    <audio
                      controls
                      src={currentTrack?.url}
                      preload="metadata"
                      className="audio-player"
                    />
                  </div>
                  <div className="dj-track-list">
                    {audioFiles.map((file) => (
                      <button
                        key={file.name}
                        type="button"
                        className={`track-button ${currentTrack?.name === file.name ? 'active' : ''}`}
                        onClick={() => setCurrentTrack(file)}
                      >
                        {file.name}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="player-placeholder">
                  <p>Pulsa el botón para abrir el reproductor del DJ.</p>
                </div>
              )
            ) : (
              <div className="admin-empty">
                Aún no hay audio disponible para este DJ.
              </div>
            )}
          </section>

          <section className="dj-playlists-public">
            <header className="dj-subheader">
              <h2>Playlists destacadas</h2>
              <p>Sets, mixes y sesiones que comparte con la comunidad.</p>
            </header>

            {playlists.length === 0 ? (
              <div className="admin-empty">
                Aún no hay playlists publicadas por este DJ.
              </div>
            ) : (
              <div className="dj-grid">
                {playlists.map((playlist) => (
                  <div
                    key={playlist.id}
                    className="neon-card dj-card"
                    onMouseMove={handleCardMouseMove}
                    onMouseEnter={handleCardMouseEnter}
                    onMouseLeave={handleCardMouseLeave}
                    onClick={handleCardClick}
                  >
                    <div className="card-content">
                      <h3>{playlist.titulo}</h3>
                      {playlist.descripcion && <p>{playlist.descripcion}</p>}
                      <div className="playlist-chip">Mood: {playlist.mood || '—'}</div>
                      <div className="playlist-chip">Tempo: {playlist.tempo || '—'}</div>
                      {playlist.plataformas && (
                        <div className="playlist-links">
                          {playlist.plataformas
                            .split(',')
                            .map((url) => url.trim())
                            .filter((url) => url.length > 0)
                            .map((url) => (
                              <a key={url} href={url} target="_blank" rel="noreferrer">
                                {url}
                              </a>
                            ))}
                        </div>
                      )}
                      <span className="playlist-date">
                        Publicada {formatDate(playlist.created_at) || 'recientemente'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </section>
      </main>
    </div>
  );
}
