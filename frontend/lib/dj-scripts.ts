import fs from "node:fs";
import path from "node:path";

// Raíz absoluta donde viven las carpetas de cada DJ.
// Se calcula desde process.cwd() (en Next dev/build es la carpeta `frontend/`)
// subiendo un nivel hasta la raíz del repo y entrando en `DJ's`.
const DJS_ROOT = path.resolve(process.cwd(), "..", "DJ's");

// Map: UUID de Supabase → nombre real de carpeta dentro de DJ's/
// El .py dentro de cada carpeta debe llamarse igual que la carpeta
// (Flamenco/Flamenco.py, Nexus/Nexus.py, Pop/POP.py, Urbano/Urbano.py).
//
// Nota: en Supabase el DJ figura como "Nexu" pero la carpeta es "Nexus".
// Mapeamos el UUID de "Nexu" → carpeta "Nexus" que es la que existe en disco.
const DJ_SCRIPTS: Record<string, string> = {
  "f7990e69-2c1a-4164-aed3-3323d9e3cae6": "Flamenco",
  "d95df9a6-4815-4a59-b590-3babe9db98c5": "Nexus",
  "941f2878-72d4-41af-b349-64b9d4799325": "Pop",
  "d0da206a-e73c-46c3-b6f8-26f42c79a0d7": "Urbano",
};

// Slugs aceptados como fallback si el id NO es un UUID conocido.
// Permite navegar también por /djs/flamenco, /djs/nexus, etc.
const SLUG_TO_FOLDER: Record<string, string> = {
  flamenco: "Flamenco",
  nexus: "Nexus",
  nexu: "Nexus", // por si en algún sitio se usa el nombre artístico tal cual
  pop: "Pop",
  urbano: "Urbano",
};

function slugify(value: string): string {
  return value
    .toString()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "")
    .replace(/--+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/**
 * Encuentra el nombre REAL de la carpeta del DJ dentro de DJ's/.
 * En Windows el fs es case-insensitive, pero queremos el nombre exacto
 * para construir correctamente la ruta al .py.
 */
function resolveActualFolderName(targetFolderName: string): string | null {
  try {
    const entries = fs.readdirSync(DJS_ROOT, { withFileTypes: true });
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      if (e.name.toLowerCase() === targetFolderName.toLowerCase()) {
        return e.name;
      }
    }
  } catch (err) {
    console.warn("[dj-scripts] No se pudo leer DJS_ROOT:", DJS_ROOT, err);
  }
  return null;
}

/**
 * Dado un id (UUID de Supabase, slug, o nombre artístico opcional),
 * devuelve la ruta absoluta al .py del DJ y la carpeta que lo contiene.
 * Devuelve null si no se encuentra.
 */
export function resolveDjScript(
  djId: string,
  nombreArtistico?: string | null
): { folder: string; scriptPath: string; folderName: string } | null {
  // 1. Por UUID exacto
  let target = DJ_SCRIPTS[djId];

  // 2. Por slug del id (por si llega "flamenco" en vez del UUID)
  if (!target) {
    const s = slugify(djId);
    if (SLUG_TO_FOLDER[s]) target = SLUG_TO_FOLDER[s];
  }

  // 3. Por slug del nombre artístico
  if (!target && nombreArtistico) {
    const s = slugify(nombreArtistico);
    if (SLUG_TO_FOLDER[s]) target = SLUG_TO_FOLDER[s];
  }

  // 4. Buscar en filesystem si nada coincide (fallback)
  if (!target) {
    const localName = resolveActualFolderName(djId);
    if (localName) target = localName;
  }

  if (!target) return null;

  const realFolderName = resolveActualFolderName(target);
  if (!realFolderName) return null;

  const folder = path.join(DJS_ROOT, realFolderName);

  // El .py se llama igual que la carpeta. Probamos varias variantes
  // por si está en mayúsculas (POP.py) o minúsculas.
  const candidates = [
    `${realFolderName}.py`,
    `${realFolderName.toUpperCase()}.py`,
    `${realFolderName.toLowerCase()}.py`,
    "player.py", // fallback por compatibilidad
  ];

  for (const c of candidates) {
    const full = path.join(folder, c);
    if (fs.existsSync(full)) {
      return { folder, scriptPath: full, folderName: realFolderName };
    }
  }

  return null;
}

export function listLocalDjScripts(): { folder: string; scriptPath: string; folderName: string }[] {
  try {
    return fs
      .readdirSync(DJS_ROOT, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && entry.name.toLowerCase() !== "core")
      .map((entry) => resolveDjScript(entry.name))
      .filter((resolved): resolved is { folder: string; scriptPath: string; folderName: string } => Boolean(resolved));
  } catch (err) {
    console.warn("[dj-scripts] No se pudieron listar DJs locales:", DJS_ROOT, err);
    return [];
  }
}

// Compatibilidad con el helper antiguo
export function getDjScriptPath(djId: string): string | null {
  return resolveDjScript(djId)?.scriptPath ?? null;
}
