import fs from 'fs';
import path from 'path';

const LOCAL_DJS_ROOT = path.resolve(process.cwd(), '..', "DJ's");
const AUDIO_EXTS = new Set(['.mp3','.wav','.ogg','.flac','.aac','.m4a']);

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

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).end();
  const { id } = req.query;
  const folder = await findFolder(id).catch(() => null);
  if (!folder) return res.status(404).json([]);

  const songsDir = path.join(folder, 'musica', 'canciones');
  const jsonDir  = path.join(folder, 'musica', 'json');

  let files = [];
  try { files = await fs.promises.readdir(songsDir); } catch { return res.json([]); }

  const tracks = [];
  for (const file of files.sort()) {
    const ext = path.extname(file).toLowerCase();
    if (!AUDIO_EXTS.has(ext)) continue;
    const stem = path.basename(file, ext);
    let meta = {};
    try {
      meta = JSON.parse(await fs.promises.readFile(path.join(jsonDir, stem+'.json'), 'utf-8'));
    } catch {}
    tracks.push({
      name: stem, file,
      bpm:                  meta.bpm || 0,
      energia:              meta.energia || 50,
      key:                  meta.key || '',
      duracion_segundos:    meta.duracion_segundos || 0,
      puede_salir:          meta.puede_salir ?? null,
      puede_empezar_mezcla: meta.puede_empezar_mezcla ?? null,
      debe_sonar_sola:      meta.debe_sonar_sola ?? null,
      intro_fin:            meta.intro_fin ?? null,
      tiene_voz_inicio:     meta.tiene_voz_inicio || false,
      beat_times:           meta.beat_times || [],
      energia_por_segundo:  meta.energia_por_segundo || [],
      start_position: meta.puede_empezar_mezcla > 0 ? parseFloat(meta.puede_empezar_mezcla)
                    : meta.intro_fin > 0 ? parseFloat(meta.intro_fin) : 0,
    });
  }
  res.setHeader('Cache-Control','no-store');
  return res.json(tracks);
}