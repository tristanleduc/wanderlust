# WanderLust — MVP Project Outline

**Draft for ModelBest / OpenBMB · 14 August 2026**
Ishrat Jahan Ananya · Tristan Leduc

Working draft, not final. Written to align on scope so resources and promotion can be planned.

---

## 1. What WanderLust is

Navigation apps answer one question: what is the fastest way there? WanderLust asks a better one. You give it a destination, a spare-time budget, and a mood in plain language — "a slow Sunday-morning kind of walk," "bookshops and quiet streets" — and it routes you from A to B past places you will actually love, then tells you why each one is on your path.

The hackathon version proved the mechanism works. This project turns it into something people use more than once.

**Positioning: the app that finds what Google Maps doesn't.** Not a trip planner, not a tour-guide app. A discovery layer over journeys already happening, built first for people who live in Paris and move through it every day.

---

## 2. Target users and core use case

**Primary — Paris residents on foot or bike.** Commuters, walkers, cyclists. They give us a repeat loop: same journey, different detour. They are also the source of the taste signal that makes the product improve over time.

**Secondary — visitors staying long enough to wander.** Not landmark tourists. People with a free afternoon in a city they want to feel rather than tick off. This group carries the strongest willingness to pay, and the roadmap after V1 is built for them.

**Core use case:** *"I am going from A to B and I have fifteen spare minutes."*

The moment of value is a journey already underway. No planning session, no itinerary, no forward commitment — which is precisely what separates this from every trip-planning product on the market.

---

## 3. Main user flow

1. Open the app — current location detected.
2. Enter a destination.
3. Describe the mood in free text.
4. Set the detour budget (how much extra time) and adventurousness.
5. Get a route: the direct line and the discovery route on one map, with the exact time the detour costs, plus a written itinerary explaining each stop.
6. Walk or ride it with live position.
7. Save what you liked. The taste profile sharpens for next time.

---

## 4. Features

### Must-have for V1

- Paris, full city, routed offline
- Free-text mood → scored routing weights (MiniCPM5-1B)
- **The Gem Layer** — see section 5, this is the core of the release
- Grounded narration behind the existing zero-hallucination gate
- Live location during the route
- Local-first taste profile, no accounts
- Alternative routes, GPX export, hand-off to Google/Apple Maps

### Deferred, and announced as coming

- **Photo → taste profile (MiniCPM-V).** Point your camera at a place whose feeling you want more of, and the route reshapes around it. We want to ship this properly rather than early, so it is out of V1 and announced publicly as the next feature. It gives the launch a second act and gives us a reason to come back to press and users a few weeks later.
- User-contributed places and moderation
- Cities beyond Paris
- Accounts, sync, social features
- Audio narration (MiniCPM-o)
- On-device inference
- Monetisation mechanics

---

## 5. The Gem Layer

This is the heart of V1 and the part most worth your engineers' attention.

**The problem.** Our hackathon build ranked 30,357 Paris places using a confidence score derived from OpenStreetMap tag richness. But a place hidden down an alley is, by definition, thinly documented — so the system actively penalised exactly the places we most want to surface. Every competitor has the same underlying map data. Solving this is the only thing that makes WanderLust different from a navigation app with a mood slider.

**The insight: gem-ness is two independent things, and they need different machinery.**

> **Gem = Character × Obscurity**
>
> High character + high fame = Notre-Dame. Not a gem.
> Low character + high obscurity = a parking garage. Not a gem.
> High character + low fame = a gem.

### Axis A — Character (the model's job)

"Is this place interesting?" is a semantic judgment, and it is exactly what a small language model is good at. One offline batch pass with MiniCPM5-1B over all 30,357 POIs, each given its name, category, full tag set, street context and immediate neighbours, returning a constrained JSON character score plus a one-line rationale.

Names alone carry enormous signal in Paris — *Librairie Jousseaume* and *Relay* are not the same kind of object, and a model can tell. Structured output under a fixed schema is MiniCPM5-1B's strongest reported axis, which is why this is the right job for it.

### Axis B — Obscurity (emphatically not the model's job)

"Is this place under-known?" is a factual question about the world that no 1B model can answer and would confidently hallucinate. We compute it classically, from four sources:

**B1 — Chain detection.** `brand`, `operator` and `wikidata` tags, plus name-frequency across the corpus: a name appearing forty times in Paris is a chain. Hard negative signal.

**B2 — Fame signals.** Wikipedia and Wikidata links, `tourism=attraction`, heritage designations. These mark places that are interesting *and already famous* — which is precisely what we want to route around, not toward.

