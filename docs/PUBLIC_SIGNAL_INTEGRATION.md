# Zero-Cost Signal Integration Roadmap

## Objective

Improve the FPL Decision Centre's probability of winning the target mini-league without adding any new paid subscriptions.

The principle is **independent evidence, not more pundit noise**. Existing Football Scout access remains a qualitative corroboration layer. Public/free data should strengthen the quantitative model underneath Transfer, Pick Team, Player Pool, League Intel, captaincy, chips and rival simulations.

## What already exists

The current engine already has:

- official FPL ETL and current-squad reconstruction
- six-GW player pool and fixture horizon
- availability and schedule-load evidence
- Football Scout consensus
- transfer/price-pressure market watch
- mini-league ownership / EO semantics
- shield, neutral and leverage roles
- captaincy model and review
- Monte Carlo transfer simulation
- multi-GW path simulation
- adaptive rival simulation
- chip path simulation / wildcard / free-hit optimisation
- season-maturity calibration
- decision journal, recommendation history and backtesting
- authoritative cross-model decision synthesis

Therefore new work must add evidence or improve calibration rather than duplicate an existing UI feature.

## Signal ladder

### Tier 0 — official FPL data (free, stable, highest operational trust)

Use before introducing new scraping dependencies.

1. Player expected-goals / expected-assists / expected-goal-involvement fields.
2. Starts and minutes converted to conservative expected-minutes evidence.
3. Team attack / defence strength fields.
4. Official `ep_next` stored as a benchmark only, not treated as ground truth.
5. Current ownership, transfers and official availability/news.
6. Official price-change information when/where exposed by the game.

Status: **Phase 1 started on this branch.**

### Tier 1 — existing Football Scout access

Use for information the FPL feed does not model well:

- predicted lineups / rotation
- injuries and press-conference interpretation
- role changes
- penalties / set pieces
- tactical position changes
- expert buy/hold/sell context

Rule: Scout modifies confidence and xMins/role assumptions; it should not replace the quantitative base model.

### Tier 2 — free public football data

Candidate sources, subject to stability and lawful/public access:

- Football-Data.co.uk free Premier League CSVs: historical/current results, match odds, totals and Asian-handicap odds.
- Public historical FPL datasets such as vaastav/Fantasy-Premier-League for leakage-safe backtesting and priors.
- Public expected-goal datasets where programmatic access is stable and terms permit it.

Use cases:

- team-strength prior
- market-implied match strength
- calibration/backtesting across prior seasons
- promoted/new-player prior construction

Do **not** create a production dependency on an undocumented endpoint unless a fallback exists.

### Tier 3 — free public FPL tools as benchmark / validation

Examples include LiveFPL public ownership/EO views and other free public planning information.

Use only when they provide a signal that cannot be reconstructed reliably from official FPL league data. Prefer our own mini-league calculation for target-rival decisions.

## Model changes

### 1. Expected minutes

Expected minutes is a first-class signal, separate from `chance_of_playing`.

Initial free estimate:

- position prior
- season starts / gameweeks
- season minutes / gameweeks
- shrink strongly in early season
- schedule-load / midweek-minutes modifier
- official availability
- Scout lineup / injury evidence when present

Future enhancement:

- start probability
- 60+ probability
- 80+ probability
- cameo probability
- manager/player rotation history

The engine should expose both the mean expected minutes and uncertainty.

### 2. Underlying performance

Do not reward raw goals/assists as if finishing variance is persistent skill.

Prefer:

- xG/90
- xA/90
- xGI/90
- team attacking environment
- role / set pieces / penalties

Early-season evidence must be shrunk toward positional/player priors.

### 3. Team-strength / market layer

Current `market_watch.py` is a **transfer-price market** model, not a betting-market model.

Add a separate team/match-strength component rather than overloading `market.json`.

Potential fields:

