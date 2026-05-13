import { supabase } from './supabase';

export const syncUserProfile = async (payload = {}) => {
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

  if (sessionError) {
    console.error('[syncUserProfile] Error obteniendo la sesión:', sessionError);
    throw new Error('No se pudo obtener la sesión actual');
  }

  const accessToken = sessionData?.session?.access_token;

  if (!accessToken) {
    console.warn('[syncUserProfile] No hay token de acceso disponible para sincronizar.');
    return { success: false, reason: 'missing_token' };
  }

  const response = await fetch('/api/profile/sync', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json();

  if (!response.ok) {
    console.error('[syncUserProfile] Error al sincronizar perfil:', result.error);
    throw new Error(result.error || 'No se pudo sincronizar el perfil');
  }

  return result;
};
