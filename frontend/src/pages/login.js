// Página de inicio de sesión
import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { supabase } from '../utils/supabase';
import { syncUserProfile } from '../utils/profileSync';

export default function PaginaLogin() {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const router = useRouter();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError(''); // Limpiar errores al escribir
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // Intentar iniciar sesión con Supabase Auth
      const { data, error } = await supabase.auth.signInWithPassword({
        email: formData.email,
        password: formData.password
      });

      if (error) {
        throw error;
      }

      if (data.user) {
        try {
          await syncUserProfile();
        } catch (syncError) {
          console.warn('No se pudo sincronizar el perfil en el login:', syncError?.message || syncError);
        }

        setSuccess('¡Inicio de sesión exitoso! Redirigiendo...');
        setTimeout(() => {
          router.push('/perfil');
        }, 1500);
      }
    } catch (error) {
      console.error('Error de login:', error);
      setError(error.message || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
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
        <h1 className="auth-title">🎵 LOGIN</h1>
        <p className="auth-subtitle">Accede a la pista de baile digital</p>
        
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}
        
        <form onSubmit={handleSubmit}>
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

          <button 
            type="submit" 
            className="btn-primary"
            disabled={loading}
          >
            {loading ? '🎵 Conectando...' : '🚀 Entrar a la Discoteca'}
          </button>
        </form>

        <Link href="/registro" className="auth-link">
          ¿No tienes cuenta? 🎉 Únete a la fiesta
        </Link>

        <Link href="/" className="btn-secondary">
          🏠 Volver al Inicio
        </Link>
      </div>
    </div>
  );
}
