import { supabaseAdmin } from '../../../utils/supabaseAdmin';
import { getAuthenticatedUser, getAppUserRecord, ensureAdmin } from '../../../utils/apiAuth';

export default async function handler(req, res) {
  if (req.method === 'GET') {
    const { user, appUser, error } = await getAuthenticatedUser(req);
    if (error) return res.status(401).json({ error });

    if (!ensureAdmin(appUser)) {
      return res.status(403).json({ error: 'No autorizado' });
    }

    const estado = req.query.estado || 'pendiente';

    const { data, error: selectError } = await supabaseAdmin
      .from('dj_requests')
      .select('*, app_users ( username, email, tipo_usuario )')
      .eq('estado', estado)
      .order('created_at', { ascending: true });

    if (selectError) {
      return res.status(500).json({ error: selectError.message });
    }

    return res.status(200).json({ requests: data });
  }

  if (req.method === 'POST') {
    const { user, appUser, error } = await getAuthenticatedUser(req);
    if (error) return res.status(401).json({ error });

    const { data } = await supabaseAdmin
      .from('dj_requests')
      .select('id')
      .eq('user_id', user.id)
      .eq('estado', 'pendiente')
      .maybeSingle();

    if (data) {
      return res.status(400).json({ error: 'Ya tienes una solicitud pendiente' });
    }

    const body = typeof req.body === 'object' ? req.body : {};
    const insertPayload = {
      user_id: user.id,
      mensaje: body.mensaje || null,
    };

    const { data: inserted, error: insertError } = await supabaseAdmin
      .from('dj_requests')
      .insert(insertPayload)
      .select('*')
      .single();

    if (insertError) {
      return res.status(500).json({ error: insertError.message });
    }

    return res.status(200).json({ request: inserted });
  }

  if (req.method === 'PATCH') {
    const { user, appUser, error } = await getAuthenticatedUser(req);
    if (error) return res.status(401).json({ error });

    if (!ensureAdmin(appUser)) {
      return res.status(403).json({ error: 'No autorizado' });
    }

    const body = typeof req.body === 'object' ? req.body : {};
    const requestId = body.id;

    if (!requestId) {
      return res.status(400).json({ error: 'Falta el ID de la solicitud' });
    }

    const { data: existingRequest, error: fetchError } = await supabaseAdmin
      .from('dj_requests')
      .select('id, user_id, mensaje, estado, created_at')
      .eq('id', requestId)
      .single();

    if (fetchError || !existingRequest) {
      return res.status(404).json({ error: 'Solicitud no encontrada' });
    }

    const updatePayload = {
      estado: body.estado,
      mensaje: body.mensaje ?? existingRequest.mensaje,
      resolved_at: body.estado !== 'pendiente' ? new Date().toISOString() : null,
    };

    const { data: updatedRequest, error: updateError } = await supabaseAdmin
      .from('dj_requests')
      .update(updatePayload)
      .eq('id', requestId)
      .select('*')
      .single();

    if (updateError) {
      return res.status(500).json({ error: updateError.message });
    }

    if (body.estado === 'aprobada') {
      const userId = existingRequest.user_id;

      await supabaseAdmin
        .from('app_users')
        .update({ tipo_usuario: 'dj' })
        .eq('id', userId);

      await supabaseAdmin.auth.admin.updateUserById(userId, {
        user_metadata: { tipo_usuario: 'dj' },
      });

      await supabaseAdmin
        .from('djs')
        .upsert({
          id: userId,
          nombre_artistico: body.nombre_artistico || appUser.username,
          bio: body.bio || null,
          estilo_visual: body.estilo_visual || null,
          estilo_musical: body.estilo_musical || null,
        });
    }

    return res.status(200).json({ request: updatedRequest });
  }

  return res.status(405).json({ error: 'Método no permitido' });
}
