# WanderLust — Hackathon Submission Kit

Everything needed to lock in the submission. **Track: Thousand Token Wood.**
Space: https://huggingface.co/spaces/build-small-hackathon/WanderLust

---

## ✅ Mandatory checklist (Build Small Hackathon)

- [x] Gradio app, hosted as a Space under `build-small-hackathon`
- [x] ≤ 32B params (MiniCPM5-1B = 1B, + bge-small 33M ≈ **1.05B**)
- [ ] **Demo video** (script below) — *you record + upload*
- [ ] **Social post** (draft below) — *you post + link*
- [ ] **Set Space variable `DISCOVERROUTE_OFFLINE=1`** (Settings → Variables) — required
      for the Off the Grid badge (no cloud APIs at request time)
- [ ] Submit on the hackathon page: Space link + video URL + social link + track + badges

## 🏅 Badges we claim (and why)

| Badge | Basis |
|---|---|
| **Off the Grid** | With `DISCOVERROUTE_OFFLINE=1`, zero cloud APIs at request time — all 4 cities pre-baked + local geocoding |
| **Off-Brand** | Hand-built `gr.Server` HTML/CSS/JS app-shell, zero default Gradio components |
| **Tiny Titan** (special, ≤4B) | MiniCPM5-1B, 1B params, in-Space on ZeroGPU |
| **Field Notes** | Publish `FIELD_NOTES.md` / `PROGRESS.md` as a post, then link it |
| **openbmb** (sponsor) | Core reasoning model is OpenBMB's MiniCPM5-1B |

---

## 🎬 Demo video script (~90 seconds)

> Screen-record the live Space. Keep it tight.

1. **(0:00–0:10) Hook.** "Most map apps ask: what's the fastest way there? WanderLust
   asks: what if those extra minutes were a gift?"
2. **(0:10–0:35) One plan, Paris.** Start "Place de la République", destination
   "Jardin du Luxembourg". Type the vibe **"bookshops and quiet streets"**. Hit Plan.
   Show the discovery route drawn vs. the plain route, the time it costs, and read one
   line of the grounded itinerary ("…why each stop is on your path").
3. **(0:35–0:55) It read your mood.** Open the interpretation panel — show the vibe
   mapped to category weights. Change the vibe to **"lively café crawl"**, re-plan, show
   a different route. "Same A to B. A walk that matches you."
4. **(0:55–1:15) Multi-city, offline.** Change to **"British Museum, London" →
   "Covent Garden, London"**, vibe "cozy bookshops and coffee". Show it routing London.
   Say: "Paris, London, Barcelona, New York — all routed **fully offline**, no cloud
   APIs, on a **1-billion-parameter** model running in the Space."
5. **(1:15–1:30) Close.** "WanderLust. Small model, big city, your taste. Built for the
   Build Small Hackathon." Show the Space URL.

**Tips:** pre-warm each city once before recording (first-load builds the index).
Record at desktop width so the map + panel both show.

---

## 📣 Social post (draft — Thousand Token Wood)

> Trim to platform length; attach a 10–15s clip or the route screenshot.

```
🗺️ Meet WanderLust — it turns any walk from A to B into a personal discovery.

Tell it your destination and your *mood* ("bookshops and quiet streets", "a lively
café crawl") and it threads you past the places you'll actually love — then tells you,
in your own words, why each one is on your path. Same destination, a walk you'll remember.

✨ A 1B-parameter model (MiniCPM5-1B) reads your vibe → routing weights → grounded itinerary
🌍 Paris · London · Barcelona · New York — all routed FULLY OFFLINE, no cloud APIs
🎨 Hand-built custom frontend (gr.Server), zero default Gradio components

Small model. Big city. Your taste.

Built for @huggingface #BuildSmallHackathon (Thousand Token Wood) on @OpenStreetMap data
with @OpenBMB's MiniCPM.

Try it 👉 [Space link]
```

---

## 📝 Field Notes (badge) — quickest path

`FIELD_NOTES.md` + `PROGRESS.md` already tell the build story. To claim the badge:
publish one as a short post (HF blog / Dev.to / Medium) titled e.g.
*"Taste-aware city routing on a 1B model — building WanderLust for the Build Small
Hackathon"*, then add the link under **🔗 Links** in `README.md`.
