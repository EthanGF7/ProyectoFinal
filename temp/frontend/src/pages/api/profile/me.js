import { getAuthenticatedUser } from '../../../utils/apiAuth';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  try {
    const { user, appUser, error } = await getAuthenticatedUser(req);
    if (error) {
      return res.status(401).json({ error });
    }

    const result = appUser
      ? {
          id: appUser.id,
          email: appUser.email,
          username: appUser.username,
          tipo_usuario: appUser.tipo_usuario,
        }
      : {
          id: user.id,
          email: user.email,
          username: user.user_metadata?.username || user.email,
          tipo_usuario: user.user_metadata?.tipo_usuario || 'usuario_normal',
        };

    return res.status(200).json({ user: result });
  } catch (err) {
    console.error('[profile/me] Error inesperado:', err);
    return res.status(500).json({ error: err.message || 'Error interno del servidor' });
  }
}
