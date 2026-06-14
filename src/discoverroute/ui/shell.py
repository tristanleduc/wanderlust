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

from discoverroute import config
from discoverroute.ui import design
from discoverroute.ui import map as mapui

_MONTHS = ["", "January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


def _provenance_line() -> str:
    """Honest data-freshness + attribution line for the results sheet footer."""
    when = ""
    d = config.DATA_BUILD_DATE
    if d:
        try:
            y, m, _ = d.split("-")
            when = f" · snapshot {_MONTHS[int(m)]} {y}"
        except Exception:  # noqa: BLE001
            when = f" · snapshot {d}"
    return (f"Places from OpenStreetMap{when} · open/close times are best-effort "
            f"(often unlisted) · © OpenStreetMap contributors (ODbL)")

# --------------------------------------------------------------- app-shell CSS
APP_SHELL_CSS = """
*{ box-sizing:border-box; }
html,body{ margin:0; height:100%; }
body{ font-family:'DM Sans',ui-sans-serif,system-ui,sans-serif; color:var(--dr-ink);
  background:radial-gradient(1100px 520px at 88% -8%,#FBEFD6 0%,transparent 60%),var(--dr-cream); }

.app-shell{
  display:grid; grid-template-columns:340px 1fr; grid-template-rows:1fr;
  height:100vh; height:100dvh; width:100%; background:var(--dr-cream);
}

/* ---- brand header (top of the left panel — replaces the old blue ribbon) ---- */
.brand{ display:flex; align-items:center; gap:10px; padding:0 0 14px; margin-bottom:6px;
  border-bottom:1px solid var(--dr-line); }
.brand .logo{ width:34px; height:34px; border-radius:11px; flex-shrink:0; display:grid;
  place-items:center; font-size:18px; background:linear-gradient(135deg,#2F5DF4,#5C7DF8);
  box-shadow:0 6px 14px -6px rgba(47,93,244,.7); }
.brand .bname{ font-family:'Fredoka',sans-serif; font-weight:700; font-size:19px;
  letter-spacing:-.01em; color:var(--dr-ink); line-height:1; }
.brand .titan-chip{ margin-left:auto; display:inline-flex; align-items:center; gap:6px;
  background:#EAF6EF; color:var(--dr-grass-d); border-radius:999px; padding:4px 10px;
  font-size:10px; font-family:'Fredoka',sans-serif; font-weight:600; white-space:nowrap; }
.brand .titan-chip::before{ content:''; width:6px; height:6px; border-radius:50%;
  background:var(--dr-grass); box-shadow:0 0 6px var(--dr-grass); }

/* ---- left control panel (340px, scrollable, sticky CTA) ---- */
.left-panel{ grid-column:1; grid-row:1; width:340px; height:100%; overflow:hidden;
  border-right:1px solid var(--dr-line);
  background:linear-gradient(180deg,#FBF3E2,var(--dr-cream) 140px);
  display:flex; flex-direction:column; }
.panel-scroll{ flex:1 1 auto; min-height:0; overflow-y:auto; overflow-x:hidden;
  padding:20px 18px 10px; scrollbar-width:thin; scrollbar-color:var(--dr-line) transparent; }
.panel-scroll::-webkit-scrollbar{ width:9px; }
.panel-scroll::-webkit-scrollbar-thumb{ background:var(--dr-line); border-radius:9px;
  border:3px solid transparent; background-clip:content-box; }
.dr-control{ margin-bottom:15px; }
.dr-label{ display:block; font-family:'Fredoka',sans-serif; font-weight:600; font-size:13.5px;
  color:var(--dr-ink); margin-bottom:6px; }
.dr-label .opt-tag{ font-family:'DM Sans',sans-serif; font-weight:500; font-size:10.5px;
  color:var(--dr-soft); text-transform:uppercase; letter-spacing:.05em; margin-left:6px; }
.dr-help{ font-size:11.5px; color:var(--dr-soft); margin-top:4px; line-height:1.4; }
.left-panel input[type=text]{ width:100%; padding:11px 13px; font-size:14px; }

/* a leading pin/flag glyph for the start & destination fields */
.field-wrap{ position:relative; }
.field-wrap > input[type=text]{ padding-left:34px; }
/* city picker <select> — styled to match the text inputs (no native chrome) */
.field-wrap > select.dr-field{
  width:100%; padding:11px 38px 11px 34px; font-size:14px;
  font-family:'DM Sans',ui-sans-serif,system-ui,sans-serif; color:var(--dr-ink);
  border:2px solid var(--dr-line); border-radius:var(--dr-r); background-color:#FFFEFB;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2.5 4.5l3.5 3.5 3.5-3.5' fill='none' stroke='%236B6256' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat; background-position:right 14px center; background-size:12px;
  -webkit-appearance:none; -moz-appearance:none; appearance:none; cursor:pointer;
  transition:border-color .18s, box-shadow .18s; }
.field-wrap > select.dr-field:hover{ border-color:#D8C9A8; }
.field-wrap > select.dr-field:focus{ outline:none; border-color:var(--dr-cobalt);
  box-shadow:0 0 0 4px rgba(47,93,244,.14); }
.field-wrap::before{ content:attr(data-glyph); position:absolute; left:12px; top:50%;
  transform:translateY(-50%); font-size:14px; pointer-events:none; z-index:2; line-height:1; }

.combo{ position:relative; }
.combo-list{ position:absolute; z-index:60; left:0; right:0; top:calc(100% + 5px);
  background:var(--dr-paper); border:1.5px solid var(--dr-line); border-radius:16px;
  box-shadow:0 18px 38px -16px rgba(43,38,32,.45); display:none; padding:5px;
  max-height:min(46vh,300px); overflow-y:auto; overflow-x:hidden;
  overscroll-behavior:contain; }
.combo-list.open{ display:block; animation:drPop .16s var(--dr-spring); }
@keyframes drPop{ from{ transform:translateY(-4px); opacity:.4; } to{ transform:none; opacity:1; } }
.combo-list div{ padding:9px 11px; font-size:13.5px; cursor:pointer; border-radius:11px;
  display:flex; align-items:center; gap:8px; transition:background .12s; }
.combo-list div::before{ content:'📍'; font-size:11px; opacity:.55; }
.combo-list div:hover,.combo-list div.active{ background:#F1FAF4; }
.combo-list div.active{ box-shadow:inset 0 0 0 1.5px rgba(47,164,99,.4); }

/* ---- VIBE — the star input ---- */
.vibe-block{ background:var(--dr-paper); border:1.5px solid var(--dr-line); border-radius:20px;
  padding:14px 14px 12px; margin-bottom:16px;
  box-shadow:0 14px 34px -22px rgba(43,38,32,.4); position:relative; }
.vibe-block::before{ content:'⭐ start here'; position:absolute; top:-9px; left:14px;
  background:var(--dr-sun); color:#5A3D00; font-family:'Fredoka',sans-serif; font-weight:600;
  font-size:10px; letter-spacing:.04em; text-transform:uppercase; padding:2px 9px;
  border-radius:999px; box-shadow:0 4px 10px -4px rgba(255,194,71,.9); }
.vibe-block .dr-label{ font-size:15px; margin-top:2px; }
.vibe-block input[type=text]{ font-size:15px !important; }
.vibe-chips{ display:flex; flex-wrap:wrap; gap:7px; margin-top:10px; }
.vibe-chips .chip{ border:1.5px solid var(--dr-line); background:#FFFDF8; color:var(--dr-ink);
  border-radius:999px; padding:6px 12px; font-size:12px; font-family:'DM Sans',sans-serif;
  font-weight:500; cursor:pointer; transition:all .18s var(--dr-spring); }
.vibe-chips .chip:hover{ transform:translateY(-2px); border-color:var(--dr-coral);
  background:#FFF1ED; box-shadow:0 8px 16px -10px rgba(255,106,82,.7); }
.vibe-chips .chip:active{ transform:translateY(0); }
.vibe-chips .chip.on{ border-color:var(--dr-coral); background:var(--dr-coral); color:#fff;
  box-shadow:0 8px 18px -8px rgba(255,106,82,.8); }

/* condensed single-row sliders: label · min-cap · slider · max-cap · value */
.dr-slider-1{ display:flex; align-items:center; gap:8px; }
.dr-slider-1 > .dr-label{ margin:0; flex:0 0 auto; width:58px; font-size:12.5px; line-height:1.1; }
.dr-slider-1 .cap{ flex:0 0 auto; font-size:10px; color:var(--dr-soft); white-space:nowrap; }
.dr-slider-1 .srng{ flex:1 1 auto; min-width:40px; display:flex; }
.dr-slider-1 .srng input[type=range]{ width:100%; }
.dr-slider-1 > .val{ flex:0 0 auto; min-width:30px; text-align:right;
  font-family:'JetBrains Mono',monospace; font-size:11.5px; color:var(--dr-soft);
  padding:2px 6px; background:#FFFDF8; border:1px solid var(--dr-line); border-radius:9px; }
/* keep the grass-accented thumb on the optional green/quiet sliders */
#dr-green input[type=range]::-webkit-slider-thumb,
#dr-quiet input[type=range]::-webkit-slider-thumb{ border-color:var(--dr-grass); }

details.dr-collapse{ padding:0; margin-bottom:14px; }
details.dr-collapse summary{ list-style:none; cursor:pointer; padding:12px 15px;
  font-family:'Fredoka',sans-serif; font-weight:600; font-size:13px; color:var(--dr-ink);
  display:flex; align-items:center; justify-content:space-between; gap:8px; }
details.dr-collapse summary::-webkit-details-marker{ display:none; }
details.dr-collapse summary::after{ content:'▾'; color:var(--dr-soft); font-size:12px;
  transition:transform .2s ease; }
details.dr-collapse[open] summary::after{ transform:rotate(180deg); }
details.dr-collapse[open] summary{ border-bottom:1.5px dashed var(--dr-line); }
details.dr-collapse .collapse-body{ padding:13px 15px; }

.dr-cta-wrap{ flex:0 0 auto; padding:12px 18px 16px; background:var(--dr-cream);
  border-top:1px solid var(--dr-line); box-shadow:0 -10px 22px -18px rgba(43,38,32,.5); }
#dr-plan button{ width:100%; padding:15px; cursor:pointer; }
.cta-hint{ text-align:center; font-size:11px; color:var(--dr-soft); margin-top:8px; }
.dr-note{ font-size:12.5px; color:var(--dr-soft); margin:8px 0; }
.dr-row{ display:flex; gap:8px; }
.dr-row button{ flex:1; padding:9px; border-radius:12px; border:1.5px solid var(--dr-line);
  background:var(--dr-paper); font-family:'Fredoka',sans-serif; font-weight:600; cursor:pointer;
  color:var(--dr-ink); transition:all .16s var(--dr-spring); }
.dr-row button:hover{ transform:translateY(-2px); border-color:var(--dr-cobalt); }
.dr-star{ width:100%; margin-top:10px; padding:10px; border-radius:12px; border:1.5px dashed var(--dr-line);
  background:#FFFDF8; font-family:'Fredoka',sans-serif; font-weight:600; cursor:pointer;
  color:var(--dr-ink); transition:all .16s var(--dr-spring); }
.dr-star:hover{ transform:translateY(-2px); border-color:var(--dr-sun); background:#FFF8E8; }

/* ---- right column: full-bleed map (the hero element) ---- */
.right-col{ grid-column:2; grid-row:1; position:relative; height:100%; min-width:0; overflow:hidden; }
.map-container{ position:absolute; inset:0; }
/* full-bleed: strip the framed-window chrome that DR_CSS gives #dr-map */
#dr-map{ height:100%; border:none !important; border-radius:0 !important;
  box-shadow:none !important; background:#F6ECD9; }
#dr-map::before{ display:none !important; }
#dr-map .map-inner{ position:absolute; inset:0; }
#dr-map .map-inner > div,
#dr-map iframe,
#dr-map .folium-map,
#dr-map .leaflet-container{ width:100% !important; height:100% !important; }
#dr-map .map-inner > div > div{ padding-bottom:0 !important; height:100% !important; }

/* the styled result blocks only exist once a route is planned */
#dr-summary:empty, #dr-interp:empty, #dr-itin:empty, #dr-nodetour:empty{ display:none; }

/* ---- floating results sheet: overlays the map, never resizes it ---- */
.results-sheet{ position:absolute; left:16px; right:16px; bottom:16px; z-index:30;
  display:flex; flex-direction:column; max-height:46%;
  background:var(--dr-paper); border:1px solid var(--dr-line); border-radius:22px;
  box-shadow:0 26px 64px -26px rgba(43,38,32,.62); overflow:hidden;
  animation:drSheetIn .34s var(--dr-spring); }
@keyframes drSheetIn{ from{ transform:translateY(16px); opacity:.4; } to{ transform:none; opacity:1; } }
.results-sheet[hidden]{ display:none; }
.sheet-head{ flex:0 0 auto; display:flex; align-items:stretch; cursor:pointer; }
.sheet-head #dr-summary{ flex:1 1 auto; margin:0 !important; border-radius:0 !important; }
.sheet-toggle{ flex:0 0 auto; width:46px; border:none; cursor:pointer; color:#fff;
  background:var(--dr-grass-d); font-size:16px; display:grid; place-items:center;
  transition:background .15s, transform .25s var(--dr-spring); }
.sheet-toggle:hover{ background:#1A6B3E; }
.results-sheet.collapsed .sheet-toggle{ transform:rotate(180deg); }
.sheet-body{ flex:1 1 auto; min-height:0; overflow-y:auto; padding:14px 18px 16px;
  scrollbar-width:thin; scrollbar-color:var(--dr-line) transparent; }
.sheet-body::-webkit-scrollbar{ width:9px; }
.sheet-body::-webkit-scrollbar-thumb{ background:var(--dr-line); border-radius:9px;
  border:3px solid transparent; background-clip:content-box; }
.results-sheet.collapsed .sheet-body{ display:none; }

/* export-to-maps row inside the results sheet */
.export-row{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-bottom:14px;
  padding-bottom:14px; border-bottom:1px dashed var(--dr-line); }
.export-row[hidden]{ display:none; }
.export-label{ font-family:'Fredoka',sans-serif; font-weight:600; font-size:12px;
  color:var(--dr-soft); margin-right:2px; }
.ex-btn{ display:inline-flex; align-items:center; gap:5px; font-family:'DM Sans',sans-serif;
  font-size:12.5px; font-weight:600; color:var(--dr-ink); text-decoration:none; cursor:pointer;
  border:1.5px solid var(--dr-line); background:#FFFDF8; border-radius:999px; padding:6px 12px;
  transition:transform .16s var(--dr-spring), border-color .16s, background .16s; }
.ex-btn:hover{ transform:translateY(-2px); border-color:var(--dr-cobalt); background:#F0F4FF; }
.ex-note{ flex-basis:100%; font-size:11px; color:var(--dr-soft); line-height:1.4; }
.data-note{ margin-top:14px; padding-top:12px; border-top:1px dashed var(--dr-line);
  font-size:10.5px; color:var(--dr-soft); line-height:1.45; }
#dr-options{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:14px; }
#dr-options:empty{ display:none; }
#dr-options .opt{ border:2px solid var(--dr-line); border-radius:var(--dr-r); padding:11px 14px;
  background:var(--dr-paper); color:var(--dr-ink); cursor:pointer; font-size:12.5px; font-weight:500;
  box-shadow:0 6px 16px -14px rgba(43,38,32,.5);
  transition:transform .2s var(--dr-spring), border-color .2s, box-shadow .2s; }
#dr-options .opt:hover{ transform:translateY(-3px); }
#dr-options .opt.selected{ border-color:var(--dr-grass); background:#F1FAF4;
  box-shadow:0 10px 26px -14px rgba(47,164,99,.6); }

/* onboarding hint shown in the itinerary slot before the first plan */
.onboard{ background:#FFFDF8; border:1.5px dashed var(--dr-line); border-radius:var(--dr-r);
  padding:16px 18px; display:flex; gap:13px; align-items:flex-start; }
.onboard .ob-emoji{ font-size:22px; line-height:1; flex-shrink:0; margin-top:1px; }
.onboard h3{ font-family:'Fredoka',sans-serif; font-weight:600; font-size:15px; margin:0 0 3px;
  color:var(--dr-ink); }
.onboard p{ margin:0; font-size:12.5px; color:var(--dr-soft); line-height:1.5; }

/* ---- loading: live-map teaser (State 2) ---- */
#dr-loading{ position:absolute; inset:0; z-index:40; display:none;
  place-items:center;
  background:radial-gradient(700px 320px at 50% 0%,#FBEFD6 0%,transparent 70%),#F6ECD9; }
#dr-loading.on{ display:grid; animation:drFade .25s ease; }
@keyframes drFade{ from{ opacity:0; } to{ opacity:1; } }
/* State 1 — non-Paris graph load (inert for the Paris demo, built per brief) */
#dr-mapping{ position:absolute; inset:0; z-index:41; display:none; place-items:center;
  background:#F6ECD9; }
#dr-mapping.on{ display:grid; }
#dr-mapping .pulse{ width:18px;height:18px;border-radius:50%;background:var(--dr-grass);
  animation:drPulse 1.1s ease-in-out infinite; margin:0 auto 10px; }
@keyframes drPulse{ 0%,100%{ transform:scale(.7); opacity:.5; } 50%{ transform:scale(1.1); opacity:1; } }

/* live-map teaser loader — a route threads itself between popping pins while we plan */
.teaser-map{ width:288px; max-width:80vw; margin:20px auto 0; }
.teaser-map svg{ width:100%; height:auto; display:block;
  filter:drop-shadow(0 14px 30px rgba(43,38,32,.16)); }
.route-line{ stroke-dasharray:360; stroke-dashoffset:360; animation:drDraw 3.4s ease-in-out infinite; }
@keyframes drDraw{ 0%{ stroke-dashoffset:360; } 55%{ stroke-dashoffset:0; }
  90%{ stroke-dashoffset:0; } 100%{ stroke-dashoffset:360; } }
.teaser-map .pin{ opacity:0; transform-box:fill-box; transform-origin:center;
  animation:drPinPop 3.4s var(--dr-spring) infinite; }
.teaser-map .p-start{ animation-delay:.15s; } .teaser-map .p1{ animation-delay:1s; }
.teaser-map .p2{ animation-delay:1.7s; } .teaser-map .p-end{ animation-delay:2.3s; }
@keyframes drPinPop{ 0%{ opacity:0; transform:scale(.2); } 9%{ opacity:1; transform:scale(1.25); }
  16%{ transform:scale(1); } 86%{ opacity:1; } 100%{ opacity:0; transform:scale(1); } }
.teaser-map .walker{ offset-rotate:0deg; animation:drWalk 3.4s ease-in-out infinite;
  offset-path:path("M26,120 C66,112 70,66 116,70 C150,73 168,44 206,58 C236,69 246,40 262,34"); }
@keyframes drWalk{ 0%{ offset-distance:0%; opacity:0; } 8%{ opacity:1; }
  55%{ offset-distance:100%; opacity:1; } 64%{ opacity:0; } 100%{ offset-distance:100%; opacity:0; } }
@media (prefers-reduced-motion: reduce){
  .route-line{ animation:none; stroke-dashoffset:0; }
  .teaser-map .pin{ animation:none; opacity:1; }
  .teaser-map .walker{ animation:none; opacity:0; } }

/* no-detour sticker slot */
#dr-nodetour:empty{ display:none; }
#dr-nodetour{ margin-bottom:14px; }

/* mobile FAB (hidden on desktop) */
.fab{ display:none; }

/* ---- mobile: left panel → bottom drawer, full-screen map, coral FAB ---- */
@media (max-width:768px){
  .app-shell{ grid-template-columns:1fr; grid-template-rows:1fr; }
  .right-col{ grid-column:1; grid-row:1; }
  .results-sheet{ left:10px; right:10px; bottom:10px; max-height:56%; }
  .left-panel{ position:fixed; left:0; right:0; bottom:0; top:auto; z-index:200; width:100%;
    height:auto; max-height:86vh; max-height:86dvh; border-right:none; border-top-left-radius:26px;
    border-top-right-radius:26px; box-shadow:0 -18px 44px -20px rgba(43,38,32,.4);
    transform:translateY(110%); transition:transform .32s var(--dr-spring);
    padding-top:8px; }
  .left-panel.open{ transform:translateY(0); }
  /* denser drawer so more of the menu is visible in the cramped mobile height */
  .panel-scroll{ padding:12px 16px 8px; }
  .dr-control{ margin-bottom:12px; }
  .brand{ margin-bottom:10px; }
  .vibe-chips{ gap:7px; }
  .fab{ display:grid; place-items:center; position:fixed; right:18px; bottom:18px; z-index:210;
    width:62px; height:62px; border-radius:50%; border:none; cursor:pointer;
    background:var(--dr-coral); color:#fff; font-size:15px; font-family:'Fredoka',sans-serif;
    font-weight:600; line-height:1.05; text-align:center;
    box-shadow:0 12px 26px -8px rgba(255,106,82,.85); transition:transform .18s var(--dr-spring); }
  .fab:hover{ transform:translateY(-3px); }
  .drawer-close{ display:flex; }
}
.drawer-close{ display:none; align-items:center; justify-content:center; width:44px; height:44px;
  margin:0 auto 4px; border-radius:50%; background:#FFFDF8; border:1.5px solid var(--dr-line);
  font-size:22px; color:var(--dr-soft); cursor:pointer; }
.drawer-grip{ display:none; }
@media (max-width:768px){ .drawer-grip{ display:block; width:42px; height:5px; border-radius:999px;
  background:var(--dr-line); margin:2px auto 8px; } }

@media (prefers-reduced-motion:reduce){ *{ animation:none !important; transition:none !important; } }
"""


_VIBE_PRESETS = [
    "quiet green wander",
    "lively café crawl",
    "bookshops & old churches",
    "morning coffee crawl",
    "riverside stroll",
    "art & history",
]


def _vibe_chips() -> str:
    chips = "".join(
        f'<button type="button" class="chip" data-vibe="{v.replace(chr(34), "")}">{v}</button>'
        for v in _VIBE_PRESETS
    )
    return f'<div class="vibe-chips" id="dr-vibe-chips">{chips}</div>'


# (slug, label) for the city picker: Paris (the always-on default) then every
# configured core. The chosen slug is sent to /plan and wins area resolution.
_CITY_CHOICES = [("paris", "Paris")] + [
    (slug, spec["label"]) for slug, spec in config.CITIES.items()
]


def _city_options() -> str:
    opts = "".join(
        f'<option value="{slug}"{" selected" if slug == "paris" else ""}>{label}</option>'
        for slug, label in _CITY_CHOICES
    )
    return opts


def _left_panel() -> str:
    return f"""
<aside class="left-panel" id="left-panel">
  <div class="drawer-grip"></div>
  <div class="drawer-close" id="drawer-close" role="button" tabindex="0"
       aria-label="Close controls">&times;</div>

  <div class="panel-scroll">
  <div class="brand">
    <span class="logo">🗺️</span>
    <span class="bname">WanderLust</span>
    <span class="titan-chip">1B · in-Space</span>
  </div>
  <div class="vibe-block">
    <div class="dr-control combo" style="margin-bottom:0;">
      <label class="dr-label" for="dr-vibe">What's your vibe today?</label>
      <input type="text" id="dr-vibe" class="dr-field"
             placeholder="Describe the wander you're after…">
      <div class="dr-help">Tell me the mood — I'll read it and pick places to match.</div>
    </div>
    {_vibe_chips()}
  </div>

  <div class="dr-control">
    <label class="dr-label" for="dr-city">City</label>
    <div class="field-wrap" data-glyph="🌍">
      <select id="dr-city" class="dr-field">{_city_options()}</select>
    </div>
    <div class="dr-help">Pick the city to explore — Start &amp; Destination should be
      places within it.</div>
  </div>

  <div class="dr-control combo">
    <label class="dr-label" for="dr-start">Start</label>
    <div class="field-wrap" data-glyph="📍">
      <input type="text" id="dr-start" class="dr-field" autocomplete="off"
             value="Place de la République, Paris">
    </div>
    <div class="combo-list" id="dr-start-list"></div>
    <div class="dr-help">Try a landmark (e.g. "British Museum"), not a street address.</div>
  </div>

  <div class="dr-control combo">
    <label class="dr-label" for="dr-dest">Destination</label>
    <div class="field-wrap" data-glyph="🏁">
      <input type="text" id="dr-dest" class="dr-field" autocomplete="off"
             value="Jardin du Luxembourg, Paris">
    </div>
    <div class="combo-list" id="dr-dest-list"></div>
  </div>

  <div class="dr-control">
    <label class="dr-label">Mode</label>
    <div id="dr-mode" class="dr-seg">
      <div class="wrap">
        <label class="selected" data-v="walk" role="button" tabindex="0">🚶 walk</label>
        <label data-v="bike" role="button" tabindex="0">🚲 bike</label>
      </div>
    </div>
  </div>

  <div class="dr-control dr-slider-1">
    <label class="dr-label" for="dr-budget-i">Detour</label>
    <span class="cap">direct</span>
    <span id="dr-budget" class="srng"><input type="range" id="dr-budget-i" min="0" max="2"
          step="0.1" value="0.5" aria-label="Detour budget"></span>
    <span class="cap">2× longer</span>
    <output id="dr-budget-o" class="val">0.5</output>
  </div>

  <div class="dr-control dr-slider-1">
    <label class="dr-label" for="dr-adv-i">Adventure</label>
    <span class="cap">classic</span>
    <span id="dr-adv" class="srng"><input type="range" id="dr-adv-i" min="0" max="1"
          step="0.05" value="0.3" aria-label="Adventurousness"></span>
    <span class="cap">hidden gems</span>
    <output id="dr-adv-o" class="val">0.3</output>
  </div>

  <details class="dr-collapse">
    <summary>Manual taste <span class="opt-tag">optional</span></summary>
    <div class="collapse-body">
      <div class="dr-help" style="margin:0 0 10px;">Only used when Vibe and your saved
        profile are both empty.</div>
      <div class="dr-control dr-slider-1">
        <label class="dr-label" for="dr-green-i">Green</label>
        <span id="dr-green" class="srng green"><input type="range" id="dr-green-i" min="0"
              max="1" step="0.05" value="0.5" aria-label="Prefer green"></span>
        <output id="dr-green-o" class="val">0.5</output>
      </div>
      <div class="dr-control dr-slider-1" style="margin-bottom:0;">
        <label class="dr-label" for="dr-quiet-i">Quiet</label>
        <span id="dr-quiet" class="srng green"><input type="range" id="dr-quiet-i" min="0"
              max="1" step="0.05" value="0.5" aria-label="Prefer quiet"></span>
        <output id="dr-quiet-o" class="val">0.5</output>
      </div>
    </div>
  </details>

  <details class="dr-collapse">
    <summary>⭐ My taste profile <span class="opt-tag">saved on this device</span></summary>
    <div class="collapse-body">
      <label class="dr-label" for="dr-profile-text">Standing preferences</label>
      <input type="text" id="dr-profile-text" class="dr-field"
             placeholder="e.g. 'I always love bookshops, gardens, and old churches'">
      <div class="dr-row" style="margin-top:10px;">
        <button type="button" id="dr-save">Save</button>
        <button type="button" id="dr-clear">Clear</button>
      </div>
      <div class="dr-note" id="dr-saved"></div>
      <button type="button" class="dr-star" id="dr-save-places">⭐ Save this route's places</button>
    </div>
  </details>
  </div>

  <div class="dr-cta-wrap">
    <div id="dr-plan"><button type="button" id="dr-plan-btn">Plan my route →</button></div>
    <div class="cta-hint">Reads your vibe · threads a detour · writes the itinerary</div>
  </div>
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
  {_left_panel()}
  <main class="right-col">
    <div class="map-container">
      <div id="dr-map"><div class="map-inner">{empty}</div></div>
      <div id="dr-mapping"><div><div class="pulse"></div>
        <span style="font-family:'Fredoka',sans-serif;font-weight:600;">Mapping the streets…</span></div></div>
      <div id="dr-loading">{_loading_inner()}</div>
    </div>
    <section class="results-sheet" id="results-sheet" hidden aria-label="Route details">
      <div class="sheet-head" id="sheet-head">
        <div id="dr-summary"></div>
        <button class="sheet-toggle" id="sheet-toggle" aria-label="Collapse or expand details"
                title="Collapse / expand">&#9662;</button>
      </div>
      <div class="sheet-body">
        <div class="export-row" id="export-row" hidden>
          <span class="export-label">Take it with you</span>
          <a id="ex-gmaps" class="ex-btn" target="_blank" rel="noopener noreferrer">🗺️ Google&nbsp;Maps</a>
          <a id="ex-apple" class="ex-btn" target="_blank" rel="noopener noreferrer">🍎 Apple&nbsp;Maps</a>
          <button id="ex-gpx" class="ex-btn" type="button">⬇️ GPX file</button>
          <span class="ex-note" id="ex-note"></span>
        </div>
        <div id="dr-options"></div>
        <div id="dr-nodetour"></div>
        <div id="dr-interp"></div>
        <div id="dr-itin"></div>
        <div class="data-note">{_provenance_line()}</div>
      </div>
    </section>
  </main>
</div>
<button class="fab" id="fab" aria-label="Open route controls">Plan</button>

<script type="module">{_app_js()}</script>
</body>
</html>"""


_TEASER_PATH = "M26,120 C66,112 70,66 116,70 C150,73 168,44 206,58 C236,69 246,40 262,34"


def _loading_inner() -> str:
    """Live-map teaser: a little route threads itself between popping pins while
    we plan — a playful preview of the real map so the wait feels like progress."""
    return f"""
<div style="text-align:center; max-width:540px; padding:0 16px;">
  <div style="font-family:'Fredoka',system-ui,sans-serif;font-weight:600;font-size:21px;
       color:#2B2620;">Scouting your wander…</div>
  <div style="font-family:'DM Sans',system-ui,sans-serif;font-size:13px;color:#6B6256;
       margin-top:6px;">reading your vibe · scoring 30,000 places · threading the detour</div>
  <div class="teaser-map" aria-hidden="true">
    <svg viewBox="0 0 288 150" role="img">
      <rect x="0" y="0" width="288" height="150" rx="18" fill="#FFFCF5" stroke="#E7DAC0"/>
      <g stroke="#EFE3C8" stroke-width="2" stroke-linecap="round">
        <line x1="20" y1="40" x2="268" y2="34"/><line x1="16" y1="92" x2="272" y2="100"/>
        <line x1="70" y1="16" x2="84" y2="138"/><line x1="178" y1="14" x2="196" y2="140"/>
      </g>
      <path class="route-line" d="{_TEASER_PATH}" fill="none" stroke="var(--dr-cobalt)"
            stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
      <circle class="pin p-start" cx="26"  cy="120" r="6.5" fill="var(--dr-grass)"  stroke="#fff" stroke-width="2"/>
      <circle class="pin p1"      cx="116" cy="70"  r="5.5" fill="var(--dr-coral)"  stroke="#fff" stroke-width="2"/>
      <circle class="pin p2"      cx="206" cy="58"  r="5.5" fill="var(--dr-coral)"  stroke="#fff" stroke-width="2"/>
      <circle class="pin p-end"   cx="262" cy="34"  r="6.5" fill="var(--dr-cobalt)" stroke="#fff" stroke-width="2"/>
      <circle class="walker" r="4.5" fill="#fff" stroke="var(--dr-cobalt)" stroke-width="3"/>
    </svg>
  </div>
</div>
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

/* ---------- mode segmented toggle (mouse + keyboard) ---------- */
let mode = "walk";
function pickMode(l) {
  document.querySelectorAll("#dr-mode label").forEach(x => {
    x.classList.remove("selected"); x.setAttribute("aria-pressed", "false");
  });
  l.classList.add("selected"); l.setAttribute("aria-pressed", "true"); mode = l.dataset.v;
}
document.querySelectorAll("#dr-mode label").forEach(l => {
  l.addEventListener("click", () => pickMode(l));
  l.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pickMode(l); }
  });
});

/* ---------- vibe preset chips (fill the field on click) ---------- */
const vibeInput = $("dr-vibe");
function syncVibeChips() {
  const v = (vibeInput.value || "").trim().toLowerCase();
  document.querySelectorAll("#dr-vibe-chips .chip").forEach(c =>
    c.classList.toggle("on", (c.dataset.vibe || "").toLowerCase() === v));
}
document.querySelectorAll("#dr-vibe-chips .chip").forEach(c => {
  c.addEventListener("click", () => {
    vibeInput.value = c.dataset.vibe || "";
    syncVibeChips();
    vibeInput.focus();
  });
});
vibeInput.addEventListener("input", syncVibeChips);

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

/* ---------- loader (live-map teaser; CSS-animated while visible) ---------- */
function hideOnboard() { const o = $("dr-onboard"); if (o) o.style.display = "none"; }
function startLoading() {
  hideOnboard();
  hideSheet();
  $("dr-loading").classList.add("on");
  $("dr-summary").innerHTML = ""; $("dr-itin").innerHTML = "";
  $("dr-interp").innerHTML = ""; $("dr-options").innerHTML = ""; $("dr-nodetour").innerHTML = "";
}
function stopLoading() { $("dr-loading").classList.remove("on"); }

/* ---------- render ---------- */
const REDUCE = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let lastAlts = [], lastCats = [], geo = null, curExport = null;
function renderMap(html) { $("dr-map").innerHTML = '<div class="map-inner">' + html + "</div>"; }

/* ---------- export to maps (client-side; data already in the /plan payload) ---------- */
function _ll(p) { return (+p[0]).toFixed(6) + "," + (+p[1]).toFixed(6); }
function buildGmaps(start, end, wps, mode) {
  const travel = mode === "bike" ? "bicycling" : "walking";
  let u = "https://www.google.com/maps/dir/?api=1&origin=" + _ll(start) +
          "&destination=" + _ll(end) + "&travelmode=" + travel;
  const w = (wps || []).slice(0, 9).map(p => p.lat.toFixed(6) + "," + p.lon.toFixed(6));
  if (w.length) u += "&waypoints=" + encodeURIComponent(w.join("|"));
  return u;
}
function buildApple(start, end) {
  return "https://maps.apple.com/?saddr=" + _ll(start) + "&daddr=" + _ll(end) + "&dirflg=w";
}
function _xml(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
function buildGpx(name, start, end, wps, coords) {
  const L = ['<?xml version="1.0" encoding="UTF-8"?>',
    '<gpx version="1.1" creator="WanderLust" xmlns="http://www.topografix.com/GPX/1/1">',
    "<metadata><name>" + _xml(name) + "</name></metadata>"];
  if (start) L.push('<wpt lat="' + start[0].toFixed(6) + '" lon="' + start[1].toFixed(6) + '"><name>Start</name></wpt>');
  (wps || []).forEach(p => L.push('<wpt lat="' + p.lat.toFixed(6) + '" lon="' + p.lon.toFixed(6) + '"><name>' + _xml(p.name) + "</name></wpt>"));
  if (end) L.push('<wpt lat="' + end[0].toFixed(6) + '" lon="' + end[1].toFixed(6) + '"><name>Destination</name></wpt>');
  L.push("<trk><name>" + _xml(name) + "</name><trkseg>");
  (coords || []).forEach(c => L.push('<trkpt lat="' + (+c[0]).toFixed(6) + '" lon="' + (+c[1]).toFixed(6) + '"/>'));
  L.push("</trkseg></trk></gpx>");
  return L.join("\n");
}
function refreshExport() {
  const row = $("export-row");
  if (!row) return;
  if (!geo || !geo.start || !geo.end || !curExport) { row.hidden = true; return; }
  row.hidden = false;
  const wps = curExport.waypoints || [];
  $("ex-gmaps").href = buildGmaps(geo.start, geo.end, wps, geo.mode);
  $("ex-apple").href = buildApple(geo.start, geo.end);
  $("ex-note").textContent = (wps.length > 9
    ? "Google Maps fits 9 stops — the GPX keeps all " + wps.length + ". " : "") +
    "Apple Maps shows start → end only; the GPX keeps every stop.";
}
function downloadGpx() {
  if (!geo || !curExport) return;
  const gpx = buildGpx("WanderLust route", geo.start, geo.end, curExport.waypoints, curExport.coords);
  const blob = new Blob([gpx], { type: "application/gpx+xml" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "wanderlust-route.gpx";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1500);
}
function enter(el) {
  if (!el || REDUCE) return;
  try { el.animate([{ transform: "translateY(10px)", opacity: 0.001 }, { transform: "none", opacity: 1 }],
    { duration: 420, easing: "cubic-bezier(.34,1.56,.64,1)" }); } catch (e) {}
}
// Organic squash-and-pop on tap/click — springy overshoot, settles back.
function bounce(el) {
  if (!el || REDUCE) return;
  try {
    el.animate(
      [{ transform: "scale(1)" }, { transform: "scale(.90)" },
       { transform: "scale(1.06)" }, { transform: "scale(.985)" }, { transform: "scale(1)" }],
      { duration: 440, easing: "cubic-bezier(.34,1.56,.64,1)" });
  } catch (e) {}
}
function selectAlt(idx) {
  const a = lastAlts[idx]; if (!a) return;
  renderMap(a.map_html);
  $("dr-summary").innerHTML = md(a.summary_md);
  $("dr-itin").innerHTML = md(a.itinerary_md);
  enter($("dr-summary")); enter($("dr-itin"));
  document.querySelectorAll("#dr-options .opt").forEach((o, i) =>
    o.classList.toggle("selected", i === idx));
  curExport = a.export || null; refreshExport();
}
function renderResult(d) {
  hideOnboard();
  if (d.error) { hideSheet(); renderMap(d.map_html); toast(d.error); return; }
  geo = { start: d.start, end: d.end, mode: d.mode,
          start_label: d.start_label, end_label: d.end_label };
  $("dr-interp").innerHTML = md(d.interpretation_md);
  enter($("dr-interp"));
  if (d.no_detour) {
    renderMap(d.map_html);
    $("dr-summary").innerHTML = md(d.summary_md);
    $("dr-itin").innerHTML = md(d.itinerary_md);
    $("dr-nodetour").innerHTML = d.nodetour_html || "";
    lastAlts = []; lastCats = [];
    curExport = d.export || null; refreshExport();
    showSheet();
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
  showSheet();
}

/* ---------- plan ---------- */
async function plan() {
  closeDrawer();  // mobile: reveal the full-screen map + route
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
      city: $("dr-city").value,
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
const openDrawer = () => $("left-panel").classList.add("open");
const closeDrawer = () => $("left-panel").classList.remove("open");
$("fab").addEventListener("click", openDrawer);
$("drawer-close").addEventListener("click", closeDrawer);

/* Keep the bottom drawer usable when the on-screen keyboard opens. On phones the
   keyboard shrinks the *visual* viewport (and on iOS overlays a fixed element)
   so a dvh-sized drawer gets crushed or hidden. We size the drawer to the
   visible area above the keyboard and scroll the focused field into view. */
(function () {
  const vv = window.visualViewport;
  if (!vv) return;
  const panel = $("left-panel");
  const fit = () => {
    if (window.innerWidth > 768 || !panel.classList.contains("open")) {
      panel.style.maxHeight = ""; return;          // desktop / closed: CSS rules
    }
    panel.style.maxHeight = Math.round(vv.height * 0.94) + "px";
  };
  vv.addEventListener("resize", fit);
  vv.addEventListener("scroll", fit);
  document.addEventListener("focusin", (e) => {
    if (window.innerWidth > 768) return;
    const field = e.target.closest && e.target.closest(".left-panel input, .left-panel textarea");
    if (!field) return;
    openDrawer(); fit();
    // let the keyboard animate in, then center the field within the scroll area
    setTimeout(() => field.scrollIntoView({ block: "center", behavior: "smooth" }), 280);
  });
  document.addEventListener("focusout", () => {
    if (window.innerWidth <= 768) setTimeout(fit, 100);
  });
})();

/* ---------- floating results sheet (collapsible overlay) ---------- */
function showSheet() { const s = $("results-sheet"); if (s) { s.hidden = false; s.classList.remove("collapsed"); } }
function hideSheet() { const s = $("results-sheet"); if (s) s.hidden = true; }
$("sheet-head").addEventListener("click", () => $("results-sheet").classList.toggle("collapsed"));
$("ex-gpx").addEventListener("click", downloadGpx);

/* ---------- organic bounce on interaction (delegated, capture phase) ---------- */
document.addEventListener("click", (e) => {
  const el = e.target.closest(
    "#dr-plan button, .vibe-chips .chip, #dr-mode label, #dr-options .opt, " +
    ".dr-row button, .dr-star, details.dr-collapse > summary, #fab, .drawer-close");
  if (el) bounce(el);
}, true);
$("drawer-close").addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); closeDrawer(); }
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

/* Enter in any text field plans the route (except while a suggestion list is open). */
["dr-vibe", "dr-start", "dr-dest"].forEach(id => {
  const el = $(id); if (!el) return;
  el.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const lists = document.querySelectorAll(".combo-list.open");
    if (lists.length) return;            // let the combo handle its own Enter
    e.preventDefault(); plan();
  });
});

syncVibeChips();
renderSaved();
"""
