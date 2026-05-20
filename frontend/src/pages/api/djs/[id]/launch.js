import fs from 'fs';
import { resolveDjScript } from '../../../../../lib/dj-scripts';
import { ensureDjRunning } from '../../../../../lib/dj-runtime';

export default async function handler(req, res) {
  const { id, nombre } = req.query;

  if (!['GET', 'POST'].includes(req.method)) {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  if (!id) {
    return res.status(400).json({ error: 'ID de DJ no proporcionado' });
  }

  let resolved = resolveDjScript(id.toString(), nombre ? nombre.toString() : null);

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
      key: resolved.folderName,
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
