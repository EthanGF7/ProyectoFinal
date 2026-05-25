import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import BarraNavegacion from '../../components/BarraNavegacion';

const visualOptions = [
  { value: 'minimal', label: 'Minimal' },
  { value: 'club', label: 'Club oscuro' },
  { value: 'chill', label: 'Chill' },
  { value: 'latin', label: 'Latin' },
  { value: 'pop', label: 'Pop editorial' },
  { value: 'retro', label: 'Retro' },
];

function getSpotifyPlaylistId(url) {
  if (!url || typeof url !== 'string') return null;
  try {
    const parsed = new URL(url.trim());
    if (!parsed.hostname.includes('spotify.com')) return null;
    const parts = parsed.pathname.split('/').filter(Boolean);
    const playlistIndex = parts.indexOf('playlist');
    return playlistIndex >= 0 ? parts[playlistIndex + 1] || null : null;
  } catch {
    return null;
  }
}

function getPlaylistLinks(plataformas) {
  return (plataformas || '')
    .split(',')
    .map((url) => url.trim())
    .filter((url) => url.length > 0);
}

function getPlaylistVisualPreset(playlist) {
  const preset = playlist?.mood || 'minimal';
  if (visualOptions.some((option) => option.value === preset)) return preset;
  return 'minimal';
}

function getVisualOptionLabel(value) {
  return visualOptions.find((option) => option.value === value)?.label || 'Minimal';
}

export default function PlaylistPage() {
  const router = useRouter();
  const { id } = router.query;
  const playlistId = Array.isArray(id) ? id[0] : id;
  const [playlist, setPlaylist] = useState(null);
  const [dj, setDj] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!playlistId) return;

    async function loadPlaylist() {
      try {
        setLoading(true);
        setError('');
        const response = await fetch(`/api/playlists/${encodeURIComponent(playlistId)}`);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || 'No se pudo cargar la playlist');
        }
        setPlaylist(payload.playlist);
        setDj(payload.dj);
      } catch (err) {
        setError(err.message || 'No se pudo cargar la playlist');
      } finally {
        setLoading(false);
      }
    }

    loadPlaylist();
  }, [playlistId]);

  return (
    <div className="page-container">
      <BarraNavegacion />
      <main className="neon-main playlist-page-main">
        {loading ? (
          <div className="profile-loading">
            <div className="loading-spinner"></div>
            <p>Cargando playlist...</p>
          </div>
        ) : error ? (
          <section className="neon-section playlist-page-shell">
            <div className="error-message">{error}</div>
            <Link href="/djs" className="btn-secondary">Volver a DJs</Link>
          </section>
        ) : (
          <section className={`playlist-page-shell visual-${getPlaylistVisualPreset(playlist)}`}>
            <div className="playlist-modal-aura" aria-hidden="true"></div>
            <div className="playlist-orb-field" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div className="playlist-waveform" aria-hidden="true">
              {Array.from({ length: 18 }).map((_, index) => (
                <span key={index}></span>
              ))}
            </div>
            <div className="playlist-visualizer playlist-modal-visualizer" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div className="playlist-page-meta">
              <span className="playlist-kicker">{getVisualOptionLabel(playlist?.mood)}</span>
              {dj && (
                <Link href={`/djs/${encodeURIComponent(dj.id)}`} className="playlist-dj-link">
                  Por {dj.nombre_artistico || 'DJ'}
                </Link>
              )}
            </div>
            <h1>{playlist?.titulo}</h1>
            {playlist?.descripcion && (
              <p className="playlist-description playlist-page-description">{playlist.descripcion}</p>
            )}
            {getPlaylistLinks(playlist?.plataformas).map((url) => {
              const spotifyPlaylistId = getSpotifyPlaylistId(url);
              if (spotifyPlaylistId) {
                return (
                  <div className="spotify-embed playlist-page-embed" key={url}>
                    <iframe
                      title={`Spotify playlist ${playlist.titulo}`}
                      src={`https://open.spotify.com/embed/playlist/${spotifyPlaylistId}`}
                      width="100%"
                      height="520"
                      frameBorder="0"
                      allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                      loading="lazy"
                    />
                  </div>
                );
              }

              return (
                <div className="playlist-links" key={url}>
                  <a href={url} target="_blank" rel="noreferrer">
                    {url}
                  </a>
                </div>
              );
            })}
          </section>
        )}
      </main>
    </div>
  );
}
