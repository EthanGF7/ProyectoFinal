// Página de inicio de la aplicación
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';
import BarraNavegacion from '../components/BarraNavegacion';

const DJ_PRESETS = ['club', 'latin', 'retro', 'minimal'];

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
          setResidentDjs(payload?.localDjs || []);
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
    return residentDjs.slice(0, 4).map((dj, i) => {
      const name = dj.nombre_artistico || dj.username || 'DJ Invitado';
      const headline = dj.isLocal ? 'DJ local por código' : dj.estilo_musical || dj.estilo_visual || 'Set en vivo';
      const description = dj.bio || 'Escucha sus últimos sets y playlists.';
      const badge = name.trim().charAt(0).toUpperCase() || '🎧';
      const preset = DJ_PRESETS[i % DJ_PRESETS.length];

      return {
        id: dj.id,
        name,
        headline,
        description,
        badge,
        preset,
      };
    });
  }, [residentDjs]);

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="home-main">
        <section className="home-hero">
          <Image src="/logo.png" alt="Namae Nashi" className="home-hero-logo" width={220} height={220} priority />
          <h1 className="home-title">Bienvenido a Namae Nashi</h1>
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
        <section className="home-section">
          <header className="section-header">
            <span className="section-tag tag-purple">DJs residentes</span>
            <h2>Artistas que mantienen la pista encendida</h2>
            <p>Descubre sus estilos, agendas y playlists destacadas.</p>
          </header>

          {djsLoading ? (
              <div className="admin-loading">Iluminando la cabina...</div>
            ) : djsError ? (
              <div className="error-message">{djsError}</div>
            ) : featuredDjs.length === 0 ? (
              <div className="admin-empty">Aún no hay DJs activos. ¡Muy pronto sabrás quién pincha!</div>
            ) : (
              <div className="public-playlist-stack">
                {featuredDjs.map((dj, index) => (
                  <Link
                    key={dj.id}
                    href={`/djs/${dj.id}`}
                    className={`neon-card playlist-visual-card public-playlist-card ${index % 2 === 1 ? 'is-reversed' : ''} visual-${dj.preset}`}
                    onMouseMove={handleCardMouseMove}
                    onMouseEnter={handleCardMouseEnter}
                    onMouseLeave={handleCardMouseLeave}
                    onClick={handleCardClick}
                  >
                    <div className="playlist-visualizer" aria-hidden="true">
                      <span></span>
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <div className="card-content">
                      <div className="public-playlist-main">
                        <span className="playlist-kicker">{dj.headline}</span>
                        <h3>{dj.name}</h3>
                        {dj.description && <p className="playlist-description">{dj.description}</p>}
                      </div>
                      <div className="public-playlist-meta">
                        <span>DJ Residente</span>
                        <strong>{dj.name}</strong>
                        <b>Ver perfil →</b>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
        </section>

        <section className="home-section home-section-highlight">
          <div className="highlight-content">
            <h2>¿No sabes por dónde empezar?</h2>
            <p>
              Explora playlists curadas, arma tu selección personalizada y recibe recomendaciones basadas en tu mood con un par de clics.
            </p>
          </div>
          <div className="highlight-actions">
            <Link
              href="/playlists"
              className="hero-cta hero-cta-tertiary"
              onMouseMove={handleCardMouseMove}
              onMouseLeave={handleCardMouseLeave}
            >
              Explorar playlists
            </Link>
            <Link
              href="/perfil"
              className="hero-cta hero-cta-outline"
              onMouseMove={handleCardMouseMove}
              onMouseLeave={handleCardMouseLeave}
            >
              Abrir tu perfil
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
