"""Folium map rendering: plain route, discovery route, and POI markers.

Returns an HTML string suitable for a Gradio ``gr.HTML`` component. Styled per
the design handoff: cobalt plain route, grass discovery route (with an
in-iframe draw-on animation), coral POI markers that pop in, and a legend.
"""
from __future__ import annotations

import folium
from branca.element import Element

from discoverroute import config
from discoverroute.routing.graph import Route
from discoverroute.ui import design

PLAIN_COLOR = "#2F5DF4"      # cobalt — the plain/fastest route
DISCOVERY_COLOR = "#2FA463"  # grass — the discovery route
POI_COLOR = "#FF6A52"        # coral — POI markers
TILES = "cartodbpositron"

_LEGEND_HTML = """
<div style="position:absolute; bottom:18px; left:12px; z-index:9999;
     background:#FFFCF5; border:1px solid #E7DAC0; border-radius:14px;
     padding:9px 13px; font-family:'DM Sans',system-ui,sans-serif; font-size:12px;
     color:#2B2620; box-shadow:0 8px 22px -12px rgba(43,38,32,.45); line-height:1.9;">
  <span style="display:inline-block;width:18px;height:4px;border-radius:2px;
        background:#2FA463;vertical-align:middle;margin-right:7px;"></span>Discovery route<br>
  <span style="display:inline-block;width:18px;height:4px;border-radius:2px;
        background:#2F5DF4;vertical-align:middle;margin-right:7px;"></span>Fastest route<br>
  <span style="display:inline-block;width:10px;height:10px;border-radius:50%;
        background:#FF6A52;vertical-align:middle;margin-right:7px;margin-left:4px;"></span>Worth a detour
</div>
"""


def _fit_bounds(fmap: folium.Map, coords: list[tuple[float, float]]) -> None:
    if not coords:
        return
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    fmap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(28, 28))


def render_routes(
    plain: Route | None = None,
    discovery: Route | None = None,
    pois=None,
    start: tuple[float, float] | None = None,
    end: tuple[float, float] | None = None,
) -> str:
    """Render routes + markers and return the map as standalone HTML."""
    center = start or config.PARIS_CENTER
    fmap = folium.Map(location=list(center), zoom_start=14, tiles=TILES)

    all_coords: list[tuple[float, float]] = []

    if plain is not None and plain.coords:
        folium.PolyLine(
            plain.coords, color=PLAIN_COLOR, weight=4, opacity=0.55,
            dash_array="7 9",
            tooltip=f"Fastest route · {plain.distance_m/1000:.2f} km · {plain.time_min:.0f} min",
        ).add_to(fmap)
        all_coords.extend(plain.coords)

    if discovery is not None and discovery.coords:
        # under-glow + main stroke; class_name lets the iframe script draw it on
        folium.PolyLine(
            discovery.coords, color=DISCOVERY_COLOR, weight=10, opacity=0.18,
        ).add_to(fmap)
        folium.PolyLine(
            discovery.coords, color=DISCOVERY_COLOR, weight=5, opacity=0.95,
            class_name="route-disc",
            tooltip=f"Discovery route · {discovery.distance_m/1000:.2f} km · {discovery.time_min:.0f} min",
        ).add_to(fmap)
        all_coords.extend(discovery.coords)

    if pois:
        for poi in pois:
            name = getattr(poi, "name", None) or getattr(poi, "category", "POI")
            folium.CircleMarker(
                location=[poi.lat, poi.lon],
                radius=7,
                color="#FFFCF5",
                weight=2,
                fill=True,
                fill_color=POI_COLOR,
                fill_opacity=1.0,
                class_name="dr-poi",
                tooltip=str(name),
            ).add_to(fmap)

    if start is not None:
        folium.Marker(list(start), tooltip="Start",
                      icon=folium.Icon(color="blue", icon="play")).add_to(fmap)
    if end is not None:
        folium.Marker(list(end), tooltip="Destination",
                      icon=folium.Icon(color="red", icon="flag")).add_to(fmap)

    _fit_bounds(fmap, all_coords or [c for c in (start, end) if c])

    root = fmap.get_root()
    root.html.add_child(Element(_LEGEND_HTML))
    root.html.add_child(Element(design.MAP_ANIMATION_JS))
    return fmap._repr_html_()


def empty_map(message: str = design.EMPTY_STATE_LABEL) -> str:
    """A blank Paris map with a friendly sticker overlay (empty/error state)."""
    fmap = folium.Map(location=list(config.PARIS_CENTER), zoom_start=12, tiles=TILES)
    overlay = f"""
    <div style="position:absolute; inset:0; z-index:9999; display:grid; place-items:center;
         pointer-events:none; background:rgba(246,236,217,.45);">
      <div style="background:#FFFCF5; border:1px solid #E7DAC0; border-radius:22px;
           padding:20px 26px; text-align:center; max-width:300px;
           box-shadow:0 18px 44px -18px rgba(43,38,32,.4);">
        <svg width="72" height="58" viewBox="0 0 90 70" fill="none" aria-hidden="true">
          <polygon points="12,14 36,6 36,56 12,64" fill="#8FD6A8"/>
          <polygon points="36,6 60,14 60,64 36,56" fill="#BDE6CD"/>
          <polygon points="60,14 82,6 82,56 60,64" fill="#8FD6A8"/>
          <path d="M20 30 Q36 20 50 32 T76 30" stroke="#2F5DF4" stroke-width="3.5"
                stroke-dasharray="1 7" stroke-linecap="round" fill="none"/>
          <circle cx="58" cy="38" r="13" fill="none" stroke="#FF6A52" stroke-width="5"/>
          <path d="M67 48 L78 60" stroke="#FF6A52" stroke-width="6" stroke-linecap="round"/>
        </svg>
        <div style="font-family:'Fredoka',system-ui,sans-serif; font-weight:600; font-size:16.5px;
             color:#2B2620; margin-top:6px;">{message}</div>
      </div>
    </div>
    """
    fmap.get_root().html.add_child(Element(overlay))
    return fmap._repr_html_()
