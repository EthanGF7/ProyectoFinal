// Componente de la barra de navegación principal
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { supabase } from '../utils/supabase';

export default function BarraNavegacion() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkUser();
    
    // Escuchar cambios en el estado de autenticación
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => authListener?.subscription?.unsubscribe();
  }, []);

  const checkUser = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
    } catch (error) {
      console.error('Error al verificar usuario:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <nav className="navbar">
      {/* Logo y título de la aplicación */}
      <div>
        <Link href="/" className="navbar-logo">
          🎵 Discoteca Online
        </Link>
      </div>
      
      {/* Menú principal de navegación */}
      <div className="navbar-menu">
        <Link href="/" className="navbar-link">
          Inicio
        </Link>
        <Link href="/playlists" className="navbar-link">
          Playlists
        </Link>
        <Link href="/generos" className="navbar-link">
          Géneros
        </Link>
        <Link href="/djs" className="navbar-link">
          DJs
        </Link>
        <Link href="/eventos" className="navbar-link">
          Eventos
        </Link>
      </div>

      {/* Enlaces de autenticación */}
      <div className="navbar-auth">
        {loading ? (
          <span className="navbar-placeholder" aria-hidden="true">&nbsp;</span>
        ) : user ? (
          // Usuario autenticado - mostrar solo perfil
          <Link href="/perfil" className="navbar-link">
            👤 Perfil
          </Link>
        ) : (
          // Usuario no autenticado - mostrar login y registro
          <>
            <Link href="/login" className="navbar-login">
              Iniciar Sesión
            </Link>
            <Link href="/registro" className="navbar-register">
              Registrarse
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
