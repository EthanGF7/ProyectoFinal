import { callAuthedApi } from './apiClient';

export const fetchDjProfile = async () => {
  const result = await callAuthedApi('/api/dj/profile');
  return result.profile || null;
};

export const updateDjProfile = async (payload) => {
  const result = await callAuthedApi('/api/dj/profile', {
    method: 'PATCH',
    body: payload,
  });
  return result.profile;
};

export const fetchDjPlaylists = async () => {
  const result = await callAuthedApi('/api/dj/playlists');
  return result.playlists || [];
};

export const createDjPlaylist = async (payload) => {
  const result = await callAuthedApi('/api/dj/playlists', {
    method: 'POST',
    body: payload,
  });
  return result.playlist;
};

export const updateDjPlaylist = async (id, payload) => {
  const result = await callAuthedApi(`/api/dj/playlists/${id}`, {
    method: 'PATCH',
    body: payload,
  });
  return result.playlist;
};

export const deleteDjPlaylist = async (id) => {
  await callAuthedApi(`/api/dj/playlists/${id}`, {
    method: 'DELETE',
  });
};
