"""Clay-pin map markers — the designed 14-piece marker family.

SVGs live in ``ui/icons/`` (source of truth: the design handoff's
``icons/markers-spec.md``). Each marker is inlined into a Leaflet ``DivIcon``
(no extra HTTP requests inside the map iframe), sized per spec with the pin tip
anchored on the coordinate, plus the spec's cast shadow, springy hover, and
staggered pop-in — all gated behind ``prefers-reduced-motion``.
"""
from __future__ import annotations

import functools
from pathlib import Path

import folium

_ICON_DIR = Path(__file__).resolve().parent / "icons"

# Our 17 OSM categories -> the 14 designed marker kinds (color-by-meaning:
# cobalt water/wayfinding · grass green space · coral culture · sun cozy stops).
CATEGORY_TO_KIND = {
    "park_garden": "park",
    "water_feature": "fountain",
    "viewpoint": "viewpoint",
    "monument_historic": "museum",
    "museum_gallery": "museum",
    "artwork": "star",            # public art = a highlight find
    "place_of_worship": "museum", # columns glyph reads classical/temple
    "library": "library",
    "bookshop": "bookshop",
    "theatre_cinema": "museum",
    "cafe": "cafe",
    "bakery_food_shop": "bakery",
    "restaurant": "cafe",
    "bar_pub": "cafe",
    "market": "market",
    "specialty_shop": "market",
    "attraction": "star",
}

_W = 40                      # marker width px (spec: 28 / 40 / 56)
_H = round(_W * 84 / 64)     # 52 — height keeps the 64x84 viewBox ratio


@functools.lru_cache(maxsize=32)
def _svg(kind: str) -> str:
    path = _ICON_DIR / f"marker-{kind}.svg"
    try:
        return path.read_text()
    except OSError:
        return ""


def marker_icon(kind: str, index: int = 0, width: int = _W) -> folium.DivIcon | None:
    """A DivIcon for one pin; ``index`` staggers the pop-in (~150 ms per spec)."""
    svg = _svg(kind)
    if not svg:
        return None
    h = round(width * 84 / 64)
    html = (f'<div class="dr-pin" style="animation-delay:{600 + index * 150}ms;'
            f'width:{width}px;height:{h}px;">{svg}</div>')
    return folium.DivIcon(html=html, icon_size=(width, h),
                          icon_anchor=(width // 2, h), class_name="dr-pin-wrap")


def poi_icon(category: str, index: int = 0) -> folium.DivIcon | None:
    return marker_icon(CATEGORY_TO_KIND.get(category, "star"), index)


def endpoint_icon(which: str) -> folium.DivIcon | None:
    """'start' (cobalt arrow) or 'dest' (coral flag), slightly larger."""
    return marker_icon(which, index=-2, width=46)


# Injected once per map (ui/map.py): shadow + hover spring + pop-in, per spec.
MARKER_CSS = """
<style>
.dr-pin-wrap{ background:transparent; border:none; }
.dr-pin{ filter: drop-shadow(0 6px 5px rgba(43,38,32,.28));
  transition: transform .25s cubic-bezier(.34,1.56,.64,1);
  transform-origin: 50% 100%;
  animation: drPinPop .55s cubic-bezier(.34,1.56,.64,1) backwards; }
.dr-pin svg{ width:100%; height:100%; display:block; }
.dr-pin:hover{ transform: translateY(-8px) scale(1.05); }
@keyframes drPinPop{ 0%{ transform:scale(.3); } 60%{ transform:scale(1.12); }
  100%{ transform:scale(1); } }
@media (prefers-reduced-motion: reduce){ .dr-pin{ animation:none; } }
</style>
"""
