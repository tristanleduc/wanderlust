# WanderLust — MVP Project Outline

**Draft for ModelBest / OpenBMB · 14 August 2026**
Ishrat Jahan Ananya · Tristan Leduc

Working draft, not final — written to align on scope so technical and promotional resources can be planned.

---

## 1. What WanderLust is

WanderLust turns a journey you were already making into a small discovery. You give it a destination, the spare time you have, and a few words about the kind of walk you want; it returns a route past places you would otherwise never have found, with a line on each explaining why it's there.

The hackathon version proved the mechanism works. This project turns it into something people use more than once.

**Positioning: the app that finds what Google Maps doesn't.** Not a trip planner, not a tour-guide app. A discovery layer over journeys already happening.

---

## 2. Users and core use case

**Primary: Paris residents on foot or bike.** Commuters, walkers, cyclists. They give us a repeat loop and, more importantly, the behavioural signal that makes the ranking improve over time.

**Secondary: visitors staying long enough to wander.** Not landmark tourists. People with a free afternoon in a city they want to feel rather than tick off. This group carries the strongest willingness to pay, and the roadmap after V1 is built for them.

**Core use case:** *"I am going from A to B and I want to discover places along the way."*

**A second mode falls out of the same solver:** leave the destination empty and it returns a loop from where you are standing — *"I have an hour in this neighbourhood, show me what is interesting."* Cheap to add because the router is unchanged. We keep the A-to-B framing as the product's story: "things to do near me" is a crowded space, and the detour is what makes us different.

---

## 3. Main user flow

1. Open the app — current location detected, or typed.
2. Enter a destination (or leave it empty for a loop).
3. Describe the mood in free text.
4. Set the detour budget and adventurousness.
5. Get a route: the direct line and the discovery route on one map, the exact time the detour costs, and a written itinerary explaining each stop.
6. Walk or ride it with live position.
7. Save what you liked. The taste profile sharpens for next time.

---

## 4. V1 features

### Must-have

- Paris, full city
- Both modes: destination routing and neighbourhood loop
- Free-text mood → scored routing weights (MiniCPM5-1B)
- **The Gem Layer** — section 5, the core of the release
- Grounded narration behind the existing zero-hallucination gate
- Live in-app navigation for the whole walk
- On-device taste profile; anonymous, consented usage telemetry (GDPR/CNIL-aware from day one — this telemetry is what trains the ranking over time, so it is designed in, not bolted on)
- Alternative routes; GPX export for bike computers

### Deferred, and announced as coming

- **Photo → taste profile (MiniCPM-V).** Point your camera at a place whose feeling you want more of, and the route reshapes around it. Held back deliberately: it gives the launch a second act, a reason to return to press and users a few weeks later, and a natural moment for a joint technical announcement with you.
- Community contributions, cities beyond Paris, accounts and sync, audio narration (MiniCPM-o), on-device inference.

---

## 5. The Gem Layer

**The problem.** Our hackathon build ranked 30,357 Paris places using a confidence score derived from OpenStreetMap tag richness. But a place hidden down an alley is, by definition, thinly documented — so the system penalised exactly the places we most want to surface. Every competitor has the same underlying map data; solving this is what makes WanderLust different from a navigation app with a mood slider.

A hidden gem is two independent things at once, and they need different machinery:

> **Gem = Character × Obscurity**
>
> High character + high fame = Notre-Dame. Not a gem.
> Low character + high obscurity = a parking garage. Not a gem.
> High character + low fame = a gem.

### Character — the model's job

"Is this place interesting?" is a semantic judgment, exactly what a small model is good at. One offline batch pass with MiniCPM5-1B over all 30,357 places, each given its name, category, tag set and street context, returning a constrained JSON character score plus a one-line rationale. Names alone carry enormous signal in Paris — *Librairie Jousseaume* and *Relay* are not the same kind of object, and a model can tell.

### Obscurity — emphatically not the model's job

"Is this place under-known?" is a factual question a 1B model would confidently hallucinate. We compute it classically:

- **Chain detection** — `brand`/`operator`/`wikidata` tags plus name frequency across the corpus (a name appearing forty times in Paris is a chain).
- **Fame signals** — Wikipedia/Wikidata links, `tourism=attraction`, heritage designations: interesting *and already famous* is what we route around, not toward.
- **Physical concealment** — pure geometry: road class of the nearest way, set-back from the street, position inside a *passage couvert* or interior *cour*, distance to the nearest tourist cluster.
- **OpenStreetMap editing metadata** — version count, last edit, contributor count from our existing Overpass queries at no extra cost. A place mapped once by one local years ago is strongly hidden; one edited forty times is under attention.

**A Paris-specific asset: Apur BDCOM.** The Paris urbanism agency publishes a field-surveyed census of every ground-floor commercial premises in Paris, openly licensed, with 2017/2020/2023 vintages. It tells us which real businesses OpenStreetMap never recorded (the gap where gems live), and an independent shop at the same address across all three vintages has survived a decade and a pandemic — an empirical proxy for "locally beloved" that exists nowhere else and cannot be gamed. As far as we can tell, nobody in this product category uses it.

### Validation — in public, not just against our own taste

The gem score is a ranking problem. We hand-label a held-out set of several hundred Paris places (ourselves plus a small group of local walkers) and measure with nDCG@k and precision@k, ablating each signal — directly our professional background in reranker evaluation. But scoring against our own labels only proves internal consistency, so the real test runs in public: every week we walk a route the gem layer generated, photograph it, and post it. If Parisians of ten years say they never knew a place existed, the ranker works. If the gems are mediocre, we learn it before the client is built.

