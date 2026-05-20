import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { callAuthedApi } from '../utils/apiClient';

const DEFAULT_ERROR_MESSAGE = 'No se pudo cargar tu historial reciente.';
const MAX_LIMIT = 50;

const normalizeLimit = (value) => {
  if (typeof value !== 'number') return 10;
  if (Number.isNaN(value) || value <= 0) return 10;
  return Math.min(Math.floor(value), MAX_LIMIT);
};

export const useListenHistory = ({ enabled = true, limit = 10, djId = null } = {}) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [serverStats, setServerStats] = useState(null);
  const mountedRef = useRef(true);
  const normalizedLimit = normalizeLimit(limit);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const getDjKey = useCallback((item) => {
    if (!item) return 'desconocido';
    return item.dj_id || item.dj_name || 'desconocido';
  }, []);

  const fetchHistory = useCallback(async () => {
    if (!enabled) {
      if (mountedRef.current) {
        setHistory([]);
        setLoading(false);
        setError('');
        setServerStats(null);
      }
      return;
    }

    if (mountedRef.current) {
      setLoading(true);
      setError('');
    }

    try {
      const params = new URLSearchParams();
      if (normalizedLimit) {
        params.set('limit', String(normalizedLimit));
      }
      if (djId) {
        params.set('djId', djId);
      }

      const path = `/api/user/listen-history${params.toString() ? `?${params.toString()}` : ''}`;
      const payload = await callAuthedApi(path);

      if (!mountedRef.current) return;

      setHistory(payload?.history || []);
      if (payload?.stats) {
        setServerStats(payload.stats);
      }
    } catch (err) {
      if (!mountedRef.current) return;
      const message = err?.message || DEFAULT_ERROR_MESSAGE;
      setError(message === 'No hay sesión activa' && !enabled ? '' : message);
      if (message === 'No hay sesión activa') {
        setHistory([]);
        setServerStats(null);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [djId, enabled, normalizedLimit]);

  useEffect(() => {
    if (enabled) {
      fetchHistory();
    }
  }, [enabled, fetchHistory]);

  useEffect(() => {
    if (!enabled) {
      setHistory([]);
      setError('');
      setLoading(false);
      setServerStats(null);
    }
  }, [enabled]);

  const stats = useMemo(() => {
    if (!history || history.length === 0) {
      return {
        ...(serverStats || {}),
        total: 0,
        uniqueDjs: 0,
        lastListen: null,
        topDj: null,
      };
    }

    const uniqueDjs = new Map();
    history.forEach((item) => {
      const key = getDjKey(item);
      const name = item.dj_name || 'DJ desconocido';
      const current = uniqueDjs.get(key) || { name, count: 0, lastListen: null };
      current.count += 1;
      if (!current.lastListen || new Date(item.listened_at) > new Date(current.lastListen.listened_at)) {
        current.lastListen = item;
      }
      uniqueDjs.set(key, current);
    });

    const [topDjKey, topDjValue] = [...uniqueDjs.entries()].sort((a, b) => b[1].count - a[1].count)[0] || [null, null];

    return {
      ...(serverStats || {}),
      total: history.length,
      uniqueDjs: uniqueDjs.size,
      lastListen: history[0] || null,
      topDj: topDjKey ? { id: topDjKey, ...topDjValue } : null,
    };
  }, [getDjKey, history, serverStats]);

  const filteredByDj = useCallback(
    (targetDjId) => {
      if (!targetDjId) return history;
      return history.filter((item) => {
        if (!item) return false;
        const comparableId = getDjKey(item);
        return comparableId === targetDjId;
      });
    },
    [getDjKey, history],
  );

  return {
    history,
    loading,
    error,
    refresh: fetchHistory,
    stats,
    filterByDj: filteredByDj,
  };
};
