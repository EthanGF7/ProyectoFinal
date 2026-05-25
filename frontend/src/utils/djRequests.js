import { supabase } from './supabase';
import { callAuthedApi } from './apiClient';

export const createDjRequest = async ({ message }) => {
  const result = await callAuthedApi('/api/dj/requests', {
    method: 'POST',
    body: { mensaje: message },
  });

  return result.request;
};

export const fetchOwnDjRequest = async () => {
  const { data: { user }, error: userError } = await supabase.auth.getUser();

  if (userError) throw userError;
  if (!user) return null;

  try {
    const result = await callAuthedApi('/api/dj/my-request');
    return result?.request || null;
  } catch (err) {
    if (err?.message?.includes('404') || err?.message?.includes('no encontrada')) return null;
    throw err;
  }
};

export const fetchAdminDjRequests = async ({ status = 'pendiente' } = {}) => {
  const result = await callAuthedApi(`/api/dj/requests?estado=${status}`);
  return result.requests || [];
};

export const approveDjRequest = async ({
  id,
  nombre_artistico,
  bio,
  estilo_visual,
  estilo_musical,
}) => {
  const result = await callAuthedApi('/api/dj/requests', {
    method: 'PATCH',
    body: {
      id,
      estado: 'aprobada',
      nombre_artistico,
      bio,
      estilo_visual,
      estilo_musical,
    },
  });

  return result.request;
};

export const rejectDjRequest = async ({ id, mensaje }) => {
  const result = await callAuthedApi('/api/dj/requests', {
    method: 'PATCH',
    body: {
      id,
      estado: 'rechazada',
      mensaje,
    },
  });

  return result.request;
};
