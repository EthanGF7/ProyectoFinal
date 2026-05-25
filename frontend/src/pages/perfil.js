// Página de perfil de usuario
import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { supabase } from '../utils/supabase';
import { createDjRequest, fetchOwnDjRequest } from '../utils/djRequests';
import { useAppUser } from '../hooks/useAppUser';
import { useListenHistory } from '../hooks/useListenHistory';
import { useLikedTracks } from '../hooks/useLikedTracks';
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaPerfil() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const { appUser, supabaseUser } = useAppUser();
  const [editMode, setEditMode] = useState(false);
  const [djRequest, setDjRequest] = useState(null);
  const [djRequestLoading, setDjRequestLoading] = useState(false);
  const [djRequestMessage, setDjRequestMessage] = useState('');
  const [editData, setEditData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const router = useRouter();

  const {
    history: listenHistory,
    loading: historyLoading,
    error: historyError,
    refresh: refreshHistory,
    stats: historyStats,
  } = useListenHistory({ enabled: !!user, limit: 10 });

  const {
    likedTracks,
    loading: likedLoading,
    error: likedError,
    refresh: refreshLiked,
  } = useLikedTracks({ enabled: !!user, limit: 12 });

  const fetchCurrentUser = async () => {
    const { data, error } = await supabase.auth.getUser();
    if (error) throw error;
    return data?.user || null;
  };

  const checkUser = async () => {
    try {
      const refreshedUser = await fetchCurrentUser();
      if (!refreshedUser) {
        router.push('/login');
        return;
      }

      setUser(refreshedUser);
      setEditData({
        username: refreshedUser.user_metadata?.username || '',
        email: refreshedUser.email || '',
        password: '',
        confirmPassword: ''
      });
      setSuccess('');

      // La información del usuario viene directamente de Supabase Auth
      // No necesitamos consultar una tabla adicional
    } catch (error) {
      console.error('Error al obtener usuario:', error);
      setError('Error al cargar el perfil');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkUser();
  }, []);

  useEffect(() => {
    const { data } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'USER_UPDATED' || event === 'TOKEN_REFRESHED') {
        checkUser();
      }
    });

     return () => {
       const sub = data?.subscription;
       if (sub && typeof sub.unsubscribe === 'function') {
         sub.unsubscribe();
       }
     };
  }, []);

  const handleLogout = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      
      router.push('/');
    } catch (error) {
      console.error('Error al cerrar sesión:', error);
      setError('Error al cerrar sesión');
    }
  };

  const handleEditToggle = () => {
    setEditMode(!editMode);
    setError('');
    setSuccess('');
  };

  const handleInputChange = (e) => {
    setEditData({
      ...editData,
      [e.target.name]: e.target.value
    });
    setSuccess('');
    setError('');
  };

  const handleSaveProfile = async () => {
    try {
      setLoading(true);
      setError('');
      setSuccess('');

      const previousEmail = user?.email || '';

      // Validar contraseñas si se están cambiando
      if (editData.password && editData.password !== editData.confirmPassword) {
        setError('Las contraseñas no coinciden');
        setLoading(false);
        return;
      }

      if (editData.password && editData.password.length < 6) {
        setError('La contraseña debe tener al menos 6 caracteres');
        setLoading(false);
        return;
      }

      // Preparar datos de actualización
      const updateData = {
        data: {
          username: editData.username
        }
      };

      // Añadir contraseña si se ha proporcionado
      if (editData.password) {
        updateData.password = editData.password;
      }

      // Actualizar usuario en Supabase Auth (sin cambiar email aquí)
      const { data, error } = await supabase.auth.updateUser(updateData);

      if (error) throw error;

      let emailChanged = false;

      if (editData.email !== previousEmail) {
        emailChanged = true;

        const { data: sessionData } = await supabase.auth.getSession();
        const token = sessionData?.session?.access_token;

        if (!token) {
          throw new Error('No se pudo obtener el token de sesión. Vuelve a iniciar sesión.');
        }

        const response = await fetch('/api/profile/update-email', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ newEmail: editData.email })
        });

        if (!response.ok) {
          let errorMessage = 'No se pudo actualizar el correo.';
          try {
            const errorResponse = await response.json();
            if (errorResponse?.error) {
              errorMessage = errorResponse.error;
            }
          } catch (parseError) {
            // Ignorar error de parseo y usar mensaje genérico
          }
          throw new Error(errorMessage);
        }
      }

      // Obtener el usuario actualizado desde Supabase
      const { data: refreshed } = await supabase.auth.getUser();
      const refreshedUser = refreshed?.user;

      if (refreshedUser) {
        setUser(refreshedUser);
        setEditData({
          username: refreshedUser.user_metadata?.username || editData.username,
          email: refreshedUser.email || editData.email,
          password: '',
          confirmPassword: ''
        });
      }

      if (emailChanged) {
        setSuccess('Correo actualizado correctamente.');
      } else {
        setSuccess('Perfil actualizado correctamente.');
      }

      setEditMode(false);

    } catch (error) {
      console.error('Error al actualizar perfil:', error);
      setError(error.message || 'Error al actualizar el perfil');
      setEditData(prev => ({
        ...prev,
        password: '',
        confirmPassword: ''
      }));
    } finally {
      setLoading(false);
    }
  };

  const loadDjRequest = async () => {
    try {
      setDjRequestLoading(true);
      const request = await fetchOwnDjRequest();
      setDjRequest(request);
    } catch (requestError) {
      console.error('Error al cargar solicitud DJ:', requestError);
    } finally {
      setDjRequestLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadDjRequest();
    }
  }, [user]);

  const handleRequestDj = async () => {
    try {
      setDjRequestLoading(true);
      const request = await createDjRequest({ message: djRequestMessage });
      setDjRequest(request);
      setSuccess('Solicitud enviada. Te avisaremos cuando sea revisada.');
      setDjRequestMessage('');
    } catch (requestError) {
      console.error('Error al solicitar ser DJ:', requestError);
      setError(requestError.message || 'No se pudo enviar la solicitud.');
    } finally {
      setDjRequestLoading(false);
    }
  };

  const puedeSolicitarDj = useMemo(() => {
    if (!user) return false;
    const tipo = appUser?.tipo_usuario || supabaseUser?.user_metadata?.tipo_usuario;
    if (tipo === 'dj' || tipo === 'admin') return false;
    if (!djRequest) return true;
    return djRequest.estado === 'rechazada';
  }, [user, djRequest, appUser, supabaseUser]);

  const estadoSolicitudDj = useMemo(() => {
    if (!djRequest) return null;
    const estado = djRequest.estado;
    if (estado === 'pendiente') {
      return 'Tu solicitud está siendo revisada.';
    }
    if (estado === 'aprobada') {
      return '¡Solicitud aprobada! Ya puedes acceder al panel de DJ.';
    }
    if (estado === 'rechazada') {
      return 'Solicitud rechazada. Puedes volver a intentarlo cuando quieras.';
    }
    return null;
  }, [djRequest]);

  const { lastListen, lastPlaylist, totalTracks, uniqueDjs } = useMemo(() => {
    const summary = {
      lastListen: historyStats?.lastListen || listenHistory[0] || null,
      lastPlaylist: historyStats?.lastPlaylist || listenHistory.find((item) => item?.playlist_name) || null,
      totalTracks: historyStats?.total || listenHistory.length,
      uniqueDjs: historyStats?.uniqueDjs || 0,
    };
    return summary;
  }, [historyStats, listenHistory]);

  const formattedLastListen = lastListen
    ? {
        track: lastListen.track_name || 'Track sin título',
        dj: lastListen.dj_name || 'DJ desconocido',
        time: new Date(lastListen.listened_at).toLocaleString('es-ES', {
          hour: '2-digit',
          minute: '2-digit',
          day: '2-digit',
          month: 'short',
        }),
      }
    : null;

  if (loading) {
    return (
      <div className="page-container">
        <BarraNavegacion />
        <div className="profile-loading">
          <div className="loading-spinner"></div>
          <p>Cargando perfil...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="page-container">
      <BarraNavegacion />
      
      <div className="profile-container">
        {/* Efectos de fondo */}
        <div className="profile-background">
          <div className="profile-glow"></div>
        </div>

        <div className="profile-content">
          <div className="profile-header">
            <div className="profile-avatar">
              👤
            </div>
            <h1 className="profile-title">
              Mi Perfil
            </h1>
            <p className="profile-subtitle">
              Gestiona tu información en la discoteca digital
            </p>
          </div>

          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}

          <div className="profile-info">
            <div className="profile-card">
              <h3 className="profile-card-title">
                📋 Información Personal
              </h3>
              
              <div className="profile-field">
                <label className="profile-label">👤 Username:</label>
                {editMode ? (
                  <input
                    type="text"
                    name="username"
                    value={editData.username}
                    onChange={handleInputChange}
                    className="profile-input"
                    placeholder="Tu nombre de usuario"
                  />
                ) : (
                  <span className="profile-value">
                    {user.user_metadata?.username || 'No definido'}
                  </span>
                )}
              </div>

              <div className="profile-field">
                <label className="profile-label">📧 Email:</label>
                {editMode ? (
                  <input
                    type="email"
                    name="email"
                    value={editData.email}
                    onChange={handleInputChange}
                    className="profile-input"
                    placeholder="tu@email.com"
                  />
                ) : (
                  <span className="profile-value">
                    {user.email}
                  </span>
                )}
              </div>


              <div className="profile-field">
                <label className="profile-label">🎭 Tipo de Usuario:</label>
                <span className="profile-value profile-type">
                  {(appUser?.tipo_usuario || supabaseUser?.user_metadata?.tipo_usuario) === 'dj' ? '🎧 DJ' :
                   (appUser?.tipo_usuario || supabaseUser?.user_metadata?.tipo_usuario) === 'admin' ? '⚙️ Administrador' :
                   '🎵 Usuario Normal'}
                </span>
              </div>

              <div className="profile-field">
                <label className="profile-label">📅 Miembro desde:</label>
                <span className="profile-value">
                  {formatDate(user.created_at)}
                </span>
              </div>

              {editMode && (
                <>
                  <div className="profile-field">
                    <label className="profile-label">🔑 Nueva Contraseña:</label>
                    <input
                      type="password"
                      name="password"
                      value={editData.password}
                      onChange={handleInputChange}
                      className="profile-input"
                      placeholder="Nueva contraseña (opcional)"
                    />
                  </div>

                  <div className="profile-field">
                    <label className="profile-label">🔒 Confirmar Contraseña:</label>
                    <input
                      type="password"
                      name="confirmPassword"
                      value={editData.confirmPassword}
                      onChange={handleInputChange}
                      className="profile-input"
                      placeholder="Confirmar nueva contraseña"
                    />
                  </div>
                </>
              )}
            </div>

            <div className="profile-actions">
            {editMode ? (
              <div className="profile-edit-actions">
                  <button 
                    className="btn-primary"
                    onClick={handleSaveProfile}
                    disabled={loading}
                  >
                    {loading ? '💾 Guardando...' : '💾 Guardar Cambios'}
                  </button>
                  <button 
                    className="btn-secondary"
                    onClick={handleEditToggle}
                  >
                    ❌ Cancelar
                  </button>
                </div>
              ) : (
                <button 
                  className="btn-primary"
                  onClick={handleEditToggle}
                >
                  ✏️ Editar Perfil
                </button>
              )}
              {puedeSolicitarDj && (
                <div className="dj-request-card">
                  <h4>¿Quieres ser DJ?</h4>
                  <p>Envíanos un mensaje corto explicando tu estilo y por qué quieres sumarte.</p>
                  <textarea
                    className="profile-textarea"
                    value={djRequestMessage}
                    onChange={(e) => setDjRequestMessage(e.target.value)}
                    placeholder="Comparte tu experiencia y estilo musical"
                    disabled={djRequestLoading}
                  />
                  <small className="dj-request-helper">Tu solicitud será revisada por el equipo de administración.</small>
                  <button
                    className="btn-secondary"
                    onClick={handleRequestDj}
                    disabled={djRequestLoading}
                  >
                    {djRequestLoading ? 'Enviando...' : 'Solicitar ser DJ'}
                  </button>
                </div>
              )}

              {estadoSolicitudDj && (
                <div className="dj-request-status">
                  {estadoSolicitudDj}
                </div>
              )}

              <button 
                className="btn-logout"
                onClick={handleLogout}
              >
                🚪 Cerrar Sesión
              </button>
            </div>
          </div>


          <div className="profile-stats">
            <div className="profile-stat-card">
              <div className="stat-icon">�</div>
              <div className="stat-info">
                <h4>Reproducciones</h4>
                <p>{totalTracks || 0} canciones registradas</p>
              </div>
            </div>

            <div className="profile-stat-card">
              <div className="stat-icon">🧑‍🎤</div>
              <div className="stat-info">
                <h4>DJs distintos</h4>
                <p>{uniqueDjs || 0} nombres en tu historial</p>
              </div>
            </div>

            <div className="profile-stat-card">
              <div className="stat-icon">❤️</div>
              <div className="stat-info">
                <h4>Likes guardados</h4>
                <p>{likedTracks.length} canciones favoritas</p>
              </div>
            </div>
          </div>

          <section className="profile-activity-panel" id="panel-actividad">
            <div className="profile-activity-head">
              <div>
                <h2>Tu panel de actividad</h2>
                <p>Revisa tu historial reciente, favoritos y accesos rápidos.</p>
              </div>
              <div className="profile-activity-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    refreshHistory();
                    refreshLiked();
                  }}
                  disabled={historyLoading || likedLoading}
                >
                  {historyLoading || likedLoading ? 'Actualizando...' : 'Actualizar datos'}
                </button>
              </div>
            </div>

            <div className="profile-activity-grid">
              <div className="activity-card">
                <div className="card-header">
                  <h3>🎧 Últimas canciones</h3>
                  {historyError && <span className="card-status error">{historyError}</span>}
                </div>
                {historyLoading ? (
                  <p className="card-placeholder">Cargando historial personal...</p>
                ) : listenHistory.length === 0 ? (
                  <p className="card-placeholder">
                    Aún no registramos sesiones. Lanza la cabina desde tus playlists o sets y verás todo aquí.
                  </p>
                ) : (
                  <ul className="activity-list">
                    {listenHistory.slice(0, 6).map((item) => (
                      <li key={item.id || `${item.track_name}-${item.listened_at}`}>
                        <div className="activity-track">{item.track_name || 'Track sin título'}</div>
                        <div className="activity-meta">
                          {item.dj_name || 'DJ desconocido'} ·{' '}
                          {new Date(item.listened_at).toLocaleString('es-ES', {
                            hour: '2-digit',
                            minute: '2-digit',
                            day: '2-digit',
                            month: 'short',
                          })}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="activity-card">
                <div className="card-header">
                  <h3>❤️ Tus likes recientes</h3>
                  {likedError && <span className="card-status error">{likedError}</span>}
                </div>
                {likedLoading ? (
                  <p className="card-placeholder">Consultando reacciones...</p>
                ) : likedTracks.length === 0 ? (
                  <p className="card-placeholder">Todavía no has marcado canciones con like.</p>
                ) : (
                  <ul className="activity-list">
                    {likedTracks.slice(0, 6).map((item) => (
                      <li key={item.id || `${item.dj_id}-${item.track_name}`}>
                        <div className="activity-track">{item.track_name || 'Track sin título'}</div>
                        <div className="activity-meta">
                          {item.dj_name || item.dj_id || 'DJ desconocido'} ·{' '}
                          {new Date(item.updated_at).toLocaleString('es-ES', {
                            hour: '2-digit',
                            minute: '2-digit',
                            day: '2-digit',
                            month: 'short',
                          })}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="activity-card">
                <div className="card-header">
                  <h3>📊 Resumen rápido</h3>
                </div>
                <div className="activity-summary">
                  <div className="summary-item">
                    <span className="summary-label">Último DJ escuchado</span>
                    <span className="summary-value">{formattedLastListen?.dj || 'Sin datos'}</span>
                  </div>
                  <div className="summary-item">
                    <span className="summary-label">Última canción</span>
                    <span className="summary-value">{formattedLastListen?.track || 'Sin datos'}</span>
                    {formattedLastListen && <span className="summary-meta">{formattedLastListen.time}</span>}
                  </div>
                  <div className="summary-item">
                    <span className="summary-label">Última playlist</span>
                    <span className="summary-value">{lastPlaylist?.playlist_name || 'Sin playlist registrada'}</span>
                  </div>
                  <div className="summary-item">
                    <span className="summary-label">Total de likes</span>
                    <span className="summary-value">{likedTracks.length}</span>
                  </div>
                </div>
                <div className="activity-footer">
                  <Link href="/playlists" className="card-link">
                    Explorar playlists →
                  </Link>
                </div>
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
