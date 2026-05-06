// Página del panel de administración
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';

const adminSections = [
  {
    title: '👥 Gestión de Usuarios',
    stats: ['Total usuarios: 1,234', 'DJs activos: 45', 'Nuevos registros hoy: 12'],
    link: '/admin#usuarios',
  },
  {
    title: '🎵 Contenido',
    stats: ['Total playlists: 567', 'Canciones subidas: 8,901', 'Reportes pendientes: 3'],
    link: '/admin#contenido',
  },
  {
    title: '🎬 Eventos Temáticos',
    stats: ['Evento activo: Cyberpunk 2077', 'Próximos eventos: 2', 'Crear nuevo evento'],
    link: '/admin#eventos',
  },
  {
    title: '📊 Estadísticas',
    stats: ['Reproducciones hoy: 15,678', 'Usuarios activos: 534', 'Tiempo promedio: 45 min'],
    link: '/admin#estadisticas',
  },
];

export default function PaginaAdmin() {
  const {
    handleCardMouseMove,
    handleCardMouseLeave,
    handleCardMouseEnter,
    handleCardClick,
  } = useNeonCardEffects();

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="neon-main">
        <section className="neon-section">
          <header className="section-header">
            <span className="section-tag tag-purple">Admin</span>
            <h2>Controla la discoteca desde un solo panel</h2>
            <p>Accede a usuarios, contenido, eventos y estadísticas con el mismo look neon que ves en la pista.</p>
          </header>

          <div className="admin-grid">
            {adminSections.map((section) => (
              <Link
                key={section.title}
                href={section.link}
                className="admin-card neon-tile"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <h3>{section.title}</h3>
                  <ul className="dashboard-list">
                    {section.stats.map((stat) => (
                      <li key={stat}>{stat}</li>
                    ))}
                  </ul>
                  <span className="card-link">Administrar →</span>
                </div>
              </Link>
            ))}
          </div>

          <div className="text-secondary admin-note">
            <p>(Funciones avanzadas en desarrollo — estamos afinando la consola neon)</p>
          </div>
        </section>
      </main>
    </div>
  );
}
