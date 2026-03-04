// Página para explorar todas las playlists
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaPlaylists() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Contenido principal de playlists */}
      <div className="page-content">
        <h1 className="content-title">🎧 Playlists</h1>
        <p className="content-subtitle">Descubre las mejores playlists de nuestros DJs</p>
        
        {/* Lista de playlists populares */}
        <div className="content-section">
          <h3>Playlists Populares:</h3>
          <p>🎵 Pop Hits 2024 - DJ Ejemplo</p>
          <p>🎸 Rock Clásico - DJ Rock</p>
          <p>🔥 Reggaeton Mix - DJ Latino</p>
          <p>🎛️ Electronic Vibes - DJ Techno</p>
          <p className="help-text">
            (Lista completa próximamente)
          </p>
        </div>
      </div>
    </div>
  );
}
