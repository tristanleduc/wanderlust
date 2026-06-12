"""Custom app-shell frontend for the ``gradio.Server`` backend.

Off-Brand: instead of Gradio's default column layout, the page is a hand-built
HTML/CSS/JS app-shell — fixed left control panel · large map · green route-summary
bar · scrollable itinerary · mobile bottom-drawer — served from ``app.get("/")``
and talking to ``@app.api`` endpoints through ``@gradio/client``.

Visual identity is preserved by REUSE, not reimplementation: the existing
:data:`design.DR_CSS` (tokens, sliders, segmented toggle, coral CTA, green summary
banner, dashed-rail itinerary, framed map window) is injected verbatim and the
same ``#dr-*`` element ids are kept, so every color/font/treatment carries over.
Only the spatial layout (``APP_SHELL_CSS``) and the vanilla-JS interactivity
(autocomplete, localStorage profile, sliders, the 4-step loader) are new.
"""
from __future__ import annotations

from discoverroute.ui import design
from discoverroute.ui import map as mapui

# --------------------------------------------------------------- app-shell CSS
APP_SHELL_CSS = """
*{ box-sizing:border-box; }
html,body{ margin:0; height:100%; }
body{ font-family:'DM Sans',ui-sans-serif,system-ui,sans-serif; color:var(--dr-ink);
  background:radial-gradient(1100px 520px at 88% -8%,#FBEFD6 0%,transparent 60%),var(--dr-cream); }

.app-shell{
  display:grid; grid-template-columns:320px 1fr; grid-template-rows:auto 1fr;
  height:100vh; width:100%; background:var(--dr-cream);
}

/* ---- hero (compact ≤120px, content + colors preserved) ---- */
.hero{ grid-column:1 / -1; grid-row:1; display:flex; align-items:center; gap:18px;
  background:linear-gradient(120deg,#2F5DF4,#5C7DF8); color:#fff;
  padding:12px 26px; max-height:120px; overflow:hidden; position:relative; }
.hero .hero-body{ flex:1; min-width:0; }
.hero .loc-pill{ display:inline-flex; align-items:center; gap:7px; background:rgba(255,255,255,.16);
  border-radius:999px; padding:3px 11px; font-family:'Fredoka',sans-serif; font-weight:600;
  font-size:11.5px; letter-spacing:.04em; }
.hero .loc-pill .dot{ width:7px;height:7px;border-radius:50%;background:#FFC247; }
.hero h1{ font-family:'Fredoka',sans-serif; font-weight:700; font-size:28px; letter-spacing:-.02em;
  margin:5px 0 3px; line-height:1.05; color:#fff; }
.hero h1 .accent{ color:#FFE0A0; }
.hero p{ margin:0 0 7px; max-width:62ch; color:#EAF0FF; font-size:13px; line-height:1.3; }
.hero .badges{ display:flex; flex-wrap:wrap; gap:7px; }
.hero .badges span{ background:rgba(255,255,255,.13); border-radius:999px; padding:4px 11px;
  font-size:11.5px; font-family:'Fredoka',sans-serif; font-weight:500; }
.hero .hero-art{ flex-shrink:0; width:80px; }
.hero .hero-art svg{ width:80px; height:auto; display:block; }
.hero .titan-chip{ position:absolute; top:10px; right:18px; background:rgba(255,255,255,.16);
  border-radius:999px; padding:3px 10px; font-size:10.5px; font-family:'Fredoka',sans-serif;
  font-weight:600; letter-spacing:.02em; }

/* ---- left control panel (320px, scrollable, sticky CTA) ---- */
.left-panel{ grid-column:1; grid-row:2; width:320px; height:100%; overflow-y:auto;
  padding:18px 16px 0; border-right:1px solid rgba(0,0,0,.08); background:var(--dr-cream);
  display:flex; flex-direction:column; }
.dr-control{ margin-bottom:13px; }
.dr-label{ display:block; font-family:'Fredoka',sans-serif; font-weight:600; font-size:13.5px;
  color:var(--dr-ink); margin-bottom:5px; }
.dr-help{ font-size:11.5px; color:var(--dr-soft); margin-top:3px; }
.left-panel input[type=text]{ width:100%; padding:10px 12px; font-size:14px; }
.combo{ position:relative; }
.combo-list{ position:absolute; z-index:50; left:0; right:0; top:calc(100% + 3px);
  background:var(--dr-paper); border:1px solid var(--dr-line); border-radius:14px;
  box-shadow:0 14px 30px -14px rgba(43,38,32,.4); overflow:hidden; display:none; }
.combo-list.open{ display:block; }
.combo-list div{ padding:9px 12px; font-size:13.5px; cursor:pointer; }
.combo-list div:hover,.combo-list div.active{ background:#F1FAF4; }
.dr-slider{ display:flex; align-items:center; gap:10px; }
.dr-slider input[type=range]{ flex:1; }
.dr-slider output{ font-family:'JetBrains Mono',monospace; font-size:12.5px; color:var(--dr-soft);
  min-width:30px; text-align:right; }
details.dr-collapse{ padding:0; margin-bottom:13px; }
details.dr-collapse summary{ list-style:none; cursor:pointer; padding:11px 14px;
  font-family:'Fredoka',sans-serif; font-weight:600; font-size:13px; color:var(--dr-ink); }
details.dr-collapse summary::-webkit-details-marker{ display:none; }
details.dr-collapse[open] summary{ border-bottom:1.5px dashed var(--dr-line); }
details.dr-collapse .collapse-body{ padding:12px 14px; }
.dr-cta-wrap{ position:sticky; bottom:0; padding:12px 0; margin-top:auto;
  background:linear-gradient(180deg,rgba(246,236,217,0),var(--dr-cream) 32%); }
#dr-plan button{ width:100%; padding:13px; cursor:pointer; }
.dr-note{ font-size:12.5px; color:var(--dr-soft); margin:8px 0; }
.dr-row{ display:flex; gap:8px; }
.dr-row button{ flex:1; padding:8px; border-radius:12px; border:1px solid var(--dr-line);
  background:var(--dr-paper); font-family:'Fredoka',sans-serif; font-weight:600; cursor:pointer;
  color:var(--dr-ink); }
.dr-star{ width:100%; margin-top:8px; padding:9px; border-radius:12px; border:1px solid var(--dr-line);
  background:var(--dr-paper); font-family:'Fredoka',sans-serif; font-weight:600; cursor:pointer;
  color:var(--dr-ink); }

/* ---- right column: map · summary bar · itinerary ---- */
.right-col{ grid-column:2; grid-row:2; display:flex; flex-direction:column; height:100%;
  min-width:0; padding:14px 16px 0; gap:12px; overflow:hidden; }
.map-container{ flex:1 1 0; min-height:480px; position:relative; }
#dr-map{ height:100%; }
#dr-map .map-inner{ position:absolute; inset:34px 0 0 0; }
#dr-map .map-inner > div,
#dr-map iframe,
#dr-map .folium-map,
#dr-map .leaflet-container{ width:100% !important; height:100% !important; }
#dr-map .map-inner > div > div{ padding-bottom:0 !important; height:100% !important; }
.route-summary-bar{ flex:0 0 auto; }
#dr-summary{ margin:0; }
/* the styled result blocks only exist once a route is planned */
#dr-summary:empty, #dr-interp:empty, #dr-itin:empty, #dr-nodetour:empty{ display:none; }
.itinerary-panel{ flex:0 0 auto; max-height:40vh; overflow-y:auto; padding-bottom:14px; }
#dr-options{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:12px; }
#dr-options .opt{ border:2px solid var(--dr-line); border-radius:var(--dr-r); padding:10px 13px;
  background:var(--dr-paper); color:var(--dr-ink); cursor:pointer; font-size:12.5px;
  transition:all .2s var(--dr-spring); }
#dr-options .opt:hover{ transform:translateY(-3px); }
#dr-options .opt.selected{ border-color:var(--dr-grass); background:#F1FAF4;
  box-shadow:0 10px 26px -14px rgba(47,164,99,.6); }

/* ---- loading: stride + 4-step stepper (State 2) ---- */
#dr-loading{ position:absolute; inset:34px 0 0 0; z-index:20; display:none;
  place-items:center; border-radius:0 0 26px 26px;
  background:radial-gradient(700px 320px at 50% 0%,#FBEFD6 0%,transparent 70%),#F6ECD9; }
#dr-loading.on{ display:grid; }
.stepper{ display:flex; align-items:center; gap:0; margin-top:18px; }
.stepper .step{ display:flex; flex-direction:column; align-items:center; gap:6px; width:120px;
  opacity:.4; transition:opacity .4s ease; }
.stepper .step.active{ opacity:1; }
.stepper .step .pip{ width:14px; height:14px; border-radius:50%; background:#CFE8D8;
  transition:background .4s ease, transform .4s var(--dr-spring); }
.stepper .step.active .pip{ background:var(--dr-grass); transform:scale(1.15); }
.stepper .step .lbl{ font-size:11.5px; font-family:'DM Sans',sans-serif; color:var(--dr-ink);
  text-align:center; }
.stepper .bar{ flex:1; height:3px; min-width:24px; background:#CFE8D8; position:relative; }
.stepper .bar.fill{ background:var(--dr-grass); }
/* State 1 — non-Paris graph load (inert for the Paris demo, built per brief) */
#dr-mapping{ position:absolute; inset:34px 0 0 0; z-index:21; display:none; place-items:center;
  background:#F6ECD9; }
#dr-mapping.on{ display:grid; }
#dr-mapping .pulse{ width:18px;height:18px;border-radius:50%;background:var(--dr-grass);
  animation:drPulse 1.1s ease-in-out infinite; margin:0 auto 10px; }
@keyframes drPulse{ 0%,100%{ transform:scale(.7); opacity:.5; } 50%{ transform:scale(1.1); opacity:1; } }

/* no-detour sticker slot */
#dr-nodetour:empty{ display:none; }

/* mobile FAB (hidden on desktop) */
.fab{ display:none; }

/* ---- mobile: left panel → bottom drawer, full-screen map, coral FAB ---- */
@media (max-width:768px){
  .app-shell{ grid-template-columns:1fr; grid-template-rows:auto 1fr; height:100vh; }
  .hero{ max-height:none; }
  .hero .hero-art{ display:none; }
  .right-col{ grid-column:1; grid-row:2; padding:0; gap:0; }
  .map-container{ min-height:0; }
  #dr-map .map-inner, #dr-loading, #dr-mapping{ inset:0; }
  .itinerary-panel{ max-height:34vh; padding:0 14px 14px; }
  .route-summary-bar{ padding:0 12px; }
  .left-panel{ position:fixed; left:0; right:0; bottom:0; top:auto; z-index:200; width:100%;
    height:auto; max-height:78vh; border-right:none; border-top-left-radius:24px;
    border-top-right-radius:24px; box-shadow:0 -18px 44px -20px rgba(43,38,32,.4);
    transform:translateY(110%); transition:transform .32s var(--dr-spring); }
  .left-panel.open{ transform:translateY(0); }
  .fab{ display:grid; place-items:center; position:fixed; right:18px; bottom:18px; z-index:210;
    width:60px; height:60px; border-radius:50%; border:none; cursor:pointer;
    background:var(--dr-coral); color:#fff; font-size:24px;
    box-shadow:0 10px 24px -8px rgba(255,106,82,.8); }
  .drawer-close{ display:block; }
}
.drawer-close{ display:none; width:100%; text-align:center; padding:6px; font-size:22px;
  color:var(--dr-soft); cursor:pointer; }

@media (prefers-reduced-motion:reduce){ *{ animation:none !important; transition:none !important; } }
"""


