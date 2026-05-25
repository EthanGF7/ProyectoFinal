import { supabaseAdmin } from '../../../utils/supabaseAdmin';

const PLAYLIST_SELECT =
  'id, dj_id, titulo, descripcion, mood, plataformas, created_at, djs ( id, nombre_artistico, bio, estilo_musical, estilo_visual )';

export default async function handler(req, res) {
  const { id } = req.query;

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  if (!id) {
    return res.status(400).json({ error: 'ID de playlist no proporcionado' });
  }

  try {
    const { data, error } = await supabaseAdmin
      .from('dj_playlists')
      .select(PLAYLIST_SELECT)
      .eq('id', id)
      .maybeSingle();

    if (error) {
      if (error.code === '42P01') {
        return res.status(404).json({ error: 'La tabla dj_playlists no existe todavía.' });
      }
      if (error.code === '42703') {
        return res.status(400).json({ error: 'Columnas faltantes en la tabla dj_playlists.' });
      }
      console.error('[public/playlists/:id] Error obteniendo playlist:', error);
      return res.status(500).json({ error: 'No se pudo obtener la playlist' });
    }

    if (!data) {
      return res.status(404).json({ error: 'Playlist no encontrada' });
    }

    return res.status(200).json({
      playlist: {
        id: data.id,
        dj_id: data.dj_id,
        titulo: data.titulo,
        descripcion: data.descripcion,
        mood: data.mood,
        plataformas: data.plataformas,
        created_at: data.created_at,
      },
      dj: data.djs || null,
    });
  } catch (err) {
    console.error('[public/playlists/:id] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}
