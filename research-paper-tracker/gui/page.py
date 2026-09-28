"""The dashboard rendered inside the QWebEngineView. Data, progress, clipboard,
open-url and quit come from the Python `backend` over QWebChannel.

Design: indigo/violet "cinematic" glassmorphism (ui-ux-pro-max) — deep gradient
backdrop with ambient glow, frosted-glass panels (backdrop-blur), electric indigo
accent (#5E6AD2). Papers + Analytics tabs, collapsible sidebar, search/sort/copy,
keyboard shortcuts, remembered view, WCAG-AA contrast, reduced-motion aware.
"""
from __future__ import annotations

_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --head:'Sora','Segoe UI',system-ui,sans-serif;
  --body:'Inter','Segoe UI',system-ui,sans-serif;
  --accent:#5E6AD2; --accent-2:#8B5CF6; --accent-ink:#fff; --glow:rgba(94,106,210,.35);
  --text:#EDEDF2; --muted:#A6ABC4; --faint:#767C97;
  --glass:rgba(255,255,255,.05); --glass-2:rgba(255,255,255,.08); --glass-hi:rgba(255,255,255,.14);
  --border:rgba(255,255,255,.10); --border-2:rgba(255,255,255,.18);
  --chrome:rgba(14,15,30,.74); --card:rgba(20,22,42,.74); --card-2:rgba(30,33,58,.82);
  --chip-bg:rgba(124,131,232,.20); --chip-fg:#C7CBFF; --bar:#7C83E8; --bar-2:#8B5CF6;
  --ok:#34D399; --ok-bg:rgba(52,211,153,.16); --due:#FBBF24; --due-bg:rgba(251,191,36,.16);
  --over:#F87171; --over-bg:rgba(248,113,113,.16); --never:#A6ABC4; --never-bg:rgba(255,255,255,.08);
  --g1:#0b0b16; --g2:#12122a; --g3:#0a0a13; --blur:16px; --radius:16px;
}
@media (prefers-color-scheme:light){
:root{
  --text:#1B1B2E; --muted:#54586E; --faint:#8388A0;
  --glass:rgba(255,255,255,.55); --glass-2:rgba(255,255,255,.72); --glass-hi:rgba(255,255,255,.85);
  --border:rgba(255,255,255,.8); --border-2:rgba(120,120,160,.25);
  --card:rgba(255,255,255,.72); --card-2:rgba(255,255,255,.85);
  --chip-bg:rgba(94,106,210,.14); --chip-fg:#4048B0; --bar:#5E6AD2; --bar-2:#8B5CF6;
  --ok:#059669; --ok-bg:rgba(5,150,105,.12); --due:#B45309; --due-bg:rgba(180,83,9,.12);
  --over:#DC2626; --over-bg:rgba(220,38,38,.12); --never:#54586E; --never-bg:rgba(0,0,0,.05);
  --chrome:rgba(255,255,255,.82); --card:rgba(255,255,255,.86); --card-2:rgba(255,255,255,.92);
  --border:rgba(120,120,160,.18); --border-2:rgba(120,120,160,.28);
  --g1:#EEF0FB; --g2:#F3F0FF; --g3:#E9F0FF;
}}

*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{font-family:var(--body);color:var(--text);font-size:14px;line-height:1.5;
  display:flex;flex-direction:column;overflow:hidden;-webkit-font-smoothing:antialiased}
.tnum{font-variant-numeric:tabular-nums}
button{font-family:inherit;color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:8px}

/* ---- background ---- */
.bg{position:fixed;inset:0;z-index:-2;
  background:linear-gradient(135deg,var(--g1),var(--g2) 55%,var(--g3))}
