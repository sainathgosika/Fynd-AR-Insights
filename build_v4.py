#!/usr/bin/env python3
"""Build Fynd Receivables Insights v4 dashboard."""
import json, os

with open('/sessions/serene-keen-mendel/data3.json') as f:
    DATA = f.read()

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Fynd - Receivables Insights</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<!--
  Heavy export-only libraries (XLSX, ExcelJS, jsPDF, jspdf-autotable, Papaparse)
  are NOT top-loaded any more — they add ~1.5 MB of blocking parse cost to the
  initial page paint even though most users never trigger an export. They are
  now fetched on-demand by the ensureXLSX() / ensureExcelJS() / ensureJsPDF() /
  ensurePapa() lazy loaders defined further down. See "Lazy-loaded libraries"
  section below. Do NOT re-add <script src=...xlsx.full.min.js...> here.
-->
<script>
  /* Lazy-loaded libraries — cached-promise helpers. Each ensureXxx() injects
     the CDN <script> tag on first call and returns a Promise that resolves
     with the global once loaded. Repeat calls short-circuit. */
  window.__libLoaders = window.__libLoaders || {};
  function _lazyLoadScript(id, src){
    if (window.__libLoaders[id]) return window.__libLoaders[id];
    window.__libLoaders[id] = new Promise(function(resolve, reject){
      var s = document.createElement('script');
      s.src = src; s.async = true;
      s.onload  = function(){ resolve(true); };
      s.onerror = function(){ reject(new Error('Failed to load ' + src)); };
      document.head.appendChild(s);
    });
    return window.__libLoaders[id];
  }
  window.ensureXLSX = function(){
    if (window.XLSX && window.XLSX.utils) return Promise.resolve(window.XLSX);
    return _lazyLoadScript('xlsx',
      'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js'
    ).then(function(){ return window.XLSX; });
  };
  window.ensureExcelJS = function(){
    if (window.ExcelJS) return Promise.resolve(window.ExcelJS);
    return _lazyLoadScript('exceljs',
      'https://cdn.jsdelivr.net/npm/exceljs@4.4.0/dist/exceljs.min.js'
    ).then(function(){ return window.ExcelJS; });
  };
  window.ensureJsPDF = function(){
    if (window.jspdf && window.jspdf.jsPDF) return Promise.resolve(window.jspdf);
    return _lazyLoadScript('jspdf',
      'https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js'
    ).then(function(){
      return _lazyLoadScript('jspdf-autotable',
        'https://cdn.jsdelivr.net/npm/jspdf-autotable@3.8.2/dist/jspdf.plugin.autotable.min.js'
      );
    }).then(function(){ return window.jspdf; });
  };
  window.ensurePapa = function(){
    if (window.Papa) return Promise.resolve(window.Papa);
    return _lazyLoadScript('papaparse',
      'https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js'
    ).then(function(){ return window.Papa; });
  };
</script>
<style>
  /* === Fynd · calm, decent palette === */
  :root {
    --c-bg:#f5f2ed;          /* warm cream */
    --c-card:#ffffff;
    --c-ink:#1f2a2e;          /* deep slate */
    --c-muted:#6b6660;        /* warm gray */
    --c-accent:#2c4a52;       /* deep petrol */
    --c-accent-2:#5b7a82;     /* lighter petrol */
    --c-gold:#b8956a;         /* muted gold accent */
    --c-line:#e8e1d5;         /* warm border */
    --c-soft:#f0ebe3;         /* warm soft */
    --c-pos:#6b8e5a;          /* sage green */
    --c-neg:#b85450;          /* dusty red */
  }
  html,body{background:var(--c-bg);color:var(--c-ink);font-family:'Inter',ui-sans-serif,system-ui,sans-serif;}
  .card{background:var(--c-card);border:1px solid var(--c-line);border-radius:14px;box-shadow:0 1px 2px rgba(31,42,46,.04);}
  .chip{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:9999px;font-size:12px;font-weight:500;background:var(--c-soft);color:var(--c-accent);border:1px solid var(--c-line);cursor:pointer;transition:all .15s;}
  .chip:hover{background:#e8e1d5;}
  .chip.active{background:var(--c-accent);color:#fff;border-color:var(--c-accent);box-shadow:0 1px 3px rgba(44,74,82,.25);}
  .wl-status-active{background:#1d4ed8 !important;color:#fff !important;border-color:#1d4ed8 !important;box-shadow:0 1px 3px rgba(29,78,216,.25);}
  .kpi-card{background:#fff;border:1px solid var(--c-line);border-radius:12px;padding:12px 14px;}
  .kpi-num{font-size:20px;font-weight:700;color:var(--c-ink);letter-spacing:-.02em;line-height:1.1;}
  .kpi-lab{font-size:10.5px;color:var(--c-muted);text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:2px;}
  .tab-item{padding:8px 16px;border-radius:8px;color:var(--c-muted);cursor:pointer;font-size:13px;font-weight:500;position:relative;white-space:nowrap;transition:all .15s;}
  .tab-item:hover{background:var(--c-soft);color:var(--c-accent);}
  .tab-item.active{background:var(--c-accent);color:#fff;box-shadow:0 1px 3px rgba(44,74,82,.25);}
  /* ===== Horizontal tab strip (no sidebar) ===== */
  .tab-strip{display:flex;align-items:center;gap:4px;padding:6px 0;border-top:1px solid var(--c-line);overflow-x:auto;white-space:nowrap;}
  .tab-strip::-webkit-scrollbar{height:6px;}
  .tab-strip::-webkit-scrollbar-thumb{background:rgba(0,0,0,0.15);border-radius:3px;}
  .tab-strip .tab-item{display:inline-flex;align-items:center;gap:6px;}
  /* ===== Fixed left sidebar — compact icon-stack, polished ===== */
  .sidebar{
    position:fixed; top:0; left:0; width:92px; height:100vh;
    background:linear-gradient(180deg,#ffffff 0%,#fbfaf6 100%);
    border-right:1px solid var(--c-line);
    display:flex; flex-direction:column; padding:8px 4px 10px;
    z-index:60; overflow-y:auto; overflow-x:hidden;
    box-shadow:2px 0 18px rgba(31,42,46,.04);
  }
  .sidebar::-webkit-scrollbar{width:4px;}
  .sidebar::-webkit-scrollbar-thumb{background:rgba(0,0,0,0.10);border-radius:2px;}
  .sidebar::-webkit-scrollbar-thumb:hover{background:rgba(0,0,0,0.20);}
  .sidebar .sb-brand{
    display:flex; align-items:center; justify-content:center;
    padding:4px 0 8px; margin-bottom:4px;
    border-bottom:1px solid var(--c-line);
    cursor:pointer; transition:background .15s;
  }
  .sidebar .sb-brand:hover{background:rgba(44,74,82,.04);}
  .sidebar .sb-brand img{height:22px;width:auto;display:block;}
  .sidebar .sb-brand-fallback{
    font-weight:700;font-size:14px;color:var(--c-accent);letter-spacing:-.02em;
    width:26px;height:26px;border-radius:7px;background:var(--c-soft);
    display:inline-flex;align-items:center;justify-content:center;
  }
  .sidebar .sb-brand-text{display:none;}
  /* Icon-stack tab item: icon on top, label centered below */
  .sidebar .tab-item{
    display:flex !important; flex-direction:column; align-items:center;
    justify-content:center; gap:3px;
    padding:6px 3px; margin-bottom:2px;
    border-radius:8px; cursor:pointer; color:#475569;
    text-align:center; transition:all .18s ease;
    font-size:9px; font-weight:500; letter-spacing:.005em; line-height:1.15;
    white-space:normal; position:relative;
  }
  .sidebar .tab-item:hover{background:var(--c-soft);color:var(--c-accent);}
  .sidebar .tab-item.active{
    background:var(--c-accent);color:#fff;
    box-shadow:0 2px 6px rgba(44,74,82,.22), 0 1px 2px rgba(44,74,82,.12);
  }
  .sidebar .tab-item .sb-icon{
    font-size:15px;line-height:1;display:inline-flex;
    align-items:center;justify-content:center;
    width:18px;height:18px;flex-shrink:0;
  }
  .sidebar .tab-item .sb-label{
    display:inline-block;font-size:9px;font-weight:500;
    text-align:center;line-height:1.2;letter-spacing:.005em;
  }
  /* ===== Section labels (Insights / Collections / Reports / Admin) ===== */
  .sidebar .sb-section{
    font-size:7.5px;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;
    text-align:center;padding:7px 1px 3px;margin-top:3px;
    font-weight:700;
    border-top:1px solid var(--c-line);
    white-space:nowrap;overflow:hidden;text-overflow:clip;
  }
  .sidebar .sb-section.first{border-top:none;margin-top:0;padding-top:3px;}
  /* ===== AR Activity collapsible parent (also vertical stack) ===== */
  .sidebar .sb-group-toggle{
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    gap:3px;padding:6px 3px;margin-bottom:2px;
    border-radius:8px;cursor:pointer;color:#475569;
    text-align:center;transition:all .18s ease;
    font-size:9px;font-weight:500;letter-spacing:.005em;line-height:1.15;
    white-space:normal;position:relative;
  }
  .sidebar .sb-group-toggle:hover{background:var(--c-soft);color:var(--c-accent);}
  .sidebar .sb-group-toggle .sb-icon{
    font-size:15px;line-height:1;display:inline-flex;
    align-items:center;justify-content:center;
    width:18px;height:18px;flex-shrink:0;
  }
  .sidebar .sb-group-toggle .sb-label{
    font-size:9px;font-weight:500;text-align:center;line-height:1.2;
  }
  .sidebar .sb-group-toggle .sb-caret{
    position:absolute;right:4px;top:50%;transform:translateY(-50%);
    font-size:14px;line-height:1;color:var(--c-accent);font-weight:700;
    transition:transform .25s ease, color .18s ease;display:inline-block;
    opacity:.85;text-shadow:0 0 1px rgba(44,74,82,.18);
  }
  .sidebar .sb-group-toggle:hover .sb-caret{opacity:1;color:var(--c-accent);}
  .sidebar .sb-group-toggle.open .sb-caret{transform:translateY(-50%) rotate(90deg);color:var(--c-accent);opacity:1;}
  .sidebar .sb-group-toggle.has-active-child{background:var(--c-soft);color:var(--c-accent);}
  .sidebar .sb-group-toggle.has-active-child .sb-caret{color:var(--c-accent);opacity:1;}
  .sidebar .sb-group-children{
    display:flex;flex-direction:column;
    padding-left:3px;margin-top:1px;
  }
  .sidebar .sb-group-children.hidden{display:none;}
  /* Sub-items use the same vertical layout, just slightly smaller + indented */
  .sidebar .tab-item.sb-sub{
    padding:5px 2px;margin-left:4px;margin-bottom:1px;
    border-left:2px solid var(--c-line);
    border-radius:0 7px 7px 0;
    font-size:8.5px;
  }
  .sidebar .tab-item.sb-sub:hover{border-left-color:var(--c-accent);background:var(--c-soft);}
  .sidebar .tab-item.sb-sub.active{
    border-left-color:var(--c-accent);
    background:var(--c-accent);color:#fff;
    box-shadow:0 2px 5px rgba(44,74,82,.20);
  }
  .sidebar .tab-item.sb-sub .sb-icon{font-size:13px;width:16px;height:16px;}
  .sidebar .tab-item.sb-sub .sb-label{font-size:8.5px;}
  /* Shift main content right to make room for the sidebar */
  .page-shell{padding-left:92px;}
  /* Clickable Fynd brand button (top-left) — navigates to Overview */
  .brand-btn{
    display:inline-flex;align-items:center;gap:8px;
    padding:4px 10px 4px 4px;border-radius:10px;border:1px solid transparent;
    background:transparent;cursor:pointer;transition:all .15s;
  }
  .brand-btn:hover{background:var(--c-soft);border-color:var(--c-line);}
  .brand-btn img{height:28px;width:auto;display:block;}
  .brand-btn .b-name{font-weight:700;font-size:15px;letter-spacing:-.01em;color:var(--c-accent);line-height:1.05;}
  .brand-btn .b-sub{font-size:9.5px;font-weight:600;letter-spacing:.05em;color:var(--c-muted);text-transform:uppercase;margin-top:2px;}
  /* Topbar search — kept as is */
  .topbar-search{position:relative;flex:1 1 320px;max-width:480px;}
  .topbar-search input{
    width:100%;border:1px solid var(--c-line);border-radius:10px;
    background:#fff;padding:8px 12px 8px 34px;font-size:13px;color:var(--c-ink);
  }
  .topbar-search::before{
    content:"🔍";position:absolute;left:11px;top:50%;transform:translateY(-50%);
    font-size:12px;opacity:.55;pointer-events:none;
  }

  /* Override Tailwind palette to the Fynd-decent scheme */
  .text-emerald-600, .text-green-600 { color:#6b8e5a !important; }
  .text-rose-600, .text-red-600 { color:#b85450 !important; }
  .text-indigo-600, .text-violet-600, .text-blue-600, .text-cyan-600 { color:#2c4a52 !important; }
  .text-amber-600, .text-fuchsia-600 { color:#b8956a !important; }
  .num-red, .num-red.font-semibold { color:#b85450 !important; }
  .num-green { color:#6b8e5a !important; }
  .num-amber { color:#b8956a !important; }

  /* Top-right icon-only buttons with custom hover tooltips */
  .icon-btn{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:8px;background:var(--c-soft);color:var(--c-accent);border:1px solid var(--c-line);cursor:pointer;font-size:15px;transition:all .15s;position:relative;}
  .icon-btn:hover{background:#e8e1d5;color:var(--c-ink);}
  /* Hard Refresh spin animation while reload is in flight */
  @keyframes hrSpin{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}
  #btnHardRefresh{font-size:17px;font-weight:600;line-height:1;}
  #btnHardRefresh.hr-spin, #btnHardRefresh .hr-spin{animation:hrSpin .9s linear infinite;display:inline-block;}
  .icon-btn[data-tip]:hover::after{content:attr(data-tip);position:absolute;top:calc(100% + 6px);right:0;background:var(--c-ink);color:#fff;padding:5px 10px;font-size:11px;font-weight:400;border-radius:6px;white-space:nowrap;z-index:60;box-shadow:0 4px 12px rgba(31,42,46,.18);pointer-events:none;}
  .icon-btn[data-tip]:hover::before{content:'';position:absolute;top:calc(100% + 1px);right:12px;border:5px solid transparent;border-bottom-color:var(--c-ink);z-index:60;pointer-events:none;}
  .tab-item[data-tip]:hover::after{content:attr(data-tip);position:absolute;left:50%;top:calc(100% + 8px);transform:translateX(-50%);background:#0f172a;color:#fff;padding:6px 10px;font-size:11px;font-weight:400;border-radius:6px;white-space:nowrap;z-index:50;box-shadow:0 4px 12px rgba(0,0,0,.2);}
  /* Admin-only elements: hidden by default (including ACM tab + section). applyAccessControl()
     removes .hidden-until-admin only after confirming reallyAdmin === true. The !important
     guarantees the element stays hidden even if downstream code accidentally sets style.display. */
  .hidden-until-admin{display:none !important;}
  table{font-size:12.5px;}
  thead th{background:var(--c-soft);font-weight:600;color:var(--c-accent);font-size:11px;text-transform:uppercase;letter-spacing:.04em;padding:10px 12px;text-align:left;border-bottom:1px solid var(--c-line);}
  tbody td{padding:10px 12px;border-bottom:1px solid #f3eee5;color:var(--c-ink);}
  tbody tr.expand-row td{background:#faf7f1;border-bottom:1px solid var(--c-line);}
  tbody tr.parent-row{cursor:pointer;}
  tbody tr.parent-row:hover{background:#faf7f1;}
  tbody tr.child-row td{background:#faf7f1;color:var(--c-muted);font-size:12px;padding-left:28px;}
  .badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:500;}
  .badge-blue{background:#e1eaed;color:#2c4a52;}
  .badge-green{background:#e4ece0;color:#4d6b3f;}
  .badge-red{background:#f3e0df;color:#8b3a37;}
  .badge-amber{background:#f1e6d4;color:#8b6f43;}
  .badge-violet{background:#e7e2eb;color:#5b4d6b;}
  .badge-slate{background:var(--c-soft);color:var(--c-muted);}
  .seg-btn{padding:5px 11px;font-size:11.5px;border-radius:8px;font-weight:500;color:var(--c-muted);background:transparent;cursor:pointer;}
  .seg-btn.active{background:#fff;color:var(--c-accent);box-shadow:0 1px 3px rgba(31,42,46,.08);}
  .ms-wrap{position:relative;}
  .ms-trig{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 12px;border:1px solid var(--c-line);border-radius:10px;background:#fff;cursor:pointer;font-size:12.5px;color:var(--c-ink);min-height:40px;}
  .ms-trig:hover{border-color:var(--c-accent-2);}
  .ms-pop{position:absolute;top:calc(100% + 4px);left:0;right:0;z-index:30;background:#fff;border:1px solid var(--c-line);border-radius:10px;box-shadow:0 8px 24px rgba(31,42,46,.12);max-height:300px;overflow:hidden;display:none;}
  .ms-pop.open{display:flex;flex-direction:column;}
  .ms-search{padding:8px;border-bottom:1px solid var(--c-line);}
  .ms-search input{width:100%;padding:6px 10px;border:1px solid var(--c-line);border-radius:6px;font-size:12px;outline:none;}
  .ms-search input:focus{border-color:var(--c-accent);}
  .ms-actions{display:flex;justify-content:space-between;padding:6px 10px;border-bottom:1px solid var(--c-line);background:var(--c-soft);}
  .ms-actions button{font-size:11px;color:var(--c-accent);font-weight:500;cursor:pointer;}
  .ms-list{overflow:auto;max-height:200px;}
  .ms-opt{display:flex;align-items:center;gap:8px;padding:6px 12px;cursor:pointer;font-size:12.5px;}
  .ms-opt:hover{background:var(--c-soft);}
  .ms-opt input{accent-color:var(--c-accent);}
  .ms-tag{display:inline-flex;align-items:center;gap:4px;background:var(--c-soft);color:var(--c-accent);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:500;}
  .ms-tag .x{cursor:pointer;color:var(--c-muted);font-weight:600;}
  .scroll-x{overflow-x:auto;}
  .sticky-header{position:sticky;top:0;z-index:40;background:rgba(245,242,237,0.95);backdrop-filter:blur(8px);border-bottom:1px solid var(--c-line);}
  .pill{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:9999px;font-size:11px;font-weight:600;}
  .arrow{display:inline-block;width:14px;height:14px;color:#64748b;transition:transform .15s;}
  .arrow.open{transform:rotate(90deg);color:#4f46e5;}
  .num-red{color:#b85450;font-weight:600;}
  .num-green{color:#6b8e5a;font-weight:600;}
  .num-zero{color:var(--c-muted);}
  .num-amber{color:#b8956a;font-weight:600;}
  details>summary{list-style:none;cursor:pointer;}
  details>summary::-webkit-details-marker{display:none;}
  ::-webkit-scrollbar{width:8px;height:8px;}
  ::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:8px;}
  ::-webkit-scrollbar-track{background:transparent;}
  /* Per-report date chips */
  .rp-chip{display:inline-flex;align-items:center;padding:3px 9px;border-radius:9999px;font-size:10.5px;font-weight:500;background:var(--c-soft);color:var(--c-muted);border:1px solid var(--c-line);cursor:pointer;transition:all .12s;}
  .rp-chip:hover{background:#e8e1d5;color:var(--c-accent);}
  .rp-chip.active{background:var(--c-accent);color:#fff;border-color:var(--c-accent);}
  .rp-chip.clear{background:#f3e0df;color:#8b3a37;border-color:#e8c8c6;}
  .rp-chip.clear:hover{background:#e8c8c6;}
  .rp-chips{display:flex;flex-wrap:wrap;gap:4px;}
  .rp-dates{display:none;align-items:center;gap:6px;margin-top:6px;}
  .rp-dates.open{display:flex;}
  .rp-dates input{border:1px solid var(--c-line);border-radius:6px;padding:3px 6px;font-size:11px;}
  .rp-label{font-size:10px;color:var(--c-muted);text-transform:uppercase;letter-spacing:.04em;font-weight:500;margin-bottom:4px;}
  /* Report tab strip (compact, sits inside Downloads & Reports card) */
  .report-tabs{display:flex;flex-wrap:wrap;gap:2px;border-bottom:1px solid var(--c-line);padding:0 0 6px 0;margin-bottom:10px;}
  .report-tab{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:8px 8px 0 0;font-size:11.5px;font-weight:500;color:var(--c-muted);background:transparent;border:none;cursor:pointer;transition:all .12s;white-space:nowrap;}
  .report-tab:hover{background:var(--c-soft);color:var(--c-accent);}
  .report-tab.active{background:var(--c-accent);color:#fff;}
  .report-tab.active .badge{background:rgba(255,255,255,.18);color:#fff;}
  .report-panel{display:none;padding:6px 0 0 0;}
  .report-panel.active{display:block;}
  .report-panel .rp-desc{font-size:11.5px;color:var(--c-muted);margin-bottom:8px;}
  /* Vertical report-row list (one row per report) */
  .report-list{display:flex;flex-direction:column;gap:6px;}
  .report-row{display:flex;align-items:center;gap:12px;padding:10px 14px;border:1px solid var(--c-line);border-radius:10px;background:#fff;cursor:pointer;transition:all .12s;}
  .report-row:hover{background:var(--c-soft);border-color:var(--c-accent);}
  .report-row.active{background:var(--c-accent);color:#fff;border-color:var(--c-accent);box-shadow:0 1px 4px rgba(44,74,82,.18);}
  .report-row.active .rp-desc{color:rgba(255,255,255,.85);}
  .report-row.active .rp-no{background:rgba(255,255,255,.18);color:#fff;border-color:rgba(255,255,255,.35);}
  .report-row input[type=radio]{accent-color:var(--c-accent);width:16px;height:16px;margin:0;flex:0 0 16px;}
  .report-row .rp-no{flex:0 0 26px;height:26px;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--c-line);border-radius:50%;font-size:11px;font-weight:700;color:var(--c-accent);background:#fff;}
  .report-row .rp-info{flex:1;min-width:0;}
  .report-row .rp-title{font-size:13px;font-weight:600;color:inherit;}
  .report-row .rp-desc{font-size:11.5px;color:var(--c-muted);margin-top:1px;}
  .dso-info{display:inline-block;color:var(--c-muted);font-size:10px;margin-left:2px;cursor:help;font-weight:500;vertical-align:middle;}
  .dso-info:hover{color:var(--c-accent);}
  th[title]{cursor:help;}
  /* Activity Log tabs */
  .al-tab{padding:8px 16px;border:0;border-bottom:2px solid transparent;background:transparent;cursor:pointer;font-size:13px;color:#64748b;font-weight:600;transition:color .15s,border-color .15s,background .15s;}
  .al-tab:hover:not(.al-tab-active){color:#0f172a;background:#f8fafc;}
  .al-tab-active{color:#0f172a;border-bottom-color:var(--c-accent);}
  .al-tab-pane{animation:al-fade .2s ease-out;}
  @keyframes al-fade{from{opacity:0;transform:translateY(2px);}to{opacity:1;transform:none;}}
  /* Follow-up + Activity Log */
  .kpi{background:#fff;border:1px solid var(--c-line);border-radius:10px;padding:10px 12px;}
  .kpi-l{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--c-muted);font-weight:600;}
  .kpi-v{font-size:18px;font-weight:700;color:var(--c-accent);margin-top:2px;}
  .fu-modal{position:fixed;inset:0;background:rgba(15,23,42,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;padding:24px;}
  .fu-modal-shell{background:#fff;border-radius:14px;max-width:920px;width:100%;max-height:92vh;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,0.25);}
  .fu-modal-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--c-line);}
  .fu-modal-body{padding:16px 18px;overflow:auto;flex:1;background:#f8fafc;}
  .fu-modal-foot{display:flex;align-items:center;justify-content:space-between;padding:12px 18px;border-top:1px solid var(--c-line);gap:12px;flex-wrap:wrap;}
  .fu-row-disabled{opacity:.5;}
  .fu-status-ready{color:#15803d;font-weight:600;}
  .fu-status-blocked{color:#b91c1c;font-weight:600;}
  .fu-status-cooldown{color:#92400e;font-weight:600;}

  /* ===== Customer Statement of Account (printable ledger) ===== */
  .soa-ledger{background:#fff;border:1px solid var(--c-line);border-radius:10px;padding:24px 28px;color:#0f172a;}
  .soa-letterhead{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid var(--c-accent);padding-bottom:14px;margin-bottom:14px;}
  .soa-lh-left .soa-lh-brand{font-size:22px;font-weight:700;color:var(--c-accent);letter-spacing:-.01em;line-height:1;}
  .soa-lh-left .soa-lh-co{font-size:12.5px;font-weight:600;color:#0f172a;margin-top:4px;}
  .soa-lh-left .soa-lh-addr{font-size:10.5px;color:#64748b;margin-top:2px;}
  .soa-lh-right{text-align:right;}
  .soa-lh-right .soa-lh-title{font-size:13px;font-weight:700;letter-spacing:.12em;color:var(--c-accent);text-transform:uppercase;}
  .soa-lh-right .soa-lh-meta{font-size:11px;color:#64748b;margin-top:3px;}
  .soa-cust-block{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;background:#f8fafc;border:1px solid var(--c-line);border-radius:8px;padding:12px 14px;margin-bottom:14px;flex-wrap:wrap;}
  .soa-cust-block .soa-blk-lbl{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;font-weight:600;}
  .soa-cust-block .soa-blk-val{font-size:15px;font-weight:700;color:#0f172a;margin-top:2px;}
  .soa-cust-block .soa-blk-sub{font-size:11.5px;color:#475569;margin-top:2px;}
  .soa-totals{display:grid;grid-template-columns:repeat(4,auto);gap:14px;}
  .soa-totals > div{display:flex;flex-direction:column;align-items:flex-end;padding:6px 12px;border-left:1px solid var(--c-line);}
  .soa-totals > div:first-child{border-left:none;}
  .soa-totals .soa-tot-lbl{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
  .soa-totals .soa-tot-val{font-size:14px;font-weight:700;color:#0f172a;margin-top:2px;font-variant-numeric:tabular-nums;}
  .soa-totals .soa-clos .soa-tot-val{color:var(--c-accent);font-size:16px;}
  .soa-table{width:100%;border-collapse:collapse;font-size:11.5px;}
  .soa-table thead th{background:var(--c-accent);color:#fff;font-weight:600;text-transform:uppercase;letter-spacing:.04em;font-size:10px;padding:8px 10px;text-align:left;border-bottom:1px solid var(--c-accent);}
  .soa-table thead th.soa-num{text-align:right;}
  .soa-table tbody td{padding:7px 10px;border-bottom:1px solid #e2e8f0;color:#0f172a;}
  .soa-table tbody tr:nth-child(even) td{background:#fafbfc;}
  .soa-table tbody tr:hover td{background:#f1f5f9;}
  .soa-table .soa-num{text-align:right;font-variant-numeric:tabular-nums;}
  .soa-table .soa-dr{color:#b91c1c;font-weight:500;}
  .soa-table .soa-cr{color:#15803d;font-weight:500;}
  .soa-table .soa-bal{font-weight:600;}
  .soa-table .soa-opening-row td{background:#f1f5f9 !important;font-weight:600;color:#0f172a;}
  .soa-table .soa-type-pill{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.03em;}
  .soa-pill-inv{background:#fee2e2;color:#991b1b;}
  .soa-pill-cn{background:#dcfce7;color:#166534;}
  .soa-pill-pay{background:#dbeafe;color:#1e40af;}
  .soa-pill-tds{background:#fef3c7;color:#92400e;}
  .soa-pill-adj{background:#ede9fe;color:#5b21b6;}
  .soa-pill-pdd{background:#fce7f3;color:#9d174d;}
  .soa-pill-bnk{background:#e0e7ff;color:#3730a3;}
  .soa-pill-bd{background:#1f2937;color:#ffffff;}
  /* Clickable reference / unique-ref chips — make the affordance obvious so
     users learn the column is a filter, not just a label. */
  button.soa-ref-btn{transition:background-color .12s ease, color .12s ease, box-shadow .12s ease;}
  button.soa-ref-btn:hover{background:#c7d2fe !important;color:#1e1b4b !important;box-shadow:0 0 0 2px rgba(99,102,241,.18);}
  button.soa-ref-btn:focus-visible{outline:2px solid #4f46e5;outline-offset:1px;}
  .soa-table tfoot .soa-foot-row td{background:var(--c-accent);color:#fff;font-weight:700;padding:10px;font-size:12px;border-top:2px solid var(--c-accent);}
  .soa-signoff{margin-top:18px;display:flex;justify-content:space-between;align-items:flex-end;gap:20px;font-size:10.5px;color:#475569;}
  .soa-signoff .soa-sig{text-align:right;}
  .soa-signoff .soa-sig-line{width:200px;border-top:1px solid #94a3b8;margin-bottom:4px;height:30px;}
  .soa-signoff .soa-sig-lbl{font-weight:600;color:#0f172a;}
  /* Customer picker dropdown */
  #soaCustList .soa-cust-opt{padding:8px 12px;cursor:pointer;border-bottom:1px solid #f1f5f9;font-size:12.5px;}
  #soaCustList .soa-cust-opt:last-child{border-bottom:none;}
  #soaCustList .soa-cust-opt:hover{background:#eff6ff;}
  #soaCustList .soa-cust-opt .soa-co-name{font-weight:600;color:#0f172a;}
  #soaCustList .soa-cust-opt .soa-co-meta{font-size:11px;color:#64748b;margin-top:1px;}

  @media print {
    .sticky-header { position: static !important; }
    .sidebar { display: none !important; }
    .page-shell { padding-left: 0 !important; }
    #btnRefresh, #btnPrint, #btnSettings, #btnLiveSync, #btnClearAllFilter, #btnClearAllChip, #tabBar, #sideNav { display: none !important; }
    /* Keep scrollable tables clipped to what is on-screen so PDF doesn't explode */
    .card { break-inside: avoid; box-shadow: none !important; }
    body { background: #fff !important; }
    table { font-size: 10px; }
    .ms-pop, .ms-search, .ms-actions { display: none !important; }
    /* (Customer Statement PDF is now generated via an off-screen iframe — no print-mode body class needed.) */
  }

  /* ===== Application-level login overlay ===== */
  /* Hidden by default; JS reveals it after authWhoAmI reports needsLogin.
     Full-viewport fixed layer so it hides the whole dashboard until the
     user has a valid session. */
  #loginScreen{
    position:fixed;inset:0;z-index:9999;
    display:none;align-items:center;justify-content:center;
    background:linear-gradient(135deg,#1f2a2e 0%, #2c4a52 45%, #1f2a2e 100%);
    color:#f5f2ed;font-family:'Inter',ui-sans-serif,system-ui,sans-serif;
  }
  #loginScreen.visible{display:flex;}
  #loginScreen .lg-card{
    background:rgba(255,255,255,0.98);color:#1f2a2e;
    width:min(400px, 92vw);padding:28px 26px;border-radius:16px;
    box-shadow:0 24px 60px rgba(0,0,0,0.35),0 4px 12px rgba(0,0,0,0.15);
    border:1px solid rgba(255,255,255,0.6);
  }
  #loginScreen h1{font-size:18px;font-weight:700;color:#2c4a52;margin:0 0 4px;letter-spacing:-.02em;}
  #loginScreen .lg-sub{font-size:12px;color:#6b6660;margin-bottom:18px;}
  #loginScreen label{font-size:11px;font-weight:600;color:#2c4a52;text-transform:uppercase;letter-spacing:.05em;display:block;margin:12px 0 4px;}
  #loginScreen .lg-input-wrap{position:relative;}
  #loginScreen input[type="text"],
  #loginScreen input[type="password"]{
    width:100%;padding:10px 40px 10px 12px;font-size:14px;
    border:1px solid #e8e1d5;border-radius:8px;background:#fbfaf6;color:#1f2a2e;
    box-sizing:border-box;outline:none;transition:border .15s,box-shadow .15s;
  }
  #loginScreen input:focus{border-color:#2c4a52;box-shadow:0 0 0 3px rgba(44,74,82,0.14);}
  #loginScreen .lg-eye{
    position:absolute;top:50%;right:8px;transform:translateY(-50%);
    background:transparent;border:none;cursor:pointer;padding:2px 4px;color:#6b6660;
    display:inline-flex;align-items:center;justify-content:center;line-height:0;
  }
  #loginScreen .lg-eye:hover{color:#334155;}
  #loginScreen .lg-eye svg{display:block;}
  #loginScreen .lg-submit{
    margin-top:18px;width:100%;padding:11px 14px;border:none;border-radius:8px;
    background:#2c4a52;color:#fff;font-weight:600;font-size:14px;cursor:pointer;
    transition:background .15s,transform .05s;
  }
  #loginScreen .lg-submit:hover:not(:disabled){background:#1f2a2e;}
  #loginScreen .lg-submit:disabled{opacity:.65;cursor:default;}
  #loginScreen .lg-error{
    min-height:18px;margin-top:10px;font-size:12px;color:#b85450;font-weight:500;
  }
  #loginScreen .lg-footer{
    margin-top:16px;padding-top:14px;border-top:1px solid #e8e1d5;
    font-size:11px;color:#6b6660;text-align:center;line-height:1.6;
  }
  /* ===== Change password modal ===== */
  #chgpwModal{
    position:fixed;inset:0;z-index:9500;display:none;
    align-items:center;justify-content:center;background:rgba(31,42,46,0.55);
  }
  #chgpwModal.visible{display:flex;}
  #chgpwModal .cp-card{
    background:#fff;color:#1f2a2e;
    width:min(420px, 92vw);padding:22px 22px 20px;border-radius:14px;
    box-shadow:0 20px 50px rgba(0,0,0,0.30);border:1px solid #e8e1d5;
  }
  #chgpwModal h2{font-size:15px;font-weight:700;color:#2c4a52;margin:0 0 12px;}
  #chgpwModal label{font-size:11px;font-weight:600;color:#2c4a52;display:block;margin:10px 0 4px;letter-spacing:.05em;text-transform:uppercase;}
  #chgpwModal .cp-input-wrap{position:relative;}
  #chgpwModal input{
    width:100%;padding:9px 40px 9px 12px;font-size:13px;box-sizing:border-box;
    border:1px solid #e8e1d5;border-radius:8px;background:#fbfaf6;outline:none;
  }
  #chgpwModal .cp-eye{
    position:absolute;top:50%;right:8px;transform:translateY(-50%);
    background:transparent;border:none;cursor:pointer;padding:2px 4px;color:#6b6660;
    display:inline-flex;align-items:center;justify-content:center;line-height:0;
  }
  #chgpwModal .cp-eye:hover{color:#334155;}
  #chgpwModal .cp-eye svg{display:block;}
  #chgpwModal .cp-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:16px;}
  #chgpwModal .cp-btn{padding:8px 14px;border-radius:8px;font-size:13px;font-weight:600;border:1px solid transparent;cursor:pointer;}
  #chgpwModal .cp-btn-primary{background:#2c4a52;color:#fff;}
  #chgpwModal .cp-btn-primary:hover:not(:disabled){background:#1f2a2e;}
  #chgpwModal .cp-btn-secondary{background:#f5f2ed;color:#2c4a52;border-color:#e8e1d5;}
  #chgpwModal .cp-msg{font-size:11.5px;margin-top:10px;min-height:14px;}
  #chgpwModal .cp-rules{font-size:11px;color:#6b6660;margin-top:6px;line-height:1.4;}
  /* Header sign-out + change-password controls */
  #authHdrWrap{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--c-muted);}
  #authHdrWrap .auth-link{
    background:none;border:none;color:#2c4a52;cursor:pointer;font-size:11px;font-weight:600;text-decoration:underline;padding:0;
  }
  #authHdrWrap .auth-link:hover{color:#5b7a82;}
  #authHdrWrap .auth-btn{
    background:#f0ebe3;color:#2c4a52;border:1px solid #e8e1d5;border-radius:6px;
    padding:4px 10px;font-size:11px;font-weight:600;cursor:pointer;
  }
  #authHdrWrap .auth-btn:hover{background:#e8e1d5;}
  #authWho{font-weight:600;color:#2c4a52;}
</style>
</head>
<body class="min-h-screen">

<!-- ========== Boot progress overlay ==========
     Shown from the moment the HTML mounts until renderAll() completes on
     first paint. Gives 4 stage indicators so a 12-second load feels like
     4 seconds of steady progress instead of a mystery-blank page. Once
     the app boots, JS calls bootProgress.finish() to fade this out. -->
<div id="bootProgress" aria-hidden="false">
  <div class="bp-card" role="status" aria-live="polite">
    <div class="bp-brand">Fynd · Receivables Insights</div>
    <div class="bp-sub">Loading dashboard…</div>
    <ol class="bp-stages">
      <li class="bp-stage" data-stage="1"><span class="bp-dot"></span>Loading application…</li>
      <li class="bp-stage" data-stage="2"><span class="bp-dot"></span>Preparing dashboard…</li>
      <li class="bp-stage" data-stage="3"><span class="bp-dot"></span>Connecting to sheet…</li>
      <li class="bp-stage" data-stage="4"><span class="bp-dot"></span>Rendering…</li>
    </ol>
    <div id="bpHint" class="bp-hint"></div>
  </div>
</div>
<style>
  #bootProgress{
    position:fixed;inset:0;z-index:9999;background:rgba(245,242,237,.96);
    display:flex;align-items:center;justify-content:center;
    transition:opacity .28s ease;
  }
  #bootProgress.bp-fading{opacity:0;pointer-events:none;}
  #bootProgress .bp-card{
    background:#fff;border:1px solid #e8e1d5;border-radius:16px;
    padding:22px 26px 20px;box-shadow:0 10px 30px rgba(31,42,46,.08);
    min-width:320px;max-width:420px;
  }
  #bootProgress .bp-brand{font-size:15px;font-weight:700;color:#1f2a2e;letter-spacing:-.01em;}
  #bootProgress .bp-sub{font-size:12px;color:#6b6660;margin-top:2px;margin-bottom:14px;}
  #bootProgress .bp-stages{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px;}
  #bootProgress .bp-stage{
    display:flex;align-items:center;gap:10px;font-size:12.5px;color:#9c968f;
    transition:color .2s ease;
  }
  #bootProgress .bp-dot{
    width:12px;height:12px;border-radius:50%;border:1.5px solid #cbc4b6;background:#fff;
    display:inline-block;flex-shrink:0;position:relative;
    transition:all .2s ease;
  }
  #bootProgress .bp-stage.bp-active{color:#2c4a52;font-weight:500;}
  #bootProgress .bp-stage.bp-active .bp-dot{
    border-color:#2c4a52;
    box-shadow:0 0 0 4px rgba(44,74,82,.12);
    animation:bpPulse 1.1s ease-in-out infinite;
  }
  #bootProgress .bp-stage.bp-done{color:#4a6b58;}
  #bootProgress .bp-stage.bp-done .bp-dot{
    background:#6b8e5a;border-color:#6b8e5a;
    box-shadow:none;animation:none;
  }
  @keyframes bpPulse{
    0%,100%{box-shadow:0 0 0 4px rgba(44,74,82,.12);}
    50%    {box-shadow:0 0 0 7px rgba(44,74,82,.05);}
  }
  #bootProgress .bp-hint{font-size:11px;color:#9c968f;margin-top:12px;min-height:14px;}
</style>
<script>
  /* Boot progress controller — called from head-inline script (immediately)
     and from the main app bundle later. Safe to call multiple times. */
  window.bootProgress = (function(){
    var stages = null;
    var currentStage = 0;   // highest stage number reached so far
    var autoTimer = null;
    function els(){
      if (!stages) stages = document.querySelectorAll('#bootProgress .bp-stage');
      return stages;
    }
    function paint(n){
      try{
        var list = els();
        for (var i = 0; i < list.length; i++){
          var s = list[i]; var num = i + 1;
          s.classList.remove('bp-active','bp-done');
          if (num < n)        s.classList.add('bp-done');
          else if (num === n) s.classList.add('bp-active');
        }
      } catch(_){}
    }
    // Only advance forward — protect against out-of-order callers.
    function step(n){
      if (typeof n !== 'number') return;
      if (n <= currentStage) return;
      currentStage = n;
      paint(n);
    }
    function hint(msg){
      try{ var el = document.getElementById('bpHint'); if (el) el.textContent = msg||''; } catch(_){}
    }
    function finish(){
      try{
        if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
        currentStage = 5;
        paint(5);              // marks all 4 as done
        var ov = document.getElementById('bootProgress');
        if (!ov) return;
        ov.classList.add('bp-fading');
        setTimeout(function(){ if (ov && ov.parentNode) ov.parentNode.removeChild(ov); }, 320);
      } catch(_){}
    }
    // Kick off stage 1 immediately.
    try { step(1); } catch(_){}
    // Time-based auto-advance: even while the big JS bundle is still parsing
    // (before boot() gets a chance to call step()), tick the visual progress
    // forward every ~1.2 s so the user never sees the overlay appear "stuck".
    // step() is idempotent + monotonic, so if boot() later calls step(3),
    // step(4), etc., the auto-advance is harmless.
    try {
      autoTimer = setInterval(function(){
        // Ceiling at stage 3 — leaves "Rendering…" (stage 4) for the real
        // render callback, and only shows real completion via finish().
        if (currentStage < 3) step(currentStage + 1);
      }, 1200);
    } catch(_){}
    // SAFETY NET: If boot() throws, hangs, or a wire*() function crashes,
    // the overlay would otherwise sit forever covering the whole UI. Force
    // it to clear after 12 s no matter what. The app-shell underneath will
    // then be usable even if some feature failed to initialize.
    try {
      setTimeout(function(){
        try { finish(); } catch(_){}
      }, 12000);
    } catch(_){}
    return { step: step, hint: hint, finish: finish };
  })();

  /* ============================================================
     Apps Script hosting — injection fallback
     ------------------------------------------------------------
     When serveDashboard_() serves this HTML from /exec, it injects a
     <script> block at the top of <head> that sets:
         window.__DATA_URL__            = <the /exec URL>
         window.__SERVED_BY_APPS_SCRIPT__ = true
     Those flags drive auto-connect (liveFetch) and UI trimming (hide the
     Settings gear because the URL is already known).
     If for any reason that inject is missing (stale deployment, HTML string
     mismatch, sanitizer stripped the script) we can still detect Apps Script
     hosting from the browser side:
       • location.hostname is *.googleusercontent.com (Apps Script sandbox)
       • document.referrer is the parent script.google.com/.../exec URL
     When both hold, we back-fill the two globals ourselves and kick off the
     first liveFetch as soon as liveFetch is defined. Belt-and-braces so a
     stale deployment doesn't leave the dashboard sitting empty at "Live Off".
     ============================================================ */
  (function detectAppsScriptFallback(){
    try {
      if (window.__SERVED_BY_APPS_SCRIPT__) return; // Injection already fired.
      var hn  = String((location && location.hostname) || '');
      var ref = String((document && document.referrer) || '');
      var looksLikeSandbox = /googleusercontent\.com$/i.test(hn) || /script\.google\.com/i.test(hn);
      var execMatch = ref.match(/^(https?:\/\/script\.google\.com\/[^\s?#]*\/exec)/i);
      if (looksLikeSandbox && execMatch) {
        window.__DATA_URL__ = execMatch[1];
        window.__SERVED_BY_APPS_SCRIPT__ = true;
        try { console.info('[Fynd] Apps Script hosting detected via fallback. DATA URL =', window.__DATA_URL__); } catch(_){}
        // liveFetch is not yet defined at head-inline time — arm a retry loop
        // that kicks off the fetch as soon as the main bundle wires it up.
        try {
          var _tries = 0;
          var _iv = setInterval(function(){
            _tries++;
            if (typeof window.liveFetch === 'function') {
              try { window.liveFetch(false); } catch(_){}
              try { if (typeof window.startLiveTimer === 'function') window.startLiveTimer(); } catch(_){}
              clearInterval(_iv);
            } else if (_tries > 60) {
              clearInterval(_iv); // Give up after ~30 s.
            }
          }, 500);
        } catch(_){}
      }
    } catch(_){}
  })();
</script>

<!-- ========== Login screen overlay (application-level auth) ========== -->
<!-- Full-viewport dark overlay shown before the dashboard renders when the
     viewer doesn't have a valid session token. The dashboard `#app-shell`
     stays hidden until authWhoAmI resolves successfully. Break-glass:
     the Google-identity admin (sainathgosika@gofynd.com) skips this. -->
<div id="loginScreen" role="dialog" aria-modal="true" aria-labelledby="lgTitle">
  <div class="lg-card">
    <h1 id="lgTitle">Fynd · Receivables Insights</h1>
    <div class="lg-sub">Sign in to Fynd AR Receivables</div>
    <form id="loginForm" autocomplete="on" onsubmit="return false;">
      <label for="lgUsername">Username</label>
      <div class="lg-input-wrap">
        <input id="lgUsername" name="username" type="text" autocomplete="username" spellcheck="false" required />
      </div>
      <label for="lgPassword">Password</label>
      <div class="lg-input-wrap">
        <input id="lgPassword" name="password" type="password" autocomplete="current-password" required />
        <button type="button" id="lgEyeBtn" class="lg-eye" aria-label="Show password" title="Show / hide password"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></button>
      </div>
      <button type="submit" id="lgSubmit" class="lg-submit">Sign in</button>
      <div id="lgError" class="lg-error" role="alert"></div>
    </form>
    <div class="lg-footer">
      Contact <a href="mailto:sainathgosika@gofynd.com" style="color:#2c4a52;font-weight:600;">sainathgosika@gofynd.com</a> for access.
    </div>
  </div>
</div>

<!-- ========== Change password modal ========== -->
<div id="chgpwModal" role="dialog" aria-modal="true" aria-labelledby="cpTitle">
  <div class="cp-card">
    <h2 id="cpTitle">Change password</h2>
    <form id="chgpwForm" onsubmit="return false;">
      <label for="cpOld">Current password</label>
      <div class="cp-input-wrap">
        <input id="cpOld" type="password" autocomplete="current-password" required />
        <button type="button" class="cp-eye" data-cp-eye="cpOld" aria-label="Show password"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></button>
      </div>
      <label for="cpNew">New password</label>
      <div class="cp-input-wrap">
        <input id="cpNew" type="password" autocomplete="new-password" required />
        <button type="button" class="cp-eye" data-cp-eye="cpNew" aria-label="Show password"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></button>
      </div>
      <label for="cpConfirm">Confirm new password</label>
      <div class="cp-input-wrap">
        <input id="cpConfirm" type="password" autocomplete="new-password" required />
        <button type="button" class="cp-eye" data-cp-eye="cpConfirm" aria-label="Show password"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></button>
      </div>
      <div class="cp-rules">Password must be at least 6 characters and contain a mix of letters, numbers, and symbols.</div>
      <div id="cpMsg" class="cp-msg" role="alert"></div>
      <div class="cp-actions">
        <button type="button" id="cpCancel" class="cp-btn cp-btn-secondary">Cancel</button>
        <button type="submit" id="cpSubmit" class="cp-btn cp-btn-primary">Update password</button>
      </div>
    </form>
  </div>
</div>

<!-- App shell — everything below is hidden until authWhoAmI resolves. -->
<div id="app-shell">

<!-- ========== FIXED LEFT SIDEBAR ========== -->
<aside class="sidebar" id="sideNav">
  <div class="sb-brand" id="sbBrand" title="Back to Overview">
    <img src="https://cdn.brandfetch.io/id7q4N5Xqp/w/3750/h/3750/theme/dark/idNy5EIX-i.png?c=1bxid64Mup7aczewSAYMX&t=1750146541811"
         alt="Fynd"
         onerror="this.onerror=null;this.outerHTML='<div class=&quot;sb-brand-fallback&quot;>F</div>'"/>
    <div class="sb-brand-text">
      <span class="b-name">Fynd</span>
      <span class="b-sub">Receivables</span>
    </div>
  </div>
  <div class="sb-section first">Insights</div>
  <div class="tab-item active" data-target="dashboard"><span class="sb-icon">◧</span><span class="sb-label">Overview</span></div>
  <div class="tab-item" data-target="customers"><span class="sb-icon">👥</span><span class="sb-label">Customer &amp; Region</span></div>
  <div class="tab-item" data-target="pdd"><span class="sb-icon">🛡</span><span class="sb-label">PDD</span></div>

  <div class="sb-section">Collections</div>
  <div class="tab-item" data-target="bank"><span class="sb-icon">🏦</span><span class="sb-label">Bank Receipts</span></div>
  <div class="sb-group-toggle" id="arActivityToggle" title="Toggle Follow-ups + Worklist"><span class="sb-icon">📨</span><span class="sb-label">AR Activity</span><span class="sb-caret">›</span></div>
  <div class="sb-group-children" id="arActivityChildren">
    <div class="tab-item sb-sub" data-target="followups"><span class="sb-icon">📧</span><span class="sb-label">Follow-ups</span></div>
    <div class="tab-item sb-sub" data-target="pocs"><span class="sb-icon">📇</span><span class="sb-label">Contacts</span></div>
    <div class="tab-item sb-sub" data-target="workflows"><span class="sb-icon">⚙</span><span class="sb-label">Workflows</span></div>
    <div class="tab-item sb-sub collector-only" data-target="worklist" style="display:none"><span class="sb-icon">✅</span><span class="sb-label">Worklist</span></div>
    <div class="tab-item sb-sub" data-target="statement"><span class="sb-icon">🧾</span><span class="sb-label">Customer Statement</span></div>
  </div>

  <div class="sb-section">Reports</div>
  <div class="tab-item" data-target="reports"><span class="sb-icon">📊</span><span class="sb-label">Reports</span></div>

  <div class="sb-section">Admin</div>
  <div class="tab-item" data-target="activity"><span class="sb-icon">📋</span><span class="sb-label">Activity Log</span></div>
  <div class="tab-item admin-only hidden-until-admin" data-target="acm"><span class="sb-icon">🔐</span><span class="sb-label">User Management</span></div>
</aside>

<div class="page-shell">

<!-- ========== STICKY TOPBAR + TAB STRIP + KPI BAR ========== -->
<header class="sticky-header">
  <div class="max-w-[1600px] mx-auto px-6 pt-4 pb-3">
    <div class="flex items-center justify-between gap-4 mb-3">
      <div class="flex items-center gap-3 flex-1">
        <!-- Fynd brand button: click → jump to Overview -->
        <button id="btnBrandHome" class="brand-btn" title="Back to Overview">
          <img src="https://cdn.brandfetch.io/id7q4N5Xqp/w/3750/h/3750/theme/dark/idNy5EIX-i.png?c=1bxid64Mup7aczewSAYMX&t=1750146541811"
               alt="Fynd"
               onerror="this.onerror=null;this.outerHTML='<div style=&quot;font-weight:700;font-size:18px;color:#2c4a52;letter-spacing:-.02em&quot;>fynd</div>'"/>
          <div class="text-left">
            <div class="b-name">Receivables</div>
            <div class="b-sub">Insights</div>
          </div>
        </button>
        <div class="hidden md:block">
          <div class="text-[11px]" style="color:var(--c-muted)" id="hdrMeta">AR Control Tower · Last refresh: <span id="lastRefresh">—</span> · <span id="hdrCount">0</span> records</div>
        </div>
        <div class="topbar-search hidden md:block">
          <input id="globalSearch" placeholder="Search customers, invoices, BUs…" autocomplete="off"/>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <div class="rounded-lg p-0.5 inline-flex" id="currencySeg" data-tip="Display currency unit" style="background:var(--c-soft);position:relative;">
          <button class="seg-btn active" data-cu="auto">Auto</button>
          <button class="seg-btn" data-cu="inr">₹</button>
          <button class="seg-btn" data-cu="k">K</button>
          <button class="seg-btn" data-cu="l">L</button>
          <button class="seg-btn" data-cu="cr">Cr</button>
        </div>
        <div class="flex items-center gap-1.5">
          <div id="authHdrWrap" style="display:none">
            <span id="authWho" title="Signed-in user">—</span>
            <button type="button" id="authChangePwBtn" class="auth-link" title="Change password">Change password</button>
            <button type="button" id="authLogoutBtn" class="auth-btn" title="Sign out of the dashboard">Sign out</button>
          </div>
          <button id="btnLiveSync" class="icon-btn" data-tip="Pull latest from Google Sheet">
            <span id="liveDot" style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#cbd5e1"></span>
            <span id="liveLabel" style="display:none"></span>
          </button>
          <span id="cacheStatePill" style="display:none;font-size:11px;padding:3px 8px;border-radius:9999px;background:#fef3c7;color:#92400e;border:1px solid #fde68a;">Showing cached data · refreshing…</span>
          <button id="btnHardRefresh" class="icon-btn" data-tip="Hard Refresh — purge server cache & reload everything">↻</button>
          <button id="btnPrint"   class="icon-btn" data-tip="Print or save as PDF">🖨</button>
          <button id="btnSettings" class="icon-btn" data-tip="Configure live data source">⚙</button>
        </div>
      </div>
    </div>
    <!-- Sticky KPI strip (7 metrics) -->
    <div class="grid grid-cols-2 md:grid-cols-7 gap-2" id="stickyKPIs">
      <div class="card px-3 py-2"><div class="kpi-lab">Total Collections</div><div class="kpi-num text-emerald-600" id="sk_col">—</div></div>
      <div class="card px-3 py-2"><div class="kpi-lab">Total Outstanding</div><div class="kpi-num" id="sk_os">—</div></div>
      <div class="card px-3 py-2"><div class="kpi-lab">Total Invoiced</div><div class="kpi-num text-indigo-600" id="sk_inv">—</div></div>
      <div class="card px-3 py-2"><div class="kpi-lab">Total Regions</div><div class="kpi-num text-amber-600" id="sk_bu_top">—</div></div>
      <div class="card px-3 py-2"><div class="kpi-lab">Total Customers</div><div class="kpi-num text-fuchsia-600" id="sk_cust">—</div></div>
      <div class="card px-3 py-2" title="DSO = (Outstanding ÷ Credit Sales) × Days since customer's first invoice"><div class="kpi-lab">DSO in days <span class="dso-info">ⓘ</span></div><div class="kpi-num text-violet-600" id="sk_dso">—</div></div>
      <div class="card px-3 py-2"><div class="kpi-lab">Coverage</div><div class="kpi-num text-rose-600" id="sk_cov">—</div></div>
    </div>

    <!-- ===== Sticky Filters (always visible across every tab) ===== -->
    <section class="card px-3 py-2 mt-2" id="stickyFilters">
      <!-- Row 1: title + date chips + more-filters toggle + row count + report (single line) -->
      <div class="flex items-center gap-2 flex-wrap">
        <h3 class="text-sm font-semibold mr-1" style="color:var(--c-accent)">Filters</h3>
        <div class="flex flex-wrap items-center gap-1.5" id="dateChips" title="Date Range (combined: Invoice Date ∪ Receipt Date)">
          <span class="chip" data-r="month">Monthly</span>
          <span class="chip" data-r="quarter">Quarterly</span>
          <span class="chip" data-r="ytd">Yearly</span>
          <span class="chip active" data-r="all">All</span>
          <span class="chip" data-r="custom">Custom</span>
        </div>
        <div class="flex items-center gap-1.5 hidden" id="dateCustom">
          <input id="dateFrom" type="date" class="border border-slate-200 rounded-md px-2 py-1 text-xs"/>
          <span class="text-slate-400 text-xs">to</span>
          <input id="dateTo" type="date" class="border border-slate-200 rounded-md px-2 py-1 text-xs"/>
        </div>
        <button id="btnMoreFilters" class="chip" title="Show / hide secondary filters">＋ More filters</button>
        <button id="btnClearAllChip" class="chip" style="background:#fee2e2;color:#991b1b;border-color:#fecaca;">↺ Reset</button>
        <span class="text-[11px] ml-auto" style="color:var(--c-muted)" id="rowCounter">—</span>
      </div>

      <!-- Multi-select filters: 4 primary + 4 secondary (revealed by More filters) -->
      <div id="msContainer" class="mt-2">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div data-key="customer"></div>
          <div data-key="bu"></div>
          <div data-key="invoiceType"></div>
          <div data-key="status"></div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2 hidden" id="msExtra">
          <div data-key="bucket"></div>
          <div data-key="paymentType"></div>
          <div data-key="channel"></div>
          <div data-key="paymentTerm"></div>
        </div>
      </div>
    </section>
  </div>
</header>

<!-- ===== Live Sync Settings Modal ===== -->
<div id="settingsModal" class="hidden fixed inset-0 z-[2000]" style="background:rgba(15,23,42,0.55);backdrop-filter:blur(2px)">
  <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl w-[560px] max-w-[92vw] overflow-hidden">
    <div class="px-5 py-3 flex items-center justify-between" style="background:linear-gradient(135deg,#0f172a,#312e81);color:#fff">
      <div>
        <div class="text-sm font-semibold">Live Data Source</div>
        <div class="text-[11px] text-slate-300">Connect this dashboard to your Google Sheet via Apps Script Web App</div>
      </div>
      <button id="settingsClose" class="text-white/80 hover:text-white text-lg">✕</button>
    </div>
    <div class="p-5 space-y-4">
      <div>
        <label class="text-[11px] text-slate-500 uppercase tracking-wide font-medium">Web App URL</label>
        <input id="cfgUrl" type="url" placeholder="https://script.google.com/macros/s/AKfyc.../exec"
          class="w-full mt-1 border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono"/>
        <div class="text-[11px] text-slate-500 mt-1">Deploy the Apps Script (see <code class="text-indigo-700">AR_Insights_AppsScript.gs</code>) and paste the resulting URL here.</div>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="text-[11px] text-slate-500 uppercase tracking-wide font-medium">Auto-refresh</label>
          <select id="cfgInterval" class="w-full mt-1 border border-slate-200 rounded-lg px-3 py-2 text-xs">
            <option value="0">Off (manual only)</option>
            <option value="60">Every 1 minute</option>
            <option value="300" selected>Every 5 minutes</option>
            <option value="600">Every 10 minutes</option>
            <option value="900">Every 15 minutes</option>
            <option value="1800">Every 30 minutes</option>
          </select>
        </div>
        <div>
          <label class="text-[11px] text-slate-500 uppercase tracking-wide font-medium">Status</label>
          <div id="cfgStatus" class="w-full mt-1 px-3 py-2 text-xs rounded-lg bg-slate-50 border border-slate-200 text-slate-600">Not connected</div>
        </div>
      </div>
      <div id="cfgDiag" class="rounded-lg border border-amber-200 bg-amber-50 p-3 hidden">
        <div class="text-[11px] font-semibold text-amber-800 mb-1">Last sync diagnostics</div>
        <div id="cfgDiagBody" class="text-[11px] text-amber-900 font-mono whitespace-pre-wrap" style="max-height:280px;overflow:auto"></div>
      </div>
      <div class="rounded-lg border border-slate-200 p-3 bg-slate-50/50">
        <div class="text-[11px] font-semibold text-slate-700 mb-1">Quick deploy steps</div>
        <ol class="text-[11px] text-slate-600 space-y-0.5 ml-4 list-decimal">
          <li>Open the sheet → Extensions → Apps Script.</li>
          <li>Paste contents of <code>AR_Insights_AppsScript.gs</code>, save.</li>
          <li>Deploy → New deployment → Web app → Execute as: <b>Me</b> → Access: <b>Anyone within fynd.com</b>.</li>
          <li>Copy the URL → paste above → click Test &amp; Save.</li>
        </ol>
      </div>
    </div>
    <div class="px-5 py-3 border-t border-slate-200 flex items-center justify-between bg-slate-50">
      <button id="cfgDisconnect" class="text-[11px] text-rose-600 hover:underline">Disconnect</button>
      <div class="flex gap-2">
        <button id="cfgTest" class="chip">🔌 Test</button>
        <button id="cfgSave" class="chip" style="background:#4f46e5;color:#fff;border-color:#4338ca">Save &amp; Connect</button>
      </div>
    </div>
  </div>
</div>

<!-- ========== MAIN CONTENT ========== -->
<div class="max-w-[1600px] mx-auto px-6 py-4">
  <main class="space-y-4">

    <!-- ===== DASHBOARD anchor ===== -->
    <div id="dashboard-anchor" data-section="dashboard"></div>

    <!-- Charts: 4 total (Ageing | Top 10 Customers | Channel-wise | Trend) -->
    <section class="grid md:grid-cols-2 gap-4" data-section="dashboard">
      <div class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <div><div class="text-sm font-semibold text-slate-800">Ageing Distribution</div><div class="text-[11px] text-slate-500">Outstanding by ageing bucket (ascending)</div></div>
        </div>
        <div style="height:260px"><canvas id="cAge"></canvas></div>
      </div>
      <div class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <div><div class="text-sm font-semibold text-slate-800">Top 10 Customers</div><div class="text-[11px] text-slate-500">By selected metric</div></div>
          <div class="bg-slate-100 rounded-lg p-0.5 inline-flex" id="topSeg">
            <button class="seg-btn active" data-m="collections">Collections</button>
            <button class="seg-btn" data-m="outstanding">Outstanding</button>
            <button class="seg-btn" data-m="invoiced">Invoiced</button>
          </div>
        </div>
        <div style="height:260px"><canvas id="cTop"></canvas></div>
      </div>
    </section>

    <section class="grid md:grid-cols-2 gap-4" data-section="dashboard">
      <div class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <div><div class="text-sm font-semibold text-slate-800">Channel-wise Performance</div><div class="text-[11px] text-slate-500">By selected metric</div></div>
          <div class="bg-slate-100 rounded-lg p-0.5 inline-flex" id="chSeg">
            <button class="seg-btn active" data-m="collections">Collections</button>
            <button class="seg-btn" data-m="outstanding">Outstanding</button>
            <button class="seg-btn" data-m="invoiced">Invoiced</button>
          </div>
        </div>
        <div style="height:260px"><canvas id="cCh"></canvas></div>
      </div>
      <div class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <div><div class="text-sm font-semibold text-slate-800">Collections vs Invoices Trend</div><div class="text-[11px] text-slate-500">Monthly</div></div>
        </div>
        <div style="height:260px"><canvas id="cTrend"></canvas></div>
      </div>
    </section>

    <!-- ===== CUSTOMERS anchor ===== -->
    <div id="customers-anchor" data-section="customers"></div>

    <!-- Customer-wise breakdown with split-by-BU rows + expand -->
    <section class="card p-4" data-section="customers">
      <div class="flex items-start justify-between mb-3 flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold" style="color:var(--c-ink)">Customer-wise Breakdown</div>
          <div class="text-[11px]" style="color:var(--c-muted)" id="custMeta">— customers · split by Region</div>
        </div>
        <div class="flex items-center gap-2">
          <button id="custClear" class="chip" title="Reset customer-section filters" style="background:#f3e0df;color:#8b3a37;border-color:#e8c8c6;">↺ Reset</button>
          <button id="custXlsx" class="chip" title="Generate styled Excel report from filtered customers" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent);">📊 Generate Report</button>
        </div>
      </div>
      <!-- Section filter bar with multi-selects -->
      <div class="rounded-lg border bg-[var(--c-soft)] p-3 mb-3" style="border-color:var(--c-line);">
        <div class="grid md:grid-cols-12 gap-2 items-end">
          <div class="md:col-span-4" id="custMSCustomer"></div>
          <div class="md:col-span-4" id="custMSBU"></div>
          <div class="md:col-span-4">
            <div class="text-[10.5px] uppercase tracking-wide font-medium mb-1" style="color:var(--c-muted)">Search</div>
            <input id="custFilter" placeholder="🔍 Customer / CID..." class="w-full border rounded-md px-3 py-1.5 text-xs" style="border-color:var(--c-line);"/>
          </div>
        </div>
      </div>
      <div class="scroll-x">
        <div class="cust-scroll" style="max-height:240px;overflow-y:auto;border:1px solid var(--c-line);border-radius:10px;">
        <table class="w-full">
          <thead style="position:sticky;top:0;z-index:3;background:#fafbff;">
            <tr>
              <th></th><th>#</th><th>Customer / BU</th><th class="text-right">Invoices</th>
              <th class="text-right">Invoice Amt</th><th class="text-right">Collections</th>
              <th class="text-right">Outstanding</th>
              <th class="text-right" title="DSO = (Outstanding ÷ Credit Sales) × Days since customer's first invoice">DSO in days <span class="dso-info">ⓘ</span></th>
              <th class="text-right">Collection %</th>
            </tr>
          </thead>
          <tbody id="custBody"></tbody>
        </table>
        </div>
      </div>
      <div class="mt-2 text-[11px] text-slate-500">
        <span class="num-red mr-2">●</span>Outstanding &gt; 0 (red) ·
        <span class="num-green mx-2">●</span>Outstanding ≤ 0 (green) ·
        click row to drill into BU split
      </div>
    </section>

    <!-- ===== REGIONS anchor (merged under Customers tab) ===== -->
    <div id="invoices-anchor" data-section="customers"></div>

    <!-- Region-wise breakdown - simplified columns + conditional formatting + expand -->
    <section class="card p-4" data-section="customers">
      <div class="flex items-start justify-between mb-3 flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold" style="color:var(--c-ink)">Region Breakdown</div>
          <div class="text-[11px]" style="color:var(--c-muted)" id="buMeta">— Regions · click to drill into customers</div>
        </div>
        <div class="flex items-center gap-2">
          <button id="buClear" class="chip" title="Reset Region-section filters" style="background:#f3e0df;color:#8b3a37;border-color:#e8c8c6;">↺ Reset</button>
          <button id="buXlsx" class="chip" title="Generate styled Excel report from filtered Regions" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent);">📊 Generate Report</button>
        </div>
      </div>
      <!-- Section filter bar with multi-selects -->
      <div class="rounded-lg border bg-[var(--c-soft)] p-3 mb-3" style="border-color:var(--c-line);">
        <div class="grid md:grid-cols-12 gap-2 items-end">
          <div class="md:col-span-4" id="buMSBU"></div>
          <div class="md:col-span-4" id="buMSChannel"></div>
          <div class="md:col-span-4">
            <div class="text-[10.5px] uppercase tracking-wide font-medium mb-1" style="color:var(--c-muted)">Search</div>
            <input id="buFilter" placeholder="🔍 BU name..." class="w-full border rounded-md px-3 py-1.5 text-xs" style="border-color:var(--c-line);"/>
          </div>
        </div>
      </div>
      <div class="scroll-x">
        <div class="bu-scroll" style="max-height:240px;overflow-y:auto;border:1px solid var(--c-line);border-radius:10px;">
        <table class="w-full">
          <thead style="position:sticky;top:0;z-index:3;background:#fafbff;">
            <tr>
              <th></th><th>#</th><th>Region</th><th class="text-right">Invoices</th>
              <th class="text-right">Invoice Amt</th><th class="text-right">Collections</th>
              <th class="text-right">Outstanding</th>
              <th class="text-right" title="DSO = (Outstanding ÷ Credit Sales) × Days since customer's first invoice">DSO in days <span class="dso-info">ⓘ</span></th>
              <th class="text-right">Collection %</th>
            </tr>
          </thead>
          <tbody id="buBody"></tbody>
        </table>
        </div>
      </div>
      <div class="mt-2 text-[11px] text-slate-500">
        <span class="num-red mr-2">●</span>Outstanding &gt; 0 (red) ·
        <span class="num-green mx-2">●</span>Outstanding ≤ 0 (green)
      </div>
    </section>

    <!-- ===== PDD anchor ===== -->
    <div id="pdd-anchor" data-section="pdd"></div>
    <section class="card p-4" data-section="pdd">
      <div class="flex items-start justify-between mb-3 flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">🛡 Provision for Doubtful Debts (PDD)</div>
          <div class="text-[11px] text-slate-500" id="pddMeta">— invoices booked under PDD · live from <code>PDD_Data</code></div>
        </div>
        <div class="flex items-center gap-2">
          <button id="pddClear" class="chip" title="Reset all PDD filters" style="background:#f3e0df;color:#8b3a37;border-color:#e8c8c6;">↺ Reset</button>
          <button id="pddXlsx" class="chip" title="Generate styled Excel report from filtered PDD" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent);">📊 Generate Report</button>
        </div>
      </div>
      <!-- PDD custom filters bar (single-line, compact) -->
      <div class="rounded-lg border border-slate-200 bg-slate-50/40 p-3 mb-3">
        <div class="grid md:grid-cols-12 gap-2 items-end">
          <div class="md:col-span-6">
            <div class="text-[10.5px] text-slate-500 uppercase tracking-wide font-medium mb-1">PDD Date Range</div>
            <div class="flex flex-nowrap gap-1 overflow-x-auto" id="pddDateChips" style="white-space:nowrap">
              <span class="chip pdd-r active" data-r="all">All</span>
              <span class="chip pdd-r" data-r="month">This Month</span>
              <span class="chip pdd-r" data-r="quarter">This Quarter</span>
              <span class="chip pdd-r" data-r="ytd">This Year</span>
              <span class="chip pdd-r" data-r="custom">Custom</span>
            </div>
            <div id="pddDateCustom" class="hidden mt-2 flex items-center gap-1.5">
              <input id="pddFrom" type="date" class="border border-slate-200 rounded-md px-2 py-1 text-xs"/>
              <span class="text-slate-400 text-xs">→</span>
              <input id="pddTo" type="date" class="border border-slate-200 rounded-md px-2 py-1 text-xs"/>
            </div>
          </div>
          <div class="md:col-span-3">
            <div id="pddMSQuarter"></div>
          </div>
          <div class="md:col-span-3">
            <div class="text-[10.5px] text-slate-500 uppercase tracking-wide font-medium mb-1">Search</div>
            <input id="pddFilter" placeholder="🔍 Customer / invoice / CID / CC..." class="w-full border border-slate-200 rounded-md px-3 py-1.5 text-xs"/>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        <div class="kpi-card"><div class="kpi-lab">Invoices Booked</div><div class="kpi-num" id="pdd_count">—</div></div>
        <div class="kpi-card"><div class="kpi-lab">PDD Booked</div><div class="kpi-num text-rose-600" id="pdd_os">—</div></div>
        <div class="kpi-card"><div class="kpi-lab">PDD Reversed</div><div class="kpi-num text-emerald-600" id="pdd_rev">—</div></div>
        <div class="kpi-card"><div class="kpi-lab">Current PDD</div><div class="kpi-num text-amber-600" id="pdd_cur">—</div></div>
      </div>
      <div class="grid md:grid-cols-2 gap-4 mb-3">
        <div class="card p-4" style="border:1px solid var(--c-line)">
          <div class="text-sm font-semibold text-slate-800 mb-1">PDD by Quarter Booked</div>
          <div class="text-[11px] text-slate-500 mb-3">Net PDD = Current − Reversed</div>
          <div style="height:240px"><canvas id="cPddQtr"></canvas></div>
        </div>
        <div class="card p-4" style="border:1px solid var(--c-line)">
          <div class="text-sm font-semibold text-slate-800 mb-1">Top Customers by PDD Outstanding</div>
          <div class="text-[11px] text-slate-500 mb-3">Top 10 by current PDD</div>
          <div style="height:240px"><canvas id="cPddCust"></canvas></div>
        </div>
      </div>
      <div class="scroll-x">
        <div style="max-height:240px;overflow-y:auto;border:1px solid var(--c-line);border-radius:10px;">
        <table class="w-full">
          <thead style="position:sticky;top:0;z-index:3;background:#fafbff;">
            <tr>
              <th>PDD Booked</th><th>PDD Date</th><th>CID</th><th>Customer</th><th>BU</th><th>Channel</th><th>Invoice No</th><th class="text-right">Invoice Amt</th><th class="text-right">Outstanding</th><th class="text-right">Current PDD</th><th class="text-right">Reversed</th><th>CC</th>
            </tr>
          </thead>
          <tbody id="pddBody"></tbody>
        </table>
        </div>
      </div>
    </section>

    <!-- ===== BANK anchor ===== -->
    <div id="bank-anchor" data-section="bank"></div>
    <section class="card p-4" data-section="bank">
      <div class="flex items-start justify-between mb-3 flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">🏦 Bank Receipts</div>
          <div class="text-[11px] text-slate-500" id="bankMeta">— receipts · live from <code>Bank_Receipts</code></div>
        </div>
        <div class="flex items-center gap-2">
          <button id="bankClear" class="chip" title="Reset all bank filters" style="background:#f3e0df;color:#8b3a37;border-color:#e8c8c6;">↺ Reset</button>
          <button id="bankXlsx" class="chip" title="Generate styled Excel report from filtered receipts" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent);">📊 Generate Report</button>
        </div>
      </div>
      <!-- Bank custom filters bar -->
      <div class="rounded-lg border border-slate-200 bg-slate-50/40 p-3 mb-3">
        <div class="grid md:grid-cols-12 gap-2 items-end">
          <div class="md:col-span-12">
            <div class="text-[10.5px] text-slate-500 uppercase tracking-wide font-medium mb-1">Receipt Date Range</div>
            <div class="flex flex-nowrap gap-1 overflow-x-auto" id="bankDateChips" style="white-space:nowrap">
              <span class="chip bk-r active" data-r="all">All</span>
              <span class="chip bk-r" data-r="month">This Month</span>
              <span class="chip bk-r" data-r="quarter">This Quarter</span>
              <span class="chip bk-r" data-r="ytd">This Year</span>
              <span class="chip bk-r" data-r="custom">Custom</span>
            </div>
            <div id="bankDateCustom" class="hidden mt-2 flex items-center gap-1.5">
              <input id="bankFrom" type="date" class="border border-slate-200 rounded-md px-2 py-1 text-xs"/>
              <span class="text-slate-400 text-xs">→</span>
              <input id="bankTo" type="date" class="border border-slate-200 rounded-md px-2 py-1 text-xs"/>
            </div>
          </div>
          <div class="md:col-span-3"><div id="bankMSBank"></div></div>
          <div class="md:col-span-3"><div id="bankMSStatus"></div></div>
          <div class="md:col-span-3"><div id="bankMSBU"></div></div>
          <div class="md:col-span-3">
            <div class="text-[10.5px] text-slate-500 uppercase tracking-wide font-medium mb-1">Search</div>
            <input id="bankFilter" placeholder="🔍 Company / Narration / CID / UTR..." class="w-full border border-slate-200 rounded-md px-3 py-1.5 text-xs"/>
          </div>
        </div>
        <div class="mt-2 flex items-center gap-2 text-[11px] text-slate-500">
          <label>Min Amount</label>
          <input id="bankMin" type="number" min="0" step="100" placeholder="0"
            class="border border-slate-200 rounded-md px-2 py-1 text-xs w-32"/>
          <span class="text-slate-300">|</span>
          <label>Max Amount</label>
          <input id="bankMax" type="number" min="0" step="100" placeholder="∞"
            class="border border-slate-200 rounded-md px-2 py-1 text-xs w-32"/>
        </div>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
        <div class="kpi-card"><div class="kpi-lab">Total Receipts</div><div class="kpi-num" id="bk_count">—</div></div>
        <div class="kpi-card"><div class="kpi-lab">Amount Credited</div><div class="kpi-num text-emerald-600" id="bk_total">—</div></div>
        <div class="kpi-card"><div class="kpi-lab">Applied</div><div class="kpi-num text-indigo-600" id="bk_applied">—</div></div>
        <div class="kpi-card"><div class="kpi-lab">Partial / Pending</div><div class="kpi-num text-amber-600" id="bk_pending">—</div></div>
        <div class="kpi-card"><div class="kpi-lab">Banks</div><div class="kpi-num text-violet-600" id="bk_banks">—</div></div>
      </div>
      <div class="grid md:grid-cols-2 gap-4 mb-3">
        <div class="card p-4" style="border:1px solid var(--c-line)">
          <div class="text-sm font-semibold text-slate-800 mb-1">Daily Inflow</div>
          <div class="text-[11px] text-slate-500 mb-3">Sum of Amount Credited per receipt date</div>
          <div style="height:240px"><canvas id="cBkDaily"></canvas></div>
        </div>
        <div class="card p-4" style="border:1px solid var(--c-line)">
          <div class="text-sm font-semibold text-slate-800 mb-1">Bank-wise Receipt Mix</div>
          <div class="text-[11px] text-slate-500 mb-3">Total credited per bank</div>
          <div style="height:240px"><canvas id="cBkBank"></canvas></div>
        </div>
      </div>
      <div class="scroll-x">
        <div style="max-height:240px;overflow-y:auto;border:1px solid var(--c-line);border-radius:10px;">
        <table class="w-full">
          <thead style="position:sticky;top:0;z-index:3;background:#fafbff;">
            <tr>
              <th>Receipt Date</th><th>CID</th><th>Company</th><th>Bank</th><th>BU</th><th>Narration</th><th class="text-right">Amount Credited</th><th>Status</th><th>Valyx</th>
            </tr>
          </thead>
          <tbody id="bankBody"></tbody>
        </table>
        </div>
      </div>
    </section>

    <!-- ===== FOLLOW-UPS anchor ===== -->
    <div id="followups-anchor" data-section="followups"></div>

    <section class="card p-4 space-y-3" data-section="followups">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">📧 Follow-up Emails — Outstanding Reminders</div>
          <div class="text-[11px] text-slate-500">Filter Status = Open · Invoice Type = INV · Sender ar@gofynd.com · BCC sainathgosika@gofynd.com</div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <div class="flex items-center gap-1 chip" style="padding:4px 8px;background:#fff;border:1px solid #cbd5e1;" title="Template applied to every preview and send below">
            <span class="text-[11px] text-slate-500">Template:</span>
            <select id="fuTemplate" class="text-[12px] outline-none bg-transparent" style="min-width:170px;padding:2px 4px">
              <option value="">Default (Outstanding)</option>
            </select>
            <button id="fuManageTpl" class="text-[11px] text-blue-600 hover:underline" title="Add, edit or delete shared templates">⚙ Manage</button>
          </div>
          <button id="fuBuild" class="chip" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent);">🔍 Build Preview</button>
          <button id="fuDownloadXls" class="chip" disabled title="Download outstanding list for checked customers">📥 Download Excel</button>
          <button id="fuPreviewFirst" class="chip" disabled title="Preview the first checked email">👁 Preview First Email</button>
          <button id="fuSend" class="chip" disabled style="background:#15803d;color:#fff;border-color:#15803d;">📧 Send to <span id="fuSendCount">0</span></button>
        </div>
      </div>
      <div class="grid md:grid-cols-3 gap-3">
        <div><div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Regions</div><div id="fuMSBU"></div></div>
        <div><div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Customers (optional)</div><div id="fuMSCust"></div></div>
        <div class="flex items-end"><label class="text-[12px] text-slate-600 flex items-center gap-2"><input type="checkbox" id="fuForce" class="rounded"> Force resend (override 24h cooldown)</label></div>
      </div>
      <div id="fuStatusBar" class="text-[11px] text-slate-500"></div>
      <div class="overflow-x-auto rounded-lg border border-slate-200">
        <table class="w-full text-[12px]">
          <thead class="bg-slate-50">
            <tr>
              <th class="px-3 py-2 text-left"><input type="checkbox" id="fuCheckAll"></th>
              <th class="px-3 py-2 text-left">CID</th>
              <th class="px-3 py-2 text-left">Customer</th>
              <th class="px-3 py-2 text-left">Region</th>
              <th class="px-3 py-2 text-left">To Email</th>
              <th class="px-3 py-2 text-right">Open Inv</th>
              <th class="px-3 py-2 text-right">Invoice Total</th>
              <th class="px-3 py-2 text-right">Outstanding</th>
              <th class="px-3 py-2 text-right">Oldest Days</th>
              <th class="px-3 py-2 text-left">Status</th>
              <th class="px-3 py-2 text-left">Action</th>
            </tr>
          </thead>
          <tbody id="fuTbody"><tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">Pick a Region (or Customer) above and click <b>Build Preview</b>.</td></tr></tbody>
        </table>
      </div>
    </section>

    <!-- Preview / Send modal -->
    <div id="fuModal" class="fu-modal" style="display:none">
      <div class="fu-modal-shell">
        <div class="fu-modal-head">
          <div>
            <div class="text-sm font-semibold text-slate-800" id="fuModalTitle">Email Preview</div>
            <div class="text-[11px] text-slate-500" id="fuModalSub"></div>
          </div>
          <button id="fuModalClose" class="chip">✕ Close</button>
        </div>
        <div class="fu-modal-body" id="fuModalBody"></div>
        <div class="fu-modal-foot">
          <div class="text-[11px] text-slate-500" id="fuModalMeta"></div>
          <div class="flex gap-2">
            <button id="fuModalCancel" class="chip">Cancel</button>
            <button id="fuModalConfirm" class="chip" style="background:#15803d;color:#fff;border-color:#15803d;">📧 Confirm &amp; Send</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== Manage Email Templates modal (shared pool) ===== -->
    <div id="tplModal" class="fu-modal" style="display:none">
      <div class="fu-modal-shell" style="max-width:1100px">
        <div class="fu-modal-head">
          <div>
            <div class="text-sm font-semibold text-slate-800">📝 Manage Email Templates</div>
            <div class="text-[11px] text-slate-500">Shared with every collector. Mark one as <b>Default</b> to use it for plain previews. Supports tokens: <span id="tplTokenHint" class="font-mono"></span></div>
          </div>
          <button id="tplModalClose" class="chip">✕ Close</button>
        </div>
        <div class="fu-modal-body" style="padding:0">
          <div class="grid" style="grid-template-columns:280px 1fr;min-height:480px">
            <!-- List -->
            <div style="border-right:1px solid #e2e8f0;padding:12px;background:#f8fafc">
              <button id="tplNew" class="chip w-full mb-2" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent)">＋ New Template</button>
              <div id="tplList" class="space-y-1 text-[12px]"><div class="text-slate-500">Loading…</div></div>
            </div>
            <!-- Editor -->
            <div style="padding:14px;overflow:auto">
              <div id="tplEditorEmpty" class="text-[12px] text-slate-500 mt-6 text-center">Pick a template on the left, or click <b>＋ New Template</b> to create one.</div>
              <div id="tplEditor" style="display:none" class="space-y-3">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <label class="text-[12px] text-slate-700">
                    <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Template Name <span style="color:#b91c1c">*</span></div>
                    <input id="tplName" class="w-full border border-slate-300 rounded px-2 py-1.5 text-[12px]" placeholder="e.g. Escalation - 60+ days"/>
                  </label>
                  <label class="text-[12px] text-slate-700 flex items-end gap-3">
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="tplIsDefault"> <span>Set as <b>Default</b></span></label>
                    <label class="flex items-center gap-1.5"><input type="checkbox" id="tplIncludeBank" checked> <span>Include Bank details block</span></label>
                  </label>
                </div>
                <label class="text-[12px] text-slate-700 block">
                  <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Subject</div>
                  <input id="tplSubject" class="w-full border border-slate-300 rounded px-2 py-1.5 text-[12px]" placeholder="Outstanding Invoice(s) - {{customer_name}}"/>
                </label>
                <label class="text-[12px] text-slate-700 block">
                  <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Greeting</div>
                  <input id="tplGreeting" class="w-full border border-slate-300 rounded px-2 py-1.5 text-[12px]" placeholder="Hi Team,"/>
                </label>
                <label class="text-[12px] text-slate-700 block">
                  <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Body — above invoice table (HTML allowed)</div>
                  <textarea id="tplAbove" rows="4" class="w-full border border-slate-300 rounded px-2 py-1.5 text-[12px] font-mono" placeholder="Please find below the outstanding invoices..."></textarea>
                </label>
                <div class="text-[11px] text-slate-500 italic px-2 py-1.5 bg-slate-50 border-l-2 border-slate-300">📋 Invoice table is auto-inserted here (same layout as the preview you saw — Invoice No, Channel, Type, Dates, Amounts, Days overdue, Totals).</div>
                <label class="text-[12px] text-slate-700 block">
                  <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Body — below invoice table (HTML allowed)</div>
                  <textarea id="tplBelow" rows="3" class="w-full border border-slate-300 rounded px-2 py-1.5 text-[12px] font-mono" placeholder="Kindly arrange payment and share UTR..."></textarea>
                </label>
                <label class="text-[12px] text-slate-700 block">
                  <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Sign-off (HTML allowed)</div>
                  <textarea id="tplSig" rows="3" class="w-full border border-slate-300 rounded px-2 py-1.5 text-[12px] font-mono" placeholder="Regards,&#10;{{collector_name}}&#10;Accounts Receivable, Fynd"></textarea>
                </label>
                <div class="flex items-center justify-between gap-2 pt-1 border-t border-slate-200">
                  <button id="tplDelete" class="chip" style="background:#fee2e2;color:#b91c1c;border-color:#fecaca;display:none">🗑 Delete</button>
                  <div class="flex gap-2 ml-auto">
                    <button id="tplCancel" class="chip">Cancel</button>
                    <button id="tplSave" class="chip" style="background:#15803d;color:#fff;border-color:#15803d">💾 Save Template</button>
                  </div>
                </div>
                <div id="tplSaveMsg" class="text-[11px]"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== ACTIVITY LOG anchor ===== -->
    <div id="activity-anchor" data-section="activity"></div>

    <section class="card p-4 space-y-3" data-section="activity">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">📋 Activity Log</div>
          <div class="text-[11px] text-slate-500">Use the tabs below to switch between email send activity and worklist notes &amp; follow-ups. Both support collector-wise download.</div>
        </div>
      </div>

      <!-- TAB BAR -->
      <div class="flex items-center gap-1 border-b border-slate-200" role="tablist" id="alTabBar">
        <button type="button" class="al-tab al-tab-active" data-al-tab="email" role="tab" aria-selected="true">📨 Email Sends</button>
        <button type="button" class="al-tab" data-al-tab="worklist" role="tab" aria-selected="false">📒 Worklist Activity</button>
      </div>

      <!-- ==================== TAB PANE: EMAIL SENDS ==================== -->
      <div id="alTabPaneEmail" class="al-tab-pane space-y-3" role="tabpanel">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div class="text-[12px] font-semibold text-slate-700">📨 Email Sends · <span class="text-[11px] font-normal text-slate-500">reads <span class="font-mono">Email_Log</span> sheet</span></div>
        <div class="flex items-center gap-2">
          <input id="alFrom" type="date" class="chip" style="padding:6px 10px"/>
          <input id="alTo" type="date" class="chip" style="padding:6px 10px"/>
          <button id="alRefresh" class="chip" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent);">↻ Refresh</button>
        </div>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-2" id="alKpis">
        <div class="kpi"><div class="kpi-l">Total Sends</div><div class="kpi-v" id="alK1">—</div></div>
        <div class="kpi"><div class="kpi-l">Successful</div><div class="kpi-v" id="alK2" style="color:#15803d">—</div></div>
        <div class="kpi"><div class="kpi-l">Failed</div><div class="kpi-v" id="alK3" style="color:#b91c1c">—</div></div>
        <div class="kpi"><div class="kpi-l">Unique Customers</div><div class="kpi-v" id="alK4">—</div></div>
        <div class="kpi"><div class="kpi-l">Outstanding Chased</div><div class="kpi-v" id="alK5">—</div></div>
      </div>
      <div class="grid md:grid-cols-2 gap-3">
        <div>
          <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Monthly Report</div>
          <div class="flex items-center gap-2">
            <input id="alMonth" type="month" class="chip" style="padding:6px 10px"/>
            <button id="alGenMonth" class="chip" style="background:#15803d;color:#fff;border-color:#15803d;">📊 Generate Monthly Report</button>
          </div>
          <div id="alMonthlyOut" class="mt-2 text-[12px] text-slate-600"></div>
        </div>
        <div>
          <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Per-Month Breakdown</div>
          <div id="alMonthlyTable" class="text-[12px]"></div>
        </div>
      </div>
      <div class="overflow-x-auto rounded-lg border border-slate-200">
        <table class="w-full text-[12px]">
          <thead class="bg-slate-50"><tr>
            <th class="px-3 py-2 text-left">Timestamp</th>
            <th class="px-3 py-2 text-left">CID</th>
            <th class="px-3 py-2 text-left">Customer</th>
            <th class="px-3 py-2 text-left">BU</th>
            <th class="px-3 py-2 text-left">To</th>
            <th class="px-3 py-2 text-left">Sender Used</th>
            <th class="px-3 py-2 text-right">Invoices</th>
            <th class="px-3 py-2 text-right">Outstanding</th>
            <th class="px-3 py-2 text-left">Status</th>
            <th class="px-3 py-2 text-left">Error / Note</th>
          </tr></thead>
          <tbody id="alTbody"><tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">Click Refresh to load activity.</td></tr></tbody>
        </table>
      </div>
      </div><!-- /alTabPaneEmail -->

      <!-- ==================== TAB PANE: WORKLIST ACTIVITY ==================== -->
      <div id="alTabPaneWorklist" class="al-tab-pane" role="tabpanel" style="display:none">
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div class="text-[12px] font-semibold text-slate-700">📒 Worklist Activity · Notes &amp; Follow-ups</div>
            <div class="text-[11px] text-slate-500">Reads the <span class="font-mono">Notes</span> sheet via <span class="font-mono">dailyReport</span> · filterable by collector / outcome / search · downloadable as Excel</div>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <select id="walRange" class="chip" style="padding:6px 10px">
              <option value="today">Today</option>
              <option value="7d">Last 7 days</option>
              <option value="month" selected>This Month</option>
              <option value="all">All</option>
              <option value="custom">Custom…</option>
            </select>
            <input id="walFrom" type="date" class="chip" style="padding:6px 10px;display:none"/>
            <input id="walTo"   type="date" class="chip" style="padding:6px 10px;display:none"/>
            <select id="walCollector" class="chip" style="padding:6px 10px;min-width:160px">
              <option value="">All collectors</option>
            </select>
            <select id="walOutcome" class="chip" style="padding:6px 10px;min-width:140px">
              <option value="">All outcomes</option>
              <option>Promise to Pay</option>
              <option>Reminder sent</option>
              <option>Disputed</option>
              <option>Escalated</option>
              <option>Awaiting Approval</option>
              <option>No response</option>
              <option>Other</option>
            </select>
            <input id="walSearch" type="text" class="chip" style="padding:6px 10px;min-width:180px" placeholder="Search CID / customer / note…"/>
            <button id="walRefresh" class="chip" title="Run the filters and refresh results" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent);">🔍 Search</button>
            <button id="walReset" class="chip" title="Clear all filters and reset to defaults" style="background:#fff;color:#475569;border-color:#cbd5e1">↺ Reset</button>
            <button id="walExcel" class="chip" style="background:#15803d;color:#fff;border-color:#15803d">⬇ Download Excel</button>
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-5 gap-2 mt-3">
          <div class="kpi"><div class="kpi-l">Notes Logged</div><div class="kpi-v" id="walK1">—</div></div>
          <div class="kpi"><div class="kpi-l">Unique Customers</div><div class="kpi-v" id="walK2">—</div></div>
          <div class="kpi"><div class="kpi-l">Collectors Active</div><div class="kpi-v" id="walK3">—</div></div>
          <div class="kpi"><div class="kpi-l">Promises to Pay</div><div class="kpi-v" id="walK4" style="color:#15803d">—</div></div>
          <div class="kpi"><div class="kpi-l">P2P Committed</div><div class="kpi-v" id="walK5">—</div></div>
        </div>

        <div class="overflow-x-auto rounded-lg border border-slate-200 mt-3" style="max-height:520px;overflow-y:auto">
          <table class="w-full text-[12px]">
            <thead class="bg-slate-50 sticky top-0">
              <tr class="text-left text-slate-600">
                <th class="px-3 py-2">Date</th>
                <th class="px-3 py-2">Collector</th>
                <th class="px-3 py-2">CID</th>
                <th class="px-3 py-2">Customer</th>
                <th class="px-3 py-2">Invoice</th>
                <th class="px-3 py-2 text-right">Outstanding</th>
                <th class="px-3 py-2">Note</th>
                <th class="px-3 py-2">Outcome</th>
                <th class="px-3 py-2">Next Follow-up</th>
                <th class="px-3 py-2 text-right">P2P Amount</th>
                <th class="px-3 py-2">P2P Date</th>
              </tr>
            </thead>
            <tbody id="walTbody">
              <tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">Click Search to load worklist activity.</td></tr>
            </tbody>
          </table>
        </div>

        <div class="text-[11px] text-slate-500 mt-2" id="walRowCount"></div>
      </div>
    </section>

    <!-- ================================================================
         CUSTOMER POCs (Contacts) — CRUD + Bulk Upload / Download
         Anchored inside AR Activity group. One row per contact person so
         a customer can have 1..N POCs with their own name, role, email,
         phone, priority. Feeds the follow-up sender (readContacts_ prefers
         this tab over the legacy Customer_Contacts sheet).
         ================================================================ -->
    <div id="pocs-anchor" data-section="pocs"></div>
    <section class="card p-4 space-y-3" data-section="pocs" style="display:none">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">📇 Contacts &amp; Stakeholders</div>
          <div class="text-[11px] text-slate-500">Customer POCs + Fynd internal stakeholders in one view · One click "Add Contact" registers both for the same CID · Customer Primary→To/CC→Cc/Escalation-only · Internal → BCC (Escalation → BCC on escalation stage only)</div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <button id="pocAddBtn" class="chip active">➕ Add Contact</button>
          <button id="pocDownloadBtn" class="chip">⬇ Download Excel</button>
          <label class="chip" style="cursor:pointer">
            ⬆ Bulk Upload
            <input type="file" id="pocUploadInput" accept=".xlsx,.xls,.csv" style="display:none" />
          </label>
          <button id="pocTemplateBtn" class="chip">📄 Download Template</button>
          <button id="pocMigrateBtn" class="chip" title="Import legacy Customer_Contacts rows from the sheet. Safe to re-run — matches on (CID, email). @gofynd.com CCs route to Internal Stakeholders.">🔁 Migrate legacy</button>
          <button id="pocRefreshBtn" class="chip">🔄</button>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-wrap text-[12px]">
        <input id="pocSearch" placeholder="Search CID, name, email, phone…" class="border border-slate-300 rounded px-2 py-1 text-[12px]" style="min-width:240px" />
        <select id="pocFilterType" class="border border-slate-300 rounded px-2 py-1 text-[12px]">
          <option value="">All types</option>
          <option value="customer">Customer contact</option>
          <option value="internal">Internal stakeholder</option>
        </select>
        <select id="pocFilterPriority" class="border border-slate-300 rounded px-2 py-1 text-[12px]">
          <option value="">All priorities</option>
          <option value="Primary">Primary</option>
          <option value="CC">CC</option>
          <option value="Escalation">Escalation</option>
        </select>
        <select id="pocFilterActive" class="border border-slate-300 rounded px-2 py-1 text-[12px]">
          <option value="">All (active + inactive)</option>
          <option value="Y" selected>Active only</option>
          <option value="N">Inactive only</option>
        </select>
        <span id="pocCount" class="text-slate-500"></span>
      </div>
      <div class="overflow-auto max-h-[560px] border border-slate-100 rounded">
        <table class="w-full text-[12px]">
          <thead class="bg-slate-50 sticky top-0">
            <tr>
              <th class="px-3 py-2 text-left">Type</th>
              <th class="px-3 py-2 text-left">CID</th>
              <th class="px-3 py-2 text-left">Customer</th>
              <th class="px-3 py-2 text-left">Contact</th>
              <th class="px-3 py-2 text-left">Role</th>
              <th class="px-3 py-2 text-left">Email</th>
              <th class="px-3 py-2 text-left">Phone</th>
              <th class="px-3 py-2 text-left">Priority</th>
              <th class="px-3 py-2 text-center">Active</th>
              <th class="px-3 py-2 text-left">Notes</th>
              <th class="px-3 py-2 text-center">Actions</th>
            </tr>
          </thead>
          <tbody id="pocTbody">
            <tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
          </tbody>
        </table>
      </div>
      <div id="pocStatusBar" class="text-[11px] text-slate-500"></div>
    </section>

    <!-- Unified Add-Contact modal — pick a CID ONCE, register any number of
         customer emails AND internal (Fynd) stakeholders in a single save. -->
    <div id="pocModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:1000;align-items:flex-start;justify-content:center;padding-top:30px">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4" style="max-height:94vh;overflow-y:auto">
        <div class="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div>
            <div class="font-semibold text-slate-800" id="pocModalTitle">Add Contact</div>
            <div class="text-[11px] text-slate-500">One CID · N customer emails · N internal stakeholders · single save</div>
          </div>
          <button id="pocModalClose" class="text-slate-400 hover:text-slate-700">×</button>
        </div>
        <div class="px-5 py-4 space-y-3 text-[13px]">
          <!-- Customer picker (top, picked ONCE) -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">CID <span class="text-red-500">*</span></label>
              <input id="pmCid" list="pmCidList" class="w-full border border-slate-300 rounded px-2 py-1.5 font-mono text-[12px]" />
              <datalist id="pmCidList"></datalist>
            </div>
            <div>
              <label class="block text-slate-600 mb-1">Customer Name</label>
              <input id="pmCustomerName" class="w-full border border-slate-300 rounded px-2 py-1.5" placeholder="Auto-filled from CID" />
            </div>
          </div>

          <!-- Section A: Customer emails (external — actual customer POCs) -->
          <div class="border border-slate-200 rounded p-3 bg-slate-50/40">
            <div class="flex items-center justify-between mb-2">
              <div>
                <div class="text-[12px] font-semibold text-slate-700">📧 Customer Contacts</div>
                <div class="text-[10px] text-slate-500">The customer's people · Primary → To · CC → Cc · Escalation → escalation-only stage</div>
              </div>
              <button id="pmAddEmailBtn" class="chip">+ Add customer email</button>
            </div>
            <div id="pmEmailsWrap" class="space-y-2"></div>
            <div id="pmEmailsEmpty" class="text-[11px] text-slate-400 italic mt-1" style="display:none">No customer emails yet — click "+ Add customer email" to add one.</div>
          </div>

          <!-- Section B: Internal stakeholders (Fynd owners — BCC'd on emails) -->
          <div class="border border-slate-200 rounded p-3 bg-amber-50/40">
            <div class="flex items-center justify-between mb-2">
              <div>
                <div class="text-[12px] font-semibold text-slate-700">👥 Internal Stakeholders (Fynd)</div>
                <div class="text-[10px] text-slate-500">Our owners · BCC'd on every follow-up · Escalation-priority BCC'd only on escalation stage</div>
              </div>
              <button id="pmAddStakeBtn" class="chip">+ Add stakeholder email</button>
            </div>
            <div id="pmStakeWrap" class="space-y-2"></div>
            <div id="pmStakeEmpty" class="text-[11px] text-slate-400 italic mt-1" style="display:none">No stakeholder emails yet — click "+ Add stakeholder email" to add one.</div>
          </div>

          <div id="pmError" class="text-[12px] text-red-600"></div>
        </div>
        <div class="px-5 py-3 border-t border-slate-200 flex justify-end gap-2">
          <button id="pocModalCancel" class="chip">Cancel</button>
          <button id="pocModalSave" class="chip active">Save Contact</button>
        </div>
      </div>
    </div>

    <!-- Row template — cloned by pocAddEmailRow(). Slimmed down to the four
         fields the user actually fills: Email, Name, Phone, Priority. Role
         + Notes + Active are still round-tripped as hidden inputs so
         existing records preserve those values on edit; new rows default
         to Active=Y with empty role/notes. -->
    <template id="pmEmailRowTpl">
      <div class="pm-email-row border border-slate-200 rounded p-2 bg-white space-y-2" data-original-email="">
        <div class="grid grid-cols-12 gap-2 items-end">
          <div class="col-span-4">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Email <span class="text-red-500">*</span></label>
            <input class="pm-email w-full border border-slate-300 rounded px-2 py-1 text-[12px]" type="email" placeholder="name@company.com" />
          </div>
          <div class="col-span-3">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Name</label>
            <input class="pm-contact w-full border border-slate-300 rounded px-2 py-1 text-[12px]" placeholder="e.g. Rahul Sharma" />
          </div>
          <div class="col-span-2">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Phone</label>
            <input class="pm-phone w-full border border-slate-300 rounded px-2 py-1 text-[12px]" placeholder="+91-9876543210" />
          </div>
          <div class="col-span-2">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Priority</label>
            <select class="pm-priority w-full border border-slate-300 rounded px-2 py-1 text-[12px]">
              <option value="Primary">Primary → To</option>
              <option value="CC">CC → Cc</option>
              <option value="Escalation">Escalation-only</option>
            </select>
          </div>
          <div class="col-span-1 text-right">
            <button class="pm-del-row chip" title="Remove this email">✕</button>
          </div>
          <!-- Hidden round-trip inputs — kept so _pmCollectRows() can still
               preserve Role/Active/Notes from the existing record on edit. -->
          <input class="pm-active" type="hidden" value="Y" />
          <input class="pm-role" type="hidden" value="" />
          <input class="pm-notes" type="hidden" value="" />
        </div>
      </div>
    </template>

    <!-- POC Bulk-upload preview modal -->
    <div id="pocPreviewModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:1000;align-items:flex-start;justify-content:center;padding-top:40px">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4" style="max-height:90vh;overflow-y:auto">
        <div class="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div class="font-semibold text-slate-800">Bulk Upload — Preview</div>
          <button id="pocPreviewClose" class="text-slate-400 hover:text-slate-700">×</button>
        </div>
        <div class="px-5 py-4 space-y-3 text-[12px]">
          <div id="pocPreviewSummary" class="text-slate-700"></div>
          <div class="overflow-auto max-h-[420px] border border-slate-100 rounded">
            <table class="w-full text-[11px]">
              <thead class="bg-slate-50 sticky top-0"><tr>
                <th class="px-2 py-1 text-left">Row</th>
                <th class="px-2 py-1 text-left">Target</th>
                <th class="px-2 py-1 text-left">CID</th>
                <th class="px-2 py-1 text-left">Email</th>
                <th class="px-2 py-1 text-left">Action</th>
                <th class="px-2 py-1 text-left">Status</th>
              </tr></thead>
              <tbody id="pocPreviewBody"></tbody>
            </table>
          </div>
        </div>
        <div class="px-5 py-3 border-t border-slate-200 flex justify-end gap-2">
          <button id="pocPreviewCancel" class="chip">Cancel</button>
          <button id="pocPreviewCommit" class="chip active">Commit to Sheet</button>
        </div>
      </div>
    </div>

    <!-- ================================================================
         INTERNAL STAKEHOLDERS — Fynd owners per CID
         Mirror of the Customer POCs feature but tracks *our* owners
         (Account Managers, KAMs, backup owners). Their consolidated view
         is BCC'd on every customer follow-up (Primary+CC always, Escalation
         only on escalation-stage emails).

         The standalone on-page section was removed once the "Add Contact"
         modal covered both kinds — internal stakeholders are now rendered
         INSIDE the top "Contacts & Stakeholders" card alongside customer
         POCs (differentiated by the Type column). The backend routes,
         hidden bulk-upload plumbing, edit modal + row template below are
         retained so the merged table's Edit/Delete flows still work.

         Kept-for-compat anchor: deep links to #istake-anchor still land
         on the (merged) Contacts page.
         ================================================================ -->
    <div id="istake-anchor" data-section="pocs" style="display:none"></div>

    <!-- IS Add/Edit modal — one customer, N email rows -->
    <div id="isModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:1000;align-items:flex-start;justify-content:center;padding-top:40px">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4" style="max-height:92vh;overflow-y:auto">
        <div class="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div class="font-semibold text-slate-800" id="isModalTitle">Add Stakeholder</div>
          <button id="isModalClose" class="text-slate-400 hover:text-slate-700">×</button>
        </div>
        <div class="px-5 py-4 space-y-3 text-[13px]">
          <!-- Customer section (picked ONCE) -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">CID <span class="text-red-500">*</span></label>
              <input id="imCid" list="imCidList" class="w-full border border-slate-300 rounded px-2 py-1.5 font-mono text-[12px]" />
              <datalist id="imCidList"></datalist>
            </div>
            <div>
              <label class="block text-slate-600 mb-1">Customer Name</label>
              <input id="imCustomerName" class="w-full border border-slate-300 rounded px-2 py-1.5" placeholder="Auto-filled from CID" />
            </div>
          </div>

          <!-- Emails — one row per stakeholder, each with own priority -->
          <div class="border border-slate-200 rounded p-3 bg-slate-50/40">
            <div class="flex items-center justify-between mb-2">
              <div class="text-[12px] font-semibold text-slate-700">📧 Internal owners for this customer</div>
              <button id="imAddEmailBtn" class="chip">+ Add another email</button>
            </div>
            <div id="imEmailsWrap" class="space-y-2"></div>
            <div class="text-[11px] text-slate-500 mt-2">
              Primary + CC → BCC on every follow-up · Escalation → BCC only on escalation stage. One save creates one row per email.
            </div>
          </div>

          <div id="imError" class="text-[12px] text-red-600"></div>
        </div>
        <div class="px-5 py-3 border-t border-slate-200 flex justify-end gap-2">
          <button id="isModalCancel" class="chip">Cancel</button>
          <button id="isModalSave" class="chip active">Save Stakeholder</button>
        </div>
      </div>
    </div>

    <!-- Row template — cloned by isAddEmailRow() -->
    <template id="imEmailRowTpl">
      <div class="im-email-row border border-slate-200 rounded p-2 bg-white space-y-2" data-original-email="">
        <div class="grid grid-cols-12 gap-2 items-end">
          <div class="col-span-4">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Email <span class="text-red-500">*</span></label>
            <input class="im-email w-full border border-slate-300 rounded px-2 py-1 text-[12px]" type="email" placeholder="name@gofynd.com" />
          </div>
          <div class="col-span-2">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Priority</label>
            <select class="im-priority w-full border border-slate-300 rounded px-2 py-1 text-[12px]">
              <option value="Primary">Primary → BCC</option>
              <option value="CC">CC → BCC</option>
              <option value="Escalation">Escalation-only</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Active</label>
            <select class="im-active w-full border border-slate-300 rounded px-2 py-1 text-[12px]">
              <option value="Y">Yes</option>
              <option value="N">No</option>
            </select>
          </div>
          <div class="col-span-3">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Stakeholder name</label>
            <input class="im-contact w-full border border-slate-300 rounded px-2 py-1 text-[12px]" placeholder="e.g. Priya Nair" />
          </div>
          <div class="col-span-1 text-right">
            <button class="im-del-row chip" title="Remove this email">✕</button>
          </div>
        </div>
        <div class="grid grid-cols-12 gap-2">
          <div class="col-span-3">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Role</label>
            <input class="im-role w-full border border-slate-300 rounded px-2 py-1 text-[12px]" placeholder="e.g. Account Manager" />
          </div>
          <div class="col-span-3">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Phone</label>
            <input class="im-phone w-full border border-slate-300 rounded px-2 py-1 text-[12px]" placeholder="+91-9876543210" />
          </div>
          <div class="col-span-6">
            <label class="block text-slate-600 mb-0.5 text-[11px]">Notes</label>
            <input class="im-notes w-full border border-slate-300 rounded px-2 py-1 text-[12px]" />
          </div>
        </div>
      </div>
    </template>

    <!-- IS Bulk-upload preview modal -->
    <div id="isPreviewModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:1000;align-items:flex-start;justify-content:center;padding-top:40px">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4" style="max-height:90vh;overflow-y:auto">
        <div class="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div class="font-semibold text-slate-800">Bulk Upload — Preview</div>
          <button id="isPreviewClose" class="text-slate-400 hover:text-slate-700">×</button>
        </div>
        <div class="px-5 py-4 space-y-3 text-[12px]">
          <div id="isPreviewSummary" class="text-slate-700"></div>
          <div class="overflow-auto max-h-[420px] border border-slate-100 rounded">
            <table class="w-full text-[11px]">
              <thead class="bg-slate-50 sticky top-0"><tr>
                <th class="px-2 py-1 text-left">Row</th>
                <th class="px-2 py-1 text-left">CID</th>
                <th class="px-2 py-1 text-left">Email</th>
                <th class="px-2 py-1 text-left">Action</th>
                <th class="px-2 py-1 text-left">Status</th>
              </tr></thead>
              <tbody id="isPreviewBody"></tbody>
            </table>
          </div>
        </div>
        <div class="px-5 py-3 border-t border-slate-200 flex justify-end gap-2">
          <button id="isPreviewCancel" class="chip">Cancel</button>
          <button id="isPreviewCommit" class="chip active">Commit to Sheet</button>
        </div>
      </div>
    </div>

    <!-- ================================================================
         WORKFLOWS — scheduled follow-up rules
         Anchored inside AR Activity group. Backend evaluates each active
         workflow via a daily time trigger; approve=review workflows stage
         rows in a Draft Queue for admin sign-off before send.
         ================================================================ -->
    <div id="workflows-anchor" data-section="workflows"></div>
    <section class="card p-4 space-y-3" data-section="workflows" style="display:none">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">⚙ Follow-up Workflows</div>
          <div class="text-[11px] text-slate-500">Rules that auto-send reminders on aging tiers or a fixed schedule · Daily trigger enforces send window + frequency cap</div>
        </div>
        <div class="flex items-center gap-2">
          <button id="wfAddBtn" class="chip active">➕ New Workflow</button>
          <button id="wfRefreshBtn" class="chip">🔄</button>
        </div>
      </div>
      <div class="flex items-center gap-2 text-[12px]">
        <button class="chip active" data-wf-tab="rules">Rules</button>
        <button class="chip" data-wf-tab="queue">Draft Queue</button>
        <span id="wfCount" class="text-slate-500 ml-2"></span>
      </div>
      <!-- Rules tab -->
      <div id="wfPaneRules">
        <div class="overflow-auto max-h-[540px] border border-slate-100 rounded">
          <table class="w-full text-[12px]">
            <thead class="bg-slate-50 sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left">Name</th>
                <th class="px-3 py-2 text-left">Region</th>
                <th class="px-3 py-2 text-left">Trigger</th>
                <th class="px-3 py-2 text-left">Template</th>
                <th class="px-3 py-2 text-left">Window</th>
                <th class="px-3 py-2 text-left">Cap</th>
                <th class="px-3 py-2 text-left">Approve</th>
                <th class="px-3 py-2 text-center">Active</th>
                <th class="px-3 py-2 text-left">Last Run</th>
                <th class="px-3 py-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody id="wfTbody">
              <tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <!-- Queue tab -->
      <div id="wfPaneQueue" style="display:none">
        <div class="overflow-auto max-h-[540px] border border-slate-100 rounded">
          <table class="w-full text-[12px]">
            <thead class="bg-slate-50 sticky top-0"><tr>
              <th class="px-3 py-2 text-left">Enqueued</th>
              <th class="px-3 py-2 text-left">Workflow</th>
              <th class="px-3 py-2 text-left">CID</th>
              <th class="px-3 py-2 text-left">Customer</th>
              <th class="px-3 py-2 text-left">Region</th>
              <th class="px-3 py-2 text-right">Inv</th>
              <th class="px-3 py-2 text-right">Outstanding</th>
              <th class="px-3 py-2 text-right">Oldest</th>
              <th class="px-3 py-2 text-left">Status</th>
              <th class="px-3 py-2 text-center">Actions</th>
            </tr></thead>
            <tbody id="wfQueueTbody">
              <tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">Empty queue.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div id="wfStatusBar" class="text-[11px] text-slate-500"></div>
    </section>

    <!-- Workflow editor modal -->
    <div id="wfModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:1000;align-items:flex-start;justify-content:center;padding-top:40px">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4" style="max-height:92vh;overflow-y:auto">
        <div class="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div class="font-semibold text-slate-800" id="wfModalTitle">New Workflow</div>
          <button id="wfModalClose" class="text-slate-400 hover:text-slate-700">×</button>
        </div>
        <div class="px-5 py-4 space-y-3 text-[13px]">
          <input type="hidden" id="wfId" />
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">Name <span class="text-red-500">*</span></label>
              <input id="wfName" class="w-full border border-slate-300 rounded px-2 py-1.5" placeholder="e.g. 60-day escalation" />
            </div>
            <div>
              <label class="block text-slate-600 mb-1">Region</label>
              <select id="wfRegion" class="w-full border border-slate-300 rounded px-2 py-1.5"><option value="">All regions</option></select>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">Trigger Type</label>
              <select id="wfTriggerType" class="w-full border border-slate-300 rounded px-2 py-1.5">
                <option value="aging">Aging tier (days overdue ≥ N)</option>
                <option value="cadence">Cadence (N days since last send)</option>
                <option value="schedule">Fixed schedule (every run)</option>
              </select>
            </div>
            <div>
              <label class="block text-slate-600 mb-1" id="wfTriggerValueLabel">Days overdue (≥)</label>
              <input id="wfTriggerValue" type="number" class="w-full border border-slate-300 rounded px-2 py-1.5" value="30" min="0" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">Template</label>
              <select id="wfTemplate" class="w-full border border-slate-300 rounded px-2 py-1.5"><option value="">(Default outstanding statement)</option></select>
            </div>
            <div>
              <label class="block text-slate-600 mb-1">Frequency Cap (days)</label>
              <input id="wfFreqCap" type="number" class="w-full border border-slate-300 rounded px-2 py-1.5" value="7" min="0" />
            </div>
          </div>
          <!-- Schedule: Frequency + Start Time. Frequency selects which
               conditional block below is shown (Weekly → day-of-week,
               Monthly → day-of-month, Custom → date range + days).
               Start/End Date fences are always visible so any workflow can
               be run "once for a day" and auto-expire. -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">Frequency</label>
              <select id="wfFrequency" class="w-full border border-slate-300 rounded px-2 py-1.5">
                <option value="daily">Daily</option>
                <option value="weekly" selected>Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div>
              <label class="block text-slate-600 mb-1">Start Time (HH:mm IST)</label>
              <input id="wfWindowStart" type="time" class="w-full border border-slate-300 rounded px-2 py-1.5" value="10:00" />
            </div>
          </div>
          <!-- Weekly (or Custom) cadence: pick specific weekdays -->
          <div id="wfDaysWrap">
            <label class="block text-slate-600 mb-1">Days of week</label>
            <div id="wfDaysChecks" class="flex flex-wrap gap-3 text-[12px]">
              <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-day rounded" data-day="Mon" checked /> Mon</label>
              <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-day rounded" data-day="Tue" checked /> Tue</label>
              <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-day rounded" data-day="Wed" checked /> Wed</label>
              <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-day rounded" data-day="Thu" checked /> Thu</label>
              <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-day rounded" data-day="Fri" checked /> Fri</label>
              <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-day rounded" data-day="Sat" /> Sat</label>
              <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-day rounded" data-day="Sun" /> Sun</label>
            </div>
            <div id="wfDaysHint" class="text-[10px] text-slate-500 mt-1">Weekly fires on the checked days at Start Time. Custom uses these days within the date range below.</div>
          </div>
          <!-- Monthly cadence: single day-of-month number -->
          <div id="wfMonthWrap" style="display:none">
            <label class="block text-slate-600 mb-1">Day of month (1–31)</label>
            <input id="wfDayOfMonth" type="number" min="1" max="31" class="w-full border border-slate-300 rounded px-2 py-1.5" value="1" />
            <div class="text-[10px] text-slate-500 mt-1">Fires once per month on this date at Start Time. If a month has fewer days (e.g. Feb 30), the last day of the month is used.</div>
          </div>
          <!-- Custom cadence: mandatory Start/End Date range.
               For non-Custom frequencies these date inputs also act as an
               optional "run window" fence — leave blank for no expiry. -->
          <div id="wfDateRangeWrap" class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">Start Date <span id="wfStartDateReq" class="text-slate-400 text-[10px]">(optional)</span></label>
              <input id="wfStartDate" type="date" class="w-full border border-slate-300 rounded px-2 py-1.5" />
            </div>
            <div>
              <label class="block text-slate-600 mb-1">End Date <span id="wfEndDateReq" class="text-slate-400 text-[10px]">(optional)</span></label>
              <input id="wfEndDate" type="date" class="w-full border border-slate-300 rounded px-2 py-1.5" />
            </div>
            <div class="col-span-2 text-[10px] text-slate-500 -mt-2">Workflow only runs on/between these dates. Leave End Date blank for open-ended. Set End Date = Start Date to fire on exactly one day, then auto-stop.</div>
          </div>
          <!-- Recipient priorities — split by kind so you can pick which
               customer POCs (Primary/CC/Escalation) AND which internal
               stakeholders (Primary/CC/Escalation) get looped in. -->
          <div class="grid grid-cols-2 gap-3">
            <div class="border border-slate-200 rounded p-2 bg-slate-50/40">
              <div class="text-[12px] font-semibold text-slate-700 mb-1">📧 Customer recipients</div>
              <div class="flex flex-wrap gap-3 text-[12px]">
                <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-cust-pri rounded" data-pri="Primary" checked /> Primary → To</label>
                <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-cust-pri rounded" data-pri="CC" checked /> CC → Cc</label>
                <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-cust-pri rounded" data-pri="Escalation" /> Escalation</label>
              </div>
            </div>
            <div class="border border-slate-200 rounded p-2 bg-amber-50/40">
              <div class="text-[12px] font-semibold text-slate-700 mb-1">👥 Internal stakeholders (BCC)</div>
              <div class="flex flex-wrap gap-3 text-[12px]">
                <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-int-pri rounded" data-pri="Primary" checked /> Primary</label>
                <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-int-pri rounded" data-pri="CC" checked /> CC</label>
                <label class="inline-flex items-center gap-1"><input type="checkbox" class="wf-int-pri rounded" data-pri="Escalation" /> Escalation</label>
              </div>
            </div>
          </div>
          <!-- Approve mode stays on its own row -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">Approve Mode</label>
              <select id="wfApproveMode" class="w-full border border-slate-300 rounded px-2 py-1.5">
                <option value="auto">Auto — send immediately</option>
                <option value="review">Review — stage in Draft Queue</option>
              </select>
            </div>
            <div>
              <label class="block text-slate-600 mb-1">Customer scope</label>
              <select id="wfCustomerScope" class="w-full border border-slate-300 rounded px-2 py-1.5">
                <option value="all">All customers in region</option>
                <option value="include">Only these CIDs (allow-list)</option>
                <option value="exclude">All EXCEPT these CIDs (deny-list)</option>
              </select>
            </div>
          </div>
          <!-- Limit to specific customers — surfaces when scope != all.
               Accept a comma / newline separated list of CIDs so a workflow
               can be pinned to a shortlist of customers within a region. -->
          <div id="wfCidWrap" style="display:none">
            <label class="block text-slate-600 mb-1">Customer CIDs (comma or newline separated)</label>
            <textarea id="wfCidList" rows="2" class="w-full border border-slate-300 rounded px-2 py-1.5 text-[12px] font-mono" placeholder="e.g. 10023, 10047, 10099"></textarea>
            <div class="text-[10px] text-slate-500 mt-1">Only CIDs matching this list will trigger for this workflow. Leave blank to fall back to region-wide scope.</div>
          </div>
          <!-- Status supersedes the legacy Active checkbox: Active workflows
               fire automatically; Paused workflows are kept for later resume
               but skip auto-runs; Stopped workflows are dormant end-of-life. -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-600 mb-1">Status</label>
              <select id="wfStatus" class="w-full border border-slate-300 rounded px-2 py-1.5">
                <option value="active">Active — fires on schedule</option>
                <option value="paused">Paused — skip until resumed</option>
                <option value="stopped">Stopped — dormant</option>
              </select>
              <div class="text-[10px] text-slate-500 mt-1">Use Pause for temporary halts (holidays, incidents) — you can Resume from the workflow list.</div>
            </div>
            <div class="text-[11px] text-slate-500 self-end pb-1">💡 Manual "Run now" still fires paused/stopped workflows on demand.</div>
          </div>
          <div id="wfPreviewBox" class="text-[12px] text-slate-600 border border-slate-100 rounded p-2 bg-slate-50" style="display:none"></div>
          <div id="wfError" class="text-[12px] text-red-600"></div>
        </div>
        <div class="px-5 py-3 border-t border-slate-200 flex justify-between gap-2">
          <button id="wfPreviewBtn" class="chip">👁 Preview Eligible</button>
          <div class="flex gap-2">
            <button id="wfModalCancel" class="chip">Cancel</button>
            <button id="wfModalSave" class="chip active">Save Workflow</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Workflow test-run (dry-run) modal — surfaces eligible-customer list
         WITHOUT sending anything, so admins can validate a workflow before
         hitting Run. Includes an Excel export button so the outcome list
         can be shared or filed away. -->
    <div id="wfTestModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:1000;align-items:flex-start;justify-content:center;padding-top:40px">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4" style="max-height:92vh;overflow-y:auto">
        <div class="px-5 py-3 border-b border-slate-200 flex items-center justify-between">
          <div>
            <div class="font-semibold text-slate-800" id="wfTestTitle">Test Workflow — Dry Run</div>
            <div class="text-[11px] text-slate-500" id="wfTestSubtitle">No emails will be sent. This is a dry-run preview.</div>
          </div>
          <button id="wfTestClose" class="text-slate-400 hover:text-slate-700">×</button>
        </div>
        <div class="px-5 py-4 text-[13px]">
          <div id="wfTestSummary" class="grid grid-cols-4 gap-3 mb-3">
            <div class="border border-slate-200 rounded p-2 bg-slate-50">
              <div class="text-[10px] uppercase text-slate-500">Customers</div>
              <div class="text-lg font-semibold text-slate-800" id="wfTestKpiCust">–</div>
            </div>
            <div class="border border-slate-200 rounded p-2 bg-slate-50">
              <div class="text-[10px] uppercase text-slate-500">Open Invoices</div>
              <div class="text-lg font-semibold text-slate-800" id="wfTestKpiInv">–</div>
            </div>
            <div class="border border-slate-200 rounded p-2 bg-slate-50">
              <div class="text-[10px] uppercase text-slate-500">Total Outstanding</div>
              <div class="text-lg font-semibold text-slate-800" id="wfTestKpiAmt">–</div>
            </div>
            <div class="border border-slate-200 rounded p-2 bg-slate-50">
              <div class="text-[10px] uppercase text-slate-500">Oldest (days)</div>
              <div class="text-lg font-semibold text-slate-800" id="wfTestKpiAge">–</div>
            </div>
          </div>
          <div id="wfTestStatus" class="text-[12px] text-slate-500 mb-2"></div>
          <div style="max-height:52vh;overflow:auto" class="border border-slate-100 rounded">
            <table class="w-full text-[12px]" id="wfTestTable">
              <thead class="bg-slate-50 text-slate-600 sticky top-0">
                <tr>
                  <th class="px-3 py-2 text-left">CID</th>
                  <th class="px-3 py-2 text-left">Customer</th>
                  <th class="px-3 py-2 text-left">Region</th>
                  <th class="px-3 py-2 text-right">Open Inv</th>
                  <th class="px-3 py-2 text-right">Outstanding</th>
                  <th class="px-3 py-2 text-right">Oldest (d)</th>
                  <th class="px-3 py-2 text-left">To</th>
                  <th class="px-3 py-2 text-left">Cc</th>
                </tr>
              </thead>
              <tbody id="wfTestTbody">
                <tr><td colspan="8" class="px-3 py-6 text-center text-slate-500">Evaluating…</td></tr>
              </tbody>
            </table>
          </div>
          <div id="wfTestError" class="text-[12px] text-red-600 mt-2"></div>
        </div>
        <div class="px-5 py-3 border-t border-slate-200 flex justify-between gap-2">
          <div class="text-[11px] text-slate-500 self-center">Dry-run reflects the SAVED workflow (not unsaved editor changes).</div>
          <div class="flex gap-2">
            <button id="wfTestExportBtn" class="chip" title="Download eligible-customer list as Excel">📥 Export Excel</button>
            <button id="wfTestCancel" class="chip">Close</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== REPORTS anchor ===== -->
    <div id="reports-anchor" data-section="reports"></div>

    <!-- Downloads & Reports section (vertical list, single Generate button) -->
    <section class="card p-4" data-section="reports">
      <div class="flex items-center justify-between mb-3 flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">Downloads &amp; Reports</div>
          <div class="text-[11px] text-slate-500">Pick one report — it uses the date range and filters from the top bar · Director-ready styled Excel (multi-sheet)</div>
        </div>
        <button id="reportGenerate" class="chip" title="Generate the selected report" style="background:var(--c-accent);color:#fff;border-color:var(--c-accent);">📊 Generate Report</button>
      </div>

      <div class="report-list" id="reportList">
        <label class="report-row active" data-rt="combined">
          <input type="radio" name="reportPick" value="combined" checked>
          <span class="rp-no">1</span>
          <div class="rp-info">
            <div class="rp-title">📊 Combined Business</div>
            <div class="rp-desc">3 sheets: Region Summary · Customer Summary · Full Detail rows</div>
          </div>
        </label>
        <label class="report-row" data-rt="dso">
          <input type="radio" name="reportPick" value="dso">
          <span class="rp-no">2</span>
          <div class="rp-info">
            <div class="rp-title">📈 DSO</div>
            <div class="rp-desc">Days Sales Outstanding · INV only · Summary + Detail (bucketing follows top Date Range)</div>
          </div>
        </label>
        <label class="report-row" data-rt="col">
          <input type="radio" name="reportPick" value="col">
          <span class="rp-no">3</span>
          <div class="rp-info">
            <div class="rp-title">💰 Total Collections</div>
            <div class="rp-desc">Collections aggregated by period · Summary + Detail (bucketing follows top Date Range)</div>
          </div>
        </label>
        <label class="report-row" data-rt="ageOs">
          <input type="radio" name="reportPick" value="ageOs">
          <span class="rp-no">4</span>
          <div class="rp-info">
            <div class="rp-title">📅 Outstanding Ageing</div>
            <div class="rp-desc">Status = Open · Pivot: CID × Customer × BU rows × Ageing-bucket columns × Outstanding values</div>
          </div>
        </label>
        <label class="report-row" data-rt="ageCol">
          <input type="radio" name="reportPick" value="ageCol">
          <span class="rp-no">5</span>
          <div class="rp-info">
            <div class="rp-title">🗓 Collections Ageing</div>
            <div class="rp-desc">By Receipt Date · Pivot: CID × Customer × BU rows × Ageing-bucket columns × Total Collections values</div>
          </div>
        </label>
        <label class="report-row" data-rt="tds">
          <input type="radio" name="reportPick" value="tds">
          <span class="rp-no">6</span>
          <div class="rp-info">
            <div class="rp-title">🧾 TDS Deducted by Client</div>
            <div class="rp-desc">Per-invoice TDS · FY tagged by EARLIER of Invoice Date / Receipt Date · CID, Customer, Transaction Type, Invoice details, Receipt details</div>
          </div>
        </label>
      </div>
    </section>

    <!-- ===== CUSTOMER STATEMENT (ledger) anchor ===== -->
    <div id="statement-anchor" data-section="statement"></div>
    <section class="card p-4 space-y-3" data-section="statement" style="display:none">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">🧾 Customer Statement of Account</div>
          <div class="text-[11px] text-slate-500">Pick a customer + date range. Shows invoices, credit notes, payments &amp; adjustments with running balance · Download Excel / PDF / Email to client.</div>
        </div>
      </div>

      <!-- Controls -->
      <div class="grid md:grid-cols-4 gap-2 border border-slate-200 rounded-lg p-3 bg-slate-50">
        <label class="md:col-span-2 text-[12px] flex flex-col gap-1">Customer
          <div style="position:relative">
            <input id="soaCustomer" type="text" class="chip" style="padding:6px 10px;width:100%" placeholder="Type to search by name or CID…" autocomplete="off"/>
            <div id="soaCustList" style="display:none;position:absolute;z-index:30;top:100%;left:0;right:0;max-height:280px;overflow-y:auto;background:#fff;border:1px solid var(--c-line);border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.08);margin-top:4px"></div>
          </div>
        </label>
        <label class="text-[12px] flex flex-col gap-1">From date
          <input id="soaFrom" type="date" class="chip" style="padding:6px 10px"/>
        </label>
        <label class="text-[12px] flex flex-col gap-1">To date
          <input id="soaTo" type="date" class="chip" style="padding:6px 10px"/>
        </label>
        <div class="md:col-span-4 flex items-center gap-2 flex-wrap">
          <button id="soaGen" class="chip" style="background:#15803d;color:#fff;border-color:#15803d;padding:6px 14px">🧾 Generate Statement</button>
          <button id="soaReset" class="chip" title="Clear customer, dates, filters and hide the preview" style="padding:6px 14px;background:#fef2f2;color:#991b1b;border-color:#fca5a5">↺ Reset</button>
          <button id="soaDlXlsx" class="chip" style="padding:6px 14px" disabled>⬇ Download Excel</button>
          <button id="soaDlPdf" class="chip" style="padding:6px 14px" disabled>📄 Download PDF</button>
          <button id="soaEmail" class="chip" style="padding:6px 14px;background:#dbeafe;color:#1e40af;border-color:#93c5fd" disabled>✉ Email to client</button>
          <button id="soaQuickFY" class="chip" title="Set From=Apr-1 of current FY · To=today" style="padding:6px 10px">Current FY</button>
          <button id="soaQuickAll" class="chip" title="From 01-Apr-2025 (earliest AR data) to today" style="padding:6px 10px">All-time</button>
          <span id="soaStatus" class="text-[11px] text-slate-500 ml-2"></span>
        </div>
        <!-- Status filter chips — All / Paid / Partial / Unpaid / Unmatched.
             Narrows the preview body in place; downloads/email remain full. -->
        <div class="md:col-span-4 flex items-center gap-2 flex-wrap" style="margin-top:-2px">
          <span class="text-[11px] text-slate-500" style="font-weight:600">Filter by status:</span>
          <div id="soaStatusFilter" data-active="All" style="display:inline-flex;gap:6px;flex-wrap:wrap">
            <button class="soa-status-chip chip" data-status="All" style="padding:3px 12px;font-size:11px">All</button>
            <button class="soa-status-chip chip" data-status="Paid" style="padding:3px 12px;font-size:11px">Paid</button>
            <button class="soa-status-chip chip" data-status="Partial" style="padding:3px 12px;font-size:11px">Partial</button>
            <button class="soa-status-chip chip" data-status="Unpaid" style="padding:3px 12px;font-size:11px">Unpaid</button>
            <button class="soa-status-chip chip" data-status="Unmatched" style="padding:3px 12px;font-size:11px">Unmatched</button>
          </div>
          <span id="soaStatusCount" class="text-[11px] text-slate-500"></span>
        </div>
      </div>

      <!-- Ledger preview (printable) -->
      <div id="soaLedger" class="soa-ledger" style="display:none">
        <!-- Letterhead -->
        <div class="soa-letterhead">
          <div class="soa-lh-left">
            <div class="soa-lh-brand">Fynd</div>
            <div class="soa-lh-co">Shopsense Retail Technologies Ltd.</div>
            <div class="soa-lh-addr">Mumbai · India</div>
          </div>
          <div class="soa-lh-right">
            <div class="soa-lh-title">STATEMENT OF ACCOUNT</div>
            <div class="soa-lh-meta">Generated: <span id="soaGenAt">—</span></div>
            <div class="soa-lh-meta">Period: <span id="soaPeriod">—</span></div>
          </div>
        </div>
        <!-- Customer block -->
        <div class="soa-cust-block">
          <div>
            <div class="soa-blk-lbl">Statement for</div>
            <div class="soa-blk-val" id="soaCustName">—</div>
            <div class="soa-blk-sub" id="soaCustMeta">—</div>
          </div>
          <div class="soa-totals">
            <div><span class="soa-tot-lbl">Opening</span><span class="soa-tot-val" id="soaOpening">—</span></div>
            <div><span class="soa-tot-lbl">Debits</span><span class="soa-tot-val" id="soaTotDr">—</span></div>
            <div><span class="soa-tot-lbl">Credits</span><span class="soa-tot-val" id="soaTotCr">—</span></div>
            <div class="soa-clos"><span class="soa-tot-lbl">Closing</span><span class="soa-tot-val" id="soaClosing">—</span></div>
          </div>
        </div>
        <!-- Reference filter chip — appears only when a reference is active.
             Lets the stakeholder pivot the ledger to "everything against
             one reference" (e.g. select an invoice ref → invoice line +
             its payment + TDS + adjustments all surface together). -->
        <div id="soaRefBar" style="display:none;align-items:center;gap:8px;margin:6px 0 8px 0;padding:7px 10px;background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;font-size:12px">
          <span style="color:#9a3412;font-weight:600">Filtered to reference:</span>
          <span id="soaRefBarVal" style="font-family:ui-monospace,monospace;font-weight:700;color:#7c2d12"></span>
          <span id="soaRefBarCount" style="color:#9a3412"></span>
          <button id="soaRefBarClear" class="chip" style="padding:3px 10px;margin-left:auto;background:#fff;border:1px solid #fdba74;color:#9a3412">Clear filter ✕</button>
        </div>
        <!-- Ledger table — PREVIEW layout drops the Balance column; the
             closing balance lives in the highlighted footer row instead.
             Excel / PDF / Email exports keep the full 11-column layout
             (with Balance) so external receivers still see running balance. -->
        <table class="soa-table">
          <thead>
            <tr>
              <th style="width:38px">#</th>
              <th style="width:96px">Date</th>
              <th style="width:120px">Type</th>
              <th style="width:140px">Doc No</th>
              <th style="width:140px">Reference</th>
              <th>Particulars</th>
              <th class="soa-num">Debit (₹)</th>
              <th class="soa-num">Credit (₹)</th>
              <th style="width:80px">Unique Ref</th>
              <th style="width:80px">Status</th>
            </tr>
          </thead>
          <tbody id="soaTbody"></tbody>
          <tfoot>
            <tr class="soa-foot-row">
              <td colspan="6" style="text-align:right;font-weight:600">Period totals</td>
              <td class="soa-num" id="soaFtDr">—</td>
              <td class="soa-num" id="soaFtCr">—</td>
              <td colspan="2"></td>
            </tr>
            <tr class="soa-foot-row" style="background:#fef9c3">
              <td colspan="6" style="text-align:right;font-weight:700;color:#854d0e">
                <span id="soaBalAsOnLbl">Balance as on</span> <span id="soaBalAsOnDate">—</span>
              </td>
              <td class="soa-num" colspan="2" id="soaBalAsOnVal" style="font-weight:700;color:#854d0e">—</td>
              <td colspan="2"></td>
            </tr>
          </tfoot>
        </table>
        <!-- Sign-off -->
        <div class="soa-signoff">
          <div>This statement is computer-generated. Please verify against your records and revert with any discrepancies within 7 days.</div>
          <div class="soa-sig">
            <div class="soa-sig-line"></div>
            <div class="soa-sig-lbl">For Shopsense Retail Technologies Ltd.</div>
          </div>
        </div>
      </div>

      <!-- Email modal -->
      <div id="soaEmailModal" class="fu-modal" style="display:none">
        <div class="fu-modal-shell" style="max-width:520px">
          <div class="fu-modal-head">
            <div class="text-sm font-semibold text-slate-800">✉ Email statement to client</div>
            <button id="soaEmailClose" class="chip" style="padding:4px 10px">✕</button>
          </div>
          <div class="fu-modal-body" style="background:#fff">
            <label class="text-[12px] flex flex-col gap-1 mb-2">To
              <input id="soaEmailTo" type="email" class="chip" style="padding:6px 10px" placeholder="client@example.com"/>
            </label>
            <label class="text-[12px] flex flex-col gap-1 mb-2">CC (optional)
              <input id="soaEmailCc" type="text" class="chip" style="padding:6px 10px" placeholder="cc1@example.com, cc2@example.com"/>
            </label>
            <label class="text-[12px] flex flex-col gap-1 mb-2">Subject
              <input id="soaEmailSubject" type="text" class="chip" style="padding:6px 10px"/>
            </label>
            <label class="text-[12px] flex flex-col gap-1">Message (HTML statement is appended below this note)
              <textarea id="soaEmailNote" rows="4" class="chip" style="padding:6px 10px;font-family:inherit"></textarea>
            </label>
            <div id="soaEmailMsg" class="text-[12px] mt-2"></div>
          </div>
          <div class="fu-modal-foot">
            <div class="text-[11px] text-slate-500">Sent from your Apps Script account</div>
            <button id="soaEmailSend" class="chip" style="background:#15803d;color:#fff;border-color:#15803d;padding:6px 14px">📤 Send</button>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== WORKLIST anchor (collector + admin) ===== -->
    <div id="worklist-anchor" data-section="worklist"></div>
    <section class="card p-4 space-y-4" data-section="worklist" style="display:none">
      <!-- Tab strip: To-Do List | Reports -->
      <div id="wlTabs" class="flex items-center gap-1 border-b border-slate-200" role="tablist">
        <button type="button" class="wl-tab wl-tab-active" data-wl-tab="todo" role="tab" aria-selected="true"
                style="padding:8px 14px;font-size:12px;font-weight:600;border:none;background:transparent;border-bottom:2px solid #2563eb;color:#1d4ed8;cursor:pointer;margin-bottom:-1px">✅ To-Do List</button>
        <button type="button" class="wl-tab" data-wl-tab="reports" role="tab" aria-selected="false"
                style="padding:8px 14px;font-size:12px;font-weight:500;border:none;background:transparent;border-bottom:2px solid transparent;color:#64748b;cursor:pointer;margin-bottom:-1px">📅 Reports</button>
      </div>

      <!-- ===== Pane: TO-DO LIST ===== -->
      <div data-wl-pane="todo" class="space-y-4">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">✅ To-Do List</div>
          <div class="text-[11px] text-slate-500">Your assigned customers · notes, follow-ups and promise-to-pay. <span id="wlScopeLabel" class="font-mono"></span></div>
        </div>
        <div class="flex items-center gap-2 text-[11px]">
          <select id="wlCollectorScope" class="chip" style="padding:6px 10px;min-width:180px" title="Filter the worklist by collector">
            <option value="">All collectors</option>
          </select>
          <span class="chip" id="wlWhoBadge" style="background:#dcfce7;color:#166534;border-color:#86efac;display:none">Loading…</span>
          <button id="wlReload" class="chip">↻ Reload</button>
          <button id="wlManageCollectors" class="chip" style="background:#fef3c7;color:#92400e;border-color:#fde68a">👥 Manage Collectors</button>
        </div>
      </div>

      <!-- KPI strip -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div class="card-soft p-3 rounded-lg">
          <div class="text-[10px] uppercase tracking-wide text-slate-500">My Open Customers</div>
          <div class="text-xl font-semibold" id="wlKpiOpen">—</div>
          <div class="text-[10px] text-slate-500"><span id="wlKpiOpenOs">—</span> outstanding</div>
        </div>
        <div class="card-soft p-3 rounded-lg">
          <div class="text-[10px] uppercase tracking-wide text-slate-500">Follow-ups Today</div>
          <div class="text-xl font-semibold" id="wlKpiToday" style="color:#15803d">—</div>
        </div>
        <div class="card-soft p-3 rounded-lg">
          <div class="text-[10px] uppercase tracking-wide text-slate-500">Overdue Follow-ups</div>
          <div class="text-xl font-semibold" id="wlKpiOverdue" style="color:#b91c1c">—</div>
        </div>
        <div class="card-soft p-3 rounded-lg">
          <div class="text-[10px] uppercase tracking-wide text-slate-500">P2P This Week</div>
          <div class="text-xl font-semibold" id="wlKpiP2P">—</div>
          <div class="text-[10px] text-slate-500"><span id="wlKpiP2POs">—</span> committed</div>
        </div>
      </div>

      <!-- Filters -->
      <div class="flex items-center gap-2 flex-wrap text-[12px]">
        <div id="wlStatusBtns" class="flex items-center gap-1 flex-wrap">
          <button class="wl-status-btn chip wl-status-active" data-status="all" style="padding:4px 10px">All open</button>
          <button class="wl-status-btn chip" data-status="overdue" style="padding:4px 10px">Overdue</button>
          <button class="wl-status-btn chip" data-status="today" style="padding:4px 10px">Due today</button>
          <button class="wl-status-btn chip" data-status="week" style="padding:4px 10px">This week</button>
          <button class="wl-status-btn chip" data-status="upcoming" style="padding:4px 10px">Upcoming</button>
          <button class="wl-status-btn chip" data-status="nocontact" style="padding:4px 10px">No contact</button>
          <button class="wl-status-btn chip" data-status="stale" style="padding:4px 10px">Stale 7d+</button>
        </div>
        <input id="wlSearch" type="text" class="chip" style="padding:4px 10px;min-width:220px" placeholder="Search by CID or customer name…"/>
        <span class="text-[11px] text-slate-500" id="wlRowCount"></span>
      </div>

      <!-- Worklist table — trimmed to: CID, Customer, Outstanding (sortable),
           Next Follow-up, Action. Paginated 15/page so the page stays compact. -->
      <div class="overflow-x-auto border border-slate-200 rounded-lg">
        <table class="w-full text-[12px]">
          <thead class="bg-slate-50">
            <tr class="text-left text-slate-600">
              <th class="px-3 py-2">CID</th>
              <th class="px-3 py-2">Customer</th>
              <th class="px-3 py-2 text-right">
                <button id="wlSortOs" type="button"
                  title="Sort by Outstanding"
                  style="background:none;border:none;font-size:12px;font-weight:600;color:#475569;cursor:pointer;padding:0;display:inline-flex;align-items:center;gap:4px">
                  Outstanding <span id="wlSortOsArrow" style="font-size:10px;color:#1d4ed8">▼</span>
                </button>
              </th>
              <th class="px-3 py-2">Next Follow-up</th>
              <th class="px-3 py-2">Action</th>
            </tr>
          </thead>
          <tbody id="wlTbody">
            <tr><td colspan="5" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
          </tbody>
        </table>
      </div>
      <!-- Worklist pagination bar -->
      <div id="wlPager" class="flex items-center justify-between mt-2 text-[11px] text-slate-600" style="display:none">
        <div id="wlPagerInfo">—</div>
        <div class="flex items-center gap-1">
          <button id="wlPrev" class="chip" style="padding:2px 10px">‹ Prev</button>
          <span id="wlPageNum" class="font-mono">1 / 1</span>
          <button id="wlNext" class="chip" style="padding:2px 10px">Next ›</button>
        </div>
      </div>
      </div><!-- /pane: todo -->

      <!-- ===== Pane: REPORTS ===== -->
      <div data-wl-pane="reports" style="display:none">
      <!-- Daily Report panel -->
      <div class="border border-slate-200 rounded-lg p-3 bg-slate-50">
        <div class="flex items-center justify-between mb-2 flex-wrap gap-2">
          <div>
            <div class="text-sm font-semibold text-slate-800">📅 Reports</div>
            <div class="text-[11px] text-slate-500">Range: <span id="wlDailyRangeLbl" class="font-mono">Today</span> · <span id="wlDailyDate" class="font-mono"></span></div>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <div id="wlDailyRangeBtns" class="flex items-center gap-1 flex-wrap">
              <button class="wl-range-btn chip wl-status-active" data-range="today" style="padding:4px 10px">Today</button>
              <button class="wl-range-btn chip" data-range="7d" style="padding:4px 10px">7 days</button>
              <button class="wl-range-btn chip" data-range="month" style="padding:4px 10px">Monthly</button>
              <button class="wl-range-btn chip" data-range="all" style="padding:4px 10px">All</button>
              <button class="wl-range-btn chip" data-range="custom" style="padding:4px 10px">Custom</button>
            </div>
            <button id="wlDailyReload" class="chip">↻ Refresh</button>
            <button id="wlDailyExcel" class="chip" style="background:#15803d;color:white;border-color:#15803d">⬇ Generate Report</button>
          </div>
        </div>
        <div id="wlDailyCustomBox" class="flex items-center gap-2 mb-2 text-[12px]" style="display:none">
          <label class="text-[11px] text-slate-600 flex items-center gap-1">From <input id="wlDailyFrom" type="date" class="chip" style="padding:2px 8px"/></label>
          <label class="text-[11px] text-slate-600 flex items-center gap-1">To <input id="wlDailyTo" type="date" class="chip" style="padding:2px 8px"/></label>
          <button id="wlDailyCustomApply" class="chip" style="padding:4px 10px;background:#1d4ed8;color:white;border-color:#1d4ed8">Apply</button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-[12px]">
            <thead class="bg-white">
              <tr class="text-left text-slate-600">
                <th class="px-3 py-2">Collector</th>
                <th class="px-3 py-2 text-right">CIDs</th>
                <th class="px-3 py-2 text-right">Open Os</th>
                <th class="px-3 py-2 text-right" id="wlDailyColNotes">Notes (range)</th>
                <th class="px-3 py-2 text-right">Due Today</th>
                <th class="px-3 py-2 text-right">Due Tomorrow</th>
                <th class="px-3 py-2 text-right">Due This Week</th>
                <th class="px-3 py-2 text-right">P2P #</th>
                <th class="px-3 py-2 text-right">P2P Amount</th>
                <th class="px-3 py-2 text-right">Untouched 7d+</th>
              </tr>
            </thead>
            <tbody id="wlDailyTbody">
              <tr><td colspan="10" class="px-3 py-4 text-center text-slate-500">Loading…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      </div><!-- /pane: reports -->
    </section>

    <!-- ===== NOTES MODAL (Worklist) — invoice-level ===== -->
    <div id="wlNotesModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9999;align-items:center;justify-content:center;padding:20px;overflow:auto">
      <div style="background:white;border-radius:12px;max-width:1080px;width:100%;max-height:92vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.3)">
        <div style="padding:14px 20px;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:start;gap:12px;background:#f8fafc;border-top-left-radius:12px;border-top-right-radius:12px">
          <div style="min-width:0;flex:1">
            <div class="text-sm font-semibold text-slate-800" id="wlNotesTitle">Customer</div>
            <div class="text-[11px] text-slate-500 mt-0.5" id="wlNotesSub">—</div>
            <div class="text-[11px] text-slate-700 mt-1 flex flex-wrap gap-3" id="wlNotesHeaderStats"></div>
          </div>
          <button id="wlNotesClose" class="chip" style="padding:4px 10px">✕ Close</button>
        </div>
        <!-- Invoice-type tabs -->
        <div id="wlNotesTypeTabs" style="display:flex;gap:6px;flex-wrap:wrap;padding:10px 20px;border-bottom:1px solid #e2e8f0;background:white"></div>
        <!-- Invoice filters: actionable / overdue / scheduled / etc + ageing + search -->
        <div style="padding:8px 20px;border-bottom:1px solid #e2e8f0;background:#f8fafc;display:flex;flex-wrap:wrap;align-items:center;gap:8px">
          <div id="wlNotesStatusBtns" style="display:flex;gap:4px;flex-wrap:wrap"></div>
          <div style="flex:1"></div>
          <select id="wlNotesAgeing" class="chip" style="padding:4px 8px;font-size:11px" title="Ageing bucket">
            <option value="all">All ageing</option>
            <option value="0-30">≤ 30d</option>
            <option value="31-60">31–60d</option>
            <option value="61-90">61–90d</option>
            <option value="91-180">91–180d</option>
            <option value="180+">180+d</option>
          </select>
          <input id="wlNotesSearch" type="text" class="chip" placeholder="🔍 Invoice #" style="padding:4px 10px;font-size:11px;width:140px"/>
          <button id="wlNotesFiltersReset" class="chip" style="padding:4px 8px;font-size:11px" title="Clear filters">Reset</button>
        </div>
        <!-- Body: two-column layout (invoice list | invoice detail) -->
        <div style="display:flex;flex:1;min-height:0;overflow:hidden">
          <!-- LEFT: invoice list -->
          <div style="width:46%;border-right:1px solid #e2e8f0;display:flex;flex-direction:column;min-width:0">
            <div style="padding:8px 16px;border-bottom:1px solid #f1f5f9;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#64748b;display:flex;justify-content:space-between;align-items:center;gap:8px">
              <label style="display:flex;align-items:center;gap:6px;cursor:pointer;text-transform:none;letter-spacing:0;font-size:11px;color:#475569" title="Select / deselect all invoices in this view">
                <input type="checkbox" id="wlNotesSelectAll" style="cursor:pointer">
                <span>Open invoices</span>
              </label>
              <span id="wlNotesInvCount" class="text-slate-500">—</span>
            </div>
            <div id="wlNotesInvList" style="overflow-y:auto;flex:1;padding:6px 8px">
              <div class="text-slate-500 text-[12px] p-3 text-center">Loading…</div>
            </div>
          </div>
          <!-- RIGHT: invoice detail + add note -->
          <div style="flex:1;display:flex;flex-direction:column;min-width:0">
            <div id="wlNotesInvDetail" style="padding:12px 16px;border-bottom:1px solid #f1f5f9;font-size:12px;color:#475569">
              <span class="text-slate-400">Select an invoice on the left to view notes and add a follow-up.</span>
            </div>
            <div style="padding:10px 16px;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#64748b">Notes history</div>
            <div id="wlNotesHistory" class="space-y-2" style="flex:1;overflow-y:auto;padding:0 16px 12px">
              <div class="text-slate-500 text-[12px]">—</div>
            </div>
            <div style="padding:10px 16px;border-top:1px solid #e2e8f0;background:#f8fafc;border-bottom-right-radius:12px">
              <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Add note <span id="wlNoteForInv" class="text-slate-400 normal-case tracking-normal"></span></div>
              <div class="grid md:grid-cols-2 gap-2">
                <label class="text-[12px] flex flex-col gap-1 md:col-span-2">Note
                  <textarea id="wlNoteText" rows="2" class="chip" style="padding:6px 10px;font-family:inherit" placeholder="What did you discuss?"></textarea>
                </label>
                <label class="text-[12px] flex flex-col gap-1">Next follow-up date
                  <input id="wlNoteFollowUp" type="date" class="chip" style="padding:6px 10px"/>
                </label>
                <label class="text-[12px] flex flex-col gap-1"><span>Outcome <span style="color:#b91c1c">*</span></span>
                  <select id="wlNoteOutcome" class="chip" style="padding:6px 10px" required>
                    <option value="">— Select outcome —</option>
                    <option value="Callback required">Callback required</option>
                    <option value="Promise to Pay">Promise to Pay</option>
                    <option value="Logistics Dispute">Logistics Dispute</option>
                    <option value="Billing Dispute">Billing Dispute</option>
                    <option value="Short Paid">Short Paid</option>
                    <option value="No response">No response</option>
                    <option value="Escalated">Escalated</option>
                    <option value="Other">Other</option>
                  </select>
                </label>
                <label class="text-[12px] flex flex-col gap-1 wl-p2p-only" style="display:none">P2P amount (₹)
                  <input id="wlNoteP2PAmt" type="number" min="0" step="0.01" class="chip" style="padding:6px 10px" placeholder="0.00"/>
                </label>
                <label class="text-[12px] flex flex-col gap-1 wl-p2p-only" style="display:none">P2P date
                  <input id="wlNoteP2PDate" type="date" class="chip" style="padding:6px 10px"/>
                </label>
              </div>
              <div class="flex items-center justify-between mt-2 gap-2">
                <div id="wlNoteMsg" class="text-[12px]"></div>
                <button id="wlNoteSave" class="chip" style="background:#15803d;color:white;border-color:#15803d;padding:6px 14px" disabled>💾 Save note</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== MANAGE COLLECTORS MODAL (admin-only) ===== -->
    <div id="wlMcModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:9999;align-items:center;justify-content:center;padding:20px;overflow:auto">
      <div style="background:white;border-radius:12px;max-width:920px;width:100%;max-height:92vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.3)">
        <div style="padding:16px 20px;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center">
          <div>
            <div class="text-sm font-semibold text-slate-800">👥 Manage Collectors</div>
            <div class="text-[11px] text-slate-500">Add/remove collectors and assign customer IDs to each.</div>
          </div>
          <button id="wlMcClose" class="chip" style="padding:4px 10px">✕ Close</button>
        </div>
        <div style="padding:16px 20px;overflow-y:auto;flex:1">
          <!-- Conflict banner (one-CID-one-collector audit). Shown only when duplicate ownership is detected. -->
          <div id="mcConflictBanner" style="display:none;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 12px;margin-bottom:12px"></div>

          <!-- Tab strip: Add/Update | Assign CIDs -->
          <div id="mcTabs" class="flex items-center gap-1 border-b border-slate-200 mb-4" role="tablist">
            <button type="button" class="mc-tab mc-tab-active" data-mc-tab="manage" role="tab" aria-selected="true"
                    style="padding:8px 14px;font-size:12px;font-weight:600;border:none;background:transparent;border-bottom:2px solid #2563eb;color:#1d4ed8;cursor:pointer;margin-bottom:-1px">👥 Add / Update Collectors</button>
            <button type="button" class="mc-tab" data-mc-tab="assign" role="tab" aria-selected="false"
                    style="padding:8px 14px;font-size:12px;font-weight:500;border:none;background:transparent;border-bottom:2px solid transparent;color:#64748b;cursor:pointer;margin-bottom:-1px">📌 Assign CIDs to Collectors</button>
          </div>

          <!-- ===== Pane: Add / Update Collectors ===== -->
          <div data-mc-pane="manage">
          <!-- Add collector -->
          <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 mb-4">
            <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Add or update collector</div>
            <div class="grid md:grid-cols-4 gap-2">
              <label class="text-[12px] flex flex-col gap-1">Email
                <input id="mcEmail" type="email" class="chip" style="padding:6px 10px" placeholder="collector@gofynd.com"/>
              </label>
              <label class="text-[12px] flex flex-col gap-1">Name
                <input id="mcName" type="text" class="chip" style="padding:6px 10px" placeholder="Full name"/>
              </label>
              <label class="text-[12px] flex flex-col gap-1">Active
                <select id="mcActive" class="chip" style="padding:6px 10px">
                  <option value="Yes">Yes</option>
                  <option value="No">No (suspended)</option>
                </select>
              </label>
              <div class="flex items-end gap-2">
                <button id="mcSaveCollector" class="chip" style="background:#15803d;color:white;border-color:#15803d;padding:6px 14px">💾 Save</button>
              </div>
            </div>
            <div id="mcCollectorMsg" class="text-[12px] mt-2"></div>
          </div>

          <!-- Collector list -->
          <div class="flex items-center justify-between mb-2 flex-wrap gap-2">
            <div class="text-[11px] uppercase tracking-wide text-slate-500">Collectors</div>
            <button id="mcDownload" class="chip" style="background:#15803d;color:white;border-color:#15803d;padding:4px 12px;font-size:11px" title="Download a coverage report (Excel) showing assigned vs unassigned customers per collector">⬇ Download coverage (.xlsx)</button>
          </div>
          <div class="overflow-x-auto border border-slate-200 rounded-lg mb-4">
            <table class="w-full text-[12px]">
              <thead class="bg-slate-50">
                <tr class="text-left text-slate-600">
                  <th class="px-3 py-2">Name</th>
                  <th class="px-3 py-2">Email</th>
                  <th class="px-3 py-2">Status</th>
                  <th class="px-3 py-2 text-right">CIDs</th>
                  <th class="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody id="mcCollectorTbody">
                <tr><td colspan="5" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>
              </tbody>
            </table>
          </div>
          </div><!-- /pane: manage -->

          <!-- ===== Pane: Assign CIDs to Collectors ===== -->
          <div data-mc-pane="assign" style="display:none">
          <!-- Quick collector picker (one-shot assignment without scrolling through the table) -->
          <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 mb-4">
            <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Pick a collector to assign CIDs</div>
            <div class="flex flex-wrap items-end gap-2 text-[12px]">
              <label class="flex flex-col gap-1 flex-1" style="min-width:240px">Collector
                <select id="mcAssignPick" class="chip" style="padding:6px 10px">
                  <option value="">— Select collector —</option>
                </select>
              </label>
              <button id="mcAssignPickGo" class="chip" style="background:#1d4ed8;color:white;border-color:#1d4ed8;padding:6px 14px">Load CIDs</button>
              <span id="mcAssignPickMsg" class="text-[11px] text-slate-500"></span>
            </div>
          </div>

          <!-- Bulk upload (moved here so it's grouped with the collector list it feeds) -->
          <div class="border border-amber-200 rounded-lg p-3 bg-amber-50 mb-4">
            <div class="flex items-center justify-between flex-wrap gap-2 mb-2">
              <div>
                <div class="text-[11px] uppercase tracking-wide text-amber-800">📥 Bulk assign by CSV</div>
                <div class="text-[11px] text-slate-600">CSV columns: <span class="font-mono">Email,CID</span> (one row per CID; header optional)</div>
              </div>
              <div class="flex items-center gap-2 text-[12px]">
                <label class="flex items-center gap-1 text-[11px]"><input type="radio" name="mcBulkMode" value="merge" checked> Add to existing</label>
                <label class="flex items-center gap-1 text-[11px]"><input type="radio" name="mcBulkMode" value="replace"> Replace existing</label>
                <input id="mcBulkFile" type="file" accept=".csv,.txt,text/csv" class="text-[11px]"/>
                <button id="mcBulkTemplate" class="chip" style="padding:4px 8px">⬇ Template</button>
              </div>
            </div>
            <div id="mcBulkPreview" class="text-[11px] text-slate-600 mt-1"></div>
            <div id="mcBulkActions" class="flex items-center gap-2 mt-2" style="display:none">
              <button id="mcBulkSave" class="chip" style="background:#15803d;color:white;border-color:#15803d;padding:4px 12px">💾 Apply</button>
              <button id="mcBulkCancel" class="chip" style="padding:4px 12px">Cancel</button>
              <span id="mcBulkMsg" class="text-[12px]"></span>
            </div>
          </div>

          <!-- CID assignment -->
          <div id="mcAssignBox" style="display:none">
            <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Assign CIDs to <span class="font-mono" id="mcAssignTarget"></span></div>
            <div class="flex items-center gap-2 mb-2 text-[12px] flex-wrap">
              <!-- Scope chips: "Mine only" (default) shows just the picked collector's
                   CIDs so the table aligns with the picker count. "All" exposes the
                   full universe so the user can claim CIDs from other collectors. -->
              <div id="mcScopeChips" class="flex items-center gap-1" role="tablist">
                <button class="mc-scope-btn chip mc-scope-active" data-mc-scope="mine"
                  style="padding:4px 10px;background:#1d4ed8;color:#fff;border-color:#1d4ed8">
                  👤 Mine only (<span id="mcScopeMineCount">0</span>)
                </button>
                <button class="mc-scope-btn chip" data-mc-scope="all"
                  style="padding:4px 10px">
                  🌐 All accounts (<span id="mcScopeAllCount">0</span>)
                </button>
              </div>
              <select id="mcCidBuFilter" class="chip" style="padding:4px 10px;min-width:160px">
                <option value="">All Regions</option>
              </select>
              <input id="mcCidSearch" type="text" class="chip" style="padding:4px 10px;min-width:220px" placeholder="Search customer or CID…"/>
              <span class="text-[11px] text-slate-500"><span id="mcCidSelected">0</span> selected (<span id="mcCidSelectedInView">0</span> in view) · <span id="mcCidTotal">0</span> total · <span id="mcCidShown">0</span> shown</span>
              <button id="mcCidSelectAll" class="chip" style="padding:4px 10px">Select all (filtered)</button>
              <button id="mcCidClearAll" class="chip" style="padding:4px 10px" title="With a Region/search filter active, clears only the visible rows. Otherwise clears every selection.">Clear (filtered)</button>
              <button id="mcCidPaste" class="chip" style="padding:4px 10px;background:#dbeafe;color:#1e40af;border-color:#93c5fd">📋 Paste CID list</button>
              <button id="mcCidReload" class="chip" style="padding:4px 10px">↻ Reload</button>
              <span id="mcCidLoadMsg" class="text-[11px] text-slate-500"></span>
            </div>
            <div id="mcCidPasteBox" style="display:none" class="mb-2">
              <textarea id="mcCidPasteText" rows="3" class="chip w-full" style="padding:6px 10px;font-family:monospace;font-size:11px" placeholder="Paste CIDs, one per line or comma-separated…"></textarea>
              <div class="flex gap-2 mt-1">
                <button id="mcCidPasteApply" class="chip" style="padding:4px 10px;background:#15803d;color:white;border-color:#15803d">Add to selection</button>
                <button id="mcCidPasteClose" class="chip" style="padding:4px 10px">Cancel</button>
                <span id="mcCidPasteMsg" class="text-[11px] text-slate-500"></span>
              </div>
            </div>
            <div class="border border-slate-200 rounded-lg" style="max-height:280px;overflow-y:auto">
              <table class="w-full text-[12px]">
                <thead class="bg-slate-50 sticky top-0">
                  <tr class="text-left text-slate-600">
                    <th class="px-3 py-2" style="width:36px"></th>
                    <th class="px-3 py-2">CID</th>
                    <th class="px-3 py-2">Customer</th>
                    <th class="px-3 py-2">BU</th>
                    <th class="px-3 py-2 text-right">Open Os</th>
                    <th class="px-3 py-2">Owned by</th>
                  </tr>
                </thead>
                <tbody id="mcCidTbody"></tbody>
              </table>
            </div>
            <div class="flex items-center justify-between mt-3">
              <div id="mcAssignMsg" class="text-[12px]"></div>
              <button id="mcAssignSave" class="chip" style="background:#15803d;color:white;border-color:#15803d;padding:6px 14px">💾 Save assignments</button>
            </div>
          </div>
          </div><!-- /pane: assign -->
        </div>
      </div>
    </div>

    <!-- ===== ACCESS MATRIX anchor (admin-only) ===== -->
    <!-- .hidden-until-admin uses display:none !important; applyAccessControl removes it
         only for the verified admin. Non-admin viewers cannot reveal this section via
         showTab() because showTab also hard-blocks key === 'acm' when !acmState.isAdmin,
         AND non-admin viewers have this entire section + the sidebar tab removed from
         the DOM right after the auth check completes. -->
    <div id="acm-anchor" data-section="acm" class="hidden-until-admin"></div>
    <section id="acmSection" class="card p-4 space-y-4 hidden-until-admin" data-section="acm">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-sm font-semibold text-slate-800">🔐 User Management &mdash; Admin only</div>
          <div class="text-[11px] text-slate-500">Manage who sees which tab. Stored in the <span class="font-mono">Access_Matrix</span> sheet · only <span class="font-mono" id="acmAdminEmail">sainathgosika@gofynd.com</span> can edit.</div>
        </div>
        <div class="flex items-center gap-2 text-[11px]">
          <span class="chip" id="acmWhoBadge" style="background:#dcfce7;color:#166534;border-color:#86efac">Loading…</span>
          <button id="acmReload" class="chip">↻ Reload</button>
        </div>
      </div>

      <!-- Add / Edit form — simplified to 5 visible fields per user spec:
           User Name (login), Email, Password (with eye toggle), Provisioned On,
           Tabs (checkboxes). Department/Role/Active/Notes are preserved in the
           DB with sensible defaults but hidden from the form. -->
      <div class="grid md:grid-cols-4 gap-2 border border-slate-200 rounded-lg p-3 bg-slate-50">
        <div class="md:col-span-4 text-[11px] uppercase tracking-wide text-slate-500" id="acmFormTitle">Add stakeholder</div>
        <label class="text-[12px] flex flex-col gap-1">User Name
          <input id="acmUsername" type="text" class="chip" style="padding:6px 10px" placeholder="Login username (3–32 chars)" autocomplete="off"/>
        </label>
        <label class="text-[12px] flex flex-col gap-1">Email
          <input id="acmEmail" type="email" class="chip" style="padding:6px 10px" placeholder="user@gofynd.com" autocomplete="off"/>
        </label>
        <label class="text-[12px] flex flex-col gap-1">Password
          <div style="position:relative;">
            <input id="acmPassword" type="password" class="chip" style="padding:6px 34px 6px 10px;width:100%;box-sizing:border-box" placeholder="Set password (min 6 chars, mix of letters, numbers, symbols)" autocomplete="new-password"/>
            <button type="button" id="acmPasswordEye" title="Show / hide password" aria-label="Show password"
              style="position:absolute;top:50%;right:6px;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:#6b6660;padding:2px 4px;display:inline-flex;align-items:center;justify-content:center;line-height:0;"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></button>
          </div>
        </label>
        <label class="text-[12px] flex flex-col gap-1">Provisioned On
          <input id="acmProv" type="date" class="chip" style="padding:6px 10px"/>
        </label>
        <div class="md:col-span-4">
          <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Tabs granted</div>
          <!-- Populated at runtime by renderAcmTabsCheckboxes() which walks
               the sidebar (#sideNav) so newly-added tabs automatically appear
               here without touching this template. -->
          <div id="acmTabsBox" class="flex flex-col gap-1 text-[12px]"></div>
        </div>
        <div class="md:col-span-4 flex items-center gap-2">
          <button id="acmSave" class="chip" style="background:#15803d;color:#fff;border-color:#15803d">💾 Save stakeholder</button>
          <button id="acmReset" class="chip">↺ Clear form</button>
          <span id="acmFormMsg" class="text-[11px] ml-2"></span>
        </div>
      </div>

      <!-- Stakeholder table — simplified columns: User Name, Email, Tabs, Provisioned, Status, Actions -->
      <div class="overflow-x-auto rounded-lg border border-slate-200">
        <table class="w-full text-[12px]">
          <thead class="bg-slate-50"><tr>
            <th class="px-3 py-2 text-left">User Name</th>
            <th class="px-3 py-2 text-left">Email</th>
            <th class="px-3 py-2 text-left">Tabs Granted</th>
            <th class="px-3 py-2 text-left">Provisioned</th>
            <th class="px-3 py-2 text-left">Status</th>
            <th class="px-3 py-2 text-left">Actions</th>
          </tr></thead>
          <tbody id="acmTbody"><tr><td colspan="6" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr></tbody>
        </table>
      </div>
    </section>

    <footer class="pt-2 pb-6 text-center text-[11px] text-slate-400">
      Receivables Insights · Fynd · Generated <span id="genTs"></span>
    </footer>
  </main>
</div>

</div><!-- /page-shell -->

<script>
// __DATA_INJECTION_POINT__

// ===== State =====
const state = {
  data: [],
  rowsCol: [], rowsInv: [],
  dateRange:'all', dateFrom:null, dateTo:null,
  customer:[], bu:[], status:['Open'], bucket:[], paymentType:[], invoiceType:[], channel:[], paymentTerm:[],
  topMetric:'collections', chMetric:'collections',
  dsoPeriod:'month', colPeriod:'month',
  currency:'auto',
  expandedCust: new Set(), expandedBU: new Set(),
  // per-report date scope override
  reportPeriod: { combined:'all', dso:'all', col:'all', ageOs:'all', ageCol:'all' },
  reportDates:  { combined:{from:'',to:''}, dso:{from:'',to:''}, col:{from:'',to:''}, ageOs:{from:'',to:''}, ageCol:{from:'',to:''} },
  activeReport: 'combined',
  activeTab: 'dashboard',
  // section-level multi-select filters (independent of global filter bar)
  cust2: { customers:[], bus:[], q:'' },
  bu2:   { bus:[], channels:[], q:'' },
};
const charts = {};
/* Calm muted palette — sage/petrol/sand/gold (no neon) */
const PALETTE = ['#5b7a82','#a3b8b0','#c9bfa9','#b8956a','#8e9d8a','#6b8e5a','#b85450','#a89677','#7a8a8e','#d6c9ad'];
const STRONG  = ['#2c4a52','#5b7a82','#6b8e5a','#b8956a','#8b6f43','#b85450','#5b4d6b','#3d5a4a'];

// ===== Utilities =====
function fmtINR(n){
  if(!isFinite(n)) return '₹0';
  const c = state.currency || 'auto';
  if(c==='auto'){ const a=Math.abs(n); let v,s; if(a>=1e7){v=n/1e7;s='Cr';} else if(a>=1e5){v=n/1e5;s='L';} else if(a>=1e3){v=n/1e3;s='K';} else {v=n;s='';} return '₹'+v.toLocaleString('en-IN',{maximumFractionDigits:2})+(s?' '+s:''); }
  if(c==='inr'){ return '₹'+(Math.round(n*100)/100).toLocaleString('en-IN',{maximumFractionDigits:2}); }
  if(c==='k'){ return '₹'+(n/1e3).toLocaleString('en-IN',{maximumFractionDigits:2})+' K'; }
  if(c==='l'){ return '₹'+(n/1e5).toLocaleString('en-IN',{maximumFractionDigits:2})+' L'; }
  if(c==='cr'){ return '₹'+(n/1e7).toLocaleString('en-IN',{maximumFractionDigits:2})+' Cr'; }
  return '₹'+n;
}
function fmtINRfull(n){
  if(!isFinite(n)) return '₹0';
  const c = state.currency || 'auto';
  if(c==='inr' || c==='auto'){ return '₹'+(Math.round(n*100)/100).toLocaleString('en-IN',{maximumFractionDigits:2}); }
  return fmtINR(n);
}
const fmtNum = (n)=> (n||0).toLocaleString('en-IN');
const pct = (n,d)=> d>0 ? ((n/d)*100).toFixed(1)+'%' : '—';
const parseD = (s)=> s? new Date(s+'T00:00:00') : null;

function dateRangeFor(range, customFrom, customTo){
  const today = new Date(); today.setHours(0,0,0,0);
  if(range==='all') return [null,null];
  if(range==='custom'){
    const f = customFrom ? new Date(customFrom+'T00:00:00') : null;
    const t = customTo   ? new Date(customTo+'T23:59:59') : null;
    return [f, t];
  }
  let from=new Date(today), to=new Date(today);
  if(range==='today'){ /* same day */ }
  else if(range==='month'){ from=new Date(today.getFullYear(),today.getMonth(),1); }
  else if(range==='quarter'){
    // Indian fiscal-year quarter: Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar
    const m = today.getMonth();
    const fyQStart = m>=3 ? (Math.floor((m-3)/3))*3 + 3 : 0; // 0/3/6/9 → 3/6/9/0
    if(m<3){ from = new Date(today.getFullYear(),0,1); }
    else { from = new Date(today.getFullYear(), fyQStart, 1); }
  }
  else if(range==='ytd'){
    // YTD = current Indian Fiscal Year (April 1 of current FY → today)
    const m = today.getMonth();
    const fyStartYear = m>=3 ? today.getFullYear() : today.getFullYear()-1;
    from = new Date(fyStartYear, 3, 1); // April 1
  }
  to.setHours(23,59,59,999);
  return [from,to];
}
function daysInRange(from,to){
  if(!from||!to){
    if(state.data.length===0) return 365;
    const all = state.data.map(r=>r.d).filter(Boolean).sort();
    if(!all.length) return 365;
    const a=parseD(all[0]), b=parseD(all[all.length-1]);
    return Math.max(1, Math.round((b-a)/(1000*60*60*24))+1);
  }
  return Math.max(1, Math.round((to-from)/(1000*60*60*24))+1);
}

/* =========================================================================
 * DSO — per-customer first-invoice-date anchor
 * -------------------------------------------------------------------------
 * The denominator in DSO is the number of days over which a customer has
 * actually been billed. Using the dashboard's selected date-range chip as
 * the denominator is wrong: a chip like "All / YTD / Quarter" applies the
 * same window to every customer, whether that customer has 3 years of
 * history or was onboarded 6 weeks ago.
 *
 * Correct semantics (restored):
 *   • DSO denominator = today − firstInvoiceDate(customer)
 *   • firstInvoiceDate is looked up per Company ID (primary) or per
 *     normalised seller-key (fallback when CID is missing).
 *   • If a date-range filter is active (F..T), the anchor is clipped to
 *     max(firstInv, F) and the end to min(today, T). This keeps a "Last
 *     quarter" filter honest — a 3-year-old customer contributes ~90 days
 *     to DSO, not 1095.
 *
 * `_dsoAnchorStart()` / `_dsoPeriodDays()` are kept intact because other
 * modules (SOA balance-as-on, chip-anchored aggregates) still call them.
 * Only `_custDsoDays()` was re-wired to consume state._firstInvByCID /
 * state._firstInvBySeller (populated by _computeFirstInvByCust() on every
 * recompute).
 * ========================================================================= */
function _computeFirstInvByCust(){
  const byCID = {}, bySeller = {};
  (state.data||[]).forEach(r=>{
    if(!r.d) return;
    // Track by Company ID (primary)
    if(r.ci){
      if(!byCID[r.ci] || r.d < byCID[r.ci]) byCID[r.ci] = r.d;
    }
    // Track by normalised seller key (fallback when CID is missing)
    const sk = _sellerKey(r.s);
    if(!bySeller[sk] || r.d < bySeller[sk]) bySeller[sk] = r.d;
  });
  state._firstInvByCID    = byCID;
  state._firstInvBySeller = bySeller;
}
function _periodEnd(){
  const [, T] = dateRangeFor(state.dateRange, state.dateFrom, state.dateTo);
  return T || new Date();
}
// DSO denominator anchor — the FIRST day to count from, based on the
// selected date range. Replaces the old per-customer first-invoice model
// which over-inflated DSO for customers with a long history.
//
//   all     → 2025-04-01 (start of current Indian FY, FY26)
//   month   → 1st of current calendar month
//   quarter → 1st of current Indian fiscal quarter (Apr/Jul/Oct/Jan)
//   ytd     → April 1 of the current Indian fiscal year
//   today   → today
//   custom  → user-picked From date (falls back to 2025-04-01)
function _dsoAnchorStart(range, customFrom){
  const today = new Date(); today.setHours(0,0,0,0);
  const FY_FALLBACK = new Date(2025, 3, 1); // 2025-04-01
  if(range==='custom'){
    return customFrom ? new Date(customFrom+'T00:00:00') : FY_FALLBACK;
  }
  if(range==='today'){   return today; }
  if(range==='month'){   return new Date(today.getFullYear(), today.getMonth(), 1); }
  if(range==='quarter'){
    const m = today.getMonth();
    if(m < 3) return new Date(today.getFullYear(), 0, 1);            // Q4 = Jan-Mar
    const fyQStart = Math.floor((m - 3) / 3) * 3 + 3;                // 3 / 6 / 9
    return new Date(today.getFullYear(), fyQStart, 1);
  }
  if(range==='ytd'){
    const m = today.getMonth();
    const fyStartYear = m >= 3 ? today.getFullYear() : today.getFullYear()-1;
    return new Date(fyStartYear, 3, 1);                              // April 1
  }
  // 'all' → fixed FY26 start as requested
  return FY_FALLBACK;
}
function _dsoPeriodDays(){
  const start = _dsoAnchorStart(state.dateRange, state.dateFrom);
  const end   = _periodEnd();
  if(!start || !end) return 1;
  return Math.max(1, Math.round((end - start) / (1000*60*60*24)) + 1);
}
// Per-customer DSO days = (end − firstInvoiceDate). Anchors at THIS
// customer's earliest invoice, not the dashboard's date-range chip. If
// a date-range filter is active, clip the anchor to filter start and
// the end to filter end so a "Last quarter" chip doesn't let a 3-year
// history contribute 1095 days.
function _custDsoDays(ci, sellerName){
  const today = new Date(); today.setHours(0,0,0,0);
  // Lookup per-customer first invoice date (Company ID first, seller fallback)
  var firstInv = null;
  if (ci && state._firstInvByCID && state._firstInvByCID[ci]) firstInv = state._firstInvByCID[ci];
  if (!firstInv && sellerName){
    var sk = _sellerKey(sellerName);
    if (state._firstInvBySeller && state._firstInvBySeller[sk]) firstInv = state._firstInvBySeller[sk];
  }
  if (!firstInv) return 1;
  // Convert to Date if the map stored a string (r.d is normalised to YYYY-MM-DD)
  var fi = (firstInv instanceof Date) ? firstInv : new Date(firstInv);
  if (!(fi instanceof Date) || isNaN(fi.getTime())) return 1;
  // Clip to active date-range filter — respect the user's window
  var _r = dateRangeFor(state.dateRange, state.dateFrom, state.dateTo);
  var F = _r && _r[0], T = _r && _r[1];
  if (F && fi < F) fi = F;
  var end = T || today;
  var days = Math.round((end - fi) / (1000*60*60*24)) + 1;
  return Math.max(1, days);
}
// Weighted DSO across multiple customers (used at BU-level + global KPI).
// Each customer contributes (OS_i / IA_i) × custDays_i, weighted by OS_i.
function _weightedDSO(custIter){
  let totOS = 0, weighted = 0, hasAny=false;
  custIter.forEach(c=>{
    const ia = +c.ia||0, os = +c.os||0;
    if(ia<=0) return;
    const d  = _custDsoDays(c.ci || '', c.name || c.s || '');
    const dso = (os/ia) * d;
    totOS    += Math.abs(os);
    weighted += dso * Math.abs(os);
    hasAny    = true;
  });
  if(!hasAny || totOS<=0) return 0;
  return Math.round(weighted/totOS);
}

// ===== Filtering =====
function applyMultiFilter(rows){
  const f = state;
  return rows.filter(r=>{
    if(f.customer.length && !f.customer.includes(r.s||'')) return false;
    if(f.bu.length && !f.bu.includes(r.b||'')) return false;
    if(f.status.length){
      // case-insensitive status match (handles 'Open' / 'OPEN' / 'open')
      const rsl = String(r.st||'').toLowerCase();
      const ok = f.status.some(s=> String(s||'').toLowerCase() === rsl);
      if(!ok) return false;
    }
    if(f.bucket.length && !f.bucket.includes(ageBucketFromDays(r.dy))) return false;
    if(f.paymentType.length && !f.paymentType.includes(r.pt||'')) return false;
    if(f.invoiceType.length && !f.invoiceType.includes(r.it||'')) return false;
    if(f.channel.length && !f.channel.includes(r.ch||'')) return false;
    if(f.paymentTerm.length && !f.paymentTerm.includes(String(r.ptr||''))) return false;
    return true;
  });
}
function recompute(){
  // Single combined date range applies to BOTH invoice date and receipt date (union behaviour)
  const [F,T] = dateRangeFor(state.dateRange, state.dateFrom, state.dateTo);
  // Precompute first-invoice-date per Company ID (and seller fallback) — used by all DSO sites
  _computeFirstInvByCust();
  const base = applyMultiFilter(state.data);
  state.rowsInv = base.filter(r=>{ if(!F) return true; if(!r.d) return false; const d=parseD(r.d); return d>=F && d<=T; });
  state.rowsCol = base.filter(r=>{ if(!F) return true; if(!r.rd) return false; const d=parseD(r.rd); return d>=F && d<=T; });
  // Union of distinct rows that match either invoice or receipt date filter
  const u = new Set(); state.rowsInv.forEach(r=>u.add(r)); state.rowsCol.forEach(r=>u.add(r));
  const filteredCount = u.size;
  document.getElementById('rowCounter').textContent = `${fmtNum(state.rowsInv.length)} invoice rows · ${fmtNum(state.rowsCol.length)} receipt rows`;
  // Header meta
  const ts = new Date().toLocaleString('en-IN',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
  const lr = document.getElementById('lastRefresh'); if(lr) lr.textContent = ts;
  const hc = document.getElementById('hdrCount');
  if(hc) hc.textContent = `${fmtNum(filteredCount)} of ${fmtNum(state.data.length)} filtered`;
}

// ===== KPI computations =====
function calcKPIs(){
  const inv = state.rowsInv, col = state.rowsCol;
  const totalCol = col.reduce((a,r)=>a+(+r.co||0),0);
  const totalInv = inv.filter(r=>r.it==='INV').reduce((a,r)=>a+(+r.ia||0),0);
  const totalOS = inv.reduce((a,r)=>a+(+r.os||0),0);
  const cnRows = inv.filter(r=>r.it==='CN');
  const cnVal = cnRows.reduce((a,r)=>a+Math.abs(+r.cn||0)+Math.abs(+r.ia||0),0);
  const tdsTot = inv.reduce((a,r)=>a+(+r.tds||0),0);
  const post = inv.filter(r=>r.st==='Closed' && (+r.ps||0)>0).length;
  const buSet = new Set(inv.map(r=>r.b).filter(Boolean));
  const custSet = new Set(inv.map(r=>r.s).filter(Boolean));
  const days = daysInRange(...dateRangeFor(state.dateRange, state.dateFrom, state.dateTo));
  const credSales = inv.filter(r=>r.it==='INV').reduce((a,r)=>a+(+r.ia||0),0);
  // Per-CID DSO: aggregate filtered invoices by CID, weight by outstanding
  const _byCust = {};
  inv.filter(r=>r.it==='INV').forEach(r=>{
    const k = r.ci || _sellerKey(r.s);
    if(!_byCust[k]) _byCust[k] = { ci:r.ci||'', name:r.s||'', ia:0, os:0 };
    _byCust[k].ia += (+r.ia||0);
    _byCust[k].os += (+r.os||0);
  });
  const dso = _weightedDSO(Object.values(_byCust));
  const cov = totalInv>0 ? ((totalCol/totalInv)*100) : 0;
  return { totalCol,totalInv,totalOS,cnVal,cnCount:cnRows.length,tdsTot,post,buCount:buSet.size,custCount:custSet.size,dso,cov,days };
}
function paintKPIs(){
  const k = calcKPIs();
  // sticky KPI strip (7 tiles — always visible across every tab)
  document.getElementById('sk_col').textContent = fmtINR(k.totalCol);
  document.getElementById('sk_os').textContent = fmtINR(k.totalOS);
  document.getElementById('sk_inv').textContent = fmtINR(k.totalInv);
  document.getElementById('sk_bu_top').textContent = fmtNum(k.buCount);
  document.getElementById('sk_cust').textContent = fmtNum(k.custCount);
  document.getElementById('sk_dso').textContent = k.dso + ' d';
  document.getElementById('sk_cov').textContent = k.cov.toFixed(1)+'%';
}

// ===== Charts =====
// Deferred chart creation: if the canvas is inside a hidden .tab-section
// (i.e. a tab that's not the currently-visible one), we queue the create/
// update instead of paying the Chart.js cost right now. showTab() flushes
// the queue for the newly-visible section. This shifts the ~200-400 ms
// per-chart cost off the initial paint path and onto the moment the user
// actually navigates to that tab.
const _chartQueue = {};   // id → { type, data, opts }
function _isCanvasVisibleNow(canvas){
  if(!canvas) return false;
  // A canvas is "visible" if none of its ancestors are display:none / .hidden.
  // We use offsetParent as a fast proxy — it's null when any ancestor is
  // display:none. This isn't perfect (position:fixed) but is fine for the
  // tab-section markup pattern used here.
  return canvas.offsetParent !== null;
}
function _flushChartQueue(){
  var ids = Object.keys(_chartQueue);
  for (var i = 0; i < ids.length; i++){
    var id = ids[i];
    var c = document.getElementById(id);
    if (!c || !_isCanvasVisibleNow(c)) continue;
    var q = _chartQueue[id];
    delete _chartQueue[id];
    _makeOrUpdateNow(id, q.type, q.data, q.opts);
  }
}
function _makeOrUpdateNow(id, type, data, opts){
  var el = document.getElementById(id);
  if (!el) return;
  var ctx = el.getContext('2d');
  if(charts[id]){ charts[id].data = data; if(opts) charts[id].options = opts; charts[id].update(); return; }
  charts[id] = new Chart(ctx, { type: type, data: data, options: opts || {} });
}
function makeOrUpdate(id, type, data, opts){
  var el = document.getElementById(id);
  if (!el) return;
  // If the canvas is currently hidden AND the chart doesn't yet exist, queue.
  // (If it already exists, keep it in sync so a later showTab render is fresh.)
  if (!_isCanvasVisibleNow(el) && !charts[id]){
    _chartQueue[id] = { type: type, data: data, opts: opts };
    return;
  }
  _makeOrUpdateNow(id, type, data, opts);
}
function ageBucketFromDays(d){
  d = +d || 0;
  if(d <= 30) return '0-30 days';
  if(d <= 60) return '31-60 days';
  if(d <= 90) return '61-90 days';
  if(d <= 120) return '91-120 days';
  if(d <= 180) return '121-180 days';
  if(d <= 365) return '181-365 days';
  return 'Over 365 days';
}
const AGE_ORDER = ['0-30 days','31-60 days','61-90 days','91-120 days','121-180 days','181-365 days','Over 365 days'];

function paintCharts(){
  // Ageing - ASCENDING (0-30 → Over 365), re-bucketed from days field
  const ageMap = {};
  state.rowsInv.forEach(r=>{ const k = ageBucketFromDays(r.dy); ageMap[k]=(ageMap[k]||0)+(+r.os||0); });
  const ageLabels = AGE_ORDER.filter(k => k in ageMap);
  makeOrUpdate('cAge','bar',{labels:ageLabels,datasets:[{label:'Outstanding',data:ageLabels.map(l=>ageMap[l]||0),backgroundColor:PALETTE,borderRadius:6}]},
    {responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>'Outstanding: '+fmtINR(c.parsed.y)}}},scales:{y:{ticks:{callback:v=>fmtINR(v)},grid:{color:'#f1f5f9'}},x:{grid:{display:false},ticks:{font:{size:10},autoSkip:false,maxRotation:30,minRotation:30}}}});

  // Top 10 Customers
  const cmap = {};
  const target = state.topMetric==='collections' ? state.rowsCol : state.rowsInv;
  target.forEach(r=>{ const k=r.s||'Unknown'; if(!cmap[k]) cmap[k]={col:0,os:0,inv:0}; cmap[k].col+=(+r.co||0); cmap[k].os+=(+r.os||0); cmap[k].inv+=(+r.ia||0); });
  const sortKey = state.topMetric==='collections'?'col':state.topMetric==='outstanding'?'os':'inv';
  const sorted = Object.entries(cmap).sort((a,b)=>Math.abs(b[1][sortKey])-Math.abs(a[1][sortKey])).slice(0,10);
  makeOrUpdate('cTop','bar',{labels:sorted.map(([k])=>k.length>22?k.slice(0,21)+'…':k),datasets:[{label:state.topMetric,data:sorted.map(([,v])=>v[sortKey]),backgroundColor:'#a3b8b0',borderColor:'#5b7a82',borderWidth:1,borderRadius:4}]},
    {indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>fmtINR(c.parsed.x)}}},scales:{x:{ticks:{callback:v=>fmtINR(v)},grid:{color:'#f1f5f9'}},y:{grid:{display:false},ticks:{font:{size:10.5}}}}});

  // Channel-wise Performance
  const chmap = {};
  const chTarget = state.chMetric==='collections' ? state.rowsCol : state.rowsInv;
  chTarget.forEach(r=>{ const k=r.ch||'Unknown'; if(!chmap[k]) chmap[k]={col:0,os:0,inv:0}; chmap[k].col+=(+r.co||0); chmap[k].os+=(+r.os||0); chmap[k].inv+=(+r.ia||0); });
  const chKey = state.chMetric==='collections'?'col':state.chMetric==='outstanding'?'os':'inv';
  const chSorted = Object.entries(chmap).sort((a,b)=>Math.abs(b[1][chKey])-Math.abs(a[1][chKey]));
  makeOrUpdate('cCh','bar',{labels:chSorted.map(([k])=>k),datasets:[{label:state.chMetric,data:chSorted.map(([,v])=>v[chKey]),backgroundColor:STRONG.map((_,i)=>PALETTE[i%PALETTE.length]),borderColor:'#5b7a82',borderWidth:1,borderRadius:6}]},
    {responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>fmtINR(c.parsed.y)}}},scales:{y:{ticks:{callback:v=>fmtINR(v)},grid:{color:'#f1f5f9'}},x:{grid:{display:false},ticks:{font:{size:10.5}}}}});

  // Trend - monthly Collections (receipt date) vs Invoices (invoice date)
  const t = {};
  state.rowsCol.forEach(r=>{ if(!r.rd || r.rd.length<7) return; const k=r.rd.slice(0,7); if(!t[k]) t[k]={col:0,inv:0}; t[k].col+=(+r.co||0); });
  state.rowsInv.forEach(r=>{ if(!r.d || r.d.length<7) return; const k=r.d.slice(0,7); if(!t[k]) t[k]={col:0,inv:0}; t[k].inv+=(+r.ia||0); });
  const tk = Object.keys(t).sort();
  const mNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const labels = tk.map(k=>{ const [y,m]=k.split('-'); return mNames[parseInt(m,10)-1]+'-'+y.slice(2); });
  makeOrUpdate('cTrend','line',{labels:labels,datasets:[
    {label:'Collections',data:tk.map(k=>t[k].col),borderColor:'#6b8e5a',backgroundColor:'rgba(107,142,90,.16)',tension:.3,fill:true,pointRadius:3,borderWidth:2},
    {label:'Invoices',data:tk.map(k=>t[k].inv),borderColor:'#5b7a82',backgroundColor:'rgba(91,122,130,.14)',tension:.3,fill:true,pointRadius:3,borderWidth:2}
  ]},{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:11}}},tooltip:{callbacks:{label:c=>c.dataset.label+': '+fmtINR(c.parsed.y)}}},scales:{y:{beginAtZero:true,ticks:{callback:v=>fmtINR(v)},grid:{color:'#f1f5f9'}},x:{grid:{display:false},ticks:{font:{size:10},maxRotation:0}}}});

}

// ===== DSO Report =====
function dsoBucket(dateStr, period){
  if(!dateStr) return null;
  const d = parseD(dateStr); if(!d) return null;
  if(period==='month'){ return dateStr.slice(0,7); }
  if(period==='quarter'){ const q=Math.floor(d.getMonth()/3)+1; return d.getFullYear()+'-Q'+q; }
  if(period==='year'){ return String(d.getFullYear()); }
  return null;
}
function periodDays(period){ return period==='month'?30:period==='quarter'?90:365; }
function buildDSO(){
  const inv = state.rowsInv.filter(r=>r.it==='INV');
  // Per-period totals + per-customer-within-period buckets (so DSO is weighted by CID,
  // not by an unrealistic global 30/90/365-day period denominator for new customers)
  const map = {};
  inv.forEach(r=>{
    const k = dsoBucket(r.d, state.dsoPeriod); if(!k) return;
    if(!map[k]) map[k] = { invoiced:0, count:0, os:0, custs:{} };
    map[k].invoiced += (+r.ia||0);
    map[k].count    += 1;
    map[k].os       += (+r.os||0);
    const ck = r.ci || _sellerKey(r.s);
    if(!map[k].custs[ck]) map[k].custs[ck] = { ci:r.ci||'', name:r.s||'', ia:0, os:0 };
    map[k].custs[ck].ia += (+r.ia||0);
    map[k].custs[ck].os += (+r.os||0);
  });
  // Collections aligned to invoice period (credit-period logic)
  const colMap = {};
  inv.forEach(r=>{
    const k = dsoBucket(r.d, state.dsoPeriod); if(!k) return;
    colMap[k] = (colMap[k]||0) + (+r.co||0);
  });
  const rows = Object.keys(map).sort().map(k=>{
    const m = map[k];
    // Weighted DSO from per-customer first-invoice-date — replaces the simple period-days denominator
    const dso = _weightedDSO(Object.values(m.custs));
    return { period:k, count:m.count, invoiced:m.invoiced, collections:(colMap[k]||0), os:m.os, dso };
  });
  return rows;
}
function buildTotalCollections(){
  // Use receipt date filtered rows (rowsCol)
  const rows = state.rowsCol;
  const map = {};
  rows.forEach(r=>{
    const k = dsoBucket(r.rd, state.colPeriod); if(!k) return;
    if(!map[k]) map[k] = { period:k, count:0, total:0 };
    map[k].count += 1;
    map[k].total += (+r.co||0);
  });
  return Object.keys(map).sort().map(k=>{
    const m = map[k];
    return { period:k, count:m.count, total:m.total, avg: m.count>0 ? m.total/m.count : 0 };
  });
}
// ===== Per-Business-Unit DSO (for DSO Report Summary breakdown) =====
function buildDSOByBU(){
  const inv = state.rowsInv.filter(r=>r.it==='INV');
  // map[period|BU] -> totals + per-customer DSO inputs
  const map = {};
  inv.forEach(r=>{
    const p = dsoBucket(r.d, state.dsoPeriod); if(!p) return;
    const b = r.b || '—';
    const k = p + '||' + b;
    if(!map[k]) map[k] = { period:p, bu:b, invoiced:0, count:0, os:0, custs:{} };
    map[k].invoiced += (+r.ia||0);
    map[k].count    += 1;
    map[k].os       += (+r.os||0);
    const ck = r.ci || _sellerKey(r.s);
    if(!map[k].custs[ck]) map[k].custs[ck] = { ci:r.ci||'', name:r.s||'', ia:0, os:0 };
    map[k].custs[ck].ia += (+r.ia||0);
    map[k].custs[ck].os += (+r.os||0);
  });
  const colMap = {};
  inv.forEach(r=>{
    const p = dsoBucket(r.d, state.dsoPeriod); if(!p) return;
    const b = r.b || '—';
    const k = p + '||' + b;
    colMap[k] = (colMap[k]||0) + (+r.co||0);
  });
  const rows = Object.keys(map).sort((a,b)=>{
    const ma = map[a], mb = map[b];
    return (ma.period||'').localeCompare(mb.period||'') || (ma.bu||'').localeCompare(mb.bu||'');
  }).map(k=>{
    const m = map[k];
    const dso = _weightedDSO(Object.values(m.custs));
    return { period:m.period, bu:m.bu, count:m.count, invoiced:m.invoiced, collections:(colMap[k]||0), os:m.os, dso };
  });
  return rows;
}
// ===== Per-Business-Unit Total Collections (for Collections Report Summary breakdown) =====
function buildTotalCollectionsByBU(){
  const rows = state.rowsCol;
  const map = {};
  rows.forEach(r=>{
    const p = dsoBucket(r.rd, state.colPeriod); if(!p) return;
    const b = r.b || '—';
    const k = p + '||' + b;
    if(!map[k]) map[k] = { period:p, bu:b, count:0, total:0 };
    map[k].count += 1;
    map[k].total += (+r.co||0);
  });
  return Object.keys(map).sort((a,b)=>{
    const ma = map[a], mb = map[b];
    return (ma.period||'').localeCompare(mb.period||'') || (ma.bu||'').localeCompare(mb.bu||'');
  }).map(k=>{
    const m = map[k];
    return { period:m.period, bu:m.bu, count:m.count, total:m.total, avg: m.count>0 ? m.total/m.count : 0 };
  });
}

// ===== Customer-wise breakdown (split by BU + expand) =====
// Case/whitespace-insensitive seller dedupe key (collapses 'ABC Corp', 'abc corp', 'ABC  CORP')
function _sellerKey(s){ return String(s||'Unknown').toLowerCase().replace(/\s+/g,' ').trim(); }
// Prefer the variant that has at least one uppercase letter (e.g. 'ABC Corp' over 'abc corp');
// otherwise keep the first encountered.
function _pickBetterName(existing, incoming){
  if(!existing) return incoming;
  const exHasUpper = /[A-Z]/.test(existing);
  const inHasUpper = /[A-Z]/.test(incoming);
  if(inHasUpper && !exHasUpper) return incoming;
  return existing;
}
function buildCustomerAgg(){
  // group by NORMALIZED seller-key first; within each customer, group by BU
  const inv = state.rowsInv, col = state.rowsCol;
  const cMap = {};
  inv.forEach(r=>{
    const rawC = r.s||'Unknown', b = r.b||'—';
    const ck = _sellerKey(rawC);
    if(!cMap[ck]) cMap[ck] = { name:rawC, cid:r.ci||'', total:{inv:0,ia:0,os:0,tds:0,cn:0,post:0}, bus:{} };
    cMap[ck].name = _pickBetterName(cMap[ck].name, rawC);
    if(!cMap[ck].cid && r.ci) cMap[ck].cid = r.ci;
    if(!cMap[ck].bus[b]) cMap[ck].bus[b] = { bu:b, cid:r.ci||'', inv:0, ia:0, os:0, tds:0, cn:0, post:0, col:0 };
    if(!cMap[ck].bus[b].cid && r.ci) cMap[ck].bus[b].cid = r.ci;
    cMap[ck].bus[b].inv += 1;
    cMap[ck].bus[b].ia += (+r.ia||0);
    cMap[ck].bus[b].os += (+r.os||0);
    cMap[ck].bus[b].tds += (+r.tds||0);
    cMap[ck].bus[b].cn += Math.abs(+r.cn||0);
    if(r.st==='Closed' && (+r.ps||0)>0) cMap[ck].bus[b].post += 1;
    cMap[ck].total.inv += 1;
    cMap[ck].total.ia += (+r.ia||0);
    cMap[ck].total.os += (+r.os||0);
    cMap[ck].total.tds += (+r.tds||0);
    cMap[ck].total.cn += Math.abs(+r.cn||0);
    if(r.st==='Closed' && (+r.ps||0)>0) cMap[ck].total.post += 1;
  });
  // collections by customer + BU
  col.forEach(r=>{
    const rawC = r.s||'Unknown', b = r.b||'—';
    const ck = _sellerKey(rawC);
    if(!cMap[ck]) cMap[ck] = { name:rawC, cid:r.ci||'', total:{inv:0,ia:0,os:0,tds:0,cn:0,post:0,col:0}, bus:{} };
    cMap[ck].name = _pickBetterName(cMap[ck].name, rawC);
    if(!cMap[ck].cid && r.ci) cMap[ck].cid = r.ci;
    if(!cMap[ck].bus[b]) cMap[ck].bus[b] = { bu:b, cid:r.ci||'', inv:0, ia:0, os:0, tds:0, cn:0, post:0, col:0 };
    if(!cMap[ck].bus[b].cid && r.ci) cMap[ck].bus[b].cid = r.ci;
    cMap[ck].bus[b].col = (cMap[ck].bus[b].col||0) + (+r.co||0);
    cMap[ck].total.col = (cMap[ck].total.col||0) + (+r.co||0);
  });
  // sort customers by collections then by IA
  const arr = Object.values(cMap).map(c=>{ c.total.col = c.total.col||0; c.busArr = Object.values(c.bus).sort((a,b)=>(b.col||0)-(a.col||0)); return c; });
  arr.sort((a,b)=>(b.total.col||0)-(a.total.col||0));
  return arr;
}
function buColor(bu){
  const palette = {'Reliance':'badge-blue','Reliance-RBL':'badge-violet','India':'badge-amber','SaaS':'badge-green','Commerce Global':'badge-red','Nexus':'badge-blue','India-GaaS':'badge-amber','Reliance-MI':'badge-violet','Reliance-Nexus':'badge-blue','ONDC':'badge-amber','Saas':'badge-green','Reliance-RBL(Nexus)':'badge-violet'};
  return palette[bu] || 'badge-slate';
}
function paintCustTable(){
  const arr = buildCustomerAgg();
  const filter = (document.getElementById('custFilter').value||'').trim().toLowerCase();
  // Apply section-local multi-select filters
  const selCust = state.cust2.customers.map(s=>String(s));
  const selBU   = state.cust2.bus.map(s=>String(s));
  let filtered = arr;
  if(selCust.length) filtered = filtered.filter(c=> selCust.indexOf(c.name)!==-1);
  if(selBU.length)   filtered = filtered.filter(c=> c.busArr.some(b=> selBU.indexOf(b.bu)!==-1));
  if(filter)         filtered = filtered.filter(c=> c.name.toLowerCase().includes(filter));
  // Show all customers; scroll container limits to 5 visible rows
  const top = filtered;
  document.getElementById('custMeta').textContent = `${fmtNum(filtered.length)} customers · all visible · scroll to see more · click row to expand BU split`;
  const body = document.getElementById('custBody');
  body.innerHTML = top.map((c,i)=>{
    const open = state.expandedCust.has(c.name);
    const collPct = c.total.ia>0 ? Math.min(100, (c.total.col/c.total.ia)*100) : 0;
    const buBadges = c.busArr.length>1 ? `<span class="text-[10px] text-slate-400 ml-1">(${c.busArr.length} BUs)</span>` : '';
    // DSO uses days from THIS customer's first invoice date → today (per-CID, capped at relationship length)
    const days = _custDsoDays(c.cid || '', c.name);
    const cDso = c.total.ia>0 ? Math.round((c.total.os/c.total.ia)*days) : 0;
    const parent = `<tr class="parent-row" data-c="${encodeURIComponent(c.name)}">
      <td><span class="arrow ${open?'open':''}">▶</span></td>
      <td class="text-slate-500">${i+1}</td>
      <td class="font-medium">${c.name}${buBadges}</td>
      <td class="text-right">${fmtNum(c.total.inv)}</td>
      <td class="text-right">${fmtINRfull(c.total.ia)}</td>
      <td class="text-right text-emerald-700 font-semibold">${fmtINRfull(c.total.col)}</td>
      <td class="text-right ${c.total.os>0?'num-red':c.total.os<0?'num-green':'num-zero'}">${fmtINRfull(c.total.os)}</td>
      <td class="text-right text-violet-700 font-semibold">${cDso} d</td>
      <td class="text-right">
        <div class="flex items-center justify-end gap-2"><div class="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden"><div class="h-full bg-indigo-500" style="width:${collPct}%"></div></div><span class="text-[11px]">${collPct.toFixed(0)}%</span></div>
      </td>
    </tr>`;
    const children = open ? c.busArr.map(b=>{
      const bp = b.ia>0?Math.min(100,(b.col/b.ia)*100):0;
      const bDso = b.ia>0 ? Math.round((b.os/b.ia)*days) : 0;
      return `<tr class="child-row">
        <td></td><td></td>
        <td><span class="badge ${buColor(b.bu)} mr-2">${b.bu}</span></td>
        <td class="text-right">${fmtNum(b.inv)}</td>
        <td class="text-right">${fmtINRfull(b.ia)}</td>
        <td class="text-right text-emerald-700">${fmtINRfull(b.col)}</td>
        <td class="text-right ${b.os>0?'num-red':b.os<0?'num-green':'num-zero'}">${fmtINRfull(b.os)}</td>
        <td class="text-right text-violet-700">${bDso} d</td>
        <td class="text-right">${bp.toFixed(0)}%</td>
      </tr>`;
    }).join('') : '';
    return parent + children;
  }).join('');
}

// ===== BU breakdown table (simplified + conditional + expand to customers) =====
function buildBUAgg(){
  const inv = state.rowsInv, col = state.rowsCol;
  const m = {};
  inv.forEach(r=>{
    const b = r.b||'—';
    if(!m[b]) m[b] = { bu:b, inv:0, ia:0, os:0, col:0, custs:{} };
    m[b].inv += 1;
    m[b].ia += (+r.ia||0);
    m[b].os += (+r.os||0);
    const rawC = r.s||'Unknown';
    const ck = _sellerKey(rawC);
    if(!m[b].custs[ck]) m[b].custs[ck] = { name:rawC, cid:r.ci||'', inv:0, ia:0, os:0, col:0 };
    if(!m[b].custs[ck].cid && r.ci) m[b].custs[ck].cid = r.ci;
    m[b].custs[ck].name = _pickBetterName(m[b].custs[ck].name, rawC);
    m[b].custs[ck].inv += 1;
    m[b].custs[ck].ia += (+r.ia||0);
    m[b].custs[ck].os += (+r.os||0);
  });
  col.forEach(r=>{
    const b = r.b||'—';
    if(!m[b]) m[b] = { bu:b, inv:0, ia:0, os:0, col:0, custs:{} };
    m[b].col += (+r.co||0);
    const rawC = r.s||'Unknown';
    const ck = _sellerKey(rawC);
    if(!m[b].custs[ck]) m[b].custs[ck] = { name:rawC, cid:r.ci||'', inv:0, ia:0, os:0, col:0 };
    if(!m[b].custs[ck].cid && r.ci) m[b].custs[ck].cid = r.ci;
    m[b].custs[ck].name = _pickBetterName(m[b].custs[ck].name, rawC);
    m[b].custs[ck].col += (+r.co||0);
  });
  return Object.values(m).map(b=>{ b.custArr = Object.values(b.custs).sort((a,b)=>(b.col||0)-(a.col||0)); b.custCount = b.custArr.length; return b; }).sort((a,b)=>(b.col||0)-(a.col||0));
}
function paintBUTable(){
  let arr = buildBUAgg();
  // Apply section-local multi-select + search filters
  const selBU = state.bu2.bus.map(s=>String(s));
  const selCh = state.bu2.channels.map(s=>String(s));
  const buQ   = ((document.getElementById('buFilter')||{}).value||'').trim().toLowerCase();
  if(selBU.length) arr = arr.filter(b=> selBU.indexOf(b.bu)!==-1);
  if(selCh.length){
    // BU appears if any of its source rows had a selected channel
    const buAllowed = new Set();
    state.rowsInv.concat(state.rowsCol).forEach(r=>{ if(selCh.indexOf(String(r.ch||''))!==-1) buAllowed.add(String(r.b||'—')); });
    arr = arr.filter(b=> buAllowed.has(b.bu));
  }
  if(buQ) arr = arr.filter(b=> b.bu.toLowerCase().includes(buQ));
  document.getElementById('buMeta').textContent = `${fmtNum(arr.length)} BUs · click row to drill-down to top customers`;
  const body = document.getElementById('buBody');
  body.innerHTML = arr.map((b,i)=>{
    const open = state.expandedBU.has(b.bu);
    const cp = b.ia>0?Math.min(100,(b.col/b.ia)*100):0;
    // BU-level DSO: weighted average across this BU's customers, each scaled by their own first-invoice-date
    const bDso = _weightedDSO((b.custArr||[]).map(c=>({ ci:c.cid||'', name:c.name, ia:c.ia, os:c.os })));
    const parent = `<tr class="parent-row" data-bu="${encodeURIComponent(b.bu)}">
      <td><span class="arrow ${open?'open':''}">▶</span></td>
      <td class="text-slate-500">${i+1}</td>
      <td class="font-medium"><span class="badge ${buColor(b.bu)}">${b.bu}</span> <span class="text-[10px] text-slate-400">(${b.custCount} cust.)</span></td>
      <td class="text-right">${fmtNum(b.inv)}</td>
      <td class="text-right">${fmtINRfull(b.ia)}</td>
      <td class="text-right text-emerald-700 font-semibold">${fmtINRfull(b.col)}</td>
      <td class="text-right ${b.os>0?'num-red':b.os<0?'num-green':'num-zero'}">${fmtINRfull(b.os)}</td>
      <td class="text-right text-violet-700 font-semibold">${bDso} d</td>
      <td class="text-right">
        <div class="flex items-center justify-end gap-2"><div class="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden"><div class="h-full bg-indigo-500" style="width:${cp}%"></div></div><span class="text-[11px]">${cp.toFixed(0)}%</span></div>
      </td>
    </tr>`;
    const children = open ? b.custArr.map(c=>{
      const ccp = c.ia>0?Math.min(100,(c.col/c.ia)*100):0;
      const cDso2 = c.ia>0 ? Math.round((c.os/c.ia)*_custDsoDays(c.cid||'', c.name)) : 0;
      return `<tr class="child-row">
        <td></td><td></td>
        <td>↳ ${c.name}</td>
        <td class="text-right">${fmtNum(c.inv)}</td>
        <td class="text-right">${fmtINRfull(c.ia)}</td>
        <td class="text-right text-emerald-700">${fmtINRfull(c.col)}</td>
        <td class="text-right ${c.os>0?'num-red':c.os<0?'num-green':'num-zero'}">${fmtINRfull(c.os)}</td>
        <td class="text-right text-violet-700">${cDso2} d</td>
        <td class="text-right">${ccp.toFixed(0)}%</td>
      </tr>`;
    }).join('') : '';
    return parent + children;
  }).join('');
}

// ===== Multi-select component =====
function buildMultiSelect(host, label, key){
  const allOpts = Array.from(new Set(state.data.map(r=>{
    if(key==='customer') return r.s;
    if(key==='bu') return r.b;
    if(key==='status') return r.st;
    if(key==='bucket') return ageBucketFromDays(r.dy);
    if(key==='paymentType') return r.pt;
    if(key==='invoiceType') return r.it;
    if(key==='channel') return r.ch;
    if(key==='paymentTerm') return String(r.ptr||'');
    return '';
  }).filter(v=>v!==undefined&&v!==null&&v!==''))).sort();
  const preset = (state[key]||[]).map(v=>String(v));
  host.innerHTML = `
    <div class="ms-wrap" data-msk="${key}">
      <div class="text-[10.5px] text-slate-500 mb-1 font-medium uppercase tracking-wide">${label}</div>
      <div class="ms-trig">
        <span class="text-slate-500 text-xs ms-summary">All ${label.toLowerCase()}</span>
        <span class="text-slate-400 text-xs">▾</span>
      </div>
      <div class="ms-pop">
        <div class="ms-search"><input placeholder="Search ${label.toLowerCase()}..." /></div>
        <div class="ms-actions">
          <button data-act="all">Select all</button>
          <button data-act="clear">Clear</button>
        </div>
        <div class="ms-list">
          ${allOpts.map(o=>`<label class="ms-opt"><input type="checkbox" value="${(''+o).replace(/"/g,'&quot;')}"${preset.includes(String(o))?' checked':''}/><span class="truncate" title="${(''+o).replace(/"/g,'&quot;')}">${o}</span></label>`).join('')}
        </div>
      </div>
    </div>
  `;
  const wrap = host.querySelector('.ms-wrap');
  const trig = wrap.querySelector('.ms-trig');
  const pop = wrap.querySelector('.ms-pop');
  const summary = wrap.querySelector('.ms-summary');
  const search = wrap.querySelector('.ms-search input');
  const list = wrap.querySelector('.ms-list');
  const cbs = ()=> Array.from(list.querySelectorAll('input[type=checkbox]'));

  trig.addEventListener('click', e=>{
    document.querySelectorAll('.ms-pop.open').forEach(p=>{ if(p!==pop) p.classList.remove('open'); });
    pop.classList.toggle('open');
  });
  search.addEventListener('input', ()=>{
    const q = search.value.toLowerCase();
    list.querySelectorAll('.ms-opt').forEach(opt=>{ opt.style.display = opt.textContent.toLowerCase().includes(q)?'':'none'; });
  });
  wrap.querySelectorAll('.ms-actions button').forEach(b=> b.addEventListener('click', e=>{
    e.preventDefault();
    if(b.dataset.act==='all'){ cbs().forEach(c=>{ if(c.closest('.ms-opt').style.display!=='none') c.checked=true; }); }
    else { cbs().forEach(c=>c.checked=false); }
    syncFromCBs();
  }));
  list.addEventListener('change', syncFromCBs);

  function syncFromCBs(){
    const sel = cbs().filter(c=>c.checked).map(c=>c.value);
    state[key] = sel;
    if(sel.length===0) summary.textContent = `All ${label.toLowerCase()}`;
    else if(sel.length<=2) summary.innerHTML = sel.map(s=>`<span class="ms-tag">${s}<span class="x" data-rm="${s.replace(/"/g,'&quot;')}">×</span></span>`).join(' ');
    else summary.innerHTML = `<span class="ms-tag">${sel.length} selected</span>`;
    summary.querySelectorAll('.x').forEach(x=>x.addEventListener('click', ev=>{
      ev.stopPropagation();
      const v = x.dataset.rm;
      cbs().forEach(c=>{ if(c.value===v) c.checked=false; });
      syncFromCBs();
    }));
    summary.classList.toggle('text-slate-500', sel.length===0);
    refresh();
  }
  // initial render of summary if any preset selections
  if(preset.length){
    const sel = preset;
    if(sel.length<=2) summary.innerHTML = sel.map(s=>`<span class="ms-tag">${s}<span class="x" data-rm="${s.replace(/"/g,'&quot;')}">×</span></span>`).join(' ');
    else summary.innerHTML = `<span class="ms-tag">${sel.length} selected</span>`;
    summary.classList.remove('text-slate-500');
    summary.querySelectorAll('.x').forEach(x=>x.addEventListener('click', ev=>{
      ev.stopPropagation();
      const v = x.dataset.rm;
      cbs().forEach(c=>{ if(c.value===v) c.checked=false; });
      syncFromCBs();
    }));
  }
  return { reset:()=>{ cbs().forEach(c=>c.checked=false); syncFromCBs(); } };
}

const msInstances = {};

/**
 * Lightweight multi-select used by section filter bars (Customers / BU).
 * Independent of the global state.<key> wiring — instead it mutates the
 * passed-in `targetArr` reference directly and calls onChange after each edit.
 */
function buildSimpleMS(host, label, items, targetArr, onChange){
  const sorted = Array.from(new Set(items.filter(v=>v!==undefined && v!==null && v!==''))).sort();
  const isSel = v => targetArr.indexOf(String(v)) !== -1;
  host.innerHTML = `
    <div class="ms-wrap">
      <div class="text-[10.5px] uppercase tracking-wide font-medium mb-1" style="color:var(--c-muted)">${label}</div>
      <div class="ms-trig">
        <span class="text-xs ms-summary" style="color:var(--c-muted)">All ${label.toLowerCase()}</span>
        <span class="text-xs" style="color:var(--c-muted)">▾</span>
      </div>
      <div class="ms-pop">
        <div class="ms-search"><input placeholder="Search ${label.toLowerCase()}..." /></div>
        <div class="ms-actions"><button data-act="all">Select all</button><button data-act="clear">Clear</button></div>
        <div class="ms-list">
          ${sorted.map(o=>`<label class="ms-opt"><input type="checkbox" value="${(''+o).replace(/"/g,'&quot;')}"${isSel(o)?' checked':''}/><span class="truncate" title="${(''+o).replace(/"/g,'&quot;')}">${o}</span></label>`).join('')}
        </div>
      </div>
    </div>`;
  const wrap=host.querySelector('.ms-wrap'), trig=wrap.querySelector('.ms-trig'),
        pop=wrap.querySelector('.ms-pop'), summary=wrap.querySelector('.ms-summary'),
        search=wrap.querySelector('.ms-search input'), list=wrap.querySelector('.ms-list');
  const cbs = ()=> Array.from(list.querySelectorAll('input[type=checkbox]'));
  trig.addEventListener('click', ()=>{
    document.querySelectorAll('.ms-pop.open').forEach(p=>{ if(p!==pop) p.classList.remove('open'); });
    pop.classList.toggle('open');
  });
  search.addEventListener('input', ()=>{
    const q=search.value.toLowerCase();
    list.querySelectorAll('.ms-opt').forEach(o=>{ o.style.display = o.textContent.toLowerCase().includes(q)?'':'none'; });
  });
  // Clear the inline search input AND restore full list visibility.
  // Called after every checkbox toggle / Select all / Clear so the user
  // immediately sees every option again — no need to wipe the search manually.
  function _clearSearch(){
    if(!search) return;
    search.value = '';
    list.querySelectorAll('.ms-opt').forEach(o => o.style.display = '');
  }
  wrap.querySelectorAll('.ms-actions button').forEach(b=> b.addEventListener('click', e=>{
    e.preventDefault();
    if(b.dataset.act==='all'){ cbs().forEach(c=>{ if(c.closest('.ms-opt').style.display!=='none') c.checked=true; }); }
    else { cbs().forEach(c=>c.checked=false); }
    _clearSearch();
    sync();
  }));
  list.addEventListener('change', ()=>{ _clearSearch(); sync(); });
  function sync(){
    const sel = cbs().filter(c=>c.checked).map(c=>c.value);
    targetArr.length = 0; sel.forEach(v=>targetArr.push(v));
    if(sel.length===0) summary.textContent = `All ${label.toLowerCase()}`;
    else if(sel.length<=2) summary.innerHTML = sel.map(s=>`<span class="ms-tag">${s}</span>`).join(' ');
    else summary.innerHTML = `<span class="ms-tag">${sel.length} selected</span>`;
    if(typeof onChange==='function') onChange();
  }
  // initial render
  if(targetArr.length){
    if(targetArr.length<=2) summary.innerHTML = targetArr.map(s=>`<span class="ms-tag">${s}</span>`).join(' ');
    else summary.innerHTML = `<span class="ms-tag">${targetArr.length} selected</span>`;
  }
  return { reset:()=>{ cbs().forEach(c=>c.checked=false); sync(); } };
}

/* Section-filter builders for Customers and Region sections */
let custSecMS = null, buSecMS = null;
function buildSectionFilters(){
  // Customers section
  const custCustHost = document.getElementById('custMSCustomer');
  const custBUHost   = document.getElementById('custMSBU');
  const buBUHost     = document.getElementById('buMSBU');
  const buChHost     = document.getElementById('buMSChannel');
  if(custCustHost && custBUHost){
    const customers = state.data.map(r=>r.s).filter(Boolean);
    const bus       = state.data.map(r=>r.b).filter(Boolean);
    custSecMS = {
      cust: buildSimpleMS(custCustHost, 'Customer', customers, state.cust2.customers, paintCustTable),
      bu:   buildSimpleMS(custBUHost,   'Region', bus, state.cust2.bus, paintCustTable),
    };
  }
  if(buBUHost && buChHost){
    const bus  = state.data.map(r=>r.b).filter(Boolean);
    const chans = state.data.map(r=>r.ch).filter(Boolean);
    buSecMS = {
      bu: buildSimpleMS(buBUHost,  'Region', bus,  state.bu2.bus, paintBUTable),
      ch: buildSimpleMS(buChHost,  'Channel',       chans, state.bu2.channels, paintBUTable),
    };
  }
}
function buildAllFilters(){
  const labels = { customer:'Customer', bu:'Region', invoiceType:'Invoice Type', status:'Invoice_Status', bucket:'Ageing Bucket', paymentType:'Payment Type', channel:'Channel', paymentTerm:'Payment Term' };
  Object.keys(labels).forEach(key=>{
    const host = document.querySelector(`#msContainer [data-key="${key}"]`);
    msInstances[key] = buildMultiSelect(host, labels[key], key);
  });
  buildSectionFilters();
  document.addEventListener('click', e=>{
    if(!e.target.closest('.ms-wrap')) document.querySelectorAll('.ms-pop.open').forEach(p=>p.classList.remove('open'));
  });
}

// ===== Refresh & wire-up =====
function refresh(){ recompute(); paintKPIs(); paintCharts(); paintCustTable(); paintBUTable(); }

function wireDateChips(){
  // Only attach to range chips (those with data-r) — skip the Clear All chip
  document.querySelectorAll('#dateChips .chip[data-r]').forEach(c=> c.addEventListener('click', ()=>{
    document.querySelectorAll('#dateChips .chip[data-r]').forEach(x=>x.classList.remove('active'));
    c.classList.add('active');
    state.dateRange = c.dataset.r;
    document.getElementById('dateCustom').classList.toggle('hidden', state.dateRange!=='custom');
    refresh();
  }));
  ['dateFrom','dateTo'].forEach(id=>{
    document.getElementById(id).addEventListener('change', e=>{
      state[id] = e.target.value;
      // Auto-switch to Custom when user picks dates manually
      if(state.dateRange !== 'custom'){
        state.dateRange = 'custom';
        document.querySelectorAll('#dateChips .chip[data-r]').forEach(x=>x.classList.toggle('active', x.dataset.r==='custom'));
        document.getElementById('dateCustom').classList.remove('hidden');
      }
      refresh();
    });
  });
}
function wireMoreFilters(){
  const btn = document.getElementById('btnMoreFilters');
  const extra = document.getElementById('msExtra');
  if(!btn || !extra) return;
  btn.addEventListener('click', ()=>{
    const willShow = extra.classList.contains('hidden');
    extra.classList.toggle('hidden', !willShow);
    btn.textContent = willShow ? '− Less filters' : '＋ More filters';
    btn.classList.toggle('active', willShow);
  });
}
function wireSegments(){
  document.querySelectorAll('#topSeg .seg-btn').forEach(b=> b.addEventListener('click', ()=>{ document.querySelectorAll('#topSeg .seg-btn').forEach(x=>x.classList.remove('active')); b.classList.add('active'); state.topMetric = b.dataset.m; paintCharts(); }));
  document.querySelectorAll('#chSeg .seg-btn').forEach(b=> b.addEventListener('click', ()=>{ document.querySelectorAll('#chSeg .seg-btn').forEach(x=>x.classList.remove('active')); b.classList.add('active'); state.chMetric = b.dataset.m; paintCharts(); }));
  document.querySelectorAll('#currencySeg .seg-btn').forEach(b=> b.addEventListener('click', ()=>{ document.querySelectorAll('#currencySeg .seg-btn').forEach(x=>x.classList.remove('active')); b.classList.add('active'); state.currency = b.dataset.cu; refresh(); }));
}
function wireTables(){
  document.getElementById('custBody').addEventListener('click', e=>{
    const tr = e.target.closest('tr.parent-row'); if(!tr) return;
    const c = decodeURIComponent(tr.dataset.c||'');
    if(state.expandedCust.has(c)) state.expandedCust.delete(c); else state.expandedCust.add(c);
    paintCustTable();
  });
  document.getElementById('buBody').addEventListener('click', e=>{
    const tr = e.target.closest('tr.parent-row'); if(!tr) return;
    const b = decodeURIComponent(tr.dataset.bu||'');
    if(state.expandedBU.has(b)) state.expandedBU.delete(b); else state.expandedBU.add(b);
    paintBUTable();
  });
  document.getElementById('custFilter').addEventListener('input', ()=> paintCustTable());
  const buF = document.getElementById('buFilter'); if(buF) buF.addEventListener('input', ()=> paintBUTable());
  // Customer-section Clear / Excel
  const custClear = document.getElementById('custClear');
  if(custClear) custClear.addEventListener('click', ()=>{
    state.cust2.customers.length=0; state.cust2.bus.length=0;
    document.getElementById('custFilter').value='';
    if(custSecMS){ custSecMS.cust && custSecMS.cust.reset(); custSecMS.bu && custSecMS.bu.reset(); }
    _resetGlobalSearch();
    paintCustTable();
  });
  const custXlsx = document.getElementById('custXlsx');
  if(custXlsx) custXlsx.addEventListener('click', ()=> downloadCustomersXlsx());
  // BU-section Clear / Excel
  const buClear = document.getElementById('buClear');
  if(buClear) buClear.addEventListener('click', ()=>{
    state.bu2.bus.length=0; state.bu2.channels.length=0;
    if(buF) buF.value='';
    if(buSecMS){ buSecMS.bu && buSecMS.bu.reset(); buSecMS.ch && buSecMS.ch.reset(); }
    _resetGlobalSearch();
    paintBUTable();
  });
  const buXlsx = document.getElementById('buXlsx');
  if(buXlsx) buXlsx.addEventListener('click', ()=> downloadBUXlsx());
  // Dashboard / PDD / Bank Excel buttons
  const dashXlsx = document.getElementById('dashXlsx'); if(dashXlsx) dashXlsx.addEventListener('click', ()=> downloadDashboardXlsx());
  const pddXlsx  = document.getElementById('pddXlsx');  if(pddXlsx)  pddXlsx.addEventListener('click',  ()=> downloadPDDXlsx());
  const bankXlsx = document.getElementById('bankXlsx'); if(bankXlsx) bankXlsx.addEventListener('click', ()=> downloadBankXlsx());
}
// ===== Tabs: show ONLY the matching sections, hide the rest =====
function showTab(key){
  if(!key) key = 'dashboard';
  // ============ ACCESS MATRIX / USER MANAGEMENT — NO REDIRECT ============
  // Earlier versions had a "guard" here that bounced the user back to the
  // Overview tab when neither acmState.isAdmin nor the DOM-visibility signal
  // was positive. That redirect could fire in real-world races (e.g. the user
  // clicks the tab before applyAccessControl() finishes resolving identity,
  // or applyAccessControl() errors mid-flight and never sets the state). The
  // resulting bug — "click User Management, get bounced to Overview" — is the
  // exact symptom Sainath reports.
  //
  // The fix: REMOVE the redirect entirely. If the user clicked the tab, show
  // the tab. Security is still enforced at two layers below us:
  //   1) applyAccessControl() physically removes the sidebar tab AND the
  //      [data-section="acm"] nodes from the DOM for confirmed non-admins —
  //      so a non-admin can't even click into ACM in the first place.
  //   2) The backend `acmList` route in code.gs calls isAdmin_() and returns
  //      `{ ok:false, error:'Forbidden — admin only' }` to anyone else, so
  //      even if a non-admin somehow forces the section visible they see a
  //      red error message, not actual user data.
  //
  // The only thing we do here is FORCE the section visible, defeating any
  // racing `display:none !important` CSS rule. Belt-and-braces in 3 layers:
  //   (a) strip .hidden-until-admin from the tab + every acm section node,
  //   (b) set inline display via setProperty('important'), and
  //   (c) install a 3-frame requestAnimationFrame watchdog that re-applies
  //       (a)+(b) if any other code races to re-hide the section in this paint.
  if (key === 'acm') {
    var _acmTabEl = document.querySelector('.tab-item[data-target="acm"]');
    var _acmTabVisible = !!(_acmTabEl && !_acmTabEl.classList.contains('hidden-until-admin'));
    var _acmStateAdmin = (typeof acmState !== 'undefined' && acmState.isAdmin === true);
    // Trust the click: if the user clicked the tab, the tab must have been in
    // the DOM and clickable, which means applyAccessControl() let them through
    // (or the deployment is local, in which case there's no auth to enforce
    // anyway and the backend acmList will fail safely). Re-sync state so any
    // downstream code that still reads acmState.isAdmin gets the right answer.
    if (typeof acmState !== 'undefined' && !_acmStateAdmin) {
      acmState.isAdmin = true;
    }
    // (a) Strip the gate class from the tab + every acm section node.
    if (_acmTabEl) _acmTabEl.classList.remove('hidden-until-admin');
    document.querySelectorAll('[data-section="acm"]').forEach(function(sec){
      sec.classList.remove('hidden-until-admin');
      // (b) Force display via setProperty with 'important' priority. A plain
      // assignment would lose to any leftover `display:none !important` from
      // another stylesheet (print rules, utility classes, etc.).
      sec.style.setProperty('display', 'block', 'important');
    });
    // (c) Watchdog: re-flip up to 3 frames if anything races to re-hide.
    var _acmRetries = 0;
    var _acmWatchdog = function(){
      var sec = document.getElementById('acmSection');
      if (!sec) return;
      var cs = window.getComputedStyle(sec);
      if (cs.display === 'none' && _acmRetries < 3) {
        _acmRetries++;
        sec.classList.remove('hidden-until-admin');
        sec.style.setProperty('display', 'block', 'important');
        requestAnimationFrame(_acmWatchdog);
      }
    };
    requestAnimationFrame(_acmWatchdog);
    // Diagnostic — drop a clear breadcrumb in the console so future reports
    // can be triaged at a glance.
    try {
      console.info('[acm] showTab allow path entered (no-redirect mode)',
        { tabVisible: _acmTabVisible, stateAdmin: _acmStateAdmin,
          isLocal: !window.__SERVED_BY_APPS_SCRIPT__ });
    } catch(_){}
  }
  state.activeTab = key;
  // Toggle section visibility
  document.querySelectorAll('[data-section]').forEach(el=>{
    // Never reveal the ACM section to a non-admin, even if something else asks.
    // Mirror the same dual signal used by the tab guard above: trust state OR
    // the live DOM gate. The section itself carries .hidden-until-admin until
    // applyAccessControl() lifts it for a confirmed admin, so if the class is
    // already gone we know admin was verified at some point in this session.
    if (el.dataset.section === 'acm') {
      // For ACM specifically, when it's the active tab, set display via
      // setProperty with 'important' priority. A plain `el.style.display = ''`
      // would clear any inline rule and let a leftover `display:none !important`
      // from another stylesheet win the cascade. The "non-admin" gating is
      // handled at applyAccessControl() time (the section is physically
      // removed from the DOM for non-admins) AND at the backend acmList route
      // (returns 403 to non-admins). So at this point in the code path,
      // simply mirror the requested visibility.
      if (el.dataset.section === key) {
        // Strip the gate class once more for safety, then force visible.
        el.classList.remove('hidden-until-admin');
        el.style.setProperty('display', 'block', 'important');
      } else {
        el.style.display = 'none';
      }
      return;
    }
    el.style.display = (el.dataset.section === key) ? '' : 'none';
  });
  // Highlight the active sidebar item
  document.querySelectorAll('.tab-item').forEach(t=>{
    t.classList.toggle('active', t.dataset.target===key);
  });
  // If a child of AR Activity is now active, force-open the dropdown
  // and highlight the parent toggle so the user can see context.
  const __arTog = document.getElementById('arActivityToggle');
  if (__arTog) {
    const __childActive = (key === 'followups' || key === 'worklist' || key === 'statement' || key === 'pocs' || key === 'workflows');
    __arTog.classList.toggle('has-active-child', __childActive);
    if (__childActive) {
      __arTog.classList.add('open');
      const __arKids = document.getElementById('arActivityChildren');
      if (__arKids) __arKids.classList.remove('hidden');
    }
  }
  // KPI strip + Filters strip are only relevant on Overview and Reports.
  // Every other tab (Customer & Region, PDD, Bank Receipts, Follow-ups,
  // Activity Log, Worklist, User Management) hides them so the user sees only
  // that tab's own UI.
  var skp = document.getElementById('stickyKPIs');
  var sfl = document.getElementById('stickyFilters');
  var showStrips = (key === 'dashboard' || key === 'reports');
  if (skp) skp.style.display = showStrips ? '' : 'none';
  if (sfl) sfl.style.display = showStrips ? '' : 'none';
  // Reset scroll position so the new tab starts from the top
  window.scrollTo({ top:0, behavior:'instant' in window ? 'instant' : 'auto' });
  // Chart.js canvases that were display:none can't size themselves — resize after paint
  requestAnimationFrame(()=>{
    try {
      // First, flush any charts we queued while their canvas was hidden.
      // makeOrUpdate() deferred them; now that the tab is visible, create them.
      if (typeof _flushChartQueue === 'function') _flushChartQueue();
      Object.values(charts||{}).forEach(c=>{ try{ c && c.resize && c.resize(); }catch(_){ } });
    } catch(_){}
  });
  // (Re)build Follow-ups filters every time the tab is opened —
  // state.data may have just loaded after the user clicked this tab.
  if (key === 'followups') {
    if ((state.data||[]).length === 0) {
      const sb = document.getElementById('fuStatusBar');
      if (sb) sb.innerHTML = '<span style="color:#b91c1c">Waiting for live AR data to load — switch to Overview, wait for the spinner to finish, then come back here.</span>';
    } else {
      buildFollowUpFilters();
    }
  }
  if (key === 'activity' && !window._alLoaded) {
    window._alLoaded = true;
    loadActivityLog();
  }
  // Every time the ACM tab is opened, re-render the tabs-granted checkbox
  // list from the sidebar. This keeps the form in sync if new tabs were
  // added to the sidebar since page load (no-op if sidebar not in DOM).
  // Defense in depth vs. the boot-time render.
  if (key === 'acm') { try { renderAcmTabsCheckboxes(); } catch(_){} }
  if (key === 'acm' && !window._acmLoaded) {
    // Always trigger acmLoad when the user navigates to ACM. Auth is
    // enforced at the backend (acmList route returns 403 to non-admins),
    // and the front-end renders the error inline so the user knows why.
    // No state/visibility gate here — earlier dual-signal logic could fail
    // when applyAccessControl() hadn't resolved yet, leaving the table
    // stuck on "Loading…" indefinitely.
    window._acmLoaded = true;
    acmLoad();
  }
  if (key === 'worklist' && !window._wlLoaded) {
    window._wlLoaded = true;
    try { wlLoad(); } catch(_){}
    try { wlLoadDaily(); } catch(_){}
  }
  // Customer POCs + Internal Stakeholders share the "Contacts &
  // Stakeholders" page — one sidebar tab, one merged table. pocLoad()
  // fetches BOTH data sources in parallel and renders them together with
  // a Type column so we no longer need a separate isLoad() call here.
  if (key === 'pocs' && !window._pocsLoaded) {
    window._pocsLoaded = true;
    try { pocLoad(); } catch(_){}
    try { if (typeof isLoad === 'function') isLoad(); } catch(_){}
  }
  // Workflows: same lazy-load pattern. If user is on the Queue sub-tab we
  // also refresh the queue so status changes from other admins show up.
  if (key === 'workflows') {
    if (!window._wfLoaded) {
      window._wfLoaded = true;
      try { wfLoad(); } catch(_){}
    }
    if (wfState && wfState.tab === 'queue') { try { wfQueueLoad(); } catch(_){} }
  }
}
function wireTabs(){
  document.querySelectorAll('.tab-item').forEach(n=> n.addEventListener('click', ()=>{
    showTab(n.dataset.target);
  }));
  // AR Activity collapsible group — parent is not a real tab, just a toggle.
  const arTog = document.getElementById('arActivityToggle');
  const arKids = document.getElementById('arActivityChildren');
  if (arTog && arKids) {
    arTog.addEventListener('click', () => {
      const willOpen = !arTog.classList.contains('open');
      arTog.classList.toggle('open', willOpen);
      arKids.classList.toggle('hidden', !willOpen);
    });
    // Start COLLAPSED so the sidebar is shorter and the caret arrow signals
    // there's more inside — user expands explicitly. The caret is styled
    // larger + accent-colored so the affordance is unmistakable.
    arTog.classList.remove('open');
    arKids.classList.add('hidden');
  }
  // Initial render: only Overview visible
  showTab(state.activeTab || 'dashboard');
}
// Scroll-spy is incompatible with show/hide tabs — keep as a no-op so existing
// boot() call doesn't error.
function wireScrollSpy(){ /* disabled: tabs now show only one section at a time */ }
// Clears the topbar `#globalSearch` input AND fans the empty value out to
// the per-section search inputs (custFilter / buFilter / pddFilter / bankFilter)
// by dispatching the same `input` event wireGlobalSearch() already listens for.
function _resetGlobalSearch(){
  const g = document.getElementById('globalSearch');
  if(g){
    g.value = '';
    g.dispatchEvent(new Event('input', { bubbles:true }));
  }
}
function clearAll(){
  Object.values(msInstances).forEach(i=>i.reset());
  state.dateRange='all';
  state.dateFrom=null; state.dateTo=null;
  // Clear the date input controls too
  const df = document.getElementById('dateFrom'); if(df) df.value = '';
  const dt = document.getElementById('dateTo');   if(dt) dt.value = '';
  const cf = document.getElementById('custFilter'); if(cf) cf.value = '';
  _resetGlobalSearch();
  document.querySelectorAll('#dateChips .chip[data-r]').forEach(x=>x.classList.toggle('active',x.dataset.r==='all'));
  document.getElementById('dateCustom').classList.add('hidden');
  state.expandedCust.clear(); state.expandedBU.clear();
  // Reset Reports selection to the first row (Combined Business)
  state.activeReport = 'combined';
  document.querySelectorAll('#reportList .report-row').forEach(r=>{
    const isActive = r.dataset.rt === 'combined';
    r.classList.toggle('active', isActive);
    const radio = r.querySelector('input[type=radio]');
    if(radio) radio.checked = isActive;
  });
  refresh();
}
function wirePrint(){
  const btn = document.getElementById('btnPrint');
  if(!btn) return;
  btn.addEventListener('click', ()=>{ window.print(); });
}
function wireHardRefresh(){
  const btn = document.getElementById('btnHardRefresh');
  if(!btn) return;
  btn.addEventListener('click', async ()=>{
    const icon = btn.querySelector('.hr-icon') || btn;
    icon.classList.add('hr-spin');
    btn.setAttribute('data-tip', 'Hard Refresh — reloading…');
    // Clear in-memory caches so the next paint pulls fresh data
    try { window._alLoaded = false; } catch(_){}
    try { window._acmLoaded = false; } catch(_){}
    try { window._wlLoaded = false; } catch(_){}
    try { Object.keys(charts||{}).forEach(k=>{ try{ charts[k].destroy && charts[k].destroy(); }catch(_){} delete charts[k]; }); } catch(_){}
    // If a live URL is configured, first purge the server-side CacheService
    // entry so serveData_ re-reads the sheet, then force a fresh JSONP pull.
    // Otherwise just recompute from whatever data is in memory.
    const urlKey = ('LS_KEY_URL' in window) ? LS_KEY_URL : 'fynd_ar_live_url';
    const liveUrl = (typeof localStorage !== 'undefined') ? (window.__DATA_URL__ || localStorage.getItem(urlKey) || '').trim() : '';
    if (typeof liveFetch === 'function' && liveUrl) {
      // Purge the server-side cache (best-effort; ignore failures).
      try {
        var sep = liveUrl.indexOf('?')>=0 ? '&' : '?';
        if (typeof jsonpFetch === 'function') { await jsonpFetch(liveUrl + sep + 'action=dataRefresh', 30000); }
      } catch(_){}
      try { await liveFetch(true); } catch(_){ try{ refresh(); }catch(__){} }
    } else {
      try { refresh(); } catch(_){}
    }
    setTimeout(()=>{
      icon.classList.remove('hr-spin');
      btn.setAttribute('data-tip', 'Hard Refresh — purge server cache & reload everything');
    }, 1200);
  });
}
function wireClearAll(){
  const btnFilter = document.getElementById('btnClearAllFilter');
  if(btnFilter) btnFilter.addEventListener('click', clearAll);
  const btnChip = document.getElementById('btnClearAllChip');
  if(btnChip) btnChip.addEventListener('click', clearAll);
  // (Refresh icon removed — auto-refresh handles re-rendering.)
  const btnRefresh = document.getElementById('btnRefresh');
  if(btnRefresh) btnRefresh.addEventListener('click', ()=>{ refresh(); });
}
/* CSV upload removed — dashboard is live-only via Apps Script JSONP */
// ----------------------------------------------------------------
// Header-tolerant field picker. Normalises both the row's keys and
// the candidate names by lower-casing and stripping every non-alnum
// character, so "PDD_Booked", "PDD Booked", "pddbooked", "pdd booked"
// all resolve to the same column. This is what makes the dashboard
// resilient to small naming differences in the source Google Sheet.
// ----------------------------------------------------------------
const __keyNorm = (s)=> String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
const __rowIndexCache = new WeakMap();
function pickField(row, candidates){
  if(!row) return '';
  let idx = __rowIndexCache.get(row);
  if(!idx){
    idx = {};
    for(const k in row){ idx[__keyNorm(k)] = row[k]; }
    __rowIndexCache.set(row, idx);
  }
  for(let i=0;i<candidates.length;i++){
    const v = idx[__keyNorm(candidates[i])];
    if(v !== undefined && v !== null && v !== '') return v;
  }
  // Second pass — return even empty/null if the key exists, so caller can decide
  for(let i=0;i<candidates.length;i++){
    const k = __keyNorm(candidates[i]);
    if(k in idx) return idx[k] == null ? '' : idx[k];
  }
  return '';
}
// ===== AR row mapper (used by CSV upload AND live sync) =====
function mapARRow(r){
  return {
    ci:String(r['Company ID']||''), s:String(r['Seller_Name']||r['Seller Name']||''), b:String(r['Business']||''), ch:String(r['Channel']||''), tt:String(r['Transaction_Type']||''),
    in:String(r['Invoice_No']||''), it:String(r['Invoice_Type']||''), d:normD(r['Invoice_Date']), dd:normD(r['Due_Date']),
    ia:N(r['Invoice_Amount']), os:N(r['Outstanding_Amount']), cld:N(r['Company_Level_Due']||r['Company Level Due']||r['Company_level_due']), dy:Math.round(N(r['Days'])), bk:String(r['Aging Bucket']||''), st:String(r['STATUS']||''),
    co:N(r['TOTAL COLLECTIONS']), tds:N(r['TDS Deducted by Client']), cn:N(r['Credit Note Value']), cnn:String(r['Credit Note No']||''),
    cod:N(r['COD Adjustments']), bnk:N(r['Bank Charges']), pdd:N(r['PDD Amount']), ror:N(r['Others or Round Off']),
    ps:N(r['Payment split Amt']), pb:N(r['Payment In Bank']), rd:normD(r['Receipt Date']),
    br:String(r['Bank_Ref_No_UTR']||''), oa:String(r['On account received_alwaysFIFO']||''), pt:String(r['Payment_Type']||''), ptr:String(r['Payment Term']||''), rm:String(r['Revenue_in_Month']||''),
  };
}
// Drop spreadsheet-error rows (#N/A, #REF! etc.) — applied to AR_Data feed
const ERR_TOKENS = new Set(['#N/A','#REF!','#VALUE!','#NAME?','#DIV/0!','#NULL!','#ERROR!','N/A','NA']);
function rowHasErr(r){
  for(const k in r){
    const v = r[k]; if(v==null) continue;
    const s = String(v).trim().toUpperCase();
    if(ERR_TOKENS.has(s)) return true;
  }
  return false;
}
function N(x){ if(!x) return 0; const s=String(x).replace(/[,₹\s]/g,''); const n=parseFloat(s); return isNaN(n)?0:n; }
const MONTH_MAP = {jan:'01',feb:'02',mar:'03',apr:'04',may:'05',jun:'06',jul:'07',aug:'08',sep:'09',sept:'09',oct:'10',nov:'11',dec:'12'};
function normD(x){
  if(!x && x!==0) return '';
  const s=String(x).trim();
  if(!s) return '';
  // 1) ISO YYYY-MM-DD or YYYY-M-D (also handles datetime)
  let m=s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if(m) return `${m[1]}-${m[2].padStart(2,'0')}-${m[3].padStart(2,'0')}`;
  // 2) D-MMM-YYYY or D-MMM-YY  (e.g. 02-Apr-2025, 2-Apr-24)
  m=s.match(/^(\d{1,2})[-/\s]([A-Za-z]{3,9})[-/\s](\d{2}|\d{4})$/);
  if(m){
    const mm = MONTH_MAP[m[2].toLowerCase().slice(0,3)];
    let yr = m[3]; if(yr.length===2) yr = (parseInt(yr,10) >= 70 ? '19' : '20') + yr;
    if(mm) return `${yr}-${mm}-${m[1].padStart(2,'0')}`;
  }
  // 3) D-M-YYYY or D/M/YYYY (numeric day/month)
  m=s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
  if(m) return `${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`;
  // 4) Last resort — try Date.parse and format
  const dt = new Date(s);
  if(!isNaN(dt.getTime())){
    const yr=dt.getFullYear(), mm=String(dt.getMonth()+1).padStart(2,'0'), dd=String(dt.getDate()).padStart(2,'0');
    return `${yr}-${mm}-${dd}`;
  }
  return '';
}
// Display-format YYYY-MM-DD → DD/MM/YYYY for CFO-grade exports
function fmtDateOut(s){ if(!s) return ''; const m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? `${m[3]}/${m[2]}/${m[1]}` : String(s); }
function r2(n){ return Math.round((+n||0)*100)/100; }
// Append a "GRAND TOTAL" row that sums numeric columns. labelCol = column to put the "GRAND TOTAL" text in.
function appendGrandTotal(rows, labelCol, opts){
  if(!rows || rows.length===0) return rows;
  opts = opts || {};
  const skip = new Set(opts.skip || []);   // columns to leave blank
  const cols = Object.keys(rows[0]);
  const tot = {};
  cols.forEach(c=>{ tot[c] = ''; });
  tot[labelCol] = 'GRAND TOTAL';
  cols.forEach(c=>{
    if(c === labelCol) return;
    if(skip.has(c)) return;
    let sum = 0, hasNum = false;
    for(const r of rows){
      const v = r[c];
      if(typeof v === 'number'){ sum += v; hasNum = true; }
      else if(typeof v === 'string' && v !== '' && !isNaN(parseFloat(v.replace(/,/g,'')))){
        sum += parseFloat(v.replace(/,/g,'')); hasNum = true;
      }
    }
    if(hasNum) tot[c] = r2(sum);
  });
  // Recompute weighted "Collection %" if both Collections & Invoice Amount sums exist
  if('Collection %' in tot && 'Collections' in tot && 'Invoice Amount' in tot && +tot['Invoice Amount']>0){
    tot['Collection %'] = +(((+tot['Collections'])/(+tot['Invoice Amount'])*100).toFixed(2));
  }
  // For DSO in days at the grand-total level, take the outstanding-weighted average of the per-row DSO values
  // (Each row's DSO is already scaled to that customer/BU's first-invoice-date, so weighted average is correct.)
  if('DSO in days' in tot && 'Outstanding' in tot){
    let wOS=0, wSum=0;
    rows.forEach(r=>{
      const os = Math.abs(+r['Outstanding']||0);
      const dso = +r['DSO in days']||0;
      if(os>0){ wOS += os; wSum += dso*os; }
    });
    tot['DSO in days'] = wOS>0 ? Math.round(wSum/wOS) : 0;
  }
  return rows.concat([tot]);
}

// ===== Downloads =====
function buildCustReport(){
  const arr = buildCustomerAgg();
  const out = [];
  arr.forEach(c=>{
    const cDays = _custDsoDays(c.cid || '', c.name);
    c.busArr.forEach(b=>{
      out.push({
        'CID': b.cid || c.cid || '',
        'Customer Name': c.name,
        'Region': b.bu,
        'Invoices': b.inv,
        'Invoice Amount': r2(b.ia),
        'Collections': r2(b.col||0),
        'Outstanding': r2(b.os),
        'DSO in days': b.ia>0 ? Math.round((b.os/b.ia)*cDays) : 0,
        'TDS Deducted': r2(b.tds),
        'CN Value': r2(b.cn),
        'Posting Done': b.post,
        'Collection %': b.ia>0 ? +((b.col/b.ia*100).toFixed(2)) : 0,
      });
    });
  });
  // Sort: Business Unit A-Z (primary), then Outstanding desc within BU
  out.sort((a,b)=> (a['Region']||'').localeCompare(b['Region']||'')
                    || Math.abs(b['Outstanding']||0) - Math.abs(a['Outstanding']||0));
  return appendGrandTotal(out, 'CID', { skip:['Customer Name','Region','DSO in days'] });
}
function buildBUReport(){
  const rows = buildBUAgg().map(b=>({
    'Region': b.bu,
    'Invoices': b.inv,
    'Invoice Amount': r2(b.ia),
    'Collections': r2(b.col||0),
    'Outstanding': r2(b.os),
    'DSO in days': _weightedDSO((b.custArr||[]).map(c=>({ ci:c.cid||'', name:c.name, ia:c.ia, os:c.os }))),
    'Collection %': b.ia>0 ? +((b.col/b.ia*100).toFixed(2)) : 0,
  }));
  // Sort Business Unit A-Z (primary), then Outstanding desc
  rows.sort((a,b)=> (a['Region']||'').localeCompare(b['Region']||'')
                     || Math.abs(b['Outstanding']||0) - Math.abs(a['Outstanding']||0));
  return appendGrandTotal(rows, 'Region');
}
function buildFullReport(){
  // Union of invoice-date-filtered rows and receipt-date-filtered rows
  const merged = new Map();
  (state.rowsInv||[]).forEach((r,i)=> merged.set((r.in||'_')+'|'+(r.s||'')+'|'+(r.d||'')+'|i'+i, r));
  (state.rowsCol||[]).forEach((r,i)=> merged.set((r.in||'_')+'|'+(r.s||'')+'|'+(r.rd||'')+'|c'+i, r));
  // Dedup by physical identity
  const seen = new Set();
  const out = [];
  Array.from(merged.values()).forEach(r=>{ if(!seen.has(r)){ seen.add(r); out.push(r); } });
  // Sort: Business (BU) A-Z, then Customer A-Z, then Invoice_Date asc
  out.sort((a,b)=> (a.b||'').localeCompare(b.b||'') || (a.s||'').localeCompare(b.s||'') || (a.d||'').localeCompare(b.d||''));
  return out.map(r=>({
    'Company ID': r.ci, 'Seller_Name': r.s, 'Business': r.b, 'Channel': r.ch, 'Transaction_Type': r.tt,
    'Invoice_No': r.in, 'Invoice_Type': r.it,
    'Invoice_Date': fmtDateOut(r.d), 'Due_Date': fmtDateOut(r.dd),
    'Invoice_Amount': r2(r.ia), 'Outstanding_Amount': r2(r.os), 'Days': r.dy, 'Aging Bucket': r.bk, 'STATUS': r.st,
    'TOTAL COLLECTIONS': r2(r.co), 'TDS Deducted by Client': r2(r.tds), 'Credit Note Value': r2(r.cn), 'Credit Note No': r.cnn,
    'COD Adjustments': r2(r.cod), 'Bank Charges': r2(r.bnk), 'PDD Amount': r2(r.pdd), 'Others or Round Off': r2(r.ror),
    'Payment split Amt': r2(r.ps), 'Payment In Bank': r2(r.pb), 'Receipt Date': fmtDateOut(r.rd),
    'Bank_Ref_No_UTR': r.br, 'On account received_alwaysFIFO': r.oa, 'Payment_Type': r.pt, 'Payment Term': r.ptr, 'Revenue_in_Month': r.rm,
  }));
}
function buildDSOReport(){
  // Per-period AND per-Business-Unit breakdown (each period repeats across BUs)
  const rows = buildDSOByBU();
  const out = rows.map(r=>({
    'Period': r.period,
    'Period Type': state.dsoPeriod,
    'Region': r.bu,
    'Number of Invoices': r.count,
    'Total Invoiced (INV)': r2(r.invoiced),
    'Total Collections': r2(r.collections),
    'Outstanding': r2(r.os),
    'DSO in days': r.dso,
  }));
  // Sort by Period asc, then Business Unit A-Z (chronological with BU grouped within period)
  out.sort((a,b)=> (a.Period||'').localeCompare(b.Period||'') || (a['Region']||'').localeCompare(b['Region']||''));
  // Grand-total DSO = outstanding-weighted average of per-row DSOs (each already CID-weighted)
  let wOS=0, wSum=0;
  out.forEach(r=>{ const os=Math.abs(+r['Outstanding']||0), d=+r['DSO in days']||0; if(os>0){ wOS+=os; wSum+=d*os; } });
  const wDso = wOS>0 ? Math.round(wSum/wOS) : 0;
  const withTotals = appendGrandTotal(out, 'Period', { skip:['Period Type','Region','DSO in days'] });
  if(withTotals.length){ withTotals[withTotals.length-1]['DSO in days'] = wDso; }
  return withTotals;
}
function buildDSODetail(){
  // Detail rows backing the DSO summary - INV-type invoice rows with period bucket
  return state.rowsInv.filter(r=>r.it==='INV').map(r=>({
    'Period': dsoBucket(r.d, state.dsoPeriod) || '—',
    'Invoice_No': r.in,
    'Customer': r.s,
    'Region': r.b,
    'Channel': r.ch,
    'Invoice_Date': r.d,
    'Due_Date': r.dd,
    'Invoice Amount': Math.round((+r.ia||0)*100)/100,
    'Collections': Math.round((+r.co||0)*100)/100,
    'Outstanding': Math.round((+r.os||0)*100)/100,
    'Days': r.dy,
    'Ageing Bucket': ageBucketFromDays(r.dy),
    'Status': r.st,
    'Payment Type': r.pt,
    'Receipt Date': r.rd,
    'Payment Term': r.ptr,
  })).sort((a,b)=> (a.Period||'').localeCompare(b.Period||'') || (a['Invoice_Date']||'').localeCompare(b['Invoice_Date']||''));
}
function buildTotalCollectionsReport(){
  // Per-period AND per-Business-Unit breakdown
  const rows = buildTotalCollectionsByBU();
  const out = rows.map(r=>({
    'Period': r.period,
    'Period Type': state.colPeriod,
    'Region': r.bu,
    'Number of Receipts': r.count,
    'Total Collections': r2(r.total),
  }));
  // Sort by Period asc, then Business Unit A-Z
  out.sort((a,b)=> (a.Period||'').localeCompare(b.Period||'') || (a['Region']||'').localeCompare(b['Region']||''));
  return appendGrandTotal(out, 'Period', { skip:['Period Type','Region'] });
}
// ===== Combined Business Report (3 sheets) =====
function buildCombinedSummaries(){
  return {
    bu:   buildBUReport(),
    cust: buildCustReport(),
    full: buildFullReport(),
  };
}

// ===== Ageing Pivot Reports =====
function _ageingPivot(rows, valueKey){
  // rows: array of source records; valueKey: 'os' or 'co'
  const piv = {}; // key = ci|s|b -> { CID, Customer, BU, buckets:{}, total }
  rows.forEach(r=>{
    const ci = r.ci || '—';
    const s  = r.s  || 'Unknown';
    const b  = r.b  || '—';
    const k  = ci + '|' + s + '|' + b;
    const bucket = ageBucketFromDays(r.dy);
    const v = +r[valueKey] || 0;
    if(!piv[k]) piv[k] = { CID: ci, 'Customer Name': s, 'Region': b, buckets:{}, total:0 };
    piv[k].buckets[bucket] = (piv[k].buckets[bucket]||0) + v;
    piv[k].total += v;
  });
  // Sort: Business Unit A-Z (primary), Total desc (secondary, largest to smallest)
  const arr = Object.values(piv).sort((a,b)=>
    (a['Region']||'').localeCompare(b['Region']||'')
    || Math.abs(b.total) - Math.abs(a.total)
  );
  const pivRows = arr.map(row=>{
    const out = { 'CID': row.CID, 'Customer Name': row['Customer Name'], 'Region': row['Region'] };
    AGE_ORDER.forEach(b=>{
      out[b] = Math.round(((row.buckets[b]||0))*100)/100;
    });
    out['Total'] = Math.round(row.total*100)/100;
    return out;
  });
  return appendGrandTotal(pivRows, 'CID', { skip:['Customer Name','Region'] });
}

function buildOutstandingAgeing(){
  // Filter Status = Open (case-insensitive) on INV-type rows
  const rows = state.rowsInv.filter(r=> (r.st||'').toLowerCase() === 'open');
  return _ageingPivot(rows, 'os');
}
function buildOutstandingAgeingDetail(){
  const rows = state.rowsInv.filter(r=> (r.st||'').toLowerCase() === 'open');
  return rows.map(r=>({
    'CID': r.ci, 'Customer': r.s, 'Region': r.b, 'Channel': r.ch,
    'Invoice_No': r.in, 'Invoice_Type': r.it,
    'Invoice_Date': r.d, 'Due_Date': r.dd,
    'Invoice Amount': Math.round((+r.ia||0)*100)/100,
    'Outstanding': Math.round((+r.os||0)*100)/100,
    'Days': r.dy, 'Ageing Bucket': ageBucketFromDays(r.dy),
    'Status': r.st, 'Payment Term': r.ptr,
  })).sort((a,b)=> (b['Outstanding']||0) - (a['Outstanding']||0));
}

function buildCollectionsAgeing(){
  // Use rowsCol (filtered by receipt date), value = co (collections)
  const rows = state.rowsCol.filter(r=> (+r.co||0) !== 0);
  return _ageingPivot(rows, 'co');
}
function buildCollectionsAgeingDetail(){
  const rows = state.rowsCol.filter(r=> (+r.co||0) !== 0);
  // Column order (per user spec):
  // A CID · B Customer · C Business Unit · D Channel · E Invoice_No
  // F Invoice_Date · G Invoice Amount · H Days · I Ageing Bucket · J Collection Amount · K Receipt_Date
  // L Bank Ref/UTR · M Payment Type (TDS removed)
  return rows.map(r=>({
    'CID': r.ci,
    'Customer': r.s,
    'Region': r.b,
    'Channel': r.ch,
    'Invoice_No': r.in,
    'Invoice_Date': r.d,
    'Invoice Amount': Math.round((+r.ia||0)*100)/100,
    'Days': r.dy,
    'Ageing Bucket': ageBucketFromDays(r.dy),
    'Collection Amount': Math.round((+r.co||0)*100)/100,
    'Receipt_Date': r.rd,
    'Bank Ref / UTR': r.br,
    'Payment Type': r.pt,
  })).sort((a,b)=> (b['Collection Amount']||0) - (a['Collection Amount']||0));
}

function buildTotalCollectionsDetail(){
  // Detail rows backing Total Collections summary - rows with receipts
  return state.rowsCol.filter(r=>(+r.co||0) !== 0).map(r=>({
    'Period': dsoBucket(r.rd, state.colPeriod) || '—',
    'Receipt_Date': r.rd,
    'Invoice_No': r.in,
    'Customer': r.s,
    'Region': r.b,
    'Channel': r.ch,
    'Invoice_Date': r.d,
    'Invoice_Type': r.it,
    'Invoice Amount': Math.round((+r.ia||0)*100)/100,
    'Collection Amount': Math.round((+r.co||0)*100)/100,
    'Bank Ref / UTR': r.br,
    'Payment Type': r.pt,
  })).sort((a,b)=> (a.Period||'').localeCompare(b.Period||'') || (a['Receipt_Date']||'').localeCompare(b['Receipt_Date']||''));
}
// ===== TDS Deducted by Client Report =====
// Per-invoice TDS detail for the AR sheet. Each row in the report
// corresponds to one AR row that has non-zero TDS. The FY tag is
// computed from the EARLIER of the Invoice Date and Receipt Date, per
// the stakeholder's accounting convention (TDS liability anchors to the
// earliest booking event). When only one date exists, that date drives
// the FY. Rows are sorted FY → CID → Invoice_No.
function _tdsFYFromDates(invDate, rcptDate){
  const valid = (s) => /^\d{4}-\d{2}-\d{2}/.test(String(s||''));
  let earliest = '';
  if (valid(invDate) && valid(rcptDate))      earliest = invDate < rcptDate ? invDate : rcptDate;
  else if (valid(invDate))                    earliest = invDate;
  else if (valid(rcptDate))                   earliest = rcptDate;
  if (!earliest) return 'FY —';
  const y = parseInt(earliest.slice(0,4), 10);
  const m = parseInt(earliest.slice(5,7), 10);
  const fyStart = (m >= 4) ? y : y - 1;
  const yy = (n) => String(n).slice(-2).padStart(2,'0');
  return 'FY ' + yy(fyStart) + '-' + yy(fyStart + 1);
}

function buildTDSDeductedReport(){
  // Source: state.data (mapARRow output from the AR_Data sheet). We
  // keep rows where TDS Deducted by Client is non-zero. Each row is
  // emitted as ONE report row — split-payment AR rows naturally show
  // their per-invoice TDS amount.
  const src = (state.data || []).filter(r => Math.abs(+r.tds||0) > 0.01);
  const out = src.map(r => {
    const ia   = +r.ia  || 0;
    const tds  = +r.tds || 0;
    // TDS Deducted % column dropped per stakeholder request — the
    // raw TDS amount + invoice amount are sufficient and the percentage
    // was cluttering the report with derived noise.
    return {
      'Financial Year':    _tdsFYFromDates(r.d, r.rd),
      'TDS Booked Date':   r.rd || r.d || '',
      'CID':               String(r.ci || ''),
      'Customer Name':     String(r.s  || ''),
      'Transaction Type':  String(r.tt || ''),
      'Invoice No':        String(r.in || ''),
      'Invoice Date':      r.d  || '',
      'Invoice Amount':    Math.round(ia * 100) / 100,
      'TDS Amount':        Math.round(tds * 100) / 100,
      'Receipt Split Amount': Math.round((+r.ps||0) * 100) / 100,
      'Receipt in Bank':   Math.round((+r.pb||0) * 100) / 100,
      'Receipt Date':      r.rd || '',
    };
  });
  // Sort: FY asc, then CID asc, then Invoice_No asc
  out.sort((a,b) => {
    return (a['Financial Year']||'').localeCompare(b['Financial Year']||'')
        || (a['CID']||'').localeCompare(b['CID']||'')
        || (a['Invoice No']||'').localeCompare(b['Invoice No']||'');
  });
  return appendGrandTotal(out, 'CID', {
    skip:['Customer Name','Transaction Type','Invoice No','Invoice Date',
          'TDS Booked Date','Financial Year','Receipt Date']
  });
}

// Per-FY summary: one row per Financial Year × CID × Customer with the
// total TDS amount the client deducted. Useful for the team to
// reconcile against Form 26AS.
function buildTDSDeductedSummary(){
  const src = (state.data || []).filter(r => Math.abs(+r.tds||0) > 0.01);
  const map = new Map();
  src.forEach(r => {
    const fy = _tdsFYFromDates(r.d, r.rd);
    const k  = fy + '||' + String(r.ci||'') + '||' + String(r.s||'');
    let agg = map.get(k);
    if (!agg){
      agg = {
        'Financial Year': fy,
        'CID': String(r.ci||''),
        'Customer Name': String(r.s||''),
        '# Invoices': 0,
        'Invoice Amount (Σ)': 0,
        'TDS Amount (Σ)': 0,
      };
      map.set(k, agg);
    }
    agg['# Invoices']           += 1;
    agg['Invoice Amount (Σ)']   += (+r.ia  || 0);
    agg['TDS Amount (Σ)']       += (+r.tds || 0);
  });
  const out = [...map.values()].map(a => ({
    'Financial Year':       a['Financial Year'],
    'CID':                  a['CID'],
    'Customer Name':        a['Customer Name'],
    '# Invoices':           a['# Invoices'],
    'Invoice Amount (Σ)':   Math.round(a['Invoice Amount (Σ)']*100)/100,
    'TDS Amount (Σ)':       Math.round(a['TDS Amount (Σ)']*100)/100,
  }));
  out.sort((a,b) =>
    (a['Financial Year']||'').localeCompare(b['Financial Year']||'')
    || (b['TDS Amount (Σ)']||0) - (a['TDS Amount (Σ)']||0)
  );
  return appendGrandTotal(out, 'CID', {
    skip:['Customer Name','Financial Year']
  });
}

// sheets: [{name, rows}] – multi-sheet support
async function downloadXLSX(sheets, name){
  if(!Array.isArray(sheets)) sheets = [{name:'Report', rows:sheets}];
  // Lazy-load XLSX (SheetJS) on first export — it's ~700 KB and not
  // needed on the initial dashboard paint.
  if (typeof window.ensureXLSX === 'function') { try { await window.ensureXLSX(); } catch(_){} }
  const wb = XLSX.utils.book_new();
  sheets.forEach(s=>{
    const ws = XLSX.utils.json_to_sheet(s.rows && s.rows.length ? s.rows : [{ Note:'No data' }]);
    XLSX.utils.book_append_sheet(wb, ws, (s.name||'Sheet').slice(0,31));
  });
  XLSX.writeFile(wb, name+'.xlsx');
}
// ===== Per-section "Generate Report" handlers =====
// Each one builds a STYLED Executive XLSX (same look as Reports & Downloads)
// of exactly the rows currently visible after the section's filters
// (date range, multi-selects, search) have been applied.
function _scopeLabelForGlobal(){
  const r = state.dateRange || 'all';
  if(r==='custom') return `${state.dateFrom||'…'} → ${state.dateTo||'…'}`;
  return ({today:'Today',month:'Monthly',quarter:'Quarterly',ytd:'Yearly',all:'All Time'})[r] || r;
}
async function _xlsxFromRows(rows, sheetName, fileName, title, scopeLabel){
  if(!rows || !rows.length){ alert('No rows match the current filters — nothing to export.'); return; }
  const stamp = new Date().toISOString().slice(0,10);
  const sheets = [{ name: sheetName, rows: rows }];
  // Fall back to the plain XLSX writer if ExcelJS isn't loaded yet.
  if(typeof ExcelJS === 'undefined'){
    if (typeof window.ensureXLSX === 'function') { try { await window.ensureXLSX(); } catch(_){} }
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, sheetName.slice(0,31));
    XLSX.writeFile(wb, fileName+'_'+stamp+'.xlsx');
    return;
  }
  downloadXLSX_executive(sheets, fileName+'_'+stamp, title || sheetName, scopeLabel || _scopeLabelForGlobal());
}
function downloadDashboardXlsx(){
  // Use the date-filtered AR rows that the dashboard currently shows
  const inv = state.rowsInv || [];
  const col = state.rowsCol || [];
  // Union, dedup by invoice no
  const seen = new Set();
  const merged = inv.concat(col).filter(r=>{ const k=r.in||(r.s+'|'+r.d+'|'+r.ia); if(seen.has(k))return false; seen.add(k); return true; });
  const out = merged.map(r=>({
    'Company ID':r.ci, 'Customer':r.s, 'Region':r.b, 'Channel':r.ch,
    'Invoice No':r.in, 'Invoice Type':r.it, 'Invoice Date':r.d, 'Due Date':r.dd,
    'Invoice Amount':r.ia, 'Outstanding':r.os, 'Days':r.dy, 'Aging Bucket':r.bk,
    'Status':r.st, 'Receipt Date':r.rd||'', 'Collected':r.co||0, 'Payment Type':r.pt||'',
    'Payment Term':r.ptr||''
  }));
  _xlsxFromRows(out, 'Dashboard_AR_Filtered', 'Fynd_AR_Dashboard_Filtered', 'Dashboard — AR (Filtered)');
}
function downloadCustomersXlsx(){
  // Reapply same filtering as paintCustTable
  const arr = buildCustomerAgg();
  const filter = (document.getElementById('custFilter').value||'').trim().toLowerCase();
  const selCust = state.cust2.customers.map(s=>String(s));
  const selBU   = state.cust2.bus.map(s=>String(s));
  let f = arr;
  if(selCust.length) f = f.filter(c=> selCust.indexOf(c.name)!==-1);
  if(selBU.length)   f = f.filter(c=> c.busArr.some(b=> selBU.indexOf(b.bu)!==-1));
  if(filter)         f = f.filter(c=> c.name.toLowerCase().includes(filter));
  const rows = [];
  f.forEach(c=>{
    const cDays = _custDsoDays(c.cid || '', c.name);
    const cDso  = c.total.ia>0 ? Math.round((c.total.os/c.total.ia)*cDays) : 0;
    rows.push({
      'Customer':c.name, 'Region':'(All)', 'Invoices':c.total.inv,
      'Invoice Amount':c.total.ia, 'Collections':c.total.col, 'Outstanding':c.total.os,
      'DSO (days)':cDso, 'Collection %': c.total.ia>0?+((c.total.col/c.total.ia)*100).toFixed(1):0
    });
    c.busArr.forEach(b=>{
      const bDso = b.ia>0 ? Math.round((b.os/b.ia)*cDays) : 0;
      rows.push({
        'Customer':'  ↳ '+c.name, 'Region':b.bu, 'Invoices':b.inv,
        'Invoice Amount':b.ia, 'Collections':b.col, 'Outstanding':b.os,
        'DSO (days)':bDso, 'Collection %': b.ia>0?+((b.col/b.ia)*100).toFixed(1):0
      });
    });
  });
  _xlsxFromRows(rows, 'Customers_Filtered', 'Fynd_Customers_Filtered', 'Customer-wise Breakdown (Filtered)');
}
function downloadBUXlsx(){
  let arr = buildBUAgg();
  const selBU = state.bu2.bus.map(s=>String(s));
  const selCh = state.bu2.channels.map(s=>String(s));
  const buQ   = ((document.getElementById('buFilter')||{}).value||'').trim().toLowerCase();
  if(selBU.length) arr = arr.filter(b=> selBU.indexOf(b.bu)!==-1);
  if(selCh.length){
    const buAllowed = new Set();
    state.rowsInv.concat(state.rowsCol).forEach(r=>{ if(selCh.indexOf(String(r.ch||''))!==-1) buAllowed.add(String(r.b||'—')); });
    arr = arr.filter(b=> buAllowed.has(b.bu));
  }
  if(buQ) arr = arr.filter(b=> b.bu.toLowerCase().includes(buQ));
  const rows = [];
  arr.forEach(b=>{
    const bDso = _weightedDSO((b.custArr||[]).map(c=>({ ci:c.cid||'', name:c.name, ia:c.ia, os:c.os })));
    rows.push({
      'Region':b.bu, 'Customer':'(All)', 'Customers':b.custCount, 'Invoices':b.inv,
      'Invoice Amount':b.ia, 'Collections':b.col, 'Outstanding':b.os, 'DSO (days)':bDso,
      'Collection %': b.ia>0?+((b.col/b.ia)*100).toFixed(1):0
    });
    (b.custArr||[]).forEach(c=>{
      const cDso = c.ia>0 ? Math.round((c.os/c.ia)*_custDsoDays(c.cid||'', c.name)) : 0;
      rows.push({
        'Region':'  ↳ '+b.bu, 'Customer':c.name, 'Customers':1, 'Invoices':c.inv,
        'Invoice Amount':c.ia, 'Collections':c.col, 'Outstanding':c.os, 'DSO (days)':cDso,
        'Collection %': c.ia>0?+((c.col/c.ia)*100).toFixed(1):0
      });
    });
  });
  _xlsxFromRows(rows, 'Regions_Filtered', 'Fynd_Regions_Filtered', 'Region Breakdown (Filtered)');
}
function downloadPDDXlsx(){
  const rows = (typeof getFilteredPDD==='function') ? getFilteredPDD() : (state.pdd||[]);
  const out = rows.map(r=>({
    'PDD Booked':r.qb||'', 'PDD Date':r.pd||'', 'Company ID':r.ci||'',
    'Customer':r.s||'', 'Business':r.b||'', 'Channel':r.ch||'', 'Invoice No':r.in||'',
    'Invoice Type':r.it||'', 'Invoice Date':r.d||'', 'Due Date':r.dd||'',
    'Invoice Amount':r.ia||0, 'Outstanding':r.os||0, 'Current PDD':r.cur||0,
    'PDD Reversed':r.rev||0, 'CC':r.cc||''
  }));
  _xlsxFromRows(out, 'PDD_Filtered', 'Fynd_PDD_Filtered', 'Provision for Doubtful Debts (Filtered)');
}
function downloadBankXlsx(){
  const rows = (typeof getFilteredBank==='function') ? getFilteredBank() : (state.bank||[]);
  const out = rows.map(r=>({
    'Receipt Date':r.rd||'', 'Bank':r.bk||'', 'Mapping Status':r.map||'', 'Business':r.b||'',
    'Company ID':r.ci||'', 'Company Name':r.cn||'',
    'Narration':r.nar||'', 'Razorpay/Stripe Narration':r.nar2||'',
    'Bank Date':r.bd||'', 'Amount Credited':r.amt||0, 'Valyx Status':r.vlx||''
  }));
  _xlsxFromRows(out, 'Bank_Receipts_Filtered', 'Fynd_BankReceipts_Filtered', 'Bank Receipts (Filtered)');
}

async function downloadCSV(sheets, name, title, scopeLabel){
  // Single CSV file with section headers (### Sheet ###) — director-grade
  if(!Array.isArray(sheets)) sheets = [{name:'Report', rows:sheets}];
  // Lazy-load XLSX for its sheet_to_csv helper (only if needed and
  // the library isn't already loaded).
  if (typeof XLSX === 'undefined' && typeof window.ensureXLSX === 'function') {
    try { await window.ensureXLSX(); } catch(_){}
  }
  const parts = [];
  // Executive header block
  const ts = new Date().toLocaleString('en-IN', { dateStyle:'medium', timeStyle:'short' });
  parts.push('Fynd · Receivables Insights');
  if(title) parts.push('Report,'+csvEsc(title));
  if(scopeLabel) parts.push('Period,'+csvEsc(scopeLabel));
  parts.push('Generated,'+csvEsc(ts));
  parts.push('Confidential — For Internal Use');
  parts.push('');
  // Sheets
  sheets.forEach((s, idx)=>{
    parts.push(`### ${s.name||'Sheet'} ###`);
    if(s.rows && s.rows.length){
      const ws = XLSX.utils.json_to_sheet(s.rows);
      parts.push(XLSX.utils.sheet_to_csv(ws));
    } else {
      parts.push('No data');
    }
    if(idx < sheets.length-1) parts.push('');
  });
  const blob = new Blob([parts.join('\n')], { type:'text/csv;charset=utf-8' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name+'.csv'; a.click();
}
function csvEsc(s){ s = String(s||''); if(/[",\n]/.test(s)) return '"'+s.replace(/"/g,'""')+'"'; return s; }

// ===== Executive-grade XLSX (multi-sheet, styled, frozen panes) =====
async function downloadXLSX_executive(sheets, name, title, scopeLabel){
  if(!Array.isArray(sheets)) sheets = [{name:'Report', rows:sheets}];
  // Lazy-load ExcelJS on first executive export — it's ~800 KB.
  if(typeof ExcelJS === 'undefined' && typeof window.ensureExcelJS === 'function'){
    try { await window.ensureExcelJS(); } catch(_){}
  }
  if(typeof ExcelJS === 'undefined'){ alert('Excel library failed to load. Please check your internet connection.'); return; }
  const wb = new ExcelJS.Workbook();
  wb.creator = 'Fynd Receivables Insights';
  wb.created = new Date();
  const ts = new Date().toLocaleString('en-IN', { dateStyle:'medium', timeStyle:'short' });

  // Color palette (ARGB)
  const COLOR = {
    brand:    'FF0F172A',   // slate-900
    accent:   'FF4F46E5',   // indigo-600 - column headers
    band:     'FFEEF2FF',   // indigo-50  - subtitle band
    grand:    'FF0F172A',   // slate-900  - GRAND TOTAL row
    grandTxt: 'FFFFFFFF',
    white:    'FFFFFFFF',
    border:   'FFCBD5E1',   // slate-300
    altRow:   'FFF8FAFC',   // slate-50  - zebra
  };

  // Indian number format & general fmts
  const FMT_AMT = '#,##,##0.00;[Red]-#,##,##0.00;"-"';
  const FMT_INT = '#,##,##0;[Red]-#,##,##0;"-"';
  const FMT_PCT = '0.00"%"';

  const AMOUNT_KEYS = new Set(['Invoice Amount','Invoice_Amount','Outstanding','Outstanding_Amount','Outstanding Amount',
    'Collections','Collection Amount','Total Collections','TOTAL COLLECTIONS','TDS Deducted','CN Value',
    'TDS_Amount','Receipt_Amount','CN_Amount','Total','Bills_Amount','MTD_Bills','MTD_Receipts',
    '0.0 Days','1.0-30 Days','31.0-45 Days','46.0-60 Days','61.0-90 Days','91.0-180 Days','>180 Days']);
  const INT_KEYS = new Set(['Invoices','Posting Done','DSO in days','Days','DSO_Days']);
  const PCT_KEYS = new Set(['Collection %']);

  function colWidthFor(key, vals){
    let w = String(key).length + 2;
    for(const v of vals){
      const s = (v==null) ? '' : String(v);
      if(s.length > w) w = s.length;
    }
    if(AMOUNT_KEYS.has(key)) w = Math.max(w, 14);
    return Math.min(Math.max(w + 2, 10), 48);
  }

  for(const sh of sheets){
    const wsName = (sh.name||'Sheet').replace(/[\\\/\?\*\[\]\:]/g,'-').slice(0,31);
    const rowsArr = sh.rows || [];
    const ws = wb.addWorksheet(wsName, {
      properties: { tabColor: { argb: COLOR.accent } },
      pageSetup: { orientation:'landscape', fitToPage:true, fitToWidth:1, fitToHeight:0, margins:{ left:0.3,right:0.3,top:0.4,bottom:0.4,header:0.2,footer:0.2 } },
      headerFooter: { oddFooter: '&LFynd · Receivables Insights&CConfidential — For Internal Use&RPage &P of &N' }
    });

    // Determine columns from first row
    const cols = rowsArr.length ? Object.keys(rowsArr[0]) : ['(no data)'];
    const totalCols = cols.length;

    // ---------- Branded header (rows 1-4) ----------
    // Row 1: Brand title
    ws.mergeCells(1,1,1,totalCols);
    const c1 = ws.getCell(1,1);
    c1.value = 'Fynd · Receivables Insights';
    c1.font = { name:'Calibri', size:16, bold:true, color:{argb:COLOR.white} };
    c1.alignment = { vertical:'middle', horizontal:'left', indent:1 };
    c1.fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.brand} };
    ws.getRow(1).height = 28;

    // Row 2: Report title + sheet name
    ws.mergeCells(2,1,2,totalCols);
    const c2 = ws.getCell(2,1);
    c2.value = (title||'Report') + '  ·  ' + wsName;
    c2.font = { name:'Calibri', size:11, bold:true, color:{argb:COLOR.brand} };
    c2.alignment = { vertical:'middle', horizontal:'left', indent:1 };
    c2.fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.band} };
    ws.getRow(2).height = 20;

    // Row 3: Period + Generated
    ws.mergeCells(3,1,3,totalCols);
    const c3 = ws.getCell(3,1);
    c3.value = `Period: ${scopeLabel||'All Time'}    ·    Generated: ${ts}    ·    Rows: ${rowsArr.length.toLocaleString('en-IN')}`;
    c3.font = { name:'Calibri', size:9, italic:true, color:{argb:'FF475569'} };
    c3.alignment = { vertical:'middle', horizontal:'left', indent:1 };
    c3.fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.band} };
    ws.getRow(3).height = 16;

    // Row 4: blank spacer
    ws.getRow(4).height = 6;

    // ---------- Column headers (row 5) ----------
    const HEADER_ROW = 5;
    const hdr = ws.getRow(HEADER_ROW);
    cols.forEach((k, i)=>{
      const cell = hdr.getCell(i+1);
      cell.value = k;
      cell.font = { name:'Calibri', size:10, bold:true, color:{argb:COLOR.white} };
      cell.fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.accent} };
      cell.alignment = { vertical:'middle', horizontal: (AMOUNT_KEYS.has(k)||INT_KEYS.has(k)||PCT_KEYS.has(k)) ? 'right' : 'left', wrapText:true };
      cell.border = {
        top:    { style:'thin', color:{argb:COLOR.border} },
        left:   { style:'thin', color:{argb:COLOR.border} },
        bottom: { style:'medium', color:{argb:COLOR.brand} },
        right:  { style:'thin', color:{argb:COLOR.border} }
      };
    });
    hdr.height = 28;

    // ---------- Data rows ----------
    // Detect grand total in last row to style it differently
    let grandIdx = -1;
    if(rowsArr.length){
      const last = rowsArr[rowsArr.length-1];
      const isGT = Object.values(last).some(v=> String(v).toUpperCase().trim() === 'GRAND TOTAL');
      if(isGT) grandIdx = rowsArr.length-1;
    }

    rowsArr.forEach((row, ri)=>{
      const xlRow = ws.getRow(HEADER_ROW + 1 + ri);
      cols.forEach((k, ci)=>{
        const cell = xlRow.getCell(ci+1);
        let v = row[k];
        if(v === '' || v == null){ cell.value = null; }
        else if(AMOUNT_KEYS.has(k) || INT_KEYS.has(k) || PCT_KEYS.has(k)){
          const n = (typeof v === 'number') ? v : parseFloat(String(v).replace(/,/g,''));
          cell.value = isNaN(n) ? v : n;
          if(typeof cell.value === 'number'){
            cell.numFmt = AMOUNT_KEYS.has(k) ? FMT_AMT : (PCT_KEYS.has(k) ? FMT_PCT : FMT_INT);
          }
        } else {
          cell.value = v;
        }
        cell.font = { name:'Calibri', size:9.5, color:{argb: ri===grandIdx ? COLOR.grandTxt : 'FF1E293B'}, bold: ri===grandIdx };
        cell.alignment = { vertical:'middle', horizontal: (AMOUNT_KEYS.has(k)||INT_KEYS.has(k)||PCT_KEYS.has(k)) ? 'right' : 'left' };
        cell.border = {
          top:    { style:'hair', color:{argb:COLOR.border} },
          left:   { style:'hair', color:{argb:COLOR.border} },
          bottom: { style:'hair', color:{argb:COLOR.border} },
          right:  { style:'hair', color:{argb:COLOR.border} }
        };
        if(ri===grandIdx){
          cell.fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.grand} };
          cell.border = {
            top:    { style:'medium', color:{argb:COLOR.brand} },
            left:   { style:'thin', color:{argb:COLOR.brand} },
            bottom: { style:'medium', color:{argb:COLOR.brand} },
            right:  { style:'thin', color:{argb:COLOR.brand} }
          };
        } else if(ri%2===1){
          cell.fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.altRow} };
        }
      });
      xlRow.height = ri===grandIdx ? 22 : 16;
    });

    // ---------- Column widths (auto) ----------
    cols.forEach((k, i)=>{
      const sample = rowsArr.slice(0, 200).map(r=> r[k]);
      ws.getColumn(i+1).width = colWidthFor(k, sample);
    });

    // ---------- Freeze panes (header band + column headers) ----------
    // Freeze the first 5 rows AND first column for big tables (Customer name etc.)
    const freezeCol = (cols[0]==='CID' || cols[0]==='Customer Name' || cols[0]==='Region') ? 0 : 0;
    ws.views = [{ state:'frozen', xSplit: freezeCol, ySplit: HEADER_ROW, activeCell: ws.getCell(HEADER_ROW+1, 1).address, showGridLines: false }];

    // ---------- Auto-filter on header row ----------
    if(rowsArr.length > 0){
      const lastDataRow = HEADER_ROW + rowsArr.length;
      ws.autoFilter = {
        from: { row: HEADER_ROW, column: 1 },
        to:   { row: lastDataRow, column: totalCols }
      };
    }
  }

  // ---------- Add cover sheet (Index) at the front ----------
  const cover = wb.addWorksheet('Index', { properties: { tabColor: { argb: COLOR.brand } } });
  cover.mergeCells(1,1,1,4);
  const ch = cover.getCell(1,1);
  ch.value = 'Fynd · Receivables Insights';
  ch.font = { name:'Calibri', size:18, bold:true, color:{argb:COLOR.white} };
  ch.fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.brand} };
  ch.alignment = { vertical:'middle', horizontal:'center' };
  cover.getRow(1).height = 34;

  cover.mergeCells(2,1,2,4);
  cover.getCell(2,1).value = title || 'Report';
  cover.getCell(2,1).font = { name:'Calibri', size:13, bold:true, color:{argb:COLOR.brand} };
  cover.getCell(2,1).alignment = { vertical:'middle', horizontal:'center' };
  cover.getRow(2).height = 22;

  cover.mergeCells(3,1,3,4);
  cover.getCell(3,1).value = `Period: ${scopeLabel||'All Time'}    ·    Generated: ${ts}`;
  cover.getCell(3,1).font = { name:'Calibri', size:10, italic:true, color:{argb:'FF475569'} };
  cover.getCell(3,1).alignment = { vertical:'middle', horizontal:'center' };
  cover.getRow(3).height = 18;

  cover.getRow(5).values = ['#', 'Sheet', 'Rows', 'Description'];
  [1,2,3,4].forEach(i=>{
    const c = cover.getCell(5,i);
    c.font = { name:'Calibri', size:10, bold:true, color:{argb:COLOR.white} };
    c.fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.accent} };
    c.alignment = { vertical:'middle', horizontal: i===1||i===3 ? 'center' : 'left', indent: 1 };
    c.border = { bottom:{ style:'medium', color:{argb:COLOR.brand} } };
  });
  cover.getRow(5).height = 22;

  const sheetDescriptions = {
    'Region Summary':'Pivot of Invoiced, Collected, Outstanding, DSO and Collection % per Region',
    'Customer Summary':'Customer × BU pivot with collections, outstanding, DSO and posting status',
    'Full Detail':'Invoice-level transaction list with aging, status and posting fields',
    'Summary':'Period-wise KPI summary with weighted DSO and collection efficiency',
    'Detail':'Invoice-level transactions backing the summary',
  };
  sheets.forEach((sh, i)=>{
    const r = cover.getRow(6+i);
    r.getCell(1).value = i+1;
    r.getCell(2).value = sh.name;
    r.getCell(3).value = (sh.rows||[]).length;
    r.getCell(4).value = sheetDescriptions[sh.name] || '';
    r.getCell(1).alignment = { horizontal:'center' };
    r.getCell(3).alignment = { horizontal:'right' };
    r.getCell(3).numFmt = FMT_INT;
    [1,2,3,4].forEach(ci=>{
      r.getCell(ci).font = { name:'Calibri', size:10 };
      if(i%2===1) r.getCell(ci).fill = { type:'pattern', pattern:'solid', fgColor:{argb:COLOR.altRow} };
      r.getCell(ci).border = { bottom:{ style:'hair', color:{argb:COLOR.border} } };
    });
  });
  cover.getColumn(1).width = 6;
  cover.getColumn(2).width = 32;
  cover.getColumn(3).width = 12;
  cover.getColumn(4).width = 70;
  cover.views = [{ state:'frozen', ySplit:5, showGridLines:false }];

  // Move Index to be the first sheet
  const idx = wb.worksheets.findIndex(w=> w.name==='Index');
  if(idx > 0){
    const idxWs = wb.worksheets[idx];
    wb.worksheets.splice(idx, 1);
    wb.worksheets.unshift(idxWs);
    wb.worksheets.forEach((w,k)=> w.orderNo = k);
  }

  // ---------- Write & download ----------
  const buf = await wb.xlsx.writeBuffer();
  const blob = new Blob([buf], { type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name+'.xlsx';
  a.click();
  setTimeout(()=> URL.revokeObjectURL(a.href), 1500);
}

function downloadPDF(sheets, name, title){ return downloadExecPDF(sheets, name, title, ''); }

// ===== Executive-grade PDF (director / CFO submission quality) =====
async function downloadExecPDF(sheets, name, title, scopeLabel){
  if(!Array.isArray(sheets)) sheets = [{name:'Report', rows:sheets}];
  // Lazy-load jsPDF + jspdf-autotable on first PDF export.
  if ((!window.jspdf || !window.jspdf.jsPDF) && typeof window.ensureJsPDF === 'function') {
    try { await window.ensureJsPDF(); } catch(_){}
  }
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation:'landscape', unit:'pt', format:'a4' });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const genTs = new Date().toLocaleString('en-IN', { dateStyle:'medium', timeStyle:'short' });
  const totalRows = sheets.reduce((a,s)=>a+(s.rows?s.rows.length:0),0);

  // Build a tiny aggregate of headline numbers when possible (looks across all rows)
  const flat = sheets.reduce((a,s)=> a.concat(s.rows||[]),[]);
  function sumKey(keys){
    let t=0; for(const r of flat){ for(const k of keys){ if(k in r){ t+=(+r[k]||0); break; } } } return t;
  }
  const sumInv = sumKey(['Invoice Amount','Invoiced','Total Invoiced','Invoice_Amount']);
  const sumCol = sumKey(['Collection Amount','Collections','Total Collections','TOTAL COLLECTIONS']);
  const sumOs  = sumKey(['Outstanding','Outstanding_Amount','Outstanding Amount']);

  function fmtCr(n){
    if(!n) return '—';
    const abs = Math.abs(n);
    if(abs>=1e7) return '₹'+(n/1e7).toFixed(2)+' Cr';
    if(abs>=1e5) return '₹'+(n/1e5).toFixed(2)+' L';
    if(abs>=1e3) return '₹'+(n/1e3).toFixed(2)+' K';
    return '₹'+Math.round(n);
  }

  sheets.forEach((s, idx)=>{
    if(idx>0) doc.addPage();

    // === Header band ===
    doc.setFillColor(15,23,42);
    doc.rect(0,0,pageW,72,'F');
    // Brand mark
    doc.setFillColor(79,70,229);
    doc.roundedRect(36,18,36,36,8,8,'F');
    doc.setTextColor(255,255,255); doc.setFont('helvetica','bold'); doc.setFontSize(22);
    doc.text('F', 47, 44);
    // Title block
    doc.setTextColor(255,255,255); doc.setFontSize(15); doc.setFont('helvetica','bold');
    doc.text('Fynd · Receivables Insights', 86, 36);
    doc.setFontSize(10); doc.setFont('helvetica','normal'); doc.setTextColor(203,213,225);
    doc.text(title || 'Report', 86, 52);
    // Right-aligned meta
    doc.setFontSize(9); doc.setTextColor(203,213,225);
    doc.text('Generated: '+genTs, pageW-36, 36, { align:'right' });
    if(scopeLabel){ doc.text('Period: '+scopeLabel, pageW-36, 50, { align:'right' }); }
    doc.setFontSize(8.5); doc.setTextColor(148,163,184);
    doc.text('Confidential · For Internal Use', pageW-36, 64, { align:'right' });

    // === Sheet sub-banner with key totals ===
    const bandY = 84;
    doc.setFillColor(238,242,255);
    doc.roundedRect(36, bandY, pageW-72, 36, 6, 6, 'F');
    doc.setTextColor(55,48,163); doc.setFont('helvetica','bold'); doc.setFontSize(10.5);
    doc.text((s.name || 'Report'), 48, bandY+15);
    doc.setFont('helvetica','normal'); doc.setTextColor(71,85,105); doc.setFontSize(9);
    const recs = (s.rows ? s.rows.length : 0);
    doc.text('Records: '+recs.toLocaleString('en-IN'), 48, bandY+28);

    // headline figures from current sheet only (avoids double-counting across multi-sheet exports)
    const fr = s.rows||[];
    function sumOn(keys){ let t=0; for(const r of fr){ for(const k of keys){ if(k in r){ t+=(+r[k]||0); break; } } } return t; }
    const sInv = sumOn(['Invoice Amount','Invoiced','Total Invoiced','Invoice_Amount']);
    const sCol = sumOn(['Collection Amount','Collections','Total Collections','TOTAL COLLECTIONS']);
    const sOs  = sumOn(['Outstanding','Outstanding_Amount','Outstanding Amount']);
    let xCol = 200;
    if(sInv){ doc.setFont('helvetica','bold'); doc.setTextColor(67,56,202); doc.text('Invoiced', xCol, bandY+15); doc.setFont('helvetica','normal'); doc.setTextColor(15,23,42); doc.text(fmtCr(sInv), xCol, bandY+28); xCol+=130; }
    if(sCol){ doc.setFont('helvetica','bold'); doc.setTextColor(5,150,105); doc.text('Collections', xCol, bandY+15); doc.setFont('helvetica','normal'); doc.setTextColor(15,23,42); doc.text(fmtCr(sCol), xCol, bandY+28); xCol+=130; }
    if(sOs){ doc.setFont('helvetica','bold'); doc.setTextColor(220,38,38); doc.text('Outstanding', xCol, bandY+15); doc.setFont('helvetica','normal'); doc.setTextColor(15,23,42); doc.text(fmtCr(sOs), xCol, bandY+28); xCol+=130; }

    // === Body table ===
    const startY = bandY + 50;
    if(!s.rows || s.rows.length===0){
      doc.setTextColor(100,116,139); doc.setFontSize(11); doc.setFont('helvetica','italic');
      doc.text('No data for this period.', pageW/2, startY+20, { align:'center' });
    } else {
      const cols = Object.keys(s.rows[0]).map(k=>({ header:k, dataKey:k }));
      // Numeric right-align where the column name suggests a number
      const numericLike = /^(invoice amount|outstanding|collections?|tds|days|total|amount|invoiced|collection|count|invoices|coverage|dso)/i;
      const colStyles = {};
      cols.forEach(c=>{ if(numericLike.test(String(c.header))) colStyles[c.dataKey] = { halign:'right' }; });
      // Detect a GRAND TOTAL row (last row whose first column is "GRAND TOTAL") and split into body + foot
      let body = s.rows;
      let foot = null;
      const last = s.rows[s.rows.length-1];
      if(last){
        const isGT = Object.values(last).some(v=> String(v).toUpperCase().trim() === 'GRAND TOTAL');
        if(isGT){ body = s.rows.slice(0,-1); foot = [last]; }
      }
      const tableOpts = {
        startY: startY,
        columns: cols,
        body: body,
        styles:{ fontSize:7, cellPadding:3.5, overflow:'linebreak', textColor:[15,23,42], lineColor:[226,232,240], lineWidth:0.3 },
        headStyles:{ fillColor:[79,70,229], textColor:255, fontStyle:'bold', fontSize:7.5, halign:'left' },
        alternateRowStyles:{ fillColor:[247,248,251] },
        columnStyles: colStyles,
        margin:{ left:36, right:36, top:130 },
        didDrawPage: function(data){
          // Footer on every page
          const ph = doc.internal.pageSize.getHeight();
          const pw = doc.internal.pageSize.getWidth();
          doc.setDrawColor(226,232,240); doc.setLineWidth(0.4);
          doc.line(36, ph-26, pw-36, ph-26);
          doc.setFontSize(8); doc.setTextColor(148,163,184); doc.setFont('helvetica','normal');
          doc.text('Fynd Receivables Insights · '+(title||''), 36, ph-12);
          doc.text('Page '+doc.internal.getNumberOfPages(), pw-36, ph-12, { align:'right' });
        }
      };
      if(foot){
        tableOpts.foot = foot;
        tableOpts.footStyles = { fillColor:[15,23,42], textColor:[255,255,255], fontStyle:'bold', fontSize:7.5 };
        tableOpts.showFoot = 'lastPage';
      }
      doc.autoTable(tableOpts);
    }
  });
  doc.save(name+'.pdf');
}
function buildReportPeriodControls(){
  // Render the Monthly/Quarterly/Yearly/All/Custom + Reset chip group inside every .rp-block
  const RP_OPTS = [
    {k:'month',   l:'Monthly'},
    {k:'quarter', l:'Quarterly'},
    {k:'ytd',     l:'Yearly'},
    {k:'all',     l:'All'},
    {k:'custom',  l:'Custom'},
  ];
  document.querySelectorAll('.rp-block').forEach(host=>{
    const rp = host.dataset.rp;
    host.innerHTML = `
      <div class="rp-label">Date Scope</div>
      <div class="rp-chips">
        ${RP_OPTS.map(o=>`<button class="rp-chip${o.k==='all'?' active':''}" data-r="${o.k}">${o.l}</button>`).join('')}
        <button class="rp-chip clear" data-act="clear">↺ Reset</button>
      </div>
      <div class="rp-dates">
        <input type="date" class="rp-from"/>
        <span class="text-slate-400 text-[10px]">to</span>
        <input type="date" class="rp-to"/>
      </div>
    `;
    const chips = host.querySelectorAll('.rp-chip[data-r]');
    const dates = host.querySelector('.rp-dates');
    const fromI = host.querySelector('.rp-from');
    const toI   = host.querySelector('.rp-to');
    const clr   = host.querySelector('.rp-chip[data-act="clear"]');
    chips.forEach(c=> c.addEventListener('click', ()=>{
      chips.forEach(x=>x.classList.remove('active'));
      c.classList.add('active');
      state.reportPeriod[rp] = c.dataset.r;
      dates.classList.toggle('open', c.dataset.r==='custom');
    }));
    fromI.addEventListener('change', e=>{ state.reportDates[rp].from = e.target.value; });
    toI.addEventListener('change',   e=>{ state.reportDates[rp].to   = e.target.value; });
    clr.addEventListener('click', ()=>{
      state.reportPeriod[rp] = 'all';
      state.reportDates[rp] = { from:'', to:'' };
      chips.forEach(x=>x.classList.toggle('active', x.dataset.r==='all'));
      fromI.value = ''; toI.value = '';
      dates.classList.remove('open');
    });
  });
}

function withReportScope(rp, fn){
  // Reports now use the global Date Range chip set in the sticky filter bar —
  // no per-report override. We still need to set the DSO/Collections bucketing
  // (month / quarter / year) from whatever the user picked at the top.
  // Collection-based reports (Total Collections, Collections Ageing) intentionally
  // bypass the Invoice Status filter so they always consider BOTH Open AND Closed
  // invoices (a closed invoice has been collected, and must appear in those reports).
  const saved = { dso:state.dsoPeriod, col:state.colPeriod, status:state.status.slice() };
  const bucketMap = { month:'month', quarter:'quarter', ytd:'year' };
  const bucket = bucketMap[state.dateRange] || 'month';
  if(rp === 'dso') state.dsoPeriod = bucket;
  if(rp === 'col') state.colPeriod = bucket;
  if(rp === 'col' || rp === 'ageCol') state.status = []; // include Open + Closed
  recompute();
  let out;
  try { out = fn(); } finally {
    state.dsoPeriod = saved.dso; state.colPeriod = saved.col;
    state.status = saved.status;
    recompute();
  }
  return out;
}

function wireReportTabs(){
  // Vertical-list Reports UI: clicking a row (or its radio input) sets state.activeReport
  const rows = document.querySelectorAll('#reportList .report-row');
  function activate(key){
    state.activeReport = key;
    rows.forEach(r=>{
      const isActive = r.dataset.rt === key;
      r.classList.toggle('active', isActive);
      const radio = r.querySelector('input[type=radio]');
      if(radio) radio.checked = isActive;
    });
  }
  rows.forEach(r=>{
    r.addEventListener('click', ()=> activate(r.dataset.rt));
    const radio = r.querySelector('input[type=radio]');
    if(radio) radio.addEventListener('change', ()=> activate(r.dataset.rt));
  });
}

function wireDownloads(){
  // Single Generate Report button — runs whichever report is active in the tabs
  const btn = document.getElementById('reportGenerate');
  if(!btn) return;
  btn.addEventListener('click', ()=>{
    const t = state.activeReport || 'combined';
    let sheets=[], name='', title='';
    try {
      withReportScope(t, ()=>{
        if(t==='combined'){
          const c = buildCombinedSummaries();
          sheets=[
            {name:'Region Summary', rows:c.bu},
            {name:'Customer Summary',      rows:c.cust},
            {name:'Full Detail',           rows:c.full}
          ];
          name='Receivables_Combined_Report'; title='Combined Business Report';
        }
        else if(t==='dso'){
          sheets=[
            {name:'Summary', rows:buildDSOReport()},
            {name:'Detail',  rows:buildDSODetail()}
          ];
          name='Receivables_DSO_'+state.dsoPeriod; title='DSO Report ('+state.dsoPeriod+')';
        }
        else if(t==='col'){
          sheets=[
            {name:'Summary', rows:buildTotalCollectionsReport()},
            {name:'Detail',  rows:buildTotalCollectionsDetail()}
          ];
          name='Receivables_Total_Collections_'+state.colPeriod; title='Total Collections Report ('+state.colPeriod+')';
        }
        else if(t==='ageOs'){
          sheets=[
            {name:'Summary', rows:buildOutstandingAgeing()},
            {name:'Detail',  rows:buildOutstandingAgeingDetail()}
          ];
          name='Receivables_Outstanding_Ageing'; title='Outstanding Ageing Report (Status = Open)';
        }
        else if(t==='ageCol'){
          sheets=[
            {name:'Summary', rows:buildCollectionsAgeing()},
            {name:'Detail',  rows:buildCollectionsAgeingDetail()}
          ];
          name='Receivables_Collections_Ageing'; title='Collections Ageing Report (by Receipt Date)';
        }
        else if(t==='tds'){
          sheets=[
            {name:'Summary', rows:buildTDSDeductedSummary()},
            {name:'Detail',  rows:buildTDSDeductedReport()}
          ];
          name='Receivables_TDS_Deducted_by_Client'; title='TDS Deducted by Client Report';
        }
      });
    } catch(e){ alert('Error preparing report: '+e.message); console.error(e); return; }
    const totalRows = sheets.reduce((a,s)=>a+(s.rows?s.rows.length:0),0);
    if(totalRows===0){
      alert('No data to export for this report.\n\nTip: Switch the date scope on this tab to "All" and try again.');
      return;
    }
    // Build a friendly subtitle based on the global date scope (sticky filters)
    const dr = state.dateRange || 'all';
    const scopeLabel = dr==='custom'
      ? `${state.dateFrom||'…'} → ${state.dateTo||'…'}`
      : ({today:'Today',month:'Monthly',quarter:'Quarterly',ytd:'Yearly',all:'All'})[dr] || dr;
    downloadXLSX_executive(sheets,name,title,scopeLabel);
  });
}

// ============================================================
// ===== LIVE SYNC =====  Pulls AR_Data, PDD_Data, Bank_Receipts
// ============================================================
const LS_KEY_URL = 'fynd.ar.liveUrl';
const LS_KEY_INT = 'fynd.ar.liveInterval';
// Instant-paint snapshot — a copy of the most recent successful live payload
// stashed in localStorage under `ar_snapshot_v1`. On subsequent boots we
// hydrate the dashboard from the snapshot FIRST (renders in <1 s) and then
// let the live fetch replace state when it lands. Snapshot is discarded if
// older than 24 h. Cap ~4 MB to stay within localStorage limits (browser
// quota is 5-10 MB, depending on vendor).
const LS_KEY_SNAPSHOT     = 'ar_snapshot_v1';
const LS_KEY_SNAPSHOT_TS  = 'ar_snapshot_v1_ts';
const SNAPSHOT_MAX_AGE_MS = 24 * 60 * 60 * 1000;
const SNAPSHOT_MAX_BYTES  = 4 * 1024 * 1024;
function _readSnapshot(){
  try{
    var raw = localStorage.getItem(LS_KEY_SNAPSHOT);
    if(!raw) return null;
    var ts = parseInt(localStorage.getItem(LS_KEY_SNAPSHOT_TS)||'0',10) || 0;
    var snapshotTimestamp = ts;
    if(!snapshotTimestamp || (Date.now() - snapshotTimestamp) > SNAPSHOT_MAX_AGE_MS){
      // Stale — clear and skip
      try{ localStorage.removeItem(LS_KEY_SNAPSHOT); localStorage.removeItem(LS_KEY_SNAPSHOT_TS); }catch(_){ }
      return null;
    }
    return { payload: JSON.parse(raw), snapshotTimestamp: snapshotTimestamp };
  } catch(_){ return null; }
}
function _writeSnapshot(payload){
  try{
    var json = JSON.stringify(payload);
    if(json.length > SNAPSHOT_MAX_BYTES){
      console.warn('[snapshot] payload '+(json.length>>10)+' KB exceeds '+(SNAPSHOT_MAX_BYTES>>10)+' KB cap — skipping localStorage write');
      return false;
    }
    localStorage.setItem(LS_KEY_SNAPSHOT, json);
    localStorage.setItem(LS_KEY_SNAPSHOT_TS, String(Date.now()));
    return true;
  } catch(e){
    console.warn('[snapshot] localStorage write failed:', e && e.message);
    try{ localStorage.removeItem(LS_KEY_SNAPSHOT); localStorage.removeItem(LS_KEY_SNAPSHOT_TS); }catch(_){}
    return false;
  }
}
let liveTimer = null;
state.pdd = []; state.bank = [];

function setSyncStatus(text, ok){
  const lab = document.getElementById('liveLabel');
  const dot = document.getElementById('liveDot');
  const btn = document.getElementById('btnLiveSync');
  const cs  = document.getElementById('cfgStatus');
  if(lab) lab.textContent = text;
  const isErr = (text||'').toLowerCase().includes('error')||(text||'').toLowerCase().includes('fail');
  if(dot) dot.style.background = ok ? '#6b8e5a' : (isErr ? '#b85450' : '#cbd5e1');
  // Push status into the live-button tooltip (icon-only header)
  if(btn) btn.setAttribute('data-tip', ok ? ('Live · '+text) : (isErr ? ('⚠ '+text) : (text||'Live Off')));
  if(cs)  cs.textContent = text;
  const meta = document.getElementById('hdrMeta');
  if(meta && ok){
    const t = new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
    document.getElementById('lastRefresh').textContent = t + ' (live)';
  }
}
/**
 * JSONP loader — injects a <script src="…?callback=cbName"> tag.
 * Apps Script wraps its JSON in cbName(...) and the browser executes it
 * as a script, BYPASSING CORS entirely. This is the only reliable way
 * to fetch from Apps Script when the dashboard is opened as a local
 * file:// HTML (where regular fetch fails with "Failed to fetch").
 */
function jsonpFetch(url, timeoutMs){
  return new Promise((resolve, reject)=>{
    const cbName = '__fynd_cb_' + Math.random().toString(36).slice(2,10);
    const sep = url.indexOf('?')>=0 ? '&' : '?';
    const fullUrl = url + sep + 'callback=' + cbName + '&_=' + Date.now();
    const script = document.createElement('script');
    let done = false;
    const cleanup = ()=>{
      try { delete window[cbName]; } catch(_) { window[cbName]=undefined; }
      if(script.parentNode) script.parentNode.removeChild(script);
    };
    window[cbName] = (data)=>{ done=true; cleanup(); resolve(data); };
    script.onerror = ()=>{ if(!done){ cleanup(); reject(new Error('Network error — check Web App URL & deployment access (must be "Anyone")')); } };
    setTimeout(()=>{ if(!done){ cleanup(); reject(new Error('Request timed out after '+(timeoutMs/1000)+'s')); } }, timeoutMs||60000);
    script.src = fullUrl;
    document.head.appendChild(script);
  });
}
async function liveFetch(showAlerts){
  // Resolution order:
  //   1. window.__DATA_URL__   ← injected by Apps Script when serving this HTML
  //                              (so team viewers don't need to configure anything)
  //   2. localStorage          ← when running as a local file:// HTML
  const url = (window.__DATA_URL__ || localStorage.getItem(LS_KEY_URL) || '').trim();
  if(!url){ if(showAlerts) alert('No Web App URL configured. Open Settings to add one.'); return; }
  setSyncStatus('Syncing…', false);
  try {
    const j = await jsonpFetch(url, 60000);
    if(j.error) throw new Error(j.error);
    // Filter #N/A rows defensively (Apps Script also drops them)
    const arRows = (j.ar||[]).filter(r=> !rowHasErr(r));
    // Capture raw column headers BEFORE mapping (used by diagnostics + console).
    // Prefer the explicit `headers` object from the v3.1 Apps Script (works even
    // when a tab has zero data rows); fall back to introspecting the first row.
    const apiHeaders     = j.headers || {};
    const rawArHeaders   = (apiHeaders.ar   && apiHeaders.ar.length)   ? apiHeaders.ar   : (arRows[0]      ? Object.keys(arRows[0])      : []);
    const rawPddHeaders  = (apiHeaders.pdd  && apiHeaders.pdd.length)  ? apiHeaders.pdd  : ((j.pdd||[])[0]  ? Object.keys(j.pdd[0])  : []);
    const rawBankHeaders = (apiHeaders.bank && apiHeaders.bank.length) ? apiHeaders.bank : ((j.bank||[])[0] ? Object.keys(j.bank[0]) : []);
    state.data = arRows.map(mapARRow);
    state.pdd  = (j.pdd||[]).map(mapPDDRow);
    state.bank = (j.bank||[]).map(mapBankRow);
    buildAllFilters(); refresh(); paintPDD(); paintBank();
    // Persist the (already-mapped) payload as an instant-paint snapshot for
    // the next boot. Do this AFTER render so slow write can't delay paint.
    try {
      _writeSnapshot({
        data: state.data,
        pdd:  state.pdd,
        bank: state.bank,
        counts: j.counts || {},
        tabsResolved: j.tabsResolved || {},
        generated: j.generated || new Date().toISOString()
      });
    } catch(_){}
    // Hide the "Showing cached data · refreshing…" pill once live payload is in.
    try{ var _pill = document.getElementById('cacheStatePill'); if(_pill) _pill.style.display='none'; }catch(_){}
    const skipped = (j.counts && j.counts.arSkipped) || 0;
    setSyncStatus(`Live · ${state.data.length.toLocaleString('en-IN')} AR · ${state.pdd.length} PDD · ${state.bank.length} bank${skipped?' · '+skipped+' #N/A skipped':''}`, true);
    // Sanity log — confirms how many mapped rows have non-zero PDD values.
    // If you see "non-zero rows: 0" in DevTools console, your PDD_Data column
    // names don't match the candidates in mapPDDRow — open Settings to view
    // the Headers diagnostic and add the actual column name to the mapper.
    const pddNonZero = state.pdd.filter(r=> r.cur || r.rev || r.ia || r.os).length;
    console.log('[Live Sync] PDD rows mapped:', state.pdd.length, '· non-zero:', pddNonZero);
    console.log('[Live Sync] PDD raw headers:', rawPddHeaders);
    console.log('[Live Sync] Bank raw headers:', rawBankHeaders);
    // Persist diagnostics for the Settings panel
    window.__lastSyncDiag = {
      tabsFound: j.tabsFound || [],
      tabsResolved: j.tabsResolved || {},
      counts: j.counts || {},
      generated: j.generated,
      headers: { ar: rawArHeaders, pdd: rawPddHeaders, bank: rawBankHeaders },
      sample:  { pdd: (j.pdd||[])[0] || null, bank: (j.bank||[])[0] || null }
    };
    // Warn if a tab returned 0 rows
    const warns = [];
    if(!state.pdd.length)  warns.push('PDD_Data is empty (resolved tab: '+(j.tabsResolved && j.tabsResolved.pdd || 'NOT FOUND')+')');
    if(!state.bank.length) warns.push('Bank_Receipts is empty (resolved tab: '+(j.tabsResolved && j.tabsResolved.bank || 'NOT FOUND')+')');
    if(warns.length){
      console.warn('[Live Sync] Tabs found in sheet:', j.tabsFound);
      console.warn('[Live Sync] Resolved:', j.tabsResolved);
      console.warn('[Live Sync] '+warns.join(' · '));
    }
  } catch(e){
    console.error('liveFetch failed', e);
    setSyncStatus('Sync failed: '+e.message, false);
    if(showAlerts) alert('Live sync failed:\n'+e.message+'\n\n• Re-deploy the Apps Script after pasting the v3 code (it adds JSONP support — required for opening this HTML directly from disk).\n• In Deploy → Manage deployments → ✏️ → New version, set Access = "Anyone".\n• Confirm the URL ends in /exec, NOT /dev.');
  }
}
function startLiveTimer(){
  if(liveTimer){ clearInterval(liveTimer); liveTimer=null; }
  const sec = parseInt(localStorage.getItem(LS_KEY_INT)||'300', 10);
  if(sec > 0){
    liveTimer = setInterval(()=> liveFetch(false), sec*1000);
  }
}
function wireSettings(){
  const modal = document.getElementById('settingsModal');
  const open  = ()=> modal.classList.remove('hidden');
  const close = ()=> modal.classList.add('hidden');
  document.getElementById('btnSettings').addEventListener('click', ()=>{
    document.getElementById('cfgUrl').value      = localStorage.getItem(LS_KEY_URL) || '';
    document.getElementById('cfgInterval').value = localStorage.getItem(LS_KEY_INT) || '300';
    const diag = window.__lastSyncDiag;
    const box = document.getElementById('cfgDiag');
    const body= document.getElementById('cfgDiagBody');
    if(diag){
      box.classList.remove('hidden');
      const h = diag.headers || {};
      const wrap = (arr)=> (arr&&arr.length) ? arr.join(' · ') : '— none —';
      // Quick health-check: how many mapped PDD rows have non-zero numeric data
      const pddOk  = (window.state && state.pdd ) ? state.pdd.filter(r=> r.cur||r.rev||r.ia||r.os).length : 0;
      const bankOk = (window.state && state.bank) ? state.bank.filter(r=> r.amt).length : 0;
      body.textContent =
        'Tabs found:    '+(diag.tabsFound||[]).join(', ')+'\n'+
        'Resolved → AR: '+(diag.tabsResolved.ar  || '—')+'\n'+
        '         PDD: '+(diag.tabsResolved.pdd || '—')+'\n'+
        '         Bank: '+(diag.tabsResolved.bank|| '—')+'\n'+
        'Counts:        AR '+(diag.counts.ar||0)+' · PDD '+(diag.counts.pdd||0)+' · Bank '+(diag.counts.bank||0)+
        ' · #N/A skipped '+(diag.counts.arSkipped||0)+'\n'+
        'Mapped OK:     PDD non-zero rows: '+pddOk+' / '+(state.pdd?state.pdd.length:0)+
        ' · Bank non-zero rows: '+bankOk+' / '+(state.bank?state.bank.length:0)+'\n'+
        '\n'+
        '— PDD_Data columns ('+(h.pdd?h.pdd.length:0)+'):\n'+wrap(h.pdd)+'\n'+
        '\n'+
        '— Bank_Receipts columns ('+(h.bank?h.bank.length:0)+'):\n'+wrap(h.bank)+'\n'+
        '\n'+
        'Tip: if "Mapped OK" shows 0 non-zero rows, your sheet column names don\'t\n'+
        'match the candidates in mapPDDRow / mapBankRow. Compare the column lists\n'+
        'above with what the dashboard expects, then either rename the sheet column\n'+
        'or add the actual name to the candidate list in build_v4.py.';
    } else { box.classList.add('hidden'); }
    open();
  });
  document.getElementById('settingsClose').addEventListener('click', close);
  modal.addEventListener('click', e=>{ if(e.target===modal) close(); });
  document.getElementById('cfgTest').addEventListener('click', async ()=>{
    const u = document.getElementById('cfgUrl').value.trim();
    if(!u) return alert('Paste a Web App URL first.');
    const statusEl = document.getElementById('cfgStatus');
    statusEl.textContent = 'Testing…';
    // IMPORTANT: Apps Script Web Apps deployed to "Anyone within <domain>"
    // redirect through Google's OAuth flow. A plain fetch() trips CORS and
    // dies with the generic browser error "Failed to fetch". JSONP (via a
    // <script> tag) follows redirects transparently and is the only reliable
    // way to talk to Apps Script from the browser — it's also what the live
    // sync uses, so a successful Test here proves the same path will work.
    try {
      const j = await jsonpFetch(u, 30000);
      if(j && j.error) throw new Error(j.error);
      const c = (j && j.counts) || {};
      statusEl.innerHTML = '<span style="color:#15803d">OK — AR '+(c.ar||0)+' · PDD '+(c.pdd||0)+' · Bank '+(c.bank||0)+'</span>';
    } catch(e){
      // Friendlier error than the raw browser string
      const m = String(e && e.message || e);
      let hint = '';
      if (/network|script error|^error$/i.test(m)) {
        hint = ' — check that the URL ends in /exec (not /dev) and that Deploy → Access = Anyone (or Anyone within fynd.com if you are signed in).';
      } else if (/time/i.test(m)) {
        hint = ' — the script took too long. Open the URL in a new tab to wake it up, then try Test again.';
      }
      statusEl.innerHTML = '<span style="color:#b91c1c">Failed: '+m+hint+'</span>';
    }
  });
  document.getElementById('cfgSave').addEventListener('click', async ()=>{
    const u = document.getElementById('cfgUrl').value.trim();
    const iv = document.getElementById('cfgInterval').value;
    if(!u) return alert('Paste a Web App URL first.');
    localStorage.setItem(LS_KEY_URL, u);
    localStorage.setItem(LS_KEY_INT, iv);
    close();
    await liveFetch(true);
    startLiveTimer();
  });
  document.getElementById('cfgDisconnect').addEventListener('click', ()=>{
    localStorage.removeItem(LS_KEY_URL);
    localStorage.removeItem(LS_KEY_INT);
    if(liveTimer){ clearInterval(liveTimer); liveTimer=null; }
    setSyncStatus('Live Off', false);
    close();
  });
  document.getElementById('btnLiveSync').addEventListener('click', ()=>{
    if(localStorage.getItem(LS_KEY_URL)) liveFetch(true);
    else open();
  });
}

// ============================================================
// ===== PDD MODULE =====
// ============================================================
function mapPDDRow(r){
  // header-tolerant — accepts spaces / underscores / case variations
  return {
    qb : String(pickField(r, ['PDD Booked','PDD_Booked','PDDBooked','Quarter Booked','PDD Quarter','Quarter','PDD_Quarter'])||''),
    pd : normD(pickField(r, ['PDD Date','PDD_Date','PDDDate','Date PDD','PDD On','PDD Booked Date'])),
    ci : String(pickField(r, ['Company ID','Company_ID','CompanyID','Company Id','CID','Company','Cust ID'])||''),
    s  : String(pickField(r, ['Seller Name','Seller_Name','SellerName','Customer','Customer Name','Customer_Name','Cust Name','Buyer Name','Buyer_Name'])||''),
    b  : String(pickField(r, ['Business','Region','Business Unit','Business_Unit','BU','BusinessUnit'])||''),
    ch : String(pickField(r, ['Channel','Sales Channel','Sales_Channel'])||''),
    tt : String(pickField(r, ['Transaction_Type','Transaction Type','TxnType','Txn Type'])||''),
    in : String(pickField(r, ['Invoice_No','Invoice No','InvoiceNo','Invoice Number','Inv_No','Inv No','InvNo'])||''),
    it : String(pickField(r, ['Invoice_Type','Invoice Type','InvoiceType','Inv Type','Inv_Type'])||''),
    d  : normD(pickField(r, ['Invoice_Date','Invoice Date','InvoiceDate','Inv Date','Inv_Date'])),
    dd : normD(pickField(r, ['Due_Date','Due Date','DueDate'])),
    ia : N(pickField(r, ['Invoice_Amount','Invoice Amount','InvoiceAmount','Inv Amount','Inv_Amount','Amount'])),
    os : N(pickField(r, ['Outstanding_Amount','Outstanding Amount','OutstandingAmount','Outstanding','OS Amount','OS_Amount','Net Outstanding'])),
    cld: N(pickField(r, ['Company_Level_Due','Company Level Due','CompanyLevelDue','Company Due','Total Due','Customer Level Due'])),
    cur: N(pickField(r, ['Current_PDD_Amouunt','Current_PDD_Amount','Current PDD Amount','CurrentPDDAmount','Current PDD','Current_PDD','CurrentPDD','PDD Amount','PDD_Amount','Net PDD'])),
    rev: N(pickField(r, ['PDD Reversed','PDD_Reversed','PDDReversed','Reversed','Reversal','PDD Reversal','PDD_Reversal'])),
    cc : String(pickField(r, ['CC','CC Name','Customer Care','Owner','Cost Center','Cost_Center'])||'')
  };
}
// PDD filter state — quarter is now an array (multi-select)
state.pddFilters = { dateRange:'all', from:null, to:null, quarter:[], q:'' };
// Convert a Date (or string) to YYYY-MM-DD so it compares correctly to ISO date strings
// stored on PDD / Bank rows. Without this, Date objects coerce to e.g. "Sun May 11 2025…"
// and the string comparison `'2025-04-15' < 'Sun May 11…'` always fails — which silently
// hid every row when a date chip was selected.
function _toISODate(d){
  if(d == null || d === '') return null;
  if(typeof d === 'string'){
    const m = d.match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[1]}-${m[2]}-${m[3]}` : d;
  }
  if(d instanceof Date && !isNaN(d)){
    const y = d.getFullYear();
    const mo= ('0'+(d.getMonth()+1)).slice(-2);
    const da= ('0'+d.getDate()).slice(-2);
    return `${y}-${mo}-${da}`;
  }
  return null;
}
function pddDateBounds(){
  const f = state.pddFilters; if(f.dateRange==='all') return [null,null];
  if(f.dateRange==='custom') return [_toISODate(f.from), _toISODate(f.to)];
  const [a,b] = dateRangeFor(f.dateRange, f.from, f.to);
  return [_toISODate(a), _toISODate(b)];
}
function getFilteredPDD(){
  const f = state.pddFilters || {};
  const [df, dt] = (typeof pddDateBounds==='function') ? pddDateBounds() : [null,null];
  let rows = (state.pdd||[]).slice();
  if(df || dt) rows = rows.filter(r=>{
    const d = r.pd || ''; if(!d) return false;
    if(df && d < df) return false;
    if(dt && d > dt) return false;
    return true;
  });
  if(Array.isArray(f.quarter) && f.quarter.length) rows = rows.filter(r=> f.quarter.indexOf(String(r.qb||''))!==-1);
  const qStr = (f.q||'').trim().toLowerCase();
  if(qStr) rows = rows.filter(r=> (r.s+' '+r.in+' '+r.ci+' '+r.cc).toLowerCase().includes(qStr));
  return rows;
}
let pddMSQuarter = null;
let _pddWired = false;
let _pddMSCount = -1;
function paintPDD(){
  const fIn  = document.getElementById('pddFilter');
  // Build/refresh the Quarter multi-select whenever PDD data changes (first paint runs
  // before the live fetch completes — at that point state.pdd is empty and the dropdown
  // would otherwise be permanently empty)
  const qHost = document.getElementById('pddMSQuarter');
  const uniqQ = Array.from(new Set((state.pdd||[]).map(r=>String(r.qb||'')).filter(Boolean)));
  if(qHost && uniqQ.length !== _pddMSCount){
    pddMSQuarter = buildSimpleMS(qHost, 'Quarter Booked', uniqQ, state.pddFilters.quarter, paintPDD);
    _pddMSCount  = uniqQ.length;
  }
  // Wire chips/search/clear once
  if(!_pddWired){
    _pddWired = true;
    if(fIn){
      fIn.addEventListener('input', ()=>{ state.pddFilters.q = fIn.value; paintPDD(); });
    }
    document.querySelectorAll('#pddDateChips .pdd-r').forEach(c=> c.addEventListener('click', ()=>{
      document.querySelectorAll('#pddDateChips .pdd-r').forEach(x=>x.classList.remove('active'));
      c.classList.add('active');
      state.pddFilters.dateRange = c.dataset.r;
      document.getElementById('pddDateCustom').classList.toggle('hidden', c.dataset.r!=='custom');
      paintPDD();
    }));
    const pf = document.getElementById('pddFrom'), pt = document.getElementById('pddTo');
    if(pf) pf.addEventListener('change', e=>{ state.pddFilters.from = e.target.value; paintPDD(); });
    if(pt) pt.addEventListener('change', e=>{ state.pddFilters.to   = e.target.value; paintPDD(); });
    const pc = document.getElementById('pddClear');
    if(pc) pc.addEventListener('click', ()=>{
      state.pddFilters.dateRange='all'; state.pddFilters.from=null; state.pddFilters.to=null;
      state.pddFilters.quarter.length=0; state.pddFilters.q='';
      if(fIn) fIn.value='';
      const pf2=document.getElementById('pddFrom'), pt2=document.getElementById('pddTo');
      if(pf2) pf2.value=''; if(pt2) pt2.value='';
      document.querySelectorAll('#pddDateChips .pdd-r').forEach(x=>x.classList.toggle('active', x.dataset.r==='all'));
      const dc=document.getElementById('pddDateCustom'); if(dc) dc.classList.add('hidden');
      if(pddMSQuarter && typeof pddMSQuarter.reset==='function') pddMSQuarter.reset();
      _resetGlobalSearch();
      paintPDD();
    });
  }
  const rows = getFilteredPDD();
  // KPIs (Invoices Booked · PDD Booked (was Outstanding) · PDD Reversed · Current PDD)
  const tot = rows.reduce((a,r)=>{ a.os+=r.os; a.cur+=r.cur; a.rev+=r.rev; return a; }, {os:0,cur:0,rev:0});
  const cEl = document.getElementById('pdd_count'); if(cEl) cEl.textContent = fmtNum(rows.length);
  const oEl = document.getElementById('pdd_os');    if(oEl) oEl.textContent = fmtINR(tot.os);
  const rEl = document.getElementById('pdd_rev');   if(rEl) rEl.textContent = fmtINR(tot.rev);
  const uEl = document.getElementById('pdd_cur');   if(uEl) uEl.textContent = fmtINR(tot.cur);
  document.getElementById('pddMeta').textContent   = rows.length.toLocaleString('en-IN')+' invoices · live from PDD_Data';
  // Chart: PDD by Quarter — uses filtered rows so date / quarter / search scope the bars too
  const byQ = {};
  rows.forEach(r=>{ if(!byQ[r.qb]) byQ[r.qb]={cur:0,rev:0}; byQ[r.qb].cur+=r.cur; byQ[r.qb].rev+=r.rev; });
  const qLabels = Object.keys(byQ).sort();
  const cur = qLabels.map(q=> Math.round((byQ[q].cur||0)*100)/100);
  const rev = qLabels.map(q=> Math.round((byQ[q].rev||0)*100)/100);
  if(charts.pddQtr) charts.pddQtr.destroy();
  const ctx1 = document.getElementById('cPddQtr');
  if(ctx1){
    charts.pddQtr = new Chart(ctx1, { type:'bar',
      data:{ labels:qLabels, datasets:[
        { label:'Current PDD', data:cur, backgroundColor:'#b8956a' },
        { label:'PDD Reversed', data:rev, backgroundColor:'#6b8e5a' },
      ]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'bottom',labels:{font:{size:10}}},tooltip:{callbacks:{label:c=>c.dataset.label+': '+fmtINR(c.parsed.y)}}}, scales:{y:{ticks:{font:{size:10},callback:v=>fmtINR(v)},grid:{color:'#f1f5f9'}}, x:{ticks:{font:{size:10}}}} }
    });
  }
  // Chart: Top customers by PDD outstanding
  const byC = {};
  rows.forEach(r=>{ if(!byC[r.s]) byC[r.s]={cur:0}; byC[r.s].cur+=r.cur; });
  const top = Object.entries(byC).sort((a,b)=>b[1].cur-a[1].cur).slice(0,10);
  if(charts.pddCust) charts.pddCust.destroy();
  const ctx2 = document.getElementById('cPddCust');
  if(ctx2){
    charts.pddCust = new Chart(ctx2, { type:'bar',
      data:{ labels: top.map(t=>t[0].slice(0,28)), datasets:[{ label:'Current PDD', data:top.map(t=>Math.round(t[1].cur*100)/100), backgroundColor:'#5b7a82' }]},
      options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>fmtINR(c.parsed.x)}}}, scales:{x:{ticks:{font:{size:10},callback:v=>fmtINR(v)},grid:{color:'#f1f5f9'}}, y:{ticks:{font:{size:9.5}}}} }
    });
  }
  // Table
  const tbody = document.getElementById('pddBody');
  rows.sort((a,b)=> b.cur - a.cur);
  tbody.innerHTML = rows.slice(0,500).map(r=>`
    <tr>
      <td>${r.qb}</td><td>${fmtDateOut(r.pd)}</td><td>${r.ci}</td><td>${r.s}</td><td>${r.b}</td><td>${r.ch}</td>
      <td>${r.in}</td><td class="text-right">${fmtINRfull(r.ia)}</td><td class="text-right ${r.os>0?'num-red':'num-green'}">${fmtINRfull(r.os)}</td>
      <td class="text-right num-amber">${fmtINRfull(r.cur)}</td><td class="text-right num-green">${fmtINRfull(r.rev)}</td><td>${r.cc}</td>
    </tr>`).join('') || `<tr><td colspan="12" class="text-center text-slate-400 py-6 text-xs">No PDD data — connect via Settings.</td></tr>`;
}

// ============================================================
// ===== BANK RECEIPTS MODULE =====
// ============================================================
function mapBankRow(r){
  // header-tolerant
  return {
    ci  : String(pickField(r, ['Company ID','Company_ID','CompanyID','CID','Company'])||''),
    cn  : String(pickField(r, ['Company Name','Company_Name','CompanyName','Customer','Customer Name'])||''),
    rd  : normD(pickField(r, ['Receipt Date','Receipt_Date','ReceiptDate','Date Received'])),
    bk  : String(pickField(r, ['Bank','Bank Name','Bank_Name','BankName'])||''),
    nar : String(pickField(r, ['Narration','Narration1','Description','Remarks','Particulars'])||''),
    nar2: String(pickField(r, ['Narration1_RazorPay & Stripe','Narration1 RazorPay Stripe','Narration2','Narration_2','PG Narration','Gateway Narration'])||''),
    bd  : normD(pickField(r, ['Date','Booking Date','Booking_Date','Txn Date','Txn_Date','Transaction Date','Bank Date'])),
    amt : N(pickField(r, ['Amount Credited','Amount_Credited','AmountCredited','Amount','Credit Amount','Credit_Amount','Net Amount'])),
    map : String(pickField(r, ['Receipt Mapping in AR_Data','Receipt_Mapping_in_AR_Data','AR Mapping','AR_Mapping','Mapping','Mapped','Status'])||''),
    vlx : String(pickField(r, ['Valyx Status','Valyx_Status','ValyxStatus','Reconcile Status','Reconciliation'])||''),
    b   : String(pickField(r, ['Business','Region','Business Unit','Business_Unit','BU','BusinessUnit'])||'')
  };
}
// Bank filter state — bank/status/bu are arrays (multi-select)
state.bankFilters = { dateRange:'all', from:null, to:null, bank:[], status:[], bu:[], q:'', min:'', max:'' };
function bankDateBounds(){
  const f = state.bankFilters; if(f.dateRange==='all') return [null,null];
  if(f.dateRange==='custom') return [_toISODate(f.from), _toISODate(f.to)];
  const [a,b] = dateRangeFor(f.dateRange, f.from, f.to);
  return [_toISODate(a), _toISODate(b)];
}
// Pull a YYYY-MM-DD date out of free-text (narration) — best effort.
// Accepts: 2026-06-11, 11/06/2026, 11-06-2026, 11.06.2026, 11 Jun 2026.
function _bankNarrationDate(s){
  if (!s) return '';
  const txt = String(s);
  // ISO first: 2026-06-11
  let m = txt.match(/(20\d{2})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])/);
  if (m) return `${m[1]}-${String(+m[2]).padStart(2,'0')}-${String(+m[3]).padStart(2,'0')}`;
  // DD/MM/YYYY (incl - or .)
  m = txt.match(/(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|1[0-2])[-/.](20\d{2})/);
  if (m) return `${m[3]}-${String(+m[2]).padStart(2,'0')}-${String(+m[1]).padStart(2,'0')}`;
  // DD Mon YYYY
  const MON = {jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,sept:9,oct:10,nov:11,dec:12};
  m = txt.match(/(\b\d{1,2})\s+([A-Za-z]{3,4})\s+(20\d{2})/);
  if (m && MON[m[2].toLowerCase().slice(0,3)]) {
    return `${m[3]}-${String(MON[m[2].toLowerCase().slice(0,3)]).padStart(2,'0')}-${String(+m[1]).padStart(2,'0')}`;
  }
  return '';
}
function _bankEffectiveRd(r){
  return r.rd || _bankNarrationDate(r.nar) || _bankNarrationDate(r.nar2) || '';
}

function getFilteredBank(){
  const f = state.bankFilters || {};
  const [df, dt] = (typeof bankDateBounds==='function') ? bankDateBounds() : [null,null];
  // Strip trailing/empty rows that don't belong in the audit: a real receipt
  // either has a date (rd or narration-derived) or an amount > 0. Anything else
  // is sheet noise and used to inflate the row count + mis-match the figure totals.
  let rows = (state.bank||[]).filter(r => {
    const hasDate = !!_bankEffectiveRd(r);
    const hasAmt  = +r.amt > 0;
    return hasDate || hasAmt;
  });
  if(df || dt) rows = rows.filter(r=>{
    // Honor Receipt Date OR a date parsed from Narration so receipts where the
    // booking date sits inside the narration line still flow into the figures.
    const d = _bankEffectiveRd(r);
    if(!d) return false;
    if(df && d < df) return false;
    if(dt && d > dt) return false;
    return true;
  });
  if(Array.isArray(f.bank)   && f.bank.length)   rows = rows.filter(r=> f.bank.indexOf(String(r.bk||''))!==-1);
  if(Array.isArray(f.status) && f.status.length) rows = rows.filter(r=> f.status.indexOf(String(r.map||''))!==-1);
  if(Array.isArray(f.bu)     && f.bu.length)     rows = rows.filter(r=> f.bu.indexOf(String(r.b||''))!==-1);
  const qS = (f.q||'').trim().toLowerCase();
  if(qS) rows = rows.filter(r=> (r.cn+' '+r.nar+' '+r.nar2+' '+r.ci+' '+r.bk).toLowerCase().includes(qS));
  const minN = f.min!=='' && f.min!=null ? parseFloat(f.min) : null;
  const maxN = f.max!=='' && f.max!=null ? parseFloat(f.max) : null;
  if(minN!=null && !isNaN(minN)) rows = rows.filter(r=> r.amt >= minN);
  if(maxN!=null && !isNaN(maxN)) rows = rows.filter(r=> r.amt <= maxN);
  return rows;
}
let bankMS = { bank:null, status:null, bu:null };
let _bankWired = false;
let _bankMSCount = { bank:-1, status:-1, bu:-1 };
function paintBank(){
  const fIn  = document.getElementById('bankFilter');
  const minI = document.getElementById('bankMin');
  const maxI = document.getElementById('bankMax');
  // Build/refresh the multi-selects whenever Bank data changes
  const bHost = document.getElementById('bankMSBank');
  const sHost = document.getElementById('bankMSStatus');
  const uHost = document.getElementById('bankMSBU');
  const banks = Array.from(new Set((state.bank||[]).map(r=>String(r.bk||'')).filter(Boolean)));
  const stats = Array.from(new Set((state.bank||[]).map(r=>String(r.map||'')).filter(Boolean)));
  const bus   = Array.from(new Set((state.bank||[]).map(r=>String(r.b||'')).filter(Boolean)));
  if(bHost && banks.length !== _bankMSCount.bank){
    bankMS.bank = buildSimpleMS(bHost, 'Bank', banks, state.bankFilters.bank, paintBank);
    _bankMSCount.bank = banks.length;
  }
  if(sHost && stats.length !== _bankMSCount.status){
    bankMS.status = buildSimpleMS(sHost, 'Status', stats, state.bankFilters.status, paintBank);
    _bankMSCount.status = stats.length;
  }
  if(uHost && bus.length !== _bankMSCount.bu){
    bankMS.bu = buildSimpleMS(uHost, 'Region', bus, state.bankFilters.bu, paintBank);
    _bankMSCount.bu = bus.length;
  }
  // Wire chips/search/inputs/clear once
  if(!_bankWired){
    _bankWired = true;
    if(fIn)   fIn.addEventListener('input', ()=>{ state.bankFilters.q   = fIn.value;  paintBank(); });
    if(minI)  minI.addEventListener('input',()=>{ state.bankFilters.min = minI.value; paintBank(); });
    if(maxI)  maxI.addEventListener('input',()=>{ state.bankFilters.max = maxI.value; paintBank(); });
    document.querySelectorAll('#bankDateChips .bk-r').forEach(c=> c.addEventListener('click', ()=>{
      document.querySelectorAll('#bankDateChips .bk-r').forEach(x=>x.classList.remove('active'));
      c.classList.add('active');
      state.bankFilters.dateRange = c.dataset.r;
      document.getElementById('bankDateCustom').classList.toggle('hidden', c.dataset.r!=='custom');
      paintBank();
    }));
    const bf = document.getElementById('bankFrom'), bt = document.getElementById('bankTo');
    if(bf) bf.addEventListener('change', e=>{ state.bankFilters.from = e.target.value; paintBank(); });
    if(bt) bt.addEventListener('change', e=>{ state.bankFilters.to   = e.target.value; paintBank(); });
    const bc = document.getElementById('bankClear');
    if(bc) bc.addEventListener('click', ()=>{
      state.bankFilters.dateRange='all'; state.bankFilters.from=null; state.bankFilters.to=null;
      state.bankFilters.bank.length=0; state.bankFilters.status.length=0; state.bankFilters.bu.length=0;
      state.bankFilters.q=''; state.bankFilters.min=''; state.bankFilters.max='';
      if(fIn) fIn.value=''; if(minI) minI.value=''; if(maxI) maxI.value='';
      const bf2 = document.getElementById('bankFrom'), bt2 = document.getElementById('bankTo');
      if(bf2) bf2.value=''; if(bt2) bt2.value='';
      document.querySelectorAll('#bankDateChips .bk-r').forEach(x=>x.classList.toggle('active', x.dataset.r==='all'));
      const dc=document.getElementById('bankDateCustom'); if(dc) dc.classList.add('hidden');
      if(bankMS.bank   && typeof bankMS.bank.reset==='function')   bankMS.bank.reset();
      if(bankMS.status && typeof bankMS.status.reset==='function') bankMS.status.reset();
      if(bankMS.bu     && typeof bankMS.bu.reset==='function')     bankMS.bu.reset();
      _resetGlobalSearch();
      paintBank();
    });
  }
  const rows = getFilteredBank();
  // KPIs
  const tot = rows.reduce((a,r)=>{
    a.amt += r.amt;
    if(/applied/i.test(r.map) && !/partial/i.test(r.map)) a.applied += r.amt;
    else a.pending += r.amt;
    return a;
  }, {amt:0, applied:0, pending:0});
  document.getElementById('bk_count').textContent  = fmtNum(rows.length);
  document.getElementById('bk_total').textContent  = fmtINR(tot.amt);
  document.getElementById('bk_applied').textContent= fmtINR(tot.applied);
  document.getElementById('bk_pending').textContent= fmtINR(tot.pending);
  document.getElementById('bk_banks').textContent  = new Set(rows.map(r=>r.bk).filter(Boolean)).size;
  document.getElementById('bankMeta').textContent  = rows.length.toLocaleString('en-IN')+' receipts · live from Bank_Receipts';
  // Daily inflow chart — bucket by effective rd so the chart matches the table totals.
  const byD = {};
  rows.forEach(r=>{
    const d = _bankEffectiveRd(r);
    if(!d) return;
    byD[d] = (byD[d]||0) + r.amt;
  });
  const days = Object.keys(byD).sort();
  if(charts.bkDaily) charts.bkDaily.destroy();
  const ctxD = document.getElementById('cBkDaily');
  if(ctxD){
    charts.bkDaily = new Chart(ctxD, { type:'line',
      data:{ labels: days.map(d=> fmtDateOut(d)), datasets:[{ label:'Amount Credited', data: days.map(d=> Math.round(byD[d]*100)/100), borderColor:'#6b8e5a', backgroundColor:'rgba(107,142,90,.14)', fill:true, tension:.3, pointRadius:2 }]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>fmtINR(c.parsed.y)}}}, scales:{y:{ticks:{font:{size:10},callback:v=>fmtINR(v)},grid:{color:'#f1f5f9'}}, x:{ticks:{font:{size:9},maxRotation:0,autoSkip:true,autoSkipPadding:8}}} }
    });
  }
  // Bank-wise mix
  const byB = {};
  rows.forEach(r=>{ if(!r.bk) return; byB[r.bk]=(byB[r.bk]||0)+r.amt; });
  const blab = Object.keys(byB).sort((a,b)=> byB[b]-byB[a]);
  if(charts.bkBank) charts.bkBank.destroy();
  const ctxB = document.getElementById('cBkBank');
  if(ctxB){
    charts.bkBank = new Chart(ctxB, { type:'bar',
      data:{ labels:blab, datasets:[{ label:'Credited', data: blab.map(b=> Math.round(byB[b]*100)/100), backgroundColor: blab.map((_,i)=> STRONG[i % STRONG.length]) }]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>fmtINR(c.parsed.y)}}}, scales:{y:{ticks:{font:{size:10},callback:v=>fmtINR(v)},grid:{color:'#f1f5f9'}}, x:{ticks:{font:{size:10},maxRotation:25}}} }
    });
  }
  // Table
  const tbody = document.getElementById('bankBody');
  // Sort by EFFECTIVE date (Receipt Date OR Narration-derived date) so rows
  // that inherit their date from the narration still order correctly.
  rows.sort((a,b)=> String(_bankEffectiveRd(b)).localeCompare(String(_bankEffectiveRd(a))) || b.amt-a.amt);
  tbody.innerHTML = rows.slice(0,500).map(r=>{
    const status = r.map || '—';
    const cls = /partial/i.test(status) ? 'badge badge-amber' : (/applied/i.test(status) ? 'badge badge-green' : 'badge');
    const effRd = _bankEffectiveRd(r);
    return `<tr>
      <td>${fmtDateOut(effRd)}</td><td>${r.ci}</td><td>${r.cn}</td><td>${r.bk}</td><td>${r.b}</td>
      <td title="${(r.nar||'').replace(/"/g,'&quot;')}" style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.nar||r.nar2}</td>
      <td class="text-right">${fmtINRfull(r.amt)}</td><td><span class="${cls}">${status}</span></td><td>${r.vlx||'—'}</td>
    </tr>`;
  }).join('') || `<tr><td colspan="9" class="text-center text-slate-400 py-6 text-xs">No bank receipts — connect via Settings.</td></tr>`;
}

// ============================================================
// ===== CUSTOMER STATEMENT OF ACCOUNT (LEDGER) MODULE =====
// ============================================================
// Builds a printable ledger of all transactions (invoices, credit notes,
// payments, TDS, COD adjustments, bank charges, PDD, others/round-off)
// for a single customer between user-selected From/To dates. Each AR row
// is "exploded" into one or more ledger lines tagged with running balance.
// Stakeholder can preview, download to Excel/PDF, or email the client.

const soaState = {
  cid: '',
  custName: '',
  custMeta: '',
  fromDate: '',
  toDate: '',
  lines: [],         // {date, type, doc, ref, refs, particulars, debit, credit, balance}
  opening: 0,
  totDr: 0,
  totCr: 0,
  closing: 0,
  filterRef: '',     // active reference filter (UI-only; downloads stay full)
  statusFilter: 'All', // 'All' | 'Paid' | 'Partial' | 'Unpaid' | 'Unmatched' — preview-only narrowing
};

// Type-pill CSS class for the ledger Type column.
// Note: "Bad Debt" is no longer emitted as a type (it now appears as
// "Adjustment" → soa-pill-adj). The legacy soa-pill-bd class is still
// kept in CSS for safety but is unreachable from new ledger lines.
function _soaPillCls(t){
  const k = String(t||'').toLowerCase();
  if (k.indexOf('invoice') >= 0) return 'soa-pill-inv';
  if (k.indexOf('credit note') >= 0 || k === 'cn') return 'soa-pill-cn';
  if (k.indexOf('payment') >= 0) return 'soa-pill-pay';
  if (k.indexOf('tds') >= 0) return 'soa-pill-tds';
  if (k.indexOf('cod') >= 0) return 'soa-pill-adj';
  if (k.indexOf('pdd') >= 0) return 'soa-pill-pdd';
  if (k.indexOf('bank') >= 0) return 'soa-pill-bnk';
  return 'soa-pill-adj';
}

// Explode a single AR row into per-event ledger lines.
// Invoice line is dated by r.d (invoice date). All credit-side events
// (CN, TDS, COD adj, bank charges, others, PDD) are dated by r.rd
// (receipt date). If r.rd is missing for those events, fall back to r.d.
//
// NOTE: Payment-in-bank lines are NOT emitted here. They are aggregated
// separately in buildLedger() and emitted as ONE row per unique UTR/Bank
// Ref — so a Rs.10 payment split across 4 invoices shows as a single
// credit of Rs.10 (not four duplicate Rs.X rows with the same Doc No).
// Each line carries:
//   ref   — primary reference for that line (Invoice no. for invoice-tied
//           events; UTR for the aggregated payment row)
//   refs  — array of ALL identifiers this line is linked to. The UI uses
//           this so that "select a reference → show every transaction
//           against that reference" works across invoice, payment, TDS,
//           credit-note, COD/bank/PDD/other adjustments.
// Builds the same key the payment aggregator uses to group split rows.
// Sharing this function across explode + aggregate is what guarantees
// that every row tied to one settlement event ends up with the same
// Unique Ref (so the client's Excel filter surfaces the full set).
function _soaSettleKey(r){
  const utr     = String(r.br||'').trim();
  const evDate  = r.rd || r.d || '';
  const bankTot = +r.pb || 0;
  const slice   = +r.ps || 0;
  const hasPay  = Math.abs(slice) > 0.01 || Math.abs(bankTot) > 0.01;
  if (utr) return utr;
  if (hasPay) return 'NO-UTR|' + evDate + '|' + (bankTot || slice).toFixed(2);
  // No payment activity at all → unpaid invoice. Each invoice gets its
  // OWN check ref so unpaid lines aren't all lumped together.
  return 'INV|' + String(r.in||'').trim();
}

function _soaExplodeAR(r){
  const out = [];
  const evDate = r.rd || r.d;
  const inv    = String(r.in||'').trim();
  const utr    = String(r.br||'').trim();
  // Linked refs for every credit-side event on this AR row: the invoice
  // it belongs to AND the UTR of the payment that settled it (so the
  // client can pivot in either direction).
  const linkAll = [inv, utr].filter(Boolean);
  // Settlement seed ties this AR row to the payment that settled it (via
  // UTR or synthetic key). Same seed used by _soaAggregatePayments, so
  // the payment row and all its invoice/TDS/CN/COD/adj rows end up
  // sharing one Unique Ref number (assigned by buildLedger after the
  // chronological sort, so refs read 1, 2, 3, … in encounter order).
  const checkSeed = _soaSettleKey(r);

  // ----- Write-off / Internal-Transfer adjustment detection -----
  // Some AR rows represent a balance write-off (booked from the AR
  // Google Sheet via Apps Script) rather than an actual invoice +
  // settlement. They are flagged via:
  //   * Invoice_Type / Transaction_Type containing "Bad Debt" /
  //     "Write off" / "W/Off" (kept for back-compat with historical data)
  //   * Invoice number / particulars carrying "BadDebt" / "WriteOff"
  //   * "Internal Transfer" workaround: the team books these as a
  //     synthetic invoice (negative ia + matching pdd to zero out the
  //     outstanding) using Invoice_Type = "Internal Transfer" and an
  //     invoice number like "<cid>_InternalTransfer_<n>". This is the
  //     long-standing pattern for FY-end write-offs in this dataset
  //     (e.g. Khadim CID 292 with ia=-8969).
  // We surface these as a dedicated 'Adjustment' ledger line so the
  // customer ledger shows where an opening balance was written off.
  // Per stakeholder direction we no longer use the term "Bad Debt"
  // anywhere — these now appear as Type = Adjustment with Status
  // mirroring the underlying AR row's closure state (Paid when r.os
  // is ~0 i.e. the row is closed, otherwise Unpaid).
  // Once detected we short-circuit so this row does NOT also re-emit as
  // Invoice + PDD + COD lines (which would net to zero in the running
  // balance and hide the write-off from the user entirely).
  const itLower  = String(r.it||'').toLowerCase();
  const ttLower  = String(r.tt||'').toLowerCase();
  const invLower = String(inv||'').toLowerCase();
  const writeOffRx = /(bad\s*debt|write[\s\-]?off|w\/off|writeoff|baddebt)/;
  const internalRx = /internal\s*transfer/;
  const isWriteOff =
    writeOffRx.test(itLower) || writeOffRx.test(ttLower) || writeOffRx.test(invLower) ||
    internalRx.test(itLower) || internalRx.test(invLower);
  if (isWriteOff){
    // Sign convention (revised — see Da Milano CID 870, B-JV-08793-FY25):
    //   The team books write-offs both ways:
    //     · Khadim-style: negative ia (e.g. -8969) → write-off entry
    //     · Da Milano-style: positive ia (e.g. +8,272.16) + COD adjustment
    //       column carrying the same amount, comment "Written off"
    //   In BOTH cases the underlying accounting truth is identical: the
    //   customer's receivable is being reduced. From the customer-ledger
    //   perspective that is unconditionally a CREDIT (DR Bad Debt Expense,
    //   CR Trade Receivables). The previous sign-aware logic (positive →
    //   debit) silently flipped Da Milano's write-off to the wrong side
    //   and hid the credit on 31-Jan-26.
    //
    //   Fix: when the row is CLOSED (os ~ 0) — which is the normal write-
    //   off case — always post abs(ia) as CREDIT. For the rare OPEN case
    //   (write-off booked but balance not yet zeroed in AR_Data) we keep
    //   the sign-aware logic as a defensive fallback so a stray positive
    //   open entry still surfaces visibly rather than silently muting.
    const v = +r.ia || 0;
    if (Math.abs(v) > 0.01){
      // Particulars distinguish labelled write-offs vs Internal Transfer.
      const isInternal = internalRx.test(itLower) || internalRx.test(invLower);
      const label = isInternal ? 'Adjustment (Internal Transfer)' : 'Adjustment write-off';
      const isClosed = Math.abs(+r.os || 0) <= 0.01;
      // Closed → land on receipt date (so opening auto-closes alongside
      // COD/CN/Payment rows). Open → keep on invoice date.
      const adjDate = isClosed
        ? (r.rd || r.d)
        : (r.d  || r.rd);
      // Closed write-off: ALWAYS post as credit (the receivable is being
      // reduced). Open write-off: fall back to sign-aware logic for safety.
      let dbVal, crVal;
      if (isClosed){
        dbVal = 0;
        crVal = Math.abs(v);
      } else {
        dbVal = v > 0 ?  v          : 0;
        crVal = v < 0 ?  Math.abs(v) : 0;
      }
      out.push({
        date: adjDate,
        type: 'Adjustment',
        doc: inv,
        particulars: label + (inv?(' · '+inv):''),
        debit:  dbVal,
        credit: crVal,
        ref: inv,
        refList: [inv].filter(Boolean),
        refs: [inv, utr].filter(Boolean),
        checkSeed,
        status: isClosed ? 'Paid' : 'Unpaid',
        isWriteOff: true,
        // Back-compat alias — older render paths may still reference
        // isBadDebt; keep it true so range/keep logic below stays valid.
        isBadDebt: true,
        // Source invoice date — buildLedger uses this to recognise that
        // an adjustment closes an opening-balance contributor (invoice
        // dated before the period start).
        srcD: r.d || '',
      });
    }
    return out;
  }
  // ----- /write-off detection -----
  // Status: settlement is Paid when the outstanding balance on this AR
  // row is zero (allowing for ₹0.01 rounding noise). Otherwise Unpaid.
  // This matches the per-invoice math the user described: Paid when
  //   invoice_amount − (payment + TDS + CN + COD + bank chg + PDD + adj) = 0
  // because that delta is literally what r.os captures.
  //
  // Status placement (per stakeholder spec):
  //   * INVOICE row → carries the per-invoice settlement status
  //     (Paid / Partial / Unpaid). This is the row the user looks at to
  //     decide whether the invoice is still open.
  //   * NON-INVOICE rows (TDS / CN / COD / Bank Chg / PDD / Adjustment)
  //     → always 'Paid' because their mere existence means the credit
  //     event itself happened against the invoice. The invoice's
  //     overall status (Partial / Unpaid) is read off the invoice row.
  const isPaid = Math.abs(+r.os || 0) <= 0.01;
  // Invoice-row status — Paid when fully settled, else Unpaid. (Partial
  // is set later by the payment-row builder when the underlying receipt
  // didn't fully close every linked invoice; if the AR row carries an
  // open balance and no receipt, the invoice itself remains Unpaid.)
  const invStatus = isPaid ? 'Paid' : 'Unpaid';
  // Cross-link: include the check ref so the Excel/HTML filter picks up
  // the full settlement set from any row.
  // Cross-link refs: invoice + UTR. Unique Ref number is added by the
  // post-sort numbering step in buildLedger.
  const refsFull = [inv, utr].filter(Boolean);

  // Invoice (debit) — primary ref = invoice number
  // Particulars: shows the Invoice_Type (e.g. "INV" / "Commission")
  // followed by the Transaction_Type pulled from AR_Data, so the user
  // can identify what category of invoice the row is against
  // (e.g. "INV · Marketplace", "INV · Direct"). Falls back to
  // "Invoice" if Invoice_Type is blank, and silently drops the
  // Transaction_Type suffix if that column is empty.
  if (Math.abs(+r.ia||0) > 0.01){
    const invBase = String(r.it||'').trim() || 'Invoice';
    const invTxn  = String(r.tt||'').trim();
    const invLabel = invTxn ? (invBase + ' · ' + invTxn) : invBase;
    // Sign convention: positive r.ia is a customer-side debit (we raised
    // an invoice on them). A NEGATIVE r.ia (e.g. "TDS Payable" rows that
    // appear with a negative invoice amount in source data) means the
    // entry actually moves money the OTHER way and belongs on the CREDIT
    // side — otherwise the running balance shows a phantom "negative
    // debit" that throws off the totals (as in the user's TDS Payable
    // row that displayed as ₹-2,767.68 in Debit). Mirror the sign-aware
    // posting already used for round-off / write-off lines.
    const v = +r.ia || 0;
    out.push({
      date: r.d || r.rd, type: 'Invoice', doc: inv,
      particulars: invLabel,
      debit:  v > 0 ?  v          : 0,
      credit: v < 0 ?  Math.abs(v) : 0,
      ref: inv, refList: [inv].filter(Boolean), refs: refsFull,
      checkSeed,
      status: invStatus      // Paid / Unpaid lives ON the invoice row
    });
  }
  // TDS (credit) — keyed to the invoice it was deducted against.
  // Particulars now read "TDS for FY YY-YY" where the FY is computed
  // from the EARLIER of Invoice Date and Receipt Date. The stakeholder
  // uses this label in their books, and the FY anchor is the earliest
  // booking event (matches the convention in the AR Google Sheet).
  //
  // Sign-aware posting (applies to every credit-side row below): the
  // field's NATURAL side is credit, so a positive amount goes to credit.
  // A negative amount means the underlying transaction reversed direction
  // — flip it to the debit column (abs value) so the running balance
  // stays internally consistent. Stakeholder ask: "Whenever the negative
  // number shows then it should be reflect in credit side not a debit
  // side" — the same logic, mirrored, applies to invoice rows that go
  // negative (already handled above).
  if (Math.abs(+r.tds||0) > 0.01){
    const v = +r.tds || 0;
    out.push({
      date: evDate, type: 'TDS', doc: inv,
      particulars: 'TDS for ' + _soaFYLabel(r.d, r.rd),
      debit:  v < 0 ? Math.abs(v) : 0,
      credit: v > 0 ? v           : 0,
      ref: inv, refList: [inv].filter(Boolean), refs: refsFull,
      checkSeed,
      status: 'Paid'         // event already happened
    });
  }
  // Credit Note (credit) — surface Transaction_Type so the user can
  // tell which kind of invoice the CN is netted against.
  if (Math.abs(+r.cn||0) > 0.01){
    const v = +r.cn || 0;
    const cnn   = String(r.cnn||'').trim();
    const cnTxn = String(r.tt||'').trim();
    const cnLabel = 'Credit note adjusted'
                  + (cnTxn ? (' · ' + cnTxn) : '')
                  + (inv   ? (' · Inv ' + inv) : '');
    out.push({
      date: evDate, type: 'Credit Note', doc: cnn,
      particulars: cnLabel,
      debit:  v < 0 ? Math.abs(v) : 0,
      credit: v > 0 ? v           : 0,
      ref: inv || cnn,
      refList: [inv].filter(Boolean),
      refs: [inv, cnn, utr].filter(Boolean),
      checkSeed,
      status: 'Paid'
    });
  }
  // COD Adjustment (credit)
  if (Math.abs(+r.cod||0) > 0.01){
    const v = +r.cod || 0;
    out.push({
      date: evDate, type: 'COD Adj', doc: inv,
      particulars: 'COD adjustment' + (inv?(' · Inv '+inv):''),
      debit:  v < 0 ? Math.abs(v) : 0,
      credit: v > 0 ? v           : 0,
      ref: inv, refList: [inv].filter(Boolean), refs: refsFull,
      checkSeed,
      status: 'Paid'
    });
  }
  // Bank Charges (credit)
  if (Math.abs(+r.bnk||0) > 0.01){
    const v = +r.bnk || 0;
    out.push({
      date: evDate, type: 'Bank Chg', doc: inv,
      particulars: 'Bank charges deducted' + (inv?(' · Inv '+inv):''),
      debit:  v < 0 ? Math.abs(v) : 0,
      credit: v > 0 ? v           : 0,
      ref: inv, refList: [inv].filter(Boolean), refs: refsFull,
      checkSeed,
      status: 'Paid'
    });
  }
  // PDD (credit)
  if (Math.abs(+r.pdd||0) > 0.01){
    const v = +r.pdd || 0;
    out.push({
      date: evDate, type: 'PDD', doc: inv,
      particulars: 'PDD booked' + (inv?(' · Inv '+inv):''),
      debit:  v < 0 ? Math.abs(v) : 0,
      credit: v > 0 ? v           : 0,
      ref: inv, refList: [inv].filter(Boolean), refs: refsFull,
      checkSeed,
      status: 'Paid'
    });
  }
  // Others / round-off (sign-aware → debit if positive adj raises balance, credit if it lowers)
  if (Math.abs(+r.ror||0) > 0.01){
    const v = +r.ror||0;
    out.push({
      date: evDate, type: 'Adjustment', doc: inv,
      particulars: 'Other / round-off adjustment' + (inv?(' · Inv '+inv):''),
      debit: v > 0 ? v : 0, credit: v < 0 ? Math.abs(v) : 0,
      ref: inv, refList: [inv].filter(Boolean), refs: refsFull,
      checkSeed,
      status: 'Paid'
    });
  }
  // Decorate every emitted line with the source invoice date so buildLedger
  // can identify which adjustments / credits close opening-balance
  // contributors (i.e. underlying invoice date < period start).
  out.forEach(ln => { if (ln.srcD == null) ln.srcD = r.d || ''; });
  return out;
}

// Compute the Indian Financial Year (Apr → Mar) label "FY YY-YY" using
// the EARLIER of two ISO dates (e.g. invoice date vs receipt date). The
// FY anchor is set by whichever event was booked first, since that's
// when the TDS liability arose for the deductor.
//
//   _soaFYLabel('2026-03-15', '2026-05-15') → 'FY 25-26'  (earliest = Mar)
//   _soaFYLabel('2025-05-01', '2024-12-15') → 'FY 24-25'  (earliest = Dec)
//   _soaFYLabel('',           '2026-05-15') → 'FY 26-27'  (only receipt date)
//
// Falls back to a blank string if neither date is parseable.
function _soaFYLabel(invDate, rcptDate){
  const valid = (s) => /^\d{4}-\d{2}-\d{2}/.test(String(s||''));
  let earliest = '';
  if (valid(invDate) && valid(rcptDate))      earliest = invDate < rcptDate ? invDate : rcptDate;
  else if (valid(invDate))                    earliest = invDate;
  else if (valid(rcptDate))                   earliest = rcptDate;
  if (!earliest) return 'FY —';
  const y = parseInt(earliest.slice(0,4), 10);
  const m = parseInt(earliest.slice(5,7), 10);
  // Apr (m≥4) → FY (y)-(y+1); Jan–Mar → FY (y−1)-(y)
  const fyStart = (m >= 4) ? y : y - 1;
  const fyEnd   = fyStart + 1;
  const yy = (n) => String(n).slice(-2).padStart(2,'0');
  return 'FY ' + yy(fyStart) + '-' + yy(fyEnd);
}

// Aggregate payment-in-bank rows by UTR/Bank Ref so a payment that was
// split across N invoices appears ONCE in the ledger (instead of N times
// with the same Doc No). Returns one ledger line per unique UTR.
//
//   arRows — every AR row for the customer
//
// Aggregation key: r.br (UTR/Bank Ref). If a row is missing UTR we fall
// back to a synthetic key of "date|amount" to avoid collapsing unrelated
// receipts together.
//
// Each aggregated line carries:
//   ref   — the UTR (so the client can search payments by UTR)
//   refs  — [UTR, every invoice number this payment touched] — this is
//           the link that lets the UI's reference filter pull up the
//           payment when the client selects any one of those invoices,
//           and pull up every settled invoice when they select the UTR.
function _soaAggregatePayments(arRows){
  // Field reference (from mapARRow):
  //   r.pb = "Payment In Bank"      — TOTAL bank receipt; same value on
  //                                    every split row of one payment.
  //   r.ps = "Payment split Amt"    — PER-INVOICE slice of that receipt.
  // Bug fix: previously this function summed r.pb across split rows, so a
  // Rs.165.04 payment split into 6 invoices showed up as 6 × 165.04 = 990.24.
  // The correct credit is sum(r.ps), or — if ps is unpopulated — the
  // first non-zero r.pb taken ONCE per UTR group (never summed).
  const groups = new Map();
  arRows.forEach(r => {
    const slice    = +r.ps || 0;   // per-invoice settled amount
    const bankTot  = +r.pb || 0;   // bank receipt total (repeated across split rows)
    // Skip rows that contribute nothing to a payment event
    if (Math.abs(slice) <= 0.01 && Math.abs(bankTot) <= 0.01) return;
    const utr = String(r.br||'').trim();
    const evDate = r.rd || r.d || '';
    // Fallback key uses the bank-total (NOT the slice) so split rows of
    // the same UTR-less payment still collapse into one group.
    const key = utr || ('NO-UTR|' + evDate + '|' + (bankTot || slice).toFixed(2));
    let g = groups.get(key);
    if (!g){
      g = {
        utr, date: evDate, type: String(r.pt||''),
        invoices: [],                 // ordered, de-duped invoice list
        invoiceSet: new Set(),
        sliceTot: 0,                  // Σ Payment split Amt  (per-invoice attribution)
        pbAnchor: 0,                  // first non-zero Payment In Bank seen (taken once)
        rowCount: 0,                  // # of split rows in this group
        cnTot: 0,                     // Credit Note adjustments touching this payment
        codTot: 0,                    // COD adjustments
        rorTot: 0,                    // Other / round-off adjustments
        tdsTot: 0,                    // TDS captured against this payment
        bnkTot: 0,                    // Bank charges
        pddTot: 0,                    // PDD
        firstDate: evDate,
        // Settlement key — same value _soaExplodeAR used as checkSeed for
        // every AR row in this group. After buildLedger sorts the lines
        // and assigns sequential Unique Refs, the payment row and all
        // its related invoice / TDS / adjustment rows will share one ref.
        seed: key,
        // allPaid stays true only if every contributing AR row's
        // outstanding balance is zero — i.e. the receipt fully closes
        // every invoice it touched. Otherwise the payment row is marked
        // "Partial" so the user sees at a glance that some invoice is
        // still open against this UTR.
        allPaid: true,
      };
      groups.set(key, g);
    }
    g.sliceTot += slice;
    if (!g.pbAnchor && Math.abs(bankTot) > 0.01) g.pbAnchor = bankTot;
    g.rowCount++;
    g.cnTot  += (+r.cn  || 0);
    g.codTot += (+r.cod || 0);
    g.rorTot += (+r.ror || 0);
    g.tdsTot += (+r.tds || 0);
    g.bnkTot += (+r.bnk || 0);
    g.pddTot += (+r.pdd || 0);
    const inv = String(r.in||'').trim();
    if (inv && !g.invoiceSet.has(inv)){
      g.invoiceSet.add(inv);
      g.invoices.push(inv);
    }
    // Use the earliest receipt date as the ledger date for this payment
    if (evDate && (!g.firstDate || evDate < g.firstDate)) g.firstDate = evDate;
    if (!g.type && r.pt) g.type = String(r.pt);
    // The settlement is "Paid" only when EVERY contributing AR row's
    // outstanding balance nets to zero. Even one open invoice flips this
    // to false → the payment row's status becomes "Partial" so the user
    // can see at a glance that the settlement set isn't fully closed.
    g.allPaid = g.allPaid && (Math.abs(+r.os||0) <= 0.01);
  });
  const fmtAmt = (n)=> '₹' + (Math.round((+n||0)*100)/100).toLocaleString('en-IN',{maximumFractionDigits:2});
  const out = [];
  groups.forEach(g => {
    const invList = g.invoices.slice();
    const docNo = g.utr || '—';
    // Choose the credit amount the right way:
    //  1) Prefer Σ Payment split Amt — this is the per-invoice attribution
    //     and it sums (across split rows) to the original bank receipt.
    //  2) If ps is unpopulated (sliceTot == 0) but pb is filled, fall back
    //     to the bank-total ANCHOR (taken ONCE per UTR, never summed).
    //  3) If both are zero, drop the row — nothing settled here.
    let payAmt = 0;
    if (Math.abs(g.sliceTot) > 0.01) {
      payAmt = g.sliceTot;
    } else if (Math.abs(g.pbAnchor) > 0.01) {
      payAmt = g.pbAnchor;
    }
    if (Math.abs(payAmt) <= 0.01) return;
    // Particulars: list components from the database that contributed to
    // this payment settlement. Only labels with a non-zero amount appear.
    //   "Payment in Bank ₹150.00 · CN Adjustment ₹15.00 · COD Adjustment ₹0.04"
    const parts = [];
    parts.push('Payment in Bank ' + fmtAmt(payAmt));
    if (Math.abs(g.cnTot ) > 0.01) parts.push('CN Adjustment '   + fmtAmt(g.cnTot));
    if (Math.abs(g.codTot) > 0.01) parts.push('COD Adjustment '  + fmtAmt(g.codTot));
    if (Math.abs(g.tdsTot) > 0.01) parts.push('TDS Adjustment '  + fmtAmt(g.tdsTot));
    if (Math.abs(g.bnkTot) > 0.01) parts.push('Bank Charges '    + fmtAmt(g.bnkTot));
    if (Math.abs(g.pddTot) > 0.01) parts.push('PDD '             + fmtAmt(g.pddTot));
    if (Math.abs(g.rorTot) > 0.01) parts.push('Other Adjustment '+ fmtAmt(g.rorTot));
    // Stakeholder asked us to STRIP the Postpaid / Prepaid prefix from
    // payment particulars — only the breakdown (Payment in Bank + TDS /
    // CN / COD / Bank Chg / PDD / Other Adjustment) should show.
    const particulars = parts.join(' · ');
    out.push({
      date: g.firstDate, type: 'Payment', doc: docNo,
      particulars,
      debit: 0,
      // Credit on the ledger = the money actually received in bank.
      // CN/COD/Other/TDS/Bank Chg/PDD still appear as their own ledger
      // rows so the running balance keeps tracking everything individually.
      credit: payAmt,
      // Display reference is the invoice list (invoice-wise details on
      // the payment row, per stakeholder spec). The single `ref` is kept
      // for back-compat (first invoice or UTR).
      ref: invList[0] || g.utr || '—',
      refList: invList,
      // Linked refs: every invoice plus the UTR. Selecting any of these
      // in the UI surfaces this payment alongside the related invoice /
      // TDS / CN / COD / adjustment rows.
      refs: [g.utr, ...invList].filter(Boolean),
      // Settlement seed shared with the invoice/TDS/CN/COD/adj rows that
      // _soaExplodeAR emitted for the same AR rows. After buildLedger
      // sorts and assigns sequential numbers, this whole settlement set
      // shares ONE Unique Ref the client can filter on in Excel / PDF.
      checkSeed: g.seed,
      // "Paid" if every invoice in this settlement closed completely,
      // else "Partial" (e.g. payment short of one invoice's net).
      status: g.allPaid ? 'Paid' : 'Partial'
    });
  });
  return out;
}

// Build the full ledger array (chronological, with running balance)
// for the given customer + date range.
//   cid:       Company ID to match (exact)
//   fromISO:   YYYY-MM-DD inclusive
//   toISO:     YYYY-MM-DD inclusive
// Returns { lines:[...], opening, totDr, totCr, closing, custName, custMeta }
function buildLedger(cid, fromISO, toISO){
  const ar = state.data || [];
  const bk = state.bank || [];
  cid = String(cid||'').trim();
  // 1) Find all matching AR rows for this CID
  const arRows = ar.filter(r => String(r.ci||'').trim() === cid);
  if (!arRows.length) return { lines:[], opening:0, totDr:0, totCr:0, closing:0, custName:'', custMeta:'' };
  // Customer name = first non-empty seller name; meta = CID · BU(s) · Channel(s)
  const custName = arRows.map(r=>r.s).find(Boolean) || '';
  const buSet = [...new Set(arRows.map(r=>r.b).filter(Boolean))];
  const chSet = [...new Set(arRows.map(r=>r.ch).filter(Boolean))];
  const custMeta = `CID ${cid}` + (buSet.length?(' · '+buSet.join(', ')):'') + (chSet.length?(' · '+chSet.join(', ')):'');
  // 2) Explode every AR row into per-event ledger lines (excludes Payment;
  //    payments are aggregated by UTR in step 2b to avoid duplicating the
  //    same payment when one UTR settles multiple invoices).
  let allLines = [];
  arRows.forEach(r => { allLines = allLines.concat(_soaExplodeAR(r)); });
  // 2b) Aggregate payment-in-bank rows by UTR — one ledger line per payment
  allLines = allLines.concat(_soaAggregatePayments(arRows));
  // 3) Also include bank-only receipts for this customer (on-account / unmapped)
  bk.filter(b => String(b.ci||'').trim() === cid).forEach(b => {
    if (Math.abs(+b.amt||0) > 0.01){
      // Only include bank rows that are NOT yet mapped to AR (avoids double-count)
      const isMapped = /applied|partial/i.test(String(b.map||''));
      if (!isMapped){
        const utr = String(b.bk||'').trim();
        // On-account / unmapped bank receipts aren't tied to any AR row,
        // so they get their own settlement seed (per-UTR or per-amount).
        // Status is left as 'Unmatched' so the user can filter on it and
        // chase the mapping with ops if needed.
        const seed = utr
          ? ('BANK|' + utr)
          : ('BANK|' + (b.rd || b.bd || '') + '|' + ((+b.amt||0).toFixed(2)));
        allLines.push({
          date: b.rd || b.bd, type: 'Bank Receipt', doc: utr,
          particulars: ['On-account receipt', b.nar || b.nar2].filter(Boolean).join(' · '),
          debit: 0, credit: +b.amt||0,
          ref: utr || '—',
          refList: [utr].filter(Boolean),
          refs: [utr].filter(Boolean),
          checkSeed: seed,
          status: 'Unmatched'
        });
      }
    }
  });
  // 4) Sort chronologically. Invoice events sort before credit events on same date.
  const typeOrder = (t)=> {
    const k = String(t||'').toLowerCase();
    if (k === 'invoice') return 0;
    if (k.indexOf('adjustment') >= 0) return 1;
    if (k.indexOf('credit note') >= 0) return 2;
    if (k.indexOf('cod') >= 0) return 3;
    if (k.indexOf('tds') >= 0) return 4;
    if (k.indexOf('bank chg') >= 0) return 5;
    if (k.indexOf('pdd') >= 0) return 6;
    if (k.indexOf('payment') >= 0) return 7;
    if (k.indexOf('bank receipt') >= 0) return 8;
    return 9;
  };
  allLines.sort((a,b)=>{
    if (a.date < b.date) return -1;
    if (a.date > b.date) return 1;
    return typeOrder(a.type) - typeOrder(b.type);
  });
  // 4b) Assign sequential Unique Ref numbers (1, 2, 3, …) per unique
  //     checkSeed in chronological encounter order. Same seed = same
  //     number = filter-by-this-number surfaces the entire settlement
  //     set (payment + every invoice / TDS / CN / COD / adjustment row
  //     it touched). This is the integer the client filters on in Excel
  //     / PDF when reconciling. We also append the number to refs[] so
  //     the existing "click a chip → narrow to related rows" UX picks
  //     it up for free.
  const seedToRef = new Map();
  let nextRef = 1;
  allLines.forEach(ln => {
    const seed = ln.checkSeed || '';
    if (!seed){ ln.checkRef = ''; return; }
    if (!seedToRef.has(seed)) seedToRef.set(seed, nextRef++);
    ln.checkRef = seedToRef.get(seed);
    ln.refs = (ln.refs || []).concat([String(ln.checkRef)]);
  });
  // 5) Compute opening balance (sum of all events strictly before fromISO)
  //    Bad Debt write-offs are a special case: they're often dated to the
  //    FY-end immediately BEFORE the window (e.g. 31-Mar-2025 to wipe an
  //    opening that lingered from FY24-25), but the stakeholder needs to
  //    SEE them inline so it's obvious why the opening is zero. So we:
  //      * Adjustment lines (write-offs / internal transfers) are now
  //        dated by their CLOSURE event — receipt date when closed,
  //        invoice date when still open (see _soaExplodeAR). That means
  //        a closed write-off naturally lands inside the period if the
  //        receipt fell inside the period, and rolls into opening when
  //        the receipt was before the window (the opening already
  //        reflects the closure, so there's nothing to show inline).
  //      * Older versions of this code unconditionally surfaced every
  //        bad-debt-tagged line in inRange. That bypass is no longer
  //        needed and was actively harmful — it'd double-count an
  //        already-closed write-off both in the opening AND in the body.
  //        We retain a narrower bypass for STILL-OPEN write-offs whose
  //        invoice date is before the window, so they don't disappear
  //        silently from the audit trail.
  let opening = 0;
  const inRange = [];
  for (const ln of allLines){
    if (!ln.date) { continue; }
    if (fromISO && ln.date < fromISO){
      // Open write-offs dated before the window: keep visible AND skip
      // the opening contribution. Otherwise the customer would see a
      // write-off line that affects the opening balance without any
      // body row explaining where the opening came from.
      // Also keep CLOSED write-offs that lack a receipt date — there is
      // no meaningful date to post the credit on inside the window, so
      // surface the invoice line (and its receipt credit at invoice date,
      // emitted by _soaExplodeAR) rather than absorbing it into opening.
      if (ln.isWriteOff && (String(ln.status||'') === 'Unpaid' || !ln.rd)){
        inRange.push(ln);
        continue;
      }
      opening += (+ln.debit||0) - (+ln.credit||0);
    } else if (toISO && ln.date > toISO){
      // out of range — skip
    } else {
      inRange.push(ln);
    }
  }
  // 6) Compute running balance starting from opening
  let bal = opening;
  let totDr = 0, totCr = 0;
  inRange.forEach(ln => {
    bal += (+ln.debit||0) - (+ln.credit||0);
    ln.balance = bal;
    totDr += (+ln.debit||0);
    totCr += (+ln.credit||0);
  });
  // 7) Reconcile against AR_Data.Company_Level_Due — this is the master
  //    "what the customer owes us" figure. The SOA closing must tie out
  //    to it so a customer's statement always matches AR's number. If
  //    there's a mismatch (rounding noise from PDD timing, unmapped
  //    receipts after toISO, manual journal entries not yet in AR, etc.)
  //    we surface an explicit "Reconciliation adjustment" line so the
  //    audit trail is transparent. We only enforce this when the period
  //    end is today-or-later (otherwise Company_Level_Due — which is the
  //    as-of-now snapshot — wouldn't be the right anchor for a historical
  //    statement). cld is read from any non-zero row for the CID.
  let targetClosing = 0;
  let haveCld = false;
  for (const ar of arRows){
    const v = +ar.cld || 0;
    if (Math.abs(v) > 0.01){ targetClosing = v; haveCld = true; break; }
  }
  const todayISO = new Date().toISOString().slice(0,10);
  const reconcileToCld = haveCld && (!toISO || toISO >= todayISO);
  if (reconcileToCld){
    const diff = +(targetClosing - bal).toFixed(2);
    if (Math.abs(diff) > 0.01){
      // Positive diff → AR shows MORE owed than our running balance →
      // post as Debit (extra invoice-side). Negative → AR shows LESS →
      // post as Credit (extra collection-side).
      const reconLine = {
        date: toISO || todayISO,
        type: 'Adjustment',
        doc: '',
        particulars: 'Reconciliation to AR_Data · Company Level Due',
        debit:  diff > 0 ?  diff           : 0,
        credit: diff < 0 ?  Math.abs(diff) : 0,
        ref: 'RECON',
        refList: ['RECON'],
        refs: ['RECON'],
        checkSeed: 'RECON|' + cid,
        status: 'Paid',
        srcD: ''  // recon line — not tied to an underlying invoice
      };
      // Append + reflect in totals + running balance.
      inRange.push(reconLine);
      bal += (reconLine.debit - reconLine.credit);
      reconLine.balance = bal;
      totDr += reconLine.debit;
      totCr += reconLine.credit;
    }
  }
  // 8) Opening-balance refs: any adjustment / credit row in inRange
  //    whose underlying invoice date is BEFORE fromISO is, by
  //    construction, a closure event for an opening-balance contributor.
  //    Surface those Unique Refs on the opening row so the reader can
  //    pivot from "what made up my opening?" straight to the rows that
  //    closed it.
  const openingRefs = [];
  const seenRefs = {};
  if (fromISO){
    inRange.forEach(ln => {
      if (ln.checkRef == null || ln.checkRef === '') return;
      const sd = String(ln.srcD || '');
      if (!sd || sd >= fromISO) return;       // only opening-period sources
      const t = String(ln.type||'').toLowerCase();
      // Adjustment / TDS / CN / COD / Bank Chg / PDD / Payment are all
      // settlement-side; the invoice itself doesn't tell us anything new.
      if (t === 'invoice') return;
      const key = String(ln.checkRef);
      if (seenRefs[key]) return;
      seenRefs[key] = true;
      openingRefs.push(ln.checkRef);
    });
  }
  return {
    lines: inRange, opening, totDr, totCr, closing: bal,
    custName, custMeta, openingRefs
  };
}

// ----- Customer picker -----
function _soaUniqueCustomers(){
  const ar = state.data || [];
  const map = new Map(); // cid → name
  ar.forEach(r => {
    const cid = String(r.ci||'').trim();
    const nm  = String(r.s||'').trim();
    if (!cid) return;
    if (!map.has(cid) || (!map.get(cid) && nm)) map.set(cid, nm);
  });
  return [...map.entries()].map(([cid,nm])=>({cid,name:nm}))
    .sort((a,b)=> (a.name||a.cid).localeCompare(b.name||b.cid));
}

function _soaRenderCustList(query){
  const list = document.getElementById('soaCustList');
  if (!list) return;
  const q = String(query||'').trim().toLowerCase();
  const all = _soaUniqueCustomers();
  // If a customer has already been picked AND the input value still
  // matches the "<name> · CID <cid>" shape we wrote on selection, the
  // user just clicked back into the field — they aren't searching, so
  // treat the query as empty so they can scroll the full list to
  // re-pick. Without this, the populated input value filters down to
  // zero rows and we'd misleadingly show "No customers — connect Live
  // in Settings first." even though there are plenty of customers.
  const lookingHasSelection = !!(soaState && soaState.cid);
  const looksLikeSelectedLabel = / · CID\s+\d+/i.test(String(query||''));
  const effectiveQ = (lookingHasSelection && looksLikeSelectedLabel) ? '' : q;
  const rows = effectiveQ
    ? all.filter(c => (c.name+' '+c.cid).toLowerCase().indexOf(effectiveQ) >= 0).slice(0, 60)
    : all.slice(0, 60);
  if (!rows.length){
    // Distinguish "no data loaded" from "your query didn't match" so we
    // don't tell the user to connect Live when they have a perfectly
    // good selection — they just typed something that doesn't match.
    if (!all.length){
      list.innerHTML = '<div style="padding:8px 10px;color:#94a3b8;font-size:12px">No customers — connect Live in Settings first.</div>';
      list.style.display = 'block';
    } else {
      // No matches for the query, but data exists — hide the list
      // silently. The input keeps the user's text and a matching pick
      // is still possible by editing the query.
      list.style.display = 'none';
    }
    return;
  }
  list.innerHTML = rows.map(r => `
    <div class="soa-cust-opt" data-cid="${r.cid}" data-name="${(r.name||'').replace(/"/g,'&quot;')}"
         style="padding:7px 10px;cursor:pointer;border-bottom:1px solid #f1f5f9;font-size:12px">
      <div style="font-weight:600;color:#0f172a">${r.name||'(unnamed)'}</div>
      <div style="color:#64748b;font-size:11px">CID ${r.cid}</div>
    </div>`).join('');
  list.style.display = 'block';
  list.querySelectorAll('.soa-cust-opt').forEach(opt => {
    opt.addEventListener('mouseenter', ()=> opt.style.background = '#f8fafc');
    opt.addEventListener('mouseleave', ()=> opt.style.background = '#fff');
    opt.addEventListener('click', ()=>{
      const cid = opt.dataset.cid;
      const name = opt.dataset.name;
      soaState.cid = cid;
      soaState.custName = name;
      const inp = document.getElementById('soaCustomer');
      if (inp) {
        inp.value = `${name} · CID ${cid}`;
        // Drop focus from the input so the focus listener doesn't re-open the
        // dropdown the moment we close it. Without blur(), the click that
        // landed on the option leaves the input focused — and any subsequent
        // re-render (auto-generate paint, document click, etc.) was leaving
        // the list visible because the focus handler had already fired
        // _soaRenderCustList(inp.value) with the populated "name · CID"
        // label, which the dropdown treats as "show all customers".
        try { inp.blur(); } catch(_){ }
      }
      list.style.display = 'none';
      // Belt-and-braces: a layout pass can re-paint the list mid-frame; pin
      // it closed on the next tick too, so any racing render is overruled.
      setTimeout(() => { try { list.style.display = 'none'; } catch(_){ } }, 0);
      // Auto-generate the statement now that we have a customer — saves
      // the user a click. Skips silently if dates aren't set yet.
      _soaAutoGenerate();
    });
  });
}

// ----- Date helpers -----
function _soaToday(){
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function _soaFYStart(){
  // Indian FY starts Apr 1. If today is Jan-Mar, FY started previous year.
  const d = new Date();
  const y = d.getMonth() < 3 ? d.getFullYear() - 1 : d.getFullYear();
  return `${y}-04-01`;
}
// Earliest available data point in the AR universe.
// AR feed starts at Apr 1, 2025 — All-time always anchors here regardless of customer.
const SOA_DATA_START = '2025-04-01';
function _soaEarliestDate(_cid){ return SOA_DATA_START; }

// Escape helper for safely embedding ref values inside HTML attributes.
function _soaEsc(s){
  return String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Render the Reference column as a flat comma-joined string. Used by
// Excel / PDF / Email exports where we can't have per-chip click
// handlers — so the cell becomes plain text "INV001, INV002, INV003".
function _soaRefStr(ln){
  if (Array.isArray(ln.refList) && ln.refList.length) return ln.refList.join(', ');
  return ln.ref || '';
}

// ----- Render the ledger to the preview -----
// Renders TWO things:
//   1) The full ledger preview into #soaTbody (unfiltered — the source of
//      truth, used by Excel/PDF/Email downloads).
//   2) The "filter chip" + body, if soaState.filterRef is set, which
//      narrows the on-screen body to just the rows whose refs[] include
//      the active reference. This is the "select one reference → show
//      all related transactions" behaviour the stakeholder asked for.
function _soaRender(led, fromISO, toISO){
  const ledger = document.getElementById('soaLedger');
  if (!ledger) return;
  // Header bits
  document.getElementById('soaGenAt').textContent = new Date().toLocaleString('en-IN');
  document.getElementById('soaPeriod').textContent = `${fmtDateOut(fromISO)} → ${fmtDateOut(toISO)}`;
  document.getElementById('soaCustName').textContent = led.custName || '(unnamed)';
  document.getElementById('soaCustMeta').textContent = led.custMeta || '';
  // Totals
  document.getElementById('soaOpening').textContent = fmtINRfull(led.opening);
  document.getElementById('soaTotDr').textContent  = fmtINRfull(led.totDr);
  document.getElementById('soaTotCr').textContent  = fmtINRfull(led.totCr);
  document.getElementById('soaClosing').textContent = fmtINRfull(led.closing);
  document.getElementById('soaFtDr').textContent = fmtINRfull(led.totDr);
  document.getElementById('soaFtCr').textContent = fmtINRfull(led.totCr);
  // "Balance as on <to-date>" footer row — surfaces the closing balance
  // for the period without needing a per-row Balance column.
  const balDt = document.getElementById('soaBalAsOnDate');
  if (balDt) balDt.textContent = fmtDateOut(toISO);
  const balV = document.getElementById('soaBalAsOnVal');
  if (balV) balV.textContent = fmtINRfull(led.closing);

  // Stash full unfiltered data first — downloads always use this.
  soaState.lines    = led.lines;
  soaState.opening  = led.opening;
  soaState.totDr    = led.totDr;
  soaState.totCr    = led.totCr;
  soaState.closing  = led.closing;
  soaState.openingRefs = led.openingRefs || [];
  soaState.custName = led.custName;
  soaState.custMeta = led.custMeta;
  soaState.fromDate = fromISO;
  soaState.toDate   = toISO;
  // Fresh statement → reset status filter to "All" so the new build
  // surfaces every line. The user can re-apply a filter after.
  soaState.statusFilter = 'All';
  _soaPaintStatusChips();

  _soaPaintBody();

  ledger.style.display = 'block';
  // Enable download buttons
  document.getElementById('soaDlXlsx').disabled = false;
  document.getElementById('soaDlPdf').disabled  = false;
  document.getElementById('soaEmail').disabled  = false;
}

// Paint (or repaint) the table body. Honours soaState.filterRef so the
// reference-filter chip can re-narrow the view without rebuilding the
// whole ledger.
function _soaPaintBody(){
  const tb = document.getElementById('soaTbody');
  if (!tb) return;
  const lines = soaState.lines || [];
  const filterRef = String(soaState.filterRef || '').trim();
  const statusFilter = String(soaState.statusFilter || 'All').trim() || 'All';
  // Refresh the filter chip
  const bar = document.getElementById('soaRefBar');
  const barVal = document.getElementById('soaRefBarVal');
  const barCnt = document.getElementById('soaRefBarCount');
  // Decide what's visible
  let visible = lines;
  if (filterRef){
    visible = lines.filter(ln => Array.isArray(ln.refs) && ln.refs.indexOf(filterRef) >= 0);
    if (bar){ bar.style.display = 'flex'; }
    if (barVal){ barVal.textContent = filterRef; }
    if (barCnt){ barCnt.textContent = '· ' + visible.length + ' transaction' + (visible.length===1?'':'s'); }
  } else {
    if (bar){ bar.style.display = 'none'; }
  }
  // Apply Status filter (preview-only). 'All' is a passthrough.
  if (statusFilter && statusFilter !== 'All'){
    visible = visible.filter(ln => String(ln.status||'').trim() === statusFilter);
  }
  // Surface a per-status hit count next to the chip group.
  const sCount = document.getElementById('soaStatusCount');
  if (sCount){
    if (statusFilter && statusFilter !== 'All'){
      sCount.textContent = '· ' + visible.length + ' row' + (visible.length===1?'':'s') + ' match "' + statusFilter + '"';
    } else {
      sCount.textContent = '';
    }
  }

  // ----- Footer totals: subtotal of VISIBLE rows when any filter is
  // active; full period totals when "All / no ref" is showing.
  // The user explicitly asked: "When i click on reference number then
  // below total should also change, as it should calculate as subtotal
  // of selected fields." So the Period totals + Balance-as-on row now
  // track the visible set.
  //
  // Stakeholder ask (Jun 2026): "the subtotal should calculate from
  // opening balance row not from after that row." → fold the opening
  // balance into the running subtotal so the displayed "Balance as on"
  // ties back to a hand-tally that starts with the Opening line.
  // Convention used by the rest of the SOA:
  //   positive opening → debit-side opening (customer owes us)
  //   negative opening → credit-side opening (we owe customer)
  // So we contribute the absolute value of opening to the matching column.
  const anyFilter = !!filterRef || (statusFilter && statusFilter !== 'All');
  const opening = +soaState.opening || 0;
  let ftDr = 0, ftCr = 0;
  if (anyFilter){
    visible.forEach(ln => { ftDr += (+ln.debit||0); ftCr += (+ln.credit||0); });
  } else {
    ftDr = +soaState.totDr || 0;
    ftCr = +soaState.totCr || 0;
    // Opening row participates in the unfiltered subtotal — it's the
    // first row of the visible ledger and the user expects the bottom
    // total to include it.
    if (opening > 0) ftDr += opening;
    else if (opening < 0) ftCr += Math.abs(opening);
  }
  const ftDrEl = document.getElementById('soaFtDr');
  const ftCrEl = document.getElementById('soaFtCr');
  if (ftDrEl) ftDrEl.textContent = fmtINRfull(ftDr);
  if (ftCrEl) ftCrEl.textContent = fmtINRfull(ftCr);
  // Balance-as-on row: when filtered, show the running net of the
  // visible rows (no opening contribution — opening is a period concept
  // and doesn't make sense inside a per-reference / per-status slice).
  // When unfiltered, this is the closing balance of the period (which
  // already includes opening by construction in buildLedger).
  const balEl = document.getElementById('soaBalAsOnVal');
  const balDateEl = document.getElementById('soaBalAsOnDate');
  if (balEl){
    if (anyFilter){
      balEl.textContent = fmtINRfull(ftDr - ftCr);
    } else {
      balEl.textContent = fmtINRfull(+soaState.closing || 0);
    }
  }
  // The footer prefix label should reflect what we're summing:
  //   • Unfiltered  → "Balance as on <to-date>"
  //   • Filtered    → "Subtotal of <N> filtered row(s)"
  const balLblEl = document.getElementById('soaBalAsOnLbl');
  if (anyFilter){
    if (balLblEl)  balLblEl.textContent = 'Subtotal of ' + visible.length + ' filtered row' + (visible.length===1?'':'s');
    if (balDateEl) balDateEl.textContent = '';
  } else {
    if (balLblEl)  balLblEl.textContent = 'Balance as on';
    if (balDateEl) balDateEl.textContent = fmtDateOut(soaState.toDate);
  }

  if (visible.length === 0){
    const why = filterRef
      ? 'No transactions match this reference.'
      : (statusFilter !== 'All' ? 'No transactions match this status.' : 'No transactions in this date range.');
    tb.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:18px;color:#94a3b8">${why}</td></tr>`;
    return;
  }
  // Opening row (only when no filter is active — opening b/f isn't meaningful inside a per-reference view).
  // Preview layout has NO Balance column, so we show the opening amount in
  // Debit (if owed by customer) or Credit (if advance / credit balance).
  let html = '';
  if (!filterRef && statusFilter === 'All'){
    const op = +soaState.opening || 0;
    const opDr = op >= 0 ? fmtINRfull(op) : '—';
    const opCr = op <  0 ? fmtINRfull(-op) : '—';
    // Surface the Unique Ref numbers of the adjustment / payment rows
    // that closed opening-balance contributors. Each ref becomes a
    // clickable chip that narrows the body to the rows sharing that ref.
    const oRefs = Array.isArray(soaState.openingRefs) ? soaState.openingRefs : [];
    const opRefCell = oRefs.length
      ? oRefs.map(n => `<span class="ref-chip" data-ref="${String(n)}" style="cursor:pointer">${String(n)}</span>`).join(' ')
      : '—';
    html += `<tr class="soa-open-row">
      <td>—</td><td>${fmtDateOut(soaState.fromDate)}</td><td colspan="4" style="font-weight:600;color:#334155">Opening balance carried forward</td>
      <td class="soa-num" style="font-weight:700">${opDr}</td>
      <td class="soa-num" style="font-weight:700">${opCr}</td>
      <td class="soa-num">${opRefCell}</td>
      <td></td>
    </tr>`;
  }
  // Tiny pill style for the Status column. Paid = green, Partial =
  // amber, Unpaid = slate, Unmatched = blue. Kept inline so the column
  // is self-contained (no new global CSS needed).
  const statusPill = (s) => {
    const v = String(s||'').trim();
    let bg = '#f1f5f9', fg = '#334155', bd = '#e2e8f0';
    if (v === 'Paid')           { bg='#dcfce7'; fg='#166534'; bd='#86efac'; }
    else if (v === 'Partial')   { bg='#fef3c7'; fg='#92400e'; bd='#fcd34d'; }
    else if (v === 'Unpaid')    { bg='#fee2e2'; fg='#991b1b'; bd='#fca5a5'; }
    else if (v === 'Unmatched') { bg='#dbeafe'; fg='#1e40af'; bd='#93c5fd'; }
    if (!v) return '<span style="color:#94a3b8">—</span>';
    return `<span style="display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;background:${bg};color:${fg};border:1px solid ${bd}">${v}</span>`;
  };
  visible.forEach((ln, i) => {
    // The Reference cell may contain MULTIPLE invoice numbers (e.g. for
    // a Payment row that settled 6 invoices). Each chip is independently
    // clickable — selecting one re-narrows the view to "everything
    // linked to that reference". refs[] holds the full cross-link list
    // (invoice ↔ payment ↔ TDS ↔ CN ↔ COD ↔ adj).
    const refList = Array.isArray(ln.refList) && ln.refList.length
      ? ln.refList
      : (ln.ref ? [ln.ref] : []);
    let refCell;
    if (!refList.length){
      refCell = `<span style="color:#94a3b8">—</span>`;
    } else {
      refCell = refList.map(r => {
        const a = _soaEsc(r);
        return `<button class="soa-ref-btn" data-ref="${a}" title="Show all transactions against ${a}" style="background:none;border:none;padding:0 4px 0 0;margin:0 2px 2px 0;color:#0369a1;font:inherit;font-family:ui-monospace,monospace;font-size:11px;cursor:pointer;text-decoration:underline">${a}</button>`;
      }).join('');
    }
    // Unique Ref cell — sequential integer (1, 2, 3, …) shared by every
    // row in one settlement group. Rendered as a click-to-filter chip:
    // selecting a number narrows the view to the entire settlement set
    // (payment + every invoice/TDS/CN/COD/adj it touched).
    const cRef = (ln.checkRef === 0 || ln.checkRef) ? String(ln.checkRef) : '';
    const checkCell = cRef
      ? `<button class="soa-ref-btn" data-ref="${_soaEsc(cRef)}" title="Show every row in settlement #${_soaEsc(cRef)}" style="background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;font:inherit;font-family:ui-monospace,monospace;font-size:11px;cursor:pointer;padding:2px 8px;border-radius:999px;font-weight:600">${_soaEsc(cRef)}</button>`
      : `<span style="color:#94a3b8">—</span>`;
    // Preview layout: NO running-balance cell — closing balance is
    // surfaced in the highlighted "Balance as on" footer row. Excel /
    // PDF / Email exports still include the per-row Balance column for
    // external receivers who need the running total.
    html += `<tr>
      <td>${i+1}</td>
      <td>${fmtDateOut(ln.date)}</td>
      <td><span class="soa-pill ${_soaPillCls(ln.type)}">${ln.type}</span></td>
      <td style="font-family:ui-monospace,monospace;font-size:11px">${_soaEsc(ln.doc||'—')}</td>
      <td>${refCell}</td>
      <td>${_soaEsc(ln.particulars||'—')}</td>
      <td class="soa-num">${ln.debit ? fmtINRfull(ln.debit) : '—'}</td>
      <td class="soa-num">${ln.credit ? fmtINRfull(ln.credit) : '—'}</td>
      <td style="text-align:center">${checkCell}</td>
      <td style="text-align:center">${statusPill(ln.status)}</td>
    </tr>`;
  });
  tb.innerHTML = html;
  // Wire up reference clicks (each chip can drive its own filter)
  tb.querySelectorAll('.soa-ref-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const ref = btn.getAttribute('data-ref') || '';
      if (!ref) return;
      soaState.filterRef = ref;
      _soaPaintBody();
    });
  });
}

// Clear the active reference filter and repaint.
function _soaClearRefFilter(){
  soaState.filterRef = '';
  _soaPaintBody();
}

// ----- Generate -----
function soaGenerate(){
  const cid = soaState.cid;
  const fromISO = document.getElementById('soaFrom').value;
  const toISO   = document.getElementById('soaTo').value;
  const status = document.getElementById('soaStatus');
  if (!cid){ status.innerHTML = '<span style="color:#b91c1c">Please pick a customer first.</span>'; return; }
  if (!fromISO || !toISO){ status.innerHTML = '<span style="color:#b91c1c">Pick both From and To dates.</span>'; return; }
  if (fromISO > toISO){ status.innerHTML = '<span style="color:#b91c1c">From date is after To date.</span>'; return; }
  status.textContent = 'Building ledger…';
  // Reset any prior reference filter — a fresh generation should start
  // with the full view, otherwise the old chip lingers across runs.
  soaState.filterRef = '';
  setTimeout(()=>{
    const led = buildLedger(cid, fromISO, toISO);
    _soaRender(led, fromISO, toISO);
    status.innerHTML = `<span style="color:#15803d">${led.lines.length} transactions · Closing ${fmtINRfull(led.closing)}</span>`;
  }, 30);
}

// Silent auto-generate: fires when customer picked / dates changed /
// quick-preset clicked. Skips quietly if pre-conditions aren't met,
// so the user isn't pestered with "please pick a customer first" on
// every keystroke. Manual "Generate Statement" button still validates
// loudly via soaGenerate().
function _soaAutoGenerate(){
  const cid = soaState.cid;
  if (!cid) return;
  const f = document.getElementById('soaFrom');
  const t = document.getElementById('soaTo');
  if (!f || !t) return;
  const fromISO = f.value, toISO = t.value;
  if (!fromISO || !toISO) return;
  if (fromISO > toISO) return;
  soaGenerate();
}

// ----- Reset -----
// Restores the SOA panel to a pristine state: clears the customer,
// resets dates to current FY, wipes filters, hides the preview, and
// disables the download/email buttons.
function soaReset(){
  // Clear core state
  soaState.cid = '';
  soaState.custName = '';
  soaState.custMeta = '';
  soaState.fromDate = '';
  soaState.toDate = '';
  soaState.lines = [];
  soaState.opening = 0;
  soaState.totDr = 0;
  soaState.totCr = 0;
  soaState.closing = 0;
  soaState.filterRef = '';
  soaState.statusFilter = 'All';
  // Clear inputs
  const inp = document.getElementById('soaCustomer');
  if (inp) inp.value = '';
  const dF = document.getElementById('soaFrom');
  const dT = document.getElementById('soaTo');
  if (dF) dF.value = _soaFYStart();
  if (dT) dT.value = _soaToday();
  // Hide picker dropdown if open
  const list = document.getElementById('soaCustList');
  if (list) list.style.display = 'none';
  // Hide preview
  const led = document.getElementById('soaLedger');
  if (led) led.style.display = 'none';
  // Disable downloads / email
  const dx = document.getElementById('soaDlXlsx'); if (dx) dx.disabled = true;
  const dp = document.getElementById('soaDlPdf');  if (dp) dp.disabled = true;
  const de = document.getElementById('soaEmail');  if (de) de.disabled = true;
  // Wipe status message
  const st = document.getElementById('soaStatus');
  if (st) st.innerHTML = '<span style="color:#0f172a">Reset · Pick a customer to begin.</span>';
  // Repaint status chips so the "All" chip looks selected again
  _soaPaintStatusChips();
  // Clear status-count badge
  const sc = document.getElementById('soaStatusCount');
  if (sc) sc.textContent = '';
}

// Paint the status filter chip group so the currently-active status
// is visually highlighted. Called on init and after each chip click.
function _soaPaintStatusChips(){
  const wrap = document.getElementById('soaStatusFilter');
  if (!wrap) return;
  const active = String(soaState.statusFilter || 'All') || 'All';
  wrap.setAttribute('data-active', active);
  // Per-status colour palette — matches the in-row status pills so the
  // chip and the row visually agree once the filter is applied.
  const palette = {
    'All':       { bg:'#0f172a', fg:'#ffffff', bd:'#0f172a' },
    'Paid':      { bg:'#16a34a', fg:'#ffffff', bd:'#16a34a' },
    'Partial':   { bg:'#d97706', fg:'#ffffff', bd:'#d97706' },
    'Unpaid':    { bg:'#dc2626', fg:'#ffffff', bd:'#dc2626' },
    'Unmatched': { bg:'#2563eb', fg:'#ffffff', bd:'#2563eb' }
  };
  wrap.querySelectorAll('.soa-status-chip').forEach(btn => {
    const s = btn.getAttribute('data-status') || 'All';
    const on = (s === active);
    const c = palette[s] || palette['All'];
    if (on){
      btn.style.background = c.bg;
      btn.style.color = c.fg;
      btn.style.borderColor = c.bd;
      btn.style.fontWeight = '700';
    } else {
      btn.style.background = '#fff';
      btn.style.color = '#475569';
      btn.style.borderColor = '#cbd5e1';
      btn.style.fontWeight = '500';
    }
  });
}

// ----- Common file-name helper: CID_CustomerName_Ledger_YYYY-MM-DD_to_YYYY-MM-DD -----
function _soaFileBase(){
  const safeCust = String(soaState.custName||'').replace(/[^A-Za-z0-9]+/g,'_').replace(/^_+|_+$/g,'').slice(0,40) || 'Customer';
  return `${soaState.cid}_${safeCust}_Ledger_${soaState.fromDate}_to_${soaState.toDate}`;
}

// ----- Lazy-load xlsx-js-style (styled cell support, drop-in upgrade to SheetJS) -----
function _soaEnsureXLSX(){
  return new Promise((resolve, reject)=>{
    // xlsx-js-style is a superset of SheetJS — if vanilla SheetJS was already
    // loaded earlier, we still load the styled fork on top so cell .s works.
    if (window.XLSX && window.XLSX.__styled) return resolve(window.XLSX);
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js';
    s.onload = ()=>{ try { window.XLSX.__styled = true; } catch(_){} resolve(window.XLSX); };
    s.onerror = ()=> reject(new Error('Failed to load xlsx-js-style'));
    document.head.appendChild(s);
  });
}

// Convert (r,c) → "A1" notation, supporting AA..AZ.
function _soaA1(r,c){
  let s = '';
  c = c|0;
  while (c >= 0){ s = String.fromCharCode(65 + (c%26)) + s; c = Math.floor(c/26) - 1; }
  return s + (r+1);
}

async function soaDownloadXlsx(){
  if (!soaState.lines || !soaState.cid) return;
  const XLSX = await _soaEnsureXLSX();

  // Style palette — matches the on-screen ledger
  const TEAL    = '2C4A52';
  const TEAL_LT = 'EAF1F2';
  const SAND    = 'FDFCF7';
  const STRIPE  = 'F8FAF9';
  const INK     = '1F2A2E';
  const SOFT_BD = 'CBD5E1';

  const sBorder = (col)=> ({
    top:    {style:'thin', color:{rgb: col||SOFT_BD}},
    bottom: {style:'thin', color:{rgb: col||SOFT_BD}},
    left:   {style:'thin', color:{rgb: col||SOFT_BD}},
    right:  {style:'thin', color:{rgb: col||SOFT_BD}},
  });

  // Build row data
  const rows = [];
  const merges = [];
  const styles = []; // {addr, style}

  // Sheet is 10 columns wide (the running Balance column was dropped per
  // user request — the closing balance is shown in the "Balance as on"
  // footer instead). Column layout:
  //   0 #   1 Date   2 Type   3 Doc No   4 Reference   5 Particulars
  //   6 Debit   7 Credit   8 Unique Ref   9 Status
  // Excel's autofilter is enabled below so the client can pivot on any
  // column including Payment, Unique Ref and Status.
  const COLS = 10;
  const blank = (n)=> Array(n).fill('');
  // r=0 : Banner title
  rows.push(['STATEMENT OF ACCOUNT', ...blank(COLS-1)]);
  merges.push({s:{r:0,c:0},e:{r:0,c:COLS-1}});
  // r=1 : Company subtitle
  rows.push(['Shopsense Retail Technologies Ltd.', ...blank(COLS-1)]);
  merges.push({s:{r:1,c:0},e:{r:1,c:COLS-1}});
  // r=2 : Mumbai / India subtitle
  rows.push(['Mumbai · India', ...blank(COLS-1)]);
  merges.push({s:{r:2,c:0},e:{r:2,c:COLS-1}});
  rows.push([]);
  // r=4..7 : Customer block (label | value spans the remaining cols)
  // CID/Meta in exports keeps ONLY the CID — the stakeholder asked us
  // to strip Region / Business Unit / Channel from the value here so it
  // reads "CID : 292" instead of "CID 292 · India · Store OS, …".
  rows.push(['Customer', soaState.custName, ...blank(COLS-2)]);
  merges.push({s:{r:4,c:1},e:{r:4,c:COLS-1}});
  rows.push(['CID', soaState.cid ? String(soaState.cid) : '', ...blank(COLS-2)]);
  merges.push({s:{r:5,c:1},e:{r:5,c:COLS-1}});
  rows.push(['Period', `${fmtDateOut(soaState.fromDate)} → ${fmtDateOut(soaState.toDate)}`, ...blank(COLS-2)]);
  merges.push({s:{r:6,c:1},e:{r:6,c:COLS-1}});
  rows.push(['Generated', new Date().toLocaleString('en-IN'), ...blank(COLS-2)]);
  merges.push({s:{r:7,c:1},e:{r:7,c:COLS-1}});
  rows.push([]);
  // r=9 : Summary band header — 4 sections distributed across 10 cols.
  // Opening 0..1 (2), Debits 2..4 (3), Credits 5..6 (2), Closing 7..9 (3).
  const sumRanges = [[0,1],[2,4],[5,6],[7,9]];
  const sumHdr = blank(COLS);
  sumHdr[0]='Opening (₹)'; sumHdr[2]='Debits (₹)'; sumHdr[5]='Credits (₹)'; sumHdr[7]='Closing (₹)';
  rows.push(sumHdr);
  sumRanges.forEach(([c0,c1])=> merges.push({s:{r:9,c:c0},e:{r:9,c:c1}}));
  // r=10 : Summary values
  const sumVals = blank(COLS);
  sumVals[0]=soaState.opening; sumVals[2]=soaState.totDr; sumVals[5]=soaState.totCr; sumVals[7]=soaState.closing;
  rows.push(sumVals);
  sumRanges.forEach(([c0,c1])=> merges.push({s:{r:10,c:c0},e:{r:10,c:c1}}));
  rows.push([]);
  // r=12 : Ledger table header — Unique Ref + Status follow the credit column
  rows.push(['#','Date','Type','Doc No','Reference','Particulars','Debit (₹)','Credit (₹)','Unique Ref','Status']);
  // r=13 : Opening b/f — Type+Doc+Ref+Particulars merged into the note,
  // opening balance is shown on the Credit column. Unique Ref carries
  // a comma list of the adjustment refs that closed opening contributors.
  const _xlsxOpRefs = Array.isArray(soaState.openingRefs) ? soaState.openingRefs.join(', ') : '';
  rows.push(['', fmtDateOut(soaState.fromDate),'','','', 'Opening balance carried forward','', soaState.opening, _xlsxOpRefs, '']);
  merges.push({s:{r:13,c:2},e:{r:13,c:5}});
  // r=14.. : ledger lines (no running Balance column)
  const startBodyRow = 14;
  soaState.lines.forEach((ln,i)=>{
    const cRef = (ln.checkRef === 0 || ln.checkRef) ? ln.checkRef : '';
    rows.push([
      i+1, fmtDateOut(ln.date), ln.type, ln.doc||'', _soaRefStr(ln), ln.particulars||'',
      ln.debit||0, ln.credit||0,
      cRef, ln.status || ''
    ]);
  });
  const endBodyRow = startBodyRow + soaState.lines.length - 1;
  // Period totals row + a separate "Balance as on" footer that replaces the
  // running balance column (mirrors the on-screen footer).
  const totalsRow = endBodyRow + 1;
  rows.push(['','','','','', 'Period totals', soaState.totDr, soaState.totCr, '','']);
  const balRow = totalsRow + 1;
  // Place the closing figure in the column matching its sign so the label
  // and value land next to each other (banking convention: a positive
  // closing = customer owes us = debit-side; a negative closing = we owe
  // customer = credit-side). Stakeholder fix: the prior layout left an
  // empty Debit column between the "Balance as on…" label and the value,
  // and in some Excel viewers the gap broke the merge so the label
  // appeared to be missing altogether. Now the label merge spans cols
  // 0..5 and the value sits in col 6 OR 7 based on sign — never both.
  const closingV = +soaState.closing || 0;
  const balLabel = `Balance as on ${fmtDateOut(soaState.toDate)}`;
  if (closingV >= 0){
    // Positive closing → Debit-side balance. Value goes in col 6.
    rows.push(['','','','','', balLabel, closingV, '', '','']);
  } else {
    // Negative closing → Credit-side balance. Show absolute value in col 7.
    rows.push(['','','','','', balLabel, '', Math.abs(closingV), '','']);
  }
  merges.push({s:{r:balRow,c:0},e:{r:balRow,c:5}});
  // Sign-off (after Period totals + Balance-as-on rows)
  const signRow = balRow + 2;
  rows.push([]);
  rows.push(['This statement is computer-generated. Please verify against your records and revert with any discrepancies within 7 days.', ...blank(COLS-1)]);
  merges.push({s:{r:signRow,c:0},e:{r:signRow,c:COLS-1}});

  // ---- Materialise sheet ----
  const ws = XLSX.utils.aoa_to_sheet(rows);
  // 10 columns: #, Date, Type, Doc No, Reference, Particulars, Debit,
  // Credit, Unique Ref, Status.
  ws['!cols'] = [
    {wch:6},   // #
    {wch:13},  // Date
    {wch:15},  // Type
    {wch:20},  // Doc No
    {wch:34},  // Reference (can hold a comma-separated invoice list)
    {wch:50},  // Particulars
    {wch:16},  // Debit
    {wch:16},  // Credit
    {wch:12},  // Unique Ref
    {wch:12},  // Status
  ];
  ws['!merges'] = merges;
  // Freeze the customer / summary / ledger-header band so the table header stays put
  ws['!freeze'] = { xSplit: 0, ySplit: 13 };
  // Enable autofilter across the entire ledger header → totals row span.
  // This is what gives the client per-column dropdowns in Excel; in
  // particular the user asked for Payment / Unique Ref / Status to be
  // filterable, so the range must cover all 10 columns (A12..J{totals}).
  ws['!autofilter'] = { ref: `${_soaA1(12,0)}:${_soaA1(totalsRow,COLS-1)}` };

  // ---- Apply styles ----
  const num = '#,##0.00;[Red]-#,##0.00';
  const setS = (r, c, style)=>{
    const a = _soaA1(r,c);
    if (!ws[a]) ws[a] = { t:'s', v:'' };
    ws[a].s = Object.assign(ws[a].s||{}, style);
  };
  const setNum = (r,c)=>{
    const a = _soaA1(r,c);
    if (ws[a]){ ws[a].z = num; ws[a].t = 'n'; }
  };
  // Banner (r=0)
  for (let c=0; c<COLS; c++) setS(0, c, {
    font:{name:'Calibri', sz:18, bold:true, color:{rgb:'FFFFFF'}},
    fill:{fgColor:{rgb:TEAL}},
    alignment:{horizontal:'center', vertical:'center'},
  });
  ws['!rows'] = ws['!rows'] || [];
  ws['!rows'][0] = { hpt: 28 };
  // Sub-title r=1
  for (let c=0; c<COLS; c++) setS(1, c, {
    font:{name:'Calibri', sz:11, italic:true, color:{rgb:'FFFFFF'}},
    fill:{fgColor:{rgb:TEAL}},
    alignment:{horizontal:'center'},
  });
  // Mumbai / India r=2
  for (let c=0; c<COLS; c++) setS(2, c, {
    font:{name:'Calibri', sz:10, italic:true, color:{rgb:'D7E3E5'}},
    fill:{fgColor:{rgb:TEAL}},
    alignment:{horizontal:'center'},
  });
  ws['!rows'][2] = { hpt: 16 };
  // Customer block r=4..7
  for (let r=4; r<=7; r++){
    setS(r, 0, {
      font:{name:'Calibri', sz:10, bold:true, color:{rgb:'64748B'}},
      alignment:{horizontal:'left', vertical:'center'},
      fill:{fgColor:{rgb:SAND}}
    });
    setS(r, 1, {
      font:{name:'Calibri', sz:11, bold:(r===4), color:{rgb:INK}},
      alignment:{horizontal:'left', vertical:'center'},
      fill:{fgColor:{rgb:SAND}}
    });
    for (let c=2; c<COLS; c++) setS(r, c, { fill:{fgColor:{rgb:SAND}} });
  }
  // Summary band header r=9
  ['Opening','Debits','Credits','Closing'].forEach((_, idx)=>{
    const [c0,c1] = sumRanges[idx];
    for (let c=c0; c<=c1; c++) setS(9, c, {
      font:{name:'Calibri', sz:9, bold:true, color:{rgb:'64748B'}},
      fill:{fgColor:{rgb:TEAL_LT}},
      alignment:{horizontal:'center'},
      border: sBorder(TEAL),
    });
  });
  // Summary values r=10
  ['Opening','Debits','Credits','Closing'].forEach((_, idx)=>{
    const [c0,c1] = sumRanges[idx];
    for (let c=c0; c<=c1; c++) setS(10, c, {
      font:{name:'Calibri', sz:13, bold:true, color:{rgb: idx===3 ? TEAL : INK}},
      fill:{fgColor:{rgb:'FFFFFF'}},
      alignment:{horizontal:'center', vertical:'center'},
      border: sBorder(TEAL),
    });
    setNum(10, c0);
  });
  ws['!rows'][10] = { hpt: 26 };
  // Ledger table header r=12 — number columns 6,7 right-aligned; col 5
  // (Particulars) left-aligned; everything else centered. Unique Ref +
  // Status (8, 9) also centered.
  for (let c=0; c<COLS; c++) setS(12, c, {
    font:{name:'Calibri', sz:11, bold:true, color:{rgb:'FFFFFF'}},
    fill:{fgColor:{rgb:TEAL}},
    alignment:{horizontal: (c>=6 && c<=7) ? 'right' : (c===5 ? 'left' : 'center'), vertical:'center'},
    border: sBorder(TEAL),
  });
  ws['!rows'][12] = { hpt: 22 };
  // Opening b/f r=13 — italic, light fill. Opening balance is rendered on
  // the Credit column (col 7) so the running balance column doesn't need
  // to exist.
  for (let c=0; c<COLS; c++) setS(13, c, {
    font:{name:'Calibri', sz:10, italic:true, color:{rgb:'334155'}},
    fill:{fgColor:{rgb:TEAL_LT}},
    alignment:{horizontal: (c>=6 && c<=7) ? 'right' : (c===5 ? 'left' : 'center'), vertical:'center'},
    border: sBorder(),
  });
  setNum(13, 7);
  setS(13, 7, {font:{name:'Calibri', sz:11, bold:true, color:{rgb:INK}}});
  // Body rows — striped, alternating
  for (let r=startBodyRow; r<=endBodyRow; r++){
    const stripe = ((r - startBodyRow) % 2 === 1) ? STRIPE : 'FFFFFF';
    for (let c=0; c<COLS; c++){
      setS(r, c, {
        font:{name:'Calibri', sz:10, color:{rgb:INK}},
        fill:{fgColor:{rgb:stripe}},
        alignment:{
          horizontal: (c>=6 && c<=7) ? 'right'
                    : (c===5 ? 'left'
                    : (c===0||c===1||c===2||c===8||c===9) ? 'center'
                    : 'left'),
          vertical:'center',
          wrapText:(c===4||c===5)
        },
        border: sBorder(),
      });
    }
    // Number columns (Debit=6, Credit=7)
    setNum(r, 6); setNum(r, 7);
    // Unique Ref (col 8) — render as a clean integer
    const cRefAddr = _soaA1(r, 8);
    if (ws[cRefAddr] && ws[cRefAddr].v !== ''){
      ws[cRefAddr].t = 'n';
      ws[cRefAddr].z = '0';
    }
    // Doc No (col 3) and Reference (col 4) → monospace
    setS(r, 3, {font:{name:'Consolas', sz:9, color:{rgb:'334155'}}});
    setS(r, 4, {font:{name:'Consolas', sz:9, color:{rgb:'334155'}}});
    // Status column (col 9) — colour-code the cell so it reads at a
    // glance (mirrors the on-screen pill: Paid green, Partial amber,
    // Unpaid red, Unmatched blue).
    const statusAddr = _soaA1(r, 9);
    const sv = ws[statusAddr] ? String(ws[statusAddr].v||'') : '';
    if (sv){
      let bg = 'F1F5F9', fg = '334155';
      if (sv === 'Paid')      { bg='DCFCE7'; fg='166534'; }
      else if (sv === 'Partial')   { bg='FEF3C7'; fg='92400E'; }
      else if (sv === 'Unpaid')    { bg='FEE2E2'; fg='991B1B'; }
      else if (sv === 'Unmatched') { bg='DBEAFE'; fg='1E40AF'; }
      setS(r, 9, {
        font:{name:'Calibri', sz:10, bold:true, color:{rgb:fg}},
        fill:{fgColor:{rgb:bg}},
      });
    }
    // Unique Ref column — soft indigo pill
    if (ws[cRefAddr] && ws[cRefAddr].v !== ''){
      setS(r, 8, {
        font:{name:'Consolas', sz:10, bold:true, color:{rgb:'3730A3'}},
        fill:{fgColor:{rgb:'EEF2FF'}},
      });
    }
  }
  // Period totals row
  for (let c=0; c<COLS; c++) setS(totalsRow, c, {
    font:{name:'Calibri', sz:11, bold:true, color:{rgb:INK}},
    fill:{fgColor:{rgb:'F1F5F9'}},
    alignment:{horizontal:'right', vertical:'center'},
    border: { top:{style:'medium', color:{rgb:TEAL}}, bottom:{style:'medium', color:{rgb:TEAL}}, left:sBorder().left, right:sBorder().right },
  });
  setNum(totalsRow, 6); setNum(totalsRow, 7);
  ws['!rows'][totalsRow] = { hpt: 22 };
  // Balance-as-on row — golden footer. The label "Balance as on …" is
  // merged across cols 0..5 and the closing value lives in col 6 (debit)
  // or col 7 (credit) depending on its sign. Right-align everything so
  // the label butts cleanly against the value cell — fixes the user
  // report that the date label appeared "missing" / detached from the
  // figure in earlier exports.
  for (let c=0; c<COLS; c++) setS(balRow, c, {
    font:{name:'Calibri', sz:11, bold:true, color:{rgb:'854D0E'}},
    fill:{fgColor:{rgb:'FEF9C3'}},
    alignment:{horizontal:'right', vertical:'center'},
    border: { top:{style:'medium', color:{rgb:TEAL}}, bottom:{style:'medium', color:{rgb:TEAL}}, left:sBorder().left, right:sBorder().right },
  });
  setNum(balRow, 6); setNum(balRow, 7);
  ws['!rows'][balRow] = { hpt: 22 };
  // Sign-off row
  for (let c=0; c<COLS; c++) setS(signRow, c, {
    font:{name:'Calibri', sz:9, italic:true, color:{rgb:'64748B'}},
    alignment:{horizontal:'left', wrapText:true},
  });

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Statement');
  const fn = _soaFileBase() + '.xlsx';
  XLSX.writeFile(wb, fn);
}

// ----- PDF download via a self-contained iframe (bulletproof: no blank first page,
//       correct default filename via <title>, no interference from dashboard CSS).
function soaDownloadPdf(){
  if (!soaState.lines || !soaState.cid) return;
  const fileBase = _soaFileBase();   // becomes the "Save as PDF" default
  const fmtIN = (n)=> '₹'+(Math.round((+n||0)*100)/100).toLocaleString('en-IN',{maximumFractionDigits:2});
  // Status pill helper (PDF — inline styles, no CSS class lookups so it
  // renders consistently in the print iframe regardless of host CSS).
  const statusPill = (s) => {
    const v = String(s||'').trim();
    if (!v) return '—';
    let bg='#f1f5f9', fg='#334155';
    if (v==='Paid')      { bg='#dcfce7'; fg='#166534'; }
    else if (v==='Partial')   { bg='#fef3c7'; fg='#92400e'; }
    else if (v==='Unpaid')    { bg='#fee2e2'; fg='#991b1b'; }
    else if (v==='Unmatched') { bg='#dbeafe'; fg='#1e40af'; }
    return `<span style="display:inline-block;padding:1px 7px;border-radius:9px;font-size:9px;font-weight:700;background:${bg};color:${fg}">${v}</span>`;
  };
  // Opening b/f: opening balance shown on Credit column (running Balance
  // column was dropped — a "Balance as on" row is added in tfoot below).
  // Unique Ref column carries the refs of any adjustment / payment that
  // closed an opening-balance contributor.
  const _pdfOpRefs = Array.isArray(soaState.openingRefs) ? soaState.openingRefs.join(', ') : '';
  let bodyRows = `<tr class="open">
      <td>—</td><td>${fmtDateOut(soaState.fromDate)}</td>
      <td colspan="4">Opening balance carried forward</td>
      <td class="num">—</td>
      <td class="num bold">${fmtIN(soaState.opening)}</td>
      <td class="mono" style="text-align:center;font-weight:700;color:#3730a3">${_pdfOpRefs || '—'}</td><td></td>
    </tr>`;
  soaState.lines.forEach((ln,i)=>{
    const cRef = (ln.checkRef === 0 || ln.checkRef) ? String(ln.checkRef) : '—';
    bodyRows += `<tr>
      <td>${i+1}</td>
      <td>${fmtDateOut(ln.date)}</td>
      <td><span class="pill pill-${(ln.type||'').toLowerCase().replace(/[^a-z]/g,'')}">${ln.type}</span></td>
      <td class="mono">${ln.doc||'—'}</td>
      <td class="mono">${_soaRefStr(ln)||'—'}</td>
      <td>${ln.particulars||'—'}</td>
      <td class="num">${ln.debit ? fmtIN(ln.debit) : '—'}</td>
      <td class="num">${ln.credit ? fmtIN(ln.credit) : '—'}</td>
      <td class="mono" style="text-align:center;font-weight:700;color:#3730a3">${cRef}</td>
      <td style="text-align:center">${statusPill(ln.status)}</td>
    </tr>`;
  });
  const html = `<!doctype html><html><head><meta charset="utf-8">
<title>${fileBase}</title>
<style>
  @page { size: A4 landscape; margin: 10mm 8mm; }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:#fff;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1f2a2e}
  body{font-size:10px}
  .lh{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #2c4a52;padding-bottom:8px;margin-bottom:10px}
  .lh-l .brand{font-size:24px;font-weight:800;color:#2c4a52;letter-spacing:-0.5px;line-height:1}
  .lh-l .co{font-size:11px;color:#475569;margin-top:2px}
  .lh-l .addr{font-size:10px;color:#94a3b8;margin-top:1px}
  .lh-r{text-align:right}
  .lh-r .title{font-size:13px;font-weight:700;color:#2c4a52;letter-spacing:0.5px}
  .lh-r .meta{font-size:10px;color:#475569;margin-top:2px}
  .cust{display:flex;justify-content:space-between;align-items:center;background:#fdfcf7;border:1px solid #e2e8f0;border-radius:4px;padding:9px 12px;margin-bottom:10px}
  .cust .blk-lbl{font-size:9px;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8}
  .cust .blk-val{font-size:14px;font-weight:700;color:#0f172a;margin-top:1px}
  .cust .blk-sub{font-size:10px;color:#64748b;margin-top:1px}
  .totals{display:flex;gap:14px;align-items:flex-end}
  .tot{min-width:90px;text-align:right}
  .tot .lbl{font-size:8.5px;color:#94a3b8;text-transform:uppercase}
  .tot .val{font-size:12px;font-weight:700;color:#1f2a2e;margin-top:1px}
  .tot.clos{padding-left:14px;border-left:2px solid #2c4a52}
  .tot.clos .val{color:#2c4a52;font-size:13.5px}
  table{width:100%;border-collapse:collapse;font-size:10px}
  thead tr{background:#2c4a52;color:#fff}
  thead th{padding:7px 8px;text-align:left;font-weight:700;border:1px solid #2c4a52;font-size:10px}
  thead th.num{text-align:right}
  tbody td{padding:5px 8px;border:1px solid #e2e8f0;vertical-align:top}
  tbody td.num{text-align:right;font-variant-numeric:tabular-nums}
  tbody td.bold{font-weight:700}
  tbody td.mono{font-family:Consolas,Menlo,monospace;font-size:9px;color:#334155}
  tbody tr:nth-child(even){background:#f8faf9}
  tbody tr.open{background:#eaf1f2 !important;font-style:italic}
  tbody tr.open td{color:#334155;font-weight:600}
  tfoot td{padding:7px 8px;border-top:2px solid #2c4a52;border-bottom:2px solid #2c4a52;background:#f1f5f9;font-weight:700;text-align:right;font-size:10.5px}
  tfoot td.num{font-variant-numeric:tabular-nums}
  .pill{display:inline-block;padding:1px 7px;border-radius:9px;font-size:9px;font-weight:600;letter-spacing:0.02em}
  .pill-invoice{background:#fee2e2;color:#991b1b}
  .pill-payment{background:#d1fae5;color:#065f46}
  .pill-tds{background:#fef3c7;color:#92400e}
  .pill-creditnote{background:#dbeafe;color:#1e40af}
  .pill-codadj{background:#ede9fe;color:#5b21b6}
  .pill-bankchg{background:#fce7f3;color:#9f1239}
  .pill-pdd{background:#cffafe;color:#155e75}
  .pill-bankreceipt{background:#d1fae5;color:#065f46}
  .pill-adjustment{background:#e5e7eb;color:#374151}
  tr{page-break-inside:avoid}
  thead{display:table-header-group}
  tfoot{display:table-footer-group}
  .sign{margin-top:12px;display:flex;justify-content:space-between;align-items:flex-end}
  .sign .note{font-size:9px;color:#64748b;max-width:60%}
  .sign .sig-line{width:180px;border-top:1px solid #94a3b8;height:24px}
  .sign .sig-lbl{font-size:10px;color:#0f172a;font-weight:600;text-align:right}
</style></head>
<body>
  <div class="lh">
    <div class="lh-l">
      <div class="brand">Fynd</div>
      <div class="co">Shopsense Retail Technologies Ltd.</div>
      <div class="addr">Mumbai · India</div>
    </div>
    <div class="lh-r">
      <div class="title">STATEMENT OF ACCOUNT</div>
      <div class="meta">Generated: ${new Date().toLocaleString('en-IN')}</div>
      <div class="meta">Period: ${fmtDateOut(soaState.fromDate)} → ${fmtDateOut(soaState.toDate)}</div>
    </div>
  </div>
  <div class="cust">
    <div>
      <div class="blk-lbl">Statement for</div>
      <div class="blk-val">${soaState.custName}</div>
      <div class="blk-sub">CID : ${soaState.cid || ''}</div>
    </div>
    <div class="totals">
      <div class="tot"><div class="lbl">Opening</div><div class="val">${fmtIN(soaState.opening)}</div></div>
      <div class="tot"><div class="lbl">Debits</div><div class="val">${fmtIN(soaState.totDr)}</div></div>
      <div class="tot"><div class="lbl">Credits</div><div class="val">${fmtIN(soaState.totCr)}</div></div>
      <div class="tot clos"><div class="lbl">Closing</div><div class="val">${fmtIN(soaState.closing)}</div></div>
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th style="width:24px">#</th>
        <th style="width:62px">Date</th>
        <th style="width:72px">Type</th>
        <th style="width:90px">Doc No</th>
        <th style="width:90px">Reference</th>
        <th>Particulars</th>
        <th class="num" style="width:88px">Debit (₹)</th>
        <th class="num" style="width:88px">Credit (₹)</th>
        <th style="width:64px;text-align:center">Unique Ref</th>
        <th style="width:68px;text-align:center">Status</th>
      </tr>
    </thead>
    <tbody>${bodyRows}</tbody>
    <tfoot>
      <tr>
        <td colspan="6" style="text-align:right">Period totals</td>
        <td class="num">${fmtIN(soaState.totDr)}</td>
        <td class="num">${fmtIN(soaState.totCr)}</td>
        <td></td><td></td>
      </tr>
      <tr style="background:#fef9c3;color:#854d0e;font-weight:700">
        <td colspan="6" style="text-align:right">Balance as on ${fmtDateOut(soaState.toDate)}</td>
        <td class="num"></td>
        <td class="num">${fmtIN(soaState.closing)}</td>
        <td></td><td></td>
      </tr>
    </tfoot>
  </table>
  <div class="sign">
    <div class="note">This statement is computer-generated. Please verify against your records and revert with any discrepancies within 7 days.</div>
    <div><div class="sig-line"></div><div class="sig-lbl">For Shopsense Retail Technologies Ltd.</div></div>
  </div>
</body></html>`;

  // Render inside an off-screen iframe so we control the entire document
  // (no blank first page, correct title for "Save as PDF" filename).
  const ifr = document.createElement('iframe');
  ifr.setAttribute('aria-hidden', 'true');
  ifr.style.position = 'fixed';
  ifr.style.right = '0';
  ifr.style.bottom = '0';
  ifr.style.width = '0';
  ifr.style.height = '0';
  ifr.style.border = '0';
  ifr.style.opacity = '0';
  document.body.appendChild(ifr);
  const doc = ifr.contentDocument || ifr.contentWindow.document;
  doc.open();
  doc.write(html);
  doc.close();
  // Wait for the new document's onload, then trigger print
  const trigger = ()=>{
    try {
      ifr.contentWindow.focus();
      ifr.contentWindow.print();
    } catch(err){
      console.error('SOA print failed:', err);
    }
    // Clean up after the print dialog closes
    setTimeout(()=>{ try { ifr.remove(); } catch(_){} }, 1500);
  };
  if (ifr.contentDocument.readyState === 'complete'){
    setTimeout(trigger, 80);
  } else {
    ifr.contentWindow.addEventListener('load', ()=> setTimeout(trigger, 60), { once:true });
    // Safety fallback if onload doesn't fire
    setTimeout(trigger, 800);
  }
}

// ----- Email modal -----
function soaOpenEmail(){
  if (!soaState.lines || !soaState.cid){ return; }
  document.getElementById('soaEmailModal').style.display = 'flex';
  // Defaults
  const subj = `Statement of Account · ${soaState.custName} · ${fmtDateOut(soaState.fromDate)} to ${fmtDateOut(soaState.toDate)}`;
  document.getElementById('soaEmailSubject').value = subj;
  const note = `Dear Sir / Madam,\\n\\nPlease find below the Statement of Account for ${soaState.custName} for the period ${fmtDateOut(soaState.fromDate)} to ${fmtDateOut(soaState.toDate)}.\\n\\nClosing balance as on ${fmtDateOut(soaState.toDate)} is ${fmtINRfull(soaState.closing)}.\\n\\nKindly confirm balances or revert with any discrepancies within 7 days.\\n\\nRegards,\\nFynd Finance Team`;
  document.getElementById('soaEmailNote').value = note.replace(/\\\\n/g,'\\n');
  document.getElementById('soaEmailMsg').textContent = '';
  // Auto-populate To/CC from backend (previewBU) so users don't have to type the
  // client address by hand every time. Falls back silently if backend doesn't return one.
  const toEl = document.getElementById('soaEmailTo');
  const ccEl = document.getElementById('soaEmailCc');
  if (toEl){ toEl.value = ''; toEl.placeholder = 'Loading from backend…'; }
  if (ccEl){ ccEl.value = ''; }
  try {
    _fuJsonp('previewBU', { cids: soaState.cid }).then(res => {
      const cust = (res && res.ok && Array.isArray(res.customers))
        ? res.customers.find(c => String(c.cid||'').trim() === String(soaState.cid||'').trim()) || res.customers[0]
        : null;
      if (toEl){
        toEl.placeholder = 'client@example.com';
        if (cust && cust.toEmail) toEl.value = String(cust.toEmail).trim();
      }
      if (ccEl && cust && cust.ccEmail) ccEl.value = String(cust.ccEmail).trim();
    }).catch(()=>{ if (toEl) toEl.placeholder = 'client@example.com'; });
  } catch(_){ if (toEl) toEl.placeholder = 'client@example.com'; }
}

function soaCloseEmail(){
  document.getElementById('soaEmailModal').style.display = 'none';
}

// Build a self-contained HTML statement body for the email
function _soaBuildEmailHtml(noteText){
  const fmtIN = (n)=> '₹'+(Math.round((+n||0)*100)/100).toLocaleString('en-IN',{maximumFractionDigits:2});
  const noteHtml = String(noteText||'').split(/\\n/).map(l=>'<p style="margin:0 0 8px">'+l+'</p>').join('');
  // Inline status pill (email-safe — no CSS class lookups).
  const statusPill = (s) => {
    const v = String(s||'').trim();
    if (!v) return '—';
    let bg='#f1f5f9', fg='#334155';
    if (v==='Paid')      { bg='#dcfce7'; fg='#166534'; }
    else if (v==='Partial')   { bg='#fef3c7'; fg='#92400e'; }
    else if (v==='Unpaid')    { bg='#fee2e2'; fg='#991b1b'; }
    else if (v==='Unmatched') { bg='#dbeafe'; fg='#1e40af'; }
    return `<span style="display:inline-block;padding:2px 8px;border-radius:9px;font-size:10px;font-weight:700;background:${bg};color:${fg}">${v}</span>`;
  };
  const _mailOpRefs = Array.isArray(soaState.openingRefs) ? soaState.openingRefs.join(', ') : '';
  let rowsHtml = `<tr style="background:#f8fafc">
    <td colspan="6" style="padding:8px;border:1px solid #e2e8f0;font-weight:600">Opening balance carried forward</td>
    <td style="padding:8px;border:1px solid #e2e8f0;text-align:right">—</td>
    <td style="padding:8px;border:1px solid #e2e8f0;text-align:right;font-weight:700">${fmtIN(soaState.opening)}</td>
    <td style="padding:8px;border:1px solid #e2e8f0;text-align:center;font-weight:700;color:#3730a3">${_mailOpRefs || '—'}</td>
    <td style="padding:8px;border:1px solid #e2e8f0"></td>
  </tr>`;
  soaState.lines.forEach((ln,i)=>{
    const cRef = (ln.checkRef === 0 || ln.checkRef) ? String(ln.checkRef) : '—';
    rowsHtml += `<tr>
      <td style="padding:6px;border:1px solid #e2e8f0">${i+1}</td>
      <td style="padding:6px;border:1px solid #e2e8f0">${fmtDateOut(ln.date)}</td>
      <td style="padding:6px;border:1px solid #e2e8f0">${ln.type}</td>
      <td style="padding:6px;border:1px solid #e2e8f0;font-family:monospace;font-size:11px">${ln.doc||'—'}</td>
      <td style="padding:6px;border:1px solid #e2e8f0;font-family:monospace;font-size:11px">${_soaRefStr(ln)||'—'}</td>
      <td style="padding:6px;border:1px solid #e2e8f0">${ln.particulars||'—'}</td>
      <td style="padding:6px;border:1px solid #e2e8f0;text-align:right">${ln.debit?fmtIN(ln.debit):'—'}</td>
      <td style="padding:6px;border:1px solid #e2e8f0;text-align:right">${ln.credit?fmtIN(ln.credit):'—'}</td>
      <td style="padding:6px;border:1px solid #e2e8f0;text-align:center;font-family:monospace;font-weight:700;color:#3730a3">${cRef}</td>
      <td style="padding:6px;border:1px solid #e2e8f0;text-align:center">${statusPill(ln.status)}</td>
    </tr>`;
  });
  return `
  <div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1f2a2e;max-width:880px;margin:0 auto">
    ${noteHtml}
    <div style="margin-top:20px;border:1px solid #e2e8f0;padding:18px;background:#fdfcf7;border-radius:6px">
      <div style="display:flex;justify-content:space-between;border-bottom:2px solid #2c4a52;padding-bottom:10px;margin-bottom:14px">
        <div>
          <div style="font-size:22px;font-weight:700;color:#2c4a52">Fynd</div>
          <div style="font-size:12px;color:#475569">Shopsense Retail Technologies Ltd.</div>
          <div style="font-size:11px;color:#94a3b8">Mumbai · India</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:14px;font-weight:700;color:#2c4a52">STATEMENT OF ACCOUNT</div>
          <div style="font-size:11px;color:#475569">Generated: ${new Date().toLocaleString('en-IN')}</div>
          <div style="font-size:11px;color:#475569">Period: ${fmtDateOut(soaState.fromDate)} → ${fmtDateOut(soaState.toDate)}</div>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;background:#fff;border:1px solid #e2e8f0;padding:12px;margin-bottom:14px;border-radius:4px">
        <div>
          <div style="font-size:10px;color:#94a3b8;text-transform:uppercase">Statement for</div>
          <div style="font-size:15px;font-weight:700;color:#0f172a">${soaState.custName}</div>
          <div style="font-size:11px;color:#64748b">CID : ${soaState.cid || ''}</div>
        </div>
        <div style="display:flex;gap:18px;font-size:12px">
          <div><div style="color:#94a3b8;font-size:10px">OPENING</div><div style="font-weight:700">${fmtIN(soaState.opening)}</div></div>
          <div><div style="color:#94a3b8;font-size:10px">DEBITS</div><div style="font-weight:700">${fmtIN(soaState.totDr)}</div></div>
          <div><div style="color:#94a3b8;font-size:10px">CREDITS</div><div style="font-weight:700">${fmtIN(soaState.totCr)}</div></div>
          <div style="border-left:2px solid #2c4a52;padding-left:18px"><div style="color:#94a3b8;font-size:10px">CLOSING</div><div style="font-weight:700;color:#2c4a52">${fmtIN(soaState.closing)}</div></div>
        </div>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:11.5px">
        <thead>
          <tr style="background:#2c4a52;color:#fff">
            <th style="padding:8px;border:1px solid #2c4a52;text-align:left">#</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:left">Date</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:left">Type</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:left">Doc No</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:left">Reference</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:left">Particulars</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:right">Debit (₹)</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:right">Credit (₹)</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:center">Unique Ref</th>
            <th style="padding:8px;border:1px solid #2c4a52;text-align:center">Status</th>
          </tr>
        </thead>
        <tbody>${rowsHtml}</tbody>
        <tfoot>
          <tr style="background:#f1f5f9">
            <td colspan="6" style="padding:8px;border:1px solid #cbd5e1;text-align:right;font-weight:700">Period totals</td>
            <td style="padding:8px;border:1px solid #cbd5e1;text-align:right;font-weight:700">${fmtIN(soaState.totDr)}</td>
            <td style="padding:8px;border:1px solid #cbd5e1;text-align:right;font-weight:700">${fmtIN(soaState.totCr)}</td>
            <td style="padding:8px;border:1px solid #cbd5e1"></td>
            <td style="padding:8px;border:1px solid #cbd5e1"></td>
          </tr>
          <tr style="background:#fef9c3;color:#854d0e">
            <td colspan="6" style="padding:8px;border:1px solid #fde68a;text-align:right;font-weight:700">Balance as on ${fmtDateOut(soaState.toDate)}</td>
            <td style="padding:8px;border:1px solid #fde68a"></td>
            <td style="padding:8px;border:1px solid #fde68a;text-align:right;font-weight:700">${fmtIN(soaState.closing)}</td>
            <td style="padding:8px;border:1px solid #fde68a"></td>
            <td style="padding:8px;border:1px solid #fde68a"></td>
          </tr>
        </tfoot>
      </table>
      <div style="margin-top:14px;font-size:11px;color:#64748b">This statement is computer-generated. Please verify against your records and revert with any discrepancies within 7 days.</div>
    </div>
  </div>`;
}

// Canonical sender for all AR correspondence — must exist as a verified
// "Send mail as" alias on the Apps Script owner's Gmail account.
const SOA_SENDER_EMAIL = 'ar@gofynd.com';
const SOA_SENDER_NAME  = 'Fynd Accounts Receivable';

async function soaSendEmail(){
  const to = document.getElementById('soaEmailTo').value.trim();
  const cc = document.getElementById('soaEmailCc').value.trim();
  const subj = document.getElementById('soaEmailSubject').value.trim();
  const note = document.getElementById('soaEmailNote').value.trim();
  const msg = document.getElementById('soaEmailMsg');
  if (!to){ msg.innerHTML = '<span style="color:#b91c1c">Please enter recipient email.</span>'; return; }
  if (!subj){ msg.innerHTML = '<span style="color:#b91c1c">Subject is empty.</span>'; return; }
  msg.innerHTML = '<span style="color:#475569">Sending from ' + SOA_SENDER_EMAIL + '…</span>';
  const html = _soaBuildEmailHtml(note);
  try {
    const res = await _fuJsonp('statementEmail', {
      to: to, cc: cc, subject: subj,
      htmlBody: html,
      custName: soaState.custName, cid: soaState.cid,
      fromDate: soaState.fromDate, toDate: soaState.toDate,
      // Tell the Apps Script which alias to send from. Backend should pass
      // this through to GmailApp.sendEmail({from: ...}). The alias must be
      // verified under Gmail → Settings → Accounts → Send mail as.
      from: SOA_SENDER_EMAIL,
      fromName: SOA_SENDER_NAME
    });
    if (res && res.ok){
      // Backend should echo back the actual sender it used; fall back to the
      // alias we requested so the user always sees a "from" address.
      const sender = (res.sender || res.from || SOA_SENDER_EMAIL);
      let line = '<span style="color:#15803d">✓ Sent to ' + to + ' from <b>' + sender + '</b>.</span>';
      if (res._via === 'post-optimistic'){
        line += '<div style="color:#b45309;font-size:11px;margin-top:4px">Note: response was opaque (CORS) — confirm delivery in the Sent folder of ' + sender + '.</div>';
      }
      msg.innerHTML = line;
      setTimeout(soaCloseEmail, 2200);
    } else {
      msg.innerHTML = '<span style="color:#b91c1c">Failed: '+(res && res.error || 'unknown error')+'</span>';
    }
  } catch(e){
    msg.innerHTML = '<span style="color:#b91c1c">Error: '+e.message+'</span>';
  }
}

// ----- Quick presets -----
function soaQuickFY(){
  document.getElementById('soaFrom').value = _soaFYStart();
  document.getElementById('soaTo').value   = _soaToday();
  // Auto-regenerate if a customer is already picked.
  _soaAutoGenerate();
}
function soaQuickAll(){
  // AR data starts Apr-01-2025; "All-time" always anchors there.
  document.getElementById('soaFrom').value = SOA_DATA_START;
  document.getElementById('soaTo').value   = _soaToday();
  _soaAutoGenerate();
}

// ----- Wire everything -----
function wireSoa(){
  const inp = document.getElementById('soaCustomer');
  if (!inp) return;
  inp.addEventListener('focus', ()=> _soaRenderCustList(inp.value));
  inp.addEventListener('input', ()=>{
    // typing invalidates the selection — user must pick again
    soaState.cid = ''; soaState.custName = '';
    _soaRenderCustList(inp.value);
  });
  document.addEventListener('click', (e)=>{
    const list = document.getElementById('soaCustList');
    if (!list) return;
    if (e.target === inp) return;
    if (list.contains(e.target)) return;
    list.style.display = 'none';
  });
  // Default dates → current FY
  const fy = _soaFYStart();
  const td = _soaToday();
  const dF = document.getElementById('soaFrom');
  const dT = document.getElementById('soaTo');
  if (dF && !dF.value) dF.value = fy;
  if (dT && !dT.value) dT.value = td;
  // Buttons
  document.getElementById('soaGen').addEventListener('click', soaGenerate);
  const rstBtn = document.getElementById('soaReset');
  if (rstBtn) rstBtn.addEventListener('click', soaReset);
  document.getElementById('soaDlXlsx').addEventListener('click', soaDownloadXlsx);
  document.getElementById('soaDlPdf').addEventListener('click', soaDownloadPdf);
  document.getElementById('soaEmail').addEventListener('click', soaOpenEmail);
  document.getElementById('soaQuickFY').addEventListener('click', soaQuickFY);
  document.getElementById('soaQuickAll').addEventListener('click', soaQuickAll);
  document.getElementById('soaEmailClose').addEventListener('click', soaCloseEmail);
  document.getElementById('soaEmailSend').addEventListener('click', soaSendEmail);
  // "Clear reference filter" chip → restore full ledger view
  const refClr = document.getElementById('soaRefBarClear');
  if (refClr) refClr.addEventListener('click', _soaClearRefFilter);
  // Auto-generate hooks — date inputs re-fire the statement build when a
  // customer is already picked. We listen to both `change` (committed
  // pick from the native date picker) and `input` (typed value).
  ['soaFrom','soaTo'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', _soaAutoGenerate);
    el.addEventListener('input',  _soaAutoGenerate);
  });
  // Status filter chips — clicking a chip narrows the body in place.
  const sf = document.getElementById('soaStatusFilter');
  if (sf){
    sf.querySelectorAll('.soa-status-chip').forEach(btn => {
      btn.addEventListener('click', (e)=>{
        e.preventDefault();
        const s = btn.getAttribute('data-status') || 'All';
        soaState.statusFilter = s;
        _soaPaintStatusChips();
        _soaPaintBody();
      });
    });
    _soaPaintStatusChips();
  }
}

// ===== Global topbar search =====
// Routes the topbar query into whichever section is active so the user
// can search Customers, Invoices, PDD or Bank from one place. If they
// type while still on Overview, jump them to Customers automatically.
function wireGlobalSearch(){
  const inp = document.getElementById('globalSearch');
  if(!inp) return;
  const TARGETS = {
    dashboard: 'custFilter',   // Overview has no list — fan out to Customers
    customers: 'custFilter',
    invoices:  'custFilter',   // Invoices live inside Customer expansion
    pdd:       'pddFilter',
    bank:      'bankFilter'
  };
  const fanOut = (val)=>{
    ['custFilter','buFilter','pddFilter','bankFilter'].forEach(id=>{
      const el = document.getElementById(id);
      if(el && el.value !== val){
        el.value = val;
        el.dispatchEvent(new Event('input', { bubbles:true }));
      }
    });
  };
  inp.addEventListener('input', (e)=>{
    const v = (e.target.value || '').trim();
    fanOut(v);
    // If the user starts typing while on Overview/Reports, hop to Customers
    // so they can actually see the matches.
    if(v && (state.activeTab === 'dashboard' || state.activeTab === 'reports')){
      showTab('customers');
    }
  });
  // Submit (Enter) — focus the corresponding section input
  inp.addEventListener('keydown', (e)=>{
    if(e.key !== 'Enter') return;
    e.preventDefault();
    const tgt = document.getElementById(TARGETS[state.activeTab] || 'custFilter');
    if(tgt){ tgt.focus(); tgt.select && tgt.select(); }
  });
}

// ===== Brand button — clicking either Fynd logo jumps to Overview =====
function wireBrandHome(){
  const handler = (e)=>{
    if (e && e.preventDefault) e.preventDefault();
    _resetGlobalSearch();
    showTab('dashboard');
  };
  const b = document.getElementById('btnBrandHome');
  if(b) b.addEventListener('click', handler);
  const sb = document.getElementById('sbBrand');
  if(sb) sb.addEventListener('click', handler);
}
// Drop any stale collapsed-sidebar preference from the previous layout
try { localStorage.removeItem('fynd.ar.navCollapsed'); } catch(_){}

// ===== Follow-up Emails module =====
const fuState = {
  rows: [],            // last preview customer rows
  invoices: [],        // last preview invoice rows (for Excel)
  selBus: [],          // populated in-place by buildSimpleMS
  selCust: []          // populated in-place by buildSimpleMS
};

function _fuExecUrl(){
  return window.__DATA_URL__ || localStorage.getItem(LS_KEY_URL) || '';
}

// Actions that take a while to complete on the Apps Script side (bulk
// migration, large imports) need a longer client-side timeout than the
// default 60 s. Keep the list short and explicit — a run-away timeout on a
// misconfigured endpoint is worse than a fast failure.
const _FU_LONG_ACTIONS = {
  pocMigrateFromContacts: 300000,  // 5 min — one-time legacy migration
  pocBulkImport: 180000,           // 3 min — bulk POC upload commit
  isBulkImport: 180000             // 3 min — bulk IS upload commit
};

function _fuJsonp(action, params, timeoutMs){
  return new Promise((resolve,reject)=>{
    const url = _fuExecUrl();
    if(!url){ reject(new Error('No connection — open Settings and connect.')); return; }
    const cb = '__fu_cb_' + Date.now() + '_' + Math.random().toString(36).slice(2,8);
    const sp = new URLSearchParams({action, callback:cb, ...params}).toString();
    // Browsers cap GET URLs around 8KB. Large payloads (e.g. SOA htmlBody)
    // blow past that and silently 414, which surfaces as `s.onerror` →
    // "Network error". Detect oversized requests up-front and route through
    // the POST helper so the caller still gets a single Promise interface.
    const fullUrl = url + (url.includes('?')?'&':'?') + sp;
    if (fullUrl.length > 7500){
      return _fuPost(action, params, timeoutMs).then(resolve, reject);
    }
    const s = document.createElement('script');
    s.src = fullUrl;
    s.onerror = ()=>{ cleanup(); reject(new Error('Network error')); };
    let done = false;
    const cleanup = ()=>{ delete window[cb]; s.remove(); };
    const effectiveTimeout = Number(timeoutMs) || _FU_LONG_ACTIONS[action] || 60000;
    const timer = setTimeout(()=>{ if(!done){ done=true; cleanup(); reject(new Error('Request timed out')); } }, effectiveTimeout);
    window[cb] = (data)=>{ if(done) return; done=true; clearTimeout(timer); cleanup(); resolve(data); };
    document.body.appendChild(s);
  });
}

// Hidden-form POST helper for payloads that would overflow a GET URL.
// Apps Script doPost(e) receives form fields via e.parameter — same shape
// as JSONP params — so the backend reads them identically. We POST into a
// hidden iframe with `text/plain` content-type to dodge CORS preflight, then
// read the iframe body to recover the JSON response. If same-origin reads
// are blocked we fall back to optimistic success after the load fires.
function _fuPost(action, params, timeoutMs){
  return new Promise((resolve,reject)=>{
    const url = _fuExecUrl();
    if(!url){ reject(new Error('No connection — open Settings and connect.')); return; }
    const frameName = '__fu_iframe_' + Date.now() + '_' + Math.random().toString(36).slice(2,8);
    const iframe = document.createElement('iframe');
    iframe.name = frameName;
    iframe.style.display = 'none';
    document.body.appendChild(iframe);
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = url;
    form.target = frameName;
    // application/x-www-form-urlencoded is a CORS-safe content type (no
    // preflight) AND it's what Apps Script's doPost(e) parses into
    // e.parameter — same shape as JSONP query params. text/plain skipped
    // preflight too, but Apps Script wouldn't read its body as fields, so
    // the backend silently dropped every field including `action`.
    form.enctype = 'application/x-www-form-urlencoded';
    form.style.display = 'none';
    const addField = (k, v) => {
      const i = document.createElement('input');
      i.type = 'hidden'; i.name = k; i.value = (v == null ? '' : String(v));
      form.appendChild(i);
    };
    addField('action', action);
    Object.keys(params || {}).forEach(k => addField(k, params[k]));
    document.body.appendChild(form);
    let done = false;
    const cleanup = ()=>{ try { form.remove(); } catch(_){} try { iframe.remove(); } catch(_){} };
    const effectiveTimeout = Number(timeoutMs) || _FU_LONG_ACTIONS[action] || 60000;
    const timer = setTimeout(()=>{ if(!done){ done=true; cleanup(); reject(new Error('Request timed out')); } }, effectiveTimeout);
    iframe.addEventListener('load', ()=>{
      if (done) return; done = true; clearTimeout(timer);
      // Try to read JSON response from the iframe; if cross-origin blocks it,
      // assume the backend accepted the request (best-effort confirmation).
      let payload = null;
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        const txt = (doc && doc.body && doc.body.innerText || '').trim();
        if (txt) { try { payload = JSON.parse(txt); } catch(_){} }
      } catch(_){}
      cleanup();
      resolve(payload || { ok: true, _via: 'post-optimistic' });
    });
    iframe.addEventListener('error', ()=>{
      if (done) return; done = true; clearTimeout(timer); cleanup();
      reject(new Error('Network error'));
    });
    form.submit();
  });
}

function buildFollowUpFilters(){
  const ar = state.data || [];
  // state.data uses the compact shape: r.b=Business, r.s=Seller_Name, r.ci=Company ID
  const bus  = [...new Set(ar.map(r => String(r.b||'').trim()).filter(Boolean))].sort();
  const cust = [...new Set(ar.map(r => String(r.s||'').trim()).filter(Boolean))].sort();
  const buHost = document.getElementById('fuMSBU');
  const custHost = document.getElementById('fuMSCust');
  // Reset selection arrays so a fresh open doesn't carry over stale picks
  fuState.selBus.length = 0;
  fuState.selCust.length = 0;
  if (buHost && typeof buildSimpleMS === 'function') {
    // buildSimpleMS mutates fuState.selBus in place as user toggles checkboxes
    buildSimpleMS(buHost, 'region', bus, fuState.selBus, ()=>{});
  }
  if (custHost && typeof buildSimpleMS === 'function') {
    buildSimpleMS(custHost, 'customer', cust, fuState.selCust, ()=>{});
  }
}

function fuSelectedBus(){ return fuState.selBus.slice(); }
function fuSelectedCust(){
  const names = fuState.selCust.slice();
  if(!names.length) return [];
  // Map customer names back to CIDs using compact shape
  const ar = state.data || [];
  const cids = new Set();
  ar.forEach(r=>{
    const n = String(r.s||'').trim();
    if (names.includes(n)) cids.add(String(r.ci||'').trim());
  });
  return [...cids].filter(Boolean);
}

function fuFmtINR(n){ n = Number(n)||0; return '\u20B9' + n.toLocaleString('en-IN',{maximumFractionDigits:2}); }

async function fuBuildPreview(){
  const bus = fuSelectedBus();
  const cids = fuSelectedCust();
  if(!bus.length && !cids.length){
    document.getElementById('fuStatusBar').innerHTML = '<span style="color:#b91c1c">Select at least one Region or Customer.</span>';
    return;
  }
  const status = document.getElementById('fuStatusBar');
  status.innerHTML = '<span style="color:var(--c-muted)">Loading eligible customers from live AR_Data…</span>';
  try{
    const params = {};
    if (bus.length)  params.bus  = bus.join(',');
    if (cids.length) params.cids = cids.join(',');
    // Honour Force-resend at preview time too — otherwise rows in cooldown
    // would stay disabled and the user can never re-select them in the same day.
    const forceEl = document.getElementById('fuForce');
    if (forceEl && forceEl.checked) params.force = '1';
    const res = await _fuJsonp('previewBU', params);
    if(!res || !res.ok){
      let msg;
      if (res && res.error) msg = res.error;
      else if (res && (res.ar || res.counts || res.tabsFound)) msg = 'The deployed Apps Script does not recognise <code>action=previewBU</code> — please redeploy the updated code.gs as a <b>new Web App version</b> (Deploy → Manage Deployments → Edit → New version → Deploy).';
      else msg = 'Backend did not return a success response.';
      status.innerHTML = '<span style="color:#b91c1c">'+ msg +'</span>';
      return;
    }
    fuState.rows = res.customers || [];
    fuState.invoices = res.invoices || [];
    fuRenderTable();
    const eligible = fuState.rows.filter(r=>r.eligible).length;
    status.innerHTML = `<b>${fuState.rows.length}</b> customers in scope · <b>${eligible}</b> eligible to send · Sender: <code>${res.sender}</code> · BCC: <code>${res.bcc}</code>`;
  }catch(err){
    status.innerHTML = '<span style="color:#b91c1c">'+ err.message +'</span>';
  }
}

function fuRenderTable(){
  const tbody = document.getElementById('fuTbody');
  if(!fuState.rows.length){
    tbody.innerHTML = '<tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">No matching customers.</td></tr>';
    fuUpdateSendButton();
    return;
  }
  const html = fuState.rows.map((r,i)=>{
    const checked = r.eligible ? 'checked' : '';
    const disabled = r.eligible ? '' : 'disabled';
    const statusClass = r.eligible ? 'fu-status-ready' : (r.cooldownActive ? 'fu-status-cooldown' : 'fu-status-blocked');
    const rowClass = r.eligible ? '' : 'fu-row-disabled';
    return `<tr class="${rowClass} border-t border-slate-100">
      <td class="px-3 py-2"><input type="checkbox" class="fu-row-chk" data-cid="${r.cid}" ${checked} ${disabled}></td>
      <td class="px-3 py-2 font-mono text-[11px]">${r.cid}</td>
      <td class="px-3 py-2">${r.customer||'—'}</td>
      <td class="px-3 py-2">${r.bu||'—'}</td>
      <td class="px-3 py-2 text-[11px]">${r.toEmail||'<span style="color:#b91c1c">— no contact —</span>'}</td>
      <td class="px-3 py-2 text-right">${r.count}</td>
      <td class="px-3 py-2 text-right">${fuFmtINR(r.invoiceTotal)}</td>
      <td class="px-3 py-2 text-right">${fuFmtINR(r.outstandingTotal)}</td>
      <td class="px-3 py-2 text-right">${r.oldestDays}</td>
      <td class="px-3 py-2 ${statusClass}">${r.reason}</td>
      <td class="px-3 py-2">${r.eligible ? `<button class="chip fu-preview-one" data-cid="${r.cid}">👁 Preview</button>` : ''}</td>
    </tr>`;
  }).join('');
  tbody.innerHTML = html;
  // Wire row events
  tbody.querySelectorAll('.fu-row-chk').forEach(cb => cb.addEventListener('change', fuUpdateSendButton));
  tbody.querySelectorAll('.fu-preview-one').forEach(btn => btn.addEventListener('click', e => fuPreviewOne(btn.dataset.cid)));
  fuUpdateSendButton();
}

function fuCheckedCids(){
  return [...document.querySelectorAll('.fu-row-chk:checked')].map(cb => cb.dataset.cid);
}

function fuUpdateSendButton(){
  const checked = fuCheckedCids();
  document.getElementById('fuSendCount').textContent = checked.length;
  document.getElementById('fuSend').disabled = checked.length === 0;
  document.getElementById('fuDownloadXls').disabled = checked.length === 0;
  document.getElementById('fuPreviewFirst').disabled = checked.length === 0;
}

async function fuPreviewOne(cid){
  const modalBody = document.getElementById('fuModalBody');
  const modalSub = document.getElementById('fuModalSub');
  const modalMeta = document.getElementById('fuModalMeta');
  document.getElementById('fuModalTitle').textContent = 'Email Preview · ' + cid;
  modalSub.textContent = 'Loading live data from AR_Data…';
  modalBody.innerHTML = '<div class="text-center text-slate-500 py-10">Loading…</div>';
  document.getElementById('fuModal').style.display = 'flex';
  const confirmBtn = document.getElementById('fuModalConfirm');
  confirmBtn.dataset.cids = cid;
  confirmBtn.dataset.mode = 'one';
  try{
    const tplSel = document.getElementById('fuTemplate');
    const templateId = tplSel ? tplSel.value : '';
    const reqParams = {cid};
    if (templateId) reqParams.templateId = templateId;
    // Carry the same Region scope the user picked when building the list.
    // Without this the modal preview would show all-region outstanding for
    // multi-region customers even though the table row is region-scoped.
    const busSel = fuSelectedBus();
    if (busSel.length) reqParams.bus = busSel.join(',');
    const res = await _fuJsonp('previewOne', reqParams);
    if(!res || !res.ok){
      let m;
      if (res && (res.message || res.error)) m = res.message || res.error;
      else if (res && (res.ar || res.counts || res.tabsFound)) m = 'The deployed Apps Script does not recognise <code>action=previewOne</code> — please redeploy the updated code.gs as a <b>new Web App version</b>.';
      else m = 'Backend did not return a success response.';
      modalBody.innerHTML = '<div class="p-6 text-center" style="color:#b91c1c">'+m+'</div>';
      modalSub.textContent = '';
      confirmBtn.disabled = true;
      return;
    }
    modalSub.textContent = `Recipient: ${res.contact.to} · ${res.preview.invoiceCount} invoices · Total Outstanding ${fuFmtINR(res.preview.outstandingTotal)}`;
    modalMeta.innerHTML = `Sender <code>${res.sender}</code> · BCC <code>${res.bcc}</code>` +
      (res.cooldown.active ? ` · <span style="color:#92400e">Cooldown active — last sent ${res.cooldown.lastSent}</span>` : '');
    modalBody.innerHTML = `<div class="bg-white border border-slate-200 rounded p-4">
      <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Subject</div>
      <div class="font-semibold mb-3">${res.preview.subject}</div>
      <div class="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Body</div>
      ${res.preview.htmlBody}
    </div>`;
    confirmBtn.disabled = res.cooldown.active && !document.getElementById('fuForce').checked;
  }catch(err){
    modalBody.innerHTML = '<div class="p-6 text-center" style="color:#b91c1c">'+err.message+'</div>';
  }
}

async function fuPreviewFirst(){
  const checked = fuCheckedCids();
  if(!checked.length) return;
  fuPreviewOne(checked[0]);
}

async function fuConfirmSend(){
  const confirmBtn = document.getElementById('fuModalConfirm');
  const cids = (confirmBtn.dataset.cids || '').split(',').filter(Boolean);
  const mode = confirmBtn.dataset.mode || 'bulk';
  if(!cids.length) return;
  const force = document.getElementById('fuForce').checked ? '1' : '';
  const tplSel = document.getElementById('fuTemplate');
  const templateId = tplSel ? tplSel.value : '';
  // Region scope from the Follow-ups filter. Sent to the backend so the
  // outbound email body reflects only the region the user picked (matches
  // the on-screen preview and the Excel download).
  const busSel = fuSelectedBus();
  const busCsv = busSel.length ? busSel.join(',') : '';
  confirmBtn.disabled = true;
  confirmBtn.textContent = 'Sending…';
  try{
    let result;
    if (mode === 'one') {
      const p = {cid: cids[0], force};
      if (templateId) p.templateId = templateId;
      if (busCsv) p.bus = busCsv;
      result = await _fuJsonp('sendOne', p);
    } else {
      const p = {cids: cids.join(','), force};
      if (templateId) p.templateId = templateId;
      if (busCsv) p.bus = busCsv;
      result = await _fuJsonp('sendBulk', p);
    }
    const ok = result.ok ? (result.successCount !== undefined ? `${result.successCount}/${result.total} sent successfully` : 'Email sent') : (result.error || 'Failed');
    document.getElementById('fuModalBody').innerHTML = `<div class="bg-white border border-slate-200 rounded p-4">
      <div class="text-[14px] font-semibold ${result.ok?'text-green-700':'text-red-700'} mb-2">${result.ok?'✓':'✗'} ${ok}</div>
      <pre class="text-[11px] bg-slate-50 p-2 rounded overflow-auto">${JSON.stringify(result, null, 2)}</pre>
    </div>`;
    confirmBtn.textContent = 'Done';
    confirmBtn.style.background = result.ok ? '#15803d' : '#b91c1c';
    // After 1.2s, refresh the preview list
    setTimeout(()=>{ document.getElementById('fuModal').style.display = 'none'; fuBuildPreview(); }, 1500);
  }catch(err){
    document.getElementById('fuModalBody').innerHTML = '<div class="p-6 text-center" style="color:#b91c1c">'+err.message+'</div>';
    confirmBtn.textContent = '📧 Confirm & Send';
    confirmBtn.disabled = false;
  }
}

async function fuOpenBulkSend(){
  const checked = fuCheckedCids();
  if(!checked.length) return;
  document.getElementById('fuModalTitle').textContent = `Bulk Send · ${checked.length} customers`;
  document.getElementById('fuModalSub').textContent = 'Confirm to send follow-up emails to all selected customers';
  document.getElementById('fuModalMeta').innerHTML = `Sender <code>ar@gofynd.com</code> · BCC <code>sainathgosika@gofynd.com</code> · Cooldown ${document.getElementById('fuForce').checked?'overridden':'enforced (24h)'}`;
  const rows = fuState.rows.filter(r => checked.includes(r.cid));
  const sumInv = rows.reduce((a,r)=>a+r.invoiceTotal,0);
  const sumOs  = rows.reduce((a,r)=>a+r.outstandingTotal,0);
  document.getElementById('fuModalBody').innerHTML = `
    <div class="bg-white border border-slate-200 rounded p-4">
      <div class="text-[14px] font-semibold mb-2">Confirm to send ${checked.length} follow-up emails</div>
      <div class="text-[12px] text-slate-600 mb-3">Total invoices: <b>${rows.reduce((a,r)=>a+r.count,0)}</b> · Invoice Total: <b>${fuFmtINR(sumInv)}</b> · Outstanding: <b>${fuFmtINR(sumOs)}</b></div>
      <div class="overflow-auto max-h-72 border border-slate-100 rounded">
        <table class="w-full text-[11px]">
          <thead class="bg-slate-50"><tr><th class="px-2 py-1 text-left">CID</th><th class="px-2 py-1 text-left">Customer</th><th class="px-2 py-1 text-left">To</th><th class="px-2 py-1 text-right">Inv</th><th class="px-2 py-1 text-right">Outstanding</th></tr></thead>
          <tbody>${rows.map(r=>`<tr class="border-t border-slate-100"><td class="px-2 py-1 font-mono">${r.cid}</td><td class="px-2 py-1">${r.customer}</td><td class="px-2 py-1">${r.toEmail}</td><td class="px-2 py-1 text-right">${r.count}</td><td class="px-2 py-1 text-right">${fuFmtINR(r.outstandingTotal)}</td></tr>`).join('')}</tbody>
        </table>
      </div>
    </div>`;
  const confirmBtn = document.getElementById('fuModalConfirm');
  confirmBtn.dataset.cids = checked.join(',');
  confirmBtn.dataset.mode = 'bulk';
  confirmBtn.textContent = '📧 Confirm & Send';
  confirmBtn.disabled = false;
  confirmBtn.style.background = '#15803d';
  document.getElementById('fuModal').style.display = 'flex';
}

function fuDownloadExcel(){
  const checked = new Set(fuCheckedCids());
  const subset = fuState.invoices.filter(r => checked.has(r.cid));
  if(!subset.length){ alert('No checked rows'); return; }
  if(typeof ExcelJS === 'undefined'){ alert('ExcelJS not loaded'); return; }
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('Outstanding Follow-up');
  ws.columns = [
    {header:'CID', key:'cid', width:12},
    {header:'Customer Name', key:'customer', width:30},
    {header:'Channel', key:'channel', width:14},
    {header:'Transaction Type', key:'transactionType', width:18},
    {header:'Invoice Number', key:'invoiceNo', width:22},
    {header:'Invoice Type', key:'invoiceType', width:14},
    {header:'Invoice Date', key:'invoiceDate', width:14},
    {header:'Invoice Due Date', key:'dueDate', width:16},
    {header:'Invoice Amount', key:'invoiceAmount', width:16, style:{numFmt:'#,##0.00'}},
    {header:'Outstanding Amount', key:'outstandingAmount', width:18, style:{numFmt:'#,##0.00'}},
    {header:'Days', key:'days', width:10}
  ];
  subset.forEach(r => ws.addRow(r));
  // Total row
  const tot = ws.addRow({ cid:'', customer:'TOTAL', channel:'', transactionType:'', invoiceNo:'', invoiceType:'', invoiceDate:'', dueDate:'',
    invoiceAmount: subset.reduce((a,r)=>a+r.invoiceAmount,0),
    outstandingAmount: subset.reduce((a,r)=>a+r.outstandingAmount,0), days:'' });
  tot.font = {bold:true}; tot.fill = {type:'pattern', pattern:'solid', fgColor:{argb:'FFF1F5F9'}};
  ws.getRow(1).font = {bold:true, color:{argb:'FFFFFFFF'}};
  ws.getRow(1).fill = {type:'pattern', pattern:'solid', fgColor:{argb:'FF2C4A52'}};
  ws.views = [{state:'frozen', ySplit:1}];
  const today = new Date().toISOString().slice(0,10).replace(/-/g,'');
  wb.xlsx.writeBuffer().then(buf => {
    const blob = new Blob([buf], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `Outstanding_FollowUp_${today}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  });
}

function wireFollowUps(){
  document.getElementById('fuBuild').addEventListener('click', fuBuildPreview);
  // Toggling Force-resend should immediately re-evaluate eligibility so
  // recently-sent customers become re-selectable without clicking Build Preview again.
  const forceEl = document.getElementById('fuForce');
  if (forceEl) forceEl.addEventListener('change', ()=>{
    if ((fuState.rows||[]).length) fuBuildPreview();
  });
  document.getElementById('fuSend').addEventListener('click', fuOpenBulkSend);
  document.getElementById('fuPreviewFirst').addEventListener('click', fuPreviewFirst);
  document.getElementById('fuDownloadXls').addEventListener('click', fuDownloadExcel);
  document.getElementById('fuModalClose').addEventListener('click', ()=> document.getElementById('fuModal').style.display='none');
  document.getElementById('fuModalCancel').addEventListener('click', ()=> document.getElementById('fuModal').style.display='none');
  document.getElementById('fuModalConfirm').addEventListener('click', fuConfirmSend);
  document.getElementById('fuCheckAll').addEventListener('change', e => {
    document.querySelectorAll('.fu-row-chk:not(:disabled)').forEach(cb => cb.checked = e.target.checked);
    fuUpdateSendButton();
  });
  // === Email Templates wiring (shared pool) ===
  tplLoad();   // refresh dropdown + cache when Follow-ups initialises
  const manageBtn = document.getElementById('fuManageTpl');
  if (manageBtn) manageBtn.addEventListener('click', (e)=>{ e.preventDefault(); tplOpenModal(); });
  const tplClose = document.getElementById('tplModalClose');
  if (tplClose) tplClose.addEventListener('click', tplCloseModal);
  const tplCancel = document.getElementById('tplCancel');
  if (tplCancel) tplCancel.addEventListener('click', tplCloseModal);
  const tplNewBtn = document.getElementById('tplNew');
  if (tplNewBtn) tplNewBtn.addEventListener('click', ()=> tplOpenEditor(null));
  const tplSaveBtn = document.getElementById('tplSave');
  if (tplSaveBtn) tplSaveBtn.addEventListener('click', tplSave);
  const tplDelBtn = document.getElementById('tplDelete');
  if (tplDelBtn) tplDelBtn.addEventListener('click', tplDelete);
}

// ===== Email Templates module =====
const tplState = { list: [], tokens: [], current: null };

async function tplLoad(){
  try{
    const res = await _fuJsonp('templatesList', {});
    if (!res || !res.ok) { tplState.lastErr = _tplExplainBadRes(res, 'templatesList'); return; }
    tplState.lastErr = '';
    tplState.list   = res.rows   || [];
    tplState.tokens = res.tokens || [];
    tplRenderDropdown();
  }catch(err){ tplState.lastErr = (err && err.message) || String(err); }
}

// Build a clear human message when the backend gives us something other than
// the expected {ok:true,...}. Distinguishes the "route not deployed" case
// (where serveData_ returns the AR/PDD payload) from a real error.
function _tplExplainBadRes(res, action){
  if (!res) return 'No response from backend (script timed out).';
  if (res.error) return res.error;
  if (res.ar || res.pdd || res.bank || res.counts || res.tabsFound) {
    return 'The deployed Apps Script does not recognise <code>action=' + action +
      '</code>. <b>Redeploy Code.gs as a new Web App version</b> (Deploy → Manage Deployments → Edit → New version → Deploy) — the email-templates routes were just added.';
  }
  return 'Unexpected response: ' + JSON.stringify(res).slice(0,200);
}

function tplRenderDropdown(){
  const sel = document.getElementById('fuTemplate');
  if (!sel) return;
  const prev = sel.value;
  const opts = ['<option value="">Default (built-in)</option>']
    .concat(tplState.list.map(t => {
      const lbl = (t.isDefault ? '★ ' : '') + (t.name || '(unnamed)');
      return `<option value="${t.id}">${lbl}</option>`;
    }));
  sel.innerHTML = opts.join('');
  // Re-select if still present, else fall back to the default template id.
  if (prev && tplState.list.some(t => t.id === prev)) {
    sel.value = prev;
  } else {
    const def = tplState.list.find(t => t.isDefault);
    sel.value = def ? def.id : '';
  }
}

async function tplOpenModal(){
  document.getElementById('tplModal').style.display = 'flex';
  document.getElementById('tplList').innerHTML = '<div class="text-slate-500">Loading…</div>';
  tplShowEmpty();
  // Always pull fresh from the sheet so newly-deployed routes start working
  // without a full page reload, and so any backend error gets surfaced.
  await tplLoad();
  const hint = document.getElementById('tplTokenHint');
  if (hint) hint.textContent = (tplState.tokens||[]).map(t => '{{'+t+'}}').join(' · ');
  tplRenderList();
}
function tplCloseModal(){
  document.getElementById('tplModal').style.display = 'none';
}
function tplShowEmpty(){
  document.getElementById('tplEditorEmpty').style.display = '';
  document.getElementById('tplEditor').style.display = 'none';
  tplState.current = null;
}

function tplRenderList(){
  const wrap = document.getElementById('tplList');
  if (!wrap) return;
  if (!tplState.list.length) {
    if (tplState.lastErr) {
      wrap.innerHTML = '<div style="color:#b91c1c;font-size:11px;background:#fef2f2;border:1px solid #fecaca;padding:8px;border-radius:6px;line-height:1.45">'+
        '<b>Could not load templates.</b><br>'+ tplState.lastErr +'</div>';
    } else {
      wrap.innerHTML = '<div class="text-slate-500">No templates yet. Click <b>＋ New Template</b>.</div>';
    }
    return;
  }
  wrap.innerHTML = tplState.list.map(t => {
    const star = t.isDefault ? '<span title="Default" style="color:#ca8a04">★</span>' : '';
    return `<button data-id="${t.id}" class="tpl-item w-full text-left px-2 py-1.5 rounded hover:bg-white border border-transparent hover:border-slate-200" style="display:flex;gap:6px;align-items:center">
      ${star}<span class="truncate">${(t.name||'(unnamed)')}</span>
    </button>`;
  }).join('');
  wrap.querySelectorAll('.tpl-item').forEach(btn => {
    btn.addEventListener('click', ()=>{
      const id = btn.dataset.id;
      const tpl = tplState.list.find(t => String(t.id) === String(id));
      if (tpl) tplOpenEditor(tpl);
    });
  });
}

function tplOpenEditor(tpl){
  tplState.current = tpl;   // null when creating new
  document.getElementById('tplEditorEmpty').style.display = 'none';
  document.getElementById('tplEditor').style.display = '';
  document.getElementById('tplName').value      = tpl ? (tpl.name||'')      : '';
  document.getElementById('tplSubject').value   = tpl ? (tpl.subject||'')   : 'Outstanding Invoice(s) - {{customer_name}}';
  document.getElementById('tplGreeting').value  = tpl ? (tpl.greeting||'')  : 'Hi Team,';
  document.getElementById('tplAbove').value     = tpl ? (tpl.bodyAbove||'') : '';
  document.getElementById('tplBelow').value     = tpl ? (tpl.bodyBelow||'') : '';
  document.getElementById('tplSig').value       = tpl ? (tpl.signature||'') : '';
  document.getElementById('tplIsDefault').checked = !!(tpl && tpl.isDefault);
  document.getElementById('tplIncludeBank').checked = tpl ? (tpl.includeBank !== false) : true;
  document.getElementById('tplDelete').style.display = tpl ? '' : 'none';
  document.getElementById('tplSaveMsg').textContent = '';
}

async function tplSave(){
  const msg = document.getElementById('tplSaveMsg');
  const name = (document.getElementById('tplName').value || '').trim();
  if (!name) { msg.innerHTML = '<span style="color:#b91c1c">Template Name is required.</span>'; return; }
  const params = {
    id:          (tplState.current && tplState.current.id) || '',
    name:        name,
    subject:     document.getElementById('tplSubject').value || '',
    greeting:    document.getElementById('tplGreeting').value || '',
    bodyAbove:   document.getElementById('tplAbove').value || '',
    bodyBelow:   document.getElementById('tplBelow').value || '',
    signature:   document.getElementById('tplSig').value || '',
    isDefault:   document.getElementById('tplIsDefault').checked ? 'true' : 'false',
    includeBank: document.getElementById('tplIncludeBank').checked ? 'true' : 'false'
  };
  msg.innerHTML = '<span style="color:#64748b">Saving…</span>';
  try{
    const res = await _fuJsonp('templatesSave', params);
    if (!res || !res.ok) {
      msg.innerHTML = '<span style="color:#b91c1c">Save failed: '+ _tplExplainBadRes(res, 'templatesSave') +'</span>';
      return;
    }
    msg.innerHTML = '<span style="color:#15803d">Saved ✓</span>';
    await tplLoad();
    tplRenderList();
    // Re-open editor on the saved row so subsequent saves are updates
    const saved = tplState.list.find(t => String(t.id) === String(res.id));
    if (saved) tplOpenEditor(saved);
  }catch(err){
    msg.innerHTML = '<span style="color:#b91c1c">Save failed: '+ ((err && err.message) || String(err)) +'</span>';
  }
}

async function tplDelete(){
  if (!tplState.current || !tplState.current.id) return;
  if (!confirm('Delete template "' + (tplState.current.name||'') + '"? This cannot be undone.')) return;
  const msg = document.getElementById('tplSaveMsg');
  msg.innerHTML = '<span style="color:#64748b">Deleting…</span>';
  try{
    const res = await _fuJsonp('templatesDelete', { id: tplState.current.id });
    if (!res || !res.ok) {
      msg.innerHTML = '<span style="color:#b91c1c">Delete failed: '+ _tplExplainBadRes(res, 'templatesDelete') +'</span>';
      return;
    }
    await tplLoad();
    tplRenderList();
    tplShowEmpty();
  }catch(err){
    msg.innerHTML = '<span style="color:#b91c1c">Delete failed: '+ ((err && err.message) || String(err)) +'</span>';
  }
}

// =============================================================
// Customer POCs (Contacts) — CRUD + Bulk Upload/Download
// Backed by tabs Customer_POCs. Feeds the follow-up sender.
// =============================================================
const pocState = {
  rows: [],             // list of {cid, customerName, contactName, role, email, phone, priority, active, notes, updatedBy, updatedAt}
  filtered: [],
  cidUniverse: [],      // [{cid, name, region}]
  priorities: ['Primary','CC','Escalation'],
  editing: null,        // rec being edited, null when creating new
  bulk: { rows: [], report: [], summary: null },
  lastErr: ''
};

function _pocEsc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function _pocExplainBadRes(res, action){
  if (!res) return 'No response from backend (script timed out).';
  if (res.error) return res.error;
  if (res.ar || res.pdd || res.bank || res.counts || res.tabsFound) {
    return 'The deployed Apps Script does not recognise <code>action=' + action +
      '</code>. <b>Redeploy Code.gs as a new Web App version</b> — POC + Workflow routes were just added.';
  }
  return 'Unexpected response: ' + JSON.stringify(res).slice(0,200);
}

async function pocLoad(){
  // Merged loader — fetches customer POCs AND internal stakeholders in
  // parallel, then renders them in ONE table with a Type column. Failures
  // on the internal-stakeholder side degrade gracefully so a stale IS
  // deploy doesn't take out the customer-contacts table.
  const tbody = document.getElementById('pocTbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>';
  // Fire-and-forget: refresh the one-time-migration lock state alongside
  // the data load so the Migrate-legacy button reflects the backend truth.
  pocRefreshMigrateState();
  try{
    // Fire both requests concurrently — no ordering dependency.
    const [pocRes, isRes] = await Promise.all([
      _fuJsonp('pocList', {}).catch(err => ({ error: (err && err.message) || String(err) })),
      _fuJsonp('isList',  {}).catch(err => ({ error: (err && err.message) || String(err) }))
    ]);
    if (!pocRes || !pocRes.ok) {
      pocState.lastErr = _pocExplainBadRes(pocRes, 'pocList');
      if (tbody) tbody.innerHTML = `<tr><td colspan="11" class="px-3 py-6 text-center" style="color:#b91c1c">${pocState.lastErr}</td></tr>`;
      return;
    }
    pocState.lastErr = '';
    // Tag every customer POC row with _kind='customer'
    const custRows = (pocRes.rows || []).map(r => Object.assign({}, r, { _kind: 'customer' }));
    // Internal stakeholder rows carry stakeholderName not contactName; alias
    // so downstream filter/render doesn't need to branch on kind.
    let intRows = [];
    if (isRes && isRes.ok) {
      intRows = (isRes.rows || []).map(r => Object.assign({}, r, {
        _kind: 'internal',
        contactName: r.contactName || r.stakeholderName || ''
      }));
      // Mirror IS state for downstream helpers (isOpenModal / isDelete /
      // bulk-upload preview) that still consult isState.rows.
      if (typeof isState !== 'undefined') {
        isState.rows = isRes.rows || [];
        isState.cidUniverse = isRes.cidUniverse || isState.cidUniverse;
        isState.priorities = isRes.priorities || isState.priorities;
        isState.lastErr = '';
      }
    } else if (typeof isState !== 'undefined') {
      // Don't kill the whole page if IS backend is not yet deployed —
      // surface a small note in the status bar and press on.
      isState.lastErr = _pocExplainBadRes(isRes, 'isList');
    }
    pocState.rows = custRows.concat(intRows);
    pocState.cidUniverse = pocRes.cidUniverse || [];
    pocState.priorities = pocRes.priorities || pocState.priorities;
    pocApplyFilter();
    _pocFillCidDatalist();
    // Surface a soft warning if IS fetch failed but customer POCs loaded.
    const sb = document.getElementById('pocStatusBar');
    if (sb) {
      if (isRes && !isRes.ok) {
        sb.innerHTML = `<span style="color:#b45309">Internal stakeholders unavailable: ${_pocEsc(_pocExplainBadRes(isRes,'isList'))}</span>`;
      } else {
        sb.textContent = '';
      }
    }
  }catch(err){
    pocState.lastErr = (err && err.message) || String(err);
    if (tbody) tbody.innerHTML = `<tr><td colspan="11" class="px-3 py-6 text-center" style="color:#b91c1c">${pocState.lastErr}</td></tr>`;
  }
}

function _pocFillCidDatalist(){
  const html = pocState.cidUniverse.map(c => `<option value="${_pocEsc(c.cid)}">${_pocEsc(c.name||'')}${c.region ? ' — ' + _pocEsc(c.region) : ''}</option>`).join('');
  ['pmCidList','imCidList'].forEach(id => {
    const dl = document.getElementById(id);
    if (dl) dl.innerHTML = html;
  });
}

function pocApplyFilter(){
  const q   = (document.getElementById('pocSearch')?.value || '').trim().toLowerCase();
  const typ = document.getElementById('pocFilterType')?.value || '';
  const pri = document.getElementById('pocFilterPriority')?.value || '';
  const act = document.getElementById('pocFilterActive')?.value || '';
  pocState.filtered = (pocState.rows || []).filter(r => {
    if (typ && String(r._kind||'customer') !== typ) return false;
    if (pri && String(r.priority||'').toLowerCase() !== pri.toLowerCase()) return false;
    if (act === 'Y' && !r.active) return false;
    if (act === 'N' && r.active) return false;
    if (q){
      const hay = [r.cid, r.customerName, r.contactName, r.stakeholderName, r.email, r.phone, r.role, r.notes].map(x=>String(x||'').toLowerCase()).join(' | ');
      if (hay.indexOf(q) === -1) return false;
    }
    return true;
  });
  pocRenderTable();
}

function pocRenderTable(){
  const tbody = document.getElementById('pocTbody');
  const countEl = document.getElementById('pocCount');
  if (!tbody) return;
  if (!pocState.filtered.length){
    tbody.innerHTML = '<tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">No contacts match the current filters.</td></tr>';
    if (countEl) countEl.textContent = `0 of ${pocState.rows.length} shown`;
    return;
  }
  const rows = pocState.filtered.map((r, i) => {
    const priColor = r.priority === 'Primary' ? '#0d9488' : (r.priority === 'CC' ? '#0369a1' : '#a16207');
    const activeBadge = r.active
      ? '<span style="color:#15803d;font-weight:600">✓</span>'
      : '<span style="color:#94a3b8">—</span>';
    const kind = r._kind === 'internal' ? 'internal' : 'customer';
    const typeBadge = kind === 'internal'
      ? '<span class="text-[10px] font-semibold" style="background:#fef3c7;color:#92400e;padding:2px 6px;border-radius:9999px">👥 Internal</span>'
      : '<span class="text-[10px] font-semibold" style="background:#dbeafe;color:#1e40af;padding:2px 6px;border-radius:9999px">📧 Customer</span>';
    const rowShade = kind === 'internal' ? 'background:#fffbeb' : '';
    const contactLabel = r.contactName || r.stakeholderName || '—';
    return `<tr class="border-t border-slate-100" data-cid="${_pocEsc(r.cid)}" data-email="${_pocEsc(r.email)}" data-kind="${kind}" style="${rowShade}">
      <td class="px-3 py-2">${typeBadge}</td>
      <td class="px-3 py-2 font-mono text-[11px]">${_pocEsc(r.cid)}</td>
      <td class="px-3 py-2">${_pocEsc(r.customerName||'')}</td>
      <td class="px-3 py-2">${_pocEsc(contactLabel)}</td>
      <td class="px-3 py-2 text-slate-500">${_pocEsc(r.role||'')}</td>
      <td class="px-3 py-2 text-[11px]">${_pocEsc(r.email||'')}</td>
      <td class="px-3 py-2 text-[11px]">${_pocEsc(r.phone||'')}</td>
      <td class="px-3 py-2" style="color:${priColor};font-weight:600">${_pocEsc(r.priority||'Primary')}</td>
      <td class="px-3 py-2 text-center">${activeBadge}</td>
      <td class="px-3 py-2 text-[11px] text-slate-500" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${_pocEsc(r.notes||'')}">${_pocEsc(r.notes||'')}</td>
      <td class="px-3 py-2 text-center whitespace-nowrap">
        <button class="chip poc-edit" data-idx="${i}">✎</button>
        <button class="chip poc-del" data-idx="${i}" style="color:#b91c1c">🗑</button>
      </td>
    </tr>`;
  }).join('');
  tbody.innerHTML = rows;
  const custCount = pocState.filtered.filter(r => r._kind !== 'internal').length;
  const intCount  = pocState.filtered.length - custCount;
  if (countEl) countEl.textContent = `${pocState.filtered.length} of ${pocState.rows.length} shown · ${custCount} customer · ${intCount} internal`;
  // Edit/Delete route to the correct backend based on _kind so the merged
  // table can drive both the customer-POC and internal-stakeholder flows.
  tbody.querySelectorAll('.poc-edit').forEach(btn => btn.addEventListener('click', ()=>{
    const rec = pocState.filtered[Number(btn.dataset.idx)];
    if (!rec) return;
    if (rec._kind === 'internal' && typeof isOpenModal === 'function') { isOpenModal(rec); }
    else { pocOpenModal(rec); }
  }));
  tbody.querySelectorAll('.poc-del').forEach(btn => btn.addEventListener('click', ()=>{
    const rec = pocState.filtered[Number(btn.dataset.idx)];
    if (!rec) return;
    if (rec._kind === 'internal' && typeof isDelete === 'function') { isDelete(rec); }
    else { pocDelete(rec); }
  }));
}

// -------- unified Add-Contact modal ---------------------------------------
// One modal handles BOTH customer POCs and internal (Fynd) stakeholders for
// a single CID. Each has its own wrap so we can render them separately in
// the tables below but collect+save both in one atomic-ish click.
function _pmEmailRowsWrap(){ return document.getElementById('pmEmailsWrap'); }
function _pmStakeRowsWrap(){ return document.getElementById('pmStakeWrap'); }

// kind: 'customer' | 'internal' — decides which wrap the row lands in AND
// which backend route the save loop calls. Rows carry data-poc-kind so the
// collector can round-trip the kind without extra state.
function pocAddEmailRow(seed, kind){
  kind = (kind === 'internal') ? 'internal' : 'customer';
  const wrap = kind === 'internal' ? _pmStakeRowsWrap() : _pmEmailRowsWrap();
  if (!wrap) return null;
  const tpl = document.getElementById('pmEmailRowTpl');
  if (!tpl || !tpl.content) return null;
  const node = tpl.content.firstElementChild.cloneNode(true);
  const s = seed || {};
  node.dataset.pocKind = kind;
  node.dataset.originalEmail = (s.email || '').trim();
  node.querySelector('.pm-email').value    = s.email || '';
  node.querySelector('.pm-priority').value = s.priority || 'Primary';
  node.querySelector('.pm-active').value   = s.active === false ? 'N' : (s.active === 'N' ? 'N' : 'Y');
  node.querySelector('.pm-contact').value  = s.contactName || s.stakeholderName || '';
  node.querySelector('.pm-role').value     = s.role || '';
  node.querySelector('.pm-phone').value    = s.phone || '';
  node.querySelector('.pm-notes').value    = s.notes || '';
  // Tint internal rows so the eye can tell them apart even after scrolling.
  if (kind === 'internal') node.classList.add('bg-amber-50/60');
  // Placeholder tuning per kind
  if (kind === 'internal') {
    node.querySelector('.pm-contact').placeholder = 'e.g. Priya Nair';
    node.querySelector('.pm-role').placeholder    = 'e.g. Account Manager (Fynd)';
  }
  // If this row is an existing record being edited, lock the email field
  if (seed && seed.email) node.querySelector('.pm-email').disabled = true;
  node.querySelector('.pm-del-row').addEventListener('click', (ev)=>{
    ev.preventDefault();
    node.remove();
    _pmSyncEmptyStates();
  });
  wrap.appendChild(node);
  _pmSyncEmptyStates();
  return node;
}

// Hide the empty-state hint whenever a section has at least one row.
function _pmSyncEmptyStates(){
  const cWrap = _pmEmailRowsWrap(), sWrap = _pmStakeRowsWrap();
  const cEmpty = document.getElementById('pmEmailsEmpty');
  const sEmpty = document.getElementById('pmStakeEmpty');
  if (cEmpty) cEmpty.style.display = (cWrap && cWrap.querySelectorAll('.pm-email-row').length) ? 'none' : '';
  if (sEmpty) sEmpty.style.display = (sWrap && sWrap.querySelectorAll('.pm-email-row').length) ? 'none' : '';
}

function _pmCollectRows(){
  const out = [];
  [_pmEmailRowsWrap(), _pmStakeRowsWrap()].forEach(wrap => {
    if (!wrap) return;
    wrap.querySelectorAll('.pm-email-row').forEach(row => {
      out.push({
        kind:         row.dataset.pocKind || 'customer',
        originalEmail: row.dataset.originalEmail || '',
        email:       (row.querySelector('.pm-email').value    || '').trim(),
        priority:     row.querySelector('.pm-priority').value || 'Primary',
        active:       row.querySelector('.pm-active').value   || 'Y',
        contactName: (row.querySelector('.pm-contact').value  || '').trim(),
        role:        (row.querySelector('.pm-role').value     || '').trim(),
        phone:       (row.querySelector('.pm-phone').value    || '').trim(),
        notes:       (row.querySelector('.pm-notes').value    || '').trim()
      });
    });
  });
  return out;
}

// Open the unified modal. `rec` may carry `.kind === 'internal'` to indicate
// we're editing an internal-stakeholder row — in that case we seed the
// stakeholder section instead of the customer section.
function pocOpenModal(rec){
  pocState.editing = rec || null;
  const isEditingInternal = rec && rec.kind === 'internal';
  document.getElementById('pocModalTitle').textContent = rec
    ? (isEditingInternal ? 'Edit Stakeholder' : 'Edit Contact')
    : 'Add Contact';
  document.getElementById('pmCid').value = rec ? rec.cid : '';
  document.getElementById('pmCid').disabled = !!rec;   // CID is the customer key — can't change on edit
  document.getElementById('pmCustomerName').value = rec ? (rec.customerName||'') : '';
  document.getElementById('pmError').textContent = '';
  // Reset both wraps
  const cWrap = _pmEmailRowsWrap(); if (cWrap) cWrap.innerHTML = '';
  const sWrap = _pmStakeRowsWrap(); if (sWrap) sWrap.innerHTML = '';
  if (rec) {
    // Editing → seed the correct section with the record, leave the other empty
    pocAddEmailRow(rec, isEditingInternal ? 'internal' : 'customer');
  } else {
    // Fresh add → seed ONE blank customer email row, leave stakeholders empty
    pocAddEmailRow(null, 'customer');
  }
  _pmSyncEmptyStates();
  document.getElementById('pocModal').style.display = 'flex';
}

function pocCloseModal(){ document.getElementById('pocModal').style.display = 'none'; pocState.editing = null; }

async function pocSave(){
  const err = document.getElementById('pmError');
  err.textContent = '';
  const cid          = (document.getElementById('pmCid').value||'').trim();
  const customerName = (document.getElementById('pmCustomerName').value||'').trim();
  if (!cid) { err.textContent = 'CID is required.'; return; }
  const rows = _pmCollectRows();
  if (!rows.length) { err.textContent = 'Add at least one email (customer or internal).'; return; }
  const seen = new Set();  // dedupe on (kind + lowercased email)
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const label = (r.kind === 'internal' ? 'Stakeholder' : 'Customer') + ' row ' + (i+1);
    if (!r.email) { err.textContent = label + ': email is required.'; return; }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(r.email)) { err.textContent = label + ': invalid email "' + r.email + '".'; return; }
    const key = r.kind + '|' + r.email.toLowerCase();
    if (seen.has(key)) { err.textContent = label + ': duplicate email "' + r.email + '" in this section.'; return; }
    seen.add(key);
  }
  const btn = document.getElementById('pocModalSave');
  btn.disabled = true; btn.textContent = 'Saving…';
  const failedRows = [];
  let customerSaves = 0, internalSaves = 0;
  try {
    // Save sequentially so per-row errors surface cleanly. Customer emails
    // go through pocSave; internal stakeholders go through isSave. Branch
    // explicitly (rather than a dynamic action var) so static analysers
    // and grep-based tests can see both call sites.
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      const params = {
        cid, email: r.email,
        customerName,
        contactName: r.contactName,
        role:        r.role,
        phone:       r.phone,
        priority:    r.priority || 'Primary',
        active:      r.active || 'Y',
        notes:       r.notes
      };
      let res, action;
      if (r.kind === 'internal') {
        // isSaveRoute_ reads contactName as a fallback but we also pass
        // stakeholderName explicitly to future-proof against schema drift.
        params.stakeholderName = r.contactName;
        action = 'isSave';
        res = await _fuJsonp('isSave', params);
      } else {
        action = 'pocSave';
        res = await _fuJsonp('pocSave', params);
      }
      if (!res || !res.ok) {
        const label = (r.kind === 'internal' ? 'Stakeholder' : 'Customer') + ' row ' + (i+1);
        failedRows.push(label + ' (' + r.email + '): ' + _pocExplainBadRes(res, action));
      } else {
        if (r.kind === 'internal') internalSaves++; else customerSaves++;
      }
    }
    if (failedRows.length) {
      err.innerHTML = 'Saved ' + customerSaves + ' customer / ' + internalSaves + ' internal. '
                    + 'Failed:<br>' + failedRows.join('<br>');
      // Still refresh — some rows may have committed to the backend sheet
      try { await pocLoad(); } catch(_){}
      try { if (typeof isLoad === 'function') await isLoad(); } catch(_){}
      return;
    }
    pocCloseModal();
    // Explicit persistence confirmation — the user asked to be sure every
    // Add-Contact click writes to the sheet, so we surface a status-bar toast
    // summarising exactly what was saved and where.
    const sb = document.getElementById('pocStatusBar');
    if (sb) {
      const parts = [];
      if (customerSaves) parts.push(customerSaves + ' customer contact' + (customerSaves === 1 ? '' : 's'));
      if (internalSaves) parts.push(internalSaves + ' internal stakeholder' + (internalSaves === 1 ? '' : 's'));
      sb.innerHTML = '<span style="color:#0d9488;font-weight:600">✓ Saved to sheet:</span> '
                   + parts.join(' + ')
                   + ' <span class="text-slate-500">(CID ' + _pocEsc(cid) + ')</span>';
      // Auto-clear the toast after 6 seconds so it doesn\'t linger.
      setTimeout(() => { if (sb && sb.textContent && sb.textContent.indexOf('Saved to sheet') !== -1) sb.textContent = ''; }, 6000);
    }
    // Refresh BOTH tables so the user sees the additions in either list
    try { await pocLoad(); } catch(_){}
    try { if (typeof isLoad === 'function') await isLoad(); } catch(_){}
  } catch(ex) {
    err.textContent = 'Save failed: ' + ((ex && ex.message) || String(ex));
  } finally {
    btn.disabled = false; btn.textContent = 'Save Contact';
  }
}

async function pocDelete(rec){
  if (!rec) return;
  if (!confirm(`Delete contact ${rec.email} (CID ${rec.cid})?`)) return;
  try{
    const res = await _fuJsonp('pocDelete', { cid: rec.cid, email: rec.email });
    if (!res || !res.ok){ alert('Delete failed: ' + _pocExplainBadRes(res, 'pocDelete').replace(/<[^>]+>/g,'')); return; }
    await pocLoad();
  }catch(ex){
    alert('Delete failed: ' + ((ex && ex.message) || String(ex)));
  }
}

function pocDownloadExcel(){
  if (typeof ExcelJS === 'undefined'){ alert('ExcelJS not loaded'); return; }
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('Customer POCs');
  ws.columns = [
    {header:'CID',           key:'cid',           width:14},
    {header:'Customer Name', key:'customerName',  width:32},
    {header:'Contact Name',  key:'contactName',   width:22},
    {header:'Role',          key:'role',          width:22},
    {header:'Email',         key:'email',         width:32},
    {header:'Phone',         key:'phone',         width:16},
    {header:'Priority',      key:'priority',      width:12},
    {header:'Active',        key:'active',        width:8},
    {header:'Notes',         key:'notes',         width:32},
    {header:'Updated By',    key:'updatedBy',     width:24},
    {header:'Updated At',    key:'updatedAt',     width:20}
  ];
  const src = pocState.filtered.length ? pocState.filtered : pocState.rows;
  src.forEach(r => ws.addRow({
    cid: r.cid, customerName: r.customerName, contactName: r.contactName,
    role: r.role, email: r.email, phone: r.phone,
    priority: r.priority, active: r.active ? 'Y' : 'N',
    notes: r.notes, updatedBy: r.updatedBy, updatedAt: r.updatedAt
  }));
  ws.getRow(1).font = { bold:true, color:{argb:'FFFFFFFF'} };
  ws.getRow(1).fill = { type:'pattern', pattern:'solid', fgColor:{argb:'FF2C4A52'} };
  ws.views = [{state:'frozen', ySplit:1}];
  const today = new Date().toISOString().slice(0,10).replace(/-/g,'');
  wb.xlsx.writeBuffer().then(buf => {
    const blob = new Blob([buf], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `Customer_POCs_${today}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  });
}

function pocDownloadTemplate(){
  if (typeof ExcelJS === 'undefined'){ alert('ExcelJS not loaded'); return; }
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('Template');
  // Unified template — one file feeds BOTH customer POCs and internal
  // stakeholders. The Type column routes each row to the right sheet. The
  // column set matches the slimmed Add Contact modal: Type / CID / Customer
  // Name / Contact Name / Email / Phone / Priority / Notes. Active is not
  // captured in the modal (defaults to Y); it's kept as an optional
  // last-column override for the rare case where someone wants to bulk-load
  // an inactive record.
  ws.columns = [
    {header:'Type',          key:'type',          width:12},
    {header:'CID',           key:'cid',           width:14},
    {header:'Customer Name', key:'customerName',  width:32},
    {header:'Contact Name',  key:'contactName',   width:22},
    {header:'Email',         key:'email',         width:32},
    {header:'Phone',         key:'phone',         width:16},
    {header:'Priority',      key:'priority',      width:12},
    {header:'Notes',         key:'notes',         width:32},
    {header:'Active',        key:'active',        width:8}
  ];
  // Two sample rows so users see BOTH kinds in the same file.
  ws.addRow({ type:'Customer', cid:'CID-12345', customerName:'ACME Retail Ltd', contactName:'Rahul Sharma',
              email:'rahul@acme.com', phone:'+91-9876543210',
              priority:'Primary', notes:'Sample customer POC — replace/delete before upload',
              active:'Y' });
  ws.addRow({ type:'Internal', cid:'CID-12345', customerName:'ACME Retail Ltd', contactName:'Priya Nair',
              email:'priya@gofynd.com', phone:'+91-9876500000',
              priority:'CC', notes:'Sample Fynd internal stakeholder — BCC on escalations',
              active:'Y' });
  ws.getRow(1).font = { bold:true, color:{argb:'FFFFFFFF'} };
  ws.getRow(1).fill = { type:'pattern', pattern:'solid', fgColor:{argb:'FF2C4A52'} };
  ws.views = [{state:'frozen', ySplit:1}];
  // Type dropdown (col A)
  ws.dataValidations.add('A2:A1000', {
    type:'list', allowBlank:false, formulae:['"Customer,Internal"']
  });
  // Priority dropdown (col G)
  ws.dataValidations.add('G2:G1000', {
    type:'list', allowBlank:true, formulae:['"Primary,CC,Escalation"']
  });
  // Active dropdown (col I)
  ws.dataValidations.add('I2:I1000', {
    type:'list', allowBlank:true, formulae:['"Y,N"']
  });
  wb.xlsx.writeBuffer().then(buf => {
    const blob = new Blob([buf], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `Contacts_and_Stakeholders_Template.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  });
}

// -----------------------------------------------------------------------------
// One-TIME migration from the legacy Customer_Contacts sheet.
//
// Calls the deployed Apps Script route action=pocMigrateFromContacts, which
// walks Customer_Contacts and upserts:
//   • To emails      → Customer_POCs (Priority=Primary)
//   • CC emails      → Customer_POCs (Priority=CC)  — except…
//   • @gofynd.com CC → Internal_Stakeholders (Priority=CC)  ← Fynd owners
//
// This is a ONE-TIME activity — the backend locks itself after the first
// successful run via a Script Properties marker. The UI reflects that state
// by disabling the button and labeling it with the completed timestamp.
// (Re-runs are still possible from the Apps Script editor by calling
// migrateContactsToPOCs() directly if a genuine re-import is ever needed.)
// -----------------------------------------------------------------------------
const pocMigrateState = { done: false, completedAt: '', completedBy: '' };

function _pocMigrateApplyLock(){
  const btn = document.getElementById('pocMigrateBtn');
  if (!btn) return;
  if (pocMigrateState.done){
    btn.disabled = true;
    btn.style.opacity = '0.65';
    btn.style.cursor = 'not-allowed';
    const when = pocMigrateState.completedAt || '';
    btn.textContent = '✓ Migrated' + (when ? (' · ' + when.slice(0, 10)) : '');
    btn.title = 'Legacy Customer_Contacts migration completed'
      + (when ? (' on ' + when) : '')
      + (pocMigrateState.completedBy ? (' by ' + pocMigrateState.completedBy) : '')
      + '. One-time activity — cannot be re-run from the UI.';
  } else {
    btn.disabled = false;
    btn.style.opacity = '';
    btn.style.cursor = '';
    btn.textContent = '🔁 Migrate legacy';
    btn.title = 'Import legacy Customer_Contacts rows from the sheet (one-time). @gofynd.com CCs route to Internal Stakeholders.';
  }
}

async function pocRefreshMigrateState(){
  try {
    const res = await _fuJsonp('pocMigrateStatus', {});
    if (res && res.ok){
      pocMigrateState.done        = Boolean(res.done);
      pocMigrateState.completedAt = String(res.completedAt || '');
      pocMigrateState.completedBy = String(res.completedBy || '');
    }
  } catch(_){ /* soft-fail: leave button enabled if status route is unreachable */ }
  _pocMigrateApplyLock();
}

async function pocMigrateLegacy(){
  const btn = document.getElementById('pocMigrateBtn');
  const bar = document.getElementById('pocStatusBar');
  // Hard client-side guard — even if someone force-enables the button,
  // refuse to hit the backend once the marker is set.
  if (pocMigrateState.done){
    alert('Legacy migration has already been completed'
      + (pocMigrateState.completedAt ? (' on ' + pocMigrateState.completedAt) : '')
      + '. This is a one-time activity.');
    return;
  }
  const ok = confirm(
    'Import contacts from the legacy Customer_Contacts sheet?\n\n' +
    '• To addresses  → Customer POCs (Primary)\n' +
    '• CC addresses  → Customer POCs (CC)\n' +
    '• @gofynd.com CCs → Internal Stakeholders (CC)\n\n' +
    'This is a ONE-TIME activity — the button will lock after a successful run.'
  );
  if (!ok) return;
  if (btn){ btn.disabled = true; btn.textContent = '⏳ Migrating…'; }
  if (bar) bar.innerHTML = '<span style="color:#64748b">Migrating legacy Customer_Contacts… (this can take a few minutes on large sheets)</span>';
  try {
    // Bulk migration reads/writes both Customer_POCs + Internal_Stakeholders
    // in a batched pass, but on very large legacy tabs it can still take a
    // couple of minutes end-to-end. Bump the client-side timeout well past
    // the default 60 s so the UI doesn't reject a still-running run.
    const res = await _fuJsonp('pocMigrateFromContacts', {}, 300000);
    if (!res || res.ok === false){
      const msg = (res && res.error) ? res.error : 'Migration failed';
      if (bar) bar.innerHTML = '<span style="color:#b91c1c">Migration failed: ' + _pocEsc(msg) + '</span>';
      alert('Migration failed: ' + msg);
      // If the backend already had the marker set, respect it in the UI too.
      if (res && res.alreadyMigrated){
        pocMigrateState.done = true;
        pocMigrateState.completedAt = String(res.completedAt || '');
        pocMigrateState.completedBy = String(res.completedBy || '');
      }
      return;
    }
    const m = res.migrated || {};
    const total   = Number(m.total    || 0);
    const ins     = Number(m.inserts  || 0);
    const upd     = Number(m.updates  || 0);
    const skp     = Number(m.skipped  || 0);
    const err     = Number(m.errors   || 0);
    const pocIns  = Number(m.pocInserts || 0);
    const pocUpd  = Number(m.pocUpdates || 0);
    const isIns   = Number(m.isInserts  || 0);
    const isUpd   = Number(m.isUpdates  || 0);
    const parts = [
      '<span style="color:#0d9488;font-weight:600">✓ Migration complete.</span>',
      total + ' rows scanned',
      ins + ' inserted',
      upd + ' updated',
      skp + ' skipped',
      err ? ('<span style="color:#b91c1c">' + err + ' errors</span>') : ''
    ].filter(Boolean);
    const breakdown = '<div class="text-[11px] text-slate-500">Customer POCs — ' +
      pocIns + ' inserted, ' + pocUpd + ' updated · Internal Stakeholders — ' +
      isIns + ' inserted, ' + isUpd + ' updated</div>';
    if (bar) bar.innerHTML = parts.join(' · ') + breakdown;
    alert(
      'Migration complete.\n' +
      'Rows scanned: ' + total + '\n' +
      'Customer POCs — inserted: ' + pocIns + ', updated: ' + pocUpd + '\n' +
      'Internal Stakeholders — inserted: ' + isIns + ', updated: ' + isUpd + '\n' +
      'Skipped: ' + skp + '  ·  Errors: ' + err +
      '\n\nThe migration button is now locked (one-time activity).'
    );
    pocMigrateState.done = true;
    pocMigrateState.completedAt = String(res.completedAt || _pocNowIsoClient());
    pocMigrateState.completedBy = String(res.completedBy || '');
    await pocLoad();
  } catch(ex) {
    const msg = (ex && ex.message) || String(ex);
    if (bar) bar.innerHTML = '<span style="color:#b91c1c">Migration error: ' + _pocEsc(msg) + '</span>';
    alert('Migration error: ' + msg);
  } finally {
    _pocMigrateApplyLock();
  }
}

function _pocNowIsoClient(){
  try { return new Date().toISOString(); } catch(_){ return ''; }
}

async function pocOnUpload(ev){
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  ev.target.value = '';   // allow re-uploading the same file
  if (typeof ExcelJS === 'undefined'){ alert('ExcelJS not loaded'); return; }
  const bar = document.getElementById('pocStatusBar');
  if (bar) bar.innerHTML = '<span style="color:#64748b">Parsing Excel…</span>';
  try{
    const buf = await file.arrayBuffer();
    const wb = new ExcelJS.Workbook();
    await wb.xlsx.load(buf);
    const ws = wb.worksheets[0];
    if (!ws){ if (bar) bar.innerHTML = '<span style="color:#b91c1c">No sheet found in workbook.</span>'; return; }
    const headers = ws.getRow(1).values.slice(1).map(v => String(v||'').trim().toLowerCase());
    // Accept the unified slim template AND the legacy wide template so folks
    // uploading an older file still get through. "Type" and "Stakeholder Name"
    // are new; "Role" is optional (was removed from the modal). "Contact
    // Name" and "Stakeholder Name" are aliases — either resolves to contactName.
    const idx = {
      type:            headers.indexOf('type'),
      cid:             headers.indexOf('cid'),
      customerName:    headers.indexOf('customer name'),
      contactName:     headers.indexOf('contact name'),
      stakeholderName: headers.indexOf('stakeholder name'),
      role:            headers.indexOf('role'),
      email:           headers.indexOf('email'),
      phone:           headers.indexOf('phone'),
      priority:        headers.indexOf('priority'),
      active:          headers.indexOf('active'),
      notes:           headers.indexOf('notes')
    };
    if (idx.cid === -1 || idx.email === -1){
      if (bar) bar.innerHTML = '<span style="color:#b91c1c">Missing required columns: CID and Email must be present.</span>';
      return;
    }
    const custRows = [];
    const intRows  = [];
    ws.eachRow((row, rowNum) => {
      if (rowNum === 1) return;
      const vals = row.values.slice(1);
      const pick = k => idx[k] >= 0 ? String(vals[idx[k]] == null ? '' : vals[idx[k]]).trim() : '';
      const cid = pick('cid');
      const email = pick('email');
      if (!cid && !email) return;    // skip fully empty rows
      // Type resolution:
      //   • explicit "Internal" / "Customer" wins if provided
      //   • otherwise infer from email domain: @gofynd.com → Internal, else Customer
      //   • fallback: Customer
      const rawType = pick('type').toLowerCase();
      let kind;
      if (rawType === 'internal' || rawType === 'is' || rawType === 'stakeholder') kind = 'internal';
      else if (rawType === 'customer' || rawType === 'poc' || rawType === 'contact') kind = 'customer';
      else if (/@gofynd\.com$/i.test(email)) kind = 'internal';
      else kind = 'customer';
      // "Stakeholder Name" and "Contact Name" both feed the same slot on the
      // backend — the receiving route reads either alias.
      const contactName = pick('contactName') || pick('stakeholderName');
      const rec = {
        cid, email,
        customerName: pick('customerName'),
        contactName:  contactName,
        role:         pick('role'),
        phone:        pick('phone'),
        priority:     pick('priority') || 'Primary',
        active:       (pick('active') || 'Y').toUpperCase() === 'N' ? 'N' : 'Y',
        notes:        pick('notes')
      };
      if (kind === 'internal') {
        rec.stakeholderName = contactName;
        intRows.push(rec);
      } else {
        custRows.push(rec);
      }
    });
    if (!custRows.length && !intRows.length){
      if (bar) bar.innerHTML = '<span style="color:#b91c1c">No data rows found in Excel.</span>';
      return;
    }
    pocState.bulk.rows = custRows;
    pocState.bulk.intRows = intRows;
    const totalCount = custRows.length + intRows.length;
    if (bar) bar.innerHTML = `<span style="color:#64748b">Validating ${totalCount} rows (${custRows.length} customer + ${intRows.length} internal)…</span>`;
    // Dry-run both sides in parallel so the preview covers every row.
    const [pocRes, isRes] = await Promise.all([
      custRows.length
        ? _fuPost('pocBulkImport', { rows: JSON.stringify(custRows), dryRun: '1' })
        : Promise.resolve({ ok: true, report: [], total: 0, inserts: 0, updates: 0, errors: 0 }),
      intRows.length
        ? _fuPost('isBulkImport', { rows: JSON.stringify(intRows), dryRun: '1' })
        : Promise.resolve({ ok: true, report: [], total: 0, inserts: 0, updates: 0, errors: 0 })
    ]);
    if (!pocRes || !pocRes.ok){
      if (bar) bar.innerHTML = '<span style="color:#b91c1c">Customer preview failed: ' + _pocExplainBadRes(pocRes, 'pocBulkImport') + '</span>';
      return;
    }
    if (!isRes || !isRes.ok){
      if (bar) bar.innerHTML = '<span style="color:#b91c1c">Internal-stakeholder preview failed: ' + _pocExplainBadRes(isRes, 'isBulkImport') + '</span>';
      return;
    }
    // Merge reports and tag each entry so the preview modal can show which
    // sheet a row would land in.
    const pocRep = (pocRes.report || []).map(r => Object.assign({}, r, { _target: 'customer' }));
    const isRep  = (isRes.report  || []).map(r => Object.assign({}, r, { _target: 'internal' }));
    pocState.bulk.report = pocRep.concat(isRep);
    pocState.bulk.summary = {
      total:   (pocRes.total   || 0) + (isRes.total   || 0),
      inserts: (pocRes.inserts || 0) + (isRes.inserts || 0),
      updates: (pocRes.updates || 0) + (isRes.updates || 0),
      errors:  (pocRes.errors  || 0) + (isRes.errors  || 0),
      pocTotal: pocRes.total   || 0,
      isTotal:  isRes.total    || 0
    };
    pocOpenPreviewModal();
    if (bar) bar.innerHTML = '';
  }catch(ex){
    if (bar) bar.innerHTML = '<span style="color:#b91c1c">Upload failed: ' + ((ex && ex.message) || String(ex)) + '</span>';
  }
}

function pocOpenPreviewModal(){
  const s = pocState.bulk.summary || {};
  const summaryEl = document.getElementById('pocPreviewSummary');
  const bodyEl = document.getElementById('pocPreviewBody');
  if (summaryEl){
    const split = (s.pocTotal || s.isTotal)
      ? ` <span class="text-slate-500">(${s.pocTotal||0} customer · ${s.isTotal||0} internal)</span>`
      : '';
    summaryEl.innerHTML = `Total <b>${s.total||0}</b>${split} · New <b style="color:#15803d">${s.inserts||0}</b> · Update <b style="color:#0369a1">${s.updates||0}</b> · <b style="color:#b91c1c">Errors ${s.errors||0}</b>`;
  }
  if (bodyEl){
    bodyEl.innerHTML = (pocState.bulk.report||[]).map(r => {
      const color = r.status === 'error' ? '#b91c1c' : (r.mode === 'insert' ? '#15803d' : '#0369a1');
      const label = r.status === 'error' ? ('Error: ' + r.error) : (r.mode || 'ok');
      const badgeStyle = r._target === 'internal'
        ? 'background:#fef3c7;color:#92400e'
        : 'background:#dbeafe;color:#1e40af';
      const badge = `<span class="rounded px-1.5 py-0.5 text-[10px] font-semibold" style="${badgeStyle}">${r._target === 'internal' ? '👥 Internal' : '📧 Customer'}</span>`;
      return `<tr class="border-t border-slate-100">
        <td class="px-2 py-1 font-mono">${r.line}</td>
        <td class="px-2 py-1">${badge}</td>
        <td class="px-2 py-1 font-mono">${_pocEsc(r.cid)}</td>
        <td class="px-2 py-1">${_pocEsc(r.email)}</td>
        <td class="px-2 py-1" style="color:${color};font-weight:600">${_pocEsc(r.mode||'')}</td>
        <td class="px-2 py-1" style="color:${color}">${_pocEsc(label)}</td>
      </tr>`;
    }).join('');
  }
  const commitBtn = document.getElementById('pocPreviewCommit');
  commitBtn.disabled = !(s.inserts || s.updates);
  document.getElementById('pocPreviewModal').style.display = 'flex';
}

function pocClosePreviewModal(){ document.getElementById('pocPreviewModal').style.display = 'none'; }

async function pocPreviewCommit(){
  const btn = document.getElementById('pocPreviewCommit');
  btn.disabled = true; btn.textContent = 'Saving…';
  try{
    // Commit BOTH sides — customer POCs and internal stakeholders — in
    // parallel so the sheet reflects every uploaded row.
    const custRows = pocState.bulk.rows || [];
    const intRows  = pocState.bulk.intRows || [];
    const [pocRes, isRes] = await Promise.all([
      custRows.length
        ? _fuPost('pocBulkImport', { rows: JSON.stringify(custRows) })
        : Promise.resolve({ ok: true }),
      intRows.length
        ? _fuPost('isBulkImport',  { rows: JSON.stringify(intRows) })
        : Promise.resolve({ ok: true })
    ]);
    if (!pocRes || !pocRes.ok){
      alert('Customer commit failed: ' + _pocExplainBadRes(pocRes, 'pocBulkImport').replace(/<[^>]+>/g,''));
      btn.disabled = false; btn.textContent = 'Commit to Sheet';
      return;
    }
    if (!isRes || !isRes.ok){
      alert('Internal-stakeholder commit failed: ' + _pocExplainBadRes(isRes, 'isBulkImport').replace(/<[^>]+>/g,''));
      btn.disabled = false; btn.textContent = 'Commit to Sheet';
      return;
    }
    pocClosePreviewModal();
    await pocLoad();
  }catch(ex){
    alert('Commit failed: ' + ((ex && ex.message) || String(ex)));
    btn.disabled = false; btn.textContent = 'Commit to Sheet';
  }
}

function wirePOCs(){
  const addBtn = document.getElementById('pocAddBtn');
  if (addBtn) addBtn.addEventListener('click', ()=> pocOpenModal(null));
  const dlBtn = document.getElementById('pocDownloadBtn');
  if (dlBtn) dlBtn.addEventListener('click', pocDownloadExcel);
  const tplBtn = document.getElementById('pocTemplateBtn');
  if (tplBtn) tplBtn.addEventListener('click', pocDownloadTemplate);
  const mgBtn = document.getElementById('pocMigrateBtn');
  if (mgBtn) mgBtn.addEventListener('click', pocMigrateLegacy);
  const rfBtn = document.getElementById('pocRefreshBtn');
  if (rfBtn) rfBtn.addEventListener('click', pocLoad);
  const upl = document.getElementById('pocUploadInput');
  if (upl) upl.addEventListener('change', pocOnUpload);
  ['pocSearch','pocFilterType','pocFilterPriority','pocFilterActive'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', pocApplyFilter);
    if (el) el.addEventListener('change', pocApplyFilter);
  });
  document.getElementById('pocModalClose')?.addEventListener('click', pocCloseModal);
  document.getElementById('pocModalCancel')?.addEventListener('click', pocCloseModal);
  document.getElementById('pocModalSave')?.addEventListener('click', pocSave);
  document.getElementById('pmAddEmailBtn')?.addEventListener('click', (ev)=>{ ev.preventDefault(); pocAddEmailRow(null, 'customer'); });
  document.getElementById('pmAddStakeBtn')?.addEventListener('click', (ev)=>{ ev.preventDefault(); pocAddEmailRow(null, 'internal'); });
  document.getElementById('pocPreviewClose')?.addEventListener('click', pocClosePreviewModal);
  document.getElementById('pocPreviewCancel')?.addEventListener('click', pocClosePreviewModal);
  document.getElementById('pocPreviewCommit')?.addEventListener('click', pocPreviewCommit);
  // Auto-fill customerName when a known CID is typed
  const pmCid = document.getElementById('pmCid');
  if (pmCid) pmCid.addEventListener('change', ()=>{
    const cid = (pmCid.value||'').trim();
    const hit = pocState.cidUniverse.find(c => c.cid === cid);
    const nameEl = document.getElementById('pmCustomerName');
    if (hit && nameEl && !nameEl.value) nameEl.value = hit.name || '';
  });
}

// =============================================================
// Internal Stakeholders — CRUD + Bulk Upload/Download
// Backed by tab Internal_Stakeholders. Consolidated view is BCC'd on
// every outgoing customer follow-up so leadership stays in the loop.
// =============================================================
const isState = {
  rows: [],             // list of {cid, customerName, stakeholderName, role, email, phone, priority, active, notes, updatedBy, updatedAt}
  filtered: [],
  cidUniverse: [],      // [{cid, name, region}]
  priorities: ['Primary','CC','Escalation'],
  editing: null,        // rec being edited, null when creating new
  bulk: { rows: [], report: [], summary: null },
  lastErr: ''
};

// Since the standalone Internal_Stakeholders table was merged into the
// unified "Contacts & Stakeholders" card, isLoad() is now a thin alias
// that delegates to pocLoad() — which fetches BOTH data sources and
// keeps isState.rows / isState.cidUniverse in sync as a side effect.
// This preserves every existing caller (isSave, isDelete, external
// tests) without generating a second round-trip.
async function isLoad(){
  return pocLoad();
}

function _isFillCidDatalist(){
  const dl = document.getElementById('imCidList');
  if (!dl) return;
  dl.innerHTML = isState.cidUniverse.map(c => `<option value="${_pocEsc(c.cid)}">${_pocEsc(c.name||'')}${c.region ? ' — ' + _pocEsc(c.region) : ''}</option>`).join('');
}

function isApplyFilter(){
  const q = (document.getElementById('isSearch')?.value || '').trim().toLowerCase();
  const pri = document.getElementById('isFilterPriority')?.value || '';
  const act = document.getElementById('isFilterActive')?.value || '';
  isState.filtered = (isState.rows || []).filter(r => {
    if (pri && String(r.priority||'').toLowerCase() !== pri.toLowerCase()) return false;
    if (act === 'Y' && !r.active) return false;
    if (act === 'N' && r.active) return false;
    if (q){
      const hay = [r.cid, r.customerName, r.stakeholderName, r.email, r.phone, r.role, r.notes].map(x=>String(x||'').toLowerCase()).join(' | ');
      if (hay.indexOf(q) === -1) return false;
    }
    return true;
  });
  isRenderTable();
}

function isRenderTable(){
  const tbody = document.getElementById('isTbody');
  const countEl = document.getElementById('isCount');
  if (!tbody) return;
  if (!isState.filtered.length){
    tbody.innerHTML = '<tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">No stakeholders match the current filters.</td></tr>';
    if (countEl) countEl.textContent = `0 of ${isState.rows.length} shown`;
    return;
  }
  const rows = isState.filtered.map((r, i) => {
    const priColor = r.priority === 'Primary' ? '#0d9488' : (r.priority === 'CC' ? '#0369a1' : '#a16207');
    const activeBadge = r.active
      ? '<span style="color:#15803d;font-weight:600">✓</span>'
      : '<span style="color:#94a3b8">—</span>';
    return `<tr class="border-t border-slate-100" data-cid="${_pocEsc(r.cid)}" data-email="${_pocEsc(r.email)}">
      <td class="px-3 py-2 font-mono text-[11px]">${_pocEsc(r.cid)}</td>
      <td class="px-3 py-2">${_pocEsc(r.customerName||'')}</td>
      <td class="px-3 py-2">${_pocEsc(r.stakeholderName||'—')}</td>
      <td class="px-3 py-2 text-slate-500">${_pocEsc(r.role||'')}</td>
      <td class="px-3 py-2 text-[11px]">${_pocEsc(r.email||'')}</td>
      <td class="px-3 py-2 text-[11px]">${_pocEsc(r.phone||'')}</td>
      <td class="px-3 py-2" style="color:${priColor};font-weight:600">${_pocEsc(r.priority||'Primary')}</td>
      <td class="px-3 py-2 text-center">${activeBadge}</td>
      <td class="px-3 py-2 text-[11px] text-slate-500" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${_pocEsc(r.notes||'')}">${_pocEsc(r.notes||'')}</td>
      <td class="px-3 py-2 text-center whitespace-nowrap">
        <button class="chip is-edit" data-idx="${i}">✎</button>
        <button class="chip is-del" data-idx="${i}" style="color:#b91c1c">🗑</button>
      </td>
    </tr>`;
  }).join('');
  tbody.innerHTML = rows;
  if (countEl) countEl.textContent = `${isState.filtered.length} of ${isState.rows.length} shown`;
  tbody.querySelectorAll('.is-edit').forEach(btn => btn.addEventListener('click', ()=>{
    const rec = isState.filtered[Number(btn.dataset.idx)];
    if (rec) isOpenModal(rec);
  }));
  tbody.querySelectorAll('.is-del').forEach(btn => btn.addEventListener('click', ()=>{
    const rec = isState.filtered[Number(btn.dataset.idx)];
    if (rec) isDelete(rec);
  }));
}

// -------- multi-email modal helpers ----------------------------------------
function _imEmailRowsWrap(){ return document.getElementById('imEmailsWrap'); }
function isAddEmailRow(seed){
  const wrap = _imEmailRowsWrap();
  if (!wrap) return null;
  const tpl = document.getElementById('imEmailRowTpl');
  if (!tpl || !tpl.content) return null;
  const node = tpl.content.firstElementChild.cloneNode(true);
  const s = seed || {};
  node.dataset.originalEmail = (s.email || '').trim();
  node.querySelector('.im-email').value    = s.email || '';
  node.querySelector('.im-priority').value = s.priority || 'Primary';
  node.querySelector('.im-active').value   = s.active === false ? 'N' : (s.active === 'N' ? 'N' : 'Y');
  node.querySelector('.im-contact').value  = s.stakeholderName || '';
  node.querySelector('.im-role').value     = s.role || '';
  node.querySelector('.im-phone').value    = s.phone || '';
  node.querySelector('.im-notes').value    = s.notes || '';
  // If this row is an existing record being edited, lock the email field
  if (seed && seed.email) node.querySelector('.im-email').disabled = true;
  node.querySelector('.im-del-row').addEventListener('click', (ev)=>{
    ev.preventDefault();
    // Refuse to remove the last row — always keep at least one
    if (wrap.querySelectorAll('.im-email-row').length <= 1) return;
    node.remove();
  });
  wrap.appendChild(node);
  return node;
}
function _imCollectRows(){
  const wrap = _imEmailRowsWrap();
  if (!wrap) return [];
  const out = [];
  wrap.querySelectorAll('.im-email-row').forEach(row => {
    out.push({
      originalEmail:   row.dataset.originalEmail || '',
      email:          (row.querySelector('.im-email').value    || '').trim(),
      priority:        row.querySelector('.im-priority').value || 'Primary',
      active:          row.querySelector('.im-active').value   || 'Y',
      stakeholderName:(row.querySelector('.im-contact').value  || '').trim(),
      role:           (row.querySelector('.im-role').value     || '').trim(),
      phone:          (row.querySelector('.im-phone').value    || '').trim(),
      notes:          (row.querySelector('.im-notes').value    || '').trim()
    });
  });
  return out;
}

// Redirect: the standalone IS modal is retired — open the unified
// Add-Contact modal instead, pre-seeded with a stakeholder row. This is
// how the "one click adds both" experience works: no matter which table
// you invoke Add/Edit from, you land in the same combined form.
function isOpenModal(rec){
  isState.editing = rec || null;
  const seed = rec ? Object.assign({}, rec, { kind: 'internal' }) : null;
  if (seed && rec && rec.stakeholderName && !seed.contactName) seed.contactName = rec.stakeholderName;
  if (!rec) {
    // Fresh "Add" from the IS table → open unified modal with an EMPTY
    // customer section and one blank stakeholder row instead. We drive
    // this by opening the modal with no rec, then wiping the customer
    // seed row and adding a stakeholder row.
    pocOpenModal(null);
    const cWrap = _pmEmailRowsWrap(); if (cWrap) cWrap.innerHTML = '';
    pocAddEmailRow(null, 'internal');
    _pmSyncEmptyStates();
    document.getElementById('pocModalTitle').textContent = 'Add Stakeholder / Contact';
    return;
  }
  pocOpenModal(seed);
}

function isCloseModal(){ document.getElementById('isModal').style.display = 'none'; isState.editing = null; }

async function isSave(){
  const err = document.getElementById('imError');
  err.textContent = '';
  const cid          = (document.getElementById('imCid').value||'').trim();
  const customerName = (document.getElementById('imCustomerName').value||'').trim();
  if (!cid) { err.textContent = 'CID is required.'; return; }
  const rows = _imCollectRows();
  if (!rows.length) { err.textContent = 'Add at least one email.'; return; }
  const seen = new Set();
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    if (!r.email) { err.textContent = 'Row ' + (i+1) + ': email is required.'; return; }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(r.email)) { err.textContent = 'Row ' + (i+1) + ': invalid email "' + r.email + '".'; return; }
    const key = r.email.toLowerCase();
    if (seen.has(key)) { err.textContent = 'Duplicate email "' + r.email + '" in the form.'; return; }
    seen.add(key);
  }
  const btn = document.getElementById('isModalSave');
  btn.disabled = true; btn.textContent = 'Saving…';
  let failedRows = [];
  try {
    // Save each email row sequentially so the UI can surface per-row errors clearly.
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      const params = {
        cid, email: r.email,
        customerName,
        stakeholderName: r.stakeholderName,
        role:            r.role,
        phone:           r.phone,
        priority:        r.priority || 'Primary',
        active:          r.active || 'Y',
        notes:           r.notes
      };
      const res = await _fuJsonp('isSave', params);
      if (!res || !res.ok) {
        failedRows.push('Row ' + (i+1) + ' (' + r.email + '): ' + _pocExplainBadRes(res, 'isSave'));
      }
    }
    if (failedRows.length) {
      err.innerHTML = 'Save partially failed:<br>' + failedRows.join('<br>');
      return;
    }
    isCloseModal();
    await isLoad();
  } catch(ex) {
    err.textContent = 'Save failed: ' + ((ex && ex.message) || String(ex));
  } finally {
    btn.disabled = false; btn.textContent = 'Save Stakeholder';
  }
}

async function isDelete(rec){
  if (!rec) return;
  if (!confirm(`Delete stakeholder ${rec.email} (CID ${rec.cid})?`)) return;
  try{
    const res = await _fuJsonp('isDelete', { cid: rec.cid, email: rec.email });
    if (!res || !res.ok){ alert('Delete failed: ' + _pocExplainBadRes(res, 'isDelete').replace(/<[^>]+>/g,'')); return; }
    await isLoad();
  }catch(ex){
    alert('Delete failed: ' + ((ex && ex.message) || String(ex)));
  }
}

function isDownloadExcel(){
  if (typeof ExcelJS === 'undefined'){ alert('ExcelJS not loaded'); return; }
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('Internal Stakeholders');
  ws.columns = [
    {header:'CID',              key:'cid',             width:14},
    {header:'Customer Name',    key:'customerName',    width:32},
    {header:'Stakeholder Name', key:'stakeholderName', width:22},
    {header:'Role',             key:'role',            width:22},
    {header:'Email',            key:'email',           width:32},
    {header:'Phone',            key:'phone',           width:16},
    {header:'Priority',         key:'priority',        width:12},
    {header:'Active',           key:'active',          width:8},
    {header:'Notes',            key:'notes',           width:32},
    {header:'Updated By',       key:'updatedBy',       width:24},
    {header:'Updated At',       key:'updatedAt',       width:20}
  ];
  const src = isState.filtered.length ? isState.filtered : isState.rows;
  src.forEach(r => ws.addRow({
    cid: r.cid, customerName: r.customerName, stakeholderName: r.stakeholderName,
    role: r.role, email: r.email, phone: r.phone,
    priority: r.priority, active: r.active ? 'Y' : 'N',
    notes: r.notes, updatedBy: r.updatedBy, updatedAt: r.updatedAt
  }));
  ws.getRow(1).font = { bold:true, color:{argb:'FFFFFFFF'} };
  ws.getRow(1).fill = { type:'pattern', pattern:'solid', fgColor:{argb:'FF2C4A52'} };
  ws.views = [{state:'frozen', ySplit:1}];
  const today = new Date().toISOString().slice(0,10).replace(/-/g,'');
  wb.xlsx.writeBuffer().then(buf => {
    const blob = new Blob([buf], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `Internal_Stakeholders_${today}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  });
}

// After the Customer POC + Internal Stakeholder cards were merged into one
// "Contacts & Stakeholders" view, the standalone IS template is gone —
// there's only one unified template that carries a Type column. Redirect
// any lingering caller to the unified download so nobody gets a stale
// schema.
function isDownloadTemplate(){
  return pocDownloadTemplate();
}

async function isOnUpload(ev){
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  ev.target.value = '';   // allow re-uploading the same file
  if (typeof ExcelJS === 'undefined'){ alert('ExcelJS not loaded'); return; }
  const bar = document.getElementById('isStatusBar');
  if (bar) bar.innerHTML = '<span style="color:#64748b">Parsing Excel…</span>';
  try{
    const buf = await file.arrayBuffer();
    const wb = new ExcelJS.Workbook();
    await wb.xlsx.load(buf);
    const ws = wb.worksheets[0];
    if (!ws){ if (bar) bar.innerHTML = '<span style="color:#b91c1c">No sheet found in workbook.</span>'; return; }
    const headers = ws.getRow(1).values.slice(1).map(v => String(v||'').trim().toLowerCase());
    const idx = {
      cid:             headers.indexOf('cid'),
      customerName:    headers.indexOf('customer name'),
      stakeholderName: headers.indexOf('stakeholder name'),
      role:            headers.indexOf('role'),
      email:           headers.indexOf('email'),
      phone:           headers.indexOf('phone'),
      priority:        headers.indexOf('priority'),
      active:          headers.indexOf('active'),
      notes:           headers.indexOf('notes')
    };
    if (idx.cid === -1 || idx.email === -1){
      if (bar) bar.innerHTML = '<span style="color:#b91c1c">Missing required columns: CID and Email must be present.</span>';
      return;
    }
    const rows = [];
    ws.eachRow((row, rowNum) => {
      if (rowNum === 1) return;
      const vals = row.values.slice(1);
      const pick = k => idx[k] >= 0 ? String(vals[idx[k]] == null ? '' : vals[idx[k]]).trim() : '';
      const cid = pick('cid');
      const email = pick('email');
      if (!cid && !email) return;    // skip fully empty rows
      rows.push({
        cid, email,
        customerName:    pick('customerName'),
        stakeholderName: pick('stakeholderName'),
        role:            pick('role'),
        phone:           pick('phone'),
        priority:        pick('priority') || 'Primary',
        active:          (pick('active') || 'Y').toUpperCase() === 'N' ? 'N' : 'Y',
        notes:           pick('notes')
      });
    });
    if (!rows.length){
      if (bar) bar.innerHTML = '<span style="color:#b91c1c">No data rows found in Excel.</span>';
      return;
    }
    isState.bulk.rows = rows;
    if (bar) bar.innerHTML = `<span style="color:#64748b">Validating ${rows.length} rows…</span>`;
    // Dry-run to preview inserts/updates/errors — payload posted so large sheets work
    const res = await _fuPost('isBulkImport', { rows: JSON.stringify(rows), dryRun: '1' });
    if (!res || !res.ok){
      if (bar) bar.innerHTML = '<span style="color:#b91c1c">Preview failed: ' + _pocExplainBadRes(res, 'isBulkImport') + '</span>';
      return;
    }
    isState.bulk.report = res.report || [];
    isState.bulk.summary = { total: res.total, inserts: res.inserts, updates: res.updates, errors: res.errors };
    isOpenPreviewModal();
    if (bar) bar.innerHTML = '';
  }catch(ex){
    if (bar) bar.innerHTML = '<span style="color:#b91c1c">Upload failed: ' + ((ex && ex.message) || String(ex)) + '</span>';
  }
}

function isOpenPreviewModal(){
  const s = isState.bulk.summary || {};
  const summaryEl = document.getElementById('isPreviewSummary');
  const bodyEl = document.getElementById('isPreviewBody');
  if (summaryEl){
    summaryEl.innerHTML = `Total <b>${s.total||0}</b> · New <b style="color:#15803d">${s.inserts||0}</b> · Update <b style="color:#0369a1">${s.updates||0}</b> · <b style="color:#b91c1c">Errors ${s.errors||0}</b>`;
  }
  if (bodyEl){
    bodyEl.innerHTML = (isState.bulk.report||[]).map(r => {
      const color = r.status === 'error' ? '#b91c1c' : (r.mode === 'insert' ? '#15803d' : '#0369a1');
      const label = r.status === 'error' ? ('Error: ' + r.error) : (r.mode || 'ok');
      return `<tr class="border-t border-slate-100">
        <td class="px-2 py-1 font-mono">${r.line}</td>
        <td class="px-2 py-1 font-mono">${_pocEsc(r.cid)}</td>
        <td class="px-2 py-1">${_pocEsc(r.email)}</td>
        <td class="px-2 py-1" style="color:${color};font-weight:600">${_pocEsc(r.mode||'')}</td>
        <td class="px-2 py-1" style="color:${color}">${_pocEsc(label)}</td>
      </tr>`;
    }).join('');
  }
  const commitBtn = document.getElementById('isPreviewCommit');
  commitBtn.disabled = !(s.inserts || s.updates);
  document.getElementById('isPreviewModal').style.display = 'flex';
}

function isClosePreviewModal(){ document.getElementById('isPreviewModal').style.display = 'none'; }

async function isPreviewCommit(){
  const btn = document.getElementById('isPreviewCommit');
  btn.disabled = true; btn.textContent = 'Saving…';
  try{
    const res = await _fuPost('isBulkImport', { rows: JSON.stringify(isState.bulk.rows) });
    if (!res || !res.ok){
      alert('Commit failed: ' + _pocExplainBadRes(res, 'isBulkImport').replace(/<[^>]+>/g,''));
      btn.disabled = false; btn.textContent = 'Commit to Sheet';
      return;
    }
    isClosePreviewModal();
    await isLoad();
  }catch(ex){
    alert('Commit failed: ' + ((ex && ex.message) || String(ex)));
    btn.disabled = false; btn.textContent = 'Commit to Sheet';
  }
}

function wireIS(){
  const addBtn = document.getElementById('isAddBtn');
  if (addBtn) addBtn.addEventListener('click', ()=> isOpenModal(null));
  const dlBtn = document.getElementById('isDownloadBtn');
  if (dlBtn) dlBtn.addEventListener('click', isDownloadExcel);
  const tplBtn = document.getElementById('isTemplateBtn');
  if (tplBtn) tplBtn.addEventListener('click', isDownloadTemplate);
  const rfBtn = document.getElementById('isRefreshBtn');
  if (rfBtn) rfBtn.addEventListener('click', isLoad);
  const upl = document.getElementById('isUploadInput');
  if (upl) upl.addEventListener('change', isOnUpload);
  ['isSearch','isFilterPriority','isFilterActive'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', isApplyFilter);
    if (el) el.addEventListener('change', isApplyFilter);
  });
  document.getElementById('isModalClose')?.addEventListener('click', isCloseModal);
  document.getElementById('isModalCancel')?.addEventListener('click', isCloseModal);
  document.getElementById('isModalSave')?.addEventListener('click', isSave);
  document.getElementById('imAddEmailBtn')?.addEventListener('click', (ev)=>{ ev.preventDefault(); isAddEmailRow(null); });
  document.getElementById('isPreviewClose')?.addEventListener('click', isClosePreviewModal);
  document.getElementById('isPreviewCancel')?.addEventListener('click', isClosePreviewModal);
  document.getElementById('isPreviewCommit')?.addEventListener('click', isPreviewCommit);
  // Auto-fill customerName when a known CID is typed
  const imCid = document.getElementById('imCid');
  if (imCid) imCid.addEventListener('change', ()=>{
    const cid = (imCid.value||'').trim();
    const hit = isState.cidUniverse.find(c => c.cid === cid);
    const nameEl = document.getElementById('imCustomerName');
    if (hit && nameEl && !nameEl.value) nameEl.value = hit.name || '';
  });
}

// =============================================================
// Workflows — scheduled follow-up rules
// =============================================================
const wfState = {
  rows: [],
  queue: [],
  regions: [],
  templates: [],
  editing: null,
  tab: 'rules',
  lastErr: ''
};

async function wfLoad(){
  const tbody = document.getElementById('wfTbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>';
  try{
    const res = await _fuJsonp('wfList', {});
    if (!res || !res.ok){
      wfState.lastErr = _pocExplainBadRes(res, 'wfList');
      if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="px-3 py-6 text-center" style="color:#b91c1c">${wfState.lastErr}</td></tr>`;
      return;
    }
    wfState.lastErr = '';
    wfState.rows = res.rows || [];
    wfState.regions = res.regions || [];
    wfState.templates = res.templates || [];
    wfRenderTable();
    _wfPopulateEditorDropdowns();
  }catch(ex){
    wfState.lastErr = (ex && ex.message) || String(ex);
    if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="px-3 py-6 text-center" style="color:#b91c1c">${wfState.lastErr}</td></tr>`;
  }
}

// Defensive client-side filter for Region option list: strip sheet error
// tokens (#N/A, #REF!, #VALUE!, etc.) and blanks so the dropdown never
// suggests "#N/A" as a bookable region. The backend also filters, but
// belt-and-braces since spreadsheets can regenerate errors any time.
function _wfIsErrorTokenClient(s){
  if (!s) return true;
  var t = String(s).trim();
  if (!t) return true;
  if (t.charAt(0) === '#') return true;   // #N/A, #REF!, #VALUE!, #NAME?, #DIV/0!, #NULL!
  var up = t.toUpperCase();
  return (up === 'N/A' || up === 'NA' || up === 'NULL' || up === 'UNDEFINED');
}

function _wfPopulateEditorDropdowns(){
  const reg = document.getElementById('wfRegion');
  if (reg){
    const cur = reg.value;
    const cleanRegions = (wfState.regions||[]).filter(r => !_wfIsErrorTokenClient(r));
    reg.innerHTML = '<option value="">All regions</option>' + cleanRegions.map(r => `<option value="${_pocEsc(r)}">${_pocEsc(r)}</option>`).join('');
    reg.value = cur;
  }
  const tpl = document.getElementById('wfTemplate');
  if (tpl){
    const cur = tpl.value;
    tpl.innerHTML = '<option value="">(Default outstanding statement)</option>' + (wfState.templates||[]).map(t => `<option value="${_pocEsc(t.id)}">${_pocEsc(t.name||t.id)}</option>`).join('');
    tpl.value = cur;
  }
}

function _wfTriggerLabel(wf){
  if (wf.triggerType === 'aging')    return `Aging ≥ ${wf.triggerValue} days`;
  if (wf.triggerType === 'cadence')  return `Every ${wf.triggerValue} days`;
  if (wf.triggerType === 'schedule') return `Schedule: ${wf.triggerValue}`;
  return String(wf.triggerType||'') + ' ' + String(wf.triggerValue||'');
}

function wfRenderTable(){
  const tbody = document.getElementById('wfTbody');
  const countEl = document.getElementById('wfCount');
  if (!tbody) return;
  if (!wfState.rows.length){
    tbody.innerHTML = '<tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">No workflows yet. Click <b>➕ New Workflow</b>.</td></tr>';
    if (countEl) countEl.textContent = '';
    return;
  }
  tbody.innerHTML = wfState.rows.map((r,i) => {
    const tplName = (wfState.templates.find(t => t.id === r.templateId) || {}).name || (r.templateId ? r.templateId : 'Default');
    // Resolve status: prefer new `status` field, fall back to legacy `active`.
    const st = String(r.status || (r.active ? 'active' : 'paused')).toLowerCase();
    let statusBadge;
    if (st === 'active')       statusBadge = '<span style="background:#dcfce7;color:#15803d;font-weight:600;padding:1px 6px;border-radius:9999px;font-size:10px">● Active</span>';
    else if (st === 'paused')  statusBadge = '<span style="background:#fef3c7;color:#a16207;font-weight:600;padding:1px 6px;border-radius:9999px;font-size:10px">⏸ Paused</span>';
    else                       statusBadge = '<span style="background:#e2e8f0;color:#475569;font-weight:600;padding:1px 6px;border-radius:9999px;font-size:10px">■ Stopped</span>';
    // Include Frequency and (if set) date range in the schedule cell so
    // admins can eyeball cadence + expiry from the list without opening
    // the editor.
    const freqLabel = String(r.frequency||'weekly').replace(/^./, c => c.toUpperCase());
    let winSummary = `${freqLabel} · ${r.windowStart||'10:00'}`;
    if (r.frequency === 'monthly' && r.dayOfMonth)         winSummary += ` · Day ${r.dayOfMonth}`;
    else if (r.windowDays)                                 winSummary += ` · ${r.windowDays}`;
    if (r.startDate || r.endDate){
      winSummary += ` · ${r.startDate||'…'}→${r.endDate||'∞'}`;
    }
    // Pause/Resume toggle: Active → pause icon, Paused/Stopped → play icon.
    const pauseBtn = (st === 'active')
      ? `<button class="chip wf-pause" data-idx="${i}" title="Pause this workflow">⏸</button>`
      : `<button class="chip wf-resume" data-idx="${i}" title="Resume workflow" style="color:#15803d">▶</button>`;
    return `<tr class="border-t border-slate-100" data-id="${_pocEsc(r.id)}">
      <td class="px-3 py-2 font-semibold text-slate-800">${_pocEsc(r.name)}</td>
      <td class="px-3 py-2">${_pocEsc(r.region||'All')}</td>
      <td class="px-3 py-2">${_pocEsc(_wfTriggerLabel(r))}</td>
      <td class="px-3 py-2 text-[11px]">${_pocEsc(tplName)}</td>
      <td class="px-3 py-2 text-[11px] text-slate-600">${_pocEsc(winSummary)}</td>
      <td class="px-3 py-2 text-right">${r.freqCapDays}d</td>
      <td class="px-3 py-2">${r.approveMode === 'review' ? '<span style="color:#a16207">Review</span>' : '<span style="color:#15803d">Auto</span>'}</td>
      <td class="px-3 py-2 text-center">${statusBadge}</td>
      <td class="px-3 py-2 text-[11px] text-slate-500">${_pocEsc((r.lastRunAt||'').slice(0,19).replace('T',' '))}</td>
      <td class="px-3 py-2 text-center whitespace-nowrap">
        <button class="chip wf-edit" data-idx="${i}" title="Edit">✎</button>
        ${pauseBtn}
        <button class="chip wf-test" data-idx="${i}" title="Test (dry-run — no emails sent)">🧪</button>
        <button class="chip wf-run" data-idx="${i}" title="Run now (ignores Status)">🚀</button>
        <button class="chip wf-del" data-idx="${i}" style="color:#b91c1c" title="Delete">🗑</button>
      </td>
    </tr>`;
  }).join('');
  if (countEl) countEl.textContent = `${wfState.rows.length} workflow${wfState.rows.length===1?'':'s'}`;
  tbody.querySelectorAll('.wf-edit').forEach(b => b.addEventListener('click', ()=> wfOpenModal(wfState.rows[Number(b.dataset.idx)])));
  tbody.querySelectorAll('.wf-run').forEach(b => b.addEventListener('click', ()=> wfRunNow(wfState.rows[Number(b.dataset.idx)])));
  tbody.querySelectorAll('.wf-del').forEach(b => b.addEventListener('click', ()=> wfDelete(wfState.rows[Number(b.dataset.idx)])));
  tbody.querySelectorAll('.wf-pause').forEach(b => b.addEventListener('click', ()=> wfSetStatus(wfState.rows[Number(b.dataset.idx)], 'paused')));
  tbody.querySelectorAll('.wf-resume').forEach(b => b.addEventListener('click', ()=> wfSetStatus(wfState.rows[Number(b.dataset.idx)], 'active')));
  tbody.querySelectorAll('.wf-test').forEach(b => b.addEventListener('click', ()=> wfTestWorkflow(wfState.rows[Number(b.dataset.idx)])));
}

// One-click Pause/Resume from the table — reuses wfSave under the hood so
// the backend applies the same validation as a full edit. We fetch the
// full record from wfState (already hydrated by wfLoad) and just flip the
// status field before saving.
async function wfSetStatus(rec, newStatus){
  if (!rec) return;
  const verb = newStatus === 'paused' ? 'Pause' : 'Resume';
  if (!confirm(`${verb} workflow "${rec.name}"?`)) return;
  try{
    const params = {
      id:            rec.id,
      name:          rec.name,
      region:        rec.region||'',
      triggerType:   rec.triggerType||'aging',
      triggerValue:  String(rec.triggerValue||''),
      templateId:    rec.templateId||'',
      freqCapDays:   String(rec.freqCapDays||7),
      frequency:     rec.frequency||'weekly',
      windowDays:    rec.windowDays||'',
      windowStart:   rec.windowStart||'10:00',
      windowEnd:     '',
      recipient:     rec.recipient||'primary+cc',
      custPriorities: rec.custPriorities||'Primary,CC',
      intPriorities:  rec.intPriorities||'Primary,CC',
      customerScope: rec.customerScope||'all',
      cidList:       rec.cidList||'',
      approveMode:   rec.approveMode||'auto',
      startDate:     rec.startDate||'',
      endDate:       rec.endDate||'',
      dayOfMonth:    String(rec.dayOfMonth||''),
      status:        newStatus,
      active:       (newStatus === 'active') ? 'Y' : 'N'
    };
    const res = await _fuJsonp('wfSave', params);
    if (!res || !res.ok){ alert(verb + ' failed: ' + _pocExplainBadRes(res, 'wfSave').replace(/<[^>]+>/g,'')); return; }
    await wfLoad();
  }catch(ex){
    alert(verb + ' failed: ' + ((ex && ex.message) || String(ex)));
  }
}

function wfOpenModal(rec){
  wfState.editing = rec || null;
  document.getElementById('wfModalTitle').textContent = rec ? 'Edit Workflow' : 'New Workflow';
  document.getElementById('wfId').value = rec ? rec.id : '';
  document.getElementById('wfName').value = rec ? (rec.name||'') : '';
  document.getElementById('wfRegion').value = rec ? (rec.region||'') : '';
  document.getElementById('wfTriggerType').value = rec ? (rec.triggerType||'aging') : 'aging';
  document.getElementById('wfTriggerValue').value = rec ? (rec.triggerValue||'30') : '30';
  document.getElementById('wfTemplate').value = rec ? (rec.templateId||'') : '';
  document.getElementById('wfFreqCap').value = rec ? (rec.freqCapDays||7) : 7;
  document.getElementById('wfFrequency').value = rec ? (rec.frequency||'weekly') : 'weekly';
  // Days-of-week checkboxes — hydrate from either the new `windowDays`
  // CSV string or an existing rec. Default: Mon–Fri checked.
  const daysCsv = rec ? (rec.windowDays || 'Mon,Tue,Wed,Thu,Fri') : 'Mon,Tue,Wed,Thu,Fri';
  const dayset = new Set(String(daysCsv).split(/[,\s]+/).map(s => s.trim()).filter(Boolean));
  document.querySelectorAll('#wfDaysChecks .wf-day').forEach(cb => {
    cb.checked = dayset.has(cb.dataset.day);
  });
  document.getElementById('wfWindowStart').value = rec ? (rec.windowStart||'10:00') : '10:00';
  // Day of month (Monthly frequency) — default 1st of the month.
  document.getElementById('wfDayOfMonth').value = rec && rec.dayOfMonth ? rec.dayOfMonth : (rec ? '' : 1);
  // Start / End date fences — hydrate from rec, blank on new (no expiry).
  document.getElementById('wfStartDate').value = rec ? (rec.startDate||'') : '';
  document.getElementById('wfEndDate').value   = rec ? (rec.endDate||'')   : '';
  // Customer-recipient priorities — hydrate from rec.custPriorities (CSV)
  // OR fall back to legacy rec.recipient (primary/primary+cc/…) mapping.
  const custCsv = rec && rec.custPriorities
    ? rec.custPriorities
    : _wfLegacyRecipientToCsv(rec ? rec.recipient : 'primary+cc');
  const custSet = new Set(String(custCsv||'').split(/[,\s]+/).map(s => s.trim()).filter(Boolean));
  document.querySelectorAll('.wf-cust-pri').forEach(cb => { cb.checked = custSet.has(cb.dataset.pri); });
  // Internal-stakeholder priorities — default Primary + CC BCC'd on every
  // send; Escalation only when the send is escalation-stage.
  const intCsv = rec && rec.intPriorities ? rec.intPriorities : 'Primary,CC';
  const intSet = new Set(String(intCsv||'').split(/[,\s]+/).map(s => s.trim()).filter(Boolean));
  document.querySelectorAll('.wf-int-pri').forEach(cb => { cb.checked = intSet.has(cb.dataset.pri); });
  document.getElementById('wfApproveMode').value = rec ? (rec.approveMode||'auto') : 'auto';
  // Status dropdown — hydrate from `status` field, fall back to legacy
  // `active` boolean (Active checkbox removed).
  const stat = rec ? (rec.status || (rec.active ? 'active' : 'paused')) : 'active';
  document.getElementById('wfStatus').value = String(stat).toLowerCase();
  // Customer-scope limiter — allow-list / deny-list / all
  const scope = rec ? (rec.customerScope || 'all') : 'all';
  document.getElementById('wfCustomerScope').value = scope;
  document.getElementById('wfCidList').value = rec ? (rec.cidList||'') : '';
  wfToggleCidWrap();
  wfToggleFrequencyUI();
  document.getElementById('wfPreviewBox').style.display = 'none';
  document.getElementById('wfPreviewBox').innerHTML = '';
  document.getElementById('wfError').textContent = '';
  wfUpdateTriggerValueLabel();
  document.getElementById('wfModal').style.display = 'flex';
}

// Legacy `recipient` values on old workflow rows → new CSV priority list.
function _wfLegacyRecipientToCsv(r){
  switch (String(r||'primary+cc').toLowerCase()){
    case 'primary':      return 'Primary';
    case 'escalation':   return 'Escalation';
    case 'all':          return 'Primary,CC,Escalation';
    case 'primary+cc':
    default:             return 'Primary,CC';
  }
}

// Hide the CID textarea unless the scope selector is include/exclude.
function wfToggleCidWrap(){
  const scope = document.getElementById('wfCustomerScope')?.value || 'all';
  const wrap = document.getElementById('wfCidWrap');
  if (wrap) wrap.style.display = (scope === 'all') ? 'none' : '';
}

// Show / hide the cadence-specific sub-panels based on Frequency selection:
//   Daily    → no extra picker (fires every day at Start Time)
//   Weekly   → day-of-week checkboxes
//   Monthly  → day-of-month number input
//   Custom   → day-of-week checkboxes + REQUIRED Start/End date range
// Start/End Date fences stay visible for every frequency (used as optional
// expiry). For Custom they become required and the labels are updated.
function wfToggleFrequencyUI(){
  const freq = document.getElementById('wfFrequency')?.value || 'weekly';
  const daysWrap  = document.getElementById('wfDaysWrap');
  const monthWrap = document.getElementById('wfMonthWrap');
  const dateWrap  = document.getElementById('wfDateRangeWrap');
  const startReq  = document.getElementById('wfStartDateReq');
  const endReq    = document.getElementById('wfEndDateReq');
  // Days of week — show for Weekly + Custom
  if (daysWrap)  daysWrap.style.display  = (freq === 'weekly' || freq === 'custom') ? '' : 'none';
  // Day of month — show for Monthly only
  if (monthWrap) monthWrap.style.display = (freq === 'monthly') ? '' : 'none';
  // Date range — always visible (optional expiry); required for Custom.
  if (dateWrap)  dateWrap.style.display  = '';
  if (startReq) startReq.textContent = (freq === 'custom') ? '(required)' : '(optional)';
  if (endReq)   endReq.textContent   = (freq === 'custom') ? '(required)' : '(optional — leave blank for no expiry)';
  if (startReq) startReq.className = (freq === 'custom') ? 'text-red-500 text-[10px]' : 'text-slate-400 text-[10px]';
  if (endReq)   endReq.className   = (freq === 'custom') ? 'text-red-500 text-[10px]' : 'text-slate-400 text-[10px]';
  const hint = document.getElementById('wfDaysHint');
  if (hint) {
    hint.textContent = ({
      daily:   'Fires every day at Start Time.',
      weekly:  'Fires on the checked weekdays at Start Time.',
      monthly: 'Fires once per month on the chosen day-of-month at Start Time.',
      custom:  'Fires on the checked weekdays within the Start/End date range.'
    })[freq] || '';
  }
}

// Kept as a compatibility alias so older event bindings + tests still work.
function wfToggleDaysWrap(){ return wfToggleFrequencyUI(); }

function wfCloseModal(){ document.getElementById('wfModal').style.display = 'none'; wfState.editing = null; }

function wfUpdateTriggerValueLabel(){
  const t = document.getElementById('wfTriggerType').value;
  const lbl = document.getElementById('wfTriggerValueLabel');
  const val = document.getElementById('wfTriggerValue');
  if (t === 'aging'){
    if (lbl) lbl.textContent = 'Days overdue (≥)';
    if (val && !val.value) val.value = '30';
  } else if (t === 'cadence'){
    if (lbl) lbl.textContent = 'Days between reminders';
    if (val && !val.value) val.value = '15';
  } else {
    if (lbl) lbl.textContent = 'Schedule tag (e.g. daily)';
    if (val && !val.value) val.value = 'daily';
  }
}

function _wfCollectParams(){
  // Collect selected day-of-week checkboxes into a CSV — this is what the
  // backend already understands via `windowDays`. Even when the day panel
  // is hidden (Daily / Monthly) we still emit the CSV so a later frequency
  // change doesn't lose the user's prior selection round-trip.
  const days = Array.from(document.querySelectorAll('#wfDaysChecks .wf-day'))
    .filter(cb => cb.checked)
    .map(cb => cb.dataset.day).join(',');
  const custPri = Array.from(document.querySelectorAll('.wf-cust-pri'))
    .filter(cb => cb.checked).map(cb => cb.dataset.pri).join(',');
  const intPri  = Array.from(document.querySelectorAll('.wf-int-pri'))
    .filter(cb => cb.checked).map(cb => cb.dataset.pri).join(',');
  // Derive legacy `recipient` from customer priorities so the backend
  // scheduler keeps working until it learns the new field names.
  let legacyRecipient = 'primary+cc';
  const cs = new Set(custPri.split(',').filter(Boolean));
  if (cs.has('Escalation') && !cs.has('Primary') && !cs.has('CC')) legacyRecipient = 'escalation';
  else if (cs.has('Primary') && cs.has('CC') && cs.has('Escalation')) legacyRecipient = 'all';
  else if (cs.has('Primary') && !cs.has('CC')) legacyRecipient = 'primary';
  else legacyRecipient = 'primary+cc';
  const status = document.getElementById('wfStatus').value || 'active';
  return {
    id:            document.getElementById('wfId').value,
    name:         (document.getElementById('wfName').value||'').trim(),
    region:        document.getElementById('wfRegion').value,
    triggerType:   document.getElementById('wfTriggerType').value,
    triggerValue: (document.getElementById('wfTriggerValue').value||'').trim(),
    templateId:    document.getElementById('wfTemplate').value,
    freqCapDays:   document.getElementById('wfFreqCap').value,
    frequency:     document.getElementById('wfFrequency').value,
    windowDays:    days,
    windowStart:  (document.getElementById('wfWindowStart').value||'').trim(),
    windowEnd:     '',   // End time is retired — kept in payload for backend compat.
    recipient:     legacyRecipient,
    custPriorities: custPri,
    intPriorities:  intPri,
    customerScope: document.getElementById('wfCustomerScope').value,
    cidList:      (document.getElementById('wfCidList').value||'').replace(/\s+/g,',').replace(/,+/g,',').replace(/^,|,$/g,''),
    approveMode:   document.getElementById('wfApproveMode').value,
    startDate:    (document.getElementById('wfStartDate').value||'').trim(),
    endDate:      (document.getElementById('wfEndDate').value||'').trim(),
    dayOfMonth:   (document.getElementById('wfDayOfMonth').value||'').toString().trim(),
    status:        status,
    // Retain legacy `active` flag so older backends + tests keep working.
    active:       (status === 'active') ? 'Y' : 'N'
  };
}

async function wfSave(){
  const err = document.getElementById('wfError');
  err.textContent = '';
  const params = _wfCollectParams();
  if (!params.name){ err.textContent = 'Name is required.'; return; }
  if (!params.triggerValue){ err.textContent = 'Trigger value is required.'; return; }
  // Frequency-specific client-side validation so users get instant
  // feedback before the JSONP round-trip.
  if (params.frequency === 'custom'){
    if (!params.startDate || !params.endDate){
      err.textContent = 'Custom frequency requires both a Start Date and an End Date.';
      return;
    }
  }
  if (params.frequency === 'monthly'){
    const dom = parseInt(params.dayOfMonth, 10);
    if (!(dom >= 1 && dom <= 31)){
      err.textContent = 'Monthly frequency requires Day of Month between 1 and 31.';
      return;
    }
  }
  if (params.startDate && params.endDate && params.startDate > params.endDate){
    err.textContent = 'End Date must be on or after Start Date.';
    return;
  }
  const btn = document.getElementById('wfModalSave');
  btn.disabled = true; btn.textContent = 'Saving…';
  try{
    const res = await _fuJsonp('wfSave', params);
    if (!res || !res.ok){ err.innerHTML = 'Save failed: ' + _pocExplainBadRes(res, 'wfSave'); return; }
    wfCloseModal();
    await wfLoad();
  }catch(ex){
    err.textContent = 'Save failed: ' + ((ex && ex.message) || String(ex));
  }finally{
    btn.disabled = false; btn.textContent = 'Save Workflow';
  }
}

async function wfDelete(rec){
  if (!rec) return;
  if (!confirm(`Delete workflow "${rec.name}"?`)) return;
  try{
    const res = await _fuJsonp('wfDelete', { id: rec.id });
    if (!res || !res.ok){ alert('Delete failed: ' + _pocExplainBadRes(res, 'wfDelete').replace(/<[^>]+>/g,'')); return; }
    await wfLoad();
  }catch(ex){
    alert('Delete failed: ' + ((ex && ex.message) || String(ex)));
  }
}

async function wfPreview(){
  const box = document.getElementById('wfPreviewBox');
  box.style.display = '';
  box.innerHTML = '<span style="color:#64748b">Evaluating…</span>';
  try{
    const params = _wfCollectParams();
    const res = await _fuJsonp('wfPreview', params);
    if (!res || !res.ok){ box.innerHTML = '<span style="color:#b91c1c">Preview failed: ' + _pocExplainBadRes(res, 'wfPreview') + '</span>'; return; }
    const rows = res.eligible || [];
    if (!rows.length){ box.innerHTML = '<span style="color:#64748b">No customers currently match this workflow.</span>'; return; }
    const list = rows.slice(0, 15).map(r =>
      `<tr><td class="px-1 font-mono text-[10px]">${_pocEsc(r.cid)}</td>` +
      `<td class="px-1">${_pocEsc(r.customer||'')}</td>` +
      `<td class="px-1 text-right">${r.openInv||0}</td>` +
      `<td class="px-1 text-right">${fuFmtINR(r.outstanding||0)}</td>` +
      `<td class="px-1 text-right">${r.oldestDays||0}d</td></tr>`).join('');
    const more = rows.length > 15 ? `<div class="text-[11px] text-slate-500 mt-1">+ ${rows.length - 15} more…</div>` : '';
    box.innerHTML = `<b>${rows.length}</b> customer${rows.length===1?'':'s'} eligible right now:<table class="w-full text-[11px] mt-1"><thead class="text-slate-500"><tr><th class="px-1 text-left">CID</th><th class="px-1 text-left">Customer</th><th class="px-1 text-right">Inv</th><th class="px-1 text-right">Outstanding</th><th class="px-1 text-right">Oldest</th></tr></thead><tbody>${list}</tbody></table>${more}`;
  }catch(ex){
    box.innerHTML = '<span style="color:#b91c1c">Preview failed: ' + ((ex && ex.message) || String(ex)) + '</span>';
  }
}

async function wfRunNow(rec){
  if (!rec) return;
  if (!confirm(`Run workflow "${rec.name}" now? Emails will be sent (or staged if approve=review).`)) return;
  try{
    const res = await _fuJsonp('wfRunNow', { id: rec.id });
    if (!res || !res.ok){ alert('Run failed: ' + _pocExplainBadRes(res, 'wfRunNow').replace(/<[^>]+>/g,'')); return; }
    alert(`Run complete — ${res.sent||0} sent, ${res.queued||0} queued, ${res.skipped||0} skipped, ${res.failed||0} failed.`);
    await wfLoad();
    if (wfState.tab === 'queue') await wfQueueLoad();
  }catch(ex){
    alert('Run failed: ' + ((ex && ex.message) || String(ex)));
  }
}

// Test-run modal state — holds the last fetched eligible list so the
// Export button can serialize it without a second server round-trip.
window.wfTestState = window.wfTestState || { workflow: null, rows: [], summary: null };

async function wfTestWorkflow(rec){
  if (!rec) return;
  const modal   = document.getElementById('wfTestModal');
  const tbody   = document.getElementById('wfTestTbody');
  const errEl   = document.getElementById('wfTestError');
  const statusEl= document.getElementById('wfTestStatus');
  const titleEl = document.getElementById('wfTestTitle');
  const kpiCust = document.getElementById('wfTestKpiCust');
  const kpiInv  = document.getElementById('wfTestKpiInv');
  const kpiAmt  = document.getElementById('wfTestKpiAmt');
  const kpiAge  = document.getElementById('wfTestKpiAge');
  if (!modal || !tbody) return;
  wfTestState.workflow = rec;
  wfTestState.rows = [];
  wfTestState.summary = null;
  titleEl.textContent = `Test Workflow — ${rec.name}`;
  errEl.textContent = '';
  statusEl.textContent = `Evaluating "${rec.name}" against today's AR data…`;
  kpiCust.textContent = kpiInv.textContent = kpiAmt.textContent = kpiAge.textContent = '…';
  tbody.innerHTML = '<tr><td colspan="8" class="px-3 py-6 text-center text-slate-500">Evaluating…</td></tr>';
  modal.style.display = 'flex';
  try{
    const res = await _fuJsonp('wfTest', { id: rec.id });
    if (!res || !res.ok){
      errEl.innerHTML = 'Test failed: ' + _pocExplainBadRes(res, 'wfTest');
      tbody.innerHTML = '<tr><td colspan="8" class="px-3 py-6 text-center text-red-600">Test failed — see error above.</td></tr>';
      statusEl.textContent = '';
      return;
    }
    const rows = res.eligible || [];
    const sum  = res.summary  || {};
    wfTestState.rows = rows;
    wfTestState.summary = sum;
    kpiCust.textContent = String(sum.customers || 0);
    kpiInv.textContent  = String(sum.openInv   || 0);
    kpiAmt.textContent  = fuFmtINR(sum.outstanding || 0);
    kpiAge.textContent  = (sum.oldestDays || 0) + 'd';
    if (!rows.length){
      tbody.innerHTML = '<tr><td colspan="8" class="px-3 py-6 text-center text-slate-500">✅ No customers currently match this workflow. Nothing would be sent.</td></tr>';
      statusEl.textContent = 'Dry-run complete — no emails would be sent right now.';
      return;
    }
    tbody.innerHTML = rows.map(r =>
      `<tr class="border-t border-slate-100">
        <td class="px-3 py-2 font-mono text-[11px]">${_pocEsc(r.cid||'')}</td>
        <td class="px-3 py-2">${_pocEsc(r.customer||'')}</td>
        <td class="px-3 py-2">${_pocEsc(r.region||'')}</td>
        <td class="px-3 py-2 text-right">${r.openInv||0}</td>
        <td class="px-3 py-2 text-right font-semibold">${fuFmtINR(r.outstanding||0)}</td>
        <td class="px-3 py-2 text-right">${r.oldestDays||0}</td>
        <td class="px-3 py-2 text-[11px] break-all">${_pocEsc(r.to||'')}</td>
        <td class="px-3 py-2 text-[11px] break-all">${_pocEsc(r.cc||'')}</td>
      </tr>`
    ).join('');
    statusEl.textContent = `Dry-run complete — ${rows.length} customer${rows.length===1?'':'s'} would receive this workflow now. Emails were NOT sent.`;
  }catch(ex){
    errEl.textContent = 'Test failed: ' + ((ex && ex.message) || String(ex));
    tbody.innerHTML = '<tr><td colspan="8" class="px-3 py-6 text-center text-red-600">Test failed — see error above.</td></tr>';
    statusEl.textContent = '';
  }
}

function wfTestCloseModal(){
  const m = document.getElementById('wfTestModal');
  if (m) m.style.display = 'none';
}

// Export the last dry-run result as an Excel file (using SheetJS if
// available, else CSV fallback). Keeps the export client-side so it
// works without another server round-trip.
async function wfTestExport(){
  const rows = (wfTestState && wfTestState.rows) || [];
  const wf   = (wfTestState && wfTestState.workflow) || {};
  if (!rows.length){ alert('Nothing to export — run the test first.'); return; }
  // Lazy-load XLSX (SheetJS) — the wf test export is a low-frequency action
  // and we don't want to pay the library cost on the initial dashboard paint.
  if (typeof XLSX === 'undefined' && typeof window.ensureXLSX === 'function') {
    try { await window.ensureXLSX(); } catch(_){}
  }
  const stamp = new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
  const safeName = String(wf.name || 'workflow').replace(/[^A-Za-z0-9_\-]+/g,'_');
  const fname = `WorkflowTest_${safeName}_${stamp}`;
  const header = ['CID','Customer','Region','Open Invoices','Outstanding (INR)','Oldest (days)','To','Cc'];
  const body = rows.map(r => [
    r.cid||'', r.customer||'', r.region||'',
    Number(r.openInv||0),
    Number(r.outstanding||0),
    Number(r.oldestDays||0),
    r.to||'', r.cc||''
  ]);
  const meta = [
    ['Workflow', wf.name||''],
    ['Region',   wf.region||'All'],
    ['Trigger',  (wf.triggerType||'') + ' ' + (wf.triggerValue||'')],
    ['Frequency', wf.frequency||''],
    ['Generated At', new Date().toISOString()],
    ['Note',     'Dry-run: NO emails were sent by this export.'],
    []
  ];
  try{
    if (typeof XLSX !== 'undefined' && XLSX && XLSX.utils){
      const wb = XLSX.utils.book_new();
      const aoa = meta.concat([header]).concat(body);
      const ws = XLSX.utils.aoa_to_sheet(aoa);
      // Column widths
      ws['!cols'] = [{wch:12},{wch:38},{wch:14},{wch:12},{wch:18},{wch:12},{wch:38},{wch:38}];
      XLSX.utils.book_append_sheet(wb, ws, 'Eligible Customers');
      XLSX.writeFile(wb, fname + '.xlsx');
      return;
    }
  }catch(ex){ /* fall through to CSV */ }
  // CSV fallback — quoted properly for commas/quotes/newlines.
  const quote = v => {
    const s = String(v == null ? '' : v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g,'""') + '"' : s;
  };
  const lines = [];
  meta.forEach(row => { if (row.length) lines.push(row.map(quote).join(',')); else lines.push(''); });
  lines.push(header.map(quote).join(','));
  body.forEach(row => lines.push(row.map(quote).join(',')));
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = fname + '.csv';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function wfQueueLoad(){
  const tbody = document.getElementById('wfQueueTbody');
  if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>';
  try{
    const res = await _fuJsonp('wfQueueList', {});
    if (!res || !res.ok){
      if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="px-3 py-6 text-center" style="color:#b91c1c">${_pocExplainBadRes(res, 'wfQueueList')}</td></tr>`;
      return;
    }
    wfState.queue = res.rows || [];
    wfRenderQueue();
  }catch(ex){
    if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="px-3 py-6 text-center" style="color:#b91c1c">${(ex && ex.message) || String(ex)}</td></tr>`;
  }
}

function wfRenderQueue(){
  const tbody = document.getElementById('wfQueueTbody');
  if (!tbody) return;
  if (!wfState.queue.length){
    tbody.innerHTML = '<tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">Empty queue.</td></tr>';
    return;
  }
  tbody.innerHTML = wfState.queue.map((r, i) => {
    const stColor = r.status === 'Sent' ? '#15803d' : (r.status === 'Failed' ? '#b91c1c' : '#a16207');
    const isPending = r.status === 'Pending';
    return `<tr class="border-t border-slate-100">
      <td class="px-3 py-2 text-[11px]">${_pocEsc(String(r.enqueuedAt||'').slice(0,19).replace('T',' '))}</td>
      <td class="px-3 py-2 text-[11px]">${_pocEsc(r.workflow)}</td>
      <td class="px-3 py-2 font-mono text-[11px]">${_pocEsc(r.cid)}</td>
      <td class="px-3 py-2">${_pocEsc(r.customer||'')}</td>
      <td class="px-3 py-2">${_pocEsc(r.region||'')}</td>
      <td class="px-3 py-2 text-right">${r.openInv||0}</td>
      <td class="px-3 py-2 text-right">${fuFmtINR(r.outstanding||0)}</td>
      <td class="px-3 py-2 text-right">${r.oldestDays||0}d</td>
      <td class="px-3 py-2" style="color:${stColor};font-weight:600">${_pocEsc(r.status||'Pending')}${r.error ? ' · <span class="text-[10px]" style="color:#7c2d12">'+_pocEsc(r.error)+'</span>' : ''}</td>
      <td class="px-3 py-2 text-center whitespace-nowrap">
        ${isPending ? `<button class="chip wfq-approve" data-idx="${i}">✔ Send</button>` : ''}
        <button class="chip wfq-del" data-idx="${i}" style="color:#b91c1c">🗑</button>
      </td>
    </tr>`;
  }).join('');
  tbody.querySelectorAll('.wfq-approve').forEach(b => b.addEventListener('click', ()=> wfQueueApprove(wfState.queue[Number(b.dataset.idx)])));
  tbody.querySelectorAll('.wfq-del').forEach(b => b.addEventListener('click', ()=> wfQueueDelete(wfState.queue[Number(b.dataset.idx)])));
}

async function wfQueueApprove(rec){
  if (!rec) return;
  if (!confirm(`Approve & send email for ${rec.cid} — ${rec.customer}?`)) return;
  try{
    const res = await _fuJsonp('wfQueueApprove', { rowIndex: rec.rowIndex });
    if (!res || !res.ok){ alert('Send failed: ' + _pocExplainBadRes(res, 'wfQueueApprove').replace(/<[^>]+>/g,'')); return; }
    await wfQueueLoad();
  }catch(ex){
    alert('Send failed: ' + ((ex && ex.message) || String(ex)));
  }
}

async function wfQueueDelete(rec){
  if (!rec) return;
  if (!confirm(`Remove this row from the draft queue?`)) return;
  try{
    const res = await _fuJsonp('wfQueueDelete', { rowIndex: rec.rowIndex });
    if (!res || !res.ok){ alert('Delete failed: ' + _pocExplainBadRes(res, 'wfQueueDelete').replace(/<[^>]+>/g,'')); return; }
    await wfQueueLoad();
  }catch(ex){
    alert('Delete failed: ' + ((ex && ex.message) || String(ex)));
  }
}

function wfSwitchTab(tab){
  wfState.tab = tab;
  document.querySelectorAll('[data-wf-tab]').forEach(b => b.classList.toggle('active', b.dataset.wfTab === tab));
  document.getElementById('wfPaneRules').style.display  = (tab === 'rules') ? '' : 'none';
  document.getElementById('wfPaneQueue').style.display  = (tab === 'queue') ? '' : 'none';
  if (tab === 'queue') wfQueueLoad();
}

function wireWorkflows(){
  document.getElementById('wfAddBtn')?.addEventListener('click', ()=> wfOpenModal(null));
  document.getElementById('wfRefreshBtn')?.addEventListener('click', ()=> { wfLoad(); if (wfState.tab === 'queue') wfQueueLoad(); });
  document.getElementById('wfModalClose')?.addEventListener('click', wfCloseModal);
  document.getElementById('wfModalCancel')?.addEventListener('click', wfCloseModal);
  document.getElementById('wfModalSave')?.addEventListener('click', wfSave);
  document.getElementById('wfPreviewBtn')?.addEventListener('click', wfPreview);
  document.getElementById('wfTriggerType')?.addEventListener('change', wfUpdateTriggerValueLabel);
  document.getElementById('wfFrequency')?.addEventListener('change', wfToggleFrequencyUI);
  document.getElementById('wfCustomerScope')?.addEventListener('change', wfToggleCidWrap);
  document.querySelectorAll('[data-wf-tab]').forEach(b => b.addEventListener('click', ()=> wfSwitchTab(b.dataset.wfTab)));
  // Test workflow modal
  document.getElementById('wfTestClose')?.addEventListener('click', wfTestCloseModal);
  document.getElementById('wfTestCancel')?.addEventListener('click', wfTestCloseModal);
  document.getElementById('wfTestExportBtn')?.addEventListener('click', wfTestExport);
}

// ===== Activity Log module =====
async function loadActivityLog(){
  const from = document.getElementById('alFrom').value;
  const to   = document.getElementById('alTo').value;
  const tbody = document.getElementById('alTbody');
  tbody.innerHTML = '<tr><td colspan="8" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>';
  try{
    const res = await _fuJsonp('activityLog', {from, to});
    if(!res || !res.ok){
      let m;
      if (res && res.error) m = res.error;
      else if (res && (res.ar || res.counts || res.tabsFound)) m = 'The deployed Apps Script does not recognise <code>action=activityLog</code> — please redeploy the updated code.gs as a <b>new Web App version</b>.';
      else m = 'Backend did not return a success response.';
      tbody.innerHTML = `<tr><td colspan="8" class="px-3 py-6 text-center" style="color:#b91c1c">${m}</td></tr>`;
      return;
    }
    const rows = res.rows || [];
    const s = res.summary || {};
    document.getElementById('alK1').textContent = s.total||0;
    document.getElementById('alK2').textContent = s.sent||0;
    document.getElementById('alK3').textContent = s.failed||0;
    document.getElementById('alK4').textContent = s.uniqueCustomers||0;
    document.getElementById('alK5').textContent = fuFmtINR(s.totalOs||0);
    if(!rows.length){ tbody.innerHTML = '<tr><td colspan="10" class="px-3 py-6 text-center text-slate-500">No activity in range.</td></tr>'; }
    else {
      const esc = (s)=> String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      tbody.innerHTML = rows.slice().reverse().map(r => {
        const st = String(r['Status']||'').toLowerCase();
        const color = st==='sent' ? '#15803d' : (st==='failed' ? '#b91c1c' : '#92400e');
        const err = r['Error'] || '';
        return `<tr class="border-t border-slate-100">
          <td class="px-3 py-2 text-[11px]">${String(r['Timestamp']||'').replace('T',' ').slice(0,19)}</td>
          <td class="px-3 py-2 font-mono text-[11px]">${r['CID']||''}</td>
          <td class="px-3 py-2">${r['Customer']||''}</td>
          <td class="px-3 py-2">${r['BU']||''}</td>
          <td class="px-3 py-2 text-[11px]">${r['To']||''}</td>
          <td class="px-3 py-2 text-[11px]">${r['Sender']||''}</td>
          <td class="px-3 py-2 text-right">${r['Invoice Count']||0}</td>
          <td class="px-3 py-2 text-right">${fuFmtINR(r['Outstanding Total']||0)}</td>
          <td class="px-3 py-2" style="color:${color};font-weight:600">${r['Status']||''}</td>
          <td class="px-3 py-2 text-[11px]" style="max-width:340px;word-break:break-word;color:#7c2d12">${esc(err)}</td>
        </tr>`;
      }).join('');
    }
    // Per-month breakdown
    const mt = document.getElementById('alMonthlyTable');
    const months = Object.keys(s.monthly||{}).sort().reverse();
    if(months.length){
      mt.innerHTML = `<table class="w-full border border-slate-200 rounded text-[11px]">
        <thead class="bg-slate-50"><tr><th class="px-2 py-1 text-left">Month</th><th class="px-2 py-1 text-right">Sends</th><th class="px-2 py-1 text-right">Customers</th><th class="px-2 py-1 text-right">Outstanding</th></tr></thead>
        <tbody>${months.map(m=>{const x=s.monthly[m];return `<tr class="border-t border-slate-100"><td class="px-2 py-1 font-mono">${m}</td><td class="px-2 py-1 text-right">${x.sends}</td><td class="px-2 py-1 text-right">${x.uniqueCustomers}</td><td class="px-2 py-1 text-right">${fuFmtINR(x.outstanding)}</td></tr>`;}).join('')}</tbody></table>`;
    } else { mt.innerHTML = '<div class="text-slate-500 text-[11px]">No monthly data yet.</div>'; }
  }catch(err){
    tbody.innerHTML = `<tr><td colspan="10" class="px-3 py-6 text-center" style="color:#b91c1c">${err.message}</td></tr>`;
  }
}

async function generateMonthlyReportXls(){
  const ym = document.getElementById('alMonth').value;
  if(!ym){ alert('Pick a month first'); return; }
  const out = document.getElementById('alMonthlyOut');
  out.innerHTML = 'Building report for ' + ym + '…';
  try{
    const res = await _fuJsonp('monthlyReport', {month: ym});
    if(!res || !res.ok){
      let m;
      if (res && res.error) m = res.error;
      else if (res && (res.ar || res.counts || res.tabsFound)) m = 'The deployed Apps Script does not recognise <code>action=monthlyReport</code> — please redeploy the updated code.gs as a <b>new Web App version</b>.';
      else m = 'Backend did not return a success response.';
      out.innerHTML = '<span style="color:#b91c1c">'+m+'</span>';
      return;
    }
    const r = res.report;
    if(typeof ExcelJS === 'undefined'){ out.innerHTML = '<span style="color:#b91c1c">ExcelJS not loaded</span>'; return; }
    const wb = new ExcelJS.Workbook();
    // Summary sheet
    const s1 = wb.addWorksheet('Summary');
    s1.addRow(['Fynd · Follow-up Activity — Monthly Report']);
    s1.getRow(1).font = {bold:true, size:14, color:{argb:'FF2C4A52'}};
    s1.addRow(['Month', ym]);
    s1.addRow(['Total Sends', r.totalSends]);
    s1.addRow(['Successful', r.sent]);
    s1.addRow(['Failed', r.failed]);
    s1.addRow(['Unique Customers', r.uniqueCustomers]);
    s1.addRow([]);
    s1.addRow(['Generated', new Date().toISOString().slice(0,19)]);
    s1.getColumn(1).width = 22; s1.getColumn(2).width = 28;
    // Per-customer sheet
    const s2 = wb.addWorksheet('Per Customer');
    s2.columns = [
      {header:'CID', key:'cid', width:12},
      {header:'Customer', key:'customer', width:30},
      {header:'BU', key:'bu', width:14},
      {header:'Sends', key:'sends', width:10},
      {header:'Last Sent', key:'lastSent', width:22},
      {header:'Outstanding (sum across sends)', key:'totalOs', width:28, style:{numFmt:'#,##0.00'}}
    ];
    r.perCustomer.forEach(c => s2.addRow(c));
    s2.getRow(1).font = {bold:true, color:{argb:'FFFFFFFF'}};
    s2.getRow(1).fill = {type:'pattern', pattern:'solid', fgColor:{argb:'FF2C4A52'}};
    s2.views = [{state:'frozen', ySplit:1}];
    // Detail rows sheet
    const s3 = wb.addWorksheet('All Sends');
    if(r.rows.length){
      s3.columns = Object.keys(r.rows[0]).map(k => ({header:k, key:k, width:18}));
      r.rows.forEach(row => s3.addRow(row));
      s3.getRow(1).font = {bold:true, color:{argb:'FFFFFFFF'}};
      s3.getRow(1).fill = {type:'pattern', pattern:'solid', fgColor:{argb:'FF2C4A52'}};
      s3.views = [{state:'frozen', ySplit:1}];
    }
    const buf = await wb.xlsx.writeBuffer();
    const blob = new Blob([buf], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = `Followup_Monthly_${ym}.xlsx`; a.click();
    URL.revokeObjectURL(a.href);
    out.innerHTML = `<span style="color:#15803d">✓ Report generated · ${r.totalSends} sends · ${r.uniqueCustomers} customers</span>`;
  }catch(err){ out.innerHTML = '<span style="color:#b91c1c">'+err.message+'</span>'; }
}

function wireActivityLog(){
  // Default range: this month
  const today = new Date();
  const first = new Date(today.getFullYear(), today.getMonth(), 1);
  document.getElementById('alFrom').value = first.toISOString().slice(0,10);
  document.getElementById('alTo').value = today.toISOString().slice(0,10);
  document.getElementById('alMonth').value = today.toISOString().slice(0,7);
  document.getElementById('alRefresh').addEventListener('click', loadActivityLog);
  document.getElementById('alGenMonth').addEventListener('click', generateMonthlyReportXls);

  // Worklist Activity (notes / follow-ups / P2P) panel — independent filters,
  // shares the same data source as the To-Do List daily report.
  wireWorklistActivity();

  // --- Tab switching: Email Sends ↔ Worklist Activity ---
  // Extensible: any new tab just needs data-al-tab="<key>" on the button and
  // a matching pane id of "alTabPane<KeyTitleCase>". Keep this loop simple so
  // adding a new tab in the future is a 4-line HTML edit, no JS changes.
  const _alTabPanes = {
    'email':    'alTabPaneEmail',
    'worklist': 'alTabPaneWorklist'
  };
  document.querySelectorAll('#alTabBar [data-al-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-al-tab');
      // Toggle button states
      document.querySelectorAll('#alTabBar [data-al-tab]').forEach(b => {
        const on = (b === btn);
        b.classList.toggle('al-tab-active', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      // Toggle panes
      Object.keys(_alTabPanes).forEach(k => {
        const pane = document.getElementById(_alTabPanes[k]);
        if (pane) pane.style.display = (k === key) ? '' : 'none';
      });
      // Auto-load the freshly-shown tab if it hasn't been populated yet
      if (key === 'worklist') {
        try {
          const tb = document.getElementById('walTbody');
          if (tb && tb.querySelector('td.text-center') && typeof loadWorklistActivity === 'function') {
            loadWorklistActivity();
          }
        } catch(_){}
      } else if (key === 'email') {
        try {
          const tb = document.getElementById('alTbody');
          if (tb && tb.querySelector('td.text-center') && typeof loadActivityLog === 'function') {
            loadActivityLog();
          }
        } catch(_){}
      }
    });
  });
}

// ============================================================================
// ===== Worklist Activity (notes / follow-ups / P2P) =========================
// Pulls per-note rows from the `dailyReport` action and surfaces them in the
// Activity Log section so the team can audit collector activity end-to-end
// and download a richly-formatted Excel for sharing / compliance.
//
// Client-side filtering: collector, outcome, free-text search. Range and
// custom from/to are forwarded to the server (server already supports them).
// ============================================================================
const walState = {
  rows: [],            // detail rows from dailyReport.notesDetail
  filtered: [],
  meta: {},            // {rangeLabel, rangeFrom, rangeTo, viewerEmail, isAdmin}
  collectors: [],      // collector master list (admin only)
  range: 'month',
};

function _walFmtINR(n){
  const v = Number(n||0);
  if (!isFinite(v)) return '—';
  return new Intl.NumberFormat('en-IN', {maximumFractionDigits: 0}).format(v);
}
function _walEsc(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function _walPopulateOutcomeDropdown(){
  // Build the outcome filter dropdown from the seven seed outcomes PLUS
  // any extra outcome values present in walState.rows. This makes the
  // filter automatically reflect free-form outcomes entered in the
  // Worklist (e.g. "Callback required") without code changes.
  const sel = document.getElementById('walOutcome');
  if (!sel) return;
  const SEED = ['Promise to Pay','Reminder sent','Disputed','Escalated','Awaiting Approval','No response','Other'];
  const seen = new Set(SEED.map(s => s.toLowerCase()));
  const extras = [];
  (walState.rows || []).forEach(n => {
    const v = String(n && n.outcome || '').trim();
    if (!v) return;
    const k = v.toLowerCase();
    if (seen.has(k)) return;
    seen.add(k);
    extras.push(v);
  });
  extras.sort((a,b) => a.localeCompare(b));
  const prev = sel.value || '';
  const all = SEED.concat(extras);
  sel.innerHTML = '<option value="">All outcomes</option>' + all.map(v => {
    const esc = _walEsc(v);
    return `<option value="${esc}">${esc}</option>`;
  }).join('');
  // Preserve the previously-chosen outcome if it still exists in the list
  // (or matches an extra we just added).
  if (prev && all.some(v => v === prev)) sel.value = prev;
  else if (prev) {
    // Outcome the user picked no longer present in data — fall back to "All".
    sel.value = '';
  }
}

async function _walPopulateCollectorDropdown(){
  // Only admins see the full collector list. For collectors, the server-side
  // dailyReport scopes to their own email so we don't need the dropdown.
  try {
    const sel = document.getElementById('walCollector');
    if (!sel) return;
    if (typeof _fuJsonp !== 'function') return;
    const res = await _fuJsonp('collectorList', {});
    if (!res || !res.ok || !Array.isArray(res.rows)) return;
    walState.collectors = res.rows;
    const opts = ['<option value="">All collectors</option>'].concat(
      res.rows.map(c => {
        const em = (c.email||'').replace(/"/g,'&quot;');
        const nm = _walEsc(c.name || c.email || '');
        return `<option value="${em}">${nm}</option>`;
      })
    );
    sel.innerHTML = opts.join('');
  } catch(_){ /* silent — dropdown stays as "All collectors" */ }
}

async function loadWorklistActivity(){
  const tb = document.getElementById('walTbody');
  if (!tb) return;
  tb.innerHTML = '<tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>';
  const params = { range: walState.range || 'month' };
  if (params.range === 'custom') {
    params.from = document.getElementById('walFrom').value || '';
    params.to   = document.getElementById('walTo').value   || '';
  }
  try {
    const res = await _fuJsonp('dailyReport', params);
    if (!res || !res.ok) {
      const m = (res && res.error) || 'Backend did not return a success response.';
      tb.innerHTML = `<tr><td colspan="11" class="px-3 py-6 text-center" style="color:#b91c1c">${_walEsc(m)}</td></tr>`;
      return;
    }
    walState.rows = res.notesDetail || [];
    walState.meta = {
      rangeLabel:   res.rangeLabel   || '',
      rangeFrom:    res.rangeFrom    || '',
      rangeTo:      res.rangeTo      || '',
      viewerEmail:  res.viewerEmail  || '',
      isAdmin:      !!res.isAdmin,
      today:        res.today        || ''
    };
    // Refresh the outcome dropdown options from the actual data so any
    // free-form outcome typed in the Worklist (e.g. "Callback required")
    // surfaces as a filterable option here. We always keep the seven seed
    // outcomes too so a brand-new dataset still shows the canonical set.
    try { _walPopulateOutcomeDropdown(); } catch(_){}
    renderWorklistActivity();
  } catch(err){
    tb.innerHTML = `<tr><td colspan="11" class="px-3 py-6 text-center" style="color:#b91c1c">${_walEsc(err && err.message || String(err))}</td></tr>`;
  }
}

function renderWorklistActivity(){
  const tb = document.getElementById('walTbody');
  if (!tb) return;
  const collector = document.getElementById('walCollector').value || '';
  const outcome   = document.getElementById('walOutcome').value   || '';
  const q         = (document.getElementById('walSearch').value || '').trim().toLowerCase();

  walState.filtered = (walState.rows||[]).filter(n => {
    if (collector && String(n.collector||'').toLowerCase() !== collector.toLowerCase()) return false;
    if (outcome   && String(n.outcome||'')   !== outcome) return false;
    if (q) {
      const hay = [n.cid, n.customer, n.note, n.invoiceNo, n.collector, n.collectorName, n.outcome]
        .map(x => String(x==null?'':x).toLowerCase()).join(' ');
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });

  // KPIs
  const k1 = walState.filtered.length;
  const k2 = new Set(walState.filtered.map(n => n.cid)).size;
  const k3 = new Set(walState.filtered.map(n => n.collector)).size;
  const p2p = walState.filtered.filter(n => String(n.outcome||'') === 'Promise to Pay');
  const k4 = p2p.length;
  const k5 = p2p.reduce((s,n) => s + (+n.p2pAmount || 0), 0);

  document.getElementById('walK1').textContent = k1;
  document.getElementById('walK2').textContent = k2;
  document.getElementById('walK3').textContent = k3;
  document.getElementById('walK4').textContent = k4;
  document.getElementById('walK5').textContent = '₹' + _walFmtINR(k5);

  document.getElementById('walRowCount').textContent =
    `${k1} of ${walState.rows.length} note(s) shown · range: ${walState.meta.rangeLabel || walState.range}` +
    (walState.meta.rangeFrom ? ` (${walState.meta.rangeFrom} → ${walState.meta.rangeTo})` : '');

  if (!walState.filtered.length){
    tb.innerHTML = '<tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">No worklist activity in this range / filter.</td></tr>';
    return;
  }

  // Most-recent first — prefer the precise timestamp (ts) so multiple notes saved
  // on the same day still order correctly. Falls back to date when ts is absent.
  const sorted = walState.filtered.slice().sort((a,b) => {
    const av = String(a.ts || a.date || '');
    const bv = String(b.ts || b.date || '');
    return bv.localeCompare(av);
  });
  tb.innerHTML = sorted.map(n => {
    const oc = String(n.outcome||'');
    const ocColor = oc === 'Promise to Pay' ? '#15803d'
                  : oc === 'Disputed'       ? '#b91c1c'
                  : oc === 'Escalated'      ? '#b91c1c'
                  : oc === 'No response'    ? '#92400e'
                  : '#475569';
    // Match the Worklist's note rendering: show the same timestamp + same note body
    // (the backend now returns both `n.text` and `n.note` for parity, but the field
    // is the same source-of-truth value the collector typed).
    const noteBody = String(n.text != null ? n.text : (n.note || ''));
    const dateCell = n.ts ? (typeof wlFmtTs === 'function' ? wlFmtTs(n.ts) : String(n.ts).replace('T',' ').slice(0,16)) : String(n.date || '');
    return `<tr class="border-t border-slate-100">
      <td class="px-3 py-2 font-mono text-[11px]">${_walEsc(dateCell)}</td>
      <td class="px-3 py-2"><div>${_walEsc(n.collectorName||'')}</div><div class="text-[10px] text-slate-500 font-mono">${_walEsc(n.collector||'')}</div></td>
      <td class="px-3 py-2 font-mono text-[11px]">${_walEsc(n.cid||'')}</td>
      <td class="px-3 py-2">${_walEsc(n.customer||'')}</td>
      <td class="px-3 py-2 text-[11px]">${_walEsc(n.invoiceNo||'')}</td>
      <td class="px-3 py-2 text-right">${_walFmtINR(n.invoiceOs||0)}</td>
      <td class="px-3 py-2 text-[11px]" style="max-width:280px;white-space:pre-wrap;word-break:break-word">${_walEsc(noteBody)}</td>
      <td class="px-3 py-2 text-[11px]" style="color:${ocColor};font-weight:600">${_walEsc(oc)}</td>
      <td class="px-3 py-2 text-[11px]">${_walEsc(n.followUp||'')}</td>
      <td class="px-3 py-2 text-right">${n.p2pAmount ? _walFmtINR(n.p2pAmount) : ''}</td>
      <td class="px-3 py-2 text-[11px]">${_walEsc(n.p2pDate||'')}</td>
    </tr>`;
  }).join('');
}

async function downloadWorklistActivityExcel(){
  try {
    if (!walState.filtered.length && !walState.rows.length) {
      alert('No worklist activity to export. Click Refresh first.'); return;
    }
    if (typeof ExcelJS === 'undefined') { alert('ExcelJS library not loaded.'); return; }
    const rows      = walState.filtered.length ? walState.filtered : walState.rows;
    const today     = walState.meta.today || new Date().toISOString().slice(0,10);
    const rangeLbl  = walState.meta.rangeLabel || walState.range || 'Range';
    const safeLbl   = String(rangeLbl).replace(/[^A-Za-z0-9]+/g,'_').replace(/^_+|_+$/g,'') || 'Range';
    const collector = document.getElementById('walCollector').value || '';
    const outcome   = document.getElementById('walOutcome').value   || '';
    const q         = document.getElementById('walSearch').value     || '';

    const HEADER_FILL = {type:'pattern', pattern:'solid', fgColor:{argb:'FF2C4A52'}};
    const HEADER_FONT = {bold:true, color:{argb:'FFFFFFFF'}};
    const BORDER      = {style:'thin', color:{argb:'FFE2E8F0'}};
    const ALT_FILL    = {type:'pattern', pattern:'solid', fgColor:{argb:'FFF8FAFC'}};

    const wb = new ExcelJS.Workbook();
    wb.creator  = 'Fynd Receivables Insights';
    wb.created  = new Date();

    // ===== Sheet 1: Activity Detail =====
    const s1 = wb.addWorksheet('Activity Detail');
    s1.columns = [
      {header:'Date',                key:'date',          width:12},
      {header:'Collector',           key:'collectorName', width:24},
      {header:'Collector Email',     key:'collector',     width:30},
      {header:'CID',                 key:'cid',           width:12},
      {header:'Customer',            key:'customer',      width:34},
      {header:'Invoice No',          key:'invoiceNo',     width:18},
      {header:'Invoice Outstanding', key:'invoiceOs',     width:18, style:{numFmt:'#,##0.00'}},
      {header:'Note',                key:'note',          width:60},
      {header:'Outcome',             key:'outcome',       width:18},
      {header:'Next Follow-up',      key:'followUp',      width:14},
      {header:'P2P Amount',          key:'p2pAmount',     width:14, style:{numFmt:'#,##0.00'}},
      {header:'P2P Date',            key:'p2pDate',       width:12}
    ];
    rows.forEach((n,i) => {
      const r = s1.addRow({
        date:          n.date          || '',
        collectorName: n.collectorName || '',
        collector:     n.collector     || '',
        cid:           n.cid           || '',
        customer:      n.customer      || '',
        invoiceNo:     n.invoiceNo     || '',
        invoiceOs:     Math.round((n.invoiceOs||0)*100)/100,
        note:          n.note          || '',
        outcome:       n.outcome       || '',
        followUp:      n.followUp      || '',
        p2pAmount:     Math.round((n.p2pAmount||0)*100)/100,
        p2pDate:       n.p2pDate       || ''
      });
      // Zebra striping for readability
      if (i % 2 === 1) r.eachCell(c => { c.fill = ALT_FILL; });
      // Outcome chip colour
      const ocCell = r.getCell('outcome');
      const oc = String(n.outcome||'');
      const fg = oc === 'Promise to Pay' ? 'FF15803D'
               : oc === 'Disputed'       ? 'FFB91C1C'
               : oc === 'Escalated'      ? 'FFB91C1C'
               : oc === 'No response'    ? 'FF92400E'
               : 'FF475569';
      ocCell.font = {bold:true, color:{argb:fg}};
      // Wrap notes
      r.getCell('note').alignment = {wrapText:true, vertical:'top'};
      r.getCell('customer').alignment = {wrapText:true, vertical:'top'};
      r.height = Math.max(18, Math.min(60, 14 + Math.ceil(String(n.note||'').length/60)*12));
      r.eachCell(c => { c.border = {top:BORDER, left:BORDER, bottom:BORDER, right:BORDER}; });
    });
    s1.getRow(1).font = HEADER_FONT; s1.getRow(1).fill = HEADER_FILL;
    s1.getRow(1).alignment = {vertical:'middle', horizontal:'center'};
    s1.getRow(1).height = 20;
    s1.views = [{state:'frozen', ySplit:1}];
    s1.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: s1.columns.length } };

    // ===== Sheet 2: By Collector (roll-up) =====
    const byColl = new Map();
    rows.forEach(n => {
      const k = n.collector || '—';
      let g = byColl.get(k);
      if (!g) {
        g = { collectorName: n.collectorName||'', collector: n.collector||'',
              notes: 0, customers: new Set(), p2pCount: 0, p2pAmount: 0,
              outcomes: {} };
        byColl.set(k, g);
      }
      g.notes += 1;
      g.customers.add(n.cid);
      const oc = n.outcome || 'Other';
      g.outcomes[oc] = (g.outcomes[oc]||0) + 1;
      if (oc === 'Promise to Pay') {
        g.p2pCount  += 1;
        g.p2pAmount += (+n.p2pAmount || 0);
      }
    });
    const s2 = wb.addWorksheet('By Collector');
    s2.columns = [
      {header:'Collector',         key:'collectorName', width:24},
      {header:'Collector Email',   key:'collector',     width:30},
      {header:'Notes Added',       key:'notes',         width:14},
      {header:'Unique Customers',  key:'customers',     width:18},
      {header:'P2P Count',         key:'p2pCount',      width:12},
      {header:'P2P Committed (₹)', key:'p2pAmount',     width:18, style:{numFmt:'#,##0.00'}},
      {header:'Top Outcome',       key:'topOutcome',    width:18}
    ];
    const collectorRows = [...byColl.values()].map(g => {
      const top = Object.entries(g.outcomes).sort((a,b)=>b[1]-a[1])[0];
      return {
        collectorName: g.collectorName, collector: g.collector,
        notes: g.notes, customers: g.customers.size,
        p2pCount: g.p2pCount, p2pAmount: Math.round(g.p2pAmount*100)/100,
        topOutcome: top ? `${top[0]} (${top[1]})` : ''
      };
    }).sort((a,b) => b.notes - a.notes);
    s2.addRows(collectorRows);
    if (collectorRows.length){
      const tot = s2.addRow({
        collectorName: 'TOTAL', collector: '',
        notes: collectorRows.reduce((s,r)=>s+r.notes,0),
        customers: new Set(rows.map(n=>n.cid)).size,
        p2pCount: collectorRows.reduce((s,r)=>s+r.p2pCount,0),
        p2pAmount: Math.round(collectorRows.reduce((s,r)=>s+r.p2pAmount,0)*100)/100,
        topOutcome: ''
      });
      tot.font = {bold:true};
      tot.fill = {type:'pattern', pattern:'solid', fgColor:{argb:'FFEEF2F4'}};
    }
    s2.getRow(1).font = HEADER_FONT; s2.getRow(1).fill = HEADER_FILL;
    s2.getRow(1).alignment = {vertical:'middle', horizontal:'center'};
    s2.views = [{state:'frozen', ySplit:1}];
    s2.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: s2.columns.length } };

    // ===== Sheet 3: By Outcome =====
    const byOc = new Map();
    rows.forEach(n => {
      const k = n.outcome || 'Other';
      let g = byOc.get(k);
      if (!g) g = { outcome: k, notes: 0, customers: new Set(), p2pAmount: 0 };
      g.notes += 1; g.customers.add(n.cid);
      if (k === 'Promise to Pay') g.p2pAmount += (+n.p2pAmount || 0);
      byOc.set(k, g);
    });
    const s3 = wb.addWorksheet('By Outcome');
    s3.columns = [
      {header:'Outcome',             key:'outcome',   width:22},
      {header:'Notes',               key:'notes',     width:12},
      {header:'Unique Customers',    key:'customers', width:18},
      {header:'P2P Committed (₹)',   key:'p2pAmount', width:18, style:{numFmt:'#,##0.00'}}
    ];
    const ocRows = [...byOc.values()].map(g => ({
      outcome: g.outcome, notes: g.notes, customers: g.customers.size,
      p2pAmount: Math.round(g.p2pAmount*100)/100
    })).sort((a,b)=>b.notes - a.notes);
    s3.addRows(ocRows);
    s3.getRow(1).font = HEADER_FONT; s3.getRow(1).fill = HEADER_FILL;
    s3.getRow(1).alignment = {vertical:'middle', horizontal:'center'};
    s3.views = [{state:'frozen', ySplit:1}];

    // ===== Sheet 4: Meta =====
    const meta = wb.addWorksheet('Meta');
    meta.columns = [{header:'Field', key:'k', width:24},{header:'Value', key:'v', width:60}];
    meta.addRows([
      {k:'Report',             v:'Worklist Activity Log'},
      {k:'Range',              v: rangeLbl},
      {k:'From',               v: walState.meta.rangeFrom || ''},
      {k:'To',                 v: walState.meta.rangeTo   || ''},
      {k:'Generated on',       v: today},
      {k:'Generated by',       v: walState.meta.viewerEmail || ''},
      {k:'Scope',              v: walState.meta.isAdmin ? 'Admin — all collectors' : ('Collector — ' + (walState.meta.viewerEmail||'self'))},
      {k:'Collector filter',   v: collector || '(none)'},
      {k:'Outcome filter',     v: outcome || '(none)'},
      {k:'Search filter',      v: q || '(none)'},
      {k:'Notes in workbook',  v: rows.length},
      {k:'Collectors active',  v: byColl.size},
      {k:'Unique customers',   v: new Set(rows.map(n=>n.cid)).size}
    ]);
    meta.getRow(1).font = HEADER_FONT; meta.getRow(1).fill = HEADER_FILL;

    const buf  = await wb.xlsx.writeBuffer();
    const blob = new Blob([buf], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const a    = document.createElement('a');
    const namePart = collector ? '_' + collector.replace(/[^A-Za-z0-9]+/g,'_') : '';
    a.href = URL.createObjectURL(blob);
    a.download = `Worklist_Activity_${safeLbl}${namePart}_${today}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch(err){ alert('Excel error: ' + (err && err.message || err)); }
}

function wireWorklistActivity(){
  const rng = document.getElementById('walRange');
  const wf  = document.getElementById('walFrom');
  const wt  = document.getElementById('walTo');
  if (!rng) return;

  // Default custom dates → this month, hidden until user picks "Custom…"
  const today  = new Date();
  const first  = new Date(today.getFullYear(), today.getMonth(), 1);
  wf.value = first.toISOString().slice(0,10);
  wt.value = today.toISOString().slice(0,10);

  rng.addEventListener('change', () => {
    walState.range = rng.value;
    const isCustom = walState.range === 'custom';
    wf.style.display = isCustom ? '' : 'none';
    wt.style.display = isCustom ? '' : 'none';
  });

  document.getElementById('walRefresh').addEventListener('click', loadWorklistActivity);
  document.getElementById('walExcel').addEventListener('click', downloadWorklistActivityExcel);

  // Reset: wipe every filter back to defaults and clear the table. Mirror
  // the initial state set up at the top of this function so reset feels
  // exactly like a fresh page load of the Worklist Activity tab.
  const walResetBtn = document.getElementById('walReset');
  if (walResetBtn) walResetBtn.addEventListener('click', function(){
    rng.value = 'month';
    walState.range = 'month';
    wf.style.display = 'none';
    wt.style.display = 'none';
    const todayR  = new Date();
    const firstR  = new Date(todayR.getFullYear(), todayR.getMonth(), 1);
    wf.value = firstR.toISOString().slice(0,10);
    wt.value = todayR.toISOString().slice(0,10);
    const wc = document.getElementById('walCollector'); if (wc) wc.value = '';
    const wo = document.getElementById('walOutcome');   if (wo) wo.value = '';
    const ws = document.getElementById('walSearch');    if (ws) ws.value = '';
    // Clear the table + KPIs so the user sees a clean slate; require an
    // explicit Search click to re-fetch (matches the reset semantics on
    // other reset buttons in this app).
    const tb = document.getElementById('walTbody');
    if (tb) tb.innerHTML = '<tr><td colspan="11" class="px-3 py-6 text-center text-slate-500">Click Search to load worklist activity.</td></tr>';
    ['walK1','walK2','walK3','walK4','walK5'].forEach(function(k){
      var el = document.getElementById(k); if (el) el.textContent = '—';
    });
    const rc = document.getElementById('walRowCount'); if (rc) rc.textContent = '';
    walState.rows = [];
    walState.filtered = [];
  });

  // Client-side filters re-render without re-fetching
  ['walCollector','walOutcome','walSearch'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener(id === 'walSearch' ? 'input' : 'change', renderWorklistActivity);
  });

  // Populate the collector dropdown (admin only — list returns empty / blocked for non-admins)
  _walPopulateCollectorDropdown();
}

// ===== WORKLIST (collector / admin) ==========================================
const wlState = {
  me: null, isAdmin: false, isCollector: false,
  rows: [], filtered: [],
  collectors: [],     // [{email, name, active, cidCount}]
  currentCid: null,
  currentCustomer: null,
  currentInvoiceData: null,  // {ok, cid, customer, totalOpen, invoiceCount, groups:[...], today, isAdmin}
  currentInvoiceNo: '',      // invoice with focus in the modal (drives notes-history pane)
  currentInvoiceType: '',    // type of the focused invoice
  currentTypeFilter: 'ALL',  // active invoice-type tab inside the modal
  selectedInvoiceNos: new Set(),  // multi-select: invoiceNos that the next saved note will apply to
  p2pAmountUserEdited: false,     // true once the collector has manually typed in the P2P amount field
  notesStatusFilter: 'actionable',// 'all'|'actionable'|'overdue'|'today'|'scheduled'|'nofu'|'wnotes'|'nonotes'|'p2p'|'disputed'
  notesAgeingFilter: 'all',       // 'all'|'0-30'|'31-60'|'61-90'|'91-180'|'180+'
  notesSearch: '',                // free-text invoice-number search
  notesByCid: {},     // cid -> [note, ...]  (legacy + invoice-level; KPIs use the union)
  dailyRows: [],
  dailyPerCustomer: [],     // customer-wise rollup for Summary sheet
  dailyNotesDetail: [],     // detailed per-note rows for Notes sheet
  dailyViewerEmail: '',     // who asked (echoed back from backend)
  dailyIsAdmin: false,      // backend says viewer is admin
  scope: '',          // for admin: '' = all, or specific collector email
  cidAssignTarget: null,
  cidAssignSelected: new Set(),
  cidAssignSource: [],  // [{cid, customer, bu, openOs, ownedBy}]
  cidBuFilter: '',     // active BU filter inside the assign modal ('' = all)
  cidScopeFilter: 'mine', // 'mine' = only target collector's CIDs (default);
                          // 'all'  = full universe so admin can claim CIDs.
  cidUniverseCache: null, // cached server-side universe to avoid re-fetch
  bulkParsed: null,    // last parsed CSV: [{email,cid}]
  statusFilter: 'all', // active Worklist status button
  dailyRange: 'today', // active Daily Report range: today | 7d | month | all | custom
  dailyFrom: '',
  dailyTo: '',
  dailyMeta: { rangeLabel: 'Today', rangeFrom: '', rangeTo: '' },
};

function wlEsc(s){ return String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function wlFmtINR(n){ n = Number(n)||0; return '\u20B9' + n.toLocaleString('en-IN',{maximumFractionDigits:0}); }
function wlFmtDate(s){
  if(!s) return '—';
  const d = (typeof s === 'string') ? s.slice(0,10) : '';
  return d || '—';
}
function wlFmtTs(s){
  if(!s) return '—';
  try { return new Date(s).toLocaleString('en-IN', {dateStyle:'medium', timeStyle:'short'}); }
  catch(_) { return String(s).slice(0,16); }
}
function wlTodayStr(){ return new Date().toISOString().slice(0,10); }

function wlComputeKpis(){
  const today = wlTodayStr();
  const rows = wlState.rows;
  const openCount = rows.length;
  const openOs = rows.reduce((s,r)=> s + (r.openOs||0), 0);
  let dueToday = 0, overdue = 0;
  rows.forEach(r=>{
    if (r.nextFollowUp){
      if (r.nextFollowUp === today) dueToday++;
      else if (r.nextFollowUp < today) overdue++;
    }
  });
  // P2P this week — use notes loaded into wlState (sum from all notes for owned CIDs)
  let p2pCount = 0, p2pAmt = 0;
  const weekEnd = new Date(Date.now()+7*86400000).toISOString().slice(0,10);
  Object.values(wlState.notesByCid).forEach(ns => {
    ns.forEach(n => {
      if (n.outcome === 'Promise to Pay' && n.p2pDate && n.p2pDate >= today && n.p2pDate <= weekEnd) {
        p2pCount++; p2pAmt += (Number(n.p2pAmount)||0);
      }
    });
  });
  document.getElementById('wlKpiOpen').textContent = openCount.toLocaleString('en-IN');
  document.getElementById('wlKpiOpenOs').textContent = wlFmtINR(openOs);
  document.getElementById('wlKpiToday').textContent = dueToday.toLocaleString('en-IN');
  document.getElementById('wlKpiOverdue').textContent = overdue.toLocaleString('en-IN');
  document.getElementById('wlKpiP2P').textContent = p2pCount.toLocaleString('en-IN');
  document.getElementById('wlKpiP2POs').textContent = wlFmtINR(p2pAmt);
}

function wlApplyFilter(){
  const today = wlTodayStr();
  const weekEnd = new Date(Date.now()+7*86400000).toISOString().slice(0,10);
  const sevenAgo = new Date(Date.now()-7*86400000).toISOString().slice(0,10);
  const status = wlState.statusFilter || 'all';
  const q = String(document.getElementById('wlSearch').value || '').toLowerCase().trim();
  wlState.filtered = wlState.rows.filter(r => {
    if (q) {
      const hay = (r.cid + ' ' + r.customer + ' ' + r.bu).toLowerCase();
      if (hay.indexOf(q) === -1) return false;
    }
    switch(status){
      case 'overdue':  return r.nextFollowUp && r.nextFollowUp < today;
      case 'today':    return r.nextFollowUp === today;
      case 'week':     return r.nextFollowUp && r.nextFollowUp >= today && r.nextFollowUp <= weekEnd;
      case 'upcoming': return r.nextFollowUp && r.nextFollowUp > today;
      case 'nocontact':return !r.lastNoteTs;
      case 'stale':    return !r.lastNoteTs || (r.lastNoteTs.slice(0,10) < sevenAgo);
      default:         return true;
    }
  });
  // Filter changed → reset to page 1 so the user sees the top of the new set.
  wlState.page = 1;
  wlRenderTable();
}

// Worklist table — pagination + sort state. 15 rows per page,
// Outstanding sort defaults to DESC (highest first). User-clicked sort
// is sticky for the session so chip filters and search don't reset it.
const WL_PAGE_SIZE = 15;
if (typeof wlState.page !== 'number') wlState.page = 1;
if (!wlState.sortKey) wlState.sortKey = 'os';
if (!wlState.sortDir) wlState.sortDir = 'desc';

function wlRenderTable(){
  const tb = document.getElementById('wlTbody');
  const today = wlTodayStr();
  // Sort the filtered set by current sort key/dir BEFORE paginating.
  const dir = (wlState.sortDir === 'asc') ? 1 : -1;
  const key = wlState.sortKey || 'os';
  wlState.filtered.sort((a,b) => {
    if (key === 'os') {
      const av = +a.openOs || 0, bv = +b.openOs || 0;
      if (av === bv) return 0;
      return (av < bv ? -1 : 1) * dir;
    }
    return 0;
  });
  // Sync the sort arrow in the header
  const arrow = document.getElementById('wlSortOsArrow');
  if (arrow) arrow.textContent = (wlState.sortDir === 'asc') ? '▲' : '▼';

  // Pagination math
  const total = wlState.filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / WL_PAGE_SIZE));
  if (wlState.page > totalPages) wlState.page = totalPages;
  if (wlState.page < 1) wlState.page = 1;
  const startIdx = (wlState.page - 1) * WL_PAGE_SIZE;
  const endIdx = Math.min(startIdx + WL_PAGE_SIZE, total);
  const slice = wlState.filtered.slice(startIdx, endIdx);

  const rcEl = document.getElementById('wlRowCount');
  if (rcEl) rcEl.textContent = `· ${total} of ${wlState.rows.length} shown`;

  // Pager visibility + labels
  const pager = document.getElementById('wlPager');
  if (pager) {
    if (total === 0) {
      pager.style.display = 'none';
    } else {
      pager.style.display = '';
      const info = document.getElementById('wlPagerInfo');
      if (info) info.textContent = `Showing ${startIdx + 1}–${endIdx} of ${total}`;
      const num = document.getElementById('wlPageNum');
      if (num) num.textContent = `${wlState.page} / ${totalPages}`;
      const prev = document.getElementById('wlPrev');
      const next = document.getElementById('wlNext');
      if (prev) prev.disabled = wlState.page <= 1;
      if (next) next.disabled = wlState.page >= totalPages;
    }
  }

  if (!total){
    tb.innerHTML = '<tr><td colspan="5" class="px-3 py-6 text-center text-slate-500">No customers match the filter.</td></tr>';
    return;
  }
  tb.innerHTML = slice.map(r => {
    let fuBadge = '<span class="text-slate-400">—</span>';
    if (r.nextFollowUp) {
      if (r.nextFollowUp < today) fuBadge = `<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:9999px;font-weight:600">${wlEsc(r.nextFollowUp)} · overdue</span>`;
      else if (r.nextFollowUp === today) fuBadge = `<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:9999px;font-weight:600">${wlEsc(r.nextFollowUp)} · today</span>`;
      else fuBadge = `<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:9999px;font-weight:600">${wlEsc(r.nextFollowUp)}</span>`;
    }
    const invCount = r.openInvCount || 0;
    const invHint = invCount > 1 ? ` <span class="text-[10px] text-slate-500">· ${invCount} invoices</span>` : '';
    return `<tr class="border-t border-slate-100 hover:bg-slate-50" data-wl-open="${wlEsc(r.cid)}" data-wl-cust="${wlEsc(r.customer)}" style="cursor:pointer">
      <td class="px-3 py-2 font-mono text-[11px]">${wlEsc(r.cid)}</td>
      <td class="px-3 py-2">${wlEsc(r.customer)}${invHint}</td>
      <td class="px-3 py-2 text-right font-semibold">${wlFmtINR(r.openOs)}</td>
      <td class="px-3 py-2">${fuBadge}</td>
      <td class="px-3 py-2">
        <button class="chip wl-row-open" style="padding:2px 10px;font-size:11px">📝 Open</button>
      </td>
    </tr>`;
  }).join('');
  tb.querySelectorAll('tr[data-wl-open]').forEach(tr => tr.addEventListener('click', () => {
    const cid = tr.getAttribute('data-wl-open');
    const cust = tr.getAttribute('data-wl-cust');
    wlOpenNotesModal(cid, cust);
  }));
}

// Wire up the pager + Outstanding sort header. Idempotent so it's safe to
// call from initWorklistTab AND every wlRenderTable repaint without
// stacking listeners.
(function _wlInitPagerAndSort(){
  function bind(){
    const prev = document.getElementById('wlPrev');
    const next = document.getElementById('wlNext');
    const sort = document.getElementById('wlSortOs');
    if (prev && !prev._wlBound) {
      prev._wlBound = true;
      prev.addEventListener('click', () => {
        if (wlState.page > 1) { wlState.page -= 1; wlRenderTable(); }
      });
    }
    if (next && !next._wlBound) {
      next._wlBound = true;
      next.addEventListener('click', () => {
        const tp = Math.max(1, Math.ceil((wlState.filtered||[]).length / WL_PAGE_SIZE));
        if (wlState.page < tp) { wlState.page += 1; wlRenderTable(); }
      });
    }
    if (sort && !sort._wlBound) {
      sort._wlBound = true;
      sort.addEventListener('click', () => {
        wlState.sortDir = (wlState.sortDir === 'desc') ? 'asc' : 'desc';
        wlState.page = 1;
        wlRenderTable();
      });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
  // Re-attempt on a short delay in case the tab is in a hidden pane at boot.
  setTimeout(bind, 200);
  setTimeout(bind, 800);
})();

async function wlLoad(){
  const tb = document.getElementById('wlTbody');
  tb.innerHTML = '<tr><td colspan="5" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>';
  try {
    const params = {};
    // Scope filter: send whenever the collector-scope dropdown has a value,
    // regardless of admin status. The collector-scope dropdown is universally
    // visible (see whoAmI handler), so a non-admin who picks "Naveen Soni (40)"
    // must see Naveen's 40 CIDs — not silently fall through to their own
    // assigned list. Backend now honors `scope` for any caller.
    if (wlState.scope) params.scope = wlState.scope;
    const res = await _fuJsonp('worklistData', params);
    console.log('[wlLoad] response:', res);
    if (!res) { tb.innerHTML = '<tr><td colspan="5" class="px-3 py-6 text-center" style="color:#b91c1c">Server returned empty response. Redeploy the Apps Script with the latest code.gs.</td></tr>'; return; }
    if (!res.ok) { tb.innerHTML = `<tr><td colspan="5" class="px-3 py-6 text-center" style="color:#b91c1c">${wlEsc(res.error||'Failed to load')}</td></tr>`; return; }
    wlState.rows = res.rows || [];
    // Also load all notes for KPIs. Pass the SAME scope so the KPI panel
    // (Follow-ups Today / Overdue / P2P This Week) tracks the dropdown
    // selection — otherwise selecting "Naveen Soni (40)" would shrink the
    // customer list but leak everyone's notes into the KPI tiles.
    const notesParams = {};
    if (wlState.scope) notesParams.scope = wlState.scope;
    const nres = await _fuJsonp('notesList', notesParams);
    wlState.notesByCid = {};
    if (nres && nres.ok) {
      (nres.rows||[]).forEach(n => {
        if (!wlState.notesByCid[n.cid]) wlState.notesByCid[n.cid] = [];
        wlState.notesByCid[n.cid].push(n);
      });
    }
    wlComputeKpis();
    wlApplyFilter();
  } catch (err) {
    console.error('[wlLoad] exception', err);
    tb.innerHTML = `<tr><td colspan="5" class="px-3 py-6 text-center" style="color:#b91c1c">${wlEsc(err.message||String(err))}</td></tr>`;
  }
}

// ----- Notes modal (invoice-level) -----
// Status badge derived from latest note outcome + follow-up date for a single invoice
function wlInvoiceStatusBadge(inv, today){
  const out = (inv.lastOutcome||'').toLowerCase();
  const fu = inv.nextFollowUp || '';
  if (out.indexOf('dispute') >= 0) return '<span style="background:#fee2e2;color:#991b1b;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Dispute</span>';
  if (out.indexOf('promise') >= 0 || out === 'p2p') return '<span style="background:#dcfce7;color:#166534;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">P2P</span>';
  if (out.indexOf('escalat') >= 0) return '<span style="background:#fde68a;color:#78350f;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Escalated</span>';
  if (out === 'paid') return '<span style="background:#d1fae5;color:#065f46;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Paid</span>';
  if (out.indexOf('short paid') >= 0) return '<span style="background:#fed7aa;color:#9a3412;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Short Paid</span>';
  if (out.indexOf('callback') >= 0) return '<span style="background:#dbeafe;color:#1e40af;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Callback</span>';
  if (out.indexOf('wrong') >= 0) return '<span style="background:#fef3c7;color:#92400e;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Wrong contact</span>';
  if (out.indexOf('no response') >= 0) return '<span style="background:#e2e8f0;color:#475569;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">No response</span>';
  if (fu && fu < today) return '<span style="background:#fee2e2;color:#991b1b;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Overdue</span>';
  if (fu === today) return '<span style="background:#fef3c7;color:#92400e;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Today</span>';
  if (fu) return '<span style="background:#dbeafe;color:#1e40af;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Scheduled</span>';
  return '<span style="background:#f1f5f9;color:#64748b;padding:1px 7px;border-radius:9999px;font-size:10px;font-weight:600">Open</span>';
}

async function wlOpenNotesModal(cid, customer){
  wlState.currentCid = cid;
  wlState.currentCustomer = customer;
  wlState.currentInvoiceData = null;
  wlState.currentInvoiceNo = '';
  wlState.currentInvoiceType = '';
  wlState.currentTypeFilter = 'ALL';
  wlState.selectedInvoiceNos = new Set();
  wlState.p2pAmountUserEdited = false;
  // Default to Actionable so collectors land on invoices they actually need to chase today
  wlState.notesStatusFilter = 'actionable';
  wlState.notesAgeingFilter = 'all';
  wlState.notesSearch = '';
  const ageEl = document.getElementById('wlNotesAgeing'); if (ageEl) ageEl.value = 'all';
  const srcEl = document.getElementById('wlNotesSearch'); if (srcEl) srcEl.value = '';
  const selAll = document.getElementById('wlNotesSelectAll');
  if (selAll) { selAll.checked = false; selAll.indeterminate = false; }
  document.getElementById('wlNotesTitle').textContent = customer + ' · ' + cid;
  const r = wlState.rows.find(x => x.cid === cid);
  document.getElementById('wlNotesSub').textContent = r ? r.bu : '';
  document.getElementById('wlNotesHeaderStats').innerHTML = '';
  document.getElementById('wlNotesTypeTabs').innerHTML = '<span class="text-slate-400 text-[12px]">Loading invoice list…</span>';
  document.getElementById('wlNotesInvList').innerHTML = '<div class="text-slate-500 text-[12px] p-3 text-center">Loading…</div>';
  document.getElementById('wlNotesInvCount').textContent = '—';
  document.getElementById('wlNotesInvDetail').innerHTML = '<span class="text-slate-400">Select an invoice on the left to view notes and add a follow-up.</span>';
  document.getElementById('wlNotesHistory').innerHTML = '<div class="text-slate-500 text-[12px]">—</div>';
  document.getElementById('wlNoteForInv').textContent = '';
  // Reset form
  document.getElementById('wlNoteText').value = '';
  document.getElementById('wlNoteFollowUp').value = '';
  document.getElementById('wlNoteOutcome').value = '';
  document.getElementById('wlNoteP2PAmt').value = '';
  document.getElementById('wlNoteP2PDate').value = '';
  document.querySelectorAll('.wl-p2p-only').forEach(el => el.style.display = 'none');
  document.getElementById('wlNoteMsg').textContent = '';
  document.getElementById('wlNoteSave').disabled = true;
  document.getElementById('wlNotesModal').style.display = 'flex';

  try {
    const res = await _fuJsonp('customerInvoices', { cid });
    if (!res || !res.ok) {
      const errMsg = (res && res.error) || 'Failed to load invoices';
      document.getElementById('wlNotesInvList').innerHTML = `<div class="text-[12px] p-3 text-center" style="color:#b91c1c">${wlEsc(errMsg)}</div>`;
      document.getElementById('wlNotesTypeTabs').innerHTML = '';
      return;
    }
    wlState.currentInvoiceData = res;
    wlRenderInvoiceHeader();
    wlRenderInvoiceTypeTabs();
    wlRenderNotesStatusBtns();
    wlRenderInvoiceList();
    // Auto-select: prefer the lead invoice (drives earliest follow-up), but ONLY if it passes
    // the active filters. Otherwise fall back to the first visible filtered invoice.
    const today2 = res.today || wlTodayStr();
    const visiblePool = [];
    (res.groups||[]).forEach(g => {
      if (wlState.currentTypeFilter !== 'ALL' && (g.type||'Other') !== wlState.currentTypeFilter) return;
      (g.invoices||[]).forEach(inv => {
        if (wlInvoicePassesStatus(inv, today2) && wlInvoicePassesAgeing(inv) && wlInvoicePassesSearch(inv)) visiblePool.push(inv);
      });
    });
    let auto = '';
    if (r && r.leadInvoice && visiblePool.some(i => i.invoiceNo === r.leadInvoice)) auto = r.leadInvoice;
    if (!auto && visiblePool.length) auto = visiblePool[0].invoiceNo;
    if (!auto && r && r.leadInvoice) auto = r.leadInvoice; // fallback if nothing visible
    if (!auto) {
      for (const g of (res.groups||[])) {
        if (g.invoices && g.invoices.length) { auto = g.invoices[0].invoiceNo; break; }
      }
    }
    if (auto) wlSelectInvoice(auto);
  } catch (err) {
    document.getElementById('wlNotesInvList').innerHTML = `<div class="text-[12px] p-3 text-center" style="color:#b91c1c">${wlEsc(err.message||String(err))}</div>`;
  }
}

function wlRenderInvoiceHeader(){
  const d = wlState.currentInvoiceData;
  if (!d) return;
  const r = wlState.rows.find(x => x.cid === wlState.currentCid);
  const totalOpen = d.totalOpen || 0;
  const invCount = d.invoiceCount || 0;
  const maxDays = r ? (r.maxDays||0) : 0;
  document.getElementById('wlNotesHeaderStats').innerHTML =
    `<span>Outstanding <span class="font-semibold text-slate-900">${wlFmtINR(totalOpen)}</span></span>` +
    `<span>·</span>` +
    `<span>${invCount} open invoice${invCount===1?'':'s'}</span>` +
    `<span>·</span>` +
    `<span>Max ageing <span class="font-semibold">${maxDays}d</span></span>`;
}

function wlRenderInvoiceTypeTabs(){
  const d = wlState.currentInvoiceData;
  if (!d) return;
  const host = document.getElementById('wlNotesTypeTabs');
  const totalCount = d.invoiceCount || 0;
  const tabs = [{ key: 'ALL', label: 'All', count: totalCount }];
  (d.groups||[]).forEach(g => tabs.push({ key: g.type, label: g.type || 'Other', count: g.count }));
  host.innerHTML = tabs.map(t => {
    const active = (wlState.currentTypeFilter === t.key);
    const bg = active ? '#0f766e' : '#f1f5f9';
    const fg = active ? '#ffffff' : '#475569';
    return `<button class="chip" data-wl-itype="${wlEsc(t.key)}" style="padding:3px 10px;font-size:11px;background:${bg};color:${fg};border-color:${active?'#0f766e':'#e2e8f0'}">${wlEsc(t.label)} <span style="opacity:.75">(${t.count})</span></button>`;
  }).join('');
  host.querySelectorAll('[data-wl-itype]').forEach(b => b.addEventListener('click', () => {
    wlState.currentTypeFilter = b.getAttribute('data-wl-itype');
    wlRenderInvoiceTypeTabs();
    wlRenderNotesStatusBtns();
    wlRenderInvoiceList();
    wlSyncBulkUi();
  }));
}

// Render the status filter chip row. Counts respect the current type tab + ageing + search
// so collectors see how many invoices each bucket contains right now.
function wlRenderNotesStatusBtns(){
  const host = document.getElementById('wlNotesStatusBtns');
  if (!host) return;
  const d = wlState.currentInvoiceData;
  if (!d) { host.innerHTML = ''; return; }
  const today = d.today || wlTodayStr();
  // Build the candidate pool: respect the type tab, the ageing filter, and the search box,
  // but NOT the status filter itself (so each chip shows what it would yield if picked).
  const pool = [];
  (d.groups||[]).forEach(g => {
    if (wlState.currentTypeFilter !== 'ALL' && (g.type||'Other') !== wlState.currentTypeFilter) return;
    (g.invoices||[]).forEach(inv => {
      if (!wlInvoicePassesAgeing(inv)) return;
      if (!wlInvoicePassesSearch(inv)) return;
      pool.push(inv);
    });
  });
  function cnt(pred){ let n = 0; pool.forEach(i => { if (pred(i, today)) n++; }); return n; }
  const chips = [
    { key: 'all',        label: 'All',          count: pool.length },
    { key: 'actionable', label: '🔥 Actionable',count: cnt(wlPredActionable) },
    { key: 'overdue',    label: '⏰ Overdue',   count: cnt(wlPredOverdue) },
    { key: 'today',      label: '📌 Today',     count: cnt(wlPredToday) },
    { key: 'scheduled',  label: '📅 Scheduled', count: cnt(wlPredScheduled) },
    { key: 'nofu',       label: '⚪ No follow-up', count: cnt(wlPredNoFollowUp) },
    { key: 'p2p',        label: '💰 P2P',       count: cnt(wlPredP2P) },
    { key: 'disputed',   label: '⚠ Disputed',   count: cnt(wlPredDisputed) },
    { key: 'wnotes',     label: '💬 With notes',count: cnt(wlPredWithNotes) },
    { key: 'nonotes',    label: '🆕 No notes',  count: cnt(wlPredNoNotes) },
  ];
  host.innerHTML = chips.map(c => {
    const active = (wlState.notesStatusFilter === c.key);
    const bg = active ? '#0f766e' : '#ffffff';
    const fg = active ? '#ffffff' : '#475569';
    const bd = active ? '#0f766e' : '#cbd5e1';
    return `<button class="chip" data-wl-nstat="${c.key}" style="padding:3px 9px;font-size:11px;background:${bg};color:${fg};border-color:${bd}">${c.label} <span style="opacity:.75">(${c.count})</span></button>`;
  }).join('');
  host.querySelectorAll('[data-wl-nstat]').forEach(b => b.addEventListener('click', () => {
    wlState.notesStatusFilter = b.getAttribute('data-wl-nstat');
    wlRenderNotesStatusBtns();
    wlRenderInvoiceList();
    wlSyncBulkUi();
  }));
}

// Per-invoice predicates used by both the status chips and the list filter.
function wlPredActionable(inv, today){
  const fu = inv.nextFollowUp || '';
  return !fu || fu <= today;  // No follow-up scheduled, OR follow-up date is today/past
}
function wlPredOverdue(inv, today){ return inv.nextFollowUp && inv.nextFollowUp < today; }
function wlPredToday(inv, today){ return inv.nextFollowUp === today; }
function wlPredScheduled(inv, today){ return inv.nextFollowUp && inv.nextFollowUp > today; }
function wlPredNoFollowUp(inv){ return !inv.nextFollowUp; }
function wlPredWithNotes(inv){ return (inv.notes||[]).length > 0; }
function wlPredNoNotes(inv){ return (inv.notes||[]).length === 0; }
function wlPredP2P(inv){ return (inv.lastOutcome||'') === 'Promise to Pay'; }
function wlPredDisputed(inv){ return (inv.lastOutcome||'').toLowerCase().indexOf('dispute') >= 0; }

// Ageing bucket on inv.days (days past invoice date).
function wlInvoicePassesAgeing(inv){
  const b = wlState.notesAgeingFilter;
  if (!b || b === 'all') return true;
  const d = Number(inv.days)||0;
  if (b === '0-30')   return d <= 30;
  if (b === '31-60')  return d >= 31 && d <= 60;
  if (b === '61-90')  return d >= 61 && d <= 90;
  if (b === '91-180') return d >= 91 && d <= 180;
  if (b === '180+')   return d > 180;
  return true;
}
function wlInvoicePassesSearch(inv){
  const q = (wlState.notesSearch||'').trim().toLowerCase();
  if (!q) return true;
  return String(inv.invoiceNo||'').toLowerCase().includes(q);
}
function wlInvoicePassesStatus(inv, today){
  const s = wlState.notesStatusFilter || 'all';
  if (s === 'all')        return true;
  if (s === 'actionable') return wlPredActionable(inv, today);
  if (s === 'overdue')    return wlPredOverdue(inv, today);
  if (s === 'today')      return wlPredToday(inv, today);
  if (s === 'scheduled')  return wlPredScheduled(inv, today);
  if (s === 'nofu')       return wlPredNoFollowUp(inv);
  if (s === 'wnotes')     return wlPredWithNotes(inv);
  if (s === 'nonotes')    return wlPredNoNotes(inv);
  if (s === 'p2p')        return wlPredP2P(inv);
  if (s === 'disputed')   return wlPredDisputed(inv);
  return true;
}

function wlRenderInvoiceList(){
  const d = wlState.currentInvoiceData;
  if (!d) return;
  const host = document.getElementById('wlNotesInvList');
  const today = d.today || wlTodayStr();
  // Flatten groups, filter by selected type, then apply status / ageing / search filters
  let groups = (d.groups || []).map(g => {
    if (wlState.currentTypeFilter !== 'ALL' && (g.type||'Other') !== wlState.currentTypeFilter) {
      return { ...g, invoices: [] };
    }
    const filtered = (g.invoices || []).filter(inv =>
      wlInvoicePassesStatus(inv, today) &&
      wlInvoicePassesAgeing(inv) &&
      wlInvoicePassesSearch(inv)
    );
    return { ...g, invoices: filtered };
  }).filter(g => g.invoices.length > 0);
  let totalShown = 0;
  let totalOpen = 0;
  groups.forEach(g => { totalShown += g.invoices.length; g.invoices.forEach(i => totalOpen += Number(i.openAmount)||0); });
  document.getElementById('wlNotesInvCount').textContent = totalShown + ' shown · ' + wlFmtINR(totalOpen);
  if (!totalShown) { host.innerHTML = '<div class="text-slate-500 text-[12px] p-3 text-center">No invoices match the current filters.</div>'; return; }
  let html = '';
  groups.forEach(g => {
    const items = g.invoices || [];
    if (!items.length) return;
    let groupOpen = 0;
    items.forEach(i => { groupOpen += Number(i.openAmount)||0; });
    html += `<div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#64748b;padding:6px 4px 4px;display:flex;justify-content:space-between">
      <span>${wlEsc(g.type||'Other')} · ${items.length}</span>
      <span class="font-semibold text-slate-700">${wlFmtINR(groupOpen)}</span>
    </div>`;
    items.forEach(inv => {
      const isFocus = (inv.invoiceNo === wlState.currentInvoiceNo);
      const isChecked = wlState.selectedInvoiceNos.has(inv.invoiceNo);
      const bg = isChecked ? '#fef9c3' : (isFocus ? '#ecfeff' : 'white');
      const bord = isChecked ? '#ca8a04' : (isFocus ? '#0f766e' : '#e2e8f0');
      const fu = inv.nextFollowUp
        ? (inv.nextFollowUp < today
            ? `<span style="color:#b91c1c">${wlEsc(inv.nextFollowUp)} · overdue</span>`
            : (inv.nextFollowUp === today
              ? `<span style="color:#92400e">${wlEsc(inv.nextFollowUp)} · today</span>`
              : `<span style="color:#1e40af">${wlEsc(inv.nextFollowUp)}</span>`))
        : '<span class="text-slate-400">no follow-up</span>';
      const noteCount = (inv.notes||[]).length;
      const noteText = noteCount ? `${noteCount} note${noteCount===1?'':'s'}` : 'no notes';
      html += `<div data-wl-inv="${wlEsc(inv.invoiceNo)}" data-wl-itype-val="${wlEsc(inv.invoiceType||'')}" style="cursor:pointer;border:1px solid ${bord};background:${bg};border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:12px;display:flex;gap:8px;align-items:start">
        <input type="checkbox" data-wl-invchk="${wlEsc(inv.invoiceNo)}" ${isChecked?'checked':''} style="margin-top:3px;cursor:pointer;flex-shrink:0" title="Add same note to this invoice">
        <div style="flex:1;min-width:0">
          <div style="display:flex;justify-content:space-between;align-items:start;gap:8px">
            <div style="min-width:0;flex:1">
              <div class="font-mono font-semibold text-slate-800" style="font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${wlEsc(inv.invoiceNo)}</div>
              <div class="text-[10px] text-slate-500">${wlEsc(inv.invoiceDate||'')} · ${inv.days||0}d</div>
            </div>
            <div style="text-align:right">
              <div class="font-semibold">${wlFmtINR(inv.openAmount||0)}</div>
              <div style="margin-top:2px">${wlInvoiceStatusBadge(inv, today)}</div>
            </div>
          </div>
          <div class="flex items-center justify-between mt-1 text-[11px] text-slate-500">
            <span>${fu}</span><span>${noteText}</span>
          </div>
        </div>
      </div>`;
    });
  });
  host.innerHTML = html;
  // Card body (excl. checkbox) → focus that invoice in the right pane
  host.querySelectorAll('[data-wl-inv]').forEach(el => el.addEventListener('click', (ev) => {
    // Don't focus when the click originated on the checkbox itself
    if (ev.target && ev.target.matches && ev.target.matches('input[type=checkbox]')) return;
    wlSelectInvoice(el.getAttribute('data-wl-inv'));
  }));
  // Per-card checkbox → toggle in the bulk-target set
  host.querySelectorAll('[data-wl-invchk]').forEach(cb => cb.addEventListener('click', (ev) => {
    ev.stopPropagation();
  }));
  host.querySelectorAll('[data-wl-invchk]').forEach(cb => cb.addEventListener('change', () => {
    const no = cb.getAttribute('data-wl-invchk');
    if (cb.checked) wlState.selectedInvoiceNos.add(no);
    else wlState.selectedInvoiceNos.delete(no);
    wlSyncBulkUi();
    wlMaybeAutoFillP2P();   // keep P2P amount in sync with selection when outcome=Promise to Pay
    wlRenderInvoiceList();  // re-render so the highlight tracks the new state
  }));
}

// Reflects current selection size + focus on the Save button and the Add-note label.
// Also keeps the header Select-all checkbox in sync (checked / indeterminate / unchecked).
function wlSyncBulkUi(){
  const d = wlState.currentInvoiceData;
  const btn = document.getElementById('wlNoteSave');
  const lbl = document.getElementById('wlNoteForInv');
  const selAll = document.getElementById('wlNotesSelectAll');
  const count = wlState.selectedInvoiceNos.size;
  // Outcome is mandatory — Save stays disabled until an outcome is picked,
  // even if invoices are selected. Hint shown via the message line below.
  const outcomeEl = document.getElementById('wlNoteOutcome');
  const hasOutcome = !!(outcomeEl && outcomeEl.value);
  const hasTarget  = count >= 1 || !!wlState.currentInvoiceNo;
  if (count >= 2) {
    lbl.innerHTML = `· will save to <span class="font-semibold" style="color:#ca8a04">${count} invoices</span>`;
    btn.textContent = hasOutcome ? `💾 Save note to ${count} invoices` : `Select outcome to save to ${count} invoices`;
  } else if (count === 1) {
    const onlyNo = Array.from(wlState.selectedInvoiceNos)[0];
    lbl.innerHTML = `· will save to <span class="font-semibold">${wlEsc(onlyNo)}</span>`;
    btn.textContent = hasOutcome ? '💾 Save note' : 'Select outcome to save';
  } else if (wlState.currentInvoiceNo) {
    lbl.textContent = '· for invoice ' + wlState.currentInvoiceNo;
    btn.textContent = hasOutcome ? '💾 Save note' : 'Select outcome to save';
  } else {
    lbl.textContent = '';
    btn.textContent = '💾 Save note';
  }
  btn.disabled = !(hasTarget && hasOutcome);
  // Select-all state: count visible invoices respecting all active filters
  if (selAll && d) {
    const today = d.today || wlTodayStr();
    let visible = 0;
    let checkedVisible = 0;
    (d.groups||[]).forEach(g => {
      if (wlState.currentTypeFilter !== 'ALL' && (g.type||'Other') !== wlState.currentTypeFilter) return;
      (g.invoices||[]).forEach(inv => {
        if (!wlInvoicePassesStatus(inv, today)) return;
        if (!wlInvoicePassesAgeing(inv)) return;
        if (!wlInvoicePassesSearch(inv)) return;
        visible++;
        if (wlState.selectedInvoiceNos.has(inv.invoiceNo)) checkedVisible++;
      });
    });
    if (visible === 0) { selAll.checked = false; selAll.indeterminate = false; }
    else if (checkedVisible === 0) { selAll.checked = false; selAll.indeterminate = false; }
    else if (checkedVisible === visible) { selAll.checked = true; selAll.indeterminate = false; }
    else { selAll.checked = false; selAll.indeterminate = true; }
  }
}

// Sum openAmount across whichever invoices the next saved note will apply to.
// If any checkboxes are ticked, sum those; otherwise fall back to the currently-focused invoice.
function wlSumSelectedOpenAmount(){
  const d = wlState.currentInvoiceData;
  if (!d) return 0;
  const selected = wlState.selectedInvoiceNos;
  let total = 0;
  let matched = 0;
  (d.groups||[]).forEach(g => (g.invoices||[]).forEach(inv => {
    if (selected && selected.size > 0) {
      if (selected.has(inv.invoiceNo)) { total += Number(inv.openAmount)||0; matched++; }
    } else if (wlState.currentInvoiceNo && inv.invoiceNo === wlState.currentInvoiceNo) {
      total += Number(inv.openAmount)||0; matched++;
    }
  }));
  return matched ? total : 0;
}

// When outcome is Promise to Pay and the collector hasn't manually edited the P2P amount,
// auto-fill it with the sum of selected invoice open amounts. Stays editable.
function wlMaybeAutoFillP2P(){
  const outcomeEl = document.getElementById('wlNoteOutcome');
  const amtEl = document.getElementById('wlNoteP2PAmt');
  if (!outcomeEl || !amtEl) return;
  if (outcomeEl.value !== 'Promise to Pay') return;
  if (wlState.p2pAmountUserEdited) return;
  const sum = wlSumSelectedOpenAmount();
  // Round to 2 decimals to keep the field tidy
  amtEl.value = sum ? (Math.round(sum * 100) / 100).toFixed(2) : '';
}

function wlSelectInvoice(invoiceNo){
  const d = wlState.currentInvoiceData;
  if (!d) return;
  let target = null;
  (d.groups||[]).forEach(g => (g.invoices||[]).forEach(inv => { if (inv.invoiceNo === invoiceNo) target = inv; }));
  if (!target) return;
  wlState.currentInvoiceNo = target.invoiceNo;
  wlState.currentInvoiceType = target.invoiceType || '';
  // Detail strip
  const today = d.today || wlTodayStr();
  document.getElementById('wlNotesInvDetail').innerHTML =
    `<div class="flex items-center justify-between gap-2 flex-wrap">
       <div>
         <div class="text-sm font-mono font-semibold text-slate-800">${wlEsc(target.invoiceNo)} <span class="text-[10px] text-slate-500">${wlEsc(target.invoiceType||'')}</span></div>
         <div class="text-[11px] text-slate-500">Invoice ${wlEsc(target.invoiceDate||'—')} · Due ${wlEsc(target.dueDate||'—')} · ${target.days||0} days</div>
       </div>
       <div class="text-right">
         <div class="font-semibold text-slate-900">${wlFmtINR(target.openAmount||0)}</div>
         <div>${wlInvoiceStatusBadge(target, today)}</div>
       </div>
     </div>`;
  // Reset add-note form (preserve nothing on select)
  document.getElementById('wlNoteText').value = '';
  document.getElementById('wlNoteFollowUp').value = '';
  document.getElementById('wlNoteOutcome').value = '';
  document.getElementById('wlNoteP2PAmt').value = '';
  document.getElementById('wlNoteP2PDate').value = '';
  document.querySelectorAll('.wl-p2p-only').forEach(el => el.style.display = 'none');
  document.getElementById('wlNoteMsg').textContent = '';
  wlRenderInvoiceList(); // re-render to update selected highlight
  wlRenderNotesHistory();
  wlSyncBulkUi();
  wlMaybeAutoFillP2P();  // if outcome is already Promise to Pay, keep amount synced to focus
}

function wlRenderNotesHistory(){
  const d = wlState.currentInvoiceData;
  const invNo = wlState.currentInvoiceNo;
  const host = document.getElementById('wlNotesHistory');
  if (!d || !invNo){ host.innerHTML = '<div class="text-slate-500 text-[12px]">Select an invoice to view its notes.</div>'; return; }
  let inv = null;
  (d.groups||[]).forEach(g => (g.invoices||[]).forEach(x => { if (x.invoiceNo === invNo) inv = x; }));
  const ns = (inv && inv.notes ? inv.notes : []).slice().sort((a,b) => (b.ts||'').localeCompare(a.ts||''));
  if (!ns.length){ host.innerHTML = '<div class="text-slate-500 text-[12px]">No notes yet for this invoice.</div>'; return; }
  host.innerHTML = ns.map(n => {
    const outcomeBadge = n.outcome
      ? `<span style="background:#dbeafe;color:#1e40af;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:600">${wlEsc(n.outcome)}</span>`
      : '';
    const p2p = (n.outcome === 'Promise to Pay' && (n.p2pAmount || n.p2pDate))
      ? `<div class="text-[11px] text-slate-600">P2P: ${wlFmtINR(n.p2pAmount||0)} by ${wlEsc(n.p2pDate||'—')}</div>`
      : '';
    const fu = n.followUp ? `<div class="text-[11px] text-slate-600">Next follow-up: <span class="font-semibold">${wlEsc(n.followUp)}</span></div>` : '';
    const delBtn = wlState.isAdmin
      ? `<button class="chip" data-wl-noteDel="${wlEsc(n.id)}" style="padding:0 6px;font-size:10px;background:#fef2f2;color:#991b1b;border-color:#fecaca">×</button>`
      : '';
    return `<div class="border border-slate-200 rounded p-2 bg-slate-50">
      <div class="flex items-center justify-between gap-2">
        <div class="text-[11px] text-slate-500">${wlFmtTs(n.ts)} · ${wlEsc(n.collector)} ${outcomeBadge}</div>
        ${delBtn}
      </div>
      <div class="text-[12px] text-slate-800 mt-1" style="white-space:pre-wrap">${wlEsc(n.text)}</div>
      ${fu}${p2p}
    </div>`;
  }).join('');
  host.querySelectorAll('[data-wl-noteDel]').forEach(b => b.addEventListener('click', async () => {
    const id = b.getAttribute('data-wl-noteDel');
    if (!confirm('Delete this note? (admin only)')) return;
    b.disabled = true;
    try {
      const res = await _fuJsonp('notesDelete', { id });
      if (res && res.ok) {
        // Remove from local invoice data + global cache
        const cid = wlState.currentCid;
        if (wlState.currentInvoiceData) {
          (wlState.currentInvoiceData.groups||[]).forEach(g => (g.invoices||[]).forEach(inv => {
            if (inv.notes) inv.notes = inv.notes.filter(x => x.id !== id);
          }));
        }
        wlState.notesByCid[cid] = (wlState.notesByCid[cid]||[]).filter(x => x.id !== id);
        wlRenderNotesHistory();
        wlRenderInvoiceList();
        wlLoad();  // refresh worklist row summary
      } else {
        alert((res&&res.error) || 'Delete failed');
        b.disabled = false;
      }
    } catch(err) { alert(err.message); b.disabled = false; }
  }));
}

async function wlSaveNote(){
  const cid = wlState.currentCid;
  const msg = document.getElementById('wlNoteMsg');
  msg.textContent = '';
  if (!cid) return;
  const text = document.getElementById('wlNoteText').value.trim();
  if (!text) { msg.textContent = 'Note text is required'; msg.style.color = '#b91c1c'; return; }
  // Build the target list:
  //   - if any checkboxes are checked → use those invoices (bulk mode)
  //   - else if a single invoice has focus → use that one
  //   - else error
  let targets = [];
  if (wlState.selectedInvoiceNos && wlState.selectedInvoiceNos.size > 0) {
    const d = wlState.currentInvoiceData;
    if (d) {
      (d.groups||[]).forEach(g => (g.invoices||[]).forEach(inv => {
        if (wlState.selectedInvoiceNos.has(inv.invoiceNo)) {
          targets.push({ invoiceNo: inv.invoiceNo, invoiceType: inv.invoiceType || '' });
        }
      }));
    }
  } else if (wlState.currentInvoiceNo) {
    targets.push({ invoiceNo: wlState.currentInvoiceNo, invoiceType: wlState.currentInvoiceType || '' });
  }
  if (!targets.length) { msg.textContent = 'Tick at least one invoice (or click a card to focus one)'; msg.style.color = '#b91c1c'; return; }

  const followUp = document.getElementById('wlNoteFollowUp').value || '';
  const outcome = document.getElementById('wlNoteOutcome').value || '';
  const p2pAmount = document.getElementById('wlNoteP2PAmt').value || '0';
  const p2pDate = document.getElementById('wlNoteP2PDate').value || '';
  // Backstop: outcome is mandatory. The Save button is already disabled
  // via wlSyncBulkUi when no outcome is selected, but block here too in case
  // anything bypasses the UI (keyboard Enter, DevTools, etc.).
  if (!outcome) {
    msg.textContent = 'Outcome is required — pick one before saving';
    msg.style.color = '#b91c1c';
    try { document.getElementById('wlNoteOutcome').focus(); } catch(_){}
    return;
  }
  const btn = document.getElementById('wlNoteSave');
  btn.disabled = true; const lbl = btn.textContent;
  btn.textContent = targets.length > 1 ? `Saving to ${targets.length} invoices…` : 'Saving…';

  try {
    let savedNotes = [];   // [{invoiceNo, invoiceType, id, ts}]
    let ts = '';
    if (targets.length === 1) {
      // Single-invoice path → existing notesAdd
      const t = targets[0];
      const res = await _fuJsonp('notesAdd', {
        cid, customer: wlState.currentCustomer || '',
        invoiceNo: t.invoiceNo, invoiceType: t.invoiceType,
        text, followUp, outcome, p2pAmount, p2pDate,
      });
      if (!res || !res.ok) throw new Error((res && res.error) || 'Save failed');
      ts = res.ts;
      savedNotes.push({ invoiceNo: t.invoiceNo, invoiceType: t.invoiceType, id: res.id, ts: res.ts });
    } else {
      // Bulk path → notesAddBulk (single round-trip writes one row per invoice)
      const res = await _fuJsonp('notesAddBulk', {
        cid, customer: wlState.currentCustomer || '',
        invoices: JSON.stringify(targets),
        text, followUp, outcome, p2pAmount, p2pDate,
      });
      if (!res || !res.ok) throw new Error((res && res.error) || 'Bulk save failed');
      ts = res.ts;
      (res.results||[]).forEach(r => savedNotes.push({
        invoiceNo: r.invoiceNo, invoiceType: r.invoiceType || '', id: r.id, ts: res.ts
      }));
    }

    msg.textContent = savedNotes.length > 1
      ? `✓ Note saved to ${savedNotes.length} invoices`
      : '✓ Note saved';
    msg.style.color = '#15803d';

    // Update local state for each invoice that got the note
    if (!wlState.notesByCid[cid]) wlState.notesByCid[cid] = [];
    savedNotes.forEach(sn => {
      const newNote = {
        id: sn.id, ts: sn.ts, collector: wlState.me, cid,
        invoiceNo: sn.invoiceNo, invoiceType: sn.invoiceType,
        customer: wlState.currentCustomer || '', text, followUp,
        outcome,
        p2pAmount: Number(p2pAmount)||0, p2pDate
      };
      wlState.notesByCid[cid].unshift(newNote);
      if (wlState.currentInvoiceData) {
        (wlState.currentInvoiceData.groups||[]).forEach(g => (g.invoices||[]).forEach(inv => {
          if (inv.invoiceNo === sn.invoiceNo) {
            if (!inv.notes) inv.notes = [];
            inv.notes.unshift(newNote);
            let nf = '', lo = '';
            for (let i=0;i<inv.notes.length;i++){ if (inv.notes[i].followUp) { nf = inv.notes[i].followUp; lo = inv.notes[i].outcome; break; } }
            if (!lo && inv.notes[0]) lo = inv.notes[0].outcome || '';
            inv.nextFollowUp = nf;
            inv.lastOutcome = lo;
          }
        }));
      }
    });

    // Clear form + selection + checkboxes
    document.getElementById('wlNoteText').value = '';
    document.getElementById('wlNoteFollowUp').value = '';
    document.getElementById('wlNoteOutcome').value = '';
    document.getElementById('wlNoteP2PAmt').value = '';
    document.getElementById('wlNoteP2PDate').value = '';
    document.querySelectorAll('.wl-p2p-only').forEach(el => el.style.display = 'none');
    wlState.selectedInvoiceNos.clear();
    wlState.p2pAmountUserEdited = false;
    wlRenderNotesHistory();
    wlRenderInvoiceList();
    wlSyncBulkUi();

    // Update worklist row + KPIs
    const r = wlState.rows.find(x => x.cid === cid);
    if (r) {
      r.notesCount = (r.notesCount||0) + savedNotes.length;
      r.lastNoteTs = ts;
      r.lastNoteText = text;
      r.lastNoteCollector = wlState.me;
      // Recompute earliest follow-up across all invoices for this customer
      if (wlState.currentInvoiceData) {
        let earliest = '', leadInv = '', leadOut = '';
        (wlState.currentInvoiceData.groups||[]).forEach(g => (g.invoices||[]).forEach(inv => {
          if (inv.nextFollowUp && (!earliest || inv.nextFollowUp < earliest)) {
            earliest = inv.nextFollowUp;
            leadInv = inv.invoiceNo;
            leadOut = inv.lastOutcome || '';
          }
        }));
        r.nextFollowUp = earliest;
        r.leadInvoice = leadInv;
        r.lastOutcome = leadOut || r.lastOutcome;
      } else if (followUp) {
        r.nextFollowUp = followUp;
        r.lastOutcome = outcome;
      }
      wlComputeKpis();
      wlApplyFilter();
    }
    // Keep the Activity Log in lockstep: if the user has it open (or opens it
    // shortly after saving), the freshly-saved note + outcome must appear there
    // immediately, with the exact same content. Best-effort refresh, silent on failure.
    try { if (typeof loadWorklistActivity === 'function') loadWorklistActivity(); } catch(_){}
  } catch(err) {
    msg.textContent = err.message; msg.style.color = '#b91c1c';
  } finally {
    btn.disabled = false; btn.textContent = lbl;
  }
}

// ----- Daily Report (range-aware: today | 7d | month | all | custom) -----
async function wlLoadDaily(){
  const tb = document.getElementById('wlDailyTbody');
  tb.innerHTML = '<tr><td colspan="10" class="px-3 py-4 text-center text-slate-500">Loading…</td></tr>';
  const params = { range: wlState.dailyRange || 'today' };
  if (params.range === 'custom') {
    params.from = wlState.dailyFrom || '';
    params.to   = wlState.dailyTo   || '';
  }
  try {
    const res = await _fuJsonp('dailyReport', params);
    console.log('[wlLoadDaily] response:', res);
    // Detect stale deployment: backend may have returned the AR data dump
    // instead of an {ok,...} object. That happens when the deployed code.gs
    // doesn't have the `dailyReport` action wired into the dispatcher.
    if (!res || (typeof res !== 'object')) {
      tb.innerHTML = '<tr><td colspan="10" class="px-3 py-4 text-center" style="color:#b91c1c">Empty response from server.</td></tr>';
      return;
    }
    if (!res.ok) {
      const detail = res.error || (Array.isArray(res.ar) ? 'Deployed code.gs is out of date — `dailyReport` route is not wired. Redeploy with "New version".' : 'Failed to load');
      tb.innerHTML = `<tr><td colspan="10" class="px-3 py-4 text-center" style="color:#b91c1c">${wlEsc(detail)}</td></tr>`;
      return;
    }
    wlState.dailyRows         = res.perCollector || [];
    wlState.dailyPerCustomer  = res.perCustomer  || [];
    wlState.dailyNotesDetail  = res.notesDetail  || [];
    wlState.dailyViewerEmail  = res.viewerEmail  || '';
    wlState.dailyIsAdmin      = !!res.isAdmin;
    wlState.dailyMeta = { rangeLabel: res.rangeLabel||'', rangeFrom: res.rangeFrom||'', rangeTo: res.rangeTo||'' };
    document.getElementById('wlDailyDate').textContent = res.today || '';
    const lbl = document.getElementById('wlDailyRangeLbl');
    if (lbl) lbl.textContent = res.rangeLabel || (params.range || 'Today');
    const colNotes = document.getElementById('wlDailyColNotes');
    if (colNotes) colNotes.textContent = 'Notes (' + (res.rangeLabel || 'range') + ')';
    if (!wlState.dailyRows.length){
      tb.innerHTML = '<tr><td colspan="10" class="px-3 py-4 text-center text-slate-500">No collectors configured yet, or no activity in this range.</td></tr>';
      return;
    }
    tb.innerHTML = wlState.dailyRows.map(r => `<tr class="border-t border-slate-100">
      <td class="px-3 py-2"><div class="font-semibold">${wlEsc(r.name||'—')}</div><div class="text-[10px] text-slate-500 font-mono">${wlEsc(r.email)}</div></td>
      <td class="px-3 py-2 text-right">${r.cidsAssigned||0}</td>
      <td class="px-3 py-2 text-right">${wlFmtINR(r.openOs||0)}</td>
      <td class="px-3 py-2 text-right">${(r.notesInRange!=null?r.notesInRange:r.notesToday)||0}</td>
      <td class="px-3 py-2 text-right" style="color:${r.dueToday?'#92400e':''}">${r.dueToday||0}</td>
      <td class="px-3 py-2 text-right">${r.dueTomorrow||0}</td>
      <td class="px-3 py-2 text-right">${r.dueThisWeek||0}</td>
      <td class="px-3 py-2 text-right">${r.p2pCount||0}</td>
      <td class="px-3 py-2 text-right">${wlFmtINR(r.p2pAmount||0)}</td>
      <td class="px-3 py-2 text-right" style="color:${r.untouched7d?'#b91c1c':''}">${r.untouched7d||0}</td>
    </tr>`).join('');
  } catch (err) {
    tb.innerHTML = `<tr><td colspan="10" class="px-3 py-4 text-center" style="color:#b91c1c">${wlEsc(err && err.message || String(err))}</td></tr>`;
  }
}

async function wlDownloadDailyExcel(){
  try {
    if (!wlState.dailyRows.length && !(wlState.dailyPerCustomer||[]).length) {
      alert('No data to export. Click Refresh first.'); return;
    }
    if (typeof ExcelJS === 'undefined') { alert('ExcelJS library not loaded.'); return; }
    const wb        = new ExcelJS.Workbook();
    const today     = document.getElementById('wlDailyDate').textContent || wlTodayStr();
    const rangeLbl  = (wlState.dailyMeta && wlState.dailyMeta.rangeLabel) || 'Today';
    const rangeFrom = (wlState.dailyMeta && wlState.dailyMeta.rangeFrom) || today;
    const rangeTo   = (wlState.dailyMeta && wlState.dailyMeta.rangeTo)   || today;
    const safeLbl   = rangeLbl.replace(/[^A-Za-z0-9]+/g,'_').replace(/^_+|_+$/g,'') || 'Range';
    const HEADER_FILL = {type:'pattern', pattern:'solid', fgColor:{argb:'FF2C4A52'}};
    const HEADER_FONT = {bold:true, color:{argb:'FFFFFFFF'}};

    // ===== Sheet 1: Summary (CUSTOMER-WISE) =====
    // One row per (collector, customer) that had any activity in the range.
    // For an admin this spans all collectors; for a collector it's only theirs.
    const sum = wb.addWorksheet('Summary');
    sum.columns = [
      {header:'Collector', key:'collectorName', width:22},
      {header:'Collector Email', key:'collector', width:30},
      {header:'CID', key:'cid', width:12},
      {header:'Customer', key:'customer', width:32},
      {header:'Open Invoices', key:'openInvoices', width:14},
      {header:'Outstanding Amount', key:'openOs', width:20, style:{numFmt:'#,##0.00'}},
      {header:'Notes Added', key:'notesCount', width:12},
      {header:'First Note Date', key:'firstNoteDate', width:14},
      {header:'Last Note Date', key:'lastNoteDate', width:14}
    ];
    const perCustomer = wlState.dailyPerCustomer || [];
    sum.addRows(perCustomer.map(r => ({
      collectorName: r.collectorName || '',
      collector:     r.collector     || '',
      cid:           r.cid           || '',
      customer:      r.customer      || '',
      openInvoices:  r.openInvoices  || 0,
      openOs:        Math.round((r.openOs||0)*100)/100,
      notesCount:    r.notesCount    || 0,
      firstNoteDate: r.firstNoteDate || '',
      lastNoteDate:  r.lastNoteDate  || ''
    })));
    // Totals row
    if (perCustomer.length) {
      const totRow = sum.addRow({
        collectorName: 'TOTAL',
        collector: '',
        cid: '',
        customer: perCustomer.length + ' customer' + (perCustomer.length===1?'':'s'),
        openInvoices: perCustomer.reduce((s,r)=>s+(r.openInvoices||0),0),
        openOs:       Math.round(perCustomer.reduce((s,r)=>s+(r.openOs||0),0)*100)/100,
        notesCount:   perCustomer.reduce((s,r)=>s+(r.notesCount||0),0),
        firstNoteDate: '',
        lastNoteDate:  ''
      });
      totRow.font = {bold:true};
      totRow.fill = {type:'pattern', pattern:'solid', fgColor:{argb:'FFEEF2F4'}};
    }
    sum.getRow(1).font = HEADER_FONT; sum.getRow(1).fill = HEADER_FILL;
    sum.views = [{state:'frozen', ySplit:1}];

    // ===== Sheet 2: Notes (detailed per-invoice rows) =====
    // Date is YYYY-MM-DD (no timestamp). Invoice number and invoice outstanding are exposed.
    const detail = wlState.dailyNotesDetail || [];
    if (detail.length) {
      const n2 = wb.addWorksheet('Notes (' + safeLbl.slice(0,24) + ')');
      n2.columns = [
        {header:'Date', key:'date', width:12},
        {header:'Collector', key:'collectorName', width:22},
        {header:'Collector Email', key:'collector', width:30},
        {header:'CID', key:'cid', width:12},
        {header:'Customer', key:'customer', width:32},
        {header:'Invoice No', key:'invoiceNo', width:18},
        {header:'Invoice Outstanding', key:'invoiceOs', width:20, style:{numFmt:'#,##0.00'}},
        {header:'Note', key:'note', width:60},
        {header:'Outcome', key:'outcome', width:18},
        {header:'Next Follow-up', key:'followUp', width:14},
        {header:'P2P Amount', key:'p2pAmount', width:14, style:{numFmt:'#,##0.00'}},
        {header:'P2P Date', key:'p2pDate', width:12}
      ];
      n2.addRows(detail.map(n => ({
        date:          n.date || '',
        collectorName: n.collectorName || '',
        collector:     n.collector || '',
        cid:           n.cid || '',
        customer:      n.customer || '',
        invoiceNo:     n.invoiceNo || '',
        invoiceOs:     Math.round((n.invoiceOs||0)*100)/100,
        note:          n.note || '',
        outcome:       n.outcome || '',
        followUp:      n.followUp || '',
        p2pAmount:     Math.round((n.p2pAmount||0)*100)/100,
        p2pDate:       n.p2pDate || ''
      })));
      n2.getRow(1).font = HEADER_FONT; n2.getRow(1).fill = HEADER_FILL;
      n2.views = [{state:'frozen', ySplit:1}];
    }

    // ===== Sheet 3: Per-collector roll-up (kept for backwards compatibility / quick scan) =====
    if ((wlState.dailyRows||[]).length) {
      const s3 = wb.addWorksheet('Per Collector');
      s3.columns = [
        {header:'Collector', key:'name', width:22},
        {header:'Email', key:'email', width:30},
        {header:'CIDs Assigned', key:'cidsAssigned', width:14},
        {header:'Open Outstanding', key:'openOs', width:20, style:{numFmt:'#,##0.00'}},
        {header:'Notes (' + rangeLbl + ')', key:'notesInRange', width:18},
        {header:'Due Today', key:'dueToday', width:12},
        {header:'Due Tomorrow', key:'dueTomorrow', width:14},
        {header:'Due This Week', key:'dueThisWeek', width:14},
        {header:'P2P Count', key:'p2pCount', width:12},
        {header:'P2P Amount', key:'p2pAmount', width:16, style:{numFmt:'#,##0.00'}},
        {header:'Untouched 7d+', key:'untouched7d', width:14}
      ];
      s3.addRows(wlState.dailyRows.map(r => ({
        name: r.name, email: r.email,
        cidsAssigned: r.cidsAssigned||0,
        openOs:       Math.round((r.openOs||0)*100)/100,
        notesInRange: (r.notesInRange!=null ? r.notesInRange : (r.notesToday||0)),
        dueToday:     r.dueToday||0,
        dueTomorrow:  r.dueTomorrow||0,
        dueThisWeek:  r.dueThisWeek||0,
        p2pCount:     r.p2pCount||0,
        p2pAmount:    Math.round((r.p2pAmount||0)*100)/100,
        untouched7d:  r.untouched7d||0
      })));
      s3.getRow(1).font = HEADER_FONT; s3.getRow(1).fill = HEADER_FILL;
      s3.views = [{state:'frozen', ySplit:1}];
    }

    // ===== Sheet 4: Meta =====
    const meta = wb.addWorksheet('Meta');
    meta.columns = [{header:'Field', key:'k', width:22},{header:'Value', key:'v', width:48}];
    const scopeLbl = wlState.dailyIsAdmin
      ? 'Admin — all collectors'
      : ('Collector — only ' + (wlState.dailyViewerEmail || 'you'));
    meta.addRows([
      {k:'Report', v:'Collections Report (Customer-wise)'},
      {k:'Range', v:rangeLbl},
      {k:'From',  v:rangeFrom||''},
      {k:'To',    v:rangeTo||''},
      {k:'Generated on', v: today},
      {k:'Generated by', v: wlState.dailyViewerEmail || ''},
      {k:'Scope', v: scopeLbl},
      {k:'Customers touched', v: perCustomer.length},
      {k:'Notes rows', v: detail.length},
      {k:'Collectors in summary', v: (wlState.dailyRows||[]).length}
    ]);
    meta.getRow(1).font = HEADER_FONT; meta.getRow(1).fill = HEADER_FILL;

    const buf = await wb.xlsx.writeBuffer();
    const blob = new Blob([buf], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = `Collections_Report_${safeLbl}_${today}.xlsx`; a.click();
    URL.revokeObjectURL(a.href);
  } catch(err) { alert('Excel error: ' + err.message); }
}

// ----- Manage Collectors (admin only) -----
async function wlOpenManageCollectors(){
  document.getElementById('wlMcModal').style.display = 'flex';
  document.getElementById('mcAssignBox').style.display = 'none';
  // Reset modal back to the "Add / Update Collectors" tab on every open.
  try { if (typeof mcSwitchTab === 'function') mcSwitchTab('manage'); } catch(_){}
  // Reset bulk upload UI on every open
  try { wlBulkReset(); } catch(_){}
  await wlLoadCollectorMaster();
  // Rebuild the quick-pick dropdown now that collectors are loaded
  try { if (typeof mcSyncAssignPicker === 'function') mcSyncAssignPicker(); } catch(_){}
  // Check for any pre-existing duplicate CID ownership and surface a banner.
  try { wlCheckConflicts(true); } catch(_){}
  // Pre-warm the CID universe in the background so the first "Assign CIDs"
  // click is instant. This also makes the customer list visible even if the
  // admin never visits the Overview tab.
  try { wlBuildCidUniverse(); } catch(_){}
}

async function wlLoadCollectorMaster(){
  const tb = document.getElementById('mcCollectorTbody');
  tb.innerHTML = '<tr><td colspan="5" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>';
  try {
    const res = await _fuJsonp('collectorList', {});
    if (!res || !res.ok) { tb.innerHTML = `<tr><td colspan="5" class="px-3 py-6 text-center" style="color:#b91c1c">${wlEsc((res&&res.error)||'Failed to load')}</td></tr>`; return; }
    wlState.collectors = res.rows || [];
    if (!wlState.collectors.length) { tb.innerHTML = '<tr><td colspan="5" class="px-3 py-6 text-center text-slate-500">No collectors yet. Add one above.</td></tr>'; return; }
    // Defensive dedup: recompute cidCount from canonical (last-write-wins) ownership.
    // Server-side cidCount can be stale or include duplicates when a CID was reassigned
    // but the prior owner's row wasn't pruned. This guarantees Vaseem won't show 567
    // when 30 of those are actually owned by Naveen now.
    try {
      const all = await _fuJsonp('collectorCidsList', {});
      if (all && all.ok && all.byEmail) {
        const byEmail = all.byEmail || {};
        const cidToCanonical = {};
        Object.keys(byEmail).forEach(em => {
          (byEmail[em] || []).forEach(cid => {
            const k = String(cid).trim();
            if (!k) return;
            cidToCanonical[k] = em;   // last write wins
          });
        });
        const canonicalCount = {};
        Object.keys(cidToCanonical).forEach(cid => {
          const em = cidToCanonical[cid];
          if (!em) return;
          canonicalCount[em] = (canonicalCount[em] || 0) + 1;
        });
        wlState.collectors.forEach(c => {
          const em = String(c.email||'').toLowerCase();
          if (em in canonicalCount) c.cidCount = canonicalCount[em];
          else if (byEmail[em] && byEmail[em].length === 0) c.cidCount = 0;
        });
      }
    } catch(_){}
    tb.innerHTML = wlState.collectors.map(c => `<tr class="border-t border-slate-100">
      <td class="px-3 py-2">${wlEsc(c.name||'—')}</td>
      <td class="px-3 py-2 font-mono text-[11px]">${wlEsc(c.email)}</td>
      <td class="px-3 py-2">${c.active
        ? '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:9999px;font-weight:600">Active</span>'
        : '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:9999px;font-weight:600">Suspended</span>'}</td>
      <td class="px-3 py-2 text-right">${c.cidCount||0}</td>
      <td class="px-3 py-2">
        <button class="chip" data-mc-assign="${wlEsc(c.email)}" style="padding:2px 8px;font-size:11px">📌 Assign CIDs</button>
        <button class="chip" data-mc-edit="${wlEsc(c.email)}" style="padding:2px 8px;font-size:11px">Edit</button>
        ${c.email === (wlState.me||'').toLowerCase() ? '' : `<button class="chip" data-mc-del="${wlEsc(c.email)}" style="padding:2px 8px;font-size:11px;background:#fef2f2;color:#991b1b;border-color:#fecaca">Delete</button>`}
      </td>
    </tr>`).join('');
    tb.querySelectorAll('[data-mc-assign]').forEach(b => b.addEventListener('click', () => wlStartAssignCids(b.getAttribute('data-mc-assign'))));
    tb.querySelectorAll('[data-mc-edit]').forEach(b => b.addEventListener('click', () => {
      const em = b.getAttribute('data-mc-edit');
      const c = wlState.collectors.find(x => x.email === em);
      if (!c) return;
      document.getElementById('mcEmail').value = c.email;
      document.getElementById('mcName').value = c.name||'';
      document.getElementById('mcActive').value = c.active ? 'Yes' : 'No';
    }));
    tb.querySelectorAll('[data-mc-del]').forEach(b => b.addEventListener('click', async () => {
      const em = b.getAttribute('data-mc-del');
      if (!confirm('Delete collector ' + em + '? Their CID assignments will also be removed.')) return;
      b.disabled = true;
      try {
        const res = await _fuJsonp('collectorDelete', { email: em });
        if (res && res.ok) { await wlLoadCollectorMaster(); await wlLoad(); }
        else { alert((res&&res.error)||'Delete failed'); b.disabled = false; }
      } catch(err) { alert(err.message); b.disabled = false; }
    }));
  } catch(err) {
    tb.innerHTML = `<tr><td colspan="5" class="px-3 py-6 text-center" style="color:#b91c1c">${wlEsc(err.message)}</td></tr>`;
  }
}

// Generate a multi-sheet Excel covering: per-collector counts, every CID→owner row,
// and every unassigned CID. Useful for admin reviews and offline audit.
async function wlDownloadCollectorAssignment(){
  const btn = document.getElementById('mcDownload');
  const origLbl = btn ? btn.textContent : '';
  if (btn) { btn.disabled = true; btn.textContent = 'Preparing…'; }
  try {
    // Use the freshest data: collectors from state, and pull the universe + all assignments now
    const [universe, allRes] = await Promise.all([
      wlBuildCidUniverse(),
      _fuJsonp('collectorCidsList', {})
    ]);
    const allByEmail = (allRes && allRes.ok && allRes.byEmail) ? allRes.byEmail : {};
    const collectors = wlState.collectors || [];
    // Reverse map: cid -> list of owner emails (a CID can have >1 owner if admin assigned both).
    // De-dup the owners array per CID — the backend can occasionally emit the same
    // email more than once, which previously inflated counts (Vaseem 567 even after
    // 30 reassigned to Naveen) and duplicated rows in the Excel export.
    const cidToOwners = {};
    Object.keys(allByEmail).forEach(em => {
      (allByEmail[em] || []).forEach(c => {
        const k = String(c).trim();
        if (!k) return;
        if (!cidToOwners[k]) cidToOwners[k] = [];
        if (cidToOwners[k].indexOf(em) === -1) cidToOwners[k].push(em);
      });
    });
    // Canonical owner per CID = last in the owners list (most-recently assigned wins).
    // The "All Owners" column on the Assignments sheet still surfaces every owner so
    // admins can see lingering conflicts at a glance.
    const cidToCanonical = {};
    Object.keys(cidToOwners).forEach(cid => {
      const arr = cidToOwners[cid] || [];
      cidToCanonical[cid] = arr.length ? arr[arr.length - 1] : '';
    });
    // Owners → CIDs map after de-conflict: only the canonical owner of each CID counts.
    // This keeps the Collectors sheet aligned with the "one CID, one owner" rule even
    // when the underlying sheet still has stale duplicates pending Repair.
    const canonicalByEmail = {};
    Object.keys(cidToCanonical).forEach(cid => {
      const em = cidToCanonical[cid];
      if (!em) return;
      if (!canonicalByEmail[em]) canonicalByEmail[em] = [];
      canonicalByEmail[em].push(cid);
    });
    const emailToName = {};
    collectors.forEach(c => { emailToName[String(c.email||'').toLowerCase()] = c.name || c.email; });
    // Open OS per CID (from universe)
    const cidMeta = {};
    (universe || []).forEach(u => { cidMeta[String(u.cid||'').trim()] = u; });

    // ----- Sheet 1: Coverage (one-row exec summary) -----
    const totalCids = Object.keys(cidMeta).length;
    const assignedCidSet = new Set(Object.keys(cidToOwners));
    const assignedCount = assignedCidSet.size;
    const unassignedCount = Math.max(0, totalCids - assignedCount);
    let assignedOS = 0, unassignedOS = 0;
    Object.keys(cidMeta).forEach(cid => {
      const os = Number(cidMeta[cid].openOs)||0;
      if (assignedCidSet.has(cid)) assignedOS += os; else unassignedOS += os;
    });
    const totalOS = assignedOS + unassignedOS;
    const pct = totalCids ? (assignedCount / totalCids * 100).toFixed(1) + '%' : '0%';
    const osPct = totalOS ? (assignedOS / totalOS * 100).toFixed(1) + '%' : '0%';
    const activeCount = collectors.filter(c => c.active).length;
    const coverageRows = [
      { Metric: 'Total customers (CIDs)',            Value: totalCids },
      { Metric: 'Assigned customers',                Value: assignedCount },
      { Metric: 'Unassigned customers',              Value: unassignedCount },
      { Metric: 'Coverage % (by CID count)',         Value: pct },
      { Metric: 'Total open OS',                     Value: Math.round(totalOS*100)/100 },
      { Metric: 'Assigned open OS',                  Value: Math.round(assignedOS*100)/100 },
      { Metric: 'Unassigned open OS',                Value: Math.round(unassignedOS*100)/100 },
      { Metric: 'Coverage % (by open OS)',           Value: osPct },
      { Metric: 'Active collectors',                 Value: activeCount },
      { Metric: 'Total collectors',                  Value: collectors.length },
    ];

    // ----- Sheet 2: Collectors (per-person count + open OS owned) -----
    // Use the CANONICAL owner map (last-write-wins) so a CID reassigned from Vaseem
    // to Naveen counts only under Naveen — never under both.
    const collectorRows = collectors.map(c => {
      const em = String(c.email||'').toLowerCase();
      const cids = (canonicalByEmail[em] || []);
      let os = 0;
      cids.forEach(cid => { const m = cidMeta[String(cid).trim()]; if (m) os += Number(m.openOs)||0; });
      return {
        'Name': c.name || '',
        'Email': c.email || '',
        'Status': c.active ? 'Active' : 'Suspended',
        'CIDs Assigned': cids.length,
        'Open OS Owned': Math.round(os*100)/100,
      };
    });
    // Append an "Unassigned" pseudo-row so the sheet always sums to the universe
    collectorRows.push({
      'Name': '— UNASSIGNED —',
      'Email': '',
      'Status': '',
      'CIDs Assigned': unassignedCount,
      'Open OS Owned': Math.round(unassignedOS*100)/100,
    });

    // ----- Sheet 3: Assignments (one row per CID, no duplicates) -----
    // We emit ONE row per CID (canonical owner), and surface any lingering
    // conflict owners in a separate column so admins can spot them without
    // the sheet ballooning with duplicate rows.
    const assignmentRows = [];
    Object.keys(cidMeta).forEach(cid => {
      const meta = cidMeta[cid];
      const owners = cidToOwners[cid] || [];
      if (owners.length === 0) {
        assignmentRows.push({
          'CID': cid,
          'Customer': meta.customer || '',
          'Region': meta.bu || '',
          'Open OS': Math.round((Number(meta.openOs)||0)*100)/100,
          'Owner Email': '',
          'Owner Name': '',
          'Other Owners (conflict)': '',
          'Status': 'Unassigned',
        });
      } else {
        const canonical = cidToCanonical[cid] || owners[owners.length - 1];
        const others = owners.filter(em => em !== canonical);
        assignmentRows.push({
          'CID': cid,
          'Customer': meta.customer || '',
          'Region': meta.bu || '',
          'Open OS': Math.round((Number(meta.openOs)||0)*100)/100,
          'Owner Email': canonical,
          'Owner Name': emailToName[canonical] || '',
          'Other Owners (conflict)': others.join(', '),
          'Status': others.length ? 'Assigned (conflict)' : 'Assigned',
        });
      }
    });
    assignmentRows.sort((a,b) => (b['Open OS']||0) - (a['Open OS']||0));

    // ----- Sheet 4: Unassigned only (for quick triage) -----
    const unassignedRows = assignmentRows
      .filter(r => r.Status === 'Unassigned')
      .map(r => ({ 'CID': r.CID, 'Customer': r.Customer, 'Region': r.Region, 'Open OS': r['Open OS'] }));

    const sheets = [
      { name: 'Coverage',   rows: coverageRows },
      { name: 'Collectors', rows: collectorRows },
      { name: 'Assignments',rows: assignmentRows },
      { name: 'Unassigned', rows: unassignedRows },
    ];
    const stamp = new Date().toISOString().slice(0,10);
    downloadXLSX(sheets, 'Collector_Coverage_' + stamp);
  } catch(err) {
    alert('Download failed: ' + (err.message || err));
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = origLbl; }
  }
}

async function wlSaveCollector(){
  const email = document.getElementById('mcEmail').value.trim().toLowerCase();
  const msg = document.getElementById('mcCollectorMsg');
  msg.textContent = '';
  if (!email) { msg.textContent = 'Email is required'; msg.style.color = '#b91c1c'; return; }
  const payload = {
    email,
    name: document.getElementById('mcName').value.trim(),
    active: document.getElementById('mcActive').value
  };
  const btn = document.getElementById('mcSaveCollector');
  btn.disabled = true; const lbl = btn.textContent; btn.textContent = 'Saving…';
  try {
    const res = await _fuJsonp('collectorUpsert', payload);
    if (res && res.ok) {
      msg.textContent = '✓ ' + (res.mode === 'added' ? 'Added' : 'Updated'); msg.style.color = '#15803d';
      document.getElementById('mcEmail').value = '';
      document.getElementById('mcName').value = '';
      document.getElementById('mcActive').value = 'Yes';
      await wlLoadCollectorMaster();
    } else {
      msg.textContent = (res&&res.error)||'Save failed'; msg.style.color = '#b91c1c';
    }
  } catch(err) { msg.textContent = err.message; msg.style.color = '#b91c1c'; }
  finally { btn.disabled = false; btn.textContent = lbl; }
}

async function wlStartAssignCids(email){
  wlState.cidAssignTarget = email;
  wlState.cidAssignSelected = new Set();
  wlState.cidBuFilter = '';
  // Reset scope to "Mine" every time a new target collector is picked so
  // the table always opens scoped to the chosen person's accounts. The
  // user can switch to "All" to claim or reassign from other collectors.
  wlState.cidScopeFilter = 'mine';
  // Also reset the visual chip state so the active style follows the data.
  try {
    document.querySelectorAll('#mcScopeChips .mc-scope-btn').forEach(b => {
      const isMine = b.getAttribute('data-mc-scope') === 'mine';
      b.classList.toggle('mc-scope-active', isMine);
      b.style.background  = isMine ? '#1d4ed8' : '#fff';
      b.style.color       = isMine ? '#fff'    : '#475569';
      b.style.borderColor = isMine ? '#1d4ed8' : '#cbd5e1';
    });
  } catch(_){}
  // Auto-switch into the Assign tab so the CID picker is visible.
  try { if (typeof mcSwitchTab === 'function') mcSwitchTab('assign'); } catch(_){}
  // Sync the quick-pick dropdown to reflect the active target.
  try {
    const pickEl = document.getElementById('mcAssignPick');
    if (pickEl) pickEl.value = email;
  } catch(_){}
  document.getElementById('mcAssignTarget').textContent = email;
  document.getElementById('mcAssignBox').style.display = 'block';
  document.getElementById('mcAssignMsg').textContent = '';
  const loadMsg = document.getElementById('mcCidLoadMsg');
  if (loadMsg) loadMsg.textContent = 'Loading customers…';
  const tb = document.getElementById('mcCidTbody');
  if (tb) tb.innerHTML = '<tr><td colspan="6" class="px-3 py-4 text-center text-slate-500">Loading customer list…</td></tr>';

  // Pull the universe (state.data first, then backend) + current/all assignments in parallel
  let universe = [];
  let owned = [];
  let allByEmail = {};
  try {
    const [u, r1, r2] = await Promise.all([
      wlBuildCidUniverse(),
      _fuJsonp('collectorCidsList', { email }),
      _fuJsonp('collectorCidsList', {})
    ]);
    universe = u || [];
    if (r1 && r1.ok) owned = r1.cids || [];
    if (r2 && r2.ok && r2.byEmail) allByEmail = r2.byEmail;
  } catch(err) {
    if (loadMsg) loadMsg.textContent = 'Load error: ' + (err && err.message || err);
  }
  owned.forEach(c => wlState.cidAssignSelected.add(c));
  // Build inverse map: cid -> ownedBy
  const cidOwnedBy = {};
  Object.keys(allByEmail).forEach(em => (allByEmail[em]||[]).forEach(c => { cidOwnedBy[c] = em; }));

  wlState.cidAssignSource = universe.map(u => ({
    cid: u.cid, customer: u.customer, bu: u.bu, openOs: u.openOs,
    ownedBy: cidOwnedBy[u.cid] || ''
  }));

  // If no customers loaded, surface a clear diagnostic instead of an empty table
  if (!wlState.cidAssignSource.length) {
    if (loadMsg) loadMsg.textContent = 'No customers found. Open the Overview tab first so live AR data loads, then click ↻ Reload.';
  } else if (loadMsg) {
    loadMsg.textContent = '';
  }

  document.getElementById('mcCidTotal').textContent = wlState.cidAssignSource.length;
  document.getElementById('mcCidSearch').value = '';
  wlPopulateCidBuFilter();
  wlRenderCidAssignTable();
}

// Build the BU dropdown from whatever's in cidAssignSource. Preserves selection if possible.
// Also injects a "🔓 Unassigned accounts" sentinel option so admins can quickly find
// CIDs that don't yet have any collector.
function wlPopulateCidBuFilter(){
  const sel = document.getElementById('mcCidBuFilter');
  if (!sel) return;
  const prev = wlState.cidBuFilter || '';
  // Compute the BU counts WITHIN the active scope so the dropdown reflects
  // what's actually clickable. We need both counts (mine/all) for the scope
  // chips, and BU counts for the dropdown.
  const target = String(wlState.cidAssignTarget||'').toLowerCase();
  const scoped = (wlState.cidScopeFilter === 'all')
    ? wlState.cidAssignSource
    : wlState.cidAssignSource.filter(r => String(r.ownedBy||'').toLowerCase() === target);
  const buCounts = {};
  let unassignedCount = 0;
  scoped.forEach(r => {
    const b = String(r.bu||'').trim() || '(blank)';
    buCounts[b] = (buCounts[b]||0) + 1;
    if (!String(r.ownedBy||'').trim()) unassignedCount += 1;
  });
  const bus = Object.keys(buCounts).sort();
  const opts = [
    '<option value="">All Regions (' + scoped.length + ')</option>'
  ];
  // Unassigned-accounts sentinel is only useful in "All" scope — when the
  // collector is in "Mine" scope all rows by definition belong to them.
  if (wlState.cidScopeFilter === 'all') {
    opts.push(`<option value="__unassigned__">🔓 Unassigned accounts (${unassignedCount})</option>`);
  }
  bus.forEach(b => opts.push(`<option value="${wlEsc(b)}">${wlEsc(b)} (${buCounts[b]})</option>`));
  sel.innerHTML = opts.join('');
  // restore if the previous selection is still valid (BU exists OR unassigned sentinel)
  if (prev === '__unassigned__' && wlState.cidScopeFilter === 'all') sel.value = '__unassigned__';
  else if (prev && bus.indexOf(prev) !== -1) sel.value = prev;
  else wlState.cidBuFilter = '';
  // Refresh the scope-chip counts beside "Mine only" / "All accounts"
  try {
    const mineCount = wlState.cidAssignSource.filter(r =>
      String(r.ownedBy||'').toLowerCase() === target).length;
    const mineLbl = document.getElementById('mcScopeMineCount');
    const allLbl  = document.getElementById('mcScopeAllCount');
    if (mineLbl) mineLbl.textContent = mineCount;
    if (allLbl)  allLbl.textContent  = wlState.cidAssignSource.length;
  } catch(_){}
}

// Build the CID universe — first try in-memory state.data (compact keys),
// then fall back to the backend `cidUniverse` route so admins can assign
// CIDs even when they haven't opened the Overview tab yet.
async function wlBuildCidUniverse(){
  const ar = (window.state && window.state.data) || [];
  if (ar.length) {
    const byCid = {};
    ar.forEach(r => {
      const cid = String(r.ci||'').trim();
      if (!cid) return;
      if (!byCid[cid]) byCid[cid] = { cid, customer: String(r.s||''), bu: String(r.b||''), openOs: 0 };
      const os = Number(r.os||0);
      const st = String(r.st||'').toLowerCase();
      if (st !== 'closed') byCid[cid].openOs += os;
    });
    const out = Object.values(byCid).sort((a,b) => (b.openOs||0) - (a.openOs||0));
    if (out.length) {
      wlState.cidUniverseCache = out;
      return out;
    }
  }
  // Fallback: backend (admin-only). Cache for re-opens within session.
  if (wlState.cidUniverseCache && wlState.cidUniverseCache.length) return wlState.cidUniverseCache;
  try {
    const res = await _fuJsonp('cidUniverse', {});
    if (res && res.ok && Array.isArray(res.rows)) {
      wlState.cidUniverseCache = res.rows;
      return res.rows;
    }
    console.warn('[wlBuildCidUniverse] backend error:', res && res.error);
  } catch(err) {
    console.error('[wlBuildCidUniverse] backend exception:', err);
  }
  return [];
}

function wlRenderCidAssignTable(){
  const tb = document.getElementById('mcCidTbody');
  const q = String(document.getElementById('mcCidSearch').value||'').toLowerCase().trim();
  const bu = wlState.cidBuFilter || '';
  const scope = wlState.cidScopeFilter || 'mine';
  const target = String(wlState.cidAssignTarget||'').toLowerCase();
  const filtered = wlState.cidAssignSource.filter(r => {
    // Scope first: "Mine" hides everything the target collector doesn't own.
    if (scope === 'mine' && String(r.ownedBy||'').toLowerCase() !== target) return false;
    if (bu === '__unassigned__') {
      if (String(r.ownedBy||'').trim()) return false;
    } else if (bu) {
      const rb = String(r.bu||'').trim() || '(blank)';
      if (rb !== bu) return false;
    }
    if (q && (r.cid + ' ' + r.customer + ' ' + r.bu).toLowerCase().indexOf(q) === -1) return false;
    return true;
  });
  document.getElementById('mcCidSelected').textContent = wlState.cidAssignSelected.size;
  const shownLbl = document.getElementById('mcCidShown');
  if (shownLbl) shownLbl.textContent = filtered.length;
  // How many of the currently selected rows fall inside the filtered view —
  // helps the user reconcile "I picked BU=India and 480 should be selected".
  const inViewLbl = document.getElementById('mcCidSelectedInView');
  if (inViewLbl) {
    let inView = 0;
    for (const r of filtered) if (wlState.cidAssignSelected.has(r.cid)) inView++;
    inViewLbl.textContent = inView;
  }
  if (!filtered.length){
    if (!wlState.cidAssignSource.length){
      tb.innerHTML = '<tr><td colspan="6" class="px-3 py-4 text-center text-slate-500">Customer list is empty. Make sure AR_Data has rows, then click ↻ Reload.</td></tr>';
    } else {
      tb.innerHTML = '<tr><td colspan="6" class="px-3 py-4 text-center text-slate-500">No matching CIDs for this BU / search.</td></tr>';
    }
    return;
  }
  // Cap rendered rows to 600 for perf; filter / pick a BU to narrow further
  const cap = 600;
  const view = filtered.slice(0, cap);
  // Build the collector pick list once (used for the inline "Reassign…"
  // dropdown). Keep the active-only set; rendered options are escaped.
  const collOpts = (wlState.collectors || [])
    .filter(c => c.active !== false)
    .map(c => {
      const em = String(c.email||'').trim();
      const nm = String(c.name||em||'').trim();
      return em ? `<option value="${wlEsc(em)}">${wlEsc(nm)}</option>` : '';
    })
    .filter(Boolean)
    .join('');
  tb.innerHTML = view.map(r => {
    const checked = wlState.cidAssignSelected.has(r.cid) ? 'checked' : '';
    const ownedBadge = (r.ownedBy && r.ownedBy !== wlState.cidAssignTarget)
      ? `<span style="background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:4px;font-size:10px">${wlEsc(r.ownedBy)}</span>`
      : (r.ownedBy === wlState.cidAssignTarget ? '<span style="color:#15803d;font-size:11px">— this collector</span>' : '<span class="text-slate-400 text-[11px]">unassigned</span>');
    // Inline reassign: small "↪ Reassign" pill that expands into a <select>
    // listing every collector. When the user picks a new owner we call
    // the backend single-CID reassign helper and re-render the row.
    const reassignCell = `
      <details style="display:inline-block;margin-left:6px">
        <summary style="cursor:pointer;font-size:10px;color:#1d4ed8;list-style:none">↪ Reassign</summary>
        <select class="chip mc-cid-reassign" data-mc-cid="${wlEsc(r.cid)}"
          style="padding:2px 6px;font-size:11px;margin-top:2px">
          <option value="">— pick collector —</option>
          <option value="__unassign__">🔓 Mark unassigned</option>
          ${collOpts}
        </select>
      </details>`;
    return `<tr class="border-t border-slate-100">
      <td class="px-3 py-2"><input type="checkbox" data-mc-cid="${wlEsc(r.cid)}" ${checked}></td>
      <td class="px-3 py-2 font-mono text-[11px]">${wlEsc(r.cid)}</td>
      <td class="px-3 py-2">${wlEsc(r.customer)}</td>
      <td class="px-3 py-2 text-slate-600">${wlEsc(r.bu)}</td>
      <td class="px-3 py-2 text-right">${wlFmtINR(r.openOs)}</td>
      <td class="px-3 py-2">${ownedBadge}${reassignCell}</td>
    </tr>`;
  }).join('') + (filtered.length > cap
    ? `<tr><td colspan="6" class="px-3 py-2 text-center text-slate-500 text-[11px]">… showing first ${cap} of ${filtered.length}. Pick a BU or narrow the search to see more.</td></tr>`
    : '');
  tb.querySelectorAll('input[type=checkbox][data-mc-cid]').forEach(cb => cb.addEventListener('change', () => {
    const cid = cb.getAttribute('data-mc-cid');
    if (cb.checked) wlState.cidAssignSelected.add(cid);
    else wlState.cidAssignSelected.delete(cid);
    document.getElementById('mcCidSelected').textContent = wlState.cidAssignSelected.size;
  }));
  // Wire the inline-reassign dropdowns. Pick-to-move is a backend
  // single-row update and refreshes the universe so other rows that may
  // have stale `ownedBy` (because the same CID was duplicated under more
  // than one collector — see Task #39 dedup) reflect the new canonical
  // owner the moment the user confirms.
  tb.querySelectorAll('select.mc-cid-reassign').forEach(sel => {
    sel.addEventListener('change', async () => {
      const cid = sel.getAttribute('data-mc-cid');
      const choice = sel.value;
      if (!cid || !choice) return;
      const newOwner = (choice === '__unassign__') ? '' : choice;
      // Confirm before reassigning so accidental clicks don't move CIDs.
      // (User asked: "Block + ask before reassigning".)
      const ownedNow = (wlState.cidAssignSource.find(r => r.cid === cid) || {}).ownedBy || '';
      const fromLbl = ownedNow || 'unassigned';
      const toLbl   = newOwner || 'unassigned';
      const ok = window.confirm(`Reassign CID ${cid}\nFrom: ${fromLbl}\nTo:   ${toLbl}\n\nProceed?`);
      if (!ok) { sel.value = ''; return; }
      try {
        const res = await _fuJsonp('collectorCidReassign', { cid, owner: newOwner });
        if (!res || !res.ok) {
          // Distinguish "route not deployed" from "server rejected" so the
          // user knows whether to redeploy Apps Script or to check perms.
          let m;
          if (!res) {
            m = 'No response from Apps Script. Make sure the latest code.gs is deployed and the Web App URL is current.';
          } else if (res.error) {
            m = res.error;
          } else {
            m = 'Server returned ok=false with no error. The deployed Apps Script may pre-date the collectorCidReassign route — redeploy code.gs.';
          }
          window.alert('Reassign failed: ' + m);
          sel.value = '';
          return;
        }
        // Update source in-place so the table reflects the move without a full reload.
        wlState.cidAssignSource.forEach(r => { if (r.cid === cid) r.ownedBy = newOwner; });
        // Also refresh the collector master cidCount badges (best-effort).
        try { wlLoadCollectorMaster(); } catch(_){}
        wlPopulateCidBuFilter();
        wlRenderCidAssignTable();
      } catch(err) {
        window.alert('Reassign failed: ' + (err && err.message || err));
        sel.value = '';
      }
    });
  });
}

// ---- Paste-CIDs box: turn pasted text into selections in one shot ----
function wlPasteCidsApply(){
  const txt = String(document.getElementById('mcCidPasteText').value||'');
  const msg = document.getElementById('mcCidPasteMsg');
  if (!txt.trim()) { msg.textContent = 'Paste at least one CID.'; msg.style.color = '#b91c1c'; return; }
  const tokens = txt.split(/[\s,;\r\n]+/).map(t => t.trim()).filter(Boolean);
  if (!tokens.length) { msg.textContent = 'No CIDs parsed.'; msg.style.color = '#b91c1c'; return; }
  // Build a set of known CIDs in the universe
  const known = new Set(wlState.cidAssignSource.map(r => r.cid));
  let added = 0, unknown = 0;
  tokens.forEach(t => {
    if (known.has(t)) { wlState.cidAssignSelected.add(t); added += 1; }
    else unknown += 1;
  });
  msg.textContent = `Added ${added} CID${added===1?'':'s'}` + (unknown ? ` · ${unknown} not found in AR_Data (skipped)` : '');
  msg.style.color = unknown ? '#b45309' : '#15803d';
  wlRenderCidAssignTable();
}

// ---- Bulk CSV upload (Email,CID) ----
function wlParseBulkCsv(text){
  // Tolerant CSV parser: split on lines, drop header if first row contains 'email' header
  const out = [];
  const lines = String(text||'').split(/\r?\n/);
  for (let i=0; i<lines.length; i++) {
    let line = lines[i].trim();
    if (!line) continue;
    // skip header
    if (i===0 && /email/i.test(line) && /cid/i.test(line)) continue;
    // split by , ; or tab
    const parts = line.split(/[,;\t]/).map(s => s.trim().replace(/^["']|["']$/g,''));
    if (parts.length < 2) continue;
    const email = parts[0].toLowerCase();
    const cid   = parts[1];
    if (!email || !cid) continue;
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) continue;
    out.push({ email, cid });
  }
  return out;
}

function wlBulkPreview(parsed){
  const box = document.getElementById('mcBulkPreview');
  const acts = document.getElementById('mcBulkActions');
  if (!parsed || !parsed.length) {
    box.innerHTML = '<span style="color:#b91c1c">No valid Email,CID rows parsed.</span>';
    acts.style.display = 'none';
    wlState.bulkParsed = null;
    return;
  }
  const byEmail = {};
  parsed.forEach(r => { (byEmail[r.email] = byEmail[r.email] || []).push(r.cid); });
  const collectorEmails = new Set((wlState.collectors||[]).map(c => String(c.email||'').toLowerCase()));
  let html = `<div class="mt-1">Parsed <b>${parsed.length}</b> rows · <b>${Object.keys(byEmail).length}</b> collectors</div>`;
  html += '<table class="w-full text-[11px] mt-2 border border-amber-200 rounded"><thead class="bg-amber-100/60"><tr class="text-left"><th class="px-2 py-1">Email</th><th class="px-2 py-1 text-right">CIDs</th><th class="px-2 py-1">Status</th></tr></thead><tbody>';
  Object.keys(byEmail).forEach(em => {
    const ok = collectorEmails.has(em);
    html += `<tr class="border-t border-amber-100"><td class="px-2 py-1 font-mono">${wlEsc(em)}</td><td class="px-2 py-1 text-right">${byEmail[em].length}</td><td class="px-2 py-1">${ok?'<span style="color:#15803d">✓ in Collector_Master</span>':'<span style="color:#b91c1c">✗ NOT a collector — will be skipped</span>'}</td></tr>`;
  });
  html += '</tbody></table>';
  box.innerHTML = html;
  acts.style.display = '';
  wlState.bulkParsed = parsed;
}

function wlBulkReset(){
  document.getElementById('mcBulkPreview').innerHTML = '';
  document.getElementById('mcBulkActions').style.display = 'none';
  document.getElementById('mcBulkMsg').textContent = '';
  document.getElementById('mcBulkFile').value = '';
  wlState.bulkParsed = null;
}

async function wlBulkApply(){
  if (!wlState.bulkParsed || !wlState.bulkParsed.length) return;
  const mode = (document.querySelector('input[name=mcBulkMode]:checked')||{}).value || 'merge';
  const msg = document.getElementById('mcBulkMsg');
  const btn = document.getElementById('mcBulkSave');
  btn.disabled = true; const lbl = btn.textContent; btn.textContent = 'Applying…';
  msg.textContent = '';
  try {
    const res = await _fuJsonp('bulkAssignCids', {
      mode,
      payload: JSON.stringify(wlState.bulkParsed)
    });
    if (res && res.ok) {
      msg.style.color = '#15803d';
      const ok = (res.report||[]).filter(r => r.ok).length;
      const skipped = (res.report||[]).filter(r => !r.ok).length;
      msg.textContent = `✓ Applied · ${ok} collectors updated${skipped?', '+skipped+' skipped':''}`;
      await wlLoadCollectorMaster();
      await wlLoad();
    } else {
      msg.style.color = '#b91c1c';
      msg.textContent = (res && res.error) || 'Bulk apply failed';
    }
  } catch(err) {
    msg.style.color = '#b91c1c';
    msg.textContent = err.message || 'Network error';
  } finally {
    btn.disabled = false; btn.textContent = lbl;
  }
}

function wlBulkDownloadTemplate(){
  const csv = 'Email,CID\ncollector1@gofynd.com,12345\ncollector1@gofynd.com,67890\ncollector2@gofynd.com,11111';
  const blob = new Blob([csv], { type:'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'collector_cid_bulk_template.csv';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function wlSaveCidAssignments(){
  if (!wlState.cidAssignTarget) return;
  const msg = document.getElementById('mcAssignMsg');
  msg.textContent = '';
  const cids = [...wlState.cidAssignSelected];
  // Pre-flight: warn the admin if any of the CIDs about to be saved are
  // currently owned by ANOTHER collector. They'll be moved (latest-wins).
  const target = String(wlState.cidAssignTarget||'').toLowerCase();
  const willMove = wlState.cidAssignSource
    .filter(r => wlState.cidAssignSelected.has(r.cid) &&
                 r.ownedBy && String(r.ownedBy).toLowerCase() !== target)
    .map(r => ({ cid: r.cid, from: r.ownedBy, customer: r.customer }));
  if (willMove.length) {
    const preview = willMove.slice(0,5).map(w => `• ${w.cid} (${w.customer || 'unnamed'}) — currently with ${w.from}`).join('\n');
    const more = willMove.length > 5 ? `\n… and ${willMove.length-5} more` : '';
    const ok = window.confirm(
      `${willMove.length} CID${willMove.length===1?'':'s'} will be MOVED from another collector to ${target}.\n\n` +
      `One CID can only have one collector, so the previous owner will lose them.\n\n` +
      preview + more + '\n\nContinue?'
    );
    if (!ok) { msg.textContent = 'Save cancelled.'; msg.style.color = '#64748b'; return; }
  }
  const btn = document.getElementById('mcAssignSave');
  btn.disabled = true; const lbl = btn.textContent; btn.textContent = 'Saving…';
  try {
    const res = await _fuJsonp('collectorCidsSet', { email: wlState.cidAssignTarget, cids: cids.join(',') });
    if (res && res.ok) {
      let extra = '';
      if (res.reassignedCount) {
        const lines = [];
        const ra = res.reassigned || {};
        Object.keys(ra).forEach(em => {
          lines.push(`${ra[em].length} from ${em}`);
        });
        extra = ` · ↪ moved ${res.reassignedCount} CIDs (${lines.join(', ')})`;
      }
      msg.textContent = `✓ Saved · ${res.count} CIDs assigned${extra}`; msg.style.color = '#15803d';
      await wlLoadCollectorMaster();
      // Re-check conflicts after the write
      try { await wlCheckConflicts(true); } catch(_){}
    } else {
      msg.textContent = (res&&res.error)||'Save failed'; msg.style.color = '#b91c1c';
    }
  } catch(err) { msg.textContent = err.message; msg.style.color = '#b91c1c'; }
  finally { btn.disabled = false; btn.textContent = lbl; }
}

// Detect existing duplicate ownership and surface a banner with a "Repair" action.
// Called on Manage Collectors open and after every assignment save.
async function wlCheckConflicts(silent){
  const banner = document.getElementById('mcConflictBanner');
  if (!banner) return;
  try {
    const res = await _fuJsonp('collectorCidsConflicts', {});
    if (!res || !res.ok) {
      if (!silent) {
        banner.style.display = '';
        banner.innerHTML = `<span style="color:#b91c1c">Could not check for duplicate assignments: ${wlEsc((res&&res.error)||'unknown')}</span>`;
      }
      return;
    }
    if (!res.total) {
      banner.style.display = 'none';
      banner.innerHTML = '';
      return;
    }
    // Build a compact preview (first 5 conflicts) + a Repair button.
    const preview = (res.conflicts||[]).slice(0,5).map(c => {
      const owners = (c.owners||[]).map(o => `${o.email}${o.addedOn?` (${o.addedOn})`:''}`).join(' vs ');
      return `<div style="font-family:monospace;font-size:11px">• CID <b>${wlEsc(c.cid)}</b> — ${wlEsc(owners)}</div>`;
    }).join('');
    const more = res.total > 5 ? `<div style="font-size:11px;color:#92400e">… and ${res.total-5} more</div>` : '';
    banner.style.display = '';
    banner.innerHTML =
      `<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
         <div>
           <div style="font-weight:600;color:#92400e">⚠ ${res.total} CID${res.total===1?' is':'s are'} currently assigned to more than one collector</div>
           <div style="font-size:11px;color:#78350f;margin-top:2px">Each CID should have exactly one owner. Click <b>Repair</b> to keep only the most-recently assigned owner per CID (older assignments will be dropped).</div>
           <div style="margin-top:6px">${preview}${more}</div>
         </div>
         <button id="mcConflictRepair" class="chip" style="background:#b45309;color:#fff;border-color:#b45309;white-space:nowrap">🔧 Repair conflicts</button>
       </div>`;
    document.getElementById('mcConflictRepair').addEventListener('click', wlRepairConflicts);
  } catch(err) {
    if (!silent) {
      banner.style.display = '';
      banner.innerHTML = `<span style="color:#b91c1c">Conflict check failed: ${wlEsc(err.message||err)}</span>`;
    }
  }
}

async function wlRepairConflicts(){
  const banner = document.getElementById('mcConflictBanner');
  if (!banner) return;
  if (!window.confirm(
    'Repair duplicate CID ownership?\n\n' +
    'For every CID owned by more than one collector, this will KEEP the most-recently assigned owner and REMOVE the older row(s) from Collector_CIDs.\n\n' +
    'This cannot be undone via the UI. Continue?'
  )) return;
  const btn = document.getElementById('mcConflictRepair');
  if (btn) { btn.disabled = true; btn.textContent = 'Repairing…'; }
  try {
    const res = await _fuJsonp('collectorCidsResolveConflicts', {});
    if (!res || !res.ok) {
      banner.innerHTML = `<span style="color:#b91c1c">Repair failed: ${wlEsc((res&&res.error)||'unknown')}</span>`;
      return;
    }
    banner.innerHTML =
      `<div style="color:#166534">
         ✓ Repaired <b>${res.resolved}</b> conflicting CID${res.resolved===1?'':'s'} · ${(res.dropped||[]).length} stale row${(res.dropped||[]).length===1?'':'s'} removed.
         Refresh complete.
       </div>`;
    setTimeout(() => { banner.style.display = 'none'; }, 5000);
    await wlLoadCollectorMaster();
  } catch(err) {
    banner.innerHTML = `<span style="color:#b91c1c">Repair exception: ${wlEsc(err.message||err)}</span>`;
  }
}

function wireWorklist(){
  // P2P fields toggle based on outcome. When switching TO Promise to Pay, also auto-fill
  // the amount with the sum of selected (or focused) invoice open balances. The field stays
  // editable — once the collector types in it, the user-edited flag suppresses further auto-fills.
  document.getElementById('wlNoteOutcome').addEventListener('change', e => {
    const show = e.target.value === 'Promise to Pay';
    document.querySelectorAll('.wl-p2p-only').forEach(el => el.style.display = show ? '' : 'none');
    if (show) {
      // Treat re-selecting the outcome as a fresh intent — let auto-fill apply
      wlState.p2pAmountUserEdited = false;
      wlMaybeAutoFillP2P();
    } else {
      // Outcome moved away from P2P — clear the field and reset the edited flag
      const amtEl = document.getElementById('wlNoteP2PAmt');
      if (amtEl) amtEl.value = '';
      wlState.p2pAmountUserEdited = false;
    }
    // Outcome is mandatory — recompute Save button state every time it changes
    wlSyncBulkUi();
  });
  // Collector typing in P2P amount → respect their value, stop auto-overwriting
  const p2pAmtEl = document.getElementById('wlNoteP2PAmt');
  if (p2pAmtEl) p2pAmtEl.addEventListener('input', () => { wlState.p2pAmountUserEdited = true; });
  document.getElementById('wlReload').addEventListener('click', () => {
    // Retry identity (in case the first whoAmI call timed out and left the
    // header stuck on "Loading…") then refresh the list + daily report.
    try {
      if (window.__SERVED_BY_APPS_SCRIPT__ && typeof applyAccessControl === 'function') {
        applyAccessControl();
      } else if (typeof _wlSetWhoBadgeFallback === 'function') {
        _wlSetWhoBadgeFallback('local');
      }
    } catch(_){}
    wlLoad(); wlLoadDaily();
  });
  // ===== Worklist tab strip (To-Do List | Reports) =====
  (function _wlInitTabs(){
    const tabs = document.querySelectorAll('#wlTabs .wl-tab');
    if (!tabs || !tabs.length) return;
    function activate(name){
      tabs.forEach(t => {
        const isActive = (t.getAttribute('data-wl-tab') === name);
        t.classList.toggle('wl-tab-active', isActive);
        t.setAttribute('aria-selected', isActive ? 'true' : 'false');
        t.style.borderBottomColor = isActive ? '#2563eb' : 'transparent';
        t.style.color = isActive ? '#1d4ed8' : '#64748b';
        t.style.fontWeight = isActive ? '600' : '500';
      });
      document.querySelectorAll('[data-wl-pane]').forEach(p => {
        p.style.display = (p.getAttribute('data-wl-pane') === name) ? '' : 'none';
      });
      // Lazy-load Daily report when the Reports tab is first activated
      if (name === 'reports' && !window.__wlDailyLoadedOnce){
        window.__wlDailyLoadedOnce = true;
        try { if (typeof wlLoadDaily === 'function') wlLoadDaily(); } catch(_){}
      }
    }
    tabs.forEach(t => t.addEventListener('click', () => activate(t.getAttribute('data-wl-tab'))));
  })();
  // Status filter buttons (replaces the old dropdown)
  document.querySelectorAll('#wlStatusBtns .wl-status-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const v = btn.getAttribute('data-status') || 'all';
      wlState.statusFilter = v;
      document.querySelectorAll('#wlStatusBtns .wl-status-btn').forEach(b => b.classList.remove('wl-status-active'));
      btn.classList.add('wl-status-active');
      wlApplyFilter();
    });
  });
  document.getElementById('wlSearch').addEventListener('input', wlApplyFilter);
  document.getElementById('wlNotesClose').addEventListener('click', () => { document.getElementById('wlNotesModal').style.display = 'none'; });
  // Invoice-list filters inside the Notes modal
  const wlAgeEl = document.getElementById('wlNotesAgeing');
  if (wlAgeEl) wlAgeEl.addEventListener('change', () => {
    wlState.notesAgeingFilter = wlAgeEl.value || 'all';
    wlRenderNotesStatusBtns(); // counts depend on ageing too
    wlRenderInvoiceList();
    wlSyncBulkUi();
  });
  const wlSrcEl = document.getElementById('wlNotesSearch');
  if (wlSrcEl) wlSrcEl.addEventListener('input', () => {
    wlState.notesSearch = wlSrcEl.value || '';
    wlRenderNotesStatusBtns();
    wlRenderInvoiceList();
    wlSyncBulkUi();
  });
  const wlRstEl = document.getElementById('wlNotesFiltersReset');
  if (wlRstEl) wlRstEl.addEventListener('click', () => {
    wlState.notesStatusFilter = 'all';
    wlState.notesAgeingFilter = 'all';
    wlState.notesSearch = '';
    if (wlAgeEl) wlAgeEl.value = 'all';
    if (wlSrcEl) wlSrcEl.value = '';
    wlRenderNotesStatusBtns();
    wlRenderInvoiceList();
    wlSyncBulkUi();
  });
  document.getElementById('wlNoteSave').addEventListener('click', wlSaveNote);
  // Header "Select all" checkbox — toggles all invoices in the currently-visible type filter
  const wlSelAll = document.getElementById('wlNotesSelectAll');
  if (wlSelAll) {
    wlSelAll.addEventListener('change', () => {
      const d = wlState.currentInvoiceData;
      if (!d) return;
      const today = d.today || wlTodayStr();
      const desired = wlSelAll.checked;
      (d.groups||[]).forEach(g => {
        if (wlState.currentTypeFilter !== 'ALL' && (g.type||'Other') !== wlState.currentTypeFilter) return;
        (g.invoices||[]).forEach(inv => {
          // Only toggle invoices that are currently VISIBLE under all active filters
          if (!wlInvoicePassesStatus(inv, today)) return;
          if (!wlInvoicePassesAgeing(inv)) return;
          if (!wlInvoicePassesSearch(inv)) return;
          if (desired) wlState.selectedInvoiceNos.add(inv.invoiceNo);
          else wlState.selectedInvoiceNos.delete(inv.invoiceNo);
        });
      });
      wlRenderInvoiceList();
      wlSyncBulkUi();
      wlMaybeAutoFillP2P();
    });
  }
  document.getElementById('wlDailyReload').addEventListener('click', wlLoadDaily);
  document.getElementById('wlDailyExcel').addEventListener('click', wlDownloadDailyExcel);
  // Range buttons (Today / 7 days / Monthly / All / Custom)
  document.querySelectorAll('#wlDailyRangeBtns .wl-range-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const v = btn.getAttribute('data-range') || 'today';
      wlState.dailyRange = v;
      document.querySelectorAll('#wlDailyRangeBtns .wl-range-btn').forEach(b => b.classList.remove('wl-status-active'));
      btn.classList.add('wl-status-active');
      const customBox = document.getElementById('wlDailyCustomBox');
      if (customBox) customBox.style.display = (v === 'custom') ? 'flex' : 'none';
      if (v !== 'custom') wlLoadDaily();
    });
  });
  const dailyCustomApply = document.getElementById('wlDailyCustomApply');
  if (dailyCustomApply) dailyCustomApply.addEventListener('click', () => {
    const f = document.getElementById('wlDailyFrom').value || '';
    const t = document.getElementById('wlDailyTo').value || '';
    if (!f && !t) { alert('Pick at least one date.'); return; }
    wlState.dailyRange = 'custom';
    wlState.dailyFrom = f;
    wlState.dailyTo = t;
    wlLoadDaily();
  });
  document.getElementById('wlManageCollectors').addEventListener('click', wlOpenManageCollectors);
  const mcDl = document.getElementById('mcDownload');
  if (mcDl) mcDl.addEventListener('click', wlDownloadCollectorAssignment);
  document.getElementById('wlMcClose').addEventListener('click', () => { document.getElementById('wlMcModal').style.display = 'none'; });

  // ===== Manage Collectors tab strip (Add/Update | Assign CIDs) =====
  window.mcSwitchTab = function(name){
    const tabs = document.querySelectorAll('#mcTabs .mc-tab');
    tabs.forEach(t => {
      const isActive = (t.getAttribute('data-mc-tab') === name);
      t.classList.toggle('mc-tab-active', isActive);
      t.setAttribute('aria-selected', isActive ? 'true' : 'false');
      t.style.borderBottomColor = isActive ? '#2563eb' : 'transparent';
      t.style.color = isActive ? '#1d4ed8' : '#64748b';
      t.style.fontWeight = isActive ? '600' : '500';
    });
    document.querySelectorAll('[data-mc-pane]').forEach(p => {
      p.style.display = (p.getAttribute('data-mc-pane') === name) ? '' : 'none';
    });
    if (name === 'assign') {
      try { mcSyncAssignPicker(); } catch(_){}
    }
  };
  document.querySelectorAll('#mcTabs .mc-tab').forEach(t =>
    t.addEventListener('click', () => mcSwitchTab(t.getAttribute('data-mc-tab')))
  );

  // Populate the quick-pick collector dropdown from wlState.collectors
  window.mcSyncAssignPicker = function(){
    const sel = document.getElementById('mcAssignPick');
    if (!sel) return;
    const prev = sel.value || (wlState.cidAssignTarget || '');
    const list = (wlState.collectors || []).slice().sort((a,b) =>
      String(a.name||a.email||'').localeCompare(String(b.name||b.email||''))
    );
    sel.innerHTML = '<option value="">— Select collector —</option>' +
      list.map(c => {
        const lbl = `${(c.name||'').trim() || c.email}${c.active ? '' : ' (suspended)'}`;
        return `<option value="${(c.email||'').replace(/"/g,'&quot;')}">${lbl.replace(/</g,'&lt;')}</option>`;
      }).join('');
    if (prev && list.some(c => c.email === prev)) sel.value = prev;
  };

  // Quick-pick "Load CIDs" button
  const _pickGo = document.getElementById('mcAssignPickGo');
  if (_pickGo) _pickGo.addEventListener('click', () => {
    const sel = document.getElementById('mcAssignPick');
    const msg = document.getElementById('mcAssignPickMsg');
    const em = sel ? (sel.value || '').trim() : '';
    if (!em) { if (msg) msg.textContent = 'Pick a collector first.'; return; }
    if (msg) msg.textContent = '';
    wlStartAssignCids(em);
  });
  // Pressing Enter inside the picker also triggers Load
  const _pickSel = document.getElementById('mcAssignPick');
  if (_pickSel) _pickSel.addEventListener('change', () => {
    const msg = document.getElementById('mcAssignPickMsg');
    if (msg) msg.textContent = '';
  });
  document.getElementById('mcSaveCollector').addEventListener('click', wlSaveCollector);
  document.getElementById('mcCidSearch').addEventListener('input', wlRenderCidAssignTable);
  // Shared filter helper — MUST match wlRenderCidAssignTable's filter logic
  // so "Select all (filtered)" / "Clear all" honour BOTH the BU dropdown and
  // the search text. Previously only the search text was applied here, so
  // picking "India (480)" and clicking Select-all selected the entire
  // 606-row universe instead of just the 480 filtered rows.
  function wlGetFilteredAssignRows(){
    const q = String(document.getElementById('mcCidSearch').value||'').toLowerCase().trim();
    const bu = wlState.cidBuFilter || '';
    const scope = wlState.cidScopeFilter || 'mine';
    const target = String(wlState.cidAssignTarget||'').toLowerCase();
    return wlState.cidAssignSource.filter(r => {
      if (scope === 'mine' && String(r.ownedBy||'').toLowerCase() !== target) return false;
      if (bu === '__unassigned__') {
        if (String(r.ownedBy||'').trim()) return false;
      } else if (bu) {
        const rb = String(r.bu||'').trim() || '(blank)';
        if (rb !== bu) return false;
      }
      if (q && (r.cid + ' ' + r.customer + ' ' + r.bu).toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
  }
  // Wire the Mine / All scope chips. Toggling scope re-renders both the
  // BU dropdown (so the count chips line up) and the assignment table.
  // We do NOT clear the in-progress selection — the user may want to
  // bulk-claim across scopes.
  document.querySelectorAll('#mcScopeChips .mc-scope-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-mc-scope') || 'mine';
      if (target === wlState.cidScopeFilter) return;
      wlState.cidScopeFilter = target;
      // Toggle active styling
      document.querySelectorAll('#mcScopeChips .mc-scope-btn').forEach(b => {
        b.classList.remove('mc-scope-active');
        b.style.background = '#fff';
        b.style.color = '#475569';
        b.style.borderColor = '#cbd5e1';
      });
      btn.classList.add('mc-scope-active');
      btn.style.background = '#1d4ed8';
      btn.style.color = '#fff';
      btn.style.borderColor = '#1d4ed8';
      wlPopulateCidBuFilter();
      wlRenderCidAssignTable();
    });
  });
  document.getElementById('mcCidSelectAll').addEventListener('click', () => {
    wlGetFilteredAssignRows().forEach(r => wlState.cidAssignSelected.add(r.cid));
    wlRenderCidAssignTable();
  });
  document.getElementById('mcCidClearAll').addEventListener('click', () => {
    // If a BU/search filter is active, only clear within the visible scope.
    // With no filter active, behave like a true "clear everything".
    const bu = wlState.cidBuFilter || '';
    const q = String(document.getElementById('mcCidSearch').value||'').toLowerCase().trim();
    if (bu || q) {
      wlGetFilteredAssignRows().forEach(r => wlState.cidAssignSelected.delete(r.cid));
    } else {
      wlState.cidAssignSelected.clear();
    }
    wlRenderCidAssignTable();
  });
  document.getElementById('mcAssignSave').addEventListener('click', wlSaveCidAssignments);

  // BU filter + Paste box + Reload inside the Assign modal
  const buSel = document.getElementById('mcCidBuFilter');
  if (buSel) buSel.addEventListener('change', e => {
    wlState.cidBuFilter = e.target.value || '';
    wlRenderCidAssignTable();
  });
  const reloadBtn = document.getElementById('mcCidReload');
  if (reloadBtn) reloadBtn.addEventListener('click', async () => {
    if (!wlState.cidAssignTarget) return;
    wlState.cidUniverseCache = null;  // force fresh fetch
    // If state.data is empty, kick off live sync first (best-effort)
    try { if ((window.state && window.state.data || []).length === 0 && typeof fetchDataNow === 'function') { await fetchDataNow(false); } } catch(_) {}
    wlStartAssignCids(wlState.cidAssignTarget);
  });
  const pasteOpen = document.getElementById('mcCidPaste');
  if (pasteOpen) pasteOpen.addEventListener('click', () => {
    const box = document.getElementById('mcCidPasteBox');
    box.style.display = (box.style.display === 'none' || !box.style.display) ? 'block' : 'none';
    document.getElementById('mcCidPasteMsg').textContent = '';
  });
  const pasteApply = document.getElementById('mcCidPasteApply');
  if (pasteApply) pasteApply.addEventListener('click', wlPasteCidsApply);
  const pasteClose = document.getElementById('mcCidPasteClose');
  if (pasteClose) pasteClose.addEventListener('click', () => { document.getElementById('mcCidPasteBox').style.display = 'none'; });

  // Bulk CSV upload at top of Manage Collectors modal
  const bulkFile = document.getElementById('mcBulkFile');
  if (bulkFile) bulkFile.addEventListener('change', async e => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    const txt = await f.text();
    const parsed = wlParseBulkCsv(txt);
    wlBulkPreview(parsed);
  });
  const bulkSave = document.getElementById('mcBulkSave');
  if (bulkSave) bulkSave.addEventListener('click', wlBulkApply);
  const bulkCancel = document.getElementById('mcBulkCancel');
  if (bulkCancel) bulkCancel.addEventListener('click', wlBulkReset);
  const bulkTpl = document.getElementById('mcBulkTemplate');
  if (bulkTpl) bulkTpl.addEventListener('click', wlBulkDownloadTemplate);

  // Admin scope dropdown
  document.getElementById('wlCollectorScope').addEventListener('change', e => {
    wlState.scope = e.target.value || '';
    wlLoad();
  });
}

// ===== Access Matrix (admin-only) ============================================
// Maps role -> default tab keys (must match the dashboard's data-target values).
const ACM_ROLE_DEFAULTS = {
  'Bank Ops':             ['bank'],
  'Collections Analyst':  ['dashboard','customers','worklist'],
  'AR Owner':             ['dashboard','customers','worklist'],
  'BU Finance Partner':   ['dashboard','customers'],
  'PDD / Bank Lead':      ['pdd','bank'],
  'Collections Manager':  ['dashboard','customers','worklist','followups','activity'],
  'Finance Director':     ['dashboard','customers','worklist','pdd','bank','activity','reports'],
  'Custom':               []
};

const acmState = { me: null, isAdmin: false, rows: [], editingEmail: null };

function acmEsc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// Client-side password rule (mirrors _authValidatePasswordRules_ in code.gs).
// Returns null if OK, otherwise a human-readable error string.
function acmValidatePasswordRules(pw){
  const s = String(pw == null ? '' : pw);
  if (s.length < 6) return 'Password must be at least 6 characters.';
  if (!/[A-Za-z]/.test(s)) return 'Password must contain at least one letter.';
  if (!/[0-9]/.test(s))    return 'Password must contain at least one number.';
  if (!/[^A-Za-z0-9]/.test(s)) return 'Password must contain at least one symbol.';
  return null;
}

// Build the "Tabs granted" checkbox list by walking the sidebar (#sideNav).
// This means when a new tab is added to the sidebar it automatically shows
// up in the User Management form — no template edits needed. Grouping tracks
// .sb-section headers and .sb-group-toggle labels; admin-only tabs (`acm`
// and anything tagged `admin-only`) are skipped so they can never be granted
// to non-admins. Runs on page init AND whenever the ACM section is opened
// (defensive — sidebar composition could change between visits).
function renderAcmTabsCheckboxes(){
  const box = document.getElementById('acmTabsBox');
  const sidebar = document.getElementById('sideNav');
  if (!box || !sidebar) return; // sidebar hasn't rendered yet — no-op

  // Walk the sidebar in DOM order, grouping tab-items under their nearest
  // preceding section header / group toggle.
  const groups = new Map(); // groupLabel → [{key,label}, ...]
  const order = [];         // group labels in first-seen order
  let currentGroup = 'OTHER';

  const walker = (parent) => {
    Array.prototype.forEach.call(parent.children || [], (el) => {
      if (!el || el.nodeType !== 1) return;
      if (el.classList && el.classList.contains('sb-section')) {
        currentGroup = (el.textContent || '').trim().toUpperCase() || 'OTHER';
      } else if (el.classList && el.classList.contains('sb-group-toggle')) {
        const lbl = el.querySelector('.sb-label');
        currentGroup = ((lbl && lbl.textContent) || (el.textContent || '')).trim().toUpperCase() || 'OTHER';
      } else if (el.classList && el.classList.contains('tab-item') && el.getAttribute('data-target')) {
        const key = String(el.getAttribute('data-target') || '').trim();
        if (!key) return;
        if (key === 'acm') return;                              // never grantable
        if (el.classList.contains('admin-only')) return;        // defense-in-depth
        const lbl = el.querySelector('.sb-label');
        const label = ((lbl && lbl.textContent) || key).trim();
        if (!groups.has(currentGroup)) { groups.set(currentGroup, []); order.push(currentGroup); }
        groups.get(currentGroup).push({key: key, label: label});
      } else if (el.children && el.children.length) {
        // Descend into wrappers like #arActivityChildren so nested tab-items
        // are still discovered — the currentGroup carries over from the
        // preceding sb-group-toggle.
        walker(el);
      }
    });
  };
  walker(sidebar);

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const html = order.map((group, idx) => {
    const items = groups.get(group) || [];
    const chks = items.map((it) => (
      '<label><input type="checkbox" value="' + esc(it.key) + '"/> ' + esc(it.label) + '</label>'
    )).join('');
    const marginCls = idx === 0 ? '' : ' mt-1';
    return (
      '<div class="flex flex-wrap items-center gap-3' + marginCls + '">' +
        '<span class="text-[10px] uppercase tracking-wide text-slate-500 min-w-[110px]">' + esc(group) + '</span>' +
        chks +
      '</div>'
    );
  }).join('');
  box.innerHTML = html;
}

function acmSetTabsChecks(tabs){
  const want = new Set((tabs||[]).map(t=>String(t).trim()).filter(Boolean));
  document.querySelectorAll('#acmTabsBox input[type=checkbox]').forEach(cb=>{
    cb.checked = want.has(cb.value);
  });
}
function acmGetTabsChecks(){
  return Array.from(document.querySelectorAll('#acmTabsBox input[type=checkbox]'))
    .filter(cb => cb.checked).map(cb => cb.value);
}
function acmResetForm(){
  acmState.editingEmail = null;
  document.getElementById('acmFormTitle').textContent = 'Add stakeholder';
  ['acmUsername','acmEmail','acmPassword'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('acmProv').value = new Date().toISOString().slice(0,10);
  acmSetTabsChecks([]);
  document.getElementById('acmEmail').disabled = false;
  document.getElementById('acmUsername').disabled = false;
  document.getElementById('acmPassword').placeholder = 'Set password (min 6 chars, mix of letters, numbers, symbols)';
  document.getElementById('acmFormMsg').textContent = '';
  // Reset password visibility toggle (input back to password, eye back to closed-eye SVG)
  const pw = document.getElementById('acmPassword');
  if (pw) pw.type = 'password';
  const pwEye = document.getElementById('acmPasswordEye');
  if (pwEye && typeof PASSWORD_EYE_SVG !== 'undefined') {
    pwEye.innerHTML = PASSWORD_EYE_SVG;
    pwEye.setAttribute('aria-label', 'Show password');
  }
}
function acmEditRow(rec){
  acmState.editingEmail = rec.email;
  document.getElementById('acmFormTitle').textContent = 'Editing ' + rec.email;
  document.getElementById('acmUsername').value = rec.username || '';
  document.getElementById('acmEmail').value = rec.email || '';
  document.getElementById('acmEmail').disabled = true; // lock email = primary key
  document.getElementById('acmPassword').value = '';
  document.getElementById('acmPassword').placeholder = 'Leave blank to keep current password';
  document.getElementById('acmProv').value = (String(rec.provisionedOn||'')).slice(0,10) || new Date().toISOString().slice(0,10);
  acmSetTabsChecks(rec.tabs || []);
  document.getElementById('acmFormMsg').textContent = '';
  const pw = document.getElementById('acmPassword');
  if (pw) pw.type = 'password';
  const pwEye = document.getElementById('acmPasswordEye');
  if (pwEye && typeof PASSWORD_EYE_SVG !== 'undefined') {
    pwEye.innerHTML = PASSWORD_EYE_SVG;
    pwEye.setAttribute('aria-label', 'Show password');
  }
  document.getElementById('acmFormTitle').scrollIntoView({behavior:'smooth', block:'start'});
}
function acmRenderTable(){
  const tb = document.getElementById('acmTbody');
  if(!acmState.rows.length){
    tb.innerHTML = '<tr><td colspan="6" class="px-3 py-6 text-center text-slate-500">No stakeholders yet. Add one above.</td></tr>';
    return;
  }
  tb.innerHTML = acmState.rows.map((r, i)=> {
    const statusBadge = r.active
      ? '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:9999px;font-weight:600">Active</span>'
      : '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:9999px;font-weight:600">Revoked</span>';
    const isAdminRow = String(r.email).toLowerCase() === String(acmState.me||'').toLowerCase();
    return `<tr class="border-t border-slate-100">
      <td class="px-3 py-2 font-medium">${acmEsc(r.username || r.name || '—')}</td>
      <td class="px-3 py-2 font-mono text-[11px]">${acmEsc(r.email)}</td>
      <td class="px-3 py-2 text-[11px]">${(r.tabs||[]).map(acmEsc).join(', ') || '<span class="text-slate-400">—</span>'}</td>
      <td class="px-3 py-2 text-[11px]">${acmEsc(String(r.provisionedOn||'').slice(0,10))}</td>
      <td class="px-3 py-2">${statusBadge}</td>
      <td class="px-3 py-2">
        <button class="chip" data-acm-edit="${acmEsc(r.email)}" style="padding:2px 8px;font-size:11px">Edit</button>
        ${isAdminRow ? '' : `<button class="chip" data-acm-del="${acmEsc(r.email)}" style="padding:2px 8px;font-size:11px;background:#fef2f2;color:#991b1b;border-color:#fecaca">Remove</button>`}
      </td>
    </tr>`;
  }).join('');
  // Wire row buttons
  tb.querySelectorAll('[data-acm-edit]').forEach(b=> b.addEventListener('click', ()=>{
    const em = b.getAttribute('data-acm-edit');
    const rec = acmState.rows.find(r=>r.email===em);
    if(rec) acmEditRow(rec);
  }));
  tb.querySelectorAll('[data-acm-del]').forEach(b=> b.addEventListener('click', async ()=>{
    const em = b.getAttribute('data-acm-del');
    if(!confirm('Revoke access for ' + em + '?')) return;
    b.disabled = true; b.textContent = 'Removing…';
    try {
      const res = await _fuJsonp('acmDelete', { email: em });
      if(!res || !res.ok){ alert((res&&res.error) || 'Delete failed'); b.disabled=false; b.textContent='Remove'; return; }
      await acmLoad();
    } catch(err){ alert(err.message); b.disabled=false; b.textContent='Remove'; }
  }));
}
async function acmLoad(){
  const tb = document.getElementById('acmTbody');
  tb.innerHTML = '<tr><td colspan="6" class="px-3 py-6 text-center text-slate-500">Loading…</td></tr>';
  try {
    const res = await _fuJsonp('acmList', {});
    // Verbose diagnostics so we can see what's actually coming back from Apps Script.
    console.log('[acmLoad] raw response:', res);
    if(res === undefined || res === null){
      tb.innerHTML = `<tr><td colspan="6" class="px-3 py-6 text-center" style="color:#b91c1c">
        Server returned empty response. The deployed Apps Script does not have the <code>acmList</code> route.<br>
        <span style="font-size:11px;color:#64748b">Fix: open Apps Script → paste latest <code>code.gs</code> → Deploy → <b>New version</b> (Save is not enough).</span>
      </td></tr>`;
      return;
    }
    if(!res.ok){
      const errTxt = res.error || JSON.stringify(res);
      tb.innerHTML = `<tr><td colspan="6" class="px-3 py-6 text-center" style="color:#b91c1c">
        ${acmEsc(errTxt)}
        ${res.viewer ? `<br><span style="font-size:11px;color:#64748b">Server saw viewer email as: <b>${acmEsc(res.viewer)}</b></span>` : ''}
      </td></tr>`;
      return;
    }
    acmState.rows = res.rows || [];
    acmRenderTable();
  } catch(err){
    console.error('[acmLoad] exception:', err);
    tb.innerHTML = `<tr><td colspan="6" class="px-3 py-6 text-center" style="color:#b91c1c">${acmEsc(err.message || String(err))}</td></tr>`;
  }
}
async function acmSave(){
  const msg = document.getElementById('acmFormMsg');
  msg.textContent = ''; msg.style.color = '';
  const email = document.getElementById('acmEmail').value.trim().toLowerCase();
  const username = document.getElementById('acmUsername').value.trim();
  const password = document.getElementById('acmPassword').value;
  if(!email){ msg.textContent = 'Email is required'; msg.style.color = '#b91c1c'; return; }
  if(!username){ msg.textContent = 'User Name is required'; msg.style.color = '#b91c1c'; return; }
  if(!/^[A-Za-z0-9._-]{3,32}$/.test(username)){
    msg.textContent = 'User Name must be 3–32 chars — letters, digits, . _ - only.';
    msg.style.color = '#b91c1c'; return;
  }
  // Client-side username uniqueness: skip when editing the current row.
  const dup = acmState.rows.find(r =>
    String(r.username||'').toLowerCase() === username.toLowerCase()
    && String(r.email||'').toLowerCase() !== email
  );
  if (dup) {
    msg.textContent = 'User Name already used by ' + dup.email;
    msg.style.color = '#b91c1c'; return;
  }
  // Password rules — required for new rows, optional for edits.
  const editing = !!acmState.editingEmail;
  if (password) {
    const pwErr = acmValidatePasswordRules(password);
    if (pwErr) { msg.textContent = pwErr; msg.style.color = '#b91c1c'; return; }
  } else if (!editing) {
    msg.textContent = 'Password is required for new users';
    msg.style.color = '#b91c1c'; return;
  }
  // Preserve the row's existing name/department/role/notes/active when editing;
  // for new rows those columns get sensible defaults on the server.
  const existing = acmState.rows.find(r => String(r.email||'').toLowerCase() === email);
  const payload = {
    email,
    username,
    name:        (existing && existing.name) || username,
    department:  (existing && existing.department) || '',
    role:        (existing && existing.role) || '',
    tabs:        acmGetTabsChecks().join(','),
    notes:       (existing && existing.notes) || '',
    provisionedOn: document.getElementById('acmProv').value || new Date().toISOString().slice(0,10),
  };
  if (password) payload.password = password;
  // Only override Active when the row already exists AND we know its current state
  // (existing rows retain their Active flag by default on the server).
  const btn = document.getElementById('acmSave');
  btn.disabled = true; const lbl = btn.textContent; btn.textContent = 'Saving…';
  try {
    const res = await _fuJsonp('acmUpsert', payload);
    if(!res || !res.ok){ msg.textContent = (res&&res.error)||'Save failed'; msg.style.color='#b91c1c'; }
    else {
      msg.textContent = '✓ ' + (res.mode==='updated'?'Updated':'Added') + ' · tabs: ' + (res.tabs||[]).join(', ');
      msg.style.color = '#15803d';
      acmResetForm();
      await acmLoad();
    }
  } catch(err){ msg.textContent = err.message; msg.style.color='#b91c1c'; }
  finally { btn.disabled = false; btn.textContent = lbl; }
}
function wireAcm(){
  document.getElementById('acmReload').addEventListener('click', acmLoad);
  document.getElementById('acmSave').addEventListener('click', acmSave);
  document.getElementById('acmReset').addEventListener('click', acmResetForm);
  // Password field eye toggle (show/hide) — uses shared SVG constants so
  // this button matches the login screen and change-password modal.
  const pwEye = document.getElementById('acmPasswordEye');
  const pwFld = document.getElementById('acmPassword');
  if (pwEye && pwFld) {
    pwEye.addEventListener('click', () => {
      const showing = pwFld.type === 'text';
      pwFld.type = showing ? 'password' : 'text';
      pwEye.innerHTML = showing ? PASSWORD_EYE_SVG : PASSWORD_EYE_OFF_SVG;
      pwEye.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
    });
  }
  // Render the tabs-granted checkboxes from the sidebar the first time this
  // wireup runs. renderAcmTabsCheckboxes is a no-op if the sidebar isn't in
  // the DOM yet — call sites (boot + ACM tab open) call it again defensively.
  try { renderAcmTabsCheckboxes(); } catch(_){}
  acmResetForm();
}

// Fallback badge state when applyAccessControl cannot identify the viewer.
// Keeps the user from staring at "Loading…" forever when the Apps Script
// whoAmI endpoint is slow, missing, or unreachable. Also unhides Manage
// Collectors so the admin can still get into the modal manually if needed.
//
// reason is a short label used to set the badge text; passing 'offline' or
// 'unknown' keeps the chip neutral (amber) instead of green/blue.
function _wlSetWhoBadgeFallback(reason){
  try {
    // Per user request: do NOT show any viewer-identity badge in the
    // To-Do List header (no "Loading", no "Offline", no local-mode label).
    // The badge stays hidden unless a real identity is resolved by
    // applyAccessControl(). The `reason` argument is accepted only for
    // backwards compatibility with existing callers.
    const wlWho = document.getElementById('wlWhoBadge');
    if (wlWho) wlWho.style.display = 'none';
    // Even when identity is unknown / offline / local, keep the Manage
    // Collectors button + collector scope dropdown accessible so the user
    // can review and filter the worklist. Backend persistence
    // (collectorUpsert, bulkAssignCids, etc.) still re-checks auth
    // server-side via _fuJsonp.
    const wlMgr = document.getElementById('wlManageCollectors');
    if (wlMgr) wlMgr.style.display = '';
    const wlScope = document.getElementById('wlCollectorScope');
    if (wlScope) wlScope.style.display = '';
    // Best-effort: try to populate the collector dropdown even in local
    // file mode. If the backend URL isn't configured the promise rejects
    // and the dropdown just stays with the default "All collectors" entry.
    try { _wlPopulateCollectorScope(); } catch(_){}
  } catch(_){}
}

// Fetches the collector master list and rewrites the wlCollectorScope
// dropdown options. Used by both the admin path (applyAccessControl) and
// the local/offline fallback so the dropdown is always populated when a
// backend URL is reachable.
function _wlPopulateCollectorScope(){
  const wlScope = document.getElementById('wlCollectorScope');
  if (!wlScope || typeof _fuJsonp !== 'function') return;
  // Pull master + cidsList in parallel for canonical dedup.
  Promise.all([
    _fuJsonp('collectorList', {}),
    _fuJsonp('collectorCidsList', {})
  ]).then(([cr, ar]) => {
    if (!cr || !cr.ok || !cr.rows) return;
    let counts = null;
    if (ar && ar.ok && ar.byEmail) {
      const byEmail = ar.byEmail || {};
      const cidToCanonical = {};
      Object.keys(byEmail).forEach(em => {
        (byEmail[em] || []).forEach(cid => {
          const k = String(cid).trim();
          if (!k) return;
          cidToCanonical[k] = em;   // last write wins
        });
      });
      counts = {};
      Object.keys(cidToCanonical).forEach(cid => {
        const em = cidToCanonical[cid];
        if (!em) return;
        counts[em] = (counts[em] || 0) + 1;
      });
    }
    wlScope.innerHTML = '<option value="">All collectors</option>' +
      cr.rows.map(c => {
        const em = String(c.email||'').toLowerCase();
        const raw = c.cidCount || 0;
        const canon = counts && (em in counts) ? counts[em] : raw;
        const lbl = `${(c.name||c.email||'').replace(/</g,'&lt;')} (${canon})`;
        return `<option value="${(c.email||'').replace(/"/g,'&quot;')}">${lbl}</option>`;
      }).join('');
  }).catch(()=>{});
}

// ========== APPLICATION-LEVEL AUTH (username/password) ============================
// Token storage — localStorage-backed so the tab survives reloads. Cleared on
// explicit sign-out. The token is a 64-char hex string issued by the server's
// authLogin route; the server enforces the 12h TTL and lockout policy, we
// just carry the string around.
const AUTH_TOKEN_KEY = 'arReceivablesAuthToken';
function authGetToken(){
  try { return localStorage.getItem(AUTH_TOKEN_KEY) || ''; } catch(_) { return ''; }
}
function authSetToken(t){
  try {
    if (t) localStorage.setItem(AUTH_TOKEN_KEY, String(t));
    else   localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch(_) {}
}
function authClearToken(){ authSetToken(''); }

// Show/hide the login overlay.
function authShowLoginScreen(err){
  const el = document.getElementById('loginScreen');
  const shell = document.getElementById('app-shell');
  if (shell) shell.style.display = 'none';
  if (el) {
    el.classList.add('visible');
    const errBox = document.getElementById('lgError');
    if (errBox) errBox.textContent = err || '';
    const uf = document.getElementById('lgUsername');
    if (uf) try { uf.focus(); } catch(_) {}
  }
}
function authHideLoginScreen(){
  const el = document.getElementById('loginScreen');
  const shell = document.getElementById('app-shell');
  if (el) el.classList.remove('visible');
  if (shell) shell.style.display = '';
}

// Wrap _fuJsonp / _fuPost so every backend call auto-attaches the current token.
// Also transparently forwards timeout arg. This lets legacy call sites keep
// their signatures untouched — the auth layer plumbs itself through.
(function wrapTransportWithAuth(){
  if (typeof _fuJsonp !== 'function' || typeof _fuPost !== 'function') return;
  if (_fuJsonp.__authWrapped) return;
  const _origJsonp = _fuJsonp;
  const _origPost  = _fuPost;
  function _mergeTok(params){
    const t = authGetToken();
    const out = Object.assign({}, params || {});
    if (t && out._tok == null) out._tok = t;
    return out;
  }
  const wrappedJsonp = function(action, params, timeoutMs){
    return _origJsonp(action, _mergeTok(params), timeoutMs);
  };
  const wrappedPost = function(action, params, timeoutMs){
    return _origPost(action, _mergeTok(params), timeoutMs);
  };
  wrappedJsonp.__authWrapped = true;
  wrappedPost.__authWrapped  = true;
  // Reassign in the outer scope so every subsequent caller uses the wrapper.
  _fuJsonp = wrappedJsonp;
  _fuPost  = wrappedPost;
})();

// Auth login form handler.
async function authDoLogin(){
  const uEl = document.getElementById('lgUsername');
  const pEl = document.getElementById('lgPassword');
  const btn = document.getElementById('lgSubmit');
  const err = document.getElementById('lgError');
  err.textContent = '';
  const username = (uEl.value || '').trim();
  const password = pEl.value || '';
  if (!username || !password) { err.textContent = 'Enter your username and password.'; return; }
  btn.disabled = true;
  const oldLabel = btn.textContent;
  btn.textContent = 'Signing in…';
  try {
    // POST — passwords must never live in a URL/query string.
    const res = await _fuPost('authLogin', { username, password, ua: (navigator && navigator.userAgent) || '' });
    if (!res || !res.ok) {
      err.textContent = (res && res.error) || 'Sign-in failed. Try again.';
      return;
    }
    authSetToken(res.token);
    // Clear the password field so it doesn't sit in memory after we hide.
    if (pEl) pEl.value = '';
    authHideLoginScreen();
    // Re-run the access-control pass now that we carry a token.
    try { await applyAccessControl(); } catch(_) {}
    // Pull data fresh with the new identity.
    try { if (typeof liveFetch === 'function') liveFetch(false); } catch(_) {}
  } catch (ex) {
    err.textContent = (ex && ex.message) || 'Network error.';
  } finally {
    btn.disabled = false;
    btn.textContent = oldLabel;
  }
}

// Auth sign-out handler.
async function authDoLogout(){
  const t = authGetToken();
  try { if (t) await _fuJsonp('authLogout', { _tok: t }); } catch(_) {}
  authClearToken();
  // Clean the URL so we don't reload the login screen with stale state.
  try { window.location.reload(); } catch(_) {}
}

// Change-password modal handlers.
function authOpenChangePasswordModal(){
  const t = authGetToken();
  if (!t) {
    alert('Change password is only available when signed in with a username. You appear to be using the Google-identity break-glass path.');
    return;
  }
  ['cpOld','cpNew','cpConfirm'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  document.getElementById('cpMsg').textContent = '';
  document.getElementById('chgpwModal').classList.add('visible');
  try { document.getElementById('cpOld').focus(); } catch(_) {}
}
function authCloseChangePasswordModal(){
  document.getElementById('chgpwModal').classList.remove('visible');
}
async function authDoChangePassword(){
  const oldPw = document.getElementById('cpOld').value || '';
  const newPw = document.getElementById('cpNew').value || '';
  const conf  = document.getElementById('cpConfirm').value || '';
  const msg   = document.getElementById('cpMsg');
  msg.textContent = ''; msg.style.color = '';
  if (!oldPw || !newPw || !conf){ msg.textContent = 'All fields are required.'; msg.style.color = '#b85450'; return; }
  if (newPw !== conf){ msg.textContent = 'New passwords do not match.'; msg.style.color = '#b85450'; return; }
  const pwErr = (typeof acmValidatePasswordRules === 'function')
    ? acmValidatePasswordRules(newPw)
    : (newPw.length >= 6 && /[A-Za-z]/.test(newPw) && /[0-9]/.test(newPw) && /[^A-Za-z0-9]/.test(newPw)
        ? null
        : 'Password must be 6+ chars with letters, numbers, and symbols.');
  if (pwErr){ msg.textContent = pwErr; msg.style.color = '#b85450'; return; }
  const btn = document.getElementById('cpSubmit');
  btn.disabled = true;
  const oldLabel = btn.textContent;
  btn.textContent = 'Updating…';
  try {
    const res = await _fuPost('authChangePassword', { oldPassword: oldPw, newPassword: newPw });
    if (!res || !res.ok){
      msg.textContent = (res && res.error) || 'Update failed.';
      msg.style.color = '#b85450';
      return;
    }
    msg.textContent = 'Password updated.';
    msg.style.color = '#15803d';
    setTimeout(authCloseChangePasswordModal, 900);
  } catch (ex) {
    msg.textContent = (ex && ex.message) || 'Network error.';
    msg.style.color = '#b85450';
  } finally {
    btn.disabled = false;
    btn.textContent = oldLabel;
  }
}

// Reflect signed-in identity in the header (badge + change-password link).
function authRenderHeader(res){
  const wrap = document.getElementById('authHdrWrap');
  const who  = document.getElementById('authWho');
  const chg  = document.getElementById('authChangePwBtn');
  if (!wrap || !who) return;
  const email = String(res && res.email || '').trim();
  const uname = String(res && res.username || '').trim();
  const label = uname ? (uname + (res && res.isAdmin ? ' (Admin)' : '')) : (email || 'Signed in');
  who.textContent = label;
  wrap.style.display = 'inline-flex';
  // Google-identity break-glass has no token → Change password isn't meaningful.
  const via = String(res && res.via || '');
  if (chg) chg.style.display = (via === 'google-break-glass' || !authGetToken()) ? 'none' : '';
}

// ---- Password visibility toggle icons ----
// Shared SVG constants for every password-eye toggle in the app: login screen,
// User Management form (#acmPasswordEye), and the change-password modal.
// Keeping them here as a single source of truth means all toggles render the
// same icon set — swap here and every button follows.
const PASSWORD_EYE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>';
const PASSWORD_EYE_OFF_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.06 10.06 0 0 1 12 20c-6.5 0-10-7-10-7a18.5 18.5 0 0 1 4.06-5.19M9.9 4.24A9.12 9.12 0 0 1 12 4c6.5 0 10 7 10 7a17.9 17.9 0 0 1-2.16 3.19M1 1l22 22"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/></svg>';

// Boot-time auth setup — wire login form, sign-out, change-password modal.
function wireAuth(){
  // Login form
  const form = document.getElementById('loginForm');
  if (form) form.addEventListener('submit', (ev)=>{ ev.preventDefault(); authDoLogin(); });
  const btn = document.getElementById('lgSubmit');
  if (btn) btn.addEventListener('click', (ev)=>{ ev.preventDefault(); authDoLogin(); });
  // Password eye toggle on the login screen — uses shared SVG constants so
  // this button, the UM password field, and the change-password modal all
  // render the same icon set.
  const eye = document.getElementById('lgEyeBtn');
  const pwd = document.getElementById('lgPassword');
  if (eye && pwd) {
    eye.addEventListener('click', () => {
      const showing = pwd.type === 'text';
      pwd.type = showing ? 'password' : 'text';
      eye.innerHTML = showing ? PASSWORD_EYE_SVG : PASSWORD_EYE_OFF_SVG;
      eye.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
    });
  }
  // Header controls
  const btnLogout = document.getElementById('authLogoutBtn');
  if (btnLogout) btnLogout.addEventListener('click', authDoLogout);
  const btnChg   = document.getElementById('authChangePwBtn');
  if (btnChg) btnChg.addEventListener('click', authOpenChangePasswordModal);
  // Change-password modal buttons
  const cpCancel = document.getElementById('cpCancel');
  if (cpCancel) cpCancel.addEventListener('click', authCloseChangePasswordModal);
  const cpForm   = document.getElementById('chgpwForm');
  if (cpForm) cpForm.addEventListener('submit', (ev)=>{ ev.preventDefault(); authDoChangePassword(); });
  const cpSubmit = document.getElementById('cpSubmit');
  if (cpSubmit) cpSubmit.addEventListener('click', (ev)=>{ ev.preventDefault(); authDoChangePassword(); });
  document.querySelectorAll('#chgpwModal .cp-eye[data-cp-eye]').forEach(b => {
    b.addEventListener('click', () => {
      const id = b.getAttribute('data-cp-eye');
      const el = document.getElementById(id);
      if (!el) return;
      const showing = el.type === 'text';
      el.type = showing ? 'password' : 'text';
      b.innerHTML = showing ? PASSWORD_EYE_SVG : PASSWORD_EYE_OFF_SVG;
      b.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
    });
  });
}

// Apply per-viewer tab visibility based on the Access_Matrix sheet.
// Admin sees everything; everyone else gets only the tabs in their row.
async function applyAccessControl(){
  // Belt-and-braces timeout — guarantees the "Loading…" badge resolves to
  // SOMETHING within 12 seconds even if whoAmI never responds.
  let didFinish = false;
  setTimeout(() => {
    if (!didFinish) _wlSetWhoBadgeFallback('timeout');
  }, 12000);

  try {
    const res = await _fuJsonp('authWhoAmI', {});
    // Server tells us we need to log in — reveal the overlay.
    if (res && res.needsLogin) {
      didFinish = true;
      authClearToken();
      authShowLoginScreen();
      return;
    }
    if(!res || !res.ok){
      didFinish = true;
      _wlSetWhoBadgeFallback('failed');
      return;
    }
    // Confirmed session — make sure the shell is visible.
    authHideLoginScreen();
    authRenderHeader(res);
    const viewerEmail = String(res.email||'').toLowerCase().trim();
    const adminEmail  = String(res.adminEmail||'').toLowerCase().trim();
    // DEFENSE IN DEPTH: do NOT trust res.isAdmin on its own. Require:
    //   (a) viewer email is non-empty (server identified the viewer), AND
    //   (b) viewer email exactly equals admin email.
    // This way a misconfigured backend that returns isAdmin:true for unknown
    // viewers still can't unlock the Access Matrix tab in the UI.
    const reallyAdmin = !!viewerEmail && !!adminEmail && (viewerEmail === adminEmail);
    acmState.me      = viewerEmail;
    acmState.isAdmin = reallyAdmin;

    // Mirror identity into Worklist state so it knows whether to render admin chrome.
    try {
      if (typeof wlState !== 'undefined') {
        wlState.me          = viewerEmail;
        wlState.isAdmin     = reallyAdmin;
        wlState.isCollector = !!res.isCollector;
      }
    } catch(_){}

    const allowed = new Set((res.tabs||[]).map(String));
    if(!reallyAdmin && allowed.size === 0) allowed.add('dashboard');

    // Hide sidebar tabs the viewer can't see.
    // The Access Matrix tab is special-cased: it ONLY shows when reallyAdmin is true.
    // The Worklist tab shows when the viewer is admin OR is granted 'worklist'
    // (auto-granted to anyone listed in Collector_Master).
    document.querySelectorAll('.tab-item').forEach(t=>{
      const key = t.dataset.target;
      if (key === 'acm') {
        if (reallyAdmin) {
          // Verified admin: lift the default-hidden class and show the tab.
          t.classList.remove('hidden-until-admin');
          t.style.display = '';
        } else {
          // Everyone else: physically remove the sidebar tab from the DOM so
          // there is no element left to flash, hover-discover, or unhide.
          t.parentNode && t.parentNode.removeChild(t);
        }
        return;
      }
      if (key === 'worklist') {
        t.style.display = (reallyAdmin || allowed.has('worklist')) ? '' : 'none';
        return;
      }
      t.style.display = (reallyAdmin || allowed.has(key)) ? '' : 'none';
    });

    // Access Matrix SECTION: for non-admin, remove from DOM entirely.
    // For admin, lift the .hidden-until-admin gate so showTab can reveal it.
    document.querySelectorAll('[data-section="acm"]').forEach(sec => {
      if (reallyAdmin) {
        sec.classList.remove('hidden-until-admin');
      } else {
        sec.parentNode && sec.parentNode.removeChild(sec);
      }
    });

    // Worklist header chrome: admin sees Manage Collectors button + scope dropdown.
    try {
      const wlWho = document.getElementById('wlWhoBadge');
      if (wlWho) {
        // Per user request: we no longer surface the viewer identity badge in
        // the To-Do List header (it was distracting and in local-file mode it
        // showed "identity unknown" everywhere). The badge is kept hidden in
        // all cases; identity is still tracked internally via acmState.me.
        wlWho.style.display = 'none';
      }
      // Manage Collectors + the collector scope dropdown are now ALWAYS visible
      // (admin, non-admin, and local-file mode). Backend persistence calls
      // (collectorUpsert, bulkAssignCids, collectorDelete, etc.) still
      // re-check auth server-side, so this is safe.
      const wlMgr = document.getElementById('wlManageCollectors');
      if (wlMgr) wlMgr.style.display = '';
      const wlScope = document.getElementById('wlCollectorScope');
      if (wlScope) wlScope.style.display = '';
      // Populate collectors for every viewer (admin + non-admin). The server
      // returns the full collector list; per-viewer scoping happens at the
      // worklistData call when the user picks an entry.
      try { _wlPopulateCollectorScope(); } catch(_){}
    } catch(_){}

    // Update the admin badge inside the Access Matrix section (only admin will see it)
    const badge = document.getElementById('acmWhoBadge');
    if (badge) {
      badge.textContent = (viewerEmail || 'unknown viewer') + (reallyAdmin ? ' — Admin' : ' — Viewer');
      badge.style.background = reallyAdmin ? '#dcfce7' : '#fef9c3';
      badge.style.color      = reallyAdmin ? '#166534' : '#854d0e';
      badge.style.borderColor= reallyAdmin ? '#86efac' : '#fde68a';
    }
    const adm = document.getElementById('acmAdminEmail');
    if(adm && res.adminEmail) adm.textContent = res.adminEmail;

    // If the backend warns the deployment is misconfigured AND the current
    // viewer can't be identified, push them to Overview only — never give them
    // anything else by mistake.
    if (res.deploymentWarning && !viewerEmail) {
      console.warn('[Fynd dashboard] ' + res.deploymentWarning);
      document.querySelectorAll('.tab-item').forEach(t=>{
        t.style.display = (t.dataset.target === 'dashboard') ? '' : 'none';
      });
      showTab('dashboard');
      return;
    }

    // If non-admin currently on a hidden tab, bounce them to first allowed tab
    if(!reallyAdmin){
      const cur = state.activeTab;
      if(cur === 'acm' || !allowed.has(cur)){
        const first = (res.tabs||[])[0] || 'dashboard';
        showTab(first);
      }
    }
    didFinish = true;
  } catch(_){
    // Offline / no auth available — make sure the badge isn't stuck on "Loading…"
    didFinish = true;
    _wlSetWhoBadgeFallback('offline');
  }
}

// ===== Boot =====
// Boot-time error collector. Any exception thrown inside boot() gets pushed
// here + logged to console, and boot continues so downstream steps + the
// overlay teardown still fire. window.__bootErrors__ can be inspected from
// DevTools if the dashboard misbehaves after load.
window.__bootErrors__ = window.__bootErrors__ || [];
function _bootSafe(label, fn){
  try { fn(); }
  catch(err) {
    try {
      window.__bootErrors__.push({ step: label, error: String(err && err.stack || err) });
      console.error('[boot] step "'+label+'" threw:', err);
    } catch(_){}
  }
}
function boot(){
  // Progress overlay: HTML is parsed by now, so we're past "Connecting".
  try{ if(window.bootProgress) bootProgress.step(2); }catch(_){}
  // ------------------------------------------------------------------
  // Instant-paint snapshot hydration
  // ------------------------------------------------------------------
  // If localStorage has a fresh ar_snapshot_v1 (< 24h old), use it to
  // populate state.data / state.pdd / state.bank BEFORE we contact the
  // network. This lets us call renderAll() immediately and paint a
  // fully-usable dashboard in <1 s on repeat opens. When the live
  // fetch lands, state is replaced and everything re-renders.
  var _snap = null;
  try { _snap = _readSnapshot(); } catch(_){ _snap = null; }
  if (_snap && _snap.payload && Array.isArray(_snap.payload.data)) {
    state.data = _snap.payload.data;
    state.pdd  = _snap.payload.pdd  || [];
    state.bank = _snap.payload.bank || [];
    // Reveal the "Showing cached data · refreshing…" pill so users know a
    // fresh fetch is in flight. liveFetch() hides it when the fresh payload
    // lands.
    try{
      var _pill = document.getElementById('cacheStatePill');
      if (_pill) _pill.style.display = '';
    }catch(_){}
    try{ if(window.bootProgress){ bootProgress.step(4); bootProgress.hint('Rendering cached data…'); } }catch(_){}
  } else {
    state.data = window.__AR_DATA__ || [];
  }
  _bootSafe('buildAllFilters',   function(){ buildAllFilters(); });
  _bootSafe('wireDateChips',     function(){ wireDateChips(); });
  _bootSafe('wireMoreFilters',   function(){ wireMoreFilters(); });
  _bootSafe('wireSegments',      function(){ wireSegments(); });
  _bootSafe('wireTables',        function(){ wireTables(); });
  _bootSafe('wireTabs',          function(){ wireTabs(); });
  _bootSafe('wireClearAll',      function(){ wireClearAll(); });
  _bootSafe('wirePrint',         function(){ wirePrint(); });
  _bootSafe('wireHardRefresh',   function(){ wireHardRefresh(); });
  _bootSafe('wireReportTabs',    function(){ wireReportTabs(); });
  _bootSafe('wireDownloads',     function(){ wireDownloads(); });
  _bootSafe('wireScrollSpy',     function(){ wireScrollSpy(); });
  _bootSafe('wireBrandHome',     function(){ wireBrandHome(); });
  _bootSafe('wireGlobalSearch',  function(){ wireGlobalSearch(); });
  _bootSafe('wireSettings',      function(){ wireSettings(); });
  _bootSafe('wireFollowUps',     function(){ wireFollowUps(); });
  _bootSafe('wireActivityLog',   function(){ wireActivityLog(); });
  _bootSafe('wireAuth',          function(){ wireAuth(); });
  _bootSafe('wireAcm',           function(){ wireAcm(); });
  _bootSafe('wireWorklist',      function(){ wireWorklist(); });
  _bootSafe('wireSoa',           function(){ wireSoa(); });
  _bootSafe('wirePOCs',          function(){ wirePOCs(); });
  _bootSafe('wireIS',            function(){ wireIS(); });
  _bootSafe('wireWorkflows',     function(){ wireWorkflows(); });
  // When served by Apps Script, the Apps Script Web App tells us who the
  // viewer is. Admin gets the Access Matrix tab; everyone else only sees the
  // tabs they were granted. When opened as a local file we skip this entirely.
  _bootSafe('accessControl', function(){
    if (window.__SERVED_BY_APPS_SCRIPT__) {
      // Hide the app shell until authWhoAmI confirms a valid session. This
      // prevents the dashboard from flashing behind the login overlay while
      // the auth round-trip is in flight.
      try {
        const shell = document.getElementById('app-shell');
        if (shell) shell.style.display = 'none';
      } catch(_) {}
      applyAccessControl();
    } else {
      // Local file / not served by Apps Script — identity is unknown. Make sure
      // the To-Do List header chip doesn't stay stuck on "Loading…" forever.
      _wlSetWhoBadgeFallback('local');
    }
  });
  // When served by Apps Script, viewers don't need to touch Settings — hide the gear.
  _bootSafe('hideGear', function(){
    if (window.__SERVED_BY_APPS_SCRIPT__) {
      const gear = document.getElementById('btnSettings');
      if (gear) gear.style.display = 'none';
    }
  });
  _bootSafe('genTs', function(){
    var el = document.getElementById('genTs');
    if (el) el.textContent = new Date().toLocaleString();
  });
  try{ if(window.bootProgress) bootProgress.step(4); }catch(_){}
  _bootSafe('refresh',   function(){ refresh(); });
  _bootSafe('paintPDD',  function(){ paintPDD(); });
  _bootSafe('paintBank', function(){ paintBank(); });
  // First paint is done — fade out the boot progress overlay so the app
  // is visible even if the live fetch is still running. This is inside a
  // top-level try so even if bootProgress itself blew up, subsequent code
  // still runs and the safety-net timeout in the head-inline will also
  // clear the overlay at T+12s regardless.
  try{ if(window.bootProgress) bootProgress.finish(); }catch(_){}
  // Auto-connect:
  //   • If served by Apps Script (window.__DATA_URL__ injected) → connect immediately, no Settings needed.
  //   • Else if a URL is already in localStorage              → reconnect.
  //   • Else                                                  → wait for the user to open Settings.
  const autoUrl = window.__DATA_URL__ || localStorage.getItem(LS_KEY_URL);
  if(autoUrl){
    setSyncStatus('Connecting…', false);
    liveFetch(false).then(()=> startLiveTimer());
  } else {
    setSyncStatus('Live Off', false);
  }
}
// (Standalone "Refresh data" button removed — its behavior is merged into
// the Hard Refresh (↻) button, which now also purges the server-side
// CacheService entry before pulling fresh data. See wireHardRefresh().)
// Wrap boot() in a top-level try/catch of last resort. If anything at all
// blows up, ensure the overlay clears so the app-shell underneath becomes
// interactive (the head-inline safety timeout also guarantees this at T+12s).
try {
  boot();
} catch(err) {
  try {
    window.__bootErrors__ = window.__bootErrors__ || [];
    window.__bootErrors__.push({ step: 'boot()', error: String(err && err.stack || err) });
    console.error('[boot] top-level exception:', err);
  } catch(_){}
  try { if(window.bootProgress) window.bootProgress.finish(); } catch(_){}
}
</script>
</div><!-- /#app-shell -->
</body>
</html>"""

import sys

# --- Build mode -------------------------------------------------
# Default: embed the historical AR data inline so the file works offline.
# `--slim`: skip embedded data — the dashboard always live-fetches anyway.
#           Produces a tiny HTML (~150 KB) suitable for pasting directly
#           into Apps Script as an Index.html file.
SLIM = '--slim' in sys.argv

if SLIM:
    INJECT = "window.__AR_DATA__ = [];"
    OUT = '/sessions/serene-keen-mendel/mnt/outputs/Fynd_Receivables_Insights__slim.html'
else:
    INJECT = "window.__AR_DATA__ = " + DATA + ";"
    OUT = '/sessions/serene-keen-mendel/mnt/outputs/Fynd_Receivables_Insights.html'

HTML_OUT = HTML.replace("// __DATA_INJECTION_POINT__", INJECT)

with open(OUT, 'w') as f:
    f.write(HTML_OUT)

print("Mode:", "SLIM (no embedded data)" if SLIM else "FULL (with embedded data)")
print("Wrote:", OUT)
print("Size:", os.path.getsize(OUT))
