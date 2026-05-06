import { supabaseAdmin } from '../../../../utils/supabaseAdmin';
import { getAuthenticatedUser, ensureAdmin } from '../../../../utils/apiAuth';

export default async function handler(req, res) {
  try {
    const { user, appUser, error } = await getAuthenticatedUser(req);
    if (error) return res.status(401).json({ error });
    if (!ensureAdmin(appUser)) return res.status(403).json({ error: 'No autorizado' });

    if (req.method === 'GET') {
      const { data, error: fetchError } = await supabaseAdmin
        .from('djs')
        .select('id, nombre_artistico, bio, estilo_visual, estilo_musical, created_at, app_users ( username, email, tipo_usuario )')
        .order('created_at', { ascending: false });

      if (fetchError) {
        console.error('[admin/djs] Error al obtener DJs:', fetchError);
        return res.status(500).json({ error: 'No se pudieron obtener los DJs' });
      }

      return res.status(200).json({ djs: data });
    }

    if (req.method === 'POST') {
      const body = typeof req.body === 'object' ? req.body : {};
      const { userId, email, nombre_artistico, bio, estilo_visual, estilo_musical } = body;

      if (!nombre_artistico) {
        return res.status(400).json({ error: 'nombre_artistico es obligatorio' });
      }

      let targetUserId = userId;

      if (!targetUserId && email) {
        const { data: found, error: findError } = await supabaseAdmin
          .from('app_users')
          .select('id')
          .eq('email', email)
          .maybeSingle();

        if (findError || !found) {
          return res.status(404).json({ error: 'No se encontró un usuario con ese email' });
        }

        targetUserId = found.id;
      }

      if (!targetUserId) {
        return res.status(400).json({ error: 'Debes proporcionar userId o email' });
      }

      await supabaseAdmin
        .from('app_users')
        .update({ tipo_usuario: 'dj' })
        .eq('id', targetUserId);

      await supabaseAdmin.auth.admin.updateUserById(targetUserId, {
        user_metadata: {
          tipo_usuario: 'dj',
        },
      });

      const { data, error: upsertError } = await supabaseAdmin
        .from('djs')
        .upsert(
          {
            id: targetUserId,
            nombre_artistico,
            bio: bio || null,
            estilo_visual: estilo_visual || null,
            estilo_musical: estilo_musical || null,
          },
          { onConflict: 'id' }
        )
        .select('id, nombre_artistico, bio, estilo_visual, estilo_musical, created_at')
        .single();

      if (upsertError) {
        console.error('[admin/djs] Error al crear DJ:', upsertError);
        return res.status(500).json({ error: 'No se pudo crear/actualizar el DJ' });
      }

      return res.status(201).json({ dj: data });
    }

    return res.status(405).json({ error: 'Método no permitido' });
  } catch (err) {
    console.error('[admin/djs] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}
