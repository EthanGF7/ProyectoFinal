import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../utils/supabase';
import { callAuthedApi } from '../utils/apiClient';
import { syncUserProfile } from '../utils/profileSync';
import { debugLog } from '../utils/logs';

export const useAppUser = () => {
  const [appUser, setAppUser] = useState(null);
  const [supabaseUser, setSupabaseUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAppUser = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

      if (sessionError) {
        throw sessionError;
      }

      const sessionUser = sessionData?.session?.user || null;
      setSupabaseUser(sessionUser);
      debugLog('Supabase session user', sessionUser?.id, sessionUser?.user_metadata);

      if (!sessionUser) {
        setAppUser(null);
        return;
      }

      try {
        debugLog('Attempting profile sync');
        await syncUserProfile();
      } catch (syncErr) {
        console.warn('[useAppUser] No se pudo sincronizar perfil antes de cargarlo:', syncErr?.message || syncErr);
      }

      let profile = null;
      try {
        const payload = await callAuthedApi('/api/profile/me');
        debugLog('Profile from API', payload);
        profile = payload?.user || null;
      } catch (apiError) {
        console.warn('[useAppUser] No se pudo obtener el perfil desde la API:', apiError?.message || apiError);
      }

      if (profile) {
        setAppUser(profile);
        debugLog('App user set via API', profile);
      } else {
        setAppUser({
          id: sessionUser.id,
          email: sessionUser.email,
          username: sessionUser.user_metadata?.username || sessionUser.email,
          tipo_usuario: sessionUser.user_metadata?.tipo_usuario || 'usuario_normal',
        });
        debugLog('App user fallback metadata', sessionUser.user_metadata);
      }
    } catch (err) {
      console.error('[useAppUser] No se pudo obtener el usuario:', err);
      setError(err.message || 'Error al cargar el usuario');
      if (supabaseUser) {
        setAppUser({
          id: supabaseUser.id,
          email: supabaseUser.email,
          username: supabaseUser.user_metadata?.username || supabaseUser.email,
          tipo_usuario: supabaseUser.user_metadata?.tipo_usuario || 'usuario_normal',
        });
      } else {
        setAppUser(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAppUser();

    const { data: authListener } = supabase.auth.onAuthStateChange(() => {
      loadAppUser();
    });

    return () => authListener?.subscription?.unsubscribe();
  }, [loadAppUser]);

  return { appUser, supabaseUser, loading, error, refresh: loadAppUser };
};
