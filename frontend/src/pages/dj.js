// Panel para DJs
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import BarraNavegacion from '../components/BarraNavegacion';
import { useAppUser } from '../hooks/useAppUser';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';
import {
  fetchDjProfile,
  updateDjProfile,
  fetchDjPlaylists,
  createDjPlaylist,
  updateDjPlaylist,
  deleteDjPlaylist,
} from '../utils/djPanel';

const defaultProfile = {
  nombre_artistico: '',
  bio: '',
  estilo_visual: '',
  estilo_musical: '',
};

const defaultPlaylistForm = {
  titulo: '',
  descripcion: '',
  mood: '',
  tempo: '',
  plataformas: '',
};

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

export default function PanelDj() {
  const router = useRouter();
  const { appUser, supabaseUser, loading: loadingUser } = useAppUser();
  const {
    handleCardMouseEnter,
    handleCardMouseLeave,
    handleCardMouseMove,
    handleCardClick,
  } = useNeonCardEffects();

  const role = useMemo(
    () => appUser?.tipo_usuario || supabaseUser?.user_metadata?.tipo_usuario,
    [appUser, supabaseUser]
  );
  const isDj = role === 'dj' || role === 'admin';

  const [profile, setProfile] = useState(null);
  const [profileForm, setProfileForm] = useState(defaultProfile);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');

  const [playlists, setPlaylists] = useState([]);
  const [playlistsLoading, setPlaylistsLoading] = useState(false);
  const [playlistsError, setPlaylistsError] = useState('');
  const [playlistForm, setPlaylistForm] = useState(defaultPlaylistForm);
  const [playlistSaving, setPlaylistSaving] = useState(false);

  const loadProfile = useCallback(async () => {
    try {
      setProfileLoading(true);
      setProfileError('');
      const data = await fetchDjProfile();
      setProfile(data);
      if (data) {
        setProfileForm({
          nombre_artistico: data.nombre_artistico || '',
          bio: data.bio || '',
          estilo_visual: data.estilo_visual || '',
          estilo_musical: data.estilo_musical || '',
        });
      }
    } catch (err) {
      console.error('[dj] Error cargando perfil DJ:', err);
      setProfileError(err.message || 'No se pudo cargar el perfil');
    } finally {
      setProfileLoading(false);
    }
  }, []);

  const loadPlaylists = useCallback(async () => {
    try {
      setPlaylistsLoading(true);
      setPlaylistsError('');
      const data = await fetchDjPlaylists();
      setPlaylists(data);
    } catch (err) {
      console.error('[dj] Error cargando playlists:', err);
      setPlaylistsError(err.message || 'No se pudieron cargar las playlists');
    } finally {
      setPlaylistsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!loadingUser) {
      if (!isDj) {
        router.replace('/perfil');
      } else {
        loadProfile();
        loadPlaylists();
      }
    }
  }, [loadingUser, isDj, router, loadProfile, loadPlaylists]);

  useEffect(() => {
    if (!profile && !profileLoading) {
      setProfileForm(defaultProfile);
    }
  }, [profile, profileLoading]);

  const handleProfileChange = (event) => {
    const { name, value } = event.target;
    setProfileForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    if (!profileForm.nombre_artistico) {
      setProfileError('El nombre artístico es obligatorio.');
      return;
    }

    try {
      setProfileSaving(true);
      setProfileError('');
      setProfileSuccess('');
      const updated = await updateDjProfile(profileForm);
      setProfile(updated);
      setProfileSuccess('Perfil actualizado. ¡Listo para la siguiente sesión!');
    } catch (err) {
      console.error('[dj] Error guardando perfil:', err);
      setProfileError(err.message || 'No se pudo actualizar el perfil');
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePlaylistFormChange = (event) => {
    const { name, value } = event.target;
    setPlaylistForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreatePlaylist = async (event) => {
    event.preventDefault();
    if (!playlistForm.titulo) {
      setPlaylistsError('Ponle un título a tu playlist.');
      return;
    }

    try {
      setPlaylistSaving(true);
      setPlaylistsError('');
      const created = await createDjPlaylist(playlistForm);
      setPlaylists((prev) => [created, ...prev]);
      setPlaylistForm(defaultPlaylistForm);
    } catch (err) {
      console.error('[dj] Error creando playlist:', err);
      setPlaylistsError(err.message || 'No se pudo crear la playlist');
    } finally {
      setPlaylistSaving(false);
    }
  };

  const handleEditPlaylist = async (playlist) => {
    const titulo = window.prompt('Título de la playlist', playlist.titulo || '')?.trim();
    if (!titulo) return;
    const descripcion = window.prompt('Descripción', playlist.descripcion || '') || '';
    const mood = window.prompt('Mood / ambiente', playlist.mood || '') || '';
    const tempo = window.prompt('Tempo / BPM', playlist.tempo || '') || '';
    const plataformas = window.prompt('Enlaces (Spotify playlist, SoundCloud...)', playlist.plataformas || '') || '';

    try {
      const updated = await updateDjPlaylist(playlist.id, {
        titulo,
        descripcion,
        mood,
        tempo,
        plataformas,
      });
      setPlaylists((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      console.error('[dj] Error actualizando playlist:', err);
      setPlaylistsError(err.message || 'No se pudo actualizar la playlist');
    }
  };

  const handleDeletePlaylist = async (playlistId) => {
    if (!window.confirm('¿Eliminar esta playlist? Se quitará del escaparate DJ.')) {
      return;
    }

    try {
      await deleteDjPlaylist(playlistId);
      setPlaylists((prev) => prev.filter((item) => item.id !== playlistId));
    } catch (err) {
      console.error('[dj] Error eliminando playlist:', err);
      setPlaylistsError(err.message || 'No se pudo eliminar la playlist');
    }
  };

  if (loadingUser || (isDj && profileLoading && playlistsLoading)) {
    return (
      <div className="page-container">
        <BarraNavegacion />
        <div className="profile-loading">
          <div className="loading-spinner"></div>
          <p>Cargando cabina DJ...</p>
        </div>
      </div>
    );
  }

  if (!isDj) {
    return null;
  }

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="neon-main">
        <section className="neon-section dj-panel">
          <header className="section-header">
            <span className="section-tag tag-purple">Panel DJ</span>
            <h2>Personaliza tu cabina y comparte tus sets</h2>
            <p>
              Ajusta tu perfil artístico y mantiene tus playlists listas para el próximo show.
            </p>
          </header>

          <section className="dj-profile">
            <header className="dj-subheader">
              <h3>Tu identidad en la cabina</h3>
              <p>Actualiza cómo te verá la comunidad en la página de DJs.</p>
            </header>

            <form className="dj-profile-form" onSubmit={handleProfileSubmit}>
              <div className="form-row">
                <label>Nombre artístico</label>
                <input
                  type="text"
                  name="nombre_artistico"
                  value={profileForm.nombre_artistico}
                  onChange={handleProfileChange}
                  placeholder="DJ Stardust"
                  required
                />
              </div>

              <div className="form-grid">
                <div className="form-row">
                  <label>Bio</label>
                  <textarea
                    name="bio"
                    value={profileForm.bio}
                    onChange={handleProfileChange}
                    placeholder="Cuéntanos tu historia y la energía de tus sesiones"
                    rows={4}
                  />
                  <span className="form-helper">Esta descripción se mostrará en tu tarjeta pública.</span>
                </div>
                <div className="form-row">
                  <label>Estilo visual</label>
                  <input
                    type="text"
                    name="estilo_visual"
                    value={profileForm.estilo_visual}
                    onChange={handleProfileChange}
                    placeholder="Neón vaporwave, lasers, visuales retro..."
                  />
                </div>
                <div className="form-row">
                  <label>Estilo musical</label>
                  <input
                    type="text"
                    name="estilo_musical"
                    value={profileForm.estilo_musical}
                    onChange={handleProfileChange}
                    placeholder="Tech house, synthwave, latin bass..."
                  />
                </div>
              </div>

              {profileError && <div className="error-message">{profileError}</div>}
              {profileSuccess && <div className="success-message">{profileSuccess}</div>}

              <button type="submit" className="btn-primary" disabled={profileSaving}>
                {profileSaving ? 'Guardando...' : 'Guardar perfil'}
              </button>
            </form>
          </section>

          <section className="dj-playlists">
            <header className="dj-subheader">
              <h3>Tus playlists destacadas</h3>
              <p>Comparte sets recientes, sesiones temáticas, mixes exclusivos o playlists de Spotify.</p>
            </header>

            <form className="dj-playlist-form" onSubmit={handleCreatePlaylist}>
              <div className="form-row">
                <label>Título</label>
                <input
                  type="text"
                  name="titulo"
                  value={playlistForm.titulo}
                  onChange={handlePlaylistFormChange}
                  placeholder="Sunset Rooftop Session"
                  required
                />
              </div>

              <div className="form-grid">
                <div className="form-row">
                  <label>Descripción</label>
                  <textarea
                    name="descripcion"
                    value={playlistForm.descripcion}
                    onChange={handlePlaylistFormChange}
                    placeholder="Qué atmósfera ofrece, invitados, duración..."
                    rows={3}
                  />
                </div>
                <div className="form-row">
                  <label>Mood / Ambiente</label>
                  <input
                    type="text"
                    name="mood"
                    value={playlistForm.mood}
                    onChange={handlePlaylistFormChange}
                    placeholder="Noche futurista, chill electro, sunset vibes..."
                  />
                </div>
                <div className="form-row">
                  <label>Tempo / BPM</label>
                  <input
                    type="text"
                    name="tempo"
                    value={playlistForm.tempo}
                    onChange={handlePlaylistFormChange}
                    placeholder="124 BPM, Mid-tempo, 90-100 BPM..."
                  />
                </div>
                <div className="form-row">
                  <label>Enlaces</label>
                  <input
                    type="text"
                    name="plataformas"
                    value={playlistForm.plataformas}
                    onChange={handlePlaylistFormChange}
                    placeholder="https://open.spotify.com/playlist/..."
                  />
                  <span className="form-helper">Pega una playlist de Spotify para mostrarla embebida. Separa múltiples enlaces con comas.</span>
                </div>
              </div>

              <button type="submit" className="btn-secondary" disabled={playlistSaving}>
                {playlistSaving ? 'Publicando...' : 'Añadir playlist'}
              </button>
            </form>

            {playlistsError && <div className="error-message">{playlistsError}</div>}

            <div className="dj-grid">
              {playlistsLoading ? (
                <div className="admin-loading">
                  <div className="loading-spinner"></div>
                  <p>Recopilando playlists...</p>
                </div>
              ) : playlists.length === 0 ? (
                <div className="admin-empty">
                  Aún no tienes playlists registradas. ¡Comparte tu primer set para la comunidad!
                </div>
              ) : (
                playlists.map((playlist) => (
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
                      {getPlaylistLinks(playlist.plataformas).map((url) => {
                        const spotifyPlaylistId = getSpotifyPlaylistId(url);
                        if (spotifyPlaylistId) {
                          return (
                            <div className="spotify-embed" key={url}>
                              <iframe
                                title={`Spotify playlist ${playlist.titulo}`}
                                src={`https://open.spotify.com/embed/playlist/${spotifyPlaylistId}`}
                                width="100%"
                                height="352"
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
                      <div className="admin-request-actions">
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => handleEditPlaylist(playlist)}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => handleDeletePlaylist(playlist.id)}
                        >
                          Eliminar
                        </button>
                      </div>
                    </div>
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
