import { supabaseAdmin } from '../../../utils/supabaseAdmin';

const DJ_SELECT =
  'id, nombre_artistico, bio, estilo_visual, estilo_musical, created_at, app_users ( username, email )';
const PLAYLIST_SELECT =
  'id, titulo, descripcion, mood, tempo, plataformas, created_at';

export default async function handler(req, res) {
  const { id } = req.query;

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  if (!id) {
    return res.status(400).json({ error: 'ID de DJ no proporcionado' });
  }

  try {
    const { data: dj, error: djError } = await supabaseAdmin
      .from('djs')
      .select(DJ_SELECT)
      .eq('id', id)
      .maybeSingle();

    if (djError) {
      if (djError.code === '42P01') {
        return res.status(404).json({ error: 'La tabla djs no existe todavía.' });
      }
      if (djError.code === '42703') {
        return res.status(400).json({ error: 'Columnas faltantes en la tabla djs.' });
      }
      console.error('[public/djs/:id] Error obteniendo DJ:', djError);
      return res.status(500).json({ error: 'No se pudo obtener el DJ solicitado' });
    }

    if (!dj) {
      return res.status(404).json({ error: 'DJ no encontrado' });
    }

    let playlists = [];

    try {
      const { data: playlistsData, error: playlistsError } = await supabaseAdmin
        .from('dj_playlists')
        .select(PLAYLIST_SELECT)
        .eq('dj_id', id)
        .order('created_at', { ascending: false });

      if (playlistsError) {
        if (playlistsError.code === '42P01' || playlistsError.code === '42703') {
          console.warn('[public/djs/:id] Tabla/columnas dj_playlists faltantes:', playlistsError);
        } else {
          console.error('[public/djs/:id] Error obteniendo playlists:', playlistsError);
          return res.status(500).json({ error: 'No se pudieron obtener las playlists del DJ' });
        }
      } else {
        playlists = playlistsData || [];
      }
    } catch (playlistsUnexpected) {
      console.error('[public/djs/:id] Error inesperado playlists:', playlistsUnexpected);
      return res.status(500).json({ error: 'Error interno al cargar las playlists' });
    }

    return res.status(200).json({ dj, playlists });
  } catch (err) {
    console.error('[public/djs/:id] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}
