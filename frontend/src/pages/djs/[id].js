// Página de DJ: abre la UI del DJ dentro del mismo host de la web.
// La UI del DJ se carga mediante un iframe que consume el servidor local a través de un proxy.
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { supabase } from '../../utils/supabase';

export default function FichaDj() {
  const router = useRouter();
  const { id } = router.query;
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);
  const [iframeSrc, setIframeSrc] = useState(null);
  const [iframeEl, setIframeEl] = useState(null);

  useEffect(() => {
    if (!iframeEl || status !== 'ready') return undefined;

    let cancelled = false;

    async function sendToken() {
      const { data } = await supabase.auth.getSession();
      const accessToken = data?.session?.access_token;
      if (!cancelled && accessToken && iframeEl.contentWindow) {
        iframeEl.contentWindow.postMessage({ type: 'nexus-auth-token', accessToken }, window.location.origin);
      }
    }

    sendToken();
    const interval = setInterval(sendToken, 1000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [iframeEl, status]);

  useEffect(() => {
    if (!djIdParam) return;

    async function launch() {
      try {
        const res = await fetch(`/api/djs/${encodeURIComponent(id)}/launch`, {
          method: 'POST',
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.error || `HTTP ${res.status}`);
        }

        setIframeSrc(`/api/djs/${encodeURIComponent(id)}/proxy/`);
        setStatus('ready');
      } catch (err) {
        setStatus('error');
        setError(err instanceof Error ? err.message : String(err));
      }
    }

    launch();
  }, [id]);

  if (!id) {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          background: '#07080f',
          color: '#c8ff00',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'IBM Plex Mono, monospace',
          fontSize: '12px',
          letterSpacing: '3px',
          textTransform: 'uppercase',
        }}
      >
        Cargando cabina…
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          background: '#07080f',
          color: '#c8ff00',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: '18px',
          padding: '24px',
          textAlign: 'center',
          fontFamily: 'IBM Plex Mono, monospace',
          fontSize: '14px',
          letterSpacing: '1px',
        }}
      >
        <div style={{ fontSize: '20px', fontWeight: 700, color: '#ff6b6b' }}>Error arrancando el DJ</div>
        <div>{error}</div>
        <button
          onClick={() => router.push('/djs')}
          style={{
            marginTop: '16px',
            padding: '10px 18px',
            borderRadius: '10px',
            border: '1px solid #c8ff00',
            background: 'transparent',
            color: '#c8ff00',
            cursor: 'pointer',
          }}
        >
          Volver a la lista de DJs
        </button>
      </div>
    );
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: '#07080f', overflow: 'hidden' }}>
      {status === 'loading' && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: '12px',
            color: '#c8ff00',
            fontFamily: 'IBM Plex Mono, monospace',
            textAlign: 'center',
            padding: '24px',
          }}
        >
          <div style={{ fontSize: '20px', fontWeight: 700 }}>Abriendo el DJ...</div>
          <div>Conectando el servidor local al mismo host de la web.</div>
          <div style={{ color: '#7cfc00' }}>Mantente en esta página mientras se carga.</div>
        </div>
      )}

      {status === 'ready' && iframeSrc && (
        <iframe
          ref={setIframeEl}
          title="DJ Player"
          src={iframeSrc}
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      )}
    </div>
  );
}
