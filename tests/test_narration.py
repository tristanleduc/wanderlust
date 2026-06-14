"""Brick 6 tests: grounded narration + the hard 0% hallucination gate (P0-6)."""
from __future__ import annotations

import pytest

from discoverroute import config
from discoverroute.narrate import grounding
from discoverroute.narrate.narrate import template_narration


class FakePOI:
    def __init__(self, name, category):
        self.name, self.category = name, category


POIS = [
    FakePOI("Jardin des Plantes", "park_garden"),
    FakePOI("Fontaine Médicis", "water_feature"),
    FakePOI(None, "cafe"),  # unnamed -> referred to by type, not a place name
]


def test_extract_multiword_place_names():
    mentions = grounding.extract_mentions(
        "Start at Place de la République, then visit Jardin des Plantes."
    )
    joined = " | ".join(mentions)
    assert "Place de la République" in joined
    assert "Jardin des Plantes" in joined


def test_gate_passes_grounded_text():
    text = ("From Bastille, pass by Jardin des Plantes for some green, then "
            "Fontaine Médicis. Finally on to the Panthéon area.")
    ok, offenders = grounding.verify_grounded(
        text, POIS, start_label="Bastille", end_label="Panthéon area"
    )
    assert ok, offenders


def test_gate_catches_hallucination():
    text = "Pass by Jardin des Plantes, then the Eiffel Tower, a lovely detour."
    ok, offenders = grounding.verify_grounded(text, POIS, start_label="Bastille")
    assert not ok
    assert any("Eiffel" in o for o in offenders)


def test_gate_catches_appended_qualifier():
    """A real name extended with an invented qualifier must NOT pass (the
    'Café de la Paix' -> 'Café de la Paix sur Seine' hallucination vector)."""
    pois = [FakePOI("Fontaine Médicis", "water_feature")]
    text = "Pass by Fontaine Médicis sur Montmartre, a lovely spot."
    ok, offenders = grounding.verify_grounded(text, pois, start_label="Bastille")
    assert not ok
    assert any("Montmartre" in o for o in offenders)


def test_gate_allows_shortened_reference():
    """Referring to a place by a shortened form of its real name is fine."""
    pois = [FakePOI("Jardin des Plantes de Paris", "park_garden")]
    text = "Stroll through Jardin des Plantes, then onward."
    ok, offenders = grounding.verify_grounded(text, pois, start_label="Bastille")
    assert ok, offenders


def test_gate_allows_unnamed_by_type():
    text = "Stop at a cafe near Jardin des Plantes for a coffee-stop pause."
    ok, offenders = grounding.verify_grounded(text, POIS, start_label="Bastille")
    assert ok, offenders


def test_geo_gazetteer_allows_real_districts():
    """A guide may name the city's real districts/river when given the gazetteer,
    so vivid prose passes the gate instead of being thrown out for the template."""
    from discoverroute.narrate import gazetteer
    geo = gazetteer.geo_terms("paris", "Paris")
    text = ("From the Marais, drift down toward the Seine and into the Latin "
            "Quarter, passing Jardin des Plantes for some green and Fontaine "
            "Médicis. A very Parisian wander with Roman echoes near the Panthéon.")
    ok, offenders = grounding.verify_grounded(
        text, POIS, start_label="Bastille", end_label="Panthéon",
        extra_allowed=geo,
    )
    assert ok, offenders


def test_geo_gazetteer_allows_landmarks_but_not_eiffel():
    """Expanded gazetteer lets a guide name real landmarks (Arc de Triomphe,
    Sacré-Cœur) for scene-setting, while the Eiffel Tower — the planted
    hallucination — must STILL be caught."""
    from discoverroute.narrate import gazetteer
    geo = gazetteer.geo_terms("paris", "Paris")
    ok, off = grounding.verify_grounded(
        "From the Arc de Triomphe, wander toward Sacré-Cœur, passing "
        "Jardin des Plantes.", POIS, start_label="Bastille", extra_allowed=geo)
    assert ok, off
    # the famous-landmark allowlist must not punch a hole for the planted one
    ok2, off2 = grounding.verify_grounded(
        "A lovely detour past the Eiffel Tower, then Jardin des Plantes.",
        POIS, start_label="Bastille", extra_allowed=geo)
    assert not ok2 and any("Eiffel" in o for o in off2)


def test_geo_gazetteer_still_blocks_invented_venue():
    """Loosening for districts must NOT let an invented venue through."""
    from discoverroute.narrate import gazetteer
    geo = gazetteer.geo_terms("paris", "Paris")
    text = ("Cross the Marais, then stop at Café des Mensonges, a charming "
            "invented spot, before Jardin des Plantes.")
    ok, offenders = grounding.verify_grounded(
        text, POIS, start_label="Bastille", extra_allowed=geo,
    )
    assert not ok
    assert any("Mensonges" in o for o in offenders)


def test_uncurated_city_has_no_extra_context():
    """An on-demand area (bbox-hash key) gets no gazetteer => fails closed."""
    from discoverroute.narrate import gazetteer
    assert gazetteer.geo_terms("48.1,2.2,48.2,2.3", "this area") == ["this area"]


class _Route:
    def __init__(self, time_min):
        self.time_min = time_min


def test_template_is_grounded_by_construction():
    plain, discovery = _Route(40), _Route(58)
    text = template_narration(
        plain, discovery, POIS, vibe="quiet green wander", mode="walk",
        start_label="Bastille", end_label="Panthéon",
        posture={"park_garden": "pass", "water_feature": "pass", "cafe": "stop"},
    )
    ok, offenders = grounding.verify_grounded(
        text, POIS, start_label="Bastille", end_label="Panthéon"
    )
    assert ok, f"template leaked place names: {offenders}"
    assert "Jardin des Plantes" in text and "Fontaine Médicis" in text


data_ready = pytest.mark.skipif(
    not (config.GRAPH_WALK_PATH.exists() and config.POIS_PATH.exists()),
    reason="Graph or POI table not built",
)


@data_ready
def test_end_to_end_narration_grounded():
    """The shipped itinerary for a real route must pass the gate (the release gate)."""
    from discoverroute.pipeline import plan_route
    r = plan_route("Place de la République, Paris", "Jardin du Luxembourg, Paris",
                   budget=0.7, vibe="quiet green wander")
    assert r.discovery is not None and r.pois
    ok, offenders = grounding.verify_grounded(
        r.itinerary_md, r.pois,
        start_label="Place de la République, Paris",
        end_label="Jardin du Luxembourg, Paris",
    )
    assert ok, f"hallucinated place names in shipped narration: {offenders}"
