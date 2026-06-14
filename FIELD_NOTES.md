# Field Notes: Building WanderLust

> **Draft** for the Build Small Hackathon's `achievement:fieldnotes` (Track 1 — Backyard AI).

## The inversion

Every navigation app I've used solves the same problem: get me there in the minimum time. DiscoverRoute starts from the opposite premise. If you're walking across Paris and you'd happily spend fifteen extra minutes, that surplus is a *budget* — and the interesting question is what to spend it on.

So the app takes a start, a destination, a free-text vibe, and an "adventurousness" level, and returns a walkable or bikeable route that deliberately detours past places matching your taste — within a hard travel-time budget — plus a narrated itinerary explaining why each place is on the path. The route never exceeds `(1 + budget) ×` the direct time, and budget 0 simply gives you the plain route. It runs on small (≤32B) open models and OpenStreetMap data, single city: Paris.

## Walking skeleton first, AI last

The strategy I committed to in the build log's first line: *walking skeleton first; scariest plumbing early; AI added only after a manual-weight router already works.* Each brick had a definition-of-done and a test, and wasn't left until green.

That meant the first four bricks contained no AI at all.

**Brick 0** was the boring-but-scary plumbing: download the Paris walk network via OSMnx into a graph of **77,454 nodes and 221,688 edges** (a 90 MB GraphML file), geocode inputs, run Dijkstra, render the polyline on a Folium map inside a Gradio shell. Seven tests, including a sanity check that République→Luxembourg is at least 2 km and that bike beats walk (travel time is derived per mode from one graph: walk 4.8 km/h, bike 15 km/h).

**Brick 1** built the POI layer: **30,589 Paris POIs across 17 curated categories**, cached to a 1.2 MB parquet file, each with greenness/quietness priors and a *confidence* score derived from OSM tag richness.

**Bricks 2–3** were the heart of the system, and they're classical algorithms: a budgeted **submodular orienteering solver**. The key modeling insight is diversity by design. A naive scorer that just sums point values will happily route you past five cafés, because cafés are everywhere and score fine individually. The submodular reward applies *diminishing returns per category*: the first café is worth full value, the second much less, the third almost nothing. So a park + a viewpoint + a bookshop beats five cafés — not because of a hand-tuned penalty, but because the objective itself says variety is worth more than repetition. The solver is a better-of-two greedy (picking by raw gain *and* by reward-per-added-time, keeping the better result), tested against a known-optimal synthetic instance, with an explicit diversity-beats-repetition test.

Only once that manual-weight router produced real discovery routes on a real map did any model enter the picture.

## What the small models actually do

Two models, both deliberately small, each load-bearing in exactly one place:

- **`BAAI/bge-small-en-v1.5` (~33M parameters, CPU-only)** turns your free-text vibe into category affinities. Each of the 17 categories has a short gloss; the vibe is embedded and matched by cosine similarity to those glosses, min-max rescaled into a usable weight range. "Quiet green wander" and a contrasting vibe produce measurably different waypoint sets on the same A/B pair — that's an end-to-end test, not a hope.
- **`Qwen/Qwen3.5-9B` (Apache 2.0, thinking mode off)** is an *optional* narration enhancer. The default itinerary text comes from a deterministic template that is grounded by construction; the LLM only rewrites it, on GPU (ZeroGPU on the Space), and is gated by a verifier (more on that below). bf16 at ~18 GB it sits comfortably on ZeroGPU. I considered the whole ≤32B ladder — Qwen3.5-4B (lighter), 9B (chosen), 27B (needs quantization on 40 GB) — and excluded Qwen3.5-35B-A3B because 35B breaks the hackathon's 32B cap.

