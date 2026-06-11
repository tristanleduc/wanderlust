"""DiscoverRoute — Gradio app (Hugging Face Space entrypoint).

Run locally:  python app.py
UI design ported from the Claude-design handoff (low-poly clay-sticker look):
state machine empty → loading → (routed | no-detour), framed map window with
in-iframe route-draw animation, springy controls, toasts, per-device profile.
"""
from __future__ import annotations

import gradio as gr

from discoverroute import config
from discoverroute.pipeline import plan_route
from discoverroute.ui import design
from discoverroute.ui import map as mapui

N_ALTERNATIVES = 3


def _saved_md(profile: dict) -> str:
    saved = (profile or {}).get("saved_categories") or []
    if not saved:
        return "_No saved places yet. Plan a route, then ⭐ save its places._"
    from collections import Counter
    counts = Counter(saved)
    items = ", ".join(f"{c.replace('_',' ')} ×{n}" for c, n in counts.most_common())
    return f"**Saved taste:** {items}"


def _alt_label(i: int, alt, plain) -> str:
    extra = round(alt.discovery.time_min + alt.discovery.dwell_s / 60.0
                  - plain.time_min)
    from collections import Counter
    top = Counter(p.category for p in alt.pois).most_common(2)
    flavor = ", ".join(c.replace("_", " ") for c, _ in top)
    return (f"Option {i+1} · {alt.discovery.distance_m/1000:.1f} km · +{extra} min · "
            f"{len(alt.pois)} stops ({flavor})")


def on_plan(start, dest, mode, budget, vibe, adventurousness,
            prefer_green, prefer_quiet, profile, progress=gr.Progress()):
    progress(0.1, desc="Reading your vibe…")
    result = plan_route(
        start_query=start, dest_query=dest, mode=mode, budget=budget, vibe=vibe,
        adventurousness=adventurousness, prefer_green=prefer_green,
        prefer_quiet=prefer_quiet, profile=profile or {}, n_alternatives=N_ALTERNATIVES,
    )
    progress(0.9, desc="Drawing your wander…")

    if result.error:
        gr.Warning(result.error)
        return (mapui.empty_map("Hmm — " + result.error.split(".")[0] + "."),
                gr.update(visible=False), gr.update(visible=False),
                gr.update(choices=[], visible=False),
                "", "", "", {"items": []}, [])

    alts = result.alternatives or []
    if not alts:  # honest no-detour (or budget 0 → plain route): design's stump state
        html = mapui.render_routes(plain=result.plain, start=result.start, end=result.end)
        return (html,
                gr.update(visible=True), gr.update(visible=True),
                gr.update(choices=[], visible=False),
                result.summary_md, result.interpretation_md, result.itinerary_md,
                {"items": []}, [])

    items, choices = [], []
    for i, alt in enumerate(alts):
        html = mapui.render_routes(plain=result.plain, discovery=alt.discovery,
                                   pois=alt.pois, start=result.start, end=result.end)
        choices.append(_alt_label(i, alt, result.plain))
        items.append({"map": html, "summary": alt.summary_md,
                      "itinerary": alt.itinerary_md})

    first = items[0]
    return (first["map"],
            gr.update(visible=True), gr.update(visible=False),
            gr.update(choices=choices, value=choices[0], visible=len(choices) > 1),
            first["summary"], result.interpretation_md, first["itinerary"],
            {"choices": choices, "items": items},
            [p.category for p in alts[0].pois])


def on_select_alt(choice, state):
    items = (state or {}).get("items") or []
    choices = (state or {}).get("choices") or []
    if not items or choice not in choices:
        return gr.update(), gr.update(), gr.update()
    it = items[choices.index(choice)]
    return it["map"], it["summary"], it["itinerary"]


def on_save_places(profile, last_cats):
    profile = dict(profile or {"standing_text": "", "saved_categories": []})
    if not last_cats:
        gr.Warning("Plan a route first — then I can save its places to your taste.")
        return profile, _saved_md(profile)
    profile["saved_categories"] = (profile.get("saved_categories") or []) + list(last_cats)
    gr.Info("Saved this route's places to your taste ✨")
    return profile, _saved_md(profile)


