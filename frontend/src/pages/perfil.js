// Página de perfil de usuario
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { supabase } from '../utils/supabase';
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaPerfil() {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const router = useRouter();

  useEffect(() => {
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      
      if (!user) {
        router.push('/login');
        return;
      }

      setUser(user);
      setEditData({
        username: user.user_metadata?.username || '',
        email: user.email || '',
        password: '',
        confirmPassword: ''
      });
      
      // Obtener información adicional del perfil si existe
      const { data: profile } = await supabase
        .from('app_users')
        .select('*')
        .eq('email', user.email)
        .single();
      
      if (profile) {
        setUserProfile(profile);
      }
    } catch (error) {
      console.error('Error al obtener usuario:', error);
      setError('Error al cargar el perfil');
    } finally {
      setLoading(false);
    }
  };

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
  };

  const handleInputChange = (e) => {
    setEditData({
      ...editData,
      [e.target.name]: e.target.value
    });
  };

  const handleSaveProfile = async () => {
    try {
      setLoading(true);
      setError('');

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

      // Añadir email si ha cambiado
      if (editData.email !== user.email) {
        updateData.email = editData.email;
      }

      // Añadir contraseña si se ha proporcionado
      if (editData.password) {
        updateData.password = editData.password;
      }

      // Actualizar usuario en Supabase Auth
      const { error } = await supabase.auth.updateUser(updateData);

      if (error) throw error;

      // Actualizar información local
      setUser(prev => ({
        ...prev,
        email: editData.email,
        user_metadata: {
          ...prev.user_metadata,
          username: editData.username
        }
      }));

      setEditMode(false);
      setError('');
      
      // Limpiar campos de contraseña
      setEditData(prev => ({
        ...prev,
        password: '',
        confirmPassword: ''
      }));

    } catch (error) {
      console.error('Error al actualizar perfil:', error);
      setError(error.message || 'Error al actualizar el perfil');
    } finally {
      setLoading(false);
    }
  };

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
                  {user.user_metadata?.tipo_usuario === 'dj' ? '🎧 DJ' :
                   user.user_metadata?.tipo_usuario === 'admin' ? '⚙️ Administrador' :
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
        </div>
      </div>
    </div>
  );
}
