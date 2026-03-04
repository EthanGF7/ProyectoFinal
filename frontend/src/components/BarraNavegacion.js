// Componente de la barra de navegación principal
import Link from 'next/link';

export default function BarraNavegacion() {
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
        <Link href="/chatbot" className="navbar-link">
          Chatbot
        </Link>
        <Link href="/eventos" className="navbar-link">
          Eventos
        </Link>
      </div>

      {/* Botones de autenticación */}
      <div className="navbar-auth">
        <Link href="/login" className="navbar-login">
          Login
        </Link>
        <Link href="/registro" className="navbar-register">
          Registro
        </Link>
      </div>
    </nav>
  );
}
