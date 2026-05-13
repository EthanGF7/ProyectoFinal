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
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError) {
    throw userError;
  }

  if (!user) {
    return null;
  }

  const { data, error } = await supabase
    .from('dj_requests')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) {
    throw error;
  }

  return data;
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
