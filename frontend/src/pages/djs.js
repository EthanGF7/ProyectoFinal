// Página para explorar perfiles de DJs
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaDJs() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Contenido principal de DJs */}
      <div className="page-content">
        <h1 className="content-title">🎧 DJs</h1>
        <p className="content-subtitle">Conoce a nuestros DJs y sus estilos únicos</p>
        
        {/* Grid de perfiles de DJs */}
        <div className="grid-2">
          <div className="content-card">
            <h3>🎵 DJ Pop Master</h3>
            <p>Especialista en música pop y hits actuales</p>
            <p>📊 15 playlists • 1.2K seguidores</p>
          </div>
          <div className="content-card">
            <h3>🎸 DJ Rock Legend</h3>
            <p>El mejor rock clásico y moderno</p>
            <p>📊 8 playlists • 890 seguidores</p>
          </div>
          <div className="content-card">
            <h3>🔥 DJ Latino Fire</h3>
            <p>Reggaeton, trap y música urbana</p>
            <p>📊 12 playlists • 2.1K seguidores</p>
          </div>
          <div className="content-card">
            <h3>🎛️ DJ Electronic Beats</h3>
            <p>Música electrónica y EDM</p>
            <p>📊 20 playlists • 1.8K seguidores</p>
          </div>
        </div>
      </div>
    </div>
  );
}
