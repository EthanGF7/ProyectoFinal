// Página de registro de usuarios
import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { supabase } from '../utils/supabase';
import { syncUserProfile } from '../utils/profileSync';
import PopupVerificacion from '../components/PopupVerificacion';

export default function PaginaRegistro() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    tipoUsuario: 'usuario_normal'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showPopup, setShowPopup] = useState(false);
  const router = useRouter();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError(''); // Limpiar errores al escribir
  };

  const validateForm = () => {
    if (formData.password !== formData.confirmPassword) {
      setError('Las contraseñas no coinciden');
      return false;
    }
    if (formData.password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres');
      return false;
    }
    if (formData.username.length < 3) {
      setError('El username debe tener al menos 3 caracteres');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    if (!validateForm()) {
      setLoading(false);
      return;
    }

    try {
      // Registrar usuario con Supabase Auth
      const tipoSeleccionado = formData.tipoUsuario;

      const { data, error } = await supabase.auth.signUp({
        email: formData.email,
        password: formData.password,
        options: {
          data: {
            username: formData.username,
            tipo_usuario: tipoSeleccionado
          }
        }
      });

      if (error) {
        throw error;
      }

      if (data.user) {
        try {
          await syncUserProfile({
            username: formData.username,
            tipoUsuario: tipoSeleccionado,
          });
        } catch (syncError) {
          console.warn('No se pudo sincronizar el perfil inmediatamente:', syncError?.message || syncError);
        }

        setSuccess('¡Registro exitoso! Revisa tu email para confirmar tu cuenta.');
        setShowPopup(true);
      }
    } catch (error) {
      console.error('Error de registro:', error);
      setError(error.message || 'Error al registrar usuario');
    } finally {
      setLoading(false);
    }
  };

  const handleClosePopup = () => {
    setShowPopup(false);
    // Redirigir al login después de cerrar el popup
    setTimeout(() => {
      router.push('/login');
    }, 500);
  };

  return (
    <div className="auth-container">
      {/* Vinilo animado de fondo */}
      <div className="vinyl-background">
        <div className="vinyl-glow"></div>
        <div className="vinyl-record">
          <div className="vinyl-grooves"></div>
          <div className="vinyl-reflection"></div>
        </div>
      </div>
      
      {/* Partículas musicales flotantes */}
      <div className="music-particles">
        <div className="music-note">♪</div>
        <div className="music-note">♫</div>
        <div className="music-note">♪</div>
      </div>
      
      <div className="auth-form">
        <h1 className="auth-title">🎉 REGISTRO</h1>
        <p className="auth-subtitle">Únete a la mejor discoteca digital</p>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username" className="form-label">
              👤 Username
            </label>
            <input
              type="text"
              id="username"
              name="username"
              className="form-input"
              placeholder="Tu nombre de DJ"
              value={formData.username}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="email" className="form-label">
              📧 Email
            </label>
            <input
              type="email"
              id="email"
              name="email"
              className="form-input"
              placeholder="tu@email.com"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="tipoUsuario" className="form-label">
              🎭 Tipo de Usuario
            </label>
            <select
              id="tipoUsuario"
              name="tipoUsuario"
              className="form-select"
              value={formData.tipoUsuario}
              onChange={handleChange}
              required
            >
              <option value="usuario_normal">🎵 Usuario Normal</option>
              <option value="dj">🎧 DJ</option>
              <option value="admin">⚙️ Administrador</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">
              🔑 Contraseña
            </label>
            <input
              type="password"
              id="password"
              name="password"
              className="form-input"
              placeholder="••••••••"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword" className="form-label">
              🔒 Confirmar Contraseña
            </label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              className="form-input"
              placeholder="••••••••"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
            />
          </div>

          <button 
            type="submit" 
            className="btn-primary"
            disabled={loading}
          >
            {loading ? '🎵 Creando cuenta...' : '🚀 Unirse a la Discoteca'}
          </button>
        </form>

        <Link href="/login" className="auth-link">
          ¿Ya tienes cuenta? 🎵 Inicia sesión
        </Link>

        <Link href="/" className="btn-secondary">
          🏠 Volver al Inicio
        </Link>
      </div>

      {/* Popup de verificación de email */}
      <PopupVerificacion 
        isOpen={showPopup}
        onClose={handleClosePopup}
        email={formData.email}
      />
    </div>
  );
}
