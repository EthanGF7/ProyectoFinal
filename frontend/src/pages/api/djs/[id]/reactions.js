import { getAuthenticatedUser } from '../../../../utils/apiAuth';
import { supabaseAdmin } from '../../../../utils/supabaseAdmin';

export default async function handler(req, res) {
  const { id: djId } = req.query;

  if (!djId || typeof djId !== 'string') {
    return res.status(400).json({ error: 'dj_id inválido' });
  }

  // Autenticación
  const { appUser, user, error: authError } = await getAuthenticatedUser(req);
  if (authError) {
    return res.status(401).json({ error: authError });
  }
  const userId = appUser?.id || user?.id;
  if (!userId) {
    return res.status(401).json({ error: 'Usuario no autenticado' });
  }

  // GET → devolver reacciones del usuario para este DJ
  if (req.method === 'GET') {
    try {
      const { data, error } = await supabaseAdmin
        .from('track_reactions')
        .select('track_name, reaction, updated_at')
        .eq('user_id', userId)
        .eq('dj_id', djId);

      if (error) {
        console.error('[reactions GET] Error:', error);
        return res.status(500).json({ error: 'Error obteniendo reacciones' });
      }

      const reactions = {};
      (data || []).forEach((row) => {
        reactions[row.track_name] = row.reaction;
      });

      return res.status(200).json({ reactions });
    } catch (err) {
      console.error('[reactions GET] Error inesperado:', err);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  // POST → crear / actualizar / eliminar reacción
  if (req.method === 'POST') {
    try {
      const { track_name, reaction, dj_name } = req.body || {};

      if (!track_name || typeof track_name !== 'string') {
        return res.status(400).json({ error: 'track_name requerido' });
      }
      if (![1, -1, 0].includes(reaction)) {
        return res.status(400).json({ error: 'reaction debe ser 1, -1 o 0' });
      }

      // reaction === 0 → eliminar (toggle off)
      if (reaction === 0) {
        const { error } = await supabaseAdmin
          .from('track_reactions')
          .delete()
          .eq('user_id', userId)
          .eq('dj_id', djId)
          .eq('track_name', track_name);

        if (error) {
          console.error('[reactions DELETE] Error:', error);
          return res.status(500).json({ error: 'Error eliminando reacción' });
        }
        return res.status(200).json({ ok: true, reaction: 0 });
      }

      // upsert (insert o update si ya existe)
      const { error } = await supabaseAdmin
        .from('track_reactions')
        .upsert(
          {
            user_id: userId,
            dj_id: djId,
            dj_name: typeof dj_name === 'string' ? dj_name.slice(0, 120) : null,
            track_name,
            reaction,
            updated_at: new Date().toISOString(),
          },
          { onConflict: 'user_id,dj_id,track_name' }
        );

      if (error) {
        console.error('[reactions UPSERT] Error:', error);
        return res.status(500).json({ error: 'Error guardando reacción' });
      }

      return res.status(200).json({ ok: true, reaction });
    } catch (err) {
      console.error('[reactions POST] Error inesperado:', err);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  res.setHeader('Allow', 'GET, POST');
  return res.status(405).json({ error: 'Método no permitido' });
}