### The flywheel

V1's consented telemetry collects implicit relevance signals: which suggested stops users accept versus route away from, which they save, and whether they lingered at a place. Over months this becomes training data for a learned reranker — the compounding asset, accumulating from the first user with no contribution platform and no moderation burden.

**Where your data support fits:** scaling the labelled evaluation set beyond what two people can annotate.

---

## 6. How we will judge it

Setting this down now so we are measured against the right numbers later.

- **Usage cadence.** This is a weekly/monthly product, not a daily one — the "spare fifteen minutes" moment occurs a few times a month for a typical user. We will report WAU/MAU, not DAU.
- **The metric that decides everything:** of users who complete one discovery route (actually walk it, confirmed by live position), what share complete a second within 30 days? Below ~20% the hypothesis fails regardless of ranking quality; above ~40% we scale.
- **Supporting numbers:** route-generation → route-completion conversion (are routes admired or walked?), saves per completed route, and destination mode versus loop mode split.

---

## 7. Technical approach

The routing core is built, tested and unchanged (65 tests passing). Work concentrates on the gem layer and the client.

**Routing.** Paris walk graph from OpenStreetMap (77k nodes, 221k edges). The detour is modelled as an Orienteering Problem — prize-collecting with fixed endpoints — solved with a budgeted greedy heuristic over a submodular reward, so route variety emerges from the objective rather than a hand-tuned penalty. Loop mode is the same solver with identical endpoints. SciPy multi-source Dijkstra keeps warm requests near one second.

**Models.** MiniCPM5-1B handles vibe interpretation, narration, and the offline character-scoring pass. The tiered fallback chain (MiniCPM → embedding interpreter → keyword net) from the hackathon build is preserved: the app degrades but never breaks.

**Client.** One cross-platform React Native codebase; iOS at launch, Android following from the same code. Hosted inference for V1; the on-device path comes later, on a working product rather than a prototype.

**Open question for your engineers: French.** Published MiniCPM benchmarks are English and Chinese. Paris means French place names, mood descriptions and signage. We plan a small French evaluation set early — see section 9, we think it is the most valuable joint artefact in this document.

---

## 8. Timeline

Both of us are employed full time; this is evenings and weekends. Approximate weeks so you can plan resource windows; a checkpoint with you every two to three weeks.

| Phase | Weeks | Work |
|---|---|---|
| **1** | 1–3 | Gem layer: data ingestion, obscurity signals, character pass, labelled eval set. API extracted from the Space. Weekly walked routes begin. |
| **2** | 3–7 | Cross-platform client, live in-app navigation, hosted inference. |
| **3** | 7–8 | Internal testing on real Paris routes; ranking tuned against the eval set and the public walks. |

**Target: a rough but working MVP in approximately eight weeks from kickoff.** A real app on real phones routing real people through Paris — not store-ready. Beta and public launch follow, scoped once we have seen how the MVP behaves.

---

## 9. Go-to-market

**One pre-launch motion.** A weekly Paris walk on Instagram — the route the gem layer generated, walked, photographed, with the story of what is on it. One platform, where Paris walking and photography culture actually lives. This is the same activity as our gem-layer validation, so it costs no extra evenings, and by launch it has accumulated a portfolio and a warm audience instead of a cold start. Email capture on a simple landing page.

**One launch channel: local creators.** Paris walking, photography and food accounts in the 10k–100k range. Each gets a bespoke route built for their audience; they post it. One post from a 50k account outperforms months of our own posting, the marginal cost of a route is nil, and cost-per-install and retention are measurable per creator. This is where a promotion budget converts to users most efficiently — see section 10.

**The structural channel: featured places.** Every independent café, bookshop and atelier we surface has its own audience and a direct commercial reason to share that it is on WanderLust — a card in the window, a story post. Our cheapest channel, aligned with the product's ethos, and structurally unavailable to a large incumbent.

**Timing.** We would rather launch to a moment than a date — Paris has natural walking moments, and given the eight-week MVP plus beta, the honest target is the spring walking season rather than something we would miss by construction. Worth aligning on a window together.

---

## 10. What we would need from you

Kept short and concrete.

**1. Inference credits — a specific allocation for a specific period.** Enough to cover the gem-layer batch pass plus roughly six months of MVP and beta traffic; we can size it precisely once you tell us the shape available. During the hackathon, ZeroGPU quota exhaustion repeatedly forced the app into template fallback, so this is a documented need, not a hypothetical one. We would prefer credits we spend on infrastructure we run rather than a hosted endpoint, so a consumer app's uptime does not depend on either side's best-effort infra.

**2. A joint French evaluation set for MiniCPM.** We think this is the most valuable thing in this document for you. Published MiniCPM benchmarks are English and Chinese; we can find no small-model French place-and-mood evaluation set anywhere. We will build one for our own needs regardless, and would rather build it properly and publish it with you — a genuine joint artefact, useful well beyond this app. Annotation support would make it substantially bigger than two people can produce.

**3. Promotion budget, deployed where it measurably converts.** Since you have offered a dedicated promotion budget, here is where we believe it works hardest: a capped creator-partnership pilot at launch with a handful of Paris accounts, run by us, with cost-per-install and 7-day retention reported back to you per creator. We would hold any spend beyond the pilot until the section-6 retention metric reads green — we would rather report real numbers than spend against a vanity metric. OpenBMB channel amplification we would plan at two moments: the public launch and the multimodal follow-up, agreeing channels and content nearer the time.

---

## Next

Happy to walk through this on a call. Most worth pressure-testing together: the gem-layer signal design, sizing the inference credits, and a realistic joint launch window.
