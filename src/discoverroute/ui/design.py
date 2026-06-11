"""DiscoverRoute design system — ported from the Claude-design handoff kit.

Source of truth: design_handoff_discoverroute (tokens.css / gradio-integration-kit).
Low-poly "clay sticker" aesthetic: cream paper, cobalt/grass/coral/sun blocks,
Fredoka display type, springy micro-interactions, framed map window.

Everything here is presentation only — no behavior. The strings are consumed by
app.py (theme/css/head/js) and ui/map.py (in-iframe animation script).
"""
from __future__ import annotations

import gradio as gr

# ---------------------------------------------------------------- theme (§1)
def build_theme() -> gr.themes.Soft:
    return gr.themes.Soft(
        primary_hue=gr.themes.colors.blue,      # cobalt — primary actions
        secondary_hue=gr.themes.colors.green,   # grass — discovery route
        neutral_hue=gr.themes.colors.stone,     # warm cream neutrals
        font=[gr.themes.GoogleFont("DM Sans"), "ui-sans-serif", "system-ui"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
        radius_size=gr.themes.sizes.radius_lg,
        spacing_size=gr.themes.sizes.spacing_lg,
        text_size=gr.themes.sizes.text_md,
    ).set(
        body_background_fill="#F6ECD9",
        body_text_color="#2B2620",
        background_fill_primary="#FFFCF5",
        border_color_primary="#E7DAC0",
        button_primary_background_fill="#FF6A52",
        button_primary_background_fill_hover="#FF5640",
        button_primary_text_color="#FFFFFF",
        slider_color="#2F5DF4",
        input_background_fill="#FFFEFB",
        input_border_color_focus="#2F5DF4",
    )


# ---------------------------------------------------------------- css (§2+§5)
DR_CSS = """
/* ---- tokens ---- */
:root{
  --dr-cream:#F6ECD9; --dr-paper:#FFFCF5; --dr-ink:#2B2620; --dr-soft:#6B6256;
  --dr-line:#E7DAC0; --dr-cobalt:#2F5DF4; --dr-cobalt-d:#214AD0; --dr-grass:#2FA463;
  --dr-grass-d:#1F7D49; --dr-coral:#FF6A52; --dr-coral-d:#E14D37; --dr-sun:#FFC247;
  --dr-r:18px; --dr-spring:cubic-bezier(.34,1.56,.64,1);
}
.gradio-container{ background:
  radial-gradient(1100px 520px at 88% -8%,#FBEFD6 0%,transparent 60%), var(--dr-cream) !important; }

/* display font on labels + headings */
.gradio-container label span, .gradio-container h1, .gradio-container h2,
.gradio-container h3, .dr-label{
  font-family:'Fredoka',sans-serif !important; font-weight:600; letter-spacing:-.01em;
}

/* cards / blocks become tactile stickers */
.gradio-container .block, .gradio-container .form{
  border-radius:26px !important; border:1px solid var(--dr-line) !important;
  box-shadow:0 18px 44px -20px rgba(43,38,32,.32) !important; background:var(--dr-paper) !important;
}

/* inputs — explicit ink color (theme override otherwise leaves them too pale) */
.gradio-container input[type=text], .gradio-container textarea{
  border:2px solid var(--dr-line) !important; border-radius:var(--dr-r) !important;
  background:#FFFEFB !important; color:var(--dr-ink) !important;
  transition:border-color .18s, box-shadow .18s !important;
}
.gradio-container input[type=text]::placeholder, .gradio-container textarea::placeholder{
  color:#B9AE99 !important; opacity:1;
}
.gradio-container input[type=text]:focus, .gradio-container textarea:focus{
  border-color:var(--dr-cobalt) !important; box-shadow:0 0 0 4px rgba(47,93,244,.14) !important;
}

/* primary 'Plan route' — depresses like a real button */
#dr-plan button, .gradio-container button.primary{
  font-family:'Fredoka',sans-serif !important; font-weight:600; font-size:18px !important;
  color:#fff !important; background:var(--dr-coral) !important; border:none !important;
  border-radius:var(--dr-r) !important;
  box-shadow:0 6px 0 var(--dr-coral-d), 0 14px 24px -10px rgba(255,106,82,.7) !important;
  transition:transform .12s, box-shadow .12s !important;
}
#dr-plan button:hover{ transform:translateY(-2px) !important; }
#dr-plan button:active{ transform:translateY(4px) !important;
  box-shadow:0 2px 0 var(--dr-coral-d) !important; }

/* mode toggle as a segmented control */
#dr-mode .wrap{ background:#F0E3CC; padding:5px; border-radius:var(--dr-r); gap:6px; }
#dr-mode label{ flex:1; justify-content:center; border:none !important;
  background:transparent !important; color:var(--dr-soft) !important;
  border-radius:13px !important; transition:all .2s var(--dr-spring); }
#dr-mode label span{ color:inherit !important; }
#dr-mode label.selected{ background:var(--dr-paper) !important; color:var(--dr-cobalt) !important;
  box-shadow:0 4px 12px -4px rgba(43,38,32,.25); transform:translateY(-1px); }

/* springy sliders — per-slider accents (budget coral · adventurousness sun ·
   green/quiet grass), per components.md §5 */
.gradio-container input[type=range]::-webkit-slider-thumb{
  width:26px;height:26px;border-radius:50%;background:#fff;border:4px solid var(--dr-cobalt);
  box-shadow:0 4px 10px -2px rgba(43,38,32,.4); transition:transform .15s var(--dr-spring); }
.gradio-container input[type=range]:active::-webkit-slider-thumb{ transform:scale(1.22); }
.dr-slider.green input[type=range]::-webkit-slider-thumb{ border-color:var(--dr-grass); }
.gradio-container input[type=range]{ accent-color:var(--dr-cobalt); }
#dr-budget input[type=range]{ accent-color:var(--dr-coral); }
#dr-budget input[type=range]::-webkit-slider-thumb{ border-color:var(--dr-coral); }
#dr-adv input[type=range]{ accent-color:var(--dr-sun); }
#dr-adv input[type=range]::-webkit-slider-thumb{ border-color:var(--dr-sun); }
#dr-green input[type=range], #dr-quiet input[type=range]{ accent-color:var(--dr-grass); }

/* collapsibles -> dashed taste cards (labels at full ink for readability) */
.dr-collapse{ border:1.5px dashed var(--dr-line) !important; border-radius:var(--dr-r) !important;
  background:#FFFDF8 !important; box-shadow:none !important; }
.dr-collapse .label-wrap span, .dr-collapse button span, .dr-collapse > button{
  color:var(--dr-ink) !important; opacity:1 !important; }

/* route-options radio -> selectable cards (paper bg + ink text, both states) */
#dr-options .wrap{ display:grid; grid-template-columns:repeat(3,1fr); gap:11px; }
#dr-options label{ border:2px solid var(--dr-line) !important; border-radius:var(--dr-r) !important;
  padding:14px !important; background:var(--dr-paper) !important; color:var(--dr-ink) !important;
  transition:all .2s var(--dr-spring); }
#dr-options label span, #dr-options label *{ color:var(--dr-ink) !important; }
#dr-options label:hover{ transform:translateY(-3px); }
#dr-options label.selected{ border-color:var(--dr-grass) !important; background:#F1FAF4 !important;
  box-shadow:0 10px 26px -14px rgba(47,164,99,.6) !important; }

/* the Leaflet iframe -> a framed 'window' with a titlebar */
#dr-map{ border-radius:26px !important; overflow:hidden; border:1px solid var(--dr-line);
  box-shadow:0 18px 44px -20px rgba(43,38,32,.34); position:relative; background:var(--dr-paper); }
#dr-map::before{ content:'Paris — live map'; display:block; font-family:'Fredoka',sans-serif;
  font-weight:600; font-size:13.5px; padding:11px 16px 11px 64px; color:var(--dr-ink);
  border-bottom:1px solid var(--dr-line);
  background-image:radial-gradient(circle at 20px 50%,#FF6A52 5px,transparent 5px),
    radial-gradient(circle at 36px 50%,#FFC247 5px,transparent 5px),
    radial-gradient(circle at 52px 50%,#2FA463 5px,transparent 5px),
    linear-gradient(180deg,#FFF,#FBF4E6); }
#dr-map iframe{ height:520px !important; border:none !important; display:block; width:100%; }

/* summary banner */
#dr-summary{ background:linear-gradient(110deg,#2FA463,#37B06E) !important; color:#fff !important;
  border-radius:var(--dr-r) !important; box-shadow:0 12px 26px -14px rgba(47,164,99,.8) !important;
  padding:14px 18px !important; }
#dr-summary *{ color:#fff !important; }

/* interpretation card */
#dr-interp{ background:var(--dr-paper) !important; border-radius:var(--dr-r) !important;
  padding:13px 18px !important; }

/* narrated itinerary -> numbered steps on a dashed timeline rail (components.md §13) */
#dr-itin{ background:var(--dr-paper) !important; border-radius:var(--dr-r) !important;
  padding:13px 18px !important; }
#dr-itin ol{ list-style:none; counter-reset:dr-step; margin:0; padding:0; position:relative; }
#dr-itin ol::before{ content:''; position:absolute; left:18px; top:10px; bottom:10px; width:2.5px;
  background:repeating-linear-gradient(180deg,var(--dr-line) 0 5px,transparent 5px 11px); }
#dr-itin ol > li{ counter-increment:dr-step; position:relative; z-index:1;
  padding:13px 0 13px 52px; border-bottom:1.5px dashed var(--dr-line);
  transition:transform .2s var(--dr-spring); }
#dr-itin ol > li:last-child{ border-bottom:none; }
#dr-itin ol > li:hover{ transform:translateX(5px); }
#dr-itin ol > li::before{ content:counter(dr-step); position:absolute; left:0; top:10px;
  width:36px; height:36px; border-radius:12px; display:grid; place-items:center;
  font-family:'Fredoka',sans-serif; font-weight:700; font-size:16px; color:#fff;
  background:var(--dr-grass); box-shadow:0 4px 0 var(--dr-grass-d);
  transition:transform .2s var(--dr-spring); }
#dr-itin ol > li:nth-child(3n+2)::before{ background:var(--dr-coral); box-shadow:0 4px 0 var(--dr-coral-d); }
#dr-itin ol > li:nth-child(3n)::before{ background:var(--dr-sun); box-shadow:0 4px 0 #E89E1C; }
#dr-itin ol > li:hover::before{ transform:translateY(-3px) rotate(-4deg); }

/* hero (gr.HTML wrapper sticker) */
#dr-hero{ background:transparent !important; border:none !important; box-shadow:none !important; }

/* hide gradio footer */
footer{ visibility:hidden; }

/* ---- responsive ---- */
@media (max-width: 860px){
  #dr-map iframe{ height: 440px !important; }
  #dr-options .wrap{ grid-template-columns: 1fr !important; }
  #dr-results{ margin-top: 14px; }
}
@media (max-width: 560px){
  .gradio-container{ padding: 12px !important; }
  .gradio-container h1{ font-size: 27px !important; }
  #dr-map::before{ font-size:12px; background-image:linear-gradient(180deg,#FFF,#FBF4E6); }
}

/* dark-mode belt-and-suspenders: even if the dark class sticks, keep the
   design's ink-on-cream readable (the head script also strips the class) */
.dark .gradio-container, .dark .gradio-container .prose,
.dark .gradio-container .prose *, .dark .gradio-container label span,
.dark .gradio-container p, .dark .gradio-container li{
  color:var(--dr-ink) !important; }

/* respect reduced motion */
@media (prefers-reduced-motion:reduce){
  .gradio-container *{ animation:none !important; transition:none !important; } }
/* AA focus rings everywhere */
.gradio-container *:focus-visible{ outline:3px solid var(--dr-cobalt) !important; outline-offset:3px; }
"""

# ---------------------------------------------------------------- head (§4)
# Includes the page enhancer as a real <script> — Gradio 6's launch(js=...)
# proved unreliable, while head= injection always executes.
DR_HEAD = """
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>
<link href='https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap' rel='stylesheet'>
<script>
(function(){
  // The clay design is light-only; Gradio applies a `dark` class from the OS
  // preference, flipping text vars to near-white on our cream cards. Strip it
  // and keep it stripped.
  var forceLight = function(){
    document.documentElement.classList.remove('dark');
    if (document.body) document.body.classList.remove('dark');
  };
  // Transform-only entrance (no opacity: Gradio morphs the DOM mid-animation
  // and an interrupted opacity animation would freeze content half-faded).
  var celebrate = function(el){
    if(!el || el.dataset.shown) return; el.dataset.shown='1';
    try{ el.animate([{transform:'translateY(14px)'},{transform:'none'}],
      {duration:480,easing:'cubic-bezier(.34,1.56,.64,1)'}); }catch(e){}
  };
  var arm = function(){
    forceLight();
    // Debounced via rAF and childList-only: observing class attributes fires on
    // every Svelte class toggle (constantly) and can livelock a slow renderer.
    // Dark-class re-adds are covered by the .dark CSS overrides as backstop.
    var scheduled = false;
    var tick = function(){
      scheduled = false;
      forceLight();
      ['#dr-summary','#dr-interp','#dr-itin','#dr-options'].forEach(function(s){
        var el = document.querySelector(s);
        if (el && el.textContent.trim()) celebrate(el);
      });
    };
    var obs = new MutationObserver(function(){
      if (!scheduled){ scheduled = true; requestAnimationFrame(tick); }
    });
    obs.observe(document.body, {childList:true, subtree:true});
  };
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', arm);
  else arm();
})();
</script>
"""

# ---------------------------------------------------------------- js (§4/§6)
# Outer-page enhancer: bounce results in when they (re)appear. The map's own
# route-draw / marker-pop animations run INSIDE the folium iframe (ui/map.py
# injects MAP_ANIMATION_JS there — an iframe can't be reached reliably from here).
# NOTE: the page enhancer (force-light + entrance animation) lives in DR_HEAD as
# a real <script>; Gradio 6's launch(js=...) silently failed to execute it.

# Map-press bounce the instant Plan is clicked (per-event js). NOTE: an event's
# js function receives the input values and its RETURN VALUE REPLACES them — it
# must pass the args through unchanged or every input reaches Python as null.
DR_CELEBRATE = """
(...args) => {
  const map = document.querySelector('#dr-map');
  if (map) map.animate(
    [{transform:'scale(1)'},{transform:'scale(.99)'},{transform:'scale(1)'}],
    {duration:260, easing:'cubic-bezier(.34,1.56,.64,1)'});
  return args;
}
"""

# ------------------------------------------------- in-iframe map animation
# Injected into the folium document by ui/map.py. Draws the discovery route
# (stroke-dashoffset) and pops the POI markers with a staggered spring.
MAP_ANIMATION_JS = """
<script>
window.addEventListener('load', function(){
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('path.route-disc').forEach(function(p){
    try{
      var len = p.getTotalLength();
      if(!reduce){
        p.style.strokeDasharray = len; p.style.strokeDashoffset = len;
        requestAnimationFrame(function(){
          p.style.transition = 'stroke-dashoffset 2s cubic-bezier(.4,0,.2,1)';
          p.style.strokeDashoffset = 0;
        });
      }
    }catch(e){}
  });
  document.querySelectorAll('path.dr-poi').forEach(function(m,i){
    if(reduce) return;
    m.style.opacity = 0; m.style.transformOrigin = 'center'; m.style.transformBox = 'fill-box';
    setTimeout(function(){
      m.style.opacity = 1;
      m.animate([{transform:'scale(.2)'},{transform:'scale(1.25)'},{transform:'scale(1)'}],
        {duration:500, easing:'cubic-bezier(.34,1.56,.64,1)'});
    }, 600 + i*150);
  });
});
</script>
"""

# ---------------------------------------------------------------- hero (§A)
# Inline-SVG low-poly isometric placeholder (final clay renders swap in later).
_HERO_SVG = """
<svg width="190" height="150" viewBox="0 0 200 160" fill="none" aria-hidden="true">
  <ellipse cx="100" cy="128" rx="86" ry="24" fill="#214AD0" opacity=".25"/>
  <polygon points="100,28 178,66 100,104 22,66" fill="#8FD6A8"/>
  <polygon points="22,66 100,104 100,128 22,90" fill="#2FA463"/>
  <polygon points="178,66 100,104 100,128 178,90" fill="#1F7D49"/>
  <path d="M40 72 Q70 50 100 68 T162 70" stroke="#FFFCF5" stroke-width="6"
        stroke-dasharray="1 11" stroke-linecap="round" fill="none"/>
  <polygon points="64,46 84,56 64,66 44,56" fill="#FFC247"/>
  <polygon points="44,56 64,66 64,82 44,72" fill="#E89E1C"/>
  <polygon points="84,56 64,66 64,82 84,72" fill="#C9871B"/>
  <polygon points="64,34 86,52 42,52" fill="#FF6A52"/>
  <circle cx="138" cy="52" r="13" fill="#2FA463"/>
  <circle cx="146" cy="44" r="10" fill="#48C07E"/>
  <rect x="135" y="60" width="6" height="14" rx="2" fill="#8A5A33"/>
  <path d="M118 84 c0,-10 16,-10 16,0 c0,8 -8,12 -8,18 c0,-6 -8,-10 -8,-18z" fill="#FF6A52"/>
  <circle cx="126" cy="84" r="4" fill="#FFFCF5"/>
</svg>
"""

DR_HERO = f"""
<div style="background:linear-gradient(120deg,#2F5DF4,#5C7DF8); border-radius:36px;
     padding:26px 30px; box-shadow:0 18px 44px -20px rgba(43,38,32,.34); color:#fff;
     display:flex; align-items:center; gap:18px; position:relative; overflow:hidden;">
  <div style="flex:1; min-width:0;">
    <span style="display:inline-flex; align-items:center; gap:7px; background:rgba(255,255,255,.16);
          border-radius:999px; padding:5px 13px; font-family:'Fredoka',sans-serif; font-weight:600;
          font-size:12.5px; letter-spacing:.04em;">
      <span style="width:8px;height:8px;border-radius:50%;background:#FFC247;"></span>
      Paris · walkable detours
    </span>
    <h1 style="font-family:'Fredoka',sans-serif; font-weight:700; font-size:clamp(27px,4vw,44px);
        letter-spacing:-.02em; margin:10px 0 6px; line-height:1.08; color:#fff;">
      Spend your extra time on <span style="color:#FFE0A0;">discovery.</span>
    </h1>
    <p style="margin:0 0 14px; max-width:46ch; color:#EAF0FF; font-size:15px;">
      Ordinary navigation minimizes time. DiscoverRoute detours past places that match
      your taste — within a travel-time budget — and tells you why each one is on the path.
    </p>
    <div style="display:flex; flex-wrap:wrap; gap:8px;">
      <span style="background:rgba(255,255,255,.13); border-radius:999px; padding:6px 13px;
            font-size:12.5px; font-family:'Fredoka',sans-serif; font-weight:500;">🗺️ OpenStreetMap data</span>
      <span style="background:rgba(255,255,255,.13); border-radius:999px; padding:6px 13px;
            font-size:12.5px; font-family:'Fredoka',sans-serif; font-weight:500;">🥐 A friendly local guide</span>
      <span style="background:rgba(255,255,255,.13); border-radius:999px; padding:6px 13px;
            font-size:12.5px; font-family:'Fredoka',sans-serif; font-weight:500;">✨ Tuned to your vibe</span>
    </div>
  </div>
  <div class="dr-hero-art" style="flex-shrink:0; animation:drFloat 5.5s ease-in-out infinite;">
    {_HERO_SVG}
  </div>
  <style>
    @keyframes drFloat {{ 0%,100% {{ transform:translateY(0) }} 50% {{ transform:translateY(-9px) }} }}
    @media (max-width:960px) {{ .dr-hero-art {{ display:none; }} }}
    @media (prefers-reduced-motion:reduce) {{ .dr-hero-art {{ animation:none; }} }}
  </style>
</div>
"""

# ------------------------------------------------------ no-detour state (§C)
NO_DETOUR_HTML = """
<div style="background:#FFFCF5; border:1.5px dashed #E7DAC0; border-radius:26px;
     padding:30px; text-align:center;">
  <svg width="84" height="74" viewBox="0 0 100 90" fill="none" style="margin-bottom:10px;" aria-hidden="true">
    <ellipse cx="50" cy="74" rx="34" ry="9" fill="#2B2620" opacity=".12"/>
    <polygon points="50,38 76,51 50,64 24,51" fill="#C9994F"/>
    <polygon points="24,51 50,64 50,76 24,63" fill="#A87A3A"/>
    <polygon points="76,51 50,64 50,76 76,63" fill="#8A6230"/>
    <ellipse cx="50" cy="44" rx="17" ry="7" fill="#E3BC7A"/>
    <rect x="56" y="14" width="6" height="26" rx="2" transform="rotate(28 59 27)" fill="#8A5A33"/>
    <polygon points="70,8 84,18 72,26 62,15" fill="#FF6A52"/>
    <polygon points="72,26 84,18 82,24 74,30" fill="#E14D37"/>
  </svg>
  <div style="font-family:'Fredoka',sans-serif; font-weight:600; font-size:21px; color:#2B2620;">
    No room to wander — yet</div>
  <p style="color:#6B6256; max-width:42ch; margin:6px auto 0; font-size:14px;">
    The budget is too tight to carve a worthwhile detour. Loosen it (or raise
    adventurousness) and I'll thread you past something good.</p>
</div>
"""

# Empty-map overlay message (rendered by ui/map.py inside the map frame).
EMPTY_STATE_LABEL = "Where shall we wander?"

# ------------------------------------------------------- loading state (§C)
# Shown in the map slot the instant Plan is clicked (via a .then() chain): a
# little local mid-stride + bouncing dots, per the kit's loading-state spec.
LOADING_HTML = """
<div style="height:520px; display:grid; place-items:center; background:
     radial-gradient(700px 320px at 50% 0%,#FBEFD6 0%,transparent 70%), #F6ECD9;">
  <div style="text-align:center;">
    <svg width="120" height="110" viewBox="0 0 120 110" fill="none" aria-hidden="true"
         style="animation:drStride .9s ease-in-out infinite alternate;">
      <ellipse cx="60" cy="98" rx="34" ry="7" fill="#2B2620" opacity=".12"/>
      <rect x="18" y="88" width="84" height="6" rx="3" fill="#E7DAC0"/>
      <circle cx="30" cy="91" r="2.5" fill="#FFFCF5"/>
      <circle cx="60" cy="91" r="2.5" fill="#FFFCF5"/>
      <circle cx="90" cy="91" r="2.5" fill="#FFFCF5"/>
      <circle cx="62" cy="28" r="13" fill="#FFC9A3"/>
      <path d="M50 24 a13 13 0 0 1 24 -3 l-5 2 a 9 9 0 0 0 -14 2z" fill="#8A5A33"/>
      <rect x="52" y="40" width="20" height="30" rx="9" fill="#2F5DF4"/>
      <rect x="47" y="44" width="9" height="22" rx="4.5" fill="#2F5DF4"
            transform="rotate(18 51 55)"/>
      <rect x="68" y="44" width="9" height="22" rx="4.5" fill="#214AD0"
            transform="rotate(-26 72 55)"/>
      <rect x="54" y="66" width="8" height="26" rx="4" fill="#2B2620"
            transform="rotate(14 58 79)"/>
      <rect x="62" y="66" width="8" height="26" rx="4" fill="#2B2620"
            transform="rotate(-22 66 79)"/>
      <ellipse cx="52" cy="94" rx="7" ry="3.5" fill="#E14D37"/>
      <ellipse cx="74" cy="90" rx="7" ry="3.5" fill="#E14D37"
               transform="rotate(-14 74 90)"/>
      <path d="M88 36 c0,-7 11,-7 11,0 c0,5.5 -5.5,8 -5.5,12.5 c0,-4.5 -5.5,-7 -5.5,-12.5z"
            fill="#FF6A52"/>
      <circle cx="93.5" cy="36" r="2.6" fill="#FFFCF5"/>
    </svg>
    <div style="font-family:'Fredoka',system-ui,sans-serif; font-weight:600;
         font-size:19px; color:#2B2620; margin-top:10px;">Scouting your wander…</div>
    <div style="margin-top:12px; display:flex; gap:8px; justify-content:center;">
      <span style="width:11px;height:11px;border-radius:50%;background:#FF6A52;
            animation:drBounce 1s ease-in-out infinite;"></span>
      <span style="width:11px;height:11px;border-radius:50%;background:#FFC247;
            animation:drBounce 1s ease-in-out .15s infinite;"></span>
      <span style="width:11px;height:11px;border-radius:50%;background:#2FA463;
            animation:drBounce 1s ease-in-out .3s infinite;"></span>
    </div>
    <div style="font-family:'DM Sans',system-ui,sans-serif; font-size:13px;
         color:#6B6256; margin-top:12px;">reading your vibe · scoring 30,000 places · threading the detour</div>
  </div>
  <style>
    @keyframes drBounce { 0%,100% { transform:translateY(0) } 50% { transform:translateY(-9px) } }
    @keyframes drStride { 0% { transform:translateX(-7px) } 100% { transform:translateX(7px) } }
    @media (prefers-reduced-motion:reduce){ *{ animation:none !important; } }
  </style>
</div>
"""
