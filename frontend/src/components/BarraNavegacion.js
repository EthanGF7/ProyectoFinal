// Componente de la barra de navegación principal
import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { supabase } from '../utils/supabase';
import { useAppUser } from '../hooks/useAppUser';

export default function BarraNavegacion() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const { appUser, supabaseUser } = useAppUser();

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
          <Image src="/logo.png" alt="Discoteca Online" className="navbar-logo-image" width={78} height={78} />
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
          <>
            <Link href="/perfil" className="navbar-link">
              👤 Perfil
            </Link>
            {(appUser?.tipo_usuario === 'dj' || supabaseUser?.user_metadata?.tipo_usuario === 'dj') && (
              <Link href="/dj" className="navbar-link">
                🎧 Panel DJ
              </Link>
            )}
            {(appUser?.tipo_usuario === 'admin' || supabaseUser?.user_metadata?.tipo_usuario === 'admin') && (
              <Link href="/admin" className="navbar-link">
                🛠️ Admin
              </Link>
            )}
          </>
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
