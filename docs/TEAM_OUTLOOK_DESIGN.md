# Team & Outlook — simulation presentation design

Updated: 2026-08-30

## Product intent

Simulation is decision-support machinery, not a competing recommendation surface. The primary navigation remains focused on FPL decisions. `Pick Team` contains two modes:

- **This GW** — operational starting XI, bench order, captain/vice, Triple Captain prompt and selection rationale.
- **Outlook** — periodically inspected forward simulation, future branches, stability, chip opportunities and Wildcard/Free Hit squad construction.

The authoritative weekly action remains the decision synthesis used in Transfer/GW Decision. Outlook explains where the squad may be heading and what could change the decision.

The presentation rule across the app is: **What should I do? → Why? → How sure are we? → Technical detail if useful.** Internal terms such as action gates, measured leaders and persistence should not be the primary user-facing language.

## Presentation hierarchy

Outlook presents, in order:

1. **Squad Outlook** — current synthesized action, confidence, FT/hit state, deep-model freshness and season-evidence maturity.
2. **What could happen next?** — the leading provisional multi-GW sequence. Future moves are branches, not commitments.
3. **How strong is the advice?** — cross-model support and the magnitude hurdle required before an additional transfer is promoted.
4. **Has the advice changed?** — weighted action stability, recurring alternative transfer and recurring chip windows across recent completed model runs.
5. **Chip Outlook** — WC/FH/BB/TC opportunity scouts, with first-half portfolio pressure and hard deployment inflection.
6. **Chip decision gate** — translates opportunity signals into HOLD / WATCH / CONSIDER using structure, maturity, stability, schedule context, budget confidence and dedicated chip reviews.
7. **Wildcard Lab** — when a generated WC candidate exists, show it through the same football-pitch template as Pick Team. The user can tap through each projected Gameweek XI/bench under the same WC squad.

## Wildcard and Free Hit budget safety

Public FPL picks do not currently expose selling prices, so budget confidence has three explicit tiers:

- **exact** — direct FPL selling prices are available;
- **reconstructed** — purchase prices are rebuilt from the archived GW1 squad plus public transfer transaction costs, then FPL's half-profit selling-price rule is applied;
- **estimated** — current market value is used only as a fallback planning proxy.

`budget_state.py` now reconstructs all 15 current selling prices when possible. A newly declared transfer that has not yet appeared in the public transaction endpoint is temporarily assigned its current acquisition price and listed explicitly as pending-history basis. This keeps the calculation auditable.

The GW1 archive is the earliest available ownership-price baseline, not a guaranteed pre-season purchase ledger. Therefore reconstructed budget is deliberately **not** labelled exact. A large remaining-bank buffer can make a proposed WC/FH robust to small baseline errors, but does not upgrade the confidence label.

Roster structure, position quotas and max-three-per-club legality remain exact. The full-squad optimiser records budget method and confidence alongside every result.

A large modelled uplift is not an activation recommendation. The chip gate considers:

- spendable-budget confidence and remaining buffer;
- season maturity;
- squad turnover required;
- stability evidence;
- current squad structural weakness;
- visible blank/double disruption;
- half-season chip expiry pressure;
- modelled uplift only as one input rather than the verdict.

Current early-season guardrail: a healthy squad with comfortable chip slack should not be Wildcarded merely because a noisy early-season optimiser can invent a very different squad.

## Triple Captain relationship to captaincy

Captaincy and Triple Captain are adjacent but distinct decisions:

- **Captaincy** asks: who is the best player to captain this Gameweek?
- **Triple Captain** asks: is this captain opportunity exceptional enough to spend a scarce chip now rather than preserve it?

`captaincy_review.py` owns the C/V recommendation used by the pitch and rationale. `triple_captain_review.py` performs an owned-squad-first opportunity scan across the visible horizon. The unified chip gate consumes the dedicated TC review rather than relying only on a generic transfer-path captain.

This prevents contradictory states such as a detailed TC review saying **CONSIDER Haaland v Coventry** while the compact Chip Outlook says TC HOLD.

## Compute strategy

Use three speeds rather than recomputing every expensive permutation on every page visit.

### 1. Light refresh
Runs with normal ETL. Rebuild squad/FT state, availability, market/scout signals and the immediate decision.

