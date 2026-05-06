import { supabaseAdmin } from '../../../utils/supabaseAdmin';

const ensureSupabaseConfigured = () => {
  if (!supabaseAdmin) {
    throw new Error('Supabase admin client no configurado.');
  }
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  try {
    ensureSupabaseConfigured();

    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Token de autorización ausente' });
    }

    const accessToken = authHeader.replace('Bearer', '').trim();
    if (!accessToken) {
      return res.status(401).json({ error: 'Token inválido' });
    }

    const { data: userData, error: userError } = await supabaseAdmin.auth.getUser(accessToken);

    if (userError || !userData?.user) {
      return res.status(401).json({ error: 'No se pudo obtener el usuario autenticado' });
    }

    const { user } = userData;
    const body = typeof req.body === 'object' ? req.body : {};
    const usernameFromBody = body.username?.trim();
    const tipoDesdeCliente = body.tipoUsuario;

    const { data: existingProfile } = await supabaseAdmin
      .from('app_users')
      .select('id, tipo_usuario, username')
      .eq('id', user.id)
      .maybeSingle();

    const username =
      usernameFromBody ||
      existingProfile?.username ||
      user.user_metadata?.username ||
      user.email?.split('@')[0] ||
      'usuario';

    const tipoUsuario =
      tipoDesdeCliente ||
      existingProfile?.tipo_usuario ||
      user.user_metadata?.tipo_usuario ||
      'usuario_normal';

    const { error: updateError } = await supabaseAdmin
      .from('app_users')
      .upsert(
        {
          id: user.id,
          email: user.email,
          username,
          tipo_usuario: tipoUsuario,
          password_hash: 'supabase_managed',
          created_at: user.created_at,
        },
        { onConflict: 'id' }
      );

    if (updateError) {
      console.error('[profile/sync] Error al sincronizar:', updateError);
      return res.status(500).json({ error: 'No se pudo sincronizar el perfil' });
    }

    if (user.user_metadata?.tipo_usuario !== tipoUsuario) {
      await supabaseAdmin.auth.admin.updateUserById(user.id, {
        user_metadata: {
          ...user.user_metadata,
          tipo_usuario: tipoUsuario,
          username,
        },
      });
    }

    return res.status(200).json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
        username,
        tipo_usuario: tipoUsuario,
      },
    });
  } catch (err) {
    console.error('[profile/sync] Error inesperado:', err);
    return res.status(500).json({ error: 'Error interno del servidor' });
  }
}
