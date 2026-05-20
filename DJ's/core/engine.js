// ════════════════════════════════════════════════════════════════
//  DJ AI · Shared Audio Engine  —  for all DJ themes
//  Calls window.initTheme() and window.drawTheme() for visualization
// ════════════════════════════════════════════════════════════════

const AC = window.AudioContext || window.webkitAudioContext;
let ctx = null;

const PHASE_ORDER = ['warm-up','first-build','first-peak','breakdown','second-build','second-peak','outro'];
const PHASE_LABELS = {
  'warm-up':'CALOR', 'first-build':'ASCENSO', 'first-peak':'CÚSPIDE 1',
  'breakdown':'DUENDE', 'second-build':'VUELO', 'second-peak':'CÚSPIDE 2', 'outro':'SERENO'
};
const STYLE_LABELS = { guetta:'⚡ GUETTA', avicii:'🌅 AVICII', progressive:'〰 PROG', fusion:'✦ FUSIÓN' };
const STYLE_ICONS = { guetta:'⚡', avicii:'🌅', progressive:'〰' };

const S = {
  lib:[], cur:null, curFile:null,
  nxt:null, nxtPlan:null, nxtScore:0, nxtPhase:'warm-up',
  played:[], playedSet:new Set(), count:0,
  playing:false, mixing:false,
  mixStart:0, mixDur:8,
  deck:'A', startAt:0, bufs:{},
  decks:{ A:{}, B:{} },
  modOk:false,
  silenceStart:null, lastRms:1.0, silenceTriggered:false,
  beatLastTime:0, beatThresh:0.15, beatHistory:[], lastBpm:0,
  sessionTracks:[], sessionStartTime:0, _beatSnapScheduled:false,
  cueing:false, cueSrc:null, cueGain:null,
};

let authToken = null;

window.addEventListener('message', e => {
  if (e.origin !== window.location.origin) return;
  if (e.data?.type === 'nexus-auth-token' && e.data.accessToken) {
    authToken = e.data.accessToken;
  }
});

function getAuthHeaders() {
  if (authToken) return { Authorization: `Bearer ${authToken}` };
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.includes('auth-token')) continue;
      const raw = localStorage.getItem(key);
      const parsed = JSON.parse(raw);
      const token = parsed?.access_token || parsed?.currentSession?.access_token;
      if (token) return { Authorization: `Bearer ${token}` };
    }
  } catch(e) {}
  return {};
}

async function waitAuthHeaders(timeoutMs=2500) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const headers = getAuthHeaders();
    if (headers.Authorization) return headers;
    await new Promise(r => setTimeout(r, 100));
  }
  return getAuthHeaders();
}

// ── Initialize AudioContext ──────────────────────────────────
function ic() {
  if (!ctx) {
    ctx = new AC();
    S.comp = ctx.createDynamicsCompressor();
    S.comp.threshold.value = -14;
    S.comp.knee.value = 6;
    S.comp.ratio.value = 4;
    S.comp.attack.value = 0.003;
    S.comp.release.value = 0.25;
    S.mAnl = ctx.createAnalyser();
    S.mAnl.fftSize = 1024;
    S.comp.connect(S.mAnl);
    S.mAnl.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  
  if (!S.reverb) {
    S.reverb = ctx.createConvolver();
    S.reverbGain = ctx.createGain();
    S.reverbGain.gain.value = 0;
    const rate = ctx.sampleRate;
    const len = Math.floor(rate * 2.5);
    const ir = ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = ir.getChannelData(ch);
      for (let i = 0; i < len; i++)
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.5);
    }
    S.reverb.buffer = ir;
    S.comp.connect(S.reverbGain);
    S.reverbGain.connect(S.reverb);
    S.reverb.connect(ctx.destination);
  }
  if (!S.cueOutGain) {
    S.cueOutGain = ctx.createGain();
    S.cueOutGain.gain.value = 0.85;
    S.cueOutGain.connect(ctx.destination);
  }
}

