import { spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import { resolveDjScript } from '../../../../../lib/dj-scripts';

const DJ_PORTS = {
  Flamenco: 8765,
  Nexus:    8766,
  Pop:      8767,
  Urbano:   8768,
};

const running = new Map();

function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

async function ensureRunning(key, folder, scriptPath, port) {
  const ex = running.get(key);
  if (ex && ex.exitCode === null) return true;
  if (!fs.existsSync(scriptPath)) return false;
  const py = process.env.PYTHON || (os.platform() === 'win32' ? 'python' : 'python3');
  const child = spawn(py, [scriptPath, '--port', port.toString()], {
    cwd: folder, detached: true, stdio: 'ignore',
  });
  child.on('error', () => running.delete(key));
  child.unref();
  running.set(key, child);
  await wait(1500);
  return true;
}

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();
  const { id, nombre, ...params } = req.query;
  if (!id) return res.status(400).json({ error: 'ID requerido' });

  const resolved = resolveDjScript(id.toString(), nombre ? nombre.toString() : null);
  if (!resolved) return res.status(404).json({ error: 'DJ no encontrado' });

  const port = DJ_PORTS[resolved.folderName] ?? 8765;
  const ok = await ensureRunning(id.toString(), resolved.folder, resolved.scriptPath, port);
  if (!ok) return res.status(500).json({ error: 'No se pudo arrancar el .py del DJ' });

  const qs = new URLSearchParams(params).toString();
  try {
    const r = await fetch(`http://localhost:${port}/api/next${qs ? '?' + qs : ''}`);
    const data = await r.json();
    return res.status(r.status).json(data);
  } catch (e) {
    return res.status(502).json({ error: 'Sin respuesta del player local' });
  }
}
