# FPL Decision Engine — Capability Progress

This is the durable progress gauge for the zero-extra-cost, mini-league-winning decision engine.

Progress is capability-weighted, not commit-count weighted. A milestone advances only after production-equivalent validation succeeds.

## Current validated progress: 96%

Last validated milestone: **hindsight-safe historical calibration and backtest feedback with minimum-evidence safeguards**.

Current validation gate: **decision-quality self-evaluation, calibration drift and continuous model-health monitoring**.

## Capability roadmap

| Progress | Capability | Status |
|---|---|---|
| 0–40% | Core FPL data, squad reconstruction, transfers, rivals, legal simulation | COMPLETE |
| 40–60% | Decision quality: Scout, uncertainty, schedule load, underlying stats | COMPLETE |
| 60–65% | Independent free market/team-strength calibration | COMPLETE |
| 65–72% | Probabilistic xMins: appearance/start/cameo/60+/80+ | COMPLETE |
| 72–78% | Explainable cross-source agreement/disagreement intelligence | COMPLETE |
| 78–82% | Route-level probability of taking/holding mini-league lead over explicit horizon | COMPLETE |
| 82–86% | Estimated season-end mini-league win probability with uncertainty-aware continuation | COMPLETE |
| 86–91% | League-state-aware captaincy: Safe / Best-EV / Chase modes | COMPLETE |
| 91–96% | Historical calibration and backtesting feedback | COMPLETE |
| 96–100% | Decision-quality self-evaluation, calibration drift and continuous model-health monitoring | IN PROGRESS |

## Validation rules

A capability is not counted complete merely because code exists. It should satisfy the relevant checks below:

1. New public sources fail gracefully and cannot break the core FPL decision path.
2. Early-season evidence is shrunk and bounded so small samples cannot dominate.
3. Feature-branch validation must never commit generated snapshots into `main`.
4. Full ETL / simulation / decision synthesis must complete successfully.
5. Existing legal-squad, budget, captaincy, rival and chip contracts must remain valid.
6. League-game-theory overlays must remain secondary to expected-value evidence early in the season and grow only as season state warrants.
7. Long-horizon or season-end probabilities must expose confidence/assumptions rather than imply false precision.
8. Calibration feedback may recommend investigation before it has enough evidence; it must not mutate model coefficients automatically from a tiny sample.
9. Model-health monitoring must distinguish insufficient evidence from genuine drift or source degradation.
10. No new paid dependency is allowed.

## Current public/free signal stack

- Official FPL API: squad/player/team/fixture/price/ownership/expected-stat truth.
- Existing Football Scout access: qualitative/team-news corroboration.
- FotMob public match information: schedule and workload evidence where available.
- Football-Data.co.uk free odds feed: independent market-strength calibration when available.
- Internal probabilistic xMins model.
- Internal signal consensus/disagreement model.
- Shared Monte Carlo, multi-GW, adaptive-rival and chip simulations.
- Explicit horizon league-lead probability and confidence-discounted season-win estimate.
- League-state-aware immediate captaincy with future Gameweeks re-optimised rather than pre-committed.
- Hindsight-safe `projection_history/gwN.json` snapshots paired with finalized all-player FPL outcomes.
- Sample-gated calibration audit for points, uncertainty and minutes probabilities.

## Strategic objective

The engine should not simply maximise projected FPL points. It should preserve expected value as the foundation while increasingly answering:

> Which legal decision gives this team the best chance of winning this specific mini-league, given the current point gap, rivals, ownership, uncertainty and time remaining?

Early season: EV dominates and league position is treated as noisy.

Late season: rival exposure, variance, captaincy leverage and estimated league-win probability can become materially decision-relevant.
