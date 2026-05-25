// Página de DJ: abre la UI del DJ dentro del mismo host de la web.
// La UI del DJ se carga mediante un iframe que consume el servidor local a través de un proxy.
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import BarraNavegacion from '../../components/BarraNavegacion';
import { supabase } from '../../utils/supabase';

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

export default function FichaDj() {
  const router = useRouter();
  const { id } = router.query;
  const djIdParam = Array.isArray(id) ? id[0] : id;
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);
  const [iframeSrc, setIframeSrc] = useState(null);
  const [iframeEl, setIframeEl] = useState(null);
  const [djData, setDjData] = useState(null);

  useEffect(() => {
    if (!iframeEl || status !== 'ready') return undefined;

    let cancelled = false;

    async function sendToken() {
      const { data } = await supabase.auth.getSession();
      const accessToken = data?.session?.access_token;
      if (!cancelled && accessToken && iframeEl.contentWindow) {
        iframeEl.contentWindow.postMessage({ type: 'nexus-auth-token', accessToken }, window.location.origin);
      }
    }

    sendToken();
    const interval = setInterval(sendToken, 1000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [iframeEl, status]);

  useEffect(() => {
    if (!djIdParam) return;

    async function launch() {
      try {
        const detailRes = await fetch(`/api/djs/${encodeURIComponent(djIdParam)}`);
        const detail = await detailRes.json();
        if (!detailRes.ok) {
          throw new Error(detail.error || `HTTP ${detailRes.status}`);
        }

        setDjData(detail);

        if (!detail.dj?.hasLocalPlayer) {
          setStatus('playlist');
          return;
        }

        const launchRes = await fetch(`/api/djs/${encodeURIComponent(djIdParam)}/launch`, {
          method: 'POST',
        });
        const launchData = await launchRes.json();
        if (!launchRes.ok || !launchData.ok) {
          throw new Error(launchData.error || `HTTP ${launchRes.status}`);
        }

        setIframeSrc(`/api/djs/${encodeURIComponent(djIdParam)}/proxy/`);
        setStatus('ready');
      } catch (err) {
        setStatus('error');
        setError(err instanceof Error ? err.message : String(err));
      }
    }

    launch();
  }, [djIdParam]);

  if (!djIdParam) {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          background: '#07080f',
          color: '#c8ff00',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'IBM Plex Mono, monospace',
          fontSize: '12px',
          letterSpacing: '3px',
          textTransform: 'uppercase',
        }}
      >
        Cargando cabina…
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          background: '#07080f',
          color: '#c8ff00',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: '18px',
          padding: '24px',
          textAlign: 'center',
          fontFamily: 'IBM Plex Mono, monospace',
          fontSize: '14px',
          letterSpacing: '1px',
        }}
      >
        <div style={{ fontSize: '20px', fontWeight: 700, color: '#ff6b6b' }}>Error arrancando el DJ</div>
        <div>{error}</div>
        <button
          onClick={() => router.push('/djs')}
          style={{
            marginTop: '16px',
            padding: '10px 18px',
            borderRadius: '10px',
            border: '1px solid #c8ff00',
            background: 'transparent',
            color: '#c8ff00',
            cursor: 'pointer',
          }}
        >
          Volver a la lista de DJs
        </button>
      </div>
    );
  }

  if (status === 'playlist') {
    const dj = djData?.dj;
    const playlists = djData?.playlists || [];
    return (
      <div className="page-container">
        <BarraNavegacion />
        <main className="neon-main">
          <section className="neon-section">
            <header className="section-header">
              <span className="section-tag tag-purple">DJ de playlist</span>
              <h2>{dj?.nombre_artistico || 'DJ'}</h2>
              <p>{dj?.bio || 'Este DJ comparte playlists externas para escuchar sin descargar música.'}</p>
            </header>

            <div className="dj-playlist-stack">
              {playlists.length === 0 ? (
                <div className="admin-empty">Este DJ todavía no tiene playlists publicadas.</div>
              ) : (
                playlists.map((playlist, index) => (
                  <article
                    className={`neon-card dj-card playlist-visual-card dj-playlist-wide-card ${index % 2 === 1 ? 'is-reversed' : ''} visual-${getPlaylistVisualPreset(playlist)}`}
                    key={playlist.id}
                    onClick={() => router.push(`/playlists/${encodeURIComponent(playlist.id)}`)}
                  >
                    <div className="playlist-visualizer" aria-hidden="true">
                      <span></span>
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <div className="card-content">
                      <div className="dj-playlist-info">
                        <span className="playlist-kicker">{getVisualOptionLabel(playlist.mood)}</span>
                        <h3>{playlist.titulo}</h3>
                        {playlist.descripcion && <p className="playlist-description">{playlist.descripcion}</p>}
                        <span className="card-link">Abrir playlist →</span>
                      </div>
                      <div className="dj-playlist-player">
                        {getPlaylistLinks(playlist.plataformas).map((url) => {
                          const spotifyPlaylistId = getSpotifyPlaylistId(url);
                          if (spotifyPlaylistId) {
                            return (
                              <div className="spotify-embed" key={url}>
                                <iframe
                                  title={`Spotify playlist ${playlist.titulo}`}
                                  src={`https://open.spotify.com/embed/playlist/${spotifyPlaylistId}`}
                                  width="100%"
                                  height="180"
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
                      </div>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: '#07080f', overflow: 'hidden' }}>
      {status === 'loading' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: '12px',
            color: '#c8ff00',
            fontFamily: 'IBM Plex Mono, monospace',
            textAlign: 'center',
            padding: '24px',
          }}
        >
          <div style={{ fontSize: '20px', fontWeight: 700 }}>Abriendo el DJ...</div>
          <div>Conectando el servidor local al mismo host de la web.</div>
          <div style={{ color: '#7cfc00' }}>Mantente en esta página mientras se carga.</div>
        </div>
      )}

      {status === 'ready' && iframeSrc && (
        <iframe
          ref={setIframeEl}
          title="DJ Player"
          src={iframeSrc}
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      )}
    </div>
  );
}
