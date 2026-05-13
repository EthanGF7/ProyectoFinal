import { supabaseAdmin } from './supabaseAdmin';

const extractBearerToken = (req) => {
  const authHeader = req.headers.authorization || '';
  if (authHeader.startsWith('Bearer ')) {
    return authHeader.slice(7).trim();
  }
  return null;
};

export const getAuthenticatedUser = async (req) => {
  const token = extractBearerToken(req);
  if (!token) {
    return { error: 'Token ausente' };
  }

  const { data, error } = await supabaseAdmin.auth.getUser(token);
  if (error || !data?.user) {
    return { error: 'Token inválido' };
  }

  const userId = data.user.id;

  const { data: appProfile } = await supabaseAdmin
    .from('app_users')
    .select('id, username, email, tipo_usuario')
    .eq('id', userId)
    .maybeSingle();

  return { user: data.user, appUser: appProfile || null, token };
};

export const getAppUserRecord = async (userId) => {
  const { data, error } = await supabaseAdmin
    .from('app_users')
    .select('id, username, email, tipo_usuario')
    .eq('id', userId)
    .single();

  if (error || !data) {
    return { error: 'No se encontró el perfil de usuario' };
  }

  return { appUser: data };
};

export const ensureRole = (appUser, roles = []) => {
  if (!appUser?.tipo_usuario) return false;
  return roles.includes(appUser.tipo_usuario);
};

export const ensureAdmin = (appUser) => ensureRole(appUser, ['admin']);

export const ensureDj = (appUser) => ensureRole(appUser, ['dj', 'admin']);