- home/draw/away fair probability
- expected total goals proxy
- clean-sheet probability proxy
- team scoring environment
- strength delta against the official FPL fixture rating
- source timestamp and confidence

Use this as an independent calibration signal. Large disagreement with the internal model should increase investigation/uncertainty rather than blindly overwrite the forecast.

### 4. Rival-specific objective

Keep mini-league game theory as the distinctive layer.

For every candidate action estimate:

- expected FPL points
- expected relative points against each target rival
- effective ownership within the actual league
- captaincy multiplier exposure
- probability of finishing above each rival
- probability of winning the league
- downside tail / variance

The strategy posture should continue to vary by gap and season stage:

- PROTECT
- BALANCED
- CONTROLLED CHASE
- CHASE

A differential is useful only when it has sufficient expected value. Low ownership alone is not a reason to select a player.

### 5. Captaincy

Captaincy should optimise a separate objective with:

- xPts
- xMins
- ceiling / variance
- scoring environment
- penalty / set-piece role
- rival captain EO
- league posture

Return three interpretable views where useful:

- safest captain
- highest-EV captain
- best chase/leverage captain

The authoritative recommendation selects among them based on league state.

### 6. Decision audit

Continue the decision journal but expand evaluation from outcome to process quality.

Store at deadline:

- candidates considered
- projected mean and uncertainty
- expected minutes
- rival exposure
- model disagreement
- recommendation confidence
- selected action

After the GW, attribute outcome into:

- decision quality / expected value
- finishing variance
- minutes/rotation miss
- captaincy variance
- bench variance
- model calibration error

This prevents the engine learning that a lucky bad decision was good.

## Source / cost policy

Production source order:

1. Official FPL public data
2. Existing paid access already owned by the user (Football Scout)
3. Stable free public datasets
4. Free public web data with a documented fallback

Never require a new paid subscription for the core engine.

Any source must carry:

- source name
- fetched/generated timestamp
- freshness status
- confidence / coverage
- graceful fallback behaviour

The engine should remain functional if any Tier 2/3 external source is temporarily unavailable.

## Delivery order

### Phase 1 — current branch

- [x] Add official expected-goal/assist/involvement fields to Player Pool.
- [x] Add conservative expected-minutes estimate from official starts/minutes.
- [x] Add official team-strength context to fixture/player records.
- [x] Blend xMins and xGI/90 lightly into calibrated projections.
- [x] Increase uncertainty for rotation-risk xMins.
- [ ] Run production-equivalent validation and compare recommendation deltas against main.

### Phase 2 — free market/team strength

- [ ] Add a separate match-strength dataset from a stable free source.
- [ ] Calibrate fair probabilities / totals from historical odds without bookmaker margin where possible.
- [ ] Compare market strength to official FPL fixture rating.
- [ ] Feed only bounded deltas into projection mean/confidence.

### Phase 3 — xMins v2

- [ ] Model start / cameo / 60+ / 80+ probabilities.
- [ ] Incorporate Scout predicted-lineup evidence.
- [ ] Add manager/player rotation history.
- [ ] Backtest minutes calibration separately from points calibration.

### Phase 4 — league-winning objective

- [ ] Extend simulations to report probability of beating target rival(s), not only expected points.
- [ ] Produce league-win probability for candidate transfers/captains/chips.
- [ ] Use posture-dependent utility rather than fixed leverage weights.

### Phase 5 — audit and learning

- [ ] Persist model component snapshots at deadline.
- [ ] Score forecast calibration and decision EV after each GW.
- [ ] Detect systematic model bias and adjust bounded weights only with sufficient sample size.

## Guardrails

- No stale hard-coded player/team/price facts.
- No single external model becomes authoritative.
- No early-season overreaction to tiny samples.
- No black-box combined score without component evidence.
- No sacrificing strong shared players simply to create a differential.
- No paid dependency required for production operation.
- Mobile/iPhone stability remains a non-negotiable product constraint.
