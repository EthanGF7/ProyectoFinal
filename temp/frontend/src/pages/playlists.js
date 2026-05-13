// Página para explorar todas las playlists
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';

const spotlightPlaylists = [
  {
    title: 'Pulse Pop 2024',
    description: 'Las canciones más coreadas del momento con remixes exclusivos.',
    length: '45 canciones · 2h 30m',
    link: '/playlists/pulse-pop',
  },
  {
    title: 'Neon Tech Odyssey',
    description: 'Tech house con subgraves vibrantes y builds interminables.',
    length: '38 canciones · 2h 05m',
    link: '/playlists/neon-tech',
  },
  {
    title: 'Retro Groove Memories',
    description: 'Funk y synthwave con selecciones de vinilo digitalizadas.',
    length: '52 canciones · 3h 10m',
    link: '/playlists/retro-groove',
  },
];

const collections = [
  {
    heading: 'Mood Boost',
    playlists: [
      'Sunset Chillwave',
      'Feel Good Pop',
      'Morning Disco Coffee',
    ],
  },
  {
    heading: 'Club Essentials',
    playlists: [
      'Bassline Essentials',
      'Glow House Anthems',
      'Afterhours Stories',
    ],
  },
  {
    heading: 'Experiencias',
    playlists: [
      'Cyberpunk Night Ride',
      'Latin Bass Carnival',
      'Velvet Cocktail Lounge',
    ],
  },
];

export default function PaginaPlaylists() {
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
            <span className="section-tag">Sesiones destacadas</span>
            <h2>Playlists curadas para activar cada momento</h2>
            <p>
              Descubre selecciones hechas por nuestros DJs para calentar la noche, subir la energía o bajar revoluciones.
            </p>
          </header>

          <div className="neon-grid">
            {spotlightPlaylists.map((playlist) => (
              <Link
                key={playlist.title}
                href={playlist.link}
                className="neon-card playlist-card"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
                onClick={handleCardClick}
              >
                <div className="card-content">
                  <h3>{playlist.title}</h3>
                  <p>{playlist.description}</p>
                  <div className="card-meta">{playlist.length}</div>
                  <span className="card-link">Abrir playlist →</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="neon-section">
          <header className="section-header">
            <span className="section-tag tag-purple">Colecciones</span>
            <h2>Elige la vibra y deja que el set fluya</h2>
            <p>Combina playlists según tu mood o evento; cada colección tiene transiciones pensadas para mezclar sin cortes.</p>
          </header>

          <div className="neon-grid playlist-collections">
            {collections.map((collection) => (
              <div
                key={collection.heading}
                className="neon-card neon-tile"
                onMouseMove={handleCardMouseMove}
                onMouseEnter={handleCardMouseEnter}
                onMouseLeave={handleCardMouseLeave}
              >
                <div className="card-content">
                  <h3>{collection.heading}</h3>
                  <ul className="playlist-list">
                    {collection.playlists.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <span className="card-link">Ver todas →</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
