import { useEffect, useState } from 'react';
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';

const visualOptions = [
  { value: 'minimal', label: 'Minimal' },
  { value: 'club', label: 'Club oscuro' },
  { value: 'chill', label: 'Chill' },
  { value: 'latin', label: 'Latin' },
  { value: 'pop', label: 'Pop editorial' },
  { value: 'retro', label: 'Retro' },
];

function getPlaylistVisualPreset(playlist) {
  const preset = playlist?.mood || 'minimal';
  if (visualOptions.some((option) => option.value === preset)) return preset;
  return 'minimal';
}

function getVisualOptionLabel(value) {
  return visualOptions.find((option) => option.value === value)?.label || 'Minimal';
}

export default function PaginaPlaylists() {
  const [playlists, setPlaylists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const {
    handleCardMouseMove,
    handleCardMouseLeave,
    handleCardMouseEnter,
    handleCardClick,
  } = useNeonCardEffects();

  useEffect(() => {
    async function loadPlaylists() {
      try {
        setLoading(true);
        setError('');
        const response = await fetch('/api/playlists');
        const payload = await response.json();

        if (!response.ok) {
          throw new Error(payload.error || 'No se pudieron cargar las playlists');
        }

        setPlaylists(payload.playlists || []);
      } catch (err) {
        setError(err.message || 'No se pudieron cargar las playlists');
      } finally {
        setLoading(false);
      }
    }

    loadPlaylists();
  }, []);

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="neon-main">
        <section className="neon-section">
          <header className="section-header">
            <span className="section-tag">Playlists</span>
            <h2>Playlists creadas por usuarios DJ</h2>
            <p>Explora todas las playlists publicadas por los DJs de la comunidad.</p>
          </header>

          {loading ? (
            <div className="admin-loading">
              <div className="loading-spinner"></div>
              <p>Cargando playlists...</p>
            </div>
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : playlists.length === 0 ? (
            <div className="admin-empty">Aún no hay playlists creadas por usuarios.</div>
          ) : (
            <div className="public-playlist-stack">
              {playlists.map((playlist, index) => (
                <Link
                  key={playlist.id}
                  href={`/playlists/${encodeURIComponent(playlist.id)}`}
                  className={`neon-card playlist-visual-card public-playlist-card ${index % 2 === 1 ? 'is-reversed' : ''} visual-${getPlaylistVisualPreset(playlist)}`}
                  onMouseMove={handleCardMouseMove}
                  onMouseEnter={handleCardMouseEnter}
                  onMouseLeave={handleCardMouseLeave}
                  onClick={handleCardClick}
                >
                  <div className="playlist-visualizer" aria-hidden="true">
                    <span></span>
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <div className="card-content">
                    <div className="public-playlist-main">
                      <span className="playlist-kicker">{getVisualOptionLabel(playlist.mood)}</span>
                      <h3>{playlist.titulo}</h3>
                      {playlist.descripcion && <p className="playlist-description">{playlist.descripcion}</p>}
                    </div>
                    <div className="public-playlist-meta">
                      <span>Creada por</span>
                      <strong>{playlist.dj?.nombre_artistico || 'DJ'}</strong>
                      <b>Abrir playlist →</b>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
