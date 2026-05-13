// Página principal del dashboard después del login
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';

const dashboardWidgets = [
  {
    title: '🎵 Tus Playlists Favoritas',
    items: ['Pop Hits 2024', 'Rock Clásico', 'Chill Vibes'],
    link: '/playlists',
  },
  {
    title: '📈 Estadísticas rápidas',
    items: ['45 canciones escuchadas', '12 playlists guardadas', '3 DJs seguidos'],
    link: '/dashboard#estadisticas',
  },
  {
    title: '🎧 Reproduciendo Ahora',
    items: ['Sin reproducción activa', '(Reproductor próximamente)'],
    link: '/dashboard#player',
  },
  {
    title: '🌟 Recomendaciones',
    items: ['Basadas en tu último set', 'Tres nuevas playlists para hoy'],
    link: '/playlists?recommended=true',
  },
];

export default function PaginaDashboard() {
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
            <span className="section-tag">Tu panel</span>
            <h2>Resumen de actividad y accesos rápidos</h2>
            <p>Aquí tienes tus playlists favoritas, estadísticas y accesos a las secciones más usadas.</p>
          </header>

          <div className="dashboard-grid">
            {dashboardWidgets.map((widget) => (
              <Link
                key={widget.title}
                href={widget.link}
                className="dashboard-widget neon-tile"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <h3>{widget.title}</h3>
                  <ul className="dashboard-list">
                    {widget.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <span className="card-link">Abrir sección →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
