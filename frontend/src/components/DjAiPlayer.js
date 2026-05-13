import { useEffect } from 'react';

export default function DjAiPlayer({ djId, onClose }) {
  useEffect(() => {
    if (!djId) return;

    // 1. Inject CSS
    const CSS_ID = 'djai-css';
    if (!document.getElementById(CSS_ID)) {
      const s = document.createElement('style');
      s.id = CSS_ID;
      s.textContent = "\nimport url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=Bebas+Neue&family=DM+Sans:wght@300;400;600&display=swap');\n:root{\n  --bg:#07080f; --s1:#0d0f1c; --s2:#12152a; --b:#1c2040;\n  --g:#c8ff00;  --c:#00f0ff;  --r:#ff3b5c; --o:#ff9500; --p:#b060ff;\n  --t:#dde2ff;  --dim:#3d4466;\n}\n*{margin:0;padding:0;box-sizing:border-box}\nhtml,body{height:100%;overflow:hidden}\nbody{background:var(--bg);color:var(--t);font-family:'DM Sans',sans-serif;\n  display:flex;align-items:center;justify-content:center;}\nbody::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:9999;\n  background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,.035) 3px,rgba(0,0,0,.035) 4px);}\n\n/* ── IDLE ───────────────────────────────────────────────────────────────── */\n#idle{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;\n  justify-content:center;gap:28px;z-index:100;background:var(--bg);\n  transition:opacity .9s,visibility .9s;}\n#idle.off{opacity:0;visibility:hidden;pointer-events:none}\n\n.idle-logo{font-family:'Bebas Neue',sans-serif;\n  font-size:clamp(72px,15vw,140px);letter-spacing:12px;\n  background:linear-gradient(135deg,var(--g) 30%,var(--c));\n  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;\n  animation:logopulse 3s ease-in-out infinite;}\n@keyframes logopulse{\n  0%,100%{filter:drop-shadow(0 0 20px rgba(200,255,0,.3))}\n  50%    {filter:drop-shadow(0 0 60px rgba(200,255,0,.7)) drop-shadow(0 0 120px rgba(0,240,255,.3))}}\n\n.idle-sub{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:4px;\n  color:var(--dim);text-transform:uppercase;}\n\n.play-btn{width:100px;height:100px;border-radius:50%;background:var(--g);border:none;\n  cursor:pointer;font-size:38px;color:#000;font-weight:900;\n  display:flex;align-items:center;justify-content:center;\n  box-shadow:0 0 50px rgba(200,255,0,.4),0 0 100px rgba(200,255,0,.15);\n  transition:all .25s;position:relative;}\n.play-btn::before{content:'';position:absolute;inset:-4px;border-radius:50%;\n  border:1px solid rgba(200,255,0,.2);animation:ringgrow 2s ease-out infinite;}\n@keyframes ringgrow{0%{transform:scale(1);opacity:.6}100%{transform:scale(1.4);opacity:0}}\n.play-btn:hover{transform:scale(1.09);box-shadow:0 0 80px rgba(200,255,0,.7),0 0 160px rgba(200,255,0,.25)}\n.play-btn:disabled{opacity:.3;cursor:not-allowed;transform:none;animation:none}\n.play-btn:disabled::before{display:none}\n.idle-info{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--dim);}\n.idle-info b{color:var(--g)}\n\n/* ── APP ────────────────────────────────────────────────────────────────── */\n#app{width:100%;max-width:860px;padding:12px;opacity:0;transition:opacity 1s;\n  pointer-events:none;display:flex;flex-direction:column;gap:8px;height:100vh;max-height:100vh;}\n#app.on{opacity:1;pointer-events:all}\n\n/* MAIN CARD */\n.card{background:var(--s1);border:1px solid var(--b);border-radius:16px;overflow:hidden;flex-shrink:0}\n\n/* ── VIZ (spectrum arriba) ──────────────────────────────────────────────── */\n#viz{width:100%;height:52px;display:block;border-radius:10px 10px 0 0;\n  background:var(--bg);border:1px solid var(--b);border-bottom:none;flex-shrink:0}\n\n/* ── NOW PLAYING ────────────────────────────────────────────────────────── */\n.np{padding:12px 18px 10px;border-bottom:1px solid var(--b);\n  display:flex;align-items:center;gap:14px}\n\n/* Vinyl animado */\n.vinyl{width:52px;height:52px;border-radius:50%;flex-shrink:0;position:relative;\n  background:\n    radial-gradient(circle at 50% 50%,\n      #333 0%,#333 16%,transparent 17%,\n      rgba(255,255,255,.04) 35%,transparent 36%,\n      rgba(255,255,255,.02) 55%,transparent 56%,\n      #1a1a1a 80%\n    );\n  border:1px solid #2a2a2a;}\n.vinyl.spin{animation:vspin 1.8s linear infinite}\n@keyframes vspin{to{transform:rotate(360deg)}}\n.vinyl-dot{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);\n  width:10px;height:10px;border-radius:50%;\n  background:radial-gradient(var(--g),rgba(200,255,0,.4));\n  box-shadow:0 0 8px var(--g)}\n.vinyl-groove{position:absolute;inset:6px;border-radius:50%;\n  border:1px solid rgba(255,255,255,.04)}\n.vinyl-groove2{position:absolute;inset:14px;border-radius:50%;\n  border:1px solid rgba(255,255,255,.03)}\n\n.np-info{flex:1;min-width:0}\n.np-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;\n  color:var(--dim);text-transform:uppercase;margin-bottom:2px}\n.np-title{font-family:'Bebas Neue',sans-serif;font-size:clamp(22px,3.8vw,34px);\n  letter-spacing:1px;line-height:1;margin-bottom:3px;\n  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n.np-meta{display:flex;gap:8px;font-family:'IBM Plex Mono',monospace;font-size:10px;\n  flex-wrap:wrap;align-items:center}\n.np-meta .bpm{color:var(--g);font-weight:700}\n.np-meta .egy{color:var(--c)}\n.np-meta .key{color:var(--p);font-size:9px;\n  padding:1px 5px;border-radius:5px;border:1px solid rgba(176,96,255,.25)}\n.np-meta .dm{color:var(--dim)}\n\n/* Phase pill */\n.pill{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:1px;\n  text-transform:uppercase;padding:2px 8px;border-radius:8px;flex-shrink:0;\n  border:1px solid}\n.pill-warm-up     {color:var(--c);border-color:rgba(0,240,255,.25);background:rgba(0,240,255,.06)}\n.pill-first-build {color:var(--g);border-color:rgba(200,255,0,.2);background:rgba(200,255,0,.05)}\n.pill-first-peak  {color:var(--g);border-color:rgba(200,255,0,.4);background:rgba(200,255,0,.1);\n  animation:peakpulse 1.2s ease-in-out infinite}\n.pill-breakdown   {color:var(--o);border-color:rgba(255,149,0,.3);background:rgba(255,149,0,.07)}\n.pill-second-build{color:var(--g);border-color:rgba(200,255,0,.25);background:rgba(200,255,0,.06)}\n.pill-second-peak {color:var(--g);border-color:rgba(200,255,0,.5);background:rgba(200,255,0,.12);\n  animation:peakpulse .9s ease-in-out infinite}\n.pill-outro       {color:var(--dim);border-color:rgba(61,68,102,.4);background:rgba(61,68,102,.1)}\n@keyframes peakpulse{\n  0%,100%{box-shadow:none}50%{box-shadow:0 0 10px rgba(200,255,0,.35)}}\n\n/* ── WAVEFORM + PLAYHEAD ────────────────────────────────────────────────── */\n.ww{padding:6px 18px;position:relative;border-bottom:1px solid var(--b);\n  user-select:none;-webkit-user-select:none}\n#wc{width:100%;height:42px;display:block;border-radius:5px;background:var(--s2);\n  cursor:col-resize}\n.ph{position:absolute;top:6px;bottom:6px;width:2px;\n  background:var(--g);box-shadow:0 0 8px var(--g);\n  pointer-events:none;border-radius:1px}\n.ph.scrubbing{background:white;box-shadow:0 0 12px white}\n.ph-handle{position:absolute;top:50%;transform:translate(-50%,-50%);\n  width:12px;height:12px;border-radius:50%;\n  background:var(--g);box-shadow:0 0 8px var(--g);\n  pointer-events:none;transition:transform .1s}\n.ph-handle.scrubbing{transform:translate(-50%,-50%) scale(1.5);background:white;box-shadow:0 0 12px white}\n.ww-tooltip{position:absolute;top:-22px;transform:translateX(-50%);\n  font-family:'IBM Plex Mono',monospace;font-size:9px;\n  background:rgba(0,0,0,.8);color:var(--t);padding:2px 6px;border-radius:4px;\n  pointer-events:none;opacity:0;transition:opacity .15s;white-space:nowrap}\n.ww-tooltip.show{opacity:1}\n.times{display:flex;justify-content:space-between;\n  font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--dim);margin-top:3px}\n.times .cur{color:var(--t)}\n\n/* ── EQ METERS (visual de lo que hace el EQ durante el mix) ───────────────── */\n.eq-row{padding:5px 18px;border-bottom:1px solid var(--b);\n  display:flex;gap:8px;align-items:center;opacity:0;transition:opacity .4s}\n.eq-row.on{opacity:1}\n.eq-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);\n  letter-spacing:1px;text-transform:uppercase;width:18px;flex-shrink:0}\n.eq-band{flex:1;height:3px;border-radius:2px;background:var(--s2);overflow:hidden;position:relative}\n.eq-fill{height:100%;border-radius:2px;transition:width .15s linear}\n.eq-fill.lo{background:linear-gradient(90deg,#ff3b5c,#ff6b35)}\n.eq-fill.mid{background:linear-gradient(90deg,#ff9500,var(--g))}\n.eq-fill.hi{background:linear-gradient(90deg,var(--g),var(--c))}\n.eq-sep{width:1px;background:var(--b);height:14px;flex-shrink:0}\n\n/* ── SESSION ARC ─────────────────────────────────────────────────────────── */\n.arc{padding:6px 18px;border-bottom:1px solid var(--b);\n  display:flex;align-items:center;gap:10px}\n.arc-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);\n  letter-spacing:1px;text-transform:uppercase;width:32px;flex-shrink:0}\n.arc-track{flex:1;height:18px;background:var(--s2);border-radius:4px;\n  position:relative;overflow:hidden}\n/* Curva de energía de la sesión dibujada como fondo */\n.arc-track::before{content:'';position:absolute;inset:0;\n  background:linear-gradient(90deg,\n    rgba(0,240,255,.15) 0%,\n    rgba(200,255,0,.25) 30%,\n    rgba(200,255,0,.4)  48%,\n    rgba(255,149,0,.2)  58%,\n    rgba(200,255,0,.35) 72%,\n    rgba(200,255,0,.45) 88%,\n    rgba(0,240,255,.1)  100%\n  );}\n.arc-cursor{position:absolute;top:0;bottom:0;width:3px;\n  background:white;box-shadow:0 0 8px white;\n  transition:left .9s cubic-bezier(.22,1,.36,1);border-radius:2px}\n.arc-phase{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);\n  flex-shrink:0;min-width:60px;text-align:right}\n\n/* ── MIX IN PROGRESS ─────────────────────────────────────────────────────── */\n.mix-row{padding:6px 18px;\n  border-bottom:1px solid rgba(200,255,0,.06);\n  font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:1px;\n  display:none;align-items:center;gap:8px;\n  transition:background .4s,color .4s,border-color .4s}\n.mix-row.on{display:flex}\n/* Guetta: verde lima agresivo */\n.mix-row.style-guetta{\n  background:rgba(200,255,0,.03);color:var(--g);\n  border-bottom-color:rgba(200,255,0,.08)}\n/* Avicii: naranja cálido suave */\n.mix-row.style-avicii{\n  background:rgba(255,149,0,.03);color:var(--o);\n  border-bottom-color:rgba(255,149,0,.08)}\n/* Progressive: cyan técnico */\n.mix-row.style-progressive{\n  background:rgba(0,240,255,.03);color:var(--c);\n  border-bottom-color:rgba(0,240,255,.08)}\n.mix-dot{width:5px;height:5px;border-radius:50%;\n  animation:blink .5s step-end infinite;flex-shrink:0}\n.style-guetta .mix-dot{background:var(--g)}\n.style-avicii .mix-dot{background:var(--o)}\n.style-progressive .mix-dot{background:var(--c)}\n@keyframes blink{50%{opacity:0}}\n.mix-prog{flex:1;height:3px;background:var(--b);border-radius:2px;overflow:hidden}\n.mix-fill{height:100%;border-radius:2px;width:0%;transition:width .2s linear}\n.style-guetta .mix-fill{background:linear-gradient(90deg,var(--c),var(--g))}\n.style-avicii .mix-fill{background:linear-gradient(90deg,#ff6b35,var(--o))}\n.mix-label{font-size:8px;flex-shrink:0;opacity:.7;font-weight:700;letter-spacing:2px}\n.mix-info{color:var(--dim);flex-shrink:0;font-size:8px}\n\n/* ── NEXT UP ─────────────────────────────────────────────────────────────── */\n.nxt{padding:7px 18px;background:rgba(0,240,255,.018);\n  border-bottom:1px solid rgba(0,240,255,.05);\n  display:flex;align-items:center;gap:8px;flex-wrap:wrap}\n.nxt-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:2px;\n  color:var(--c);text-transform:uppercase;flex-shrink:0}\n.nxt-nm{font-size:12px;font-weight:600;flex:1;\n  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n.nxt-sc{font-family:'IBM Plex Mono',monospace;font-size:8px;\n  padding:2px 6px;border-radius:7px;border:1px solid rgba(0,240,255,.18);\n  color:var(--c);flex-shrink:0}\n.nxt-t{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);flex-shrink:0}\n\n/* ── STATUS ──────────────────────────────────────────────────────────────── */\n.st{padding:7px 18px;display:flex;align-items:center;\n  justify-content:space-between;flex-wrap:wrap;gap:6px}\n.st-l{display:flex;align-items:center;gap:7px}\n.bx{background:var(--s2);border:1px solid var(--b);border-radius:7px;\n  padding:4px 11px;text-align:center;font-family:'IBM Plex Mono',monospace}\n.bx .v{font-size:17px;color:var(--g);font-weight:700;line-height:1}\n.bx .l{font-size:7px;color:var(--dim);letter-spacing:2px}\n.live{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:2px;\n  text-transform:uppercase;padding:2px 8px;border-radius:10px;\n  border:1px solid var(--g);color:var(--g);animation:blink 1.4s step-end infinite}\n.mod{font-family:'IBM Plex Mono',monospace;font-size:8px;padding:2px 8px;\n  border-radius:10px;border:1px solid}\n.mod.ok{border-color:rgba(0,240,255,.3);color:var(--c)}\n.mod.fb{border-color:var(--dim);color:var(--dim)}\n.skip-btn{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:1px;\n  padding:3px 10px;border-radius:8px;border:1px solid rgba(200,255,0,.3);\n  background:rgba(200,255,0,.06);color:var(--g);cursor:pointer;transition:all .15s;}\n.skip-btn:hover{background:rgba(200,255,0,.15);border-color:var(--g)}\n.skip-btn:disabled{opacity:.3;cursor:not-allowed}\n#log{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--dim);\n  max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n\n/* ── LIBRARY ─────────────────────────────────────────────────────────────── */\n.lib{background:var(--s1);border:1px solid var(--b);border-radius:14px;\n  overflow:hidden;flex:1;min-height:0;display:flex;flex-direction:column}\n.lib-h{padding:7px 14px;border-bottom:1px solid var(--b);\n  display:flex;align-items:center;justify-content:space-between;flex-shrink:0}\n.lib-h h2{font-family:'IBM Plex Mono',monospace;font-size:8px;\n  letter-spacing:2px;text-transform:uppercase;color:var(--dim)}\n.lib-h .cnt{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--g)}\n.tlist{overflow-y:auto;flex:1}\n.tlist::-webkit-scrollbar{width:2px}\n.tlist::-webkit-scrollbar-thumb{background:var(--b);border-radius:2px}\n.tk{display:grid;grid-template-columns:18px 1fr 32px 44px 28px 32px;\n  align-items:center;gap:5px;padding:5px 14px;\n  border-bottom:1px solid rgba(28,32,64,.5);transition:background .1s}\n.tk:hover{background:var(--s2)}\n.tk.cur{background:rgba(200,255,0,.045);border-left:2px solid var(--g)}\n.tk.nxt{background:rgba(0,240,255,.02);border-left:2px solid rgba(0,240,255,.35)}\n.tk.done{opacity:.28}\n.tn{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);text-align:center}\n.tt{font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n.te{height:2px;border-radius:2px;background:var(--b);overflow:hidden}\n.tef{height:100%;background:linear-gradient(90deg,var(--c),var(--g));border-radius:2px}\n.tb{font-family:'IBM Plex Mono',monospace;font-size:8px;text-align:right}\n.tb.ok{color:var(--g)}.tb.no{color:var(--dim)}\n.ts{font-family:'IBM Plex Mono',monospace;font-size:8px;text-align:right}\n.ts.hi{color:var(--g)}.ts.mi{color:var(--c)}.ts.lo{color:var(--dim)}\n.td{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--dim);text-align:right}\n.empty{padding:28px;text-align:center;color:var(--dim)}\n.empty code{font-family:'IBM Plex Mono',monospace;color:var(--g);font-size:9px}\n\n/* ── TIMELINE DE SESIÓN ──────────────────────────────────────────────────── */\n.timeline{background:var(--s1);border:1px solid var(--b);border-radius:14px;\n  overflow:hidden;flex-shrink:0;padding:8px 14px}\n.tl-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}\n.tl-h span{font-family:'IBM Plex Mono',monospace;font-size:8px;\n  letter-spacing:2px;text-transform:uppercase;color:var(--dim)}\n.tl-track{position:relative;height:28px;background:var(--s2);border-radius:5px;overflow:hidden}\n/* Curva de energía de sesión como fondo */\n.tl-energy-curve{position:absolute;inset:0;opacity:.25}\n.tl-blocks{position:absolute;inset:0;display:flex}\n.tl-block{height:100%;position:relative;border-right:1px solid var(--bg);\n  cursor:pointer;transition:filter .15s;flex-shrink:0}\n.tl-block:hover{filter:brightness(1.4)}\n.tl-block.playing{box-shadow:inset 0 0 0 1px white}\n.tl-block.done{opacity:.5}\n.tl-block.future{opacity:.3}\n.tl-head{position:absolute;top:0;bottom:0;width:2px;background:white;\n  box-shadow:0 0 6px white;pointer-events:none;transition:left .1s linear}\n.tl-labels{display:flex;margin-top:3px;position:relative;height:14px}\n.tl-lbl{position:absolute;font-family:'IBM Plex Mono',monospace;font-size:7px;\n  color:var(--dim);transform:translateX(-50%);white-space:nowrap;\n  overflow:hidden;text-overflow:ellipsis;max-width:80px}\n.tl-lbl.cur{color:var(--g)}\n\n/* ── CUE / PREVIEW ───────────────────────────────────────────────────────── */\n.cue-btn{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:1px;\n  padding:3px 9px;border-radius:8px;\n  border:1px solid rgba(176,96,255,.35);\n  background:rgba(176,96,255,.08);color:var(--p);\n  cursor:pointer;transition:all .15s;flex-shrink:0}\n.cue-btn:hover{background:rgba(176,96,255,.2);border-color:var(--p)}\n.cue-btn.cueing{background:rgba(176,96,255,.25);border-color:var(--p);\n  animation:peakpulse .8s ease-in-out infinite}\n.cue-btn:disabled{opacity:.3;cursor:not-allowed}\n\n/* ── BEAT indicator ──────────────────────────────────────────────────────── */\n.beat-dot{width:6px;height:6px;border-radius:50%;background:var(--g);\n  opacity:0;transition:opacity .05s;flex-shrink:0}\n.beat-dot.flash{opacity:1}\n";
      document.head.appendChild(s);
    }

    // 2. Pass djId to script + reset running flag
    window.__DJ_AI_ID = djId;
    window.__DJ_AI_RUNNING = false;

    // 3. Inject script (remove old one first)
    const SCRIPT_ID = 'djai-script';
    document.getElementById(SCRIPT_ID)?.remove();
    const sc = document.createElement('script');
    sc.id = SCRIPT_ID;
    sc.src = '/dj-ai-player.js?t=' + Date.now();
    document.body.appendChild(sc);

    return () => {
      document.getElementById(SCRIPT_ID)?.remove();
      document.getElementById(CSS_ID)?.remove();
      // Stop audio context if open
      try {
        if (window.ctx) { window.ctx.close(); window.ctx = null; }
      } catch(e) {}
      window.S = null;
      delete window.__DJ_AI_ID;
    };
  }, [djId]);

  return (
    <div style={{ position:'fixed', top:0, left:0, width:'100vw', height:'100vh', zIndex:9999, background:'#07080f', overflow:'hidden' }}>

      <button
        onClick={onClose}
        style={{ position:'absolute', top:'14px', right:'18px', zIndex:10000,
          background:'transparent', border:'1px solid rgba(200,255,0,0.35)',
          color:'#c8ff00', borderRadius:'8px', padding:'5px 14px',
          cursor:'pointer', fontFamily:'IBM Plex Mono,monospace', fontSize:'11px',
          letterSpacing:'2px' }}
      >
        ✕ CERRAR
      </button>

      {/* IDLE */}
<div id="idle">
  <div className="idle-logo">DJ AI</div>
  <div className="idle-sub">Sesión autónoma · mezcla inteligente en vivo</div>
  <button className="play-btn" id="btnStart" disabled>▶</button>
  <div className="idle-info" id="idleInfo">Cargando biblioteca...</div>
</div>

{/* PLAYER */}
<div id="app">

  <canvas id="viz"></canvas>

  <div className="card">

    {/* NOW PLAYING */}
    <div className="np">
      <div className="vinyl" id="vinyl">
        <div className="vinyl-groove"></div>
        <div className="vinyl-groove2"></div>
        <div className="vinyl-dot"></div>
      </div>
      <div className="np-info">
        <div className="np-lbl">Now playing</div>
        <div className="np-title" id="npTitle">—</div>
        <div className="np-meta">
          <span className="bpm" id="npBpm">—</span>
          <span className="egy" id="npEgy">—</span>
          <span className="key" id="npKey" style={{display:'none'}}>—</span>
          <span className="dm"  id="npDur">—</span>
          <span className="pill" id="phasePill">warm-up</span>
        </div>
      </div>
    </div>

    {/* WAVEFORM */}
    <div className="ww" id="ww">
      <canvas id="wc"></canvas>
      <div className="ph" id="ph" style={{left:'18px'}}>
        <div className="ph-handle" id="phHandle"></div>
      </div>
      <div className="ww-tooltip" id="wwTooltip">0:00</div>
      <div className="times">
        <span className="cur" id="tCur">0:00</span>
        <span id="tTot">0:00</span>
      </div>
    </div>

    {/* EQ BANDS (visible durante el mix) */}
    <div className="eq-row" id="eqRow">
      <div className="eq-lbl">LO</div>
      <div className="eq-band"><div className="eq-fill lo" id="eqLo" style={{width:'100%'}}></div></div>
      <div className="eq-sep"></div>
      <div className="eq-lbl" style={{width:'24px'}}>MID</div>
      <div className="eq-band"><div className="eq-fill mid" id="eqMid" style={{width:'100%'}}></div></div>
      <div className="eq-sep"></div>
      <div className="eq-lbl">HI</div>
      <div className="eq-band"><div className="eq-fill hi" id="eqHi" style={{width:'100%'}}></div></div>
    </div>

    {/* SESSION ARC */}
    <div className="arc">
      <div className="arc-lbl">Arco</div>
      <div className="arc-track">
        <div className="arc-cursor" id="arcCursor" style={{left:'0%'}}></div>
      </div>
      <div className="arc-phase" id="arcPhase">warm-up</div>
    </div>

    {/* MIX IN PROGRESS */}
    <div className="mix-row" id="mixRow">
      <div className="mix-dot"></div>
      <div className="mix-label" id="mixStyleLabel">⚡</div>
      <div className="mix-prog"><div className="mix-fill" id="mixFill"></div></div>
      <div className="mix-info" id="mixInfo">mezclando...</div>
    </div>

    {/* NEXT UP */}
    <div className="nxt" id="nxtRow" style={{display:'none'}}>
      <div className="nxt-lbl">IA Next</div>
      <div className="nxt-nm" id="nxtNm">—</div>
      <div className="nxt-sc" id="nxtSc">—</div>
      <div className="nxt-t"  id="nxtT">—</div>
      <button className="cue-btn" id="btnCue" disabled title="Preview 5s de la siguiente">👂 CUE</button>
    </div>

    {/* STATUS */}
    <div className="st">
      <div className="st-l">
        <div className="bx"><div className="v" id="bpmVal">—</div><div className="l">BPM</div></div>
        <div className="live">● LIVE</div>
        <div className="beat-dot" id="beatDot"></div>
        <div className="mod" id="modB">—</div>
        <button className="skip-btn" id="btnSkip" disabled title="Saltar al mix ahora">⏭ MIX NOW</button>
      </div>
      <div id="log">—</div>
    </div>

  </div>{/* .card */}

  {/* TIMELINE DE SESIÓN */}
  <div className="timeline" id="tlWrap" style={{display:'none'}}>
    <div className="tl-h">
      <span>Timeline · sesión</span>
      <span id="tlDur">—</span>
    </div>
    <div className="tl-track" id="tlTrack">
      <canvas className="tl-energy-curve" id="tlCurve"></canvas>
      <div className="tl-blocks" id="tlBlocks"></div>
      <div className="tl-head"   id="tlHead"  style={{left:'0%'}}></div>
    </div>
    <div className="tl-labels" id="tlLabels"></div>
  </div>

  {/* LIBRARY */}
  <div className="lib">
    <div className="lib-h">
      <h2>🎵 Biblioteca</h2>
      <span className="cnt" id="libCount">—</span>
    </div>
    <div className="tlist" id="tlist">
      <div className="empty"><p>Cargando...</p></div>
    </div>
  </div>

</div>{/* #app */}

    </div>
  );
}