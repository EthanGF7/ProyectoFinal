import { getAuthenticatedUser } from '../../../utils/apiAuth';
import { supabaseAdmin } from '../../../utils/supabaseAdmin';

const TABLE_NAME = 'user_listen_history';

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

export default async function handler(req, res) {
  try {
    const { user, appUser, error } = await getAuthenticatedUser(req);
    if (error) {
      return res.status(401).json({ error });
    }

    const userId = appUser?.id || user?.id;
    if (!userId) {
      return res.status(400).json({ error: 'No se pudo determinar el usuario autenticado' });
    }

    if (req.method === 'GET') {
      const limitParam = parseQueryValue(req.query?.limit);
      const djIdParam = parseQueryValue(req.query?.djId);
      const limit = parseLimit(limitParam);

      let query = supabaseAdmin
        .from(TABLE_NAME)
        .select('id, dj_id, dj_name, track_name, listened_at')
        .eq('user_id', userId)
        .order('listened_at', { ascending: false })
        .limit(limit);

      if (djIdParam) {
        query = query.eq('dj_id', djIdParam);
      }

      const { data, error: fetchError } = await query;

      if (fetchError) {
        console.error('[listen-history] Error al obtener historial:', fetchError);
        if (fetchError?.code === '42P01') {
          return res.status(501).json({
            error:
              'Falta la tabla user_listen_history. Crea la tabla en Supabase con columnas: id uuid default uuid_generate_v4(), user_id uuid, dj_id text, dj_name text, track_name text, listened_at timestamptz default now().',
          });
        }
        return res.status(500).json({ error: 'No se pudo obtener el historial de escuchas' });
      }

      const history = data || [];
      const uniqueDjs = new Set(history.map((item) => item.dj_id || item.dj_name || ''));
      const stats = {
        total: history.length,
        uniqueDjs: uniqueDjs.size,
        lastListen: history[0] || null,
      };

      return res.status(200).json({ history, stats });
    }

    if (req.method === 'POST') {
      const body = typeof req.body === 'object' && req.body !== null ? req.body : {};
      const { djId, djName, trackName, startedAt } = body;

      if (!djId || !trackName) {
        return res.status(400).json({ error: 'djId y trackName son obligatorios' });
      }

      const listenedAt = startedAt ? new Date(startedAt).toISOString() : new Date().toISOString();

      const payload = {
        user_id: userId,
        dj_id: sanitizeText(djId, 120),
        dj_name: sanitizeText(djName, 120),
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
              'Falta la tabla user_listen_history. Crea la tabla en Supabase con columnas: id uuid default uuid_generate_v4(), user_id uuid, dj_id text, dj_name text, track_name text, listened_at timestamptz default now().',
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