// ── Boot ─────────────────────────────────────────────────────
async function boot() {
  const [lr, mr] = await Promise.all([fetch('/api/library'), fetch('/api/modules')]);
  S.lib = await lr.json();
  const m = await mr.json();
  S.modOk = m.ok;
  await loadPrefs();
  
  const mb = document.getElementById('modB');
  if (mb) {
    mb.textContent = S.modOk ? 'MÓDULOS OK' : 'FALLBACK';
    mb.className = 'mod ' + (S.modOk ? 'ok' : 'fb');
  }
  
  document.getElementById('libCount').textContent = S.lib.length + ' canciones';
  document.getElementById('idleInfo').innerHTML = 
    `<b>${S.lib.length}</b> canción${S.lib.length!==1?'es':''} · arco automático`;
  document.getElementById('btnStart').disabled = S.lib.length === 0;
  if (!S.lib.length)
    document.getElementById('idleInfo').textContent = 'Pon MP3/WAV en musica/canciones/';
  renderLib();
}

// ── Media key blocking ───────────────────────────────────────
window.addEventListener('keydown', e => {
  const blocked = ['Space','ArrowLeft','ArrowRight','MediaPlayPause',
                   'MediaTrackNext','MediaTrackPrevious','MediaStop'];
  if (blocked.includes(e.code)) e.preventDefault();
}, {capture:true});

// ── Start ────────────────────────────────────────────────────
document.getElementById('btnStart').addEventListener('click', async () => {
  ic();
  document.getElementById('idle').classList.add('off');
  document.getElementById('stage').classList.add('on');
  if (typeof window.initTheme === 'function') window.initTheme();
  const first = chooseFirst();
  await begin(first);
});

function chooseFirst() {
  if (!S.lib.length) return null;
  const s = [...S.lib].sort((a,b)=>(a.energia||50)-(b.energia||50));
  return s[Math.floor(s.length*0.18)] || s[0];
}