def _compact_hero() -> str:
    """Hero with the exact copy/badges/colors, tightened to ≤120px."""
    return f"""
<header class="hero">
  <div class="hero-body">
    <span class="loc-pill"><span class="dot"></span>Paris · walkable detours</span>
    <h1>Spend your extra time on <span class="accent">discovery.</span></h1>
    <p>Ordinary navigation minimizes time. DiscoverRoute detours past places that match
       your taste — within a travel-time budget — and tells you why each one is on the path.</p>
    <div class="badges">
      <span>🗺️ OpenStreetMap data</span>
      <span>🥐 A friendly local guide</span>
      <span>✨ Tuned to your vibe</span>
    </div>
  </div>
  <div class="hero-art">{design._HERO_SVG}</div>
  <span class="titan-chip">running on a 1B model, in-Space</span>
</header>
"""


def _left_panel() -> str:
    return """
<aside class="left-panel" id="left-panel">
  <div class="drawer-close" id="drawer-close">×</div>

  <div class="dr-control combo">
    <label class="dr-label" for="dr-start">Start</label>
    <input type="text" id="dr-start" class="dr-field" autocomplete="off"
           value="Place de la République, Paris">
    <div class="combo-list" id="dr-start-list"></div>
    <div class="dr-help">Type a Paris place — suggestions appear as you type</div>
  </div>

  <div class="dr-control combo">
    <label class="dr-label" for="dr-dest">Destination</label>
    <input type="text" id="dr-dest" class="dr-field" autocomplete="off"
           value="Jardin du Luxembourg, Paris">
    <div class="combo-list" id="dr-dest-list"></div>
  </div>

  <div class="dr-control">
    <label class="dr-label" for="dr-vibe">Vibe (free text)</label>
    <input type="text" id="dr-vibe" class="dr-field"
           placeholder="e.g. 'quiet green wander' or 'lively café crawl'">
  </div>

  <div class="dr-control">
    <label class="dr-label">Mode</label>
    <div id="dr-mode" class="dr-seg">
      <div class="wrap">
        <label class="selected" data-v="walk">walk</label>
        <label data-v="bike">bike</label>
      </div>
    </div>
  </div>

  <div class="dr-control">
    <label class="dr-label" for="dr-budget-i">Detour budget</label>
    <div id="dr-budget" class="dr-slider">
      <input type="range" id="dr-budget-i" min="0" max="2" step="0.1" value="0.5">
      <output id="dr-budget-o">0.5</output>
    </div>
    <div class="dr-help">Extra time vs. the direct trip — 0 = straight there, 1 = up to 2× longer</div>
  </div>

  <div class="dr-control">
    <label class="dr-label" for="dr-adv-i">Adventurousness</label>
    <div id="dr-adv" class="dr-slider">
      <input type="range" id="dr-adv-i" min="0" max="1" step="0.05" value="0.3">
      <output id="dr-adv-o">0.3</output>
    </div>
    <div class="dr-help">Low = well-known places · high = hidden gems</div>
  </div>

  <details class="dr-collapse">
    <summary>Manual taste (used only when Vibe and saved profile are both empty)</summary>
    <div class="collapse-body">
      <div class="dr-control">
        <label class="dr-label" for="dr-green-i">Prefer green</label>
        <div id="dr-green" class="dr-slider green">
          <input type="range" id="dr-green-i" min="0" max="1" step="0.05" value="0.5">
          <output id="dr-green-o">0.5</output>
        </div>
      </div>
      <div class="dr-control">
        <label class="dr-label" for="dr-quiet-i">Prefer quiet</label>
        <div id="dr-quiet" class="dr-slider green">
          <input type="range" id="dr-quiet-i" min="0" max="1" step="0.05" value="0.5">
          <output id="dr-quiet-o">0.5</output>
        </div>
      </div>
    </div>
  </details>

  <div class="dr-cta-wrap">
    <div id="dr-plan"><button type="button" id="dr-plan-btn">Plan route</button></div>
  </div>

  <details class="dr-collapse">
    <summary>⭐ My taste profile (saved on this device)</summary>
    <div class="collapse-body">
      <label class="dr-label" for="dr-profile-text">Standing preferences</label>
      <input type="text" id="dr-profile-text" class="dr-field"
             placeholder="e.g. 'I always love bookshops, gardens, and old churches'">
      <div class="dr-row" style="margin-top:8px;">
        <button type="button" id="dr-save">Save</button>
        <button type="button" id="dr-clear">Clear</button>
      </div>
      <div class="dr-note" id="dr-saved"></div>
      <button type="button" class="dr-star" id="dr-save-places">⭐ Save this route's places</button>
    </div>
  </details>
</aside>
"""


