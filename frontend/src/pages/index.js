// Página de inicio de la aplicación
import BarraNavegacion from '../components/BarraNavegacion';

export default function Home() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Contenido principal de la página de inicio */}
      <div className="home-content">
        <h1 className="home-title">🎵 Bienvenido a Discoteca Online</h1>
        <p className="home-subtitle">Tu plataforma de música favorita</p>
        
        {/* Sección de características principales */}
        <div className="home-features">
          <h2>¿Qué quieres hacer?</h2>
          <p>• Escuchar playlists de tus DJs favoritos</p>
          <p>• Descubrir eventos temáticos</p>
        </div>
      </div>
    </div>
  );
}
