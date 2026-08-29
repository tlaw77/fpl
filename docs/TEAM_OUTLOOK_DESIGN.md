# Team & Outlook — simulation presentation design

Updated: 2026-08-29

## Product intent

Simulation is decision-support machinery, not a competing recommendation surface. The primary navigation remains focused on FPL decisions. `Pick Team` contains two modes:

- **This GW** — operational starting XI, bench order, captain/vice and selection rationale.
- **Outlook** — periodically inspected forward simulation, robustness, intervention paths and chip opportunity scouts.

The authoritative weekly action remains the decision synthesis used in Transfer/GW Decision. Outlook explains where the squad may be heading and what could change the decision.

## Presentation hierarchy

Outlook presents, in order:

1. **Squad Outlook** — current synthesized action, confidence, FT/hit state, model age and season-evidence maturity.
2. **Forward Path** — the leading provisional multi-GW sequence. Future moves are explicitly branches, not commitments.
3. **Model Robustness** — cross-model support and the magnitude hurdle required before an additional transfer is promoted.
4. **Plan Stability** — weighted action persistence, current leader persistence, recurring future route and recurring chip window across recent completed model runs.
5. **Chip Radar** — WC/FH/BB/TC as opportunity scouts, with first-half portfolio pressure and hard deployment inflection.
6. **Chip Activation Gate** — translates raw chip opportunities into HOLD / WATCH / CONSIDER using structure, maturity, stability, blank/double context, budget confidence and calendar pressure.
7. **Wildcard Lab** — when a generated WC candidate exists, show it through the same football-pitch template as Pick Team. The user can tap through each projected Gameweek XI/bench under the same WC squad.

## Wildcard safety

The Wildcard optimiser currently has exact position and max-three-per-club legality, but public FPL picks do not expose exact selling prices. Until exact spendable budget can be reconstructed, the budget is labelled `estimated` and Wildcard/Free Hit outputs remain provisional.

A large raw simulated uplift is not an activation recommendation. The implemented chip gate considers:

- exact/credible spendable budget;
- season maturity;
- squad turnover required;
- stability evidence;
- current squad structural weakness;
- visible blank/double disruption;
- half-season chip expiry pressure;
- raw simulated uplift only as one input rather than the verdict.

Current example: the raw WC optimiser shows a large six-GW uplift, but the gate remains HOLD because the budget is estimated, only 25% season-maturity weight is available, the current structural check has no broken assets, the rebuild changes 11/15 players, stability evidence is still thin, and first-half calendar pressure is comfortable.

## Compute strategy

Use three speeds rather than recomputing every expensive permutation on every page visit:

### 1. Light refresh
Runs with normal ETL. Rebuild squad/FT state, availability, market/scout signals and the immediate decision.

### 2. Deep simulation snapshot
Multi-GW paths, adaptive rivals, TC/BB paths and bounded WC/FH squad construction. Persist results to JSON. Full-squad chip search uses input-aware caching and is invalidated when GW, squad or budget changes.

### 3. Deadline intensity
Future enhancement: increase simulation depth/frequency near the deadline and after material events (injury/news, declared/completed transfer, major price/budget change, schedule change).

The web UI reads the latest completed snapshot and never waits for deep simulation to finish.

## Stability over time

Implemented via `simulation_stability.py` and a small independent post-ETL workflow. It keeps a bounded rolling history of simulation summaries instead of making the heavy ETL itself longer.

Current derived signals include:

- action persistence over recent runs;
- current transfer-leader persistence;
- recurring first route from the multi-GW planner;
- transfer-gate clear frequency;
- recurring Free Hit window;
- average confidence and edge over hold;
- current Wildcard raw opportunity level;
- latest deep-simulation timestamp/signature.

Materially identical snapshots inside 20 minutes are deduplicated. Stability is also **input weighted**:

- changed deep-input signature or changed decision state = **1.0 evidence**;
- unchanged-input/cached refresh = **0.25 evidence**.

This reduces false confidence from seeing the same cached model answer repeatedly. Persistence remains model stability, not independent statistical proof.

