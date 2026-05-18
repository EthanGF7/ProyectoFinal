import fs from 'fs';
import path from 'path';
import { resolveDjScript } from '../../../../../../lib/dj-scripts';
import { spawn } from 'child_process';

const DJ_PORTS = {
  Flamenco: 8765,
  Nexus:    8766,
  Pop:      8767,
  Urbano:   8768,
};

const running = new Map();

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer(port, timeout = 5000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    try {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), 1000);
      const res = await fetch(`http://127.0.0.1:${port}/api/library`, {
        method: 'GET',
        signal: controller.signal,
      });
      clearTimeout(id);
      if (res.ok) return true;
    } catch (err) {
      // ignore and retry
    }
    await wait(250);
  }
  return false;
}

async function ensureRunning(key, folder, scriptPath, port) {
  const existing = running.get(key);
  if (existing && existing.exitCode === null) return await waitForServer(port);
  if (!fs.existsSync(scriptPath)) return false;

  const py = process.env.PYTHON || 'C:\\Users\\yeray\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe';
  const child = spawn(py, [scriptPath, '--port', port.toString()], {
    cwd: folder,
    detached: true,
    stdio: 'ignore',
  });

  child.on('error', () => running.delete(key));
  child.unref();
  running.set(key, child);
  return await waitForServer(port, 8000);
}

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

export default async function handler(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
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

  const port = DJ_PORTS[resolved.folderName] ?? 8765;
  const key = rawId.toString();
  const started = await ensureRunning(key, resolved.folder, resolved.scriptPath, port);
  if (!started) {
    return res.status(500).json({ error: 'No se pudo arrancar el .py del DJ' });
  }

  const pathParam = req.query.path;
  const proxyPath = Array.isArray(pathParam)
    ? pathParam.join('/')
    : pathParam || '';
  const targetPath = proxyPath ? `/${proxyPath}` : '/';

  const originalUrl = new URL(req.url, 'http://localhost');
  const targetUrl = new URL(`http://localhost:${port}${targetPath}`);
  targetUrl.search = originalUrl.search;

  try {
    const targetRes = await fetch(targetUrl.href, {
      method: req.method,
      headers: {
        accept: req.headers.accept || '*/*',
        'user-agent': req.headers['user-agent'] || 'Mozilla/5.0',
        referer: req.headers['referer'] || undefined,
      },
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