async function begin(t) {
  S.cur = t; S.curFile = t.file; S.deck = 'A';
  S.playing = true; S.startAt = 0;
  S.played.push(t.file); S.playedSet.add(t.file); S.count = 1;
  S.sessionStartTime = ctx.currentTime;
  S.sessionTracks = [{ track:t, startCtxTime:ctx.currentTime, color:trackColor(0) }];
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

document.getElementById('btnSkip').addEventListener('click', () => {
  if (!S.mixing && S.playing) doMix();
});

document.getElementById('btnCue').addEventListener('click', async () => {
  if (!S.nxt) return;
  const btn = document.getElementById('btnCue');
  if (S.cueing) {
    if (S.cueSrc) { try{S.cueSrc.stop();}catch(e){} S.cueSrc = null; }
    if (S.cueGain) S.cueGain.gain.setValueAtTime(0, ctx.currentTime);
    S.cueing = false;
    btn.classList.remove('cueing');
    btn.textContent = '👂 CUE';
    return;
  }
  try {
    const buf = await loadBuf(S.nxt);
    const enterAt = S.nxtPlan ? (S.nxtPlan.start_next_time||0) : 0;
    const CUE_DUR = 8;
    S.cueGain = ctx.createGain();
    S.cueGain.gain.setValueAtTime(0, ctx.currentTime);
    S.cueGain.gain.linearRampToValueAtTime(0.6, ctx.currentTime+0.3);
    S.cueGain.connect(S.cueOutGain);
    S.cueSrc = ctx.createBufferSource();
    S.cueSrc.buffer = buf;
    S.cueSrc.connect(S.cueGain);
    S.cueSrc.start(0, enterAt);
    S.cueGain.gain.setValueAtTime(0.6, ctx.currentTime+CUE_DUR-1);
    S.cueGain.gain.linearRampToValueAtTime(0, ctx.currentTime+CUE_DUR);
    S.cueSrc.stop(ctx.currentTime+CUE_DUR);
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
  } catch(e) { logMsg('Error cargando preview'); }
});

async function askNext(t, ct) {
  if (!t) return;
  try {
    const pe = encodeURIComponent(JSON.stringify([...S.playedSet]));
    const pl = encodeURIComponent(JSON.stringify(
      S.played.slice(-3).map(f=>({ file:f, key:(S.lib.find(x=>x.file===f)||{}).key||'' }))
    ));
    const url = `/api/next?current=${encodeURIComponent(t.file)}&time=${ct.toFixed(1)}&played=${pe}&count=${S.count}&played_list=${pl}`;
    const d = await (await fetch(url, { headers: getAuthHeaders() })).json();
    if (d.error) { S.nxt = null; hideNext(); return; }
    S.nxt = d.track; S.nxtPlan = d.plan; S.nxtScore = d.score; S.nxtPhase = d.phase;
    showNext(d.track, d.plan, d.score, d.phase);
    updateArc(d.phase, d.target_energy);
    preload(d.track);
    renderLib();
  } catch(e) {}
}

async function loadBuf(t) {
  if (S.bufs[t.file]) return S.bufs[t.file];
  ic();
  const ab = await (await fetch('/audio/'+encodeURIComponent(t.file))).arrayBuffer();
  const buf = await ctx.decodeAudioData(ab);
  return S.bufs[t.file] = buf;
}
async function preload(t) {
  if (!t || S.bufs[t.file]) return;
  try { ic(); await loadBuf(t); } catch(e) {}
}

function resetGraph(dk) {
  const d = S.decks[dk];
  if (d.src) { try{d.src.stop();}catch(e){} d.src = null; }
  d.preGain = ctx.createGain();
  d.hipass = ctx.createBiquadFilter();
  d.lopass = ctx.createBiquadFilter();
  d.analyser = ctx.createAnalyser();
  d.analyser.fftSize = 256;
  d.hipass.type = 'highpass'; d.hipass.Q.value = 0.71;
  d.lopass.type = 'lowpass'; d.lopass.Q.value = 0.71;
  d.preGain.connect(d.hipass);
  d.hipass.connect(d.lopass);
  d.lopass.connect(d.analyser);
  d.analyser.connect(S.comp);
  return d;
}

async function playDeck(dk, track, offset=0) {
  const buf = await loadBuf(track);
  if (!track.duracion_segundos || track.duracion_segundos===0)
    track.duracion_segundos = buf.duration;
  const d = resetGraph(dk);
  const src = ctx.createBufferSource();
  src.buffer = buf;
  if (dk!==S.deck && track.bpm && S.cur && S.cur.bpm && track.bpm>0) {
    const ratio = S.cur.bpm / track.bpm;
    src.playbackRate.setValueAtTime(ratio, ctx.currentTime);
    d._bpmRatio = ratio; d._bpmTarget = 1.0;
  } else {
    src.playbackRate.value = 1.0;
    d._bpmRatio = 1.0; d._bpmTarget = 1.0;
  }
  src.connect(d.preGain);
  d.preGain.gain.setValueAtTime(dk===S.deck?1:0, ctx.currentTime);
  d.hipass.frequency.setValueAtTime(dk===S.deck?20:320, ctx.currentTime);
  d.lopass.frequency.setValueAtTime(20000, ctx.currentTime);
  src.start(0, offset);
  d.src = src;
  d.startedAt = ctx.currentTime - offset;
  if (dk===S.deck) { S.startAt = d.startedAt; drawWave(buf, track); }
  src.onended = () => { if (S.playing && dk===S.deck && !S.mixing) doMix(); };
}

function getTime() {
  return !S.playing||!ctx ? 0 : Math.max(0, ctx.currentTime-S.startAt);
}

async function doMix() {
  if (S.mixing || !S.playing) return;
  const nxt = S.nxt;
  if (!nxt) {
    askNext(S.cur, getTime());
    setTimeout(()=>{ if(!S.mixing&&S.nxt) doMix(); }, 1200);
    return;
  }
  const plan = S.nxtPlan;
  const cfDur = plan ? (plan.mix_duration||8) : 8;
  const enterAt = plan ? (plan.start_next_time||0) : 0;
  const style = plan ? (plan.style||'guetta') : 'guetta';
  
  if (S.cueing && S.cueSrc) {
    try { S.cueSrc.stop(); } catch(e) {}
    S.cueSrc = null; S.cueing = false;
    document.getElementById('btnCue').classList.remove('cueing');
    document.getElementById('btnCue').textContent = '👂 CUE';
  }
  
  S.mixing=true; S.mixStart=ctx.currentTime; S.mixDur=cfDur; S.mixStyle=style;
  showMixing(nxt.name, cfDur, style);
  logMsg(`${STYLE_LABELS[style]||style} · ⇄ ${nxt.name} · ${cfDur.toFixed(0)}s`);
  
  if (S.reverb && S.reverbGain) {
    const reverbPeak = style==='avicii'?0.35:style==='progressive'?0.10:style==='fusion'?0.22:0.18;
    const rg = S.reverbGain.gain;
    rg.cancelScheduledValues(ctx.currentTime);
    rg.setValueAtTime(0, ctx.currentTime);
    rg.linearRampToValueAtTime(reverbPeak, ctx.currentTime+cfDur*0.35);
    rg.linearRampToValueAtTime(reverbPeak*0.5, ctx.currentTime+cfDur*0.75);
    rg.linearRampToValueAtTime(0, ctx.currentTime+cfDur*1.0);
  }
  
  const out = S.deck;
  const inp = out==='A'?'B':'A';
  await playDeck(inp, nxt, enterAt);
  const inpStartedAt = ctx.currentTime - enterAt;
  const t0 = ctx.currentTime;
  const dOut = S.decks[out];
  const dIn = S.decks[inp];
  const steps = Math.round(cfDur*30);
  
  dOut.preGain.gain.cancelScheduledValues(t0);
  dIn.preGain.gain.cancelScheduledValues(t0);
  dOut.hipass.frequency.cancelScheduledValues(t0);
  dOut.lopass.frequency.cancelScheduledValues(t0);
  dIn.hipass.frequency.cancelScheduledValues(t0);
  dIn.lopass.frequency.cancelScheduledValues(t0);
  dOut.preGain.gain.setValueAtTime(1, t0);
  dIn.preGain.gain.setValueAtTime(0, t0);
  dOut.lopass.frequency.setValueAtTime(20000, t0);
  dOut.hipass.frequency.setValueAtTime(20, t0);
  dIn.lopass.frequency.setValueAtTime(20000, t0);
  
  if (style==='progressive'||style==='avicii'||style==='fusion') {
    dIn.hipass.frequency.setValueAtTime(20, t0);
    if(style==='fusion') dOut.hipass.frequency.setValueAtTime(20, t0);
  } else {
    dIn.hipass.frequency.setValueAtTime(320, t0);
  }
  
  if (style!=='progressive' && dIn.src && dIn._bpmRatio && dIn._bpmRatio!==1.0) {
    dIn.src.playbackRate.cancelScheduledValues(t0);
    dIn.src.playbackRate.setValueAtTime(dIn._bpmRatio, t0);
    dIn.src.playbackRate.exponentialRampToValueAtTime(1.0, t0+cfDur);
  }
  
  for (let i = 1; i <= steps; i++) {
    const frac = i / steps;
    const t = t0 + cfDur * frac;
    
    if (style === 'progressive') {
      const easeInOutCubic = frac < 0.5 ? 4*frac*frac*frac : 1-Math.pow(-2*frac+2,3)/2;
      dOut.preGain.gain.setValueAtTime(1 - easeInOutCubic, t);
      dIn.preGain.gain.setValueAtTime(easeInOutCubic, t);
      if (i === 1 || i % 3 === 0) {
        dOut.lopass.frequency.setValueAtTime(20000 - frac*19980, t);
        dIn.hipass.frequency.setValueAtTime(20 + frac*300, t);
      }
    } else if (style === 'avicii') {
      const easeInOutQuad = frac < 0.5 ? 2*frac*frac : -1+(4-2*frac)*frac;
      dOut.preGain.gain.setValueAtTime(Math.pow(1-frac, 1.2), t);
      dIn.preGain.gain.setValueAtTime(Math.pow(frac, 1.2), t);
      if (i % 2 === 0) {
        const lpFreq = 20000 - frac*19950 + Math.sin(frac*Math.PI)*200;
        dOut.lopass.frequency.setValueAtTime(lpFreq, t);
        dOut.hipass.frequency.setValueAtTime(20, t);
      }
    } else if (style === 'fusion') {
      const easeInOutQuint = frac < 0.5 ? 16*frac*frac*frac*frac*frac : 1-Math.pow(-2*frac+2,5)/2;
      dOut.preGain.gain.setValueAtTime(1 - easeInOutQuint, t);
      dIn.preGain.gain.setValueAtTime(easeInOutQuint, t);
      if (i % 2 === 0) {
        dOut.lopass.frequency.setValueAtTime(20000 - frac*19985, t);
      }
    } else {
      const hardDrop = frac > 0.7 ? 0 : (1 - frac/0.7);
      dOut.preGain.gain.setValueAtTime(hardDrop, t);
      dIn.preGain.gain.setValueAtTime(1 - hardDrop, t);
      if (i === 1 || i % 2 === 0) {
        dOut.lopass.frequency.setValueAtTime(20000 - frac*19200, t);
        dOut.hipass.frequency.setValueAtTime(20 + frac*300, t);
      }
    }
  }
  
  dOut.preGain.gain.setValueAtTime(0, t0+cfDur);
  dIn.preGain.gain.setValueAtTime(1, t0+cfDur);
  dIn.hipass.frequency.setValueAtTime(20, t0+cfDur);
  
  S.cur = nxt; S.curFile = nxt.file; S.deck = inp;
  S.played.push(nxt.file); S.playedSet.add(nxt.file); S.count++;
  S.sessionTracks.push({ track:nxt, startCtxTime:t0+cfDur, color:trackColor(S.count-1) });
  updateNP(nxt, S.nxtPhase);
  renderTimeline();
  
  setTimeout(() => {
    S.mixing = false;
    logMsg(`Mezclando completado: ${nxt.name}`);
    askNext(nxt, getTime());
  }, cfDur*1000);
}

function loop() {
  if (S.playing) {
    const t = getTime();
    const curDur = (S.cur && S.cur.duracion_segundos) || 0;
    const prog = curDur > 0 ? t / curDur : 0;
    
    updateProgress(t, curDur, prog);
    
    if (typeof window.drawTheme === 'function') {
      window.drawTheme();
    }
    
    analyzeBeat();
  }
  requestAnimationFrame(loop);
}

function analyzeBeat() {
  if (!S.mAnl) return;
  const data = new Uint8Array(S.mAnl.frequencyBinCount);
  S.mAnl.getByteFrequencyData(data);
  let rms = 0;
  for (let i = 0; i < data.length; i++) {
    const v = data[i] / 255;
    rms += v * v;
  }
  rms = Math.sqrt(rms / data.length);
  
  const delta = rms - S.lastRms;
  S.lastRms = rms;
  
  const now = ctx.currentTime;
  if (delta > S.beatThresh && (now - S.beatLastTime) > 0.3) {
    S.beatLastTime = now;
    S.beatHistory.push(now);
    if (S.beatHistory.length > 32) S.beatHistory.shift();
  }
}

// ── Helpers ──────────────────────────────────────────────────
function fmt(s) {
  const m = Math.floor(s/60);
  const se = Math.floor(s%60);
  return `${m}:${se.toString().padStart(2,'0')}`;
}

function trackColor(idx) {
  const hues = [0,30,60,90,120,150,180,210,240,270,300,330];
  return `hsl(${hues[idx%hues.length]}, 60%, 50%)`;
}

async function loadPrefs() {
  try {
    S.prefs = await (await fetch('/api/prefs', { headers: getAuthHeaders() })).json();
  } catch(e) {
    S.prefs = {};
  }
}

async function sendLike(action) {
  if (!S.cur) return;
  fetch('/api/like', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await waitAuthHeaders()) },
    body: JSON.stringify({ file: S.cur.file, action })
  }).then(r => {
    if (!r.ok) logMsg('Inicia sesión para guardar likes');
  }).catch(e => logMsg('Error en like'));
}

