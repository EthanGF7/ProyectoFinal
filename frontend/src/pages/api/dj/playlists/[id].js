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

  const playlistId = req.query.id;

  if (!playlistId) {
    return res.status(400).json({ error: 'ID de playlist no proporcionado' });
  }

  if (req.method === 'PATCH') {
    const body = typeof req.body === 'object' ? req.body : {};
    const { titulo, descripcion, mood, tempo, plataformas } = body;

    if (!titulo) {
      return res.status(400).json({ error: 'El título es obligatorio' });
    }

    try {
      const { data, error: updateError } = await supabaseAdmin
        .from('dj_playlists')
        .update({
          titulo,
          descripcion: descripcion ?? null,
          mood: mood ?? null,
          tempo: tempo ?? null,
          plataformas: plataformas ?? null,
        })
        .eq('id', playlistId)
        .eq('dj_id', user.id)
        .select(PLAYLIST_SELECT)
        .single();

      if (updateError) {
        if (updateError.code === '42P01') {
          return res.status(400).json({
            error: 'La tabla dj_playlists no existe. Crea la tabla en Supabase antes de actualizar playlists.',
          });
        }
        if (updateError.code === '42703') {
          return res.status(400).json({
            error:
              'Faltan columnas (mood, tempo o plataformas) en la tabla dj_playlists. Agrégalas antes de actualizar playlists.',
          });
        }
        console.error('[dj/playlists/:id] Error actualizando playlist:', updateError);
        return res.status(500).json({ error: 'No se pudo actualizar la playlist' });
      }

      if (!data) {
        return res.status(404).json({ error: 'Playlist no encontrada' });
      }

      return res.status(200).json({ playlist: data });
    } catch (err) {
      console.error('[dj/playlists/:id] Error inesperado PATCH:', err);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  if (req.method === 'DELETE') {
    try {
      const { error: deleteError } = await supabaseAdmin
        .from('dj_playlists')
        .delete()
        .eq('id', playlistId)
        .eq('dj_id', user.id);

      if (deleteError) {
        if (deleteError.code === '42P01') {
          return res.status(400).json({
            error: 'La tabla dj_playlists no existe. Crea la tabla en Supabase antes de eliminar playlists.',
          });
        }
        if (deleteError.code === '42703') {
          return res.status(400).json({
            error:
              'Faltan columnas (mood, tempo o plataformas) en la tabla dj_playlists. Agrégalas antes de eliminar playlists.',
          });
        }
        console.error('[dj/playlists/:id] Error elimando playlist:', deleteError);
        return res.status(500).json({ error: 'No se pudo eliminar la playlist' });
      }

      return res.status(204).end();
    } catch (err) {
      console.error('[dj/playlists/:id] Error inesperado DELETE:', err);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  return res.status(405).json({ error: 'Método no permitido' });
}
