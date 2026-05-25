// Página de inicio de la aplicación
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';
import { useAppUser } from '../hooks/useAppUser';
import { useListenHistory } from '../hooks/useListenHistory';
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

export default function Home() {
  const {
    handleCardMouseMove,
    handleCardMouseLeave,
    handleCardMouseEnter,
    handleCardClick,
  } = useNeonCardEffects();

  const [residentDjs, setResidentDjs] = useState([]);
  const [djsLoading, setDjsLoading] = useState(true);
  const [djsError, setDjsError] = useState(null);
  const { appUser } = useAppUser();
  const isLogged = Boolean(appUser);

  const {
    history: listenHistory,
    loading: historyLoading,
    error: historyError,
    stats: historyStats,
  } = useListenHistory({ enabled: isLogged, limit: 5 });

  const lastListen = listenHistory[0] || null;
  const secondaryListens = listenHistory.slice(1, 4);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const loadDjs = async () => {
      try {
        setDjsLoading(true);
        setDjsError(null);

        const response = await fetch('/api/djs', { signal: controller.signal });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error(payload?.error || 'No se pudieron cargar los DJs');
        }

        const payload = await response.json();
        if (isMounted) {
          setResidentDjs(payload?.djs || []);
        }
      } catch (error) {
        if (!controller.signal.aborted && isMounted) {
          setDjsError(error.message || 'No se pudieron cargar los DJs');
        }
      } finally {
        if (isMounted) {
          setDjsLoading(false);
        }
      }
    };

    loadDjs();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  const featuredDjs = useMemo(() => {
    return residentDjs.slice(0, 4).map((dj) => {
      const name = dj.nombre_artistico || dj.username || 'DJ Invitado';
      const headline = dj.estilo_musical || dj.estilo_visual || 'Set en vivo';
      const description = dj.bio || 'Escucha sus últimos sets y playlists.';
      const badge = name.trim().charAt(0).toUpperCase() || '🎧';

      return {
        id: dj.id,
        name,
        headline,
        description,
        badge,
      };
    });
  }, [residentDjs]);

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="home-main">
        <section className="home-hero">
          <Image src="/logo.png" alt="Discoteca Online" className="home-hero-logo" width={220} height={220} priority />
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

        {isLogged && (
          <section className="home-section home-section-personal">
            <header className="section-header">
              <span className="section-tag tag-cyan">Tu actividad</span>
              <h2>Retoma tu última sesión</h2>
              <p>Revisa lo que escuchaste recientemente y vuelve al panel para seguir mezclando.</p>
            </header>

            <div className="home-grid personal-grid">
              <div className="home-card personal-card">
                <div className="card-content">
                  {historyLoading ? (
                    <p className="personal-placeholder">Cargando historial personal...</p>
                  ) : historyError ? (
                    <p className="personal-placeholder">{historyError}</p>
                  ) : !lastListen ? (
                    <p className="personal-placeholder">
                      Aún no registramos sesiones. Lanza la cabina desde tu perfil y las verás aquí.
                    </p>
                  ) : (
                    <>
                      <div className="personal-now-playing">
                        <span className="personal-label">Última reproducción</span>
                        <h3>{lastListen.track_name || 'Track sin título'}</h3>
                        <p className="personal-meta">
                          {lastListen.dj_name || 'DJ desconocido'} ·{' '}
                          {new Date(lastListen.listened_at).toLocaleString('es-ES', {
                            hour: '2-digit',
                            minute: '2-digit',
                            day: '2-digit',
                            month: 'short',
                          })}
                        </p>
                      </div>

                      {secondaryListens.length > 0 && (
                        <ul className="personal-history-list">
                          {secondaryListens.map((item) => (
                            <li key={item.id || item.listened_at}>
                              <span className="personal-track">{item.track_name || 'Track sin título'}</span>
                              <span className="personal-meta">
                                {item.dj_name || 'DJ desconocido'} ·{' '}
                                {new Date(item.listened_at).toLocaleString('es-ES', {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  day: '2-digit',
                                  month: 'short',
                                })}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}

                      <div className="personal-actions">
                        <Link href="/perfil#panel-actividad" className="hero-cta hero-cta-outline">
                          Ver panel de actividad
                        </Link>
                        <span className="personal-stat">
                          Guardamos {historyStats.total} canciones · {historyStats.uniqueDjs} DJs distintos
                        </span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

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
            {djsLoading ? (
              <div className="admin-loading">Iluminando la cabina...</div>
            ) : djsError ? (
              <div className="error-message">{djsError}</div>
            ) : featuredDjs.length === 0 ? (
              <div className="admin-empty">Aún no hay DJs activos. ¡Muy pronto sabrás quién pincha!</div>
            ) : (
              featuredDjs.map((dj) => (
                <Link
                  key={dj.id}
                  href={`/djs/${dj.id}`}
                  className="home-card dj-card"
                  onMouseMove={handleCardMouseMove}
                  onMouseEnter={handleCardMouseEnter}
                  onMouseLeave={handleCardMouseLeave}
                  onClick={handleCardClick}
                >
                  <div className="card-content">
                    <div className="card-avatar" aria-hidden="true">
                      <span>{dj.badge}</span>
                    </div>
                    <h3>{dj.name}</h3>
                    <p>{dj.description}</p>
                    <div className="card-meta">🎶 {dj.headline}</div>
                    <span className="card-link">Ver perfil →</span>
                  </div>
                </Link>
              ))
            )}
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
