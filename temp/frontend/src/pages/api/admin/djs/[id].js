import { supabaseAdmin } from '../../../../utils/supabaseAdmin';
import { getAuthenticatedUser, ensureAdmin } from '../../../../utils/apiAuth';

const sanitizeUpdate = (body) => ({
  nombre_artistico: body.nombre_artistico,
  bio: body.bio ?? null,
  estilo_visual: body.estilo_visual ?? null,
  estilo_musical: body.estilo_musical ?? null,
});

export default async function handler(req, res) {
  try {
    const { user, appUser, error } = await getAuthenticatedUser(req);
    if (error) return res.status(401).json({ error });
    if (!ensureAdmin(appUser)) return res.status(403).json({ error: 'No autorizado' });

    const { id } = req.query;

    if (req.method === 'PATCH') {
      const body = typeof req.body === 'object' ? req.body : {};
      const updatePayload = sanitizeUpdate(body);

      const { data, error: updateError } = await supabaseAdmin
        .from('djs')
        .update(updatePayload)
        .eq('id', id)
        .select('id, nombre_artistico, bio, estilo_visual, estilo_musical, created_at')
        .single();

      if (updateError) {
        console.error('[admin/djs/:id] Error al actualizar DJ:', updateError);
        return res.status(500).json({ error: 'No se pudo actualizar el DJ' });
      }

      return res.status(200).json({ dj: data });
    }

    if (req.method === 'DELETE') {
      const { error: deleteError } = await supabaseAdmin
        .from('djs')
        .delete({ returning: 'minimal' })
        .eq('id', id);

      if (deleteError) {
        console.error('[admin/djs/:id] Error al eliminar DJ:', deleteError);
        return res.status(500).json({ error: 'No se pudo eliminar el DJ' });
      }

      await supabaseAdmin
        .from('app_users')
        .update({ tipo_usuario: 'usuario_normal' })
        .eq('id', id);

      await supabaseAdmin.auth.admin.updateUserById(id, {
        user_metadata: {
          tipo_usuario: 'usuario_normal',
        },
      });

      return res.status(204).end();
    }

    return res.status(405).json({ error: 'Método no permitido' });
  } catch (err) {
    console.error('[admin/djs/:id] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}
