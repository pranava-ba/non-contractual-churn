"""The single-page dashboard rendered inside QWebEngineView.

Design mirrors research-paper-tracker: indigo/violet glassmorphism, light/dark
aware, WCAG-friendly. Data + actions come from the Python `backend` over
QWebChannel. Three tiers: Core candidates -> Helpers -> Additional.
"""
from __future__ import annotations

_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
:root{
  --head:'Sora','Segoe UI',system-ui,sans-serif; --body:'Inter','Segoe UI',system-ui,sans-serif;
  --accent:#5E6AD2; --accent-2:#8B5CF6; --glow:rgba(94,106,210,.35);
  --text:#EDEDF2; --muted:#A6ABC4; --faint:#767C97;
  --glass:rgba(255,255,255,.05); --glass-2:rgba(255,255,255,.08); --glass-hi:rgba(255,255,255,.14);
  --border:rgba(255,255,255,.10); --border-2:rgba(255,255,255,.18);
  --chrome:rgba(14,15,30,.74); --card:rgba(20,22,42,.74); --card-2:rgba(30,33,58,.82);
  --chip-bg:rgba(124,131,232,.20); --chip-fg:#C7CBFF;
  --ok:#34D399; --ok-bg:rgba(52,211,153,.16); --due:#FBBF24; --due-bg:rgba(251,191,36,.16);
  --over:#F87171; --over-bg:rgba(248,113,113,.16); --never:#A6ABC4; --never-bg:rgba(255,255,255,.08);
  --g1:#0b0b16; --g2:#12122a; --g3:#0a0a13; --radius:16px;
}
@media (prefers-color-scheme:light){:root{
  --text:#1B1B2E; --muted:#54586E; --faint:#8388A0;
  --glass:rgba(255,255,255,.55); --glass-2:rgba(255,255,255,.72); --glass-hi:rgba(255,255,255,.85);
  --border:rgba(120,120,160,.18); --border-2:rgba(120,120,160,.28);
  --chrome:rgba(255,255,255,.82); --card:rgba(255,255,255,.86); --card-2:rgba(255,255,255,.92);
  --chip-bg:rgba(94,106,210,.14); --chip-fg:#4048B0;
  --ok:#059669; --ok-bg:rgba(5,150,105,.12); --due:#B45309; --due-bg:rgba(180,83,9,.12);
  --over:#DC2626; --over-bg:rgba(220,38,38,.12); --never:#54586E; --never-bg:rgba(0,0,0,.05);
  --g1:#EEF0FB; --g2:#F3F0FF; --g3:#E9F0FF;
}}
*{box-sizing:border-box} html,body{margin:0;height:100%}
body{font-family:var(--body);color:var(--text);font-size:14px;line-height:1.5;
  display:flex;flex-direction:column;height:100%;-webkit-font-smoothing:antialiased}
