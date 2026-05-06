import { supabaseAdmin } from '../../../utils/supabaseAdmin';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  try {
    const { data, error } = await supabaseAdmin
      .from('djs')
      .select(
        'id, nombre_artistico, bio, estilo_visual, estilo_musical, created_at, app_users ( username, email )'
      )
      .order('created_at', { ascending: false });

    if (error) {
      console.error('[public/djs] Error obteniendo DJs:', error);
      return res.status(500).json({ error: 'No se pudieron obtener los DJs' });
    }

    const djIds = (data || []).map((dj) => dj.id);
    let playlistCounts = {};

    if (djIds.length > 0) {
      try {
        const { data: playlistData, error: playlistError } = await supabaseAdmin
          .from('dj_playlists')
          .select('dj_id')
          .in('dj_id', djIds);

        if (playlistError) {
          if (playlistError.code === '42P01' || playlistError.code === '42703') {
            console.warn('[public/djs] Tabla/columnas dj_playlists faltantes:', playlistError);
          } else {
            console.error('[public/djs] Error obteniendo playlists para conteo:', playlistError);
            return res.status(500).json({ error: 'No se pudieron obtener los DJs' });
          }
        } else {
          playlistCounts = (playlistData || []).reduce((acc, item) => {
            acc[item.dj_id] = (acc[item.dj_id] || 0) + 1;
            return acc;
          }, {});
        }
      } catch (playlistUnexpected) {
        console.error('[public/djs] Error inesperado obteniendo conteo playlists:', playlistUnexpected);
      }
    }

    const djs = (data || []).map((dj) => ({
      id: dj.id,
      nombre_artistico: dj.nombre_artistico,
      bio: dj.bio,
      estilo_visual: dj.estilo_visual,
      estilo_musical: dj.estilo_musical,
      created_at: dj.created_at,
      username: dj.app_users?.username || null,
      email: dj.app_users?.email || null,
      playlists_count: playlistCounts[dj.id] || 0,
    }));

    return res.status(200).json({ djs });
  } catch (err) {
    console.error('[public/djs] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}
