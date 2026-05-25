import { supabaseAdmin } from '../../../utils/supabaseAdmin';

const PLAYLIST_SELECT =
  'id, dj_id, titulo, descripcion, mood, plataformas, created_at, djs ( id, nombre_artistico, bio )';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  try {
    const { data, error } = await supabaseAdmin
      .from('dj_playlists')
      .select(PLAYLIST_SELECT)
      .order('created_at', { ascending: false });

    if (error) {
      if (error.code === '42P01') {
        return res.status(200).json({ playlists: [] });
      }
      if (error.code === '42703') {
        return res.status(400).json({ error: 'Columnas faltantes en la tabla dj_playlists.' });
      }
      console.error('[public/playlists] Error obteniendo playlists:', error);
      return res.status(500).json({ error: 'No se pudieron obtener las playlists' });
    }

    const playlists = (data || []).map((playlist) => ({
      id: playlist.id,
      dj_id: playlist.dj_id,
      titulo: playlist.titulo,
      descripcion: playlist.descripcion,
      mood: playlist.mood,
      plataformas: playlist.plataformas,
      created_at: playlist.created_at,
      dj: playlist.djs || null,
    }));

    return res.status(200).json({ playlists });
  } catch (err) {
    console.error('[public/playlists] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}