**B3 — Physical concealment.** This is where "a hidden gem in a corner alleyway" literally lives, and it is pure geometry: the road class of the nearest way (`footway` and `service` versus `primary`), set-back from the street centreline, position inside a *passage couvert* or interior *cour* — a distinctly Parisian category of hidden place — distance to the nearest metro entrance, and distance to the nearest tourist cluster.

**B4 — OpenStreetMap editing metadata.** Adding `out meta` to our existing Overpass queries returns version count, last-edit timestamp and contributor identity at no additional infrastructure cost. A place mapped once by a single local contributor years ago and never revisited is strongly hidden; one edited forty times is under attention. This replaces our broken tag-richness heuristic with a principled measure of *attention* rather than simply inverting the sign.

### The Paris-specific advantage: Apur BDCOM

Apur (the Paris urbanism agency) publishes **BDCOM** under ODbL — a triennial door-to-door census of every ground-floor commercial premises in Paris with a shop window, surveyed in the field by around twenty surveyors, with vintages available for 2017, 2020 and 2023.

Three things this gives us that no map database can:

1. **Completeness.** We learn which real businesses exist that OpenStreetMap never recorded — the gap where gems live by definition.
2. **Persistence across three vintages.** A small independent business at the same address in 2017, 2020 and 2023 has survived a decade and a pandemic in a city that churns constantly. That is an empirical proxy for "locally beloved" available nowhere else, and it cannot be gamed.
3. **Premises size.** The under-300m² band cleanly separates independent from chain and big-box.

This is free, openly licensed, field-surveyed, Paris-specific, and as far as we can tell unused by anyone in this product category. It is also the clearest argument for building Paris deeply before building anywhere broadly: depth here is a real asset, breadth is a commodity.

### Validation — how we know it works

The gem score is a ranking problem, so we treat it as one rather than trusting intuition. We hand-label a held-out set of several hundred Paris places (ourselves and a small group of local walkers) and measure the ranker with nDCG@k and precision@k, ablating each signal to see what actually contributes.

This is directly our professional background — Ishrat spent this year building cross-encoder rerankers and evaluation pipelines over BEIR, MIRACL and ViDoRe — and it converts a soft product claim into a number we can defend, tune against, and eventually publish.

### The flywheel that needs no user-generated content

V1 collects implicit relevance signals passively: which suggested stops users accept versus route away from, which they save, and — with live location — whether they actually walked past a place and **lingered** there. Dwell time is a strong implicit relevance label with no moderation burden and no contribution UI.

Over months this becomes training data for a learned reranker over places. That is the compounding asset, and it starts accumulating from the first user without us building a contribution platform first. Explicit user submissions arrive later, on top of a system that already works.

**Where your data support fits:** scaling the labelled evaluation set beyond what two people can annotate, and access to licensed or purchased place data if you have it.

---

## 6. Technical approach

The routing core is built, tested and unchanged. Work concentrates on the client and the gem layer.

**Routing (65 tests passing).** Paris walk graph of 77,454 nodes and 221,688 edges from OpenStreetMap via OSMnx. The detour is modelled as an Orienteering Problem — prize-collecting with fixed endpoints — solved with a budgeted greedy heuristic over a submodular reward, so route variety emerges from the objective rather than a hand-tuned penalty. SciPy multi-source Dijkstra keeps warm requests near one second.

**Models.** MiniCPM5-1B handles vibe interpretation, narration, and the offline character-scoring pass. A tiered fallback chain (MiniCPM → embedding interpreter → keyword net) means the app degrades but never breaks; we intend to preserve that abstraction so the routing engine stays independent of which tier ran.

**Client.** The Gradio `gr.Server` shell is replaced by a native iOS and Android app against a thin API. Native is required for live location and for the on-device path later.

**Inference.** Hosted endpoint for V1.

**The direction we want to earn.** A capable model routing you through Paris with no server, working offline mid-walk, is the clearest possible demonstration of the edge-inference thesis. We would rather get there on a working product than start there on a prototype.

**Open question for your engineers: French.** Published MiniCPM benchmarks are English and Chinese. Paris means French place names, French mood descriptions, French shop signage. We plan to build a small French evaluation set early and would gladly publish it openly as a joint artefact — it is likely useful to you well beyond this app.

---

## 7. Timeline

Both of us are employed full time; this is evenings and weekends with no fixed hours. Phases rather than dates.