def index_html() -> str:
    """Assemble the full single-page app served at ``/``."""
    empty = mapui.empty_map()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DiscoverRoute · Paris</title>
{design.DR_HEAD}
<style>{design.DR_CSS}</style>
<style>{APP_SHELL_CSS}</style>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
<div class="gradio-container app-shell">
  {_compact_hero()}
  {_left_panel()}
  <main class="right-col">
    <div class="map-container">
      <div id="dr-map"><div class="map-inner">{empty}</div></div>
      <div id="dr-mapping"><div><div class="pulse"></div>
        <span style="font-family:'Fredoka',sans-serif;font-weight:600;">Mapping the streets…</span></div></div>
      <div id="dr-loading">{_loading_inner()}</div>
    </div>
    <div class="route-summary-bar"><div id="dr-summary"></div></div>
    <div class="itinerary-panel">
      <div id="dr-options"></div>
      <div id="dr-nodetour"></div>
      <div id="dr-interp"></div>
      <div id="dr-itin"></div>
    </div>
  </main>
</div>
<button class="fab" id="fab" aria-label="Open controls">☰</button>

<script type="module">{_app_js()}</script>
</body>
</html>"""


def _loading_inner() -> str:
    """Stride mascot (reused) + the 4-step stepper."""
    steps = ["Interpreting vibe", "Scoring places", "Solving route", "Writing itinerary"]
    pips = []
    for i, label in enumerate(steps):
        if i:
            pips.append('<div class="bar" data-bar="%d"></div>' % i)
        pips.append(
            f'<div class="step" data-step="{i}"><div class="pip"></div>'
            f'<div class="lbl">{label}</div></div>'
        )
    stepper = '<div class="stepper">' + "".join(pips) + "</div>"
    # Reuse the existing stride mascot markup from LOADING_HTML's inner SVG block.
    return f"""
