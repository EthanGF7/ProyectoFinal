import fs from 'fs';
import path from 'path';
import { resolveDjScript } from '../../../../../lib/dj-scripts';

const AUDIO_EXTS = new Set(['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a']);

function normalizeFileName(fileName) {
  return path.basename(fileName.toString());
}

function safeId(value) {
  return value.toString().trim().replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-_\.]/g, '').slice(0, 200);
}

function parseJsonFile(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) || {};
  } catch {
    return {};
  }
}

function getAlternateDjRoot(resolved) {
  const scriptDir = path.dirname(resolved.scriptPath);
  return path.resolve(scriptDir, '..', 'djs', resolved.folderName);
}

function getCandidateSongDirs(resolved) {
  const alternateRoot = getAlternateDjRoot(resolved);
  return [...new Set([
    path.join(resolved.folder, 'musica', 'canciones'),
    path.join(resolved.folder, 'canciones'),
    resolved.folder,
    path.join(alternateRoot, 'musica', 'canciones'),
    path.join(alternateRoot, 'canciones'),
    alternateRoot,
  ])];
}

function getCandidateJsonDirs(resolved) {
  const alternateRoot = getAlternateDjRoot(resolved);
  return [...new Set([
    path.join(resolved.folder, 'musica', 'json'),
    path.join(resolved.folder, 'json'),
    path.join(alternateRoot, 'musica', 'json'),
    path.join(alternateRoot, 'json'),
  ])];
}

function buildAudioUrl(djId, fileName) {
  return `/api/djs/${encodeURIComponent(djId)}/audio?file=${encodeURIComponent(fileName)}`;
}

export default async function handler(req, res) {
  if (req.method !== 'GET') {
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

  const songDirs = getCandidateSongDirs(resolved);
  const jsonDirs = getCandidateJsonDirs(resolved);
  let tracks = [];

  try {
    for (const songsDir of songDirs) {
      if (!fs.existsSync(songsDir)) continue;
      const entries = await fs.promises.readdir(songsDir, { withFileTypes: true });
      for (const entry of entries) {
        if (!entry.isFile()) continue;
        const fileName = normalizeFileName(entry.name);
        const ext = path.extname(fileName).toLowerCase();
        if (!AUDIO_EXTS.has(ext)) continue;

        const stem = path.basename(fileName, ext);
        let meta = {};
        for (const jsonDir of jsonDirs) {
          const metaPath = path.join(jsonDir, `${stem}.json`);
          if (fs.existsSync(metaPath)) {
            meta = parseJsonFile(metaPath);
            break;
          }
        }

        const duration = Number(meta.duracion_segundos || meta.duration || 0) || 0;
        const title = meta.titulo || meta.title || stem;
        const artist = meta.artist || meta.artista || meta.nombre_artistico || undefined;

        tracks.push({
          id: `${safeId(resolved.folderName)}-${safeId(stem)}`,
          title,
          artist,
          url: buildAudioUrl(rawId.toString(), fileName),
          duration,
          file: fileName,
          name: stem,
          bpm: Number(meta.bpm || 0) || 0,
          energia: Number(meta.energia || 50) || 50,
          key: meta.key || '',
          estilo: meta.estilo || '',
          duracion_segundos: duration,
          puede_salir: meta.puede_salir ?? null,
          puede_empezar_mezcla: meta.puede_empezar_mezcla ?? null,
          debe_sonar_sola: meta.debe_sonar_sola ?? null,
          intro_fin: meta.intro_fin ?? null,
          tiene_voz_inicio: meta.tiene_voz_inicio || false,
          beat_times: Array.isArray(meta.beat_times) ? meta.beat_times : [],
          energia_por_segundo: Array.isArray(meta.energia_por_segundo) ? meta.energia_por_segundo : [],
          start_position: Number(meta.puede_empezar_mezcla > 0 ? meta.puede_empezar_mezcla : meta.intro_fin || 0) || 0,
        });
      }
      if (tracks.length > 0) break;
    }

    tracks = tracks.sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: 'base' }));
    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).json(tracks);
  } catch (error) {
    console.error('[library] Error leyendo la librería del DJ:', error);
    return res.status(500).json({ error: 'Error interno leyendo la librería de canciones', details: error.message });
  }
}