| Phase | Work |
|---|---|
| **1** | API extraction from the Space; gem layer — BDCOM ingestion, obscurity signals, character pass; labelled evaluation set |
| **2** | Native iOS and Android client, live location, hosted inference |
| **3** | Internal testing on real Paris routes, ranking tuned against the eval set |

**Target: a rough but working MVP in approximately six weeks from kickoff.**

That means a real app on real phones routing real people through Paris. It does not mean store-ready. Beta, polish and public launch follow, and we would rather scope those once we have seen how the MVP behaves than commit to them now. We propose a checkpoint every two to three weeks.

---

## 8. Commercial intent

We intend WanderLust to become a paid product — most likely free in Paris with paid city packs later, or a low-cost subscription. Nothing is decided and there is no monetisation in V1.

We raise it now because it shapes the roadmap and because you should know before resources are committed rather than after. We do not think it conflicts with a MiniCPM showcase: a product people pay for demonstrates more than one people try once.

---

## 9. Go-to-market

**A note on channels, said plainly.** OpenBMB's audience is developers. WanderLust's users are Parisians who walk. Those are different people, and we think it is worth being explicit about which channel does which job rather than counting developer reach as user acquisition. Your channels are excellent for credibility, recruiting technical early testers, and the tech-press angle. They will not fill the app. The plan below is what fills the app.

### The core idea: the product makes its own marketing

Every route WanderLust generates is a finished, shareable artefact — a map, a photograph, a short story about a street. That is native social content, produced at zero marginal cost, and it works as marketing *before the app exists*. Tristan shoots seriously; the visual quality will not look like app marketing.

### 1. Build the audience before the product (starts immediately)

One Paris walk per week on Instagram and TikTok: the route, the photographs, what is on it and why. A simple landing page with email capture. By launch we have an audience that already wants the thing, rather than a cold start on day one. This is the highest-leverage item on this list and it costs nothing but time.

### 2. Local creators, not press

Paris walking, photography and food accounts in the 10k–100k follower range. Each gets a bespoke route built for their audience; they post it. Better cost per install than press or ads, entirely measurable, and it compounds. This is a concrete, modest budget line we would want your support on.

### 3. The featured places are the distribution

Every independent café, bookshop and atelier we surface as a discovery has its own audience and a direct commercial reason to share that they are on WanderLust — a card in the window, a story post. This is our cheapest channel, it is fully aligned with the product's ethos, and it is structurally unavailable to a large incumbent.

### 4. French-language App Store optimisation

Unglamorous and it is how walking apps are actually found. French-first listing, targeting *balade*, *promenade*, *itinéraire à pied*. Done properly at launch, not retrofitted.

### 5. Launch to a moment, not a date

Paris has city-wide walking moments — Journées du Patrimoine in September, Nuit Blanche, the start of spring walking season. Anchoring launch to one gives press an actual reason to write and gives the product a natural first surge.

### 6. Paid acquisition as a measured experiment

A small Paris-geotargeted budget, run to measure cost per install and seven-day retention before anything scales. We would report those numbers back to you rather than spend against a vanity metric.

### 7. The second act

Holding the multimodal photo feature back gives us a second launch a few weeks after the first — new press angle, reactivation of early users, and a natural moment for a joint technical announcement with you.

### Where your support matters most

- Budget for creator partnerships and a measured paid-acquisition test
- Amplification through OpenBMB channels, understood as credibility and technical recruitment rather than user acquisition
- Support on the tech-press angle for the on-device story, which serves both of us

---

## 10. What we would need from you

**Models and infrastructure**
- Hosted inference endpoint or credits for MiniCPM5-1B. During the hackathon, ZeroGPU quota exhaustion repeatedly forced the app into template fallback — a documented, not hypothetical, need.
- Mobile-quantised builds and the iOS/Android edge-deployment code, for the on-device path.
- Guidance on ecosystem lag: MiniCPM-V has at times required llama.cpp and Ollama forks ahead of upstream merges, which is a scheduling risk for a shipped app.

**People**
- A named engineering contact for model questions.

**Data**
- Annotation support to scale the labelled gem evaluation set beyond what two people can produce.
- Any licensed place data you can make available.

**Promotion**
- Budget for creator partnerships and a measured acquisition test.
- Coordinated amplification at launch and at the multimodal follow-up.

**Alignment**
- A short written note on ownership and attribution. WanderLust stays ours to steer, as your first email proposed; we would simply like that on paper before we build.

---

## Next

Happy to walk through this on a call. Most worth pressure-testing together: the gem layer signal design, what your data support can realistically cover, and a realistic joint launch window.
