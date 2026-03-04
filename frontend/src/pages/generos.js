// Página para explorar playlists por géneros musicales
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaGeneros() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Contenido principal de géneros */}
      <div className="page-content">
        <h1 className="content-title">🎵 Géneros Musicales</h1>
        <p className="content-subtitle">Explora playlists por tu género favorito</p>
        
        {/* Grid de géneros musicales */}
        <div className="grid-3">
          <div className="content-card">
            <h3>🎵 Pop</h3>
            <p>Música popular contemporánea</p>
          </div>
          <div className="content-card">
            <h3>🎸 Rock</h3>
            <p>Rock clásico y moderno</p>
          </div>
          <div className="content-card">
            <h3>🔥 Reggaeton</h3>
            <p>Música urbana latina</p>
          </div>
          <div className="content-card">
            <h3>🎛️ Electronic</h3>
            <p>Música electrónica y EDM</p>
          </div>
          <div className="content-card">
            <h3>🎤 Hip Hop</h3>
            <p>Hip hop y rap</p>
          </div>
          <div className="content-card">
            <h3>🎺 Jazz</h3>
            <p>Jazz clásico y contemporáneo</p>
          </div>
        </div>
      </div>
    </div>
  );
}
