import { supabaseAdmin } from '../../../utils/supabaseAdmin';
import { resolveDjScript } from '../../../../lib/dj-scripts';

const DJ_SELECT =
  'id, nombre_artistico, bio, estilo_visual, estilo_musical, created_at, app_users ( username, email )';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Metodo no permitido' });
  }

  try {
    const { data, error } = await supabaseAdmin
      .from('djs')
      .select(DJ_SELECT)
      .order('created_at', { ascending: false });

    if (error) {
      console.error('[public/djs] Error obteniendo DJs:', error);
      return res.status(500).json({ error: 'Error obteniendo DJs' });
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
      playlists_count: 0,
      isLocal: false,
      hasLocalPlayer: Boolean(resolveDjScript(dj.id, dj.nombre_artistico)),
    }));

    return res.status(200).json({ djs });
  } catch (err) {
    console.error('[public/djs] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}