Small-is-the-point here, not a constraint to grumble about. Routing is pure classical algorithms; the model is load-bearing only in interpretation and narration. The skeleton runs CPU-only and offline with the rule-based fallback — which means the template-narration mode runs on nothing but the 33M embedder. Your taste profile never needs to leave your device (it's persisted per-device via browser state, no accounts), and the whole interpretation stack fits on a laptop.

## The zero-hallucination gate

LLMs narrating a route is exactly the place hallucination hurts most: the model will cheerfully invent a charming bistro that doesn't exist. So narration sits behind a **fail-closed grounding verifier**: it extracts capitalized place-name spans from the generated text (handling multi-word names and French "de la" chains) and passes only if *every* mention maps to an allowed name — the route's waypoints, the start/end, or "Paris". Any violation, and the system silently falls back to the deterministic template. The release-gate test plants a hallucinated "Eiffel Tower" in narration and verifies the gate catches it; the final end-to-end test asserts the shipped narration is grounded.

Then the adversarial review pass found a real hole in it. The old check accepted an allowed name being a *substring* of a longer mention — so if "Café de la Paix" was a real waypoint, the invented "Café de la Paix sur Seine" sailed through. The fix inverts the containment: strip common words from a mention, then require the *core* to be a substring of an allowed name, not the reverse. The same pass also fixed mention extraction, which had been gluing "République, Paris and Jardin…" into one span by treating "and"/"et" as name-internal. Both attack shapes — appended qualifier and shortened reference — now have regression tests.

## War stories

A few things that broke, and what fixing them taught me:

**Overpass timed out.** The combined POI query for all of Paris was too much for the Overpass API. Fix: fetch one tag key at a time with a 300s timeout — amenity (77k raw), shop (29k), tourism (7.5k), leisure (6k), historic (2.5k), natural — then filter down to the 30,589 classified POIs.

**Per-pair routing was the first latency wall.** Computing travel times between candidate POIs pair-by-pair put warm requests at **8–14 seconds**. Replacing it with **SciPy multi-source Dijkstra** — one C call over a cached CSR adjacency matrix — brought warm per-request latency to **~1 second**.

**The 635ms hiding in a loop.** During the adversarial review, the performance reviewer reported alarming numbers — which turned out to be a red herring: their machine was thrashing. Re-measured on a clean machine, the suggested fix (porting route-stitching to CSR) was needless — stitch was only 59ms. The real bottleneck was `build_matrix` at **~635ms, recomputed three times** inside the alternatives loop. Hoisting the corridor selection and matrix out of the loop (compute once, reuse) dropped `n_alternatives=3` from **~2.1s to ~1.3s** — the same cost as a single route. An STRtree took corridor selection from 87ms to ~5ms for good measure. Lesson: measure on a quiet machine before believing a profile, and look for repeated work before clever work.

**The review fixed product lies, too.** The alternatives label showed *total* minutes where it claimed to show detour minutes; the vibe's budget hint was displayed but silently discarded; off-domain vibes ("tax deadline") manufactured false preferences until a minimum-similarity-span guard mapped them to neutral. And error handling got hardened so disconnected nodes or a corrupt parquet degrade to the plain route instead of a traceback. After the pass: 42 tests passing.

## The design handoff port

The default Gradio look got replaced wholesale from a design handoff: a low-poly "clay sticker" aesthetic — cream paper background, cobalt/grass/coral/sun palette, Fredoka display type. The port landed as a theme plus CSS (sticker cards, a coral CTA that visibly depresses, springy sliders, a framed map window with a titlebar), a results bounce-in observer, and a friendly empty/no-detour state.

The fiddliest part: the map is a Folium iframe, and **an iframe can't be animated from the parent page**. So the route draw-on and the staggered POI marker pops are injected as JavaScript *inside* the iframe's own document, keyed off CSS class names attached to the polylines and markers at render time. Reduced-motion and AA focus rings are respected throughout.

## Honest limitations

- **Bike uses the walk graph.** One mode-agnostic graph, with per-mode speeds. Routing bikes on the pedestrian network is a documented v1 approximation; a separate bike graph is on the deferred list.
- **Confidence is OSM tag richness, nothing more.** A well-tagged tourist trap looks "confident"; a beloved hole-in-the-wall with two tags looks risky. The adventurousness slider leans into this honestly — it both fades the confidence penalty and *boosts* under-documented POIs — but the signal itself is just tag count.
- **Paris only.** The graph and POI table are built offline for one city. The pipeline generalizes; the data doesn't, yet.
- Cold boot pays ~8.6s to load the 90 MB graph (plus 0.2s for the CSR cache); a faster serialization is a known, deferred debt.

## What's next

The P2 list, in rough order: live navigation (today it's plan-then-walk), external enrichment beyond OSM tags so "confidence" can mean more than tag richness, and place embeddings so taste matching can operate on places themselves rather than on 17 categories. Nearer-term housekeeping from the log: a real bike graph, faster graph serialization, and per-place removal in the profile UI.

The submission itself is the last brick: push to a Space under the hackathon org, record the demo, write the post — and decide whether DiscoverRoute is Backyard AI (a real problem, really used) or a resident of the Thousand Token Wood.