### 2. Deep simulation snapshot
Multi-GW paths, adaptive rivals, TC/BB paths and bounded WC/FH squad construction. Persist results to JSON. Full-squad chip search uses input-aware caching.

The deep-cache signature includes:

- Gameweek;
- current squad and prices;
- bank/spendable-budget state and budget method;
- production search profile;
- a quantized player-model fingerprint using six-GW model strength, adjusted availability, price and schedule-risk class.

Quantization is intentional: tiny numerical noise should not force an expensive rebuild, while a meaningful football-input change should.

### 3. Deadline intensity
Future enhancement: increase simulation depth/frequency near the deadline and after material events such as injury/news, declared/completed transfers, important budget changes or schedule changes.

The web UI reads the latest completed snapshot and never waits for deep simulation to finish.

## Deep simulation freshness

Implemented in the full-squad optimiser metadata and `docs/team-outlook-freshness-stage63.js`.

The deep output records:

- `input_signature`;
- `model_fingerprint`;
- `cache_state` (`HIT` or `MISS`);
- `cache_last_checked_at_utc`;
- original deep-build timestamp.

Outlook translates this into:

- **CURRENT · rebuilt** — the deep search was run for the current signature;
- **CURRENT · cached** — the signature was rechecked and the existing deep result remains valid;
- **REBUILD NEEDED** — the deep result has not been successfully revalidated recently.

When a rebuild is needed, the live/light weekly decision can still be shown, but long-horizon paths and chip squads are visibly treated as stale.

## Stability over time

Implemented via `simulation_stability.py` and a small independent post-ETL workflow. It keeps a bounded rolling history of simulation summaries instead of making the heavy ETL itself longer.

Current derived signals include:

- current-action stability over recent runs;
- recurring best alternative transfer;
- recurring first route from the multi-GW planner;
- frequency with which an alternative was strong enough to act on;
- recurring Free Hit window;
- average confidence and edge over hold;
- current Wildcard opportunity level;
- latest deep-simulation timestamp/signature.

Materially identical snapshots inside 20 minutes are deduplicated. Stability is also **input weighted**:

- changed deep-input signature or changed decision state = **1.0 evidence**;
- unchanged-input/cached refresh = **0.25 evidence**.

This reduces false confidence from seeing the same cached model answer repeatedly. Stability remains model consistency, not independent statistical proof.

## Chip activation gate

Implemented via `chip_activation_gate.py` in the lightweight supplemental workflow.

Execution order is deliberately:

1. update simulation stability;
2. build the dedicated owned-squad Triple Captain review;
3. build the unified chip activation gate;
4. build captaincy review;
5. evaluate archived performance.

Statuses:

- **HOLD** — no activation case.
- **WATCH** — a potentially valuable future window exists, but an activation condition is missing.
- **CONSIDER** — enough conditions have cleared to warrant an explicit decision now. It is not automatic activation.

The gate is intentionally stricter than raw simulation. For example, a Free Hit can show a positive modelled uplift but remain WATCH while there is no confirmed blank/double disruption. Wildcard can remain HOLD despite a large modelled uplift when season evidence is immature and the current squad is healthy. Triple Captain uses the dedicated owned-player review so a genuine premium home-fixture spike can reach CONSIDER even when general portfolio pressure is comfortable.

## Durable learning archive

`archive_week.py` preserves the simulation decision artifacts at Gameweek rollover in addition to the original dashboard/history files:

- single-step Monte Carlo simulation;
- multi-GW path simulation;
- adaptive-rival simulation;
- TC/BB path simulation;
- full-squad WC/FH optimiser;
- budget state;
- authoritative decision synthesis;
- simulation stability history;
- chip activation gate;
- dedicated Triple Captain review;
- dedicated captaincy review.

This archive records what the engine believed **at the time**, rather than reconstructing the recommendation after the result is known.

## Backtesting contract

`backtest_engine.py` now provides the first evaluation scaffold and writes `data/backtest_summary.json`.

Version 1 pairs a pre-Gameweek archived captaincy/TC review with the following finalized Gameweek outcome and calculates:

