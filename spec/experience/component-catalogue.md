# Component Catalogue

Components consume canonical selectors/contracts. They may format values but must
not own scoring, squad-overlay or recommendation logic.

## Global components

| Component | Required inputs | Contract |
|---|---|---|
| App header | league name, lifecycle, artifact freshness | Shows target GW and a concise phase/freshness line |
| Primary navigation | available views, active view, phase priority | One active tab; selection persists safely; touch accessible |
| KPI strip | canonical manager selector, league selector, score basis | Rank, named GW score basis, gap/lead context and bank; never recalculates totals |
| Freshness indicator | target GW, generated time, source time, lifecycle, warnings | `Fresh`, `updated Nm ago`, `update delayed` or `inapplicable`; timestamp has full accessible value |
| Status legend | semantic tokens used on current surface | Only shows states actually present; mappings match all children |
| Error/degraded banner | retained snapshot and warning codes | Explains what is stale/unavailable without replacing valid content |

## Decision components

| Component | Purpose | Important states |
|---|---|---|
| Decision hero | One promoted action and concise rationale | hold, roll, transfer route, contested, blocked, stale |
| Route comparison | Compare working alternatives consistently | recommended, selected working, declared executed, invalid, superseded |
| Route evidence | Explain uplift, XI effect, ownership, timing, risk and evidence | available, mixed, unavailable, stale |
| Action control | Record working choice or explicit execution | idle, confirming, saved, failed; execution requires explicit command |
| Decision breakers | Conditions that trigger reassessment | clear, watch, triggered |
| Decision history | Preserve recommendation/action over time | historical frozen, superseded, officially reconciled |

## Team components

| Component | Purpose | Contract |
|---|---|---|
| Pitch XI | Visualise legal XI and formation | Receives selected XI; does not select players internally |
| Player plate | Player identity, fixture, selection/captaincy and relevant score | State and performance are separate tokens |
| Bench strip | Submitted/recommended bench order | Bench order explicit; projected autosub marker optional in live context |
| Captaincy card | Captain, vice and rationale | Distinguishes recommended, submitted, projected promoted and official-final |
| Selection rationale | Explain marginal choices | References compared player IDs and canonical input factors |

## Live components

| Component | Purpose | Contract |
|---|---|---|
| Personal live scoreboard | Immediate Terry score/rank status | Shows named score basis, raw/hit/net if needed, players live/remaining and freshness |
| Live player strip | Compact progress through Terry's submitted players | Upcoming neutral, live cyan, complete solid slate; raw/counting points visible |
| Manager matrix | Compare all managers and players | Uses same projected-rule selector as KPIs; bounded horizontal region |
| Score build-up matrix | Explain how each manager total is formed | Captain first, other counted players, then bench; projected in/out visible |
| Threat/leverage ledger | Relative loss/gain per player | Exposure basis named; state colour retained independently |
| Fixture progress | Show completed/live/upcoming fixture sequence | Same state tokens and counts as player components |
| Movement badge | Temporary `+N`/`−N` correction | Expires without mutating the underlying score/state |

## Monitoring components

| Component | Purpose | Contract |
|---|---|---|
| Change summary | What changed since the named baseline | Baseline timestamp/GW visible |
| Watch item | Injury, workload, price, research or decision breaker | Severity, source, freshness and affected player/action |
| Trend spark/chart | Direction and volatility across snapshots | Named metric, baseline and missing-data handling |
| Next event card | Next fixture/deadline/review moment | Absolute time plus relative time |
| Workflow health | Data/job reliability | Last successful generation, delayed/failed state and affected surfaces |

## Player/research components

| Component | Purpose | Contract |
|---|---|---|
| Player row/card | Ranked candidate summary | Player ID, position, price, factors, confidence and squad/action badges |
| Factor breakdown | Explain composite score | Named factors with scale and missing evidence; no unexplained “AI score” |
| Fixture strip | Multi-GW opponents/difficulty | Blank/double explicit; horizon named |
| Workload summary | Midweek/international involvement | Minutes, starts, goals, assists, rating source and injury evidence separately sourced |
| Filters/sort | Bound and reorder player set | URL/local preference optional; never mutates domain data |

## Component refresh rules

1. Background data refresh preserves active tab, scroll where practical, expanded
   rows and keyboard focus.
2. An updated component displays a short movement/freshness cue without flashing
   the entire page.
3. Components reject inapplicable target-GW data.
4. Optional data failure renders an unavailable substate, not an empty replacement
   for the parent component.
5. Every score-bearing component declares its score basis in data/accessibility
   metadata even if the visible label is shortened.