<div style="text-align:center;">
  <div style="font-family:'Fredoka',system-ui,sans-serif;font-weight:600;font-size:19px;
       color:#2B2620;">Scouting your wander…</div>
  {stepper}
</div>
<style>
  @keyframes drBounce {{ 0%,100% {{ transform:translateY(0) }} 50% {{ transform:translateY(-9px) }} }}
</style>
"""


def _app_js() -> str:
    return r"""
import { Client } from "https://cdn.jsdelivr.net/npm/@gradio/client/dist/index.min.js";

const $ = (id) => document.getElementById(id);
const md = (s) => (window.marked ? window.marked.parse(s || "") : (s || ""));

let appClient = null;
async function client() {
  if (!appClient) appClient = await Client.connect(window.location.origin);
  return appClient;
}

/* ---------- taste profile via localStorage (replaces gr.BrowserState) ---------- */
const PKEY = "discoverroute_profile";
function readProfile() {
  try { return JSON.parse(localStorage.getItem(PKEY)) ||
        { standing_text: "", saved_categories: [] }; }
  catch (e) { return { standing_text: "", saved_categories: [] }; }
}
function writeProfile(p) { localStorage.setItem(PKEY, JSON.stringify(p)); renderSaved(); }
function renderSaved() {
  const p = readProfile();
  const cats = p.saved_categories || [];
  let txt = "_No saved places yet. Plan a route, then ⭐ save its places._";
  if (cats.length) {
    const counts = {};
    cats.forEach(c => counts[c] = (counts[c] || 0) + 1);
    txt = "**Saved taste:** " + Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([c, n]) => `${c.replace(/_/g, " ")} ×${n}`).join(", ");
  }
  $("dr-saved").innerHTML = md(txt);
  if ($("dr-profile-text") && !$("dr-profile-text").value) $("dr-profile-text").value = p.standing_text || "";
}

