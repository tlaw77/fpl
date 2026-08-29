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
2. **Forward Path** — the next provisional intervention from multi-GW planning. Future moves are explicitly branches, not commitments.
3. **Model Robustness** — cross-model support and the magnitude hurdle required before an additional transfer is promoted.
4. **Chip Radar** — WC/FH/BB/TC as opportunity scouts, with first-half portfolio pressure and hard deployment inflection.
5. **Wildcard Lab** — only when a generated WC candidate exists. It uses the same football-pitch visual template as Pick Team so a potential WC can be assessed as an actual XI plus bench, not as a list of names.

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
Multi-GW paths, adaptive rivals, TC/BB paths and bounded WC/FH squad construction. Persist results to JSON. Full-squad chip search uses input-aware caching and should be invalidated when GW, squad or budget changes.

### 3. Deadline intensity
Future enhancement: increase simulation depth/frequency near the deadline and after material events (injury/news, declared/completed transfer, major price/budget change, schedule change).

The web UI reads the latest completed snapshot and should never block waiting for deep simulation.

## Stability over time

Next enhancement: archive simulation summaries instead of only overwriting them. Derive:

- action persistence over recent runs;
- player/path appearance frequency;
- chip-window persistence;
- model-flip frequency;
- age of the last deep snapshot and material changes since it ran.

This allows Outlook to distinguish a persistent signal from a transient model spike.

## Current implementation

Frontend assets:

- `docs/team-outlook-stage61.js`
- `docs/team-outlook-stage61.css`

Data consumed:

- `data/decision_synthesis.json`
- `data/full_squad_chip_optimizer.json`

The Stage61 view is additive: it wraps the existing Pick Team rendering rather than replacing the proven pitch renderer.

## Next planned iterations

1. Persist simulation history/stability snapshots.
2. Add material-change invalidation metadata and deep-simulation freshness state.
3. Feed WC/FH opportunity scouts into authoritative chip synthesis only after safety gates are met.
4. Add selectable future GW Wildcard XI previews when multiple WC windows become credible.
5. Add compact rival-consequence details without duplicating League Intel.
6. Validate mobile Safari rendering and keep all Stage61 assets cache-busted.