- recommended captain actual return;
- forecast error;
- best actual return among the model's shortlisted captain alternatives;
- captain regret versus that shortlist;
- whether the recommended captain was actually the best shortlisted choice;
- TC candidate actual return and the hypothetical extra points that Triple Captain would have added over normal captaincy.

The evaluator is deliberately sparse-data safe. Until a pre-GW review and its following finalized Gameweek both exist, it reports **not enough completed evidence yet** rather than manufacturing a success rate.

No backtest UI should be promoted yet. A compact **Engine track record** view should only be considered after several evaluable Gameweeks exist; early percentages must be labelled descriptive, not statistically calibrated.

Future backtesting layers:

- transfer route versus hold and shortlisted alternatives;
- mini-league rank/gap outcome;
- calibration of Monte Carlo rank/gain probabilities;
- chip counterfactuals;
- forecast calibration by position and horizon;
- captain confidence calibration.

## Current implementation

Frontend assets include:

- `docs/team-outlook-stage61.js`
- `docs/team-outlook-stage61.css`
- `docs/team-outlook-chip-gate-stage62.js`
- `docs/team-outlook-freshness-stage63.js`
- `docs/team-outlook-tc-stage64.js`
- `docs/captaincy-review-stage65.js`

Backend/history assets include:

- `budget_state.py`
- `simulation_stability.py`
- `chip_activation_gate.py`
- `triple_captain_review.py`
- `captaincy_review.py`
- `backtest_engine.py`
- `.github/workflows/simulation-stability.yml`
- `data/budget_state.json`
- `data/simulation_stability.json`
- `data/chip_activation_gate.json`
- `data/triple_captain_review.json`
- `data/captaincy_review.json`
- `data/backtest_summary.json`

The browser reads simulation data from the repository raw-data endpoint with cache-busting rather than assuming `/data` is deployed beside `/docs` on GitHub Pages.

## Progress log

### 2026-08-29 — Outlook foundation

- Added `This GW | Outlook` inside Pick Team.
- Added current decision, forward path, robustness, stability, chip outlook and Wildcard Lab.
- Reused the existing Pick Team pitch language for the potential Wildcard XI and bench.
- Added six-GW tap-through Wildcard XI/bench previews.
- Hardened Outlook against Pick Team re-renders and Safari caching.

### 2026-08-29 — simulation safety

- Weighted stability by material input change.
- Added WC/FH bounded full-squad optimisation and input-aware deep caching.
- Added current-squad overlap and WC turnover display.
- Added chip HOLD / WATCH / CONSIDER semantics.
- Extended Gameweek archival to preserve the simulation stack.
- Added material player-model fingerprint and CURRENT / CACHED / REBUILD NEEDED deep-model presentation.

### 2026-08-29 — captaincy and chip integration

- Separated captaincy from XI selection.
- Made the pitch C/V markers use the same captaincy result as the rationale.
- Added dedicated owned-squad Triple Captain review.
- Integrated the immediate TC question beside captaincy while retaining the full future comparison in Outlook.

### 2026-08-30 — budget reconstruction and learning scaffold

- Reconstructed 15-player selling budget from archived ownership/purchase history plus public transfer costs and FPL sell-price rules.
- Added explicit `exact / reconstructed / estimated` budget confidence tiers.
- Kept declared/pending purchases auditable until the public transfer endpoint catches up.
- Updated WC/FH optimiser legality wording to distinguish reconstructed budget from market-value proxy.
- Unified the chip gate with the dedicated Triple Captain review.
- Added captaincy/TC reviews to durable Gameweek archival.
- Added `backtest_engine.py`; current output correctly reports zero evaluable Gameweeks until enough finalized evidence exists.

## Next planned iterations

1. Validate the unified chip gate after the latest supplemental workflow and keep TC/WC/FH wording consistent in This GW and Outlook.
2. Extend the backtester to transfer-versus-hold outcomes once adjacent archived decision snapshots exist.
3. Add probability calibration only after enough completed observations exist; do not tune to one or two Gameweeks.
4. Add compact rival-consequence details without duplicating League Intel.
5. Add deadline-aware simulation intensity once normal background refresh costs are measured over several cycles.
6. Continue mobile Safari refinement from real screenshots rather than hypothetical desktop layouts.
