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
- Route-quality filtering — DONE. Wider explorer routes must be positive six-GW upgrades, budget-valid and club-limit valid before being shown.
- Diverse alternatives — DONE. Explorer avoids repeatedly showing the same incoming/outgoing combination where credible alternatives exist.
- Why this route over the alternatives — DONE. The preferred route now explains its decisive lower-variance, leverage, ownership and outgoing-player advantages against the next-best routes.
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
- Selected transfer outcome is explicit — DONE via pick-team-transfer-outcome-stage25.js. Pick Team states whether the incoming player STARTS or is BENCHED this gameweek and, when benched, surfaces the relevant comparative rationale rather than silently placing YOUR IN on the bench.
- Shield / Neutral / Leverage interpretation and league impact — DONE.
- Selection rationale for marginal starters and bench decisions — DONE in safe-pick-team-pitch-stage18.js. The UI explains every bench call against the weakest selected same-position player using comparative XI score, immediate fixture, availability/minutes, underlying model score and recent form where relevant.
- Captain / vice rationale — DONE in safe-pick-team-pitch-stage18.js. The UI explains the armband and fallback using the same combined XI score plus fixture, availability, form and PPG context.

## Squad Shape / Forward Planning

- Position spend, bench value, club concentration, availability flags — DONE.
- Selected working transfer is projected into squad structure and bank — DONE.
- Multi-GW strategic fixture outlook — DONE.
- Six-GW fixture-cliff view — DONE via gap-parity-stage26.js.
- Fine / Watch / Plan statuses — DONE.
- Easy/tough fixture stacking — DONE.
- Self-cancelling fixture count — DONE.
- Decision timeline — DONE. Each visible gameweek now maps fixture stress to SET TEAM, BENCH / CAPTAINCY CHECK or TRANSFER PLAN.
- Connected forward-planning rationale — DONE. The UI distinguishes isolated difficult weeks from repeated squad-structure stress and explains when chip value should be reassessed.
- Chip window evaluation and future-window comparison — DONE.

## Player Pool

- Lazy loading — DONE.
- Model, fixtures, minutes/availability, value, Scout and Market signals — DONE.
- Positivity / overall score with semantic treatment — DONE.
- Rich evidence breakdown — DONE via gap-parity-stage26.js. Factor bars expose model, fixtures, minutes, value and EO rather than relying on one opaque combined score.
- Decision profile labels — DONE: START NOW, MEDIUM-TERM, DIFFERENTIAL, VALUE, WATCH and MINUTES RISK.
- Current squad marking — DONE.
- Selected transfer labelled YOUR IN / YOUR OUT — DONE.
- Search — DONE via gap-parity-stage26.js.
- Position filter / same-position comparison — DONE.
- Sorting by overall/model/fixtures/value/EO/price — DONE.
- Ownership / EO and Shield-Neutral-Leverage role — DONE.
- Rise / Fall / timing watch — DONE.
- Bounded mobile DOM — DONE intentionally for Safari stability.

## League Intel

- Standings and nearest target — DONE.
- Threats, shields/leverage context — DONE.
- Squad overlap — DONE.
- Manager ownership matrix — DONE, capped for mobile.
- Recent rank/points trend — DONE, capped parallel history load.
- Exposure heatmap — DONE, compact top-20 implementation.
- EO strategy posture and canonical role thresholds — DONE.
- Squad-style / variance score — DONE via gap-parity-stage26.js.
- Target-rival uniqueness — DONE. League Intel identifies useful differences, shared shields and rival threats you do not own.
- Direct answer to how to play the rival — DONE. Posture adapts between PROTECT, BALANCED, CONTROLLED CHASE and CHASE using the current gap and season stage, with an explicit rule not to sell a strong shared shield merely to be different.
- Selected working transfer is included in the effective squad used for rival strategy and variance calculations — DONE.
- Full old all-player/all-GW heatmap — RETIRED intentionally; bounded equivalent is used.

## Decision Journal / Saved State

- Read prior saved plan safely — DONE.
- Distinguish current working choice from confirmed historical decisions — DONE.
- Show confirmed decision history — DONE.
- Journal summaries only call a transfer confirmed when a confirmed transfer actually exists — DONE in safe-journal-stage8.js; zero confirmed transfers are no longer rendered as misleading text such as `GW10 confirmed`.
- Preserve prior model context where captured — DONE.
- Route selection persists across refresh — DONE.
- One-way safe UI refresh after an explicit user route choice — DONE using fplSafePlanUpdated; listeners render only and do not write.
- Automatic background localStorage writes/events/observer-driven rerenders — RETIRED intentionally.

## Architecture / UX

- Five primary tabs: Transfer, Pick Team, Squad Shape, Player Pool, League Intel — DONE.
- A chosen transfer becomes the effective working squad across all five views — DONE.
- Compact global plan status shows the current route or Roll without repeating a full banner on every view — DONE via production-cohesion-stage23.js.
- Production cards, Decision Lens and selected-player treatment share one visual language — DONE via production-cohesion-stage23.css.
- Core dashboard remains lightweight on first paint — DONE.
- Wider transfer explorer only loads Player Pool after explicit user request — DONE.
- Transfer Decision Lens defers heavy Market data until the Transfer tab is actively revisited — DONE.
- Plan projection no longer fetches latest data on startup when there is no working transfer — DONE.
- Duplicate safe-feature-completion-stage21.js production loader — RETIRED. Its required outcomes are now supplied by gap-parity-stage26.js, removing one duplicate Pool/Market fetch path.
- Pick Team only loads Player Pool when the selected incoming player is not already hydrated from the current squad snapshot — DONE.
- Bounded post-render stabilisation is used for lazy legacy panels — DONE via post-render-stabilizer-stage27.js; no observer or recurring loop is used.
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
- duplicate Stage 21 secondary-data loader

## Definition of done

Gap recovery is complete when every decision-support outcome above is available in production with the stable architecture. At this point the remaining work is enhancement and visual/product polish rather than recovery of missing Decision Centre capability.