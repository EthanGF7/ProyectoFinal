import { supabaseAdmin } from '../../../../utils/supabaseAdmin';
import { getAuthenticatedUser, ensureDj } from '../../../../utils/apiAuth';

const PLAYLIST_SELECT =
  'id, dj_id, titulo, descripcion, mood, tempo, plataformas, created_at';

export default async function handler(req, res) {
  const { user, appUser, error } = await getAuthenticatedUser(req);

  if (error) {
    return res.status(401).json({ error });
  }

  if (!ensureDj(appUser)) {
    return res.status(403).json({ error: 'Solo los DJs pueden acceder a este recurso' });
  }

  if (req.method === 'GET') {
    try {
      const { data, error: fetchError } = await supabaseAdmin
        .from('dj_playlists')
        .select(PLAYLIST_SELECT)
        .eq('dj_id', user.id)
        .order('created_at', { ascending: false });

      if (fetchError) {
        if (fetchError.code === '42P01') {
          console.warn('[dj/playlists] Tabla dj_playlists no existe todavía.');
          return res.status(200).json({ playlists: [] });
        }
        if (fetchError.code === '42703') {
          console.warn('[dj/playlists] Columnas esperadas no existen aún:', fetchError);
          return res.status(200).json({ playlists: [] });
        }
        console.error('[dj/playlists] Error obteniendo playlists:', fetchError);
        return res.status(500).json({ error: 'No se pudieron obtener las playlists' });
      }

      return res.status(200).json({ playlists: data || [] });
    } catch (err) {
      console.error('[dj/playlists] Error inesperado:', err);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  if (req.method === 'POST') {
    const body = typeof req.body === 'object' ? req.body : {};
    const { titulo, descripcion, mood, tempo, plataformas } = body;

    if (!titulo) {
      return res.status(400).json({ error: 'El título es obligatorio' });
    }

    try {
      const insertPayload = {
        dj_id: user.id,
        titulo,
        descripcion: descripcion ?? null,
      };

      if (typeof mood !== 'undefined') insertPayload.mood = mood ?? null;
      if (typeof tempo !== 'undefined') insertPayload.tempo = tempo ?? null;
      if (typeof plataformas !== 'undefined') insertPayload.plataformas = plataformas ?? null;

      const { error: insertError } = await supabaseAdmin
        .from('dj_playlists')
        .insert(insertPayload);

      if (insertError) {
        if (insertError.code === '42P01') {
          return res.status(400).json({
            error: 'La tabla dj_playlists no existe. Crea la tabla en Supabase antes de añadir playlists.',
          });
        }
        if (insertError.code === '42703') {
          console.warn('[dj/playlists] Columnas opcionales ausentes, guardando sin ellas.');
        } else {
          console.error('[dj/playlists] Error creando playlist:', insertError);
          return res.status(500).json({ error: 'No se pudo crear la playlist' });
        }
      }

      const { data: latest, error: selectError } = await supabaseAdmin
        .from('dj_playlists')
        .select(PLAYLIST_SELECT)
        .eq('dj_id', user.id)
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle();

      if (selectError) {
        console.error('[dj/playlists] Playlist creada pero no recuperada:', selectError);
        return res.status(500).json({ error: 'La playlist se creó pero no se pudo recuperar.' });
      }

      return res.status(201).json({ playlist: latest });
    } catch (err) {
      console.error('[dj/playlists] Error inesperado POST:', err);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  return res.status(405).json({ error: 'Método no permitido' });
}
