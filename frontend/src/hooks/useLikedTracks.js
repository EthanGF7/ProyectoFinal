import { useCallback, useEffect, useRef, useState } from 'react';
import { callAuthedApi } from '../utils/apiClient';

const DEFAULT_ERROR_MESSAGE = 'No se pudieron cargar tus canciones favoritas.';

export const useLikedTracks = ({ enabled = true, limit = 20 } = {}) => {
  const [likedTracks, setLikedTracks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const mountedRef = useRef(true);

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  const fetchLikedTracks = useCallback(async () => {
    if (!enabled) {
      if (mountedRef.current) {
        setLikedTracks([]);
        setLoading(false);
        setError('');
      }
      return;
    }

    if (mountedRef.current) {
      setLoading(true);
      setError('');
    }

    try {
      const query = limit ? `?limit=${encodeURIComponent(limit)}` : '';
      const payload = await callAuthedApi(`/api/user/liked-tracks${query}`);
      if (!mountedRef.current) return;
      setLikedTracks(payload?.likedTracks || []);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err?.message || DEFAULT_ERROR_MESSAGE);
      setLikedTracks([]);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [enabled, limit]);

  useEffect(() => {
    fetchLikedTracks();
  }, [fetchLikedTracks]);

  useEffect(() => {
    if (!enabled) {
      setLikedTracks([]);
      setError('');
      setLoading(false);
    }
  }, [enabled]);

  return {
    likedTracks,
    loading,
    error,
    refresh: fetchLikedTracks,
  };
};
