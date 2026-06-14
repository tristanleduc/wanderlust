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
        # well-known landmarks/areas a guide name-checks in passing.
        # NOTE: the Eiffel Tower is deliberately NOT listed — it's the planted
        # hallucination the zero-hallucination gate must keep catching.
        "Sorbonne", "Panthéon", "Champs-Élysées", "Tuileries", "Louvre",
        "Notre-Dame", "Île-de-France", "Arc de Triomphe", "Sacré-Cœur",
        "Sacre-Coeur", "Pont Neuf", "Pont des Arts", "Palais Garnier",
        "Opéra Garnier", "Grand Palais", "Petit Palais", "Place de la Concorde",
        "Place Vendôme", "Place des Vosges", "Place de la République",
        "Jardin du Luxembourg", "Luxembourg Gardens", "Jardin des Tuileries",
        "Centre Pompidou", "Musée d'Orsay", "Orsay", "Hôtel de Ville",
        "Trocadéro", "Les Invalides", "Invalides", "La Madeleine",
        "Père Lachaise", "Bois de Boulogne", "Bois de Vincennes", "Mona Lisa",
    ],
    "london": [
        "Thames", "South Bank", "Southbank", "North Bank", "the City",
        "Bloomsbury", "Soho", "Covent Garden", "Mayfair", "Westminster",
        "Southwark", "Lambeth", "Vauxhall", "Holborn", "Clerkenwell",
        "Fitzrovia", "Marylebone", "the West End", "the East End", "Shoreditch",
        "Bankside", "Embankment", "Strand", "Piccadilly",
        # landmarks
        "Big Ben", "the Tower of London", "Tower Bridge", "London Bridge",
        "St Paul's", "St Paul's Cathedral", "Buckingham Palace",
        "Trafalgar Square", "Leicester Square", "the Shard", "the Gherkin",
        "the London Eye", "Hyde Park", "Regent's Park", "St James's Park",
        "Green Park", "the British Museum", "Tate Modern", "the National Gallery",
        "Borough Market", "Camden", "Camden Town", "Notting Hill", "Kensington",
        "Greenwich", "Canary Wharf", "the Barbican", "Whitehall",
        "Downing Street", "the Houses of Parliament", "Westminster Abbey",
    ],
    "barcelona": [
        "Mediterranean", "Barri Gòtic", "Gothic Quarter", "El Raval", "El Born",
        "La Ribera", "Eixample", "La Rambla", "Las Ramblas", "Barceloneta",
        "Gràcia", "Montjuïc", "Poble Sec", "Ciutat Vella", "Port Vell",
        "Passeig de Gràcia",
        # landmarks
        "Sagrada Família", "Sagrada Familia", "Park Güell", "Casa Batlló",
        "Casa Milà", "La Pedrera", "Plaça de Catalunya", "Plaça Reial",
        "the Cathedral", "Catedral", "Camp Nou", "Tibidabo", "Arc de Triomf",
        "La Boqueria", "Mercat de la Boqueria", "Port Olímpic",
        "Barceloneta Beach",
    ],
    "newyork": [
        "Manhattan", "Midtown", "Downtown", "Uptown", "SoHo", "NoHo", "Tribeca",
        "Greenwich Village", "the Village", "East Village", "West Village",
        "Chelsea", "the Lower East Side", "the Upper West Side",
        "the Upper East Side", "Times Square", "Central Park", "Hudson",
        "East River", "Broadway", "Fifth Avenue", "the Flatiron",
        "Brooklyn", "Brooklyn Heights", "Saint Patrick's Cathedral", "St. Patrick's",
        "the Garment District", "Hell's Kitchen", "Murray Hill", "Koreatown",
        "Herald Square", "Madison Square", "the High Line", "Rockefeller Center",
        "Grand Central", "Penn Station", "Bryant Park",
        # landmarks
        "the Empire State Building", "the Chrysler Building",
        "the Statue of Liberty", "the Brooklyn Bridge", "Wall Street",
        "Washington Square", "Washington Square Park", "Madison Square Garden",
        "the Met", "the Metropolitan Museum", "MoMA", "the Guggenheim",
        "the Flatiron Building", "Battery Park", "Columbus Circle",
        "Lincoln Center", "Little Italy", "Nolita", "the Meatpacking District",
    ],
    "sanfrancisco": [
        "San Francisco", "Union Square", "the Financial District", "North Beach",
        "Chinatown", "Nob Hill", "Russian Hill", "Telegraph Hill", "the Embarcadero",
        "SoMa", "the Mission", "Hayes Valley", "the Tenderloin", "Fisherman's Wharf",
        "the Marina", "Market Street", "the Bay", "San Francisco Bay",
        # landmarks
        "the Golden Gate Bridge", "the Golden Gate", "Alcatraz", "Coit Tower",
        "Lombard Street", "the Painted Ladies", "Alamo Square",
        "the Ferry Building", "Pier 39", "the Presidio", "Golden Gate Park",
        "the Castro", "Haight-Ashbury", "the Haight", "Twin Peaks",
        "the Transamerica Pyramid", "Ghirardelli Square", "Dolores Park",
    ],
    "tokyo": [
        "Tokyo", "Ginza", "Marunouchi", "Nihonbashi", "Yurakucho", "Tokyo Station",
        "the Imperial Palace", "Chiyoda", "Hibiya", "Kanda", "Otemachi",
        "Shimbashi", "Tsukiji", "the Sumida", "the Sumida River",
        # landmarks / districts
        "Tokyo Tower", "Tokyo Skytree", "Sensō-ji", "Senso-ji", "Asakusa",
        "Shibuya", "Shibuya Crossing", "Shinjuku", "Harajuku", "Akihabara",
        "Ueno", "Ueno Park", "Roppongi", "Meiji Shrine", "Edo Castle",
        "Hibiya Park",
    ],
    "mumbai": [
        "Mumbai", "Colaba", "Fort", "Marine Drive", "Churchgate", "Nariman Point",
        "Kala Ghoda", "Ballard Estate", "Cuffe Parade", "South Mumbai",
        "the Gateway of India", "the Arabian Sea",
        # landmarks
        "Chhatrapati Shivaji Terminus", "the Taj Mahal Palace", "Haji Ali",
        "Girgaum Chowpatty", "Chowpatty", "Flora Fountain", "Crawford Market",
        "the Hanging Gardens", "Banganga", "Bandra", "Worli",
    ],
    "shanghai": [
        "Shanghai", "the Bund", "People's Square", "Huangpu", "the Huangpu River",
        "Nanjing Road", "Yu Garden", "the French Concession", "Jing'an",
        "Lujiazui", "Xintiandi", "the Old City",
        # landmarks
        "the Oriental Pearl Tower", "the Shanghai Tower", "the Jin Mao Tower",
        "the City God Temple", "the Jade Buddha Temple", "Tianzifang",
        "Jing'an Temple", "People's Park", "the Yuyuan Garden",
    ],
    "berlin": [
        "Berlin", "Mitte", "the Spree", "Museum Island", "Unter den Linden",
        "Alexanderplatz", "the Brandenburg Gate", "Kreuzberg", "Prenzlauer Berg",
        "Friedrichshain", "Hackescher Markt", "Gendarmenmarkt", "Potsdamer Platz",
        "the Tiergarten",
        # landmarks
        "the Reichstag", "the TV Tower", "Fernsehturm", "Checkpoint Charlie",
        "the Berlin Wall", "the East Side Gallery", "Berliner Dom",
        "the Berlin Cathedral", "the Holocaust Memorial", "Charlottenburg",
        "the Victory Column", "the Siegessäule", "Nikolaiviertel",
        "Kurfürstendamm", "the Pergamon Museum",
    ],
}


def geo_terms(area_key: str, label: str = "") -> list[str]:
    """Allowed geographic-context names for an area (empty for un-curated ones)."""
    terms = list(CITY_GAZETTEER.get((area_key or "").lower(), ()))
    if label and label.strip():
        terms.append(label.strip())  # the city's own name ("London", "Paris")
    return terms
