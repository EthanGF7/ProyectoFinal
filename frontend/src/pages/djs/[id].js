// Ficha pública de un DJ con sus playlists
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import BarraNavegacion from '../../components/BarraNavegacion';
import { useNeonCardEffects } from '../../hooks/useNeonCardEffects';
import DjAiPlayer from '../../components/DjAiPlayer';
import { useAppUser } from '../../hooks/useAppUser';
import { useListenHistory } from '../../hooks/useListenHistory';

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
  const djIdParam = Array.isArray(id) ? id[0] : id;
  const [dj, setDj] = useState(null);
  const [playlists, setPlaylists] = useState([]);
  const [audioFiles, setAudioFiles] = useState([]);
  const [currentTrack, setCurrentTrack] = useState(null);
  const [playerVisible, setPlayerVisible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { appUser } = useAppUser();
  const isLogged = Boolean(appUser);

  const {
    handleCardMouseEnter,
    handleCardMouseLeave,
    handleCardMouseMove,
    handleCardClick,
  } = useNeonCardEffects();

  const {
    history: djListenHistory,
    loading: djHistoryLoading,
    error: djHistoryError,
    refresh: refreshDjHistory,
  } = useListenHistory({ enabled: isLogged && Boolean(djIdParam), limit: 6, djId: djIdParam });

  const recentDjHistory = useMemo(() => djListenHistory.slice(0, 5), [djListenHistory]);

  useEffect(() => {
    if (!djIdParam) return;

    const loadData = async () => {
      try {
        setLoading(true);
        setError('');
        const response = await fetch(`/api/djs/${djIdParam}`);
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
  }, [djIdParam]);

  const headline = useMemo(() => {
    if (!dj) return '';
    const segments = [dj.estilo_musical, dj.estilo_visual].filter((value) => value);
    return segments.join(' · ');
  }, [dj]);


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

          {playerVisible && djIdParam && (
            <DjAiPlayer
              djId={djIdParam}
              djName={dj?.nombre_artistico || dj?.username || ''}
              onClose={() => setPlayerVisible(false)}
            />
          )}

          <section className="dj-player-section">
            <header className="dj-subheader player-header">
              <div>
                <h2>Player del DJ</h2>
                <p>Sesión autónoma con mezcla inteligente.</p>
              </div>
              <div className="player-actions">
                {dj.isLocal && (
                  <button
                    type="button"
                    className="player-toggle-button"
                    onClick={() => setPlayerVisible((v) => !v)}
                  >
                    {playerVisible ? '✕ Cerrar cabina' : '▶ Abrir cabina'}
                  </button>
                )}
              </div>
            </header>
            {!dj.isLocal && (
              <div className="admin-empty">
                Este DJ aún no tiene cabina local disponible.
              </div>
            )}
          </section>

          {isLogged && (
            <section className="dj-user-history" id="mi-historial-con-dj">
              <header className="dj-subheader">
                <div>
                  <h2>Tus sesiones con {dj?.nombre_artistico || 'este DJ'}</h2>
                  <p>Solo tú puedes ver este historial personal.</p>
                </div>
                <div className="player-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={refreshDjHistory}
                    disabled={djHistoryLoading}
                  >
                    {djHistoryLoading ? 'Actualizando...' : 'Actualizar'}
                  </button>
                </div>
              </header>

              {djHistoryError && (
                <div className="error-message" style={{ marginBottom: '16px' }}>
                  {djHistoryError}
                </div>
              )}

              {!djHistoryError && (
                <div className="dj-user-history-content">
                  {djHistoryLoading ? (
                    <p className="personal-placeholder">Cargando tus últimas sesiones...</p>
                  ) : recentDjHistory.length === 0 ? (
                    <p className="personal-placeholder">
                      Aún no registramos reproducciones tuyas con este DJ. Escucha una sesión y aparecerá aquí.
                    </p>
                  ) : (
                    <ul className="dj-user-history-list">
                      {recentDjHistory.map((item) => (
                        <li key={item.id || item.listened_at}>
                          <span className="dj-user-track">{item.track_name || 'Track sin título'}</span>
                          <span className="dj-user-meta">
                            {new Date(item.listened_at).toLocaleString('es-ES', {
                              hour: '2-digit',
                              minute: '2-digit',
                              day: '2-digit',
                              month: 'short',
                            })}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </section>
          )}

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
