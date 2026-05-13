// Página de inicio de la aplicación
import Link from 'next/link';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';
import BarraNavegacion from '../components/BarraNavegacion';

const upcomingEvents = [
  {
    title: 'Noche Retro Wave',
    date: 'Viernes 12 Julio',
    location: 'Sala Prisma',
    description: 'Luces neón, synthwave en directo y sets visuales 80s.',
    link: '/eventos#retro-wave',
  },
  {
    title: 'Glow House Experience',
    date: 'Sábado 20 Julio',
    location: 'Club Aurora',
    description: 'Line-up house/tech-house con pista fluorescente y live visuals.',
    link: '/eventos#glow-house',
  },
  {
    title: 'Electro Latin Fest',
    date: 'Viernes 26 Julio',
    location: 'Terraza Solaris',
    description: 'Fusión electrónica + ritmos latinos al aire libre.',
    link: '/eventos#electro-latin',
  },
];

const featuredDJs = [
  {
    name: 'Luna Vega',
    genre: 'House Progresivo',
    description: 'Sets con melodías espaciales y drops envolventes.',
    link: '/djs#luna-vega',
  },
  {
    name: 'DJ Prisma',
    genre: 'Synthwave & Future Funk',
    description: 'Remixes cargados de nostalgia y visuales en 3D.',
    link: '/djs#dj-prisma',
  },
  {
    name: 'Kora Beat',
    genre: 'Afrohouse & Latin Bass',
    description: 'Ritmos híbridos con percusiones tribales y groove.',
    link: '/djs#kora-beat',
  },
];

export default function Home() {
  const {
    handleCardMouseMove,
    handleCardMouseLeave,
    handleCardMouseEnter,
    handleCardClick,
  } = useNeonCardEffects();

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="home-main">
        <section className="home-hero">
          <div className="hero-badge">Vibes nocturnas · 24/7</div>
          <h1 className="home-title">Bienvenido a Discoteca Online</h1>
          <p className="home-subtitle">
            Sintoniza sets exclusivos, descubre nuevos DJs y reserva tu lugar en los próximos eventos.
          </p>

          <div className="hero-actions">
            <Link
              href="/playlists"
              className="hero-cta hero-cta-primary"
              onMouseMove={handleCardMouseMove}
              onMouseLeave={handleCardMouseLeave}
            >
              ▶️ Explorar Playlists
            </Link>
            <Link
              href="/registro"
              className="hero-cta hero-cta-secondary"
              onMouseMove={handleCardMouseMove}
              onMouseLeave={handleCardMouseLeave}
            >
              ✨ Únete a la comunidad
            </Link>
          </div>
        </section>

        <section className="home-section home-section-events">
          <header className="section-header">
            <span className="section-tag">Próximos eventos</span>
            <h2>Luces, pista y ritmos en la agenda</h2>
            <p>Haz clic en cada tarjeta para ver la programación completa y asegurar tu spot.</p>
          </header>

          <div className="home-grid events-grid">
            {upcomingEvents.map((event) => (
              <Link
                key={event.title}
                href={event.link}
                className="home-card event-card"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <div className="card-date">{event.date}</div>
                  <h3>{event.title}</h3>
                  <p>{event.description}</p>
                  <div className="card-meta">📍 {event.location}</div>
                  <span className="card-link">Ver detalles →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="home-section">
          <header className="section-header">
            <span className="section-tag tag-purple">DJs residentes</span>
            <h2>Artistas que mantienen la pista encendida</h2>
            <p>Descubre sus estilos, agendas y playlists destacadas.</p>
          </header>

          <div className="home-grid dj-grid">
            {featuredDJs.map((dj) => (
              <Link
                key={dj.name}
                href={dj.link}
                className="home-card dj-card"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <div className="card-avatar" aria-hidden="true">
                    <span>{dj.name.split(' ')[0]}</span>
                  </div>
                  <h3>{dj.name}</h3>
                  <p>{dj.description}</p>
                  <div className="card-meta">🎶 {dj.genre}</div>
                  <span className="card-link">Escuchar set →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="home-section home-section-highlight">
          <div className="highlight-content">
            <h2>¿No sabes por dónde empezar?</h2>
            <p>
              Explora géneros, arma tu playlist personalizada y recibe recomendaciones basadas en tu mood con un par de clics.
            </p>
          </div>
          <div className="highlight-actions">
            <Link
              href="/generos"
              className="hero-cta hero-cta-tertiary"
              onMouseMove={handleCardMouseMove}
              onMouseLeave={handleCardMouseLeave}
            >
              Ver géneros musicales
            </Link>
            <Link
              href="/dashboard"
              className="hero-cta hero-cta-outline"
              onMouseMove={handleCardMouseMove}
              onMouseLeave={handleCardMouseLeave}
            >
              Abrir tu dashboard
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
