import { resolveDjScript } from '../../../../../../lib/dj-scripts';
import { ensureDjRunning } from '../../../../../../lib/dj-runtime';
import { getAuthenticatedUser } from '../../../../../utils/apiAuth';
import { supabaseAdmin } from '../../../../../utils/supabaseAdmin';

function buildProxyPrefix(id) {
  return `/api/djs/${encodeURIComponent(id)}/proxy`;
}

function getTrackDisplayName(file) {
  if (!file || typeof file !== 'string') return '';
  try {
    return decodeURIComponent(file).split('/').pop();
  } catch (err) {
    return file.split('/').pop();
  }
}

function rewriteProxyBody(body, id) {
  const prefix = buildProxyPrefix(id);
  const rewritten = body
    .replace(/(["'`(])\/api\//g, `$1${prefix}/api/`)
    .replace(/(["'`(])\/audio\//g, `$1${prefix}/audio/`)
    .replace(/(["'`(])\/engine\.js/g, `$1${prefix}/engine.js`);

  if (!/<\/head>/i.test(rewritten)) return rewritten;

  return rewritten.replace(/<\/head>/i, `
<script>
(function(){
  var nexusAuthToken = null;
  function findStoredToken() {
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var key = localStorage.key(i);
        if (!key || key.indexOf('auth-token') === -1) continue;
        var raw = localStorage.getItem(key);
        if (!raw) continue;
        var parsed = JSON.parse(raw);
        var token = parsed && (parsed.access_token || (parsed.currentSession && parsed.currentSession.access_token));
        if (token) return token;
      }
    } catch (e) {}
    return null;
  }
  window.addEventListener('message', function(e) {
    if (e.origin !== window.location.origin) return;
    if (e.data && e.data.type === 'nexus-auth-token' && e.data.accessToken) {
      nexusAuthToken = e.data.accessToken;
    }
  });
  var originalFetch = window.fetch.bind(window);
  window.fetch = function(input, init) {
    init = init || {};
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    var token = nexusAuthToken || findStoredToken();
    if (token && (url.indexOf('${prefix}/api/') === 0 || url.indexOf('/api/djs/') === 0)) {
      var headers = new Headers(init.headers || {});
      headers.set('Authorization', 'Bearer ' + token);
      init.headers = headers;
    }
    return originalFetch(input, init);
  };
})();
</script>
</head>`);
}

async function getUserPrefs(req, djId) {
  const { user } = await getAuthenticatedUser(req);
  if (!user) return null;

  const { data, error } = await supabaseAdmin
    .from('track_reactions')
    .select('track_name, reaction')
    .eq('user_id', user.id)
    .eq('dj_id', djId);

  if (error) {
    console.error('[proxy] Error leyendo preferencias:', error);
    return {};
  }

  return (data || []).reduce((acc, row) => {
    const key = row.track_name;
    const displayKey = getTrackDisplayName(key);
    acc[key] = row.reaction;
    if (displayKey) acc[displayKey] = row.reaction;
    return acc;
  }, {});
}

function mergeDislikesIntoPlayed(targetUrl, prefs) {
  if (!prefs || typeof prefs !== 'object') return;

  const disliked = Object.entries(prefs)
    .filter(([, reaction]) => Number(reaction) === -1)
    .map(([trackName]) => trackName)
    .filter(Boolean);

  if (!disliked.length) return;

  let played = [];
  try {
    played = JSON.parse(targetUrl.searchParams.get('played') || '[]');
    if (!Array.isArray(played)) played = [];
  } catch (err) {
    played = [];
  }

  const merged = new Set(played);
  disliked.forEach((trackName) => {
    merged.add(trackName);
    const displayName = getTrackDisplayName(trackName);
    if (displayName) merged.add(displayName);
  });

  targetUrl.searchParams.set('played', JSON.stringify([...merged]));
}

async function handleUserLike(req, res, djId) {
  const { user, error } = await getAuthenticatedUser(req);
  if (error || !user) return res.status(401).json({ error: error || 'No hay sesión activa' });

  let body = typeof req.body === 'object' && req.body ? req.body : {};
  if (!Object.keys(body).length && typeof req.body === 'string') {
    try {
      body = JSON.parse(req.body);
    } catch (err) {
      body = {};
    }
  }
  const file = body.file || '';
  const action = body.action || '';

  if (!file || !['like', 'dislike', 'clear'].includes(action)) {
    return res.status(400).json({ error: 'Preferencia inválida' });
  }

  if (action === 'clear') {
    const { error: deleteError } = await supabaseAdmin
      .from('track_reactions')
      .delete()
      .eq('user_id', user.id)
      .eq('dj_id', djId)
      .eq('track_name', file);

    if (deleteError) return res.status(500).json({ error: 'No se pudo borrar la preferencia' });
    return res.status(200).json({ ok: true, file, action });
  }

  const { error: upsertError } = await supabaseAdmin
    .from('track_reactions')
    .upsert(
      {
        user_id: user.id,
        dj_id: djId,
        track_name: file,
        reaction: action === 'like' ? 1 : -1,
        updated_at: new Date().toISOString(),
      },
      { onConflict: 'user_id,dj_id,track_name' }
    );

  if (upsertError) {
    console.error('[proxy] Error guardando preferencia:', upsertError);
    return res.status(500).json({ error: 'No se pudo guardar la preferencia' });
  }

  try {
    await recordListenHistory(req, djId, djId, getTrackDisplayName(file) || file);
  } catch (err) {
    console.error('[proxy] Error registrando historial desde reacción:', err);
  }
  return res.status(200).json({ ok: true, file, action });
}

async function recordListenHistory(req, djId, djName, trackName) {
  if (!trackName) return;

  const { user, appUser } = await getAuthenticatedUser(req);
  const userId = appUser?.id || user?.id;
  if (!userId) return;

  const twoMinutesAgo = new Date(Date.now() - 2 * 60 * 1000).toISOString();
  const { data: recent, error: recentError } = await supabaseAdmin
    .from('user_listen_history')
    .select('id')
    .eq('user_id', userId)
    .eq('dj_id', djId)
    .eq('track_name', trackName)
    .gte('listened_at', twoMinutesAgo)
    .limit(1);

  if (!recentError && recent?.length) return;

  const { error } = await supabaseAdmin
    .from('user_listen_history')
    .insert({
      user_id: userId,
      dj_id: djId,
      dj_name: djName,
      track_name: trackName,
      listened_at: new Date().toISOString(),
    });

  if (error && error?.code !== '42P01') {
    console.error('[proxy] Error guardando historial:', error);
  }
}

export default async function handler(req, res) {
  if (!['GET', 'HEAD', 'POST'].includes(req.method)) {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  const rawId = Array.isArray(req.query.id) ? req.query.id[0] : req.query.id;
  if (!rawId) {
    return res.status(400).json({ error: 'ID de DJ no proporcionado' });
  }

  const resolved = resolveDjScript(rawId.toString());
  if (!resolved) {
    return res.status(404).json({ error: 'DJ no encontrado' });
  }

  let info;
  try {
    info = await ensureDjRunning({
      key: resolved.folderName,
      folderName: resolved.folderName,
      folder: resolved.folder,
      scriptPath: resolved.scriptPath,
    });
  } catch (err) {
    console.error('[proxy] No se pudo arrancar el DJ:', err);
    return res.status(500).json({
      error: err.message || 'No se pudo arrancar el .py del DJ',
      stderr: err.stderr,
    });
  }

  const port = info.port;
  const pathParam = req.query.path;
  const proxyPath = Array.isArray(pathParam) ? pathParam.join('/') : pathParam || '';
  const targetPath = proxyPath ? `/${proxyPath}` : '/';

  if (req.method === 'POST' && targetPath === '/api/like') {
    return handleUserLike(req, res, resolved.folderName);
  }

  if (req.method === 'GET' && targetPath === '/api/prefs') {
    const prefs = await getUserPrefs(req, resolved.folderName);
    return res.status(200).json(prefs || {});
  }

  const originalUrl = new URL(req.url, 'http://localhost');
  const targetUrl = new URL(`http://127.0.0.1:${port}${targetPath}`);
  targetUrl.search = originalUrl.search;

  if (req.method === 'GET' && targetPath === '/api/next') {
    const prefs = await getUserPrefs(req, resolved.folderName);
    if (prefs) {
      targetUrl.searchParams.set('prefs', JSON.stringify(prefs));
      mergeDislikesIntoPlayed(targetUrl, prefs);
    }
    await recordListenHistory(
      req,
      resolved.folderName,
      resolved.folderName,
      getTrackDisplayName(targetUrl.searchParams.get('current')) || targetUrl.searchParams.get('current')
    );
  }

  try {
    const targetRes = await fetch(targetUrl.href, {
      method: req.method,
      headers: {
        accept: req.headers.accept || '*/*',
        'content-type': req.headers['content-type'] || undefined,
        'user-agent': req.headers['user-agent'] || 'Mozilla/5.0',
        referer: req.headers['referer'] || undefined,
      },
      body: req.method === 'POST' ? JSON.stringify(req.body || {}) : undefined,
    });

    const contentType = targetRes.headers.get('content-type') || '';
    res.status(targetRes.status);

    for (const [name, value] of targetRes.headers.entries()) {
      if (name === 'content-length') continue;
      if (name === 'set-cookie') continue;
      if (name === 'content-type') {
        res.setHeader('content-type', value);
      } else {
        res.setHeader(name, value);
      }
    }

    if (contentType.includes('text/html') || contentType.includes('javascript')) {
      const text = await targetRes.text();
      const rewritten = rewriteProxyBody(text, rawId.toString());
      return res.send(rewritten);
    }

    const buffer = Buffer.from(await targetRes.arrayBuffer());
    res.setHeader('content-length', buffer.length);
    return res.end(buffer);
  } catch (err) {
    console.error('[proxy] Error proxying DJ server:', err);
    return res.status(502).json({ error: 'No se pudo conectar con el servidor local del DJ' });
  }
}
