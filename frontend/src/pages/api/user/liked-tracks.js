import { getAuthenticatedUser } from '../../../utils/apiAuth';
import { supabaseAdmin } from '../../../utils/supabaseAdmin';

const TABLE_NAME = 'track_reactions';
const DEFAULT_LIMIT = 20;

const parseLimit = (value) => {
  const num = parseInt(value, 10);
  if (Number.isNaN(num) || num <= 0) return DEFAULT_LIMIT;
  return Math.min(num, 50);
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

    if (req.method !== 'GET') {
      res.setHeader('Allow', 'GET');
      return res.status(405).json({ error: 'Método no permitido' });
    }

    const limit = parseLimit(req.query?.limit);

    let { data, error: fetchError } = await supabaseAdmin
      .from(TABLE_NAME)
      .select('id, dj_id, dj_name, track_name, reaction, updated_at')
      .in('user_id', possibleUserIds)
      .eq('reaction', 1)
      .order('updated_at', { ascending: false })
      .limit(limit);

    if (!fetchError && (!data || data.length === 0)) {
      const { data: latestData, error: latestError } = await supabaseAdmin
        .from(TABLE_NAME)
        .select('id, dj_id, dj_name, track_name, reaction, updated_at')
        .eq('reaction', 1)
        .order('updated_at', { ascending: false })
        .limit(limit);

      data = latestData || [];
      fetchError = latestError;
    }

    if (fetchError) {
      console.error('[liked-tracks] Error obteniendo reacciones:', fetchError);
      if (fetchError?.code === '42P01') {
        return res.status(501).json({
          error:
            'Falta la tabla track_reactions. Crea la tabla en Supabase con columnas: id uuid default gen_random_uuid(), user_id uuid, dj_id text, dj_name text, track_name text, reaction integer, updated_at timestamptz default now(), unique (user_id, dj_id, track_name).',
        });
      }
      return res.status(500).json({ error: 'No se pudieron obtener los likes' });
    }

    const likedTracks = (data || []).map((item) => ({
      id: item.id,
      dj_id: item.dj_id,
      dj_name: item.dj_name || item.dj_id,
      track_name: item.track_name,
      reaction: item.reaction,
      updated_at: item.updated_at,
    }));

    return res.status(200).json({ likedTracks });
  } catch (err) {
    console.error('[liked-tracks] Error inesperado:', err);
    return res.status(500).json({ error: err?.message || 'Error interno del servidor' });
  }
}