.tnum{font-variant-numeric:tabular-nums}
a{color:inherit} button{font-family:inherit;color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:8px}
.bg{position:fixed;inset:0;z-index:-2;background:linear-gradient(135deg,var(--g1),var(--g2) 55%,var(--g3))}
.blob{position:fixed;z-index:-1;border-radius:50%;filter:blur(80px);opacity:.4;pointer-events:none}
.b1{width:520px;height:520px;top:-140px;left:-120px;background:radial-gradient(circle,#5E6AD2,transparent 62%)}
.b2{width:460px;height:460px;bottom:-160px;right:-100px;background:radial-gradient(circle,#8B5CF6,transparent 62%)}

header{display:flex;align-items:center;gap:14px;padding:11px 20px;background:var(--chrome);
  border-bottom:1px solid var(--border);flex:none}
.brand{display:flex;align-items:center;gap:10px}
.brand .logo{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;
  background:linear-gradient(135deg,var(--accent),var(--accent-2));box-shadow:0 4px 14px var(--glow)}
.brand .logo svg{width:18px;height:18px;color:#fff}
.brand h1{font-family:var(--head);font-size:17px;font-weight:700;margin:0}
.brand .sub{font-size:12px;color:var(--muted);margin-top:1px}
.spacer{flex:1}
.iconbtn{width:36px;height:36px;display:grid;place-items:center;border-radius:10px;cursor:pointer;
  background:var(--glass);border:1px solid var(--border);transition:all .16s ease}
.iconbtn:hover{background:var(--glass-hi)} .iconbtn svg{width:17px;height:17px;color:var(--muted)}
.iconbtn.danger:hover{background:var(--over-bg);border-color:var(--over)} .iconbtn.danger:hover svg{color:var(--over)}

.scroll{flex:1;overflow:auto;padding:20px;display:flex;flex-direction:column;gap:16px}
.wrap{max-width:1180px;width:100%;margin:0 auto;display:flex;flex-direction:column;gap:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  box-shadow:0 8px 30px rgba(0,0,0,.14)}

/* search */
.search{padding:16px 18px;display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end}
.field{display:flex;flex-direction:column;gap:5px}
.field label{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--faint);font-weight:700}
.field.grow{flex:1;min-width:240px}
input,select{font-family:inherit;font-size:13.5px;color:var(--text);background:var(--never-bg);
  border:1px solid var(--border);border-radius:10px;padding:9px 11px;outline:none}
input:focus,select:focus{border-color:var(--accent)}
select option{color:#111}
input[type=number]{width:96px}
.toggle{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--muted);padding-bottom:9px;cursor:pointer}
.btn{display:inline-flex;align-items:center;gap:8px;border:none;cursor:pointer;
  background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff;
  padding:10px 18px;border-radius:10px;font-size:13.5px;font-weight:700;box-shadow:0 4px 16px var(--glow);
  transition:filter .16s ease,opacity .16s ease;white-space:nowrap}
.btn:hover{filter:brightness(1.08)} .btn:disabled{opacity:.55;cursor:default;box-shadow:none}
.btn.ghost{background:var(--never-bg);color:var(--text);border:1px solid var(--border);box-shadow:none}
.btn.ghost:hover{background:var(--glass-hi)}
.spinner{width:15px;height:15px;border:2px solid #fff;border-right-color:transparent;border-radius:50%;
  animation:spin .7s linear infinite;display:none} .btn.busy .spinner{display:inline-block}
@keyframes spin{to{transform:rotate(360deg)}}

.hint{color:var(--faint);font-size:12.5px;padding:0 4px;line-height:1.6}
.hint b{color:var(--muted)}
.sec-head{display:flex;align-items:center;gap:10px;font-family:var(--head);font-size:15px;font-weight:700;padding:0 4px}
.sec-head .n{font-size:12px;font-weight:700;color:var(--muted);background:var(--never-bg);
  border:1px solid var(--border);padding:2px 9px;border-radius:999px}

/* paper card */
.plist{display:flex;flex-direction:column;gap:10px}
.paper{padding:13px 15px;border:1px solid var(--border);border-radius:13px;background:var(--card-2);
  display:flex;gap:12px;align-items:flex-start;transition:border-color .15s ease}
.paper:hover{border-color:var(--border-2)}
.paper.sel{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.dot{width:11px;height:11px;border-radius:50%;flex:none;margin-top:5px}
.dot.strong{background:var(--ok);box-shadow:0 0 8px var(--ok)} .dot.ok{background:var(--due)}
.dot.weak{background:var(--over)} .dot.unknown{background:var(--never)}
.pbody{flex:1;min-width:0}
.ptitle{font-family:var(--head);font-weight:600;font-size:14.5px;line-height:1.35;cursor:pointer}
.ptitle:hover{color:var(--accent);text-decoration:underline}
.pmeta{color:var(--muted);font-size:12px;margin-top:3px}
.pmeta .vt{text-transform:capitalize}
.chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px;align-items:center}
.chip{font-size:11px;font-weight:600;border-radius:6px;padding:2px 8px;white-space:nowrap}
.chip.metric{color:#fff}
.chip.metric.open{background:var(--ok)} .chip.metric.tight{background:var(--due)}
.chip.metric.saturated{background:var(--over)} .chip.metric.unknown{background:var(--never)}
.chip.ds{background:var(--chip-bg);color:var(--chip-fg)}
.chip.code{background:var(--ok-bg);color:var(--ok)}
.chip.src{background:var(--never-bg);color:var(--muted);border:1px solid var(--border)}
.pacts{display:flex;flex-direction:column;gap:6px;flex:none;align-items:flex-end}
.mini{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;cursor:pointer;
  background:var(--never-bg);border:1px solid var(--border);border-radius:8px;padding:6px 10px;color:var(--text);
  transition:all .14s ease;white-space:nowrap}
.mini:hover{background:var(--glass-hi);border-color:var(--border-2)}
.mini.primary{background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff;border:none}
.mini svg{width:13px;height:13px}
.abs{display:none;margin-top:10px;padding:11px 13px;background:var(--never-bg);border:1px solid var(--border);
  border-radius:10px;color:var(--muted);font-size:12.5px;line-height:1.6}
.paper.open .abs{display:block}
.why{margin-top:8px;padding-top:8px;border-top:1px dashed var(--border-2);color:var(--faint);font-size:12px}
.why b{color:var(--accent)}

/* related */
.banner{padding:14px 16px;display:flex;gap:12px;align-items:center;
  background:linear-gradient(135deg,rgba(94,106,210,.16),rgba(139,92,246,.10))}
.banner .bt{font-family:var(--head);font-weight:700;font-size:14px}
.banner .bm{color:var(--muted);font-size:12px;margin-top:2px}
.controls{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;padding:14px 16px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:860px){.cols{grid-template-columns:1fr}}
.col h3{font-family:var(--head);font-size:13.5px;font-weight:700;margin:0 0 4px;padding:0 4px}
.col .csub{color:var(--faint);font-size:11.5px;padding:0 4px;margin-bottom:9px}
.rrow{display:flex;gap:10px;padding:10px 12px;border:1px solid var(--border);border-radius:11px;
  background:var(--card-2);margin-bottom:8px}
.rrow .idx{color:var(--faint);font-weight:700;font-size:12px;min-width:20px}
.rrow .rt{font-weight:600;font-size:13px;line-height:1.35;cursor:pointer}
.rrow .rt:hover{color:var(--accent);text-decoration:underline}
.rrow .rm{color:var(--muted);font-size:11.5px;margin-top:2px}
.racts{display:flex;gap:5px;flex:none}
.ract{width:26px;height:26px;border-radius:7px;display:grid;place-items:center;cursor:pointer;
  background:transparent;border:1px solid transparent}
.ract:hover{background:var(--glass-hi);border-color:var(--border)} .ract svg{width:13px;height:13px;color:var(--muted)}
.exportbar{display:flex;gap:10px;align-items:center;padding:14px 16px;flex-wrap:wrap}
.exportbar .lab{color:var(--muted);font-size:12.5px;margin-right:auto}

.empty{color:var(--faint);font-size:13px;text-align:center;padding:34px 16px}
.err{background:var(--over-bg);color:var(--over);padding:10px 14px;border-radius:11px;font-size:13px;font-weight:600}
#toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(20px);
  background:var(--card-2);border:1px solid var(--border-2);color:var(--text);padding:10px 18px;
  border-radius:11px;font-size:13px;font-weight:600;box-shadow:0 8px 30px rgba(0,0,0,.3);opacity:0;
  pointer-events:none;transition:all .25s ease;z-index:50}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.hidden{display:none!important}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<div class="bg"></div><div class="blob b1"></div><div class="blob b2"></div>

<header>
  <div class="brand">
    <span class="logo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg></span>
    <div><h1>Paper Explorer</h1><div class="sub">find a journal (not conference) paper to reproduce &amp; beat</div></div>
  </div>
  <span class="spacer"></span>
  <button id="exit" class="iconbtn danger" title="Exit"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg></button>
</header>

<div class="scroll">
<div class="wrap">

  <div class="card search">
    <div class="field grow">
      <label for="preset">Sub-domain</label>
      <select id="preset"></select>
    </div>
    <div class="field grow">
      <label for="query">Search query</label>
      <input id="query" type="text" placeholder="e.g. deep learning EEG classification">
    </div>
    <div class="field"><label for="year">Since year</label><input id="year" type="number" value="2023" min="2023" max="2026"></div>
    <div class="field"><label for="cites">Min citations</label><input id="cites" type="number" value="5" min="0" step="5"></div>
    <label class="toggle"><input id="jonly" type="checkbox" checked> Journals only</label>
    <button id="go" class="btn"><span class="spinner"></span><span id="go-label">Find core papers</span></button>
  </div>

  <div id="err" class="err hidden"></div>

  <div class="hint" id="hint">
    Pick a sub-domain (or type a query), then <b>Find core papers</b>. Results are
    <b>journal articles only</b> &mdash; conferences are filtered out. The coloured dot rates
    beatability from the abstract: <b style="color:var(--ok)">green</b> = clear room + public data,
    <b style="color:var(--due)">amber</b> = partial, <b style="color:var(--over)">red</b> = saturated (hard to beat).
    Select a core paper to pull its <b>helpers</b> (foundational references) and <b>additional</b>
    (papers that cite it) for your reference list.
  </div>

  <div id="core-section" class="hidden">
    <div class="sec-head">Core candidates <span class="n" id="core-n">0</span>
      <span style="font-weight:400;color:var(--faint);font-size:12px">journal, not conference</span></div>
    <div class="card" style="padding:12px"><div id="core-list" class="plist"></div></div>
  </div>

  <div id="related" class="hidden">
    <div class="card" style="overflow:hidden">
      <div class="banner">
        <span class="dot strong" id="ban-dot"></span>
        <div style="flex:1;min-width:0"><div class="bt" id="ban-title">&mdash;</div><div class="bm" id="ban-meta"></div></div>
        <button class="mini" id="ban-open"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>Open</button>
      </div>
      <div class="controls">
        <div class="field"><label for="nh">Helpers</label><input id="nh" type="number" value="5" min="1" max="25"></div>
        <div class="field"><label for="na">Additional</label><input id="na" type="number" value="40" min="5" max="50"></div>
        <div class="field"><label for="asort">Additional order</label>
          <select id="asort"><option value="cited_by_count:desc">Most cited</option><option value="publication_date:desc">Most recent</option></select></div>
        <button id="reload" class="btn ghost"><span class="spinner"></span><span id="reload-label">Update lists</span></button>
      </div>
    </div>

    <div class="cols">
      <div class="col"><h3>Helpers &mdash; 5 to start with</h3>
        <div class="csub">The core paper's most-cited references (read these first).</div>
        <div id="helpers"><div class="empty">Loading&hellip;</div></div></div>
      <div class="col"><h3>Additional &mdash; reference pool</h3>
        <div class="csub">Papers that cite the core &mdash; fill your 25&ndash;50 reference list.</div>
        <div id="additional"><div class="empty">Loading&hellip;</div></div></div>
    </div>

    <div class="card exportbar">
      <span class="lab">Export the core + helpers + additional as your bibliography.</span>
      <button id="exp-bib" class="btn ghost">Export BibTeX</button>
      <button id="exp-csv" class="btn ghost">Export CSV</button>
    </div>
  </div>

</div>
</div>
<div id="toast"></div>

<script>/*QWEBCHANNEL_JS*/</script>
<script>
"use strict";
let backend=null, PRESETS=[], CORE=[], SELECTED=null, HELPERS=[], ADDITIONAL=[];

function el(t,c,x){const e=document.createElement(t); if(c)e.className=c; if(x!=null)e.textContent=x; return e;}
function $(id){return document.getElementById(id);}
let toastT; function toast(m){const t=$("toast");t.textContent=m;t.classList.add("show");
  clearTimeout(toastT);toastT=setTimeout(()=>t.classList.remove("show"),1800);}
function showErr(m){const e=$("err");e.textContent=m;e.classList.remove("hidden");}
function clearErr(){$("err").classList.add("hidden");}

const ICON={
  open:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
  copy:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'};

function authorsShort(a){ if(!a||!a.length) return ""; return a.length<=3?a.join(", "):a.slice(0,3).join(", ")+" et al."; }
function citation(p){ const yr=p.year?("("+p.year+").") : "";
  const id=p.doi?("https://doi.org/"+p.doi):(p.url||"");
  return [authorsShort(p.authors), yr, p.title+".", p.venue?(p.venue+"."):"", id].filter(Boolean).join(" "); }

function metricChip(p){ if(p.headline){ const v=p.headline.value;
    return {cls:p.room, txt:p.headline.name+" "+v+"%"}; }
  return {cls:"unknown", txt:"no metric"}; }

/* ---------- core list ---------- */
function renderCore(){
  const box=$("core-list"); box.innerHTML="";
  $("core-n").textContent=CORE.length;
  $("core-section").classList.toggle("hidden", CORE.length===0);
  if(!CORE.length){ box.appendChild(el("div","empty","No journal papers matched. Loosen the filters (lower min citations or earlier year).")); return; }
  CORE.forEach(p=>{
    const row=el("div","paper"+(SELECTED&&SELECTED.id===p.id?" sel":""));
    row.appendChild(el("span","dot "+(p.band||"unknown")));
    const body=el("div","pbody");
    const t=el("div","ptitle",p.title); t.onclick=()=>backend.openUrl(p.url); body.appendChild(t);
    body.appendChild(el("div","pmeta",authorsShort(p.authors)));
    const meta2=el("div","pmeta"); meta2.innerHTML=
      '<span class="vt">'+(p.venue||"—")+'</span> · '+(p.year||"—")+' · '+p.citations+' citations'+
      (p.topic?(' · '+p.topic):'');
    body.appendChild(meta2);
    const chips=el("div","chips"); const mc=metricChip(p);
    chips.appendChild(el("span","chip metric "+mc.cls, mc.txt));
    (p.datasets||[]).forEach(d=>chips.appendChild(el("span","chip ds",d)));
    if(p.public_hint && !(p.datasets||[]).length) chips.appendChild(el("span","chip ds","public data"));
    if(p.code) chips.appendChild(el("span","chip code","code ✓"));
    if(!(p.datasets||[]).length && !p.public_hint) chips.appendChild(el("span","chip src","no public data named"));
    body.appendChild(chips);
    const abs=el("div","abs");
    if(p.abstract) abs.appendChild(el("div",null,p.abstract));
    const why=el("div","why"); why.innerHTML="<b>Beatability:</b> "+(p.reasons||[]).join(" · ");
    abs.appendChild(why); body.appendChild(abs);
    const acts=el("div","pacts");
    const sel=el("button","mini primary"); sel.textContent=(SELECTED&&SELECTED.id===p.id)?"Selected":"Select core →";
    sel.onclick=()=>selectCore(p.id); acts.appendChild(sel);
    const det=el("button","mini"); det.textContent="Abstract";
    det.onclick=()=>row.classList.toggle("open"); acts.appendChild(det);
    row.appendChild(body); row.appendChild(acts);
    box.appendChild(row);
  });
}

/* ---------- select + related ---------- */
function selectCore(id){
  SELECTED=CORE.find(p=>p.id===id); if(!SELECTED) return;
  renderCore();
  const mc=metricChip(SELECTED);
  $("ban-dot").className="dot "+(SELECTED.band||"unknown");
  $("ban-title").textContent=SELECTED.title;
  $("ban-meta").textContent=(SELECTED.venue||"—")+" · "+(SELECTED.year||"—")+" · "+SELECTED.citations+" citations · "+mc.txt;
  $("ban-open").onclick=()=>backend.openUrl(SELECTED.url);
  $("related").classList.remove("hidden");
  $("helpers").innerHTML='<div class="empty">Loading…</div>';
  $("additional").innerHTML='<div class="empty">Loading…</div>';
  loadRelated();
  $("related").scrollIntoView({behavior:"smooth",block:"start"});
}
function loadRelated(){
  if(!SELECTED) return;
  setBusy("reload",true);
  backend.loadRelated(JSON.stringify({workId:SELECTED.id,
    nHelpers:+$("nh").value||5, nAdditional:+$("na").value||40, addSort:$("asort").value}));
}
function rrow(p,i){
  const r=el("div","rrow");
  r.appendChild(el("span","idx tnum",i+1));
  const b=el("div",null); b.style.flex="1"; b.style.minWidth="0";
  const t=el("div","rt",p.title); t.onclick=()=>backend.openUrl(p.url); b.appendChild(t);
  const mc=metricChip(p);
  let m=authorsShort(p.authors)+" · "+(p.year||"—")+" · "+p.citations+" cites";
  if(p.venue) m+=" · "+p.venue;
  b.appendChild(el("div","rm",m));
  const acts=el("div","racts");
  const cp=el("button","ract"); cp.title="Copy citation"; cp.innerHTML=ICON.copy;
  cp.onclick=()=>{backend.copyToClipboard(citation(p));toast("Citation copied");}; acts.appendChild(cp);
  const op=el("button","ract"); op.title="Open"; op.innerHTML=ICON.open;
  op.onclick=()=>backend.openUrl(p.url); acts.appendChild(op);
  r.appendChild(b); r.appendChild(acts); return r;
}
function renderRelated(){
  const h=$("helpers"); h.innerHTML="";
  if(!HELPERS.length) h.appendChild(el("div","empty","No references found for this paper."));
  else HELPERS.forEach((p,i)=>h.appendChild(rrow(p,i)));
  const a=$("additional"); a.innerHTML="";
  if(!ADDITIONAL.length) a.appendChild(el("div","empty","No papers cite this one yet."));
  else ADDITIONAL.forEach((p,i)=>a.appendChild(rrow(p,i)));
}

/* ---------- export ---------- */
function exportSet(kind){
  if(!SELECTED){toast("Select a core paper first");return;}
  const set=[Object.assign({role:"core"},SELECTED)]
    .concat(HELPERS.map(p=>Object.assign({role:"helper"},p)))
    .concat(ADDITIONAL.map(p=>Object.assign({role:"additional"},p)));
  backend.exportSelection(kind, JSON.stringify(set));
}

/* ---------- busy ---------- */
function setBusy(btn,b){ const e=$(btn); e.classList.toggle("busy",b); e.disabled=b;
  const lab=$(btn+"-label"); if(lab) lab.textContent=b?(btn==="go"?"Searching…":"Updating…"):(btn==="go"?"Find core papers":"Update lists"); }

/* ---------- init ---------- */
function doSearch(){
  clearErr(); setBusy("go",true);
  backend.searchCore(JSON.stringify({
    query:$("query").value, yearFrom:Math.max(+$("year").value||2023,2023),
    minCitations:+$("cites").value||0, journalsOnly:$("jonly").checked, limit:40}));
}
window.onload=function(){
  new QWebChannel(qt.webChannelTransport,function(ch){
    backend=ch.objects.backend;
    backend.searchStarted.connect(()=>setBusy("go",true));
    backend.coreResults.connect(j=>{ setBusy("go",false);
      const d=JSON.parse(j); CORE=d.papers||[]; SELECTED=null;
      $("related").classList.add("hidden"); renderCore();
      if(CORE.length) $("core-section").scrollIntoView({behavior:"smooth",block:"nearest"}); });
    backend.relatedStarted.connect(()=>setBusy("reload",true));
    backend.relatedResults.connect(j=>{ setBusy("reload",false);
      const d=JSON.parse(j); HELPERS=d.helpers||[]; ADDITIONAL=d.additional||[]; renderRelated(); });
    backend.failed.connect(m=>{ setBusy("go",false); setBusy("reload",false); showErr(m); });
    backend.exported.connect(p=>{ if(p) toast("Saved: "+p); });
    backend.presets(function(j){ PRESETS=JSON.parse(j);
      const sel=$("preset"); sel.appendChild(new Option("— choose a sub-domain —",""));
      PRESETS.forEach(pr=>sel.appendChild(new Option(pr.label,pr.key)));
    });
  });
  $("preset").onchange=e=>{ const pr=PRESETS.find(x=>x.key===e.target.value);
    if(pr){ $("query").value=pr.query; } };
  $("go").onclick=doSearch;
  $("query").addEventListener("keydown",e=>{ if(e.key==="Enter") doSearch(); });
  $("reload").onclick=loadRelated;
  $("exp-bib").onclick=()=>exportSet("bibtex");
  $("exp-csv").onclick=()=>exportSet("csv");
  $("exit").onclick=()=>backend.quit();
};
</script>
</body>
</html>
"""


def render_page(qwebchannel_js: str) -> str:
    return _HTML.replace("/*QWEBCHANNEL_JS*/", qwebchannel_js)