def on_save_prefs(standing_text, profile):
    profile = dict(profile or {"standing_text": "", "saved_categories": []})
    profile["standing_text"] = standing_text or ""
    gr.Info("Saved your standing preferences ✨")
    return profile, _saved_md(profile)


def on_clear_profile():
    gr.Info("Profile cleared 🧹")
    empty = {"standing_text": "", "saved_categories": []}
    return empty, "", _saved_md(empty)


def on_suggest(evt: gr.KeyUpData):
    """Autocomplete a Start/Destination field from the local POI-name index."""
    from discoverroute.routing.geocode import suggest
    typed = evt.input_value or ""
    matches = list(suggest(typed))
    # keep what the user typed selectable on top; never clobber their text
    choices = ([typed] if typed and typed not in matches else []) + matches
    return gr.update(choices=choices or [typed])


def show_loading():
    """Instant feedback the moment Plan is clicked (the .then chain computes)."""
    return (design.LOADING_HTML, gr.update(visible=False),
            gr.update(visible=False), gr.update(visible=False))


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="DiscoverRoute · Paris") as demo:
        profile = gr.BrowserState(
            {"standing_text": "", "saved_categories": []},
            storage_key="discoverroute_profile",
        )
        alts_state = gr.State({"items": []})
        last_cats = gr.State([])

        gr.HTML(design.DR_HERO, elem_id="dr-hero")

        with gr.Row(equal_height=False):
            # ---- LEFT: controls --------------------------------------------
            with gr.Column(scale=4, min_width=340):
                with gr.Group():
                    start = gr.Dropdown(
                        label="Start", elem_id="dr-start", elem_classes="dr-field",
                        info="Type a Paris place — suggestions appear as you type",
                        value="Place de la République, Paris",
                        choices=["Place de la République, Paris"],
                        allow_custom_value=True, filterable=True)
                    dest = gr.Dropdown(
                        label="Destination", elem_id="dr-dest", elem_classes="dr-field",
                        value="Jardin du Luxembourg, Paris",
                        choices=["Jardin du Luxembourg, Paris"],
                        allow_custom_value=True, filterable=True)
                    vibe = gr.Textbox(label="Vibe (free text)", elem_id="dr-vibe",
                                      elem_classes="dr-field",
                                      info="e.g. 'quiet green wander' or 'lively café crawl'")
                mode = gr.Radio(choices=["walk", "bike"], value=config.DEFAULT_MODE,
                                label="Mode", elem_id="dr-mode", elem_classes="dr-seg")
                budget = gr.Slider(0.0, config.MAX_BUDGET, value=config.DEFAULT_BUDGET,
                                   step=0.1, label="Detour budget",
                                   elem_id="dr-budget", elem_classes="dr-slider",
                                   info="Extra time vs. the direct trip — 0 = straight there, 1 = up to 2× longer")
                adventurousness = gr.Slider(
                    0.0, 1.0, value=config.DEFAULT_ADVENTUROUSNESS, step=0.05,
                    label="Adventurousness", elem_id="dr-adv", elem_classes="dr-slider",
                    info="Low = well-known places · high = hidden gems")
                with gr.Accordion("Manual taste (used only when Vibe and saved profile are both empty)",
                                  open=False, elem_id="dr-manual", elem_classes="dr-collapse"):
                    prefer_green = gr.Slider(0.0, 1.0, value=0.5, step=0.05,
                                             label="Prefer green", elem_id="dr-green",
                                             elem_classes=["dr-slider", "green"])
                    prefer_quiet = gr.Slider(0.0, 1.0, value=0.5, step=0.05,
                                             label="Prefer quiet", elem_id="dr-quiet",
                                             elem_classes=["dr-slider", "green"])
                go = gr.Button("Plan route", variant="primary", size="lg",
                               elem_id="dr-plan")
                with gr.Accordion("⭐ My taste profile (saved on this device)",
                                  open=False, elem_id="dr-profile", elem_classes="dr-collapse"):
                    standing = gr.Textbox(
                        label="Standing preferences", lines=3, elem_id="dr-profile-text",
                        info="e.g. 'I always love bookshops, gardens, and old churches'")
                    with gr.Row():
                        save_prefs_btn = gr.Button("Save", size="sm", elem_id="dr-save")
                        clear_btn = gr.Button("Clear", size="sm", variant="secondary",
                                              elem_id="dr-clear")
                    saved_display = gr.Markdown(_saved_md({}), elem_id="dr-saved",
                                                elem_classes="dr-note")
                    save_places_btn = gr.Button("⭐ Save this route's places",
                                                elem_id="dr-save-places",
                                                elem_classes="dr-star")

            # ---- RIGHT: results --------------------------------------------
            with gr.Column(scale=7, min_width=440, elem_id="dr-results"):
                alt_radio = gr.Radio(choices=[], label="Route options", visible=False,
                                     elem_id="dr-options", elem_classes="dr-cards")
                map_out = gr.HTML(mapui.empty_map(), elem_id="dr-map")
                with gr.Group(visible=False) as results_grp:
                    summary_out = gr.Markdown(elem_id="dr-summary")
                    interpretation_out = gr.Markdown(elem_id="dr-interp",
                                                     elem_classes="dr-tags")
                    itinerary_out = gr.Markdown(elem_id="dr-itin")
                nodetour_html = gr.HTML(design.NO_DETOUR_HTML, visible=False,
                                        elem_id="dr-nodetour")

        # Cosmetic map-press bounce. Gradio feeds an event's `js` return value
        # back as the inputs to its `fn`; a side-effect-only js (returns
        # undefined) attached to the data event corrupts on_plan's inputs and
        # white-screens the frontend. So keep the animation on its own fn-less
        # listener, where its return value is harmless.
        go.click(None, js=design.DR_CELEBRATE)
        # Loading state first (instant), then the actual planning overwrites it.
        go.click(
            show_loading,
            outputs=[map_out, results_grp, nodetour_html, alt_radio],
            show_progress="hidden",
        ).then(
            on_plan,
            inputs=[start, dest, mode, budget, vibe, adventurousness,
                    prefer_green, prefer_quiet, profile],
            outputs=[map_out, results_grp, nodetour_html, alt_radio,
                     summary_out, interpretation_out, itinerary_out,
                     alts_state, last_cats],
            show_progress="minimal",
        )
        # Autocomplete Start/Destination from the local POI-name index.
        for _field in (start, dest):
            _field.key_up(on_suggest, outputs=[_field], show_progress="hidden")
        alt_radio.change(on_select_alt, inputs=[alt_radio, alts_state],
                         outputs=[map_out, summary_out, itinerary_out])
        save_places_btn.click(on_save_places, inputs=[profile, last_cats],
                              outputs=[profile, saved_display])
        save_prefs_btn.click(on_save_prefs, inputs=[standing, profile],
                             outputs=[profile, saved_display])
        clear_btn.click(on_clear_profile, outputs=[profile, standing, saved_display])

        demo.load(lambda p: (p.get("standing_text", ""), _saved_md(p)),
                  inputs=[profile], outputs=[standing, saved_display])
    return demo


def warmup():
    """Preload graph + CSR + POIs + the vibe embedder at boot so the first
    request is fast (~1s) instead of paying the torch/model load lazily."""
    try:
        from discoverroute.routing import graph as g
        from discoverroute.routing import pois as poimod
        g.load_graph()
        g.graph_csr()
        poimod.load_pois()
        print("[warmup] routing graph + POIs ready", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[warmup] graph FAILED: {exc}", flush=True)
    try:
        from discoverroute.interpret import embed
        embed.vibe_to_affinity("quiet green wander")  # loads model + gloss cache
        print("[warmup] vibe embedder ready", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[warmup] embedder skipped: {exc}", flush=True)


if __name__ == "__main__":
    warmup()
    build_ui().queue(default_concurrency_limit=4).launch(
        theme=design.build_theme(),
        css=design.DR_CSS,
        head=design.DR_HEAD,
    )
