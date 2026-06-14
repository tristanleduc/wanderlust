"""Per-city geographic context the narrator is allowed to name.

The zero-hallucination gate (:mod:`grounding`) rejects any capitalized place
name that isn't a selected POI or an endpoint. That guarantee is sound for
*venues* (you must not be told to visit an invented café), but it also rejected
every neighbourhood, river and quarter a real city guide naturally mentions —
so any vivid LLM narration crossing recognizable geography got thrown away and
the flat template shipped instead.

This module supplies a curated, real allowlist of district / quarter / river /
landmark names per pre-baked city. These are *context* the narrator may
reference ("as you cross the Marais", "along the Seine") — not stops. They are
real OSM-scale places, so naming them is grounded, not invented. The generic
era/architecture adjectives ("Roman", "Gothic") live in :data:`grounding._COMMON`
instead, since they are city-independent.

On-demand (arbitrary) cities have no gazetteer entry: they get only the POIs +
endpoints, exactly as before, so an un-curated city still fails closed to the
template rather than risking an ungrounded neighbourhood name.
"""
from __future__ import annotations

# Keyed by ``Area.key`` (see routing/area.py): "paris", "london", "barcelona",
# "newyork". On-demand areas use a bbox-hash key absent from this map -> no extra
# context (safe default). Phrases may be multi-word; the gate substring-matches a
# mention's distinctive core, so "the Latin Quarter" grounds against "Latin
# Quarter" while "Eiffel Tower" (Eiffel not listed) still correctly fails.
CITY_GAZETTEER: dict[str, list[str]] = {
    "paris": [
        # river / islands / banks
        "Seine", "Rive Gauche", "Rive Droite", "Left Bank", "Right Bank",
        "Île de la Cité", "Île Saint-Louis", "Canal Saint-Martin",
        # quarters / neighbourhoods
        "Le Marais", "Marais", "Quartier Latin", "Latin Quarter",
        "Saint-Germain", "Saint-Germain-des-Prés", "Montmartre", "Montparnasse",
        "Belleville", "Bastille", "Pigalle", "Oberkampf", "Le Sentier",
        # well-known landmarks/areas a guide name-checks in passing
        "Sorbonne", "Panthéon", "Champs-Élysées", "Tuileries", "Louvre",
        "Notre-Dame", "Île-de-France",
    ],
    "london": [
        "Thames", "South Bank", "Southbank", "North Bank", "the City",
        "Bloomsbury", "Soho", "Covent Garden", "Mayfair", "Westminster",
        "Southwark", "Lambeth", "Vauxhall", "Holborn", "Clerkenwell",
        "Fitzrovia", "Marylebone", "the West End", "the East End", "Shoreditch",
        "Bankside", "Embankment", "Strand", "Piccadilly",
    ],
    "barcelona": [
        "Mediterranean", "Barri Gòtic", "Gothic Quarter", "El Raval", "El Born",
        "La Ribera", "Eixample", "La Rambla", "Las Ramblas", "Barceloneta",
        "Gràcia", "Montjuïc", "Poble Sec", "Ciutat Vella", "Port Vell",
        "Passeig de Gràcia",
    ],
    "newyork": [
        "Manhattan", "Midtown", "Downtown", "Uptown", "SoHo", "NoHo", "Tribeca",
        "Greenwich Village", "the Village", "East Village", "West Village",
        "Chelsea", "the Lower East Side", "the Upper West Side",
        "the Upper East Side", "Times Square", "Central Park", "Hudson",
        "East River", "Broadway", "Fifth Avenue", "the Flatiron",
    ],
}


def geo_terms(area_key: str, label: str = "") -> list[str]:
    """Allowed geographic-context names for an area (empty for un-curated ones)."""
    terms = list(CITY_GAZETTEER.get((area_key or "").lower(), ()))
    if label and label.strip():
        terms.append(label.strip())  # the city's own name ("London", "Paris")
    return terms
