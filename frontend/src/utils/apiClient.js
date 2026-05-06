import { supabase } from './supabase';

export const callAuthedApi = async (path, { method = 'GET', body, headers = {} } = {}) => {
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

  if (sessionError) {
    throw sessionError;
  }

  const accessToken = sessionData?.session?.access_token;

  if (!accessToken) {
    throw new Error('No hay sesión activa');
  }

  const response = await fetch(path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = result?.error || 'Error en la solicitud';
    throw new Error(message);
  }

  return result;
};