## Chip activation gate

Implemented via `chip_activation_gate.py` and run after stability history in the lightweight supplemental workflow.

Statuses:

- **HOLD** — no activation case.
- **WATCH** — a potentially valuable future window exists, but an activation condition is missing.
- **CONSIDER** — enough of the activation conditions have cleared to warrant an explicit decision review.

The gate is intentionally stricter than raw simulation. For example, a Free Hit can show a positive modelled uplift but remain WATCH while there is no confirmed blank/double disruption.

## Current implementation

Frontend assets:

- `docs/team-outlook-stage61.js`
- `docs/team-outlook-stage61.css`
- `docs/team-outlook-chip-gate-stage62.js`

Backend/history assets:

- `simulation_stability.py`
- `chip_activation_gate.py`
- `.github/workflows/simulation-stability.yml`
- `data/simulation_stability.json`
- `data/chip_activation_gate.json`

Data consumed by Outlook:

- `data/decision_synthesis.json`
- `data/path_simulation.json`
- `data/full_squad_chip_optimizer.json`
- `data/simulation_stability.json`
- `data/chip_activation_gate.json`

The browser reads these from the repository raw-data endpoint with cache-busting rather than assuming `/data` is deployed beside `/docs` on GitHub Pages.

The Stage61 view is additive: it wraps the existing Pick Team rendering rather than replacing the proven pitch renderer. A MutationObserver re-attaches the Team/Outlook shell after any later Pick Team redraw, preserving the selected Team/Outlook mode.

## Durable learning archive

`archive_week.py` now preserves the simulation decision artifacts at Gameweek rollover in addition to the original dashboard/history files:

- single-step Monte Carlo simulation;
- multi-GW path simulation;
- adaptive-rival simulation;
- TC/BB path simulation;
- full-squad WC/FH optimiser;
- budget state;
- authoritative decision synthesis;
- simulation stability history;
- chip activation gate.

This archive is intended to support future backtesting: what the engine recommended, what alternatives it believed were credible, how confident/stable those beliefs were, and what subsequently happened.

## Progress log

### 2026-08-29 — Stage61 initial

- Added `This GW | Outlook` inside Pick Team.
- Added Squad Outlook, Forward Path, Model Robustness, Chip Radar and Wildcard Lab.
- Reused the existing Pick Team pitch language for the potential Wildcard XI and bench.
- Kept WC/FH provisional while spendable budget remains estimated.

### 2026-08-29 — Stage61 stability iteration

- Added post-ETL simulation stability history without lengthening the main FPL ETL.
- First stability snapshot completed successfully.
- Added Plan Stability presentation to Outlook.
- Forward Path now reads the leading multi-GW action sequence rather than only the first future action.
- Hardened Stage61 against Pick Team re-renders.
- Corrected Outlook data sources to the same raw-GitHub pattern used by the core dashboard.
- Cache-busted Stage61 for iPhone Safari.

### 2026-08-29 — Stage61/62 decision-safety iteration

- Weighted stability by material input change.
- Added six-GW tap-through Wildcard XI/bench previews using the Pick Team pitch template.
- Added current-squad overlap and WC turnover display.
- Added a separate chip activation gate with HOLD / WATCH / CONSIDER semantics.
- Current gate: WC HOLD, FH WATCH (GW6 scout), BB HOLD, TC HOLD.
- Added Stage62 to present the gated chip result beside the raw opportunity signals.
- Extended Gameweek archival to preserve the simulation stack for later backtesting.

## Next planned iterations

1. Add visible deep-simulation freshness/material-change state beyond simple age.
2. Backtest archived simulation probabilities and route rankings as completed Gameweeks accumulate.
3. Feed a mature WC/FH gate into the authoritative synthesis only when safety criteria are sufficiently validated.
4. Add compact rival-consequence details without duplicating League Intel.
5. Validate mobile Safari rendering after the current Pages deployment and tune the compact layout from screenshots.
6. Add deadline-aware simulation intensity once normal background refresh costs are measured over several cycles.
