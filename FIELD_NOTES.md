# Field Notes: Building WanderLust

*A walk from point A to B, routed through the places you'll actually love powered by a 1B model and a city's worth of OpenStreetMap, running entirely inside one Hugging Face Space.*

**Track:** Backyard AI · **Live Space:** https://huggingface.co/spaces/build-small-hackathon/WanderLust · **Demo video:** https://www.youtube.com/watch?v=55Ofnt6Hhv4 · **Source:** https://github.com/tristanleduc/wanderlust · **Published on the HF blog:** https://huggingface.co/blog/coreprinciple/wanderlust

This is an app built by myself and my teammate (https://huggingface.co/JohnDoe6) as a submission for the Huggingface Hackathon.

---

## The inversion

Every navigation app we've used solves the same problem: get me there in the minimum time. WanderLust starts from the opposite premise. We're cyclists, and crossing an unfamiliar city we kept hitting the same frustration which is that the map only ever knows the *fastest* line between two points, but the whole joy of exploring is the bookshop, the quiet square, the viewpoint you'd never have found on the direct route. If you'd happily spend fifteen extra minutes, that surplus is a *budget* — and the interesting question is what to spend it on!

So WanderLust takes a start, a destination, a free-text *vibe*, and an *adventurousness* level, and returns a walkable or bikeable route that deliberately detours past places matching your taste within a hard travel-time budget plus a narrated itinerary explaining why each place is on your path. The route never exceeds `(1 + budget) ×` the direct time; budget 0 simply gives you the plain route. It runs on a 1B model and OpenStreetMap data, across nine cities, with no cloud API calls at request time.

## Why the AI is load-bearing

Routing a path isnt actually the hard problem here, it's the gap between *how people describe what they want* and *what a router can optimize*. Someone types "a slow Sunday-morning kind of walk" or "bookshops and quiet streets," and something has to turn that unbounded human mood into concrete, scored weights across seventeen place categories plus quiet/green/lively modifiers. No lookup table or keyword list maps open-ended language onto a route. The model *is* the bridge and then it writes the itinerary that explains, in your own words, why each chosen stop matches what you asked for.

**Small is the point, not a constraint to grumble about.** Routing stays pure classical algorithm; the model is load-bearing in exactly two places —> interpretation and narration — and both fit a 1B. Your taste profile never has to leave the Space; there are no accounts and no external inference API.

## Walking skeleton first, AI last

The strategy we committed to on the build log's first line: *walking skeleton first, scariest plumbing early, AI added only after a manual-weight router already works.* Each brick had a definition-of-done and a test, and wasn't left until green. The first bricks contained no AI at all.

The boring-but-scary plumbing came first: download the Paris walk network via OSMnx into a graph of **77,454 nodes and 221,688 edges** (a 90 MB GraphML), geocode inputs, run Dijkstra, render the polyline on a map. Then the POI layer: **30,357 Paris POIs across 17 curated categories**, each with greenness/quietness priors and a *confidence* score derived from OSM tag richness.

The heart of the system is classical, and it's where the engineering went. We model the detour as the **Orienteering Problem** — prize-collecting with fixed endpoints, NP-hard in general and solve it with a budgeted greedy heuristic over a **submodular reward**. The key modeling insight is *diversity by design*. A naive scorer that just sums point values will happily route you past five cafés, because cafés are everywhere and each scores fine on its own. The submodular reward applies diminishing returns *per category*: the first café is worth full value, the second much less, the third almost nothing. So a park + a viewpoint + a bookshop beats five cafés not from a hand-tuned penalty, but because the objective itself says variety is worth more than repetition. The solver runs two greedy passes: by raw marginal gain *and* by reward-per-added-time and keeps the higher-reward feasible result; a single ratio pass alone gets trapped hoarding cheap duplicates. It's tested against a known-optimal synthetic instance, with an explicit diversity-beats-repetition test.

Only once that manual-weight router produced real discovery routes on a real map did any model enter the picture.

## What the small models actually do

Two models, both deliberately small, each load-bearing in exactly one place — with graceful fallbacks so the app *never* breaks:

- **`openbmb/MiniCPM5-1B`** (1B parameters, standard `LlamaForCausalLM`, no custom kernels) does two jobs from one set of weights. **Call 1** turns your free-text vibe into a scored JSON of category weights. **Call 2** writes the first-person itinerary narration. It runs **inside the Space on ZeroGPU** via `@spaces.GPU`, weights pulled straight from the Hub — no external inference API, nothing leaves the Space.
- **`BAAI/bge-small-en-v1.5`** (~33M parameters, CPU-only) is the fallback interpreter: when no GPU is allocated, the vibe is embedded and matched by cosine similarity against a gloss for each of the 17 categories.

The interpreter is a **tiered dispatcher** — MiniCPM5-1B → bge-small embeddings → a model-free keyword net → neutral — and every tier returns the same `{category: affinity}` shape, so the routing engine is oblivious to which one ran. The model is what makes the experience feel like it read your mind; the fallbacks are what keep it standing when ZeroGPU is busy. Narration has the same property: a deterministic, grounded-by-construction template is always available, and the LLM only *rewrites* it.

## The zero-hallucination gate

Letting an LLM narrate a route is exactly the place a hallucination hurts most: the model will cheerfully invent a charming bistro that doesn't exist, and a user might walk there. So narration sits behind a **fail-closed grounding verifier**. It extracts capitalized place-name spans from the generated text — handling multi-word names and French "de la" chains, and treating "and"/"et" as list-joiners that *separate* names rather than glue them — and the text passes only if *every* mention maps to an allowed name: the route's actual waypoints, the start/end, or a curated per-city gazetteer of districts, rivers, and landmarks. Any violation, and the system silently falls back to the deterministic template. The release-gate test plants a hallucinated "Eiffel Tower" and verifies the gate catches it.

The interesting part was getting the gate *right*, and it took a real adversarial pass to find the holes:

- **The substring trap.** The first version accepted an allowed name being a substring of a longer mention — so if "Café de la Paix" was a real waypoint, the invented "Café de la Paix sur Seine" sailed straight through. The fix inverts the containment: strip common words to a mention's *core*, then require the core to be a substring of an allowed name, not the reverse. Appending an invented qualifier to a real name is the precise hallucination vector, and it's now closed with a regression test.
- **The gate vs. good prose.** Fail-closed cuts both ways: a *too*-strict gate rejected genuinely grounded, evocative writing — a guide naming the Marais, the Seine, or the Latin Quarter — and silently dropped the app back to template narration every time. We watched this happen in the live inference traces. The fix was the per-city gazetteer plus a vocabulary of era/architecture adjectives and generic geographic nouns ("river," "quarter," "bridge"), so the model can write like an actual city guide and scene-set, while a distinctive token like "Eiffel" still has to match a real allowed name. The guarantee holds; the prose breathes.

## Off the grid: nine cities, no cloud at request time

Paris ships full-city. The other eight — London, Barcelona, Berlin, New York, San Francisco, Tokyo, Mumbai, Shanghai — are baked offline as bounded walkable cores and hosted as an **open Hub dataset** (`build-small-hackathon/discoverroute-cities`), pulled and **pre-warmed into memory at boot** so the first user to pick a city waits zero seconds. With `DISCOVERROUTE_OFFLINE=1` (the deployed config) there are **no cloud API calls at request time**: geocoding resolves against the local POI index, routing runs on the cached graph, and the model runs in-Space. The whole interpretation-and-narration stack — and the template path entirely fits on a laptop.

## War stories

A few things broke, and what fixing them taught us:

- **Overpass timed out.** The combined POI query for all of Paris was too much for the Overpass API. Fix: fetch one tag key at a time with a long timeout — amenity, shop, tourism, leisure, historic, natural — then classify down to the 30,357 POIs.
- **Per-pair routing was the first latency wall.** Computing travel times between candidate POIs pair-by-pair put warm requests at **8–14 seconds**. Replacing it with **SciPy multi-source Dijkstra** — one C call over a cached CSR adjacency matrix — brought warm per-request latency to **~1 second**.
- **The 635 ms hiding in a loop.** During the adversarial review, a performance profile flagged alarming numbers that turned out to be a thrashing machine — a red herring. Re-measured on a quiet machine, the real bottleneck was `build_matrix` recomputed **three times** inside the alternatives loop. Hoisting it out (compute once, reuse) dropped three alternative routes from **~2.1 s to ~1.3 s** — the cost of a single route. Lesson: measure on a quiet machine before believing a profile, and look for repeated work before clever work.
- **ZeroGPU quota is per-call duration.** The live Space started falling back to the template, and the traces told us why: every inference threw `"180s requested vs. 170s left."` ZeroGPU *reserves* the requested `duration` seconds per call, so asking for a fat 120 s slice drains a day's allowance in a dozen requests. A 1B model loading from cache and generating ≤480 tokens on an A10G finishes well inside 45 s, so we ask for that — roughly 3× more calls per day. Reading the actual production traces, not guessing, is what found it.

These last two only surfaced because we logged every inference call to a trace dataset (`build-small-hackathon/discoverroute-traces`) — which turned debugging the live Space from guesswork into reading rows.

## The custom frontend

The default Gradio look got replaced wholesale. WanderLust runs on a hand-built HTML/CSS/JS app-shell served by Gradio's `gr.Server` FastAPI backend and called from the browser via `@gradio/client` — **no default Gradio components**: a custom map window with its own titlebar, custom controls, a live-map loader. The fiddliest part: the map is an iframe, and an iframe can't be animated from the parent page. So the route draw-on and the staggered marker pops are injected as JavaScript *inside* the iframe's own document, keyed off CSS classes attached to the polylines and markers at render time. Reduced-motion preferences and focus rings are respected throughout.

## Save your taste, and take the route with you

Two product details we care about, because a discovery route is only worth planning if you can actually *keep* it.

**Your taste, remembered.** You can save a standing taste profile — free-text preferences plus the categories of places you've saved — and WanderLust blends that with each trip's mood instead of asking you to re-describe yourself every time. A handful of saved places nudges the route toward what you like, with a saturating boost so a few saves matter but a hundred don't swamp the trip's actual vibe. True to the "small, local-first" spirit, there are **no accounts**: the profile lives on your device, never on a server.

**Your route, taken with you.** A plan you can't follow is just a pretty picture, so every result carries a *Take it with you* row built entirely client-side from the plan payload — no extra round-trip:

- **Open in Google Maps** — a turn-by-turn deep link with your detour stops as waypoints (in walking or biking mode to match your choice; Google caps a single link at 9 stops).
- **Open in Apple Maps** — a walking-directions deep link from start to destination.
- **Download GPX** — the full track plus *every* waypoint, named, ready for a watch, a bike computer, or any mapping app.

The GPX is the lossless option, and the UI says so honestly: when a route has more stops than a Google Maps link can hold, it tells you the GPX keeps all of them. You plan the interesting way here, then walk or ride it with whatever navigation you already trust.

## Honest limitations

- **The eight secondary cities are walkable cores, not whole metros.** Paris is the only full-city build; the rest are bounded around their centres. The pipeline generalizes; the offline data is sized to keep the Space lean.
- **The model path depends on a GPU slice being free.** When ZeroGPU is saturated, you get the embedding interpreter and the template narration — correct and grounded, just less personal. That's a deliberate floor, not a crash.

## What we shipped

A discovery router where the AI is genuinely load-bearing but small enough to run in one Space; a classical orienteering core that earns *diversity* from its objective rather than a hack; a fail-closed grounding gate hardened by real adversarial review; nine cities offline; a custom frontend; and two open datasets — city cores and inference traces — left on the Hub for anyone to reuse.

The spend-your-extra-time-on-discovery idea turned out to need surprisingly little model and a surprising amount of careful plumbing. That felt like the right ratio.
