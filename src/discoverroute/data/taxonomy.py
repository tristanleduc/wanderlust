"""The finite OSM category vocabulary + interpretable feature priors.

This is the single source of truth for:
  1. mapping raw OSM tags -> a curated category a person would detour for, and
  2. the per-category greenness / quietness priors (proxies derived from OSM), and
  3. the confidence (tag-richness) computation.

The category vocabulary defined here is the same finite set that Brick 4's
embedding affinity will target (resolving spec open-question §12 "OSM category
vocabulary"). It is deliberately curated — generic noise (supermarkets, banks,
pharmacies, ATMs) is excluded because you do not detour for them.

Greenness and quietness are *category priors*: grounded in what the category
inherently is, not in per-place measurement. They are honest proxies (spec §9.3)
and a documented v1 simplification; richer sources (Sentinel greenness,
road-proximity quietness) are P2.
"""
from __future__ import annotations

# Category -> (greenness 0..1, quietness 0..1). Order matters: classification
# walks the matcher list top-to-bottom and takes the first match, so put more
# specific categories before broader ones.
CATEGORIES: dict[str, dict[str, float]] = {
    "park_garden":      {"greenness": 1.00, "quietness": 0.80},
    "water_feature":    {"greenness": 0.45, "quietness": 0.60},
    "viewpoint":        {"greenness": 0.40, "quietness": 0.55},
    "monument_historic":{"greenness": 0.20, "quietness": 0.50},
    "museum_gallery":   {"greenness": 0.10, "quietness": 0.80},
    "artwork":          {"greenness": 0.20, "quietness": 0.60},
    "place_of_worship": {"greenness": 0.25, "quietness": 0.90},
    "library":          {"greenness": 0.10, "quietness": 0.95},
    "bookshop":         {"greenness": 0.10, "quietness": 0.80},
    "theatre_cinema":   {"greenness": 0.05, "quietness": 0.40},
    "cafe":             {"greenness": 0.10, "quietness": 0.40},
    "bakery_food_shop": {"greenness": 0.10, "quietness": 0.50},
    "restaurant":       {"greenness": 0.10, "quietness": 0.30},
    "bar_pub":          {"greenness": 0.10, "quietness": 0.15},
    "market":           {"greenness": 0.20, "quietness": 0.25},
    "specialty_shop":   {"greenness": 0.05, "quietness": 0.55},
    "attraction":       {"greenness": 0.30, "quietness": 0.40},
}

# Human-readable gloss per category — fed to the text encoder in Brick 4 so a
# free-text vibe can be matched to categories by meaning.
CATEGORY_GLOSS: dict[str, str] = {
    "park_garden": "a green park or garden, lawns and trees, calm open nature",
    "water_feature": "a fountain, pond, canal or riverside water feature",
    "viewpoint": "a scenic viewpoint or panorama overlooking the city",
    "monument_historic": "a historic monument, statue, memorial or heritage site",
    "museum_gallery": "an art museum or gallery, culture and exhibitions",
    "artwork": "a piece of public art, street art or sculpture",
    "place_of_worship": "a church, temple or quiet place of worship",
    "library": "a library, quiet reading and books",
    "bookshop": "an independent bookshop, browsing books",
    "theatre_cinema": "a theatre or cinema, performance and film",
    "cafe": "a cosy cafe or specialty coffee shop, espresso and a pause",
    "bakery_food_shop": "a bakery, patisserie, coffee roaster, chocolate or fine-food shop",
    "restaurant": "a restaurant for a proper meal",
    "bar_pub": "a lively bar, pub or wine bar, drinks and atmosphere",
    "market": "a bustling open-air or covered market, food and stalls",
    "specialty_shop": "a characterful specialty shop — antiques, art, design",
    "attraction": "a famous landmark or major sight worth seeing",
}


# Default posture per category: "stop" (you'd dwell) vs "pass" (you'd roll past).
# The mood can shift this globally (Brick 4). Dual stop/pass budgeting is P1-2.
POSTURE_DEFAULT: dict[str, str] = {
    "park_garden": "pass",
    "water_feature": "pass",
    "viewpoint": "pass",
    "monument_historic": "pass",
    "museum_gallery": "stop",
    "artwork": "pass",
    "place_of_worship": "pass",
    "library": "stop",
    "bookshop": "stop",
    "theatre_cinema": "stop",
    "cafe": "stop",
    "bakery_food_shop": "stop",
    "restaurant": "stop",
    "bar_pub": "stop",
    "market": "stop",
    "specialty_shop": "stop",
    "attraction": "pass",
}

# Default dwell time (seconds) when stopping at a POI. Realistic estimates based on
# typical visit duration. Stops pay this cost; pass-bys pay 0. P1-2 dual budgeting.
DWELL_TIME_SEC: dict[str, float] = {
    "park_garden": 300.0,      # 5 min to stroll through a bit
    "water_feature": 180.0,    # 3 min to enjoy water
    "viewpoint": 120.0,        # 2 min to take in the view
    "monument_historic": 180.0, # 3 min to absorb history
    "museum_gallery": 900.0,   # 15 min at a real museum
    "artwork": 180.0,          # 3 min to appreciate public art
    "place_of_worship": 300.0, # 5 min for quiet reflection
    "library": 600.0,          # 10 min to browse shelves
    "bookshop": 600.0,         # 10 min browsing books
    "theatre_cinema": 1800.0,  # 30 min for a show (conservative lower bound)
    "cafe": 600.0,             # 10 min for coffee & pause
    "bakery_food_shop": 300.0, # 5 min to pick up pastries
    "restaurant": 1200.0,      # 20 min for a light meal
    "bar_pub": 900.0,          # 15 min for a drink
    "market": 600.0,           # 10 min to explore stalls
    "specialty_shop": 600.0,   # 10 min to browse
    "attraction": 300.0,       # 5 min generic attraction
}


