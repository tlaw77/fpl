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
4. **Plan Stability** — action persistence, current leader persistence, recurring future route and recurring chip window across recent completed model runs.
5. **Chip Radar** — WC/FH/BB/TC as opportunity scouts, with first-half portfolio pressure and hard deployment inflection.
6. **Wildcard Lab** — only when a generated WC candidate exists. It uses the same football-pitch visual template as Pick Team so a potential WC can be assessed as an actual XI plus bench, not as a list of names.

## Wildcard safety

The Wildcard optimiser currently has exact position and max-three-per-club legality, but public FPL picks do not expose exact selling prices. Until exact spendable budget can be reconstructed, the budget is labelled `estimated` and Wildcard/Free Hit outputs remain provisional.

A large raw simulated uplift is not an activation recommendation. Future synthesis gates should include:

- exact/credible spendable budget;
- season maturity;
- squad turnover required;
- robustness across projection perturbations;
- visible future fixture/chip opportunity cost;
- half-season chip expiry pressure;
- rival-aware utility without allowing league leverage to justify a poor FPL move.

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

Materially identical snapshots inside 20 minutes are deduplicated. Persistence is explicitly labelled as repeated-model stability, not independent evidence.

Future refinement: weight runs with genuinely changed inputs more strongly than cached/unchanged-input runs.

## Current implementation

Frontend assets:

- `docs/team-outlook-stage61.js`
- `docs/team-outlook-stage61.css`

Backend/history assets:

- `simulation_stability.py`
- `.github/workflows/simulation-stability.yml`
- `data/simulation_stability.json`

Data consumed by Outlook:

- `data/decision_synthesis.json`
- `data/path_simulation.json`
- `data/full_squad_chip_optimizer.json`
- `data/simulation_stability.json`

The browser reads these from the repository raw-data endpoint with cache-busting rather than assuming `/data` is deployed beside `/docs` on GitHub Pages.

The Stage61 view is additive: it wraps the existing Pick Team rendering rather than replacing the proven pitch renderer. A MutationObserver now re-attaches the Team/Outlook shell after any later Pick Team redraw, preserving the user's selected Team/Outlook mode.

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

## Next planned iterations

1. Weight simulation-history observations by material input change rather than treating all retained runs equally.
2. Add material-change invalidation metadata and a visible deep-simulation freshness state.
3. Feed WC/FH opportunity scouts into authoritative chip synthesis only after safety gates are met.
4. Add selectable future-GW Wildcard XI previews when multiple WC windows become credible.
5. Add compact rival-consequence details without duplicating League Intel.
6. Validate mobile Safari rendering after the current Pages deployment and tune the compact layout from screenshots.
