// Página principal del dashboard después del login
import { useMemo } from 'react';
import Link from 'next/link';
import BarraNavegacion from '../components/BarraNavegacion';
import { useNeonCardEffects } from '../hooks/useNeonCardEffects';
import { useAppUser } from '../hooks/useAppUser';
import { useListenHistory } from '../hooks/useListenHistory';

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
  const { appUser, loading: userLoading } = useAppUser();
  const isLogged = Boolean(appUser);

  const {
    history: listenHistory,
    loading: historyLoading,
    error: historyError,
    refresh: refreshHistory,
    stats: historyStats,
  } = useListenHistory({ enabled: isLogged, limit: 8 });

  const mergedStats = useMemo(() => {
    if (historyStats?.topDj) return historyStats;

    const uniqueDjs = new Map();
    listenHistory.forEach((item) => {
      if (!item) return;
      const key = item.dj_id || item.dj_name || 'desconocido';
      const name = item.dj_name || 'DJ desconocido';
      const current = uniqueDjs.get(key) || { name, count: 0 };
      current.count += 1;
      uniqueDjs.set(key, current);
    });

    if (uniqueDjs.size === 0) {
      return {
        ...historyStats,
        topDj: null,
      };
    }

    const [topDjKey, topDjValue] = [...uniqueDjs.entries()].sort((a, b) => b[1].count - a[1].count)[0];
    return {
      ...historyStats,
      topDj: { id: topDjKey, ...topDjValue },
    };
  }, [historyStats, listenHistory]);

  const recentTracks = useMemo(() => listenHistory.slice(0, 4), [listenHistory]);

  const personalWidgets = useMemo(() => {
    if (!isLogged) return [];

    const recentItems = historyLoading
      ? ['Cargando últimas escuchas...']
      : historyError
        ? [historyError]
        : recentTracks.length === 0
          ? ['No tienes reproducciones registradas todavía.']
          : recentTracks.map((item) => {
              const track = item?.track_name || 'Track sin título';
              const dj = item?.dj_name || 'DJ desconocido';
              const timestamp = item?.listened_at
                ? new Date(item.listened_at).toLocaleString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit',
                    day: '2-digit',
                    month: 'short',
                  })
                : '';
              return `${track} · ${dj}${timestamp ? ` · ${timestamp}` : ''}`;
            });

    const statsItems = historyLoading
      ? ['Preparando estadísticas...']
      : [
          `${mergedStats.total ?? 0} canciones registradas`,
          `${mergedStats.uniqueDjs ?? 0} DJs diferentes`,
          mergedStats.topDj
            ? `Más repetido: ${mergedStats.topDj.name} (${mergedStats.topDj.count})`
            : 'Aún sin DJ destacado',
        ];

    return [
      {
        title: '🎧 Tus últimas sesiones',
        items: recentItems,
        link: '/perfil#historial-reciente',
      },
      {
        title: '📊 Resumen de escuchas',
        items: statsItems,
        link: '/perfil#panel-actividad',
      },
    ];
  }, [historyError, historyLoading, mergedStats, isLogged, recentTracks]);

  const composedWidgets = useMemo(() => {
    if (!isLogged) return dashboardWidgets;
    return [...personalWidgets, ...dashboardWidgets];
  }, [isLogged, personalWidgets]);

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

          {isLogged && (
            <div className="dashboard-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={refreshHistory}
                disabled={historyLoading}
              >
                {historyLoading ? 'Actualizando historial...' : 'Actualizar historial'}
              </button>
              {historyError && !historyLoading && (
                <span className="dashboard-error">{historyError}</span>
              )}
            </div>
          )}

          {!isLogged && !userLoading && (
            <div className="dashboard-empty">
              <p>
                Inicia sesión para ver tu actividad reciente y estadísticas personalizadas. Mientras tanto, explora las
                secciones destacadas.
              </p>
            </div>
          )}

          <div className="dashboard-grid">
            {composedWidgets.map((widget) => (
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
