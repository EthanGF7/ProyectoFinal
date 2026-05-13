import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !serviceRoleKey) {
  console.error('Faltan variables de entorno para actualizar el correo del usuario.');
}

const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
});

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  try {
    if (!serviceRoleKey) {
      return res.status(500).json({ error: 'Servicio no configurado' });
    }

    const authHeader = req.headers.authorization;
    const token = authHeader?.startsWith('Bearer ') ? authHeader.slice(7) : null;

    if (!token) {
      return res.status(401).json({ error: 'Token de acceso requerido' });
    }

    const { newEmail } = req.body || {};

    if (!newEmail || typeof newEmail !== 'string') {
      return res.status(400).json({ error: 'Nuevo correo inválido' });
    }

    // Validar el token para asegurar que pertenece a un usuario real
    const { data: userData, error: sessionError } = await supabaseAdmin.auth.getUser(token);

    if (sessionError || !userData?.user) {
      return res.status(401).json({ error: 'Sesión no válida' });
    }

    const userId = userData.user.id;

    // Actualizar el correo usando privilegios de administrador
    const { error: updateError } = await supabaseAdmin.auth.admin.updateUserById(userId, {
      email: newEmail
    });

    if (updateError) {
      return res.status(400).json({ error: updateError.message });
    }

    return res.status(200).json({ success: true, email: newEmail });
  } catch (error) {
    console.error('Error en /api/profile/update-email:', error);
    return res.status(500).json({ error: 'Error interno al actualizar el correo' });
  }
}
