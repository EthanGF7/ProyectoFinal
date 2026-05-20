// Página de perfil de usuario
import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { supabase } from '../utils/supabase';
import { createDjRequest, fetchOwnDjRequest } from '../utils/djRequests';
import { useAppUser } from '../hooks/useAppUser';
import BarraNavegacion from '../components/BarraNavegacion';
import { useListenHistory } from '../hooks/useListenHistory';

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
  const [historyScope, setHistoryScope] = useState('all');
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
    const { data: subscription } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'USER_UPDATED' || event === 'TOKEN_REFRESHED') {
        checkUser();
      }
    });

    return () => subscription?.subscription?.unsubscribe();
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

  const displayedHistory = useMemo(() => {
    if (historyScope === 'top' && historyStats.topDj?.id) {
      const targetId = historyStats.topDj.id;
      return listenHistory.filter((item) => (item?.dj_id || '') === targetId);
    }
    return listenHistory;
  }, [historyScope, historyStats, listenHistory]);

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
              <div className="stat-icon">🎵</div>
              <div className="stat-info">
                <h4>Playlists</h4>
                <p>Próximamente</p>
              </div>
            </div>
            
            <div className="profile-stat-card">
              <div className="stat-icon">❤️</div>
              <div className="stat-info">
                <h4>Favoritos</h4>
                <p>Próximamente</p>
              </div>
            </div>
            
            <div className="profile-stat-card">
              <div className="stat-icon">🎧</div>
              <div className="stat-info">
                <h4>Escuchadas</h4>
                <p>Próximamente</p>
              </div>
            </div>
          </div>

          <section className="profile-dashboard-panel" id="panel-actividad">
            <div className="profile-dashboard-head">
              <div>
                <h2>Tu panel de actividad</h2>
                <p>Accede rápido a tus datos recientes y tu cabina personal.</p>
              </div>
              <div className="profile-dashboard-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={refreshHistory}
                  disabled={historyLoading}
                >
                  {historyLoading ? 'Actualizando...' : 'Actualizar' }
                </button>
                <Link href="/dashboard" className="btn-primary-outline">
                  Abrir panel completo →
                </Link>
              </div>
            </div>

            {historyError && (
              <div className="error-message" style={{ marginBottom: '20px' }}>
                {historyError}
              </div>
            )}

            <div className="dashboard-grid profile-dashboard-grid">
              <div className="dashboard-widget neon-tile profile-dashboard-card" id="historial-reciente">
                <div className="card-content">
                  <h3>🎧 Historial reciente</h3>
                  {historyLoading ? (
                    <p className="profile-dashboard-placeholder">Cargando últimas escuchas...</p>
                  ) : listenHistory.length === 0 ? (
                    <p className="profile-dashboard-placeholder">
                      Cuando uses la cabina o escuches DJs, verás las últimas canciones aquí.
                    </p>
                  ) : (
                    <>
                      <div className="history-toggle-group">
                        <button
                          type="button"
                          className={`history-toggle ${historyScope === 'all' ? 'active' : ''}`}
                          onClick={() => setHistoryScope('all')}
                          disabled={historyScope === 'all'}
                        >
                          Todas
                        </button>
                        <button
                          type="button"
                          className={`history-toggle ${historyScope === 'top' ? 'active' : ''}`}
                          onClick={() => setHistoryScope('top')}
                          disabled={!historyStats.topDj || historyScope === 'top'}
                          title={historyStats.topDj ? `Ver solo sesiones con ${historyStats.topDj.name}` : 'Necesitas más escuchas para ver tu DJ más frecuente'}
                        >
                          Top DJ
                        </button>
                      </div>

                      <ul className="dashboard-list profile-history-list">
                        {displayedHistory.slice(0, 5).map((item) => (
                          <li key={item.id || `${item.track_name}-${item.listened_at}`}>
                            <span className="profile-history-track">{item.track_name || 'Track sin título'}</span>
                            <span className="profile-history-meta">
                              {item.dj_name ? `por ${item.dj_name}` : 'DJ desconocido'} ·{' '}
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
                    </>
                  )}
                </div>
              </div>

              <div className="dashboard-widget neon-tile profile-dashboard-card">
                <div className="card-content">
                  <h3>📈 Tus números rápidos</h3>
                  <ul className="dashboard-list">
                    <li>{historyStats.total} canciones registradas recientemente</li>
                    <li>{historyStats.uniqueDjs} DJs diferentes en tus sesiones</li>
                    <li>
                      Última escucha:{' '}
                      {historyStats.lastListen
                        ? `${historyStats.lastListen.track_name || 'Track'} · ${historyStats.lastListen.dj_name || 'DJ desconocido'}`
                        : '—'}
                    </li>
                    <li>
                      DJ más repetido:{' '}
                      {historyStats.topDj
                        ? `${historyStats.topDj.name} (${historyStats.topDj.count} sesiones)`
                        : '—'}
                    </li>
                  </ul>
                  <span className="card-link">Seguimos guardando las 10 últimas mezclas</span>
                </div>
              </div>

              <Link href="/dj" className="dashboard-widget neon-tile profile-dashboard-card">
                <div className="card-content">
                  <h3>🎚️ Cabina DJ</h3>
                  <p>Gestiona tus playlists, bio y sesiones si ya eres DJ.</p>
                  <span className="card-link">Ir al panel de DJ →</span>
                </div>
              </Link>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
