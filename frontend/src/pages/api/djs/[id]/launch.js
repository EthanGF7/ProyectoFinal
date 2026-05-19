import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { resolveDjScript } from '../../../../../lib/dj-scripts';
import { ensureDjRunning } from '../../../../../lib/dj-runtime';

// Intenta resolver el DJ por filesystem (si el ID es un slug como "urbano")
function resolveDjLocalFolder(id) {
  const DJS_ROOT = path.resolve(process.cwd(), "..", "DJ's");
  try {
    const entries = fs.readdirSync(DJS_ROOT, { withFileTypes: true });
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      if (e.name.toLowerCase() === id.toString().toLowerCase()) {
        return e.name;
      }
    }
  } catch (err) {
    console.warn("[launch] No se pudo leer DJS_ROOT:", err);
  }
  return null;
}

export default async function handler(req, res) {
  const { id, nombre } = req.query;

  if (!['GET', 'POST'].includes(req.method)) {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  if (!id) {
    return res.status(400).json({ error: 'ID de DJ no proporcionado' });
  }

  // Intenta resolver por UUID primero
  let resolved = resolveDjScript(id.toString(), nombre ? nombre.toString() : null);

  // Si no funciona, intenta por slug directo (para casos como /djs/urbano)
  if (!resolved) {
    const localFolder = resolveDjLocalFolder(id);
    if (localFolder) {
      resolved = resolveDjScript(localFolder);
    }
  }

  if (!resolved) {
    return res.status(404).json({
      error: 'DJ no encontrado o sin script asociado',
      hint: "Añade el UUID del DJ a DJ_SCRIPTS en frontend/lib/dj-scripts.ts",
    });
  }

  if (!fs.existsSync(resolved.scriptPath)) {
    return res.status(404).json({ error: 'Script .py no encontrado', scriptPath: resolved.scriptPath });
  }

  try {
    const info = await ensureDjRunning({
      key: id.toString(),
      folderName: resolved.folderName,
      folder: resolved.folder,
      scriptPath: resolved.scriptPath,
    });

    return res.status(200).json({
      ok: true,
      port: info.port,
      dj: resolved.folderName,
      script: resolved.scriptPath,
      alreadyRunning: info.alreadyRunning,
    });
  } catch (err) {
    console.error('[launch] Error arrancando player:', err);
    return res.status(500).json({
      error: err.message || 'No se pudo arrancar el player local',
      stderr: err.stderr,
    });
  }
}
