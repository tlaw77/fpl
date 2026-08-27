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
- Hold / roll decision lens — DONE via safe-transfer-decision-depth-stage22.js.
- Hold / roll is a selectable working choice that clears the planned transfer and projects the current squad across all views — DONE.
- Rival ownership context — DONE.
- Scout/news corroboration — DONE.
- Market direction / transfer pressure — DONE.
- Availability/minutes evidence — DONE.
- Side-by-side route alternatives across different outgoing/incoming players — DONE via safe-transfer-routes-stage17.js.
- Explicit route picking from the comparison list — DONE.
- Selected route clearly marked as Your choice — DONE.
- Consequence / urgency context — DONE via safe-transfer-decision-depth-stage22.js.
- Decision Journal with historical recommendation context — DONE.
- Automatic uplift_snapshot persistence/backfill — RETIRED intentionally because equivalent evidence is rendered directly and the old persistence mechanism was unsafe.

## Pick Team

- Recommended legal XI from next-GW squad data — DONE.
- Formation, captain, vice-captain and bench order — DONE.
- Uses decision score, fixture ease, availability, form and PPG — DONE.
- Rich pitch-style presentation — DONE via safe-pick-team-pitch-stage18.js.
- Selected working transfer is applied before XI/bench/bank calculations — DONE.
- Incoming working-plan player is visibly marked — DONE.
- Shield / Neutral / Leverage interpretation and league impact — DONE.
- Selection rationale for marginal starters and bench decisions — PENDING. The UI must explain why a player is omitted or started (for example why Maguire is left out), using the actual comparative factors that drove the XI: decision score, fixture quality, availability/minutes, form/PPG, formation constraints and the competing player's edge.
- Captain / vice rationale — PENDING. Explain the main factors behind the armband recommendation rather than only showing C / VC.

## Squad Shape / Forward Planning

- Position spend, bench value, club concentration, availability flags — DONE.
- Selected working transfer is projected into squad structure and bank — DONE.
- Multi-GW strategic fixture outlook — DONE.
- Six-GW fixture-cliff view — DONE via safe-feature-completion-stage21.js.
- Fine / Watch / Plan statuses — DONE.
- Easy/tough fixture stacking — DONE.
- Self-cancelling fixture count — DONE.
- Chip window evaluation and future-window comparison — DONE.

## Player Pool

- Lazy loading — DONE.
- Model, fixtures, minutes/availability, value, Scout and Market signals — DONE.
- Positivity / overall score with semantic treatment — DONE.
- Current squad marking — DONE.
- Selected transfer labelled YOUR IN / YOUR OUT — DONE.
- Search — DONE via safe-feature-completion-stage21.js.
- Position filter / same-position comparison — DONE.
- Sorting by overall/model/fixtures/value/EO/price — DONE.
- Ownership / EO and Shield-Neutral-Leverage role — DONE.
- Rise / Fall Watch — DONE.
- Bounded mobile DOM — DONE intentionally for Safari stability.

## League Intel

- Standings and nearest target — DONE.
- Threats, shields/leverage context — DONE.
- Squad overlap — DONE.
- Manager ownership matrix — DONE, capped for mobile.
- Recent rank/points trend — DONE, capped parallel history load.
- Exposure heatmap — DONE, compact top-20 implementation.
- EO strategy posture and canonical role thresholds — DONE.
- Squad-style / variance score — DONE via safe-feature-completion-stage21.js.
- Selected working transfer visibly carried into League Intel — DONE.
- Full old all-player/all-GW heatmap — RETIRED intentionally; bounded equivalent is used.

## Decision Journal / Saved State

- Read prior saved plan safely — DONE.
- Distinguish current working choice from confirmed historical decisions — DONE.
- Show confirmed decision history — DONE.
- Preserve prior model context where captured — DONE.
- Route selection persists across refresh — DONE.
- One-way safe UI refresh after an explicit user route choice — DONE using fplSafePlanUpdated; listeners render only and do not write.
- Automatic background localStorage writes/events/observer-driven rerenders — RETIRED intentionally.

## Architecture / UX

- Five primary tabs: Transfer, Pick Team, Squad Shape, Player Pool, League Intel — DONE.
- A chosen transfer becomes the effective working squad across all five views — DONE.
- Compact global plan status shows the current route or Roll without repeating a full banner on every view — DONE via production-cohesion-stage23.js.
- Production cards, Decision Lens and selected-player treatment share one visual language — DONE via production-cohesion-stage23.css.
- Core dashboard one lightweight snapshot request first — DONE.
- Scout/Market/Pool/Intel/history secondary work lazy or bounded — DONE.
- No MutationObserver in the recovered production path — DONE.
- No recursive fplPlanChanged event loop in the recovered production path — DONE.
- No transfer-uplift persistence loop — DONE.
- Recovery/stage diagnostic wording removed from production UI — DONE.

## Deliberately retired implementation details

These are not missing user requirements; they are old implementation mechanisms replaced by safer equivalents:

- self-triggering MutationObservers
- automatic localStorage backfills
- recursive fplPlanChanged event propagation
- unbounded full-season / all-player rendering on first load
- transfer-uplift persistence loop

## Definition of done

A requirement is complete when its decision-support outcome is available in the production UI with the stable architecture. Old mechanisms are not requirements where a safer equivalent now exists.