/* ---------- toast ---------- */
function toast(msg) {
  const t = document.createElement("div");
  t.textContent = msg;
  t.style.cssText = "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:999;" +
    "background:#2B2620;color:#fff;padding:11px 18px;border-radius:14px;font-size:13.5px;" +
    "box-shadow:0 12px 30px -12px rgba(0,0,0,.5);font-family:'DM Sans',sans-serif;";
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2600);
}

/* ---------- sliders ---------- */
[["dr-budget-i", "dr-budget-o"], ["dr-adv-i", "dr-adv-o"],
 ["dr-green-i", "dr-green-o"], ["dr-quiet-i", "dr-quiet-o"]].forEach(([i, o]) => {
  const inp = $(i); if (!inp) return;
  const out = $(o);
  inp.addEventListener("input", () => out.textContent = (+inp.value).toFixed(2).replace(/\.?0+$/, "") || "0");
});

/* ---------- mode segmented toggle ---------- */
let mode = "walk";
document.querySelectorAll("#dr-mode label").forEach(l => {
  l.addEventListener("click", () => {
    document.querySelectorAll("#dr-mode label").forEach(x => x.classList.remove("selected"));
    l.classList.add("selected"); mode = l.dataset.v;
  });
});

/* ---------- autocomplete combobox (replaces gr.Dropdown) ---------- */
function wireCombo(inputId, listId) {
  const input = $(inputId), list = $(listId);
  let timer = null, items = [], active = -1;
  const close = () => { list.classList.remove("open"); active = -1; };
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        const c = await client();
        const r = await c.predict("/suggest", { query: input.value });
        items = (r.data && r.data[0]) || [];
        if (!items.length) return close();
        list.innerHTML = items.map((s, i) =>
          `<div data-i="${i}">${s.replace(/</g, "&lt;")}</div>`).join("");
        list.querySelectorAll("div").forEach(d => d.addEventListener("mousedown", (e) => {
          e.preventDefault(); input.value = items[+d.dataset.i]; close();
        }));
        list.classList.add("open");
      } catch (e) { /* suggestions are best-effort */ }
    }, 160);
  });
  input.addEventListener("keydown", (e) => {
    if (!list.classList.contains("open")) return;
    const els = list.querySelectorAll("div");
    if (e.key === "ArrowDown") { active = Math.min(active + 1, els.length - 1); e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = Math.max(active - 1, 0); e.preventDefault(); }
    else if (e.key === "Enter" && active >= 0) { input.value = items[active]; close(); e.preventDefault(); return; }
    else if (e.key === "Escape") { return close(); }
    els.forEach((d, i) => d.classList.toggle("active", i === active));
  });
  input.addEventListener("blur", () => setTimeout(close, 120));
}
wireCombo("dr-start", "dr-start-list");
wireCombo("dr-dest", "dr-dest-list");

