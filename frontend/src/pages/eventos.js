// Página de eventos temáticos (películas/series)
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';

const activeEvent = {
  title: 'Beat Battle · Juego de ritmo',
  description: 'Compite pulsando al ritmo, consigue combos y domina la pista con BPM configurables.',
  schedule: 'Evento interactivo · Click, táctil o barra espaciadora',
  action: 'Jugar ahora',
  link: '/eventos/ritmo',
};

const upcomingEvents = [
  {
    title: 'Stranger Things Night',
    description: 'Neón ochentero, arcades retro y sets live de darkwave.',
    date: 'Próximamente · Club Upside',
    link: '/eventos#stranger',
  },
  {
    title: 'Marvel Heroes Weekend',
    description: 'Himnos épicos con proyecciones 360º y cosplay contest.',
    date: 'Próximamente · Sala Quantum',
    link: '/eventos#marvel',
  },
  {
    title: 'Matrix Reloaded Party',
    description: 'Techno industrial, performances acrobáticas y bullet time booth.',
    date: 'Próximamente · Hangar Black',
    link: '/eventos#matrix',
  },
];

export default function PaginaEventos() {
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
            <span className="section-tag">Evento en curso</span>
            <h2>Vive experiencias temáticas inmersivas</h2>
            <p>Cada semana o mes transformamos la discoteca con conceptos exclusivos que solo ocurren una vez.</p>
          </header>

          <Link
            href={activeEvent.link}
            className="neon-card event-active"
            onMouseMove={handleCardMouseMove}
            onMouseEnter={handleCardMouseEnter}
            onMouseLeave={handleCardMouseLeave}
            onClick={handleCardClick}
          >
            <div className="card-content">
              <h3>{activeEvent.title}</h3>
              <p>{activeEvent.description}</p>
              <div className="card-meta">{activeEvent.schedule}</div>
              <span className="card-link">{activeEvent.action} →</span>
            </div>
          </Link>
        </section>

        <section className="neon-section">
          <header className="section-header">
            <span className="section-tag tag-purple">Próximamente</span>
            <h2>Agenda de eventos especiales</h2>
            <p>Haz clic en cada tarjeta para descubrir sorpresas, playlists y reservar tu plaza.</p>
          </header>

          <div className="neon-grid events-grid">
            {upcomingEvents.map((event) => (
              <Link
                key={event.title}
                href={event.link}
                className="neon-card events-card"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <h3>{event.title}</h3>
                  <p>{event.description}</p>
                  <div className="card-meta">{event.date}</div>
                  <span className="card-link">Ver detalles →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
