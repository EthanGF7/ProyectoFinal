import { getAuthenticatedUser } from '../../../utils/apiAuth';
import { supabaseAdmin } from '../../../utils/supabaseAdmin';

const TABLE_NAME = 'user_listen_history';
const LEGACY_TABLE_NAME = 'historial_reproducciones';

const sanitizeText = (value, maxLength = 160) => {
  if (typeof value !== 'string') return null;
  return value.slice(0, maxLength);
};

const parseQueryValue = (value) => {
  if (!value) return undefined;
  if (Array.isArray(value)) return value[0];
  return value;
};

const parseLimit = (value) => {
  const num = parseInt(value, 10);
  if (Number.isNaN(num) || num <= 0) return 10;
  return Math.min(num, 50);
};

const buildStats = (history) => {
  const djCounts = new Map();
  history.forEach((item) => {
    const key = item.dj_id || item.dj_name || 'desconocido';
    const current = djCounts.get(key) || { id: key, name: item.dj_name || key, count: 0 };
    current.count += 1;
    djCounts.set(key, current);
  });
  const topDj = [...djCounts.values()].sort((a, b) => b.count - a.count)[0] || null;
  const lastPlaylist = history.find((entry) => entry?.playlist_name) || null;
  return {
    total: history.length,
    uniqueDjs: djCounts.size,
    lastListen: history[0] || null,
    topDj,
    lastPlaylist,
  };
};

const fetchListenHistory = async ({ possibleUserIds, limit, djIdParam }) => {
  let query = supabaseAdmin
    .from(TABLE_NAME)
    .select('id, dj_id, dj_name, playlist_id, playlist_name, track_name, listened_at')
    .in('user_id', possibleUserIds)
    .order('listened_at', { ascending: false })
    .limit(limit);

  if (djIdParam) {
    query = query.eq('dj_id', djIdParam);
  }

  const { data, error } = await query;
  if (!error && data?.length) {
    return { history: data };
  }

  if (error && error?.code !== '42P01') {
    return { error };
  }

  const { data: legacyData, error: legacyError } = await supabaseAdmin
    .from(LEGACY_TABLE_NAME)
    .select('id, user_id, cancion_id, playlist_id, reproducido_en')
    .in('user_id', possibleUserIds)
    .order('reproducido_en', { ascending: false })
    .limit(limit);

  if (!legacyError && legacyData?.length) {
    return {
      history: legacyData.map((item) => ({
        id: item.id,
        dj_id: null,
        dj_name: null,
        playlist_id: item.playlist_id,
        playlist_name: item.playlist_id,
        track_name: item.cancion_id,
        listened_at: item.reproducido_en,
      })),
    };
  }

  if (legacyError && legacyError?.code !== '42P01') {
    return { error: legacyError };
  }

  const { data: latestData, error: latestError } = await supabaseAdmin
    .from(TABLE_NAME)
    .select('id, dj_id, dj_name, playlist_id, playlist_name, track_name, listened_at')
    .order('listened_at', { ascending: false })
    .limit(limit);

  if (!latestError && latestData?.length) {
    return { history: latestData };
  }

  if (latestError && latestError?.code !== '42P01') {
    return { error: latestError };
  }

  return { history: data || [] };
};

export default async function handler(req, res) {
  try {
    const { user, appUser, error } = await getAuthenticatedUser(req);
    if (error) {
      return res.status(401).json({ error });
    }

    const userId = appUser?.id || user?.id;
    const possibleUserIds = [...new Set([appUser?.id, user?.id].filter(Boolean))];
    if (!userId) {
      return res.status(400).json({ error: 'No se pudo determinar el usuario autenticado' });
    }

    if (req.method === 'GET') {
      const limitParam = parseQueryValue(req.query?.limit);
      const djIdParam = parseQueryValue(req.query?.djId);
      const limit = parseLimit(limitParam);

      const { history: fetchedHistory, error: fetchError } = await fetchListenHistory({
        possibleUserIds,
        limit,
        djIdParam,
      });

      if (fetchError) {
        console.error('[listen-history] Error al obtener historial:', fetchError);
        return res.status(500).json({ error: 'No se pudo obtener el historial de escuchas' });
      }

      let history = fetchedHistory || [];

      if (history.length === 0) {
        const { data: reactions } = await supabaseAdmin
          .from('track_reactions')
          .select('id, dj_id, dj_name, track_name, updated_at')
          .in('user_id', possibleUserIds)
          .order('updated_at', { ascending: false })
          .limit(limit);

        history = (reactions || []).map((item) => ({
          id: item.id,
          dj_id: item.dj_id,
          dj_name: item.dj_name || item.dj_id,
          playlist_id: null,
          playlist_name: null,
          track_name: item.track_name,
          listened_at: item.updated_at,
        }));
      }

      const stats = buildStats(history);

      return res.status(200).json({ history, stats });
    }

    if (req.method === 'POST') {
      const body = typeof req.body === 'object' && req.body !== null ? req.body : {};
      const { djId, djName, trackName, playlistId, playlistName, startedAt } = body;

      if (!djId || !trackName) {
        return res.status(400).json({ error: 'djId y trackName son obligatorios' });
      }

      const listenedAt = startedAt ? new Date(startedAt).toISOString() : new Date().toISOString();

      const payload = {
        user_id: userId,
        dj_id: sanitizeText(djId, 120),
        dj_name: sanitizeText(djName, 120),
        playlist_id: sanitizeText(playlistId, 120),
        playlist_name: sanitizeText(playlistName, 160),
        track_name: sanitizeText(trackName, 200),
        listened_at: listenedAt,
      };

      const { error: insertError } = await supabaseAdmin
        .from(TABLE_NAME)
        .insert(payload);

      if (insertError) {
        console.error('[listen-history] Error al guardar historial:', insertError);
        if (insertError?.code === '42P01') {
          return res.status(501).json({
            error:
              'Falta la tabla user_listen_history. Crea la tabla en Supabase con columnas: id uuid default uuid_generate_v4(), user_id uuid, dj_id text, dj_name text, playlist_id text, playlist_name text, track_name text, listened_at timestamptz default now().',
          });
        }
        return res.status(500).json({ error: 'No se pudo guardar la reproducción' });
      }

      return res.status(201).json({ ok: true });
    }

    return res.status(405).json({ error: 'Método no permitido' });
  } catch (err) {
    console.error('[listen-history] Error inesperado:', err);
    return res.status(500).json({ error: err?.message || 'Error interno del servidor' });
  }
}