/* ---------- 4-step loader (paced to the pipeline phases) ---------- */
let stepTimer = null;
function setStep(n) {
  document.querySelectorAll(".stepper .step").forEach(s =>
    s.classList.toggle("active", +s.dataset.step <= n));
  document.querySelectorAll(".stepper .bar").forEach(b =>
    b.classList.toggle("fill", +b.dataset.bar <= n));
}
function startLoading() {
  $("dr-loading").classList.add("on");
  $("dr-summary").innerHTML = ""; $("dr-itin").innerHTML = "";
  $("dr-interp").innerHTML = ""; $("dr-options").innerHTML = ""; $("dr-nodetour").innerHTML = "";
  let n = 0; setStep(0);
  stepTimer = setInterval(() => { n = Math.min(n + 1, 3); setStep(n); }, 1200);
}
function stopLoading() { clearInterval(stepTimer); setStep(3); $("dr-loading").classList.remove("on"); }

/* ---------- render ---------- */
let lastAlts = [], lastCats = [];
function renderMap(html) { $("dr-map").innerHTML = '<div class="map-inner">' + html + "</div>"; }
function selectAlt(idx) {
  const a = lastAlts[idx]; if (!a) return;
  renderMap(a.map_html);
  $("dr-summary").innerHTML = md(a.summary_md);
  $("dr-itin").innerHTML = md(a.itinerary_md);
  document.querySelectorAll("#dr-options .opt").forEach((o, i) =>
    o.classList.toggle("selected", i === idx));
}
function renderResult(d) {
  if (d.error) { renderMap(d.map_html); toast("Hmm — " + d.error.split(".")[0] + "."); return; }
  $("dr-interp").innerHTML = md(d.interpretation_md);
  if (d.no_detour) {
    renderMap(d.map_html);
    $("dr-summary").innerHTML = md(d.summary_md);
    $("dr-itin").innerHTML = md(d.itinerary_md);
    $("dr-nodetour").innerHTML = d.nodetour_html || "";
    lastAlts = []; lastCats = [];
    return;
  }
  $("dr-nodetour").innerHTML = "";
  lastAlts = d.alternatives || [];
  lastCats = d.last_cats || [];
  if (lastAlts.length > 1) {
    $("dr-options").innerHTML = lastAlts.map((a, i) =>
      `<div class="opt${i === 0 ? " selected" : ""}" data-i="${i}">${a.label}</div>`).join("");
    document.querySelectorAll("#dr-options .opt").forEach(o =>
      o.addEventListener("click", () => selectAlt(+o.dataset.i)));
  } else { $("dr-options").innerHTML = ""; }
  selectAlt(0);
}