function updateNP(t, phase) {
  document.getElementById('npTitle').textContent = t.name || '—';
  document.getElementById('npBpm').textContent = t.bpm ? `${t.bpm} BPM` : '';
  document.getElementById('npDur').textContent = t.duracion_segundos ? fmt(t.duracion_segundos) : '';
  document.getElementById('npTitleHidden').textContent = t.name || '—';
  document.getElementById('npBpmHidden').textContent = t.bpm ? `${t.bpm}` : '—';
  document.getElementById('npEgy').textContent = t.energia ? `${t.energia}` : '—';
  document.getElementById('npKeyHidden').textContent = t.key || '—';
  document.getElementById('npDurHidden').textContent = t.duracion_segundos ? fmt(t.duracion_segundos) : '—';
  
  const phaseLabel = PHASE_LABELS[phase] || phase;
  document.getElementById('phasePill').textContent = phaseLabel;
  document.getElementById('phasePillHidden').textContent = phase;
}

function showNext(t, plan, score, phase) {
  document.getElementById('nxtNm').textContent = t.name || '—';
  document.getElementById('nxtSc').textContent = score ? score.toFixed(0) : '—';
  document.getElementById('nxtT').textContent = plan ? fmt(plan.mix_duration) : '—';
  document.getElementById('btnCue').disabled = false;
}

