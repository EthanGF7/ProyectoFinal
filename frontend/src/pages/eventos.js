// Página de eventos temáticos (películas/series)
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaEventos() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Contenido principal de eventos */}
      <div className="page-content">
        <h1 className="content-title">🎬 Eventos Temáticos</h1>
        <p className="content-subtitle">Eventos especiales inspirados en películas y series</p>
        
        <div className="content-section">
          {/* Evento activo destacado */}
          <div className="event-active">
            <h3>🌆 EVENTO ACTIVO: Cyberpunk 2077</h3>
            <p>Sumérgete en el futuro distópico con synthwave y techno</p>
            <p>📅 10-17 Mayo 2024</p>
            <p>🎵 Playlists especiales disponibles</p>
          </div>
          
          {/* Próximos eventos */}
          <div className="events-upcoming">
            <h3>Próximos Eventos:</h3>
            <div className="grid-2">
              <div className="content-card">
                <h4>🔮 Stranger Things Night</h4>
                <p>Viaje a los 80s con música retro</p>
                <p>📅 Próximamente</p>
              </div>
              <div className="content-card">
                <h4>⚡ Marvel Heroes Weekend</h4>
                <p>Música épica y heroica</p>
                <p>📅 Próximamente</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