/* static (non-animated) glows — animating these forces constant recompositing/flicker */
.blob{position:fixed;z-index:-1;border-radius:50%;filter:blur(80px);opacity:.4;pointer-events:none}
.b1{width:520px;height:520px;top:-140px;left:-120px;background:radial-gradient(circle,#5E6AD2,transparent 62%)}
.b2{width:460px;height:460px;bottom:-160px;right:-100px;background:radial-gradient(circle,#8B5CF6,transparent 62%)}
.b3{width:400px;height:400px;top:38%;right:24%;background:radial-gradient(circle,#3B82F6,transparent 62%);opacity:.24}

.glass{background:var(--glass);border:1px solid var(--border)}

/* ---- header ---- */
header{display:flex;align-items:center;gap:14px;padding:11px 18px;
  background:var(--chrome);border-bottom:1px solid var(--border)}
.brand{display:flex;align-items:center;gap:9px}
.brand .logo{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;
  background:linear-gradient(135deg,var(--accent),var(--accent-2));box-shadow:0 4px 14px var(--glow)}
.brand .logo svg{width:17px;height:17px;color:#fff}
.brand h1{font-family:var(--head);font-size:16.5px;font-weight:700;margin:0;letter-spacing:.2px}
.tabs{display:flex;gap:3px;background:var(--never-bg);padding:3px;border-radius:11px;border:1px solid var(--border)}
.tab{border:none;background:transparent;padding:7px 15px;border-radius:8px;font-size:13px;font-weight:600;
  color:var(--muted);cursor:pointer;transition:all .18s ease;display:flex;align-items:center;gap:6px}
.tab:hover{color:var(--text)}
.tab.active{background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff;box-shadow:0 3px 12px var(--glow)}
.tab svg{width:14px;height:14px}
.spacer{flex:1}
.pill{display:inline-flex;align-items:center;gap:7px;padding:5px 12px;border-radius:999px;font-size:12.5px;font-weight:700}
.pill .dot{width:8px;height:8px;border-radius:50%}
.pill.ok{background:var(--ok-bg);color:var(--ok)}.pill.ok .dot{background:var(--ok);box-shadow:0 0 8px var(--ok)}
.pill.due_today{background:var(--due-bg);color:var(--due)}.pill.due_today .dot{background:var(--due)}
.pill.overdue{background:var(--over-bg);color:var(--over)}.pill.overdue .dot{background:var(--over);animation:pulse 1.6s infinite}
.pill.never{background:var(--never-bg);color:var(--never)}.pill.never .dot{background:var(--never)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.iconbtn{width:36px;height:36px;display:grid;place-items:center;border-radius:10px;cursor:pointer;
  background:var(--glass);border:1px solid var(--border);transition:all .16s ease}
.iconbtn:hover{background:var(--glass-hi);border-color:var(--border-2)}
.iconbtn svg{width:17px;height:17px;color:var(--muted)}
.iconbtn:hover svg{color:var(--text)}
.iconbtn.danger:hover{background:var(--over-bg);border-color:var(--over)} .iconbtn.danger:hover svg{color:var(--over)}
.btn{display:inline-flex;align-items:center;gap:8px;border:none;cursor:pointer;
  background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff;
  padding:9px 16px;border-radius:10px;font-size:13.5px;font-weight:700;box-shadow:0 4px 16px var(--glow);
  transition:filter .16s ease,opacity .16s ease}
.btn:hover{filter:brightness(1.08)} .btn:disabled{opacity:.6;cursor:default;box-shadow:none}
.spinner{width:15px;height:15px;border:2px solid #fff;border-right-color:transparent;border-radius:50%;
  animation:spin .7s linear infinite;display:none}
.btn.busy .spinner{display:inline-block}
@keyframes spin{to{transform:rotate(360deg)}}

/* ---- progress ---- */
#progress{height:0;overflow:hidden;transition:height .2s ease}
#progress.show{height:36px}
.pwrap{display:flex;align-items:center;gap:12px;padding:8px 18px;background:var(--glass);border-bottom:1px solid var(--border)}
.ptrack{flex:1;height:7px;background:var(--never-bg);border-radius:999px;overflow:hidden;border:1px solid var(--border)}
.pbar{height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent-2));border-radius:999px;transition:width .3s ease}
.plabel{font-size:12.5px;color:var(--muted);white-space:nowrap}
#errbar{background:var(--over-bg);color:var(--over);padding:8px 18px;font-size:13px;font-weight:600}
.hidden{display:none!important}

/* ---- toolbar ---- */
.toolbar{display:flex;align-items:center;gap:10px;padding:10px 18px;
  background:var(--chrome);border-bottom:1px solid var(--border);font-size:13px;color:var(--muted)}
.search{flex:1;max-width:340px;display:flex;align-items:center;gap:8px;background:var(--never-bg);
  border:1px solid var(--border);border-radius:10px;padding:7px 11px}
.search svg{width:15px;height:15px;color:var(--faint)}
.search input{flex:1;background:none;border:none;outline:none;color:var(--text);font-size:13px}
.search input::placeholder{color:var(--faint)}
select{font-family:inherit;font-size:13px;color:var(--text);background:var(--never-bg);
  border:1px solid var(--border);border-radius:10px;padding:7px 10px;cursor:pointer}
select option{color:#111}
.toolbar label{font-weight:600;color:var(--text)}
#subcount{margin-left:auto;color:var(--muted)}

/* ---- layout ---- */
main{flex:1;display:flex;min-height:0;position:relative}
.side{width:266px;flex:none;overflow:auto;padding:12px 10px;transition:width .22s ease,padding .22s ease;
  background:var(--chrome);border-right:1px solid var(--border)}
.side.collapsed{width:66px;padding:12px 8px}
.side h2{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);font-weight:700;margin:2px 8px 8px}
.side.collapsed h2{opacity:0}
.cat{display:flex;align-items:center;gap:10px;padding:9px 11px;border-radius:11px;cursor:pointer;
  margin-bottom:3px;transition:background .15s ease;position:relative}
.cat:hover{background:var(--glass-2)}
.cat.active{background:linear-gradient(135deg,rgba(94,106,210,.22),rgba(139,92,246,.16));
  box-shadow:inset 0 0 0 1px var(--border-2)}
.cat .badge{width:26px;height:26px;flex:none;border-radius:8px;display:grid;place-items:center;
  font-size:12px;font-weight:700;background:var(--never-bg);color:var(--muted);border:1px solid var(--border)}
.cat.active .badge{background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff;border:none}
.cat.important .badge{color:var(--due)}
.cat.active.important .badge{color:#fff}
.cat-label{flex:1;font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cat.active .cat-label{font-weight:700}
.cat .count{font-size:12px;font-weight:700;color:var(--muted)}
.side.collapsed .cat-label,.side.collapsed .cat .count{display:none}
.side.collapsed .cat{justify-content:center;padding:9px 0}

.content{flex:1;overflow:auto;padding:16px}

/* ---- card + table ---- */
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.18)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
thead th{text-align:left;padding:11px 16px;font-size:11px;
  text-transform:uppercase;letter-spacing:.05em;color:var(--faint);font-weight:700;
  background:var(--card-2);border-bottom:1px solid var(--border)}
tbody td{padding:12px 16px;border-bottom:1px solid var(--border);vertical-align:top}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:var(--glass-2)} tr.open{background:var(--glass-2)}
td.rank{width:38px;color:var(--faint);font-weight:700}
.title-row{display:flex;align-items:flex-start;gap:8px}
.title-link{color:var(--text);text-decoration:none;font-weight:600;font-size:14.5px;cursor:pointer;
  font-family:var(--head);line-height:1.35}
.title-link:hover{color:var(--accent);text-decoration:underline;text-decoration-color:var(--accent)}
.actions{margin-left:auto;display:flex;gap:4px;flex:none}
.act{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;background:transparent;
  border:1px solid transparent;cursor:pointer;opacity:0;transition:opacity .14s ease}
tr:hover .act{opacity:1}
.act:hover{background:var(--glass-hi);border-color:var(--border)}
.act svg{width:14px;height:14px;color:var(--muted)}
.act.on{opacity:1} .act.on svg{color:var(--due)}
.tick{width:20px;height:20px;border-radius:6px;border:1.6px solid var(--border-2);background:transparent;
  cursor:pointer;display:grid;place-items:center;transition:all .14s ease;flex:none}
.tick:hover{border-color:var(--accent)}
.tick.on{background:var(--accent);border-color:var(--accent)}
.tick svg{width:12px;height:12px;color:#fff;opacity:0} .tick.on svg{opacity:1}
td.tickcell{width:34px} tr.read{opacity:.52} tr.read:hover{opacity:.74}
.meta{color:var(--muted);font-size:12px;margin-top:4px}
.chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
.chip{font-size:11px;font-weight:600;background:var(--chip-bg);color:var(--chip-fg);border-radius:6px;padding:2px 8px}
.chip.src{background:var(--never-bg);color:var(--muted);border:1px solid var(--border)}
.chip.tagc{background:transparent;color:var(--accent);border:1px solid var(--accent);font-weight:700}
.chip.new{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.chip.tracked{background:var(--never-bg);color:var(--muted);border:1px solid var(--border-2);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.tagchips{margin-top:5px} .tagchips:empty{display:none}
.tagedit{margin-top:10px;display:flex;align-items:center;gap:9px;border-top:1px dashed var(--border-2);padding-top:9px}
.tagedit .tl{font-size:12px;color:var(--faint);font-weight:700}
.tag-input{flex:1;max-width:420px;background:var(--never-bg);border:1px solid var(--border);border-radius:8px;
  padding:6px 10px;color:var(--text);font-size:12.5px;outline:none;font-family:inherit}
.tag-input:focus{border-color:var(--accent)}
header select{padding:8px 10px}
td.venue{color:var(--text);max-width:210px}
td.date{color:var(--muted);white-space:nowrap}
.hint{color:var(--faint);font-size:11px;margin-top:6px}
.detail{display:none;margin-top:10px;padding:12px 14px;background:var(--never-bg);border:1px solid var(--border);border-radius:11px}
tr.open .detail{display:block}
.detail .abs{color:var(--muted);font-size:13px;line-height:1.6}
.detail .why{margin-top:9px;font-size:12.5px;color:var(--faint);border-top:1px dashed var(--border-2);padding-top:8px}
.detail .why b{color:var(--accent)}

/* ---- empty / skeleton ---- */
.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:70px 24px;color:var(--muted)}
.empty .ico{width:56px;height:56px;border-radius:16px;display:grid;place-items:center;background:var(--glass-2);border:1px solid var(--border);margin-bottom:14px}
.empty .ico svg{width:26px;height:26px;color:var(--accent)}
.empty .big{font-family:var(--head);font-size:18px;color:var(--text);margin-bottom:6px;font-weight:600}
.skel{padding:16px}
.skrow{height:56px;border-radius:12px;margin-bottom:10px;background:linear-gradient(90deg,var(--glass) 25%,var(--glass-2) 37%,var(--glass) 63%);background-size:400% 100%;animation:shim 1.4s infinite}
@keyframes shim{0%{background-position:100% 0}100%{background-position:-100% 0}}

/* ---- analytics ---- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:16px}
.kpi{padding:16px 18px}
.kpi .k-val{font-family:var(--head);font-size:28px;font-weight:700;line-height:1;
  background:linear-gradient(135deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}
.kpi .k-lab{font-size:12px;color:var(--muted);margin-top:8px;font-weight:600}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}
.chart{padding:16px 18px}
.chart h3{font-family:var(--head);font-size:14px;font-weight:600;margin:0 0 14px}
.bars{display:flex;flex-direction:column;gap:9px}
.barrow{display:grid;grid-template-columns:130px 1fr 42px;align-items:center;gap:10px;font-size:12.5px}
.barrow .bl{color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.barrow .bt{height:9px;background:var(--never-bg);border-radius:999px;overflow:hidden;border:1px solid var(--border)}
.barrow .bf{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--bar),var(--bar-2))}
.barrow .bv{text-align:right;color:var(--text);font-weight:700}
.chart-empty{color:var(--faint);font-size:13px;padding:8px 0}

/* ---- coverage ---- */
.covgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:16px;align-items:start}
.covhead{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--border)}
.covhead h3{font-family:var(--head);font-size:15px;font-weight:700;margin:0;flex:1}
.covhead .covsub{font-size:12px;color:var(--muted)}
.covstats{display:flex;gap:14px;padding:10px 18px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.covstat{font-size:12px;color:var(--muted)} .covstat b{color:var(--text);font-weight:700}
table.covtbl{width:100%;border-collapse:collapse;font-size:12.5px}
table.covtbl th{text-align:left;padding:8px 10px;font-size:10.5px;text-transform:uppercase;
  letter-spacing:.05em;color:var(--faint);font-weight:700;background:var(--card-2);border-bottom:1px solid var(--border)}
table.covtbl td{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:top}
table.covtbl tr:last-child td{border-bottom:none}
table.covtbl tr:hover{background:var(--glass-2)}
td.covtitle{max-width:1px;width:100%}
.covtitle .t{color:var(--text);font-weight:600;font-family:var(--head);font-size:13px;line-height:1.35;
  display:block;text-decoration:none;cursor:pointer}
.covtitle .t:hover{color:var(--accent);text-decoration:underline}
.covtitle .m{color:var(--muted);font-size:11px;margin-top:3px}
.usedbadge{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:999px;
  font-size:11px;font-weight:700;cursor:pointer;border:1px solid transparent;white-space:nowrap;user-select:none}
.usedbadge.yes{background:var(--ok-bg);color:var(--ok);border-color:var(--ok)}
.usedbadge.no{background:var(--never-bg);color:var(--faint);border-color:var(--border-2)}
.usedbadge.override{box-shadow:0 0 0 1.5px var(--due) inset}
.covempty{color:var(--faint);font-size:12.5px;padding:20px;text-align:center}

/* ---- toast ---- */
#toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(20px);
  background:var(--card-2);border:1px solid var(--border-2);
  color:var(--text);padding:10px 18px;border-radius:11px;font-size:13px;font-weight:600;
  box-shadow:0 8px 30px rgba(0,0,0,.3);opacity:0;pointer-events:none;transition:all .25s ease;z-index:50}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
  <div class="bg"></div><div class="blob b1"></div><div class="blob b2"></div><div class="blob b3"></div>

  <header>
    <div class="brand">
      <span class="logo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg></span>
      <h1>Paper Tracker</h1>
    </div>
    <div class="tabs" role="tablist">
      <button class="tab active" data-tab="papers" role="tab"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>Papers</button>
      <button class="tab" data-tab="analytics" role="tab"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>Analytics</button>
      <button class="tab" data-tab="coverage" role="tab"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>Coverage</button>
    </div>
    <span class="spacer"></span>
    <span id="pill" class="pill never"><span class="dot"></span><span id="pill-msg">Loading…</span></span>
    <select id="source" title="Which API to search on Refresh" aria-label="Search source">
      <option value="all">Both sources</option>
      <option value="openalex">OpenAlex</option>
      <option value="crossref">Crossref</option>
    </select>
    <button id="refresh" class="btn" aria-label="Refresh now (R)"><span class="spinner"></span><span id="refresh-label">Refresh</span></button>
    <button id="exit" class="iconbtn danger" aria-label="Exit application" title="Exit"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg></button>
  </header>

  <div id="progress"><div class="pwrap"><div class="ptrack"><div id="pbar" class="pbar"></div></div><span id="plabel" class="plabel"></span></div></div>
  <div id="errbar" class="hidden"></div>

  <!-- PAPERS -->
  <div id="view-papers" style="display:flex;flex-direction:column;flex:1;min-height:0">
    <div class="toolbar">
      <button id="collapse" class="iconbtn" aria-label="Collapse sidebar (Esc)" title="Collapse sidebar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg></button>
      <label for="week">Week</label>
      <select id="week" aria-label="Filter by week"></select>
      <div class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input id="search" type="text" placeholder="Search title, author, term…  ( / )" aria-label="Search papers"></div>
      <label for="sort">Sort</label>
      <select id="sort" aria-label="Sort papers"><option value="rank">Rank</option><option value="date">Newest</option><option value="venue">Venue</option></select>
      <label for="filter">Show</label>
      <select id="filter" aria-label="Filter papers"><option value="new">New</option><option value="tracked">Tracked</option><option value="all">All (new + tracked)</option><option value="unread">Unread</option><option value="starred">Starred</option><option value="hidden">Hidden</option></select>
      <span id="subcount" class="tnum"></span>
    </div>
    <main>
      <div class="side" id="side"><h2>Categories</h2><div id="cats"></div></div>
      <div class="content" id="content"><div class="skel"><div class="skrow"></div><div class="skrow"></div><div class="skrow"></div><div class="skrow"></div></div></div>
    </main>
  </div>

  <!-- ANALYTICS -->
  <div id="view-analytics" class="content hidden" style="flex:1"></div>

  <!-- COVERAGE -->
  <div id="view-coverage" class="content hidden" style="flex:1"></div>

  <div id="toast"></div>

<script>/*QWEBCHANNEL_JS*/</script>
<script>
"use strict";
let SNAP=null, curCat=null, curWeek="", curTab="papers", sortMode="rank", search="", filterMode="new";
const LS={get:(k,d)=>{try{return localStorage.getItem("rpt."+k)??d}catch(e){return d}},
          set:(k,v)=>{try{localStorage.setItem("rpt."+k,v)}catch(e){}}};
const ICON={
  check:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
  star:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.1 8.3 22 9.3 17 14.1 18.2 21 12 17.8 5.8 21 7 14.1 2 9.3 8.9 8.3 12 2"/></svg>',
  starFill:'<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.1 8.3 22 9.3 17 14.1 18.2 21 12 17.8 5.8 21 7 14.1 2 9.3 8.9 8.3 12 2"/></svg>',
  download:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
  copy:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  tag:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
  hide:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>',
  eye:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'};

function fmtDate(iso){ if(!iso) return ""; const m=/^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? (m[3]+"/"+m[2]+"/"+m[1]) : iso; }
function authorsShort(a){ if(!a) return ""; const p=a.split(";").map(x=>x.trim()).filter(Boolean);
  return p.length<=3?p.join(", "):p.slice(0,3).join(", ")+" et al."; }
function el(t,c,x){const e=document.createElement(t); if(c)e.className=c; if(x!=null)e.textContent=x; return e;}
function terms(p){return (p.matched_terms||"").split(";").map(t=>t.trim()).filter(Boolean);}

/* "new" = first surfaced in the most recent refresh; a non-hidden paper that was
   pulled in an earlier refresh is "tracked". Off-topic papers we're not using stay
   hidden via curation and only appear under the Hidden filter. */
function latestRun(){ return (SNAP.status && SNAP.status.last_refreshed) || ""; }
function isNew(p){ const lr=latestRun(); return !!lr && p.first_seen===lr; }

/* Does a paper pass the current Show filter (week + mode), ignoring the search box? */
function matchesFilter(p){
  if(curWeek && p.run_date!==curWeek) return false;
  if(filterMode==="hidden") return !!p.hidden;
  if(p.hidden) return false;              // "not using" — never in the normal feeds
  if(filterMode==="new")     return isNew(p);
  if(filterMode==="tracked") return !isNew(p);
  if(filterMode==="unread")  return !p.read;
  if(filterMode==="starred") return !!p.starred;
  return true;                            // "all" = every non-hidden paper
}
/* Category badge = papers to review in the current feed (drops as you tick read);
   under the Hidden filter it just counts the hidden ones. */
function countFor(cat){ const a=(SNAP.papers[cat]||[]).filter(matchesFilter);
  return filterMode==="hidden" ? a.length : a.filter(p=>!p.read).length; }
function papersFor(cat){ let a=(SNAP.papers[cat]||[]).filter(matchesFilter);
  if(search){ const q=search.toLowerCase();
    a=a.filter(p=>(p.title+" "+p.authors+" "+p.matched_terms+" "+(p.tags||"")).toLowerCase().includes(q)); }
  if(sortMode==="date") a.sort((x,y)=>(y.date||"").localeCompare(x.date||""));
  else if(sortMode==="venue") a.sort((x,y)=>(x.venue||"").localeCompare(y.venue||""));
  else a.sort((x,y)=>x.rank-y.rank);
  return a; }

/* ---------- header / status ---------- */
function renderStatus(){ const s=SNAP.status,p=document.getElementById("pill");
  p.className="pill "+(s.state||"never"); document.getElementById("pill-msg").textContent=s.message||""; }
function renderWeeks(){ const sel=document.getElementById("week"); sel.innerHTML="";
  sel.appendChild(new Option("All weeks",""));
  (SNAP.weeks||[]).forEach(w=>sel.appendChild(new Option(fmtDate(w.run_date)+" ("+w.count+")",w.run_date)));
  sel.value=curWeek; }

/* ---------- sidebar ---------- */
function renderCats(){ const box=document.getElementById("cats"); box.innerHTML="";
  SNAP.categories.forEach((c,i)=>{
    const n=countFor(c.key);
    const row=el("div","cat"+(c.key===curCat?" active":"")+(c.important?" important":""));
    row.title=c.label; row.setAttribute("role","button"); row.tabIndex=0;
    row.appendChild(el("span","badge tnum", c.important?"★":(i+1)));
    row.appendChild(el("span","cat-label",c.label));
    row.appendChild(el("span","count tnum",n));
    const pick=()=>{curCat=c.key; LS.set("cat",c.key); renderCats(); renderPapers();};
    row.onclick=pick; row.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();pick();}};
    box.appendChild(row);
  }); }

/* ---------- papers table ---------- */
function citation(p){ const yr=(p.date||"").slice(0,4);
  const id=p.doi?("https://doi.org/"+p.doi):(p.arxiv_id?("arXiv:"+p.arxiv_id):p.url);
  return [authorsShort(p.authors), yr?("("+yr+")."):"", p.title+".", p.venue?(p.venue+"."):"", id].filter(Boolean).join(" "); }

function renderPapers(){
  const c=document.getElementById("content");
  const cat=SNAP.categories.find(x=>x.key===curCat), rows=papersFor(curCat);
  document.getElementById("subcount").textContent=(cat?cat.label:"")+" — "+rows.length+" paper"+(rows.length===1?"":"s");
  if(!rows.length){ c.innerHTML="";
    const never=!SNAP.status.ever_run, e=el("div","empty");
    const ic=el("div","ico"); ic.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>';
    e.appendChild(ic); e.appendChild(el("div","big",never?"No papers yet":(search?"No matches":(filterMode==="new"?"No new papers":"Nothing here"))));
    e.appendChild(el("div",null,
      never?"Click Refresh to fetch the latest papers.":
      (search?"Try a different search.":
      (filterMode==="new"?"Nothing new in the latest refresh — switch Show to “Tracked” to browse papers you’ve already pulled.":
      "Try another week or category."))));
    c.appendChild(e); return; }
  const card=el("div","card"), tbl=el("table");
  tbl.innerHTML="<thead><tr><th></th><th>#</th><th>Paper</th><th>Venue</th><th>Published</th></tr></thead>";
  const tb=el("tbody");
  rows.forEach((p,i)=>{
    const tr=el("tr"); if(p.read) tr.classList.add("read");

    const tick=el("button","tick"+(p.read?" on":"")); tick.title="Mark read / unread";
    tick.setAttribute("aria-label","Mark read"); tick.setAttribute("aria-pressed",p.read?"true":"false");
    tick.innerHTML=ICON.check;
    tick.onclick=ev=>{ev.stopPropagation(); p.read=!p.read; backend.setRead(p.uid,p.read);
      tr.classList.toggle("read",p.read); tick.classList.toggle("on",p.read);
      tick.setAttribute("aria-pressed",p.read?"true":"false");
      renderCats();  /* live-update the to-review badge as papers are checked */
      if(filterMode==="unread")renderPapers();};
    const tcell=el("td","tickcell"); tcell.appendChild(tick); tr.appendChild(tcell);

    tr.appendChild(el("td","rank tnum",(sortMode==="rank"?p.rank:i+1)));

    const td=el("td");
    const trow=el("div","title-row");
    const a=el("a","title-link",p.title); a.href="#";
    a.onclick=ev=>{ev.preventDefault();ev.stopPropagation(); if(p.url)backend.openUrl(p.url);};
    trow.appendChild(a);

    const acts=el("div","actions");
    const star=el("button","act"+(p.starred?" on":"")); star.title="Star"; star.setAttribute("aria-label","Star");
    star.innerHTML=p.starred?ICON.starFill:ICON.star;
    star.onclick=ev=>{ev.stopPropagation(); p.starred=!p.starred; backend.setStarred(p.uid,p.starred);
      star.classList.toggle("on",p.starred); star.innerHTML=p.starred?ICON.starFill:ICON.star;
      if(filterMode==="starred")renderPapers();};
    acts.appendChild(star);
    const dl=el("button","act"); dl.title="Download PDF"; dl.setAttribute("aria-label","Download PDF");
    dl.innerHTML=ICON.download;
    dl.onclick=ev=>{ev.stopPropagation(); backend.downloadPaper(p.uid); toast("Downloading “"+p.title.slice(0,38)+"”…");};
    acts.appendChild(dl);
    const cp=el("button","act"); cp.title="Copy citation"; cp.setAttribute("aria-label","Copy citation");
    cp.innerHTML=ICON.copy;
    cp.onclick=ev=>{ev.stopPropagation(); backend.copyToClipboard(citation(p)); toast("Citation copied");};
    acts.appendChild(cp);
    const tg=el("button","act"); tg.title="Tag"; tg.setAttribute("aria-label","Tag"); tg.innerHTML=ICON.tag;
    tg.onclick=ev=>{ev.stopPropagation(); tr.classList.add("open"); const q=tr.querySelector(".tag-input"); if(q)q.focus();};
    acts.appendChild(tg);
    const hd=el("button","act"); hd.title=p.hidden?"Unhide":"Hide from list"; hd.setAttribute("aria-label","Hide");
    hd.innerHTML=p.hidden?ICON.eye:ICON.hide;
    hd.onclick=ev=>{ev.stopPropagation(); p.hidden=!p.hidden; backend.setHidden(p.uid,p.hidden);
      toast(p.hidden?"Hidden":"Unhidden"); renderCats(); renderPapers();};
    acts.appendChild(hd);
    trow.appendChild(acts); td.appendChild(trow);
    td.appendChild(el("div","meta",authorsShort(p.authors)+(p.doi?("  ·  doi:"+p.doi):(p.arxiv_id?("  ·  arXiv:"+p.arxiv_id):""))));
    const chips=el("div","chips"), tl=terms(p);
    if(!p.hidden) chips.appendChild(el("span","chip "+(isNew(p)?"new":"tracked"), isNew(p)?"new":"tracked"));
    if(tl.length){ tl.slice(0,5).forEach(t=>chips.appendChild(el("span","chip",t)));
      if(tl.length>5)chips.appendChild(el("span","chip","+"+(tl.length-5))); }
    else chips.appendChild(el("span","chip src",p.source==="arxiv"?"arXiv preprint":"Top-journal pick"));
    td.appendChild(chips);
    const tagChips=el("div","chips tagchips");
    function renderTagChips(){ tagChips.innerHTML="";
      (p.tags||"").split(",").map(t=>t.trim()).filter(Boolean).forEach(t=>tagChips.appendChild(el("span","chip tagc",t))); }
    renderTagChips(); td.appendChild(tagChips);
    td.appendChild(el("div","hint","▸ click row for abstract, tags & why it matched"));
    const det=el("div","detail");
    if(p.abstract) det.appendChild(el("div","abs",p.abstract));
    const why=el("div","why"), bits=[];
    if(tl.length)bits.push("Matched: "+tl.join(", "));
    bits.push("match score "+p.match_score+(p.relevance?(" · OpenAlex relevance "+p.relevance):""));
    why.innerHTML="<b>Why it surfaced:</b> "+bits.join(" · "); det.appendChild(why);
    const tagEdit=el("div","tagedit"); tagEdit.appendChild(el("span","tl","Tags"));
    const tinp=el("input","tag-input"); tinp.type="text"; tinp.value=p.tags||"";
    tinp.placeholder="comma-separated (e.g. must-read, methodology)";
    tinp.onclick=ev=>ev.stopPropagation();
    tinp.onkeydown=ev=>{ if(ev.key==="Enter"){ev.preventDefault(); tinp.blur();} };
    tinp.onblur=()=>{ p.tags=tinp.value.trim(); backend.setTags(p.uid,p.tags); renderTagChips(); };
    tagEdit.appendChild(tinp); det.appendChild(tagEdit);
    td.appendChild(det); tr.appendChild(td);
    tr.appendChild(el("td","venue",p.venue));
    tr.appendChild(el("td","date tnum",fmtDate(p.date)));
    tr.onclick=()=>tr.classList.toggle("open");
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); card.appendChild(tbl); c.innerHTML=""; c.appendChild(card);
}

/* ---------- analytics ---------- */
function uniquePapers(){ const m={}; for(const k in SNAP.papers) for(const p of SNAP.papers[k]) m[p.uid]=p; return Object.values(m); }
function tally(arr){ const m={}; arr.forEach(v=>{if(v)m[v]=(m[v]||0)+1});
  return Object.entries(m).map(([label,count])=>({label,count})).sort((a,b)=>b.count-a.count); }
function barChart(title,data,note){
  const c=el("div","chart card"); c.appendChild(el("h3",null,title));
  if(!data.length){ c.appendChild(el("div","chart-empty",note||"No data yet.")); return c; }
  const max=Math.max(...data.map(d=>d.count))||1, box=el("div","bars");
  data.forEach(d=>{ const r=el("div","barrow");
    r.appendChild(el("div","bl",d.label)); const t=el("div","bt"),f=el("div","bf");
    f.style.width=Math.max(4,d.count/max*100)+"%"; t.appendChild(f); r.appendChild(t);
    r.appendChild(el("div","bv tnum",d.count)); box.appendChild(r); });
  c.appendChild(box); return c;
}
function kpi(v,l){ const c=el("div","kpi card"); c.appendChild(el("div","k-val tnum",v)); c.appendChild(el("div","k-lab",l)); return c; }

function renderAnalytics(){
  const v=document.getElementById("view-analytics"); v.innerHTML="";
  if(!SNAP.status.ever_run){ const e=el("div","empty");
    const ic=el("div","ico"); ic.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>';
    e.appendChild(ic); e.appendChild(el("div","big","No analytics yet")); e.appendChild(el("div",null,"Refresh to start collecting data."));
    v.appendChild(e); return; }
  const uniq=uniquePapers();
  const newest=uniq.filter(isNew).length;
  const kpis=el("div","kpis");
  kpis.appendChild(kpi(uniq.length,"Papers tracked"));
  kpis.appendChild(kpi(newest,"New (last refresh)"));
  kpis.appendChild(kpi(uniq.filter(p=>p.read).length,"Read"));
  kpis.appendChild(kpi(uniq.filter(p=>p.starred).length,"Starred"));
  kpis.appendChild(kpi(SNAP.categories.length,"Categories"));
  kpis.appendChild(kpi(fmtDate(SNAP.status.next_due||""),"Next refresh due"));
  v.appendChild(kpis);

  const grid=el("div","grid2");
  grid.appendChild(barChart("Papers per category",
    SNAP.categories.map(c=>({label:c.label,count:(SNAP.papers[c.key]||[]).length}))));
  grid.appendChild(barChart("Papers per week",
    (SNAP.weeks||[]).slice().reverse().map(w=>({label:fmtDate(w.run_date),count:w.count}))));
  grid.appendChild(barChart("Source",
    tally(uniq.map(p=>p.source==="arxiv"?"arXiv":"Journal (OpenAlex)"))));
  grid.appendChild(barChart("Top venues", tally(uniq.map(p=>p.venue)).slice(0,8)));
  const allTerms=[]; uniq.forEach(p=>terms(p).forEach(t=>allTerms.push(t)));
  grid.appendChild(barChart("Hot topics (matched terms)", tally(allTerms).slice(0,12), "Appears once keyword categories have matches."));
  v.appendChild(grid);
}

/* ---------- coverage (NBD vs Causal review-status board) ---------- */
const COV_LABEL={nbd:"Non-Contractual / BTYD (Gear 1)", causal:"Causal ML / Uplift (Gear 2)"};
function covCite(p){ const yr=(p.date||"").slice(0,4);
  return [authorsShort(p.authors), yr?("("+yr+")"):"", p.venue].filter(Boolean).join(" · "); }
function usedBadge(p){
  const state = p.used===true?"yes":p.used===false?"no":"no";
  const label = p.used===true?"Used ✓":p.used===false?"Not used":"Not used";
  const b=el("span","usedbadge "+state+(p.used_override!==null?" override":""));
  b.title = p.used_override!==null
    ? "Manually set — click to cycle (auto → yes → no → auto)"
    : "Auto-detected from the manuscript .bib — click to override";
  b.textContent=label;
  b.onclick=ev=>{ ev.stopPropagation();
    const cur = p.used_override===true?1:p.used_override===false?0:-1;
    const next = cur===-1?1:(cur===1?0:-1);
    backend.setUsedOverride(p.uid, next);
    p.used_override = next<0?null:!!next;
    p.used = p.used_override!==null ? p.used_override : p.used_auto;
    renderCoverage();
  };
  return b;
}
function covPanel(group, rows){
  const card=el("div","card");
  const head=el("div","covhead");
  head.appendChild(el("h3",null,COV_LABEL[group]||group));
  head.appendChild(el("span","covsub", rows.length+" tracked"));
  card.appendChild(head);
  const nRead=rows.filter(p=>p.read).length, nAnalyzed=rows.filter(p=>p.analyzed).length,
        nUsed=rows.filter(p=>p.used===true).length;
  const stats=el("div","covstats");
  stats.appendChild(el("span","covstat")).innerHTML="<b>"+nRead+"</b>/"+rows.length+" read";
  stats.appendChild(el("span","covstat")).innerHTML="<b>"+nAnalyzed+"</b>/"+rows.length+" analyzed";
  stats.appendChild(el("span","covstat")).innerHTML="<b>"+nUsed+"</b>/"+rows.length+" cited in manuscript";
  card.appendChild(stats);
  if(!rows.length){ card.appendChild(el("div","covempty","No tracked (non-hidden) papers in this group yet.")); return card; }
  const sorted=rows.slice().sort((a,b)=>{
    if(a.read!==b.read) return a.read?1:-1;
    if(a.analyzed!==b.analyzed) return a.analyzed?1:-1;
    return (b.date||"").localeCompare(a.date||"");
  });
  const tbl=el("table","covtbl");
  tbl.innerHTML="<thead><tr><th></th><th></th><th>Used</th><th>Paper</th></tr></thead>";
  const tb=el("tbody");
  sorted.forEach(p=>{
    const tr=el("tr");
    const rt=el("td"); const rtick=el("button","tick"+(p.read?" on":"")); rtick.title="Read";
    rtick.innerHTML=ICON.check;
    rtick.onclick=ev=>{ev.stopPropagation(); p.read=!p.read; backend.setRead(p.uid,p.read); renderCoverage();};
    rt.appendChild(rtick); tr.appendChild(rt);
    const at=el("td"); const atick=el("button","tick"+(p.analyzed?" on":"")); atick.title="Analyzed (deep-dived, not just skimmed)";
    atick.innerHTML=ICON.check;
    atick.onclick=ev=>{ev.stopPropagation(); p.analyzed=!p.analyzed; backend.setAnalyzed(p.uid,p.analyzed); renderCoverage();};
    at.appendChild(atick); tr.appendChild(at);
    const ut=el("td"); ut.appendChild(usedBadge(p)); tr.appendChild(ut);
    const td=el("td","covtitle");
    const a=el("a","t",p.title); a.href="#";
    a.onclick=ev=>{ev.preventDefault();ev.stopPropagation(); if(p.url)backend.openUrl(p.url);};
    td.appendChild(a); td.appendChild(el("div","m",covCite(p)));
    tr.appendChild(td);
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); card.appendChild(tbl);
  return card;
}
function renderCoverage(){
  const v=document.getElementById("view-coverage"); v.innerHTML="";
  if(!SNAP || !SNAP.status.ever_run){ const e=el("div","empty");
    const ic=el("div","ico"); ic.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M9 11l3 3L22 4"/></svg>';
    e.appendChild(ic); e.appendChild(el("div","big","No coverage yet")); e.appendChild(el("div",null,"Refresh to start tracking papers."));
    v.appendChild(e); return; }
  const cov = SNAP.coverage||{nbd:[],causal:[]};
  const grid=el("div","covgrid");
  grid.appendChild(covPanel("nbd", cov.nbd||[]));
  grid.appendChild(covPanel("causal", cov.causal||[]));
  v.appendChild(grid);
}

/* ---------- tabs / sidebar ---------- */
function switchTab(t){ curTab=t; LS.set("tab",t);
  document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("active",b.dataset.tab===t));
  document.getElementById("view-papers").style.display = t==="papers"?"flex":"none";
  document.getElementById("view-analytics").classList.toggle("hidden",t!=="analytics");
  document.getElementById("view-coverage").classList.toggle("hidden",t!=="coverage");
  if(t==="analytics" && SNAP) renderAnalytics();   // SNAP may be null during restore()
  if(t==="coverage" && SNAP) renderCoverage();
}
function setCollapsed(v){ document.getElementById("side").classList.toggle("collapsed",v); LS.set("sidebar",v?"1":"0"); }

/* ---------- toast ---------- */
let toastT; function toast(msg){ const t=document.getElementById("toast"); t.textContent=msg;
  t.classList.add("show"); clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove("show"),1800); }

/* ---------- snapshot ---------- */
function renderAll(){ renderStatus(); renderWeeks(); renderCats(); renderPapers();
  if(curTab==="analytics")renderAnalytics(); if(curTab==="coverage")renderCoverage(); }
function setSnapshot(s){ SNAP=s;
  const err=document.getElementById("errbar");
  if(s.error){err.textContent="Last refresh error: "+s.error;err.classList.remove("hidden");}else err.classList.add("hidden");
  const keys=(s.categories||[]).map(c=>c.key);
  if(!curCat||!keys.includes(curCat)) curCat=keys[0]||null;
  if(curWeek && !(s.weeks||[]).some(w=>w.run_date===curWeek)) curWeek="";
  renderAll();
}
function setBusy(b){ const btn=document.getElementById("refresh");
  btn.classList.toggle("busy",b); btn.disabled=b;
  document.getElementById("refresh-label").textContent=b?"Refreshing…":"Refresh";
  const pr=document.getElementById("progress");
  if(b){pr.classList.add("show"); setProgress(0,1,"Starting…");} else setTimeout(()=>pr.classList.remove("show"),450);
}
function setProgress(d,t,l){ const pct=t?Math.round(d/t*100):0;
  document.getElementById("pbar").style.width=pct+"%";
  document.getElementById("plabel").textContent=(l||"")+"  ("+d+"/"+t+")"; }

/* ---------- init ---------- */
function restore(){ curTab=LS.get("tab","papers"); curCat=LS.get("cat",null); curWeek=LS.get("week","");
  sortMode=LS.get("sort","rank"); document.getElementById("sort").value=sortMode;
  filterMode=LS.get("filter","new"); document.getElementById("filter").value=filterMode;
  document.getElementById("source").value=LS.get("source","all");
  if(LS.get("sidebar","0")==="1") setCollapsed(true);
  switchTab(curTab);
}
function curSource(){ return document.getElementById("source").value; }
window.onload=function(){
  restore();
  document.getElementById("refresh").onclick=()=>backend.refresh(curSource());
  document.getElementById("source").onchange=e=>LS.set("source",e.target.value);
  document.getElementById("exit").onclick=()=>backend.quit();
  document.getElementById("collapse").onclick=()=>setCollapsed(!document.getElementById("side").classList.contains("collapsed"));
  document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));
  document.getElementById("week").onchange=e=>{curWeek=e.target.value; LS.set("week",curWeek); renderCats(); renderPapers();};
  document.getElementById("sort").onchange=e=>{sortMode=e.target.value; LS.set("sort",sortMode); renderPapers();};
  document.getElementById("filter").onchange=e=>{filterMode=e.target.value; LS.set("filter",filterMode); renderPapers();};
  document.getElementById("search").oninput=e=>{search=e.target.value; renderPapers();};
  document.addEventListener("keydown",e=>{
    const typing=/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if(e.key==="/"&&!typing){e.preventDefault(); document.getElementById("search").focus(); return;}
    if(e.key==="Escape"){ const s=document.getElementById("search");
      if(document.activeElement===s&&s.value){s.value="";search="";renderCats();renderPapers();} else setCollapsed(!document.getElementById("side").classList.contains("collapsed")); return;}
    if(typing) return;
    if(e.key==="r"||e.key==="R"){ if(!document.getElementById("refresh").disabled)backend.refresh(curSource()); }
    else if(e.key>="1"&&e.key<="9"&&SNAP){ const i=+e.key-1; if(SNAP.categories[i]){curTab==="papers"||switchTab("papers"); curCat=SNAP.categories[i].key; LS.set("cat",curCat); renderCats(); renderPapers();} }
  });
  new QWebChannel(qt.webChannelTransport,function(ch){
    window.backend=ch.objects.backend;
    backend.refreshStarted.connect(()=>setBusy(true));
    backend.progress.connect((d,t,l)=>setProgress(d,t,l));
    backend.refreshFinished.connect(j=>{setProgress(1,1,"Done"); setBusy(false); setSnapshot(JSON.parse(j));});
    backend.downloaded.connect(j=>{ const r=JSON.parse(j);
      toast(r.ok ? ("Saved via "+r.source+" ✓") : ("Download failed"+(r.error?": "+r.error:"")));});
    backend.snapshot(j=>setSnapshot(JSON.parse(j)));
  });
};
</script>
</body>
</html>
"""


def render_page(qwebchannel_js: str) -> str:
    return _HTML.replace("/*QWEBCHANNEL_JS*/", qwebchannel_js)