/* ---------- plan ---------- */
async function plan() {
  // map-press bounce (reused micro-interaction)
  const mapEl = $("dr-map");
  if (mapEl) mapEl.animate(
    [{ transform: "scale(1)" }, { transform: "scale(.99)" }, { transform: "scale(1)" }],
    { duration: 260, easing: "cubic-bezier(.34,1.56,.64,1)" });
  startLoading();
  try {
    const c = await client();
    const r = await c.predict("/plan", {
      start: $("dr-start").value, dest: $("dr-dest").value, mode,
      budget: +$("dr-budget-i").value, vibe: $("dr-vibe").value,
      adventurousness: +$("dr-adv-i").value,
      prefer_green: +$("dr-green-i").value, prefer_quiet: +$("dr-quiet-i").value,
      profile: JSON.stringify(readProfile()),
    });
    renderResult((r.data && r.data[0]) || {});
  } catch (e) {
    toast("Something went wrong planning the route.");
    console.error(e);
  } finally { stopLoading(); }
}
$("dr-plan-btn").addEventListener("click", plan);

/* ---------- profile buttons ---------- */
$("dr-save").addEventListener("click", () => {
  const p = readProfile(); p.standing_text = $("dr-profile-text").value || "";
  writeProfile(p); toast("Saved your standing preferences ✨");
});
$("dr-clear").addEventListener("click", () => {
  writeProfile({ standing_text: "", saved_categories: [] });
  $("dr-profile-text").value = ""; toast("Profile cleared 🧹");
});
$("dr-save-places").addEventListener("click", () => {
  if (!lastCats.length) return toast("Plan a route first — then I can save its places.");
  const p = readProfile();
  p.saved_categories = (p.saved_categories || []).concat(lastCats);
  writeProfile(p); toast("Saved this route's places to your taste ✨");
});

/* ---------- mobile drawer ---------- */
$("fab").addEventListener("click", () => $("left-panel").classList.add("open"));
$("drawer-close").addEventListener("click", () => $("left-panel").classList.remove("open"));

renderSaved();
"""