# Warm, natural noun per category for POIs that have no OSM name — so an unnamed
# place reads as "a quiet garden", not the clunky "a park garden" / raw snake_case.
PRETTY_CATEGORY: dict[str, str] = {
    "park_garden": "garden",
    "water_feature": "fountain",
    "viewpoint": "viewpoint",
    "monument_historic": "historic landmark",
    "museum_gallery": "museum",
    "artwork": "piece of public art",
    "place_of_worship": "church",
    "library": "library",
    "bookshop": "bookshop",
    "theatre_cinema": "theatre",
    "cafe": "café",
    "bakery_food_shop": "bakery",
    "restaurant": "restaurant",
    "bar_pub": "bar",
    "market": "market",
    "specialty_shop": "shop",
    "attraction": "landmark",
}


def pretty_category(category: str) -> str:
    """Human noun for a category, e.g. 'park_garden' -> 'garden'."""
    return PRETTY_CATEGORY.get(category) or (category or "place").replace("_", " ")


def display_label(poi) -> str:
    """The single source of truth for naming a POI in any UI surface.

    The real OSM name when present; otherwise a natural 'a/an <noun>' phrase with
    the correct article (never a raw 'a artwork' or snake_case category).
    """
    name = getattr(poi, "name", None)
    if name is not None and str(name).strip():
        return str(name).strip()
    noun = pretty_category(getattr(poi, "category", "") or "")
    article = "an" if noun[:1].lower() in "aeiou" else "a"
    return f"{article} {noun}"


def posture(category: str) -> str:
    return POSTURE_DEFAULT.get(category, "pass")


def dwell_time_sec(category: str) -> float:
    """Dwell time in seconds for a stop at this category, or 0 if pass-by."""
    default_posture = posture(category)
    if default_posture == "stop":
        return DWELL_TIME_SEC.get(category, 300.0)
    return 0.0


def classify(tags: dict) -> str | None:
    """Map a POI's OSM tags to one curated category, or None if not of interest.

    ``tags`` is a flat dict of {osm_key: value} (NaN/None values allowed; they
    are treated as absent).
    """
    def has(key: str, *values: str) -> bool:
        v = tags.get(key)
        if v is None or (isinstance(v, float)):  # NaN from pandas
            return False
        v = str(v)
        return True if not values else v in values

    # --- order: specific before general ---
    if has("leisure", "park", "garden", "nature_reserve", "dog_park") \
            or has("landuse", "grass", "forest", "meadow", "village_green") \
            or has("natural", "wood", "grassland", "scrub"):
        return "park_garden"
    if has("tourism", "viewpoint"):
        return "viewpoint"
    if has("amenity", "fountain") or has("natural", "water", "spring") \
            or has("water") or has("waterway", "canal"):
        return "water_feature"
    if has("tourism", "museum"):
        return "museum_gallery"
    if has("tourism", "gallery"):
        return "museum_gallery"
    if has("tourism", "artwork"):
        return "artwork"
    if has("historic") or has("tourism", "monument", "memorial"):
        return "monument_historic"
    if has("amenity", "place_of_worship"):
        return "place_of_worship"
    if has("amenity", "library"):
        return "library"
    if has("shop", "books"):
        return "bookshop"
    if has("amenity", "theatre", "cinema", "arts_centre"):
        return "theatre_cinema"
    if has("amenity", "cafe"):
        return "cafe"
    if has("shop", "bakery", "pastry", "confectionery", "chocolate",
            "cheese", "deli", "wine", "coffee"):
        return "bakery_food_shop"
    if has("amenity", "restaurant"):
        return "restaurant"
    if has("amenity", "bar", "pub", "biergarten", "wine_bar"):
        return "bar_pub"
    if has("amenity", "marketplace") or has("shop", "greengrocer"):
        return "market"
    if has("shop", "art", "antiques", "antique", "craft", "interior_decoration",
            "musical_instrument", "second_hand", "frame", "photo"):
        return "specialty_shop"
    if has("tourism", "attraction", "artwork", "theme_park", "gallery"):
        return "attraction"
    return None


# OSM keys that signal a place is well-described. Presence => higher confidence.
_RICHNESS_KEYS = (
    "name", "wikidata", "wikipedia", "description", "website", "contact:website",
    "opening_hours", "phone", "contact:phone", "addr:housenumber", "addr:street",
    "image", "heritage", "tourism", "cuisine", "operator", "start_date",
)
# A place with a name + wikidata + description is essentially fully documented.
_RICHNESS_SATURATION = 6.0


def confidence(tags: dict) -> float:
    """Tag-richness/completeness in [0,1]. Bare category tag -> low; rich -> high."""
    present = 0
    for key in _RICHNESS_KEYS:
        v = tags.get(key)
        if v is not None and not (isinstance(v, float)):
            present += 1
    # name is necessary for the place to be nameable at all — weight it.
    name = tags.get("name")
    has_name = name is not None and not isinstance(name, float)
    score = present / _RICHNESS_SATURATION
    if not has_name:
        score *= 0.4  # unnamed places are inherently low-confidence
    return min(1.0, score)


def greenness(category: str) -> float:
    return CATEGORIES.get(category, {}).get("greenness", 0.0)


def quietness(category: str) -> float:
    return CATEGORIES.get(category, {}).get("quietness", 0.5)


# Tags to request from OSM when extracting POIs (broad pull; classify() filters).
OSM_QUERY_TAGS: dict[str, bool] = {
    "amenity": True,
    "leisure": True,
    "tourism": True,
    "shop": True,
    "historic": True,
    "natural": True,
}
