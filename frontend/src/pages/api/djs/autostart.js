import { listLocalDjScripts } from '../../../../lib/dj-scripts';
import { ensureDjRunning } from '../../../../lib/dj-runtime';

export default async function handler(req, res) {
  if (!['GET', 'POST'].includes(req.method)) {
    return res.status(405).json({ error: 'Método no permitido' });
  }

  const scripts = listLocalDjScripts();

  if (scripts.length === 0) {
    return res.status(200).json({ ok: true, started: [], failed: [] });
  }

  const results = await Promise.allSettled(
    scripts.map(async (script) => {
      const info = await ensureDjRunning({
        key: script.folderName,
        folderName: script.folderName,
        folder: script.folder,
        scriptPath: script.scriptPath,
      });

      return {
        dj: script.folderName,
        port: info.port,
        alreadyRunning: info.alreadyRunning,
      };
    })
  );

  const started = [];
  const failed = [];

  results.forEach((result, index) => {
    const script = scripts[index];
    if (result.status === 'fulfilled') {
      started.push(result.value);
      return;
    }

    failed.push({
      dj: script.folderName,
      error: result.reason?.message || String(result.reason),
      stderr: result.reason?.stderr || null,
    });
  });

  return res.status(200).json({ ok: failed.length === 0, started, failed });
}
