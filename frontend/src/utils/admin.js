import { callAuthedApi } from './apiClient';

export const fetchAdminDjs = async () => {
  const result = await callAuthedApi('/api/admin/djs');
  return result.djs || [];
};

export const createOrPromoteDj = async (payload) => {
  const result = await callAuthedApi('/api/admin/djs', {
    method: 'POST',
    body: payload,
  });
  return result.dj;
};

export const updateDjProfile = async (id, payload) => {
  const result = await callAuthedApi(`/api/admin/djs/${id}`, {
    method: 'PATCH',
    body: payload,
  });
  return result.dj;
};

export const deleteDj = async (id) => {
  await callAuthedApi(`/api/admin/djs/${id}`, {
    method: 'DELETE',
  });
};