function hideNext() {
  document.getElementById('nxtNm').textContent = '—';
  document.getElementById('nxtSc').textContent = '—';
  document.getElementById('nxtT').textContent = '—';
  document.getElementById('btnCue').disabled = true;
}

function showMixing(name, dur, style) {
  const ind = document.getElementById('mixIndicator');
  ind.classList.add('active');
  document.getElementById('mixLabel').textContent = 'MEZCLANDO';
  document.getElementById('mixStyleLabel').textContent = STYLE_ICONS[style] || '♦';
  document.getElementById('mixInfo').textContent = `${dur.toFixed(0)}s`;
}

function updateProgress(t, dur, prog) {
  document.getElementById('progressLine').style.width = `${prog*100}%`;
  document.getElementById('tCur').textContent = fmt(t);
  document.getElementById('tTot').textContent = fmt(dur);
  
  if (S.mixing) {
    const mixProg = (ctx.currentTime - S.mixStart) / S.mixDur;
    if (mixProg >= 1) {
      document.getElementById('mixIndicator').classList.remove('active');
    }
  }
}

function updateArc(phase, targetE) {
  const idx = PHASE_ORDER.indexOf(phase);
  const prog = (idx + 0.5) / PHASE_ORDER.length * 100;
  const cursor = document.getElementById('arcCursor');
  if (cursor) cursor.style.left = `${prog}%`;
  document.getElementById('arcPhase').textContent = phase;
}

