// Página para explorar perfiles de DJs
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';

const residencies = [
  {
    title: 'Glow House Fridays',
    description: 'Residencia semanal con colaboraciones en vivo y sets B2B sorpresa.',
    link: '/eventos#glow-house',
  },
  {
    title: 'Noches Retro Wave',
    description: 'Lineup rotativo de synthwave con visuales VHS y challengers retro.',
    link: '/eventos#retro-wave',
  },
];

export default function PaginaDJs() {
  const [djs, setDjs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const {
    handleCardMouseMove,
    handleCardMouseLeave,
    handleCardMouseEnter,
    handleCardClick,
  } = useNeonCardEffects();

  useEffect(() => {
    const loadDjs = async () => {
      try {
        setLoading(true);
        setError('');
        fetch('/api/djs/autostart', { method: 'POST' }).catch((err) => {
          console.warn('[djs] No se pudieron arrancar automáticamente los DJs:', err);
        });
        const response = await fetch('/api/djs');
        if (!response.ok) {
          throw new Error('No se pudieron cargar los DJs.');
        }
        const payload = await response.json();
        setDjs(payload.djs || []);
      } catch (err) {
        console.error('[djs] Error cargando DJs:', err);
        setError(err.message || 'No se pudieron cargar los DJs');
      } finally {
        setLoading(false);
      }
    };

    loadDjs();
  }, []);

  const preparedDjs = useMemo(() => {
    return (djs || []).map((dj) => {
      const badge = dj.nombre_artistico?.[0]?.toUpperCase() || '🎧';
      let activoDesde = null;
      if (dj.created_at) {
        const parsed = new Date(dj.created_at);
        if (!Number.isNaN(parsed.getTime())) {
          activoDesde = parsed.toLocaleDateString('es-ES', {
            month: 'short',
            year: 'numeric',
          });
        }
      }

      const headlineParts = [dj.estilo_musical, dj.estilo_visual].filter(Boolean);

      return {
        ...dj,
        badge,
        activoDesde,
        headline: headlineParts.join(' · '),
        profileUrl: `/djs/${dj.id}`,
      };
    });
  }, [djs]);

  return (
    <div className="page-container">
      <BarraNavegacion />

      <main className="neon-main">
        <section className="neon-section">
          <header className="section-header">
            <span className="section-tag tag-purple">Artistas</span>
            <h2>Conoce a los DJs que mantienen la pista encendida</h2>
            <p>
              Cada dj crea sets exclusivos para la discoteca y comparte su energía en los eventos especiales.
            </p>
          </header>

          {loading ? (
            <div className="admin-loading">
              <div className="loading-spinner"></div>
              <p>Iluminando la cabina...</p>
            </div>
          ) : error ? (
            <div className="error-message">{error}</div>
          ) : preparedDjs.length === 0 ? (
            <div className="admin-empty">Aún no hay DJs activos. ¡Pronto llegará el primer line-up!</div>
          ) : (
            <div className="neon-grid dj-profiles">
              {preparedDjs.map((dj) => (
                <Link
                  key={dj.id}
                  href={dj.profileUrl}
                  className="neon-card dj-card"
                  onMouseMove={handleCardMouseMove}
                  onMouseEnter={handleCardMouseEnter}
                  onMouseLeave={handleCardMouseLeave}
                  onClick={handleCardClick}
                >
                  <div className="card-content">
                    <div className="dj-badge">{dj.badge}</div>
                    <h3>{dj.nombre_artistico}</h3>
                    {dj.headline && <div className="card-meta">{dj.headline}</div>}
                    {dj.bio && <p>{dj.bio}</p>}
                    <p className="chip">Playlists destacadas: {dj.playlists_count || 0}</p>
                    {dj.activoDesde && <span className="dj-stats">Activo desde {dj.activoDesde}</span>}
                    <span className="card-link">Ver perfil →</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="neon-section">
          <header className="section-header">
            <span className="section-tag">Residencias</span>
            <h2>Noches fijas donde podrás encontrarlos</h2>
            <p>Reserva tu entrada y prepárate para pistas iluminadas, visuales envolventes y sets sorpresa.</p>
          </header>

          <div className="highlight-actions curated-grid">
            {residencies.map((item) => (
              <Link
                key={item.title}
                href={item.link}
                className="neon-card curated-card"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                  <span className="card-link">Ver programación →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
