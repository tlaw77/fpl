# FPL Decision Centre — Requirements Reconciliation

This file is the production source-of-truth for the recovered Decision Centre after the iPhone Safari stability incident.

## Non-negotiable constraints

- Mobile/iPhone Safari stability and fast first paint take priority over restoring old implementation patterns.
- Current player, club, price and squad data must come from the latest generated FPL datasets; do not hard-code stale football facts.
- Semantic colours: green = favourable, amber = mixed/watch, red = weak/risk, blue/slate = neutral/context.
- Heavy secondary datasets must be lazy-loaded after the user opens the relevant tab.
- Do not reintroduce self-triggering MutationObservers, automatic localStorage backfills, or recursive plan-change event loops.
- Saved plan writes must be explicit user actions only.

## Transfer

- Core preferred transfer recommendation — DONE.
- Lower-variance and leverage uplift — DONE.
- Rival ownership context — DONE.
- Scout/news corroboration — DONE.
- Market direction / transfer pressure — DONE.
- Availability/minutes evidence — DONE.
- Side-by-side route alternatives — DONE via safe-transfer-routes-stage17.js.
- Working-plan save/clear — DONE; explicit button press only.
- Decision Journal with historical recommendation context — DONE, read-only render.
- Automatic uplift_snapshot persistence/backfill — RETIRED intentionally because it contributed to unstable state/event behaviour. Equivalent evidence is rendered directly from current/history data instead.

## Pick Team

- Recommended legal XI from next-GW squad data — DONE.
- Formation, captain, vice-captain and bench order — DONE.
- Uses decision score, fixture ease, availability, form and PPG — DONE.
- Rich pitch-style presentation — OPTIONAL VISUAL ENHANCEMENT; logic is present, old heavy pitch implementation is not required for decision correctness.
- Explainable rationale — DONE at summary/player-fixture level; can be expanded without changing selection logic.

## Squad Shape / Forward Planning

- Position spend, bench value, club concentration, availability flags — DONE.
- Multi-GW strategic fixture outlook — DONE via safe-requirements-stage16.js.
- Working-plan-aware forward squad IDs — DONE without background writes.
- Chip window evaluation and future-window comparison — DONE via safe-requirements-stage16.js using data/chip_window.json.

## Player Pool

- Lazy loading — DONE.
- Model, fixtures, minutes/availability, value, Scout and Market signals — DONE.
- Positivity score with semantic green/amber/red treatment — DONE.
- Current squad marking — DONE.
- Bounded mobile DOM (top 40) — DONE intentionally for Safari stability.
- Historical full dynamic strategic-outlook injection from player-pool.js — RETIRED; strategic outlook is restored independently and safely.

## League Intel

- Standings and nearest target — DONE.
- Threats, shields/leverage context — DONE.
- Squad overlap — DONE.
- Manager ownership matrix — DONE, capped for mobile.
- Recent rank/points trend — DONE, capped parallel history load.
- Exposure heatmap — DONE, compact top-20 implementation.
- EO strategy posture and canonical role thresholds — DONE via safe-requirements-stage16.js.
- Full old all-player/all-GW heatmap — RETIRED intentionally; bounded equivalent is used.

## Decision Journal / Saved State

- Read prior saved plan safely — DONE.
- Show pending/confirmed decision history — DONE.
- Preserve prior model context where captured — DONE.
- Explicit save and clear controls — DONE.
- Automatic localStorage writes/events/observer-driven rerenders — RETIRED intentionally.

## Architecture / UX

- Five primary tabs: Transfer, Pick Team, Squad Shape, Player Pool, League Intel — DONE.
- Core dashboard one lightweight snapshot request first — DONE.
- Scout/Market/Pool/Intel/history secondary work lazy or bounded — DONE.
- No MutationObserver in the recovered production path — DONE.
- No fplPlanChanged event loop in the recovered production path — DONE.
- No transfer-uplift persistence loop — DONE.
- Recovery/stage diagnostic wording removed from production UI — DONE.

## Definition of done

A requirement is considered complete when its decision-support outcome is available in the production UI with the stable architecture. Old implementation mechanisms are not requirements when an equivalent safer implementation exists.