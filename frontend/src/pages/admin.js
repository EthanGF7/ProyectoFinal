// Página del panel de administración
import { useEffect, useMemo, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';
import { useAppUser } from '../hooks/useAppUser';
import {
  fetchAdminDjRequests,
  approveDjRequest,
  rejectDjRequest,
} from '../utils/djRequests';
import {
  fetchAdminDjs,
  createOrPromoteDj,
  updateDjProfile,
  deleteDj,
} from '../utils/admin';

const STATUS_TABS = [
  { value: 'pendiente', label: 'Pendientes' },
  { value: 'aprobada', label: 'Aprobadas' },
  { value: 'rechazada', label: 'Rechazadas' },
];

export default function PaginaAdmin() {
  const {
    handleCardMouseMove,
    handleCardMouseLeave,
    handleCardMouseEnter,
    handleCardClick,
  } = useNeonCardEffects();
  const { appUser, supabaseUser, loading: loadingAppUser } = useAppUser();
  const router = useRouter();

  const [requests, setRequests] = useState([]);
  const [requestsLoading, setRequestsLoading] = useState(false);
  const [requestsError, setRequestsError] = useState('');
  const [statusFilter, setStatusFilter] = useState('pendiente');
  const [actionLoading, setActionLoading] = useState(false);
  const [djs, setDjs] = useState([]);
  const [djsLoading, setDjsLoading] = useState(false);
  const [djsError, setDjsError] = useState('');
  const [djForm, setDjForm] = useState({ email: '', nombre_artistico: '', bio: '', estilo_visual: '', estilo_musical: '' });
  const [djFormLoading, setDjFormLoading] = useState(false);

  const isAdmin = useMemo(() => {
    const role = appUser?.tipo_usuario || supabaseUser?.user_metadata?.tipo_usuario;
    return role === 'admin';
  }, [appUser, supabaseUser]);

  const loadRequests = useCallback(async (estado) => {
    try {
      setRequestsLoading(true);
      setRequestsError('');
      const data = await fetchAdminDjRequests({ status: estado });
      setRequests(data);
    } catch (err) {
      console.error('[admin] Error cargando solicitudes:', err);
      setRequestsError(err.message || 'No se pudieron cargar las solicitudes');
    } finally {
      setRequestsLoading(false);
    }
  }, []);

  const loadDjs = useCallback(async () => {
    try {
      setDjsLoading(true);
      setDjsError('');
      const data = await fetchAdminDjs();
      setDjs(data);
    } catch (err) {
      console.error('[admin] Error cargando DJs:', err);
      setDjsError(err.message || 'No se pudieron obtener los DJs');
    } finally {
      setDjsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!loadingAppUser) {
      if (!isAdmin) {
        router.replace('/');
      } else {
        loadRequests(statusFilter);
        loadDjs();
      }
    }
  }, [loadingAppUser, isAdmin, router, loadRequests, loadDjs, statusFilter]);

  const handleChangeStatus = (value) => {
    setStatusFilter(value);
    loadRequests(value);
  };

  const handleApprove = async (request) => {
    try {
      setActionLoading(true);
      await approveDjRequest({
        id: request.id,
        nombre_artistico:
          request?.app_users?.username || request?.app_users?.email?.split('@')[0] || 'DJ Neon',
      });
      loadRequests(statusFilter);
    } catch (err) {
      console.error('[admin] No se pudo aprobar la solicitud:', err);
      setRequestsError(err.message || 'No se pudo aprobar la solicitud');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (request) => {
    try {
      const reason = window.prompt('Indica el motivo del rechazo (opcional):', request.mensaje || '');
      setActionLoading(true);
      await rejectDjRequest({ id: request.id, mensaje: reason || null });
      loadRequests(statusFilter);
    } catch (err) {
      console.error('[admin] No se pudo rechazar la solicitud:', err);
      setRequestsError(err.message || 'No se pudo rechazar la solicitud');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDjFormChange = (event) => {
    const { name, value } = event.target;
    setDjForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateDj = async (event) => {
    event.preventDefault();
    if (!djForm.email && !djForm.userId) {
      setDjsError('Debes indicar un email de usuario existente.');
      return;
    }
    if (!djForm.nombre_artistico) {
      setDjsError('El nombre artístico es obligatorio.');
      return;
    }

    try {
      setDjFormLoading(true);
      setDjsError('');
      await createOrPromoteDj({
        email: djForm.email || undefined,
        userId: djForm.userId || undefined,
        nombre_artistico: djForm.nombre_artistico,
        bio: djForm.bio || undefined,
        estilo_visual: djForm.estilo_visual || undefined,
        estilo_musical: djForm.estilo_musical || undefined,
      });
      setDjForm({ email: '', nombre_artistico: '', bio: '', estilo_visual: '', estilo_musical: '' });
      loadDjs();
    } catch (err) {
      console.error('[admin] Error al crear/promocionar DJ:', err);
      setDjsError(err.message || 'No se pudo crear/promocionar al DJ');
    } finally {
      setDjFormLoading(false);
    }
  };

  const handleDeleteDj = async (djId) => {
    if (!window.confirm('¿Seguro que deseas eliminar este DJ? El usuario volverá a ser normal.')) {
      return;
    }

    try {
      await deleteDj(djId);
      loadDjs();
    } catch (err) {
      console.error('[admin] Error eliminando DJ:', err);
      setDjsError(err.message || 'No se pudo eliminar el DJ');
    }
  };

  if (loadingAppUser) {
    return (
      <div className="page-container">
        <BarraNavegacion />
        <div className="profile-loading">
          <div className="loading-spinner"></div>
          <p>Cargando panel...</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="neon-main">
        <section className="neon-section">
          <header className="section-header">
            <span className="section-tag tag-purple">Panel administrador</span>
            <h2>Revisa solicitudes DJ y mantiene la pista bajo control</h2>
            <p>Aprueba talento nuevo, gestiona contenido y mantén la fiesta encendida.</p>
          </header>

          <div className="admin-requests">
            <div className="admin-tabs">
              {STATUS_TABS.map((tab) => (
                <button
                  key={tab.value}
                  type="button"
                  className={`admin-tab ${statusFilter === tab.value ? 'is-active' : ''}`}
                  onClick={() => handleChangeStatus(tab.value)}
                  disabled={requestsLoading && statusFilter === tab.value}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {requestsError && <div className="error-message">{requestsError}</div>}

            <div className="requests-grid">
              {requestsLoading ? (
                <div className="admin-loading">
                  <div className="loading-spinner"></div>
                  <p>Consultando solicitudes...</p>
                </div>
              ) : requests.length === 0 ? (
                <div className="admin-empty">No hay solicitudes en este estado.</div>
              ) : (
                requests.map((request) => (
                  <div
                    key={request.id}
                    className="neon-card admin-request-card"
                    onMouseMove={handleCardMouseMove}
                    onMouseEnter={handleCardMouseEnter}
                    onMouseLeave={handleCardMouseLeave}
                  >
                    <div className="card-content">
                      <h3>{request?.app_users?.username || 'Usuario'}</h3>
                      <div className="card-meta">{request?.app_users?.email}</div>
                      {request.mensaje && <p>{request.mensaje}</p>}
                      <p className="request-date">
                        {new Date(request.created_at).toLocaleString('es-ES')}
                      </p>

                      {request.estado === 'pendiente' ? (
                        <div className="admin-request-actions">
                          <button
                            type="button"
                            className="btn-primary"
                            onClick={() => handleApprove(request)}
                            disabled={actionLoading}
                          >
                            {actionLoading ? 'Procesando...' : 'Aprobar' }
                          </button>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => handleReject(request)}
                            disabled={actionLoading}
                          >
                            Rechazar
                          </button>
                        </div>
                      ) : (
                        <div className={`request-status-badge status-${request.estado}`}>
                          {request.estado === 'aprobada' ? 'Aprobada' : 'Rechazada'}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <section className="admin-djs">
            <header className="admin-djs-header">
              <h3>Control de DJs</h3>
              <p>Promociona usuarios a DJ, ajusta sus perfiles y retíralos si es necesario.</p>
            </header>

            <form className="dj-create-form" onSubmit={handleCreateDj}>
              <div className="form-row">
                <label>Email del usuario</label>
                <input
                  type="email"
                  name="email"
                  value={djForm.email}
                  onChange={handleDjFormChange}
                  placeholder="usuario@ejemplo.com"
                  required
                />
              </div>
              <div className="form-row">
                <label>Nombre artístico</label>
                <input
                  type="text"
                  name="nombre_artistico"
                  value={djForm.nombre_artistico}
                  onChange={handleDjFormChange}
                  placeholder="DJ Neon Pulse"
                  required
                />
              </div>
              <div className="form-grid">
                <div className="form-row">
                  <label>Bio</label>
                  <textarea
                    name="bio"
                    value={djForm.bio}
                    onChange={handleDjFormChange}
                    placeholder="Cuenta quién eres y qué música mezclas"
                    rows={3}
                  />
                </div>
                <div className="form-row">
                  <label>Estilo visual</label>
                  <input
                    type="text"
                    name="estilo_visual"
                    value={djForm.estilo_visual}
                    onChange={handleDjFormChange}
                    placeholder="Neón futurista, retro synth, etc."
                  />
                </div>
                <div className="form-row">
                  <label>Estilo musical</label>
                  <input
                    type="text"
                    name="estilo_musical"
                    value={djForm.estilo_musical}
                    onChange={handleDjFormChange}
                    placeholder="Tech house, synthwave, latin bass..."
                  />
                </div>
              </div>
              <button type="submit" className="btn-primary" disabled={djFormLoading}>
                {djFormLoading ? 'Promocionando...' : 'Añadir / Promocionar DJ'}
              </button>
            </form>

            {djsError && <div className="error-message">{djsError}</div>}

            <div className="admin-dj-list">
              {djsLoading ? (
                <div className="admin-loading">
                  <div className="loading-spinner"></div>
                  <p>Cargando DJs...</p>
                </div>
              ) : djs.length === 0 ? (
                <div className="admin-empty">Todavía no hay DJs registrados.</div>
              ) : (
                djs.map((dj) => (
                  <div
                    key={dj.id}
                    className="neon-card admin-dj-wide-card"
                    onMouseMove={handleCardMouseMove}
                    onMouseEnter={handleCardMouseEnter}
                    onMouseLeave={handleCardMouseLeave}
                  >
                    <div className="card-content admin-dj-wide-content">
                      <div className="admin-dj-wide-main">
                        <div className="admin-dj-wide-header">
                          <h3>{dj.nombre_artistico}</h3>
                          <div className="card-meta">{dj.app_users?.email}</div>
                        </div>

                        {dj.bio && <p className="admin-dj-wide-bio">{dj.bio}</p>}

                        <div className="admin-dj-wide-tags">
                          <span className="chip">Estilo visual: {dj.estilo_visual || '—'}</span>
                          <span className="chip">Estilo musical: {dj.estilo_musical || '—'}</span>
                        </div>
                      </div>

                      <div className="admin-dj-wide-actions">
                        <button type="button" className="btn-secondary" onClick={() => {
                          const nombre_artistico = window.prompt('Nombre artístico', dj.nombre_artistico || '');
                          if (!nombre_artistico) return;
                          const bio = window.prompt('Bio', dj.bio || '') || '';
                          const estilo_visual = window.prompt('Estilo visual', dj.estilo_visual || '') || '';
                          const estilo_musical = window.prompt('Estilo musical', dj.estilo_musical || '') || '';
                          updateDjProfile(dj.id, { nombre_artistico, bio, estilo_visual, estilo_musical })
                            .then(loadDjs)
                            .catch((err) => {
                              console.error('[admin] Error actualizando DJ:', err);
                              setDjsError(err.message || 'No se pudo actualizar el DJ');
                            });
                        }}>
                          Editar
                        </button>
                        <button type="button" className="btn-secondary" onClick={() => handleDeleteDj(dj.id)}>
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
