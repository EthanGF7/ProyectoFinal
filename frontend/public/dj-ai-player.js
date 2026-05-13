// DJ AI Player script — window.__DJ_AI_ID must be set before this loads
// DJ AI Player — auto-isolated
(function() {
  // Prevent double-execution
  if (window.__DJ_AI_RUNNING) {
    console.warn('[DjAI] Script already running, skipping');
    return;
  }
  window.__DJ_AI_RUNNING = true;


// ════════════════════════════════════════════════════════════════
//  DJ AI  ·  Audio Engine
//
//  Grafo de audio por deck:
//
//    BufferSource → preGain
//                     → hipass (EQ kick: corta graves pista entrante)
//                       → lopass (EQ high-kill: corta agudos pista saliente)
//                         → masterGain
//                           → compressor
//                             → analyser
//                               → destination
//
//  Durante el crossfade (técnica DJ):
//    OUT: gainA 1→0 (curva cóncava lenta)
//         lopass baja 20kHz→400Hz  (quita agudos/mids)
//
//    IN:  gainB 0→1 (sigmoide TARDÍA: casi nada hasta t=55%, luego aparece)
//         hipass baja 350Hz→20Hz (los graves entran DESPUÉS del resto)
//         = "bass swap": se escuchan los graves de la entrante solo cuando
//           la saliente ya ha desaparecido casi por completo → drop limpio
//
//  EQ visual: 3 barras (lo/mid/hi) muestran lo que está pasando
// ════════════════════════════════════════════════════════════════

const AC = window.AudioContext || window.webkitAudioContext;
let ctx  = null;

const PHASE_ORDER = ['warm-up','first-build','first-peak','breakdown','second-build','second-peak','outro'];
const PHASE_LABELS = {'warm-up':'WARM','first-build':'BUILD','first-peak':'PEAK 1',
  'breakdown':'DOWN','second-build':'BUILD 2','second-peak':'PEAK 2','outro':'OUTRO'};
const STYLE_LABELS = { guetta: '⚡ GUETTA', avicii: '🌅 AVICII', progressive: '〰 PROG' };
const STYLE_ICONS  = { guetta: '⚡', avicii: '🌅', progressive: '〰' };

const S = {
  lib: [], cur: null, curFile: null,
  nxt: null, nxtPlan: null, nxtScore: 0, nxtPhase: 'warm-up',
  played: [], playedSet: new Set(), count: 0,
  playing: false, mixing: false,
  mixStart: 0, mixDur: 8,
  deck: 'A',
  startAt: 0,
  bufs: {},
  // Deck nodes: S.decks.A = { src, preGain, hipass, lopass, gain, analyser }
  decks: { A: {}, B: {} },
  modOk: false,

  // Silence detection
  silenceStart: null,
  lastRms: 1.0,
  silenceTriggered: false,

  // Beat detection
  beatLastTime: 0,       // ctx.currentTime del último beat detectado
  beatThresh: 0.15,      // umbral dinámico de energía de sub-bass
  beatHistory: [],       // últimas energías para calcular umbral adaptativo
  lastBpm: 0,            // BPM estimado en tiempo real

  // Session timeline
  sessionTracks: [],     // [{track, startCtxTime, color}] orden real de reproducción
  sessionStartTime: 0,   // ctx.currentTime cuando empezó la sesión

  // Mix trigger
  _beatSnapScheduled: false,

  // Cue (preview siguiente)
  cueing: false,
  cueSrc: null,
  cueGain: null,
};

// ── Init ─────────────────────────────────────────────────────
function ic() {
  if (!ctx) {
    ctx  = new AC();
    // Master compressor — limita el volumen total, evita clipping durante el mix
    S.comp = ctx.createDynamicsCompressor();
    S.comp.threshold.value = -14;
    S.comp.knee.value      = 6;
    S.comp.ratio.value     = 4;
    S.comp.attack.value    = 0.003;
    S.comp.release.value   = 0.25;
    // Master analyser (para el visualizador principal)
    S.mAnl = ctx.createAnalyser();
    S.mAnl.fftSize = 1024;
    S.comp.connect(S.mAnl);
    S.mAnl.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();

  // Reverb (ConvolverNode con impulse response sintético)
  if (!S.reverb) {
    S.reverb    = ctx.createConvolver();
    S.reverbGain = ctx.createGain();
    S.reverbGain.gain.value = 0;  // empieza apagado, se activa en el mix

    // Generar impulse response exponencial (sala grande ~2.5s)
    const rate = ctx.sampleRate;
    const len  = Math.floor(rate * 2.5);
    const ir   = ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = ir.getChannelData(ch);
      for (let i = 0; i < len; i++) {
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i/len, 2.5);
      }
    }
    S.reverb.buffer = ir;
    S.comp.connect(S.reverbGain);
    S.reverbGain.connect(S.reverb);
    S.reverb.connect(ctx.destination);
  }

  // Cue output (auriculares DJ — va directo a destination con gain propio)
  if (!S.cueOutGain) {
    S.cueOutGain = ctx.createGain();
    S.cueOutGain.gain.value = 0.85;
    S.cueOutGain.connect(ctx.destination);
  }
}

// ── Boot ─────────────────────────────────────────────────────
async function boot() {
  const [lr, mr] = await Promise.all([fetch('/api/djs/' + window.__DJ_AI_ID + '/library'), Promise.resolve({ json: () => Promise.resolve({ ok: false }) })]);
  S.lib  = await lr.json();
  const m = await mr.json();
  S.modOk = m.ok;

  const mb = document.getElementById('modB');
  mb.textContent = S.modOk ? 'MÓDULOS OK' : 'FALLBACK';
  mb.className   = 'mod ' + (S.modOk ? 'ok' : 'fb');

  document.getElementById('libCount').textContent = S.lib.length + ' canciones';
  document.getElementById('idleInfo').innerHTML =
    `<b>${S.lib.length}</b> canción${S.lib.length!==1?'es':''} · arco automático`;
  document.getElementById('btnStart').disabled = S.lib.length === 0;
  if (!S.lib.length)
    document.getElementById('idleInfo').textContent = 'Pon MP3/WAV en musica/canciones/';
  renderLib();
}

// ── Scrubbing (arrastrar playhead) ────────────────────────────
{
  const ww      = document.getElementById('ww');
  const ph      = document.getElementById('ph');
  const handle  = document.getElementById('phHandle');
  const tooltip = document.getElementById('wwTooltip');
  let dragging  = false;

  function scrubPos(e) {
    const rect = ww.getBoundingClientRect();
    const pad  = 18; // padding del .ww en px
    const x    = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left - pad;
    const w    = rect.width - pad * 2;
    return Math.max(0, Math.min(1, x / w));
  }

  function seekTo(frac) {
    const dur = S.cur ? (S.cur.duracion_segundos || 0) : 0;
    if (!dur || !S.playing || !ctx) return;
    const newTime = frac * dur;

    const dk  = S.deck;
    const trk = S.cur;
    if (!trk || !S.bufs[trk.file]) return;

    const d = S.decks[dk];
    if (d.src) {
      // Marcar como seek para que onended no dispare doMix
      d.src.onended = null;
      try { d.src.stop(); } catch(e) {}
      d.src = null;
    }

    const src = ctx.createBufferSource();
    src.buffer = S.bufs[trk.file];
    src.playbackRate.value = 1.0;
    src.connect(d.preGain);
    src.start(0, newTime);
    d.src       = src;
    d.startedAt = ctx.currentTime - newTime;
    S.startAt   = d.startedAt;
    S.silenceStart     = null;
    S.silenceTriggered = false;

    src.onended = () => {
      if (S.playing && dk === S.deck && !S.mixing) doMix();
    };
  }

  function onMove(e) {
    if (!S.playing) return;
    e.preventDefault();
    const frac = scrubPos(e);
    const dur  = S.cur ? (S.cur.duracion_segundos || 0) : 0;
    const wc   = document.getElementById('wc');
    const w    = wc.offsetWidth;

    // Mover playhead visualmente
    ph.style.left = (18 + frac * w) + 'px';

    // Tooltip con tiempo
    const t = frac * dur;
    tooltip.textContent = fmt(t);
    tooltip.style.left  = (18 + frac * w) + 'px';
    tooltip.classList.add('show');

    if (dragging) {
      // Actualizar tiempo en pantalla en tiempo real
      document.getElementById('tCur').textContent = fmt(t);
    }
  }

  function onDown(e) {
    if (!S.playing || S.mixing) return;
    dragging = true;
    ph.classList.add('scrubbing');
    handle.classList.add('scrubbing');
    onMove(e);
  }

  function onUp(e) {
    if (!dragging) return;
    dragging = false;
    ph.classList.remove('scrubbing');
    handle.classList.remove('scrubbing');
    tooltip.classList.remove('show');
    const frac = scrubPos(e.changedTouches ? {clientX: e.changedTouches[0].clientX} : e.clientX);
    seekTo(frac);
  }

  ww.addEventListener('mousedown',  onDown);
  ww.addEventListener('touchstart', onDown, {passive:false});
  window.addEventListener('mousemove', e => { if (dragging) onMove(e); });
  window.addEventListener('touchmove', e => { if (dragging) onMove(e); }, {passive:false});
  window.addEventListener('mouseup',   onUp);
  window.addEventListener('touchend',  onUp);

  // Hover: mostrar tooltip sin arrastrar
  ww.addEventListener('mousemove', e => { if (!dragging && S.playing) onMove(e); });
  ww.addEventListener('mouseleave', () => { if (!dragging) tooltip.classList.remove('show'); });

  // Guardar referencia para que el loop sepa si está scrubbing
  S._dragging = () => dragging;
}

// ── Start ─────────────────────────────────────────────────────
document.getElementById('btnStart').addEventListener('click', async () => {
  ic();
  document.getElementById('idle').classList.add('off');
  document.getElementById('app').classList.add('on');
  const first = chooseFirst();
  await begin(first);
});

function chooseFirst() {
  if (!S.lib.length) return null;
  // Warm-up: energía baja-media, primer cuartil
  const s = [...S.lib].sort((a,b)=>(a.energia||50)-(b.energia||50));
  return s[Math.floor(s.length * 0.18)] || s[0];
}

async function begin(t) {
  S.cur = t; S.curFile = t.file; S.deck = 'A';
  S.playing = true; S.startAt = 0;
  S.played.push(t.file); S.playedSet.add(t.file); S.count = 1;
  S.sessionStartTime = ctx.currentTime;
  S.sessionTracks = [{ track: t, startCtxTime: ctx.currentTime, color: trackColor(0) }];
  updateNP(t, 'warm-up');
  const startPos = t.start_position ?? 0;
  await playDeck('A', t, startPos);
  logMsg(`Iniciando desde ${fmt(startPos)}: ${t.name}`);
  document.getElementById('btnSkip').disabled = false;
  renderLib();
  renderTimeline();
  loop();
  askNext(t, 0);
}

// Botón de skip: salta directamente al mix (para testing)
document.getElementById('btnSkip').addEventListener('click', () => {
  if (!S.mixing && S.playing) doMix();
});

// ── CUE: preview de la siguiente pista ───────────────────────
// Reproduce 5s de la siguiente canción (desde puede_empezar_mezcla)
// en paralelo, en voz baja, para que el DJ pueda oírla.
// Pulsar de nuevo para parar.
document.getElementById('btnCue').addEventListener('click', async () => {
  if (!S.nxt) return;
  const btn = document.getElementById('btnCue');

  if (S.cueing) {
    // Parar cue
    if (S.cueSrc)  { try{S.cueSrc.stop();}catch(e){} S.cueSrc = null; }
    if (S.cueGain) { S.cueGain.gain.setValueAtTime(0, ctx.currentTime); }
    S.cueing = false;
    btn.classList.remove('cueing');
    btn.textContent = '👂 CUE';
    return;
  }

  // Cargar buffer
  try {
    const buf = await loadBuf(S.nxt);
    const enterAt = S.nxtPlan ? (S.nxtPlan.start_next_time || 0) : 0;
    const CUE_DUR = 8; // segundos de preview

    S.cueGain = ctx.createGain();
    S.cueGain.gain.setValueAtTime(0, ctx.currentTime);
    S.cueGain.gain.linearRampToValueAtTime(0.6, ctx.currentTime + 0.3);
    S.cueGain.connect(S.cueOutGain);

    S.cueSrc = ctx.createBufferSource();
    S.cueSrc.buffer = buf;
    S.cueSrc.connect(S.cueGain);
    S.cueSrc.start(0, enterAt);

    // Auto-fade y stop tras CUE_DUR segundos
    S.cueGain.gain.setValueAtTime(0.6, ctx.currentTime + CUE_DUR - 1);
    S.cueGain.gain.linearRampToValueAtTime(0, ctx.currentTime + CUE_DUR);
    S.cueSrc.stop(ctx.currentTime + CUE_DUR);
    S.cueSrc.onended = () => {
      S.cueing = false;
      btn.classList.remove('cueing');
      btn.textContent = '👂 CUE';
      S.cueSrc = null;
    };

    S.cueing = true;
    btn.classList.add('cueing');
    btn.textContent = '■ STOP';
    logMsg(`👂 Preview: ${S.nxt.name}`);
  } catch(e) {
    logMsg('Error cargando preview');
  }
});

// ── Ask server for next track ─────────────────────────────────
async function askNext(t, ct) {
  if (!t) return;
  try {
    const pe  = encodeURIComponent(JSON.stringify([...S.playedSet]));
    // Pasar las últimas 3 canciones con su key para anti-repetición de tonalidad
    const pl  = encodeURIComponent(JSON.stringify(
      S.played.slice(-3).map(f => ({ file: f, key: (S.lib.find(x=>x.file===f)||{}).key||'' }))
    ));
    const url = `/api/djs/${window.__DJ_AI_ID}/next?current=${encodeURIComponent(t.file)}&time=${ct.toFixed(1)}&played=${pe}&count=${S.count}&played_list=${pl}`;
    const d   = await (await fetch(url)).json();
    if (d.error) { S.nxt = null; hideNext(); return; }
    S.nxt = d.track; S.nxtPlan = d.plan; S.nxtScore = d.score; S.nxtPhase = d.phase;
    showNext(d.track, d.plan, d.score, d.phase);
    updateArc(d.phase, d.target_energy);
    preload(d.track);
    renderLib();
  } catch(e) {}
}

// ── Buffer cache ──────────────────────────────────────────────
async function loadBuf(t) {
  if (S.bufs[t.file]) return S.bufs[t.file];
  ic();
  const ab  = await (await fetch('/api/djs/' + window.__DJ_AI_ID + '/audio?file=' + encodeURIComponent(t.file))).arrayBuffer();
  const buf = await ctx.decodeAudioData(ab);
  return S.bufs[t.file] = buf;
}
async function preload(t) {
  if (!t || S.bufs[t.file]) return;
  try { ic(); await loadBuf(t); } catch(e) {}
}

// ── Create / reset deck audio graph ──────────────────────────
function resetGraph(dk) {
  const d = S.decks[dk];
  if (d.src)  { try{d.src.stop();}catch(e){} d.src = null; }

  // Recrear nodos (evita problemas con nodos usados)
  d.preGain  = ctx.createGain();
  d.hipass   = ctx.createBiquadFilter();
  d.lopass   = ctx.createBiquadFilter();
  d.analyser = ctx.createAnalyser();
  d.analyser.fftSize = 256;

  d.hipass.type = 'highpass';  d.hipass.Q.value = 0.71;
  d.lopass.type = 'lowpass';   d.lopass.Q.value = 0.71;

  // Chain: preGain → hipass → lopass → analyser → compressor
  d.preGain.connect(d.hipass);
  d.hipass.connect(d.lopass);
  d.lopass.connect(d.analyser);
  d.analyser.connect(S.comp);

  return d;
}

// ── Play a track on a deck ────────────────────────────────────
async function playDeck(dk, track, offset = 0) {
  const buf = await loadBuf(track);
  // Si la pista no tiene duración en el JSON, usar la del AudioBuffer
  // Esto garantiza que el trigger del mix funcione aunque no haya JSON
  if (!track.duracion_segundos || track.duracion_segundos === 0) {
    track.duracion_segundos = buf.duration;
  }
  const d   = resetGraph(dk);

  const src = ctx.createBufferSource();
  src.buffer = buf;

  // BPM matching: si la entrante tiene BPM distinto, empezar en el ratio
  // que la hace sonar al mismo tempo que la saliente, y programar un ramp
  // gradual a 1.0 para que al terminar el fade suene a su tempo original.
  if (dk !== S.deck && track.bpm && S.cur && S.cur.bpm && track.bpm > 0) {
    const ratio = S.cur.bpm / track.bpm;
    src.playbackRate.setValueAtTime(ratio, ctx.currentTime);
    // Guardar el ramp para cuando se conozca cfDur en doMix
    // (lo haremos desde doMix con d.src ya disponible)
    d._bpmRatio = ratio;
    d._bpmTarget = 1.0;
  } else {
    src.playbackRate.value = 1.0;
    d._bpmRatio  = 1.0;
    d._bpmTarget = 1.0;
  }

  src.connect(d.preGain);
  d.preGain.gain.setValueAtTime(dk === S.deck ? 1 : 0, ctx.currentTime);

  // Deck entrante: graves cortados hasta que la IA los abra (bass swap)
  d.hipass.frequency.setValueAtTime(dk === S.deck ? 20  : 320, ctx.currentTime);
  d.lopass.frequency.setValueAtTime(20000, ctx.currentTime);

  src.start(0, offset);
  d.src = src;

  // Guardar el momento de inicio de ESTE deck para poder calcular su tiempo
  d.startedAt = ctx.currentTime - offset;

  if (dk === S.deck) {
    S.startAt = d.startedAt;
    drawWave(buf, track);
  }

  src.onended = () => {
    if (S.playing && dk === S.deck && !S.mixing) doMix();
  };
}

function getTime() {
  return !S.playing || !ctx ? 0 : Math.max(0, ctx.currentTime - S.startAt);
}

// ════════════════════════════════════════════════════════════
//  D O M I X — Triple style: Guetta / Avicii / Progressive
//
//  GUETTA:
//    OUT: gain cóncava suavizada (pow 0.9)
//         lopass 20kHz→400Hz (mata agudos progresivamente)
//    IN:  sigmoide TARDÍA (aparece de golpe en el 65%)
//         hipass 320Hz→20Hz con bass swap abrupto en el 60%
//         → Drop percibido físicamente
//
//  AVICII:
//    OUT: gain coseno suave (sale en arco simétrico)
//         hipass 20Hz→800Hz (pierde graves gradualmente = "se va")
//    IN:  sigmoide TEMPRANA (empieza a oírse desde el 20%)
//         graves abiertos desde el principio
//         → La melodía de la entrante llega ANTES que el beat
//    Reverb: más pronunciado (0.35 vs 0.18)
//
//  PROGRESSIVE:
//    Equal-power puro: vOut=cos(f·π/2), vIn=sin(f·π/2)
//    → En cualquier punto del fade: vOut²+vIn²=1 (sin bajón matemático)
//    EQ neutro — sin highpass/lowpass agresivo
//    BPM casi idéntico → sin pitch shifting apreciable
//    Reverb mínimo (0.10)
// ════════════════════════════════════════════════════════════
async function doMix() {
  if (S.mixing || !S.playing) return;
  const nxt = S.nxt;
  if (!nxt) {
    askNext(S.cur, getTime());
    setTimeout(() => { if (!S.mixing && S.nxt) doMix(); }, 1200);
    return;
  }

  const plan    = S.nxtPlan;
  const cfDur   = plan ? (plan.mix_duration || 8) : 8;
  const enterAt = plan ? (plan.start_next_time || 0) : 0;
  const style   = plan ? (plan.style || 'guetta') : 'guetta';

  // Detener CUE si está activo antes de empezar la mezcla
  if (S.cueing && S.cueSrc) {
    try { S.cueSrc.stop(); } catch(e) {}
    S.cueSrc = null;
    S.cueing = false;
    document.getElementById('btnCue').classList.remove('cueing');
    document.getElementById('btnCue').textContent = '👂 CUE';
  }

  S.mixing   = true;
  S.mixStart = ctx.currentTime;
  S.mixDur   = cfDur;
  S.mixStyle = style;

  showMixing(nxt.name, cfDur, style);
  logMsg(`${STYLE_LABELS[style]||style} · ⇄ ${nxt.name} · ${cfDur.toFixed(0)}s`);

  // Reverb — Progressive casi nada, Avicii mucho, Guetta moderado
  if (S.reverb && S.reverbGain) {
    const reverbPeak = style === 'avicii' ? 0.35 : style === 'progressive' ? 0.10 : 0.18;
    const rg = S.reverbGain.gain;
    rg.cancelScheduledValues(ctx.currentTime);
    rg.setValueAtTime(0, ctx.currentTime);
    rg.linearRampToValueAtTime(reverbPeak,     ctx.currentTime + cfDur * 0.25);
    rg.linearRampToValueAtTime(reverbPeak*0.5, ctx.currentTime + cfDur * 0.75);
    rg.linearRampToValueAtTime(0,              ctx.currentTime + cfDur * 1.0);
  }

  const out = S.deck;
  const inp = out === 'A' ? 'B' : 'A';

  await playDeck(inp, nxt, enterAt);
  const inpStartedAt = ctx.currentTime - enterAt;

  const t0    = ctx.currentTime;
  const dOut  = S.decks[out];
  const dIn   = S.decks[inp];
  const steps = Math.round(cfDur * 30);

  // Anclar estado inicial
  dOut.preGain.gain.cancelScheduledValues(t0);
  dIn.preGain.gain.cancelScheduledValues(t0);
  dOut.hipass.frequency.cancelScheduledValues(t0);
  dOut.lopass.frequency.cancelScheduledValues(t0);
  dIn.hipass.frequency.cancelScheduledValues(t0);
  dIn.lopass.frequency.cancelScheduledValues(t0);

  dOut.preGain.gain.setValueAtTime(1,     t0);
  dIn.preGain.gain.setValueAtTime(0,      t0);
  dOut.lopass.frequency.setValueAtTime(20000, t0);
  dOut.hipass.frequency.setValueAtTime(20,    t0);
  dIn.lopass.frequency.setValueAtTime(20000, t0);

  if (style === 'progressive') {
    // EQ completamente neutro — las pistas suenan completas
    dIn.hipass.frequency.setValueAtTime(20, t0);
  } else if (style === 'avicii') {
    // Entrante empieza con graves abiertos — melodía llega primero
    dIn.hipass.frequency.setValueAtTime(20, t0);
  } else {
    // Guetta: graves de la entrante cortados hasta el bass swap
    dIn.hipass.frequency.setValueAtTime(320, t0);
  }

  // BPM ramp (solo Guetta/Avicii — Progressive tiene BPM casi igual)
  if (style !== 'progressive' && dIn.src && dIn._bpmRatio && dIn._bpmRatio !== 1.0) {
    dIn.src.playbackRate.cancelScheduledValues(t0);
    dIn.src.playbackRate.setValueAtTime(dIn._bpmRatio, t0);
    dIn.src.playbackRate.exponentialRampToValueAtTime(1.0, t0 + cfDur);
  }

  // ── Nodo de compensación de volumen (anti-bajón) ─────────────
  // Guetta/Avicii: las curvas no son equal-power → puede haber hueco.
  // Progressive: equal-power puro → sin hueco (pero lo dejamos activo
  // para uniformidad y por si el compresor pump).
  if (!S.compGain) {
    S.compGain = ctx.createGain();
    S.compGain.gain.value = 1;
    S.comp.disconnect(S.mAnl);
    S.comp.connect(S.compGain);
    S.compGain.connect(S.mAnl);
  }
  S.compGain.gain.cancelScheduledValues(t0);
  S.compGain.gain.setValueAtTime(1, t0);

  for (let i = 0; i <= steps; i++) {
    const f   = i / steps;
    const tAt = t0 + f * cfDur;

    let vOut, vIn;

    if (style === 'progressive') {
      // ── PROGRESSIVE: equal-power puro ──────────────────────
      // Garantía matemática: vOut²+vIn²=1 en todo momento.
      // No hay bajón posible — es la base del DJ mixing técnico.
      vOut = Math.cos(f * Math.PI / 2);
      vIn  = Math.sin(f * Math.PI / 2);

    } else if (style === 'avicii') {
      // ── AVICII: fade simétrico tipo coseno con sigmoide temprana
      vOut = Math.pow(Math.cos(f * Math.PI / 2), 1.2);
      vIn  = 1 / (1 + Math.exp(-10 * (f - 0.35)));

    } else {
      // ── GUETTA: asimétrico, drop abrupto ───────────────────
      // OUT: cóncava suavizada — pow(0.9) mantiene volumen en la primera mitad
      vOut = Math.pow(1 - f, 0.9);
      // IN: sigmoide TARDÍA — aparece de golpe en el 65%
      vIn  = 1 / (1 + Math.exp(-16 * (f - 0.65)));
    }

    dOut.preGain.gain.setValueAtTime(Math.max(0, vOut), tAt);
    dIn.preGain.gain.setValueAtTime(Math.min(1, vIn),   tAt);

    // Gain de compensación: normaliza la potencia combinada a ≥ 1.
    // Progressive: power=1 siempre (sin ajuste necesario).
    // Guetta/Avicii: puede bajar — este nodo lo compensa.
    const power = Math.sqrt(vOut * vOut + vIn * vIn);
    const cGain = power > 0.01 ? Math.min(1.35, 1 / power) : 1;
    S.compGain.gain.setValueAtTime(cGain, tAt);

    if (style === 'progressive') {
      // EQ neutro: solo un leve lowpass a la saliente en la segunda mitad
      // para que no haya superposición de frecuencias altas que cause comb filtering
      const loFreq = f > 0.5 ? (20000 * Math.pow(8000/20000, (f-0.5)*2)) : 20000;
      dOut.lopass.frequency.setValueAtTime(Math.max(8000, loFreq), tAt);
      // Entrante: sin tocar nada — suena completa y limpia
      dIn.hipass.frequency.setValueAtTime(20, tAt);

    } else if (style === 'avicii') {
      // OUT lopass: mantiene cuerpo hasta el final
      const loFreq = 20000 * Math.pow(800/20000, Math.pow(f, 1.4));
      dOut.lopass.frequency.setValueAtTime(Math.max(700, loFreq), tAt);
      // OUT hipass: pierde graves gradualmente ("se va")
      const outHpFreq = 20 * Math.pow(600/20, Math.pow(f, 1.8));
      dOut.hipass.frequency.setValueAtTime(Math.min(600, outHpFreq), tAt);
      // IN hipass: ya abierto, desaparece rápido
      const inHpFreq = 80 * Math.pow(20/80, Math.pow(f * 2, 1.5));
      dIn.hipass.frequency.setValueAtTime(Math.max(20, inHpFreq), tAt);

    } else {
      // GUETTA EQ
      // OUT lopass: agudos mueren progresivamente
      const loFreq = 20000 * Math.pow(500/20000, Math.pow(f, 0.7));
      dOut.lopass.frequency.setValueAtTime(Math.max(400, loFreq), tAt);
      // IN hipass: bass swap abrupto en el 60%
      let hpFreq;
      if (f < 0.60) {
        hpFreq = 320 * Math.pow(200/80, f/0.60);
      } else {
        const bassF = (f - 0.60) / 0.40;
        hpFreq = 80 * Math.pow(20/80, Math.pow(bassF, 1.5));
      }
      dIn.hipass.frequency.setValueAtTime(Math.max(20, hpFreq), tAt);
    }
  }

  // A mitad del fade: actualizar UI
  setTimeout(async () => {
    updateNP(nxt, S.nxtPhase);
    if (S.bufs[nxt.file]) drawWave(S.bufs[nxt.file], nxt);
  }, cfDur * 500);

  // Al final del fade: cambiar deck activo
  setTimeout(async () => {
    S.deck    = inp;
    S.startAt = inpStartedAt;
    S.cur  = nxt; S.curFile = nxt.file;
    S.played.push(nxt.file); S.playedSet.add(nxt.file); S.count++;
    S.nxt  = null; S.nxtPlan = null;
    S.sessionTracks.push({
      track: nxt,
      startCtxTime: inpStartedAt,
      color: trackColor(S.sessionTracks.length)
    });
    document.getElementById('btnCue').disabled = true;
    await askNext(nxt, getTime());
    renderLib();
    renderTimeline();
  }, cfDur * 950);

  // Fin: apagar deck saliente limpiamente
  setTimeout(() => {
    const dO = S.decks[out];
    if (dO.preGain) {
      dO.preGain.gain.cancelScheduledValues(ctx.currentTime);
      dO.preGain.gain.setValueAtTime(0, ctx.currentTime);
    }
    if (dO.src) { try{dO.src.stop();}catch(e){} dO.src = null; }
    if (dO.hipass) dO.hipass.frequency.setValueAtTime(20,    ctx.currentTime);
    if (dO.lopass) dO.lopass.frequency.setValueAtTime(20000, ctx.currentTime);

    // Volver el gain de compensación a 1 limpiamente
    if (S.compGain) {
      S.compGain.gain.cancelScheduledValues(ctx.currentTime);
      S.compGain.gain.linearRampToValueAtTime(1, ctx.currentTime + 0.3);
    }

    S.mixing           = false;
    S.silenceStart     = null;
    S.silenceTriggered = false;
    hideMixing();
    hideEQ();
    logMsg(`Reproduciendo: ${S.cur.name}`);
  }, cfDur * 1000 + 250);
}

// ── Animation loop ────────────────────────────────────────────
function loop() {
  requestAnimationFrame(loop);
  if (!S.playing || !ctx) return;

  const t   = getTime();
  const dur = S.cur ? (S.cur.duracion_segundos || 0) : 0;

  // Playhead — no mover mientras el usuario arrastra
  const wW = document.getElementById('wc').offsetWidth;
  if (!S._dragging || !S._dragging()) {
    const pad = 18;
    document.getElementById('ph').style.left   = (pad + (dur > 0 ? (t/dur)*wW : 0)) + 'px';
    document.getElementById('tCur').textContent = fmt(t);
  }
  document.getElementById('tTot').textContent  = fmt(dur);

  // Vinyl spin
  document.getElementById('vinyl').classList.toggle('spin', S.playing && !S.mixing);

  // Mix progress bar
  if (S.mixing) {
    const pct = Math.min(100, ((ctx.currentTime - S.mixStart) / S.mixDur) * 100);
    document.getElementById('mixFill').style.width = pct + '%';
    updateEQVisual(pct / 100);
  }

  // ── Trigger del mix ─────────────────────────────────────────
  // No disparar mientras el usuario está arrastrando el playhead
  if (!S.mixing && S.nxt && dur > 0 && !(S._dragging && S._dragging())) {
    const cf         = S.nxtPlan ? (S.nxtPlan.mix_duration || 8) : 8;
    const puedeSalir = S.cur ? (S.cur.puede_salir) || 0 : 0;
    const planExit   = S.nxtPlan ? (S.nxtPlan.exit_at) || 0 : 0;

    let trig;
    if (puedeSalir > 0) {
      trig = puedeSalir - cf;
    } else if (planExit > 0) {
      trig = planExit - cf;
    } else {
      trig = dur - cf - 2;
    }
    trig = Math.max(trig, dur * 0.73);

    // Beat-snapping: si el trigger está a menos de 1 beat de distancia,
    // esperar al beat más cercano para arrancar alineado con el ritmo.
    // Usa los beat_times del JSON si están disponibles.
    if (t >= trig - 0.5 && t < trig + 2.5 && !S._beatSnapScheduled) {
      S._beatSnapScheduled = true;
      const beatTimes = S.cur ? (S.cur.beat_times || []) : [];
      let snapTarget = trig;

      if (beatTimes.length > 0) {
        // Encontrar el beat más próximo dentro de ±1.5s del trigger ideal
        let bestDist = 9999, bestBeat = trig;
        for (const bt of beatTimes) {
          const dist = Math.abs(bt - trig);
          if (dist < bestDist && dist < 1.5) { bestDist = dist; bestBeat = bt; }
        }
        snapTarget = bestBeat;
      }

      const delay = Math.max(0, (snapTarget - t) * 1000);
      setTimeout(() => {
        S._beatSnapScheduled = false;
        if (!S.mixing && S.nxt) doMix();
      }, delay);
    }
  }

  // Refrescar plan cada 20s para mantenerlo actualizado
  if (!S.mixing && S.cur && S.nxt && Math.round(t) % 20 === 0 && t > 8) {
    askNext(S.cur, t);
  }

  // ── Detección de beat en tiempo real ───────────────────────
  // Analiza la energía de sub-bass (bins 0-4 ≈ 20-80Hz) cada frame.
  // Si supera el umbral adaptativo → beat detectado → flash visual.
  // El umbral se adapta al nivel medio de los últimos 30 beats.
  if (!S.mixing && S.playing && t > 2) {
    const dk = S.decks[S.deck];
    if (dk && dk.analyser) {
      const fdata = new Uint8Array(dk.analyser.frequencyBinCount);
      dk.analyser.getByteFrequencyData(fdata);
      // Sub-bass energy (primeros 4 bins)
      const subE = (fdata[0] + fdata[1] + fdata[2] + fdata[3]) / (4 * 255);
      S.beatHistory.push(subE);
      if (S.beatHistory.length > 60) S.beatHistory.shift();
      const avg = S.beatHistory.reduce((a,b)=>a+b,0) / S.beatHistory.length;
      S.beatThresh = avg * 1.5;

      const now = ctx.currentTime;
      const minInterval = S.cur && S.cur.bpm ? 60/S.cur.bpm * 0.7 : 0.25;
      if (subE > S.beatThresh && subE > 0.1 && (now - S.beatLastTime) > minInterval) {
        S.beatLastTime = now;
        // Flash visual del beat dot
        const dot = document.getElementById('beatDot');
        dot.classList.add('flash');
        setTimeout(() => dot.classList.remove('flash'), 80);
      }
    }
  }

  // ── Update timeline playhead ─────────────────────────────────
  if (S.playing && S.sessionTracks.length > 0) {
    const elapsed = ctx.currentTime - S.sessionStartTime;
    const totalEst = S.sessionTracks.reduce((acc, st) => {
      return acc + (st.track.duracion_segundos || 180);
    }, 0);
    const pct = Math.min(99, (elapsed / Math.max(totalEst, 1)) * 100);
    const tlHead = document.getElementById('tlHead');
    if (tlHead) tlHead.style.left = pct + '%';
  }

  // ── Detección de silencio / caída de canción ─────────────────
  if (!S.mixing && S.playing && t > 5 && !(S._dragging && S._dragging())) {
    const dk = S.decks[S.deck];
    if (dk && dk.analyser) {
      const buf = new Uint8Array(dk.analyser.frequencyBinCount);
      dk.analyser.getByteFrequencyData(buf);
      // RMS normalizado 0-1
      let sum = 0;
      for (let i = 0; i < buf.length; i++) sum += (buf[i]/255) * (buf[i]/255);
      const rms = Math.sqrt(sum / buf.length);

      const SILENCE_THRESHOLD = 0.03;   // por debajo de esto = silencio percibido
      const SILENCE_MS        = 1800;   // debe durar 1.8s para confirmar
      const MIN_PROGRESS      = 0.30;   // ignorar antes del 30% de la canción

      const progress = dur > 0 ? t / dur : 0;

      if (rms < SILENCE_THRESHOLD && progress > MIN_PROGRESS && !S.silenceTriggered) {
        if (S.silenceStart === null) {
          S.silenceStart = ctx.currentTime;
        } else if ((ctx.currentTime - S.silenceStart) * 1000 > SILENCE_MS) {
          // ¡Silencio confirmado! Saltar al siguiente
          S.silenceTriggered = true;
          S.silenceStart     = null;
          logMsg('⚡ Silencio detectado — saltando');
          doMix();
        }
      } else if (rms >= SILENCE_THRESHOLD) {
        // Señal volvió — resetear contador
        S.silenceStart     = null;
        S.silenceTriggered = false;
      }
    }
  }

  drawViz();
}

// ── EQ visual durante el mix ──────────────────────────────────
function updateEQVisual(frac) {
  // frac 0→1 durante el crossfade
  // Muestra lo que el EQ está haciendo a la pista saliente
  const hiPct  = Math.max(0, (1 - Math.pow(frac / 0.8, 0.6)) * 100);
  const midPct = Math.max(0, (1 - Math.pow(frac / 0.9, 0.8)) * 100);
  const loPct  = Math.max(0, (1 - Math.pow(frac / 1.0, 1.2)) * 100);
  document.getElementById('eqHi').style.width  = hiPct + '%';
  document.getElementById('eqMid').style.width = midPct + '%';
  document.getElementById('eqLo').style.width  = loPct + '%';
}

function hideEQ() {
  document.getElementById('eqRow').classList.remove('on');
  document.getElementById('eqHi').style.width  = '100%';
  document.getElementById('eqMid').style.width = '100%';
  document.getElementById('eqLo').style.width  = '100%';
}

// ── UI helpers ────────────────────────────────────────────────
function updateNP(t, phase) {
  document.getElementById('npTitle').textContent = t.name;
  document.getElementById('npBpm').textContent   = t.bpm  ? t.bpm.toFixed(1)+' BPM' : '—';
  document.getElementById('npEgy').textContent   = t.energia ? 'E'+t.energia : '';
  document.getElementById('npDur').textContent   = t.duracion_segundos ? fmt(t.duracion_segundos) : '';
  document.getElementById('bpmVal').textContent  = t.bpm ? Math.round(t.bpm) : '—';

  const keyEl = document.getElementById('npKey');
  if (t.key) { keyEl.textContent = t.key; keyEl.style.display = 'inline'; }
  else keyEl.style.display = 'none';

  const pill = document.getElementById('phasePill');
  const p = phase || S.nxtPhase || 'warm-up';
  pill.textContent = PHASE_LABELS[p] || p;
  pill.setAttribute('class', 'pill pill-' + p);
}

function updateArc(phase, targetE) {
  const idx = PHASE_ORDER.indexOf(phase);
  const pct = idx < 0 ? 0 : (idx / (PHASE_ORDER.length-1)) * 100;
  document.getElementById('arcCursor').style.left  = pct + '%';
  document.getElementById('arcPhase').textContent  = (PHASE_LABELS[phase]||phase) + ' · E→' + Math.round(targetE);
}

function showNext(t, plan, score, phase) {
  document.getElementById('nxtRow').style.display = 'flex';
  document.getElementById('nxtNm').textContent    = t.name;
  document.getElementById('nxtSc').textContent    = 'Score ' + Math.round(score);
  const style  = plan ? (plan.style || 'guetta') : 'guetta';
  const sLabel = STYLE_ICONS[style] || '⚡';
  const timing = plan
    ? `${sLabel} ${style.toUpperCase()} · ${(plan.mix_duration||8).toFixed(0)}s fade`
    : '';
  document.getElementById('nxtT').textContent = timing;
  document.getElementById('btnCue').disabled = false;
}
function hideNext() { document.getElementById('nxtRow').style.display = 'none'; }

function showMixing(name, dur, style) {
  const row   = document.getElementById('mixRow');
  const label = document.getElementById('mixStyleLabel');
  row.classList.add('on');
  row.classList.remove('style-guetta', 'style-avicii', 'style-progressive');
  row.classList.add('style-' + (style || 'guetta'));
  label.textContent = STYLE_LABELS[style] || '⚡ GUETTA';
  document.getElementById('mixInfo').textContent = `→ ${name} · ${dur.toFixed(0)}s`;
  document.getElementById('mixFill').style.width = '0%';
  document.getElementById('eqRow').classList.add('on');
}
function hideMixing() { document.getElementById('mixRow').classList.remove('on'); }

function renderLib() {
  const list = document.getElementById('tlist');
  if (!S.lib.length) {
    list.innerHTML = '<div class="empty"><p>Pon MP3/WAV en <code>musica/canciones/</code></p></div>';
    return;
  }
  const cBpm = S.cur ? (S.cur.bpm||0) : 0;
  list.innerHTML = S.lib.map((t,i) => {
    const iC   = t.file === S.curFile;
    const iN   = S.nxt && t.file === S.nxt.file;
    const done = !iC && S.playedSet.has(t.file);
    const bOk  = !cBpm || !t.bpm || Math.abs(t.bpm-cBpm) <= 10;
    const sc   = iN ? Math.round(S.nxtScore) : null;
    const sC   = sc===null ? '' : sc>70?'hi':sc>40?'mi':'lo';
    return `<div class="tk ${iC?'cur':''} ${iN?'nxt':''} ${done?'done':''}">
      <div class="tn">${iC?'▶':iN?'→':done?'✓':i+1}</div>
      <div class="tt">${t.name}</div>
      <div class="te"><div class="tef" style="width:${t.energia||50}%"></div></div>
      <div class="tb ${bOk?'ok':'no'}">${t.bpm?t.bpm.toFixed(0)+'bpm':'—'}</div>
      <div class="ts ${sC}">${sc!==null?sc:'—'}</div>
      <div class="td">${t.duracion_segundos?fmt(t.duracion_segundos):'—'}</div>
    </div>`;
  }).join('');
}

// ── Waveform ──────────────────────────────────────────────────
function drawWave(buf, track) {
  const c = document.getElementById('wc'), dpr = devicePixelRatio||1;
  c.width = c.offsetWidth*dpr; c.height = c.offsetHeight*dpr;
  const g = c.getContext('2d'); g.scale(dpr,dpr);
  const W=c.offsetWidth, H=c.offsetHeight, mid=H/2;
  const data=buf.getChannelData(0), step=Math.ceil(data.length/W);
  g.clearRect(0,0,W,H);

  // Gradiente que refleja la energía de la canción
  const gr = g.createLinearGradient(0,0,W,0);
  gr.addColorStop(0,  'rgba(200,255,0,.08)');
  gr.addColorStop(.4, 'rgba(200,255,0,.65)');
  gr.addColorStop(.6, 'rgba(0,240,255,.55)');
  gr.addColorStop(1,  'rgba(200,255,0,.08)');
  g.strokeStyle = gr; g.lineWidth = 1; g.beginPath();
  for(let i=0;i<W;i++){
    let mn=1,mx=-1;
    for(let j=0;j<step;j++){const v=data[i*step+j]||0;if(v<mn)mn=v;if(v>mx)mx=v;}
    g.moveTo(i,mid+mn*mid); g.lineTo(i,mid+mx*mid);
  }
  g.stroke();

  if(!track) return;
  const dur = track.duracion_segundos || buf.duration;

  // Zona de entrada permitida (azul)
  if(track.puede_empezar_mezcla) {
    const x1=(track.puede_empezar_mezcla/dur)*W;
    const x2=track.debe_sonar_sola?(track.debe_sonar_sola/dur)*W:W;
    g.fillStyle='rgba(0,240,255,.04)'; g.fillRect(x1,0,x2-x1,H);
    g.strokeStyle='rgba(0,240,255,.18)'; g.lineWidth=1;
    g.beginPath();g.moveTo(x1,0);g.lineTo(x1,H);g.stroke();
    if(track.debe_sonar_sola){g.beginPath();g.moveTo(x2,0);g.lineTo(x2,H);g.stroke();}
  }
  // Punto de salida (rojo)
  if(track.puede_salir){
    const xo=(track.puede_salir/dur)*W;
    g.strokeStyle='rgba(255,59,92,.35)'; g.lineWidth=1;
    g.beginPath();g.moveTo(xo,0);g.lineTo(xo,H);g.stroke();
    // Pequeño triángulo marcador
    g.fillStyle='rgba(255,59,92,.5)';
    g.beginPath();g.moveTo(xo-3,0);g.lineTo(xo+3,0);g.lineTo(xo,5);g.fill();
  }
}

// ── Spectrum visualizer ───────────────────────────────────────
function drawViz() {
  const c = document.getElementById('viz'), dpr = devicePixelRatio||1;
  if(c.width!==c.offsetWidth*dpr){c.width=c.outputWidth*dpr;c.height=c.offsetHeight*dpr;}
  const g = c.getContext('2d'), W=c.offsetWidth, H=c.offsetHeight;
  g.setTransform(dpr,0,0,dpr,0,0);

  // Fade out fondo (efecto de cola)
  g.fillStyle = 'rgba(7,8,15,.55)';
  g.fillRect(0,0,W,H);

  // Dibuja ambos decks durante el crossfade (superpuestos)
  const drawDeck = (dkId, colorFn) => {
    const dk = S.decks[dkId];
    if (!dk || !dk.analyser) return;
    const d = new Uint8Array(dk.analyser.frequencyBinCount);
    dk.analyser.getByteFrequencyData(d);
    const bw = (W / d.length) * 1.2;
    for(let i=0;i<d.length;i++){
      const v=d[i]/255, bh=v*H*0.96;
      if(bh < 1) continue;
      const col = colorFn(i/d.length, v);
      g.fillStyle = col;
      // Barra + reflejo especular
      g.fillRect(i*bw, H-bh, bw-0.5, bh);
      g.globalAlpha = 0.12;
      g.fillRect(i*bw, H, bw-0.5, -bh*0.25);
      g.globalAlpha = 1;
    }
  };

  const colorOut = (x, v) => `rgba(200,255,0,${(0.25+v*0.75).toFixed(2)})`;
  const colorIn  = (x, v) => `rgba(0,240,255,${(0.2+v*0.7).toFixed(2)})`;

  if (S.mixing) {
    const other = S.deck === 'A' ? 'B' : 'A';
    drawDeck(other, colorIn);
    drawDeck(S.deck, colorOut);
  } else {
    drawDeck(S.deck, colorOut);
  }
}

function logMsg(m) { document.getElementById('log').textContent = m; }

// ── Track color palette ───────────────────────────────────────
function trackColor(idx) {
  const palette = [
    'rgba(200,255,0',    // verde lima
    'rgba(0,240,255',    // cyan
    'rgba(176,96,255',   // violeta
    'rgba(255,149,0',    // naranja
    'rgba(255,59,92',    // rojo
    'rgba(0,255,180',    // verde agua
    'rgba(255,220,0',    // amarillo
    'rgba(80,160,255',   // azul
  ];
  return palette[idx % palette.length];
}

// ── Timeline de sesión ────────────────────────────────────────
function renderTimeline() {
  const wrap = document.getElementById('tlWrap');
  if (!wrap || !S.sessionTracks.length) return;
  wrap.style.display = 'block';

  const blocks  = document.getElementById('tlBlocks');
  const labels  = document.getElementById('tlLabels');
  const tlDur   = document.getElementById('tlDur');

  // Calcular duración total estimada de la sesión
  const durations = S.sessionTracks.map(st => st.track.duracion_segundos || 180);
  const total     = durations.reduce((a,b)=>a+b, 0);

  // Render bloques
  blocks.innerHTML = S.sessionTracks.map((st, i) => {
    const dur  = st.track.duracion_segundos || 180;
    const pct  = (dur / total * 100).toFixed(2);
    const isCur = st.track.file === S.curFile;
    const isDone = !isCur && i < S.sessionTracks.length - 1;
    const e    = st.track.energia || 50;
    const col  = st.color;
    // Altura de la barra proporcional a la energía
    const hPct = 30 + e * 0.7;
    return `<div class="tl-block ${isCur?'playing':''} ${isDone?'done':'future'}"
      style="width:${pct}%;background:${col},.08)"
      title="${st.track.name}"
      onclick="tlSeek(${i})">
      <div style="position:absolute;bottom:0;left:0;right:0;height:${hPct}%;
        background:${col},.4);border-radius:2px 2px 0 0;pointer-events:none"></div>
    </div>`;
  }).join('');

  // Labels debajo (nombre truncado, solo algunas)
  let leftPct = 0;
  labels.innerHTML = S.sessionTracks.map((st, i) => {
    const dur = st.track.duracion_segundos || 180;
    const pct = dur / total * 100;
    const mid = leftPct + pct / 2;
    leftPct  += pct;
    const isCur = st.track.file === S.curFile;
    const name  = st.track.name.length > 12 ? st.track.name.slice(0,11)+'…' : st.track.name;
    return `<span class="tl-lbl ${isCur?'cur':''}" style="left:${mid.toFixed(1)}%">${name}</span>`;
  }).join('');

  // Duración total
  const totalMins = Math.floor(total / 60);
  tlDur.textContent = `~${totalMins} min`;
}

// Seek directo a una canción del timeline (click en bloque)
function tlSeek(idx) {
  if (S.mixing) return;  // no permitir seek durante mezcla
  const st = S.sessionTracks[idx];
  if (!st) return;
  // Si es la pista actual, solo saltar al principio
  if (st.track.file === S.curFile) {
    const d = S.decks[S.deck];
    if (d && d.src) {
      d.src.onended = null;
      try { d.src.stop(); } catch(e) {}
    }
    const buf = S.bufs[st.track.file];
    if (!buf) return;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = 1.0;
    src.connect(d.preGain);
    src.start(0, 0);
    d.src = src;
    d.startedAt = ctx.currentTime;
    S.startAt = d.startedAt;
    S.silenceStart = null; S.silenceTriggered = false;
    src.onended = () => { if (S.playing && !S.mixing) doMix(); };
    logMsg(`↩ Reiniciando: ${st.track.name}`);
  }
  // (Para canciones pasadas/futuras no hacemos nada — solo informativo)
}
function fmt(s) { s=Math.max(0,Math.floor(s)); return Math.floor(s/60)+':'+String(s%60).padStart(2,'0'); }
function resize() {
  ['viz','wc'].forEach(id=>{
    const c=document.getElementById(id);
    c.width=c.offsetWidth*(devicePixelRatio||1);
    c.height=c.offsetHeight*(devicePixelRatio||1);
  });
}
window.addEventListener('resize', resize); resize();
boot();


})();