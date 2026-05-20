// Runtime compartido para arrancar y trackear los .py de los DJs.
// Usa globalThis para sobrevivir al hot-reload de Next.js dev.
import { spawn } from 'child_process';
import fs from 'fs';
import os from 'os';

// Ports are now fully dynamic - each DJ gets an OS-assigned port.
// Passing 0 tells the OS to select an available port automatically.
// The DJ scripts will print DJ_READY_PORT=<port> once bound.
const DEFAULT_PORTS = {
  Flamenco: 0,
  Nexus: 0,
  Pop: 0,
  Urbano: 0,
};

const STORE_KEY = '__DJ_RUNTIME_STORE__';
if (!globalThis[STORE_KEY]) {
  globalThis[STORE_KEY] = {
    // key (dj id) -> { child, port, folderName, startedAt }
    players: new Map(),
    // Promesas de arranque en curso para evitar dobles spawns concurrentes
    pending: new Map(),
  };
}
const store = globalThis[STORE_KEY];

function getPythonCommand() {
  if (process.env.PYTHON) return process.env.PYTHON;
  return os.platform() === 'win32' ? 'python' : 'python3';
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pingServer(port, timeoutMs = 800) {
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    const res = await fetch(`http://127.0.0.1:${port}/api/library`, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(id);
    return res.ok;
  } catch {
    return false;
  }
}

async function waitForServer(port, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await pingServer(port, 800)) return true;
    await wait(250);
  }
  return false;
}

function isAlive(child) {
  return child && child.exitCode === null && !child.killed;
}

/**
 * Arranca el .py si no está vivo y devuelve { port, alreadyRunning }.
 * Idempotente y seguro frente a llamadas concurrentes.
 */
export async function ensureDjRunning({ key, folderName, folder, scriptPath }) {
  // 1. ¿Ya tenemos un proceso vivo registrado?
  const existing = store.players.get(key);
  if (existing && isAlive(existing.child)) {
    if (await pingServer(existing.port, 1000)) {
      return { port: existing.port, alreadyRunning: true };
    }
    // Proceso vivo pero no responde: lo damos por muerto.
    try { existing.child.kill(); } catch {}
    store.players.delete(key);
  }

  // 2. ¿Hay arranque en curso? Esperarlo en vez de duplicar.
  if (store.pending.has(key)) {
    return store.pending.get(key);
  }

  const startPromise = startPythonPlayer({ key, folderName, folder, scriptPath });
  store.pending.set(key, startPromise);
  try {
    const result = await startPromise;
    return result;
  } finally {
    store.pending.delete(key);
  }
}

async function startPythonPlayer({ key, folderName, folder, scriptPath }) {
  // Con puertos dinámicos (puerto 0), el SO asigna uno libre.
  // El servidor Python imprime "DJ_READY_PORT=<port>" cuando está listo.
  const preferredPort = 0;

  if (!fs.existsSync(scriptPath)) {
    throw new Error(`Script .py no encontrado: ${scriptPath}`);
  }

  console.log(`[dj-runtime] Spawning ${folderName} at ${scriptPath} (dynamic port)`);
  console.log(`[dj-runtime] Python: ${getPythonCommand()}`);
  console.log(`[dj-runtime] CWD: ${folder}`);

  // -u  => unbuffered stdout/stderr (clave en Windows con pipes)
  // PYTHONUNBUFFERED=1 => doble seguro por si -u no se respeta
  // PYTHONIOENCODING=utf-8 => evita crashes por chars no-ascii en stdout
  const child = spawn(
    getPythonCommand(),
    ['-u', scriptPath, '--port', preferredPort.toString()],
    {
      cwd: folder,
      detached: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
      },
    }
  );

  child.on('error', (err) => {
    console.error('[dj-runtime] Spawn error:', err);
  });

  let resolvedPort = null;
  let stderrBuf = '';
  let stdoutBuf = '';

  child.stdout.on('data', (chunk) => {
    const text = chunk.toString();
    stdoutBuf += text;
    process.stdout.write(`[dj-runtime stdout] ${text}`);
    if (!resolvedPort) {
      const m = text.match(/DJ_READY_PORT=(\d+)/);
      if (m) {
        const p = parseInt(m[1], 10);
        if (p > 0) resolvedPort = p;
      }
    }
  });

  child.stderr.on('data', (chunk) => {
    const text = chunk.toString();
    stderrBuf += text;
    process.stderr.write(`[dj-runtime stderr] ${text}`);
  });

  const earlyExit = new Promise((resolve) => {
    child.once('exit', (code, signal) => resolve({ code, signal }));
    child.once('error', (err) => resolve({ error: err }));
  });

  // Esperamos DJ_READY_PORT hasta 30s (librosa/numpy frío en Windows tarda).
  const portDeadline = Date.now() + 30000;
  while (!resolvedPort && Date.now() < portDeadline) {
    const racing = await Promise.race([
      wait(150).then(() => 'tick'),
      earlyExit.then((e) => ({ exited: e })),
    ]);
    if (racing && typeof racing === 'object' && racing.exited) {
      const { code, signal, error } = racing.exited;
      const msg = error
        ? `No se pudo lanzar Python: ${error.message}`
        : `El proceso .py terminó antes de arrancar (code=${code}, signal=${signal})`;
      console.error(`[dj-runtime] ${msg}`);
      if (stderrBuf) console.error(`[dj-runtime] stderr: ${stderrBuf}`);
      if (stdoutBuf) console.error(`[dj-runtime] stdout: ${stdoutBuf}`);
      const e = new Error(msg);
      e.stderr = stderrBuf || stdoutBuf || null;
      throw e;
    }
  }

  if (!resolvedPort) {
    try { child.kill(); } catch {}
    const msg = 'Timeout esperando DJ_READY_PORT del .py (30s)';
    console.error(`[dj-runtime] ${msg}`);
    if (stderrBuf) console.error(`[dj-runtime] stderr: ${stderrBuf}`);
    if (stdoutBuf) console.error(`[dj-runtime] stdout: ${stdoutBuf}`);
    const e = new Error(msg);
    e.stderr = stderrBuf || stdoutBuf || null;
    throw e;
  }

  // Confirmar que responde HTTP en ese puerto (margen amplio).
  const ready = await waitForServer(resolvedPort, 15000);
  if (!ready) {
    try { child.kill(); } catch {}
    const e = new Error(`El .py dijo puerto ${resolvedPort} pero no responde HTTP`);
    e.stderr = stderrBuf || stdoutBuf || null;
    throw e;
  }

  child.unref();
  store.players.set(key, {
    child,
    port: resolvedPort,
    folderName,
    startedAt: Date.now(),
  });

  console.log(`[dj-runtime] ${folderName} ready on port ${resolvedPort}`);
  return { port: resolvedPort, alreadyRunning: false };
}

/**
 * Helper de debug opcional (no usado por las rutas).
 */
export function listRunningDjs() {
  return Array.from(store.players.entries()).map(([key, v]) => ({
    key,
    port: v.port,
    folderName: v.folderName,
    alive: isAlive(v.child),
    startedAt: v.startedAt,
  }));
}
