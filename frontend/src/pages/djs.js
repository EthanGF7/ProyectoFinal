// Página para explorar perfiles de DJs
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';

const djs = [
  {
    id: 'luna-vega',
    emoji: '🌙',
    name: 'Luna Vega',
    tagline: 'Progressive house etéreo',
    bio: 'Sets con pads envolventes, voces celestiales y drops que suben lentamente.',
    stats: '18 playlists · 2.4K seguidores',
    link: '/djs#luna-vega',
  },
  {
    id: 'prisma',
    emoji: '🔮',
    name: 'DJ Prisma',
    tagline: 'Synthwave / Future Funk',
    bio: 'Remixes retrofuturistas con visuales 3D que sincronizan con cada beat.',
    stats: '22 playlists · 3.1K seguidores',
    link: '/djs#dj-prisma',
  },
  {
    id: 'kora-beat',
    emoji: '🪘',
    name: 'Kora Beat',
    tagline: 'Afrohouse & Latin Bass',
    bio: 'Percusiones tribales con bajos densos para no parar de bailar.',
    stats: '16 playlists · 2.8K seguidores',
    link: '/djs#kora-beat',
  },
  {
    id: 'arcanum',
    emoji: '⚡',
    name: 'Arcana Pulse',
    tagline: 'Techno hipnótico',
    bio: 'Capas industriales, vocal chops distorsionados y finales de sets explosivos.',
    stats: '14 playlists · 1.6K seguidores',
    link: '/djs#arcana-pulse',
  },
];

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
            <span className="section-tag tag-purple">Artistas</span>
            <h2>Conoce a los DJs que mantienen la pista encendida</h2>
            <p>
              Cada dj crea sets exclusivos para la discoteca y comparte su energía en los eventos especiales.
            </p>
          </header>

          <div className="neon-grid dj-profiles">
            {djs.map((dj) => (
              <Link
                key={dj.id}
                href={dj.link}
                className="neon-card dj-card"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <div className="dj-badge">{dj.emoji}</div>
                  <h3>{dj.name}</h3>
                  <div className="card-meta">{dj.tagline}</div>
                  <p>{dj.bio}</p>
                  <span className="dj-stats">{dj.stats}</span>
                  <span className="card-link">Ver perfil →</span>
                </div>
              </Link>
            ))}
          </div>
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