function drawWave(buf, track) {
  const wc = document.getElementById('wc');
  if (!wc) return;
  const cctx = wc.getContext('2d');
  const data = buf.getChannelData(0);
  const width = wc.width, height = wc.height;
  cctx.fillStyle = 'rgba(10,10,10,0.9)';
  cctx.fillRect(0, 0, width, height);
  cctx.strokeStyle = '#0f0';
  cctx.lineWidth = 1;
  cctx.beginPath();
  for (let i = 0; i < width; i++) {
    const idx = Math.floor(i / width * data.length);
    const y = height / 2 * (1 - data[idx]);
    i === 0 ? cctx.moveTo(i, y) : cctx.lineTo(i, y);
  }
  cctx.stroke();
}

function renderLib() {
  const list = document.getElementById('tlist');
  if (!list) return;
  list.innerHTML = '';
  for (const t of S.lib) {
    const div = document.createElement('div');
    div.className = 'trow' + (t.file === S.curFile ? ' playing' : '');
    div.textContent = t.name;
    list.appendChild(div);
  }
}

function renderTimeline() {
  const blk = document.getElementById('tlBlocks');
  if (!blk) return;
  blk.innerHTML = '';
  const startTime = S.sessionTracks[0]?.startCtxTime || 0;
  for (const e of S.sessionTracks) {
    const div = document.createElement('div');
    div.className = 'tlBlock';
    div.style.backgroundColor = e.color;
    div.textContent = e.track.name.substring(0, 3);
    blk.appendChild(div);
  }
}

function logMsg(msg) {
  const log = document.getElementById('log');
  if (log) log.textContent = msg;
}
