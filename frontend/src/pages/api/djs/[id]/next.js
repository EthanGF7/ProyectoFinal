import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

const LOCAL_DJS_ROOT = path.resolve(process.cwd(), '..', "DJ's");
const PORT = 8765;
const running = new Map();

function slugify(v) {
  return v.toString().trim().toLowerCase()
    .replace(/\s+/g,'-').replace(/[^a-z0-9-]/g,'')
    .replace(/--+/g,'-').replace(/^-+|-+$/g,'');
}

async function findFolder(id) {
  const entries = await fs.promises.readdir(LOCAL_DJS_ROOT, { withFileTypes: true });
  for (const e of entries) {
    if (e.isDirectory() && slugify(e.name) === slugify(id))
      return path.join(LOCAL_DJS_ROOT, e.name);
  }
  return null;
}

function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

async function ensureRunning(id, folder) {
  const ex = running.get(id);
  if (ex && ex.exitCode === null) return true;
  const playerPath = path.join(folder, 'player.py');
  if (!fs.existsSync(playerPath)) return false;
  const py = process.env.PYTHON || 'C:\\Users\\yeray\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe';
  const child = spawn(py, [playerPath, '--port', PORT.toString()], {
    cwd: folder, detached: true, stdio: 'ignore'
  });
  child.on('error', () => running.delete(id));
  child.unref();
  running.set(id, child);
  await wait(1500);
  return true;
}

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();
  const { id, ...params } = req.query;
  const folder = await findFolder(id.toString()).catch(() => null);
  if (!folder) return res.status(404).json({ error: 'DJ no encontrado' });
  const ok = await ensureRunning(id.toString(), folder);
  if (!ok) return res.status(500).json({ error: 'No se pudo arrancar player.py' });
  const qs = new URLSearchParams(params).toString();
  try {
    const r = await fetch(`http://localhost:${PORT}/api/next${qs ? '?'+qs : ''}`);
    const data = await r.json();
    return res.status(r.status).json(data);
  } catch(e) {
    return res.status(502).json({ error: 'Sin respuesta del player local' });
  }
}