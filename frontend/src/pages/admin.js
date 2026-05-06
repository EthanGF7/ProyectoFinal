// Página del panel de administración
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaAdmin() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Contenido principal del panel de administración */}
      <div className="page-content">
        <h1 className="content-title">⚙️ Panel de Administración</h1>
        <p className="content-subtitle">Gestiona usuarios, contenido y configuración del sistema</p>
        
        {/* Grid de funciones de administración */}
        <div className="admin-grid">
          <div className="admin-card">
            <h3>👥 Gestión de Usuarios</h3>
            <p>• Total usuarios: 1,234</p>
            <p>• DJs activos: 45</p>
            <p>• Nuevos registros hoy: 12</p>
          </div>
          <div className="admin-card">
            <h3>🎵 Contenido</h3>
            <p>• Total playlists: 567</p>
            <p>• Canciones subidas: 8,901</p>
            <p>• Reportes pendientes: 3</p>
          </div>
          <div className="admin-card">
            <h3>🎬 Eventos Temáticos</h3>
            <p>• Evento activo: Cyberpunk 2077</p>
            <p>• Próximos eventos: 2</p>
            <p>• Configurar nuevo evento</p>
          </div>
          <div className="admin-card">
            <h3>📊 Estadísticas</h3>
            <p>• Reproducciones hoy: 15,678</p>
            <p>• Usuarios activos: 534</p>
            <p>• Tiempo promedio: 45 min</p>
          </div>
        </div>
        
        {/* Nota informativa */}
        <div className="text-secondary">
          <p>(Funciones de administración próximamente)</p>
        </div>
      </div>
    </div>
  );
}
