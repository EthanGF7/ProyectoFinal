// Página principal del dashboard después del login
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaDashboard() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Contenido principal del dashboard */}
      <div className="page-content">
        <h1 className="content-title">📊 Dashboard</h1>
        <p className="content-subtitle">Bienvenido a tu panel personal</p>
        
        {/* Grid de widgets del dashboard */}
        <div className="dashboard-grid">
          <div className="dashboard-widget">
            <h3>🎵 Tus Playlists Favoritas</h3>
            <p>• Pop Hits 2024</p>
            <p>• Rock Clásico</p>
            <p>• Chill Vibes</p>
          </div>
          <div className="dashboard-widget">
            <h3>📈 Estadísticas</h3>
            <p>• 45 canciones escuchadas</p>
            <p>• 12 playlists guardadas</p>
            <p>• 3 DJs seguidos</p>
          </div>
          <div className="dashboard-widget">
            <h3>🎧 Reproduciendo Ahora</h3>
            <p>Ninguna canción reproduciéndose</p>
            <p className="help-text">(Reproductor próximamente)</p>
          </div>
          <div className="dashboard-widget">
            <h3>🤖 Última Recomendación</h3>
            <p>El chatbot te recomendó:</p>
            <p>"Electronic Vibes" para tu estado energético</p>
          </div>
        </div>
      </div>
    </div>
  );
}
