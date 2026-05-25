import { supabaseAdmin } from '../../../utils/supabaseAdmin';
import { resolveDjScript } from '../../../../lib/dj-scripts';

const DJ_SELECT =
  'id, nombre_artistico, bio, estilo_visual, estilo_musical, created_at, app_users ( username, email )';
const LOCAL_DJ_NAMES = ['Flamenco', 'Nexus', 'Pop', 'Urbano'];

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

    const userDjs = (data || [])
      .filter((dj) => !LOCAL_DJ_NAMES.some((name) => name.toLowerCase() === dj.nombre_artistico?.toLowerCase()))
      .map((dj) => ({
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

    const localDjs = LOCAL_DJ_NAMES.map((name) => ({
      id: name.toLowerCase(),
      nombre_artistico: name,
      bio: `Cabina local del DJ ${name}`,
      estilo_visual: null,
      estilo_musical: null,
      created_at: null,
      username: null,
      email: null,
      playlists_count: 0,
      isLocal: true,
      hasLocalPlayer: Boolean(resolveDjScript(name)),
    }));

    return res.status(200).json({ djs: [...localDjs, ...userDjs], localDjs, userDjs });
  } catch (err) {
    console.error('[public/djs] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}