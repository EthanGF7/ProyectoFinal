import { resolveDjScript } from '../../../../../../lib/dj-scripts';
import { ensureDjRunning } from '../../../../../../lib/dj-runtime';
import { getAuthenticatedUser } from '../../../../../utils/apiAuth';
import { supabaseAdmin } from '../../../../../utils/supabaseAdmin';

function buildProxyPrefix(id) {
  return `/api/djs/${encodeURIComponent(id)}/proxy`;
}

function rewriteProxyBody(body, id) {
  const prefix = buildProxyPrefix(id);
  return body
    .replace(/(["'`(])\/api\//g, `$1${prefix}/api/`)
    .replace(/(["'`(])\/audio\//g, `$1${prefix}/audio/`)
    .replace(/(["'`(])\/engine\.js/g, `$1${prefix}/engine.js`);
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

  return Object.fromEntries((data || []).map((row) => [row.track_name, row.reaction]));
}

async function handleUserLike(req, res, djId) {
  const { user, error } = await getAuthenticatedUser(req);
  if (error || !user) return res.status(401).json({ error: error || 'No hay sesión activa' });

  const body = typeof req.body === 'object' && req.body ? req.body : {};
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

  return res.status(200).json({ ok: true, file, action });
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
    if (prefs) targetUrl.searchParams.set('prefs', JSON.stringify(prefs));
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
