// Página para explorar playlists por géneros musicales
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';

const genres = [
  {
    id: 'pop-glow',
    emoji: '🎵',
    title: 'Pop Glow',
    description: 'Hits brillantes y coreables para encender la pista.',
    mood: 'Top 40 · Electro Pop · Remix VIP',
    link: '/playlists?genre=pop',
  },
  {
    id: 'rock-stadium',
    emoji: '🎸',
    title: 'Rock Stadium',
    description: 'Guitarras distorsionadas con toques synth y solos épicos.',
    mood: 'Indie · Classic Rock · Darkwave',
    link: '/playlists?genre=rock',
  },
  {
    id: 'reggaeton-fiesta',
    emoji: '🔥',
    title: 'Reggaeton Fiesta',
    description: 'Percusiones latinas con bajos electrónicos y drops explosivos.',
    mood: 'Perreo · Dembow · Latin Bass',
    link: '/playlists?genre=reggaeton',
  },
  {
    id: 'edm-universe',
    emoji: '🎛️',
    title: 'EDM Universe',
    description: 'Progresivo, future house y big room con drops luminosos.',
    mood: 'Festival · Future House · Trance',
    link: '/playlists?genre=edm',
  },
  {
    id: 'hiphop-neon',
    emoji: '🎤',
    title: 'Hip Hop Neon',
    description: 'Beats urbanos con capas synth y flows futuristas.',
    mood: 'Trap · Boom Bap · Drillwave',
    link: '/playlists?genre=hiphop',
  },
  {
    id: 'jazz-lounge',
    emoji: '🎺',
    title: 'Jazz Lounge 2AM',
    description: 'Improvisación suave con toques electrónicos y groove nocturno.',
    mood: 'Smooth Jazz · Nu Jazz · Chillhop',
    link: '/playlists?genre=jazz',
  },
];

const curatedMoments = [
  {
    title: 'Sunrise After Party',
    description: 'Downtempo, lo-fi house y melodías para ver amanecer desde la terraza.',
    link: '/playlists?mood=sunrise',
  },
  {
    title: 'Basement Rave',
    description: 'Techno hipnótico, acid lines y luces estroboscópicas.',
    link: '/playlists?mood=basement',
  },
  {
    title: 'Velvet Cocktail',
    description: 'Neo-soul, R&B alternativo y beats sensuales para charlar.',
    link: '/playlists?mood=velvet',
  },
];

export default function PaginaGeneros() {
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
            <span className="section-tag">Tu soundtrack</span>
            <h2>Escoge el género que marca tu noche</h2>
            <p>Cada tarjeta abre playlists seleccionadas por nuestros DJs residentes con mezclas en exclusiva.</p>
          </header>

          <div className="neon-grid genre-grid">
            {genres.map((genre) => (
              <Link
                key={genre.id}
                href={genre.link}
                className="neon-card genre-card"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <div className="genre-badge">{genre.emoji}</div>
                  <h3>{genre.title}</h3>
                  <p>{genre.description}</p>
                  <div className="card-meta">{genre.mood}</div>
                  <span className="card-link">Explorar playlists →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="neon-section neon-section-highlight">
          <div className="highlight-content">
            <h2>Sets curados para cada momento</h2>
            <p>
              Además de los géneros clásicos, descubre colecciones pensadas para vibes muy concretas.
            </p>
          </div>
          <div className="highlight-actions curated-grid">
            {curatedMoments.map((moment) => (
              <Link
                key={moment.title}
                href={moment.link}
                className="neon-card curated-card"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <h3>{moment.title}</h3>
                  <p>{moment.description}</p>
                  <span className="card-link">Escuchar ahora →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
